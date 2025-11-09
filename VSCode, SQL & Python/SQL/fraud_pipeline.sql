-- ============================================================
-- 💳 CREDIT CARD FRAUD PIPELINE — FINAL VERSION
-- ============================================================

-- ============================================================
-- ✅ 1. Create schema and set context
-- ============================================================

CREATE SCHEMA IF NOT EXISTS fraud;
SET search_path TO fraud;

-- ============================================================
-- ✅ 2. Import raw dataset (CSV → Postgres table)
-- ============================================================

DROP TABLE IF EXISTS raw_transactions;

CREATE TABLE raw_transactions (
    step INTEGER,
    type VARCHAR(20),
    amount NUMERIC(18,2),
    nameOrig VARCHAR(50),
    oldbalanceOrg NUMERIC(18,2),
    newbalanceOrig NUMERIC(18,2),
    nameDest VARCHAR(50),
    oldbalanceDest NUMERIC(18,2),
    newbalanceDest NUMERIC(18,2),
    isFraud INTEGER,
    isFlaggedFraud INTEGER
);

-- ⚠️ Adjust this file path to match your system
COPY raw_transactions
FROM 'C:\Users\ayman\OneDrive\Desktop\New folder (3)\VSCode, SQL & Python\CSV\PS_20174392719_1491204439457_log.csv'
DELIMITER ',' CSV HEADER;

-- ============================================================
-- ✅ 3. Create CLEAN table (fix types, remove negatives)
-- ============================================================

DROP TABLE IF EXISTS transactions_clean;

CREATE TABLE transactions_clean AS
SELECT
    step,
    type,
    amount,
    nameOrig,
    GREATEST(oldbalanceOrg, 0) AS oldbalanceOrg,
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

ALTER TABLE transactions_clean
ADD COLUMN IF NOT EXISTS balance_delta NUMERIC,
ADD COLUMN IF NOT EXISTS balance_change_ratio NUMERIC,
ADD COLUMN IF NOT EXISTS is_merchant BOOLEAN,
ADD COLUMN IF NOT EXISTS is_cashout BOOLEAN,
ADD COLUMN IF NOT EXISTS is_payment BOOLEAN,
ADD COLUMN IF NOT EXISTS is_transfer BOOLEAN,
ADD COLUMN IF NOT EXISTS is_cashin BOOLEAN;

UPDATE transactions_clean
SET
    balance_delta = newbalanceOrig - oldbalanceOrg,
    balance_change_ratio = CASE 
        WHEN oldbalanceOrg = 0 THEN 0
        ELSE (newbalanceOrig - oldbalanceOrg) / oldbalanceOrg
    END,
    is_merchant = (nameDest LIKE 'M%' OR nameDest LIKE 'C%'),
    is_cashout = (type = 'CASH_OUT'),
    is_payment = (type = 'PAYMENT'),
    is_transfer = (type = 'TRANSFER'),
    is_cashin = (type = 'CASH_IN');

-- ============================================================
-- ✅ 5. Create summary views for Power BI
-- ============================================================

-- 🗓️ Fraud by day
DROP VIEW IF EXISTS vw_fraud_by_day;
CREATE VIEW vw_fraud_by_day AS
SELECT
    step,
    COUNT(*) AS total_txn,
    SUM(isFraud) AS fraud_txn,
    AVG(isFraud)::FLOAT AS fraud_rate,
    SUM(CASE WHEN isFraud = 1 THEN amount ELSE 0 END) AS fraud_loss
FROM transactions_clean
GROUP BY step
ORDER BY step;

-- 💳 Fraud by transaction type
DROP VIEW IF EXISTS vw_fraud_by_type;
CREATE VIEW vw_fraud_by_type AS
SELECT
    type,
    COUNT(*) AS total_txn,
    SUM(isFraud) AS fraud_txn,
    AVG(isFraud)::FLOAT AS fraud_rate,
    SUM(CASE WHEN isFraud = 1 THEN amount ELSE 0 END) AS fraud_loss
FROM transactions_clean
GROUP BY type
ORDER BY type;

-- 👥 Top 20 origins causing fraud
DROP VIEW IF EXISTS vw_fraud_by_origin;
CREATE VIEW vw_fraud_by_origin AS
SELECT
    nameOrig,
    SUM(amount) AS fraud_loss
FROM transactions_clean
WHERE isFraud = 1
GROUP BY nameOrig
ORDER BY fraud_loss DESC
LIMIT 20;

-- 🧾 User-level summary (for drillthrough)
DROP VIEW IF EXISTS vw_user_summary;
CREATE VIEW vw_user_summary AS
SELECT 
    nameOrig,
    COUNT(*) AS total_txn,
    SUM(isFraud) AS fraud_txn,
    AVG(isFraud)::FLOAT AS fraud_rate,
    AVG(amount)::FLOAT AS avg_amount,
    SUM(amount)::FLOAT AS total_amount,
    SUM(CASE WHEN isFraud = 1 THEN amount ELSE 0 END) AS fraud_loss
FROM transactions_clean
GROUP BY nameOrig;

-- ============================================================
-- ✅ DONE — All tables and views created under schema "fraud"
-- ============================================================

-- You can verify with:
--   \dn+ fraud
--   \dt fraud.*
