"""Read-only FastAPI endpoint layer for governed metrics and data-quality results."""
from __future__ import annotations
from pathlib import Path
import duckdb
from fastapi import FastAPI, HTTPException, Query

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "data" / "pulseiq.duckdb"
app = FastAPI(title="PulseIQ Metrics API", version="1.0.0", description="Read-only API over governed PulseIQ analytics views.")


def run_query(sql: str, params: list | None = None):
    if not DB_FILE.exists():
        raise HTTPException(status_code=503, detail="Database is not built yet. Run python run_pipeline.py first.")
    con = duckdb.connect(str(DB_FILE), read_only=True)
    try:
        return con.execute(sql, params or []).df().to_dict(orient="records")
    finally:
        con.close()


@app.get("/health")
def health():
    if not DB_FILE.exists():
        return {"status": "not_ready", "database": str(DB_FILE)}
    try:
        row = run_query("SELECT COUNT(*) AS metric_rows FROM analytics.vw_all_metrics")[0]
        return {"status": "ok", "database": str(DB_FILE), "metric_rows": row["metric_rows"]}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database exists but analytics views are not ready: {type(exc).__name__}")


@app.get("/metrics")
def metrics(metric_id: str | None = Query(default=None, pattern=r"^M\d{2}$"), limit: int = Query(default=500, ge=1, le=5000)):
    if metric_id:
        return run_query("SELECT * FROM analytics.vw_all_metrics WHERE metric_id=? LIMIT ?", [metric_id, limit])
    return run_query("SELECT * FROM analytics.vw_metric_catalog ORDER BY metric_id")


@app.get("/metrics/{metric_id}")
def metric_detail(metric_id: str, limit: int = Query(default=500, ge=1, le=5000)):
    if not metric_id.startswith("M") or len(metric_id) != 3 or not metric_id[1:].isdigit():
        raise HTTPException(status_code=400, detail="Metric ID must look like M01.")
    catalog = run_query("SELECT metric_id FROM analytics.vw_metric_catalog WHERE metric_id=?", [metric_id])
    if not catalog:
        raise HTTPException(status_code=404, detail="Metric not found.")
    return run_query("SELECT * FROM analytics.vw_all_metrics WHERE metric_id=? ORDER BY period LIMIT ?", [metric_id, limit])


@app.get("/dq")
def dq():
    return run_query("SELECT check_id,check_name,severity,rows_affected,status,description,recommended_action FROM analytics.vw_dq_results ORDER BY check_id")


@app.get("/lineage")
def lineage(metric_id: str | None = Query(default=None, pattern=r"^M\d{2}$")):
    if metric_id:
        return run_query("SELECT * FROM analytics.vw_lineage WHERE metric_id=?", [metric_id])
    return run_query("SELECT * FROM analytics.vw_lineage ORDER BY metric_id")
