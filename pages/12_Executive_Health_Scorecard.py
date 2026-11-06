
import streamlit as st
import pandas as pd

from src.dashboard_utils import (
    metric,
    load_view,
    money_compact,
    privacy_note,
)

# --------------------------------------------------
# Page setup
# --------------------------------------------------

st.set_page_config(
    page_title="Executive Health Scorecard",
    page_icon="📊",
    layout="wide",
)

st.title("Executive Company-Health Scorecard")
st.caption(
    "Phase 3 | Task 15 — Eight headline KPIs "
    "for workforce, finance, collections and delivery"
)

# --------------------------------------------------
# Load governed metric views
# --------------------------------------------------

metric_ids = [
    "M01", "M09", "M13", "M16",
    "M17", "M18", "M21", "M22",
]

data = {mid: metric(mid) for mid in metric_ids}

targets = load_view("vw_kpi_target_performance")

if all(df.empty for df in data.values()):
    st.info("Run the pipeline first, then refresh this page.")
    st.stop()

# Convert dates
for df in data.values():
    if not df.empty:
        df["period"] = pd.to_datetime(
            df["period"], errors="coerce"
        )
        df["month"] = df["period"].dt.to_period("M")

if not targets.empty:
    targets["month"] = pd.to_datetime(
        targets["month"], errors="coerce"
    ).dt.to_period("M")

# --------------------------------------------------
# Month selector
# --------------------------------------------------

available_months = set()

for df in data.values():
    if not df.empty:
        available_months.update(
            df["month"].dropna().tolist()
        )

if not targets.empty:
    available_months.update(
        targets["month"].dropna().tolist()
    )

if not available_months:
    st.warning("No valid reporting months are available.")
    st.stop()

months = sorted(available_months, reverse=True)

selected_month = st.selectbox(
    "Reporting month",
    months,
    index=0,
    format_func=lambda x: x.strftime("%B %Y"),
)

st.caption(
    f"Selected reporting month: "
    f"{selected_month.strftime('%B %Y')}"
)

# --------------------------------------------------
# Helper functions
# --------------------------------------------------

def month_rows(metric_id):
    df = data[metric_id]

    if df.empty:
        return df

    return df.loc[
        df["month"] == selected_month
    ].copy()


def visible_sum(metric_id):
    df = month_rows(metric_id)

    if df.empty:
        return None

    values = df["metric_value"].dropna()

    if values.empty:
        return None

    return float(values.sum())


def company_value(metric_id):
    df = month_rows(metric_id)

    if df.empty:
        return None

    values = df["metric_value"].dropna()

    if values.empty:
        return None

    return float(values.sum())


def get_target_values(kpi_type):
    if targets.empty:
        return None, None

    rows = targets.loc[
        targets["month"] == selected_month
    ].copy()

    if rows.empty:
        return None, None

    if kpi_type == "attendance":
        actual_col = "attendance_rate"
        target_col = "attendance_rate_target"
    else:
        actual_col = "task_completion_pct"
        target_col = "task_completion_target_pct"

    rows[actual_col] = pd.to_numeric(
        rows[actual_col], errors="coerce"
    )

    rows[target_col] = pd.to_numeric(
        rows[target_col], errors="coerce"
    )

    rows = rows.dropna(
        subset=[actual_col, target_col]
    )

    if rows.empty:
        return None, None

    return (
        float(rows[actual_col].mean()),
        float(rows[target_col].mean()),
    )


def trend_text(metric_id, aggregation="sum"):
    df = data[metric_id]

    if df.empty:
        return None

    monthly = df.dropna(
        subset=["period", "metric_value"]
    ).copy()

    if monthly.empty:
        return None

    monthly["month"] = (
        monthly["period"].dt.to_period("M")
    )

    if aggregation == "average":
        grouped = monthly.groupby("month")[
            "metric_value"
        ].mean()
    else:
        grouped = monthly.groupby("month")[
            "metric_value"
        ].sum()

    current = grouped.get(selected_month)

    previous = grouped.loc[
        grouped.index < selected_month
    ]

    if current is None or previous.empty:
        return None

    prior = float(previous.iloc[-1])
    difference = float(current) - prior

    # Attendance metric is stored as a ratio.
    if metric_id == "M13":
        return (
            f"{difference * 100:+.2f} "
            "percentage points vs prior month"
        )

    # Operating margin is already stored as a percentage.
    if metric_id == "M18":
        return (
            f"{difference:+.2f} "
            "percentage points vs prior month"
        )

    if metric_id == "M21":
        return (
            f"{difference:+,.0f} INR "
            "vs prior available month"
        )

    return (
        f"{difference:+,.0f} "
        "vs prior available month"
    )


