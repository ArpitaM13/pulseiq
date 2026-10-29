import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard_utils import metric, load_view, apply_period_filter, department_filter, money, privacy_note

st.title("Payroll Cost & Budget")
st.caption("Phase 2  |  Tasks 9-10 - Employer cost, payroll mix, reconciliation and targets")
pay=metric("M09")
if pay.empty: st.info("Run the pipeline first."); st.stop()
pay=apply_period_filter(pay, key_prefix="payroll_total"); pay=department_filter(pay, key_prefix="payroll_total")
visible=pay.dropna(subset=["metric_value"])
if not visible.empty:
    total=visible.groupby("period",as_index=False).metric_value.sum()
    fig=px.line(total,x="period",y="metric_value",markers=True,title="Validated employer payroll cost by month",labels={"period":"Month","metric_value":"INR"})
    st.plotly_chart(fig,width="stretch")
for mid,title in [("M10","Cost per head"),("M11","Overtime share (%)"),("M12","Variable pay share (%)")]:
    d=metric(mid).dropna(subset=["metric_value"])
    if not d.empty:
        d=apply_period_filter(d, key_prefix=f"payroll_{mid.lower()}")
        fig=px.line(d,x="period",y="metric_value",color="department_id",markers=True,title=title,labels={"period":"Month","metric_value":"Value"})
        st.plotly_chart(fig,width="stretch")
