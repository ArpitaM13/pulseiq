"""Build the warehouse from the immutable raw layer and audit model keys."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "data" / "pulseiq.duckdb"
REPORTS = ROOT / "reports"


def qi(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


# Candidate primary keys were checked for null and duplicate values against the
# supplied workbook. No source foreign-key constraints are added because several
# planted orphan rows must remain present for the DQ gatekeeper to identify.
PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "dim_date": ("date_key",),
    "dim_employee": ("employee_key",),
    "dim_department": ("department_id",),
    "dim_role": ("role_id",),
    "dim_location": ("work_location",),
    "dim_leave_type": ("leave_type_code",),
    "dim_account": ("account_code",),
    "dim_client": ("client_id",),
    "dim_vendor": ("vendor_id",),
    "dim_team": ("team_id",),
    "dim_sprint": ("sprint_id",),
    "fact_payroll": ("payroll_item_id",),
    "fact_attendance_monthly": ("attendance_fact_id",),
    "fact_leave": ("leave_request_id",),
    "fact_headcount_monthly": ("date_key", "department_id"),
    "fact_ledger": ("line_id",),
    "fact_invoice": ("invoice_id",),
    "fact_invoice_payment": ("payment_id",),
    "fact_expense": ("expense_id",),
    "fact_task": ("task_id",),
    "fact_anomaly": ("result_id",),
    "fact_attrition_risk": ("prediction_id",),
    "fact_forecast": ("forecast_id",),
    "budget_payroll_dept_month": ("month", "department_id"),
    "kpi_targets": ("month", "department_id"),
    "reference_summary_dept_month": ("month", "department_id"),
    "reconciliation_answer_key": ("month",),
    "dq_known_issues": ("issue_id",),
    "dq_checks_catalog": ("check_id",),
    "metric_dictionary": ("metric_id",),
    "data_contracts": ("feed", "column_name"),
}

# Relationship audits are checks, not enforced foreign keys, to retain the source
# anomalies in raw/warehouse for the quality report and traceability.
FOREIGN_KEYS = [
    ("fact_payroll", "employee_key", "dim_employee", "employee_key", "Payroll employee history; join by employee_key"),
    ("fact_payroll", "department_id", "dim_department", "department_id", "Payroll department"),
    ("fact_payroll", "role_id", "dim_role", "role_id", "Payroll role"),
    ("fact_payroll", "date_key", "dim_date", "date_key", "Payroll date"),
    ("fact_attendance_monthly", "employee_key", "dim_employee", "employee_key", "Attendance employee history"),
    ("fact_attendance_monthly", "department_id", "dim_department", "department_id", "Attendance department"),
    ("fact_attendance_monthly", "date_key", "dim_date", "date_key", "Attendance date"),
    ("fact_leave", "employee_key", "dim_employee", "employee_key", "Leave employee history"),
    ("fact_leave", "leave_type_code", "dim_leave_type", "leave_type_code", "Leave type"),
    ("fact_leave", "start_date_key", "dim_date", "date_key", "Leave start date"),
    ("fact_leave", "end_date_key", "dim_date", "date_key", "Leave end date"),
    ("fact_headcount_monthly", "department_id", "dim_department", "department_id", "Headcount department"),
    ("fact_headcount_monthly", "date_key", "dim_date", "date_key", "Headcount month-end date"),
    ("fact_ledger", "account_code", "dim_account", "account_code", "Ledger account"),
    ("fact_ledger", "date_key", "dim_date", "date_key", "Ledger date"),
    ("fact_ledger", "cost_center_department_id", "dim_department", "department_id", "Optional ledger cost-centre department"),
    ("fact_invoice", "client_id", "dim_client", "client_id", "Invoice client"),
    ("fact_invoice", "invoice_date_key", "dim_date", "date_key", "Invoice date"),
    ("fact_invoice", "service_line_account", "dim_account", "account_code", "Invoice service-line account"),
    ("fact_invoice_payment", "invoice_id", "fact_invoice", "invoice_id", "Payment invoice"),
    ("fact_invoice_payment", "payment_date_key", "dim_date", "date_key", "Payment date"),
    ("fact_expense", "vendor_id", "dim_vendor", "vendor_id", "Expense vendor"),
    ("fact_expense", "department_id", "dim_department", "department_id", "Expense department"),
    ("fact_expense", "expense_date_key", "dim_date", "date_key", "Expense date"),
    ("fact_expense", "category_account", "dim_account", "account_code", "Expense account"),
    ("fact_task", "team_id", "dim_team", "team_id", "Task team"),
    ("fact_task", "sprint_id", "dim_sprint", "sprint_id", "Task sprint"),
    ("fact_task", "assignee_employee_id", "dim_employee", "employee_id", "Task assignee; employee_id may repeat across history versions"),
    ("fact_attrition_risk", "employee_key", "dim_employee", "employee_key", "Risk prediction employee history"),
    ("fact_attrition_risk", "department_id", "dim_department", "department_id", "Risk prediction department"),
    ("fact_anomaly", "employee_id", "dim_employee", "employee_id", "Anomaly employee; employee_id may repeat across history versions"),
    ("fact_forecast", "department_id", "dim_department", "department_id", "Forecast department; ALL is an allowed aggregate"),
    ("kpi_targets", "department_id", "dim_department", "department_id", "KPI target department"),
    ("budget_payroll_dept_month", "department_id", "dim_department", "department_id", "Budget department"),
]


def _copy_table_with_key(con: duckdb.DuckDBPyConnection, table: str) -> tuple[bool, str]:
    key_cols = PRIMARY_KEYS.get(table)
    if not key_cols:
        con.execute(f"CREATE OR REPLACE TABLE warehouse.{qi(table)} AS SELECT * FROM raw.{qi(table)}")
        return False, "No stable candidate key configured"

    description = con.execute(f"DESCRIBE raw.{qi(table)}").fetchall()
    columns = [(str(row[0]), str(row[1])) for row in description]
    column_names = {name for name, _ in columns}
    if not set(key_cols).issubset(column_names):
        raise ValueError(f"Configured primary key for {table} references missing columns: {sorted(set(key_cols)-column_names)}")

    definitions = [f"{qi(name)} {col_type}" for name, col_type in columns]
    primary_key = "PRIMARY KEY (" + ", ".join(qi(col) for col in key_cols) + ")"
    con.execute(f"DROP TABLE IF EXISTS warehouse.{qi(table)}")
    con.execute(f"CREATE TABLE warehouse.{qi(table)} ({', '.join(definitions)}, {primary_key})")
    con.execute(f"INSERT INTO warehouse.{qi(table)} SELECT * FROM raw.{qi(table)}")
    return True, ", ".join(key_cols)


def _relationship_orphans(
    con: duckdb.DuckDBPyConnection,
    child_table: str,
    child_col: str,
    parent_table: str,
    parent_col: str,
) -> int:
    child_columns = {r[0] for r in con.execute(f"DESCRIBE warehouse.{qi(child_table)}").fetchall()}
    parent_columns = {r[0] for r in con.execute(f"DESCRIBE warehouse.{qi(parent_table)}").fetchall()}
    if child_col not in child_columns or parent_col not in parent_columns:
        return -1
    allowed_all = child_table == "fact_forecast" and child_col == "department_id"
    all_clause = f"AND CAST(c.{qi(child_col)} AS VARCHAR) <> 'ALL'" if allowed_all else ""
    sql = f"""
        SELECT COUNT(*)
        FROM warehouse.{qi(child_table)} c
        WHERE c.{qi(child_col)} IS NOT NULL {all_clause}
          AND NOT EXISTS (
            SELECT 1 FROM warehouse.{qi(parent_table)} p
            WHERE CAST(p.{qi(parent_col)} AS VARCHAR) = CAST(c.{qi(child_col)} AS VARCHAR)
          )
    """
    return int(con.execute(sql).fetchone()[0])


def build_warehouse() -> None:
    if not DB_FILE.exists():
        raise FileNotFoundError("DuckDB database missing. Run python load_to_duckdb.py first.")
    REPORTS.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB_FILE))
    row_counts: list[dict] = []
    pk_audit: list[dict] = []
    fk_rows: list[dict] = []
    try:
        # Drop dependent views before rebuilding source tables; raw remains immutable.
        con.execute("DROP SCHEMA IF EXISTS analytics CASCADE")
        for schema in ("warehouse", "staging", "analytics", "audit"):
            con.execute(f"CREATE SCHEMA IF NOT EXISTS {qi(schema)}")

        tables = con.execute("SHOW TABLES FROM raw").fetchall()
        for (table_raw,) in tables:
            table = str(table_raw)
            raw_count = int(con.execute(f"SELECT COUNT(*) FROM raw.{qi(table)}").fetchone()[0])
            has_pk, key_label = _copy_table_with_key(con, table)
            warehouse_count = int(con.execute(f"SELECT COUNT(*) FROM warehouse.{qi(table)}").fetchone()[0])
            if raw_count != warehouse_count:
                raise RuntimeError(f"Warehouse row count mismatch for {table}: raw={raw_count}, warehouse={warehouse_count}")
            row_counts.append({"table_name": table, "raw_rows": raw_count, "warehouse_rows": warehouse_count, "count_matches": raw_count == warehouse_count})
            if table in PRIMARY_KEYS:
                pk_audit.append({"table_name": table, "primary_key_columns": key_label, "primary_key_enforced": has_pk, "status": "PASS" if has_pk else "NOT_CONFIGURED"})

        # Materialize the five core ETL clean/reject outputs into staging.
        for table in ("dim_employee", "fact_payroll", "fact_attendance_monthly", "fact_leave", "fact_headcount_monthly"):
            clean_file = ROOT / "data" / "clean" / f"{table}.csv"
            reject_file = ROOT / "rejected" / f"{table}_rejected.csv"
            if clean_file.exists():
                frame = pd.read_csv(clean_file)
                con.register("_stage_frame", frame)
                try:
                    con.execute(f"CREATE OR REPLACE TABLE staging.{qi('clean_' + table)} AS SELECT * FROM _stage_frame")
                finally:
                    con.unregister("_stage_frame")
            if reject_file.exists():
                frame = pd.read_csv(reject_file)
                con.register("_reject_frame", frame)
                try:
                    con.execute(f"CREATE OR REPLACE TABLE staging.{qi('rejected_' + table)} AS SELECT * FROM _reject_frame")
                finally:
                    con.unregister("_reject_frame")

        con.execute("""CREATE TABLE IF NOT EXISTS audit.etl_run_log (
            run_id VARCHAR, started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
            status VARCHAR, source_file VARCHAR, note VARCHAR
        )""")
        now = datetime.now(timezone.utc)
        run_id = now.strftime("%Y%m%dT%H%M%S.%fZ")
        con.execute(
            "INSERT INTO audit.etl_run_log VALUES (?, ?, ?, ?, ?, ?)",
            [run_id, now, now, "IN_PROGRESS", "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx", "Raw ingestion, warehouse copy, and staging completed; metric and DQ stages remain"],
        )

        for audit_table, frame in (
            ("warehouse_row_counts", pd.DataFrame(row_counts)),
            ("primary_key_audit", pd.DataFrame(pk_audit)),
        ):
            con.register("_audit_frame", frame)
            try:
                con.execute(f"CREATE OR REPLACE TABLE audit.{qi(audit_table)} AS SELECT * FROM _audit_frame")
            finally:
                con.unregister("_audit_frame")

        for child_table, child_col, parent_table, parent_col, relationship in FOREIGN_KEYS:
            try:
                orphan_rows = _relationship_orphans(con, child_table, child_col, parent_table, parent_col)
                status = "PASS" if orphan_rows == 0 else ("NOT_CHECKED" if orphan_rows < 0 else "FAIL")
            except Exception as exc:
                orphan_rows, status = -1, "ERROR"
                relationship = f"{relationship} ({type(exc).__name__}: {exc})"
            fk_rows.append({
                "child_table": child_table, "child_column": child_col,
                "parent_table": parent_table, "parent_column": parent_col,
                "relationship": relationship, "orphan_rows": orphan_rows, "status": status,
            })
        fk_frame = pd.DataFrame(fk_rows)
        con.register("_fk_audit", fk_frame)
        try:
            con.execute("CREATE OR REPLACE TABLE audit.foreign_key_audit AS SELECT * FROM _fk_audit")
        finally:
            con.unregister("_fk_audit")
    finally:
        con.close()

    pd.DataFrame(row_counts).to_csv(REPORTS / "warehouse_row_counts.csv", index=False)
    pd.DataFrame(pk_audit).to_csv(REPORTS / "primary_key_audit.csv", index=False)
    pd.DataFrame(fk_rows).to_csv(REPORTS / "foreign_key_audit.csv", index=False)


def mark_pipeline_success() -> None:
    """Mark the latest run successful only after all required pipeline stages finish."""
    if not DB_FILE.exists():
        raise FileNotFoundError("DuckDB database missing.")
    con = duckdb.connect(str(DB_FILE))
    try:
        row = con.execute("SELECT run_id FROM audit.etl_run_log WHERE status='IN_PROGRESS' ORDER BY started_at DESC LIMIT 1").fetchone()
        if row is None:
            raise RuntimeError("No in-progress pipeline run exists to mark successful.")
        con.execute("UPDATE audit.etl_run_log SET status='SUCCESS', finished_at=?, note=? WHERE run_id=?", [datetime.now(timezone.utc), "All ETL, warehouse, contract, metric and DQ query stages completed", row[0]])
    finally:
        con.close()


def main() -> None:
    build_warehouse()
    print("Warehouse build completed with verified primary keys where source keys are unique.")
    print(f"Row-count audit: {REPORTS / 'warehouse_row_counts.csv'}")
    print(f"Primary-key audit: {REPORTS / 'primary_key_audit.csv'}")
    print(f"Relationship/orphan audit: {REPORTS / 'foreign_key_audit.csv'}")


if __name__ == "__main__":
    main()
