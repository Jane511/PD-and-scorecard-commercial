from pathlib import Path

import numpy as np
import pandas as pd

from .config import INDUSTRY_RISK_SOURCE_DIRS, INDUSTRY_SETTINGS, PUBLIC_INPUT_DIR, ROOT


LISTED_COMPANY_DIR = PUBLIC_INPUT_DIR / "listed_company_reports"
KAGGLE_TRANSACTIONS_DIR = PUBLIC_INPUT_DIR / "kaggle_transactions"
KAGGLE_INVOICES_DIR = PUBLIC_INPUT_DIR / "kaggle_invoices"

_LISTED_STANDARD_COLUMNS = [
    "source_file",
    "company_name",
    "industry",
    "period",
    "revenue",
    "ebitda",
    "ebit",
    "operating_cash_flow",
    "current_assets",
    "current_liabilities",
    "total_debt",
    "interest_expense",
    "cash",
    "debtors",
    "inventory",
    "net_worth",
]

_LISTED_BENCHMARK_COLUMNS = [
    "industry",
    "listed_company_count",
    "listed_revenue_median",
    "listed_ebitda_margin_median",
    "listed_ocf_margin_median",
    "listed_current_ratio_median",
    "listed_debt_to_ebitda_median",
    "listed_benchmark_source",
]

_TRANSACTION_STANDARD_COLUMNS = [
    "source_file",
    "public_account_id",
    "industry",
    "transaction_date",
    "amount",
    "credit_amount",
    "debit_amount",
    "balance",
    "event_failed_flag",
    "cash_advance_flag",
]

_TRANSACTION_BENCHMARK_COLUMNS = [
    "industry",
    "transaction_account_count",
    "transaction_record_count",
    "tx_avg_monthly_credits_median",
    "tx_avg_monthly_debits_median",
    "tx_credit_turnover_cv_median",
    "tx_months_negative_net_cash_median",
    "tx_failed_event_rate_median",
    "tx_cash_advance_rate_median",
    "transaction_benchmark_source",
]

_INVOICE_STANDARD_COLUMNS = [
    "source_file",
    "invoice_id",
    "customer_id",
    "industry",
    "invoice_amount",
    "due_date",
    "payment_date",
    "payment_delay_days",
    "late_payment_flag",
    "severe_late_payment_90dpd_flag",
    "dilution_proxy_flag",
]

_INVOICE_BENCHMARK_COLUMNS = [
    "industry",
    "invoice_record_count",
    "invoice_customer_count",
    "invoice_amount_median",
    "invoice_payment_delay_median_days",
    "invoice_late_payment_rate",
    "invoice_severe_late_rate_90dpd",
    "invoice_top_customer_concentration_pct",
    "invoice_dilution_proxy_rate",
    "invoice_benchmark_source",
]

_CANONICAL_INDUSTRY_MAP = {
    "accommodation and food services": "Accommodation and Food Services",
    "agriculture forestry and fishing": "Agriculture, Forestry and Fishing",
    "construction": "Construction - Trade Services",
    "construction trade services": "Construction - Trade Services",
    "construction engineering and mining": "Construction - Trade Services",
    "health care": "Health Care and Social Assistance",
    "health care and social assistance": "Health Care and Social Assistance",
    "manufacturing": "Manufacturing",
    "professional scientific and technical services": "Professional, Scientific and Technical Services",
    "retail": "Retail Trade",
    "retail trade": "Retail Trade",
    "transport and logistics": "Transport, Postal and Warehousing",
    "transport logistics": "Transport, Postal and Warehousing",
    "transport postal and warehousing": "Transport, Postal and Warehousing",
    "wholesale and distribution": "Wholesale Trade",
    "wholesale trade": "Wholesale Trade",
}


def _normalise_text(value) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip().lower()
    for old, new in (
        ("&", " and "),
        ("-", " "),
        ("/", " "),
        (",", " "),
    ):
        text = text.replace(old, new)
    return " ".join(text.split())


def normalise_industry_name(value) -> str | None:
    normalised = _normalise_text(value)
    if not normalised:
        return None
    return _CANONICAL_INDUSTRY_MAP.get(normalised)


def _coalesce_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    normalised = {_normalise_text(column): column for column in df.columns}
    for candidate in candidates:
        found = normalised.get(_normalise_text(candidate))
        if found:
            return found
    return None


def _read_csv_files(directory: Path) -> list[tuple[Path, pd.DataFrame]]:
    if not directory.exists():
        return []
    frames: list[tuple[Path, pd.DataFrame]] = []
    for path in sorted(directory.glob("*.csv")):
        if path.name.startswith("template_"):
            continue
        try:
            frames.append((path, pd.read_csv(path)))
        except Exception:
            continue
    return frames


