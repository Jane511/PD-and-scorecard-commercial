# Commercial Lending PD - Cash Flow and Property-Backed

## Business Problem

This repository now demonstrates two separate commercial-lending PD streams:

- an SME cash-flow lending scorecard for unsecured and working-capital products
- a property-backed / development lending scorecard built on synthetic facility-level loans

Both streams finish with facility-level PD Final Layers and one combined EL-facing PD export.

## Product Scope

- cash-flow stream:
  - business overdrafts
  - working capital revolvers
  - unsecured term loans
  - invoice finance
  - trade receivables finance
  - trade finance lines
  - business credit cards
  - bank guarantees
- property-backed stream:
  - property investment loans
  - bridging loans
  - development facilities
- out of scope:
  - home lending
  - land subdivision

## Data Used

- public industry, macro, and property-reference overlays from sibling repo `../9.Industry Risk Analysis_Australia/`
- public listed-company, transaction, and invoice benchmarks from sibling repo `../8. Financial Statement Analysis — Commercial Cash Flow Lending/`
- synthetic borrower financials, bureau fields, bank-statement conduct, and product-underwriting inputs for the cash-flow stream in `data/raw/`
- synthetic facility-level property-backed loans and public property reference joins in `data/processed/`
- merged processed datasets in `data/processed/`, including `cashflow_lending_feature_dataset.csv`, `property_backed_facility_dataset.csv`, and `property_reference_segments.csv`

## Model Logic

1. Load public benchmark layers from repos `8` and `9`.
2. Build the SME cash-flow stream with synthetic borrower financials, conduct, underwriting, and policy overlays.
3. Build the property-backed stream with synthetic facility-level loans.
4. Use repo `9` property-reference outputs to define region risk bands, market-softness / construction-cycle bands, macro arrears environment, and simple downturn overlays.
5. Build WOE and IV transformations for each stream separately.
6. Fit separate logistic-regression PD scorecards for cash-flow and property-backed lending.
7. Build a cash-flow PD Final Layer.
8. Build a property PD Final Layer plus scenario-ready downturn overlays.
9. Combine both streams into one EL-facing `facility_pd_final_combined.csv`.

## Outputs

- narrative overview in `PROJECT_OVERVIEW.md`
- combined portfolio summary in `output/portfolio_summary.md`
- cash-flow policy and scorecard outputs in `output/policy_overlay.csv` and `output/scorecard_outputs/`
- property-backed scorecard outputs in `output/property_pd/`
- property reference snapshots and provenance in `data/processed/property_reference_*.csv` plus `data/processed/property_*_reference.csv`
- PD final-layer exports in `output/pd_final/facility_pd_final.csv`, `output/pd_final/pd_final_summary_by_product.csv`, `output/pd_final/pd_final_validation_checks.csv`, `output/pd_final/property_pd_final.csv`, `output/pd_final/property_pd_final_summary_by_product.csv`, `output/pd_final/property_pd_final_validation_checks.csv`, `output/pd_final/property_pd_downturn_scenarios.csv`, and `output/pd_final/facility_pd_final_combined.csv`

## Limitations

- public data is used as a calibration layer, not as a substitute for unavailable bank-internal borrower history
- cash-flow borrower data and property facility-level loan data remain synthetic
- listed-company, transaction, and invoice benchmarks are proxies rather than raw bank ledgers
- the property reference layer currently uses national segment-level public joins rather than state-level loan-by-loan geography

## Sample Outputs

| Metric | Value |
| --- | --- |
| Cash-flow borrowers scored | 720 |
| Property facilities scored | 360 |
| Combined EL-facing facilities | 1,080 |
| Cash-flow product families covered | 6 |
| Property product types covered | 3 |

- Quick-review files: `output/portfolio_summary.md`, `output/property_pd/property_portfolio_summary.md`, `output/pd_final/pd_final_summary_by_product.csv`, `output/pd_final/property_pd_final_summary_by_product.csv`, and `output/pd_final/facility_pd_final_combined.csv`
- Local notebooks, rendered PDFs, and Jupyter runtime folders are treated as disposable scratch artifacts rather than maintained source files.

