from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from .config import (
    PROPERTY_PD_FINAL_CALIBRATION_SCALAR,
    PROPERTY_PD_FINAL_DEFAULT_HORIZON_MONTHS,
    PROPERTY_PD_FINAL_MODEL_NAME,
    PROPERTY_PD_FINAL_MODEL_VERSION,
)


SCORE_BAND_TO_RISK_GRADE = {
    "A": "RG1",
    "B": "RG2",
    "C": "RG3",
    "D": "RG4",
    "E": "RG5",
}
SCORE_BAND_ORDER = ["A", "B", "C", "D", "E"]
RISK_GRADE_ORDER = ["RG1", "RG2", "RG3", "RG4", "RG5"]

REQUIRED_COLUMNS = [
    "facility_id",
    "borrower_id",
    "product_type",
    "property_segment",
    "region",
    "score",
    "score_band",
    "predicted_pd",
    "current_lvr",
    "completion_stage",
    "exit_risk_band",
]

OUTPUT_COLUMNS = [
    "facility_id",
    "borrower_id",
    "borrower_name",
    "product_type",
    "property_type",
    "property_segment",
    "region",
    "score",
    "score_band",
    "risk_grade",
    "watchlist_flag",
    "pd_12m_raw",
    "pd_overlay_lvr",
    "pd_overlay_completion_stage",
    "pd_overlay_exit_risk",
    "pd_overlay_watchlist",
    "pd_12m_adjusted",
    "pd_12m_calibrated",
    "pd_final",
    "default_horizon_months",
    "pd_model_name",
    "pd_model_version",
    "as_of_date",
]

OPTIONAL_OUTPUT_COLUMNS = [
    "state",
    "region_group",
    "security_type",
    "loan_term_months",
    "loan_amount",
    "current_balance",
    "property_value",
    "total_project_cost",
    "current_lvr",
    "ltc",
    "dscr",
    "interest_cover",
    "presales_ratio",
    "completion_stage",
    "fund_to_complete_flag",
    "exit_risk_band",
    "guarantor_support_flag",
    "region_risk_score",
    "region_risk_band",
    "market_softness_score",
    "market_softness_band",
    "cycle_stage",
    "macro_housing_risk_score",
    "macro_housing_risk_band",
    "arrears_environment_level",
    "arrears_trend",
    "arrears_days",
    "policy_override_flag",
    "data_split",
]


def _as_bool_flag(value) -> bool:
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _as_float(value, default: float = 0.0) -> float:
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def assign_lvr_overlay(current_lvr) -> float:
    lvr = _as_float(current_lvr)
    if lvr >= 0.80:
        return 0.25
    if lvr >= 0.70:
        return 0.12
    if lvr >= 0.60:
        return 0.04
    return 0.0


def assign_completion_stage_overlay(completion_stage) -> float:
    stage = str(completion_stage).strip().lower()
    if stage == "early stage":
        return 0.20
    if stage == "mid stage":
        return 0.12
    if stage == "practical completion":
        return 0.05
    if stage == "completed / sale pending":
        return 0.03
    return 0.0


def assign_exit_risk_overlay(exit_risk_band) -> float:
    band = str(exit_risk_band).strip().lower()
    if band == "high":
        return 0.20
    if band == "elevated":
        return 0.12
    if band == "medium":
        return 0.05
    return 0.0


def assign_watchlist_overlay(flag) -> float:
    return 0.20 if _as_bool_flag(flag) else 0.0


def _derive_watchlist_flag(row: pd.Series) -> int:
    return int(
        _as_bool_flag(row.get("watchlist_flag"))
        or _as_float(row.get("arrears_days")) >= 30
        or _as_bool_flag(row.get("fund_to_complete_flag"))
        or str(row.get("exit_risk_band", "")).strip().lower() == "high"
    )


