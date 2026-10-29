
import streamlit as st
import pandas as pd
import plotly.express as px

from src.dashboard_utils import (
    metric,
    load_view,
    apply_period_filter,
    department_filter,
    privacy_note,
)

# ============================================================
# PHASE 2 - TASK 6: ATTENDANCE & LEAVE ANALYTICS
# ============================================================

st.title("Attendance & Leave")

st.caption(
    "Phase 2 | Task 6 - Attendance rate, punctuality, "
    "overtime, leave patterns and holiday insights"
)

# Reporting period
REPORT_START = pd.Timestamp("2025-04-01")
REPORT_END = pd.Timestamp("2026-09-01")


# ============================================================
# 1. ATTENDANCE RATE BY DEPARTMENT (M13)
# ============================================================

st.subheader("Attendance Rate by Department")

attendance = metric("M13")

if attendance.empty:
    st.info("Run the pipeline first.")
    st.stop()

attendance = apply_period_filter(
    attendance,
    key_prefix="attendance_rate"
)

attendance = department_filter(
    attendance,
    key_prefix="attendance_rate"
)

attendance = attendance.copy()
attendance["attendance_pct"] = attendance["metric_value"] * 100

attendance_visible = attendance.dropna(
    subset=["attendance_pct"]
)

if not attendance_visible.empty:
    fig = px.line(
        attendance_visible,
        x="period",
        y="attendance_pct",
        color="department_id",
        markers=True,
        title="Monthly Attendance Rate by Department",
        labels={
            "period": "Month",
            "attendance_pct": "Attendance (%)",
            "department_id": "Department"
        }
    )

    st.plotly_chart(fig, width="stretch")

    st.caption(
        f"Visible department-month points: "
        f"{len(attendance_visible):,}. "
        "Paid leave is treated as not present under the "
        "supplied metric definition."
    )
else:
    st.info("No attendance data for the selected filters.")


# ============================================================
# 2. LATE ARRIVALS (M14)
# ============================================================

st.subheader("Late Arrivals by Department")

late = metric("M14").copy()

if not late.empty:
    late = apply_period_filter(
        late,
        key_prefix="late_arrivals"
    )

    late = department_filter(
        late,
        key_prefix="late_arrivals"
    )

    late["late_per_present_day"] = late["metric_value"]

    late_visible = late.dropna(
        subset=["late_per_present_day"]
    )

    if not late_visible.empty:
        fig = px.line(
            late_visible,
            x="period",
            y="late_per_present_day",
            color="department_id",
            markers=True,
            title="Late Arrivals per Present Day",
            labels={
                "period": "Month",
                "late_per_present_day": "Late Arrival Ratio",
                "department_id": "Department"
            }
        )

        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No late-arrival data for the selected filters.")
else:
    st.info("Late-arrival data is unavailable.")


# ============================================================
# 3. OVERTIME HOURS BY MONTH AND DEPARTMENT
# ============================================================

st.subheader("Overtime Hours by Month and Department")

overtime = load_view("vw_attendance_overtime_monthly")

if not overtime.empty:
    overtime = apply_period_filter(
        overtime,
        key_prefix="overtime_hours"
    )

    overtime = department_filter(
        overtime,
        key_prefix="overtime_hours"
    )

    overtime = overtime.dropna(
        subset=["overtime_hours"]
    )

    if not overtime.empty:
        fig = px.line(
            overtime,
            x="period",
            y="overtime_hours",
            color="department_id",
            markers=True,
            title="Monthly Overtime Hours",
            labels={
                "period": "Month",
                "overtime_hours": "Overtime Hours",
                "department_id": "Department"
            }
        )

        st.plotly_chart(fig, width="stretch")
    else:
        st.info(
            "No visible overtime data for the selected filters."
        )
else:
    st.info("Overtime data is unavailable.")


# ============================================================
# 4. LEAVE REQUESTS BY TYPE AND STATUS
# ============================================================

st.subheader("Leave Requests by Type and Status")

leave = load_view("vw_leave_type_summary")

if not leave.empty:
    leave = leave.dropna(
        subset=["visible_request_count"]
    )

    if not leave.empty:
        fig = px.bar(
            leave,
            x="leave_type_code",
            y="visible_request_count",
            color="status",
            barmode="group",
            title="Leave Requests by Type and Status",
            labels={
                "leave_type_code": "Leave Type",
                "visible_request_count": "Requests",
                "status": "Status"
            }
        )

        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No visible leave-request data.")

    st.caption(
        "Only leave groups meeting the minimum privacy "
        "threshold are displayed. Two swapped-date requests "
        "are quarantined and are not silently rewritten."
    )
