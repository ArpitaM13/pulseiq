"""Load every worksheet from the supplied workbook into DuckDB's raw schema."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent
INPUT_FILE = ROOT / "data" / "raw" / "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx"
DB_FILE = ROOT / "data" / "pulseiq.duckdb"
SUMMARY_FILE = ROOT / "logs" / "duckdb_load_summary.json"


def safe_table_name(sheet_name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_]+", "_", sheet_name.strip()).strip("_").lower() or "unnamed_sheet"
    return f"sheet_{name}" if name[0].isdigit() else name


def qi(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def load_to_duckdb() -> dict:
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Workbook not found: {INPUT_FILE}. Keep it in data/raw/.")
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    summary = {"started_at_utc": started, "input_file": str(INPUT_FILE.relative_to(ROOT)), "database_file": str(DB_FILE.relative_to(ROOT)), "tables": {}}
    workbook = pd.ExcelFile(INPUT_FILE)
    con = duckdb.connect(str(DB_FILE))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS raw")
        used = set()
        for sheet in workbook.sheet_names:
            table = safe_table_name(sheet)
            if table in used:
                raise ValueError(f"Worksheet names collide after normalisation: {sheet!r} -> {table!r}")
            used.add(table)
            frame = pd.read_excel(workbook, sheet_name=sheet)
            con.register("_incoming_df", frame)
            try:
                con.execute(f"CREATE OR REPLACE TABLE raw.{qi(table)} AS SELECT * FROM _incoming_df")
            finally:
                con.unregister("_incoming_df")
            count = con.execute(f"SELECT COUNT(*) FROM raw.{qi(table)}").fetchone()[0]
            cols = len(frame.columns)
            summary["tables"][table] = {"source_sheet": sheet, "rows_loaded": int(count), "columns_loaded": int(cols)}
            print(f"Loaded {sheet}: {count:,} rows, {cols} columns")
        # A second count pass catches failed/incomplete table writes.
        for table, details in summary["tables"].items():
            actual = con.execute(f"SELECT COUNT(*) FROM raw.{qi(table)}").fetchone()[0]
            if int(actual) != details["rows_loaded"]:
                raise RuntimeError(f"Row-count mismatch for {table}: expected {details['rows_loaded']}, got {actual}")
    finally:
        con.close()
        workbook.close()
    summary["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    SUMMARY_FILE.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nLoaded {len(summary['tables'])} worksheet tables into {DB_FILE}")
    print(f"Load summary: {SUMMARY_FILE}")
    return summary


def main() -> None:
    load_to_duckdb()


if __name__ == "__main__":
    main()
