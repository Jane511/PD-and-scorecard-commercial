# Commercial Credit Scorecard (PD Model) Project

This repository is the borrower PD and scorecard layer in the public commercial credit-risk stack. It uses borrower financial analysis outputs, industry context, and synthetic lending data to produce facility-level PDs, score bands, and policy-style decision tables for both bank-aligned risk assessment and practical origination decisioning workflows.

## What this repo is

This project shows how a commercial credit scorecard can be structured for both portfolio risk review and real-world underwriting discussion. It is designed as a public portfolio project, so the logic is explainable, the workflows are modular, and the data is synthetic rather than confidential lender data.

## Where it sits in the stack

Upstream inputs:
- `financial-statement-analysis`
- `industry-analysis`
  - required canonical exports:
    - `data/exports/industry_risk_scores.parquet`
    - `data/exports/macro_regime_flags.parquet`
    - `data/exports/downturn_overlay_table.parquet`

Downstream consumers:
- `LGD-commercial`
- `expected-loss-engine-commercial`
- `stress-testing-commercial`
- `RAROC-pricing-and-return-hurdle`
- `RWA-capital-commercial`

## How this is used in practice

This project can be applied in:

### Bank / Institutional context

- PD estimation for internal risk grading, capital-style frameworks, and stress testing
- Portfolio risk assessment and borrower segmentation
- Credit risk monitoring and structured risk review using score bands and policy outputs

### Non-bank / Fintech context

- Credit scorecards for originations decisioning and approval strategy
- Approve / decline / refer decision support using score bands and policy thresholds
- Ongoing performance monitoring and re-segmentation of booked customers

## Key inputs

- borrower financial outputs from `financial-statement-analysis`
- industry and macro overlay context from `industry-analysis` canonical parquet exports:
  - `data/exports/industry_risk_scores.parquet`
  - `data/exports/macro_regime_flags.parquet`
  - `data/exports/downturn_overlay_table.parquet`
- synthetic borrower, facility, and policy-threshold inputs staged under `data/`

## Key outputs

- `outputs/tables/pd_model_output.csv`
- `outputs/tables/borrower_grade_summary.csv`
- `outputs/tables/policy_decisions.csv`
- `outputs/tables/score_band_output.csv`
- `outputs/tables/pipeline_validation_report.csv`

## Repo structure

- `data/`: raw, interim, processed, and external portfolio inputs
- `src/`: reusable PD, scorecard, and pipeline modules
- `scripts/`: wrapper scripts for pipeline execution
- `docs/`: methodology, assumptions, data dictionary, and validation notes
- `notebooks/`: walkthrough notebooks for reviewer context
- `output/`: legacy scorecard and PD-final export paths retained for compatibility with existing modules
- `outputs/`: exported tables, reports, and sample artifacts
- `tests/`: validation and regression checks

## How to run

```powershell
python -m src.run_pipeline
```

Or:

```powershell
python scripts/run_demo_pipeline.py
```

## Limitations / Demo-Only Note

- All data is synthetic and included for demonstration only.
- Score thresholds, overlays, and decision rules are simplified portfolio assumptions rather than production credit policy.
- The repo is intended to show modelling workflow and documentation quality, not to represent a live bank rating engine.
