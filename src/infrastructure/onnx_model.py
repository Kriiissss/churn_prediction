from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort

from src.domain.interfaces import IModel


def _repo_root() -> Path:
    # src/infrastructure/onnx_model.py -> parents[2] == корень репозитория
    return Path(__file__).resolve().parents[2]


class ONNXModel(IModel):
    """
    ONNX inference для определения языка текста.

    Важно:
      - модель принимает list[str]
      - возвращает probabilities + labels в фиксированном порядке классов
    """

    def __init__(
        self,
        *,
        onnx_path: Path | None = None,
        classes_path: Path | None = None,
    ) -> None:
        repo = _repo_root()
        resolved_onnx = onnx_path or (repo / "models" / "language_detector.onnx")
        resolved_classes = classes_path or (repo / "models" / "classes.json")

        if not resolved_onnx.is_file():
            raise FileNotFoundError(f"ONNX model not found: {resolved_onnx}")
        if not resolved_classes.is_file():
            raise FileNotFoundError(f"classes.json not found: {resolved_classes}")

        self._classes_path = resolved_classes
        self._classes: list[str] = json.loads(resolved_classes.read_text(encoding="utf-8"))
        if not self._classes:
            raise ValueError(f"Empty classes mapping: {resolved_classes}")

        self._session = ort.InferenceSession(str(resolved_onnx), providers=["CPUExecutionProvider"])

    def _extract_probabilities(
        self,
        outputs: list[Any],
        output_names: list[str],
        batch_size: int,
    ) -> list[list[float]]:
        """
        ONNX runtime может вернуть:
          - numpy array [batch, num_classes] (zipmap=False)
          - список словарей (zipmap=True)
        """
        probabilities_candidate: list[list[float]] | None = None

        for out, name in zip(outputs, output_names):
            if isinstance(out, np.ndarray) and out.ndim == 2 and out.shape[0] == batch_size:
                probabilities_candidate = out.astype(np.float32).tolist()
                break

            if isinstance(out, list) and out and isinstance(out[0], dict):
                rows: list[list[float]] = []
                for d in out:
                    row = [float(d.get(cls, 0.0)) for cls in self._classes]
                    rows.append(row)
                probabilities_candidate = rows
                break

            _ = name

        if probabilities_candidate is None:
            for out in outputs:
                if isinstance(out, np.ndarray) and out.ndim == 2 and out.shape[0] == batch_size:
                    probabilities_candidate = out.astype(np.float32).tolist()
                    break

        if probabilities_candidate is None:
            raise RuntimeError("Unable to extract probabilities from ONNX outputs.")

        return probabilities_candidate

    def predict(self, texts: list[str]) -> tuple[list[list[float]], list[str]]:
        if not texts:
            raise ValueError("texts must be non-empty")
        if any(not t or not str(t).strip() for t in texts):
            raise ValueError("all texts must be non-empty strings")

        input_name = self._session.get_inputs()[0].name
        x = np.array(texts, dtype=object)

        output_names = [o.name for o in self._session.get_outputs()]
        outputs = self._session.run(output_names, {input_name: x})

        probabilities = self._extract_probabilities(
            outputs=outputs,
            output_names=output_names,
            batch_size=len(texts),
        )
        return probabilities, list(self._classes)

