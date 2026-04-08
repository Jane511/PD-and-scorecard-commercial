from __future__ import annotations

import numpy as np
import pandas as pd

from .config import PROPERTY_TARGET_DEFAULT_RATE
from .property_reference import property_reference_lookup


PROPERTY_PRODUCT_DEFINITIONS = (
    {
        "product_type": "Property Investment Loan",
        "loan_purpose_options": (
            "Term investment refinance",
            "Acquisition of stabilised income-producing asset",
            "Portfolio hold against rental cash flow",
        ),
        "security_type": "Registered first mortgage",
        "loan_term_range": (24, 84),
        "property_value_range": (2_500_000, 24_000_000),
        "current_lvr_range": (0.45, 0.76),
        "ltc_range": (0.40, 0.72),
        "dscr_range": (1.20, 2.60),
        "interest_cover_range": (1.60, 3.80),
    },
    {
        "product_type": "Bridging Loan",
        "loan_purpose_options": (
            "Bridge to refinance or sale",
            "Short-dated residual stock bridge",
            "Settlement timing bridge",
        ),
        "security_type": "Registered first mortgage / limited recourse support",
        "loan_term_range": (6, 24),
        "property_value_range": (2_000_000, 18_000_000),
        "current_lvr_range": (0.52, 0.82),
        "ltc_range": (0.50, 0.82),
        "dscr_range": (0.85, 1.80),
        "interest_cover_range": (1.10, 2.70),
    },
    {
        "product_type": "Development Facility",
        "loan_purpose_options": (
            "Construction finance",
            "Build-to-hold development",
            "Build-to-sell staged development",
        ),
        "security_type": "Registered first mortgage / project security package",
        "loan_term_range": (12, 36),
        "property_value_range": (4_000_000, 40_000_000),
        "current_lvr_range": (0.35, 0.78),
        "ltc_range": (0.48, 0.80),
        "dscr_range": (0.75, 1.65),
        "interest_cover_range": (0.95, 2.20),
    },
)

PROPERTY_NAME_PREFIXES = (
    "Cedar",
    "Granite",
    "Harbour",
    "Laneway",
    "Mariner",
    "Oak",
    "Quay",
    "Summit",
    "Terrace",
    "Vista",
)

PROPERTY_NAME_SUFFIXES = (
    "Capital",
    "Developments",
    "Holdings",
    "Projects",
    "Property Group",
    "Projects Pty Ltd",
    "Investments",
    "Partners",
)

COMPLETION_STAGE_WEIGHTS = {
    "Stabilised": 0.00,
    "Completed / sale pending": 0.03,
    "Practical completion": 0.05,
    "Mid stage": 0.12,
    "Early stage": 0.20,
}

EXIT_RISK_WEIGHTS = {
    "Low": 0.00,
    "Medium": 0.06,
    "Elevated": 0.12,
    "High": 0.20,
}


def _make_borrower_name(rng: np.random.Generator) -> str:
    return f"{rng.choice(PROPERTY_NAME_PREFIXES)} {rng.choice(PROPERTY_NAME_SUFFIXES)}"


def _product_probability(product_type: str) -> float:
    return {
        "Property Investment Loan": 0.44,
        "Bridging Loan": 0.20,
        "Development Facility": 0.36,
    }[product_type]


def _arrears_environment_factor(environment_level: str) -> float:
    return {
        "Low": 0.15,
        "Moderate": 0.40,
        "Elevated": 0.75,
        "High": 1.05,
    }.get(str(environment_level), 0.40)


def _macro_risk_score(arrears_row: dict) -> float:
    try:
        return float(arrears_row.get("macro_housing_risk_score", 2.0))
    except (TypeError, ValueError):
        return 2.0


def _choose_completion_stage(product_type: str, rng: np.random.Generator) -> str:
    if product_type == "Property Investment Loan":
        return "Stabilised"
    if product_type == "Bridging Loan":
        return rng.choice(["Completed / sale pending", "Practical completion"], p=[0.60, 0.40])
    return rng.choice(["Early stage", "Mid stage", "Practical completion"], p=[0.28, 0.47, 0.25])


