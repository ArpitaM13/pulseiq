import pandas as pd
from src.etl import TABLES, transform


def test_headcount_composite_key_does_not_reject_repeated_month_key():
    frame = pd.DataFrame({
        "date_key": [20200131, 20200131],
        "month_start_date": ["2020-01-01", "2020-01-01"],
        "department_id": ["D01", "D02"],
        "headcount_start": [10, 12],
        "hires": [1, 0],
        "exits": [0, 1],
        "headcount_end": [11, 11],
    })
    clean, rejected, counts = transform("fact_headcount_monthly", frame, TABLES["fact_headcount_monthly"])
    assert len(clean) == 2
    assert rejected.empty
    assert counts["rows_in"] == counts["rows_out"] + counts["rejected"]


def test_swapped_leave_dates_are_quarantined_with_specific_reason():
    frame = pd.DataFrame({
        "leave_request_id": ["LR-TEST"],
        "start_date": ["2026-02-20"],
        "end_date": ["2026-02-19"],
        "days": [2],
    })
    clean, rejected, _ = transform("fact_leave", frame, TABLES["fact_leave"])
    assert clean.empty
    assert len(rejected) == 1
    assert "start_date is after end_date" in rejected.iloc[0]["_reject_reason"]


def test_open_ended_employee_valid_to_sentinel_is_not_quarantined():
    frame = pd.DataFrame({
        "employee_key": [100001],
        "hire_date": ["2020-01-01"],
        "exit_date": [None],
        "valid_from": ["2020-01-01"],
        "valid_to": ["9999-12-31"],
    })
    clean, rejected, _ = transform("dim_employee", frame, TABLES["dim_employee"])
    assert len(clean) == 1
    assert rejected.empty
    assert pd.isna(clean.iloc[0]["valid_to"])


def test_exact_duplicate_is_quarantined_and_reconciled():
    row = {
        "date_key": 20200131,
        "month_start_date": "2020-01-01",
        "department_id": "D01",
        "headcount_start": 10,
        "hires": 1,
        "exits": 0,
        "headcount_end": 11,
    }
    frame = pd.DataFrame([row, row])
    clean, rejected, counts = transform("fact_headcount_monthly", frame, TABLES["fact_headcount_monthly"])
    assert len(clean) == 1
    assert len(rejected) == 1
    assert "Exact duplicate" in rejected.iloc[0]["_reject_reason"]
    assert counts["rows_in"] == counts["rows_out"] + counts["rejected"]
