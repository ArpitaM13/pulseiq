# Core-table contract notes: three-table evidence

This note records the column promises for three tables requested by the Phase 1 Task 1 evidence checklist. Column types, examples, descriptions and observed null counts are taken from the workbook `data_dictionary` and actual source sheet. Where the supplied workbook does not declare a formal closed enumeration or nullable rule, the note says so rather than inventing a contract. The separate `data_contracts` sheet formally defines 42 column-level rules for four other feeds; it does not define a formal rule for every column in these three tables.

## `dim_employee`

- **Key and grain:** One row per employee history version. `employee_key` is the unique surrogate primary key; `employee_id` repeats across SCD history versions.
- **Type/validity:** Dates must be parseable. If both dates exist, `hire_date` must not follow `exit_date`; `valid_from` must not follow `valid_to`. `9999-12-31` in `valid_to` is the source open-ended sentinel and becomes a null end date in the clean stage.
- **Allowed values:** Use categorical values described in the data dictionary (for example gender lists Male/Female/Other where stated). For columns whose description does not enumerate a closed set, do not assume the observed sample is a complete enumeration.
- **Join rule:** Facts that store `employee_key` must join on that version key, not only `employee_id`, so historical department/role attribution remains correct.

| Column | Data dictionary type | Observed blank allowed? | Observed nulls | Example value | Dictionary description / validation promise |
|---|---|---|---:|---|---|
| `employee_key` | integer | No (none observed) | 0/1606 (0.0%) | `100000` | Surrogate key of one version of the employee in dim_employee (changes when department, role or manager changes). |
| `employee_id` | text | No (none observed) | 0/1606 (0.0%) | `EMP-0001` | Unique employee code (EMP-0001 ...). Same code in every table and every workbook. |
| `full_name` | text | No (none observed) | 0/1606 (0.0%) | `Ganesh Murthy` | First and last name (fictional). |
| `gender` | text | No (none observed) | 0/1606 (0.0%) | `Male` | Self-declared gender: Male, Female or Other. Use only for fairness testing, never as a model input. |
| `date_of_birth` | date | No (none observed) | 0/1606 (0.0%) | `1989-10-08` | Date of birth (fictional). |
| `hire_date` | date | No (none observed) | 0/1606 (0.0%) | `2012-01-19` | Date the employee joined. |
| `exit_date` | date | Yes | 1036/1606 (64.5%) | `2020-01-24` | Last working day; blank for active employees. |
| `employment_status` | text | No (none observed) | 0/1606 (0.0%) | `Resigned` | Active, Resigned, Terminated or Contract Ended. |
| `employment_type` | text | No (none observed) | 0/1606 (0.0%) | `Permanent` | Permanent or Fixed-Term Contract. Contract staff have no PF/ESI. |
| `department_id` | text | No (none observed) | 0/1606 (0.0%) | `D01` | Department code (D00 Executive ... D10 Legal & Compliance). |
| `role_id` | text | No (none observed) | 0/1606 (0.0%) | `R002` | Job role code from the roles table. |
| `role_title` | text | No (none observed) | 0/1606 (0.0%) | `Associate Software Engineer` | Role title. |
| `job_level` | integer | No (none observed) | 0/1606 (0.0%) | `1` | Level 1 to 7 (1 Associate ... 6 Head, 7 CEO). |
| `manager_id` | text | Yes | 1/1606 (0.1%) | `EMP-0051` | Employee id of the reporting manager at that time. |
| `work_location` | text | No (none observed) | 0/1606 (0.0%) | `Pune` | City of the office the employee is attached to. |
| `work_mode` | text | No (none observed) | 0/1606 (0.0%) | `Hybrid` | Onsite, Hybrid or Remote. |
| `highest_education` | text | No (none observed) | 0/1606 (0.0%) | `B.E. Computer Science` | Highest qualification (may be blank). |
| `valid_from` | date | No (none observed) | 0/1606 (0.0%) | `2012-01-19` | Date this version of the employee starts. |
| `valid_to` | date | No (none observed) | 0/1606 (0.0%) | `2012-05-12` | Date this version ends (9999-12-31 if current). |
| `is_current` | text | No (none observed) | 0/1606 (0.0%) | `N` | Y for the latest version of the employee. |
| `change_reason` | text | No (none observed) | 0/1606 (0.0%) | `Joining` | Why the assignment changed: Joining, Promotion, Transfer, Manager Change or Manager Exit / Reassignment. |

**Nullability interpretation:** “No (none observed)” describes only this workbook snapshot; it is not proof that a future feed may never contain blanks. A nullable column must still follow its business rule if one is stated.