def _derive_exit_risk_band(
    product_type: str,
    current_lvr: float,
    dscr: float,
    presales_ratio: float,
    market_softness_score: float,
    completion_stage: str,
    guarantor_support_flag: int,
) -> str:
    exit_signal = (
        max(current_lvr - 0.65, 0.0) * 4.0
        + max(1.20 - dscr, 0.0) * 0.9
        + max(0.65 - presales_ratio, 0.0) * 1.6
        + max(market_softness_score - 2.5, 0.0) * 0.8
        + COMPLETION_STAGE_WEIGHTS.get(completion_stage, 0.08) * 3.0
        + (0.30 if product_type == "Bridging Loan" else 0.0)
        + (0.45 if product_type == "Development Facility" else 0.0)
        - 0.25 * guarantor_support_flag
    )
    if exit_signal >= 2.10:
        return "High"
    if exit_signal >= 1.30:
        return "Elevated"
    if exit_signal >= 0.70:
        return "Medium"
    return "Low"


def _generate_arrears_days(
    rng: np.random.Generator,
    current_lvr: float,
    market_softness_score: float,
    fund_to_complete_flag: int,
    exit_risk_band: str,
    macro_housing_risk_score: float,
    environment_level: str,
    product_type: str,
) -> int:
    arrears_signal = (
        _arrears_environment_factor(environment_level)
        + max(current_lvr - 0.68, 0.0) * 3.0
        + max(market_softness_score - 2.6, 0.0) * 0.9
        + 0.65 * fund_to_complete_flag
        + (0.45 if exit_risk_band == "High" else 0.22 if exit_risk_band == "Elevated" else 0.0)
        + max(macro_housing_risk_score - 2.0, 0.0) * 0.7
        + (0.10 if product_type == "Bridging Loan" else 0.18 if product_type == "Development Facility" else 0.0)
        + rng.normal(0.0, 0.20)
    )
    if arrears_signal < 0.55:
        return int(rng.choice([0, 5, 15], p=[0.72, 0.18, 0.10]))
    if arrears_signal < 1.05:
        return int(rng.choice([0, 15, 30], p=[0.35, 0.40, 0.25]))
    if arrears_signal < 1.70:
        return int(rng.choice([15, 30, 60], p=[0.20, 0.45, 0.35]))
    return int(rng.choice([30, 60, 90], p=[0.20, 0.45, 0.35]))


