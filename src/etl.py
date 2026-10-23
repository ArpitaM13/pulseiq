"""Clean the five Phase-1 core tables and quarantine invalid records.

Raw workbook tabs are preserved in DuckDB by load_to_duckdb.py. This module
creates CSV outputs for human inspection and a timestamped row reconciliation.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

try:
    import pandera.pandas as pa
except Exception:  # The other explicit checks remain available if Pandera is absent.
    pa = None

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
INPUT_FILE = ROOT / os.getenv("INPUT_FILE", "data/raw/03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx")
CLEAN_DIR = ROOT / "data" / "clean"
REJECTED_DIR = ROOT / "rejected"
LOG_DIR = ROOT / "logs"
for folder in (CLEAN_DIR, REJECTED_DIR, LOG_DIR):
    folder.mkdir(parents=True, exist_ok=True)

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
LOG_PATH = LOG_DIR / f"etl_{RUN_ID}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger("pulseiq.etl")

TABLES: dict[str, dict[str, Any]] = {
    "dim_employee": {
        "date_cols": ["date_of_birth", "hire_date", "exit_date", "valid_from", "valid_to"],
        "dedupe": ["employee_key"],
    },
    "fact_payroll": {
        "date_cols": ["period_end_date"],
        "dedupe": ["payroll_item_id"],
        "numeric_nonnegative": ["monthly_fixed_gross", "earned_fixed_pay", "overtime_pay", "variable_pay", "gross_pay", "net_pay", "employer_cost"],
    },
    "fact_attendance_monthly": {
        "date_cols": ["period_end_date"],
        "dedupe": ["attendance_fact_id"],
        "numeric_nonnegative": ["scheduled_days", "present_days", "late_arrivals", "overtime_hours"],
    },
    "fact_leave": {
        "date_cols": ["start_date", "end_date", "applied_on", "decided_on"],
        "dedupe": ["leave_request_id"],
        "numeric_nonnegative": ["days"],
    },
    "fact_headcount_monthly": {
        "date_cols": ["month_start_date"],
        "dedupe": [["date_key", "department_id"]],
        "numeric_nonnegative": ["headcount_start", "hires", "exits", "headcount_end"],
    },
}


def normalise_names(frame: pd.DataFrame) -> pd.DataFrame:
    """Standardise column labels and trim text without changing source meaning."""
    df = frame.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)
        # Excel sometimes supplies whitespace-only cells instead of true blanks.
        # Normalize those to NA before date parsing so open-ended SCD dates remain valid.
        df[col] = df[col].replace(r"^\s*$", pd.NA, regex=True)
    if "full_name" in df.columns:
        df["full_name"] = df["full_name"].map(
            lambda x: " ".join(x.split()).title() if isinstance(x, str) and x.strip() else x
        )
    return df


def _add_reason(reasons: pd.Series, mask: pd.Series, message: str) -> None:
    mask = mask.fillna(False).astype(bool)
    add = mask & reasons.eq("")
    reasons.loc[add] = message


def validate_table(table: str, df: pd.DataFrame, cfg: dict[str, Any]) -> pd.Series:
    """Return one explicit quarantine reason per invalid row, if possible."""
    reasons = pd.Series("", index=df.index, dtype="object")
    for key in cfg.get("dedupe", []):
        keys = key if isinstance(key, list) else [key]
        if all(k in df.columns for k in keys):
            _add_reason(reasons, df[keys].isna().any(axis=1), f"Missing business key: {', '.join(keys)}")
            _add_reason(reasons, df.duplicated(subset=keys, keep="first"), f"Duplicate business key: {', '.join(keys)}")

    for col in cfg.get("numeric_nonnegative", []):
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce")
            _add_reason(reasons, df[col].notna() & values.isna(), f"{col} is not numeric")
            _add_reason(reasons, values.notna() & (values < 0), f"{col} must be non-negative")

    if table == "dim_employee":
        if {"hire_date", "exit_date"}.issubset(df.columns):
            _add_reason(reasons, df["hire_date"].notna() & df["exit_date"].notna() & (df["hire_date"] > df["exit_date"]), "hire_date is after exit_date")
        if {"valid_from", "valid_to"}.issubset(df.columns):
            _add_reason(reasons, df["valid_from"].notna() & df["valid_to"].notna() & (df["valid_from"] > df["valid_to"]), "valid_from is after valid_to")

    if table == "fact_leave" and {"start_date", "end_date"}.issubset(df.columns):
        _add_reason(reasons, df["start_date"].notna() & df["end_date"].notna() & (df["start_date"] > df["end_date"]), "start_date is after end_date; check source dates and date keys")

    if table == "fact_attendance_monthly" and {"present_days", "scheduled_days"}.issubset(df.columns):
        _add_reason(reasons, df["present_days"].notna() & df["scheduled_days"].notna() & (df["present_days"] > df["scheduled_days"]), "present_days exceeds scheduled_days")

    if table == "fact_payroll" and "gross_pay" in df.columns and pa is not None:
        # Pandera adds an explicit schema check; normal row-level validation above
        # provides the quarantine reason and keeps the audit trail human-readable.
        try:
            schema = pa.DataFrameSchema({"gross_pay": pa.Column(float, nullable=True, coerce=True, checks=pa.Check.ge(0))}, strict=False, coerce=True)
            schema.validate(df, lazy=True)
        except Exception as exc:
            logger.warning("Pandera reported a payroll schema issue; row rules will quarantine invalid values: %s", type(exc).__name__)
            values = pd.to_numeric(df["gross_pay"], errors="coerce")
            _add_reason(reasons, values.notna() & (values < 0), "gross_pay must be non-negative")
    return reasons


def transform(table: str, raw: pd.DataFrame, cfg: dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    df = normalise_names(raw)
    rows_in = len(df)
    df["_source_row"] = range(2, rows_in + 2)

    for col in cfg.get("date_cols", []):
        if col in df.columns:
            source_dates = df[col].copy()
            # This workbook uses 9999-12-31 as the open-ended SCD valid_to sentinel.
            # pandas timestamps cannot represent year 9999, so preserve its meaning
            # as a null end date in the clean dimension rather than rejecting the row.
            open_ended = pd.Series(False, index=df.index)
            if col == "valid_to":
                open_ended = source_dates.astype(str).str.startswith("9999-12-31")
                df.loc[open_ended, col] = pd.NaT
            original_nonblank = source_dates.notna() & ~open_ended
            parsed = pd.to_datetime(df[col], errors="coerce")
            df[col] = parsed
            # Other date parse failures become explicit rejects, not silent nulls.
            df[f"_bad_date_{col}"] = original_nonblank & parsed.isna()
    for col in cfg.get("numeric_nonnegative", []):
        if col in df.columns:
            original_nonblank = df[col].notna()
            parsed = pd.to_numeric(df[col], errors="coerce")
            df[col] = parsed
            df[f"_bad_numeric_{col}"] = original_nonblank & parsed.isna()

    # Exact duplicates are quarantined with a reason rather than silently lost.
    # Helper flags and the source-row number do not form part of the source payload.
    payload_cols = [c for c in df.columns if c != "_source_row" and not c.startswith("_bad_")]
    exact_duplicate_mask = df.duplicated(subset=payload_cols, keep="first")
    exact_duplicates = df.loc[exact_duplicate_mask].copy()
    df = df.loc[~exact_duplicate_mask].copy().reset_index(drop=True)
    reasons = validate_table(table, df, cfg)
    for col in df.columns:
        if col.startswith("_bad_date_"):
            _add_reason(reasons, df[col], f"Invalid date in {col.removeprefix('_bad_date_')}")
        if col.startswith("_bad_numeric_"):
            _add_reason(reasons, df[col], f"Non-numeric value in {col.removeprefix('_bad_numeric_')}")

    invalid = reasons.ne("")
    rejected = df.loc[invalid].copy()
    if not rejected.empty:
        rejected["_reject_reason"] = reasons.loc[invalid]
    if not exact_duplicates.empty:
        exact_duplicates["_reject_reason"] = "Exact duplicate of an earlier source row"
        rejected = pd.concat([rejected, exact_duplicates], ignore_index=True, sort=False)
    clean = df.loc[~invalid].copy()
    helper_cols = [c for c in clean.columns if c == "_source_row" or c.startswith("_bad_")]
    clean = clean.drop(columns=helper_cols, errors="ignore")
    helper_cols = [c for c in rejected.columns if c.startswith("_bad_")]
    rejected = rejected.drop(columns=helper_cols, errors=False)

    if table == "dim_employee" and "hire_date" in clean.columns:
        as_of = pd.Timestamp(os.getenv("AS_OF_DATE", "2026-10-20")).normalize()
        end = clean["exit_date"] if "exit_date" in clean.columns else pd.Series(pd.NaT, index=clean.index)
        effective_end = end.fillna(as_of)
        clean["tenure_days"] = (effective_end - clean["hire_date"]).dt.days.clip(lower=0)
        clean["tenure_years"] = (clean["tenure_days"] / 365.25).round(2)

    for date_col in ("period_end_date", "start_date", "month_start_date"):
        if date_col in clean.columns:
            clean["month"] = clean[date_col].dt.month
            clean["year"] = clean[date_col].dt.year
            break

    counts = {
        "rows_in": rows_in,
        "rows_after_exact_dedup": len(df),
        "rows_exact_duplicates": int(exact_duplicate_mask.sum()),
        "rows_out": len(clean),
        "rejected": len(rejected),
    }
    if counts["rows_in"] != counts["rows_out"] + counts["rejected"]:
        raise AssertionError(f"Row reconciliation failed for {table}: {counts}")
    logger.info("%s: rows_in=%d exact_duplicates=%d rows_out=%d rejected=%d", table, rows_in, counts["rows_exact_duplicates"], len(clean), len(rejected))
    return clean, rejected, counts


def run_etl() -> dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    logger.info("ETL started at %s", started)
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input workbook not found: {INPUT_FILE}")

    summary: dict[str, Any] = {"started_at_utc": started, "input_file": INPUT_FILE.name, "tables": {}}
    with pd.ExcelFile(INPUT_FILE) as workbook:
        for table, cfg in TABLES.items():
            if table not in workbook.sheet_names:
                logger.warning("Configured worksheet %s was not found; skipping", table)
                continue
            raw = pd.read_excel(workbook, sheet_name=table)
            clean, rejected, counts = transform(table, raw, cfg)
            clean_path = CLEAN_DIR / f"{table}.csv"
            reject_path = REJECTED_DIR / f"{table}_rejected.csv"
            clean.to_csv(clean_path, index=False, date_format="%Y-%m-%d")
            rejected.to_csv(reject_path, index=False, date_format="%Y-%m-%d")
            counts.update({"clean_file": str(clean_path.relative_to(ROOT)), "rejected_file": str(reject_path.relative_to(ROOT))})
            summary["tables"][table] = counts
            if counts["rows_in"] != counts["rows_out"] + counts["rejected"]:
                raise AssertionError(f"rows_in reconciliation failed for {table}: {counts}")
    summary["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    summary_path = LOG_DIR / f"etl_summary_{RUN_ID}.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("ETL finished. Summary: %s", summary_path)
    return summary


def main() -> None:
    run_etl()


if __name__ == "__main__":
    main()
