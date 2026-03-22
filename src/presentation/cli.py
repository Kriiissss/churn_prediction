from __future__ import annotations

import argparse

from src.domain.entities import CustomerActivity
from src.presentation.factories import create_churn_analysis_service, create_language_detector


def _build_recommendations(is_high_risk: bool) -> list[str]:
    if is_high_risk:
        return ["- Offer discount", "- Contact support team"]
    return ["- Keep current service level"]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Churn Prediction CLI (mock ML) и определение языка текста по корпусу (DVC)."
    )
    parser.add_argument(
        "--text",
        type=str,
        default=None,
        help="Если указано — определить язык этого текста по корпусу data/corpus (иначе сценарий churn).",
    )
    parser.add_argument("--client_id", type=int, default=None)
    parser.add_argument("--days_since_last_login", type=int, default=None)
    parser.add_argument("--total_spend", type=float, default=None)
    parser.add_argument("--support_tickets_count", type=int, default=None)
    return parser


def run_cli(args: argparse.Namespace) -> None:
    if args.text is not None:
        detector = create_language_detector()
        lang = detector.detect(args.text)
        print(f"Detected language: {lang}")
        print(f"Available languages: {', '.join(detector.get_available_languages())}")
        return

    missing = [
        name
        for name, value in (
            ("--client_id", args.client_id),
            ("--days_since_last_login", args.days_since_last_login),
            ("--total_spend", args.total_spend),
            ("--support_tickets_count", args.support_tickets_count),
        )
        if value is None
    ]
    if missing:
        raise SystemExit(f"Для сценария churn укажите: {', '.join(missing)} (либо используйте --text для языка).")

    activity = CustomerActivity(
        days_since_last_login=args.days_since_last_login,
        total_spend=args.total_spend,
        support_tickets_count=args.support_tickets_count,
    )

    service = create_churn_analysis_service()
    risk = service.analyze(activity)

    risk_label = "HIGH" if risk.is_high_risk else "LOW"
    recommendations = _build_recommendations(risk.is_high_risk)

    print(f"Client ID: {args.client_id}")
    print(f"Risk: {risk_label}")
    print(f"Score: {risk.risk_score:.1f}")
    print()
    print("Recommendation:")
    for line in recommendations:
        print(line)


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    run_cli(args)


if __name__ == "__main__":
    main()