## `fact_payroll`

- **Key and grain:** `payroll_item_id` is unique per payroll line. Payroll reconciliation additionally tests one logical row per `employee_id` + `run_id`; seeded duplicate pairs remain in raw and are flagged by DQ-C03.
- **Type/validity:** Date fields must parse. `monthly_fixed_gross`, `earned_fixed_pay`, `overtime_pay`, `variable_pay`, `gross_pay`, `net_pay`, and `employer_cost` must be numeric and non-negative in the core ETL.
- **Allowed values:** Identifier formats and descriptive categorical values follow the data dictionary descriptions; a closed enumeration is enforced only where the source describes a finite allowed set.
- **Join rule:** Use `employee_key` to resolve the effective-dated employee version. The two source rows with missing employee references are preserved and identified by DQ-C04 / the relationship audit.

| Column | Data dictionary type | Observed blank allowed? | Observed nulls | Example value | Dictionary description / validation promise |
|---|---|---|---:|---|---|
| `payroll_item_id` | text | No (none observed) | 0/7344 (0.0%) | `PI-000001` | Unique id of one employee-month pay calculation. |
| `run_id` | text | No (none observed) | 0/7344 (0.0%) | `PR-2025-04` | Payroll run id (PR-YYYY-MM). |
| `employee_id` | text | No (none observed) | 0/7344 (0.0%) | `EMP-0002` | Unique employee code (EMP-0001 ...). Same code in every table and every workbook. |
| `date_key` | integer | No (none observed) | 0/7344 (0.0%) | `20250430` | Date as number YYYYMMDD. |
| `employee_key` | integer | No (none observed) | 0/7344 (0.0%) | `100009` | Surrogate key of one version of the employee in dim_employee (changes when department, role or manager changes). |
| `period_end_date` | date | No (none observed) | 0/7344 (0.0%) | `2025-04-30` | Last day of the month the row covers. |
| `department_id` | text | No (none observed) | 0/7344 (0.0%) | `D08` | Department code (D00 Executive ... D10 Legal & Compliance). |
| `role_id` | text | No (none observed) | 0/7344 (0.0%) | `R047` | Job role code from the roles table. |
| `payable_days` | decimal | No (none observed) | 0/7344 (0.0%) | `30` | Days paid = days employed minus loss-of-pay days. |
| `lop_days` | decimal | No (none observed) | 0/7344 (0.0%) | `0` | Loss-of-pay days (unpaid absence, unpaid leave, half day = 0.5). |
| `overtime_hours_paid` | decimal | No (none observed) | 0/7344 (0.0%) | `0` | Overtime hours paid (capped at 50). |
| `variable_pay_type` | text | Yes | 6192/7344 (84.3%) | `Performance Bonus` | Performance Bonus, Sales Incentive, Festival Bonus or Spot Award. |
| `monthly_fixed_gross` | decimal | No (none observed) | 0/7344 (0.0%) | `144460` | Full-month fixed gross entitlement (INR). |
| `basic` | decimal | No (none observed) | 0/7344 (0.0%) | `57784` | Basic salary earned in the month. |
| `hra` | decimal | No (none observed) | 0/7344 (0.0%) | `28892` | House rent allowance earned. |
| `conveyance` | decimal | No (none observed) | 0/7344 (0.0%) | `1600` | Conveyance allowance earned. |
| `medical` | decimal | No (none observed) | 0/7344 (0.0%) | `1250` | Medical allowance earned. |
| `special_allowance` | decimal | No (none observed) | 0/7344 (0.0%) | `54934` | Special allowance earned (balancing component). |
| `earned_fixed_pay` | decimal | No (none observed) | 0/7344 (0.0%) | `144460` | Sum of fixed components after loss-of-pay proration. |
| `overtime_pay` | decimal | No (none observed) | 0/7344 (0.0%) | `0` | Overtime pay (2x hourly rate). |
| `variable_pay` | decimal | No (none observed) | 0/7344 (0.0%) | `34670.4` | Bonus, incentive or award paid in the month. |
| `gross_pay` | decimal | No (none observed) | 0/7344 (0.0%) | `179130` | Earned fixed pay + overtime + variable pay. |
| `pf_employee` | decimal | No (none observed) | 0/7344 (0.0%) | `1800` | Employee provident fund deduction. |
| `esi_employee` | decimal | No (none observed) | 0/7344 (0.0%) | `0` | Employee ESI deduction. |
| `professional_tax` | decimal | No (none observed) | 0/7344 (0.0%) | `200` | Professional tax deduction. |
| `tds` | decimal | No (none observed) | 0/7344 (0.0%) | `18625.8` | Income tax deducted at source. |
| `other_deductions` | decimal | No (none observed) | 0/7344 (0.0%) | `0` | Other deductions (loan recovery). |
| `total_deductions` | decimal | No (none observed) | 0/7344 (0.0%) | `20625.8` | Sum of all employee deductions. |
| `net_pay` | decimal | No (none observed) | 0/7344 (0.0%) | `158505` | Take-home pay = gross pay minus total deductions. |
| `pf_employer` | decimal | No (none observed) | 0/7344 (0.0%) | `1800` | Employer provident fund contribution. |
| `esi_employer` | decimal | No (none observed) | 0/7344 (0.0%) | `0` | Employer ESI contribution. |
| `employer_cost` | decimal | No (none observed) | 0/7344 (0.0%) | `180930` | Full cost to company = gross pay + employer PF + employer ESI. |
| `headcount_flag` | integer | No (none observed) | 0/7344 (0.0%) | `1` | Always 1: lets you SUM to count employees. |

