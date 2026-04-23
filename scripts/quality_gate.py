#!/usr/bin/env python3
from __future__ import annotations

import argparse

from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from scripts.train_model import build_pipeline, load_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Quality gate for language detector.")
    parser.add_argument("--corpus-root", default="data/corpus")
    parser.add_argument("--threshold", type=float, default=0.98)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    texts, labels = load_dataset(args.corpus_root)
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
    print(f"quality_gate accuracy={acc:.4f}, threshold={args.threshold:.4f}")

    if acc <= args.threshold:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
