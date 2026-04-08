import numpy as np
import pandas as pd

from .config import INDUSTRY_SETTINGS, TARGET_DEFAULT_RATE


def _safe_divide(numerator, denominator, default=np.nan):
    denominator = np.asarray(denominator)
    numerator = np.asarray(numerator)
    return np.where(np.abs(denominator) > 0, numerator / denominator, default)


def calculate_financial_ratios(financials_df: pd.DataFrame) -> pd.DataFrame:
    df = financials_df.copy()

    df["ebitda_margin"] = _safe_divide(df["ebitda"], df["revenue"])
    df["ebit_margin"] = _safe_divide(df["ebit"], df["revenue"])
    df["ocf_margin"] = _safe_divide(df["operating_cash_flow"], df["revenue"])
    df["debt_to_ebitda"] = _safe_divide(df["total_debt"], df["ebitda"])
    df["debt_to_cashflow"] = _safe_divide(df["total_debt"], df["operating_cash_flow"])
    df["current_ratio"] = _safe_divide(df["current_assets"], df["current_liabilities"])
    df["quick_ratio"] = _safe_divide(df["cash"] + df["debtors"], df["current_liabilities"])
    df["working_capital"] = df["current_assets"] - df["current_liabilities"]
    df["icr"] = _safe_divide(df["ebit"], df["interest_expense"])
    df["dscr"] = _safe_divide(
        df["operating_cash_flow"],
        df["interest_expense"] + df["scheduled_principal"],
    )
    df["fccr"] = _safe_divide(
        df["ebitda"],
        df["interest_expense"] + df["lease_fixed_charges"] + df["tax_paid"] + df["scheduled_principal"],
    )
    df["free_cash_flow"] = df["operating_cash_flow"] - df["capex"] - df["dividends"]
    df["free_cash_flow_margin"] = _safe_divide(df["free_cash_flow"], df["revenue"])
    df["tangible_net_worth"] = df["net_worth"] - df["intangible_assets"]
    df["requested_limit_to_revenue"] = _safe_divide(df["requested_limit"], df["revenue"])

    return df


def build_trend_features(financials_with_ratios: pd.DataFrame) -> pd.DataFrame:
    period_order = {"FY-2": 0, "FY-1": 1, "FY0": 2}
    df = financials_with_ratios.copy()
    df["period_order"] = df["period"].map(period_order)
    df = df.sort_values(["borrower_id", "period_order"])

    rows = []
    for borrower_id, borrower_df in df.groupby("borrower_id"):
        borrower_df = borrower_df.sort_values("period_order")
        revenue_values = borrower_df["revenue"].to_numpy(dtype=float)
        ebitda_margin_values = borrower_df["ebitda_margin"].to_numpy(dtype=float)
        ocf_values = borrower_df["operating_cash_flow"].to_numpy(dtype=float)
        leverage_values = borrower_df["debt_to_ebitda"].to_numpy(dtype=float)
        dscr_values = borrower_df["dscr"].to_numpy(dtype=float)

        x = np.arange(len(borrower_df), dtype=float)
        rows.append(
            {
                "borrower_id": borrower_id,
                "revenue_cagr_2y": (revenue_values[-1] / revenue_values[0]) ** 0.5 - 1 if revenue_values[0] > 0 else 0.0,
                "ebitda_margin_trend": np.polyfit(x, ebitda_margin_values, 1)[0],
                "operating_cash_flow_trend": np.polyfit(x, ocf_values, 1)[0],
                "debt_to_ebitda_trend": np.polyfit(x, leverage_values, 1)[0],
                "dscr_trend": np.polyfit(x, dscr_values, 1)[0],
            }
        )
    return pd.DataFrame(rows)


def build_borrower_snapshot(
    financials_with_ratios: pd.DataFrame,
    trend_df: pd.DataFrame,
) -> pd.DataFrame:
    fy0 = financials_with_ratios[financials_with_ratios["period"] == "FY0"].copy()
    df = fy0.merge(trend_df, on="borrower_id", how="left")

    df["wc_flag"] = np.where(
        (df["working_capital"] > 0) & (df["current_ratio"] >= 1.20),
        "Green",
        np.where(df["working_capital"] > 0, "Amber", "Red"),
    )

    industry_score_map = {name: settings["final_industry_risk_score"] for name, settings in INDUSTRY_SETTINGS.items()}
    industry_level_map = {name: settings["risk_level"] for name, settings in INDUSTRY_SETTINGS.items()}
    df["industry_risk_score"] = df["industry_risk_score"].fillna(df["industry"].map(industry_score_map))
    df["risk_level"] = df["risk_level"].fillna(df["industry"].map(industry_level_map))
    if "industry_overlay_source" not in df.columns:
        df["industry_overlay_source"] = "Fallback config"
    else:
        df["industry_overlay_source"] = df["industry_overlay_source"].fillna("Fallback config")
    if "financial_benchmark_source" not in df.columns:
        df["financial_benchmark_source"] = "Synthetic SME fallback"
    else:
        df["financial_benchmark_source"] = df["financial_benchmark_source"].fillna("Synthetic SME fallback")

    keep_columns = [
        "borrower_id",
        "borrower_name",
        "industry",
        "product_family",
        "funding_type",
        "facility_type",
        "purpose",
        "security_type",
        "loan_term_months",
        "years_trading",
        "gst_registered_years",
        "requested_limit",
        "revenue",
        "ebitda",
        "ebit",
        "operating_cash_flow",
        "free_cash_flow",
        "free_cash_flow_margin",
        "current_ratio",
        "quick_ratio",
        "working_capital",
        "dscr",
        "icr",
        "fccr",
        "debt_to_ebitda",
        "debt_to_cashflow",
        "tangible_net_worth",
        "requested_limit_to_revenue",
        "industry_risk_score",
        "risk_level",
        "industry_overlay_source",
        "financial_benchmark_source",
        "wc_flag",
        "revenue_cagr_2y",
        "ebitda_margin_trend",
        "operating_cash_flow_trend",
        "debt_to_ebitda_trend",
        "dscr_trend",
        "interest_expense",
        "scheduled_principal",
        "capex",
        "cash",
    ]
    return df[keep_columns]


