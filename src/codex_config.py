from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[1]
REPO_NAME='PD-and-Scorecard-Cashflow-Lending'
PIPELINE_KIND='pd'
EXPECTED_OUTPUTS=['pd_model_output.csv', 'borrower_grade_summary.csv', 'policy_decisions.csv', 'score_band_output.csv']
