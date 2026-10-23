"""Create the governed, privacy-aware metric views (M01-M28) and supporting marts."""
from __future__ import annotations
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "data" / "pulseiq.duckdb"

METRIC_VIEWS: dict[str, str] = {
"vw_metric_m01_headcount": """
WITH a AS (SELECT CAST(month_start_date AS DATE) period, department_id, SUM(headcount_end)::DOUBLE metric_raw_value, SUM(headcount_end)::DOUBLE n FROM warehouse.fact_headcount_monthly GROUP BY 1,2)
SELECT 'M01' metric_id, 'Headcount' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN metric_raw_value END metric_value, n group_size, 5 min_group_size, 'count' unit FROM a""",
"vw_metric_m02_hires": """
WITH a AS (SELECT CAST(month_start_date AS DATE) period, department_id, SUM(hires)::DOUBLE metric_raw_value, SUM(headcount_end)::DOUBLE n FROM warehouse.fact_headcount_monthly GROUP BY 1,2)
SELECT 'M02' metric_id, 'Hires' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN metric_raw_value END metric_value, n group_size, 5 min_group_size, 'count' unit FROM a""",
"vw_metric_m03_exits": """
WITH a AS (SELECT CAST(month_start_date AS DATE) period, department_id, SUM(exits)::DOUBLE metric_raw_value, SUM(headcount_end)::DOUBLE n FROM warehouse.fact_headcount_monthly GROUP BY 1,2)
SELECT 'M03' metric_id, 'Exits' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN metric_raw_value END metric_value, n group_size, 5 min_group_size, 'count' unit FROM a""",
"vw_metric_m04_monthly_attrition": """
WITH a AS (SELECT CAST(month_start_date AS DATE) period, department_id, SUM(exits)::DOUBLE exits, SUM(headcount_start)::DOUBLE denom, SUM(headcount_end)::DOUBLE n FROM warehouse.fact_headcount_monthly GROUP BY 1,2)
SELECT 'M04' metric_id, 'Attrition rate (monthly)' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 10 THEN 100*exits/NULLIF(denom,0) END metric_value, n group_size, 10 min_group_size, 'percent' unit FROM a""",
"vw_metric_m05_rolling_attrition": """
WITH a AS (SELECT CAST(month_start_date AS DATE) period, department_id, SUM(exits)::DOUBLE exits, SUM(headcount_end)::DOUBLE hc FROM warehouse.fact_headcount_monthly GROUP BY 1,2), r AS (SELECT *, COUNT(*) OVER(PARTITION BY department_id ORDER BY period ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) months_in_window, SUM(exits) OVER(PARTITION BY department_id ORDER BY period ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) exits_12m, AVG(hc) OVER(PARTITION BY department_id ORDER BY period ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) avg_hc_12m FROM a)
SELECT 'M05' metric_id, 'Attrition rate (rolling 12 months)' metric_name, period, department_id, department_id dimension_label, CASE WHEN months_in_window = 12 AND hc >= 10 THEN 100*exits_12m/NULLIF(avg_hc_12m,0) END metric_value, hc group_size, 10 min_group_size, 'percent' unit FROM r""",
"vw_metric_m06_voluntary_attrition": """
WITH a AS (SELECT CAST(month_start_date AS DATE) period, department_id, SUM(voluntary_exits)::DOUBLE exits, SUM(headcount_end)::DOUBLE hc FROM warehouse.fact_headcount_monthly GROUP BY 1,2), r AS (SELECT *, COUNT(*) OVER(PARTITION BY department_id ORDER BY period ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) months_in_window, SUM(exits) OVER(PARTITION BY department_id ORDER BY period ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) exits_12m, AVG(hc) OVER(PARTITION BY department_id ORDER BY period ROWS BETWEEN 11 PRECEDING AND CURRENT ROW) avg_hc_12m FROM a)
SELECT 'M06' metric_id, 'Voluntary attrition rate' metric_name, period, department_id, department_id dimension_label, CASE WHEN months_in_window = 12 AND hc >= 10 THEN 100*exits_12m/NULLIF(avg_hc_12m,0) END metric_value, hc group_size, 10 min_group_size, 'percent' unit FROM r""",
"vw_metric_m07_gross_pay": """
WITH a AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, department_id, SUM(gross_pay)::DOUBLE metric_raw_value, COUNT(DISTINCT employee_id)::DOUBLE n FROM analytics.fact_payroll_valid GROUP BY 1,2)
SELECT 'M07' metric_id, 'Gross pay' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN metric_raw_value END metric_value, n group_size, 5 min_group_size, 'INR' unit FROM a""",
"vw_metric_m08_net_pay": """
WITH a AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, department_id, SUM(net_pay)::DOUBLE metric_raw_value, COUNT(DISTINCT employee_id)::DOUBLE n FROM analytics.fact_payroll_valid GROUP BY 1,2)
SELECT 'M08' metric_id, 'Net pay' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN metric_raw_value END metric_value, n group_size, 5 min_group_size, 'INR' unit FROM a""",
"vw_metric_m09_payroll_cost": """
WITH a AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, department_id, SUM(employer_cost)::DOUBLE metric_raw_value, COUNT(DISTINCT employee_id)::DOUBLE n FROM analytics.fact_payroll_valid GROUP BY 1,2)
SELECT 'M09' metric_id, 'Payroll cost (employer cost)' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN metric_raw_value END metric_value, n group_size, 5 min_group_size, 'INR' unit FROM a""",
"vw_metric_m10_cost_per_head": """
WITH a AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, department_id, SUM(employer_cost)::DOUBLE employer_cost_total, COUNT(DISTINCT employee_id)::DOUBLE n FROM analytics.fact_payroll_valid GROUP BY 1,2)
SELECT 'M10' metric_id, 'Cost per head' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN employer_cost_total/NULLIF(n,0) END metric_value, n group_size, 5 min_group_size, 'INR' unit FROM a""",
"vw_metric_m11_overtime_share": """
WITH a AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, department_id, SUM(overtime_pay)::DOUBLE overtime_pay_total, SUM(employer_cost)::DOUBLE employer_cost_total, COUNT(DISTINCT employee_id)::DOUBLE n FROM analytics.fact_payroll_valid GROUP BY 1,2)
SELECT 'M11' metric_id, 'Overtime share' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN 100*overtime_pay_total/NULLIF(employer_cost_total,0) END metric_value, n group_size, 5 min_group_size, 'percent' unit FROM a""",
"vw_metric_m12_variable_pay_share": """
WITH a AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, department_id, SUM(variable_pay)::DOUBLE variable_pay_total, SUM(gross_pay)::DOUBLE gross_pay_total, COUNT(DISTINCT employee_id)::DOUBLE n FROM analytics.fact_payroll_valid GROUP BY 1,2)
SELECT 'M12' metric_id, 'Variable pay share' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN 100*variable_pay_total/NULLIF(gross_pay_total,0) END metric_value, n group_size, 5 min_group_size, 'percent' unit FROM a""",
"vw_metric_m13_attendance_rate": """
WITH a AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, department_id, (SUM(present_days)+0.5*SUM(half_days_unpaid))::DOUBLE present_days_total, SUM(scheduled_days)::DOUBLE scheduled_days_total, COUNT(DISTINCT employee_id)::DOUBLE n FROM analytics.fact_attendance_valid GROUP BY 1,2)
SELECT 'M13' metric_id, 'Attendance rate' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN present_days_total/NULLIF(scheduled_days_total,0) END metric_value, n group_size, 5 min_group_size, 'ratio' unit FROM a""",
"vw_metric_m14_late_arrival_rate": """
WITH a AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, department_id, SUM(late_arrivals)::DOUBLE late_arrival_total, SUM(present_days)::DOUBLE present_days_total, COUNT(DISTINCT employee_id)::DOUBLE n FROM analytics.fact_attendance_valid GROUP BY 1,2)
SELECT 'M14' metric_id, 'Late arrival rate' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN late_arrival_total/NULLIF(present_days_total,0) END metric_value, n group_size, 5 min_group_size, 'ratio' unit FROM a""",
"vw_metric_m15_lop_days": """
WITH a AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, department_id, SUM(lop_days)::DOUBLE metric_raw_value, COUNT(DISTINCT employee_id)::DOUBLE n FROM analytics.fact_payroll_valid GROUP BY 1,2)
SELECT 'M15' metric_id, 'Leave without pay days' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 5 THEN metric_raw_value END metric_value, n group_size, 5 min_group_size, 'days' unit FROM a""",
"vw_metric_m16_revenue": """
WITH a AS (SELECT CAST(date_trunc('month',entry_date) AS DATE) period, CAST(account_code AS VARCHAR) account_label, SUM(-signed_amount_debit_positive)::DOUBLE metric_raw_value FROM warehouse.fact_ledger WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4004 GROUP BY 1,2)
SELECT 'M16' metric_id, 'Revenue' metric_name, period, CAST(NULL AS VARCHAR) department_id, account_label dimension_label, metric_raw_value metric_value, CAST(NULL AS DOUBLE) group_size, CAST(NULL AS INTEGER) min_group_size, 'INR' unit FROM a""",
"vw_metric_m17_net_profit": """
WITH a AS (SELECT CAST(date_trunc('month',entry_date) AS DATE) period, SUM(-signed_amount_debit_positive)::DOUBLE metric_raw_value FROM warehouse.fact_ledger WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 4000 AND 5999 GROUP BY 1)
SELECT 'M17' metric_id, 'Net profit' metric_name, period, CAST(NULL AS VARCHAR) department_id, 'All company' dimension_label, metric_raw_value metric_value, CAST(NULL AS DOUBLE) group_size, CAST(NULL AS INTEGER) min_group_size, 'INR' unit FROM a""",
"vw_metric_m18_operating_margin": """
WITH r AS (SELECT CAST(date_trunc('month',entry_date) AS DATE) period, SUM(-signed_amount_debit_positive)::DOUBLE revenue_total FROM warehouse.fact_ledger WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4004 GROUP BY 1), p AS (SELECT CAST(date_trunc('month',entry_date) AS DATE) period, SUM(-signed_amount_debit_positive)::DOUBLE net_profit_total FROM warehouse.fact_ledger WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 4000 AND 5999 GROUP BY 1)
SELECT 'M18' metric_id, 'Operating margin' metric_name, p.period, CAST(NULL AS VARCHAR) department_id, 'All company' dimension_label, 100*p.net_profit_total/NULLIF(r.revenue_total,0) metric_value, CAST(NULL AS DOUBLE) group_size, CAST(NULL AS INTEGER) min_group_size, 'percent' unit FROM p JOIN r USING(period)""",
"vw_metric_m19_payroll_percent_revenue": """
WITH r AS (SELECT CAST(date_trunc('month',entry_date) AS DATE) period, SUM(-signed_amount_debit_positive)::DOUBLE revenue_total FROM warehouse.fact_ledger WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 4001 AND 4004 GROUP BY 1), p AS (SELECT CAST(date_trunc('month',entry_date) AS DATE) period, SUM(signed_amount_debit_positive)::DOUBLE payroll_cost_total FROM warehouse.fact_ledger WHERE TRY_CAST(account_code AS INTEGER) BETWEEN 5001 AND 5005 GROUP BY 1)
SELECT 'M19' metric_id, 'Payroll as % of revenue' metric_name, p.period, CAST(NULL AS VARCHAR) department_id, 'All company' dimension_label, 100*p.payroll_cost_total/NULLIF(r.revenue_total,0) metric_value, CAST(NULL AS DOUBLE) group_size, CAST(NULL AS INTEGER) min_group_size, 'percent' unit FROM p JOIN r USING(period)""",
"vw_metric_m20_dso": """
WITH cutoff AS (SELECT MAX(CAST(invoice_date AS DATE)) d FROM warehouse.fact_invoice), ar AS (SELECT SUM(balance_due)::DOUBLE outstanding_balance FROM analytics.fact_invoice_valid WHERE status NOT IN ('DRAFT','CANCELLED')), sales AS (SELECT SUM(total_amount)::DOUBLE sales_total FROM warehouse.fact_invoice i, cutoff c WHERE CAST(i.invoice_date AS DATE) > c.d - INTERVAL 90 DAY AND CAST(i.invoice_date AS DATE) <= c.d AND i.status NOT IN ('DRAFT','CANCELLED'))
SELECT 'M20' metric_id, 'Days sales outstanding (DSO)' metric_name, CAST(c.d AS DATE) period, CAST(NULL AS VARCHAR) department_id, 'All company' dimension_label, (ar.outstanding_balance/NULLIF(sales.sales_total,0))*90 metric_value, CAST(NULL AS DOUBLE) group_size, CAST(NULL AS INTEGER) min_group_size, 'days' unit FROM cutoff c CROSS JOIN ar CROSS JOIN sales""",
"vw_metric_m21_overdue_receivables": """
WITH cutoff AS (SELECT MAX(CAST(invoice_date AS DATE)) d FROM warehouse.fact_invoice), a AS (SELECT i.client_id, SUM(i.balance_due)::DOUBLE metric_raw_value FROM analytics.fact_invoice_valid i, cutoff c WHERE CAST(i.due_date AS DATE) < c.d AND i.balance_due > 0 AND i.status NOT IN ('DRAFT','CANCELLED') GROUP BY i.client_id)
SELECT 'M21' metric_id, 'Overdue receivables' metric_name, CAST(c.d AS DATE) period, CAST(NULL AS VARCHAR) department_id, a.client_id dimension_label, a.metric_raw_value metric_value, CAST(NULL AS DOUBLE) group_size, CAST(NULL AS INTEGER) min_group_size, 'INR' unit FROM a CROSS JOIN cutoff c""",
"vw_metric_m22_task_completion": """
WITH a AS (SELECT CAST(t.sprint_id AS VARCHAR) sprint_id, CAST(s.start_date AS DATE) period, t.team_id, COUNT(*) FILTER (WHERE t.status='Done')::DOUBLE done_n, COUNT(*) FILTER (WHERE t.status<>'Cancelled')::DOUBLE planned_n FROM analytics.fact_task_valid t LEFT JOIN warehouse.dim_sprint s USING(sprint_id) GROUP BY 1,2,3)
SELECT 'M22' metric_id, 'Task completion rate' metric_name, period, CAST(NULL AS VARCHAR) department_id, team_id || ' / ' || sprint_id dimension_label, CASE WHEN planned_n >= 5 THEN 100*done_n/NULLIF(planned_n,0) END metric_value, planned_n group_size, 5 min_group_size, 'percent' unit FROM a""",
"vw_metric_m23_on_time_delivery": """
WITH a AS (SELECT CAST(s.start_date AS DATE) period, t.team_id, t.sprint_id, COUNT(*) FILTER (WHERE t.status='Done')::DOUBLE done_n, COUNT(*) FILTER (WHERE t.status='Done' AND t.completed_on_time='Y')::DOUBLE ontime_n, COUNT(*) FILTER (WHERE t.status<>'Cancelled')::DOUBLE planned_n FROM analytics.fact_task_valid t LEFT JOIN warehouse.dim_sprint s USING(sprint_id) GROUP BY 1,2,3)
SELECT 'M23' metric_id, 'On-time delivery rate' metric_name, period, CAST(NULL AS VARCHAR) department_id, team_id || ' / ' || sprint_id dimension_label, CASE WHEN planned_n >= 5 THEN 100*ontime_n/NULLIF(done_n,0) END metric_value, planned_n group_size, 5 min_group_size, 'percent' unit FROM a""",
"vw_metric_m24_velocity": """
WITH a AS (SELECT CAST(s.start_date AS DATE) period, t.team_id, t.sprint_id, SUM(story_points) FILTER (WHERE t.status='Done')::DOUBLE metric_raw_value, COUNT(*) FILTER (WHERE t.status<>'Cancelled')::DOUBLE n FROM analytics.fact_task_valid t LEFT JOIN warehouse.dim_sprint s USING(sprint_id) GROUP BY 1,2,3)
SELECT 'M24' metric_id, 'Velocity' metric_name, period, CAST(NULL AS VARCHAR) department_id, team_id || ' / ' || sprint_id dimension_label, CASE WHEN n >= 5 THEN metric_raw_value END metric_value, n group_size, 5 min_group_size, 'points' unit FROM a""",
"vw_metric_m25_cycle_time": """
WITH a AS (SELECT CAST(s.start_date AS DATE) period, t.team_id, t.sprint_id, AVG(t.cycle_time_days) FILTER (WHERE t.status='Done')::DOUBLE metric_raw_value, COUNT(*) FILTER (WHERE t.status='Done')::DOUBLE n FROM analytics.fact_task_valid t LEFT JOIN warehouse.dim_sprint s USING(sprint_id) GROUP BY 1,2,3)
SELECT 'M25' metric_id, 'Average cycle time' metric_name, period, CAST(NULL AS VARCHAR) department_id, team_id || ' / ' || sprint_id dimension_label, CASE WHEN n >= 5 THEN metric_raw_value END metric_value, n group_size, 5 min_group_size, 'days' unit FROM a""",
"vw_metric_m26_anomaly_flag_rate": """
WITH a AS (SELECT CAST(date_trunc('month',period) AS DATE) period, source_dataset, COUNT(*)::DOUBLE n, COUNT(*) FILTER (WHERE flagged='Y')::DOUBLE flagged_n FROM warehouse.fact_anomaly GROUP BY 1,2)
SELECT 'M26' metric_id, 'Anomaly flag rate' metric_name, period, CAST(NULL AS VARCHAR) department_id, source_dataset dimension_label, 100*flagged_n/NULLIF(n,0) metric_value, n group_size, CAST(NULL AS INTEGER) min_group_size, 'percent' unit FROM a""",
"vw_metric_m27_high_risk_share": """
WITH max_batch AS (SELECT MAX(as_of_date) latest FROM analytics.fact_attrition_risk_valid), a AS (SELECT r.department_id, CAST(m.latest AS DATE) period, COUNT(*)::DOUBLE n, COUNT(*) FILTER (WHERE r.risk_band='High')::DOUBLE high_n FROM analytics.fact_attrition_risk_valid r CROSS JOIN max_batch m WHERE r.as_of_date=m.latest GROUP BY 1,2)
SELECT 'M27' metric_id, 'High-risk share' metric_name, period, department_id, department_id dimension_label, CASE WHEN n >= 10 THEN 100*high_n/NULLIF(n,0) END metric_value, n group_size, 10 min_group_size, 'percent' unit FROM a""",
"vw_metric_m28_forecast_mape": """
WITH f AS (
  SELECT CAST(forecast_month AS DATE) period, department_id, CAST(forecast_value AS DOUBLE) forecast_value
  FROM warehouse.fact_forecast WHERE metric='headcount_end'
), h AS (
  SELECT CAST(month_start_date AS DATE) period, department_id, SUM(headcount_end)::DOUBLE headcount_end
  FROM warehouse.fact_headcount_monthly GROUP BY 1,2
)
SELECT 'M28' metric_id, 'Forecast error (MAPE)' metric_name, f.period, f.department_id, f.department_id dimension_label,
       CASE WHEN h.headcount_end IS NOT NULL AND h.headcount_end<>0 THEN ABS(h.headcount_end-f.forecast_value)/h.headcount_end*100 END metric_value,
       h.headcount_end::DOUBLE group_size, CAST(NULL AS INTEGER) min_group_size, 'percent' unit
FROM f LEFT JOIN h USING(period, department_id)""",
}


