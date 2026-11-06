
import streamlit as st
import pandas as pd
import plotly.express as px
from src.dashboard_utils import metric, load_view, apply_period_filter, money

st.title("Finance, Receivables & Cash Flow")
st.caption("Phase 3 | Tasks 11-12 - P&L trends, invoice aging, expenses and cash collections")

# --------------------------------------------------
# 1. Monthly Profit and Loss
# --------------------------------------------------
f = load_view("vw_finance_monthly")

if not f.empty:
    f = apply_period_filter(f, key_prefix="finance_monthly")

    st.subheader("Monthly Profit & Loss")

    months = sorted(f["period"].dropna().unique())

    if months:
        selected_month = st.selectbox(
            "Select month",
            months,
            format_func=lambda x: pd.to_datetime(x).strftime("%B %Y"),
            key="monthly_pnl_selector"
        )

        selected = f.loc[f["period"] == selected_month].iloc[0]

        c1, c2, c3 = st.columns(3)
        c1.metric("Revenue", f"₹{selected['revenue']:,.2f}")
        c2.metric("Expenses", f"₹{selected['expenses']:,.2f}")
        c3.metric("Net Profit", f"₹{selected['net_profit']:,.2f}")

    fig = px.line(
        f,
        x="period",
        y=["revenue", "net_profit"],
        markers=True,
        title="Revenue and Net Profit from the Ledger",
        labels={
            "period": "Month",
            "value": "INR",
            "variable": "Metric"
        }
    )
    st.plotly_chart(fig, width="stretch")

    fig = px.line(
        f,
        x="period",
        y=["operating_margin_pct", "payroll_pct_revenue"],
        markers=True,
        title="Operating Margin and Payroll Share of Revenue",
        labels={
            "period": "Month",
            "value": "Percent",
            "variable": "Metric"
        }
    )
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------
# 2. Days Sales Outstanding
# --------------------------------------------------
dso = metric("M20")

if not dso.empty and dso.metric_value.notna().any():
    st.metric(
        "Days Sales Outstanding (90-day basis)",
        f"{dso.metric_value.dropna().iloc[0]:.1f} days"
    )

# --------------------------------------------------
# 3. Invoice Aging
# --------------------------------------------------
age = load_view("vw_invoice_aging")

if not age.empty:
    st.subheader("Outstanding Invoice Balance by Aging Bucket")

    fig = px.bar(
        age,
        x="ageing_bucket",
        y="balance_due",
        title="Open Receivable Balance",
        labels={
            "ageing_bucket": "Aging Bucket",
            "balance_due": "INR"
        }
    )
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------
# 4. Overdue Receivables by Client
# --------------------------------------------------
ov = metric("M21")

if not ov.empty:
    st.subheader("Overdue Receivables by Client")

    shown = (
        ov.dropna(subset=["metric_value"])
        .sort_values("metric_value", ascending=False)
        .head(15)
    )

    if not shown.empty:
        fig = px.bar(
            shown,
            x="metric_value",
            y="dimension_label",
            orientation="h",
            title="Largest Overdue Balances (Top 15)",
            labels={
                "metric_value": "INR",
                "dimension_label": "Client ID"
            }
        )
        st.plotly_chart(fig, width="stretch")

# --------------------------------------------------
# 5. Monthly Cash Collections
# --------------------------------------------------
cash = load_view("vw_cash_collections_monthly")

if not cash.empty:
    st.subheader("Monthly Cash Collections")

    cash = cash.sort_values("period")

    total_collected = cash["cash_collected"].sum()
    total_invoices = cash["invoices_paid"].sum()

    c1, c2 = st.columns(2)

    c1.metric(
        "Total Cash Collected",
        f"₹{total_collected:,.2f}"
    )

    c2.metric(
        "Invoices with Payments",
        f"{total_invoices:,.0f}"
    )

    fig = px.line(
        cash,
        x="period",
        y="cash_collected",
        markers=True,
        title="Monthly Cash Collections Trend",
        labels={
            "period": "Month",
            "cash_collected": "Cash Collected (INR)"
        }
    )
    st.plotly_chart(fig, width="stretch")

    fig = px.bar(
        cash,
        x="period",
        y="invoices_paid",
        title="Number of Invoices with Payments by Month",
        labels={
            "period": "Month",
            "invoices_paid": "Invoices Paid"
        }
    )
    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Cash collections are calculated using invoice-level amount_paid "
        "grouped by last_payment_date. This is an invoice-level collection "
        "proxy, not a transaction-level or bank-reconciled cash flow."
    )

# --------------------------------------------------
# 6. Expense Trends by Department
# --------------------------------------------------
e = load_view("vw_expense_monthly_department")

if not e.empty:
    st.subheader("Expense Trends by Department")

    e = apply_period_filter(e, key_prefix="expense_monthly")

    fig = px.line(
        e,
        x="period",
        y="total_expense",
        color="department_id",
        markers=True,
        title="Valid Expense Total by Department",
        labels={
            "period": "Month",
            "total_expense": "INR",
            "department_id": "Department"
        }
    )
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------
# 7. Expense by Category
# --------------------------------------------------
cat = load_view("vw_expense_by_category")

if not cat.empty:
    st.subheader("Expense by Category")

    cat = cat.sort_values("spend", ascending=False)

    fig = px.bar(
        cat,
        x="spend",
        y="category",
        orientation="h",
        title="Expense Category Spend (Excluding GST)",
        labels={
            "spend": "INR",
            "category": "Category"
        }
    )

    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------
# 8. Top 10 Vendors
# --------------------------------------------------
vendors = load_view("vw_top_vendors")

if not vendors.empty:
    st.subheader("Top 10 Vendors")

    vendors = vendors.sort_values(
        "spend",
        ascending=False
    ).head(10)

    fig = px.bar(
        vendors,
        x="spend",
        y="vendor_name",
        orientation="h",
        title="Top 10 Vendors by Spend (Excluding GST)",
        labels={
            "spend": "INR",
            "vendor_name": "Vendor"
        }
    )

    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig, width="stretch")

# --------------------------------------------------
# 9. Data Interpretation and Findings
# --------------------------------------------------
st.caption(
    "The monthly DSO uses the workbook's current invoice balance "
    "snapshot and 90-day invoice totals. It should not be read as "
    "a historical balance reconstruction."
)

st.divider()

st.subheader("Key Findings")

st.markdown("""
1. **Office Rent** is the largest expense category, with spending of ₹3.82 crore.
2. **Cloud Hosting** is the second-largest category, with spending of ₹2.79 crore.
3. **Skyline Realty Holdings** is the highest-spend vendor, with spending of ₹1.69 crore.
""")

st.subheader("Possible Reasons for Revenue Increasing but Profit Margin Decreasing")

st.markdown("""
1. Expenses may be increasing faster than revenue.
2. Higher discounts or operating costs may be reducing profitability.
3. Increased spending on rent, cloud hosting, or marketing may be affecting margins.
""")
