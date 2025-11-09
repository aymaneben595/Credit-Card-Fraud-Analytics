# 💳 Financial Fraud Analytics & ML Pipeline

---

## 📘 Project Background

This project showcases a complete **end-to-end data analytics and machine learning workflow** focused on **financial fraud detection**, covering every stage from **data ingestion in SQL** and **model development in Python** to **interactive visualization in Power BI**.

It mirrors the real-world operations of a **Risk & Fraud team**, integrating **ETL**, **feature engineering**, **predictive modeling**, and **business intelligence** into one cohesive analytical solution.

### Key KPIs Tracked
* **Total Transactions:** 6M
* **Fraudulent Transactions:** 8K
* **Fraud Rate (%):** 0.13%
* **Total Fraud Loss (USD):** $12bn
* **Model Accuracy:** 98.18%
* **Model Recall (Fraud):** 93.99%
* **AUC-ROC:** 1.00

Insights and results are structured around two main dashboard pages:

1.  **Fraud Overview:** Analyzing KPIs, high-risk transaction types, and risky receivers.
2.  **Model Performance:** Benchmarking models (XGBoost, Random Forest, Logistic Regression) and evaluating model quality.

---

🔗 **SQL ETL Script:** **[View ETL & Feature Engineering (fraud_pipeline.sql)](https://github.com/your-username/your-repo/blob/main/SQL/fraud_pipeline.sql)**

🐍 **Python Modeling Script:** **[View Modeling & BI Export (fraud_ml_pipeline.py)](https://github.com/your-username/your-repo/blob/main/Python/fraud_ml_pipeline.py)**

📊 **Power BI Dashboard:** **[⬇️ Download Fraud Analytics Dashboard.pbix](https://github.com/your-username/your-repo/raw/main/Power%20BI/Dashboard.pbix)**

---

## 🚀 Project Workflow

This project was executed in **three main stages** to move from raw data to a finished intelligence product.

### 1. SQL: ETL & Feature Engineering
* Designed a **PostgreSQL schema** (`fraud`) for analytics.
* Loaded the raw dataset (`PS_2017...csv`) into a `raw_transactions` table.
* Cleaned data by correcting negative balances using `GREATEST(..., 0)`.
* Engineered key analytical features:
    * `balance_delta` (Origin balance change)
    * `balance_change_ratio`
    * `is_merchant`
    * `is_cashout`
    * `is_payment`
    * `is_transfer`
* Created `transactions_clean` table and multiple summary views (e.g., `vw_fraud_by_day`, `vw_fraud_by_type`) for BI.

### 2. Python: Modeling & BI Export
* Loaded the `transactions_clean` table directly from PostgreSQL.
* Addressed extreme class imbalance (0.13% fraud) using model-level weighting (`class_weight='balanced'` and `scale_pos_weight=10`).
* Trained and evaluated three classification models:
    * Logistic Regression
    * Random Forest
    * **XGBoost** (Chosen as best model)
* Generated export-ready CSVs for Power BI:
    * `fraud_by_day.csv`
    * `fraud_by_type.csv`
    * `fraud_by_sender.csv`
    * `fraud_by_receiver.csv`
    * `model_metrics.csv`
    * `confusion_matrix.csv`
    * `transactions_scored.csv` (Main dataset with XGBoost fraud scores)

### 3. Power BI: Visualization
* Integrated the summary CSV outputs into a two-page interactive dashboard.
* Built KPI cards, trend charts, and risk tables for executive insights.
* Structured the report into two pages: **Fraud Overview** and **Model Performance**.

---

## 🧩 Data Pipeline & Feature Engineering

The raw **Kaggle PaySim dataset** was transformed via SQL-based ETL (`fraud_pipeline.sql`):

* **Ingestion:** Loaded `..._log.csv` into `raw_transactions`.
* **Cleaning:** Corrected negative balance values (e.g., `GREATEST(oldbalanceOrg, 0)`).
* **Feature Engineering:** Added boolean flags and balance-change metrics.
    * `balance_delta`
    * `balance_change_ratio`
    * `is_merchant`
    * `is_cashout`
    * `is_payment`
    * `is_transfer`
    * `is_cashin`

✅ Final output: **`fraud.transactions_clean`** — a clean, feature-rich table ready for modeling.

---

## 📈 Executive Summary

### Overview of Findings

From **6 million transactions**, the system identified **8,000 fraudulent cases**, resulting in **$12 billion** in losses. The ML models proved highly effective at identification.

| Metric | Value |
| :--- | :--- |
| **Total Transactions** | 6M |
| **Fraudulent Transactions** | 8K |
| **Fraud Rate (%)** | 0.13% |
| **Total Fraud Loss (USD)** | $12bn |
| **Avg. Fraud Amount (USD)** | $1M |

The **XGBoost** model (selected) achieved:
* **Accuracy:** 98.18%
* **Precision (Fraud):** 0.44
* **Recall (Fraud):** 0.94
* **F1-Score (Fraud):** 0.53
* **ROC-AUC:** 1.00

<p align="center">
  </p>

---

## 🔍 Insights Deep Dive

### **Page 1: Fraud Overview & Risk Analysis**

* **High-Risk Transaction Types:** Fraud is almost exclusively concentrated in **TRANSFER** and **CASH_OUT** transactions. Other types (`CASH_IN`, `DEBIT`, `PAYMENT`) show zero detected fraud.
* **Top Risky Receivers:** The dashboard identifies specific receiver accounts responsible for the largest losses. The top account, `C668046170`, is linked to nearly **$10M** in fraudulent funds.
* **Temporal Trends:** The 'Fraud Trends' line chart shows the fraud rate fluctuating significantly by step/day, peaking at **14.00%** on Day 2. *(See caveat below regarding this metric)*.

<p align="center">
  </p>

---

### **Page 2: Model Performance & Quality**

* **Model Comparison:** The 'Model Comparison' chart shows all three models (XGBoost, Random Forest, Logistic Regression) achieve very high accuracy (near 100%), which is common on imbalanced datasets.
* **Recall is Key:** The most important metric, **Recall (Fraud)**, is **93.99%**. This means the model successfully **catches 94 out of every 100** fraudulent transactions.
* **Precision Trade-off:** The **Precision (Fraud)** is **44.43%**. This indicates that when the model flags a transaction as fraud, it is correct 44% of the time. The remaining 56% are false positives.
* **Confusion Matrix:** The confusion matrix provides a clear breakdown of the model's performance on the test set:
    * **True Positives (Caught Fraud): 1,550**
    * **False Negatives (Missed Fraud): 93**
    * **False Positives (Blocked Legit): 688**
    * **True Negatives (Allowed Legit): 1,270,193**
* **Score Distribution:** The 'Fraud Score Distribution' histogram shows the model is highly effective, assigning a score of `0-0.001` to the vast majority of legitimate (Label 0) transactions.

<p align="center">
  </p>

---

## 💡 Recommendations & Business Actions

1.  **Deploy XGBoost Model:** The model's **94% Recall** and **1.00 AUC-ROC** make it ideal for real-time scoring and fraud prevention.
2.  **Apply Strict Rules to 'TRANSFER' & 'CASH_OUT':** Given these two types account for 100% of fraud, they should be subjected to the new scoring model, lower transaction limits, or multi-factor authentication.
3.  **Investigate Risky Receivers:** Immediately flag and investigate the accounts listed in the 'Top Risky Receivers' table (starting with `C668046170`) to recover funds and prevent further losses.
4.  **Tune for Precision vs. Recall:** The current model is optimized for high recall (catching fraud) at the cost of precision (false positives). The business should evaluate the cost of reviewing the **688 false positives** versus the cost of the **93 missed frauds** to find the optimal balance.

---

## ⚙️ Assumptions & Caveats

* **Data Source:** Data is from the "PaySim" simulator, based on real financial transaction data.
* **'Step / Day' Metric:** The `step` column (representing one hour) was used as a proxy for time. The 'Fraud Trends' chart likely uses `step % 7` or a similar grouping.
* **KPI Discrepancy:** The overall **Fraud Rate is 0.13%** (8K / 6M). The 'Fraud Trends' chart shows rates of 11-14%; this chart likely represents a different metric (e.g., % of total fraud *loss* by day) or a specific, high-risk *subset* of the data, not the overall daily transaction fraud rate.
* **Class Imbalance:** Models were trained using class weighting (`scale_pos_weight`, `class_weight='balanced'`) to manage the extreme 0.13% imbalance.

---

<p align="center">
  <i>Created by [Your Name] — Personal Data Analytics Project (PostgreSQL, Python, Power BI)</i><br>
  <a href="mailto:your.email@gmail.com">your.email@gmail.com</a>
</p>
