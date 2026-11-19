
"""Shared helpers for the Streamlit UI.
Pages query governed analytics views only.
"""

from __future__ import annotations

from pathlib import Path
from contextlib import contextmanager
import os
import subprocess
import sys
import threading
import time

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# 1. Project paths and database
# --------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
DB_FILE = ROOT / "data" / "pulseiq.duckdb"


# --------------------------------------------------
# 2. Database readiness and startup protection
# --------------------------------------------------

@st.cache_resource(show_spinner=False)
def _get_database_thread_lock():
    """Share one initialization lock across Streamlit sessions."""
    return threading.Lock()


@contextmanager
def _database_process_lock():
    """Prevent multiple processes from rebuilding DuckDB together."""

    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_path = DB_FILE.parent / ".pulseiq_pipeline.lock"

    with lock_path.open("a+b") as handle:

        if os.name == "nt":
            import msvcrt

            handle.seek(0, os.SEEK_END)

            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()

            handle.seek(0)

            deadline = time.monotonic() + 900

            while True:
                try:
                    msvcrt.locking(
                        handle.fileno(),
                        msvcrt.LK_NBLCK,
                        1,
                    )
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError(
                            "Timed out waiting for the database startup lock."
                        )
                    time.sleep(0.5)

        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)

        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(
                    handle.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _database_is_ready() -> bool:
    """Check that the required governed analytics views exist."""

    if not DB_FILE.is_file():
        return False

    con = duckdb.connect(str(DB_FILE), read_only=True)

    try:
        existing_views = {
            row[0]
            for row in con.execute("""
                SELECT table_name
                FROM information_schema.views
                WHERE table_schema = 'analytics'
            """).fetchall()
        }

        required_views = {
            "vw_company_kpis",
            "vw_all_metrics",
        }

        return required_views.issubset(existing_views)

    finally:
        con.close()


def ensure_database_ready() -> bool:
    """Validate the database and build it once when necessary."""

    with _get_database_thread_lock():

        with _database_process_lock():

            if _database_is_ready():
                return True

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "run_pipeline.py"),
                ],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=False,
                timeout=900,
            )

            if result.returncode != 0:
                raise RuntimeError(
                    "PulseIQ pipeline failed during database initialization.\n\n"
                    f"STDOUT:\n{result.stdout}\n\n"
                    f"STDERR:\n{result.stderr}"
                )

            if not _database_is_ready():
                raise RuntimeError(
                    "Pipeline finished, but required analytics views "
                    "are still missing."
                )

            return True


# --------------------------------------------------
# 3. Load governed analytics views
# --------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def load_view(view_name: str) -> pd.DataFrame:
    """Load data only from an approved analytics view."""

    if (
        not view_name.replace("_", "").isalnum()
        or not view_name.startswith("vw_")
    ):
        raise ValueError(
            "Only named analytics views can be loaded "
            "into the dashboard."
        )

    ensure_database_ready()

    con = duckdb.connect(str(DB_FILE), read_only=True)

    try:
        return con.execute(
            f"SELECT * FROM analytics.{view_name}"
        ).df()
    finally:
        con.close()


def require_data(view_name: str) -> pd.DataFrame:
    """Load a view and display a helpful message when it is empty."""

    df = load_view(view_name)

    if df.empty:
        st.info(
            "No rows are available yet. Run "
            "`python run_pipeline.py` from the project folder first."
        )

    return df


def metric(metric_id: str) -> pd.DataFrame:
    """Return the rows for one governed metric."""

    all_metrics = load_view("vw_all_metrics")

    if all_metrics.empty:
        return all_metrics

    return all_metrics.loc[
        all_metrics["metric_id"].astype(str).eq(metric_id)
    ].copy()


# --------------------------------------------------
# 4. Formatting helpers
# --------------------------------------------------

def money(value) -> str:
    """Format a number as a full INR amount."""

    if value is None or pd.isna(value):
        return "-"

    return "₹" + f"{float(value):,.0f}"


def money_compact(value) -> str:
    """Format INR amounts compactly for narrow KPI cards."""

    if value is None or pd.isna(value):
        return "-"

    amount = float(value)
    sign = "-" if amount < 0 else ""
    amount = abs(amount)

    if amount >= 10_000_000:
        return f"{sign}₹{amount / 10_000_000:.2f} Cr"

    if amount >= 100_000:
        return f"{sign}₹{amount / 100_000:.2f} L"

    if amount >= 1_000:
        return f"{sign}₹{amount / 1_000:.1f}K"

    return sign + money(amount)


def money_delta(current, previous) -> str | None:
    """Show the difference from the previous available period."""

    if (
        current is None
        or previous is None
        or pd.isna(current)
        or pd.isna(previous)
    ):
        return None

    change = float(current) - float(previous)
    sign = "+" if change >= 0 else "-"

    return (
        f"{sign}{money_compact(abs(change))} "
        "vs prior available month"
    )


def pct(value, multiplier=1.0) -> str:
    """Format a percentage."""

    if value is None or pd.isna(value):
        return "-"

    return f"{float(value) * multiplier:.1f}%"


# --------------------------------------------------
# 5. Date-range filter
# --------------------------------------------------

