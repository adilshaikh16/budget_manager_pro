import streamlit as st
import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
from datetime import datetime

# ===================== CONFIG =====================
st.set_page_config(page_title="💰 Budget Manager Pro – PKR Edition", layout="wide")

# ===================== DATABASE =====================
def init_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            account TEXT,
            category TEXT,
            type TEXT,
            amount REAL,
            note TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_transaction(date, account, category, type_, amount, note):
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO transactions (date, account, category, type, amount, note)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (date, account, category, type_, amount, note))
    conn.commit()
    conn.close()

def get_transactions():
    conn = sqlite3.connect('data.db')
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC", conn)
    conn.close()
    return df

# ===================== INIT DB =====================
init_db()

# ===================== SIDEBAR =====================
st.sidebar.title("💼 Budget Manager Pro")
st.sidebar.markdown("**Edition:** v1.0 By Adil")
st.sidebar.markdown("---")

menu = st.sidebar.radio("Navigate", ["📊 Dashboard", "➕ Add Transaction", "📁 View Records", "📤 Export Data"])

# ===================== ADD TRANSACTION =====================
if menu == "➕ Add Transaction":
    st.title("➕ Add New Transaction")
    col1, col2 = st.columns(2)

    with col1:
        date = st.date_input("Date", datetime.today())
        account = st.selectbox("Account", ["Cash", "Bank", "JazzCash", "Easypaisa", "Other"])
        category = st.text_input("Category (e.g. Food, Rent, Salary)")
    with col2:
        type_ = st.radio("Type", ["Income", "Expense"])
        amount = st.number_input("Amount (PKR)", min_value=0.0, step=100.0)
        note = st.text_area("Note (optional)")

    if st.button("💾 Save Transaction"):
        add_transaction(str(date), account, category, type_, amount, note)
        st.success("✅ Transaction added successfully!")

# ===================== VIEW RECORDS =====================
elif menu == "📁 View Records":
    st.title("📜 All Transactions")
    df = get_transactions()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No transactions found yet.")

# ===================== DASHBOARD =====================
elif menu == "📊 Dashboard":
    st.title("📊 Financial Overview")
    df = get_transactions()
    if df.empty:
        st.info("No transactions found yet.")
    else:
        total_income = df[df['type'] == 'Income']['amount'].sum()
        total_expense = df[df['type'] == 'Expense']['amount'].sum()
        balance = total_income - total_expense

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Income", f"PKR {total_income:,.0f}")
        col2.metric("Total Expense", f"PKR {total_expense:,.0f}")
        col3.metric("Current Balance", f"PKR {balance:,.0f}")

        st.markdown("---")

        # Pie chart
        exp_df = df[df['type'] == 'Expense']
        if not exp_df.empty:
            exp_by_cat = exp_df.groupby('category')['amount'].sum()
            fig, ax = plt.subplots()
            ax.pie(exp_by_cat, labels=exp_by_cat.index, autopct="%1.1f%%")
            ax.set_title("Expense Breakdown by Category")
            st.pyplot(fig)

# ===================== EXPORT DATA =====================
elif menu == "📤 Export Data":
    st.title("📤 Export Transactions")
    df = get_transactions()
    if df.empty:
        st.info("No data to export.")
    else:
        df.to_excel("transactions.xlsx", index=False)
        with open("transactions.xlsx", "rb") as f:
            st.download_button("⬇️ Download Excel File", f, "transactions.xlsx")