def _empty(columns: list[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def _discover_precomputed_public_company_output_dirs() -> list[Path]:
    output_dirs: list[Path] = []
    for pattern in (
        "8. Financial Statement Analysis*",
        "Financial Statement Analysis*",
        "Financial-Statement-Analysis*",
    ):
        for repo_dir in sorted(ROOT.parent.glob(pattern)):
            output_dir = repo_dir / "outputs" / "tables" / "public_company_analysis"
            if output_dir not in output_dirs:
                output_dirs.append(output_dir)
    return output_dirs


def _discover_precomputed_listed_company_output_dirs() -> list[Path]:
    return _discover_precomputed_public_company_output_dirs()


def _discover_precomputed_transaction_output_dirs() -> list[Path]:
    return _discover_precomputed_public_company_output_dirs()


def _discover_precomputed_invoice_output_dirs() -> list[Path]:
    return _discover_precomputed_public_company_output_dirs()


def _format_listed_standard_df(df: pd.DataFrame) -> pd.DataFrame:
    formatted = df.copy()
    for column in _LISTED_STANDARD_COLUMNS:
        if column not in formatted.columns:
            formatted[column] = np.nan
    formatted["industry"] = formatted["industry"].map(normalise_industry_name)
    formatted = formatted.dropna(subset=["industry", "revenue"])
    return formatted[_LISTED_STANDARD_COLUMNS].reset_index(drop=True)


def _build_listed_company_benchmarks(
    standard_df: pd.DataFrame,
    source_label: str,
) -> pd.DataFrame:
    if standard_df.empty:
        return _empty(_LISTED_BENCHMARK_COLUMNS)

    benchmark_base = standard_df.copy()
    benchmark_base["listed_ebitda_margin"] = benchmark_base["ebitda"] / benchmark_base["revenue"].replace(0, np.nan)
    benchmark_base["listed_ocf_margin"] = benchmark_base["operating_cash_flow"] / benchmark_base["revenue"].replace(0, np.nan)
    benchmark_base["listed_current_ratio"] = benchmark_base["current_assets"] / benchmark_base["current_liabilities"].replace(0, np.nan)
    benchmark_base["listed_debt_to_ebitda"] = benchmark_base["total_debt"] / benchmark_base["ebitda"].replace(0, np.nan)

    benchmark_df = (
        benchmark_base.groupby("industry", as_index=False)
        .agg(
            listed_company_count=("company_name", "nunique"),
            listed_revenue_median=("revenue", "median"),
            listed_ebitda_margin_median=("listed_ebitda_margin", "median"),
            listed_ocf_margin_median=("listed_ocf_margin", "median"),
            listed_current_ratio_median=("listed_current_ratio", "median"),
            listed_debt_to_ebitda_median=("listed_debt_to_ebitda", "median"),
        )
        .sort_values("industry")
        .reset_index(drop=True)
    )
    benchmark_df["listed_benchmark_source"] = source_label
    return benchmark_df[_LISTED_BENCHMARK_COLUMNS]


def _format_benchmark_df(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    formatted = df.copy()
    for column in columns:
        if column not in formatted.columns:
            formatted[column] = np.nan
    formatted["industry"] = formatted["industry"].map(normalise_industry_name)
    formatted = formatted.dropna(subset=["industry"])
    return formatted[columns].reset_index(drop=True)


def _load_precomputed_listed_company_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame] | None:
    for output_dir in _discover_precomputed_listed_company_output_dirs():
        standard_path = output_dir / "public_listed_company_financials_standardized.csv"
        benchmark_path = output_dir / "public_listed_company_benchmarks.csv"
        if not benchmark_path.exists():
            continue

        try:
            benchmark_df = pd.read_csv(benchmark_path)
        except Exception:
            continue

        for column in _LISTED_BENCHMARK_COLUMNS:
            if column not in benchmark_df.columns:
                benchmark_df[column] = np.nan
        benchmark_df["industry"] = benchmark_df["industry"].map(normalise_industry_name)
        benchmark_df = benchmark_df.dropna(subset=["industry"])[_LISTED_BENCHMARK_COLUMNS].reset_index(drop=True)
        if benchmark_df.empty:
            continue

        standard_df = _empty(_LISTED_STANDARD_COLUMNS)
        if standard_path.exists():
            try:
                standard_df = _format_listed_standard_df(pd.read_csv(standard_path))
            except Exception:
                standard_df = _empty(_LISTED_STANDARD_COLUMNS)

        provenance_df = pd.DataFrame(
            [
                {
                    "dataset_name": "listed_company_financials",
                    "dataset_group": "public_listed_precomputed",
                    "status": "loaded",
                    "records_loaded": int(len(standard_df) if not standard_df.empty else len(benchmark_df)),
                    "source_path": str(benchmark_path),
                    "notes": "Loaded precomputed listed-company benchmark exports from the sibling financial-statement-analysis repository.",
                }
            ]
        )
        return standard_df, benchmark_df, provenance_df

    return None


def _load_precomputed_transaction_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame] | None:
    for output_dir in _discover_precomputed_transaction_output_dirs():
        benchmark_path = output_dir / "public_transaction_benchmarks.csv"
        if not benchmark_path.exists():
            continue

        try:
            benchmark_df = _format_benchmark_df(pd.read_csv(benchmark_path), _TRANSACTION_BENCHMARK_COLUMNS)
        except Exception:
            continue
        if benchmark_df.empty:
            continue

        provenance_df = pd.DataFrame(
            [
                {
                    "dataset_name": "transaction_benchmarks",
                    "dataset_group": "public_proxy_precomputed",
                    "status": "loaded",
                    "records_loaded": int(len(benchmark_df)),
                    "source_path": str(benchmark_path),
                    "notes": "Loaded precomputed transaction benchmark proxies from the sibling financial-statement-analysis repository.",
                }
            ]
        )
        return _empty(_TRANSACTION_STANDARD_COLUMNS), benchmark_df, provenance_df

    return None


def _load_precomputed_invoice_outputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame] | None:
    for output_dir in _discover_precomputed_invoice_output_dirs():
        benchmark_path = output_dir / "public_invoice_benchmarks.csv"
        if not benchmark_path.exists():
            continue

        try:
            benchmark_df = _format_benchmark_df(pd.read_csv(benchmark_path), _INVOICE_BENCHMARK_COLUMNS)
        except Exception:
            continue
        if benchmark_df.empty:
            continue

        provenance_df = pd.DataFrame(
            [
                {
                    "dataset_name": "invoice_benchmarks",
                    "dataset_group": "public_proxy_precomputed",
                    "status": "loaded",
                    "records_loaded": int(len(benchmark_df)),
                    "source_path": str(benchmark_path),
                    "notes": "Loaded precomputed invoice benchmark proxies from the sibling financial-statement-analysis repository.",
                }
            ]
        )
        return _empty(_INVOICE_STANDARD_COLUMNS), benchmark_df, provenance_df

    return None


