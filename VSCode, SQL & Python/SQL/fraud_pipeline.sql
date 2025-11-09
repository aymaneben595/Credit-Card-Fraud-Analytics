-- ============================================================
-- 💳 CREDIT CARD FRAUD PIPELINE — FINAL VERSION
-- ============================================================

-- ============================================================
-- ✅ 1. Create schema and set context
-- ============================================================

-- "Schema" = a folder inside the database where we organize related tables and views.
-- Here we create a new schema called "fraud" (if it doesn’t already exist)
-- and tell PostgreSQL to use it for all the upcoming work.

CREATE SCHEMA IF NOT EXISTS fraud;
SET search_path TO fraud;

-- ============================================================
-- ✅ 2. Import raw dataset (CSV → Postgres table)
-- ============================================================

-- We start by removing any old version of the same table, to avoid conflicts.
DROP TABLE IF EXISTS raw_transactions;

-- We create a new table called "raw_transactions" to store the raw data
-- exactly as it appears in the CSV file (one row per transaction).
CREATE TABLE raw_transactions (
    step INTEGER,                    -- Time step (like a day or an hour number)
    type VARCHAR(20),                -- Transaction type (e.g., TRANSFER, CASH_OUT)
    amount NUMERIC(18,2),            -- Amount of money moved
    nameOrig VARCHAR(50),            -- ID of the account sending money
    oldbalanceOrg NUMERIC(18,2),     -- Sender’s balance before transaction
    newbalanceOrig NUMERIC(18,2),    -- Sender’s balance after transaction
    nameDest VARCHAR(50),            -- ID of the account receiving money
    oldbalanceDest NUMERIC(18,2),    -- Receiver’s balance before transaction
    newbalanceDest NUMERIC(18,2),    -- Receiver’s balance after transaction
    isFraud INTEGER,                 -- 1 if transaction is fraudulent, 0 if not
    isFlaggedFraud INTEGER           -- 1 if system flagged it as suspicious
);

-- This command loads the CSV file into the table above.
-- ⚠️ You may need to change the file path to match where your CSV file is located.
COPY raw_transactions
FROM 'C:\Users\ayman\OneDrive\Desktop\New folder (3)\VSCode, SQL & Python\CSV\PS_20174392719_1491204439457_log.csv'
DELIMITER ',' CSV HEADER;

-- ============================================================
-- ✅ 3. Create CLEAN table (fix types, remove negatives)
-- ============================================================

-- We make a cleaned version of the raw data.
-- Negative balances don’t make sense, so we replace them with 0.
-- The cleaned data is stored in a new table called "transactions_clean".
DROP TABLE IF EXISTS transactions_clean;

CREATE TABLE transactions_clean AS
SELECT
    step,
    type,
    amount,
    nameOrig,
    GREATEST(oldbalanceOrg, 0) AS oldbalanceOrg,        -- Replace negatives with 0
    GREATEST(newbalanceOrig, 0) AS newbalanceOrig,
    nameDest,
    GREATEST(oldbalanceDest, 0) AS oldbalanceDest,
    GREATEST(newbalanceDest, 0) AS newbalanceDest,
    isFraud,
    isFlaggedFraud
FROM raw_transactions;

-- ============================================================
-- ✅ 4. Add engineered features
-- ============================================================

-- We now add extra columns that will help us analyze fraud patterns later.
-- These are *new calculated features* that didn’t exist in the original data.
ALTER TABLE transactions_clean
ADD COLUMN IF NOT EXISTS balance_delta NUMERIC,          -- Change in sender’s balance
ADD COLUMN IF NOT EXISTS balance_change_ratio NUMERIC,   -- % change in sender’s balance
ADD COLUMN IF NOT EXISTS is_merchant BOOLEAN,            -- Whether receiver looks like a merchant
ADD COLUMN IF NOT EXISTS is_cashout BOOLEAN,             -- True if transaction is CASH_OUT
ADD COLUMN IF NOT EXISTS is_payment BOOLEAN,             -- True if transaction is PAYMENT
ADD COLUMN IF NOT EXISTS is_transfer BOOLEAN,            -- True if transaction is TRANSFER
ADD COLUMN IF NOT EXISTS is_cashin BOOLEAN;              -- True if transaction is CASH_IN

