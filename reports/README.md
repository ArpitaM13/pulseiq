# Generated pipeline reports

This folder contains the destination for reproducible reports created by `python run_pipeline.py`. The DuckDB-backed pipeline was not executed in the packaging environment, so the package does not include fabricated DQ results, a fake database, or a sample board pack. Run the full pipeline locally to generate `dq_results.csv`, `dq_report.md`, `contract_validation.csv`, `manual_metric_checks.csv`, `pipeline_summary.json`, and `board_pack.html`.
