# Phase 1 evidence map: Tasks 1, 2, 4 and 5

Use this checklist alongside the Phase 1 programme guide. It describes files and intended evidence for this repository; it does not replace the requested 2-3 page submission PDF or any owner-controlled GitHub/programme-site actions.

## Task 1 - Workspace, ETL, contracts, and row conservation

**Implementation:** `load_to_duckdb.py` loads all 33 source workbook tabs into the DuckDB `raw` schema. `src/etl.py` cleans five core workforce tables, normalizes values, flags non-parseable dates/numerics, and quarantines duplicate/invalid records with a source row and reason. `src/contracts.py` applies the supplied 42 column-level rules across four governed feeds. Unexpected columns use the warn-and-preserve policy. `src/row_audit.py` writes one row for each worksheet with rows in, passed, quarantined, raw-to-warehouse row match, and explicit validation scope.

**Evidence after running:** `logs/duckdb_load_summary.json`, `logs/etl_summary_*.json`, `reports/table_row_audit.csv`, `reports/contract_validation.csv`, `data/clean/`, and `rejected/`. Rows in must equal rows passed plus quarantined. Pass-through sheets are clearly labelled because the source contract worksheet does not define column-level rules for every tab.

**Source-data findings:** expected bad rows remain quarantined or flagged; do not manually edit raw values to force a PASS.

## Task 2 - Star schema, keys, joins, and orphans

**Implementation:** `src/warehouse.py` rebuilds the `warehouse` schema from `raw` and enforces candidate primary keys that are non-null and unique in the supplied workbook. `docs/star_schema.mmd` is the ER/star-schema source. The loader compares row counts before and after raw-to-warehouse copy and audits relationship keys without enforcing foreign keys that would prevent seeded data issues from being investigated.

**Evidence after running:** `docs/star_schema.mmd`, `docs/warehouse_keys_and_joins.md`, `reports/warehouse_row_counts.csv`, `reports/primary_key_audit.csv`, and `reports/foreign_key_audit.csv`. Employee facts are joined through `employee_key`, which identifies a specific SCD Type 2 version; `employee_id` alone repeats across versions.

**Known issue:** two payroll rows (`PI-X0003`, `PI-X0004`) contain orphan employee keys/IDs and are intentionally retained in raw data for DQ-C04 to catch.

## Task 4 - Governed metric layer

**Implementation:** `src/metric_layer.py` creates named SQL views M01-M28, `analytics.vw_metric_catalog`, lineage and supporting marts. Defined minimum-group rules suppress restricted values below their threshold. `src/metric_hand_checks.py` independently recalculates five representative metrics in pandas and compares values and NULL suppression decisions with the SQL views.

**Evidence after running:** `reports/manual_metric_checks.csv`, `docs/metric_validation.md`, and SQL view/catalog queries against DuckDB. The current supplied data has forecasts after the latest actual headcount month, so M28 Forecast MAPE is NULL for future periods until actuals arrive; NULL is not changed to zero.

## Task 5 - Workforce and headcount dashboard

**Implementation:** the Streamlit workforce page reads analytics views only. It includes company-wide KPI cards, date and department filters, a department-aware headcount trend, department breakdown, work-mode chart, city-tier chart, numerical finding titles/captions, compact INR cards, and privacy notes. Chart/table layout uses Streamlit's `width="stretch"` API.

**Evidence after running:** launch with `run_dashboard.bat`, open the local URL (normally `http://localhost:8501`), navigate to `Workforce and Headcount`, test both filters, and capture a screenshot. Confirm the other dashboard pages also load and show no exception tracebacks.

## Owner-controlled submission items

- Run `python run_pipeline.py` and `python -m pytest -q` in your local Windows environment after applying this package.
- Review DQ FAIL/WARN findings and keep seeded source issues documented.
- Create or verify the private GitHub repository, commit this version, tag `phase-1`, push the tag, and complete any required reviewer invitation.
- Fill the programme report template with your name, real repository URL, screenshot evidence, what you learned in your own words, and export the required PDF. Upload it in the programme portal yourself.
