-- The Python loader supplies a validated temporary incoming table in this transaction.
CREATE SCHEMA IF NOT EXISTS fraud;
CREATE TABLE IF NOT EXISTS fraud.raw_transactions (LIKE incoming INCLUDING CONSTRAINTS);
TRUNCATE fraud.raw_transactions;
INSERT INTO fraud.raw_transactions
    (step,type,amount,nameorig,oldbalanceorg,newbalanceorig,namedest,oldbalancedest,newbalancedest,isfraud,isflaggedfraud)
SELECT * FROM incoming;

CREATE OR REPLACE VIEW fraud.vw_clean_input AS
SELECT r.*, newbalanceorig-oldbalanceorg AS balance_delta,
       (newbalanceorig-oldbalanceorg)/nullif(oldbalanceorg,0) AS balance_change_ratio,
       namedest LIKE 'M%' AS is_merchant, type='CASH_OUT' AS is_cashout,
       type='PAYMENT' AS is_payment, type='TRANSFER' AS is_transfer, type='CASH_IN' AS is_cashin
FROM fraud.raw_transactions r;

-- Older installations materialized this relation. Refresh it without dropping dependent views.
DO $$
BEGIN
    IF to_regclass('fraud.transactions_clean') IS NULL THEN
        CREATE VIEW fraud.transactions_clean AS SELECT * FROM fraud.vw_clean_input;
    ELSIF (SELECT relkind FROM pg_class WHERE oid='fraud.transactions_clean'::regclass)='r' THEN
        TRUNCATE fraud.transactions_clean;
        INSERT INTO fraud.transactions_clean SELECT * FROM fraud.vw_clean_input;
    ELSE
        CREATE OR REPLACE VIEW fraud.transactions_clean AS SELECT * FROM fraud.vw_clean_input;
    END IF;
END $$;

CREATE OR REPLACE VIEW fraud.vw_activity AS
SELECT (step-1)/24+1 AS simulation_day, type, count(*) AS transactions,
       sum(isfraud) AS fraud_cases, sum(CASE WHEN isfraud=1 THEN amount ELSE 0 END) AS fraud_amount
FROM fraud.transactions_clean GROUP BY 1,2;

-- Keep the previous aggregate interfaces. Their rates are fractions, their amounts are in simulation units.
CREATE OR REPLACE VIEW fraud.vw_fraud_by_day AS
SELECT simulation_day AS step, sum(transactions)::bigint AS total_txn, sum(fraud_cases)::bigint AS fraud_txn,
       sum(fraud_cases)::double precision/sum(transactions)::double precision AS fraud_rate, sum(fraud_amount) AS fraud_loss
FROM fraud.vw_activity GROUP BY simulation_day;
CREATE OR REPLACE VIEW fraud.vw_fraud_by_type AS
SELECT type, sum(transactions)::bigint AS total_txn, sum(fraud_cases)::bigint AS fraud_txn,
       sum(fraud_cases)::double precision/sum(transactions)::double precision AS fraud_rate, sum(fraud_amount) AS fraud_loss
FROM fraud.vw_activity GROUP BY type;
CREATE OR REPLACE VIEW fraud.vw_fraud_by_origin AS
SELECT nameorig, sum(amount) AS fraud_loss FROM fraud.transactions_clean WHERE isfraud=1
GROUP BY nameorig ORDER BY fraud_loss DESC, nameorig LIMIT 20;
CREATE OR REPLACE VIEW fraud.vw_user_summary AS
SELECT nameorig, count(*) AS total_txn, sum(isfraud) AS fraud_txn, avg(isfraud)::double precision AS fraud_rate,
       avg(amount)::double precision AS avg_amount, sum(amount)::double precision AS total_amount,
       sum(CASE WHEN isfraud=1 THEN amount ELSE 0 END) AS fraud_loss
FROM fraud.transactions_clean GROUP BY nameorig;