def _default_industry_overlay() -> pd.DataFrame:
    rows = []
    for industry, settings in INDUSTRY_SETTINGS.items():
        rows.append(
            {
                "industry": industry,
                "classification_risk_score": settings["classification_risk_score"],
                "macro_risk_score": settings["macro_risk_score"],
                "final_industry_risk_score": settings["final_industry_risk_score"],
                "risk_level": settings["risk_level"],
                "public_ebitda_margin_pct_latest": np.nan,
                "public_inventory_days_est": np.nan,
                "public_employment_yoy_growth_pct": np.nan,
                "public_demand_yoy_growth_pct": np.nan,
                "public_cash_rate_latest_pct": np.nan,
                "industry_overlay_source": "Fallback config",
                "industry_overlay_path": "",
            }
        )
    return pd.DataFrame(rows)


def load_public_industry_overlays() -> tuple[pd.DataFrame, pd.DataFrame]:
    overlay = _default_industry_overlay()
    provenance_rows = []

    for repo_dir in INDUSTRY_RISK_SOURCE_DIRS:
        base_path = repo_dir / "output" / "tables" / "industry_base_risk_scorecard.csv"
        benchmark_path = repo_dir / "output" / "tables" / "industry_public_benchmarks.csv"
        if not base_path.exists():
            continue

        base_df = pd.read_csv(base_path)
        base_df["industry"] = base_df["industry"].map(normalise_industry_name)
        base_df = base_df.dropna(subset=["industry"])

        merge_df = base_df[[
            "industry",
            "classification_risk_score",
            "macro_risk_score",
            "industry_base_risk_score",
            "industry_base_risk_level",
            "employment_yoy_growth_pct",
            "ebitda_margin_pct_latest",
            "inventory_days_est",
            "demand_yoy_growth_pct",
            "cash_rate_latest_pct",
        ]].rename(
            columns={
                "industry_base_risk_score": "final_industry_risk_score",
                "industry_base_risk_level": "risk_level",
                "employment_yoy_growth_pct": "public_employment_yoy_growth_pct",
                "ebitda_margin_pct_latest": "public_ebitda_margin_pct_latest",
                "inventory_days_est": "public_inventory_days_est",
                "demand_yoy_growth_pct": "public_demand_yoy_growth_pct",
                "cash_rate_latest_pct": "public_cash_rate_latest_pct",
            }
        )

        if benchmark_path.exists():
            benchmark_df = pd.read_csv(benchmark_path)
            benchmark_df["industry"] = benchmark_df["industry"].map(normalise_industry_name)
            benchmark_df = benchmark_df.dropna(subset=["industry"])
            benchmark_df = benchmark_df[[
                "industry",
                "ebitda_margin_pct_latest",
                "inventory_days_est",
                "employment_yoy_growth_pct",
                "demand_yoy_growth_pct",
            ]].rename(
                columns={
                    "ebitda_margin_pct_latest": "benchmark_ebitda_margin_pct_latest",
                    "inventory_days_est": "benchmark_inventory_days_est",
                    "employment_yoy_growth_pct": "benchmark_employment_yoy_growth_pct",
                    "demand_yoy_growth_pct": "benchmark_demand_yoy_growth_pct",
                }
            )
            merge_df = merge_df.merge(benchmark_df, on="industry", how="left")
            merge_df["public_ebitda_margin_pct_latest"] = merge_df["public_ebitda_margin_pct_latest"].fillna(
                merge_df["benchmark_ebitda_margin_pct_latest"]
            )
            merge_df["public_inventory_days_est"] = merge_df["public_inventory_days_est"].fillna(
                merge_df["benchmark_inventory_days_est"]
            )
            merge_df["public_employment_yoy_growth_pct"] = merge_df["public_employment_yoy_growth_pct"].fillna(
                merge_df["benchmark_employment_yoy_growth_pct"]
            )
            merge_df["public_demand_yoy_growth_pct"] = merge_df["public_demand_yoy_growth_pct"].fillna(
                merge_df["benchmark_demand_yoy_growth_pct"]
            )
            merge_df = merge_df.drop(
                columns=[
                    "benchmark_ebitda_margin_pct_latest",
                    "benchmark_inventory_days_est",
                    "benchmark_employment_yoy_growth_pct",
                    "benchmark_demand_yoy_growth_pct",
                ]
            )

        merge_df["industry_overlay_source"] = "Public industry risk repo"
        merge_df["industry_overlay_path"] = str(base_path)

        overlay = overlay.drop(columns=["industry_overlay_source", "industry_overlay_path"]).merge(
            merge_df,
            on="industry",
            how="left",
            suffixes=("_fallback", ""),
        )

        for column in [
            "classification_risk_score",
            "macro_risk_score",
            "final_industry_risk_score",
            "risk_level",
            "public_ebitda_margin_pct_latest",
            "public_inventory_days_est",
            "public_employment_yoy_growth_pct",
            "public_demand_yoy_growth_pct",
            "public_cash_rate_latest_pct",
            "industry_overlay_source",
            "industry_overlay_path",
        ]:
            fallback_column = f"{column}_fallback"
            if fallback_column in overlay.columns:
                overlay[column] = overlay[column].fillna(overlay[fallback_column])
                overlay = overlay.drop(columns=[fallback_column])

        provenance_rows.append(
            {
                "dataset_name": "industry_overlays",
                "dataset_group": "public_official",
                "status": "loaded",
                "records_loaded": int(len(merge_df)),
                "source_path": str(base_path),
                "notes": "Loaded public industry and macro overlays from the external industry-risk repository.",
            }
        )
        break

    if not provenance_rows:
        provenance_rows.append(
            {
                "dataset_name": "industry_overlays",
                "dataset_group": "public_official",
                "status": "fallback",
                "records_loaded": int(len(overlay)),
                "source_path": "",
                "notes": "External industry-risk repository not found. Using in-repo fallback settings.",
            }
        )

    return overlay.sort_values("industry").reset_index(drop=True), pd.DataFrame(provenance_rows)


