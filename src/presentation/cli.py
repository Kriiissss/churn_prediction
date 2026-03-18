from __future__ import annotations

import argparse

from src.domain.entities import CustomerActivity
from src.presentation.factories import create_churn_analysis_service


def _build_recommendations(is_high_risk: bool) -> list[str]:
    if is_high_risk:
        return ["- Offer discount", "- Contact support team"]
    return ["- Keep current service level"]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Churn Prediction CLI (mock ML).")
    parser.add_argument("--client_id", type=int, required=True)
    parser.add_argument("--days_since_last_login", type=int, required=True)
    parser.add_argument("--total_spend", type=float, required=True)
    parser.add_argument("--support_tickets_count", type=int, required=True)
    return parser


def run_cli(args: argparse.Namespace) -> None:
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

