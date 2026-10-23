"""Phase 1 workforce page: KPI cards, filters, findings and privacy-aware breakdowns."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.dashboard_utils import (
    load_view, metric, money, money_compact, pct, metric_line, metric_bar,
    privacy_note, empty_state,
)

st.title("Workforce and Headcount")
st.caption("Phase 1 - Task 5 | Company snapshot, filtered headcount trend, department mix, work mode and city tier")

company = load_view("vw_company_kpis")
hc = metric("M01")
if company.empty or hc.empty:
    empty_state()
    st.stop()

company["period"] = pd.to_datetime(company["period"], errors="coerce")
company = company.dropna(subset=["period"]).sort_values("period")
hc["period"] = pd.to_datetime(hc["period"], errors="coerce")


def latest_value(frame: pd.DataFrame, col: str):
    available = frame.dropna(subset=[col]).sort_values("period")
    return None if available.empty else available.iloc[-1]


hc_latest = latest_value(company, "headcount")
hire_latest = latest_value(company, "hires")
exit_latest = latest_value(company, "exits")
att_latest = latest_value(company, "attendance_rate")
pay_latest = latest_value(company, "payroll_cost")

st.subheader("Latest company-wide snapshot")
kpis = st.columns(5)
kpis[0].metric(
    f"Headcount | {hc_latest['period']:%b %Y}" if hc_latest is not None else "Headcount",
    f"{hc_latest['headcount']:,.0f}" if hc_latest is not None and pd.notna(hc_latest["headcount"]) else "-",
)
kpis[1].metric(
    f"Hires | {hire_latest['period']:%b %Y}" if hire_latest is not None else "Hires",
    f"{hire_latest['hires']:,.0f}" if hire_latest is not None and pd.notna(hire_latest["hires"]) else "-",
)
kpis[2].metric(
    f"Exits | {exit_latest['period']:%b %Y}" if exit_latest is not None else "Exits",
    f"{exit_latest['exits']:,.0f}" if exit_latest is not None and pd.notna(exit_latest["exits"]) else "-",
)
kpis[3].metric(
    f"Attendance | {att_latest['period']:%b %Y}" if att_latest is not None else "Attendance",
    pct(att_latest["attendance_rate"], 100) if att_latest is not None else "-",
)
kpis[4].metric(
    f"Payroll cost | {pay_latest['period']:%b %Y}" if pay_latest is not None else "Payroll cost",
    money_compact(pay_latest["payroll_cost"]) if pay_latest is not None else "-",
)
st.caption("Company-wide cards use each measure's latest available period. Filters below apply to detailed headcount charts.")

min_date = hc["period"].min().date()
max_date = hc["period"].max().date()
with st.sidebar:
    st.subheader("Workforce filters")
    start_date = st.date_input("From month", value=min_date, min_value=min_date, max_value=max_date, key="workforce_start")
    end_date = st.date_input("To month", value=max_date, min_value=min_date, max_value=max_date, key="workforce_end")
    department_options = sorted(hc["department_id"].dropna().astype(str).unique().tolist())
    selected_departments = st.multiselect("Departments", department_options, default=department_options, key="workforce_departments")

filtered = hc.copy()
if start_date <= end_date:
    filtered = filtered.loc[filtered["period"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))]
else:
    st.warning("The start date is after the end date. Correct the range to filter the chart.")
filtered = filtered.loc[filtered["department_id"].astype(str).isin(selected_departments)] if selected_departments else filtered.iloc[0:0]

st.subheader("Headcount trend for selected departments")
visible = filtered.dropna(subset=["metric_value"]).copy()
if visible.empty:
    st.info("No unsuppressed headcount values are available for this selection. Widen the date range or select more departments.")
else:
    visible_totals = visible.groupby("period", as_index=False)["metric_value"].sum().sort_values("period")
    latest_visible = visible_totals.iloc[-1]
    metric_line(
        visible_totals,
        f"Visible selected-department headcount totals {int(latest_visible['metric_value']):,} in {latest_visible['period']:%b %Y}",
        y_title="Employees",
        x="period",
        y="metric_value",
        color=None,
    )
    first_visible = visible_totals.iloc[0]
    movement = int(latest_visible["metric_value"] - first_visible["metric_value"])
    movement_word = "increased" if movement >= 0 else "decreased"
    st.caption(f"Visible selected groups {movement_word} by {abs(movement):,} between {first_visible['period']:%b %Y} and {latest_visible['period']:%b %Y}. Values below each metric's minimum group size remain suppressed.")

st.subheader("Department breakdown")
if not visible.empty:
    latest_period = visible["period"].max()
    latest_depts = visible.loc[visible["period"].eq(latest_period)].copy()
    if not latest_depts.empty:
        top = latest_depts.sort_values("metric_value", ascending=False).iloc[0]
        metric_bar(latest_depts, f"Largest visible department: {top['department_id']} ({int(top['metric_value']):,} employees)", x="dimension_label", y="metric_value")
        st.caption(f"Department distribution for {latest_period:%b %Y}; departments below the privacy threshold are omitted.")

st.subheader("Work mode and city tier")
mix = load_view("vw_workforce_mix")
if not mix.empty:
    modes = mix.loc[mix["dimension_type"].eq("Work mode")].dropna(subset=["employee_count"]).copy()
    if not modes.empty:
        top_mode = modes.sort_values("employee_count", ascending=False).iloc[0]
        modes = modes.rename(columns={"dimension_value": "dimension_label", "employee_count": "metric_value"})
        metric_bar(modes, f"Most common visible work mode: {top_mode['dimension_value']} ({int(top_mode['employee_count']):,} employees)", x="dimension_label", y="metric_value")
        st.caption("The chart uses the latest active workforce snapshot; categories below five employees are suppressed.")

locations = load_view("vw_location_summary")
if not locations.empty and "city_tier" in locations.columns:
    loc = locations.dropna(subset=["employee_count"]).copy()
    if not loc.empty:
        # Apply the source view's location-level suppression first, then summarise visible locations by city tier.
        tier = loc.groupby("city_tier", as_index=False)["employee_count"].sum()
        tier = tier.rename(columns={"city_tier": "dimension_label", "employee_count": "metric_value"})
        top_tier = tier.sort_values("metric_value", ascending=False).iloc[0]
        metric_bar(tier, f"Largest visible city tier: {top_tier['dimension_label']} ({int(top_tier['metric_value']):,} employees)", x="dimension_label", y="metric_value")
        st.caption("City-tier totals aggregate only location groups already permitted by the minimum-group rule; suppressed locations are not reconstructed.")

privacy_note()
