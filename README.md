# PulseIQ Analytics

A local analytics workspace for the fictional company **Zenith Nova Technologies**, built from the supplied PulseIQ Analytics workbook. The project brings workforce, payroll, attendance, finance, delivery, AI-signal and data-quality information into one DuckDB-backed model.

> **Dataset note:** The workbook is fictional training data. It deliberately contains known data-quality issues. The project keeps raw data unchanged, reports those issues, and uses validation-controlled analytical views where appropriate. A failed quality check is not hidden or automatically “fixed”.

## What is included

- **Workbook ingestion:** all 33 worksheet tabs are loaded into DuckDB's `raw` schema.
- **ETL and quarantine:** five Phase-1 core tables are standardized and validated into `data/clean/`; rejected records and explanations (including exact duplicate rows) are written to `rejected/`. The row reconciliation is `rows_in = rows_out + rejected`.
- **Warehouse:** the source star-schema tables are available in the `warehouse` schema; ETL clean/rejected outputs are available in `staging`.
- **Data contracts:** the supplied `data_contracts` sheet is evaluated for its four governed feeds. Unexpected columns are warned about and preserved rather than silently dropped.
- **Data quality gatekeeper:** all 14 checks from the workbook catalogue run into `audit.dq_results` and are exported to `reports/`.
- **Metric layer:** 28 named SQL metric views (M01–M28), a catalog and lineage view. Privacy-sensitive values are suppressed below their published group size. Five representative metrics are independently spot-checked with pandas against their governed SQL views.
- **Dashboards:** Streamlit pages for workforce, attendance/leave, attrition risk, productivity, payroll/budget, finance/receivables, AI signals, data quality, KPI exploration, lineage/API, cross-department comparison and executive health scorecard.
- **Read-only API:** FastAPI endpoints for metric catalog/data, quality results and lineage.
- **Handover evidence:** CSV/JSON summaries, an HTML board pack, independent metric spot-check output, architecture notes, a walkthrough, report templates and a GitHub Actions workflow.

## Setup (Windows PowerShell)

Open PowerShell in the folder containing this README. If you have already created a `.venv`, activate it first; otherwise run:

```powershell
if (-not (Test-Path .venv)) { py -3.10 -m venv .venv }
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

The setup only creates `.venv` and `.env` when they do not already exist, so it will not overwrite your settings.

## Run the full pipeline

```powershell
python run_pipeline.py
```

This one command loads the workbook, runs ETL, builds the warehouse, checks data contracts, creates metric views, runs the 14 DQ checks and produces reports. The database file is `data/pulseiq.duckdb`.

For step-by-step stages, you can also run:

```powershell
python load_to_duckdb.py
python -m src.etl
python -m src.warehouse
python -m src.contracts
python -m src.metric_layer
python -m src.dq_checks
python -m src.reporting
```

The stages can be rerun. Worksheet tables and clean CSV files are replaced rather than appended, so reruns do not duplicate output rows.

## Start the dashboard

After the pipeline succeeds, open a second terminal in the project folder, activate `.venv`, and run:

```powershell
streamlit run app.py
```

Streamlit prints a local URL (normally `http://localhost:8501`). Open that URL in your browser. Use the left sidebar to move between the pages.

## Start the metrics API

Open another terminal in the project folder, activate `.venv`, and run:

```powershell
uvicorn api:app --reload
```

Useful endpoints:

- `GET /health`
- `GET /metrics`
- `GET /metrics/M01`
- `GET /dq`
- `GET /lineage`
- `GET /docs` (interactive API documentation)

The API is read-only. It does not accept data writes.

## Verify the work

```powershell
python -m compileall -q .
python -m pytest -q
```

A test run should follow a successful pipeline run because the tests inspect the built database and views.

## Main outputs

| Path | Purpose |
|---|---|
| `data/pulseiq.duckdb` | Local DuckDB database with `raw`, `warehouse`, `staging`, `analytics` and `audit` schemas |
| `data/clean/` | Clean CSVs for five core Phase-1 tables |
| `rejected/` | Quarantined ETL rows and contract-rejected rows with reason columns |
| `logs/duckdb_load_summary.json` | Source worksheet counts |
| `logs/etl_summary_*.json` | ETL row-count reconciliation |
| `reports/contract_validation.csv` | Contract rule results |
| `reports/dq_results.csv` and `reports/dq_report.md` | 14 quality checks and explanations |
| `reports/known_issue_review.csv` | Map from the 11 known training issues to expected checks |
| `reports/manual_metric_checks.csv` | Independent pandas-versus-SQL validation for five metrics and suppression decisions |
| `docs/metric_validation.md` | Formula-by-formula notes for the five spot checks |
| `reports/pipeline_summary.json` | Machine-readable pipeline summary |
| `reports/board_pack.html` | Browser-readable executive handover report |
| `docs/star_schema.mmd` | Star-schema diagram source |

## Model and quality decisions

- Raw data is immutable after ingestion. It is the place to investigate known planted issues.
- Clean ETL outputs preserve quarantined rows with a reason; date values are not automatically swapped or repaired.
- Employee history is joined through `employee_key` to avoid counting a historical employee under the wrong department.
- Payroll metrics use a deduplicated employee/run pair and matched employee keys. The quality report still flags duplicate/orphan raw records.
- Dashboard values are served from `analytics` views, not raw worksheets. Views suppress group values below the applicable minimum size.
- Forecast MAPE remains NULL for forecast periods that have no matching actual headcount yet. The M28 view still emits those forecast periods so the metric remains discoverable; MAPE becomes measurable only after actuals arrive.
- Unexpected columns in governed feeds produce warnings and remain in raw storage for review.

## Status and production caveat

This is a **local release candidate** intended for study, demonstration and review. The code builds locally reproducible ETL, warehouse, metric views, dashboards, reports and a read-only API. A cloud deployment, private GitHub access/collaboration, secrets review and actual programme-site submission must be completed using the user's own accounts. See `docs/implementation_status.md` for the task-by-task mapping and remaining release actions.