def load_listed_company_financials() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    precomputed_outputs = _load_precomputed_listed_company_outputs()
    if precomputed_outputs is not None:
        return precomputed_outputs

    standard_rows = []
    provenance_rows = []

    for path, raw_df in _read_csv_files(LISTED_COMPANY_DIR):
        company_col = _coalesce_column(raw_df, [
            "company",
            "company_name",
            "borrower_name",
            "borrower",
            "entity",
            "issuer",
            "name",
            "ticker",
        ])
        industry_col = _coalesce_column(raw_df, [
            "industry",
            "sector",
            "industry_folder",
            "industry_group",
            "anzsic_industry",
            "anzsic_division",
            "division",
            "gics_sector",
        ])
        revenue_col = _coalesce_column(raw_df, ["revenue", "sales", "turnover", "total_revenue"])
        if industry_col is None or revenue_col is None:
            provenance_rows.append(
                {
                    "dataset_name": "listed_company_financials",
                    "dataset_group": "public_listed",
                    "status": "skipped",
                    "records_loaded": 0,
                    "source_path": str(path),
                    "notes": "Missing at least industry and revenue columns after schema inference.",
                }
            )
            continue

        period_col = _coalesce_column(raw_df, ["period", "fiscal_year", "year", "reporting_period"])
        standard_df = pd.DataFrame(
            {
                "source_file": path.name,
                "company_name": raw_df[company_col].astype(str) if company_col else path.stem,
                "industry": raw_df[industry_col].map(normalise_industry_name),
                "period": raw_df[period_col].astype(str) if period_col else "Latest",
                "revenue": pd.to_numeric(raw_df[revenue_col], errors="coerce"),
            }
        )

        for target, candidates in {
            "ebitda": ["ebitda"],
            "ebit": ["ebit", "operating_profit"],
            "operating_cash_flow": ["operating_cash_flow", "operating_cashflow", "cash_from_operations"],
            "current_assets": ["current_assets"],
            "current_liabilities": ["current_liabilities"],
            "total_debt": ["total_debt", "borrowings", "interest_bearing_debt"],
            "interest_expense": ["interest_expense", "finance_costs"],
            "cash": ["cash", "cash_and_equivalents"],
            "debtors": ["debtors", "trade_receivables", "accounts_receivable"],
            "inventory": ["inventory", "inventories"],
            "net_worth": ["net_worth", "equity", "shareholders_equity"],
        }.items():
            column = _coalesce_column(raw_df, candidates)
            standard_df[target] = pd.to_numeric(raw_df[column], errors="coerce") if column else np.nan

        standard_df = standard_df.dropna(subset=["industry", "revenue"])
        if standard_df.empty:
            provenance_rows.append(
                {
                    "dataset_name": "listed_company_financials",
                    "dataset_group": "public_listed",
                    "status": "skipped",
                    "records_loaded": 0,
                    "source_path": str(path),
                    "notes": "No rows matched the project's in-scope industries after normalisation.",
                }
            )
            continue

        standard_rows.append(standard_df)
        provenance_rows.append(
            {
                "dataset_name": "listed_company_financials",
                "dataset_group": "public_listed",
                "status": "loaded",
                "records_loaded": int(len(standard_df)),
                "source_path": str(path),
                "notes": "Loaded structured listed-company line items for industry benchmark calibration.",
            }
        )

    if not standard_rows:
        if not provenance_rows:
            provenance_rows.append(
                {
                    "dataset_name": "listed_company_financials",
                    "dataset_group": "public_listed",
                    "status": "not_provided",
                    "records_loaded": 0,
                    "source_path": str(LISTED_COMPANY_DIR),
                    "notes": "Drop structured listed-company CSVs into this folder to calibrate financial benchmarks.",
                }
            )
        return _empty(_LISTED_STANDARD_COLUMNS), _empty(_LISTED_BENCHMARK_COLUMNS), pd.DataFrame(provenance_rows)

    standard_df = pd.concat(standard_rows, ignore_index=True)[_LISTED_STANDARD_COLUMNS]
    benchmark_df = _build_listed_company_benchmarks(standard_df, "Public listed-company reports")
    return standard_df, benchmark_df, pd.DataFrame(provenance_rows)


