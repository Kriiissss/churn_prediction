"""
Тесты детектора языка: корпус на диске, n-граммы, фабрика и интерфейс ILanguageDetector.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from src.domain.interfaces import ILanguageDetector
from src.infrastructure.language_detector import (
    CorpusLanguageDetector,
    _build_ngram_profile,
    _char_ngrams,
    _cosine_similarity,
    _normalize_text,
    _resolve_default_corpus_root,
)
from src.presentation.factories import create_language_detector


class SuperCallingLanguageDetector(ILanguageDetector):
    """Покрывает вызов базовой реализации интерфейса (как в тестах churn)."""

    def detect(self, text: str) -> str:
        return super().detect(text)

    def get_available_languages(self) -> list[str]:
        return super().get_available_languages()


def test_interface_super_call_raises_not_implemented() -> None:
    det = SuperCallingLanguageDetector()
    with pytest.raises(NotImplementedError):
        det.detect("hello")
    with pytest.raises(NotImplementedError):
        det.get_available_languages()


def test_resolve_default_corpus_root_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGUAGE_CORPUS_ROOT", str(tmp_path))
    assert _resolve_default_corpus_root() == tmp_path.resolve()


def test_resolve_default_corpus_root_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGUAGE_CORPUS_ROOT", raising=False)
    root = _resolve_default_corpus_root()
    assert root.name == "corpus"
    # root = <репозиторий>/data/corpus → pyproject.toml в корне репозитория
    assert (root.parent.parent / "pyproject.toml").exists()


def test_normalize_text_strips_punctuation() -> None:
    assert _normalize_text("Hello, WORLD!!!") == "hello world"


def test_char_ngrams_padded_too_short_for_large_n() -> None:
    # Для n=3 при слишком коротком паддинге возвращается пустой Counter (ветка len(padded) < n).
    assert _char_ngrams("", 3) == Counter()


def test_build_ngram_profile_combines_sizes() -> None:
    profile = _build_ngram_profile("abc")
    assert profile


def test_cosine_similarity_empty_or_disjoint() -> None:
    assert _cosine_similarity(Counter(), Counter({"a": 1})) == 0.0
    assert _cosine_similarity(Counter({"a": 1}), Counter({"b": 1})) == 0.0


def test_cosine_similarity_non_trivial() -> None:
    a = Counter({"aa": 2, "bb": 1})
    b = Counter({"aa": 1, "cc": 9})
    assert _cosine_similarity(a, b) > 0.0


def test_corpus_root_missing_raises(tmp_path: Path) -> None:
    missing = tmp_path / "nope"
    with pytest.raises(ValueError, match="Каталог корпуса не найден"):
        CorpusLanguageDetector(corpus_root=missing)


def test_corpus_without_any_txt_raises(tmp_path: Path) -> None:
    (tmp_path / "en").mkdir()
    with pytest.raises(ValueError, match="Не найдено ни одного языкового корпуса"):
        CorpusLanguageDetector(corpus_root=tmp_path)


def test_skips_non_directory_entries_and_empty_language_dirs(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("ignore", encoding="utf-8")
    (tmp_path / "empty_lang").mkdir()
    lang = tmp_path / "en"
    lang.mkdir()
    (lang / "a.txt").write_text("hello world from english corpus sample text", encoding="utf-8")

    det = CorpusLanguageDetector(corpus_root=tmp_path)
    assert det.get_available_languages() == ["en"]


def test_factory_returns_working_detector() -> None:
    det = create_language_detector()
    assert isinstance(det, CorpusLanguageDetector)
    assert "en" in det.get_available_languages()


def test_detect_empty_text_raises() -> None:
    det = create_language_detector()
    with pytest.raises(ValueError, match="не должен быть пустым"):
        det.detect("   ")


@pytest.mark.parametrize(
    "text,expected",
    [
        (
            "The quick brown fox jumps over the lazy dog and visits museums in London.",
            "en",
        ),
        (
            "Le petit-déjeuner avec une baguette et de la confiture est très typique en France.",
            "fr",
        ),
        (
            "Der schnelle braune Fuchs springt über den faulen Hund und fährt mit der Bahn.",
            "de",
        ),
        (
            "El zorro marrón salta sobre el perro y el desayuno incluye pan tostado.",
            "es",
        ),
    ],
)
def test_detect_language_against_repo_corpus(text: str, expected: str) -> None:
    det = create_language_detector()
    assert det.detect(text) == expected


def test_get_available_languages_sorted() -> None:
    det = create_language_detector()
    langs = det.get_available_languages()
    assert langs == sorted(langs)
    assert set(langs) >= {"en", "fr", "de", "es"}
