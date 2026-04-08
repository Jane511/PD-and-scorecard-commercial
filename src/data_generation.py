import math

import numpy as np
import pandas as pd

from .config import INDUSTRY_SETTINGS, PRODUCT_DEFINITIONS
from .public_data import benchmark_lookup


NAME_PREFIXES = (
    "Apex",
    "Atlas",
    "Coastal",
    "Delta",
    "Harbour",
    "Meridian",
    "Metro",
    "Nova",
    "Pacific",
    "Peak",
    "Southern",
    "Summit",
    "Titan",
    "Vanguard",
)

NAME_SUFFIXES = (
    "Group",
    "Industries",
    "Logistics",
    "Partners",
    "Pty Ltd",
    "Services",
    "Solutions",
    "Supply Co",
    "Trading",
    "Works",
)

PRODUCT_MAP = {product["facility_type"]: product for product in PRODUCT_DEFINITIONS}


def _safe_ratio(numerator, denominator, default=0.0):
    return numerator / denominator if denominator not in (0, 0.0) else default


def _make_borrower_name(rng: np.random.Generator) -> str:
    return f"{rng.choice(NAME_PREFIXES)} {rng.choice(NAME_SUFFIXES)}"


def generate_cashflow_lending_financials(
    n_borrowers: int,
    seed: int,
    industry_profile_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    public_profile_map = (
        industry_profile_df.set_index("industry").to_dict(orient="index")
        if industry_profile_df is not None and not industry_profile_df.empty
        else {}
    )

    for borrower_id in range(1, n_borrowers + 1):
        industry_name = rng.choice(list(INDUSTRY_SETTINGS.keys()))
        profile = dict(INDUSTRY_SETTINGS[industry_name])
        profile.update({key: value for key, value in public_profile_map.get(industry_name, {}).items() if pd.notna(value)})
        facility = PRODUCT_DEFINITIONS[rng.integers(0, len(PRODUCT_DEFINITIONS))]
        years_trading = int(rng.integers(2, 26))
        gst_registered_years = max(years_trading - int(rng.integers(0, 2)), 1)

        revenue_low, revenue_high = profile["revenue_range"]
        base_revenue = rng.uniform(revenue_low, revenue_high)
        growth_1 = np.clip(rng.normal(profile["growth_mean"], profile["growth_std"]), -0.22, 0.35)
        growth_2 = np.clip(rng.normal(profile["growth_mean"], profile["growth_std"]), -0.22, 0.35)
        revenues = [
            base_revenue,
            base_revenue * (1 + growth_1),
            base_revenue * (1 + growth_1) * (1 + growth_2),
        ]

        public_margin_anchor = profile.get("listed_ebitda_margin_median")
        if pd.isna(public_margin_anchor):
            public_margin_anchor = _safe_ratio(profile.get("public_ebitda_margin_pct_latest", np.nan), 100.0, default=np.nan)
        base_margin = rng.uniform(*profile["ebitda_margin"])
        if pd.notna(public_margin_anchor):
            base_margin = float(np.clip((base_margin + public_margin_anchor) / 2.0, 0.03, 0.35))
        ebitda_margins = [
            np.clip(base_margin + rng.normal(0, 0.015), 0.03, 0.35)
            for _ in range(3)
        ]
        ebitda = [revenue * margin for revenue, margin in zip(revenues, ebitda_margins)]

        depreciation_pct = rng.uniform(0.01, 0.03)
        depreciation = [revenue * depreciation_pct for revenue in revenues]
        ebit = [ebitda_value - dep for ebitda_value, dep in zip(ebitda, depreciation)]

        debt_to_revenue = rng.uniform(0.12, 0.42)
        public_leverage_anchor = profile.get("listed_debt_to_ebitda_median")
        if pd.notna(public_leverage_anchor):
            implied_debt_to_revenue = public_leverage_anchor * max(base_margin, 0.05)
            debt_to_revenue = float(np.clip((debt_to_revenue + implied_debt_to_revenue) / 2.0, 0.08, 0.55))
        opening_debt = revenues[0] * debt_to_revenue
        amortisation = rng.uniform(0.03, 0.10)
        total_debt = [
            opening_debt,
            opening_debt * (1 - amortisation),
            opening_debt * (1 - amortisation) ** 2,
        ]

        interest_rate = rng.uniform(0.065, 0.11)
        interest_expense = [debt * interest_rate for debt in total_debt]
        scheduled_principal = [debt * rng.uniform(0.05, 0.12) for debt in total_debt]

        tax_rate = rng.uniform(0.24, 0.30)
        profit_before_tax = [ebit_value - interest for ebit_value, interest in zip(ebit, interest_expense)]
        npat = [max(pbt * (1 - tax_rate), pbt * 0.45) for pbt in profit_before_tax]
        tax_paid = [max(pbt * tax_rate, 0.0) for pbt in profit_before_tax]

        working_capital_noise = [rng.normal(0, revenue * 0.015) for revenue in revenues]
        operating_cash_flow = [
            max(npat_value + dep + noise, revenue * 0.01)
            for npat_value, dep, noise, revenue in zip(npat, depreciation, working_capital_noise, revenues)
        ]

        debtor_days = rng.uniform(28, 75)
        payment_delay_anchor = profile.get("invoice_payment_delay_median_days")
        if pd.notna(payment_delay_anchor):
            debtor_days = float(np.clip((debtor_days + max(payment_delay_anchor + 30.0, 15.0)) / 2.0, 20.0, 95.0))
        inventory_days = (
            rng.uniform(10, 55)
            if "Professional" not in industry_name and "Health Care" not in industry_name
            else rng.uniform(1, 20)
        )
        cash_pct = rng.uniform(0.03, 0.12)
        other_ca_pct = rng.uniform(0.01, 0.05)
        fixed_assets_pct = rng.uniform(0.35, 0.60)
        current_ratio_target = rng.uniform(0.95, 1.60)
        if pd.notna(profile.get("listed_current_ratio_median")):
            current_ratio_target = float(np.clip((current_ratio_target + profile["listed_current_ratio_median"]) / 2.0, 0.90, 1.80))

        debtors = [revenue * debtor_days / 365 for revenue in revenues]
        inventory = [revenue * inventory_days / 365 for revenue in revenues]
        cash = [revenue * cash_pct for revenue in revenues]
        current_assets = [
            cash_value + debtors_value + inventory_value + revenue * other_ca_pct
            for cash_value, debtors_value, inventory_value, revenue in zip(cash, debtors, inventory, revenues)
        ]
        current_liabilities = [assets / max(current_ratio_target + rng.normal(0, 0.06), 0.70) for assets in current_assets]
        total_assets = [assets / max(1 - fixed_assets_pct, 0.20) for assets in current_assets]

        base_equity = total_assets[0] * rng.uniform(0.18, 0.38)
        net_worth = [
            base_equity,
            base_equity + npat[0] * 0.60,
            base_equity + npat[0] * 0.60 + npat[1] * 0.60,
        ]
        share_capital = [equity * rng.uniform(0.28, 0.45) for equity in net_worth]
        capex = [revenue * rng.uniform(0.015, 0.045) for revenue in revenues]
        dividends = [max(net_profit * rng.uniform(0.08, 0.18), 0.0) for net_profit in npat]
        intangible_assets = [assets * rng.uniform(0.01, 0.05) for assets in total_assets]
        lease_fixed_charges = [revenue * rng.uniform(0.004, 0.012) for revenue in revenues]

        if facility["product_family"] == "Receivables Finance":
            requested_limit = debtors[-1] * rng.uniform(
                facility["limit_multiple_low"],
                facility["limit_multiple_high"],
            )
        elif facility["product_family"] == "Business Cards":
            requested_limit = min(
                max((revenues[-1] / 12.0) * rng.uniform(0.08, 0.35), 10_000),
                250_000,
            )
        elif facility["product_family"] == "Contingent Facilities":
            requested_limit = revenues[-1] * rng.uniform(
                facility["limit_multiple_low"],
                facility["limit_multiple_high"],
            )
        else:
            requested_limit = revenues[-1] * rng.uniform(
                facility["limit_multiple_low"],
                facility["limit_multiple_high"],
            )

        borrower_name = _make_borrower_name(rng)
        purpose = rng.choice(facility["purpose_options"])

        for period, revenue, ebitda_value, ebit_value, npat_value, ocf_value, cash_value, debtors_value, inventory_value, assets_value, liabilities_value, total_assets_value, total_debt_value, interest_value, share_capital_value, equity_value, principal_value, capex_value, dividend_value, intangible_value, lease_value, tax_value in zip(
            ("FY-2", "FY-1", "FY0"),
            revenues,
            ebitda,
            ebit,
            npat,
            operating_cash_flow,
            cash,
            debtors,
            inventory,
            current_assets,
            current_liabilities,
            total_assets,
            total_debt,
            interest_expense,
            share_capital,
            net_worth,
            scheduled_principal,
            capex,
            dividends,
            intangible_assets,
            lease_fixed_charges,
            tax_paid,
        ):
            rows.append(
                {
                    "borrower_id": borrower_id,
                    "borrower_name": borrower_name,
                    "industry": industry_name,
                    "period": period,
                    "product_family": facility["product_family"],
                    "funding_type": facility["funding_type"],
                    "years_trading": years_trading,
                    "gst_registered_years": gst_registered_years,
                    "facility_type": facility["facility_type"],
                    "purpose": purpose,
                    "security_type": facility["security_type"],
                    "loan_term_months": facility["loan_term_months"],
                    "requested_limit": round(requested_limit),
                    "revenue": round(revenue),
                    "ebitda": round(ebitda_value),
                    "ebit": round(ebit_value),
                    "npat": round(npat_value),
                    "operating_cash_flow": round(ocf_value),
                    "cash": round(cash_value),
                    "debtors": round(debtors_value),
                    "inventory": round(inventory_value),
                    "current_assets": round(assets_value),
                    "current_liabilities": round(liabilities_value),
                    "total_assets": round(total_assets_value),
                    "total_debt": round(total_debt_value),
                    "interest_expense": round(interest_value),
                    "share_capital": round(share_capital_value),
                    "net_worth": round(equity_value),
                    "scheduled_principal": round(principal_value),
                    "capex": round(capex_value),
                    "dividends": round(dividend_value),
                    "intangible_assets": round(intangible_value),
                    "lease_fixed_charges": round(lease_value),
                    "tax_paid": round(tax_value),
                    "industry_risk_score": profile["final_industry_risk_score"],
                    "risk_level": profile["risk_level"],
                    "industry_overlay_source": profile.get("industry_overlay_source", "Fallback config"),
                    "financial_benchmark_source": profile.get("listed_benchmark_source", "Synthetic SME fallback"),
                }
            )

    return pd.DataFrame(rows)


def generate_credit_bureau_reports(
    borrower_snapshot: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 101)
    rows = []

    for row in borrower_snapshot.itertuples(index=False):
        dscr_gap = max(1.20 - row.dscr, 0.0)
        leverage_gap = max(row.debt_to_ebitda - 3.0, 0.0)
        liquidity_gap = max(1.10 - row.current_ratio, 0.0)
        risk_signal = (
            0.90 * (row.industry_risk_score - 2.0)
            + 1.10 * dscr_gap
            + 0.45 * leverage_gap
            + 0.35 * liquidity_gap
            + rng.normal(0.0, 0.35)
        )
        bureau_score = float(np.clip(760 - 65 * risk_signal - rng.normal(0.0, 35.0), 320, 900))
        defaults = int(np.clip(rng.poisson(max(risk_signal - 0.6, 0.0) * 0.8), 0, 4))
        inquiries = int(np.clip(round(rng.normal(2.0 + risk_signal, 1.3)), 0, 10))
        days_beyond_terms = float(np.clip(10 + 14 * risk_signal + rng.normal(0.0, 7.0), 0.0, 90.0))

        tax_arrears = "Yes" if risk_signal > 1.55 and rng.random() < 0.55 else "No"
        writs_judgements = "Yes" if risk_signal > 2.10 and rng.random() < 0.35 else "No"
        external_admin = "Yes" if risk_signal > 2.75 and rng.random() < 0.18 else "No"
        director_adverse = "Yes" if risk_signal > 1.80 and rng.random() < 0.30 else "No"

        rows.append(
            {
                "borrower_id": row.borrower_id,
                "borrower_name": row.borrower_name,
                "bureau_provider": "Synthetic AU commercial bureau blend",
                "bureau_score": round(bureau_score, 1),
                "commercial_defaults_24m": defaults,
                "recent_credit_inquiries_6m": inquiries,
                "days_beyond_terms_avg": round(days_beyond_terms, 1),
                "tax_arrears_flag": tax_arrears,
                "writs_judgements_flag": writs_judgements,
                "external_administration_flag": external_admin,
                "director_adverse_history_flag": director_adverse,
            }
        )

    return pd.DataFrame(rows)


def generate_bank_statement_data(
    borrower_snapshot: pd.DataFrame,
    seed: int,
    transaction_benchmark_df: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed + 202)
    monthly_rows = []

    for row in borrower_snapshot.itertuples(index=False):
        transaction_benchmark = benchmark_lookup(transaction_benchmark_df, row.industry) if transaction_benchmark_df is not None else {}
        base_credit = row.revenue / 12.0
        base_ebitda_margin = _safe_ratio(row.ebitda, row.revenue, default=0.08)
        balance = max(row.cash * 0.55, row.requested_limit * 0.02)
        monthly_debt_service = (row.interest_expense + row.scheduled_principal) / 12.0
        volatility = 0.05 + max(row.industry_risk_score - 2.1, 0.0) * 0.03
        public_cv = transaction_benchmark.get("tx_credit_turnover_cv_median")
        if pd.notna(public_cv):
            volatility = float(np.clip((volatility + public_cv) / 2.0, 0.03, 0.30))
        public_failed_event_rate = transaction_benchmark.get("tx_failed_event_rate_median", np.nan)

        for month in range(1, 13):
            seasonal = 1.0 + 0.12 * math.sin((month / 12.0) * 2 * math.pi)
            inflows = base_credit * seasonal * (1 + rng.normal(0.0, volatility))
            operating_outflows = inflows * (1 - base_ebitda_margin + rng.normal(0.0, 0.03))
            capex_outflow = row.capex / 12.0
            total_outflows = max(operating_outflows + monthly_debt_service + capex_outflow, 0.0)
            net_cash = inflows - total_outflows

            balance = balance + net_cash
            min_buffer = -row.requested_limit * (1.00 if row.facility_type == "Business Overdraft" else 0.10)
            balance = max(balance, min_buffer)

            utilisation_pct = (
                abs(balance) / row.requested_limit
                if balance < 0 and row.requested_limit > 0
                else 0.0
            )
            failed_intensity = max(utilisation_pct - 0.45, 0.0) * 1.5
            nsf_intensity = max(utilisation_pct - 0.30, 0.0) * 2.0
            if pd.notna(public_failed_event_rate):
                failed_intensity += public_failed_event_rate * 2.5
                nsf_intensity += public_failed_event_rate * 3.0
            unpaid_direct_debits = int(max(0, round(rng.poisson(failed_intensity))))
            nsf_count = int(max(0, round(rng.poisson(nsf_intensity))))

            monthly_rows.append(
                {
                    "borrower_id": row.borrower_id,
                    "borrower_name": row.borrower_name,
                    "month_index": month,
                    "monthly_credits": round(inflows, 2),
                    "monthly_debits": round(total_outflows, 2),
                    "net_cash_movement": round(net_cash, 2),
                    "end_balance": round(balance, 2),
                    "utilisation_pct": round(utilisation_pct, 4),
                    "unpaid_direct_debits": unpaid_direct_debits,
                    "nsf_count": nsf_count,
                }
            )

    monthly_df = pd.DataFrame(monthly_rows)
    summary = (
        monthly_df.groupby(["borrower_id", "borrower_name"], as_index=False)
        .agg(
            avg_monthly_credits=("monthly_credits", "mean"),
            avg_monthly_debits=("monthly_debits", "mean"),
            avg_end_balance=("end_balance", "mean"),
            min_end_balance=("end_balance", "min"),
            months_negative_net_cash=("net_cash_movement", lambda s: int((s < 0).sum())),
            months_overdrawn=("end_balance", lambda s: int((s < 0).sum())),
            unpaid_direct_debits_12m=("unpaid_direct_debits", "sum"),
            nsf_count_12m=("nsf_count", "sum"),
            credit_turnover_std=("monthly_credits", "std"),
            peak_utilisation_pct=("utilisation_pct", "max"),
        )
    )
    summary["credit_turnover_std"] = summary["credit_turnover_std"].fillna(0.0)
    summary["credit_turnover_cv"] = summary["credit_turnover_std"] / summary["avg_monthly_credits"].replace(0, np.nan)
    summary["credit_turnover_cv"] = summary["credit_turnover_cv"].fillna(0.0)
    summary["avg_end_balance_to_turnover"] = summary["avg_end_balance"] / summary["avg_monthly_credits"].replace(0, np.nan)
    summary["avg_end_balance_to_turnover"] = summary["avg_end_balance_to_turnover"].fillna(0.0)
    summary["statement_conduct_flag"] = np.where(
        (summary["months_overdrawn"] <= 1) & (summary["nsf_count_12m"] == 0),
        "Green",
        np.where(
            (summary["months_overdrawn"] <= 3) & (summary["nsf_count_12m"] <= 2),
            "Amber",
            "Red",
        ),
    )
    return monthly_df, summary


def generate_product_underwriting_data(
    borrower_snapshot: pd.DataFrame,
    bureau_df: pd.DataFrame,
    bank_summary: pd.DataFrame,
    seed: int,
    transaction_benchmark_df: pd.DataFrame | None = None,
    invoice_benchmark_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed + 303)
    summary_map = bank_summary.set_index("borrower_id")
    bureau_map = bureau_df.set_index("borrower_id")
    rows = []

    for row in borrower_snapshot.itertuples(index=False):
        product = PRODUCT_MAP[row.facility_type]
        bank = summary_map.loc[row.borrower_id]
        bureau = bureau_map.loc[row.borrower_id]
        transaction_benchmark = benchmark_lookup(transaction_benchmark_df, row.industry) if transaction_benchmark_df is not None else {}
        invoice_benchmark = benchmark_lookup(invoice_benchmark_df, row.industry) if invoice_benchmark_df is not None else {}

        accounting_software_months = max(int(row.years_trading * 12 - rng.integers(0, 24)), 0)
        linked_bank_account_months = max(int(row.years_trading * 12 - rng.integers(0, 12)), 0)
        bas_lodgement_days_avg = float(np.clip(6 + (row.industry_risk_score - 2.0) * 4 + rng.normal(0.0, 5.0), 0.0, 45.0))

        clean_down_days = np.nan
        peak_limit_utilisation_pct = np.nan
        excess_days_12m = np.nan
        eligible_receivables_pct = np.nan
        aged_receivables_90dpd_pct = np.nan
        top_5_debtor_concentration_pct = np.nan
        dilution_pct = np.nan
        debtor_book_value = np.nan
        card_utilisation_avg_pct = np.nan
        card_cash_advance_pct = np.nan
        card_days_past_due_12m = np.nan
        trade_cycle_days = np.nan
        supplier_concentration_pct = np.nan
        document_discrepancies_12m = np.nan
        fx_exposure_pct = np.nan
        counterparty_strength_score = np.nan
        guarantee_tenor_months = np.nan
        guarantee_call_event_flag = np.nan

        if row.product_family == "Revolving Liquidity":
            peak_limit_utilisation_pct = float(np.clip(bank["peak_utilisation_pct"] + rng.normal(0.05, 0.08), 0.05, 1.35))
            clean_down_days = int(
                np.clip(
                    75 - bank["months_overdrawn"] * 14 - peak_limit_utilisation_pct * 35 + rng.normal(0.0, 8.0),
                    0,
                    95,
                )
            )
            excess_days_12m = int(np.clip(max(peak_limit_utilisation_pct - 1.0, 0.0) * 60 + rng.poisson(1), 0, 45))
        elif row.product_family == "Receivables Finance":
            debtor_book_value = row.revenue * rng.uniform(0.10, 0.28)
            top_5_debtor_concentration_pct = float(np.clip(rng.normal(0.42, 0.12), 0.10, 0.85))
            if pd.notna(invoice_benchmark.get("invoice_top_customer_concentration_pct")):
                top_5_debtor_concentration_pct = float(
                    np.clip(
                        (top_5_debtor_concentration_pct + invoice_benchmark["invoice_top_customer_concentration_pct"]) / 2.0,
                        0.10,
                        0.90,
                    )
                )
            aged_receivables_90dpd_pct = float(
                np.clip(
                    0.03 + bureau["days_beyond_terms_avg"] / 250 + max(bureau["commercial_defaults_24m"], 0) * 0.02 + rng.normal(0.0, 0.03),
                    0.0,
                    0.45,
                )
            )
            if pd.notna(invoice_benchmark.get("invoice_severe_late_rate_90dpd")):
                aged_receivables_90dpd_pct = float(
                    np.clip(
                        (aged_receivables_90dpd_pct + invoice_benchmark["invoice_severe_late_rate_90dpd"]) / 2.0,
                        0.0,
                        0.45,
                    )
                )
            dilution_pct = float(np.clip(rng.normal(0.06, 0.03), 0.0, 0.20))
            if pd.notna(invoice_benchmark.get("invoice_dilution_proxy_rate")):
                dilution_pct = float(
                    np.clip((dilution_pct + invoice_benchmark["invoice_dilution_proxy_rate"]) / 2.0, 0.0, 0.20)
                )
            eligible_receivables_pct = float(
                np.clip(
                    0.88 - top_5_debtor_concentration_pct * 0.20 - aged_receivables_90dpd_pct * 0.45 - dilution_pct * 0.30,
                    0.35,
                    0.92,
                )
            )
        elif row.product_family == "Business Cards":
            card_utilisation_avg_pct = float(
                np.clip(
                    0.25 + bank["months_negative_net_cash"] * 0.05 + rng.normal(0.0, 0.12),
                    0.05,
                    1.15,
                )
            )
            card_cash_advance_pct = float(np.clip(rng.normal(0.06 + row.industry_risk_score * 0.01, 0.04), 0.0, 0.45))
            if pd.notna(transaction_benchmark.get("tx_cash_advance_rate_median")):
                card_cash_advance_pct = float(
                    np.clip((card_cash_advance_pct + transaction_benchmark["tx_cash_advance_rate_median"]) / 2.0, 0.0, 0.45)
                )
            card_days_past_due_12m = int(np.clip(rng.poisson(card_utilisation_avg_pct * 4), 0, 8))
        elif row.product_family == "Trade Finance":
            trade_cycle_days = float(np.clip(rng.normal(70 + row.industry_risk_score * 8, 18), 20, 180))
            supplier_concentration_pct = float(np.clip(rng.normal(0.38, 0.14), 0.08, 0.85))
            document_discrepancies_12m = int(np.clip(rng.poisson(1.0 + max(row.industry_risk_score - 2.0, 0.0)), 0, 10))
            fx_exposure_pct = float(np.clip(rng.normal(0.18, 0.15), 0.0, 0.80))
        elif row.product_family == "Contingent Facilities":
            guarantee_tenor_months = int(np.clip(rng.normal(product["loan_term_months"], 4), 3, 36))
            counterparty_strength_score = float(np.clip(rng.normal(3.2, 0.9), 1.0, 5.0))
            guarantee_call_event_flag = int(
                rng.random()
                < np.clip(
                    0.01 + max(row.industry_risk_score - 2.0, 0.0) * 0.03 + max(1.2 - row.dscr, 0.0) * 0.06,
                    0.0,
                    0.35,
                )
            )

        rows.append(
            {
                "borrower_id": row.borrower_id,
                "accounting_software_months": accounting_software_months,
                "linked_bank_account_months": linked_bank_account_months,
                "bas_lodgement_days_avg": round(bas_lodgement_days_avg, 1),
                "clean_down_days_12m": clean_down_days,
                "peak_limit_utilisation_pct": peak_limit_utilisation_pct,
                "excess_days_12m": excess_days_12m,
                "debtor_book_value": debtor_book_value,
                "eligible_receivables_pct": eligible_receivables_pct,
                "aged_receivables_90dpd_pct": aged_receivables_90dpd_pct,
                "top_5_debtor_concentration_pct": top_5_debtor_concentration_pct,
                "dilution_pct": dilution_pct,
                "card_utilisation_avg_pct": card_utilisation_avg_pct,
                "card_cash_advance_pct": card_cash_advance_pct,
                "card_days_past_due_12m": card_days_past_due_12m,
                "trade_cycle_days": trade_cycle_days,
                "supplier_concentration_pct": supplier_concentration_pct,
                "document_discrepancies_12m": document_discrepancies_12m,
                "fx_exposure_pct": fx_exposure_pct,
                "counterparty_strength_score": counterparty_strength_score,
                "guarantee_tenor_months": guarantee_tenor_months,
                "guarantee_call_event_flag": guarantee_call_event_flag,
            }
        )

    return pd.DataFrame(rows)
