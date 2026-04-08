import pandas as pd

from .config import PRODUCT_DEFINITIONS


PRODUCT_MAP = {product["facility_type"]: product for product in PRODUCT_DEFINITIONS}

SOFT_FAIL_TAGS = {
    "bank_statements",
    "accounting_data",
    "trade_documents",
}


def assess_product_eligibility(feature_df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for row in feature_df.itertuples(index=False):
        product = PRODUCT_MAP[row.facility_type]
        checks = []

        checks.append(("years_trading", row.years_trading >= product["min_years_trading"], f"min {product['min_years_trading']} years trading"))
        checks.append(("gst_history", row.gst_registered_years >= product["min_gst_registered_years"], f"min {product['min_gst_registered_years']} years GST history"))
        checks.append(("turnover", row.revenue >= product["min_turnover"], f"turnover >= A${product['min_turnover']:,.0f}"))
        checks.append(("turnover_ceiling", row.revenue <= product["max_turnover"], f"turnover <= A${product['max_turnover']:,.0f}"))
        checks.append(("bank_statements", row.linked_bank_account_months >= product["min_bank_statement_months"], f"min {product['min_bank_statement_months']} months bank statements"))
        checks.append(("accounting_data", row.accounting_software_months >= product["min_accounting_months"], f"min {product['min_accounting_months']} months accounting data"))

        serviceability_pass = row.dscr >= (1.10 if row.funding_type == "Funded" else 1.00)
        checks.append(("serviceability", serviceability_pass, "DSCR threshold met"))
        checks.append(("bureau", row.commercial_defaults_24m == 0 and row.bureau_score >= 520, "no recent commercial default and bureau score >= 520"))
        checks.append(("tax_status", row.tax_arrears_flag == "No", "tax arrears not present"))

        conduct_pass = row.nsf_count_12m <= 2 and row.months_negative_net_cash <= 7
        checks.append(("conduct", conduct_pass, "acceptable statement conduct"))

        if product["clean_down_required"]:
            checks.append(("clean_down", row.clean_down_days_12m >= 30 and row.peak_limit_utilisation_pct <= 1.10, "clean-down and utilisation test met"))

        if product["requires_debtor_ledger"]:
            receivables_pass = (
                row.eligible_receivables_pct >= 0.60
                and row.aged_receivables_90dpd_pct <= 0.15
                and row.top_5_debtor_concentration_pct <= 0.60
                and row.dilution_pct <= 0.12
            )
            checks.append(("receivables_quality", receivables_pass, "receivables quality within borrowing-base policy"))

        if row.product_family == "Business Cards":
            card_pass = (
                row.card_utilisation_avg_pct <= 0.85
                and row.card_cash_advance_pct <= 0.20
                and row.card_days_past_due_12m <= 1
            )
            checks.append(("card_behaviour", card_pass, "card utilisation and payment behaviour within policy"))

        if row.product_family == "Trade Finance":
            trade_pass = (
                row.trade_cycle_days <= 150
                and row.supplier_concentration_pct <= 0.70
                and row.document_discrepancies_12m <= 3
            )
            checks.append(("trade_documents", trade_pass, "trade-cycle and document controls met"))

        if row.product_family == "Contingent Facilities":
            contingent_pass = (
                row.guarantee_call_event_flag == 0
                and row.counterparty_strength_score >= 2.0
                and row.guarantee_tenor_months <= 24
            )
            checks.append(("trade_documents", contingent_pass, "guarantee tenor and counterparty tests met"))

        failed = [check for check in checks if not check[1]]
        hard_fails = [check for check in failed if check[0] not in SOFT_FAIL_TAGS]
        soft_fails = [check for check in failed if check[0] in SOFT_FAIL_TAGS]

        if not failed:
            status = "Eligible"
        elif hard_fails:
            status = "Outside Criteria"
        else:
            status = "Conditional"

        fail_reasons = "; ".join(check[2] for check in failed) if failed else ""
        rows.append(
            {
                "borrower_id": row.borrower_id,
                "eligibility_status": status,
                "eligibility_pass": status == "Eligible",
                "hard_fail_count": len(hard_fails),
                "soft_fail_count": len(soft_fails),
                "eligibility_fail_reasons": fail_reasons,
            }
        )

    return pd.DataFrame(rows)
