# Cash Flow Lending Project Overview

This project is an end-to-end demonstration of how a bank-style PD and scorecard framework can be built for Australian business cash flow lending.

It covers:

- revolving working-capital facilities
- unsecured term cash-flow loans
- receivables finance
- trade finance
- business cards
- contingent facilities such as bank guarantees

It does not cover:

- home lending
- property-backed commercial lending
- land subdivision
- development finance

## The simple idea

This repo does not pretend public data is enough to build a real bank model on its own.

Instead, it uses public benchmark layers from sibling repos to make the synthetic SME portfolio more realistic:

- repo `9` supplies industry and macro risk overlays
- repo `8` supplies public-company financial, conduct, and receivables proxy benchmarks
- repo `1.2` generates the missing borrower-level bank data and builds the PD scorecard

So the design is:

1. Use public external information wherever it is reasonable.
2. Use synthetic data for the bank-only fields that are not public.
3. Join both together into one explainable PD workflow.

## What comes from repo 9

Source repo:

- `../9.Industry Risk Analysis_Australia`

Files used here:

- `output/tables/industry_base_risk_scorecard.csv`
- `output/tables/industry_public_benchmarks.csv`

What this repo takes from those files:

- industry classification risk
- macro risk
- final industry risk score
- industry risk level
- public EBITDA margin by industry
- public inventory-days estimate
- public employment growth
- public demand growth proxy
- public cash-rate overlay

Where those values land in repo `1.2`:

- `data/processed/public_industry_profiles.csv`

How those values matter:

- they control the sector risk overlay attached to each borrower
- they influence the realism of synthetic margin, liquidity, and working-capital assumptions
- they provide the base industry environment before any borrower-specific modelling starts

## What comes from repo 8

Source repo:

- `../8. Financial Statement Analysis — Commercial Cash Flow Lending`

Files used here:

- `outputs/tables/public_company_analysis/public_listed_company_benchmarks.csv`
- `outputs/tables/public_company_analysis/public_transaction_benchmarks.csv`
- `outputs/tables/public_company_analysis/public_invoice_benchmarks.csv`
- `outputs/tables/public_company_analysis/public_listed_company_financials_standardized.csv`

### Listed-company benchmarks

Key metrics used:

- `listed_ebitda_margin_median`
- `listed_debt_to_ebitda_median`
- `listed_current_ratio_median`
- `listed_company_count`
- `listed_revenue_median`

What they do in repo `1.2`:

- anchor industry-level profitability
- anchor leverage
- anchor liquidity
- show how much public-company support each industry benchmark has

### Transaction-conduct proxy benchmarks

Key metrics used:

- `tx_credit_turnover_cv_median`
- `tx_failed_event_rate_median`
- `tx_cash_advance_rate_median`

Other stored metrics:

- `transaction_account_count`
- `transaction_record_count`
- `tx_avg_monthly_credits_median`
- `tx_avg_monthly_debits_median`
- `tx_months_negative_net_cash_median`

What they do in repo `1.2`:

- set the volatility of synthetic statement inflows
- influence simulated failed-payment behaviour
- influence simulated business-card cash-advance behaviour

Important limitation:

- these are public-company proxy benchmarks, not raw bank transaction histories

### Invoice and receivables proxy benchmarks

Key metrics used:

- `invoice_payment_delay_median_days`
- `invoice_top_customer_concentration_pct`
- `invoice_severe_late_rate_90dpd`
- `invoice_dilution_proxy_rate`

Other stored metrics:

- `invoice_record_count`
- `invoice_customer_count`
- `invoice_amount_median`
- `invoice_late_payment_rate`

What they do in repo `1.2`:

- influence debtor-days assumptions in synthetic borrower financials
- anchor debtor concentration in receivables finance
- anchor severe arrears assumptions for the debtor book
- anchor dilution assumptions for borrowing-base style lending

Important limitation:

- these are public-company receivables proxy benchmarks, not raw invoice ledgers

## What this repo creates itself

Repo `1.2` creates the bank-only borrower layer that is not publicly available:

- synthetic SME financial statements
- synthetic bureau records
- synthetic bank-statement conduct summaries
- synthetic product-underwriting fields
- synthetic default labels for PD modelling

Key files:

- `data/raw/cashflow_lending_financials.csv`
- `data/raw/credit_bureau_reports.csv`
- `data/raw/bank_statement_monthly.csv`
- `data/raw/bank_statement_summary.csv`
- `data/raw/product_underwriting_data.csv`

This is why the repo is still a portfolio model rather than a production model. The scorecard is real in structure, but the borrower-level target data is synthetic.

## How the model is built

### 1. Public benchmark assembly

The repo first builds one merged benchmark table:

- `data/processed/public_industry_profiles.csv`

That file combines:

- repo `9` industry and macro overlays
- repo `8` listed-company financial benchmarks
- repo `8` conduct proxy benchmarks
- repo `8` receivables proxy benchmarks

### 2. Synthetic borrower generation

Using those benchmark layers, the repo generates:

- borrower financials
- bureau signals
- statement conduct
- product-specific underwriting fields

This is where public benchmarks shape the synthetic distributions.

### 3. Product eligibility

The repo applies policy-style product rules such as:

- years trading
- GST history
- turnover thresholds
- conduct expectations
- debtor-book quality
- trade-document controls
- contingent-facility conditions

Output:

- `data/processed/product_eligibility_matrix.csv`

### 4. Feature engineering

The repo builds serviceability, leverage, liquidity, conduct, and structure features.

Output:

- `data/processed/cashflow_lending_feature_dataset.csv`

### 5. Scorecard fitting

The repo then:

- bins variables into WOE
- measures IV
- fits logistic regression
- converts PD into score and bands

Outputs:

- `output/scorecard_outputs/01_iv_summary.csv`
- `output/scorecard_outputs/02_woe_table.csv`
- `output/scorecard_outputs/03_scorecard_coefficients.csv`
- `output/scorecard_outputs/04_scorecard_points.csv`
- `output/scorecard_outputs/07_scorecard_metadata.csv`

### 6. Policy and monitoring outputs

The final scored portfolio is turned into:

- decisions
- review rules
- conditions
- pricing overlays
- monitoring tables

Outputs:

- `output/policy_overlay.csv`
- `output/portfolio_summary.md`
- `output/scorecard_outputs/08_calibration_table.csv`
- `output/scorecard_outputs/09_score_band_summary.csv`
- `output/scorecard_outputs/10_monitoring_psi.csv`
- `output/scorecard_outputs/11_test_deciles.csv`
- `output/scorecard_outputs/12_test_ks.csv`

## Best files to open

If you want to understand the project quickly, open these in order:

1. `README.md`
2. `data/processed/public_data_provenance.csv`
3. `data/processed/public_industry_profiles.csv`
4. `data/processed/public_listed_company_benchmarks.csv`
5. `data/processed/public_transaction_benchmarks.csv`
6. `data/processed/public_invoice_benchmarks.csv`
7. `output/scorecard_outputs/07_scorecard_metadata.csv`
8. `output/policy_overlay.csv`
9. `output/portfolio_summary.md`

## What to say in an interview

The strongest summary is:

- repo `9` gives the sector risk environment
- repo `8` gives public-company benchmark anchors
- repo `1.2` uses those public anchors to calibrate a synthetic SME cash-flow lending portfolio
- the PD model itself is built here with WOE, IV, logistic regression, policy overlays, and monitoring outputs

That is the correct description of what is public, what is synthetic, and where each part of the workflow lives.
