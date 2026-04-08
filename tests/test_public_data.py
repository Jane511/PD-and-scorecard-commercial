from pathlib import Path
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.public_data as public_data


def test_load_listed_company_financials_prefers_precomputed_outputs(monkeypatch):
    fixture_dir = ROOT / "tests" / "fixtures" / "public_company_analysis"
    monkeypatch.setattr(public_data, "_discover_precomputed_listed_company_output_dirs", lambda: [fixture_dir])

    standard_df, benchmark_df, provenance_df = public_data.load_listed_company_financials()

    assert len(standard_df) == 2
    assert set(standard_df["company_name"]) == {"Fixture Export Limited"}
    assert set(benchmark_df["industry"]) == {"Wholesale Trade"}
    assert benchmark_df.iloc[0]["listed_company_count"] == 1
    assert benchmark_df.iloc[0]["listed_benchmark_source"] == "Financial Statement Analysis public company outputs"
    assert provenance_df.iloc[0]["dataset_group"] == "public_listed_precomputed"


def test_load_transaction_benchmarks_prefers_precomputed_outputs(monkeypatch):
    fixture_dir = ROOT / "tests" / "fixtures" / "public_company_analysis"
    monkeypatch.setattr(public_data, "_discover_precomputed_transaction_output_dirs", lambda: [fixture_dir])

    standard_df, benchmark_df, provenance_df = public_data.load_transaction_benchmarks()

    assert standard_df.empty
    assert set(benchmark_df["industry"]) == {"Wholesale Trade"}
    assert benchmark_df.iloc[0]["transaction_account_count"] == 1
    assert benchmark_df.iloc[0]["transaction_benchmark_source"] == "Financial Statement Analysis public company proxy conduct benchmarks"
    assert provenance_df.iloc[0]["dataset_group"] == "public_proxy_precomputed"


def test_load_invoice_benchmarks_prefers_precomputed_outputs(monkeypatch):
    fixture_dir = ROOT / "tests" / "fixtures" / "public_company_analysis"
    monkeypatch.setattr(public_data, "_discover_precomputed_invoice_output_dirs", lambda: [fixture_dir])

    standard_df, benchmark_df, provenance_df = public_data.load_invoice_benchmarks()

    assert standard_df.empty
    assert set(benchmark_df["industry"]) == {"Wholesale Trade"}
    assert benchmark_df.iloc[0]["invoice_customer_count"] == 24
    assert benchmark_df.iloc[0]["invoice_benchmark_source"] == "Financial Statement Analysis public company proxy receivables benchmarks"
    assert provenance_df.iloc[0]["dataset_group"] == "public_proxy_precomputed"


def test_load_listed_company_financials_accepts_financial_statement_analysis_schema(monkeypatch):
    fixture_dir = ROOT / "tests" / "fixtures" / "listed_company_reports"
    monkeypatch.setattr(public_data, "_discover_precomputed_listed_company_output_dirs", lambda: [])
    monkeypatch.setattr(public_data, "LISTED_COMPANY_DIR", fixture_dir)

    standard_df, benchmark_df, provenance_df = public_data.load_listed_company_financials()

    metcash_df = standard_df[
        standard_df["source_file"] == "metcash_limited_financial_statement_analysis_extract.csv"
    ].reset_index(drop=True)

    assert len(metcash_df) == 2
    assert set(metcash_df["company_name"]) == {"Metcash Limited"}
    assert set(metcash_df["industry"]) == {"Wholesale Trade"}
    assert list(metcash_df["period"]) == ["2023", "2024"]

    benchmark_row = benchmark_df.loc[benchmark_df["industry"] == "Wholesale Trade"].iloc[0]
    assert benchmark_row["listed_company_count"] == 1

    expected_debt_to_ebitda = pd.Series(
        [
            1411000000 / 688300000,
            1890800000 / 747800000,
        ]
    ).median()
    assert benchmark_row["listed_debt_to_ebitda_median"] == pytest.approx(expected_debt_to_ebitda)

    metcash_provenance = provenance_df.loc[
        provenance_df["source_path"].astype(str).str.contains("metcash_limited_financial_statement_analysis_extract.csv", regex=False)
    ].iloc[0]
    assert metcash_provenance["status"] == "loaded"
