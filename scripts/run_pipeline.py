from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_full_pipeline


if __name__ == "__main__":
    result = run_full_pipeline()
    cashflow_feature_df = result["cashflow_result"]["feature_dataset"]
    cashflow_metadata = result["cashflow_result"]["scorecard_result"]["metadata"].iloc[0]
    cashflow_provenance_df = result["cashflow_result"]["public_data_context"]["public_data_provenance"]
    cashflow_pd_final_df = result["cashflow_result"]["pd_final_result"]["facility_pd_final"]
    property_feature_df = result["property_result"]["facility_dataset"]
    property_metadata = result["property_result"]["scorecard_result"]["metadata"].iloc[0]
    property_reference_df = result["property_reference_context"]["reference_provenance"]
    property_pd_final_df = result["property_result"]["pd_final_result"]["facility_pd_final"]
    combined_pd_final_df = result["combined_pd_final"]

    print("Cash flow stream")
    print(f"Borrowers scored: {len(cashflow_feature_df)}")
    print(f"Observed default rate: {cashflow_feature_df['default_12m'].mean():.2%}")
    print(f"Average final PD: {cashflow_pd_final_df['pd_final'].mean():.2%}")
    print(f"Product families: {cashflow_feature_df['product_family'].nunique()}")
    print(f"Eligibility pass rate: {(cashflow_feature_df['eligibility_status'] == 'Eligible').mean():.2%}")
    print(f"Train AUC: {cashflow_metadata['train_auc']:.3f}")
    print(f"Test AUC: {cashflow_metadata['test_auc']:.3f}")
    for row in cashflow_provenance_df.itertuples(index=False):
        print(f"Public data {row.dataset_name}: {row.status} ({int(row.records_loaded)} records)")

    print("\nProperty-backed stream")
    print(f"Facilities scored: {len(property_feature_df)}")
    print(f"Observed default rate: {property_feature_df['default_12m'].mean():.2%}")
    print(f"Average final PD: {property_pd_final_df['pd_final'].mean():.2%}")
    print(f"Product types: {property_feature_df['product_type'].nunique()}")
    print(f"Average current LVR: {property_feature_df['current_lvr'].mean():.2%}")
    print(f"Train AUC: {property_metadata['train_auc']:.3f}")
    print(f"Test AUC: {property_metadata['test_auc']:.3f}")
    for row in property_reference_df.itertuples(index=False):
        print(f"Property reference {row.dataset_name}: {row.status} ({int(row.records_loaded)} records)")

    print("\nCombined EL-facing PD feed")
    print(f"Combined facilities: {len(combined_pd_final_df)}")
    print(f"Average combined final PD: {combined_pd_final_df['pd_final'].mean():.2%}")
