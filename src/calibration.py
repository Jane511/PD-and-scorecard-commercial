import numpy as np
import pandas as pd


def calibration_table(df: pd.DataFrame, score_col: str, target_col: str = "default_12m", bins: int = 10) -> pd.DataFrame:
    temp = df[[score_col, target_col]].dropna().copy()
    temp["bucket"] = pd.qcut(temp[score_col], q=bins, duplicates="drop")
    out = (
        temp.groupby("bucket", observed=False)[target_col]
        .agg(observed_default_rate="mean", observations="count")
        .reset_index()
    )
    bucket_midpoint = temp.groupby("bucket", observed=False)[score_col].mean().reset_index(drop=True)
    out["predicted_pd"] = bucket_midpoint
    return out


def calibrate_pd(raw_pd, observed_dr: float, target_dr: float):
    factor = target_dr / observed_dr if observed_dr > 0 else 1.0
    return np.clip(raw_pd * factor, 1e-6, 1.0), factor
