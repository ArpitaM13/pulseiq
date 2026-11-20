"""Read-only FastAPI endpoints for governed PulseIQ metrics, DQ and lineage."""
from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path

import duckdb
from fastapi import FastAPI, HTTPException, Query

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "data" / "pulseiq.duckdb"

app = FastAPI(
    title="PulseIQ Metrics API",
    version="1.0.0",
    description="Read-only API over governed PulseIQ analytics views.",
)


def json_safe(value):
    """Convert database values into JSON-compatible values."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    # Handle NumPy scalar values returned by pandas/DuckDB.
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except (ValueError, TypeError):
            pass
    return value


def run_query(sql: str, params: list | None = None) -> list[dict]:
    if not DB_FILE.exists():
        raise HTTPException(
            status_code=503,
            detail="Database is not built yet. Run python run_pipeline.py first.",
        )

    con = duckdb.connect(str(DB_FILE), read_only=True)
    try:
        rows = con.execute(sql, params or []).fetchdf().to_dict(orient="records")
        return json_safe(rows)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {type(exc).__name__}",
        ) from exc
    finally:
        con.close()


def latest_refresh() -> dict | None:
    rows = run_query(
        """
        SELECT started_at, finished_at, status, source_file
        FROM audit.etl_run_log
        WHERE UPPER(status) = 'SUCCESS'
        ORDER BY finished_at DESC
        LIMIT 1
        """
    )
    return rows[0] if rows else None


@app.get("/health")
def health():
    if not DB_FILE.exists():
        return {"status": "not_ready", "database": str(DB_FILE)}

    rows = run_query(
        "SELECT COUNT(*) AS metric_rows FROM analytics.vw_all_metrics"
    )
    return {
        "status": "ok",
        "database": str(DB_FILE),
        "metric_rows": rows[0]["metric_rows"],
    }


@app.get("/metrics")
def metrics(
    metric_id: str | None = Query(default=None, pattern=r"^M\d{2}$"),
    limit: int = Query(default=500, ge=1, le=5000),
):
    if metric_id:
        return metric_detail(metric_id, limit)
    return run_query(
        "SELECT * FROM analytics.vw_metric_catalog ORDER BY metric_id"
    )


@app.get("/metrics/{metric_id}")
def metric_detail(
    metric_id: str,
    limit: int = Query(default=500, ge=1, le=5000),
):
    if (
        not metric_id.startswith("M")
        or len(metric_id) != 3
        or not metric_id[1:].isdigit()
    ):
        raise HTTPException(
            status_code=400,
            detail="Metric ID must look like M01.",
        )

    catalog = run_query(
        "SELECT * FROM analytics.vw_metric_catalog WHERE metric_id = ?",
        [metric_id],
    )
    if not catalog:
        raise HTTPException(status_code=404, detail="Metric not found.")

    definition = catalog[0]
    records = run_query(
        """
        SELECT *
        FROM analytics.vw_all_metrics
        WHERE metric_id = ?
        ORDER BY period
        LIMIT ?
        """,
        [metric_id, limit],
    )

    return {
        "metric_id": definition["metric_id"],
        "metric_name": definition["metric_name"],
        "definition": definition["business_definition"],
        "formula": definition["formula"],
        "source_table": definition["source_table"],
        "owner_team": definition["owner_team"],
        "grain": definition["grain"],
        "unit": definition["unit"],
        "good_direction": definition["good_direction"],
        "caveat": definition["caveat"],
        "minimum_group_size": definition["minimum_group_size"],
        "last_refresh": latest_refresh(),
        "records": records,
    }


@app.get("/dq")
def dq():
    return run_query(
        """
        SELECT check_id, check_name, severity, rows_affected,
               status, description, recommended_action
        FROM analytics.vw_dq_results
        ORDER BY check_id
        """
    )


@app.get("/lineage")
def lineage(
    metric_id: str | None = Query(default=None, pattern=r"^M\d{2}$"),
):
    if metric_id:
        return run_query(
            "SELECT * FROM analytics.vw_lineage WHERE metric_id = ?",
            [metric_id],
        )
    return run_query(
        "SELECT * FROM analytics.vw_lineage ORDER BY metric_id"
    )
