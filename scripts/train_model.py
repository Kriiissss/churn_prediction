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
import subprocess
import sys
from pathlib import Path

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import StringTensorType

import onnx  # noqa: F401  # требуется для проверки/сериализации, типы зависят от сборки


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

    print(f"Saved ONNX: {onnx_path}")
    print(f"Saved classes: {classes_path}")

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