def generate_property_facility_dataset(
    n_facilities: int,
    seed: int,
    property_reference_context: dict,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 707)
    reference_df = property_reference_context["segment_reference"].copy()
    if reference_df.empty:
        raise ValueError("Property reference context must include at least one segment reference row.")

    reference_rows = reference_df.to_dict(orient="records")
    product_types = [product["product_type"] for product in PROPERTY_PRODUCT_DEFINITIONS]
    product_probabilities = [_product_probability(product_type) for product_type in product_types]
    product_lookup = {product["product_type"]: product for product in PROPERTY_PRODUCT_DEFINITIONS}

    arrears_environment_df = property_reference_context["arrears_environment"]
    if arrears_environment_df.empty:
        arrears_row = {
            "as_of_date": "2026-03-16",
            "arrears_environment_level": "Moderate",
            "arrears_trend": "Stable",
            "macro_housing_risk_band": "Medium",
            "macro_housing_risk_score": 2.20,
        }
    else:
        arrears_row = arrears_environment_df.iloc[0].to_dict()
    macro_housing_risk_score = _macro_risk_score(arrears_row)

    rows = []
    for facility_number in range(1, n_facilities + 1):
        borrower_id = 300_000 + facility_number
        facility_id = f"PBL-{facility_number:05d}"
        borrower_name = _make_borrower_name(rng)

        product_type = rng.choice(product_types, p=product_probabilities)
        product = product_lookup[product_type]
        reference = reference_rows[int(rng.integers(0, len(reference_rows)))]

        property_segment = str(reference["property_segment"])
        region = str(reference.get("region", "Australia"))
        state = str(reference.get("state", "Australia"))
        region_group = str(reference.get("region_group", "Commercial"))
        region_risk_score = float(reference.get("region_risk_score", 2.8))
        market_softness_score = float(reference.get("market_softness_score", 2.7))
        region_risk_band = str(reference.get("region_risk_band", "Medium"))
        market_softness_band = str(reference.get("market_softness_band", "Medium"))
        cycle_stage = str(reference.get("cycle_stage", "neutral"))

        property_value = rng.uniform(*product["property_value_range"]) * (
            1.0
            + max(region_risk_score - 2.5, 0.0) * 0.08
            + max(market_softness_score - 2.5, 0.0) * 0.04
        )
        current_lvr = float(
            np.clip(
                rng.normal(
                    np.mean(product["current_lvr_range"])
                    + max(region_risk_score - 2.6, 0.0) * 0.03
                    + max(market_softness_score - 2.7, 0.0) * 0.02,
                    0.08,
                ),
                product["current_lvr_range"][0],
                product["current_lvr_range"][1],
            )
        )
        ltc = float(
            np.clip(
                rng.normal(
                    np.mean(product["ltc_range"])
                    + max(market_softness_score - 2.7, 0.0) * 0.03,
                    0.07,
                ),
                product["ltc_range"][0],
                product["ltc_range"][1],
            )
        )
        dscr = float(
            np.clip(
                rng.normal(
                    np.mean(product["dscr_range"])
                    - max(market_softness_score - 2.7, 0.0) * 0.14
                    - max(region_risk_score - 2.8, 0.0) * 0.10,
                    0.22,
                ),
                product["dscr_range"][0],
                product["dscr_range"][1],
            )
        )
        interest_cover = float(
            np.clip(
                rng.normal(
                    np.mean(product["interest_cover_range"])
                    - max(region_risk_score - 2.8, 0.0) * 0.12
                    - max(macro_housing_risk_score - 2.0, 0.0) * 0.10,
                    0.30,
                ),
                product["interest_cover_range"][0],
                product["interest_cover_range"][1],
            )
        )

        completion_stage = _choose_completion_stage(product_type, rng)
        if product_type == "Property Investment Loan":
            presales_ratio = 1.00
        elif product_type == "Bridging Loan":
            presales_ratio = float(
                np.clip(
                    rng.normal(0.78 - max(market_softness_score - 2.7, 0.0) * 0.06, 0.15),
                    0.25,
                    1.00,
                )
            )
        else:
            stage_anchor = {
                "Early stage": 0.40,
                "Mid stage": 0.62,
                "Practical completion": 0.84,
            }[completion_stage]
            presales_ratio = float(
                np.clip(
                    rng.normal(stage_anchor - max(market_softness_score - 2.7, 0.0) * 0.05, 0.16),
                    0.00,
                    1.00,
                )
            )

        loan_purpose = rng.choice(product["loan_purpose_options"])
        loan_term_months = int(rng.integers(product["loan_term_range"][0], product["loan_term_range"][1] + 1))
        loan_amount = float(property_value * current_lvr * rng.uniform(1.01, 1.08))
        current_balance = float(property_value * current_lvr)
        total_project_cost = loan_amount / max(ltc, 0.30)

        base_guarantor_probability = 0.68 if product_type == "Property Investment Loan" else 0.56 if product_type == "Bridging Loan" else 0.52
        guarantor_support_flag = int(
            rng.random()
            < np.clip(
                base_guarantor_probability
                - max(region_risk_score - 2.8, 0.0) * 0.06
                - max(market_softness_score - 2.8, 0.0) * 0.05,
                0.15,
                0.90,
            )
        )
        fund_to_complete_flag = int(
            product_type == "Development Facility"
            and completion_stage != "Practical completion"
            and (
                ltc >= 0.72
                or presales_ratio <= 0.50
                or rng.random() < 0.22
            )
        )
        if product_type == "Bridging Loan" and rng.random() < 0.10 and current_lvr >= 0.72:
            fund_to_complete_flag = 1

        exit_risk_band = _derive_exit_risk_band(
            product_type=product_type,
            current_lvr=current_lvr,
            dscr=dscr,
            presales_ratio=presales_ratio,
            market_softness_score=market_softness_score,
            completion_stage=completion_stage,
            guarantor_support_flag=guarantor_support_flag,
        )
        arrears_days = _generate_arrears_days(
            rng=rng,
            current_lvr=current_lvr,
            market_softness_score=market_softness_score,
            fund_to_complete_flag=fund_to_complete_flag,
            exit_risk_band=exit_risk_band,
            macro_housing_risk_score=macro_housing_risk_score,
            environment_level=str(arrears_row.get("arrears_environment_level", "Moderate")),
            product_type=product_type,
        )
        watchlist_flag = int(
            arrears_days >= 30
            or fund_to_complete_flag == 1
            or exit_risk_band == "High"
            or (product_type == "Development Facility" and completion_stage == "Early stage" and presales_ratio < 0.35)
        )
        policy_override_flag = int(
            current_lvr >= 0.80
            or ltc >= 0.75
            or presales_ratio < 0.45
            or arrears_days >= 60
            or exit_risk_band == "High"
        )

        rows.append(
            {
                "facility_id": facility_id,
                "borrower_id": borrower_id,
                "borrower_name": borrower_name,
                "product_type": product_type,
                "loan_purpose": loan_purpose,
                "security_type": product["security_type"],
                "property_type": property_segment,
                "property_segment": property_segment,
                "region": region,
                "state": state,
                "region_group": region_group,
                "loan_term_months": loan_term_months,
                "loan_amount": round(loan_amount, 0),
                "current_balance": round(current_balance, 0),
                "property_value": round(property_value, 0),
                "total_project_cost": round(total_project_cost, 0),
                "current_lvr": round(current_lvr, 4),
                "ltc": round(ltc, 4),
                "dscr": round(dscr, 4),
                "interest_cover": round(interest_cover, 4),
                "presales_ratio": round(presales_ratio, 4),
                "completion_stage": completion_stage,
                "fund_to_complete_flag": fund_to_complete_flag,
                "exit_risk_band": exit_risk_band,
                "guarantor_support_flag": guarantor_support_flag,
                "region_risk_score": round(region_risk_score, 2),
                "region_risk_band": region_risk_band,
                "market_softness_score": round(market_softness_score, 2),
                "market_softness_band": market_softness_band,
                "cycle_stage": cycle_stage,
                "macro_housing_risk_score": round(macro_housing_risk_score, 2),
                "macro_housing_risk_band": str(arrears_row.get("macro_housing_risk_band", "Medium")),
                "arrears_environment_level": str(arrears_row.get("arrears_environment_level", "Moderate")),
                "arrears_trend": str(arrears_row.get("arrears_trend", "Stable")),
                "arrears_days": arrears_days,
                "watchlist_flag": watchlist_flag,
                "policy_override_flag": policy_override_flag,
                "reference_region_note": str(reference.get("source_note", "")),
                "reference_cycle_note": str(reference.get("cycle_source_note", "")),
                "as_of_date": str(arrears_row.get("as_of_date", reference.get("cycle_as_of_date", "2026-03-16"))),
            }
        )

    property_df = pd.DataFrame(rows)

    completion_weights = property_df["completion_stage"].map(COMPLETION_STAGE_WEIGHTS).fillna(0.08)
    exit_weights = property_df["exit_risk_band"].map(EXIT_RISK_WEIGHTS).fillna(0.08)
    rng_defaults = np.random.default_rng(seed + 808)
    base_logit = (
        1.10 * np.clip(property_df["current_lvr"] - 0.60, 0.0, None) * 4.0
        + 0.90 * np.clip(property_df["ltc"] - 0.65, 0.0, None) * 4.0
        + 0.75 * np.clip(1.25 - property_df["dscr"], 0.0, None)
        + 0.55 * np.clip(2.00 - property_df["interest_cover"], 0.0, None)
        + 0.85 * np.clip(0.70 - property_df["presales_ratio"], 0.0, None)
        + 1.40 * completion_weights
        + 1.75 * exit_weights
        + 0.45 * np.clip(property_df["region_risk_score"] - 2.4, 0.0, None)
        + 0.55 * np.clip(property_df["market_softness_score"] - 2.4, 0.0, None)
        + 0.30 * np.clip(property_df["macro_housing_risk_score"] - 2.0, 0.0, None)
        + 0.55 * property_df["fund_to_complete_flag"]
        + 0.55 * property_df["watchlist_flag"]
        + 0.004 * property_df["arrears_days"]
        + 0.25 * property_df["policy_override_flag"]
        + 0.22 * (property_df["product_type"] == "Bridging Loan").astype(int)
        + 0.38 * (property_df["product_type"] == "Development Facility").astype(int)
        - 0.22 * property_df["guarantor_support_flag"]
        + rng_defaults.normal(0.0, 0.32, size=len(property_df))
    )

    lower_bound, upper_bound = -10.0, 10.0
    for _ in range(60):
        intercept = (lower_bound + upper_bound) / 2.0
        mean_probability = float((1.0 / (1.0 + np.exp(-(base_logit + intercept)))).mean())
        if mean_probability > PROPERTY_TARGET_DEFAULT_RATE:
            upper_bound = intercept
        else:
            lower_bound = intercept
    intercept = (lower_bound + upper_bound) / 2.0
    property_df["default_probability_true"] = 1.0 / (1.0 + np.exp(-(base_logit + intercept)))
    property_df["default_12m"] = rng_defaults.binomial(1, property_df["default_probability_true"]).astype(int)

    reference_df = property_reference_context["segment_reference"]
    if not reference_df.empty:
        property_df["reference_join_check"] = property_df["property_segment"].apply(
            lambda property_segment: bool(property_reference_lookup(reference_df, property_segment))
        )
    else:
        property_df["reference_join_check"] = False

    return property_df
