import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard_utils import load_view, metric, privacy_note

st.title("AI Signals & Forecasts")
st.caption("Phase 3  |  Task 14 - Explainable anomaly signals, aggregated risk and forecast evaluation")
a=load_view("vw_ai_anomaly_summary")
if not a.empty:
    fig=px.line(a,x="period",y="flag_rate_pct",color="source_dataset",markers=True,title="Share of scored records flagged as unusual",labels={"period":"Month","flag_rate_pct":"Flag rate (%)"})
    st.plotly_chart(fig,width="stretch")
    latest=a[a.period==a.period.max()]
    c1,c2=st.columns(2)
    c1.metric("Latest-month flagged rows",f"{latest.flagged_rows.sum():,}")
    c2.metric("Latest-month money-at-risk estimate",f"₹{latest.money_at_risk.sum():,.0f}")
    st.dataframe(a.sort_values("period",ascending=False),width="stretch",hide_index=True)
r=load_view("vw_attrition_risk_department")
if not r.empty:
    st.subheader("Risk summary by department")
    fig=px.bar(r.dropna(subset=["high_risk_share_pct"]),x="department_id",y="high_risk_share_pct",title="High-risk share (minimum group size 10)",labels={"department_id":"Department","high_risk_share_pct":"High-risk share (%)"})
    st.plotly_chart(fig,width="stretch")
m=metric("M28")
st.subheader("Forecast evaluation")
if m.empty:
    st.info("No forecast months overlap with actual headcount months in the current workbook. MAPE is unavailable until actuals arrive for a forecast period.")
else:
    st.dataframe(m.dropna(subset=["metric_value"]),width="stretch",hide_index=True)
st.warning("Anomaly flags are investigation leads, not proof of fraud or employee misconduct. Do not take action from a model flag alone.")
privacy_note()
