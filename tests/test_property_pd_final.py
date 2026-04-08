from pathlib import Path
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.pd_final_property import (
    build_property_pd_downturn_scenarios,
    build_property_pd_final_layer,
    validate_property_pd_final_layer,
)


def test_build_property_pd_final_layer_applies_expected_overlays():
    scored_df = pd.DataFrame(
        [
            {
                "facility_id": "PBL-00001",
                "borrower_id": 1,
                "borrower_name": "Borrower One",
                "product_type": "Property Investment Loan",
                "property_type": "Warehouses",
                "property_segment": "Warehouses",
                "region": "Australia",
                "score": 705.0,
                "score_band": "A",
                "predicted_pd": 0.02,
                "current_lvr": 0.58,
                "completion_stage": "Stabilised",
                "exit_risk_band": "Low",
                "watchlist_flag": 0,
                "arrears_days": 0,
            },
            {
                "facility_id": "PBL-00002",
                "borrower_id": 2,
                "borrower_name": "Borrower Two",
                "product_type": "Development Facility",
                "property_type": "Offices",
                "property_segment": "Offices",
                "region": "Australia",
                "score": 540.0,
                "score_band": "D",
                "predicted_pd": 0.05,
                "current_lvr": 0.74,
                "completion_stage": "Mid stage",
                "exit_risk_band": "Elevated",
                "watchlist_flag": 1,
                "arrears_days": 30,
            },
            {
                "facility_id": "PBL-00003",
                "borrower_id": 3,
                "borrower_name": "Borrower Three",
                "product_type": "Bridging Loan",
                "property_type": "Offices",
                "property_segment": "Offices",
                "region": "Australia",
                "score": 470.0,
                "score_band": "E",
                "predicted_pd": 0.70,
                "current_lvr": 0.82,
                "completion_stage": "Early stage",
                "exit_risk_band": "High",
                "watchlist_flag": 1,
                "arrears_days": 60,
            },
        ]
    )

    final_df = build_property_pd_final_layer(scored_df)

    low_risk_row = final_df.loc[final_df["facility_id"] == "PBL-00001"].iloc[0]
    assert low_risk_row["pd_overlay_lvr"] == pytest.approx(0.0)
    assert low_risk_row["pd_overlay_completion_stage"] == pytest.approx(0.0)
    assert low_risk_row["pd_overlay_exit_risk"] == pytest.approx(0.0)
    assert low_risk_row["pd_overlay_watchlist"] == pytest.approx(0.0)
    assert low_risk_row["pd_final"] == pytest.approx(0.021)

    development_row = final_df.loc[final_df["facility_id"] == "PBL-00002"].iloc[0]
    assert development_row["pd_overlay_lvr"] == pytest.approx(0.12)
    assert development_row["pd_overlay_completion_stage"] == pytest.approx(0.12)
    assert development_row["pd_overlay_exit_risk"] == pytest.approx(0.12)
    assert development_row["pd_overlay_watchlist"] == pytest.approx(0.20)
    assert development_row["pd_12m_adjusted"] == pytest.approx(0.078)
    assert development_row["pd_final"] == pytest.approx(0.0819)

    stressed_row = final_df.loc[final_df["facility_id"] == "PBL-00003"].iloc[0]
    assert stressed_row["pd_overlay_lvr"] == pytest.approx(0.25)
    assert stressed_row["pd_overlay_completion_stage"] == pytest.approx(0.20)
    assert stressed_row["pd_overlay_exit_risk"] == pytest.approx(0.20)
    assert stressed_row["pd_overlay_watchlist"] == pytest.approx(0.20)
    assert stressed_row["pd_12m_calibrated"] == pytest.approx(1.35975)
    assert stressed_row["pd_final"] == pytest.approx(1.0)


def test_property_pd_downturn_scenarios_and_validation():
    final_df = pd.DataFrame(
        [
            {
                "facility_id": "PBL-00001",
                "borrower_id": 1,
                "product_type": "Property Investment Loan",
                "property_segment": "Warehouses",
                "region": "Australia",
                "score_band": "A",
                "risk_grade": "RG1",
                "current_lvr": 0.55,
                "watchlist_flag": 0,
                "pd_final": 0.02,
            },
            {
                "facility_id": "PBL-00002",
                "borrower_id": 2,
                "product_type": "Development Facility",
                "property_segment": "Offices",
                "region": "Australia",
                "score_band": "C",
                "risk_grade": "RG3",
                "current_lvr": 0.72,
                "watchlist_flag": 1,
                "pd_final": 0.08,
            },
            {
                "facility_id": "PBL-00003",
                "borrower_id": 3,
                "product_type": "Bridging Loan",
                "property_segment": "Offices",
                "region": "Australia",
                "score_band": "E",
                "risk_grade": "RG5",
                "current_lvr": 0.82,
                "watchlist_flag": 1,
                "pd_final": 0.20,
            },
        ]
    )
    overlay_df = pd.DataFrame(
        [
            {"scenario": "base", "pd_multiplier": 1.0, "lgd_multiplier": 1.0, "ccf_multiplier": 1.0, "property_value_haircut": 0.0, "notes": "Base", "as_of_date": "2026-03-16"},
            {"scenario": "severe", "pd_multiplier": 2.0, "lgd_multiplier": 1.3, "ccf_multiplier": 1.2, "property_value_haircut": 0.2, "notes": "Severe", "as_of_date": "2026-03-16"},
        ]
    )

    scenarios = build_property_pd_downturn_scenarios(final_df, overlay_df)
    checks = validate_property_pd_final_layer(final_df)

    severe_row = scenarios.loc[
        (scenarios["facility_id"] == "PBL-00003") & (scenarios["scenario"] == "severe")
    ].iloc[0]
    assert severe_row["pd_final_downturn"] == pytest.approx(0.40)
    assert severe_row["property_value_haircut"] == pytest.approx(0.2)

    assert checks["passed"].all()
