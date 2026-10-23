"""Build an evidence-first HTML handover pack and machine-readable summary."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "data" / "pulseiq.duckdb"
REPORTS = ROOT / "reports"


def _money(value) -> str:
    if value is None or pd.isna(value): return "N/A"
    return f"₹{float(value):,.0f}"


def build_reports() -> dict:
    REPORTS.mkdir(exist_ok=True)
    con = duckdb.connect(str(DB_FILE), read_only=True)
    try:
        table_counts = con.execute("SELECT table_name, warehouse_rows AS row_count, raw_rows, count_matches FROM audit.warehouse_row_counts ORDER BY table_name").df()
        row_audit = con.execute("SELECT * FROM audit.table_row_audit ORDER BY table_name").df()
        pk_audit = con.execute("SELECT * FROM audit.primary_key_audit ORDER BY table_name").df()
        fk_audit = con.execute("SELECT * FROM audit.foreign_key_audit ORDER BY child_table, child_column").df()
        dq = con.execute("SELECT check_id,check_name,severity,rows_affected,status,description,recommended_action FROM audit.dq_results ORDER BY check_id").df()
        catalog = con.execute("SELECT metric_id,metric_name,source_table,grain,unit,owner_team,minimum_group_size FROM analytics.vw_metric_catalog ORDER BY metric_id").df()
        latest_hc = con.execute("SELECT period, headcount FROM analytics.vw_company_kpis WHERE headcount IS NOT NULL ORDER BY period DESC LIMIT 1").df()
        latest_finance = con.execute("SELECT * FROM analytics.vw_finance_monthly ORDER BY period DESC LIMIT 1").df()
        latest_pay = con.execute("SELECT period,payroll_cost FROM analytics.vw_company_kpis WHERE payroll_cost IS NOT NULL ORDER BY period DESC LIMIT 1").df()
        contract = pd.read_csv(REPORTS / "contract_validation.csv") if (REPORTS / "contract_validation.csv").exists() else pd.DataFrame()
        manual = pd.read_csv(REPORTS / "manual_metric_checks.csv") if (REPORTS / "manual_metric_checks.csv").exists() else pd.DataFrame()
        clean_counts = {}
        for table in ("dim_employee", "fact_payroll", "fact_attendance_monthly", "fact_leave", "fact_headcount_monthly"):
            clean_file = ROOT / "data" / "clean" / f"{table}.csv"
            reject_file = ROOT / "rejected" / f"{table}_rejected.csv"
            clean_counts[table] = {"clean_rows": int(len(pd.read_csv(clean_file))) if clean_file.exists() else 0, "rejected_rows": int(len(pd.read_csv(reject_file))) if reject_file.exists() and reject_file.stat().st_size else 0}
        summary = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_workbook": "03_PulseIQ_Analytics_Star_Schema_Dataset.xlsx",
            "source_worksheets_loaded": int(len(table_counts)),
            "row_audit_tables_reconciled": int((row_audit["row_conservation_ok"] & row_audit["raw_matches_warehouse"]).sum()) if not row_audit.empty else 0,
            "row_audit_tables_total": int(len(row_audit)),
            "row_audit_failures": int((~(row_audit["row_conservation_ok"] & row_audit["raw_matches_warehouse"])).sum()) if not row_audit.empty else 0,
            "primary_key_tables_enforced": int((pk_audit["status"] == "PASS").sum()) if not pk_audit.empty else 0,
            "primary_key_tables_total": int(len(pk_audit)),
            "foreign_key_relationships_checked": int(len(fk_audit)),
            "foreign_key_relationships_with_orphans": int((fk_audit["status"] == "FAIL").sum()) if not fk_audit.empty else 0,
            "foreign_key_orphan_rows": int(fk_audit.loc[fk_audit["orphan_rows"] > 0, "orphan_rows"].sum()) if not fk_audit.empty else 0,
            "contract_rule_rows": int((~contract["detail"].astype(str).str.startswith("Unexpected column preserved")).sum()) if not contract.empty and "detail" in contract.columns else 0,
            "contract_rule_failures": int((contract["status"] == "FAIL").sum()) if not contract.empty else 0,
            "unexpected_column_warnings": int(contract["detail"].astype(str).str.startswith("Unexpected column preserved").sum()) if not contract.empty and "detail" in contract.columns else 0,
            "partial_contract_coverage_warnings": int(contract["detail"].astype(str).str.startswith("WARN:").sum()) if not contract.empty and "detail" in contract.columns else 0,
            "governed_metrics_defined": int(len(catalog)),
            "dq_checks_run": int(len(dq)),
            "dq_status_counts": {str(k): int(v) for k,v in dq.status.value_counts().items()},
            "contract_columns_checked": int((~contract["detail"].astype(str).str.startswith("Unexpected column preserved")).sum()) if not contract.empty and "detail" in contract.columns else 0,
            "manual_metric_check_rows": int(len(manual)) if not manual.empty else 0,
            "manual_metric_checks_passed": int(manual["passed"].astype(str).str.lower().isin(["true", "1"]).sum()) if not manual.empty and "passed" in manual.columns else 0,
            "manual_metric_check_failures": int((~manual["passed"].astype(str).str.lower().isin(["true", "1"])).sum()) if not manual.empty and "passed" in manual.columns else 0,
            "clean_stage_counts": clean_counts,
            "latest_headcount_period": str(latest_hc.iloc[0]["period"]) if not latest_hc.empty else None,
            "latest_headcount": int(latest_hc.iloc[0]["headcount"]) if not latest_hc.empty and pd.notna(latest_hc.iloc[0]["headcount"]) else None,
            "latest_payroll_period": str(latest_pay.iloc[0]["period"]) if not latest_pay.empty else None,
            "latest_payroll_cost": float(latest_pay.iloc[0]["payroll_cost"]) if not latest_pay.empty and pd.notna(latest_pay.iloc[0]["payroll_cost"]) else None,
            "latest_finance_period": str(latest_finance.iloc[0]["period"]) if not latest_finance.empty else None,
            "latest_revenue": float(latest_finance.iloc[0]["revenue"]) if not latest_finance.empty and pd.notna(latest_finance.iloc[0]["revenue"]) else None,
            "latest_net_profit": float(latest_finance.iloc[0]["net_profit"]) if not latest_finance.empty and pd.notna(latest_finance.iloc[0]["net_profit"]) else None,
        }
        (REPORTS / "pipeline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

        fail_n = int((dq.status == "FAIL").sum()) if not dq.empty else 0
        warn_n = int((dq.status == "WARN").sum()) if not dq.empty else 0
        metric_rows = "".join(f"<tr><td>{r.metric_id}</td><td>{r.metric_name}</td><td>{r.source_table}</td><td>{r.grain}</td><td>{r.unit}</td><td>{r.owner_team}</td></tr>" for r in catalog.itertuples())
        dq_rows = "".join(f"<tr class='{str(r.status).lower()}'><td>{r.check_id}</td><td>{r.check_name}</td><td>{r.severity}</td><td>{r.status}</td><td>{r.rows_affected}</td><td>{r.recommended_action}</td></tr>" for r in dq.itertuples())
        count_rows = "".join(
            f"<tr><td>{r.table_name}</td><td>{r.row_count:,}</td><td>{int(r.raw_rows):,}</td><td>{'PASS' if bool(r.count_matches) else 'FAIL'}</td></tr>"
            for r in table_counts.itertuples()
        )
        latest_hc_text = f"{summary['latest_headcount']:,}" if summary["latest_headcount"] is not None else "N/A"
        latest_pay_text = _money(summary["latest_payroll_cost"])
        rev_text = _money(summary["latest_revenue"])
        profit_text = _money(summary["latest_net_profit"])
        html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PulseIQ Analytics | Project Handover</title>
<style>
:root{{--navy:#14213d;--blue:#2563eb;--teal:#0f766e;--bg:#f4f7fb;--ink:#182230;--muted:#64748b;--line:#dbe3ef}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 Segoe UI,Arial,sans-serif}}header{{background:linear-gradient(110deg,#10223f,#174c75);color:white;padding:38px max(24px,calc((100vw - 1160px)/2))}}header h1{{margin:0 0 8px;font-size:32px}}header p{{max-width:850px;margin:0;color:#e0eaf6}}main{{max-width:1160px;margin:26px auto;padding:0 22px}}section{{background:white;border:1px solid var(--line);border-radius:14px;padding:22px;margin:18px 0;box-shadow:0 3px 18px rgba(15,23,42,.04)}}h2{{font-size:21px;color:var(--navy);margin:0 0 14px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}.card{{padding:18px;border-radius:12px;background:#f7fafc;border:1px solid var(--line)}}.card small{{display:block;color:var(--muted);font-weight:600}}.card strong{{display:block;font-size:24px;color:var(--navy);margin-top:5px}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:9px;border-bottom:1px solid var(--line);vertical-align:top}}th{{background:#f7fafc;color:var(--navy)}}tr.fail td:nth-child(4){{color:#b91c1c;font-weight:700}}tr.warn td:nth-child(4){{color:#b45309;font-weight:700}}tr.pass td:nth-child(4){{color:#0f766e;font-weight:700}}.scroll{{overflow:auto}}.pill{{display:inline-block;padding:4px 8px;background:#e2e8f0;border-radius:30px;font-size:12px;color:#334155}}.note{{color:var(--muted)}}footer{{color:var(--muted);font-size:12px;padding:8px 0 30px}}
</style></head><body><header><h1>PulseIQ Analytics</h1><p>Workforce, payroll, finance and delivery analytics for fictional company Zenith Nova Technologies. This handover was generated from the supplied workbook and local DuckDB pipeline.</p></header><main>
<section><h2>Executive snapshot</h2><div class="cards"><div class="card"><small>Workbook sheets loaded</small><strong>{len(table_counts)}</strong></div><div class="card"><small>Governed metric definitions</small><strong>{len(catalog)} / 28</strong></div><div class="card"><small>Quality checks executed</small><strong>{len(dq)} / 14</strong></div><div class="card"><small>Worksheet row audits</small><strong>{summary['row_audit_tables_reconciled']} / {summary['row_audit_tables_total']}</strong></div><div class="card"><small>Primary-key tables enforced</small><strong>{summary['primary_key_tables_enforced']} / {summary['primary_key_tables_total']}</strong></div><div class="card"><small>Independent metric checks</small><strong>{summary['manual_metric_checks_passed']} / {summary['manual_metric_check_rows']}</strong></div><div class="card"><small>Latest headcount available</small><strong>{latest_hc_text}</strong></div><div class="card"><small>Latest payroll cost period</small><strong>{latest_pay_text}</strong><small>{summary['latest_payroll_period'] or 'No data'}</small></div><div class="card"><small>Latest ledger revenue</small><strong>{rev_text}</strong><small>Latest period: {summary['latest_finance_period'] or 'N/A'}</small></div><div class="card"><small>Latest ledger net profit</small><strong>{profit_text}</strong></div><div class="card"><small>Critical quality failures</small><strong>{fail_n}</strong><small>{warn_n} warning checks with findings</small></div></div><p class="note">Quality findings are surfaced rather than hidden. The workbook is a deliberately fictional training dataset and contains known planted issues.</p></section>
<section><h2>Pipeline architecture</h2><p><span class="pill">Excel workbook</span> -&gt; <span class="pill">raw schema</span> -&gt; <span class="pill">ETL clean / quarantine</span> -&gt; <span class="pill">warehouse schema</span> -&gt; <span class="pill">14 DQ checks</span> -&gt; <span class="pill">28 metric views</span> -&gt; <span class="pill">Streamlit dashboard / API</span></p><p>Raw tables are preserved for auditability. Invalid rows are retained in rejection CSVs with reasons. Business metrics use governed SQL views with group-size suppression.</p></section>
<section><h2>Data quality results</h2><p>Critical check findings: <strong>{fail_n}</strong> · Warning checks with findings: <strong>{warn_n}</strong>. Review every FAIL/WARN before a production release.</p><div class="scroll"><table><thead><tr><th>ID</th><th>Check</th><th>Severity</th><th>Status</th><th>Rows affected</th><th>Suggested action</th></tr></thead><tbody>{dq_rows}</tbody></table></div></section>
<section><h2>Source table row counts</h2><p>{summary['row_audit_tables_reconciled']} of {summary['row_audit_tables_total']} worksheet tables conserve rows and match raw-to-warehouse counts. See <code>reports/table_row_audit.csv</code> for rows in, passed, quarantined, and validation scope.</p><div class="scroll"><table><thead><tr><th>Table</th><th>Warehouse rows</th><th>Raw rows</th><th>Count matches</th></tr></thead><tbody>{count_rows}</tbody></table></div></section>
<section><h2>Warehouse keys and relationship checks</h2><p>Primary-key constraints are enforced for {summary['primary_key_tables_enforced']} of {summary['primary_key_tables_total']} configured tables. {summary['foreign_key_relationships_with_orphans']} relationship checks have orphan findings affecting {summary['foreign_key_orphan_rows']} rows. Seeded orphan records remain visible for review.</p><p>See <code>reports/primary_key_audit.csv</code> and <code>reports/foreign_key_audit.csv</code>.</p></section>
<section><h2>Data contract coverage</h2><p>{summary['contract_rule_rows']} supplied contract-rule rows evaluated; {summary['contract_rule_failures']} have violations, {summary['unexpected_column_warnings']} unexpected-column warnings, and {summary['partial_contract_coverage_warnings']} partial-source-coverage warnings. The source contract catalogue covers four feeds and is not a universal per-column contract for all 33 sheets. See <code>docs/data_contract_notes.md</code> and <code>docs/core_table_contract_notes.md</code>.</p></section>
<section><h2>Governed metric catalog</h2><div class="scroll"><table><thead><tr><th>ID</th><th>Metric</th><th>Source</th><th>Grain</th><th>Unit</th><th>Owner</th></tr></thead><tbody>{metric_rows}</tbody></table></div></section>
<section><h2>Independent metric spot-checks</h2><p>The pipeline recalculates five representative metrics with pandas formulas and compares them with the governed SQL metric views. The detailed row-by-row results are saved in <code>reports/manual_metric_checks.csv</code>.</p><p><strong>{summary['manual_metric_checks_passed']}</strong> values or suppression decisions matched out of <strong>{summary['manual_metric_check_rows']}</strong> check rows. Any mismatch blocks the pipeline before the final report is generated.</p></section>
<section><h2>Operational notes and limitations</h2><ul><li>All 33 worksheets are ingested into the raw schema, including dictionaries, catalogues, and reference sheets.</li><li>The supplied source already contains a star-schema extract; the warehouse schema mirrors business and reference tables, enforces verified primary keys, and records relationship/orphan checks, while staging stores clean/quarantined core rows.</li><li>Metric views suppress values below their documented minimum group size. The risk page only shows department aggregates, not named employees.</li><li>Forecast error is only calculable when a forecast period overlaps an actual headcount period. An empty M28 view means no overlapping actuals in the current fixture, not a zero error.</li><li>This build is a local release candidate. External production deployment, private GitHub access, and programme-site submission still require the user's accounts and approval.</li></ul></section>
<footer>Generated {summary['generated_at_utc']} | Local report: reports/board_pack.html | Data source: {summary['source_workbook']}</footer></main></body></html>'''
        (REPORTS / "board_pack.html").write_text(html, encoding="utf-8")
        return summary
    finally:
        con.close()


def main() -> None:
    summary = build_reports()
    print(json.dumps(summary, indent=2))
    print(f"Board pack: {REPORTS / 'board_pack.html'}")


if __name__ == "__main__":
    main()
