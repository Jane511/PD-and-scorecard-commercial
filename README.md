# Cash Flow Lending PD and Scorecard

This repo builds a bank-style Probability of Default scorecard for Australian business cash flow lending.

It is not a mortgage model and it is not a property-development model. The product scope is:

- business overdrafts
- working capital revolvers
- unsecured term loans
- invoice finance
- trade receivables finance
- trade finance lines
- business credit cards
- bank guarantees

If you want the plain-English walkthrough first, open:

- `PROJECT_OVERVIEW.md`

## What this repo does

The pipeline creates a full cash-flow lending portfolio and then scores it:

1. Load public benchmark layers from sibling repos.
2. Generate synthetic SME borrower financials for the missing bank-internal data.
3. Generate synthetic bureau, statement-conduct, and product-underwriting fields.
4. Apply product eligibility rules.
5. Build WOE and IV features.
6. Fit a logistic-regression PD scorecard.
7. Convert PD into score bands, policy outcomes, pricing overlays, and monitoring outputs.

Main run command:

```bash
python scripts/run_pipeline.py
```

## What data this repo uses from repo 9

Sibling repo:

- `../9.Industry Risk Analysis_Australia/`

Files used here:

- `output/tables/industry_base_risk_scorecard.csv`
- `output/tables/industry_public_benchmarks.csv`

Metrics loaded from `industry_base_risk_scorecard.csv`:

- `classification_risk_score`
- `macro_risk_score`
- `industry_base_risk_score`
- `industry_base_risk_level`
- `employment_yoy_growth_pct`
- `ebitda_margin_pct_latest`
- `inventory_days_est`
- `demand_yoy_growth_pct`
- `cash_rate_latest_pct`

Metrics loaded from `industry_public_benchmarks.csv` as fill-ins when needed:

- `ebitda_margin_pct_latest`
- `inventory_days_est`
- `employment_yoy_growth_pct`
- `demand_yoy_growth_pct`

How repo `1.2` uses repo `9`:

- It maps those fields into `data/processed/public_industry_profiles.csv`.
- `classification_risk_score`, `macro_risk_score`, and `final_industry_risk_score` become the core industry-risk overlay for each synthetic borrower.
- `public_ebitda_margin_pct_latest` and `public_inventory_days_est` help anchor sector realism.
- `public_employment_yoy_growth_pct`, `public_demand_yoy_growth_pct`, and `public_cash_rate_latest_pct` are preserved in the merged industry profile and audit layer.

## What data this repo uses from repo 8

Sibling repo:

- `../8. Financial Statement Analysis — Commercial Cash Flow Lending/`

Repo `8` exports the benchmark files this repo prefers:

- `outputs/tables/public_company_analysis/public_listed_company_financials_standardized.csv`
- `outputs/tables/public_company_analysis/public_listed_company_benchmarks.csv`
- `outputs/tables/public_company_analysis/public_transaction_benchmarks.csv`
- `outputs/tables/public_company_analysis/public_invoice_benchmarks.csv`

### Listed-company layer

Main file used:

- `public_listed_company_benchmarks.csv`

Metrics loaded:

- `listed_company_count`
- `listed_revenue_median`
- `listed_ebitda_margin_median`
- `listed_ocf_margin_median`
- `listed_current_ratio_median`
- `listed_debt_to_ebitda_median`

How they are used in repo `1.2`:

- `listed_ebitda_margin_median` anchors synthetic borrower EBITDA margin by industry.
- `listed_debt_to_ebitda_median` anchors synthetic leverage.
- `listed_current_ratio_median` anchors synthetic liquidity.
- `listed_company_count` and `listed_revenue_median` are stored in `data/processed/public_industry_profiles.csv` for transparency and context.

Audit file also loaded:

- `public_listed_company_financials_standardized.csv`

That row-level file is mainly kept for provenance and inspection. The benchmark file is the one that actually drives calibration.

### Transaction-conduct proxy layer

Main file used:

- `public_transaction_benchmarks.csv`

Metrics loaded:

- `transaction_account_count`
- `transaction_record_count`
- `tx_avg_monthly_credits_median`
- `tx_avg_monthly_debits_median`
- `tx_credit_turnover_cv_median`
- `tx_months_negative_net_cash_median`
- `tx_failed_event_rate_median`
- `tx_cash_advance_rate_median`

