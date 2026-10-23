from __future__ import annotations
import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard_utils import DB_FILE, load_view, money, money_compact, money_delta, pct, metric_line, metric_bar, privacy_note, empty_state

st.set_page_config(page_title="PulseIQ Analytics", page_icon="📊", layout="wide")
st.markdown("""<style>
.block-container {padding-top: 1.6rem; max-width: 1450px}
[data-testid="stMetric"] {background:#f4f7fb;border:1px solid #dbe3ef;padding:15px;border-radius:12px}
[data-testid="stSidebar"] {background:#f7f9fc}
</style>""", unsafe_allow_html=True)

if not DB_FILE.exists() or load_view("vw_company_kpis").empty:
    empty_state()
    st.stop()

st.title("PulseIQ Analytics")
st.markdown("**Company health, workforce, pay, finance and team delivery - in one governed analytics workspace.**")
st.caption("Fictional training data for Zenith Nova Technologies  |  Local release candidate  |  Metric values come from DuckDB analytics views")

company = load_view("vw_company_kpis")
company["period"] = pd.to_datetime(company["period"])
company = company.sort_values("period")
def latest_two(column):
    available = company.dropna(subset=[column]).sort_values("period")
    if available.empty:
        return None, None
    last_row = available.iloc[-1]
    prior_row = available.iloc[-2] if len(available) > 1 else last_row
    return last_row, prior_row

def delta(current, previous, suffix=""):
    if pd.isna(current) or pd.isna(previous): return None
    return f"{(float(current)-float(previous)):+,.1f}{suffix} vs prior available month"

hc_last, hc_prev = latest_two("headcount")
hire_last, _ = latest_two("hires")
exit_last, _ = latest_two("exits")
att_last, att_prev = latest_two("attendance_rate")
pay_last, pay_prev = latest_two("payroll_cost")

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric(f"Headcount  |  {hc_last['period']:%b %Y}" if hc_last is not None else "Headcount", f"{hc_last['headcount']:,.0f}" if hc_last is not None else "-", delta(hc_last['headcount'],hc_prev['headcount']) if hc_last is not None and hc_prev is not None else None)
c2.metric(f"Hires  |  {hire_last['period']:%b %Y}" if hire_last is not None else "Hires", f"{hire_last['hires']:,.0f}" if hire_last is not None else "-")
c3.metric(f"Exits  |  {exit_last['period']:%b %Y}" if exit_last is not None else "Exits", f"{exit_last['exits']:,.0f}" if exit_last is not None else "-")
c4.metric(f"Attendance  |  {att_last['period']:%b %Y}" if att_last is not None else "Attendance", pct(att_last['attendance_rate'],100) if att_last is not None else "-", delta(att_last['attendance_rate']*100, att_prev['attendance_rate']*100," pp") if att_last is not None and att_prev is not None else None)
c5.metric(f"Payroll cost  |  {pay_last['period']:%b %Y}" if pay_last is not None else "Payroll cost", money_compact(pay_last['payroll_cost']) if pay_last is not None else "-", money_delta(pay_last['payroll_cost'], pay_prev['payroll_cost']) if pay_last is not None and pay_prev is not None else None)

st.subheader("What changed over time")
tab1,tab2,tab3 = st.tabs(["Workforce", "Payroll", "Attendance"])
with tab1:
    trend_value = int(hc_last["headcount"]) if hc_last is not None and pd.notna(hc_last["headcount"]) else None
    trend_period = hc_last["period"] if hc_last is not None else None
    trend_title = f"Company headcount reached {trend_value:,} in {trend_period:%b %Y}" if trend_value is not None and trend_period is not None else "Company headcount trend"
    metric_line(company.rename(columns={"headcount":"metric_value"}), trend_title, y_title="Employees", color=None, y="metric_value")
    if hc_last is not None and hc_prev is not None:
        change = int(hc_last["headcount"] - hc_prev["headcount"])
        word = "increased" if change >= 0 else "decreased"
        st.caption(f"Headcount {word} by {abs(change):,} versus the prior available month.")
    st.caption("Each KPI card uses the latest available period for that measure because the source feeds have different end dates. Headcount is an end-of-month measure from the supplied headcount fact table.")
