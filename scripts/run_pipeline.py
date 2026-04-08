from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pipeline import run_full_pipeline


if __name__ == "__main__":
    result = run_full_pipeline()
    feature_df = result["feature_dataset"]
    metadata = result["scorecard_result"]["metadata"].iloc[0]
    provenance_df = result["public_data_context"]["public_data_provenance"]
    print(f"Borrowers scored: {len(feature_df)}")
    print(f"Observed default rate: {feature_df['default_12m'].mean():.2%}")
    print(f"Product families: {feature_df['product_family'].nunique()}")
    print(f"Eligibility pass rate: {(feature_df['eligibility_status'] == 'Eligible').mean():.2%}")
    print(f"Train AUC: {metadata['train_auc']:.3f}")
    print(f"Test AUC: {metadata['test_auc']:.3f}")
    for row in provenance_df.itertuples(index=False):
        print(f"Public data {row.dataset_name}: {row.status} ({int(row.records_loaded)} records)")
