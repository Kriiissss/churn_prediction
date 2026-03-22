"""
Тесты «версий» корпуса: смена каталога (аналог git checkout + dvc pull) и согласованность языков.

Полный цикл с реальным git/dvc в CI не обязателен: здесь проверяется то же свойство модели —
список языков и предсказание зависят только от содержимого выбранного корпуса.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.infrastructure.language_detector import CorpusLanguageDetector


def _write_lang(tmp: Path, code: str, content: str) -> None:
    d = tmp / code
    d.mkdir(parents=True, exist_ok=True)
    (d / "corpus.txt").write_text(content, encoding="utf-8")


def test_model_sees_only_languages_from_current_corpus_version(tmp_path: Path) -> None:
    v1 = tmp_path / "v1"
    v1.mkdir()
    _write_lang(v1, "en", "hello world english text " * 50)
    _write_lang(v1, "fr", "bonjour le monde français " * 50)

    v2 = tmp_path / "v2"
    v2.mkdir()
    _write_lang(v2, "en", "hello world english text " * 50)
    _write_lang(v2, "fr", "bonjour le monde français " * 50)
    _write_lang(v2, "es", "el zorro salta y el español tiene muchas palabras " * 50)

    d1 = CorpusLanguageDetector(corpus_root=v1)
    d2 = CorpusLanguageDetector(corpus_root=v2)

    assert d1.get_available_languages() == ["en", "fr"]
    assert set(d2.get_available_languages()) == {"en", "es", "fr"}

    assert d1.detect("hello english museum learning natural language") == "en"
    assert d2.detect("el zorro salta sobre el perro y toma café") == "es"


def test_after_switch_corpus_model_behavior_matches_directory(tmp_path: Path) -> None:
    """
    Имитация: был корпус без es, затем «подтянули» данные — появился es.
    """
    before = tmp_path / "before"
    before.mkdir()
    _write_lang(before, "de", "Der Fuchs und die Bahn und das Frühstück " * 40)

    after = tmp_path / "after"
    after.mkdir()
    _write_lang(after, "de", "Der Fuchs und die Bahn und das Frühstück " * 40)
    _write_lang(after, "es", "El metro y el desayuno y el zorro marrón " * 40)

    det_before = CorpusLanguageDetector(corpus_root=before)
    det_after = CorpusLanguageDetector(corpus_root=after)

    assert "es" not in det_before.get_available_languages()
    assert "es" in det_after.get_available_languages()

    assert det_before.detect("Der Fuchs springt über den faulen Hund") == "de"
    assert det_after.detect("El zorro salta y el desayuno está listo") == "es"


def test_dvc_corpus_is_tracked_when_dvc_files_present() -> None:
    """
    Дымовой тест репозитория: после `dvc add data/corpus` должен появиться data/corpus.dvc.
    (Если DVC ещё не инициализировали локально — тест пропускается.)
    """
    root = Path(__file__).resolve().parents[1]
    corpus_dvc = root / "data" / "corpus.dvc"
    dvc_dir = root / ".dvc"
    if not dvc_dir.exists():
        pytest.skip("DVC не инициализирован в этом клоне.")
    assert corpus_dvc.exists(), "Ожидается data/corpus.dvc после dvc add data/corpus"
