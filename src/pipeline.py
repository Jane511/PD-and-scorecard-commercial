from pathlib import Path

from .config import (
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    N_BORROWERS,
    OUTPUT_DIR,
    PUBLIC_INPUT_DIR,
    RANDOM_SEED,
    SCORECARD_OUTPUT_DIR,
)
from .data_generation import (
    generate_bank_statement_data,
    generate_cashflow_lending_financials,
    generate_credit_bureau_reports,
    generate_product_underwriting_data,
)
from .eligibility import assess_product_eligibility
from .features import (
    assemble_feature_dataset,
    build_borrower_snapshot,
    build_trend_features,
    calculate_financial_ratios,
)
from .output import save_dataframe, write_portfolio_summary
from .policy import build_policy_overlay
from .public_data import build_public_data_context
from .scorecard import fit_pd_scorecard


def _ensure_directories() -> None:
    for path in [DATA_RAW_DIR, DATA_PROCESSED_DIR, PUBLIC_INPUT_DIR, OUTPUT_DIR, SCORECARD_OUTPUT_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def run_full_pipeline(
    n_borrowers: int = N_BORROWERS,
    seed: int = RANDOM_SEED,
    persist: bool = True,
    use_public_data: bool = True,
) -> dict:
    _ensure_directories()

    public_data_context = build_public_data_context(use_public_data=use_public_data)
    financials = generate_cashflow_lending_financials(
        n_borrowers=n_borrowers,
        seed=seed,
        industry_profile_df=public_data_context["industry_profiles"],
    )
    ratios = calculate_financial_ratios(financials)
    trends = build_trend_features(ratios)
    snapshot = build_borrower_snapshot(ratios, trends)
    bureau = generate_credit_bureau_reports(snapshot, seed=seed)
    bank_monthly, bank_summary = generate_bank_statement_data(
        snapshot,
        seed=seed,
        transaction_benchmark_df=public_data_context["transaction_benchmarks"],
    )
    product_underwriting = generate_product_underwriting_data(
        snapshot,
        bureau,
        bank_summary,
        seed=seed,
        transaction_benchmark_df=public_data_context["transaction_benchmarks"],
        invoice_benchmark_df=public_data_context["invoice_benchmarks"],
    )
    pre_eligibility_dataset = snapshot.merge(bureau, on=["borrower_id", "borrower_name"], how="left")
    pre_eligibility_dataset = pre_eligibility_dataset.merge(bank_summary, on=["borrower_id", "borrower_name"], how="left")
    pre_eligibility_dataset = pre_eligibility_dataset.merge(product_underwriting, on="borrower_id", how="left")
    eligibility = assess_product_eligibility(pre_eligibility_dataset)
    feature_dataset = assemble_feature_dataset(snapshot, bureau, bank_summary, product_underwriting, eligibility, seed=seed)
    scorecard_result = fit_pd_scorecard(feature_dataset, seed=seed)
    policy_overlay = build_policy_overlay(scorecard_result["portfolio_scored"])

    product_family_summary = (
        feature_dataset.groupby(["product_family", "facility_type", "eligibility_status"], as_index=False)
        .agg(
            borrowers=("borrower_id", "count"),
            observed_default_rate=("default_12m", "mean"),
            average_limit=("requested_limit", "mean"),
        )
        .sort_values(["product_family", "facility_type", "eligibility_status"])
    )

    if persist:
        save_dataframe(financials, DATA_RAW_DIR / "cashflow_lending_financials.csv")
        save_dataframe(bureau, DATA_RAW_DIR / "credit_bureau_reports.csv")
        save_dataframe(bank_monthly, DATA_RAW_DIR / "bank_statement_monthly.csv")
        save_dataframe(bank_summary, DATA_RAW_DIR / "bank_statement_summary.csv")
        save_dataframe(product_underwriting, DATA_RAW_DIR / "product_underwriting_data.csv")
        save_dataframe(snapshot, DATA_PROCESSED_DIR / "borrower_snapshot.csv")
        save_dataframe(feature_dataset, DATA_PROCESSED_DIR / "cashflow_lending_feature_dataset.csv")
        save_dataframe(eligibility, DATA_PROCESSED_DIR / "product_eligibility_matrix.csv")
        save_dataframe(product_family_summary, DATA_PROCESSED_DIR / "product_family_summary.csv")
        save_dataframe(public_data_context["industry_profiles"], DATA_PROCESSED_DIR / "public_industry_profiles.csv")
        save_dataframe(public_data_context["listed_company_financials"], DATA_PROCESSED_DIR / "public_listed_company_financials_standardized.csv")
        save_dataframe(public_data_context["listed_company_benchmarks"], DATA_PROCESSED_DIR / "public_listed_company_benchmarks.csv")
        save_dataframe(public_data_context["transaction_records"], DATA_PROCESSED_DIR / "public_transaction_records_standardized.csv")
        save_dataframe(public_data_context["transaction_benchmarks"], DATA_PROCESSED_DIR / "public_transaction_benchmarks.csv")
        save_dataframe(public_data_context["invoice_records"], DATA_PROCESSED_DIR / "public_invoice_records_standardized.csv")
        save_dataframe(public_data_context["invoice_benchmarks"], DATA_PROCESSED_DIR / "public_invoice_benchmarks.csv")
        save_dataframe(public_data_context["public_data_provenance"], DATA_PROCESSED_DIR / "public_data_provenance.csv")

        save_dataframe(scorecard_result["iv_summary"], SCORECARD_OUTPUT_DIR / "01_iv_summary.csv")
        save_dataframe(scorecard_result["woe_table"], SCORECARD_OUTPUT_DIR / "02_woe_table.csv")
        save_dataframe(scorecard_result["coefficients"], SCORECARD_OUTPUT_DIR / "03_scorecard_coefficients.csv")
        save_dataframe(scorecard_result["points_table"], SCORECARD_OUTPUT_DIR / "04_scorecard_points.csv")
        save_dataframe(scorecard_result["train_scored"], SCORECARD_OUTPUT_DIR / "05_train_scored.csv")
        save_dataframe(scorecard_result["test_scored"], SCORECARD_OUTPUT_DIR / "06_test_scored.csv")
        save_dataframe(scorecard_result["metadata"], SCORECARD_OUTPUT_DIR / "07_scorecard_metadata.csv")
        save_dataframe(scorecard_result["calibration_table"], SCORECARD_OUTPUT_DIR / "08_calibration_table.csv")
        save_dataframe(scorecard_result["score_band_summary"], SCORECARD_OUTPUT_DIR / "09_score_band_summary.csv")
        save_dataframe(scorecard_result["monitoring_psi"], SCORECARD_OUTPUT_DIR / "10_monitoring_psi.csv")
        save_dataframe(scorecard_result["decile_table"], SCORECARD_OUTPUT_DIR / "11_test_deciles.csv")
        save_dataframe(scorecard_result["ks_table"], SCORECARD_OUTPUT_DIR / "12_test_ks.csv")
        save_dataframe(product_family_summary, SCORECARD_OUTPUT_DIR / "13_product_family_summary.csv")

        save_dataframe(policy_overlay, OUTPUT_DIR / "policy_overlay.csv")
        write_portfolio_summary(
            OUTPUT_DIR / "portfolio_summary.md",
            feature_dataset,
            scorecard_result,
            policy_overlay,
            public_data_context["public_data_provenance"],
        )

    return {
        "public_data_context": public_data_context,
        "financials": financials,
        "bureau": bureau,
        "bank_monthly": bank_monthly,
        "bank_summary": bank_summary,
        "product_underwriting": product_underwriting,
        "snapshot": snapshot,
        "feature_dataset": feature_dataset,
        "eligibility": eligibility,
        "scorecard_result": scorecard_result,
        "product_family_summary": product_family_summary,
        "policy_overlay": policy_overlay,
    }
