# Commercial PD & Scorecard Project

This repository is the Probability of Default and borrower scorecard layer in the commercial credit-risk stack. It uses borrower financial analysis outputs, industry context, and synthetic commercial lending data to produce facility-level PDs, score bands, and policy-style decision tables. The resulting outputs feed downstream expected loss, monitoring, and pricing workflows across the commercial portfolio.

## What this repo is

This project shows how a bank-style commercial borrower-rating engine can be structured for portfolio review and underwriting discussion. It is designed as a public portfolio project, so the logic is explainable, the workflows are modular, and the data is synthetic rather than confidential bank data.

## Where it sits in the stack

Upstream inputs:
- `financial-statement-analysis`
- `industry-analysis`

Downstream consumers:
- `expected-loss-engine-commercial`
- `portfolio-monitor-commercial` (planned downstream repo; not yet published on the public portfolio)
- `RAROC-pricing-and-return-hurdle`

Some downstream modules are planned but not yet published on the public portfolio.

## Key outputs

- `outputs/tables/pd_model_output.csv`
- `outputs/tables/borrower_grade_summary.csv`
- `outputs/tables/policy_decisions.csv`
- `outputs/tables/score_band_output.csv`
- `outputs/tables/pipeline_validation_report.csv`

## Repo structure

- `data/`: raw, interim, processed, and external portfolio inputs
- `output/`: retained legacy scorecard, PD-final, and HTML review artifacts used by earlier portfolio outputs
- `src/`: reusable PD, scorecard, and pipeline modules
- `scripts/`: wrapper scripts for pipeline execution
- `docs/`: methodology, assumptions, data dictionary, and validation notes
- `notebooks/`: walkthrough notebooks for reviewer context
- `outputs/`: exported tables, reports, and sample artifacts
- `tests/`: validation and regression checks

## How to run

```powershell
python -m src.codex_run_pipeline
```

Or:

```powershell
python scripts/run_codex_pipeline.py
```

## Limitations / Demo-Only Note

- All data is synthetic and included for demonstration only.
- Score thresholds, overlays, and decision rules are simplified portfolio assumptions rather than production credit policy.
- The repo is intended to show modelling workflow and documentation quality, not to represent a live bank rating engine.
