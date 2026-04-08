import numpy as np
import pandas as pd


def safe_qcut(series: pd.Series, max_bins: int = 5):
    clean = series.dropna()
    if clean.nunique() <= 1:
        return None
    if clean.nunique() <= max_bins:
        try:
            return pd.cut(clean, bins=clean.nunique(), duplicates="drop")
        except ValueError:
            return None
    for q in range(max_bins, 1, -1):
        try:
            categories = pd.qcut(clean, q=q, duplicates="drop")
            if len(categories.cat.categories) >= 2:
                return categories
        except ValueError:
            continue
    return None


def fit_woe(train_series, target, feature_name, max_bins: int = 5, smoothing: float = 0.5):
    df = pd.DataFrame({"x": train_series, "target": target}).copy()

    if pd.api.types.is_numeric_dtype(df["x"]):
        binned = safe_qcut(df["x"], max_bins=max_bins)
        if binned is None:
            df["bin"] = df["x"].astype(str).fillna("MISSING")
            spec = {"type": "categorical"}
        else:
            df.loc[binned.index, "bin"] = binned.astype(str)
            df["bin"] = df["bin"].fillna("MISSING")
            intervals = pd.IntervalIndex(binned.cat.categories)
            edges = [intervals[0].left] + [interval.right for interval in intervals]
            spec = {"type": "numeric", "edges": edges}
    else:
        df["bin"] = df["x"].astype(str).fillna("MISSING")
        spec = {"type": "categorical"}

    grouped = df.groupby("bin", dropna=False)["target"].agg(total="count", bad="sum").reset_index()
    grouped["good"] = grouped["total"] - grouped["bad"]

    total_good = grouped["good"].sum()
    total_bad = grouped["bad"].sum()

    grouped["dist_good"] = (grouped["good"] + smoothing) / (total_good + smoothing * len(grouped))
    grouped["dist_bad"] = (grouped["bad"] + smoothing) / (total_bad + smoothing * len(grouped))
    grouped["woe"] = np.log(grouped["dist_good"] / grouped["dist_bad"])
    grouped["iv_component"] = (grouped["dist_good"] - grouped["dist_bad"]) * grouped["woe"]
    grouped["iv"] = grouped["iv_component"].sum()
    grouped["feature"] = feature_name

    mapping = dict(zip(grouped["bin"], grouped["woe"]))
    return grouped, spec, mapping
