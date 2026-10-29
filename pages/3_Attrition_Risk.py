import streamlit as st
import pandas as pd
import plotly.express as px
import duckdb

from src.dashboard_utils import (
    metric,
    load_view,
    apply_period_filter,
    department_filter,
    privacy_note,
)

# ============================================================
# PHASE 2 - TASK 7: ATTRITION ANALYTICS
# ============================================================

st.title("Attrition & Risk Signals")

st.caption(
    "Phase 2 | Task 7 - Employee exits, tenure, "
    "attrition trends and predicted risk"
)

REPORT_START = pd.Timestamp("2025-04-01")
REPORT_END = pd.Timestamp("2026-09-30")

MIN_GROUP_SIZE = 5
MIN_RISK_GROUP_SIZE = 10


# ============================================================
# HELPER: PRIVACY-SAFE ACTUAL EXIT CHARTS
# ============================================================

def show_safe_bar_chart(
    data,
    x_column,
    title,
    x_label,
):
    """
    Display only groups containing at least five exits.
    """

    if data.empty:
        st.info("No exit data is available for this chart.")
        return

    safe = data[
        data["employee_exits"].notna()
        & (data["employee_exits"] >= MIN_GROUP_SIZE)
    ].copy()

    if safe.empty:
        st.info(
            "No groups meet the minimum privacy threshold "
            f"of {MIN_GROUP_SIZE} exits."
        )
        return

    fig = px.bar(
        safe,
        x=x_column,
        y="employee_exits",
        title=title,
        labels={
            x_column: x_label,
            "employee_exits": "Employee Exits",
        },
        text="employee_exits",
    )

    fig.update_traces(textposition="outside")

    fig.update_layout(
        xaxis_title=x_label,
        yaxis_title="Employee Exits",
        margin=dict(t=65, b=40),
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    suppressed = int(
        (
            data["employee_exits"].isna()
            | (data["employee_exits"] < MIN_GROUP_SIZE)
        ).sum()
    )

    if suppressed:
        st.caption(
            f"{suppressed} group(s) suppressed because "
            f"they contain fewer than {MIN_GROUP_SIZE} exits."
        )


# ============================================================
# LOAD UNIQUE EMPLOYEE EXITS
# ============================================================

@st.cache_data
def load_employee_exits():

    con = duckdb.connect(
        "data/pulseiq.duckdb",
        read_only=True,
    )

    try:
        query = """
        WITH ranked_employees AS (
            SELECT
                employee_key,
                employee_id,
                department_id,
                employment_status,
                CAST(hire_date AS DATE) AS hire_date,
                CAST(exit_date AS DATE) AS exit_date,

                ROW_NUMBER() OVER (
                    PARTITION BY employee_id
                    ORDER BY
                        CASE
                            WHEN UPPER(TRIM(is_current)) = 'Y'
                            THEN 0
                            ELSE 1
                        END,
                        valid_from DESC NULLS LAST,
                        employee_key DESC
                ) AS row_num

            FROM warehouse.dim_employee
            WHERE employee_id IS NOT NULL
        )

        SELECT
            employee_id,
            department_id,
            employment_status,
            hire_date,
            exit_date

        FROM ranked_employees

        WHERE row_num = 1
          AND exit_date IS NOT NULL
          AND exit_date BETWEEN DATE '2025-04-01'
                            AND DATE '2026-09-30'
        """

        return con.execute(query).df()

    finally:
        con.close()


exits = load_employee_exits()

# Ensure the dashboard can be refreshed without stale cached data.
if st.sidebar.button("Refresh attrition data"):
    load_employee_exits.clear()
    st.rerun()


# ============================================================
# 1. ACTUAL EMPLOYEE EXITS
# ============================================================

st.header("Actual Employee Exits")

exits["exit_date"] = pd.to_datetime(
    exits["exit_date"],
    errors="coerce",
)

exits["hire_date"] = pd.to_datetime(
    exits["hire_date"],
    errors="coerce",
)

exits = exits.dropna(
    subset=["employee_id", "exit_date"]
).copy()

exits = exits[
    exits["exit_date"].between(
        REPORT_START,
        REPORT_END,
    )
].copy()

if not exits.empty:

    exits["period"] = (
        exits["exit_date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    exits["exit_type"] = (
        exits["employment_status"]
        .astype("string")
        .str.strip()
        .map({
            "Resigned": "Voluntary - Resigned",
            "Terminated": "Other - Terminated",
            "Contract Ended": "Other - Contract Ended",
        })
        .fillna("Other / Unknown")
    )

    total_exits = exits["employee_id"].nunique()

    resignations = exits.loc[
        exits["employment_status"] == "Resigned",
        "employee_id",
    ].nunique()

    other_exits = total_exits - resignations

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Exits",
        f"{total_exits:,}",
    )

    col2.metric(
        "Resignations",
        f"{resignations:,}",
    )

    col3.metric(
        "Other Exits",
        f"{other_exits:,}",
    )

    st.caption(
        "Employees are deduplicated using their latest "
        "available employee record. Resignations are "
        "voluntary exits; terminations and contract "
        "endings are other exits."
    )

    # --------------------------------------------------------
    # MONTHLY EXITS
    # --------------------------------------------------------

    st.subheader("Employee Exits by Month")

    monthly_exits = (
        exits.groupby(
            "period",
            as_index=False,
        )
        .agg(
            employee_exits=(
                "employee_id",
                "nunique",
            )
        )
        .sort_values("period")
    )

    show_safe_bar_chart(
        monthly_exits,
        "period",
        "Monthly Employee Exits",
        "Month",
    )

    # --------------------------------------------------------
    # DEPARTMENT EXITS
    # --------------------------------------------------------

    st.subheader("Employee Exits by Department")

    dept_exits = (
        exits.groupby(
            "department_id",
            dropna=False,
            as_index=False,
        )
        .agg(
            employee_exits=(
                "employee_id",
                "nunique",
            )
        )
    )

    show_safe_bar_chart(
        dept_exits,
        "department_id",
        "Employee Exits by Department",
        "Department",
    )

    st.caption(
        "Department assignments use the selected latest "
        "employee record. Exit counts are not attrition rates."
    )

    # --------------------------------------------------------
    # TENURE ANALYSIS
    # --------------------------------------------------------

    st.subheader("Employee Exits by Tenure")

    tenure_data = exits.dropna(
        subset=["hire_date", "exit_date"]
    ).copy()

    tenure_data["tenure_days"] = (
        tenure_data["exit_date"]
        - tenure_data["hire_date"]
    ).dt.days

    tenure_data = tenure_data[
        tenure_data["tenure_days"] >= 0
    ].copy()

    tenure_data["tenure_years"] = (
        tenure_data["tenure_days"] / 365.25
    )

    tenure_data["tenure_group"] = pd.cut(
        tenure_data["tenure_years"],
        bins=[
            -float("inf"),
            1,
            3,
            5,
            float("inf"),
        ],
        labels=[
            "Under 1 year",
            "1-3 years",
            "3-5 years",
            "5+ years",
        ],
        right=False,
    )

    tenure_exits = (
        tenure_data.groupby(
            "tenure_group",
            observed=True,
            as_index=False,
        )
        .agg(
            employee_exits=(
                "employee_id",
                "nunique",
            )
        )
    )

    show_safe_bar_chart(
        tenure_exits,
        "tenure_group",
        "Employee Exits by Tenure Group",
        "Tenure",
    )

    st.caption(
        "Tenure is calculated using hire date and exit date. "
        "Records with missing dates or invalid negative tenure "
        "are excluded. These are exit counts, not "
        "tenure-specific attrition rates."
    )

    # --------------------------------------------------------
    # EXIT TYPE ANALYSIS
    # --------------------------------------------------------

    st.subheader("Voluntary vs Other Employee Exits")

    exit_types = (
        exits.groupby(
            "exit_type",
            as_index=False,
        )
        .agg(
            employee_exits=(
                "employee_id",
                "nunique",
            )
        )
    )

    show_safe_bar_chart(
        exit_types,
        "exit_type",
        "Employee Exits by Type",
        "Exit Type",
    )

    st.caption(
        "Exit categories are derived from employment_status, "
        "not change_reason. The change_reason field describes "
        "historical employee-record changes."
    )

else:

    total_exits = 0
    resignations = 0
    other_exits = 0

    tenure_data = pd.DataFrame(
        columns=[
            "employee_id",
            "tenure_group",
        ]
    )

    st.info(
        "No employee exits were found in the reporting period."
    )


# ============================================================
# 2. GOVERNED ATTRITION METRICS
# ============================================================

st.header("Governed Attrition Trends")

st.caption(
    "Reporting period: April 2025 - September 2026"
)

metric_charts = [
    ("M04", "Monthly Attrition Rate"),
    ("M05", "Rolling 12-Month Attrition Rate"),
    ("M06", "Voluntary Attrition Rate"),
]

for metric_id, chart_title in metric_charts:

    st.subheader(chart_title)

    data = metric(metric_id)

    if data.empty:
        st.info(
            f"{chart_title} data is unavailable."
        )
        continue

    data = data.copy()

    data["period"] = pd.to_datetime(
        data["period"],
        errors="coerce",
    )

    data = data.dropna(
        subset=["period"]
    )

    data = data[
        data["period"].between(
            REPORT_START,
            REPORT_END,
        )
    ].copy()

    if data.empty:
        st.info(
            "No records exist within the Phase 2 "
            "reporting period."
        )
        continue

    data = apply_period_filter(
        data,
        key_prefix=f"attrition_{metric_id}_phase2",
    )

    data = department_filter(
        data,
        key_prefix=f"attrition_{metric_id}_phase2",
    )

    data["metric_value"] = pd.to_numeric(
        data["metric_value"],
        errors="coerce",
    )

    data = data.dropna(
        subset=["metric_value", "period"]
    )

    if data.empty:
        st.info(
            "No visible metric values exist for the "
            "selected filters. Values may be suppressed "
            "for privacy."
        )
        continue

    fig = px.line(
        data,
        x="period",
        y="metric_value",
        color="department_id",
        markers=True,
        title=chart_title,
        labels={
            "period": "Month",
            "metric_value": "Percent",
            "department_id": "Department",
        },
    )

    fig.update_layout(
        xaxis_title="Month",
        yaxis_title="Percent",
        legend_title="Department",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )


# ============================================================
# 3. PREDICTED ATTRITION RISK
# ============================================================

st.header("Predicted Attrition Risk")

st.info(
    "This section displays model-generated risk estimates. "
    "Predictions are not actual employee exits and do not "
    "confirm future departures."
)

risk = load_view(
    "vw_attrition_risk_department"
)

if not risk.empty:

    risk = risk.copy()

    risk["as_of_date"] = pd.to_datetime(
        risk["as_of_date"],
        errors="coerce",
    )

    risk = risk.dropna(
        subset=["as_of_date", "department_id"]
    )

if not risk.empty:

    latest_date = risk["as_of_date"].max()

    risk_latest = risk[
        risk["as_of_date"] == latest_date
    ].copy()

    st.caption(
        "Latest prediction snapshot: "
        f"{latest_date.strftime('%d %B %Y')}"
    )

    st.subheader("High-Risk Share by Department")

    required_risk_columns = {
        "department_id",
        "as_of_date",
        "employee_count",
        "high_risk_count",
        "group_size",
        "high_risk_share_pct",
    }

    missing_columns = (
        required_risk_columns - set(risk_latest.columns)
    )

    if missing_columns:

        st.warning(
            "The risk view is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    else:

        for column in [
            "employee_count",
            "high_risk_count",
            "group_size",
            "high_risk_share_pct",
        ]:
            risk_latest[column] = pd.to_numeric(
                risk_latest[column],
                errors="coerce",
            )

        safe_risk = risk_latest[
            risk_latest["group_size"].ge(
                MIN_RISK_GROUP_SIZE
            )
            & risk_latest["high_risk_share_pct"].notna()
        ].copy()

        if not safe_risk.empty:

            safe_risk = safe_risk.sort_values(
                "high_risk_share_pct",
                ascending=False,
            )

            fig = px.bar(
                safe_risk,
                x="department_id",
                y="high_risk_share_pct",
                text="high_risk_share_pct",
                title=(
                    "Predicted High-Risk Share by Department"
                ),
                labels={
                    "department_id": "Department",
                    "high_risk_share_pct": (
                        "High-Risk Share (%)"
                    ),
                },
            )

            fig.update_traces(
                texttemplate="%{text:.1f}%",
                textposition="outside",
            )

            fig.update_layout(
                xaxis_title="Department",
                yaxis_title="High-Risk Share (%)",
                yaxis_ticksuffix="%",
            )

            st.plotly_chart(
                fig,
                width="stretch",
            )

            st.subheader("Department-Level Risk Summary")

            st.dataframe(
                safe_risk[
                    [
                        "department_id",
                        "as_of_date",
                        "employee_count",
                        "high_risk_count",
                        "high_risk_share_pct",
                    ]
                ].rename(
                    columns={
                        "department_id": "Department",
                        "as_of_date": "Snapshot Date",
                        "employee_count": "Employees",
                        "high_risk_count": "High-Risk Employees",
                        "high_risk_share_pct": (
                            "High-Risk Share (%)"
                        ),
                    }
                ),
                width="stretch",
                hide_index=True,
            )

        else:

            st.info(
                "No department-level risk results meet "
                f"the minimum group-size threshold of "
                f"{MIN_RISK_GROUP_SIZE}."
            )

    st.caption(
        "Only aggregate department-level results are shown. "
        "Individual employee names and risk scores are not "
        "displayed. High-risk share is a model estimate, "
        "not a confirmed departure rate."
    )

else:

    st.info(
        "No dated attrition risk snapshot is available."
    )


# ============================================================
# 4. KEY FINDINGS
# ============================================================

st.header("Task 7 - Key Findings")

if not exits.empty:

    resignation_share = (
        resignations / total_exits * 100
        if total_exits > 0
        else 0
    )

    if not tenure_data.empty:

        tenure_one_to_three = tenure_data.loc[
            tenure_data["tenure_group"] == "1-3 years",
            "employee_id",
        ].nunique()

    else:
        tenure_one_to_three = 0

    tenure_share = (
        tenure_one_to_three / total_exits * 100
        if total_exits > 0
        else 0
    )

    st.markdown(
        f"""
**1. Resignations among observed exits**

Between April 2025 and September 2026, **{resignations:,}**
of **{total_exits:,}** unique exits were resignations
(**{resignation_share:.1f}%**).

**2. Exits by tenure**

Employees with 1-3 years of tenure accounted for
**{tenure_one_to_three:,}** observed exits
(**{tenure_share:.1f}%** of all observed exits).

These figures are exit counts, not tenure-specific
attrition rates.

**3. Predicted risk is separate from actual exits**

Department-level risk predictions may support workforce
planning, but they do not confirm future employee departures.
"""
    )

else:

    st.info(
        "Key findings cannot be calculated because no "
        "employee exits were found in the reporting period."
    )

st.caption(
    "These findings cover the full Phase 2 reporting period "
    "and do not change with the governed metric chart filters."
)


# ============================================================
# 5. PRIVACY AND GOVERNANCE
# ============================================================

st.warning(
    "Privacy guardrail: actual-exit chart groups below five "
    "are suppressed. Predicted high-risk groups below ten "
    "are suppressed. Individual employee names and "
    "person-level risk scores are not displayed. Predicted "
    "risk should be used as a planning signal, not as a "
    "conclusion about any employee."
)

privacy_note()