def apply_period_filter(
    df: pd.DataFrame,
    date_col: str = "period",
    key_prefix: str = "default",
) -> pd.DataFrame:
    """Filter rows by date using unique Streamlit widget keys."""

    if df.empty or date_col not in df.columns:
        return df

    out = df.copy()
    out[date_col] = pd.to_datetime(
        out[date_col],
        errors="coerce",
    )

    valid = out[date_col].dropna()

    if valid.empty:
        return out

    min_d = valid.min().date()
    max_d = valid.max().date()

    col1, col2 = st.columns(2)

    widget_prefix = f"{key_prefix}_{date_col}"

    start = col1.date_input(
        "From",
        value=min_d,
        min_value=min_d,
        max_value=max_d,
        key=f"{widget_prefix}_from",
    )

    end = col2.date_input(
        "To",
        value=max_d,
        min_value=min_d,
        max_value=max_d,
        key=f"{widget_prefix}_to",
    )

    if start > end:
        st.warning(
            "The start date is after the end date. "
            "Correct the selected range to filter the data."
        )
        return out

    return out.loc[
        out[date_col].between(
            pd.Timestamp(start),
            pd.Timestamp(end),
        )
    ]


# --------------------------------------------------
# 6. Department filter
# --------------------------------------------------

def department_filter(
    df: pd.DataFrame,
    label: str = "Department",
    key_prefix: str = "default",
) -> pd.DataFrame:
    """Filter a dataframe using a unique department selector."""

    if df.empty or "department_id" not in df.columns:
        return df

    options = sorted(
        df["department_id"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    chosen = st.multiselect(
        label,
        options,
        default=options,
        key=f"dep_{key_prefix}_{label}",
    )

    if not chosen:
        return df.iloc[0:0]

    return df.loc[
        df["department_id"].astype(str).isin(chosen)
    ]


# --------------------------------------------------
# 7. Line chart
# --------------------------------------------------

def metric_line(
    df: pd.DataFrame,
    title: str,
    y_title: str | None = None,
    x: str = "period",
    y: str = "metric_value",
    color: str | None = "department_id",
) -> None:
    """Display a line chart from a governed metric dataframe."""

    if (
        not df.empty
        and x in df.columns
        and y in df.columns
    ):
        usable = df.dropna(subset=[x, y]).copy()
    else:
        usable = pd.DataFrame()

    if usable.empty:
        st.info(
            "No unsuppressed values are available "
            "for this chart and date range."
        )
        return

    if color not in usable.columns:
        color = None

    labels = {
        x: "Period",
        y: y_title or "Value",
    }

    if color is not None:
        labels[color] = "Group"

    fig = px.line(
        usable,
        x=x,
        y=y,
        color=color,
        markers=True,
        title=title,
        labels=labels,
    )

    fig.update_layout(
        margin=dict(l=10, r=10, t=55, b=10),
        legend_title_text="Group",
        hovermode="x unified",
    )

    st.plotly_chart(fig, width="stretch")


# --------------------------------------------------
# 8. Bar chart
# --------------------------------------------------

def metric_bar(
    df: pd.DataFrame,
    title: str,
    x: str = "dimension_label",
    y: str = "metric_value",
    horizontal: bool = True,
    value_label: str = "Value",
) -> None:
    """Display a bar chart with a configurable value-axis label.

    Set value_label="Employees" for headcount charts.
    Other charts retain the default "Value" label unless
    the caller provides a more suitable description.
    """

    if (
        not df.empty
        and x in df.columns
        and y in df.columns
    ):
        usable = df.dropna(subset=[x, y]).copy()
    else:
        usable = pd.DataFrame()

    if usable.empty:
        st.info(
            "No unsuppressed values are available "
            "for this chart."
        )
        return

    usable = usable.sort_values(
        y,
        ascending=not horizontal,
    )

    chart_labels = {
        x: "Group",
        y: value_label,
    }

    if horizontal:
        fig = px.bar(
            usable,
            x=y,
            y=x,
            orientation="h",
            title=title,
            labels=chart_labels,
        )
    else:
        fig = px.bar(
            usable,
            x=x,
            y=y,
            title=title,
            labels=chart_labels,
        )

    fig.update_layout(
        margin=dict(l=10, r=10, t=55, b=10),
    )

    st.plotly_chart(fig, width="stretch")


# --------------------------------------------------
# 9. Privacy message
# --------------------------------------------------

def privacy_note() -> None:
    """Display the project's small-group privacy reminder."""

    st.caption(
        "Privacy guardrail: metric values for groups below "
        "the metric dictionary's minimum group size are "
        "suppressed. This dashboard does not display "
        "individual employee risk scores."
    )


# --------------------------------------------------
# 10. Empty database state
# --------------------------------------------------

def empty_state() -> None:
    """Show instructions when the local database is missing."""

    st.title("PulseIQ Analytics")

    st.warning(
        "The local DuckDB database is not ready yet."
    )

    st.code(
        "python run_pipeline.py",
        language="powershell",
    )

    st.write(
        "Run the command in a terminal opened at the "
        "project root, then refresh this page."
    )
