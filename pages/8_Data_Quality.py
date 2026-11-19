
import streamlit as st
import pandas as pd
import plotly.express as px

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

st.title("Data Quality Gatekeeper")

st.caption(
    "Phase 1 | Task 3 - The raw source is preserved, "
    "defects are visible, and fixes remain auditable"
)

# --------------------------------------------------
# Data Quality Results
# --------------------------------------------------

dq = load_view("vw_dq_results")

if dq.empty:
    st.info(
        "No check results yet. "
        "Run `python run_pipeline.py` first."
    )
    st.stop()

a, b, c = st.columns(3)

a.metric("Checks", len(dq))

b.metric(
    "Critical failures",
    int((dq.status == "FAIL").sum())
)

c.metric(
    "Warnings",
    int((dq.status == "WARN").sum())
)

st.dataframe(
    dq[
        [
            "check_id",
            "check_name",
            "severity",
            "status",
            "rows_affected",
            "description",
            "recommended_action",
        ]
    ],
    width="stretch",
    hide_index=True,
)

# --------------------------------------------------
# Contract Validation
# --------------------------------------------------

contract = load_view("vw_contract_validation")

if not contract.empty:
    st.subheader("Contract validation")

    a, b, c = st.columns(3)

    a.metric(
        "Contract column/rule rows",
        len(contract)
    )

    b.metric(
        "Failing rules",
        int((contract.status == "FAIL").sum())
    )

    c.metric(
        "Unexpected columns warned",
        int((contract.status == "WARN").sum())
    )

    st.dataframe(
        contract[contract.status != "PASS"],
        width="stretch",
        hide_index=True,
    )

# --------------------------------------------------
# Evidence Files
# --------------------------------------------------

st.markdown("### Evidence files")

st.code(
    "reports/dq_results.csv\n"
    "reports/dq_report.md\n"
    "reports/known_issue_review.csv\n"
    "reports/contract_validation.csv\n"
    "rejected/*_rejected.csv",
    language="text",
)

# --------------------------------------------------
# Governance Notice
# --------------------------------------------------

st.info(
    "Critical failures from deliberately planted training issues "
    "are expected. The app is a release candidate, not a sign-off "
    "that source data is defect-free."
)
