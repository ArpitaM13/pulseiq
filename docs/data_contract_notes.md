# Data Contract Notes

The supplied workbook defines **42 column-level contract rows across 4 feeds**. The rules below are generated directly from `data_contracts`; the validator adds row-level reasons for violations and preserves the original raw data.

## fact_anomaly

| Column | Declared type | Nullable | Allowed values / rule | Description |
|---|---|---|---|---|
| result_id | string | no | unique, format AN-nnnn | Row id |
| source_dataset | string | no | attendance_monthly_features \| payroll_monthly_features | Which dataset was scored |
| record_id | string | no | exists in source dataset | Scored record id |
| employee_id | string | no | exists in dim_employee | Employee |
| period | date | no | month end or start date | Period of the record |
| anomaly_score | decimal(4,3) | no | 0 to 1, higher is more unusual | Normalised score |
| flagged | char(1) | no | Y or N | Whether the threshold was crossed |
| reason_code | string | no | one of the published codes | Machine reason |
| reason_text | string | no | plain English | Reason for business users |
| money_at_risk | decimal(14,2) | yes | blank for attendance rows | Estimated money exposure for payroll rows |
| model_version | string | no | semantic version text | Model that produced it |
| scored_at | timestamp | no | UTC | When scored |

## fact_attrition_risk

| Column | Declared type | Nullable | Allowed values / rule | Description |
|---|---|---|---|---|
| prediction_id | string | no | unique AR-nnnn | Row id |
| employee_id | string | no | exists in dim_employee and active | Employee |
| department_id | string | no | exists in dim_department | Department at as-of date |
| as_of_date | date | no | same for the whole batch | Prediction date |
| risk_score_12m | decimal(4,3) | no | 0 to 1 | Probability of leaving within 12 months |
| risk_band | string | no | Low \| Medium \| High | Band: High = top 10%, Medium = next 20% |
| top_reason_1..3 | string | yes | plain English | Main drivers |
| model_version | string | no | text | Model |

## fact_forecast

| Column | Declared type | Nullable | Allowed values / rule | Description |
|---|---|---|---|---|
| forecast_id | string | no | unique FC-nnnn | Row id |
| metric | string | no | headcount_end \| attrition_rate_monthly_pct | Forecast metric |
| department_id | string | no | dept id or ALL | Scope |
| forecast_month | date | no | first day of month | Forecast month |
| forecast_value | decimal | no | >= 0 | Point forecast |
| lower_80 | decimal | no | <= forecast_value | 80% lower bound |
| upper_80 | decimal | no | >= forecast_value | 80% upper bound |
| method | string | no | text | Method |
| trained_through | string | no | YYYY-MM | Last actual month used |

## fact_task

| Column | Declared type | Nullable | Allowed values / rule | Description |
|---|---|---|---|---|
| task_id | string | no | unique TASK-nnnnn | Row id |
| team_id | string | no | exists in dim_team | Team |
| sprint_id | string | no | exists in dim_sprint | Sprint |
| assignee_employee_id | string | no | exists in dim_employee | Assignee |
| task_type | string | no | Feature \| Bug \| Chore \| Spike | Type |
| priority | string | no | P1..P4 | Priority |
| story_points | int | no | 1,2,3,5,8,13 | Effort |
| created_date | date | no | <= started_date | Created |
| started_date | date | yes | blank only when To Do | Started |
| due_date | date | no | sprint end date | Due |
| completed_date | date | yes | required when status = Done; >= started_date | Completed |
| status | string | no | Done \| In Progress \| Blocked \| To Do \| Cancelled | Status |
| reopened_count | int | no | >= 0 | Times reopened |

## Unexpected columns: warn and preserve

The ingestion pipeline keeps all source columns. If a governed feed contains fields not in its supplied contract, the report emits a `WARN` row and leaves the field in raw/warehouse storage rather than silently dropping it. Review schema changes with the source owner before adding fields to the formal contract.

## Enforcement scope

The source workbook only supplies explicit column contracts for `fact_anomaly`, `fact_attrition_risk`, `fact_forecast`, and `fact_task`. The other 29 worksheets are still loaded, counted, represented in the warehouse, and covered by the applicable ETL/quality/metric rules, but they do not have column-by-column rules in the supplied `data_contracts` sheet. The project therefore does not claim universal per-column contract validation for all 33 worksheets.

## Quarantine and traceability

Contract-failing rows are written to `rejected/<table>_contract_rejected.csv` with `_contract_reject_reason`. The raw and warehouse source copy is not changed. `reports/contract_validation.csv` contains one result per contract rule/column plus warnings for additional columns. `reports/table_row_audit.csv` distinguishes ETL-validated, contract-validated, and pass-through tables and records `rows_in`, `rows_passed`, and `rows_quarantined`.

## Validation notes and deliberate limitations

- Numeric ranges, enumerations, identifier patterns, integer values, date parsing, month-start/month-end dates, forecast interval ordering, and selected cross-column/date rules are checked where the contract provides them.
- The contract says anomaly `record_id` must exist in the scoring source. The workbook includes payroll item IDs and validates IDs from the supplied payroll feature feed; the separate attendance feature extract is not supplied as a worksheet, so those AF feature IDs cannot be independently reconciled to that absent source file. The `record_id` contract result is therefore a `WARN` for partial coverage rather than silently reporting the whole column as fully validated.
- The source is training data with planted errors. Failures are recorded; values are not silently swapped or rewritten to make checks pass.
