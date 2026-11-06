import streamlit as st
import pandas as pd
import plotly.express as px

from src.dashboard_utils import load_view, privacy_note


# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.title("Cross-Department Impact View")

st.caption(
    "Phase 3 | Task 13 - Department-wise workforce, "
    "attendance, attrition, payroll and operational impact"
)


# --------------------------------------------------
# LOAD GOVERNED ANALYTICS VIEWS
# --------------------------------------------------

metrics = load_view("vw_all_metrics")
departments = load_view("vw_department_lookup")
overtime = load_view("vw_attendance_overtime_monthly")
risk = load_view("vw_attrition_risk_department")
expenses = load_view("vw_expense_monthly_department")
leave = load_view("vw_leave_days_monthly")

if metrics.empty:
    st.info("Run the pipeline first.")
    st.stop()

if departments.empty:
    st.warning("Department lookup is unavailable.")
    st.stop()


# --------------------------------------------------
# DEPARTMENT NAME MAPPING
# --------------------------------------------------

department_map = departments.set_index(
    "department_id"
)["department_name"].to_dict()


# --------------------------------------------------
# REPORTING PERIOD
# --------------------------------------------------

start_date = pd.Timestamp("2025-04-01")
end_date = pd.Timestamp("2026-09-01")


def filter_period(df):
    df = df.copy()

    if "period" in df.columns:
        df["period"] = pd.to_datetime(
            df["period"], errors="coerce"
        )
        df = df[
            (df["period"] >= start_date)
            & (df["period"] <= end_date)
        ]

    return df


# --------------------------------------------------
# WORKFORCE METRICS
# --------------------------------------------------

selected_ids = ["M01", "M04", "M09", "M13"]

sub = metrics[
    metrics["metric_id"].isin(selected_ids)
].copy()

sub = filter_period(sub)

base = sub.pivot_table(
    index=["period", "department_id"],
    columns="metric_id",
    values="metric_value",
    aggfunc="first"
).reset_index()

base = base.rename(columns={
    "M01": "headcount",
    "M04": "monthly_attrition_pct",
    "M09": "payroll_cost_inr",
    "M13": "attendance_rate"
})

base["department_name"] = base[
    "department_id"
].map(department_map)

base = base[
    base["department_name"].notna()
    & (base["department_id"] != "D00")
].copy()

if base.empty:
    st.info("No comparable department data is available.")
    st.stop()


# --------------------------------------------------
# FILTERS
# --------------------------------------------------

st.subheader("Dashboard Filters")

departments_available = sorted(
    base["department_name"].dropna().unique()
)

selected_departments = st.multiselect(
    "Select departments",
    departments_available,
    default=departments_available
)

base = base[
    base["department_name"].isin(selected_departments)
].copy()

if base.empty:
    st.warning("Select at least one department.")
    st.stop()


# --------------------------------------------------
# LATEST DEPARTMENT SNAPSHOT
# --------------------------------------------------

latest_period = base["period"].max()

latest = base[
    base["period"] == latest_period
].copy()

st.caption(
    f"Latest workforce reporting period: "
    f"{latest_period.strftime('%B %Y')}"
)


# --------------------------------------------------
# KPI CARDS
# --------------------------------------------------

total_headcount = latest["headcount"].sum(
    min_count=1
)

total_payroll = latest["payroll_cost_inr"].sum(
    min_count=1
)

avg_attendance = latest["attendance_rate"].mean() * 100

avg_attrition = latest[
    "monthly_attrition_pct"
].mean()

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Visible Headcount",
    f"{total_headcount:,.0f}"
    if pd.notna(total_headcount) else "N/A"
)

c2.metric(
    "Visible Payroll",
    f"₹{total_payroll / 10000000:,.2f} Cr"
    if pd.notna(total_payroll) else "N/A"
)

c3.metric(
    "Average Attendance",
    f"{avg_attendance:.2f}%"
    if pd.notna(avg_attendance) else "N/A"
)

c4.metric(
    "Average Monthly Attrition",
    f"{avg_attrition:.2f}%"
    if pd.notna(avg_attrition) else "N/A"
)


# --------------------------------------------------
# DEPARTMENT WORKFORCE COMPARISON
# --------------------------------------------------

st.divider()
st.subheader("1. Department Workforce Comparison")

a, b = st.columns(2)

with a:
    fig = px.bar(
        latest.dropna(subset=["headcount"]),
        x="department_name",
        y="headcount",
        title="Department-wise Headcount",
        labels={
            "department_name": "Department",
            "headcount": "Employees"
        }
    )

    st.plotly_chart(fig, width="stretch")

with b:
    fig = px.bar(
        latest.dropna(subset=["payroll_cost_inr"]),
        x="department_name",
        y="payroll_cost_inr",
        title="Department-wise Payroll Cost",
        labels={
            "department_name": "Department",
            "payroll_cost_inr": "Payroll (INR)"
        }
    )

    st.plotly_chart(fig, width="stretch")


# --------------------------------------------------
# ATTENDANCE AND ATTRITION
# --------------------------------------------------

st.divider()
st.subheader("2. Attendance and Attrition Analysis")

a, b = st.columns(2)

with a:
    attendance_data = base.dropna(
        subset=["attendance_rate"]
    )

    fig = px.line(
        attendance_data,
        x="period",
        y="attendance_rate",
        color="department_name",
        title="Monthly Attendance Trends",
        labels={
            "period": "Month",
            "attendance_rate": "Attendance Ratio",
            "department_name": "Department"
        }
    )

    st.plotly_chart(fig, width="stretch")

