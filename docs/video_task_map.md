# Presentation Video — Task and Phase Map

The uploaded orientation deck presents **PulseIQ Analytics** as a connected product for people, pay, money and work. It frames the project as a 20-day build and repeatedly emphasizes traceability: every number should have one definition and be traceable from raw data to a released dashboard or report.

| Phase | Days | Video task names / focus |
|---|---:|---|
| Phase 1 — Foundation | 1–5 | Set up workspace and ETL pipeline; design/build star-schema warehouse; build data-quality gatekeeper; create governed metric layer; first workforce/headcount dashboard |
| Phase 2 — People and Teams | 6–10 | Attendance and leave trends; attrition analytics; team productivity dashboard; payroll cost dashboard and reconciliation; budget vs actual and KPI targets |
| Phase 3 — Money and Insight | 11–15 | Profit/loss and expense analytics; invoices, receivables and cash flow; cross-department impact view; AI signals dashboard; executive company-health scorecard |
| Phase 4 — Release and Advanced | 16–20 | Automated report builder/release candidate; release to production/live dashboard; self-service KPI explorer with privacy; metrics API and data lineage; board pack and final handover |

## Technology stack shown in the video

The deck associates tools with specific jobs: Python and pandas for data work, DuckDB and SQL for storage/metrics, Streamlit and Plotly for dashboards, pytest for testing, FastAPI for a read-only metrics API, and Git/GitHub for version control. Optional BI/release tools are shown as possible later extensions.

## How the repository maps to the deck

- Days 1–4: `load_to_duckdb.py`, `src/etl.py`, `src/warehouse.py`, `src/contracts.py`, `src/dq_checks.py`, `src/metric_layer.py`.
- Days 5–15: `app.py` and `pages/1_...` through `pages/7_...`, supported by `analytics.vw_*` views.
- Day 16 and Day 20: `src/reporting.py`, `reports/board_pack.html`, and documentation/report templates.
- Day 18: `pages/9_Self_Service_KPI.py` with threshold-based suppression already built into metric views.
- Day 19: `api.py` and `pages/10_Lineage_API.py`.
- Day 17: run instructions and a release checklist are provided. External hosting is not represented as completed because it requires a deployment target and account access.
