# Project Walkthrough (plain-language version)

Use this file to understand the project before presenting it. Rewrite the explanation in your own words and do not claim a result you have not run or checked.

## What problem does it solve?

The workbook contains people, payroll, attendance, leave, finance, task-board and AI-signal data. If every chart calculates totals differently, managers could get conflicting answers. PulseIQ keeps the source data, checks it, defines official metrics once and uses those definitions in its dashboards and API.

## What happens when I run the pipeline?

1. All workbook sheets are copied into DuckDB's `raw` schema. That is the untouched reference layer.
2. The Phase-1 ETL standardizes five core tables and sends invalid rows to CSV quarantine files. Each reject has a reason; source dates are not automatically swapped.
3. A warehouse copy is built and the clean/rejected files are loaded into `staging`.
4. The contract gate checks the contract entries provided for anomaly results, attrition risk, forecast and task-board feeds.
5. Fourteen data-quality checks are run against the source tables. They deliberately surface the known training issues.
6. Twenty-eight metric views are created from documented formulas. A dashboard and API read those governed views.
7. The pipeline writes row-count summaries, a DQ report, a known-issue review file and a browser-readable board pack.

## Why is `employee_key` important?

A person can appear in more than one row in the employee dimension because the dataset tracks history. `employee_id` identifies the person. `employee_key` identifies the employee version that was valid for a particular period. Joining payroll or attendance using the version key helps preserve historical department assignments.

## Why are two leave rows rejected?

The supplied fixture has `LR-000025` and `LR-002286` with `start_date` later than `end_date`. The ETL keeps them in quarantine and writes the issue as a reason. It does not guess which date the source owner intended.

## Why might a quality check fail?

The workbook documents 11 known seeded issues, such as duplicate payroll rows, orphan employee references, mismatched payroll/ledger totals, invalid invoice/expense arithmetic, task dates, swapped leave dates, stale attrition predictions and overlapping employee history. The gatekeeper is supposed to expose these so the analyst can investigate them.

## How do I know whether a dashboard number is trusted?

I should be able to name its metric ID, explain the formula/grain, identify its source table, state its caveat and confirm that the quality report has been reviewed. Values below minimum group size are suppressed instead of shown as small groups.

## Five-minute demo order

1. Show the workbook load summary and explain that the raw layer is retained.
2. Run `python run_pipeline.py` and point out the clean/reject counts.
3. Open `reports/dq_report.md` and explain one critical issue and one warning from the fictional data.
4. Open the Streamlit overview, then one people page, one finance page and the data-quality page.
5. Open the self-service KPI explorer and show the definition/formula. Finish with `/docs` from the read-only API and the HTML board pack.

## Short demo script to personalize

"I built PulseIQ Analytics using a supplied fictional workbook. I started by loading every worksheet into DuckDB so the raw source is preserved. I then created an ETL step for the core workforce tables and quarantined rows that fail rules instead of silently editing them. I added the documented quality checks and put the 28 metric definitions in a shared SQL layer. The Streamlit pages and the read-only API use those views, so the same metric definition is reused across reports. I also added group-size suppression for sensitive workforce metrics. Before I would call this production-ready, I would review the remaining critical quality findings and complete the deployment/security checklist."