def load_transaction_benchmarks() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    precomputed_outputs = _load_precomputed_transaction_outputs()
    if precomputed_outputs is not None:
        return precomputed_outputs

    standard_rows = []
    provenance_rows = []

    for path, raw_df in _read_csv_files(KAGGLE_TRANSACTIONS_DIR):
        amount_col = _coalesce_column(raw_df, ["amount", "transaction_amount", "amt", "value", "posted_amount"])
        date_col = _coalesce_column(raw_df, ["transaction_date", "date", "booking_date", "post_date", "timestamp"])
        if amount_col is None or date_col is None:
            provenance_rows.append(
                {
                    "dataset_name": "transaction_benchmarks",
                    "dataset_group": "public_proxy_kaggle",
                    "status": "skipped",
                    "records_loaded": 0,
                    "source_path": str(path),
                    "notes": "Missing transaction amount or date columns after schema inference.",
                }
            )
            continue

        account_col = _coalesce_column(raw_df, ["account_id", "card_id", "customer_id", "business_id", "entity_id"])
        balance_col = _coalesce_column(raw_df, ["balance", "running_balance", "current_balance"])
        direction_col = _coalesce_column(raw_df, ["direction", "debit_credit", "dr_cr", "type", "transaction_type"])
        status_col = _coalesce_column(raw_df, ["status", "transaction_status", "state", "response"])
        category_col = _coalesce_column(raw_df, ["category", "merchant_category", "description", "merchant"])
        industry_col = _coalesce_column(raw_df, ["industry", "sector"])

        standard_df = pd.DataFrame(
            {
                "source_file": path.name,
                "public_account_id": raw_df[account_col].astype(str) if account_col else "portfolio_proxy",
                "industry": raw_df[industry_col].map(normalise_industry_name) if industry_col else np.nan,
                "transaction_date": pd.to_datetime(raw_df[date_col], errors="coerce"),
                "amount_raw": pd.to_numeric(raw_df[amount_col], errors="coerce"),
            }
        )
        standard_df = standard_df.dropna(subset=["transaction_date", "amount_raw"])
        if standard_df.empty:
            provenance_rows.append(
                {
                    "dataset_name": "transaction_benchmarks",
                    "dataset_group": "public_proxy_kaggle",
                    "status": "skipped",
                    "records_loaded": 0,
                    "source_path": str(path),
                    "notes": "No valid transaction rows remained after type conversion.",
                }
            )
            continue

        if direction_col:
            direction_text = raw_df.loc[standard_df.index, direction_col].astype(str).str.lower()
            credit_mask = direction_text.str.contains("credit|cr|deposit|inflow|payment received", regex=True)
            debit_mask = direction_text.str.contains("debit|dr|withdrawal|purchase|outflow|payment made", regex=True)
            standard_df["amount"] = standard_df["amount_raw"]
            standard_df.loc[credit_mask, "amount"] = standard_df.loc[credit_mask, "amount_raw"].abs()
            standard_df.loc[debit_mask, "amount"] = -standard_df.loc[debit_mask, "amount_raw"].abs()
            standard_df.loc[~credit_mask & ~debit_mask, "amount"] = standard_df.loc[~credit_mask & ~debit_mask, "amount_raw"]
        else:
            standard_df["amount"] = standard_df["amount_raw"]

        if balance_col:
            standard_df["balance"] = pd.to_numeric(raw_df.loc[standard_df.index, balance_col], errors="coerce")
        else:
            standard_df = standard_df.sort_values(["public_account_id", "transaction_date"])
            standard_df["balance"] = standard_df.groupby("public_account_id")["amount"].cumsum()

        status_text = raw_df.loc[standard_df.index, status_col].astype(str).str.lower() if status_col else pd.Series("", index=standard_df.index)
        category_text = raw_df.loc[standard_df.index, category_col].astype(str).str.lower() if category_col else pd.Series("", index=standard_df.index)
        standard_df["event_failed_flag"] = status_text.str.contains("declin|fail|reject|reverse", regex=True).astype(int)
        standard_df["cash_advance_flag"] = category_text.str.contains("cash advance|atm|cash withdrawal|cashout", regex=True).astype(int)
        standard_df["credit_amount"] = standard_df["amount"].clip(lower=0.0)
        standard_df["debit_amount"] = (-standard_df["amount"]).clip(lower=0.0)

        standard_rows.append(standard_df[[
            "source_file",
            "public_account_id",
            "industry",
            "transaction_date",
            "amount",
            "credit_amount",
            "debit_amount",
            "balance",
            "event_failed_flag",
            "cash_advance_flag",
        ]])
        provenance_rows.append(
            {
                "dataset_name": "transaction_benchmarks",
                "dataset_group": "public_proxy_kaggle",
                "status": "loaded",
                "records_loaded": int(len(standard_df)),
                "source_path": str(path),
                "notes": "Loaded Kaggle-style transaction or card data for conduct benchmark calibration.",
            }
        )

    if not standard_rows:
        if not provenance_rows:
            provenance_rows.append(
                {
                    "dataset_name": "transaction_benchmarks",
                    "dataset_group": "public_proxy_kaggle",
                    "status": "not_provided",
                    "records_loaded": 0,
                    "source_path": str(KAGGLE_TRANSACTIONS_DIR),
                    "notes": "Drop Kaggle banking or card transaction CSVs into this folder to calibrate conduct benchmarks.",
                }
            )
        return _empty(_TRANSACTION_STANDARD_COLUMNS), _empty(_TRANSACTION_BENCHMARK_COLUMNS), pd.DataFrame(provenance_rows)

    standard_df = pd.concat(standard_rows, ignore_index=True)
    standard_df["industry"] = standard_df["industry"].fillna("All Industries")
    standard_df["year_month"] = standard_df["transaction_date"].dt.to_period("M").astype(str)
    monthly_df = (
        standard_df.groupby(["industry", "public_account_id", "year_month"], as_index=False)
        .agg(
            monthly_credits=("credit_amount", "sum"),
            monthly_debits=("debit_amount", "sum"),
            net_cash=("amount", "sum"),
            avg_balance=("balance", "mean"),
            failed_events=("event_failed_flag", "sum"),
            cash_advance_events=("cash_advance_flag", "sum"),
        )
    )
    account_summary = (
        monthly_df.groupby(["industry", "public_account_id"], as_index=False)
        .agg(
            avg_monthly_credits=("monthly_credits", "mean"),
            avg_monthly_debits=("monthly_debits", "mean"),
            months_negative_net_cash=("net_cash", lambda s: int((s < 0).sum())),
            failed_event_rate=("failed_events", lambda s: float(np.mean(s > 0))),
            cash_advance_rate=("cash_advance_events", lambda s: float(np.mean(s > 0))),
            credit_turnover_cv=("monthly_credits", lambda s: float(s.std(ddof=0) / s.mean()) if s.mean() else 0.0),
        )
    )
    benchmark_df = (
        account_summary.groupby("industry", as_index=False)
        .agg(
            transaction_account_count=("public_account_id", "nunique"),
            transaction_record_count=("public_account_id", "count"),
            tx_avg_monthly_credits_median=("avg_monthly_credits", "median"),
            tx_avg_monthly_debits_median=("avg_monthly_debits", "median"),
            tx_credit_turnover_cv_median=("credit_turnover_cv", "median"),
            tx_months_negative_net_cash_median=("months_negative_net_cash", "median"),
            tx_failed_event_rate_median=("failed_event_rate", "median"),
            tx_cash_advance_rate_median=("cash_advance_rate", "median"),
        )
        .sort_values("industry")
    )
    benchmark_df["transaction_benchmark_source"] = "Kaggle banking/card transactions"
    standard_df = standard_df.drop(columns=["year_month"], errors="ignore")
    return standard_df, benchmark_df, pd.DataFrame(provenance_rows)


