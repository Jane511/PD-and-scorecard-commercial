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


def test_load_public_industry_overlays_prefers_canonical_parquet(monkeypatch, tmp_path):
    upstream_repo = tmp_path / "industry-analysis"
    scores_path = upstream_repo / "data" / "exports" / "industry_risk_scores.parquet"
    macro_path = upstream_repo / "data" / "exports" / "macro_regime_flags.parquet"
    downturn_path = upstream_repo / "data" / "exports" / "downturn_overlay_table.parquet"
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    scores_path.touch()
    macro_path.touch()
    downturn_path.touch()

    monkeypatch.setattr(public_data, "_discover_industry_analysis_source_dirs", lambda: [upstream_repo])

    def fake_read_parquet(path):
        if Path(path) == scores_path:
            return pd.DataFrame(
                [
                    {
                        "industry_name": "Wholesale Trade",
                        "classification_score": 3.10,
                        "macro_score": 2.80,
                        "industry_risk_score": 2.95,
                        "ebitda_margin_pct_latest": 11.2,
                    }
                ]
            )
        if Path(path) == macro_path:
            return pd.DataFrame(
                [
                    {
                        "cash_rate_pct": 4.10,
                        "employment_yoy_growth_pct": 1.3,
                        "demand_yoy_growth_pct": 0.8,
                    }
                ]
            )
        raise AssertionError(f"Unexpected parquet path requested: {path}")

    monkeypatch.setattr(public_data.pd, "read_parquet", fake_read_parquet)

    overlay_df, provenance_df = public_data.load_public_industry_overlays()
    wholesale_row = overlay_df.loc[overlay_df["industry"] == "Wholesale Trade"].iloc[0]

    assert wholesale_row["final_industry_risk_score"] == pytest.approx(2.95)
    assert wholesale_row["risk_level"] == "Elevated"
    assert wholesale_row["public_cash_rate_latest_pct"] == pytest.approx(4.10)
    assert wholesale_row["industry_overlay_source"] == "industry-analysis canonical exports"
    assert provenance_df.iloc[0]["dataset_group"] == "industry_analysis_canonical"
    assert provenance_df.iloc[0]["status"] == "loaded"


def test_load_public_industry_overlays_fails_when_required_file_missing(monkeypatch, tmp_path):
    upstream_repo = tmp_path / "industry-analysis"
    scores_path = upstream_repo / "data" / "exports" / "industry_risk_scores.parquet"
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    scores_path.touch()

    monkeypatch.setattr(public_data, "_discover_industry_analysis_source_dirs", lambda: [upstream_repo])

    with pytest.raises(FileNotFoundError):
        public_data.load_public_industry_overlays()


def test_load_public_industry_overlays_fails_when_required_columns_missing(monkeypatch, tmp_path):
    upstream_repo = tmp_path / "industry-analysis"
    scores_path = upstream_repo / "data" / "exports" / "industry_risk_scores.parquet"
    macro_path = upstream_repo / "data" / "exports" / "macro_regime_flags.parquet"
    downturn_path = upstream_repo / "data" / "exports" / "downturn_overlay_table.parquet"
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    scores_path.touch()
    macro_path.touch()
    downturn_path.touch()

    monkeypatch.setattr(public_data, "_discover_industry_analysis_source_dirs", lambda: [upstream_repo])

    def fake_read_parquet(path):
        if Path(path) == scores_path:
            return pd.DataFrame([{"industry_name": "Wholesale Trade"}])
        if Path(path) == macro_path:
            return pd.DataFrame([{"cash_rate_pct": 4.00}])
        raise AssertionError(f"Unexpected parquet path requested: {path}")

    monkeypatch.setattr(public_data.pd, "read_parquet", fake_read_parquet)

    with pytest.raises(ValueError):
        public_data.load_public_industry_overlays()
