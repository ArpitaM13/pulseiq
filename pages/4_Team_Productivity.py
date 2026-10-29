import streamlit as st
import pandas as pd
import plotly.express as px
import duckdb

from src.dashboard_utils import (
    metric,
    privacy_note,
)


# ============================================================
# PHASE 2 - TASK 8: TEAM PRODUCTIVITY ANALYTICS
# ============================================================

st.title("Team Productivity")

st.caption(
    "Phase 2 | Task 8 - Sprint completion, on-time "
    "delivery, velocity, cycle time, blocked and reopened tasks"
)

REPORT_START = pd.Timestamp("2025-04-01")
REPORT_END = pd.Timestamp("2026-09-30")
MIN_GROUP_SIZE = 5


# ============================================================
# LOAD GOVERNED TEAM-SPRINT SUMMARY
# ============================================================

@st.cache_data
def load_team_summary():
    con = duckdb.connect(
        "data/pulseiq.duckdb",
        read_only=True,
    )

    try:
        return con.execute("""
            SELECT *
            FROM analytics.vw_task_summary
        """).df()
    finally:
        con.close()


@st.cache_data
def load_reopened_summary():
    con = duckdb.connect(
        "data/pulseiq.duckdb",
        read_only=True,
    )

    try:
        return con.execute("""
            SELECT
                s.start_date::DATE AS sprint_start,
                t.sprint_id,
                t.team_id,
                COUNT(*) AS group_size,
                COUNT(*) FILTER (
                    WHERE COALESCE(t.reopened_count, 0) > 0
                ) AS reopened_tasks,
                SUM(
                    COALESCE(t.reopened_count, 0)
                ) AS reopen_events
            FROM analytics.fact_task_valid t
            JOIN warehouse.dim_sprint s
                ON t.sprint_id = s.sprint_id
            GROUP BY
                s.start_date::DATE,
                t.sprint_id,
                t.team_id
        """).df()
    finally:
        con.close()


# ============================================================
# LOAD DATA
# ============================================================

summary = load_team_summary()
reopened = load_reopened_summary()


# ============================================================
# REPORT FILTERS
# ============================================================

st.header("Productivity Filters")

if summary.empty:
    st.warning("No team productivity data is available.")
    st.stop()

required_summary_columns = {
    "sprint_start",
    "sprint_id",
    "team_id",
    "planned_tasks",
    "done_tasks",
    "blocked_tasks",
    "completed_points",
    "avg_cycle_days",
    "group_size",
}

missing_columns = required_summary_columns - set(summary.columns)

if missing_columns:
    st.error(
        "The team productivity summary is missing required "
        f"columns: {', '.join(sorted(missing_columns))}"
    )
    st.stop()

summary["sprint_start"] = pd.to_datetime(
    summary["sprint_start"],
    errors="coerce",
)

reopened["sprint_start"] = pd.to_datetime(
    reopened["sprint_start"],
    errors="coerce",
)

# Keep only records inside the reporting period.
summary = summary[
    (summary["sprint_start"] >= REPORT_START)
    & (summary["sprint_start"] <= REPORT_END)
].copy()

reopened = reopened[
    (reopened["sprint_start"] >= REPORT_START)
    & (reopened["sprint_start"] <= REPORT_END)
].copy()

if summary.empty:
    st.info("No sprint data exists in the reporting period.")
    st.stop()

