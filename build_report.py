
from pathlib import Path
from datetime import datetime, timezone
import argparse

import duckdb
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "data" / "pulseiq.duckdb"
REPORTS = ROOT / "reports"


def get_month_data(con, view, month_start):
    return con.execute(
        f"SELECT * FROM analytics.{view} WHERE period = ?",
        [month_start]
    ).fetchdf()


def build_report(month):
    month_start = datetime.strptime(month, "%Y-%m").date()

    month_end = datetime(
        month_start.year + (month_start.month == 12),
        1 if month_start.month == 12 else month_start.month + 1,
        1
    ).date()

    if not DB_FILE.exists():
        raise FileNotFoundError(f"Database not found: {DB_FILE}")

    REPORTS.mkdir(exist_ok=True)

    con = duckdb.connect(str(DB_FILE), read_only=True)

    try:
        # 1. Workforce KPIs
        workforce = get_month_data(
            con, "vw_company_kpis", month_start
        )

        # 2. Financial performance
        finance = get_month_data(
            con, "vw_finance_monthly", month_start
        )

        # 3. Monthly expense analysis
        categories = con.execute("""
            SELECT
                a.account_name AS category,
                SUM(e.amount_excl_gst) AS spend_excl_gst,
                SUM(e.total_amount) AS spend_incl_gst,
                COUNT(*) AS bill_count
            FROM analytics.fact_expense_valid e
            LEFT JOIN warehouse.dim_account a
                ON e.category_account = a.account_code
            WHERE e.expense_date >= ?
              AND e.expense_date < ?
            GROUP BY 1
            ORDER BY spend_excl_gst DESC
        """, [month_start, month_end]).fetchdf()

        vendors = con.execute("""
            SELECT
                v.vendor_name,
                SUM(e.amount_excl_gst) AS spend_excl_gst,
                SUM(e.total_amount) AS spend_incl_gst,
                COUNT(*) AS bill_count
            FROM analytics.fact_expense_valid e
            LEFT JOIN warehouse.dim_vendor v
                ON e.vendor_id = v.vendor_id
            WHERE e.expense_date >= ?
              AND e.expense_date < ?
            GROUP BY 1
            ORDER BY spend_excl_gst DESC
            LIMIT 10
        """, [month_start, month_end]).fetchdf()

        departments = con.execute("""
            SELECT
                department_id,
                SUM(total_expense) AS spend_incl_gst,
                SUM(bill_count) AS bill_count
            FROM analytics.vw_expense_monthly_department
            WHERE period = ?
            GROUP BY department_id
            ORDER BY spend_incl_gst DESC
        """, [month_start]).fetchdf()

        expense_reconciliation = con.execute("""
            SELECT
                COUNT(*) AS bill_count,
                SUM(amount_excl_gst) AS spend_excl_gst,
                SUM(total_amount) AS spend_incl_gst
            FROM analytics.fact_expense_valid
            WHERE expense_date >= ?
              AND expense_date < ?
        """, [month_start, month_end]).fetchdf()

        department_total = con.execute("""
            SELECT
                SUM(total_expense) AS spend_incl_gst,
                SUM(bill_count) AS bill_count
            FROM analytics.vw_expense_monthly_department
            WHERE period = ?
        """, [month_start]).fetchdf()

        # 4. Cash collections
        collections = get_month_data(
            con, "vw_cash_collections_monthly", month_start
        )

        # 5. Latest available data-quality results
        latest_dq_run = con.execute("""
            SELECT MAX(run_at_utc)
            FROM analytics.vw_dq_results
        """).fetchone()[0]

        if latest_dq_run:
            dq = con.execute("""
                SELECT
                    check_id,
                    check_name,
                    severity,
                    rows_affected,
                    status,
                    description,
                    recommended_action,
                    run_at_utc
                FROM analytics.vw_dq_results
                WHERE run_at_utc = ?
                ORDER BY severity, check_id
            """, [latest_dq_run]).fetchdf()
        else:
            dq = pd.DataFrame()

        # Latest available reporting periods
        reporting_periods = {}

        for view in [
            "vw_company_kpis",
            "vw_finance_monthly",
            "vw_cash_collections_monthly"
        ]:
            reporting_periods[view] = con.execute(
                f"SELECT MAX(period) FROM analytics.{view}"
            ).fetchone()[0]

        # Validate selected reporting month
        if workforce.empty and finance.empty and collections.empty:
            raise ValueError(
                f"No workforce, finance, or collections data "
                f"available for {month}."
            )

        if categories.empty:
            raise ValueError(
                f"No expense data available for {month}."
            )

        # Expense reconciliation
        expense_values = expense_reconciliation.iloc[0]
        department_values = department_total.iloc[0]

        gst_inclusive_match = (
            pd.notna(expense_values["spend_incl_gst"])
            and pd.notna(department_values["spend_incl_gst"])
            and abs(
                expense_values["spend_incl_gst"]
                - department_values["spend_incl_gst"]
            ) < 0.01
        )

        bill_count_match = (
            expense_values["bill_count"]
            == department_values["bill_count"]
        )

        # Executive summary helper
        def first_value(df, column):
            if df.empty or column not in df.columns:
                return None
            return df.iloc[0][column]

        # Executive summary
        summary = [
            ["Reporting month", month],
            [
                "Reporting period",
                f"{month_start} to {month_end} (exclusive)"
            ],
            ["Headcount", first_value(workforce, "headcount")],
            ["Hires", first_value(workforce, "hires")],
            ["Exits", first_value(workforce, "exits")],
            [
                "Monthly attrition (%)",
                first_value(workforce, "attrition_pct")
            ],
            [
                "Attendance (%)",
                first_value(workforce, "attendance_rate") * 100
                if first_value(workforce, "attendance_rate") is not None
                else None
            ],
            [
                "Employer payroll cost (INR)",
                first_value(workforce, "payroll_cost")
            ],
            ["Revenue (INR)", first_value(finance, "revenue")],
            [
                "Finance expenses (INR)",
                first_value(finance, "expenses")
            ],
            ["Net profit (INR)", first_value(finance, "net_profit")],
            [
                "Operating margin (%)",
                first_value(finance, "operating_margin_pct")
            ],
            [
                "Invoices paid",
                first_value(collections, "invoices_paid")
            ],
            [
                "Cash collected (INR)",
                first_value(collections, "cash_collected")
            ],
            ["Expense bills", expense_values["bill_count"]],
            [
                "Expense excluding GST (INR)",
                expense_values["spend_excl_gst"]
            ],
            [
                "Expense including GST (INR)",
                expense_values["spend_incl_gst"]
            ],
            [
                "Expense GST-inclusive reconciliation",
                "PASS" if gst_inclusive_match else "FAIL"
            ],
            [
                "Expense bill-count reconciliation",
                "PASS" if bill_count_match else "FAIL"
            ],
            ["Latest DQ run (UTC)", latest_dq_run],
            [
                "Latest available reporting period: workforce",
                reporting_periods["vw_company_kpis"]
            ],
            [
                "Latest available reporting period: finance",
                reporting_periods["vw_finance_monthly"]
            ],
            [
                "Latest available reporting period: collections",
                reporting_periods["vw_cash_collections_monthly"]
            ],
            [
                "Report generated (UTC)",
                datetime.now(timezone.utc).isoformat()
            ],
        ]

        summary_df = pd.DataFrame(
            summary,
            columns=["Metric", "Value"]
        )

        # Definitions and notes
        notes = pd.DataFrame([
            ["Reporting month", month],
            [
                "Reporting date range",
                f"{month_start} to {month_end} (end date exclusive)"
            ],
            ["Workforce source", "analytics.vw_company_kpis"],
            ["Finance source", "analytics.vw_finance_monthly"],
            ["Expense source", "analytics.fact_expense_valid"],
            [
                "Department expense source",
                "analytics.vw_expense_monthly_department"
            ],
            [
                "Collections source",
                "analytics.vw_cash_collections_monthly"
            ],
            ["Data quality source", "analytics.vw_dq_results"],
            [
                "Expense excluding GST",
                "Calculated using amount_excl_gst"
            ],
            [
                "Expense including GST",
                "Calculated using total_amount"
            ],
            [
                "Expense reconciliation",
                "GST-inclusive fact total compared with the monthly "
                "department view; bill counts compared separately."
            ],
            [
                "Cash collections caveat",
                "Based on amount_paid grouped by invoice last_payment_date. "
                "This is not a transaction-level bank reconciliation."
            ],
            [
                "Data quality caveat",
                "The quality sheet displays the latest available DQ run. "
                "It is not necessarily specific to the selected report month."
            ],
            [
                "Reporting period note",
                "Latest available reporting periods are shown for each "
                "source. Actual source-data extraction timestamps are "
                "not available."
            ],
            [
                "Privacy note",
                "This workbook contains aggregated reporting data, "
                "not employee-level personal records."
            ],
        ], columns=["Item", "Description"])

        output_file = REPORTS / f"monthly_report_{month}.xlsx"

        # Create Excel workbook
        with pd.ExcelWriter(
            output_file,
            engine="openpyxl"
        ) as writer:

            summary_df.to_excel(
                writer,
                sheet_name="Executive Summary",
                index=False
            )

            workforce.to_excel(
                writer,
                sheet_name="Workforce KPIs",
                index=False
            )

            finance.to_excel(
                writer,
                sheet_name="Finance",
                index=False
            )

            categories.to_excel(
                writer,
                sheet_name="Expense Categories",
                index=False
            )

            vendors.to_excel(
                writer,
                sheet_name="Top Vendors",
                index=False
            )

            departments.to_excel(
                writer,
                sheet_name="Expense Departments",
                index=False
            )

            collections.to_excel(
                writer,
                sheet_name="Cash Collections",
                index=False
            )

            dq.to_excel(
                writer,
                sheet_name="Data Quality",
                index=False
            )

            notes.to_excel(
                writer,
                sheet_name="Definitions & Notes",
                index=False
            )

        # Workbook formatting
        wb = load_workbook(output_file)

        for ws in wb.worksheets:
            ws.freeze_panes = "A2"
            ws.sheet_view.showGridLines = False

            if ws.max_row >= 1:
                ws.auto_filter.ref = ws.dimensions

            # Header formatting
            for cell in ws[1]:
                cell.font = Font(
                    bold=True,
                    color="FFFFFF"
                )

                cell.fill = PatternFill(
                    fill_type="solid",
                    fgColor="1F4E78"
                )

                cell.alignment = Alignment(
                    horizontal="center",
                    vertical="center"
                )

            # Column widths
            for column_cells in ws.columns:
                max_length = max(
                    len(str(cell.value))
                    if cell.value is not None else 0
                    for cell in column_cells
                )

                column_letter = get_column_letter(
                    column_cells[0].column
                )

                ws.column_dimensions[column_letter].width = min(
                    max(max_length + 3, 14),
                    55
                )

        wb.save(output_file)
        wb.close()

        print("\nMONTHLY REPORT CREATED SUCCESSFULLY")
        print("File:", output_file)
        print("Month:", month)
        print(
            "Expense GST-inclusive reconciliation:",
            "PASS" if gst_inclusive_match else "FAIL"
        )
        print(
            "Expense bill-count reconciliation:",
            "PASS" if bill_count_match else "FAIL"
        )

    finally:
        con.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate a monthly PulseIQ Excel report."
    )

    parser.add_argument(
        "--month",
        required=True,
        help="Reporting month in YYYY-MM format, e.g. 2026-09"
    )

    args = parser.parse_args()

    try:
        datetime.strptime(args.month, "%Y-%m")
    except ValueError:
        parser.error(
            "Month must use YYYY-MM format, e.g. 2026-09"
        )

    build_report(args.month)


if __name__ == "__main__":
    main()