def status_text(actual, target, higher_is_better=True):
    if actual is None or target is None:
        return "Informational"

    achieved = (
        actual >= target
        if higher_is_better
        else actual <= target
    )

    return "On target" if achieved else "Below target"


def show_card(
    column,
    title,
    value,
    target_text,
    status,
    trend=None,
    note=None,
):
    with column:
        with st.container(border=True):
            st.markdown(f"**{title}**")

            st.metric(
                label="Value",
                value=value if value is not None else "No data",
            )

            st.caption(f"Target: {target_text}")
            st.caption(f"Status: {status}")

            if trend:
                st.caption(f"Trend: {trend}")

            if note:
                st.caption(note)


# --------------------------------------------------
# Calculate KPIs
# --------------------------------------------------

headcount = visible_sum("M01")
payroll = visible_sum("M09")

attendance, attendance_target = get_target_values(
    "attendance"
)

revenue = visible_sum("M16")
net_profit = company_value("M17")
operating_margin = company_value("M18")
overdue = visible_sum("M21")

task_completion, task_target = get_target_values(
    "task"
)

# --------------------------------------------------
# Display eight KPI cards
# --------------------------------------------------

st.subheader("Company health indicators")

row1 = st.columns(4)

show_card(
    row1[0],
    "Headcount",
    f"{headcount:,.0f}" if headcount is not None else None,
    "No approved target",
    "Informational",
    trend_text("M01"),
    "Visible department groups only; suppressed groups excluded.",
)

show_card(
    row1[1],
    "Employer payroll cost",
    money_compact(payroll) if payroll is not None else None,
    "No approved target",
    "Informational",
    trend_text("M09"),
    "Visible department groups only; suppressed groups excluded.",
)

show_card(
    row1[2],
    "Attendance rate",
    f"{attendance * 100:.2f}%"
    if attendance is not None else None,
    f"{attendance_target * 100:.1f}%"
    if attendance_target is not None else "No approved target",
    status_text(attendance, attendance_target),
    trend_text("M13", "average"),
    "Average of visible department rates.",
)

show_card(
    row1[3],
    "Revenue",
    money_compact(revenue) if revenue is not None else None,
    "No approved target",
    "Informational",
    trend_text("M16"),
    "Sum of governed revenue account values.",
)

row2 = st.columns(4)

show_card(
    row2[0],
    "Net profit",
    money_compact(net_profit)
    if net_profit is not None else None,
    "No approved target",
    "Informational",
    trend_text("M17"),
    "All-company metric.",
)

show_card(
    row2[1],
    "Operating margin",
    f"{operating_margin:.2f}%"
    if operating_margin is not None else None,
    "No approved target",
    "Informational",
    trend_text("M18"),
    "All-company metric.",
)

show_card(
    row2[2],
    "Overdue receivables",
    money_compact(overdue)
    if overdue is not None else None,
    "No approved target",
    "Informational",
    trend_text("M21"),
    "Point-in-time invoice/client snapshot.",
)

show_card(
    row2[3],
    "Task completion",
    f"{task_completion:.2f}%"
    if task_completion is not None else None,
    f"{task_target:.1f}%"
    if task_target is not None else "No approved target",
    status_text(task_completion, task_target),
    None,
    "Monthly average of visible department values.",
)

# --------------------------------------------------
# Detailed page links
# --------------------------------------------------

st.subheader("Explore KPI details")

links = [
    ("Headcount", "pages/1_Workforce_Headcount.py"),
    ("Attendance", "pages/2_Attendance_Leave.py"),
    ("Payroll", "pages/5_Payroll_Budget.py"),
    ("Finance and receivables", "pages/6_Finance_Receivables.py"),
    ("Team productivity", "pages/4_Team_Productivity.py"),
]

link_cols = st.columns(5)

for col, (label, page) in zip(link_cols, links):
    with col:
        st.page_link(page, label=label)

# --------------------------------------------------
# Executive interpretation
# --------------------------------------------------

st.subheader("Executive interpretation")

st.markdown(
    """
    - Review workforce size and attendance together before making staffing decisions.
    - Check payroll cost alongside revenue and operating margin.
    - Prioritize overdue receivables for collection follow-up.
    - Review task completion with the relevant sprint and department context.
    - Do not treat informational KPIs as target failures when no approved target exists.
    """
)

st.caption(
    "Data note: source feeds can have different reporting dates and grains. "
    "Department averages are not company-wide weighted rates."
)

privacy_note()
