st.write("App started successfully")

"""
Budget Manager Pro — Streamlit Edition (app.py)
- SQLite backend (budget_streamlit.db)
- Dark theme compatible (see .streamlit/config.toml instructions below)
- Features: Multi-accounts, categories, add/edit transactions, transfer, filters,
  dashboard with charts, export to Excel.

Run locally:
1) Install dependencies:
   pip install streamlit pandas matplotlib openpyxl
2) Create a folder, put this file `app.py` inside.
3) (Optional) For dark theme create `.streamlit/config.toml` with contents shown in README below.
4) Run: streamlit run app.py

Deploy to Streamlit Cloud / GitHub:
- Push repo with `app.py`, `requirements.txt` (list dependencies), and `.streamlit/config.toml`.

"""

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
from io import BytesIO
import matplotlib.pyplot as plt

DB_FILE = 'budget_streamlit.db'

# --------------------- Database Helpers ---------------------

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            balance REAL DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            account_id INTEGER,
            category_id INTEGER,
            description TEXT,
            FOREIGN KEY(account_id) REFERENCES accounts(id),
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
    ''')
    # seed defaults
    c.execute('SELECT COUNT(*) FROM categories')
    if c.fetchone()[0] == 0:
        default_cats = ['Food','Transport','Rent','Bills','Salary','Shopping','Misc']
        c.executemany('INSERT INTO categories (name) VALUES (?)', [(x,) for x in default_cats])
    c.execute('SELECT COUNT(*) FROM accounts')
    if c.fetchone()[0] == 0:
        default_acc = [('Cash', 0.0), ('Bank', 0.0)]
        c.executemany('INSERT INTO accounts (name,balance) VALUES (?,?)', default_acc)
    conn.commit()
    conn.close()


def get_conn():
    return sqlite3.connect(DB_FILE)

# --------------------- Utility Functions ---------------------

def fetch_accounts():
    conn = get_conn(); c = conn.cursor()
    c.execute('SELECT id, name, balance FROM accounts')
    rows = c.fetchall(); conn.close()
    return rows


def fetch_categories():
    conn = get_conn(); c = conn.cursor()
    c.execute('SELECT id, name FROM categories')
    rows = c.fetchall(); conn.close()
    return rows


def add_account(name):
    conn = get_conn(); c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO accounts (name,balance) VALUES (?,?)', (name,0.0))
    conn.commit(); conn.close()


def add_category(name):
    conn = get_conn(); c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO categories (name) VALUES (?)', (name,))
    conn.commit(); conn.close()


def add_transaction(date, ttype, amount, account_id, category_id, description):
    conn = get_conn(); c = conn.cursor()
    c.execute('INSERT INTO transactions (date,type,amount,account_id,category_id,description) VALUES (?,?,?,?,?,?)', (date,ttype,amount,account_id,category_id,description))
    if ttype == 'Expense':
        c.execute('UPDATE accounts SET balance = balance - ? WHERE id=?', (amount, account_id))
    else:
        c.execute('UPDATE accounts SET balance = balance + ? WHERE id=?', (amount, account_id))
    conn.commit(); conn.close()


def transfer_between_accounts(from_id, to_id, amount):
    conn = get_conn(); c = conn.cursor()
    # balance check
    c.execute('SELECT balance FROM accounts WHERE id=?', (from_id,))
    row = c.fetchone()
    if not row or row[0] < amount:
        conn.close(); return False, 'Insufficient balance'
    # ensure Transfer category
    c.execute("SELECT id FROM categories WHERE name='Transfer'")
    row = c.fetchone()
    if row:
        cat_id = row[0]
    else:
        c.execute("INSERT INTO categories (name) VALUES ('Transfer')")
        cat_id = c.lastrowid
    today = datetime.now().strftime('%Y-%m-%d')
    # make two transactions
    c.execute('UPDATE accounts SET balance = balance - ? WHERE id=?', (amount, from_id))
    c.execute('UPDATE accounts SET balance = balance + ? WHERE id=?', (amount, to_id))
    c.execute('INSERT INTO transactions (date,type,amount,account_id,category_id,description) VALUES (?,?,?,?,?,?)', (today,'Expense',amount,from_id,cat_id,'Transfer'))
    c.execute('INSERT INTO transactions (date,type,amount,account_id,category_id,description) VALUES (?,?,?,?,?,?)', (today,'Income',amount,to_id,cat_id,'Transfer'))
    conn.commit(); conn.close()
    return True, 'Transfer successful'


def query_transactions(start_date=None, end_date=None, account_id=None, category_id=None):
    q = "SELECT t.id, t.date, t.type, t.amount, a.name as account, c.name as category, t.description FROM transactions t LEFT JOIN accounts a ON t.account_id=a.id LEFT JOIN categories c ON t.category_id=c.id"
    conds = []
    params = []
    if start_date:
        conds.append("date(t.date) >= date(?)"); params.append(start_date)
    if end_date:
        conds.append("date(t.date) <= date(?)"); params.append(end_date)
    if account_id:
        conds.append('t.account_id = ?'); params.append(account_id)
    if category_id:
        conds.append('t.category_id = ?'); params.append(category_id)
    if conds:
        q += ' WHERE ' + ' AND '.join(conds)
    q += ' ORDER BY date DESC'
    conn = get_conn(); c = conn.cursor(); c.execute(q, params); rows = c.fetchall(); conn.close()
    df = pd.DataFrame(rows, columns=['id','date','type','amount','account','category','description'])
    return df

# --------------------- Streamlit UI ---------------------

st.set_page_config(page_title='Budget Manager Pro', layout='wide')
# NOTE: For full dark theme, create .streamlit/config.toml with baseTheme = "dark"

init_db()

st.title('💼 Budget Manager Pro — Streamlit (PKR)')

# Sidebar - settings & quick actions
with st.sidebar:
    st.header('Quick Actions')
    if st.button('Add Default Accounts (Cash/Bank)'):
        add_account('Cash'); add_account('Bank'); st.success('Default accounts added')
    if st.button('Seed Default Categories'):
        for cat in ['Food','Transport','Rent','Bills','Salary','Shopping','Misc']:
            add_category(cat)
        st.success('Default categories seeded')
    st.markdown('---')
    st.header('Create')
    new_acc = st.text_input('New Account name')
    if st.button('Create Account') and new_acc:
        add_account(new_acc); st.success(f'Account "{new_acc}" created')
    new_cat = st.text_input('New Category name', key='newcat')
    if st.button('Create Category') and new_cat:
        add_category(new_cat); st.success(f'Category "{new_cat}" created')
    st.markdown('---')
    st.header('Export / Backup')
    if st.button('Export Transactions to Excel'):
        df_all = query_transactions()
        if df_all.empty:
            st.info('No transactions to export')
        else:
            towrite = BytesIO(); df_all.to_excel(towrite, index=False, engine='openpyxl'); towrite.seek(0)
            st.download_button('Download Excel', towrite, file_name='transactions.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    if st.button('Backup DB (.db)'):
        with open(DB_FILE, 'rb') as f:
            data = f.read()
            st.download_button('Download DB', data, file_name=DB_FILE)

# Main layout
col1, col2 = st.columns([1.4, 2.6])

with col1:
    st.subheader('Add Transaction')
    accounts = fetch_accounts()
    cats = fetch_categories()
    acc_options = {name: aid for (aid, name, bal) in accounts}
    cat_options = {name: cid for (cid, name) in cats}

    date = st.date_input('Date', datetime.now())
    ttype = st.selectbox('Type', ['Expense','Income'])
    amount = st.number_input('Amount (PKR)', min_value=0.0, format='%f')
    account_sel = st.selectbox('Account', list(acc_options.keys()))
    category_sel = st.selectbox('Category', list(cat_options.keys()))
    desc = st.text_input('Description')
    if st.button('Save Transaction'):
        if amount <= 0:
            st.error('Amount must be greater than zero')
        else:
            add_transaction(date.strftime('%Y-%m-%d'), ttype, float(amount), acc_options[account_sel], cat_options[category_sel], desc)
            st.success('Transaction saved')

    st.markdown('---')
    st.subheader('Transfer')
    if len(accounts) < 2:
        st.info('Create at least two accounts to transfer')
    else:
        from_acc = st.selectbox('From Account', list(acc_options.keys()), key='from_acc')
        to_acc = st.selectbox('To Account', list(acc_options.keys()), index=1, key='to_acc')
        tr_amt = st.number_input('Amount to transfer (PKR)', min_value=0.0, format='%f', key='tramt')
        if st.button('Transfer Now'):
            if from_acc == to_acc:
                st.error('Select different accounts')
            else:
                ok, msg = transfer_between_accounts(acc_options[from_acc], acc_options[to_acc], float(tr_amt))
                if ok: st.success(msg)
                else: st.error(msg)

with col2:
    st.subheader('Dashboard')
    accounts = fetch_accounts()
    total_balance = sum([b for (_,_,b) in accounts])
    st.metric('Total Balance (PKR)', f'{total_balance:.2f}')
    # show top accounts
    acc_df = pd.DataFrame(accounts, columns=['id','Account','Balance'])
    st.dataframe(acc_df[['Account','Balance']].set_index('Account'))

    st.markdown('---')
    st.subheader('Charts')
    # expenses vs income last 30 days
    end = datetime.now().date()
    start = end.replace(day=1)
    df_30 = query_transactions(start_date=None, end_date=end.strftime('%Y-%m-%d'))
    if not df_30.empty:
        # aggregate
        last_30 = df_30.copy()
        last_30['date'] = pd.to_datetime(last_30['date'])
        # bar: daily income vs expense for last 30 days
        recent = last_30[last_30['date'] >= (end - pd.Timedelta(days=30))]
        if not recent.empty:
            pivot = recent.groupby(['date','type'])['amount'].sum().unstack(fill_value=0)
            fig, ax = plt.subplots(figsize=(8,3))
            pivot.plot(kind='bar', stacked=False, ax=ax)
            ax.set_xlabel('Date')
            ax.set_ylabel('Amount (PKR)')
            ax.legend()
            st.pyplot(fig)
        # pie: category breakdown for expenses last 30 days
        exp_recent = recent[recent['type']=='Expense']
        if not exp_recent.empty:
            pie = exp_recent.groupby('category')['amount'].sum()
            fig2, ax2 = plt.subplots(figsize=(6,4))
            ax2.pie(pie.values, labels=pie.index, autopct='%1.1f%%')
            ax2.set_title('Expense breakdown (last 30 days)')
            st.pyplot(fig2)
    else:
        st.info('No transactions yet — add some to see charts')

st.markdown('---')

# Transactions table and filters
st.subheader('Transactions')
colf1, colf2, colf3 = st.columns(3)
with colf1:
    fd = st.date_input('From', value=None, key='fdate')
with colf2:
    td = st.date_input('To', value=None, key='tdate')
with colf3:
    acc_filter = st.selectbox('Account (Filter)', options=['All'] + [name for (_,name,_) in fetch_accounts()])

cat_filter = st.selectbox('Category (Filter)', options=['All'] + [name for (_,name) in fetch_categories()], index=0)

start_date = fd.strftime('%Y-%m-%d') if fd else None
end_date = td.strftime('%Y-%m-%d') if td else None
acc_id = None if acc_filter == 'All' else [aid for (aid,name,bal) in fetch_accounts() if name==acc_filter][0]
cat_id = None if cat_filter == 'All' else [cid for (cid,name) in fetch_categories() if name==cat_filter][0]

df = query_transactions(start_date=start_date, end_date=end_date, account_id=acc_id, category_id=cat_id)
if df.empty:
    st.info('No matching transactions')
else:
    st.dataframe(df)
    # allow delete / edit actions via simple selection (small workaround)
    sel = st.number_input('Enter transaction id to delete (use value from table) or 0 to skip', min_value=0, step=1, value=0)
    if st.button('Delete Transaction') and sel>0:
        conn = get_conn(); c = conn.cursor(); c.execute('SELECT amount,type,account_id FROM transactions WHERE id=?', (int(sel),)); old = c.fetchone()
        if old:
            amt, ttype, acc = old
            if ttype=='Expense':
                c.execute('UPDATE accounts SET balance = balance + ? WHERE id=?', (amt, acc))
            else:
                c.execute('UPDATE accounts SET balance = balance - ? WHERE id=?', (amt, acc))
            c.execute('DELETE FROM transactions WHERE id=?', (int(sel),))
            conn.commit(); conn.close(); st.success('Deleted')
        else:
            st.error('ID not found')

# Footer instructions
st.markdown('---')
st.info('DB file: budget_streamlit.db — keep it in the same folder. For Streamlit Cloud deploy: push this repo to GitHub with requirements.txt and .streamlit/config.toml (set baseTheme = "dark")')

# --------------------- End of app.py ---------------------
