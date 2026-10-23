"""One-command orchestration for PulseIQ Analytics."""
from __future__ import annotations
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from load_to_duckdb import load_to_duckdb
from src.etl import run_etl
from src.warehouse import build_warehouse, mark_pipeline_success
from src.row_audit import build_row_audit
from src.contracts import validate_contracts
from src.metric_layer import create_metric_views
from src.metric_hand_checks import run_manual_checks
from src.dq_checks import run_checks
from src.reporting import build_reports


def main() -> None:
    print("\n[1/6] Loading all workbook sheets into DuckDB raw schema...")
    raw_summary = load_to_duckdb()
    print("\n[2/6] Cleaning core Phase-1 tables and quarantining invalid rows...")
    etl_summary = run_etl()
    print("\n[3/6] Building warehouse and staging layers...")
    build_warehouse()
    print("\n[4/6] Validating supplied data contracts...")
    contract_results = validate_contracts()
    print(f"Contract results: {len(contract_results)} rule/column rows; FAIL={(contract_results.status == 'FAIL').sum()}, WARN={(contract_results.status == 'WARN').sum()}")
    row_audit = build_row_audit(raw_summary, etl_summary)
    print(f"Row reconciliation: {len(row_audit)} worksheets; all rows conserved and raw-to-warehouse counts match.")
    print(f"Row audit: {ROOT / 'reports' / 'table_row_audit.csv'}")
    print("\n[5/6] Creating governed metric views and running 14 quality checks...")
    create_metric_views()
    manual_results = run_manual_checks()
    manual_failures = int((~manual_results["passed"]).sum())
    print(f"Independent metric spot-checks: {len(manual_results)} rows; failures={manual_failures}")
    if manual_failures:
        raise RuntimeError("Independent metric checks failed; see reports/manual_metric_checks.csv")
    dq_results = run_checks()
    # The freshness check should describe a fully completed run, not merely the
    # earlier warehouse stage. If any DQ query itself errored, do not mark success.
    if not (dq_results["status"] == "ERROR").any():
        mark_pipeline_success()
        dq_results = run_checks()  # refreshes DQ-C13 after the completed-run log is written
    print(dq_results[["check_id", "status", "rows_affected"]].to_string(index=False))
    print("\n[6/6] Building handover summary...")
    report = build_reports()
    print("\nPipeline completed.")
    print(f"Worksheets loaded: {len(raw_summary['tables'])}")
    print(f"Core ETL tables: {len(etl_summary['tables'])}")
    print(f"Metric definitions: {report['governed_metrics_defined']}")
    print(f"Quality checks: {report['dq_checks_run']}")
    print(f"Database: {ROOT / 'data' / 'pulseiq.duckdb'}")
    print(f"Board pack: {ROOT / 'reports' / 'board_pack.html'}")
    print(f"Summary: {ROOT / 'reports' / 'pipeline_summary.json'}")


if __name__ == "__main__":
    main()
