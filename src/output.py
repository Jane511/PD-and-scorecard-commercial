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
    pd_final_df: pd.DataFrame | None = None,
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

    if pd_final_df is not None and not pd_final_df.empty:
        lines.extend(
            [
                "",
                "## PD final layer",
                "",
                f"- Average raw 12-month PD: {pd_final_df['pd_12m_raw'].mean():.1%}",
                f"- Average final 12-month PD: {pd_final_df['pd_final'].mean():.1%}",
                f"- Watchlist share: {pd_final_df['watchlist_flag'].mean():.1%}",
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


def write_property_portfolio_summary(
    path: Path,
    property_df: pd.DataFrame,
    scorecard_result: dict,
    property_pd_final_df: pd.DataFrame,
    reference_provenance: pd.DataFrame | None = None,
) -> None:
    metrics = scorecard_result["metadata"].iloc[0]
    band_summary = scorecard_result["score_band_summary"]
    selected_features = metrics["selected_features"].split("|")

    lines = [
        "# Property-Backed Lending PD Summary",
        "",
        f"- Facilities scored: {len(property_df)}",
        f"- Observed synthetic default rate: {property_df['default_12m'].mean():.1%}",
        f"- Product types covered: {property_df['product_type'].nunique()}",
        f"- Average current LVR: {property_df['current_lvr'].mean():.1%}",
        f"- Average market softness score: {property_df['market_softness_score'].mean():.2f}",
        f"- Train AUC: {metrics['train_auc']:.3f}",
        f"- Test AUC: {metrics['test_auc']:.3f}",
        f"- Selected scorecard features: {', '.join(selected_features)}",
        "",
        "## Product coverage",
        "",
    ]

    product_summary = (
        property_df.groupby("product_type")
        .agg(
            facilities=("facility_id", "count"),
            default_rate=("default_12m", "mean"),
            average_lvr=("current_lvr", "mean"),
        )
        .reset_index()
        .sort_values("product_type")
    )
    for row in product_summary.itertuples(index=False):
        lines.append(
            f"- {row.product_type}: {int(row.facilities)} facilities, default rate {row.default_rate:.1%}, average LVR {row.average_lvr:.1%}"
        )

    segment_summary = (
        property_df.groupby(["property_segment", "region_risk_band", "market_softness_band"])
        .size()
        .reset_index(name="facilities")
        .sort_values(["property_segment", "region_risk_band", "market_softness_band"])
    )
    lines.extend(["", "## Public reference overlays", ""])
    for row in segment_summary.itertuples(index=False):
        lines.append(
            f"- {row.property_segment}: {int(row.facilities)} facilities, region band {row.region_risk_band}, cycle band {row.market_softness_band}"
        )

    lines.extend(["", "## Score bands", ""])
    for row in band_summary.itertuples(index=False):
        lines.append(
            f"- Band {row.score_band}: {int(row.obs)} facilities, default rate {row.default_rate:.1%}"
        )

    lines.extend(
        [
            "",
            "## Property PD final layer",
            "",
            f"- Average raw 12-month PD: {property_pd_final_df['pd_12m_raw'].mean():.1%}",
            f"- Average final 12-month PD: {property_pd_final_df['pd_final'].mean():.1%}",
            f"- Watchlist share: {property_pd_final_df['watchlist_flag'].mean():.1%}",
        ]
    )

    if reference_provenance is not None and not reference_provenance.empty:
        lines.extend(["", "## Reference-layer provenance", ""])
        for row in reference_provenance.itertuples(index=False):
            lines.append(f"- {row.dataset_name}: {row.status} ({int(row.records_loaded)} records)")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_combined_portfolio_summary(
    path: Path,
    cashflow_result: dict,
    property_result: dict,
    combined_pd_final_df: pd.DataFrame,
) -> None:
    cashflow_df = cashflow_result["feature_dataset"]
    cashflow_pd_final_df = cashflow_result["pd_final_result"]["facility_pd_final"]
    property_df = property_result["facility_dataset"]
    property_pd_final_df = property_result["pd_final_result"]["facility_pd_final"]

    lines = [
        "# Commercial Lending PD Summary",
        "",
        "## Cash Flow Stream",
        "",
        f"- Borrowers scored: {len(cashflow_df)}",
        f"- Product families covered: {cashflow_df['product_family'].nunique()}",
        f"- Average final PD: {cashflow_pd_final_df['pd_final'].mean():.1%}",
        "",
        "## Property-Backed Stream",
        "",
        f"- Facilities scored: {len(property_df)}",
        f"- Product types covered: {property_df['product_type'].nunique()}",
        f"- Average final PD: {property_pd_final_df['pd_final'].mean():.1%}",
        f"- Public reference tables used: region bands, property cycle, arrears environment, downturn overlays",
        "",
        "## Combined EL Feed",
        "",
        f"- Total facilities in combined PD final: {len(combined_pd_final_df)}",
        f"- Cashflow facilities: {(combined_pd_final_df['pd_model_stream'] == 'cashflow').sum()}",
        f"- Property facilities: {(combined_pd_final_df['pd_model_stream'] == 'property').sum()}",
        f"- Average combined final PD: {combined_pd_final_df['pd_final'].mean():.1%}",
        "",
        "## Key Files",
        "",
        "- `outputs/tables/pd_model_output.csv`",
        "- `outputs/tables/score_band_output.csv`",
        "- `outputs/tables/policy_decisions.csv`",
        "- `outputs/tables/pipeline_validation_report.csv`",
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
