from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import PROPERTY_REFERENCE_SOURCE_DIRS


FALLBACK_AS_OF_DATE = "2026-03-16"

REGION_RISK_COLUMNS = [
    "region",
    "state",
    "region_group",
    "property_segment",
    "building_approvals_trend",
    "building_activity_trend",
    "housing_finance_trend",
    "region_risk_score",
    "region_risk_band",
    "as_of_date",
    "source_note",
]

PROPERTY_CYCLE_COLUMNS = [
    "region",
    "property_segment",
    "approvals_change_pct",
    "commencements_signal",
    "completions_signal",
    "cycle_stage",
    "market_softness_score",
    "market_softness_band",
    "as_of_date",
    "source_note",
]

ARREARS_ENVIRONMENT_COLUMNS = [
    "as_of_date",
    "arrears_environment_level",
    "arrears_trend",
    "macro_housing_risk_band",
    "macro_housing_risk_score",
    "notes",
    "source_note",
]

DOWNTURN_OVERLAY_COLUMNS = [
    "scenario",
    "pd_multiplier",
    "lgd_multiplier",
    "ccf_multiplier",
    "property_value_haircut",
    "notes",
    "as_of_date",
]


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _discover_property_reference_source_dirs() -> list[Path]:
    candidates: list[Path] = []
    for path in PROPERTY_REFERENCE_SOURCE_DIRS:
        if path not in candidates:
            candidates.append(path)
    for pattern in (
        "9.Industry Risk Analysis*",
        "industry-risk-reference-layer*",
    ):
        for repo_dir in sorted(Path(__file__).resolve().parents[1].parent.glob(pattern)):
            if repo_dir not in candidates:
                candidates.append(repo_dir)
    return candidates


def _fallback_region_risk_table() -> pd.DataFrame:
    rows = [
        ("Commercial", "Offices", "Sharp contraction", 4.03, "High"),
        ("Social infrastructure", "Education buildings", "Softening", 3.38, "Elevated"),
        ("Commercial", "Retail and wholesale trade buildings", "Improving", 2.95, "Medium"),
        ("Accommodation", "Short term accommodation buildings", "Strong expansion", 2.55, "Medium"),
        ("Social infrastructure", "Aged care facilities", "Improving", 2.73, "Medium"),
        ("Social infrastructure", "Health buildings", "Strong expansion", 1.82, "Low"),
        ("Industrial", "Industrial Buildings - Total", "Improving", 2.45, "Medium"),
        ("Industrial", "Warehouses", "Improving", 2.35, "Medium"),
    ]
    return pd.DataFrame(
        [
            {
                "region": "Australia",
                "state": "Australia",
                "region_group": region_group,
                "property_segment": property_segment,
                "building_approvals_trend": approvals_trend,
                "building_activity_trend": "Fallback approvals proxy",
                "housing_finance_trend": "Fallback cash-rate proxy",
                "region_risk_score": score,
                "region_risk_band": band,
                "as_of_date": FALLBACK_AS_OF_DATE,
                "source_note": "Fallback property reference settings used because no sibling region-risk output was available.",
            }
            for region_group, property_segment, approvals_trend, score, band in rows
        ]
    )[REGION_RISK_COLUMNS]


def _fallback_property_cycle_table() -> pd.DataFrame:
    rows = [
        ("Offices", -35.72, "downturn", 4.30, "High"),
        ("Education buildings", -21.37, "slowing", 3.25, "Elevated"),
        ("Retail and wholesale trade buildings", 68.47, "neutral", 3.15, "Elevated"),
        ("Short term accommodation buildings", 113.70, "growth", 2.85, "Medium"),
        ("Aged care facilities", 219.88, "neutral", 2.70, "Medium"),
        ("Health buildings", 355.03, "growth", 1.65, "Low"),
        ("Industrial Buildings - Total", 55.53, "neutral", 2.40, "Medium"),
        ("Warehouses", 69.32, "neutral", 2.20, "Medium"),
    ]
    return pd.DataFrame(
        [
            {
                "region": "Australia",
                "property_segment": property_segment,
                "approvals_change_pct": approvals_change_pct,
                "commencements_signal": "Fallback approvals proxy",
                "completions_signal": "Fallback approvals proxy",
                "cycle_stage": cycle_stage,
                "market_softness_score": softness_score,
                "market_softness_band": softness_band,
                "as_of_date": "2026-02-01",
                "source_note": "Fallback property-cycle settings used because no sibling property-cycle output was available.",
            }
            for property_segment, approvals_change_pct, cycle_stage, softness_score, softness_band in rows
        ]
    )[PROPERTY_CYCLE_COLUMNS]