def calculate_pd_adjusted(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["pd_12m_adjusted"] = out["pd_12m_raw"] * (
        1.0
        + out["pd_overlay_lvr"]
        + out["pd_overlay_completion_stage"]
        + out["pd_overlay_exit_risk"]
        + out["pd_overlay_watchlist"]
    )
    return out


def calibrate_pd(
    df: pd.DataFrame,
    calibration_scalar: float = PROPERTY_PD_FINAL_CALIBRATION_SCALAR,
) -> pd.DataFrame:
    out = df.copy()
    out["pd_12m_calibrated"] = out["pd_12m_adjusted"] * calibration_scalar
    return out


def build_property_pd_final_layer(
    df: pd.DataFrame,
    calibration_scalar: float = PROPERTY_PD_FINAL_CALIBRATION_SCALAR,
    default_horizon_months: int = PROPERTY_PD_FINAL_DEFAULT_HORIZON_MONTHS,
    pd_model_name: str = PROPERTY_PD_FINAL_MODEL_NAME,
    pd_model_version: str = PROPERTY_PD_FINAL_MODEL_VERSION,
) -> pd.DataFrame:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for property PD final layer: {missing}")

    out = df.copy()
    out["borrower_name"] = out.get("borrower_name", pd.Series([pd.NA] * len(out), index=out.index))
    out["property_type"] = out.get("property_type", out["property_segment"])
    out["pd_12m_raw"] = pd.to_numeric(out["predicted_pd"], errors="coerce").fillna(0.0).clip(0, 1)
    out["watchlist_flag"] = out.apply(_derive_watchlist_flag, axis=1).astype(int)
    out["pd_overlay_lvr"] = out["current_lvr"].apply(assign_lvr_overlay)
    out["pd_overlay_completion_stage"] = out["completion_stage"].apply(assign_completion_stage_overlay)
    out["pd_overlay_exit_risk"] = out["exit_risk_band"].apply(assign_exit_risk_overlay)
    out["pd_overlay_watchlist"] = out["watchlist_flag"].apply(assign_watchlist_overlay)
    out = calculate_pd_adjusted(out)
    out = calibrate_pd(out, calibration_scalar=calibration_scalar)
    out["pd_final"] = out["pd_12m_calibrated"].clip(0, 1)
    out["risk_grade"] = out["score_band"].map(SCORE_BAND_TO_RISK_GRADE).fillna("RG5")
    out["default_horizon_months"] = int(default_horizon_months)
    out["pd_model_name"] = pd_model_name
    out["pd_model_version"] = pd_model_version
    if "as_of_date" not in out.columns:
        out["as_of_date"] = date.today().isoformat()
    else:
        out["as_of_date"] = out["as_of_date"].fillna(date.today().isoformat())

    ordered_columns = OUTPUT_COLUMNS + [column for column in OPTIONAL_OUTPUT_COLUMNS if column in out.columns]
    return out[ordered_columns]


def summarise_property_final_pd(df: pd.DataFrame) -> pd.DataFrame:
    def _weighted_final_pd(group: pd.DataFrame) -> float:
        exposure = pd.to_numeric(group["current_balance"], errors="coerce")
        valid = exposure.notna() & (exposure > 0)
        if not valid.any():
            return group["pd_final"].mean()
        return float((group.loc[valid, "pd_final"] * exposure.loc[valid]).sum() / exposure.loc[valid].sum())

    summary = (
        df.groupby(["product_type", "property_segment"], observed=True)
        .apply(
            lambda group: pd.Series(
                {
                    "facility_count": len(group),
                    "average_pd_12m_raw": group["pd_12m_raw"].mean(),
                    "average_pd_12m_final": group["pd_final"].mean(),
                    "watchlist_share": group["watchlist_flag"].mean(),
                    "weighted_pd_final": _weighted_final_pd(group),
                }
            ),
            include_groups=False,
        )
        .reset_index()
        .sort_values(["product_type", "property_segment"])
        .reset_index(drop=True)
    )
    return summary


def validate_property_pd_final_layer(df: pd.DataFrame) -> pd.DataFrame:
    band_means = df.groupby("score_band", observed=True)["pd_final"].mean().reindex(SCORE_BAND_ORDER).dropna()
    grade_means = df.groupby("risk_grade", observed=True)["pd_final"].mean().reindex(RISK_GRADE_ORDER).dropna()
    watchlist_means = df.groupby("watchlist_flag", observed=True)["pd_final"].mean()

    high_lvr_mean = df.loc[df["current_lvr"] >= 0.70, "pd_final"].mean()
    low_lvr_mean = df.loc[df["current_lvr"] < 0.60, "pd_final"].mean()
    watchlist_pd = watchlist_means.get(1)
    non_watchlist_pd = watchlist_means.get(0)

    checks = [
        {
            "check_name": "no_negative_pd",
            "passed": bool((df["pd_final"] >= 0).all()),
            "detail": f"min_pd_final={df['pd_final'].min():.4f}",
        },
        {
            "check_name": "no_pd_above_100pct",
            "passed": bool((df["pd_final"] <= 1).all()),
            "detail": f"max_pd_final={df['pd_final'].max():.4f}",
        },
        {
            "check_name": "score_band_monotonic",
            "passed": bool(band_means.is_monotonic_increasing),
            "detail": "; ".join(f"{band}={mean:.4f}" for band, mean in band_means.items()),
        },
        {
            "check_name": "risk_grade_monotonic",
            "passed": bool(grade_means.is_monotonic_increasing),
            "detail": "; ".join(f"{grade}={mean:.4f}" for grade, mean in grade_means.items()),
        },
        {
            "check_name": "watchlist_above_non_watchlist",
            "passed": bool(
                pd.notna(watchlist_pd)
                and pd.notna(non_watchlist_pd)
                and watchlist_pd >= non_watchlist_pd
            ),
            "detail": (
                f"watchlist={watchlist_pd:.4f}; non_watchlist={non_watchlist_pd:.4f}"
                if pd.notna(watchlist_pd) and pd.notna(non_watchlist_pd)
                else "insufficient watchlist split"
            ),
        },
        {
            "check_name": "high_lvr_above_low_lvr",
            "passed": bool(
                pd.notna(high_lvr_mean)
                and pd.notna(low_lvr_mean)
                and high_lvr_mean >= low_lvr_mean
            ),
            "detail": (
                f"high_lvr={high_lvr_mean:.4f}; low_lvr={low_lvr_mean:.4f}"
                if pd.notna(high_lvr_mean) and pd.notna(low_lvr_mean)
                else "insufficient lvr split"
            ),
        },
    ]
    return pd.DataFrame(checks)


def build_property_pd_downturn_scenarios(
    property_pd_final_df: pd.DataFrame,
    downturn_overlay_df: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "facility_id",
        "borrower_id",
        "product_type",
        "property_segment",
        "region",
        "score_band",
        "risk_grade",
        "base_pd_final",
        "scenario",
        "pd_multiplier",
        "pd_final_downturn",
        "lgd_multiplier",
        "ccf_multiplier",
        "property_value_haircut",
        "scenario_notes",
        "as_of_date",
    ]
    if property_pd_final_df.empty or downturn_overlay_df.empty:
        return pd.DataFrame(columns=columns)

    scenario_frames = []
    for scenario_row in downturn_overlay_df.itertuples(index=False):
        scenario_df = property_pd_final_df[
            [
                "facility_id",
                "borrower_id",
                "product_type",
                "property_segment",
                "region",
                "score_band",
                "risk_grade",
                "pd_final",
            ]
        ].copy()
        scenario_df["base_pd_final"] = scenario_df["pd_final"]
        scenario_df["scenario"] = scenario_row.scenario
        scenario_df["pd_multiplier"] = scenario_row.pd_multiplier
        scenario_df["pd_final_downturn"] = (scenario_df["base_pd_final"] * scenario_row.pd_multiplier).clip(0, 1)
        scenario_df["lgd_multiplier"] = scenario_row.lgd_multiplier
        scenario_df["ccf_multiplier"] = scenario_row.ccf_multiplier
        scenario_df["property_value_haircut"] = scenario_row.property_value_haircut
        scenario_df["scenario_notes"] = scenario_row.notes
        scenario_df["as_of_date"] = scenario_row.as_of_date
        scenario_frames.append(scenario_df[columns])

    return pd.concat(scenario_frames, ignore_index=True)


def save_property_pd_final_outputs(
    property_pd_final_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    validation_df: pd.DataFrame,
    scenario_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    property_pd_final_df.to_csv(output_dir / "property_pd_final.csv", index=False)
    summary_df.to_csv(output_dir / "property_pd_final_summary_by_product.csv", index=False)
    validation_df.to_csv(output_dir / "property_pd_final_validation_checks.csv", index=False)
    scenario_df.to_csv(output_dir / "property_pd_downturn_scenarios.csv", index=False)
