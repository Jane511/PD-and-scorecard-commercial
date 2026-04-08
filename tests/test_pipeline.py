from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import FORBIDDEN_KEYWORDS
from src.pipeline import run_full_pipeline


def test_pipeline_generates_cashflow_only_scope():
    result = run_full_pipeline(n_borrowers=120, n_property_facilities=180, seed=7, persist=False)
    feature_df = result["feature_dataset"]
    policy_df = result["policy_overlay"]
    pd_final_df = result["pd_final_result"]["facility_pd_final"]
    pd_final_checks = result["pd_final_result"]["validation_checks"]
    property_result = result["property_result"]
    property_df = property_result["facility_dataset"]
    property_pd_final_df = property_result["pd_final_result"]["facility_pd_final"]
    property_pd_checks = property_result["pd_final_result"]["validation_checks"]
    combined_pd_final_df = result["combined_pd_final"]
    metadata = result["scorecard_result"]["metadata"].iloc[0]
    property_metadata = property_result["scorecard_result"]["metadata"].iloc[0]
    product_summary = result["product_family_summary"]
    public_data_context = result["public_data_context"]
    property_reference_context = result["property_reference_context"]

    assert not feature_df.empty
    assert not pd_final_df.empty
    assert not property_df.empty
    assert not property_pd_final_df.empty
    assert not combined_pd_final_df.empty
    assert len(result["scorecard_result"]["selected_features"]) >= 8
    assert metadata["train_auc"] >= 0.60
    assert metadata["test_auc"] >= 0.60
    assert property_metadata["train_auc"] >= 0.60
    assert property_metadata["test_auc"] >= 0.60
    assert feature_df["product_family"].nunique() == 6
    assert feature_df["facility_type"].nunique() == 8
    assert {"Eligible", "Conditional", "Outside Criteria"} & set(feature_df["eligibility_status"].unique())
    assert product_summary["product_family"].nunique() == 6
    assert policy_df["decision"].isin(["Approve", "Refer", "Refer with conditions", "Decline"]).all()
    assert policy_df["eligibility_status"].isin(["Eligible", "Conditional", "Outside Criteria"]).all()
    assert pd_final_df["facility_id"].is_unique
    assert pd_final_df["pd_final"].between(0, 1).all()
    assert {"RG1", "RG2", "RG3", "RG4", "RG5"} & set(pd_final_df["risk_grade"].unique())
    assert {"no_negative_pd", "no_pd_above_100pct", "score_band_monotonic"} <= set(pd_final_checks["check_name"])
    assert property_df["facility_id"].is_unique
    assert property_df["reference_join_check"].all()
    assert property_df["product_type"].nunique() == 3
    assert property_pd_final_df["pd_final"].between(0, 1).all()
    assert {"RG1", "RG2", "RG3", "RG4", "RG5"} & set(property_pd_final_df["risk_grade"].unique())
    assert {"no_negative_pd", "no_pd_above_100pct", "score_band_monotonic"} <= set(property_pd_checks["check_name"])
    assert {"cashflow", "property"} <= set(combined_pd_final_df["pd_model_stream"].unique())
    assert combined_pd_final_df["facility_id"].is_unique
    assert "industry_overlay_source" in feature_df.columns
    assert "financial_benchmark_source" in feature_df.columns
    assert "public_data_provenance" in public_data_context
    assert not public_data_context["public_data_provenance"].empty
    assert not public_data_context["listed_company_financials"].empty
    assert not public_data_context["listed_company_benchmarks"].empty
    assert not public_data_context["transaction_benchmarks"].empty
    assert not public_data_context["invoice_benchmarks"].empty
    assert "Wholesale Trade" in set(public_data_context["listed_company_benchmarks"]["industry"])
    assert not property_reference_context["segment_reference"].empty
    assert not property_reference_context["arrears_environment"].empty
    assert not property_reference_context["downturn_overlays"].empty

    facility_text = " ".join(feature_df["facility_type"].astype(str).tolist()).lower()
    purpose_text = " ".join(feature_df["purpose"].astype(str).tolist()).lower()
    for keyword in FORBIDDEN_KEYWORDS:
        assert keyword not in facility_text
        assert keyword not in purpose_text
