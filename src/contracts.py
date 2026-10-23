"""Apply the supplied data_contracts sheet to the four contract-governed feeds."""
from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "data" / "pulseiq.duckdb"
REPORTS = ROOT / "reports"
REJECTED = ROOT / "rejected"


def _table_from_feed(feed: str) -> str | None:
    m = re.search(r"\(([^()]+)\)\s*$", str(feed))
    return m.group(1).strip().lower() if m else None


def _rule_reasons(df: pd.DataFrame, row: pd.Series, con: duckdb.DuckDBPyConnection) -> pd.Series:
    col = str(row["column_name"])
    dtype = str(row["data_type"]).lower()
    nullable = str(row["nullable"]).strip().lower() in {"yes", "true", "1"}
    rule = "" if pd.isna(row["rule_or_allowed_values"]) else str(row["rule_or_allowed_values"]).strip()
    reasons = pd.Series("", index=df.index, dtype="object")
    if col not in df.columns:
        reasons[:] = f"Missing required column: {col}"
        return reasons
    vals = df[col]
    if not nullable:
        reasons.loc[vals.isna()] = f"{col} is required"
    if dtype == "string":
        bad = vals.notna() & ~vals.map(lambda value: isinstance(value, str))
        reasons.loc[bad & reasons.eq("")] = f"{col} must be textual"
    if dtype in {"date", "timestamp"}:
        parsed = pd.to_datetime(vals, errors="coerce", utc=(dtype == "timestamp"))
        bad = vals.notna() & parsed.isna()
        reasons.loc[bad & reasons.eq("")] = f"{col} is not a valid {dtype}"
    elif dtype in {"int", "integer"}:
        parsed = pd.to_numeric(vals, errors="coerce")
        bad = vals.notna() & (parsed.isna() | ((parsed % 1) != 0))
        reasons.loc[bad & reasons.eq("")] = f"{col} must be an integer"
    elif dtype.startswith(("decimal", "numeric", "float")):
        parsed = pd.to_numeric(vals, errors="coerce")
        bad = vals.notna() & parsed.isna()
        reasons.loc[bad & reasons.eq("")] = f"{col} is not numeric"
    elif dtype.startswith("char(") and dtype.endswith(")"):
        try:
            width = int(dtype[5:-1])
            bad = vals.notna() & vals.astype(str).str.len().ne(width)
            reasons.loc[bad & reasons.eq("")] = f"{col} must contain exactly {width} character(s)"
        except ValueError:
            pass

    if "unique" in rule.lower():
        duplicate = vals.notna() & vals.duplicated(keep="first")
        reasons.loc[duplicate & reasons.eq("")] = f"{col} must be unique"

    # Named patterns from the contract catalogue.
    pattern_map = {
        "AN-nnnn": r"^AN-\d{4}$", "AR-nnnn": r"^AR-\d{4}$",
        "FC-nnnn": r"^FC-\d{4}$", "TASK-nnnnn": r"^TASK-\d{5}$",
    }
    for token, pattern in pattern_map.items():
        if token in rule:
            bad = vals.notna() & ~vals.astype(str).str.match(pattern)
            reasons.loc[bad & reasons.eq("")] = f"{col} must match {token} format"

    # Explicit enumerations in the contract are written as A | B | C.
    enum = None
    if " | " in rule and not any(t in rule.lower() for t in ["month end", "exists in", "source dataset", "allowed"]):
        parts = [p.strip() for p in rule.split(" | ") if p.strip()]
        if len(parts) > 1 and all(len(p) < 80 for p in parts):
            enum = parts
    if enum:
        bad = vals.notna() & ~vals.astype(str).isin(enum)
        reasons.loc[bad & reasons.eq("")] = f"{col} must be one of: {', '.join(enum)}"

    if "0 to 1" in rule:
        num = pd.to_numeric(vals, errors="coerce")
        bad = num.notna() & ~num.between(0, 1)
        reasons.loc[bad & reasons.eq("")] = f"{col} must be between 0 and 1"
    if rule.startswith(">= 0"):
        num = pd.to_numeric(vals, errors="coerce")
        bad = num.notna() & (num < 0)
        reasons.loc[bad & reasons.eq("")] = f"{col} must be >= 0"
    if "<= forecast_value" in rule and {"lower_80", "forecast_value"}.issubset(df.columns):
        bad = pd.to_numeric(df["lower_80"], errors="coerce") > pd.to_numeric(df["forecast_value"], errors="coerce")
        reasons.loc[bad & reasons.eq("")] = "lower_80 exceeds forecast_value"
    if ">= forecast_value" in rule and {"upper_80", "forecast_value"}.issubset(df.columns):
        bad = pd.to_numeric(df["upper_80"], errors="coerce") < pd.to_numeric(df["forecast_value"], errors="coerce")
        reasons.loc[bad & reasons.eq("")] = "upper_80 is below forecast_value"
    if "P1..P4" in rule:
        reasons.loc[vals.notna() & ~vals.astype(str).isin(["P1", "P2", "P3", "P4"]) & reasons.eq("")] = "priority must be P1, P2, P3 or P4"
    if "1,2,3,5,8,13" in rule:
        num = pd.to_numeric(vals, errors="coerce")
        reasons.loc[num.notna() & ~num.isin([1, 2, 3, 5, 8, 13]) & reasons.eq("")] = "story_points must be one of 1, 2, 3, 5, 8 or 13"
    if "Y or N" in rule:
        reasons.loc[vals.notna() & ~vals.astype(str).isin(["Y", "N"]) & reasons.eq("")] = f"{col} must be Y or N"

    if col == "reason_code" and "published codes" in rule.lower():
        published_codes = {
            "FREQUENT_LATE", "GROSS_ABOVE_NORM", "GROSS_BELOW_EXPECTED",
            "LONG_UNPAID_ABSENCE", "NEGATIVE_NET_PAY", "NO_ATTENDANCE",
            "OVERTIME_ABOVE_CAP", "PATTERN_SHIFT", "PF_NOT_DEDUCTED",
            "STATISTICAL_OUTLIER", "ZERO_PAY",
        }
        reasons.loc[vals.notna() & ~vals.astype(str).isin(published_codes) & reasons.eq("")] = "reason_code is not in the published reason-code catalogue"

    if col == "period" and "month end or start date" in rule.lower():
        parsed = pd.to_datetime(vals, errors="coerce")
        month_start = parsed.dt.day.eq(1)
        month_end = parsed.dt.day.eq(parsed.dt.days_in_month)
        bad = vals.notna() & parsed.notna() & ~(month_start | month_end)
        reasons.loc[bad & reasons.eq("")] = "period must be a month-start or month-end date"

    if col == "forecast_month" and "first day of month" in rule.lower():
        parsed = pd.to_datetime(vals, errors="coerce")
        bad = vals.notna() & parsed.notna() & parsed.dt.day.ne(1)
        reasons.loc[bad & reasons.eq("")] = "forecast_month must be the first day of a month"

    if col == "trained_through" and "yyyy-mm" in rule.lower():
        bad = vals.notna() & ~vals.astype(str).str.fullmatch(r"\d{4}-(0[1-9]|1[0-2])")
        reasons.loc[bad & reasons.eq("")] = "trained_through must match YYYY-MM"

    # The source workbook includes payroll feature record IDs but not the separate
    # attendance feature extract. Validate IDs only for the available source feed.
    if col == "record_id" and "source dataset" in rule.lower() and "source_dataset" in df.columns:
        payroll_ids = set(con.execute("SELECT payroll_item_id FROM warehouse.fact_payroll").df().iloc[:, 0].dropna().astype(str))
        payroll_rows = df["source_dataset"].astype(str).eq("payroll_monthly_features")
        bad = vals.notna() & payroll_rows & ~vals.astype(str).isin(payroll_ids)
        reasons.loc[bad & reasons.eq("")] = "record_id does not exist in the supplied payroll source records"
    if col == "money_at_risk" and "source_dataset" in df.columns and "blank for attendance rows" in rule.lower():
        attendance_rows = df["source_dataset"].astype(str).eq("attendance_monthly_features")
        payroll_rows = df["source_dataset"].astype(str).eq("payroll_monthly_features")
        bad = (attendance_rows & vals.notna()) | (payroll_rows & vals.isna())
        reasons.loc[bad & reasons.eq("")] = "money_at_risk must be blank for attendance rows and populated for payroll rows"

    # Row-level cross-column rules from the contract.
    if col == "created_date" and {"created_date", "started_date"}.issubset(df.columns):
        created = pd.to_datetime(df["created_date"], errors="coerce")
        started = pd.to_datetime(df["started_date"], errors="coerce")
        bad = created.notna() & started.notna() & (created > started)
        reasons.loc[bad & reasons.eq("")] = "created_date must be on/before started_date"
    if col == "started_date" and "status" in df.columns:
        bad = df["status"].astype(str).ne("To Do") & vals.isna()
        reasons.loc[bad & reasons.eq("")] = "started_date may be blank only when status is To Do"
    if col == "completed_date" and {"completed_date", "started_date", "status"}.issubset(df.columns):
        completed = pd.to_datetime(df["completed_date"], errors="coerce")
        started = pd.to_datetime(df["started_date"], errors="coerce")
        bad = (df["status"].astype(str).eq("Done") & completed.isna()) | (completed.notna() & started.notna() & (completed < started))
        reasons.loc[bad & reasons.eq("")] = "Done tasks need completed_date >= started_date"
    if col == "department_id" and "exists in dim_department" in rule:
        known = set(con.execute("SELECT department_id FROM warehouse.dim_department").df().iloc[:, 0].dropna().astype(str))
        bad = vals.notna() & ~vals.astype(str).isin(known) & vals.astype(str).ne("ALL")
        reasons.loc[bad & reasons.eq("")] = "department_id does not exist in dim_department"
    if col in {"employee_id", "assignee_employee_id"} and "exists in dim_employee" in rule:
        known = set(con.execute("SELECT DISTINCT employee_id FROM warehouse.dim_employee").df().iloc[:, 0].dropna().astype(str))
        bad = vals.notna() & ~vals.astype(str).isin(known)
        reasons.loc[bad & reasons.eq("")] = f"{col} does not exist in dim_employee"
    if col == "team_id" and "exists in dim_team" in rule:
        known = set(con.execute("SELECT team_id FROM warehouse.dim_team").df().iloc[:, 0].dropna().astype(str))
        bad = vals.notna() & ~vals.astype(str).isin(known)
        reasons.loc[bad & reasons.eq("")] = "team_id does not exist in dim_team"
    if col == "sprint_id" and "exists in dim_sprint" in rule:
        known = set(con.execute("SELECT sprint_id FROM warehouse.dim_sprint").df().iloc[:, 0].dropna().astype(str))
        bad = vals.notna() & ~vals.astype(str).isin(known)
        reasons.loc[bad & reasons.eq("")] = "sprint_id does not exist in dim_sprint"
    if col == "employee_id" and "and active" in rule.lower() and {"employee_id", "as_of_date"}.issubset(df.columns):
        employee_versions = con.execute("SELECT employee_id, valid_from, valid_to, exit_date FROM warehouse.dim_employee").df()
        for date_col in ("valid_from", "valid_to", "exit_date"):
            employee_versions[date_col] = pd.to_datetime(employee_versions[date_col], errors="coerce")
        as_of = pd.to_datetime(df["as_of_date"], errors="coerce")
        unknown_or_inactive = pd.Series(False, index=df.index)
        for idx in df.index[vals.notna() & as_of.notna()]:
            emp_id = str(vals.loc[idx])
            when = as_of.loc[idx]
            versions = employee_versions.loc[employee_versions["employee_id"].astype(str).eq(emp_id)]
            active = versions.loc[
                versions["valid_from"].notna()
                & (versions["valid_from"] <= when)
                & (versions["valid_to"].isna() | (versions["valid_to"] >= when))
                & (versions["exit_date"].isna() | (versions["exit_date"] >= when))
            ]
            if active.empty:
                unknown_or_inactive.loc[idx] = True
        reasons.loc[unknown_or_inactive & reasons.eq("")] = "employee_id does not resolve to an active employee version on as_of_date"

    if col == "due_date" and "sprint end date" in rule.lower() and {"due_date", "sprint_id"}.issubset(df.columns):
        sprint_ends = con.execute("SELECT sprint_id, end_date FROM warehouse.dim_sprint").df()
        sprint_ends["end_date"] = pd.to_datetime(sprint_ends["end_date"], errors="coerce").dt.normalize()
        due = pd.to_datetime(df["due_date"], errors="coerce").dt.normalize()
        expected_end = df["sprint_id"].map(sprint_ends.drop_duplicates("sprint_id").set_index("sprint_id")["end_date"])
        bad = vals.notna() & due.notna() & expected_end.notna() & due.ne(expected_end)
        reasons.loc[bad & reasons.eq("")] = "due_date must equal the referenced sprint end_date"

    if col == "risk_band":
        reasons.loc[vals.notna() & ~vals.astype(str).isin(["Low", "Medium", "High"]) & reasons.eq("")] = "risk_band must be Low, Medium or High"
    if col == "metric" and "headcount_end" in rule:
        reasons.loc[vals.notna() & ~vals.astype(str).isin(["headcount_end", "attrition_rate_monthly_pct"]) & reasons.eq("")] = "Unsupported forecast metric"
    if col == "department_id" and "dept id or ALL" in rule:
        known = set(con.execute("SELECT department_id FROM warehouse.dim_department").df().iloc[:, 0].dropna().astype(str))
        bad = vals.notna() & ~vals.astype(str).isin(known | {"ALL"})
        reasons.loc[bad & reasons.eq("")] = "department_id must exist in dim_department or be ALL"
    return reasons