else:
    st.info("Leave-request data is unavailable.")


# ============================================================
# 5. MONTHLY LEAVE DAYS BY TYPE
# ============================================================

st.subheader("Monthly Leave Days by Type")

leave_days = load_view("vw_leave_days_monthly")

if not leave_days.empty:

    # Restrict to the attendance reporting period
    leave_days = leave_days.copy()
    leave_days["period"] = pd.to_datetime(
        leave_days["period"]
    )

    leave_days = leave_days[
        (leave_days["period"] >= REPORT_START)
        & (leave_days["period"] <= REPORT_END)
    ].copy()

    if not leave_days.empty:
        leave_days = apply_period_filter(
            leave_days,
            key_prefix="monthly_leave_days"
        )

        leave_days = leave_days.dropna(
            subset=["visible_leave_days"]
        )

        if not leave_days.empty:
            fig = px.bar(
                leave_days,
                x="period",
                y="visible_leave_days",
                color="leave_type_code",
                barmode="stack",
                title="Approved Leave Days by Month and Type",
                labels={
                    "period": "Month",
                    "visible_leave_days": "Leave Days",
                    "leave_type_code": "Leave Type"
                }
            )

            st.plotly_chart(fig, width="stretch")

            st.caption(
                "Only groups with at least 5 employees are "
                "displayed. Maternity leave is allocated "
                "proportionally across working dates and "
                "should be treated as an estimate."
            )
        else:
            st.info(
                "No visible leave-days data for the selected dates."
            )
    else:
        st.info("No leave data within the reporting period.")
else:
    st.info("Monthly leave-days data is unavailable.")


# ============================================================
# 6. ATTENDANCE INSIGHTS AND HOLIDAY CONTEXT
# ============================================================

st.subheader("Attendance Insights & Holiday Context")

st.markdown("""
### Insight 1: July 2025 - High Attendance

**Attendance Rate: 95.51%**

- 23 working days.
- No recorded holidays.
- Highest attendance among the months investigated.
- Provides a useful high-attendance reference point.

### Insight 2: January 2026 - Lower Attendance

**Attendance Rate: 93.29%**

- 19 working days.
- Three recorded holidays.
- January 26 fell on a Monday, creating a three-day weekend.
- Leave and punctuality patterns warrant further investigation.

### Insight 3: May 2026 - Low Attendance

**Attendance Rate: 92.89%**

- 20 working days.
- One recorded holiday.
- May 1 fell on a Friday, creating a three-day weekend.
- Attendance was **2.62 percentage points lower** than July 2025.
""")

st.caption(
    "The three attendance percentages use the governed "
    "M13 calculation. These are selected monthly observations "
    "across the workforce, not department-specific values. "
    "Holiday patterns provide context and do not establish "
    "causation."
)


# ============================================================
# 7. HOLIDAY AND LONG-WEEKEND OBSERVATIONS
# ============================================================

st.subheader("Holiday and Long-Weekend Observations")

holiday_data = pd.DataFrame([
    {
        "Holiday": "14 April 2025",
        "Day": "Monday",
        "Long Weekend": "12-14 April 2025"
    },
    {
        "Holiday": "18 April 2025",
        "Day": "Friday",
        "Long Weekend": "18-20 April 2025"
    },
    {
        "Holiday": "15 August 2025",
        "Day": "Friday",
        "Long Weekend": "15-17 August 2025"
    },
    {
        "Holiday": "20-21 October 2025",
        "Day": "Monday-Tuesday",
        "Long Weekend": "18-21 October 2025"
    },
    {
        "Holiday": "26 January 2026",
        "Day": "Monday",
        "Long Weekend": "24-26 January 2026"
    },
    {
        "Holiday": "20 March 2026",
        "Day": "Friday",
        "Long Weekend": "20-22 March 2026"
    },
    {
        "Holiday": "3 April 2026",
        "Day": "Friday",
        "Long Weekend": "3-5 April 2026"
    },
    {
        "Holiday": "1 May 2026",
        "Day": "Friday",
        "Long Weekend": "1-3 May 2026"
    },
    {
        "Holiday": "14 September 2026",
        "Day": "Monday",
        "Long Weekend": "12-14 September 2026"
    }
])

st.dataframe(
    holiday_data,
    width="stretch",
    hide_index=True
)

st.caption(
    "Long weekends are derived from the supplied holiday "
    "calendar and a Saturday-Sunday weekend pattern."
)


# ============================================================
# 8. PRIVACY NOTE
# ============================================================

privacy_note()
