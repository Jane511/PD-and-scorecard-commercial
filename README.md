# Commercial Probability of Default & Scorecard Project

This repository is the borrower PD and scorecard layer in the public commercial credit-risk stack. It uses borrower financial analysis outputs, industry context, and synthetic lending data to produce facility-level PDs, score bands, and policy-style decision tables for downstream loss, monitoring, and pricing workflows.

## What this repo is

This project shows how a bank-style commercial borrower-rating engine can be structured for portfolio review and underwriting discussion. It is designed as a public portfolio project, so the logic is explainable, the workflows are modular, and the data is synthetic rather than confidential bank data.

## Where it sits in the stack

This repo sits after financial statement analysis and industry overlay work, and before expected loss, monitoring, and pricing in the public commercial stack.

## Key inputs

- borrower financial outputs from `financial-statement-analysis`
- industry and macro overlay context from `industry-analysis`
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
