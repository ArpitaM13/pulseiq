# SQL and metric layer

The authoritative SQL view definitions live in `src/metric_layer.py` so the pipeline can create them repeatably. They are created in the DuckDB `analytics` schema, with IDs M01–M28 named after the supplied `metric_dictionary`. The queries are view-only; they do not mutate raw source rows.

Quick checks in DuckDB:

```sql
SELECT * FROM analytics.vw_metric_catalog ORDER BY metric_id;
SELECT check_id, check_name, status, rows_affected FROM audit.dq_results ORDER BY check_id;
SELECT period, metric_value FROM analytics.vw_metric_m01_headcount WHERE department_id='D01' ORDER BY period;
SELECT * FROM analytics.vw_lineage WHERE metric_id='M09';
```
