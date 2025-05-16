import streamlit as st
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime

# --- Database configuration ---
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'PhantomSlayers15042005',
    'database': 'BankingDB'
}

# --- Helper functions ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn, conn.cursor(dictionary=True)
    except mysql.connector.Error as err:
        st.error(f"Database connection error: {err}")
        st.stop()

def get_all_accounts():
    conn, cursor = get_db_connection()
    cursor.execute("SELECT AccountID FROM Accounts")
    rows = cursor.fetchall()        # ← actually pull the results
    cursor.close()
    conn.close()
    return rows                   # list of dicts, e.g. [{ 'AccountID': 1 }, …]

# Ensure default branches exist
def ensure_default_branches():
    conn, cursor = get_db_connection()
    cursor.execute("SELECT COUNT(*) AS cnt FROM Branches")
    if cursor.fetchone()['cnt'] == 0:
        default = [
            ('Downtown Branch', '123 Main St'),
            ('Uptown Branch', '456 North Ave'),
            ('Suburban Branch', '789 Elm Rd')
        ]
        cursor.executemany(
            "INSERT INTO Branches (BranchName, Address) VALUES (%s, %s)", default
        )
        conn.commit()
    cursor.close()
    conn.close()

# Ensure EmployeeCredentials table exists
def ensure_employee_credentials_table():
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS EmployeeCredentials (
            EmployeeID INT PRIMARY KEY,
            Username VARCHAR(50) UNIQUE,
            Password VARCHAR(255),
            LastLogin DATETIME,
            IsLocked BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID)
        )
        """
    )
    conn.commit()
    cursor.close()
    conn.close()

# Predefined positions
POSITIONS = ['Teller', 'Manager', 'Cashier', 'Loan Officer', 'Customer Service']

# Load branches for selection
@st.cache_data
def load_branches():
    conn, cursor = get_db_connection()
    cursor.execute("SELECT BranchID, BranchName FROM Branches")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# ─── NEW HELPER: transfer funds ──────────────────────────────────────────────
def transfer_funds(from_acct, to_acct, amount):
    conn, cursor = get_db_connection()
    try:
        # 1) check balance
        cursor.execute(
            "SELECT Balance FROM Accounts WHERE AccountID=%s",
            (from_acct,)
        )
        bal = cursor.fetchone()['Balance']
        if bal < amount:
            st.error("❌ Insufficient funds.")
            return

        # 2) debit source
        cursor.execute(
            "UPDATE Accounts SET Balance = Balance - %s WHERE AccountID=%s",
            (amount, from_acct)
        )
        cursor.execute(
            """
            INSERT INTO Transactions
              (AccountID, TransactionDate, Amount, TransactionType, TransactionInfo)
            VALUES
              (%s, NOW(), %s, 'transfer_out', %s)
            """,
            (from_acct, amount, f"To {to_acct}")
        )

        # 3) credit destination
        cursor.execute(
            "UPDATE Accounts SET Balance = Balance + %s WHERE AccountID=%s",
            (amount, to_acct)
        )
        cursor.execute(
            """
            INSERT INTO Transactions
              (AccountID, TransactionDate, Amount, TransactionType, TransactionInfo)
            VALUES
              (%s, NOW(), %s, 'transfer_in', %s)
            """,
            (to_acct, amount, f"From {from_acct}")
        )

        # 4) commit once at the end
        conn.commit()
        st.success(f"✅ Transferred {amount:.2f} from {from_acct} → {to_acct}")
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Transfer failed: {e}")
    finally:
        cursor.close()
        conn.close()

# ─── NEW HELPER: get transaction log ────────────────────────────────────────
def get_transaction_log(customer_id):
    conn, cursor = get_db_connection()
    cursor.execute(
        """
        SELECT
          t.TransactionID,
          t.AccountID,
          t.TransactionDate,
          t.Amount,
          t.TransactionType,
          t.TransactionInfo
        FROM Transactions t
        JOIN Accounts a ON t.AccountID = a.AccountID
        WHERE a.CustomerID = %s
        ORDER BY t.TransactionDate DESC
        """,
        (customer_id,)
    )
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# --- Authentication & session state ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_type = None  # 'customer' or 'employee'
    st.session_state.customer_id = None
    st.session_state.customer_name = None
    st.session_state.employee_id = None
    st.session_state.employee_name = None
    st.session_state.branch_id = None

# --- Registration / Login functions (unchanged) ---
def register_customer(name, phone, address, username, password):
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            "INSERT INTO Customers (CustomerName, PhoneNumber, Address) VALUES (%s,%s,%s)",
            (name, phone, address)
        )
        cust_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO LoginCredentials (CustomerID, Username, Password) VALUES (%s,%s,%s)",
            (cust_id, username, password)
        )
        conn.commit()
        st.success(f"Customer registered! ID: {cust_id}")
    except Exception as e:
        conn.rollback()
        st.error(f"Customer registration failed: {e}")
    finally:
        cursor.close()
        conn.close()


def register_employee(name, position, branch_id, username, password):
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            "INSERT INTO Employees (EmployeeName, Position, BranchID) VALUES (%s,%s,%s)",
            (name, position, branch_id)
        )
        emp_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO EmployeeCredentials (EmployeeID, Username, Password) VALUES (%s,%s,%s)",
            (emp_id, username, password)
        )
        conn.commit()
        st.success(f"Employee registered! ID: {emp_id}")
    except Exception as e:
        conn.rollback()
        st.error(f"Employee registration failed: {e}")
    finally:
        cursor.close()
        conn.close()

def login_customer(username, password):
    conn, cursor = get_db_connection()
    cursor.execute(
        "SELECT lc.CustomerID, c.CustomerName "
        "FROM LoginCredentials lc "
        "JOIN Customers c ON lc.CustomerID=c.CustomerID "
        "WHERE lc.Username=%s AND lc.Password=%s AND lc.IsLocked=FALSE",
        (username, password)
    )
    row = cursor.fetchone()
    if row:
        st.session_state.logged_in = True
        st.session_state.user_type = 'customer'
        st.session_state.customer_id = row['CustomerID']
        st.session_state.customer_name = row['CustomerName']
        cursor.execute(
            "UPDATE LoginCredentials SET LastLogin=%s WHERE CustomerID=%s",
            (datetime.now(), row['CustomerID'])
        )
        conn.commit()
        st.success(f"Welcome, {row['CustomerName']} (Customer)!")
    else:
        st.error("Customer login failed.")
    cursor.close()
    conn.close()


def login_employee(username, password):
    conn, cursor = get_db_connection()
    cursor.execute(
        "SELECT ec.EmployeeID, e.EmployeeName, e.BranchID "
        "FROM EmployeeCredentials ec "
        "JOIN Employees e ON ec.EmployeeID=e.EmployeeID "
        "WHERE ec.Username=%s AND ec.Password=%s AND ec.IsLocked=FALSE",
        (username, password)
    )
    row = cursor.fetchone()
    if row:
        st.session_state.logged_in = True
        st.session_state.user_type = 'employee'
        st.session_state.employee_id = row['EmployeeID']
        st.session_state.employee_name = row['EmployeeName']
        st.session_state.branch_id = row['BranchID']
        cursor.execute(
            "UPDATE EmployeeCredentials SET LastLogin=%s WHERE EmployeeID=%s",
            (datetime.now(), row['EmployeeID'])
        )
        conn.commit()
        st.success(f"Welcome, {row['EmployeeName']} (Employee, Branch {row['BranchID']})!")
    else:
        st.error("Employee login failed.")
    cursor.close()
    conn.close()

# --- Account operations for customers (unchanged) ---
def list_accounts():
    cid = st.session_state.customer_id
    conn, cursor = get_db_connection()
    cursor.execute(
        "SELECT AccountID, Balance FROM Accounts WHERE CustomerID=%s",
        (cid,)
    )
    accounts = cursor.fetchall()
    cursor.close()
    conn.close()
    return accounts

# Open account
def open_account(initial):
    cid = st.session_state.customer_id
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            "INSERT INTO Accounts (CustomerID, Balance, OpenDate) VALUES (%s,%s,%s)",
            (cid, initial, datetime.today().date())
        )
        conn.commit()
        st.success(f"Account opened: {cursor.lastrowid} (Balance: {initial:.2f})")
    except Exception as e:
        conn.rollback()
        st.error(f"Failed to open account: {e}")
    finally:
        cursor.close()
        conn.close()
        
# Deposit
def deposit(account_id, amount):
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            "UPDATE Accounts SET Balance = Balance + %s WHERE AccountID = %s",
            (amount, account_id)
        )
        cursor.execute(
            """INSERT INTO Transactions
               (AccountID, TransactionDate, Amount, TransactionType, TransactionInfo)
               VALUES (%s, NOW(), %s, 'deposit', 'Deposit via Streamlit')""",
            (account_id, amount)
        )
        conn.commit()
        st.success(f"✅  Deposited {amount:.2f} to account {account_id}")
    except Exception as e:
        conn.rollback()
        st.error(f"❌  Deposit failed: {e}")
    finally:
        cursor.close()
        conn.close()

# Withdraw
def withdraw(account_id, amount):
    conn, cursor = get_db_connection()
    try:
        cursor.execute(
            "SELECT Balance FROM Accounts WHERE AccountID = %s",
            (account_id,)
        )
        bal = cursor.fetchone()['Balance']
        if bal < amount:
            st.error("❌  Insufficient funds.")
        else:
            cursor.execute(
                "UPDATE Accounts SET Balance = Balance - %s WHERE AccountID = %s",
                (amount, account_id)
            )
            cursor.execute(
                """INSERT INTO Transactions
                   (AccountID, TransactionDate, Amount, TransactionType, TransactionInfo)
                   VALUES (%s, NOW(), %s, 'withdraw', 'Withdrawal via Streamlit')""",
                (account_id, amount)
            )
            conn.commit()
            st.success(f"✅  Withdrew {amount:.2f} from account {account_id}")
    except Exception as e:
        conn.rollback()
        st.error(f"❌  Withdrawal failed: {e}")
    finally:
        cursor.close()
        conn.close()        

# --- Employee dashboard function (unchanged) ---
def list_all_customers():
    conn, cursor = get_db_connection()
    cursor.execute(
        "SELECT c.CustomerID, c.CustomerName, a.AccountID, a.Balance "
        "FROM Customers c LEFT JOIN Accounts a ON c.CustomerID=a.CustomerID "
        "ORDER BY c.CustomerID"
    )
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# --- Streamlit App Layout ---
ensure_default_branches()
ensure_employee_credentials_table()
branches = load_branches()

st.title("Banking Management System")

menu = ["Home", "Register", "Login"]
if st.session_state.logged_in:
    if st.session_state.user_type == 'customer':
        menu += [
            "Open account",
            "Deposit",
            "Withdraw",
            "View my accounts",
            "Transfer Funds",       # ← added
            "Transaction Log"       # ← added
        ]
    else:
        menu += ["List customers & accounts"]

choice = st.sidebar.selectbox("Menu", menu)

# Home
if choice == "Home":
    st.write("Welcome to the banking system.")

# Register / Login (keep your existing handlers)...
elif choice == "Register":
    st.subheader("Register")
    user_type = st.radio("Register as", ["Customer", "Employee"])
    if user_type == "Customer":
        name = st.text_input("Name")
        phone = st.text_input("Phone")
        address = st.text_input("Address")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Register Customer"):
            register_customer(name, phone, address, username, password)
    else:
        name = st.text_input("Employee Name")
        position = st.selectbox("Position", POSITIONS)
        branch_map = {b['BranchName']: b['BranchID'] for b in branches}
        branch_sel = st.selectbox("Branch", list(branch_map.keys()))
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Register Employee"):
            register_employee(name, position, branch_map[branch_sel], username, password)

elif choice == "Login":
    st.subheader("Login")
    user_type = st.radio("Login as", ["Customer", "Employee"])
    username = st.text_input("Username", key="login_user")
    password = st.text_input("Password", type="password", key="login_pass")
    if st.button("Login"):
        if user_type == 'Customer':
            login_customer(username, password)
        else:
            login_employee(username, password)

# Customer pages
elif choice == "Open account":
    st.subheader("Open Account")
    initial = st.number_input("Initial deposit", min_value=0.0)
    if st.button("Open"):
        open_account(initial)

elif choice == "Deposit":
    st.subheader("Deposit")
    accounts = list_accounts()
    if accounts:
        acct_id = st.selectbox("Account", [a['AccountID'] for a in accounts])
        amt = st.number_input("Amount", min_value=0.0, format="%.2f")
        if st.button("Deposit Funds"):
            deposit(acct_id, amt)
    else:
        st.info("No accounts to deposit into.")

elif choice == "Withdraw":
    st.subheader("Withdraw")
    accounts = list_accounts()
    if accounts:
        acct_id = st.selectbox("Account", [a['AccountID'] for a in accounts])
        amt = st.number_input("Amount", min_value=0.0, format="%.2f")
        if st.button("Withdraw Funds"):
            withdraw(acct_id, amt)
    else:
        st.info("No accounts to withdraw from.")

elif choice == "View my accounts":
    st.subheader("My Accounts")
    st.table(list_accounts())

elif choice == "Transfer Funds":
    st.subheader("Transfer Between Accounts")
    # fetch only _your_ accounts to debit from
    your_accts = list_accounts()  
    if not your_accts:
        st.info("You have no accounts to transfer from.")
    else:
        from_opts = [f"{a['AccountID']} (Bal: {a['Balance']:.2f})"
                     for a in your_accts]
        sel_from = st.selectbox("From account", from_opts)
        from_id   = int(sel_from.split()[0])

        # fetch **all** accounts to credit to
        all_accts = get_all_accounts()
        to_opts   = [str(r['AccountID']) for r in all_accts]
        sel_to    = st.selectbox("To account", to_opts)
        to_id     = int(sel_to)

        amount = st.number_input("Amount to transfer", min_value=0.0, format="%.2f")
        if st.button("Execute Transfer"):
            if from_id == to_id:
                st.error("Cannot transfer to the same account.")
            else:
                transfer_funds(from_id, to_id, amount)

elif choice == "Transaction Log":  # ← new section
    st.subheader("Your Transaction History")
    log = get_transaction_log(st.session_state.customer_id)
    if log:
        st.table(log)
    else:
        st.info("No transactions found.")

# Employee page
elif choice == "List customers & accounts":
    st.subheader("All customers and their accounts")
    data = list_all_customers()
    st.dataframe(data)
