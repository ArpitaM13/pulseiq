
import hmac

import duckdb
import pandas as pd
import streamlit as st

from src.dashboard_utils import (
    DB_FILE,
    ensure_database_ready,
    load_view,
    privacy_note,
)


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Self-Service KPI Explorer",
    page_icon="📊",
    layout="wide",
)

st.title("Self-Service KPI Explorer")
st.caption(
    "Phase 4 | Task 18 - Role-based KPI exploration "
    "with privacy-aware drill-down"
)


# ---------------------------------------------------------
# DATABASE READINESS
# ---------------------------------------------------------

try:
    with st.spinner("Checking analytics database..."):
        ensure_database_ready()
except Exception as exc:
    st.error(f"Analytics database is not ready: {exc}")
    st.stop()


# ---------------------------------------------------------
# ROLE CONFIGURATION
# ---------------------------------------------------------

ROLE_SETTINGS = {
    "ADMIN": {
        "password_key": "admin_password",
        "metrics": None,
        "levels": ["Company", "Department", "Team"],
    },
    "HR": {
        "password_key": "hr_password",
        "metrics": {
            "M01", "M02", "M03", "M04", "M05", "M06",
            "M07", "M08", "M09", "M10", "M11", "M12",
            "M13", "M14", "M15", "M27", "M28",
        },
        "levels": ["Department"],
    },
    "MANAGER": {
        "password_key": "manager_password",
        "metrics": {
            "M01", "M02", "M03", "M04", "M05", "M06",
            "M07", "M08", "M09", "M10", "M11", "M12",
            "M13", "M14", "M15",
            "M22", "M23", "M24", "M25",
        },
        "levels": ["Department", "Team"],
    },
    "EXECUTIVE": {
        "password_key": "executive_password",
        "metrics": {"M17", "M18", "M19", "M20"},
        "levels": ["Company"],
    },
}


def get_role_secrets():
    """Read role credentials from Streamlit secrets."""
    try:
        return st.secrets["role_access"]
    except Exception:
        return None


def authenticate_user():
    """Authenticate using a role-specific secret password."""

    role_secrets = get_role_secrets()

    if role_secrets is None:
        st.error(
            "Role access is not configured. "
            "The administrator must add the role_access "
            "credentials to Streamlit Cloud Secrets."
        )

        st.code(
            """
[role_access]
admin_password = "SET_A_PRIVATE_PASSWORD"
hr_password = "SET_A_PRIVATE_PASSWORD"
manager_password = "SET_A_PRIVATE_PASSWORD"
manager_department_id = "D03"
manager_team_id = ""
executive_password = "SET_A_PRIVATE_PASSWORD"
            """.strip(),
            language="toml",
        )

        st.info(
            "Do not put real passwords in this Python file "
            "or commit them to GitHub."
        )

        return None

    if "kpi_authenticated_role" in st.session_state:
        return st.session_state["kpi_authenticated_role"]

    st.subheader("Sign in to KPI Explorer")

    with st.form("kpi_role_login"):
        selected_role = st.selectbox(
            "Select your assigned role",
            list(ROLE_SETTINGS.keys()),
        )

        entered_password = st.text_input(
            "Role password",
            type="password",
        )

        submitted = st.form_submit_button("Sign in")

    if submitted:
        password_key = ROLE_SETTINGS[selected_role]["password_key"]

        expected_password = str(
            role_secrets.get(password_key, "")
        )

        if (
            expected_password
            and entered_password
            and hmac.compare_digest(
                entered_password,
                expected_password,
            )
        ):
            st.session_state["kpi_authenticated_role"] = (
                selected_role
            )
            st.rerun()
        else:
            st.error("Invalid role credentials.")

    return None


role = authenticate_user()

if role is None:
    st.stop()


# ---------------------------------------------------------
# AUTHENTICATED ROLE DETAILS
# ---------------------------------------------------------

role_secrets = get_role_secrets()
role_config = ROLE_SETTINGS[role]

manager_department = str(
    role_secrets.get("manager_department_id", "")
).strip()

manager_team = str(
    role_secrets.get("manager_team_id", "")
).strip()

header_col1, header_col2 = st.columns([4, 1])

