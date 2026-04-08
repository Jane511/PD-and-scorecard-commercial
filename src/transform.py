import pandas as pd


def apply_bins(series: pd.Series, spec: dict) -> pd.Series:
    if spec["type"] == "numeric":
        return pd.cut(series, bins=spec["edges"], include_lowest=True).astype(str).fillna("MISSING")
    return series.astype(str).fillna("MISSING")


def transform_to_woe(df: pd.DataFrame, binning_store: dict, default_woe: float = 0.0) -> pd.DataFrame:
    output = pd.DataFrame(index=df.index)
    for feature, meta in binning_store.items():
        bins = apply_bins(df[feature], meta["spec"])
        output[feature] = bins.map(meta["mapping"]).fillna(default_woe)
    return output