**Nullability interpretation:** “No (none observed)” describes only this workbook snapshot; it is not proof that a future feed may never contain blanks. A nullable column must still follow its business rule if one is stated.

## `fact_attendance_monthly`

- **Key and grain:** `attendance_fact_id` is unique per employee-month attendance fact.
- **Type/validity:** Date fields must parse. `scheduled_days`, `present_days`, `late_arrivals`, and `overtime_hours` must be numeric and non-negative. `present_days` must not exceed `scheduled_days`.
- **Allowed values:** Categorical meanings are described in the workbook data dictionary. Numeric day/hour/count fields are non-negative; attendance rates are derived downstream rather than overwriting source fields.
- **Join rule:** Use `employee_key` for the historical employee version. DQ-C05 separately flags attendance after the employee exit month; the source records are not silently removed from raw.

| Column | Data dictionary type | Observed blank allowed? | Observed nulls | Example value | Dictionary description / validation promise |
|---|---|---|---:|---|---|
| `attendance_fact_id` | text | No (none observed) | 0/7343 (0.0%) | `FA-00001` | Row id of the monthly attendance fact. |
| `employee_id` | text | No (none observed) | 0/7343 (0.0%) | `EMP-0002` | Unique employee code (EMP-0001 ...). Same code in every table and every workbook. |
| `date_key` | integer | No (none observed) | 0/7343 (0.0%) | `20250430` | Date as number YYYYMMDD. |
| `employee_key` | integer | No (none observed) | 0/7343 (0.0%) | `100009` | Surrogate key of one version of the employee in dim_employee (changes when department, role or manager changes). |
| `department_id` | text | No (none observed) | 0/7343 (0.0%) | `D08` | Department code (D00 Executive ... D10 Legal & Compliance). |
| `scheduled_days` | decimal | No (none observed) | 0/7343 (0.0%) | `20` | Working days the employee was scheduled in the month. |
| `present_days` | decimal | No (none observed) | 0/7343 (0.0%) | `20` | Days present (office or work from home). |
| `wfh_days` | decimal | No (none observed) | 0/7343 (0.0%) | `18` | Days worked from home. |
| `half_days_unpaid` | decimal | No (none observed) | 0/7343 (0.0%) | `0` | Half days without pay. |
| `paid_leave_days` | decimal | No (none observed) | 0/7343 (0.0%) | `0` | Days on paid leave. |
| `unpaid_absence_days` | decimal | No (none observed) | 0/7343 (0.0%) | `0` | Unpaid absence and unpaid leave days. |
| `late_arrivals` | decimal | No (none observed) | 0/7343 (0.0%) | `1` | Late check-ins in the month. |
| `avg_hours_worked` | decimal | No (none observed) | 0/7343 (0.0%) | `8.5` | Average working hours per recorded day. |
| `overtime_hours` | decimal | No (none observed) | 0/7343 (0.0%) | `0` | Overtime hours recorded (only overtime-eligible roles). |
| `attendance_rate` | decimal | No (none observed) | 0/7343 (0.0%) | `1` | (Present days + 0.5 x half days) / scheduled days. |
| `period_end_date` | date | No (none observed) | 0/7343 (0.0%) | `2025-04-30` | Last day of the month the row covers. |

**Nullability interpretation:** “No (none observed)” describes only this workbook snapshot; it is not proof that a future feed may never contain blanks. A nullable column must still follow its business rule if one is stated.