with header_col1:
    st.success(f"Authenticated role: {role}")

with header_col2:
    if st.button("Sign out"):
        st.session_state.pop("kpi_authenticated_role", None)
        st.rerun()


# ---------------------------------------------------------
# LOAD ANALYTICS DATA
# ---------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def load_team_lookup():
    con = duckdb.connect(str(DB_FILE), read_only=True)

    try:
        return con.execute("""
            SELECT
                team_id,
                team_name,
                department_id,
                team_lead_employee_id,
                active_members
            FROM warehouse.dim_team
            ORDER BY team_name
        """).fetchdf()
    finally:
        con.close()


@st.cache_data(ttl=60, show_spinner=False)
def load_department_lookup():
    con = duckdb.connect(str(DB_FILE), read_only=True)

    try:
        return con.execute("""
            SELECT
                department_id,
                department_name
            FROM warehouse.dim_department
            ORDER BY department_name
        """).fetchdf()
    finally:
        con.close()


try:
    metrics = load_view("vw_all_metrics").copy()
    catalog = load_view("vw_metric_catalog").copy()
    teams = load_team_lookup()
    departments = load_department_lookup()

except Exception as exc:
    st.error(f"Unable to load KPI data: {exc}")
    st.stop()


if metrics.empty:
    st.warning("No KPI records are currently available.")
    st.stop()


# ---------------------------------------------------------
# PREPARE METRIC DATA
# ---------------------------------------------------------

metrics["period"] = pd.to_datetime(
    metrics["period"],
    errors="coerce",
)

metrics["metric_id"] = metrics["metric_id"].astype(str)

metrics = metrics.dropna(subset=["period"]).copy()

metrics["department_id"] = (
    metrics["department_id"].fillna("").astype(str)
)

metrics["dimension_label"] = (
    metrics["dimension_label"].fillna("").astype(str)
)

# Team metric labels use the format: T01 / SP-38.
metrics["team_id"] = (
    metrics["dimension_label"]
    .str.split("/", n=1)
    .str[0]
    .str.strip()
)

metrics = metrics.merge(
    teams[["team_id", "team_name", "department_id"]].rename(
        columns={"department_id": "team_department_id"}
    ),
    on="team_id",
    how="left",
)

metrics = metrics.merge(
    departments,
    on="department_id",
    how="left",
)


# ---------------------------------------------------------
# ROLE-BASED METRIC RESTRICTIONS
# ---------------------------------------------------------

allowed_metrics = role_config["metrics"]

if allowed_metrics is not None:
    metrics = metrics[
        metrics["metric_id"].isin(allowed_metrics)
    ].copy()


if role == "MANAGER":
    if not manager_department:
        st.error(
            "Manager department is not configured. "
            "Ask the administrator to set "
            "manager_department_id in Streamlit Secrets."
        )
        st.stop()

    metrics = metrics[
        (
            metrics["department_id"] == manager_department
        )
        |
        (
            metrics["team_department_id"] == manager_department
        )
    ].copy()

    if manager_team:
        metrics = metrics[
            (
                metrics["metric_id"].isin(
                    ["M22", "M23", "M24", "M25"]
                )
                & (metrics["team_id"] == manager_team)
            )
            |
            (
                metrics["department_id"] == manager_department
            )
        ].copy()


if metrics.empty:
    st.warning(
        "No metrics are available for the authenticated role."
    )
    st.stop()


# ---------------------------------------------------------
# DRILL-DOWN LEVEL
# ---------------------------------------------------------

st.subheader("Explore analytics")

available_levels = role_config["levels"]

selected_level = st.selectbox(
    "Select analysis level",
    available_levels,
)

if role == "ADMIN":
    st.caption(
        "Administrator access: approved company, department "
        "and team metrics are available."
    )
elif role == "HR":
    st.caption("HR access: workforce metrics only.")
elif role == "MANAGER":
    st.caption(
        f"Manager access is restricted to department "
        f"{manager_department}."
    )
else:
    st.caption(
        "Executive access: company-level financial metrics only."
    )


# ---------------------------------------------------------
# FILTER DATA BY LEVEL
# ---------------------------------------------------------

