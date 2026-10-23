# Applying the refreshed Tasks 1, 2, 4 and 5 update (Windows)

This update replaces project code, tests, and documentation only. It does **not** contain or overwrite `.venv`, `data/pulseiq.duckdb`, the original workbook, or runtime evidence in `logs/`, `reports/`, `rejected/`, and `data/clean/`.

1. Download the patch ZIP supplied with this project update and save it in Downloads.
2. Open PowerShell at your existing project root, the folder that contains `app.py`, `run_pipeline.py`, `src/`, and `.venv/`.
3. Extract the patch over that folder (the ZIP contains relative paths, not an extra enclosing folder):

   ```powershell
   Expand-Archive -Path "$HOME\Downloads\PulseIQ-Tasks-1-2-4-5-Patch.zip" -DestinationPath "$PWD" -Force
   ```

4. Check syntax (this does not need a built database):

   ```powershell
   .\.venv\Scripts\python.exe -m compileall -q .
   ```

5. Run the full local pipeline first. It builds the audit tables that the integration tests inspect:

   ```powershell
   .\.venv\Scripts\python.exe .\run_pipeline.py
   ```

6. Run the tests after the pipeline has succeeded:

   ```powershell
   .\.venv\Scripts\python.exe -m pytest -q
   ```

7. Review `reports/table_row_audit.csv`, `reports/contract_validation.csv`, `reports/foreign_key_audit.csv`, `reports/dq_results.csv`, and `reports/manual_metric_checks.csv`. Seeded FAIL/WARN findings are expected and must be explained, not edited away.
8. Restart the dashboard after a successful pipeline run. In the terminal running Streamlit, press Ctrl+C, then launch `run_dashboard.bat` and open the local URL it prints (normally `http://localhost:8501`).

The Python syntax and source-workbook tests are verified when this package is assembled. Database integration tests require DuckDB to be installed in your local virtual environment and should be confirmed by running the pipeline on your computer.
