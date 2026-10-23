from pathlib import Path
import pytest

duckdb = pytest.importorskip("duckdb")
ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "data" / "pulseiq.duckdb"


def connection():
    if not DB_FILE.exists():
        pytest.skip("Run `python run_pipeline.py` before integrated tests.")
    return duckdb.connect(str(DB_FILE), read_only=True)


def test_all_workbook_sheets_loaded():
    con = connection()
    try:
        n = con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='raw' AND table_type='BASE TABLE'").fetchone()[0]
        assert n == 33
    finally:
        con.close()


def test_all_28_metric_views_return_a_catalogued_id():
    con = connection()
    try:
        n = con.execute("SELECT COUNT(DISTINCT metric_id) FROM analytics.vw_all_metrics").fetchone()[0]
        c = con.execute("SELECT COUNT(*) FROM analytics.vw_metric_catalog").fetchone()[0]
        assert c == 28
        assert n == 28
    finally:
        con.close()


def test_all_14_quality_checks_were_recorded():
    con = connection()
    try:
        n = con.execute("SELECT COUNT(DISTINCT check_id) FROM audit.dq_results").fetchone()[0]
        assert n == 14
    finally:
        con.close()


def test_private_metric_values_are_suppressed():
    con = connection()
    try:
        n = con.execute("SELECT COUNT(*) FROM analytics.vw_all_metrics WHERE metric_value IS NOT NULL AND min_group_size IS NOT NULL AND group_size<min_group_size").fetchone()[0]
        assert n == 0
    finally:
        con.close()


def test_all_worksheet_row_audit_reconciles_and_primary_keys_are_enforced():
    con = connection()
    try:
        n = con.execute("SELECT COUNT(*) FROM audit.table_row_audit").fetchone()[0]
        assert n == 33
        bad_rows = con.execute("SELECT COUNT(*) FROM audit.table_row_audit WHERE NOT row_conservation_ok OR NOT raw_matches_warehouse").fetchone()[0]
        assert bad_rows == 0
        bad_keys = con.execute("SELECT COUNT(*) FROM audit.primary_key_audit WHERE status <> 'PASS'").fetchone()[0]
        assert bad_keys == 0
    finally:
        con.close()


def test_warehouse_records_orphan_relationship_findings_without_dropping_raw_rows():
    con = connection()
    try:
        raw_rows = con.execute("SELECT COUNT(*) FROM warehouse.fact_payroll").fetchone()[0]
        assert raw_rows == 7344
        checks = con.execute("SELECT COUNT(*) FROM audit.foreign_key_audit WHERE child_table='fact_payroll' AND child_column='employee_key' AND orphan_rows=2 AND status='FAIL'").fetchone()[0]
        assert checks == 1
    finally:
        con.close()
