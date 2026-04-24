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
import re
import subprocess
import sys
from pathlib import Path

import onnx
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import StringTensorType

MLFLOW_ONNX_ARTIFACT_PATH = "language_model_onnx"
MLFLOW_META_ARTIFACT_PATH = "language_model_artifacts"

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
            for variant in _augment_text(text.lower()):
                texts.append(variant)
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
    # Важно: lowercase=False убирает StringNormalizer из ONNX-графа и зависимость от locale.
    # В CI runner используется версия skl2onnx, где text vectorizer стабильно
    # конвертируется в ONNX в word-режиме.
    vectorizer = CountVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        token_pattern=r"\b\w+\b",
        lowercase=False,
    )
    clf = LogisticRegression(max_iter=2000, C=8.0)
    return Pipeline([("vect", vectorizer), ("clf", clf)])


def _augment_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []

    compact = " ".join(text.split())
    no_punct = re.sub(r"[^\w\s]", " ", compact)
    no_punct = " ".join(no_punct.split())
    no_digits = re.sub(r"\d+", " ", compact)
    no_digits = " ".join(no_digits.split())

    variants = [compact, no_punct, no_digits]
    # Стабильная дедупликация без изменения порядка.
    return list(dict.fromkeys(v for v in variants if v))


def _repo_root() -> Path:
    # scripts/train_model.py -> parents[1] == repo root
    return Path(__file__).resolve().parent.parent


def _dvc_run(*args: str, timeout: float = 120.0) -> subprocess.CompletedProcess[str]:
    """DVC из того же venv, что и текущий интерпретатор (надёжно под poetry run)."""
    return subprocess.run(
        [sys.executable, "-m", "dvc", *args],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _dvc_push_models(*, onnx_dvc: Path, classes_dvc: Path) -> None:
    """
    Отправляет артефакты модели в MinIO через DVC remote `models_storage`.

    Требования:
      - MinIO запущен
      - remote `models_storage` настроен (см. README)
    """
    out = _dvc_run(
        "push",
        "-r",
        "models_storage",
        str(onnx_dvc),
        str(classes_dvc),
        timeout=600.0,
    )
    if out.returncode != 0:
        raise RuntimeError(
            "dvc push failed.\n"
            f"stdout:\n{out.stdout}\n"
            f"stderr:\n{out.stderr}\n"
            "Hint: start MinIO (`docker compose up -d`) and verify DVC remote `models_storage`."
        )


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
    # На Windows cp1251 MLflow печатает emoji-ссылки и может упасть с UnicodeEncodeError.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Train language detector and export ONNX.")
    parser.add_argument("--corpus-root", type=Path, default=Path("data/corpus"))
    parser.add_argument("--models-dir", type=Path, default=Path("models"))
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument(
        "--skip-dvc",
        action="store_true",
        help="Не выполнять dvc add/push (только локальное обучение и экспорт ONNX).",
    )
    parser.add_argument("--model-name", type=str, default=os.getenv("MLFLOW_MODEL_NAME", "language_detector"))
    parser.add_argument("--model-stage", type=str, default=os.getenv("MLFLOW_MODEL_STAGE", "Production"))
    parser.add_argument("--model-alias", type=str, default=os.getenv("MLFLOW_MODEL_ALIAS", "production"))
    parser.add_argument("--accuracy-threshold", type=float, default=0.98)
    parser.add_argument(
        "--mlflow-experiment",
        type=str,
        default=os.getenv("MLFLOW_EXPERIMENT_NAME", "lab5_variant13_language_detector"),
    )
    args = parser.parse_args()

    texts, labels = load_dataset(str(args.corpus_root))

    x_train, x_test, y_train, y_test = train_test_split(
        texts,
        labels,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=labels if len(set(labels)) > 1 else None,
    )

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    import mlflow
    import mlflow.onnx

    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(args.mlflow_experiment)

    with mlflow.start_run(run_name="train_language_detector"):
        mlflow.log_params(
            {
                "model_name": args.model_name,
                "model_stage": args.model_stage,
                "model_alias": args.model_alias,
                "vectorizer_analyzer": "word",
                "vectorizer_ngram_range": "(1,2)",
                "vectorizer_token_pattern": r"\b\w+\b",
                "classifier": "LogisticRegression",
                "classifier_max_iter": 2000,
                "classifier_C": 8.0,
                "test_size": args.test_size,
                "random_state": args.random_state,
            }
        )

        model = build_pipeline()
        model.fit(x_train, y_train)

        y_pred = model.predict(x_test)
        acc = accuracy_score(y_test, y_pred)
        mlflow.log_metric("accuracy", float(acc))
        print(f"Accuracy: {acc:.4f} (test_size={args.test_size})")

        # Требование: сохранить mapping классов.
        # LogisticRegression хранит порядок классов в clf.classes_.
        classes = list(model.named_steps["clf"].classes_)
        model_with_classes = LanguageDetectorSklearn(pipeline=model, classes=classes)

        args.models_dir.mkdir(parents=True, exist_ok=True)
        classes_path = args.models_dir / "classes.json"
        with classes_path.open("w", encoding="utf-8") as f:
            json.dump(model_with_classes.classes_, f, ensure_ascii=False, indent=2)

        # Конвертация ВЕСЬ pipeline в ONNX.
        initial_types = [("input", StringTensorType([None]))]
        options = {id(model.named_steps["clf"]): {"zipmap": False}}
        onnx_model = convert_sklearn(model, initial_types=initial_types, options=options)
        onnx_path = args.models_dir / "language_detector.onnx"
        onnx.save_model(onnx_model, str(onnx_path))
        print(f"Saved ONNX: {onnx_path}")
        print(f"Saved classes: {classes_path}")

        onnx_proto = onnx.load(str(onnx_path))
        mlflow.onnx.log_model(
            onnx_model=onnx_proto,
            artifact_path=MLFLOW_ONNX_ARTIFACT_PATH,
            registered_model_name=args.model_name,
        )
        mlflow.log_artifact(str(classes_path), artifact_path=MLFLOW_META_ARTIFACT_PATH)

        if acc < args.accuracy_threshold:
            raise RuntimeError(f"Quality gate failed: accuracy={acc:.4f} <= {args.accuracy_threshold}")

        if args.skip_dvc:
            print("Skip DVC: --skip-dvc")
            return 0

        # Версионирование модели через DVC + remote `models_storage` (бакет `models` в MinIO).
        add_out = _dvc_run("add", str(onnx_path), str(classes_path), timeout=600.0)
        if add_out.returncode != 0:
            raise RuntimeError(
                "dvc add failed.\n"
                f"stdout:\n{add_out.stdout}\n"
                f"stderr:\n{add_out.stderr}\n"
                "Hint: ensure DVC is initialized and remote `models_storage` exists (see README)."
            )

        onnx_dvc = onnx_path.with_suffix(onnx_path.suffix + ".dvc")
        classes_dvc = classes_path.with_suffix(classes_path.suffix + ".dvc")
        _dvc_push_models(onnx_dvc=onnx_dvc, classes_dvc=classes_dvc)

        print("DVC: models pushed to remote `models_storage`.")
        print("DVC: verify workspace state:")
        print("  poetry run dvc status")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

