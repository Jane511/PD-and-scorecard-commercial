from __future__ import annotations

import pandas as pd


COMBINED_OUTPUT_COLUMNS = [
    "facility_id",
    "borrower_id",
    "borrower_name",
    "product_type",
    "pd_model_stream",
    "industry",
    "property_segment",
    "score",
    "score_band",
    "risk_grade",
    "pd_final",
    "default_horizon_months",
    "pd_model_name",
    "pd_model_version",
    "as_of_date",
]


def _prepare_cashflow_pd_final(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["product_type"] = out.get("product_type", out.get("facility_type"))
    out["pd_model_stream"] = "cashflow"
    out["property_segment"] = pd.NA
    for column in COMBINED_OUTPUT_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    return out[COMBINED_OUTPUT_COLUMNS]


def _prepare_property_pd_final(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["pd_model_stream"] = "property"
    out["industry"] = pd.NA
    for column in COMBINED_OUTPUT_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    return out[COMBINED_OUTPUT_COLUMNS]


def build_combined_pd_final(
    cashflow_pd_final_df: pd.DataFrame,
    property_pd_final_df: pd.DataFrame,
) -> pd.DataFrame:
    frames = []
    if cashflow_pd_final_df is not None and not cashflow_pd_final_df.empty:
        frames.append(_prepare_cashflow_pd_final(cashflow_pd_final_df))
    if property_pd_final_df is not None and not property_pd_final_df.empty:
        frames.append(_prepare_property_pd_final(property_pd_final_df))
    if not frames:
        return pd.DataFrame(columns=COMBINED_OUTPUT_COLUMNS)
    return pd.concat(frames, ignore_index=True)