# Available teams for the multiselect.
available_teams = sorted(
    summary["team_id"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

selected_teams = st.multiselect(
    "Select teams",
    options=available_teams,
    default=available_teams,
)

if not selected_teams:
    st.info("Select at least one team to view productivity.")
    st.stop()

# Date range.
min_date = summary["sprint_start"].min().date()
max_date = summary["sprint_start"].max().date()

selected_dates = st.date_input(
    "Select sprint start date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if not isinstance(selected_dates, (tuple, list)) or len(selected_dates) != 2:
    st.info("Select both start and end dates.")
    st.stop()

start_date, end_date = selected_dates

if start_date > end_date:
    st.error("The start date must be on or before the end date.")
    st.stop()

# Filter the summary by selected teams and dates.
summary = summary[
    summary["team_id"].astype(str).isin(selected_teams)
    & (summary["sprint_start"].dt.date >= start_date)
    & (summary["sprint_start"].dt.date <= end_date)
].copy()

# Filter reopened-task data using the same selections.
reopened = reopened[
    reopened["team_id"].astype(str).isin(selected_teams)
    & (reopened["sprint_start"].dt.date >= start_date)
    & (reopened["sprint_start"].dt.date <= end_date)
].copy()

# ============================================================
# PRIVACY THRESHOLD
# ============================================================

summary = summary[
    pd.to_numeric(
        summary["group_size"],
        errors="coerce",
    ).fillna(0) >= MIN_GROUP_SIZE
].copy()

reopened = reopened[
    pd.to_numeric(
        reopened["group_size"],
        errors="coerce",
    ).fillna(0) >= MIN_GROUP_SIZE
].copy()

if summary.empty:
    st.info(
        "No visible team-sprint groups match the selected filters "
        "and minimum privacy threshold."
    )
    st.stop()


# ============================================================
# 1. PRODUCTIVITY OVERVIEW
# ============================================================

st.header("Productivity Overview")

planned_tasks = int(
    pd.to_numeric(
        summary["planned_tasks"],
        errors="coerce",
    ).fillna(0).sum()
)

done_tasks = int(
    pd.to_numeric(
        summary["done_tasks"],
        errors="coerce",
    ).fillna(0).sum()
)

blocked_tasks = int(
    pd.to_numeric(
        summary["blocked_tasks"],
        errors="coerce",
    ).fillna(0).sum()
)

completed_points = float(
    pd.to_numeric(
        summary["completed_points"],
        errors="coerce",
    ).fillna(0).sum()
)

reopened_tasks = int(
    pd.to_numeric(
        reopened["reopened_tasks"],
        errors="coerce",
    ).fillna(0).sum()
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Planned Tasks",
    f"{planned_tasks:,}",
)

col2.metric(
    "Completed Tasks",
    f"{done_tasks:,}",
)

col3.metric(
    "Blocked Tasks",
    f"{blocked_tasks:,}",
)

col4, col5, col6 = st.columns(3)

col4.metric(
    "Completed Story Points",
    f"{completed_points:,.0f}",
)

col5.metric(
    "Reopened Tasks",
    f"{reopened_tasks:,}",
)

completion_pct = (
    done_tasks / planned_tasks * 100
    if planned_tasks > 0
    else 0
)

col6.metric(
    "Task Completion Rate",
    f"{completion_pct:.1f}%",
)

st.caption(
    "Overview figures are aggregated from visible "
    "team-sprint groups in the selected reporting period."
)


# ============================================================
# 2. GOVERNED M22-M25 METRICS
# ============================================================

st.header("Governed Productivity Metrics")

metric_configs = [
    ("M22", "Task Completion Rate", "Rate (%)"),
    ("M23", "On-Time Delivery Rate", "Rate (%)"),
    ("M24", "Sprint Velocity", "Story Points"),
    ("M25", "Average Cycle Time", "Days"),
]

for metric_id, chart_title, y_label in metric_configs:

    st.subheader(chart_title)

    data = metric(metric_id)

    if data.empty:
        st.info(f"{chart_title} data is unavailable.")
        continue

    data = data.copy()

    # Check the columns required for governed metric filtering.
    required_metric_columns = {
        "period",
        "dimension_label",
        "metric_value",
    }

    missing_metric_columns = (
        required_metric_columns - set(data.columns)
    )

    if missing_metric_columns:
        st.warning(
            f"{chart_title} cannot be displayed because "
            "the metric data is missing required columns: "
            f"{', '.join(sorted(missing_metric_columns))}."
        )
        continue

    data["period"] = pd.to_datetime(
        data["period"],
        errors="coerce",
    )

    data = data.dropna(
        subset=["period"],
    )

    # Apply the selected date range.
    data = data[
        (data["period"].dt.date >= start_date)
        & (data["period"].dt.date <= end_date)
    ].copy()

    # --------------------------------------------------------
    # CORRECTED TEAM FILTER
    # Labels look like "T05 / SP-01".
    # Extract the team ID before "/" and match it exactly.
    # This prevents a team such as T1 from accidentally
    # matching a different team such as T10.
    # --------------------------------------------------------

    data["team_id_filter"] = (
        data["dimension_label"]
        .astype(str)
        .str.split("/", n=1)
        .str[0]
        .str.strip()
    )

    data = data[
        data["team_id_filter"].isin(selected_teams)
    ].copy()

    # Convert metric values to numeric.
    data["metric_value"] = pd.to_numeric(
        data["metric_value"],
        errors="coerce",
    )

    data = data.dropna(
        subset=["metric_value"],
    )

    # Apply the governed minimum group-size threshold.
    # Use the metric's own threshold when provided.
    if "group_size" in data.columns:

        data["group_size"] = pd.to_numeric(
            data["group_size"],
            errors="coerce",
        )

        if "min_group_size" in data.columns:
            data["min_group_size"] = pd.to_numeric(
                data["min_group_size"],
                errors="coerce",
            ).fillna(MIN_GROUP_SIZE)
        else:
            data["min_group_size"] = MIN_GROUP_SIZE

        data = data[
            data["group_size"].notna()
            & (
                data["group_size"]
                >= data["min_group_size"]
            )
        ].copy()

    if data.empty:
        st.info(
            "No visible data for this metric matches "
            "the selected teams, dates, and privacy threshold."
        )
        continue

    fig = px.line(
        data,
        x="period",
        y="metric_value",
        color="dimension_label",
        markers=True,
        title=chart_title,
        labels={
            "period": "Sprint Start",
            "metric_value": y_label,
            "dimension_label": "Team / Sprint",
        },
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )


# ============================================================
# 3. TEAM VELOCITY COMPARISON
# ============================================================

st.header("Team Velocity Comparison")

velocity_by_team = (
    summary.groupby("team_id", as_index=False)
    .agg(
        completed_points=("completed_points", "sum"),
        sprints=("sprint_id", "nunique"),
    )
)

velocity_by_team["points_per_sprint"] = (
    velocity_by_team["completed_points"]
    / velocity_by_team["sprints"].replace(
        0,
        float("nan"),
    )
)

velocity_by_team = velocity_by_team.dropna(
    subset=["points_per_sprint"],
)

if not velocity_by_team.empty:

    fig = px.bar(
        velocity_by_team.sort_values(
            "points_per_sprint",
            ascending=False,
        ),
        x="team_id",
        y="points_per_sprint",
        title="Average Completed Story Points per Sprint",
        labels={
            "team_id": "Team",
            "points_per_sprint": "Story Points per Sprint",
        },
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

else:
    st.info("No velocity data is available for these filters.")

st.caption(
    "Velocity comparisons use completed story points "
    "per sprint, rather than total points alone, "
    "to account for different numbers of sprints."
)


# ============================================================
# 4. BLOCKED TASK ANALYSIS
# ============================================================

st.header("Blocked Task Analysis")

blocked_by_team = (
    summary.groupby("team_id", as_index=False)
    .agg(
        blocked_tasks=("blocked_tasks", "sum"),
        planned_tasks=("planned_tasks", "sum"),
    )
)

blocked_by_team["blocked_share_pct"] = (
    blocked_by_team["blocked_tasks"]
    / blocked_by_team["planned_tasks"].replace(
        0,
        float("nan"),
    )
    * 100
)

fig = px.bar(
    blocked_by_team,
    x="team_id",
    y="blocked_tasks",
    title="Blocked Tasks by Team",
    labels={
        "team_id": "Team",
        "blocked_tasks": "Blocked Tasks",
    },
)

st.plotly_chart(
    fig,
    width="stretch",
)

st.caption(
    "Blocked task counts are based on the task status "
    "recorded in the source data."
)


# ============================================================
# 5. REOPENED TASK ANALYSIS
# ============================================================

st.header("Reopened Task Analysis")

if not reopened.empty:

    reopened_by_team = (
        reopened.groupby("team_id", as_index=False)
        .agg(
            reopened_tasks=("reopened_tasks", "sum"),
            reopen_events=("reopen_events", "sum"),
            total_tasks=("group_size", "sum"),
        )
    )

    reopened_by_team["reopen_rate_pct"] = (
        reopened_by_team["reopened_tasks"]
        / reopened_by_team["total_tasks"].replace(
            0,
            float("nan"),
        )
        * 100
    )

    fig = px.bar(
        reopened_by_team,
        x="team_id",
        y="reopened_tasks",
        title="Reopened Tasks by Team",
        labels={
            "team_id": "Team",
            "reopened_tasks": "Reopened Tasks",
        },
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    st.dataframe(
        reopened_by_team[
            [
                "team_id",
                "reopened_tasks",
                "reopen_events",
                "reopen_rate_pct",
            ]
        ].round(2),
        width="stretch",
        hide_index=True,
    )

    st.caption(
        "Reopened tasks count task records with "
        "reopened_count greater than zero. Reopen events "
        "represent the sum of all recorded reopen occurrences."
    )

else:
    st.info("No reopened task data is available for these filters.")


# ============================================================
# 6. CYCLE TIME COMPARISON
# ============================================================

st.header("Cycle Time by Team")

cycle_by_team = (
    summary.groupby("team_id", as_index=False)
    .agg(
        avg_cycle_days=("avg_cycle_days", "mean"),
    )
)

cycle_by_team = cycle_by_team.dropna(
    subset=["avg_cycle_days"],
)

if not cycle_by_team.empty:

    fig = px.bar(
        cycle_by_team,
        x="team_id",
        y="avg_cycle_days",
        title="Mean Sprint-Level Cycle Time by Team",
        labels={
            "team_id": "Team",
            "avg_cycle_days": "Cycle Time (Days)",
        },
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    st.caption(
        "Cycle time is the unweighted mean of visible "
        "sprint-level average cycle times. It is not "
        "the task-weighted average across all completed tasks."
    )

else:
    st.info("No cycle-time data is available for these filters.")


# ============================================================
# 7. TASK 8 KEY FINDINGS
# ============================================================

st.header("Task 8 - Key Findings")

st.markdown("""
**1. Sprint velocity**

Completed story points per sprint provide a measure of
team delivery throughput. Compare teams alongside sprint
scope and task complexity.

**2. Blocked tasks**

Teams with higher blocked-task counts may need dependency
reviews or earlier issue escalation.

**3. Reopened tasks**

Reopened tasks can indicate rework. Review recurring
reopen patterns alongside quality and acceptance criteria.

**4. Cycle time and on-time delivery**

Lower cycle time can indicate faster completion, while
on-time delivery measures performance against deadlines.
Both should be considered together.
""")

st.caption(
    "These are interpretation guidelines. Review the "
    "filtered charts before drawing conclusions about "
    "individual teams."
)


# ============================================================
# 8. PRIVACY AND GOVERNANCE
# ============================================================

st.warning(
    "Productivity metrics are displayed at team and sprint "
    "level. Groups below the minimum privacy threshold "
    "are excluded. These metrics should not be used "
    "to evaluate individual employees."
)

privacy_note()