## What this repo does

The pipeline now runs two separate commercial-lending PD streams and then combines them:

1. Load public benchmark and property-reference layers from sibling repos.
2. Generate the synthetic SME borrower portfolio for cash-flow lending.
3. Generate the synthetic facility-level property-backed portfolio.
4. Fit separate PD scorecards for each stream.
5. Build a final facility-level PD for each stream.
6. Export one combined PD file for downstream Expected Loss use.

Main run command:

```bash
python scripts/run_pipeline.py
```

Standalone cash-flow final-layer rebuild:

```bash
python -m src.pd_final
```

The detailed sections below still describe the original cash-flow benchmark plumbing first, then the new property-backed additions.

## Property reference outputs consumed from repo 9

Sibling repo:

- `../9.Industry Risk Analysis_Australia/`

Files used by the property-backed stream:

- `data/output/region_risk/region_risk_table.csv`
- `data/output/property_cycle/property_cycle_table.csv`
- `data/output/arrears_environment/base_arrears_environment.csv`
- `data/output/downturn_overlays/property_downturn_overlays.csv`

How they are used here:

- `region_risk_table.csv` anchors `region_risk_score` and `region_risk_band`
- `property_cycle_table.csv` anchors `cycle_stage`, `market_softness_score`, and `market_softness_band`
- `base_arrears_environment.csv` anchors the macro arrears backdrop used in synthetic arrears and watchlist generation
- `property_downturn_overlays.csv` feeds the simple scenario multipliers exported to `output/pd_final/property_pd_downturn_scenarios.csv`

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
- `output/pd_final/facility_pd_final.csv`
- `output/pd_final/pd_final_summary_by_product.csv`
- `output/pd_final/pd_final_validation_checks.csv`
- `output/property_pd/07_scorecard_metadata.csv`
- `output/pd_final/property_pd_final.csv`
- `output/pd_final/property_pd_final_summary_by_product.csv`
- `output/pd_final/property_pd_final_validation_checks.csv`
- `output/pd_final/property_pd_downturn_scenarios.csv`
- `output/pd_final/facility_pd_final_combined.csv`
- `output/portfolio_summary.md`

## PD Final Layer

The repository now includes two simplified PD final layers for downstream Expected Loss usage.

Cash-flow final layer:

- raw `pd_12m_raw` from the logistic scorecard
- watchlist uplift based on adverse bureau, conduct, and policy signals
- arrears uplift based on the strongest available delinquency proxy in the synthetic conduct layer
- policy override uplift for conditional or outside-criteria cases
- a calibration scalar to create the business-ready `pd_final`

Property-backed final layer:

- raw `pd_12m_raw` from the property logistic scorecard
- LVR overlay
- completion-stage overlay
- exit-risk overlay
- watchlist overlay
- scenario-ready downturn multipliers sourced from repo `9`

The main EL-facing outputs are:

- `output/pd_final/facility_pd_final.csv`
- `output/pd_final/pd_final_summary_by_product.csv`
- `output/pd_final/pd_final_validation_checks.csv`
- `output/pd_final/property_pd_final.csv`
- `output/pd_final/property_pd_final_summary_by_product.csv`
- `output/pd_final/property_pd_final_validation_checks.csv`
- `output/pd_final/property_pd_downturn_scenarios.csv`
- `output/pd_final/facility_pd_final_combined.csv`

The combined file is ready for use in an EL engine:

```python
expected_loss = pd_final * lgd_final * ead
```

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
│   ├── property_pd/
│   ├── pd_final/
│   └── scorecard_outputs/
├── scripts/
│   └── run_pipeline.py
├── src/
│   ├── pd_final.py
│   ├── pd_final_property.py
│   ├── pd_output_merge.py
│   ├── property_data.py
│   ├── property_model.py
│   └── property_reference.py
└── tests/
```

The maintained source tree is `scripts/`, `src/`, `tests/`, `README.md`, and `PROJECT_OVERVIEW.md`. Local notebook scratch work and rendered PDF drafts are intentionally kept out of the tracked repo.