def load_invoice_benchmarks() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    precomputed_outputs = _load_precomputed_invoice_outputs()
    if precomputed_outputs is not None:
        return precomputed_outputs

    standard_rows = []
    provenance_rows = []

    for path, raw_df in _read_csv_files(KAGGLE_INVOICES_DIR):
        amount_col = _coalesce_column(raw_df, ["invoice_amount", "amount", "total", "invoice_value"])
        due_col = _coalesce_column(raw_df, ["due_date", "payment_due_date"])
        invoice_col = _coalesce_column(raw_df, ["invoice_id", "id"])
        if amount_col is None or due_col is None:
            provenance_rows.append(
                {
                    "dataset_name": "invoice_benchmarks",
                    "dataset_group": "public_proxy_kaggle",
                    "status": "skipped",
                    "records_loaded": 0,
                    "source_path": str(path),
                    "notes": "Missing invoice amount or due-date columns after schema inference.",
                }
            )
            continue

        payment_col = _coalesce_column(raw_df, ["payment_date", "paid_date", "settlement_date"])
        customer_col = _coalesce_column(raw_df, ["customer_id", "debtor_id", "client_id", "buyer_id"])
        status_col = _coalesce_column(raw_df, ["status", "invoice_status", "state"])
        type_col = _coalesce_column(raw_df, ["type", "document_type"])
        industry_col = _coalesce_column(raw_df, ["industry", "sector"])

        standard_df = pd.DataFrame(
            {
                "source_file": path.name,
                "invoice_id": raw_df[invoice_col].astype(str) if invoice_col else raw_df.index.astype(str),
                "customer_id": raw_df[customer_col].astype(str) if customer_col else "portfolio_proxy",
                "industry": raw_df[industry_col].map(normalise_industry_name) if industry_col else np.nan,
                "invoice_amount": pd.to_numeric(raw_df[amount_col], errors="coerce"),
                "due_date": pd.to_datetime(raw_df[due_col], errors="coerce"),
                "payment_date": pd.to_datetime(raw_df[payment_col], errors="coerce") if payment_col else pd.NaT,
            }
        )
        standard_df = standard_df.dropna(subset=["invoice_amount", "due_date"])
        if standard_df.empty:
            provenance_rows.append(
                {
                    "dataset_name": "invoice_benchmarks",
                    "dataset_group": "public_proxy_kaggle",
                    "status": "skipped",
                    "records_loaded": 0,
                    "source_path": str(path),
                    "notes": "No valid invoice rows remained after type conversion.",
                }
            )
            continue

        status_text = raw_df.loc[standard_df.index, status_col].astype(str).str.lower() if status_col else pd.Series("", index=standard_df.index)
        type_text = raw_df.loc[standard_df.index, type_col].astype(str).str.lower() if type_col else pd.Series("", index=standard_df.index)
        delay = (standard_df["payment_date"] - standard_df["due_date"]).dt.days
        standard_df["payment_delay_days"] = delay.fillna(0.0)
        standard_df["late_payment_flag"] = (standard_df["payment_delay_days"] > 0).astype(int)
        standard_df["severe_late_payment_90dpd_flag"] = (standard_df["payment_delay_days"] > 90).astype(int)
        standard_df["dilution_proxy_flag"] = (
            status_text.str.contains("credit|revers|cancel|adjust", regex=True)
            | type_text.str.contains("credit|adjust|return", regex=True)
        ).astype(int)

        standard_rows.append(standard_df[[
            "source_file",
            "invoice_id",
            "customer_id",
            "industry",
            "invoice_amount",
            "due_date",
            "payment_date",
            "payment_delay_days",
            "late_payment_flag",
            "severe_late_payment_90dpd_flag",
            "dilution_proxy_flag",
        ]])
        provenance_rows.append(
            {
                "dataset_name": "invoice_benchmarks",
                "dataset_group": "public_proxy_kaggle",
                "status": "loaded",
                "records_loaded": int(len(standard_df)),
                "source_path": str(path),
                "notes": "Loaded invoice and payment-date data for receivables benchmark calibration.",
            }
        )

    if not standard_rows:
        if not provenance_rows:
            provenance_rows.append(
                {
                    "dataset_name": "invoice_benchmarks",
                    "dataset_group": "public_proxy_kaggle",
                    "status": "not_provided",
                    "records_loaded": 0,
                    "source_path": str(KAGGLE_INVOICES_DIR),
                    "notes": "Drop invoice and payment-date CSVs into this folder to calibrate receivables benchmarks.",
                }
            )
        return _empty(_INVOICE_STANDARD_COLUMNS), _empty(_INVOICE_BENCHMARK_COLUMNS), pd.DataFrame(provenance_rows)

    standard_df = pd.concat(standard_rows, ignore_index=True)
    standard_df["industry"] = standard_df["industry"].fillna("All Industries")
    customer_concentration = (
        standard_df.groupby(["industry", "customer_id"], as_index=False)
        .agg(invoice_amount=("invoice_amount", "sum"))
    )
    total_amount = customer_concentration.groupby("industry", as_index=False).agg(total_invoice_amount=("invoice_amount", "sum"))
    customer_concentration = customer_concentration.merge(total_amount, on="industry", how="left")
    customer_concentration["customer_share"] = customer_concentration["invoice_amount"] / customer_concentration["total_invoice_amount"].replace(0, np.nan)
    concentration_df = customer_concentration.groupby("industry", as_index=False).agg(
        invoice_top_customer_concentration_pct=("customer_share", "max")
    )
    benchmark_df = (
        standard_df.groupby("industry", as_index=False)
        .agg(
            invoice_record_count=("invoice_id", "count"),
            invoice_customer_count=("customer_id", "nunique"),
            invoice_amount_median=("invoice_amount", "median"),
            invoice_payment_delay_median_days=("payment_delay_days", "median"),
            invoice_late_payment_rate=("late_payment_flag", "mean"),
            invoice_severe_late_rate_90dpd=("severe_late_payment_90dpd_flag", "mean"),
            invoice_dilution_proxy_rate=("dilution_proxy_flag", "mean"),
        )
        .merge(concentration_df, on="industry", how="left")
        .sort_values("industry")
    )
    benchmark_df["invoice_benchmark_source"] = "Kaggle invoices and payment dates"
    return standard_df, benchmark_df, pd.DataFrame(provenance_rows)


