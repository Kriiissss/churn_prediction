#!/usr/bin/env python3
"""
Обучение языковой модели (char n-grams + LogisticRegression) и конвертация в ONNX.

Данные берутся строго из структуры директории:
  data/corpus/<lang>/*.txt
где:
  <lang> — label (код языка).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import StringTensorType

import onnx  # noqa: F401  # требуется для проверки/сериализации, типы зависят от сборки
import boto3
from dotenv import load_dotenv
from botocore.exceptions import EndpointConnectionError, NoCredentialsError


def load_dataset(path: str):
    """
    Загружает датасет из data/corpus/<label>/*.txt.

    Returns:
        texts: list[str]
        labels: list[str]
    """
    corpus_root = Path(path)
    if not corpus_root.is_dir():
        raise ValueError(f"Корень корпуса не найден: {corpus_root}")

    texts: list[str] = []
    labels: list[str] = []

    # Стабильный порядок, чтобы воспроизводить обучение.
    for label_dir in sorted(p for p in corpus_root.iterdir() if p.is_dir()):
        label = label_dir.name
        for txt_path in sorted(label_dir.glob("*.txt")):
            text = txt_path.read_text(encoding="utf-8")
            if not text.strip():
                continue
            texts.append(text)
            labels.append(label)

    if not texts:
        raise ValueError(f"Не найдено ни одного .txt файла в {corpus_root}")

    return texts, labels


def build_pipeline() -> Pipeline:
    """
    Pipeline:
      CountVectorizer(analyzer='char', ngram_range=(1,3))
      LogisticRegression(max_iter=1000)
    """
    vectorizer = CountVectorizer(analyzer="char", ngram_range=(1, 3))
    clf = LogisticRegression(max_iter=1000)
    return Pipeline([("vect", vectorizer), ("clf", clf)])


def _repo_root() -> Path:
    # scripts/train_model.py -> parents[1] == repo root
    return Path(__file__).resolve().parent.parent


def _upload_models_to_minio(
    *,
    models_dir: Path,
    remote_onnx_key: str,
    remote_classes_key: str,
) -> None:
    """
    Загружает обученные файлы модели в MinIO/S3 бакет `models`.

    Настройки берутся из `.env` в корне репозитория.
    """
    load_dotenv(dotenv_path=_repo_root() / ".env")

    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")
    models_bucket = os.getenv("MINIO_MODELS_BUCKET", "models")

    if not endpoint or not access_key or not secret_key:
        # Если в окружении нет MinIO-конфига — не валимся жёстко, просто уведомим.
        print("MinIO credentials are missing (.env). Skip uploading models.")
        return

    onnx_local = models_dir / "language_detector.onnx"
    classes_local = models_dir / "classes.json"
    if not onnx_local.is_file():
        raise FileNotFoundError(f"Missing ONNX file: {onnx_local}")
    if not classes_local.is_file():
        raise FileNotFoundError(f"Missing classes file: {classes_local}")

    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )

    print(f"Uploading models to s3://{models_bucket}/ ...")
    try:
        client.upload_file(str(onnx_local), models_bucket, remote_onnx_key)
        client.upload_file(str(classes_local), models_bucket, remote_classes_key)
        print("Models uploaded.")
    except EndpointConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to MinIO at {endpoint}. "
            "Start MinIO with: `docker compose up -d` and try again."
        ) from e
    except NoCredentialsError as e:
        raise RuntimeError("MinIO credentials are missing/invalid in .env") from e


class LanguageDetectorSklearn:
    """
    Небольшой wrapper, который гарантирует наличие `classes_` (требование ЛР),
    даже если базовый объект `Pipeline` не позволяет задать `classes_` вручную.
    """

    def __init__(self, pipeline: Pipeline, classes: list[str]) -> None:
        self._pipeline = pipeline
        self.classes_ = classes

    def predict(self, texts: list[str]) -> list[str]:
        # Делегируем в обученный pipeline.
        return list(self._pipeline.predict(texts))


def main() -> int:
    parser = argparse.ArgumentParser(description="Train language detector and export ONNX.")
    parser.add_argument("--corpus-root", type=Path, default=Path("data/corpus"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    texts, labels = load_dataset(str(args.corpus_root))

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=labels if len(set(labels)) > 1 else None,
    )

    model = build_pipeline()
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {acc:.4f} (test_size={args.test_size})")

    # Требование: сохранить mapping классов.
    # LogisticRegression хранит порядок классов в clf.classes_.
    classes = list(model.named_steps["clf"].classes_)
    # Требование ЛР: чтобы существовал `model.classes_`,
    # поэтому оборачиваем pipeline в объект со settable атрибутом.
    model_with_classes = LanguageDetectorSklearn(pipeline=model, classes=classes)

    args.models_dir.mkdir(parents=True, exist_ok=True)
    classes_path = args.models_dir / "classes.json"
    with classes_path.open("w", encoding="utf-8") as f:
        json.dump(model_with_classes.classes_, f, ensure_ascii=False, indent=2)

    # Конвертация ВЕСЬ pipeline в ONNX.
    # Важно: initial_types должен быть string tensor.
    initial_types = [("input", StringTensorType([None]))]

    # Отключаем zipmap, чтобы получить вероятности как тензор.
    options = {id(model.named_steps["clf"]): {"zipmap": False}}

    onnx_model = convert_sklearn(model, initial_types=initial_types, options=options)
    onnx_path = args.models_dir / "language_detector.onnx"
    args.models_dir.mkdir(parents=True, exist_ok=True)
    onnx.save_model(onnx_model, str(onnx_path))

    # По требованию: после обучения отправляем модель и classes.json в MinIO.
    # remote keys лежат на верхнем уровне бакета `models`.
    _upload_models_to_minio(
        models_dir=args.models_dir,
        remote_onnx_key=os.getenv("LANGUAGE_MODEL_ONNX_REMOTE_KEY", "language_detector.onnx"),
        remote_classes_key=os.getenv("LANGUAGE_MODEL_CLASSES_REMOTE_KEY", "classes.json"),
    )

    print(f"Saved ONNX: {onnx_path}")
    print(f"Saved classes: {classes_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