def _fallback_arrears_environment() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "as_of_date": FALLBACK_AS_OF_DATE,
                "arrears_environment_level": "Low",
                "arrears_trend": "Improving",
                "macro_housing_risk_band": "Low",
                "macro_housing_risk_score": 1.75,
                "notes": "Fallback macro arrears setting aligned to the March 2026 reference baseline.",
                "source_note": "Fallback arrears environment used because no sibling arrears-environment output was available.",
            }
        ]
    )[ARREARS_ENVIRONMENT_COLUMNS]


def _fallback_downturn_overlays() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "scenario": "base",
                "pd_multiplier": 1.00,
                "lgd_multiplier": 1.00,
                "ccf_multiplier": 1.00,
                "property_value_haircut": 0.00,
                "notes": "Current environment baseline.",
                "as_of_date": FALLBACK_AS_OF_DATE,
            },
            {
                "scenario": "mild",
                "pd_multiplier": 1.20,
                "lgd_multiplier": 1.10,
                "ccf_multiplier": 1.05,
                "property_value_haircut": 0.05,
                "notes": "Illustrative mild downturn overlay.",
                "as_of_date": FALLBACK_AS_OF_DATE,
            },
            {
                "scenario": "moderate",
                "pd_multiplier": 1.50,
                "lgd_multiplier": 1.20,
                "ccf_multiplier": 1.10,
                "property_value_haircut": 0.10,
                "notes": "Illustrative moderate downturn overlay.",
                "as_of_date": FALLBACK_AS_OF_DATE,
            },
            {
                "scenario": "severe",
                "pd_multiplier": 2.00,
                "lgd_multiplier": 1.30,
                "ccf_multiplier": 1.20,
                "property_value_haircut": 0.20,
                "notes": "Illustrative severe downturn overlay.",
                "as_of_date": FALLBACK_AS_OF_DATE,
            },
        ]
    )[DOWNTURN_OVERLAY_COLUMNS]


def _load_reference_table(relative_path: str, columns: list[str]) -> tuple[pd.DataFrame, str] | None:
    for repo_dir in _discover_property_reference_source_dirs():
        file_path = repo_dir / relative_path
        if not file_path.exists():
            continue
        try:
            df = pd.read_csv(file_path)
        except Exception:
            continue
        for column in columns:
            if column not in df.columns:
                df[column] = pd.NA
        return df[columns].copy(), str(file_path)
    return None


def load_region_risk_reference() -> tuple[pd.DataFrame, pd.DataFrame]:
    loaded = _load_reference_table("data/output/region_risk/region_risk_table.csv", REGION_RISK_COLUMNS)
    if loaded is not None:
        df, source_path = loaded
        provenance = pd.DataFrame(
            [
                {
                    "dataset_name": "property_region_risk",
                    "status": "loaded",
                    "records_loaded": int(len(df)),
                    "source_path": source_path,
                    "notes": "Loaded property segment region-risk reference bands from the sibling industry-risk repository.",
                }
            ]
        )
        return df, provenance

    df = _fallback_region_risk_table()
    provenance = pd.DataFrame(
        [
            {
                "dataset_name": "property_region_risk",
                "status": "fallback",
                "records_loaded": int(len(df)),
                "source_path": "",
                "notes": "Sibling industry-risk property reference output not found. Using in-repo fallback region bands.",
            }
        ]
    )
    return df, provenance


def load_property_cycle_reference() -> tuple[pd.DataFrame, pd.DataFrame]:
    loaded = _load_reference_table("data/output/property_cycle/property_cycle_table.csv", PROPERTY_CYCLE_COLUMNS)
    if loaded is not None:
        df, source_path = loaded
        provenance = pd.DataFrame(
            [
                {
                    "dataset_name": "property_cycle",
                    "status": "loaded",
                    "records_loaded": int(len(df)),
                    "source_path": source_path,
                    "notes": "Loaded property-cycle and market-softness reference bands from the sibling industry-risk repository.",
                }
            ]
        )
        return df, provenance

    df = _fallback_property_cycle_table()
    provenance = pd.DataFrame(
        [
            {
                "dataset_name": "property_cycle",
                "status": "fallback",
                "records_loaded": int(len(df)),
                "source_path": "",
                "notes": "Sibling industry-risk property-cycle output not found. Using in-repo fallback cycle bands.",
            }
        ]
    )
    return df, provenance