if selected_level == "Company":

    level_data = metrics[
        metrics["department_id"].eq("")
        & metrics["dimension_label"].isin(
            ["ALL", "All company"]
        )
    ].copy()

    level_description = (
        "Company-level records. Department, account and team "
        "records are not presented as company totals."
    )

elif selected_level == "Department":

    level_data = metrics[
        metrics["department_id"].ne("")
        & ~metrics["metric_id"].isin(
            ["M22", "M23", "M24", "M25"]
        )
    ].copy()

    if role == "MANAGER":
        level_data = level_data[
            level_data["department_id"] == manager_department
        ]

    department_options = (
        level_data[
            ["department_id", "department_name"]
        ]
        .drop_duplicates()
        .sort_values("department_name")
    )

    if department_options.empty:
        st.warning("No department-level records are available.")
        st.stop()

    department_labels = {
        row.department_id: (
            f"{row.department_name} ({row.department_id})"
        )
        for row in department_options.itertuples()
    }

    selected_department = st.selectbox(
        "Select department",
        list(department_labels.keys()),
        format_func=lambda value: department_labels[value],
    )

    level_data = level_data[
        level_data["department_id"] == selected_department
    ].copy()

    level_description = (
        "Department-level workforce metrics. "
        "Only approved department aggregates are displayed."
    )

elif selected_level == "Team":

    level_data = metrics[
        metrics["metric_id"].isin(
            ["M22", "M23", "M24", "M25"]
        )
        & metrics["team_id"].ne("")
    ].copy()

    if role == "MANAGER":
        level_data = level_data[
            level_data["team_department_id"] == manager_department
        ]

        if manager_team:
            level_data = level_data[
                level_data["team_id"] == manager_team
            ]

    team_options = (
        level_data[
            ["team_id", "team_name", "team_department_id"]
        ]
        .drop_duplicates()
        .dropna(subset=["team_name"])
        .sort_values("team_name")
    )

    if team_options.empty:
        st.warning("No approved team-level metrics are available.")
        st.stop()

    team_labels = {
        row.team_id: (
            f"{row.team_name} ({row.team_id})"
        )
        for row in team_options.itertuples()
    }

    selected_team = st.selectbox(
        "Select team",
        list(team_labels.keys()),
        format_func=lambda value: team_labels[value],
    )

    level_data = level_data[
        level_data["team_id"] == selected_team
    ].copy()

    level_description = (
        "Team-level sprint metrics. Each record represents "
        "a team and sprint, not an employee."
    )

else:
    st.error("Unsupported analysis level.")
    st.stop()


st.caption(level_description)


# ---------------------------------------------------------
# METRIC SELECTION
# ---------------------------------------------------------

if level_data.empty:
    st.info("No records are available at this analysis level.")
    st.stop()


available_metric_ids = sorted(
    level_data["metric_id"].dropna().unique().tolist()
)

available_catalog = catalog[
    catalog["metric_id"].astype(str).isin(available_metric_ids)
].copy()

if available_catalog.empty:
    st.warning("Metric definitions are unavailable.")
    st.stop()


metric_options = {
    f"{row.metric_id} | {row.metric_name}": row.metric_id
    for row in available_catalog.itertuples()
}

selected_metric_label = st.selectbox(
    "Select KPI",
    list(metric_options.keys()),
)

selected_metric_id = metric_options[selected_metric_label]

selected_data = level_data[
    level_data["metric_id"] == selected_metric_id
].copy()

selected_definition = available_catalog[
    available_catalog["metric_id"].astype(str)
    == selected_metric_id
].iloc[0]


# ---------------------------------------------------------
# METRIC DEFINITION
# ---------------------------------------------------------

st.subheader("Metric definition")

definition_col1, definition_col2 = st.columns(2)

with definition_col1:
    st.write("**Business definition**")
    st.write(
        selected_definition.get(
            "business_definition",
            "Definition not available.",
        )
    )

    st.write("**Source table**")
    st.write(
        selected_definition.get(
            "source_table",
            "Not specified",
        )
    )

with definition_col2:
    st.write("**Formula**")
    st.write(
        selected_definition.get(
            "formula",
            "See the metric catalogue.",
        )
    )

    st.write("**Grain**")
    st.write(
        selected_definition.get(
            "grain",
            "Not specified",
        )
    )


