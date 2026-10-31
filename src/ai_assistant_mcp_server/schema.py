"""SQLite schema for the synthetic company.

One database holds four industries, each with the kinds of fields attackers go for.
Tables whose name starts with _lab_ are the answer key for the demos (which records
are canaries or carry injection payloads); the MCP server should not expose them.
"""

SCHEMA = """
-- healthcare ---------------------------------------------------------------
CREATE TABLE healthcare_patients (
    id INTEGER PRIMARY KEY,
    mrn TEXT NOT NULL,
    full_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    ssn TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    insurance_provider TEXT NOT NULL,
    insurance_id TEXT NOT NULL
);
CREATE TABLE healthcare_visits (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES healthcare_patients(id),
    visit_date TEXT NOT NULL,
    physician TEXT NOT NULL,
    diagnosis_code TEXT NOT NULL,
    diagnosis TEXT NOT NULL,
    notes TEXT NOT NULL
);
CREATE TABLE healthcare_prescriptions (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES healthcare_patients(id),
    drug TEXT NOT NULL,
    dose TEXT NOT NULL,
    prescriber TEXT NOT NULL
);

-- banking -------------------------------------------------------------------
CREATE TABLE banking_customers (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    ssn TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    online_username TEXT NOT NULL,
    online_password TEXT NOT NULL,     -- legacy system stores these in plain text
    security_question TEXT NOT NULL,
    security_answer TEXT NOT NULL
);
CREATE TABLE banking_accounts (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES banking_customers(id),
    account_number TEXT NOT NULL,
    routing_number TEXT NOT NULL,
    account_type TEXT NOT NULL,
    balance_cents INTEGER NOT NULL
);
CREATE TABLE banking_cards (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES banking_customers(id),
    card_number TEXT NOT NULL,
    expiry TEXT NOT NULL,
    cvv TEXT NOT NULL,
    pin TEXT NOT NULL
);
CREATE TABLE banking_transactions (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES banking_accounts(id),
    posted_at TEXT NOT NULL,
    amount_cents INTEGER NOT NULL,
    description TEXT NOT NULL
);

-- manufacturing -----------------------------------------------------------
CREATE TABLE mfg_suppliers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    bank_account TEXT NOT NULL,
    bank_routing TEXT NOT NULL,
    payment_terms TEXT NOT NULL
);
CREATE TABLE mfg_parts (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    unit_cost_cents INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL REFERENCES mfg_suppliers(id),
    trade_secret INTEGER NOT NULL DEFAULT 0
);

-- technology / internal IT -------------------------------------------------
CREATE TABLE tech_employees (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    ssn TEXT NOT NULL,
    salary INTEGER NOT NULL,
    title TEXT NOT NULL,
    department TEXT NOT NULL,
    manager_id INTEGER,
    home_address TEXT NOT NULL
);
CREATE TABLE tech_credentials (
    id INTEGER PRIMARY KEY,
    system TEXT NOT NULL,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    api_key TEXT NOT NULL,
    notes TEXT NOT NULL
);
CREATE TABLE tech_tickets (
    id INTEGER PRIMARY KEY,
    created_by INTEGER NOT NULL REFERENCES tech_employees(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL
);

-- answer key for the demos (not for the MCP server to expose) --------------
CREATE TABLE _lab_canaries (
    kind TEXT NOT NULL,
    value TEXT NOT NULL,
    location TEXT NOT NULL
);
CREATE TABLE _lab_poisoned (
    table_name TEXT NOT NULL,
    row_id INTEGER NOT NULL,
    column_name TEXT NOT NULL,
    payload_kind TEXT NOT NULL
);
"""
