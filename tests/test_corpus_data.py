"""
Тесты структуры корпуса data/corpus: каталоги языков и чтение .txt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CORPUS = _REPO_ROOT / "data" / "corpus"


def test_corpus_language_directories_exist() -> None:
    assert _CORPUS.is_dir()
    expected = {"de", "en", "es", "fr"}
    found = {p.name for p in _CORPUS.iterdir() if p.is_dir()}
    assert expected <= found


@pytest.mark.parametrize(
    "lang",
    ["en", "fr", "de", "es"],
)
def test_corpus_has_multiple_txt_files_per_language(lang: str) -> None:
    lang_dir = _CORPUS / lang
    assert lang_dir.is_dir()
    txts = sorted(lang_dir.glob("*.txt"))
    assert len(txts) >= 3


def test_corpus_txt_files_are_readable_utf8() -> None:
    for lang_dir in sorted(p for p in _CORPUS.iterdir() if p.is_dir()):
        for txt in lang_dir.glob("*.txt"):
            content = txt.read_text(encoding="utf-8")
            assert isinstance(content, str)
            assert len(content.strip()) > 0
