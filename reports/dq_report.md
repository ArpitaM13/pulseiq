# Data quality report

Run time (UTC): 2026-10-23T12:46:10.308102+00:00

| Check | Severity | Status | Rows affected |
|---|---|---:|---:|
| DQ-C01 - Payroll equals ledger | Critical | **FAIL** | 5 |
| DQ-C02 - Ledger balanced | Critical | **PASS** | 0 |
| DQ-C03 - Unique payroll rows | Critical | **FAIL** | 2 |
| DQ-C04 - No orphan employees | Critical | **FAIL** | 2 |
| DQ-C05 - No attendance after exit | Warning | **WARN** | 4 |
| DQ-C06 - Unpaid leave deducted | Warning | **WARN** | 1 |
| DQ-C07 - Invoice arithmetic | Warning | **WARN** | 1 |
| DQ-C08 - Expense arithmetic | Warning | **WARN** | 1 |
| DQ-C09 - Task dates sensible | Warning | **WARN** | 20 |
| DQ-C10 - Leave dates sensible | Warning | **WARN** | 2 |
| DQ-C11 - AI feeds are fresh | Warning | **WARN** | 5 |
| DQ-C12 - Dimension history does not overlap | Critical | **FAIL** | 1 |
| DQ-C13 - Pipeline freshness | Critical | **PASS** | 0 |
| DQ-C14 - Minimum group size | Critical | **PASS** | 0 |

## Interpretation

A FAIL on a Critical check should block promotion of affected data into a production release. WARN means the check found a quality issue that should be reviewed. The supplied workbook intentionally contains known issues; failures are evidence that the gatekeeper detects them, not proof the source is production-clean.

## Recommended handling

Raw tables remain unchanged for auditability. The analytics layer excludes selected invalid records from the affected metric calculations; it does not overwrite or silently repair the raw source.