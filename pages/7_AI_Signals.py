import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from src.dashboard_utils import load_view, metric, privacy_note

st.title("AI Signals & Forecasts")
st.caption(
    "Phase 3 | Task 14 - Explainable anomaly signals, "
    "aggregated risk and forecast evaluation"
)

# --------------------------------------------------
# 1. Headcount Forecast with 80% Confidence Band
# --------------------------------------------------

st.header("Headcount Forecast")

forecast = load_view("vw_headcount_forecast")

if not forecast.empty:
    departments = sorted(forecast["department_id"].dropna().unique())

    default_index = departments.index("ALL") if "ALL" in departments else 0

    selected_department = st.selectbox(
        "Select department",
        departments,
        index=default_index
    )

    selected = forecast[
        forecast["department_id"] == selected_department
    ].sort_values("period")

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=selected["period"],
        y=selected["upper_80"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip"
    ))

    fig.add_trace(go.Scatter(
        x=selected["period"],
        y=selected["lower_80"],
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(99, 110, 250, 0.18)",
        name="80% confidence band"
    ))

    fig.add_trace(go.Scatter(
        x=selected["period"],
        y=selected["forecast_value"],
        mode="lines+markers",
        name="Forecast headcount",
        line=dict(width=3)
    ))

    fig.update_layout(
        title=f"Headcount Forecast - {selected_department}",
        xaxis_title="Forecast Month",
        yaxis_title="Headcount",
        hovermode="x unified"
    )

    st.plotly_chart(fig, width="stretch")

    latest = selected.sort_values("period").iloc[-1]

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Latest Forecast",
        f"{latest['forecast_value']:,.1f}"
    )

    c2.metric(
        "Lower 80% Bound",
        f"{latest['lower_80']:,.1f}"
    )

    c3.metric(
        "Upper 80% Bound",
        f"{latest['upper_80']:,.1f}"
    )

    st.caption(
        f"Model: {latest['model_version']} | "
        f"Trained through: {latest['trained_through']}"
    )

    st.dataframe(
        selected,
        width="stretch",
        hide_index=True
    )
else:
    st.info("No forecast data is currently available.")

# --------------------------------------------------
# 2. Anomaly Signals
# --------------------------------------------------

st.header("Anomaly Detection")

a = load_view("vw_ai_anomaly_summary")

if not a.empty:
    fig = px.line(
        a,
        x="period",
        y="flag_rate_pct",
        color="source_dataset",
        markers=True,
        title="Share of scored records flagged as unusual",
        labels={
            "period": "Month",
            "flag_rate_pct": "Flag rate (%)"
        }
    )

    st.plotly_chart(fig, width="stretch")

    latest = a[a.period == a.period.max()]

    c1, c2 = st.columns(2)

    c1.metric(
        "Latest-month flagged rows",
        f"{latest.flagged_rows.sum():,}"
    )

    c2.metric(
        "Latest-month money-at-risk estimate",
        f"₹{latest.money_at_risk.sum():,.0f}"
    )

    st.dataframe(
        a.sort_values("period", ascending=False),
        width="stretch",
        hide_index=True
    )
else:
    st.info("No anomaly summary data is available.")

# --------------------------------------------------
# 3. Department Attrition Risk
# --------------------------------------------------

# --------------------------------------------------
# 3. Department Attrition Risk
# --------------------------------------------------

st.header("Risk Summary by Department")

r = load_view("vw_attrition_risk_department")

if not r.empty:
    r["high_risk_share_pct"] = pd.to_numeric(
        r["high_risk_share_pct"],
        errors="coerce"
    )

    r = r.dropna(subset=["high_risk_share_pct"])

    r = r.sort_values(
        "high_risk_share_pct",
        ascending=False
    )

    st.write(f"Departments available: {len(r)}")

    st.dataframe(
        r,
        width="stretch",
        hide_index=True
    )

    fig = px.bar(
        r,
        x="department_id",
        y="high_risk_share_pct",
        title="High-risk Share by Department",
        labels={
            "department_id": "Department",
            "high_risk_share_pct": "High-risk Share (%)"
        },
        text="high_risk_share_pct"
    )

    fig.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="outside"
    )

    fig.update_layout(
        yaxis_title="High-risk Share (%)",
        xaxis_title="Department"
    )

    st.plotly_chart(fig, width="stretch")

else:
    st.info("No department risk data is available.")

# --------------------------------------------------
# 4. Forecast Evaluation
# --------------------------------------------------

st.header("Forecast Evaluation")

m = metric("M28")

if m.empty:
    st.info(
        "No forecast months overlap with actual headcount months "
        "in the current workbook. MAPE is unavailable until actuals "
        "arrive for a forecast period."
    )
else:
    st.dataframe(
        m.dropna(subset=["metric_value"]),
        width="stretch",
        hide_index=True
    )

# --------------------------------------------------
# 5. Governance Notice
# --------------------------------------------------

st.warning(
    "Anomaly flags are investigation leads, not proof of fraud "
    "or employee misconduct. Do not take action from a model flag alone."
)

privacy_note()