# Warehouse keys, grains, joins, and reconciliation

The warehouse is rebuilt from `raw` on each run. Raw workbook tables are not updated by transformations. Verified single/composite primary keys are applied to the warehouse copies; source relationship checks are recorded as an audit rather than adding foreign-key constraints that would block planted orphan rows from being retained.

## Key and grain register

| Table | Primary key | Grain |
|---|---|---|
| `dim_date` | `date_key` | One calendar date |
| `dim_employee` | `employee_key` | One employee version (SCD Type 2) |
| `dim_department` | `department_id` | One department |
| `dim_role` | `role_id` | One role definition |
| `dim_location` | `work_location` | One location lookup value |
| `dim_leave_type` | `leave_type_code` | One leave type |
| `dim_account` | `account_code` | One chart-of-accounts entry |
| `dim_client` | `client_id` | One client |
| `dim_vendor` | `vendor_id` | One vendor |
| `dim_team` | `team_id` | One team |
| `dim_sprint` | `sprint_id` | One sprint |
| `fact_payroll` | `payroll_item_id` | One payroll line |
| `fact_attendance_monthly` | `attendance_fact_id` | One monthly employee attendance row |
| `fact_leave` | `leave_request_id` | One leave request |
| `fact_headcount_monthly` | `date_key`, `department_id` | One department at one month-end |
| `fact_ledger` | `line_id` | One ledger line |
| `fact_invoice` | `invoice_id` | One invoice |
| `fact_invoice_payment` | `payment_id` | One payment allocation |
| `fact_expense` | `expense_id` | One expense row |
| `fact_task` | `task_id` | One task |
| `fact_anomaly` | `result_id` | One anomaly result |
| `fact_attrition_risk` | `prediction_id` | One risk prediction row |
| `fact_forecast` | `forecast_id` | One forecast row |
| `budget_payroll_dept_month` | `month`, `department_id` | One payroll budget per department-month |
| `kpi_targets` | `month`, `department_id` | One target bundle per department-month |
| `reference_summary_dept_month` | `month`, `department_id` | One reference summary per department-month |
| `reconciliation_answer_key` | `month` | One company reconciliation per month |
| `dq_known_issues` | `issue_id` | One planted issue definition |
| `dq_checks_catalog` | `check_id` | One check definition |
| `metric_dictionary` | `metric_id` | One metric definition |
| `data_contracts` | `feed`, `column_name` | One contract per feed column |

## Join policy

- Payroll and attendance join to employee history by **`employee_key`**, not `employee_id`; the ID alone repeats across SCD versions.
- Payroll/attendance use department and date dimensions; leave also links to leave type and start/end date keys.
- Ledger lines link to accounts/date and optionally cost-centre departments.
- Invoices link to clients and invoice dates; payments link to invoices and payment dates.
- Expenses link to vendors, departments, accounts, and expense dates.
- Tasks link to teams/sprints. The source task feed has only `assignee_employee_id`, so that relationship is audited by employee ID across employee history versions.
- Forecast rows with `department_id='ALL'` are company-level aggregates, not orphan department keys.

## Source anomalies and audit evidence

`reports/primary_key_audit.csv` records which primary keys are configured and enforced. `reports/warehouse_row_counts.csv` verifies row counts before and after raw-to-warehouse copy. `reports/foreign_key_audit.csv` gives relationship-level orphan counts. These checks are intentionally separate from constraints so raw defects remain inspectable.

The known payroll orphans `PI-X0003` and `PI-X0004` use `employee_key=-1` and employee IDs absent from `dim_employee`; DQ-C04 flags both and the validated payroll metrics exclude unmatched employee-key rows. Do not delete or rewrite these records in the raw layer.

`reports/table_row_audit.csv` reconciles `rows_in = rows_passed + rows_quarantined` for all 33 sheets. Five core tables use the ETL outputs; four feeds use the supplied contract validation; uncontracted sheets are visibly labelled `PASS_THROUGH` because the source workbook does not define a contract for every worksheet.