with tab2:
    pay = company.dropna(subset=["payroll_cost"])
    if pay.empty: st.info("Payroll metric is not available for this period.")
    else:
        latest_pay = pay.sort_values("period").iloc[-1]
        pay_title = f"Employer payroll cost was {money_compact(latest_pay['payroll_cost'])} in {latest_pay['period']:%b %Y}"
        fig=px.line(pay,x="period",y="payroll_cost",markers=True,title=pay_title,labels={"period":"Month","payroll_cost":"INR"})
        st.plotly_chart(fig,width="stretch")
        st.caption(f"The latest available payroll cost is {money(latest_pay['payroll_cost'])}; metric definitions use validated payroll records.")
        st.caption("Payroll cost is aggregated from validated payroll records after duplicate employee/run pairs and unmatched employee keys are excluded.")
with tab3:
    att=company.dropna(subset=["attendance_rate"])
    if att.empty: st.info("Attendance metric is not available.")
    else:
        latest_att = att.sort_values("period").iloc[-1]
        att_title = f"Attendance reached {pct(latest_att['attendance_rate'], 100)} in {latest_att['period']:%b %Y}"
        fig=px.line(att,x="period",y=att["attendance_rate"]*100,markers=True,title=att_title,labels={"period":"Month","y":"Attendance (%)"})
        st.plotly_chart(fig,width="stretch")
        st.caption(f"Latest available attendance rate: {pct(latest_att['attendance_rate'], 100)}.")

st.subheader("Department signals")
headcount=load_view("vw_metric_m01_headcount")
if not headcount.empty:
    headcount["period"]=pd.to_datetime(headcount["period"], errors="coerce")
    latest_rows=headcount.dropna(subset=["metric_value"]).copy()
    if not latest_rows.empty:
        last_period=latest_rows["period"].max()
        mix=latest_rows.loc[latest_rows["period"].eq(last_period)].copy()
        left, right = st.columns(2)
        with left:
            if not mix.empty:
                top_department = mix.sort_values("metric_value", ascending=False).iloc[0]
                title = f"Largest visible department: {top_department['department_id']} ({int(top_department['metric_value']):,} employees)"
                metric_bar(mix, title, x="dimension_label", y="metric_value")
                st.caption(f"Largest visible department in {last_period:%b %Y}; small groups remain suppressed.")
        with right:
            finance=load_view("vw_finance_monthly")
            if not finance.empty and "period" in finance.columns:
                finance["period"]=pd.to_datetime(finance["period"], errors="coerce")
                fin_valid = finance.dropna(subset=["net_profit"]).sort_values("period")
                if not fin_valid.empty:
                    latest_fin = fin_valid.iloc[-1]
                    title = f"Ledger net profit was {money_compact(latest_fin['net_profit'])} in {latest_fin['period']:%b %Y}"
                    fig=px.line(fin_valid,x="period",y="net_profit",markers=True,title=title,labels={"period":"Month","net_profit":"INR"})
                    st.plotly_chart(fig,width="stretch")
                    st.caption(f"Latest available ledger net profit: {money(latest_fin['net_profit'])}.")
                else:
                    st.info("No ledger net-profit values are available for the current period range.")
privacy_note()

dq=load_view("vw_dq_results")
if not dq.empty:
    fail=int((dq["status"]=="FAIL").sum()); warn=int((dq["status"]=="WARN").sum())
    st.subheader("Data quality before decisions")
    q1,q2,q3=st.columns(3)
    q1.metric("Checks run",len(dq)); q2.metric("Critical failures",fail); q3.metric("Warnings",warn)
    st.caption("See the Data Quality page before using results for a business decision. Known issues are retained in the raw layer and surfaced rather than silently corrected.")

with st.expander("Questions this workspace is designed to answer"):
    st.markdown("""- Is headcount moving up or down, and where is the change concentrated?
- Are attendance, leave, attrition and delivery metrics moving toward their targets?
- How is payroll cost tracking against budget and company revenue?
- Where are invoice balances, unusual signals or quality issues that need follow-up?
- Can each published number be traced to an official metric definition and source table?""")