def validate_contracts() -> pd.DataFrame:
    REPORTS.mkdir(exist_ok=True)
    REJECTED.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB_FILE), read_only=False)
    try:
        contracts = con.execute("SELECT * FROM warehouse.data_contracts").df()
        all_rows = []
        table_reasons: dict[str, pd.Series] = {}
        tables: dict[str, pd.DataFrame] = {}
        for feed, contract_rows in contracts.groupby("feed", dropna=False):
            table = _table_from_feed(str(feed))
            if not table:
                continue
            try:
                df = con.execute(f'SELECT * FROM warehouse."{table}"').df()
            except Exception:
                continue
            tables[table] = df
            row_reasons = pd.Series("", index=df.index, dtype="object")
            expected = set(contract_rows["column_name"].astype(str))
            # Contract shorthand top_reason_1..3 describes three actual columns.
            if "top_reason_1..3" in expected:
                expected.remove("top_reason_1..3")
                expected.update({"top_reason_1", "top_reason_2", "top_reason_3"})
            extras = sorted(set(df.columns) - expected)
            missing = sorted(expected - set(df.columns))
            for extra in extras:
                all_rows.append({"feed": feed, "table_name": table, "column_name": extra, "rows_checked": len(df), "violations": 0, "status": "WARN", "detail": "Unexpected column preserved in raw/warehouse table; review schema change"})
            for missing_col in missing:
                all_rows.append({"feed": feed, "table_name": table, "column_name": missing_col, "rows_checked": len(df), "violations": len(df), "status": "FAIL", "detail": "Required contract column is missing"})
            for _, contract_row in contract_rows.iterrows():
                col = str(contract_row["column_name"])
                contract_cols = [col]
                if col == "top_reason_1..3":
                    contract_cols = ["top_reason_1", "top_reason_2", "top_reason_3"]
                violations = 0
                detail_parts = []
                for one_col in contract_cols:
                    r = contract_row.copy()
                    r["column_name"] = one_col
                    reasons = _rule_reasons(df, r, con)
                    bad = reasons.ne("")
                    violations += int(bad.sum())
                    for i in df.index[bad]:
                        message = reasons.loc[i]
                        if not row_reasons.loc[i]:
                            row_reasons.loc[i] = message
                        elif message not in row_reasons.loc[i]:
                            row_reasons.loc[i] += "; " + message
                    if bad.any(): detail_parts.append(f"{one_col}: {int(bad.sum())}")

                # The contract promises record_id must exist in its scoring source.
                # The workbook contains the payroll feature rows' source table but not
                # the separate attendance feature extract, so that portion is unverified.
                partial_coverage = (
                    col == "record_id"
                    and "source_dataset" in df.columns
                    and df["source_dataset"].astype(str).eq("attendance_monthly_features").any()
                )
                if partial_coverage:
                    detail_parts.append(
                        "WARN: attendance feature source is not supplied, so its record_id values cannot be cross-checked"
                    )
                status = "FAIL" if violations else ("WARN" if partial_coverage else "PASS")
                default_detail = "Contract type/nullability/basic rule passed"
                all_rows.append({
                    "feed": feed, "table_name": table, "column_name": col,
                    "rows_checked": len(df), "violations": violations,
                    "status": status,
                    "detail": "; ".join(detail_parts) if detail_parts else default_detail,
                })
            table_reasons[table] = row_reasons
        result = pd.DataFrame(all_rows)
        result.to_csv(REPORTS / "contract_validation.csv", index=False)
        con.execute("CREATE SCHEMA IF NOT EXISTS audit")
        con.register("_contract_frame", result)
        try:
            exists = con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='audit' AND table_name='contract_validation'").fetchone()[0]
            if exists:
                con.execute("DELETE FROM audit.contract_validation")
                con.execute("INSERT INTO audit.contract_validation SELECT * FROM _contract_frame")
            else:
                con.execute("CREATE TABLE audit.contract_validation AS SELECT * FROM _contract_frame")
        finally:
            con.unregister("_contract_frame")
        for table, reasons in table_reasons.items():
            df = tables[table]
            bad = reasons.ne("")
            rejected = df.loc[bad].copy()
            if not rejected.empty:
                rejected["_contract_reject_reason"] = reasons.loc[bad]
            rejected.to_csv(REJECTED / f"{table}_contract_rejected.csv", index=False)
        return result
    finally:
        con.close()


if __name__ == "__main__":
    result = validate_contracts()
    print(result.groupby("status").size().to_string())
    print(f"Details: {REPORTS / 'contract_validation.csv'}")
