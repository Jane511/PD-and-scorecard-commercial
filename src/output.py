from pathlib import Path

import pandas as pd


def save_dataframe(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_portfolio_summary(
    path: Path,
    feature_df: pd.DataFrame,
    scorecard_result: dict,
    policy_df: pd.DataFrame,
    public_data_provenance: pd.DataFrame | None = None,
) -> None:
    metrics = scorecard_result["metadata"].iloc[0]
    band_summary = scorecard_result["score_band_summary"]
    selected_features = metrics["selected_features"].split("|")
    default_rate = feature_df["default_12m"].mean()

    lines = [
        "# Cash Flow Lending PD and Scorecard Summary",
        "",
        f"- Borrowers scored: {len(feature_df)}",
        f"- Observed synthetic default rate: {default_rate:.1%}",
        f"- Product families covered: {feature_df['product_family'].nunique()}",
        f"- Eligibility pass rate: {(feature_df['eligibility_status'] == 'Eligible').mean():.1%}",
        f"- Train AUC: {metrics['train_auc']:.3f}",
        f"- Test AUC: {metrics['test_auc']:.3f}",
        f"- Selected scorecard features: {', '.join(selected_features)}",
        "",
        "## Product family coverage",
        "",
    ]

    family_summary = (
        feature_df.groupby("product_family")
        .agg(
            borrowers=("borrower_id", "count"),
            default_rate=("default_12m", "mean"),
        )
        .reset_index()
        .sort_values("product_family")
    )
    for row in family_summary.itertuples(index=False):
        lines.append(
            f"- {row.product_family}: {int(row.borrowers)} borrowers, default rate {row.default_rate:.1%}"
        )

    eligibility_summary = (
        feature_df.groupby(["product_family", "eligibility_status"])
        .size()
        .reset_index(name="borrowers")
        .sort_values(["product_family", "eligibility_status"])
    )
    lines.extend(
        [
            "",
            "## Eligibility mix",
            "",
        ]
    )
    for row in eligibility_summary.itertuples(index=False):
        lines.append(
            f"- {row.product_family} / {row.eligibility_status}: {int(row.borrowers)}"
        )

    lines.extend(
        [
            "",
        "## Score bands",
        "",
        ]
    )
    for row in band_summary.itertuples(index=False):
        lines.append(
            f"- Band {row.score_band}: {int(row.obs)} borrowers, default rate {row.default_rate:.1%}"
        )

    approve_count = int(policy_df["decision"].isin(["Approve"]).sum())
    refer_count = int(policy_df["decision"].str.contains("Refer").sum())
    decline_count = int((policy_df["decision"] == "Decline").sum())
    lines.extend(
        [
            "",
            "## Policy overlay",
            "",
            f"- Approve outcomes: {approve_count}",
            f"- Refer outcomes: {refer_count}",
            f"- Decline outcomes: {decline_count}",
            "- Scope excludes property-backed lending and property development purposes.",
        ]
    )

    if public_data_provenance is not None and not public_data_provenance.empty:
        lines.extend(
            [
                "",
                "## Public data mix",
                "",
            ]
        )
        for row in public_data_provenance.itertuples(index=False):
            lines.append(
                f"- {row.dataset_name}: {row.status} ({int(row.records_loaded)} records)"
            )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
