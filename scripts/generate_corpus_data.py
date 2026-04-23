#!/usr/bin/env python3
"""
Генерация демонстрационного языкового корпуса (подкаталоги = коды языков, внутри *.txt).

Использование:
  poetry run python scripts/generate_corpus_data.py
  poetry run python scripts/generate_corpus_data.py --output-root data/corpus --seed 42
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

# Запуск из корня репозитория: poetry run python scripts/...
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _paragraphs_for_lang(code: str, rng: random.Random) -> list[str]:
    """Набор осмысленных фраз по языку (для n-граммного детектора)."""
    pools: dict[str, list[str]] = {
        "en": [
            "The quick brown fox jumps over the lazy dog.",
            "Machine learning models need clean training data.",
            "London weather is often rainy but museums stay popular.",
            "Breakfast may include toast eggs and fresh coffee.",
            "Natural language processing helps computers read text.",
        ],
        "fr": [
            "Le renard brun rapide saute par-dessus le chien paresseux. Le français utilise des accents.",
            "L'apprentissage automatique transforme l'analyse des données.",
            "Paris est célèbre pour ses cafés, ses musées et ses promenades.",
            "Pour le petit-déjeuner on mange souvent une baguette avec du beurre.",
            "Le traitement du langage naturel ouvre de nouvelles applications.",
        ],
        "de": [
            "Der schnelle braune Fuchs springt über den faulen Hund. Das Deutsche hat Umlaute.",
            "Maschinelles Lernen verbessert Vorhersagen in vielen Branchen.",
            "Berlin bietet viele Parks, Museen und eine lebendige Musikszene.",
            "Zum Frühstück gibt es oft Brötchen, Marmelade und Kaffee.",
            "Verarbeitung natürlicher Sprache ist ein zentrales Forschungsfeld.",
        ],
        "es": [
            "El zorro marrón rápido salta sobre el perro perezoso. El español usa la ñ.",
            "El aprendizaje automático ayuda a extraer patrones de grandes cantidades de datos.",
            "Madrid combina historia, tapas y una vida nocturna animada.",
            "Para el desayuno muchas personas toman café con leche y pan tostado.",
            "El procesamiento del lenguaje natural es muy útil.",
        ],
    }
    base = pools.get(code, pools["en"])
    # Лёгкая вариативность без поломки языка
    out: list[str] = []
    for p in base:
        if rng.random() < 0.25:
            out.append(p + f" Variant {rng.randint(1, 9999)}.")
        else:
            out.append(p)
    return out


def generate_corpus(
    *,
    output_root: Path,
    languages: list[str],
    files_per_lang: int,
    seed: int | None,
) -> None:
    rng = random.Random(seed)
    for code in languages:
        lang_dir = output_root / code
        lang_dir.mkdir(parents=True, exist_ok=True)
        paras = _paragraphs_for_lang(code, rng)
        for i in range(files_per_lang):
            text = paras[i % len(paras)]
            if files_per_lang > len(paras):
                text = text + " " + paras[(i + 1) % len(paras)]
            path = lang_dir / f"sample_{i + 1:02d}.txt"
            path.write_text(text.strip() + "\n", encoding="utf-8")
            print(f"  записан {path.relative_to(_REPO_ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Генерация текстовых файлов корпуса для ЛР (языки по папкам).")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=_REPO_ROOT / "data" / "corpus",
        help="Корень корпуса (по умолчанию data/corpus)",
    )
    parser.add_argument(
        "--languages",
        type=str,
        default="en,fr,de,es",
        help="Коды языков через запятую (по умолчанию en,fr,de,es)",
    )
    parser.add_argument(
        "--files-per-lang",
        type=int,
        default=4,
        help="Сколько .txt файлов на язык (>=3 для требований ЛР)",
    )
    parser.add_argument("--seed", type=int, default=None, help="Seed для воспроизводимости")

    args = parser.parse_args()
    langs = [x.strip() for x in args.languages.split(",") if x.strip()]
    if args.files_per_lang < 1:
        print("ОШИБКА: files-per-lang должен быть >= 1")
        return 1

    print("=" * 60)
    print("Генерация корпуса")
    print("=" * 60)
    print(f"Корень: {args.output_root.resolve()}")
    print(f"Языки: {', '.join(langs)}")
    print(f"Файлов на язык: {args.files_per_lang}")
    if args.seed is not None:
        print(f"Seed: {args.seed}")
    print()

    try:
        generate_corpus(
            output_root=args.output_root.resolve(),
            languages=langs,
            files_per_lang=args.files_per_lang,
            seed=args.seed,
        )
    except OSError as e:
        print(f"ОШИБКА записи: {e}")
        return 1

    print()
    print("Готово. Дальше (Windows): scripts\\lab_dvc_push_corpus.bat")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
