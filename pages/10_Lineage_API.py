
import streamlit as st

from src.dashboard_utils import (
    ensure_database_ready,
    load_view,
)

# --------------------------------------------------
# Database Readiness
# --------------------------------------------------

try:
    with st.spinner("Checking PulseIQ database..."):
        ensure_database_ready()
except Exception as exc:
    st.error("Unable to prepare the PulseIQ database.")
    st.exception(exc)
    st.stop()

# --------------------------------------------------
# Page Title
# --------------------------------------------------

st.title("Metric Lineage & API")

st.caption(
    "Phase 4 | Task 19 - Shared definitions "
    "and traceability from metric to source"
)

# --------------------------------------------------
# Metric Lineage
# --------------------------------------------------

st.header("Metric Lineage")

lineage = load_view("vw_lineage")

if not lineage.empty:
    st.dataframe(
        lineage,
        width="stretch",
        hide_index=True
    )
else:
    st.info("No metric lineage information is currently available.")

# --------------------------------------------------
# API Endpoints
# --------------------------------------------------

st.subheader("Local API endpoints")

st.code(
    "GET /health\n"
    "GET /metrics\n"
    "GET /metrics/{metric_id}\n"
    "GET /dq\n"
    "GET /lineage\n"
    "GET /docs",
    language="http"
)

# --------------------------------------------------
# Start API
# --------------------------------------------------

st.markdown(
    "Start the API from the project root in a separate terminal:"
)

st.code(
    "uvicorn api:app --reload",
    language="powershell"
)

# --------------------------------------------------
# API Information
# --------------------------------------------------

st.markdown(
    "The API reads governed views in the same DuckDB file. "
    "It does not offer write endpoints."
)

st.info(
    "This project is a local release candidate. Hosting it publicly "
    "requires deployment configuration, secrets review, access "
    "controls, and a production data/privacy review."
)
