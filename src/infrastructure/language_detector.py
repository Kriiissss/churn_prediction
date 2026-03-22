"""
Детектор языка по корпусу текстов: профили символьных n-грамм и косинусное сходство.

Корпус: в корне лежат подкаталоги с кодами языков; в каждом — файлы *.txt.
Языки и объём данных версионируются через DVC (см. README).
"""

from __future__ import annotations

import math
import os
import re
from collections import Counter
from pathlib import Path

from src.domain.interfaces import ILanguageDetector

# Размеры n-грамм (символьные); пара значений обычно устойчивее, чем одно.
_NGRAM_SIZES: tuple[int, ...] = (2, 3)

# Убираем пунктуацию, сохраняем буквы (в т.ч. Unicode) и пробелы.
_NON_WORD = re.compile(r"[^\w\s]", re.UNICODE)


def _resolve_default_corpus_root() -> Path:
    """
    Корень корпуса по умолчанию: <корень проекта>/data/corpus.

    Переопределение: переменная окружения LANGUAGE_CORPUS_ROOT (удобно для тестов и CI).
    """
    env = os.environ.get("LANGUAGE_CORPUS_ROOT")
    if env:
        return Path(env).resolve()
    # src/infrastructure/language_detector.py -> parents[2] == корень репозитория
    return Path(__file__).resolve().parents[2] / "data" / "corpus"


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    cleaned = _NON_WORD.sub(" ", lowered)
    return " ".join(cleaned.split())


def _char_ngrams(text: str, n: int) -> Counter[str]:
    """Символьные n-граммы с паддингом пробелами (границы слов)."""
    padded = f" {text} "
    if len(padded) < n:
        return Counter()
    return Counter(padded[i : i + n] for i in range(len(padded) - n + 1))


def _build_ngram_profile(text: str) -> Counter[str]:
    normalized = _normalize_text(text)
    profile: Counter[str] = Counter()
    for n in _NGRAM_SIZES:
        profile.update(_char_ngrams(normalized, n))
    return profile


def _cosine_similarity(a: Counter[str], b: Counter[str]) -> float:
    """Косинус между векторами частот n-грамм (разреженные Counter)."""
    if not a or not b:
        return 0.0
    keys_a = set(a)
    keys_b = set(b)
    intersection = keys_a & keys_b
    if not intersection:
        return 0.0
    dot = sum(a[k] * b[k] for k in intersection)
    # Нормируем как вектора частот (не вероятности) — масштаб согласован.
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb)


class CorpusLanguageDetector(ILanguageDetector):
    """
    Загружает тексты из corpus_root/<lang>/*.txt и строит эталонные профили n-грамм.
    """

    def __init__(self, corpus_root: Path | None = None) -> None:
        self._corpus_root = corpus_root or _resolve_default_corpus_root()
        # Профиль эталона по языку (агрегированный по всем файлам языка).
        self._profiles: dict[str, Counter[str]] = {}
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not self._corpus_root.is_dir():
            raise ValueError(f"Каталог корпуса не найден: {self._corpus_root}")

        for entry in sorted(self._corpus_root.iterdir()):
            # В корне могут лежать служебные файлы — учитываем только каталоги.
            if not entry.is_dir():
                continue
            lang_code = entry.name
            chunks: list[str] = []
            for txt_path in sorted(entry.glob("*.txt")):
                chunks.append(txt_path.read_text(encoding="utf-8"))
            if not chunks:
                # Пустая папка языка не считается доступным языком.
                continue
            combined = "\n".join(chunks)
            profile = _build_ngram_profile(combined)
            self._profiles[lang_code] = profile

        if not self._profiles:
            raise ValueError(
                f"Не найдено ни одного языкового корпуса (.txt в подкаталогах): {self._corpus_root}"
            )

    def get_available_languages(self) -> list[str]:
        # Стабильный порядок: лексикографически по коду языка.
        return sorted(self._profiles.keys())

    def detect(self, text: str) -> str:
        if not text or not text.strip():
            raise ValueError("Текст для определения языка не должен быть пустым.")

        sample = _build_ngram_profile(text)

        scored: list[tuple[float, str]] = []
        for lang, reference in self._profiles.items():
            score = _cosine_similarity(sample, reference)
            scored.append((score, lang))

        # Сначала больший score, при равенстве — лексикографически по коду (детерминизм).
        scored.sort(key=lambda item: (-item[0], item[1]))
        return scored[0][1]