# ---------------------------------------------------------
# DATE FILTER
# ---------------------------------------------------------

minimum_date = selected_data["period"].min().date()
maximum_date = selected_data["period"].max().date()

date_range = st.date_input(
    "Select reporting date range",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
)

if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
    st.info("Select both a start date and an end date.")
    st.stop()

start_date, end_date = date_range

if start_date > end_date:
    st.error("Start date cannot be after end date.")
    st.stop()

selected_data = selected_data[
    selected_data["period"].dt.date.between(
        start_date,
        end_date,
    )
].copy()


# ---------------------------------------------------------
# PRIVACY SUPPRESSION
# ---------------------------------------------------------

if "group_size" not in selected_data.columns:
    selected_data["group_size"] = None

if "min_group_size" not in selected_data.columns:
    selected_data["min_group_size"] = None

selected_data["metric_value"] = pd.to_numeric(
    selected_data["metric_value"],
    errors="coerce",
)

selected_data["group_size"] = pd.to_numeric(
    selected_data["group_size"],
    errors="coerce",
)

selected_data["min_group_size"] = pd.to_numeric(
    selected_data["min_group_size"],
    errors="coerce",
)

minimum_group = selected_data["min_group_size"].fillna(5)

is_suppressed = (
    selected_data["metric_value"].isna()
    |
    (
        selected_data["group_size"].notna()
        & (selected_data["group_size"] < minimum_group)
    )
)

selected_data["display_status"] = "Available"

selected_data.loc[
    is_suppressed,
    "display_status",
] = "Suppressed by privacy rule"

# Never display the underlying value for a suppressed group.
selected_data.loc[
    is_suppressed,
    "metric_value",
] = None


# ---------------------------------------------------------
# KPI SUMMARY
# ---------------------------------------------------------

st.subheader("KPI results")

total_records = len(selected_data)

available_records = int(
    (selected_data["display_status"] == "Available").sum()
)

suppressed_records = int(
    (selected_data["display_status"] != "Available").sum()
)

summary_col1, summary_col2, summary_col3 = st.columns(3)

summary_col1.metric("Records", total_records)
summary_col2.metric("Available", available_records)
summary_col3.metric("Privacy-suppressed", suppressed_records)


# ---------------------------------------------------------
# DISPLAY RESULTS
# ---------------------------------------------------------

if selected_data.empty:
    st.info("No records match the selected filters.")

else:
    display_data = selected_data.copy()

    if selected_level == "Team":
        display_data["analysis_dimension"] = (
            display_data["team_name"].fillna("Unknown team")
            + " / "
            + display_data["dimension_label"]
            .str.split("/", n=1)
            .str[-1]
            .str.strip()
        )

    elif selected_level == "Department":
        display_data["analysis_dimension"] = (
            display_data["department_name"].fillna(
                display_data["department_id"]
            )
        )

    else:
        display_data["analysis_dimension"] = (
            display_data["dimension_label"]
        )

    display_columns = [
        "period",
        "analysis_dimension",
        "metric_value",
        "unit",
        "display_status",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in display_data.columns
    ]

    final_data = display_data[display_columns].copy()

    final_data["period"] = (
        final_data["period"].dt.strftime("%Y-%m-%d")
    )

    st.dataframe(
        final_data,
        width="stretch",
        hide_index=True,
    )

    csv_data = final_data.to_csv(index=False).encode("utf-8")

    st.download_button(
        "Download filtered KPI data",
        data=csv_data,
        file_name=(
            f"pulseiq_{selected_level.lower()}_"
            f"{selected_metric_id}.csv"
        ),
        mime="text/csv",
    )


# ---------------------------------------------------------
# GOVERNANCE NOTES
# ---------------------------------------------------------

st.divider()

st.subheader("Access and privacy controls")

st.write(f"Authenticated role: **{role}**")

st.write(
    "Role permissions are applied before KPI selection. "
    "The explorer does not expose employee names, employee IDs, "
    "or individual task assignments."
)

st.write(
    "Team metrics are displayed at team-sprint grain. "
    "Department metrics are displayed at department-month grain. "
    "Different grains are not combined into misleading totals."
)

privacy_note()
