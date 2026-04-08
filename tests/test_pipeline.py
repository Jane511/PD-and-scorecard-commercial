from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import FORBIDDEN_KEYWORDS
from src.pipeline import run_full_pipeline


def test_pipeline_generates_cashflow_only_scope():
    result = run_full_pipeline(n_borrowers=120, seed=7, persist=False)
    feature_df = result["feature_dataset"]
    policy_df = result["policy_overlay"]
    metadata = result["scorecard_result"]["metadata"].iloc[0]
    product_summary = result["product_family_summary"]
    public_data_context = result["public_data_context"]

    assert not feature_df.empty
    assert len(result["scorecard_result"]["selected_features"]) >= 8
    assert metadata["train_auc"] >= 0.60
    assert metadata["test_auc"] >= 0.60
    assert feature_df["product_family"].nunique() == 6
    assert feature_df["facility_type"].nunique() == 8
    assert {"Eligible", "Conditional", "Outside Criteria"} & set(feature_df["eligibility_status"].unique())
    assert product_summary["product_family"].nunique() == 6
    assert policy_df["decision"].isin(["Approve", "Refer", "Refer with conditions", "Decline"]).all()
    assert policy_df["eligibility_status"].isin(["Eligible", "Conditional", "Outside Criteria"]).all()
    assert "industry_overlay_source" in feature_df.columns
    assert "financial_benchmark_source" in feature_df.columns
    assert "public_data_provenance" in public_data_context
    assert not public_data_context["public_data_provenance"].empty
    assert not public_data_context["listed_company_financials"].empty
    assert not public_data_context["listed_company_benchmarks"].empty
    assert not public_data_context["transaction_benchmarks"].empty
    assert not public_data_context["invoice_benchmarks"].empty
    assert "Wholesale Trade" in set(public_data_context["listed_company_benchmarks"]["industry"])

    facility_text = " ".join(feature_df["facility_type"].astype(str).tolist()).lower()
    purpose_text = " ".join(feature_df["purpose"].astype(str).tolist()).lower()
    for keyword in FORBIDDEN_KEYWORDS:
        assert keyword not in facility_text
        assert keyword not in purpose_text