def build_public_data_context(use_public_data: bool = True) -> dict:
    industry_overlay_df, industry_provenance = load_public_industry_overlays()
    if use_public_data:
        listed_standard_df, listed_benchmark_df, listed_provenance = load_listed_company_financials()
        transaction_standard_df, transaction_benchmark_df, transaction_provenance = load_transaction_benchmarks()
        invoice_standard_df, invoice_benchmark_df, invoice_provenance = load_invoice_benchmarks()
    else:
        listed_standard_df = _empty([])
        listed_benchmark_df = _empty([])
        listed_provenance = _empty([])
        transaction_standard_df = _empty([])
        transaction_benchmark_df = _empty([])
        transaction_provenance = _empty([])
        invoice_standard_df = _empty([])
        invoice_benchmark_df = _empty([])
        invoice_provenance = _empty([])

    merged_industry_profiles = industry_overlay_df.copy()
    if not listed_benchmark_df.empty:
        merged_industry_profiles = merged_industry_profiles.merge(listed_benchmark_df, on="industry", how="left")
    else:
        for column in [
            "listed_company_count",
            "listed_revenue_median",
            "listed_ebitda_margin_median",
            "listed_ocf_margin_median",
            "listed_current_ratio_median",
            "listed_debt_to_ebitda_median",
            "listed_benchmark_source",
        ]:
            merged_industry_profiles[column] = np.nan

    if not transaction_benchmark_df.empty:
        merged_industry_profiles = merged_industry_profiles.merge(
            transaction_benchmark_df[transaction_benchmark_df["industry"] != "All Industries"],
            on="industry",
            how="left",
        )
    else:
        for column in [
            "transaction_account_count",
            "transaction_record_count",
            "tx_avg_monthly_credits_median",
            "tx_avg_monthly_debits_median",
            "tx_credit_turnover_cv_median",
            "tx_months_negative_net_cash_median",
            "tx_failed_event_rate_median",
            "tx_cash_advance_rate_median",
            "transaction_benchmark_source",
        ]:
            merged_industry_profiles[column] = np.nan

    if not invoice_benchmark_df.empty:
        merged_industry_profiles = merged_industry_profiles.merge(
            invoice_benchmark_df[invoice_benchmark_df["industry"] != "All Industries"],
            on="industry",
            how="left",
        )
    else:
        for column in [
            "invoice_record_count",
            "invoice_customer_count",
            "invoice_amount_median",
            "invoice_payment_delay_median_days",
            "invoice_late_payment_rate",
            "invoice_severe_late_rate_90dpd",
            "invoice_top_customer_concentration_pct",
            "invoice_dilution_proxy_rate",
            "invoice_benchmark_source",
        ]:
            merged_industry_profiles[column] = np.nan

    provenance_df = pd.concat(
        [
            industry_provenance,
            listed_provenance,
            transaction_provenance,
            invoice_provenance,
        ],
        ignore_index=True,
    )
    if provenance_df.empty:
        provenance_df = _empty(["dataset_name", "dataset_group", "status", "records_loaded", "source_path", "notes"])

    return {
        "industry_overlays": industry_overlay_df,
        "industry_profiles": merged_industry_profiles.sort_values("industry").reset_index(drop=True),
        "listed_company_financials": listed_standard_df,
        "listed_company_benchmarks": listed_benchmark_df,
        "transaction_records": transaction_standard_df,
        "transaction_benchmarks": transaction_benchmark_df,
        "invoice_records": invoice_standard_df,
        "invoice_benchmarks": invoice_benchmark_df,
        "public_data_provenance": provenance_df,
    }


def benchmark_lookup(benchmark_df: pd.DataFrame, industry: str) -> dict:
    if benchmark_df.empty:
        return {}
    if "industry" in benchmark_df.columns:
        industry_match = benchmark_df[benchmark_df["industry"] == industry]
        if not industry_match.empty:
            return industry_match.iloc[0].to_dict()
        global_match = benchmark_df[benchmark_df["industry"] == "All Industries"]
        if not global_match.empty:
            return global_match.iloc[0].to_dict()
    return benchmark_df.iloc[0].to_dict()