def assemble_feature_dataset(
    borrower_snapshot: pd.DataFrame,
    bureau_df: pd.DataFrame,
    bank_summary_df: pd.DataFrame,
    product_underwriting_df: pd.DataFrame,
    eligibility_df: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    df = borrower_snapshot.merge(bureau_df, on=["borrower_id", "borrower_name"], how="left")
    df = df.merge(bank_summary_df, on=["borrower_id", "borrower_name"], how="left")
    df = df.merge(product_underwriting_df, on="borrower_id", how="left")
    df = df.merge(eligibility_df, on="borrower_id", how="left")

    df["avg_end_balance_to_turnover"] = df["avg_end_balance_to_turnover"].fillna(0.0)
    df["credit_turnover_cv"] = df["credit_turnover_cv"].fillna(0.0)
    df["months_negative_net_cash"] = df["months_negative_net_cash"].fillna(0).astype(int)
    df["nsf_count_12m"] = df["nsf_count_12m"].fillna(0).astype(int)
    df["recent_credit_inquiries_6m"] = df["recent_credit_inquiries_6m"].fillna(0).astype(int)
    df["commercial_defaults_24m"] = df["commercial_defaults_24m"].fillna(0).astype(int)
    df["eligibility_status"] = df["eligibility_status"].fillna("Eligible")
    df["eligibility_pass"] = df["eligibility_pass"].fillna(True)
    df["hard_fail_count"] = df["hard_fail_count"].fillna(0).astype(int)
    df["soft_fail_count"] = df["soft_fail_count"].fillna(0).astype(int)

    clean_down_gap = np.clip((30 - df["clean_down_days_12m"].fillna(30)) / 30, 0.0, None)
    receivables_gap = (
        np.clip(0.60 - df["eligible_receivables_pct"].fillna(0.60), 0.0, None)
        + np.clip(df["aged_receivables_90dpd_pct"].fillna(0.0) - 0.15, 0.0, None)
        + np.clip(df["top_5_debtor_concentration_pct"].fillna(0.0) - 0.60, 0.0, None)
    )
    card_gap = (
        np.clip(df["card_utilisation_avg_pct"].fillna(0.0) - 0.85, 0.0, None)
        + np.clip(df["card_cash_advance_pct"].fillna(0.0) - 0.20, 0.0, None)
        + df["card_days_past_due_12m"].fillna(0.0) / 10.0
    )
    trade_gap = (
        np.clip(df["trade_cycle_days"].fillna(0.0) - 150.0, 0.0, None) / 150.0
        + np.clip(df["supplier_concentration_pct"].fillna(0.0) - 0.70, 0.0, None)
        + df["document_discrepancies_12m"].fillna(0.0) / 10.0
    )
    contingent_gap = (
        df["guarantee_call_event_flag"].fillna(0.0)
        + np.clip(2.0 - df["counterparty_strength_score"].fillna(2.0), 0.0, None) / 2.0
    )

    rng = np.random.default_rng(seed + 303)
    base_logit = (
        0.22 * (df["product_family"] == "Contingent Facilities").astype(int)
        + 0.14 * (df["product_family"] == "Business Cards").astype(int)
        + 0.60 * (df["industry_risk_score"] - 2.1)
        + 1.15 * np.clip(1.20 - df["dscr"], 0.0, None)
        + 0.55 * np.clip(df["debt_to_ebitda"] - 3.0, 0.0, None)
        + 0.35 * np.clip(1.10 - df["current_ratio"], 0.0, None)
        + 0.70 * np.clip(0.03 - df["free_cash_flow_margin"], 0.0, None) * 10
        + 0.60 * np.clip((700 - df["bureau_score"]) / 100, 0.0, None)
        + 0.90 * df["commercial_defaults_24m"]
        + 0.15 * df["recent_credit_inquiries_6m"]
        + 0.03 * df["days_beyond_terms_avg"]
        + 0.18 * df["months_negative_net_cash"]
        + 0.12 * df["nsf_count_12m"]
        + 0.65 * (df["tax_arrears_flag"] == "Yes").astype(int)
        + 0.45 * (df["writs_judgements_flag"] == "Yes").astype(int)
        + 0.75 * (df["external_administration_flag"] == "Yes").astype(int)
        + 0.55 * clean_down_gap
        + 1.05 * receivables_gap
        + 0.90 * card_gap
        + 0.70 * trade_gap
        + 1.20 * contingent_gap
        + 0.45 * (df["eligibility_status"] == "Conditional").astype(int)
        + 1.10 * (df["eligibility_status"] == "Outside Criteria").astype(int)
        - 0.06 * df["years_trading"]
        - 2.50 * df["revenue_cagr_2y"]
        + rng.normal(0.0, 0.35, size=len(df))
    )
    lower, upper = -10.0, 10.0
    for _ in range(60):
        midpoint = (lower + upper) / 2
        mean_probability = float((1.0 / (1.0 + np.exp(-(base_logit + midpoint)))).mean())
        if mean_probability > TARGET_DEFAULT_RATE:
            upper = midpoint
        else:
            lower = midpoint
    intercept = (lower + upper) / 2
    df["default_probability_true"] = 1.0 / (1.0 + np.exp(-(intercept + base_logit)))
    df["default_12m"] = rng.binomial(1, df["default_probability_true"]).astype(int)

    return df
