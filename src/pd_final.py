"""
Final PD layer builder for EL-ready facility-level outputs.

This module adds a simplified final PD layer on top of the detailed cash-flow
scorecard workflow. It converts raw model PD into one clean `pd_final` field
per facility, applies a small set of explainable overlays, adds a calibration
step, and writes EL-ready outputs for downstream use.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

try:
    from .config import (
        OUTPUT_DIR,
        PD_FINAL_CALIBRATION_SCALAR,
        PD_FINAL_DEFAULT_HORIZON_MONTHS,
        PD_FINAL_MODEL_NAME,
        PD_FINAL_MODEL_VERSION,
        PD_FINAL_OUTPUT_DIR,
        SCORECARD_OUTPUT_DIR,
    )
except ImportError:  # pragma: no cover - enables direct script execution
    from config import (
        OUTPUT_DIR,
        PD_FINAL_CALIBRATION_SCALAR,
        PD_FINAL_DEFAULT_HORIZON_MONTHS,
        PD_FINAL_MODEL_NAME,
        PD_FINAL_MODEL_VERSION,
        PD_FINAL_OUTPUT_DIR,
        SCORECARD_OUTPUT_DIR,
    )

DEFAULT_OUTPUT_DIR = PD_FINAL_OUTPUT_DIR

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
    "product_family",
    "facility_type",
    "industry",
    "score",
    "score_band",
    "predicted_pd",
]

OUTPUT_COLUMNS = [
    "facility_id",
    "borrower_id",
    "borrower_name",
    "product_type",
    "facility_type",
    "industry",
    "score",
    "score_band",
    "risk_grade",
    "watchlist_flag",
    "arrears_days",
    "policy_override_flag",
    "pd_12m_raw",
    "pd_overlay_watchlist",
    "pd_overlay_arrears",
    "pd_overlay_policy",
    "pd_12m_adjusted",
    "pd_12m_calibrated",
    "pd_final",
    "default_horizon_months",
    "pd_model_name",
    "pd_model_version",
    "as_of_date",
]

OPTIONAL_OUTPUT_COLUMNS = [
    "funding_type",
    "security_type",
    "requested_limit",
    "recommended_limit",
    "eligibility_status",
    "decision",
    "review_frequency",
    "approval_authority",
    "pricing_margin_pct",
    "all_in_rate_pct",
    "data_split",
]


def _as_bool_flag(value) -> bool:
    """Interpret mixed numeric/text flags into a boolean."""
    if pd.isna(value):
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _as_float(value, default: float = 0.0) -> float:
    """Coerce mixed numeric input into a float with a safe default."""
    if pd.isna(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def assign_watchlist_overlay(flag) -> float:
    """Return the watchlist uplift factor."""
    return 0.25 if _as_bool_flag(flag) else 0.0


def assign_arrears_overlay(days) -> float:
    """Return the arrears uplift factor."""
    arrears_days = _as_float(days)
    if arrears_days >= 60:
        return 0.40
    if arrears_days >= 30:
        return 0.20
    return 0.0


def assign_policy_overlay(flag) -> float:
    """Return the policy exception uplift factor."""
    return 0.15 if _as_bool_flag(flag) else 0.0


def _derive_watchlist_flag(row: pd.Series) -> int:
    """
    Build a simple watchlist proxy from adverse bureau, conduct, and policy data.
    """
    conduct_flag = str(row.get("statement_conduct_flag", "")).strip().lower()
    eligibility_status = str(row.get("eligibility_status", "Eligible")).strip().lower()
    watchlist = any(
        [
            _as_bool_flag(row.get("tax_arrears_flag")),
            _as_bool_flag(row.get("writs_judgements_flag")),
            _as_bool_flag(row.get("external_administration_flag")),
            _as_float(row.get("commercial_defaults_24m")) > 0,
            conduct_flag == "red",
            eligibility_status == "outside criteria",
        ]
    )
    return int(watchlist)


def _derive_arrears_days(row: pd.Series) -> int:
    """
    Create a facility arrears proxy using the strongest available conduct signal.

    The repo does not store contractual facility arrears directly, so this final
    layer converts the available statement, card, receivables, and bureau
    delinquency indicators into one explainable `arrears_days` field.
    """
    arrears_days = max(
        _as_float(row.get("days_beyond_terms_avg")),
        _as_float(row.get("card_days_past_due_12m")),
    )

    if _as_float(row.get("unpaid_direct_debits_12m")) >= 2 or _as_float(row.get("nsf_count_12m")) >= 2:
        arrears_days = max(arrears_days, 30.0)
    if _as_float(row.get("aged_receivables_90dpd_pct")) >= 0.10:
        arrears_days = max(arrears_days, 60.0)
    if _as_bool_flag(row.get("external_administration_flag")) or _as_float(row.get("commercial_defaults_24m")) > 0:
        arrears_days = max(arrears_days, 90.0)

    return int(round(arrears_days))


def _derive_policy_override_flag(row: pd.Series) -> int:
    """Create a simple policy exception flag for final-layer uplifting."""
    eligibility_status = str(row.get("eligibility_status", "Eligible")).strip()
    override = any(
        [
            eligibility_status != "Eligible",
            _as_float(row.get("hard_fail_count")) > 0,
            _as_float(row.get("soft_fail_count")) > 0,
            _as_bool_flag(row.get("director_adverse_history_flag")),
            _as_bool_flag(row.get("guarantee_call_event_flag")),
        ]
    )
    return int(override)


def calculate_pd_adjusted(df: pd.DataFrame) -> pd.DataFrame:
    """Combine raw PD and overlay factors into one adjusted PD."""
    out = df.copy()
    out["pd_12m_adjusted"] = out["pd_12m_raw"] * (
        1.0
        + out["pd_overlay_watchlist"]
        + out["pd_overlay_arrears"]
        + out["pd_overlay_policy"]
    )
    return out


def calibrate_pd(
    df: pd.DataFrame,
    calibration_scalar: float = PD_FINAL_CALIBRATION_SCALAR,
) -> pd.DataFrame:
    """Apply the final PD calibration scalar."""
    out = df.copy()
    out["pd_12m_calibrated"] = out["pd_12m_adjusted"] * calibration_scalar
    return out


def _resolve_as_of_date(df: pd.DataFrame, as_of_date: str | None) -> str:
    """Resolve the final-layer as-of date."""
    if as_of_date is not None:
        return pd.Timestamp(as_of_date).date().isoformat()
    if "as_of_date" in df.columns:
        values = [str(value) for value in df["as_of_date"].dropna().unique().tolist()]
        if len(values) == 1:
            return values[0]
    return date.today().isoformat()


def build_pd_final_layer(
    df: pd.DataFrame,
    calibration_scalar: float = PD_FINAL_CALIBRATION_SCALAR,
    default_horizon_months: int = PD_FINAL_DEFAULT_HORIZON_MONTHS,
    pd_model_name: str = PD_FINAL_MODEL_NAME,
    pd_model_version: str = PD_FINAL_MODEL_VERSION,
    as_of_date: str | None = None,
) -> pd.DataFrame:
    """
    Build the simplified facility-level PD final layer from scored repo output.
    """
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns for PD final layer: {missing}")

    out = df.copy()
    out["borrower_name"] = out.get("borrower_name", pd.Series([pd.NA] * len(out), index=out.index))
    out["product_type"] = out.get("product_type", out["product_family"])
    out["pd_12m_raw"] = pd.to_numeric(out["predicted_pd"], errors="coerce").fillna(0.0).clip(0, 1)
    out["watchlist_flag"] = out.apply(_derive_watchlist_flag, axis=1).astype(int)
    out["arrears_days"] = out.apply(_derive_arrears_days, axis=1).astype(int)
    out["policy_override_flag"] = out.apply(_derive_policy_override_flag, axis=1).astype(int)
    out["pd_overlay_watchlist"] = out["watchlist_flag"].apply(assign_watchlist_overlay)
    out["pd_overlay_arrears"] = out["arrears_days"].apply(assign_arrears_overlay)
    out["pd_overlay_policy"] = out["policy_override_flag"].apply(assign_policy_overlay)
    out = calculate_pd_adjusted(out)
    out = calibrate_pd(out, calibration_scalar=calibration_scalar)
    out["pd_final"] = out["pd_12m_calibrated"].clip(0, 1)
    out["risk_grade"] = out["score_band"].map(SCORE_BAND_TO_RISK_GRADE).fillna("RG5")
    out["default_horizon_months"] = int(default_horizon_months)
    out["pd_model_name"] = pd_model_name
    out["pd_model_version"] = pd_model_version
    out["as_of_date"] = _resolve_as_of_date(out, as_of_date=as_of_date)

    ordered_columns = OUTPUT_COLUMNS + [column for column in OPTIONAL_OUTPUT_COLUMNS if column in out.columns]
    return out[ordered_columns]


def summarise_final_pd_by_product(df: pd.DataFrame) -> pd.DataFrame:
    """Create a compact product-level final-PD summary for handoff and validation."""

    def _limit_weighted_pd(group: pd.DataFrame) -> float:
        if "recommended_limit" in group.columns:
            exposure = pd.to_numeric(group["recommended_limit"], errors="coerce")
        elif "requested_limit" in group.columns:
            exposure = pd.to_numeric(group["requested_limit"], errors="coerce")
        else:
            exposure = pd.Series([pd.NA] * len(group), index=group.index, dtype="float64")

        valid = exposure.notna() & (exposure > 0)
        if not valid.any():
            return group["pd_final"].mean()
        return float((group.loc[valid, "pd_final"] * exposure.loc[valid]).sum() / exposure.loc[valid].sum())

    summary = (
        df.groupby(["product_type", "facility_type"], observed=True)
        .apply(
            lambda group: pd.Series(
                {
                    "facility_count": len(group),
                    "average_pd_12m_raw": group["pd_12m_raw"].mean(),
                    "average_pd_12m_final": group["pd_final"].mean(),
                    "watchlist_share": group["watchlist_flag"].mean(),
                    "policy_override_share": group["policy_override_flag"].mean(),
                    "limit_weighted_pd_final": _limit_weighted_pd(group),
                }
            ),
            include_groups=False,
        )
        .reset_index()
        .sort_values(["product_type", "facility_type"])
        .reset_index(drop=True)
    )
    return summary


def validate_pd_final_layer(df: pd.DataFrame) -> pd.DataFrame:
    """Run final-layer sanity and monotonicity checks."""
    band_means = df.groupby("score_band", observed=True)["pd_final"].mean().reindex(SCORE_BAND_ORDER).dropna()
    grade_means = df.groupby("risk_grade", observed=True)["pd_final"].mean().reindex(RISK_GRADE_ORDER).dropna()
    watchlist_means = df.groupby("watchlist_flag", observed=True)["pd_final"].mean()
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
    ]
    return pd.DataFrame(checks)


def load_repo_pd_inputs() -> pd.DataFrame:
    """
    Load the scored repo portfolio and merge the policy overlay context.

    If persisted files do not yet exist, the full pipeline is run first.
    """
    train_path = SCORECARD_OUTPUT_DIR / "05_train_scored.csv"
    test_path = SCORECARD_OUTPUT_DIR / "06_test_scored.csv"
    policy_path = OUTPUT_DIR / "policy_overlay.csv"

    if train_path.exists() and test_path.exists():
        scored_df = pd.concat(
            [
                pd.read_csv(train_path),
                pd.read_csv(test_path),
            ],
            ignore_index=True,
        )
        policy_df = pd.read_csv(policy_path) if policy_path.exists() else pd.DataFrame()
    else:
        try:
            from .pipeline import run_full_pipeline
        except ImportError:  # pragma: no cover - enables direct script execution
            from pipeline import run_full_pipeline

        result = run_full_pipeline(persist=True)
        scored_df = result["scorecard_result"]["portfolio_scored"].copy()
        policy_df = result["policy_overlay"].copy()

    if not policy_df.empty and "facility_id" in scored_df.columns and "facility_id" in policy_df.columns:
        keep_columns = [
            "facility_id",
            "recommended_limit",
            "decision",
            "review_frequency",
            "approval_authority",
            "pricing_margin_pct",
            "all_in_rate_pct",
        ]
        available_columns = [column for column in keep_columns if column in policy_df.columns]
        if available_columns:
            scored_df = scored_df.merge(policy_df[available_columns], on="facility_id", how="left")

    return scored_df


def build_and_save_repo_pd_final(
    scored_df: pd.DataFrame | None = None,
    output_dir: str | Path | None = None,
    calibration_scalar: float = PD_FINAL_CALIBRATION_SCALAR,
    default_horizon_months: int = PD_FINAL_DEFAULT_HORIZON_MONTHS,
    pd_model_name: str = PD_FINAL_MODEL_NAME,
    pd_model_version: str = PD_FINAL_MODEL_VERSION,
    as_of_date: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build the repo PD final layer and save the CSV outputs."""
    final_layer_inputs = scored_df.copy() if scored_df is not None else load_repo_pd_inputs()
    facility_pd_final = build_pd_final_layer(
        final_layer_inputs,
        calibration_scalar=calibration_scalar,
        default_horizon_months=default_horizon_months,
        pd_model_name=pd_model_name,
        pd_model_version=pd_model_version,
        as_of_date=as_of_date,
    )
    summary = summarise_final_pd_by_product(facility_pd_final)
    checks = validate_pd_final_layer(facility_pd_final)

    target_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    facility_pd_final.to_csv(target_dir / "facility_pd_final.csv", index=False)
    summary.to_csv(target_dir / "pd_final_summary_by_product.csv", index=False)
    checks.to_csv(target_dir / "pd_final_validation_checks.csv", index=False)

    return facility_pd_final, summary, checks


def main() -> None:
    """CLI entry point for building the final PD layer outputs."""
    facility_pd_final, summary, checks = build_and_save_repo_pd_final()

    print(f"Saved {len(facility_pd_final)} rows to {DEFAULT_OUTPUT_DIR / 'facility_pd_final.csv'}")
    print("\nAverage final PD by product:")
    print(summary.to_string(index=False))
    print("\nValidation checks:")
    print(checks.to_string(index=False))


if __name__ == "__main__":
    main()