b=load_view("vw_budget_vs_actual")
if not b.empty:
    st.subheader("Budget versus actual")
    b=apply_period_filter(b, date_col="month", key_prefix="payroll_budget"); b=department_filter(b, key_prefix="payroll_budget")
    shown=b.dropna(subset=["visible_actual_cost","budget_cost"])
    if not shown.empty:
        fig=px.bar(shown,x="month",y=["visible_actual_cost","budget_cost"],barmode="group",color_discrete_sequence=["#2563eb","#94a3b8"],title="Budget versus actual payroll cost",labels={"month":"Month","value":"INR"})
        st.plotly_chart(fig,width="stretch")
        st.dataframe(shown[["month","department_id","visible_actual_cost","budget_cost","variance","variance_pct"]].sort_values("month",ascending=False),width="stretch",hide_index=True)
    st.caption("Budget comparison is available only for department-months where both budget and validated payroll cost exist.")
        # --------------------------------------------------
    # TASK 10: BUDGET VS ACTUAL ANALYSIS
    # --------------------------------------------------

    st.divider()
    st.header("Task 10 - Budget vs Actual Analysis")

    if not shown.empty:

        total_budget = shown["budget_cost"].sum()
        total_actual = shown["visible_actual_cost"].sum()
        total_variance = total_actual - total_budget

        variance_pct = (
            100 * total_variance / total_budget
            if total_budget != 0 else 0
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Payroll Budget", money(total_budget))
        c2.metric("Actual Payroll Cost", money(total_actual))
        c3.metric("Budget Variance", money(total_variance))
        c4.metric("Variance %", f"{variance_pct:.2f}%")

        st.caption(
            "Positive variance indicates overspending. "
            "Negative variance indicates spending below budget."
        )

        st.subheader("Department-wise Budget Variance")

        dept_variance = (
            shown.groupby("department_id", as_index=False)
            .agg(
                budget=("budget_cost", "sum"),
                actual=("visible_actual_cost", "sum")
            )
        )

        dept_variance["variance"] = (
            dept_variance["actual"] - dept_variance["budget"]
        )

        dept_variance["variance_pct"] = (
            100 * dept_variance["variance"]
            / dept_variance["budget"].replace(0, float("nan"))
        )

        dept_variance["status"] = dept_variance["variance"].apply(
            lambda x: "Over Budget" if x > 0
            else "Under Budget" if x < 0
            else "On Budget"
        )

        fig = px.bar(
            dept_variance.sort_values("variance"),
            x="variance",
            y="department_id",
            orientation="h",
            color="status",
            title="Payroll Budget Variance by Department",
            labels={
                "variance": "Variance (INR)",
                "department_id": "Department"
            }
        )

        fig.add_vline(x=0, line_dash="dash")
        st.plotly_chart(fig, width="stretch")

        st.subheader("Budget Status Summary")

        status_counts = shown.assign(
            status=shown.apply(
                lambda row: (
                    "Over Budget"
                    if row["visible_actual_cost"] > row["budget_cost"]
                    else "Under Budget"
                    if row["visible_actual_cost"] < row["budget_cost"]
                    else "On Budget"
                ),
                axis=1
            )
        )["status"].value_counts()

        st.dataframe(
            status_counts.rename_axis("Budget Status")
            .reset_index(name="Department-Months"),
            width="stretch",
            hide_index=True
        )

        st.subheader("Department Budget Performance")

        st.dataframe(
            dept_variance.sort_values(
                "variance", ascending=False
            ).round(2),
            width="stretch",
            hide_index=True
        )

        st.subheader("Key Findings")

        highest_over = dept_variance.loc[
            dept_variance["variance"].idxmax()
        ]

        highest_saving = dept_variance.loc[
            dept_variance["variance"].idxmin()
        ]

        st.write(
            f"1. Overall payroll variance is "
            f"{variance_pct:+.2f}% against budget."
        )

        st.write(
            f"2. {highest_over['department_id']} has the "
            f"highest absolute overspending at "
            f"{money(highest_over['variance'])}."
        )

        st.write(
            f"3. {highest_saving['department_id']} has the "
            f"largest savings at "
            f"{money(abs(highest_saving['variance']))}."
        )

        st.caption(
            "All calculations use only department-month records "
            "where validated payroll cost and budget are available. "
            "Results follow the selected date and department filters."
        )
    # --------------------------------------------------
# TASK 9: PAYROLL RECONCILIATION
# --------------------------------------------------

import duckdb

st.divider()
st.header("Task 9 — Payroll Reconciliation")
st.caption(
    "Monthly payroll validation against the reconciliation "
    "reference, including ledger expense comparison."
)

con = duckdb.connect("data/pulseiq.duckdb", read_only=True)

try:
    reconciliation = con.execute("""
        WITH payroll AS (
            SELECT
                STRFTIME(period_end_date, '%Y-%m') AS month,
                COUNT(DISTINCT employee_id) AS employees_paid,
                SUM(gross_pay) AS gross_pay,
                SUM(net_pay) AS net_pay,
                SUM(employer_cost) AS employer_cost
            FROM analytics.fact_payroll_valid
            GROUP BY 1
        ),
        reference AS (
            SELECT
                SUBSTR(month, 1, 7) AS month,
                employees_paid AS expected_employees,
                payroll_gross_pay,
                payroll_net_pay,
                payroll_employer_cost,
                ledger_salary_related_expense
            FROM warehouse.reconciliation_answer_key
        )
        SELECT
            COALESCE(p.month, r.month) AS month,
            p.employees_paid,
            r.expected_employees,
            ROUND(p.gross_pay - r.payroll_gross_pay, 2)
                AS gross_difference,
            ROUND(p.net_pay - r.payroll_net_pay, 2)
                AS net_difference,
            ROUND(p.employer_cost - r.payroll_employer_cost, 2)
                AS employer_cost_difference,
            ROUND(
                p.employer_cost - r.ledger_salary_related_expense,
                2
            ) AS ledger_difference
        FROM payroll p
        FULL OUTER JOIN reference r
            ON p.month = r.month
        ORDER BY month
    """).df()

    st.subheader("Monthly Reconciliation Results")

    if not reconciliation.empty:
        diff_cols = [
            "gross_difference",
            "net_difference",
            "employer_cost_difference",
            "ledger_difference"
        ]

        matched = (
            reconciliation["employees_paid"].notna()
            & reconciliation["expected_employees"].notna()
            & (
                reconciliation["employees_paid"]
                == reconciliation["expected_employees"]
            )
            & reconciliation[diff_cols].notna().all(axis=1)
            & reconciliation[diff_cols].abs().le(0.01).all(axis=1)
        )

        months_checked = len(reconciliation)
        months_matched = int(matched.sum())

        c1, c2, c3 = st.columns(3)

        c1.metric("Months Checked", months_checked)
        c2.metric("Months Reconciled", months_matched)
        c3.metric(
            "Months With Exceptions",
            months_checked - months_matched
        )

        st.dataframe(
            reconciliation,
            width="stretch",
            hide_index=True
        )

        if months_matched == months_checked:
            st.success(
                "All payroll months match the reconciliation reference."
            )
        else:
            st.warning(
                "Some months contain reconciliation differences "
                "or missing reference data."
            )

    st.subheader("Payroll Data Validation")

    validation = con.execute("""
        WITH checked AS (
            SELECT
                p.payroll_item_id,
                p.period_end_date,
                CASE
                    WHEN NOT EXISTS (
                        SELECT 1
                        FROM warehouse.dim_employee d
                        WHERE d.employee_key = p.employee_key
                    )
                    THEN 'Unmatched employee key'

                    WHEN ROW_NUMBER() OVER (
                        PARTITION BY p.employee_id, p.run_id
                        ORDER BY p.payroll_item_id
                    ) > 1
                    THEN 'Duplicate employee/run'

                    ELSE 'Valid'
                END AS validation_status
            FROM warehouse.fact_payroll p
        )
        SELECT
            validation_status,
            COUNT(*) AS records
        FROM checked
        GROUP BY validation_status
        ORDER BY validation_status
    """).df()

    st.dataframe(
        validation,
        width="stretch",
        hide_index=True
    )

    st.caption(
        "Validated payroll excludes duplicate employee/run records "
        "and records with unmatched employee keys. "
        "No individual employee salary information is displayed."
    )

    st.info(
        "Reconciliation compares validated payroll with the provided "
        "reference table. The ledger expense comparison uses the "
        "reference table's ledger figures, not a separately "
        "recomputed ledger total."
    )

finally:
    con.close()
privacy_note()