def load_arrears_environment_reference() -> tuple[pd.DataFrame, pd.DataFrame]:
    loaded = _load_reference_table(
        "data/output/arrears_environment/base_arrears_environment.csv",
        ARREARS_ENVIRONMENT_COLUMNS,
    )
    if loaded is not None:
        df, source_path = loaded
        provenance = pd.DataFrame(
            [
                {
                    "dataset_name": "property_arrears_environment",
                    "status": "loaded",
                    "records_loaded": int(len(df)),
                    "source_path": source_path,
                    "notes": "Loaded macro property arrears environment from the sibling industry-risk repository.",
                }
            ]
        )
        return df, provenance

    df = _fallback_arrears_environment()
    provenance = pd.DataFrame(
        [
            {
                "dataset_name": "property_arrears_environment",
                "status": "fallback",
                "records_loaded": int(len(df)),
                "source_path": "",
                "notes": "Sibling industry-risk arrears-environment output not found. Using in-repo fallback macro setting.",
            }
        ]
    )
    return df, provenance


def load_property_downturn_overlays() -> tuple[pd.DataFrame, pd.DataFrame]:
    loaded = _load_reference_table(
        "data/output/downturn_overlays/property_downturn_overlays.csv",
        DOWNTURN_OVERLAY_COLUMNS,
    )
    if loaded is not None:
        df, source_path = loaded
        provenance = pd.DataFrame(
            [
                {
                    "dataset_name": "property_downturn_overlays",
                    "status": "loaded",
                    "records_loaded": int(len(df)),
                    "source_path": source_path,
                    "notes": "Loaded simple property downturn overlays from the sibling industry-risk repository.",
                }
            ]
        )
        return df, provenance

    df = _fallback_downturn_overlays()
    provenance = pd.DataFrame(
        [
            {
                "dataset_name": "property_downturn_overlays",
                "status": "fallback",
                "records_loaded": int(len(df)),
                "source_path": "",
                "notes": "Sibling industry-risk downturn overlays not found. Using in-repo fallback scenario multipliers.",
            }
        ]
    )
    return df, provenance


def build_property_reference_context(use_public_data: bool = True) -> dict:
    if use_public_data:
        region_risk_df, region_provenance = load_region_risk_reference()
        property_cycle_df, cycle_provenance = load_property_cycle_reference()
        arrears_environment_df, arrears_provenance = load_arrears_environment_reference()
        downturn_df, downturn_provenance = load_property_downturn_overlays()
    else:
        region_risk_df, region_provenance = _fallback_region_risk_table(), _empty([])
        property_cycle_df, cycle_provenance = _fallback_property_cycle_table(), _empty([])
        arrears_environment_df, arrears_provenance = _fallback_arrears_environment(), _empty([])
        downturn_df, downturn_provenance = _fallback_downturn_overlays(), _empty([])

    segment_reference = region_risk_df.merge(
        property_cycle_df[
            [
                "region",
                "property_segment",
                "approvals_change_pct",
                "commencements_signal",
                "completions_signal",
                "cycle_stage",
                "market_softness_score",
                "market_softness_band",
                "as_of_date",
                "source_note",
            ]
        ].rename(
            columns={
                "as_of_date": "cycle_as_of_date",
                "source_note": "cycle_source_note",
            }
        ),
        on=["region", "property_segment"],
        how="left",
    )
    segment_reference["cycle_as_of_date"] = segment_reference["cycle_as_of_date"].fillna(segment_reference["as_of_date"])
    segment_reference["cycle_source_note"] = segment_reference["cycle_source_note"].fillna(segment_reference["source_note"])
    segment_reference = segment_reference.sort_values(["region_group", "property_segment"]).reset_index(drop=True)

    provenance = pd.concat(
        [
            region_provenance,
            cycle_provenance,
            arrears_provenance,
            downturn_provenance,
        ],
        ignore_index=True,
    )

    return {
        "region_risk": region_risk_df,
        "property_cycle": property_cycle_df,
        "arrears_environment": arrears_environment_df,
        "downturn_overlays": downturn_df,
        "segment_reference": segment_reference,
        "reference_provenance": provenance,
    }


def property_reference_lookup(reference_df: pd.DataFrame, property_segment: str, region: str = "Australia") -> dict:
    if reference_df.empty:
        return {}
    match = reference_df[
        (reference_df["property_segment"] == property_segment)
        & (reference_df["region"] == region)
    ]
    if not match.empty:
        return match.iloc[0].to_dict()
    segment_match = reference_df[reference_df["property_segment"] == property_segment]
    if not segment_match.empty:
        return segment_match.iloc[0].to_dict()
    return reference_df.iloc[0].to_dict()