How they are used in repo `1.2`:

- `tx_credit_turnover_cv_median` anchors synthetic inflow volatility in generated bank-statement conduct.
- `tx_failed_event_rate_median` influences synthetic failed-payment and NSF intensity.
- `tx_cash_advance_rate_median` anchors business-card cash-advance behaviour.
- The other transaction fields are carried into `data/processed/public_industry_profiles.csv` for benchmark context and audit.

Important note:

- These are public-company proxy conduct benchmarks built in repo `8`.
- They are not raw bank transaction ledgers.

### Invoice and receivables proxy layer

Main file used:

- `public_invoice_benchmarks.csv`

Metrics loaded:

- `invoice_record_count`
- `invoice_customer_count`
- `invoice_amount_median`
- `invoice_payment_delay_median_days`
- `invoice_late_payment_rate`
- `invoice_severe_late_rate_90dpd`
- `invoice_top_customer_concentration_pct`
- `invoice_dilution_proxy_rate`

How they are used in repo `1.2`:

- `invoice_payment_delay_median_days` feeds into debtor-days calibration in synthetic financial generation.
- `invoice_top_customer_concentration_pct` anchors top-debtor concentration for receivables finance.
- `invoice_severe_late_rate_90dpd` anchors aged receivables stress.
- `invoice_dilution_proxy_rate` anchors dilution assumptions.
- The remaining invoice fields are stored in the benchmark layer for reference and audit.

Important note:

- These are public-company receivables proxy benchmarks built in repo `8`.
- They are not raw invoice event data.

## What remains synthetic in this repo

This repo still synthesises the borrower-level data that would normally be private inside a bank:

- three-year SME borrower financial statements
- commercial bureau records
- bank-statement monthly conduct history
- product-specific underwriting fields
- borrower-level default flag used for PD modelling
- product-policy and approval overlays

Public data is being used as a calibration layer, not as a substitute for unavailable bank-internal borrower history.

## Current source priority

The benchmark loading order is:

1. Repo `9` for industry and macro overlays.
2. Repo `8` for listed-company, conduct, and receivables benchmark exports.
3. Local fallback CSVs in `data/public_inputs/` only if the sibling exported files are missing.

Local fallback folders are still supported if you want to drop your own CSVs:

- `data/public_inputs/listed_company_reports/`
- `data/public_inputs/kaggle_transactions/`
- `data/public_inputs/kaggle_invoices/`

## Key outputs in this repo

Core processed benchmark layer:

- `data/processed/public_industry_profiles.csv`
- `data/processed/public_listed_company_benchmarks.csv`
- `data/processed/public_transaction_benchmarks.csv`
- `data/processed/public_invoice_benchmarks.csv`
- `data/processed/public_data_provenance.csv`

Synthetic borrower and underwriting layer:

- `data/raw/cashflow_lending_financials.csv`
- `data/raw/credit_bureau_reports.csv`
- `data/raw/bank_statement_summary.csv`
- `data/raw/product_underwriting_data.csv`
- `data/processed/borrower_snapshot.csv`
- `data/processed/cashflow_lending_feature_dataset.csv`
- `data/processed/product_eligibility_matrix.csv`

Scorecard and policy outputs:

- `output/scorecard_outputs/03_scorecard_coefficients.csv`
- `output/scorecard_outputs/07_scorecard_metadata.csv`
- `output/scorecard_outputs/13_product_family_summary.csv`
- `output/policy_overlay.csv`
- `output/portfolio_summary.md`

## How to refresh everything

Run repo `8` first so this repo can consume the latest exported benchmarks:

```bash
cd "..\\8. Financial Statement Analysis — Commercial Cash Flow Lending"
python -m src.public_company_analysis
```

Then run this repo:

```bash
cd "..\\1.2 PD and Score Card_Cashflow Lending"
python scripts/run_pipeline.py
```

## Folder structure

```text
.
├── data/
│   ├── public_inputs/
│   ├── raw/
│   └── processed/
├── output/
│   └── scorecard_outputs/
├── scripts/
│   └── run_pipeline.py
├── src/
└── tests/
```
