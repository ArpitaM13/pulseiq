

\# PulseIQ Analytics — Release Notes



\*\*Release:\*\* v1.0.0

\*\*Release date:\*\* 20 November 2026

\*\*Project:\*\* PulseIQ Analytics

\*\*Reporting period:\*\* September 2026

\*\*Repository:\*\* https://github.com/ArpitaM13/pulseiq

\*\*Dashboard:\*\* https://arpita-pulseiq-dashboard.streamlit.app/



\## 1. Release Overview



This release consolidates the PulseIQ Analytics workforce, finance, operations, AI anomaly, data-quality, dashboard, reporting and metric API capabilities developed across the project phases.



The release includes a 10-slide board presentation and the latest pipeline validation evidence.



\## 2. Key Business Findings



\- September workforce headcount: 441.

\- September revenue: ₹8.03 crore.

\- September net profit: ₹1.50 crore.

\- September operating margin: 18.67%.

\- September attendance rate: 95.19%.

\- Overdue receivables: ₹2.71 crore across 9 clients.

\- Task completion average: 86.23% across 16 records through 7 September.

\- On-time delivery average: 94.19% across 16 records through 7 September.

\- AI anomaly summary: 25 of 25 scored records flagged, with estimated exposure of ₹32.98 lakh.



AI anomaly flags are indicators for investigation, not confirmed fraud or realised financial losses.



\## 3. Deliverables



\- `reports/PulseIQ\_Board\_Presentation\_v1.0.0.pptx` — 10-slide board presentation.

\- `reports/monthly\_report\_2026-09.xlsx` — September monthly report.

\- `build\_report.py` — automated monthly report builder.

\- `api.py` — FastAPI metric endpoints and lineage.

\- `app.py` — Streamlit dashboard.

\- `pages/9\_Self\_Service\_KPI.py` — self-service KPI explorer.

\- `.github/workflows/monthly-report.yml` — scheduled and manually triggered reporting workflow.

\- `requirements.txt` — pinned Python dependencies.



\## 4. Pipeline and Quality Validation



Latest pipeline execution: 20 November 2026.



\- Source worksheets loaded: 33.

\- Worksheet row reconciliations: 33 of 33 passed.

\- Primary-key tables enforced: 31 of 31.

\- Independent metric spot-checks: 3,069 of 3,069 passed.

\- Governed metric definitions: 28.

\- Data-quality checks: 14.

\- Data-quality results: 3 PASS, 7 WARN and 4 FAIL.

\- Two leave records were rejected during ETL and retained outside the clean output.



Outstanding failures include payroll-ledger reconciliation, duplicate payroll rows, orphan employee records and employee-history overlap. These exceptions require remediation.



\## 5. Dashboard and API



Public dashboard:

https://arpita-pulseiq-dashboard.streamlit.app/



The dashboard includes workforce, attendance, attrition, payroll, finance, AI signals, data quality, self-service KPI, cross-department impact and executive scorecard views.



The FastAPI service was tested locally, including health, metric, data-quality and lineage endpoints.



API documentation during local testing:

http://127.0.0.1:8000/docs



\## 6. Known Limitations



\- The deployed dashboard does not yet receive an automated scheduled database refresh.

\- The monthly GitHub Actions workflow generates a report artifact but does not update the deployed Streamlit database.

\- The FastAPI service has been tested locally but is not publicly hosted.

\- The reporting source workbook currently contains data through September 2026.

\- AI anomaly outputs require human validation.

\- Data-quality warnings and failures remain open and should not be treated as resolved.



\## 7. Recommended Next Steps



1\. Investigate September operating-margin decline and expense movements.

2\. Prioritise overdue receivables and assign collection owners.

3\. Resolve payroll and employee-key data-quality failures.

4\. Validate AI anomaly flags with business owners.

5\. Implement a controlled scheduled refresh for the public dashboard.

6\. Plan secure public API hosting and access controls.



\## 8. Release Evidence



\- Board presentation: `reports/PulseIQ\_Board\_Presentation\_v1.0.0.pptx`

\- Monthly report: `reports/monthly\_report\_2026-09.xlsx`

\- Pipeline summary: `reports/pipeline\_summary.json`

\- Data-quality report: `reports/dq\_report.md`

\- Automated workflow: `.github/workflows/monthly-report.yml`



\---



\*\*Release status:\*\* Board presentation and reporting deliverables prepared. Outstanding data-quality issues and deployment limitations are documented for follow-up.
