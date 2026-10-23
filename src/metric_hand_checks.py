"""Independently spot-check five governed metrics with pandas formulas.

This is a reproducible equivalent of the manual calculation exercise in Phase 1.
It compares grouped pandas calculations against the published metric views and
writes a row-level evidence file without fabricating expected values.
"""
from __future__ import annotations
from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "data" / "pulseiq.duckdb"
REPORTS = ROOT / "reports"


def _period(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce").dt.to_period("M").dt.to_timestamp()


def run_manual_checks() -> pd.DataFrame:
    REPORTS.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB_FILE), read_only=True)
    try:
        headcount = con.execute("SELECT * FROM warehouse.fact_headcount_monthly").df()
        payroll = con.execute("SELECT * FROM warehouse.fact_payroll").df()
        attendance = con.execute("SELECT * FROM warehouse.fact_attendance_monthly").df()
        employees = con.execute("SELECT employee_key, employee_id, exit_date FROM warehouse.dim_employee").df()

        headcount["month_start_date"] = pd.to_datetime(headcount["month_start_date"], errors="coerce")
        base_hc = headcount.groupby(["month_start_date", "department_id"], dropna=False).agg(
            headcount_end=("headcount_end", "sum"), hires=("hires", "sum"), exits=("exits", "sum"),
            headcount_start=("headcount_start", "sum")
        ).reset_index()
        base_hc["metric_m01"] = base_hc["headcount_end"].where(base_hc["headcount_end"] >= 5)
        base_hc["metric_m02"] = base_hc["hires"].where(base_hc["headcount_end"] >= 5)
        base_hc["metric_m04"] = (100 * base_hc["exits"] / base_hc["headcount_start"].replace({0: pd.NA})).where(base_hc["headcount_end"] >= 10)

        payroll["period_end_date"] = pd.to_datetime(payroll["period_end_date"], errors="coerce")
        pay_joined = payroll.merge(employees[["employee_key"]], on="employee_key", how="inner")
        pay_joined = pay_joined.sort_values("payroll_item_id").drop_duplicates(["employee_id", "run_id"], keep="first")
        pay_joined["period"] = _period(pay_joined["period_end_date"])
        base_pay = pay_joined.groupby(["period", "department_id"], dropna=False).agg(
            gross_pay=("gross_pay", "sum"), employee_count=("employee_id", "nunique")
        ).reset_index()
        base_pay["metric_m07"] = base_pay["gross_pay"].where(base_pay["employee_count"] >= 5)

        attendance["period_end_date"] = pd.to_datetime(attendance["period_end_date"], errors="coerce")
        employees["exit_date"] = pd.to_datetime(employees["exit_date"], errors="coerce")
        att_joined = attendance.merge(employees[["employee_key", "exit_date"]], on="employee_key", how="inner")
        exit_month_end = att_joined["exit_date"] + pd.offsets.MonthEnd(0)
        att_joined = att_joined.loc[att_joined["exit_date"].isna() | (att_joined["period_end_date"] <= exit_month_end)].copy()
        att_joined["period"] = _period(att_joined["period_end_date"])
        att_joined["attendance_days_numerator"] = att_joined["present_days"] + 0.5 * att_joined["half_days_unpaid"]
        base_att = att_joined.groupby(["period", "department_id"], dropna=False).agg(
            present=("attendance_days_numerator", "sum"), scheduled=("scheduled_days", "sum"),
            employee_count=("employee_id", "nunique")
        ).reset_index()
        base_att["metric_m13"] = (base_att["present"] / base_att["scheduled"].replace({0: pd.NA})).where(base_att["employee_count"] >= 5)

        expected = {
            "M01": (base_hc, "month_start_date", "department_id", "metric_m01"),
            "M02": (base_hc, "month_start_date", "department_id", "metric_m02"),
            "M04": (base_hc, "month_start_date", "department_id", "metric_m04"),
            "M07": (base_pay, "period", "department_id", "metric_m07"),
            "M13": (base_att, "period", "department_id", "metric_m13"),
        }
        view_rows = con.execute("SELECT metric_id, period, department_id, metric_value FROM analytics.vw_all_metrics WHERE metric_id IN ('M01','M02','M04','M07','M13')").df()
        view_rows["period"] = pd.to_datetime(view_rows["period"], errors="coerce")
        output = []
        for metric_id, (formula_df, date_col, dept_col, expected_col) in expected.items():
            sql_df = view_rows.loc[view_rows["metric_id"].eq(metric_id)]
            left = formula_df.copy()
            left["period"] = pd.to_datetime(left[date_col], errors="coerce")
            key_values = left[["period", dept_col, expected_col]].rename(columns={dept_col: "department_id", expected_col: "pandas_value"})
            joined = key_values.merge(sql_df[["period", "department_id", "metric_value"]], on=["period", "department_id"], how="outer", indicator=True)
            for _, row in joined.iterrows():
                expected_value, actual_value = row.get("pandas_value"), row.get("metric_value")
                has_exp = pd.notna(expected_value)
                has_sql = pd.notna(actual_value)
                if row["_merge"] != "both":
                    passed = False
                    result = "ROW_MISSING_ON_ONE_SIDE"
                elif not has_exp and not has_sql:
                    passed = True
                    result = "PASS_SUPPRESSION_MATCH"
                elif has_exp and has_sql and abs(float(expected_value) - float(actual_value)) <= max(0.01, abs(float(expected_value)) * 1e-8):
                    passed = True
                    result = "PASS_VALUE_MATCH"
                else:
                    passed = False
                    result = "FAIL_VALUE_OR_SUPPRESSION_MISMATCH"
                output.append({
                    "metric_id": metric_id,
                    "period": row.get("period"),
                    "department_id": row.get("department_id"),
                    "pandas_expected": expected_value,
                    "sql_view_value": actual_value,
                    "result": result,
                    "passed": bool(passed),
                })
        result_df = pd.DataFrame(output)
        result_df.to_csv(REPORTS / "manual_metric_checks.csv", index=False, date_format="%Y-%m-%d")
        return result_df
    finally:
        con.close()


if __name__ == "__main__":
    df = run_manual_checks()
    print(df["result"].value_counts(dropna=False).to_string())
    failures = int((~df["passed"]).sum())
    print(f"Spot checks: {len(df)} rows; failures: {failures}; details: reports/manual_metric_checks.csv")
    if failures:
        raise SystemExit(1)
