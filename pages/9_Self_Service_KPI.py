import streamlit as st
import pandas as pd
from src.dashboard_utils import load_view, privacy_note

st.title("Self-Service KPI Explorer")
st.caption("Phase 4  |  Task 18 - Explore approved metrics without changing their definitions")
m=load_view("vw_all_metrics")
c=load_view("vw_metric_catalog")
if m.empty or c.empty: st.info("Run the pipeline first."); st.stop()
options={f"{r.metric_id}  |  {r.metric_name}":r.metric_id for r in c.itertuples()}
selected=st.selectbox("Choose a governed metric",list(options.keys()))
metric_id=options[selected]
meta=c[c.metric_id.astype(str)==str(metric_id)].iloc[0]
st.markdown(f"**Definition:** {meta.business_definition}")
st.markdown(f"**Formula:** `{meta.formula}`")
st.caption(f"Source: {meta.source_table}  |  Grain: {meta.grain}  |  Owner: {meta.owner_team}  |  Unit: {meta.unit}")
d=m[m.metric_id.astype(str)==str(metric_id)].copy()
d["period"]=pd.to_datetime(d["period"],errors="coerce")
valid_dates=d.period.dropna()
if len(valid_dates):
    min_date,max_date=valid_dates.min().date(),valid_dates.max().date()
    x,y=st.columns(2)
    start=x.date_input("From",value=min_date,min_value=min_date,max_value=max_date,key="explorer_start")
    end=y.date_input("To",value=max_date,min_value=min_date,max_value=max_date,key="explorer_end")
    d=d[d.period.between(pd.Timestamp(start),pd.Timestamp(end))]
if "department_id" in d.columns and d.department_id.notna().any():
    depts=sorted(d.department_id.dropna().astype(str).unique())
    chosen=st.multiselect("Department filter",depts,default=depts,key="explorer_dept")
    d=d[d.department_id.isna()|d.department_id.astype(str).isin(chosen)]
if d.empty:
    st.info("No observations exist for this metric/date selection. For forecast error, this can mean actuals have not yet arrived.")
else:
    d["display_status"]=d.apply(lambda row:"Suppressed: below minimum group size" if pd.isna(row.metric_value) and pd.notna(row.min_group_size) else ("Available" if pd.notna(row.metric_value) else "Not calculable"),axis=1)
    st.dataframe(d[["period","department_id","dimension_label","metric_value","unit","group_size","min_group_size","display_status"]],width="stretch",hide_index=True)
    st.download_button("Download this filtered metric output (CSV)",data=d.to_csv(index=False).encode("utf-8"),file_name=f"{metric_id.lower()}_explorer.csv",mime="text/csv")
privacy_note()
