import pandas as pd

from .config import PRODUCT_DEFINITIONS, SCORE_BAND_RULES


def _rule_lookup():
    return {rule["band"]: rule for rule in SCORE_BAND_RULES}


def _product_lookup():
    return {product["facility_type"]: product for product in PRODUCT_DEFINITIONS}


def _band_for_pd(predicted_pd: float) -> str:
    for rule in SCORE_BAND_RULES:
        if predicted_pd <= rule["max_pd"]:
            return rule["band"]
    return SCORE_BAND_RULES[-1]["band"]


def assign_score_band(predicted_pd):
    if isinstance(predicted_pd, pd.Series):
        return predicted_pd.apply(_band_for_pd)
    return _band_for_pd(float(predicted_pd))


def build_policy_overlay(scored_df: pd.DataFrame, cash_rate_pct: float = 3.85) -> pd.DataFrame:
    rules = _rule_lookup()
    products = _product_lookup()
    rows = []

    for row in scored_df.itertuples(index=False):
        band_rule = rules[row.score_band]
        product = products[row.facility_type]
        industry_loading_pct = max(row.industry_risk_score - 2.0, 0.0) * 0.35
        pricing_margin_pct = band_rule["pricing_margin_pct"] + industry_loading_pct + product["product_margin_addon_pct"]
        recommended_limit = row.requested_limit * band_rule["limit_factor"]
        review_frequency = band_rule["review_frequency"]
        approval_authority = band_rule["approval_authority"]

        if row.product_family == "Receivables Finance":
            recommended_limit *= max(min(row.eligible_receivables_pct / 0.80, 1.00), 0.45)
            review_frequency = "Monthly borrowing base / annual review"
        if row.product_family == "Business Cards":
            recommended_limit *= max(1.00 - max(row.card_utilisation_avg_pct - 0.70, 0.0), 0.60)
            review_frequency = "Annual" if row.score_band in {"A", "B"} else "Semi-annual"
        if row.product_family == "Contingent Facilities":
            recommended_limit *= 1.00 if row.counterparty_strength_score >= 3.0 else 0.80
            review_frequency = "Annual / contract milestone"
            approval_authority = "Senior credit manager" if row.score_band in {"A", "B"} else "Credit committee"
        if row.product_family == "Trade Finance":
            review_frequency = "Transaction-specific / annual review"

        conditions = [band_rule["conditions"]]
        decision = band_rule["decision"]

        if getattr(row, "eligibility_status", "Eligible") == "Outside Criteria":
            decision = "Decline"
            conditions.append("Fails product eligibility criteria.")
        elif getattr(row, "eligibility_status", "Eligible") == "Conditional" and decision == "Approve":
            decision = "Refer with conditions"
            conditions.append("One or more documentary or product-structure conditions remain outstanding.")

        if getattr(row, "tax_arrears_flag", "No") == "Yes":
            conditions.append("Require clear tax position before drawdown.")
        if getattr(row, "writs_judgements_flag", "No") == "Yes":
            conditions.append("Escalate adverse bureau event to credit committee.")
        if row.facility_type == "Business Overdraft":
            conditions.append("Annual clean-down of at least 30 consecutive days when utilisation remains behavioural.")
            if row.score_band in {"C", "D"}:
                conditions.append("Monthly conduct review on transaction account.")
        if row.facility_type == "Working Capital Revolver":
            conditions.append("Monthly borrowing-base style review of cash conversion and turnover trends.")
        if row.product_family == "Receivables Finance":
            conditions.append("Monthly debtor ledger and borrowing-base certificate required.")
            conditions.append("Top-5 debtor concentration and aged debt caps apply.")
        if row.product_family == "Trade Finance":
            conditions.append("Underlying trade documents and tenor limits required for each utilisation.")
            if getattr(row, "fx_exposure_pct", 0.0) > 0.35:
                conditions.append("FX risk management or hedging evidence required.")
        if row.product_family == "Business Cards":
            conditions.append("Direct debit required with cash advances prohibited or tightly capped.")
        if row.product_family == "Contingent Facilities":
            conditions.append("Underlying contract review, indemnity, and expiry tracking required.")

        rows.append(
            {
                "facility_id": getattr(row, "facility_id", f"CFL-{int(row.borrower_id):05d}"),
                "borrower_id": row.borrower_id,
                "borrower_name": row.borrower_name,
                "industry": row.industry,
                "product_family": row.product_family,
                "funding_type": row.funding_type,
                "facility_type": row.facility_type,
                "security_type": row.security_type,
                "eligibility_status": getattr(row, "eligibility_status", "Eligible"),
                "eligibility_fail_reasons": getattr(row, "eligibility_fail_reasons", ""),
                "requested_limit": row.requested_limit,
                "recommended_limit": round(recommended_limit, 0),
                "predicted_pd": row.predicted_pd,
                "score": row.score,
                "score_band": row.score_band,
                "decision": decision,
                "review_frequency": review_frequency,
                "approval_authority": approval_authority,
                "pricing_margin_pct": round(pricing_margin_pct, 2),
                "all_in_rate_pct": round(cash_rate_pct + pricing_margin_pct, 2),
                "contingent_conversion_factor": product["contingent_conversion_factor"],
                "risk_weighted_exposure": round(recommended_limit * product["contingent_conversion_factor"], 0),
                "conditions": " ".join(conditions),
            }
        )

    return pd.DataFrame(rows)