def create_metric_views() -> None:
    con = duckdb.connect(str(DB_FILE))
    try:
        # Downstream views depend on each other; rebuilding the schema avoids stale
        # dependencies and makes this stage safe to run again.
        con.execute("DROP SCHEMA IF EXISTS analytics CASCADE")
        con.execute("CREATE SCHEMA IF NOT EXISTS analytics")
        con.execute("CREATE SCHEMA IF NOT EXISTS audit")
        con.execute("""CREATE TABLE IF NOT EXISTS audit.dq_results (
            run_at_utc VARCHAR, check_id VARCHAR, check_name VARCHAR, severity VARCHAR,
            rows_affected BIGINT, status VARCHAR, description VARCHAR, recommended_action VARCHAR, error VARCHAR
        )""")
        # Privacy/quality-controlled model inputs used by all metric definitions.
        con.execute("""
        CREATE OR REPLACE VIEW analytics.fact_payroll_valid AS
        WITH ranked AS (
          SELECT p.*, ROW_NUMBER() OVER (PARTITION BY p.employee_id, p.run_id ORDER BY p.payroll_item_id) AS _rn
          FROM warehouse.fact_payroll p
          JOIN warehouse.dim_employee d ON p.employee_key=d.employee_key
        ) SELECT * EXCLUDE(_rn) FROM ranked WHERE _rn=1
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.fact_attendance_valid AS
        SELECT a.* FROM warehouse.fact_attendance_monthly a
        JOIN warehouse.dim_employee d ON a.employee_key=d.employee_key
        WHERE d.exit_date IS NULL OR CAST(a.period_end_date AS DATE) <= CAST(last_day(d.exit_date) AS DATE)
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.fact_leave_valid AS
        SELECT * FROM warehouse.fact_leave WHERE start_date IS NOT NULL AND end_date IS NOT NULL AND CAST(end_date AS DATE)>=CAST(start_date AS DATE)
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.fact_task_valid AS
        SELECT * FROM warehouse.fact_task
        WHERE (started_date IS NULL OR CAST(created_date AS DATE)<=CAST(started_date AS DATE))
          AND (completed_date IS NULL OR started_date IS NULL OR CAST(completed_date AS DATE)>=CAST(started_date AS DATE))
          AND (status<>'Done' OR completed_date IS NOT NULL)
          AND (started_date IS NOT NULL OR status='To Do')
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.fact_invoice_valid AS
        SELECT * FROM warehouse.fact_invoice WHERE amount_paid<=total_amount AND balance_due>=0
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.fact_expense_valid AS
        SELECT * FROM warehouse.fact_expense WHERE ABS(total_amount-(amount_excl_gst+gst_amount))<=0.01
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.fact_attrition_risk_valid AS
        SELECT r.* FROM warehouse.fact_attrition_risk r
        WHERE CAST(r.as_of_date AS DATE) >= (SELECT MAX(CAST(as_of_date AS DATE)) FROM warehouse.fact_attrition_risk) - INTERVAL 7 DAY
        """)
        for name, query in METRIC_VIEWS.items():
            con.execute(f"CREATE OR REPLACE VIEW analytics.{name} AS {query}")
        view_names = list(METRIC_VIEWS.keys())
        union = " UNION ALL ".join(f"SELECT * FROM analytics.{name}" for name in view_names)
        con.execute(f"CREATE OR REPLACE VIEW analytics.vw_all_metrics AS {union}")
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_metric_catalog AS
        SELECT metric_id, metric_name, business_definition, formula, source_table, grain, time_period,
               owner_team, unit, good_direction, caveat,
               TRY_CAST(REGEXP_EXTRACT(CAST(minimum_group_size AS VARCHAR), '([0-9]+)', 1) AS INTEGER) minimum_group_size
        FROM warehouse.metric_dictionary
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_workforce_mix AS
        WITH latest AS (SELECT CAST(last_day(MAX(CAST(month_start_date AS DATE))) AS DATE) month_end FROM warehouse.fact_headcount_monthly),
        current_employees AS (SELECT * FROM warehouse.dim_employee WHERE is_current='Y' AND (exit_date IS NULL OR CAST(exit_date AS DATE)>(SELECT month_end FROM latest))),
        base AS (
          SELECT 'Work mode' dimension_type, COALESCE(work_mode,'Unknown') dimension_value, COUNT(DISTINCT employee_id)::DOUBLE n
          FROM current_employees GROUP BY 1,2
          UNION ALL
          SELECT 'Work location', COALESCE(work_location,'Unknown'), COUNT(DISTINCT employee_id)::DOUBLE
          FROM current_employees GROUP BY 1,2
          UNION ALL
          SELECT 'Department', COALESCE(department_id,'Unknown'), COUNT(DISTINCT employee_id)::DOUBLE
          FROM current_employees GROUP BY 1,2
        ) SELECT dimension_type, dimension_value, CASE WHEN n>=5 THEN n END employee_count, CASE WHEN n>=5 THEN n END group_size FROM base
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_leave_type_summary AS
        SELECT CAST(date_trunc('month',start_date) AS DATE) period, leave_type_code, status,
               CASE WHEN COUNT(DISTINCT employee_id)>=5 THEN COUNT(*)::DOUBLE END request_count,
               CASE WHEN COUNT(DISTINCT employee_id)>=5 THEN COUNT(DISTINCT employee_id)::DOUBLE END group_size,
               CASE WHEN COUNT(DISTINCT employee_id)>=5 THEN COUNT(*)::DOUBLE END visible_request_count
        FROM analytics.fact_leave_valid GROUP BY 1,2,3
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_budget_vs_actual AS
        WITH p AS (
            SELECT CAST(date_trunc('month', period_end_date) AS DATE) AS period_month,
                   department_id,
                   SUM(employer_cost)::DOUBLE AS actual_cost,
                   COUNT(DISTINCT employee_id)::DOUBLE AS employee_count
            FROM analytics.fact_payroll_valid
            GROUP BY 1, 2
        )
        SELECT p.period_month AS "month", p.department_id,
               CASE WHEN p.employee_count>=5 THEN p.actual_cost END AS actual_cost,
               CASE WHEN p.employee_count>=5 THEN b.budget_payroll_cost::DOUBLE END AS budget_cost,
               CASE WHEN p.employee_count>=5 THEN p.actual_cost-b.budget_payroll_cost END AS variance,
               CASE WHEN p.employee_count>=5 THEN 100*(p.actual_cost-b.budget_payroll_cost)/NULLIF(b.budget_payroll_cost,0) END AS variance_pct,
               CASE WHEN p.employee_count>=5 THEN p.actual_cost END AS visible_actual_cost,
               CASE WHEN p.employee_count>=5 THEN p.employee_count END AS group_size
        FROM p JOIN warehouse.budget_payroll_dept_month b ON p.department_id=b.department_id AND p.period_month=CAST(b.month AS DATE)
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_kpi_target_performance AS
        WITH ar AS (
            SELECT period AS period_month, department_id, metric_value AS attendance_rate
            FROM analytics.vw_metric_m13_attendance_rate
        ),
        ot AS (
            SELECT period AS period_month, department_id, metric_value AS overtime_share_pct
            FROM analytics.vw_metric_m11_overtime_share
        ),
        attrition AS (
            SELECT period AS period_month, department_id, metric_value AS attrition_pct
            FROM analytics.vw_metric_m04_monthly_attrition
        ),
        tc AS (
            SELECT CAST(date_trunc('month', m.period) AS DATE) AS period_month, d.department_id, AVG(m.metric_value) AS task_completion_pct
            FROM analytics.vw_metric_m22_task_completion m
            JOIN warehouse.dim_team d ON split_part(m.dimension_label, ' / ', 1)=d.team_id
            GROUP BY 1, 2
        )
        SELECT CAST(k.month AS DATE) AS "month", k.department_id, k.attendance_rate_target, ar.attendance_rate,
               k.overtime_share_target_pct, ot.overtime_share_pct,
               k.attrition_monthly_target_pct, attrition.attrition_pct,
               k.task_completion_target_pct, tc.task_completion_pct
        FROM warehouse.kpi_targets k
        LEFT JOIN ar ON CAST(k.month AS DATE)=ar.period_month AND k.department_id=ar.department_id
        LEFT JOIN ot ON CAST(k.month AS DATE)=ot.period_month AND k.department_id=ot.department_id
        LEFT JOIN attrition ON CAST(k.month AS DATE)=attrition.period_month AND k.department_id=attrition.department_id
        LEFT JOIN tc ON CAST(k.month AS DATE)=tc.period_month AND k.department_id=tc.department_id
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_finance_monthly AS
        WITH rev AS (SELECT period, SUM(metric_value)::DOUBLE revenue FROM analytics.vw_metric_m16_revenue GROUP BY 1),
        profit AS (SELECT period, metric_value::DOUBLE net_profit FROM analytics.vw_metric_m17_net_profit),
        margin AS (SELECT period, metric_value::DOUBLE operating_margin_pct FROM analytics.vw_metric_m18_operating_margin),
        payroll AS (SELECT period, metric_value::DOUBLE payroll_pct_revenue FROM analytics.vw_metric_m19_payroll_percent_revenue)
        SELECT r.period, r.revenue, p.net_profit, m.operating_margin_pct, py.payroll_pct_revenue
        FROM rev r LEFT JOIN profit p USING(period) LEFT JOIN margin m USING(period) LEFT JOIN payroll py USING(period)
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_invoice_aging AS
        SELECT COALESCE(ageing_bucket_at_cutoff,'Unknown') ageing_bucket, SUM(balance_due)::DOUBLE balance_due,
               COUNT(*)::INTEGER invoice_count
        FROM analytics.fact_invoice_valid WHERE status NOT IN ('DRAFT','CANCELLED') AND balance_due>0
        GROUP BY 1
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_expense_monthly_department AS
        SELECT CAST(date_trunc('month',expense_date) AS DATE) period, department_id,
               SUM(total_amount)::DOUBLE total_expense, COUNT(*)::INTEGER bill_count
        FROM analytics.fact_expense_valid GROUP BY 1,2
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_ai_anomaly_summary AS
        SELECT CAST(date_trunc('month',period) AS DATE) period, source_dataset, COUNT(*)::INTEGER scored_rows,
               COUNT(*) FILTER (WHERE flagged='Y')::INTEGER flagged_rows,
               SUM(COALESCE(money_at_risk,0))::DOUBLE money_at_risk,
               100.0*COUNT(*) FILTER (WHERE flagged='Y')/NULLIF(COUNT(*),0) flag_rate_pct
        FROM warehouse.fact_anomaly GROUP BY 1,2
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_attrition_risk_department AS
        WITH latest AS (SELECT MAX(CAST(as_of_date AS DATE)) d FROM analytics.fact_attrition_risk_valid)
        SELECT r.department_id, CAST(r.as_of_date AS DATE) as_of_date,
               CASE WHEN COUNT(*)>=10 THEN COUNT(*)::INTEGER END employee_count,
               CASE WHEN COUNT(*)>=10 THEN COUNT(*) FILTER (WHERE risk_band='High')::INTEGER END high_risk_count,
               CASE WHEN COUNT(*)>=10 THEN COUNT(*)::INTEGER END group_size,
               CASE WHEN COUNT(*)>=10 THEN 100.0*COUNT(*) FILTER (WHERE risk_band='High')/NULLIF(COUNT(*),0) END high_risk_share_pct
        FROM analytics.fact_attrition_risk_valid r, latest l WHERE CAST(r.as_of_date AS DATE)=l.d GROUP BY 1,2
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_task_summary AS
        SELECT CAST(s.start_date AS DATE) sprint_start, t.sprint_id, t.team_id,
               CASE WHEN COUNT(*) FILTER (WHERE t.status<>'Cancelled')>=5 THEN COUNT(*) FILTER (WHERE t.status<>'Cancelled')::INTEGER END planned_tasks,
               CASE WHEN COUNT(*) FILTER (WHERE t.status<>'Cancelled')>=5 THEN COUNT(*) FILTER (WHERE t.status='Done')::INTEGER END done_tasks,
               CASE WHEN COUNT(*) FILTER (WHERE t.status<>'Cancelled')>=5 THEN COUNT(*) FILTER (WHERE t.status='Blocked')::INTEGER END blocked_tasks,
               CASE WHEN COUNT(*) FILTER (WHERE t.status<>'Cancelled')>=5 THEN SUM(t.story_points) FILTER (WHERE t.status='Done')::DOUBLE END completed_points,
               CASE WHEN COUNT(*) FILTER (WHERE t.status='Done')>=5 THEN AVG(t.cycle_time_days) FILTER (WHERE t.status='Done' AND t.cycle_time_days>=0)::DOUBLE END avg_cycle_days,
               CASE WHEN COUNT(*) FILTER (WHERE t.status<>'Cancelled')>=5 THEN COUNT(*) FILTER (WHERE t.status<>'Cancelled')::INTEGER END group_size,
               CASE WHEN COUNT(*) FILTER (WHERE t.status<>'Cancelled')>=5 THEN 100.0*COUNT(*) FILTER (WHERE t.status='Done')/NULLIF(COUNT(*) FILTER (WHERE t.status<>'Cancelled'),0) END completion_rate_pct,
               CASE WHEN COUNT(*) FILTER (WHERE t.status='Done')>=5 THEN 100.0*COUNT(*) FILTER (WHERE t.status='Done' AND t.completed_on_time='Y')/NULLIF(COUNT(*) FILTER (WHERE t.status='Done'),0) END on_time_rate_pct
        FROM analytics.fact_task_valid t LEFT JOIN warehouse.dim_sprint s USING(sprint_id) GROUP BY 1,2,3
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_dq_results AS SELECT * FROM audit.dq_results
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_lineage AS
        SELECT metric_id, metric_name, source_table, formula, owner_team, grain, unit, caveat FROM analytics.vw_metric_catalog
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_contract_validation AS
        SELECT * FROM audit.contract_validation
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_company_kpis AS
        WITH hc AS (SELECT CAST(month_start_date AS DATE) period, SUM(headcount_end)::DOUBLE headcount, SUM(hires)::DOUBLE hires, SUM(exits)::DOUBLE exits, SUM(headcount_start)::DOUBLE start_hc FROM warehouse.fact_headcount_monthly GROUP BY 1),
        pay AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, SUM(employer_cost)::DOUBLE payroll_cost FROM analytics.fact_payroll_valid GROUP BY 1),
        att AS (SELECT CAST(date_trunc('month',period_end_date) AS DATE) period, (SUM(present_days)+0.5*SUM(half_days_unpaid))::DOUBLE present, SUM(scheduled_days)::DOUBLE scheduled FROM analytics.fact_attendance_valid GROUP BY 1),
        months AS (SELECT period FROM hc UNION SELECT period FROM pay UNION SELECT period FROM att)
        SELECT months.period, hc.headcount, hc.hires, hc.exits, 100*hc.exits/NULLIF(hc.start_hc,0) attrition_pct,
               pay.payroll_cost, att.present/NULLIF(att.scheduled,0) attendance_rate
        FROM months LEFT JOIN hc USING(period) LEFT JOIN pay USING(period) LEFT JOIN att USING(period)
        """)
        con.execute("""
        CREATE OR REPLACE VIEW analytics.vw_location_summary AS
        WITH latest AS (SELECT CAST(last_day(MAX(CAST(month_start_date AS DATE))) AS DATE) as_of_date FROM warehouse.fact_headcount_monthly)
        SELECT COALESCE(l.work_location,'Unknown') work_location, COALESCE(l.state,'Unknown') state,
               COALESCE(l.city_tier,'Unknown') city_tier,
               CASE WHEN COUNT(DISTINCT e.employee_id)>=5 THEN COUNT(DISTINCT e.employee_id)::INTEGER END group_size,
               CASE WHEN COUNT(DISTINCT e.employee_id)>=5 THEN COUNT(DISTINCT e.employee_id)::INTEGER END employee_count
        FROM warehouse.dim_employee e LEFT JOIN warehouse.dim_location l ON e.work_location=l.work_location
        CROSS JOIN latest a
        WHERE e.is_current='Y' AND (e.exit_date IS NULL OR CAST(e.exit_date AS DATE)>a.as_of_date)
        GROUP BY 1,2,3
        """)
    finally:
        con.close()


def main() -> None:
    create_metric_views()
    print(f"Created {len(METRIC_VIEWS)} governed metric views plus supporting dashboard views.")


if __name__ == "__main__":
    create_metric_views()
