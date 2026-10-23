# PulseIQ Analytics — Architecture Notes

## Processing flow

1. **Extract:** `load_to_duckdb.py` reads every tab in the provided Excel workbook and writes each tab to the `raw` schema. The load summary records source row and column counts.
2. **Transform:** `src/etl.py` normalizes the five core Phase-1 tables, parses dates/numerics, removes exact duplicate rows deterministically, runs rule checks and writes clean/quarantine CSVs. The original `raw` tables are unchanged.
3. **Warehouse:** `src/warehouse.py` mirrors source tables into `warehouse`, writes clean and rejected outputs to `staging`, and records row-count/run information in `audit`.
4. **Contract gate:** `src/contracts.py` evaluates the supplied contract rows for anomaly, attrition-risk, forecast and task feeds. It checks nullability, common type/range/enum/ID/date rules and writes row-level rejected copies. Unexpected columns are WARNed and preserved.
5. **Quality gate:** `src/dq_checks.py` runs the 14 rules in `dq_checks_catalog`, writes the result table and produces an issue-to-check review for the 11 documented seeded issues.
6. **Metric layer:** `src/metric_layer.py` builds 28 official metric views and supporting analytical views for dashboards. Core analytical views filter selected invalid records but preserve the underlying raw records for audit.
7. **Consumption:** `app.py` and the `pages/` scripts read named `analytics.vw_*` views. `api.py` exposes read-only metric and lineage endpoints. `src/reporting.py` creates the HTML board pack and JSON summary.

## Schemas

- `raw`: worksheet copies; source of truth for debugging and audit.
- `warehouse`: table-level copy of source business/reference tables.
- `staging`: core clean/rejected ETL tables.
- `analytics`: data-quality-controlled inputs, KPI metric views, support marts and lineage views.
- `audit`: ETL run log, row-count inventory, data-contract results and DQ results.

## Data handling principles

- Never rewrite the source Excel file to make tests pass.
- Keep invalid data visible through row-level quarantine and DQ output.
- A critical check failure requires review before production promotion. Warnings require a documented decision.
- Use `employee_key` for employee-version joins; `employee_id` alone is a person identifier and may repeat in the historical dimension.
- A displayed KPI must come from a governed view and should include its period/grain. Suppressed values are null, not zero.
- AI anomaly and attrition-risk signals prompt investigation; they do not prove misconduct or predict a specific outcome with certainty.