with b:
    attrition_data = base.dropna(
        subset=["monthly_attrition_pct"]
    )

    fig = px.line(
        attrition_data,
        x="period",
        y="monthly_attrition_pct",
        color="department_name",
        title="Monthly Attrition Trends",
        labels={
            "period": "Month",
            "monthly_attrition_pct": "Attrition (%)",
            "department_name": "Department"
        }
    )

    st.plotly_chart(fig, width="stretch")


# --------------------------------------------------
# ATTENDANCE VS ATTRITION
# --------------------------------------------------

st.subheader("Attendance vs Monthly Attrition")

comparison = base.dropna(
    subset=[
        "attendance_rate",
        "monthly_attrition_pct",
        "headcount"
    ]
)

fig = px.scatter(
    comparison,
    x="attendance_rate",
    y="monthly_attrition_pct",
    size="headcount",
    color="department_name",
    hover_data=["period", "payroll_cost_inr"],
    title="Attendance and Attrition by Department",
    labels={
        "attendance_rate": "Attendance Ratio",
        "monthly_attrition_pct": "Attrition (%)",
        "department_name": "Department"
    }
)

st.plotly_chart(fig, width="stretch")


# --------------------------------------------------
# OVERTIME ANALYSIS
# --------------------------------------------------

st.divider()
st.subheader("3. Overtime Analysis")

overtime = filter_period(overtime)

if not overtime.empty:
    overtime["department_name"] = overtime[
        "department_id"
    ].map(department_map)

    overtime = overtime[
        overtime["department_name"].isin(
            selected_departments
        )
    ]

    fig = px.bar(
        overtime,
        x="period",
        y="overtime_hours",
        color="department_name",
        title="Monthly Overtime Hours by Department",
        labels={
            "period": "Month",
            "overtime_hours": "Overtime Hours",
            "department_name": "Department"
        },
        barmode="group"
    )

    st.plotly_chart(fig, width="stretch")
else:
    st.info("Overtime data is unavailable.")


# --------------------------------------------------
# ATTRITION RISK
# --------------------------------------------------

st.divider()
st.subheader("4. Department Attrition Risk")

if not risk.empty:
    risk = risk.copy()

    risk["department_name"] = risk[
        "department_id"
    ].map(department_map)

    risk = risk[
        risk["department_name"].isin(
            selected_departments
        )
        & (risk["department_id"] != "D00")
    ]

    if not risk.empty:
        fig = px.bar(
            risk,
            x="department_name",
            y="high_risk_share_pct",
            title="High-Risk Employee Share by Department",
            labels={
                "department_name": "Department",
                "high_risk_share_pct": "High-Risk Share (%)"
            }
        )

        st.plotly_chart(fig, width="stretch")

        st.dataframe(
            risk[[
                "department_name",
                "employee_count",
                "high_risk_count",
                "high_risk_share_pct"
            ]].sort_values(
                "high_risk_share_pct",
                ascending=False
            ),
            width="stretch",
            hide_index=True
        )
else:
    st.info("Attrition risk data is unavailable.")


# --------------------------------------------------
# DEPARTMENT EXPENSES
# --------------------------------------------------

st.divider()
st.subheader("5. Department Expense Analysis")

expenses = filter_period(expenses)

if not expenses.empty:
    expenses["department_name"] = expenses[
        "department_id"
    ].map(department_map)

    expenses = expenses[
        expenses["department_name"].isin(
            selected_departments
        )
    ]

    fig = px.bar(
        expenses,
        x="period",
        y="total_expense",
        color="department_name",
        title="Monthly Expenses by Department",
        labels={
            "period": "Month",
            "total_expense": "Expense (INR)",
            "department_name": "Department"
        },
        barmode="group"
    )

    st.plotly_chart(fig, width="stretch")
else:
    st.info("Department expense data is unavailable.")


# --------------------------------------------------
# LEAVE TRENDS
# --------------------------------------------------

st.divider()
st.subheader("6. Leave Trends")

if not leave.empty:
    leave = filter_period(leave)

    if not leave.empty:
        fig = px.line(
            leave,
            x="period",
            y="visible_leave_days",
            color="leave_type_code",
            markers=True,
            title="Monthly Leave Days by Leave Type",
            labels={
                "period": "Month",
                "visible_leave_days": "Leave Days",
                "leave_type_code": "Leave Type"
            }
        )

        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No leave records in the selected period.")
else:
    st.info("Leave data is unavailable.")


# --------------------------------------------------
# DETAILED DEPARTMENT DATA
# --------------------------------------------------

st.divider()
st.subheader("7. Department Performance Details")

display_data = base.sort_values(
    ["period", "department_name"],
    ascending=[False, True]
).copy()

display_data["attendance_rate"] = (
    display_data["attendance_rate"] * 100
)

st.dataframe(
    display_data,
    width="stretch",
    hide_index=True
)


# --------------------------------------------------
# GOVERNANCE AND INTERPRETATION
# --------------------------------------------------

st.divider()

st.warning(
    "This dashboard provides descriptive comparisons. "
    "It does not establish that attendance causes attrition "
    "or that payroll and expenses cause business outcomes."
)

st.caption(
    "Privacy note: Department-level values suppressed by "
    "the minimum group-size rule are not reconstructed. "
    "Leave trends are shown by leave type because the "
    "governed leave view does not contain department IDs."
)

privacy_note()