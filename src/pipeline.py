from .config import (
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    N_BORROWERS,
    N_PROPERTY_FACILITIES,
    OUTPUT_DIR,
    PD_FINAL_OUTPUT_DIR,
    PROPERTY_OUTPUT_DIR,
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
from .output import (
    save_dataframe,
    write_combined_portfolio_summary,
    write_portfolio_summary,
    write_property_portfolio_summary,
)
from .pd_final import build_pd_final_layer, summarise_final_pd_by_product, validate_pd_final_layer
from .pd_final_property import (
    build_property_pd_downturn_scenarios,
    build_property_pd_final_layer,
    save_property_pd_final_outputs,
    summarise_property_final_pd,
    validate_property_pd_final_layer,
)
from .pd_output_merge import build_combined_pd_final
from .policy import build_policy_overlay
from .property_data import generate_property_facility_dataset
from .property_model import fit_property_pd_scorecard
from .property_reference import build_property_reference_context
from .public_data import build_public_data_context
from .scorecard import fit_pd_scorecard


def _ensure_directories() -> None:
    for path in [
        DATA_RAW_DIR,
        DATA_PROCESSED_DIR,
        PUBLIC_INPUT_DIR,
        OUTPUT_DIR,
        SCORECARD_OUTPUT_DIR,
        PROPERTY_OUTPUT_DIR,
        PD_FINAL_OUTPUT_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def run_cashflow_pipeline(
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
    pd_final_inputs = scorecard_result["portfolio_scored"].merge(
        policy_overlay[
            [
                "facility_id",
                "recommended_limit",
                "decision",
                "review_frequency",
                "approval_authority",
                "pricing_margin_pct",
                "all_in_rate_pct",
            ]
        ],
        on="facility_id",
        how="left",
    )
    facility_pd_final = build_pd_final_layer(pd_final_inputs)
    pd_final_summary = summarise_final_pd_by_product(facility_pd_final)
    pd_final_validation_checks = validate_pd_final_layer(facility_pd_final)

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
        save_dataframe(facility_pd_final, PD_FINAL_OUTPUT_DIR / "facility_pd_final.csv")
        save_dataframe(pd_final_summary, PD_FINAL_OUTPUT_DIR / "pd_final_summary_by_product.csv")
        save_dataframe(pd_final_validation_checks, PD_FINAL_OUTPUT_DIR / "pd_final_validation_checks.csv")
        write_portfolio_summary(
            OUTPUT_DIR / "portfolio_summary.md",
            feature_dataset,
            scorecard_result,
            policy_overlay,
            facility_pd_final,
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
        "pd_final_result": {
            "facility_pd_final": facility_pd_final,
            "summary": pd_final_summary,
            "validation_checks": pd_final_validation_checks,
        },
    }


def run_property_pipeline(
    n_facilities: int = N_PROPERTY_FACILITIES,
    seed: int = RANDOM_SEED,
    persist: bool = True,
    use_public_data: bool = True,
    property_reference_context: dict | None = None,
) -> dict:
    _ensure_directories()

    property_reference_context = property_reference_context or build_property_reference_context(use_public_data=use_public_data)
    facility_dataset = generate_property_facility_dataset(
        n_facilities=n_facilities,
        seed=seed,
        property_reference_context=property_reference_context,
    )
    scorecard_result = fit_property_pd_scorecard(facility_dataset, seed=seed)
    facility_pd_final = build_property_pd_final_layer(scorecard_result["portfolio_scored"])
    property_pd_final_summary = summarise_property_final_pd(facility_pd_final)
    property_pd_final_validation = validate_property_pd_final_layer(facility_pd_final)
    property_pd_downturn_scenarios = build_property_pd_downturn_scenarios(
        facility_pd_final,
        property_reference_context["downturn_overlays"],
    )

    if persist:
        save_dataframe(property_reference_context["segment_reference"], DATA_PROCESSED_DIR / "property_reference_segments.csv")
        save_dataframe(property_reference_context["region_risk"], DATA_PROCESSED_DIR / "property_region_risk_reference.csv")
        save_dataframe(property_reference_context["property_cycle"], DATA_PROCESSED_DIR / "property_cycle_reference.csv")
        save_dataframe(property_reference_context["arrears_environment"], DATA_PROCESSED_DIR / "property_arrears_environment.csv")
        save_dataframe(property_reference_context["downturn_overlays"], DATA_PROCESSED_DIR / "property_downturn_overlays.csv")
        save_dataframe(property_reference_context["reference_provenance"], DATA_PROCESSED_DIR / "property_reference_provenance.csv")
        save_dataframe(facility_dataset, DATA_PROCESSED_DIR / "property_backed_facility_dataset.csv")

        save_dataframe(scorecard_result["iv_summary"], PROPERTY_OUTPUT_DIR / "01_iv_summary.csv")
        save_dataframe(scorecard_result["woe_table"], PROPERTY_OUTPUT_DIR / "02_woe_table.csv")
        save_dataframe(scorecard_result["coefficients"], PROPERTY_OUTPUT_DIR / "03_scorecard_coefficients.csv")
        save_dataframe(scorecard_result["points_table"], PROPERTY_OUTPUT_DIR / "04_scorecard_points.csv")
        save_dataframe(scorecard_result["train_scored"], PROPERTY_OUTPUT_DIR / "05_train_scored.csv")
        save_dataframe(scorecard_result["test_scored"], PROPERTY_OUTPUT_DIR / "06_test_scored.csv")
        save_dataframe(scorecard_result["metadata"], PROPERTY_OUTPUT_DIR / "07_scorecard_metadata.csv")
        save_dataframe(scorecard_result["calibration_table"], PROPERTY_OUTPUT_DIR / "08_calibration_table.csv")
        save_dataframe(scorecard_result["score_band_summary"], PROPERTY_OUTPUT_DIR / "09_score_band_summary.csv")
        save_dataframe(scorecard_result["decile_table"], PROPERTY_OUTPUT_DIR / "10_test_deciles.csv")
        save_dataframe(scorecard_result["ks_table"], PROPERTY_OUTPUT_DIR / "11_test_ks.csv")
        save_dataframe(scorecard_result["monitoring_psi"], PROPERTY_OUTPUT_DIR / "12_monitoring_psi.csv")
        save_property_pd_final_outputs(
            facility_pd_final,
            property_pd_final_summary,
            property_pd_final_validation,
            property_pd_downturn_scenarios,
            PD_FINAL_OUTPUT_DIR,
        )
        write_property_portfolio_summary(
            PROPERTY_OUTPUT_DIR / "property_portfolio_summary.md",
            facility_dataset,
            scorecard_result,
            facility_pd_final,
            property_reference_context["reference_provenance"],
        )

    return {
        "property_reference_context": property_reference_context,
        "facility_dataset": facility_dataset,
        "scorecard_result": scorecard_result,
        "pd_final_result": {
            "facility_pd_final": facility_pd_final,
            "summary": property_pd_final_summary,
            "validation_checks": property_pd_final_validation,
            "downturn_scenarios": property_pd_downturn_scenarios,
        },
    }


def run_full_pipeline(
    n_borrowers: int = N_BORROWERS,
    n_property_facilities: int = N_PROPERTY_FACILITIES,
    seed: int = RANDOM_SEED,
    persist: bool = True,
    use_public_data: bool = True,
    property_reference_context: dict | None = None,
) -> dict:
    cashflow_result = run_cashflow_pipeline(
        n_borrowers=n_borrowers,
        seed=seed,
        persist=persist,
        use_public_data=use_public_data,
    )
    property_result = run_property_pipeline(
        n_facilities=n_property_facilities,
        seed=seed,
        persist=persist,
        use_public_data=use_public_data,
        property_reference_context=property_reference_context,
    )
    combined_pd_final = build_combined_pd_final(
        cashflow_result["pd_final_result"]["facility_pd_final"],
        property_result["pd_final_result"]["facility_pd_final"],
    )

    if persist:
        save_dataframe(combined_pd_final, PD_FINAL_OUTPUT_DIR / "facility_pd_final_combined.csv")
        write_combined_portfolio_summary(
            OUTPUT_DIR / "portfolio_summary.md",
            cashflow_result,
            property_result,
            combined_pd_final,
        )

    result = dict(cashflow_result)
    result.update(
        {
            "cashflow_result": cashflow_result,
            "property_result": property_result,
            "property_reference_context": property_result["property_reference_context"],
            "combined_pd_final": combined_pd_final,
        }
    )
    return result
