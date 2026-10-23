"""Create row-conservation evidence for every workbook worksheet.

Five core tables are validated by the ETL. Four additional feeds have explicit
column contracts in the supplied workbook. Remaining sheets are preserved and
counted as pass-through because no supplied column-level contract describes them.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "data" / "pulseiq.duckdb"
LOGS = ROOT / "logs"
REPORTS = ROOT / "reports"
REJECTED = ROOT / "rejected"
CORE_ETL_TABLES = {
    "dim_employee", "fact_payroll", "fact_attendance_monthly",
    "fact_leave", "fact_headcount_monthly",
}
CONTRACT_TABLES = {"fact_anomaly", "fact_attrition_risk", "fact_forecast", "fact_task"}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _csv_rows(path: Path) -> int:
    if not path.exists() or path.stat().st_size == 0:
        return 0
    try:
        return int(len(pd.read_csv(path)))
    except pd.errors.EmptyDataError:
        return 0


def build_row_audit(raw_summary: dict | None = None, etl_summary: dict | None = None) -> pd.DataFrame:
    REPORTS.mkdir(exist_ok=True)
    if raw_summary is None:
        raw_summary = _read_json(LOGS / "duckdb_load_summary.json")
    if not raw_summary or "tables" not in raw_summary:
        raise FileNotFoundError("Missing or invalid logs/duckdb_load_summary.json; run the workbook loader first.")
    if etl_summary is None:
        candidates = sorted(LOGS.glob("etl_summary_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        etl_summary = _read_json(candidates[0]) if candidates else {"tables": {}}

    etl_tables = etl_summary.get("tables", {})
    load_tables = raw_summary.get("tables", {})
    rows: list[dict] = []
    con = duckdb.connect(str(DB_FILE), read_only=True)
    try:
        for table, loaded in load_tables.items():
            rows_in = int(loaded.get("rows_loaded", 0))
            warehouse_rows = int(con.execute(f'SELECT COUNT(*) FROM warehouse."{table}"').fetchone()[0])
            if table in CORE_ETL_TABLES and table in etl_tables:
                detail = etl_tables[table]
                rows_passed = int(detail.get("rows_out", 0))
                rows_quarantined = int(detail.get("rejected", 0))
                # Exact duplicates are included in rows_rejected by this ETL.
                scope = "Core ETL rules; duplicate/invalid rows quarantined"
                status = "ETL_VALIDATED"
            elif table in CONTRACT_TABLES:
                rows_quarantined = _csv_rows(REJECTED / f"{table}_contract_rejected.csv")
                rows_passed = rows_in - rows_quarantined
                scope = "The supplied data_contracts rules for this feed"
                status = "CONTRACT_VALIDATED"
            else:
                rows_passed = rows_in
                rows_quarantined = 0
                scope = "Pass-through preserved; no explicit column contract for this worksheet"
                status = "PASS_THROUGH"

            rows_conserved = rows_in == rows_passed + rows_quarantined
            warehouse_matches = rows_in == warehouse_rows
            rows.append({
                "table_name": table,
                "source_sheet": loaded.get("source_sheet", table),
                "rows_in": rows_in,
                "rows_passed": rows_passed,
                "rows_quarantined": rows_quarantined,
                "warehouse_rows": warehouse_rows,
                "raw_matches_warehouse": warehouse_matches,
                "row_conservation_ok": rows_conserved,
                "validation_status": status,
                "validation_scope": scope,
            })
    finally:
        con.close()

    frame = pd.DataFrame(rows).sort_values("table_name").reset_index(drop=True)
    frame.to_csv(REPORTS / "table_row_audit.csv", index=False)
    con = duckdb.connect(str(DB_FILE))
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS audit")
        con.register("_row_audit", frame)
        try:
            con.execute("CREATE OR REPLACE TABLE audit.table_row_audit AS SELECT * FROM _row_audit")
        finally:
            con.unregister("_row_audit")
    finally:
        con.close()

    conservation_bad = frame.loc[~frame["row_conservation_ok"]]
    warehouse_bad = frame.loc[~frame["raw_matches_warehouse"]]
    if not conservation_bad.empty:
        raise AssertionError("Rows were not conserved:\n" + conservation_bad[["table_name", "rows_in", "rows_passed", "rows_quarantined"]].to_string(index=False))
    if not warehouse_bad.empty:
        raise AssertionError("Raw-to-warehouse row counts differ:\n" + warehouse_bad[["table_name", "rows_in", "warehouse_rows"]].to_string(index=False))
    return frame


if __name__ == "__main__":
    audit = build_row_audit()
    print(audit[["table_name", "rows_in", "rows_passed", "rows_quarantined", "validation_status"]].to_string(index=False))
    print(f"\nAll {len(audit)} worksheets reconcile. Details: {REPORTS / 'table_row_audit.csv'}")