-- Fill these new columns with actual values based on logic.
UPDATE transactions_clean
SET
    balance_delta = newbalanceOrig - oldbalanceOrg,        -- Money lost or gained
    balance_change_ratio = CASE 
        WHEN oldbalanceOrg = 0 THEN 0                     -- Avoid dividing by zero
        ELSE (newbalanceOrig - oldbalanceOrg) / oldbalanceOrg
    END,
    is_merchant = (nameDest LIKE 'M%' OR nameDest LIKE 'C%'), -- Merchant names often start with M or C
    is_cashout = (type = 'CASH_OUT'),
    is_payment = (type = 'PAYMENT'),
    is_transfer = (type = 'TRANSFER'),
    is_cashin = (type = 'CASH_IN');

-- ============================================================
-- ✅ 5. Create summary views for Power BI
-- ============================================================

-- These "views" act like pre-built reports.
-- They help Power BI (or other dashboards) get summarized data easily.

-- 🗓️ View 1: Fraud by day (step)
DROP VIEW IF EXISTS vw_fraud_by_day;
CREATE VIEW vw_fraud_by_day AS
SELECT
    step,                                                -- Time step
    COUNT(*) AS total_txn,                               -- Total number of transactions that day
    SUM(isFraud) AS fraud_txn,                           -- Number of fraud cases
    AVG(isFraud)::FLOAT AS fraud_rate,                   -- Fraud percentage
    SUM(CASE WHEN isFraud = 1 THEN amount ELSE 0 END) AS fraud_loss  -- Total money lost to fraud
FROM transactions_clean
GROUP BY step
ORDER BY step;

-- 💳 View 2: Fraud by transaction type
DROP VIEW IF EXISTS vw_fraud_by_type;
CREATE VIEW vw_fraud_by_type AS
SELECT
    type,                                                -- Transaction type
    COUNT(*) AS total_txn,
    SUM(isFraud) AS fraud_txn,
    AVG(isFraud)::FLOAT AS fraud_rate,
    SUM(CASE WHEN isFraud = 1 THEN amount ELSE 0 END) AS fraud_loss
FROM transactions_clean
GROUP BY type
ORDER BY type;

-- 👥 View 3: Top 20 origins causing the most fraud
DROP VIEW IF EXISTS vw_fraud_by_origin;
CREATE VIEW vw_fraud_by_origin AS
SELECT
    nameOrig,                                            -- Sender’s ID
    SUM(amount) AS fraud_loss                            -- Total fraudulent amount sent
FROM transactions_clean
WHERE isFraud = 1
GROUP BY nameOrig
ORDER BY fraud_loss DESC
LIMIT 20;

-- 🧾 View 4: User-level summary (for drill-down analysis)
DROP VIEW IF EXISTS vw_user_summary;
CREATE VIEW vw_user_summary AS
SELECT 
    nameOrig,
    COUNT(*) AS total_txn,                               -- Total number of transactions
    SUM(isFraud) AS fraud_txn,                           -- Number of frauds
    AVG(isFraud)::FLOAT AS fraud_rate,                   -- % of transactions that were fraud
    AVG(amount)::FLOAT AS avg_amount,                    -- Average transaction size
    SUM(amount)::FLOAT AS total_amount,                  -- Total money moved
    SUM(CASE WHEN isFraud = 1 THEN amount ELSE 0 END) AS fraud_loss
FROM transactions_clean
GROUP BY nameOrig;

-- ============================================================
-- ✅ DONE — All tables and views created under schema "fraud"
-- ============================================================

-- To check your schema and tables in PostgreSQL:
--   \dn+ fraud      → shows schema details
--   \dt fraud.*     → lists all tables and views inside "fraud"
