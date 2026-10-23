# Metric spot-check evidence

After `python run_pipeline.py`, the pipeline independently recalculates five representative measures with pandas and compares the results with their governed DuckDB metric views. It writes `reports/manual_metric_checks.csv` and stops before the final handover report if any row differs or if a suppression decision is inconsistent.

| Metric ID | Measure | Independent calculation |
|---|---|---|
| M01 | Headcount | Sum `headcount_end` by month and department; suppress when group size is below 5. |
| M02 | Hires | Sum `hires` by month and department; apply the same published minimum group size. |
| M04 | Monthly attrition | `100 × sum(exits) / sum(headcount_start)` by month and department; suppress below the metric's minimum group size of 10. |
| M07 | Gross pay | Sum gross pay by month and department after matching the employee version key and de-duplicating employee/run pairs. |
| M13 | Attendance rate | `(sum(present_days) + 0.5 × sum(half_days_unpaid)) / sum(scheduled_days)` on attendance records that meet the exit-date rule. |

The comparison is made row-by-row across periods and departments, including null-vs-null suppression decisions. Financial/ratio results are compared with a tolerance of `max(0.01, |expected| × 1e-8)`. This is an automated reproducible check; it complements, rather than replaces, the analyst's manual review of the metric definitions and source caveats. Rolling and voluntary attrition views (M05/M06) remain NULL until a full 12-month window is available, so partial-window figures are not mislabeled as 12-month rates. KPI task-completion values are aligned to calendar months by sprint start month before joining to the monthly targets.


## Forecast MAPE availability

The supplied forecast starts in October 2026 while actual headcount ends in September 2026. M28 is therefore represented for forecast periods with a NULL metric value until matching actual headcount exists. This is intentionally different from a numeric zero and prevents the catalog from making the measure disappear.
