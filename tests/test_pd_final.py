from pathlib import Path
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pd_final import build_pd_final_layer, validate_pd_final_layer


def test_build_pd_final_layer_applies_overlays_and_calibration():
    scored_df = pd.DataFrame(
        [
            {
                "facility_id": "CFL-00001",
                "borrower_id": 1,
                "borrower_name": "Borrower One",
                "product_family": "Revolving Liquidity",
                "facility_type": "Business Overdraft",
                "industry": "Retail Trade",
                "score": 710.0,
                "score_band": "A",
                "predicted_pd": 0.02,
                "statement_conduct_flag": "Green",
                "days_beyond_terms_avg": 12,
                "card_days_past_due_12m": 0,
                "eligibility_status": "Eligible",
                "commercial_defaults_24m": 0,
                "tax_arrears_flag": "No",
                "writs_judgements_flag": "No",
                "external_administration_flag": "No",
                "director_adverse_history_flag": "No",
                "unpaid_direct_debits_12m": 0,
                "nsf_count_12m": 0,
                "aged_receivables_90dpd_pct": 0.00,
                "hard_fail_count": 0,
                "soft_fail_count": 0,
            },
            {
                "facility_id": "CFL-00002",
                "borrower_id": 2,
                "borrower_name": "Borrower Two",
                "product_family": "Term Cash Flow",
                "facility_type": "Unsecured Term Loan",
                "industry": "Construction - Trade Services",
                "score": 560.0,
                "score_band": "D",
                "predicted_pd": 0.04,
                "statement_conduct_flag": "Red",
                "days_beyond_terms_avg": 35,
                "card_days_past_due_12m": 0,
                "eligibility_status": "Conditional",
                "commercial_defaults_24m": 0,
                "tax_arrears_flag": "Yes",
                "writs_judgements_flag": "No",
                "external_administration_flag": "No",
                "director_adverse_history_flag": "No",
                "unpaid_direct_debits_12m": 2,
                "nsf_count_12m": 1,
                "aged_receivables_90dpd_pct": 0.00,
                "hard_fail_count": 0,
                "soft_fail_count": 1,
            },
            {
                "facility_id": "CFL-00003",
                "borrower_id": 3,
                "borrower_name": "Borrower Three",
                "product_family": "Receivables Finance",
                "facility_type": "Invoice Finance",
                "industry": "Wholesale Trade",
                "score": 480.0,
                "score_band": "E",
                "predicted_pd": 0.80,
                "statement_conduct_flag": "Red",
                "days_beyond_terms_avg": 20,
                "card_days_past_due_12m": 0,
                "eligibility_status": "Outside Criteria",
                "commercial_defaults_24m": 1,
                "tax_arrears_flag": "Yes",
                "writs_judgements_flag": "Yes",
                "external_administration_flag": "Yes",
                "director_adverse_history_flag": "Yes",
                "unpaid_direct_debits_12m": 4,
                "nsf_count_12m": 3,
                "aged_receivables_90dpd_pct": 0.20,
                "hard_fail_count": 1,
                "soft_fail_count": 1,
            },
        ]
    )

    pd_final_df = build_pd_final_layer(scored_df, as_of_date="2026-04-08")

    safe_row = pd_final_df.loc[pd_final_df["facility_id"] == "CFL-00001"].iloc[0]
    assert safe_row["watchlist_flag"] == 0
    assert safe_row["arrears_days"] == 12
    assert safe_row["policy_override_flag"] == 0
    assert safe_row["pd_12m_adjusted"] == pytest.approx(0.02)
    assert safe_row["pd_final"] == pytest.approx(0.022)
    assert safe_row["risk_grade"] == "RG1"

    watchlist_row = pd_final_df.loc[pd_final_df["facility_id"] == "CFL-00002"].iloc[0]
    assert watchlist_row["watchlist_flag"] == 1
    assert watchlist_row["pd_overlay_watchlist"] == pytest.approx(0.25)
    assert watchlist_row["pd_overlay_arrears"] == pytest.approx(0.20)
    assert watchlist_row["pd_overlay_policy"] == pytest.approx(0.15)
    assert watchlist_row["pd_12m_adjusted"] == pytest.approx(0.064)
    assert watchlist_row["pd_final"] == pytest.approx(0.0704)
    assert watchlist_row["risk_grade"] == "RG4"

    stressed_row = pd_final_df.loc[pd_final_df["facility_id"] == "CFL-00003"].iloc[0]
    assert stressed_row["watchlist_flag"] == 1
    assert stressed_row["arrears_days"] == 90
    assert stressed_row["policy_override_flag"] == 1
    assert stressed_row["pd_overlay_arrears"] == pytest.approx(0.40)
    assert stressed_row["pd_12m_calibrated"] == pytest.approx(1.584)
    assert stressed_row["pd_final"] == pytest.approx(1.0)
    assert stressed_row["as_of_date"] == "2026-04-08"


def test_validate_pd_final_layer_checks_monotonicity():
    pd_final_df = pd.DataFrame(
        [
            {"score_band": "A", "risk_grade": "RG1", "watchlist_flag": 0, "pd_final": 0.01},
            {"score_band": "B", "risk_grade": "RG2", "watchlist_flag": 0, "pd_final": 0.03},
            {"score_band": "C", "risk_grade": "RG3", "watchlist_flag": 1, "pd_final": 0.06},
            {"score_band": "D", "risk_grade": "RG4", "watchlist_flag": 1, "pd_final": 0.12},
            {"score_band": "E", "risk_grade": "RG5", "watchlist_flag": 1, "pd_final": 0.30},
        ]
    )

    checks = validate_pd_final_layer(pd_final_df)

    assert checks["passed"].all()
