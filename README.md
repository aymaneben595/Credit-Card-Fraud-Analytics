# 💰 Credit Card Fraud Analytics & Machine Learning Pipeline

---

## 📘 Project Background

This project presents a **realistic end-to-end fraud analytics workflow**, starting from **raw transactional data** and progressing all the way to **machine learning–driven insights** and **Power BI visualization**.  

The goal is to mirror the day-to-day responsibilities of a **Risk & Fraud Automation analyst** — cleaning and transforming raw data in **PostgreSQL**, building predictive models in **Python**, and designing an **executive dashboard in Power BI** that helps detect and prevent fraudulent activity in real time.

### Key KPIs
- **Total Transactions:** 6M  
- **Fraudulent Transactions:** 8K  
- **Fraud Rate:** 0.13%  
- **Model Accuracy:** 98.18%  
- **AUC-ROC:** 1.00  

The project revolves around two interactive dashboard pages:
1. **Fraud Overview:** Key KPIs, fraud trends, and risky entities  
2. **Model Performance:** Machine learning results and quality metrics  

---

🔗 **SQL ETL Script:**  
[View ETL & Feature Engineering (fraud_pipeline.sql)](https://github.com/aymaneben595/Fourth-Project/blob/bd76a24d22c246dc9a47d61312253e47d6659e4a/VSCode%2C%20SQL%20%26%20Python/SQL/fraud_pipeline.sql)

🐍 **Python Modeling Script:**  
[View Modeling & BI Export (fraud_pipeline.py)](https://github.com/aymaneben595/Fourth-Project/blob/bd76a24d22c246dc9a47d61312253e47d6659e4a/VSCode%2C%20SQL%20%26%20Python/Python/fraud_pipeline.py)

📊 **Power BI Dashboard:**  
[⬇️ Download Power BI Report (Fraud Analytics.pbix)](https://github.com/aymaneben595/Fraud-Analytics-Pipeline/raw/24ebc3b479ec05239e1eadf063bc0a072991e80a/Power%20Bi/Dashboard.pbix)

---

## 🚀 Workflow Overview

The pipeline follows a **three-stage structure**, mirroring what’s used in fintech and risk analytics teams.

### 1️⃣ SQL: ETL & Feature Engineering  
- Created a dedicated `fraud` schema in PostgreSQL.  
- Ingested the Kaggle PaySim dataset into a `raw_transactions` table.  
- Cleaned and transformed the data, correcting negative balances and data types.  
- Engineered analytical features:
  - `balance_delta`, `balance_change_ratio`  
  - Transaction type flags: `is_cashout`, `is_payment`, `is_transfer`, etc.  
- Produced multiple summarized views for Power BI (e.g., `vw_fraud_by_day`, `vw_fraud_by_type`, `vw_user_summary`).

### 2️⃣ Python: Machine Learning & Data Exports  
- Loaded the cleaned SQL dataset directly from PostgreSQL.  
- Addressed extreme class imbalance using **class weights** (`scale_pos_weight=10`).  
- Trained and evaluated three classification models:  
  - Logistic Regression  
  - Random Forest  
  - XGBoost *(selected as the best performer)*  
- Exported multiple Power BI–ready CSVs, including:
  - `fraud_by_day.csv`
  - `fraud_by_type.csv`
  - `model_metrics.csv`
  - `transactions_scored.csv`

### 3️⃣ Power BI: Interactive Visualization  
- Integrated model outputs and SQL summaries into a two-page Power BI report.  
- Built KPI cards, trend lines, and fraud-risk tables.  
- Structured for drill-through analysis across fraud types, users, and models.

---

## 🧩 Data Pipeline Summary

The dataset, based on the **PaySim credit card transactions simulator**, underwent a full transformation in SQL:

- **Ingestion:** Loaded CSV into `fraud.raw_transactions`.  
- **Cleaning:** Replaced negative balances with valid values using `GREATEST()`.  
- **Feature Engineering:** Added transaction-type flags and balance ratio metrics.  
- **Final Output:** `fraud.transactions_clean` — a rich dataset for modeling and BI.

---

## 📈 Executive Summary

From over **6 million transactions**, **8,000** were identified as fraudulent — representing losses exceeding **$12 billion**.  

| Metric | Value |
| --- | --- |
| **Total Transactions** | 6,000,000 |
| **Fraudulent Transactions** | 8,000 |
| **Fraud Rate** | 0.13% |
| **Model Accuracy** | 98.18% |
| **Model Recall (Fraud)** | 93.99% |
| **ROC-AUC** | 1.00 |

The **XGBoost** model achieved exceptional fraud recall (94%), ensuring high sensitivity for risk detection.

<p align="center">
  <img src="Images/last.PNG" alt="Fraud Overview Dashboard" width="800">
</p>

---

## 🔍 Insights Breakdown

### 🧭 Page 1 — Fraud Overview & Risk Insights  
- **High-Risk Transaction Types:** Fraud occurs exclusively in **TRANSFER** and **CASH_OUT**.  
- **Top Risky Accounts:** The receiver `C668046170` alone caused nearly **$10M** in losses.  
- **Fraud Trends:** The rate fluctuates sharply across time steps, suggesting cyclical risk behavior.  

### ⚙️ Page 2 — Model Performance & Quality  
- **Model Comparison:** All models achieved high accuracy, but recall was the key differentiator.  
- **XGBoost** outperformed others with:
  - **Accuracy:** 98.18%  
  - **Recall (Fraud):** 93.99%  
  - **Precision (Fraud):** 44.4%  
  - **ROC-AUC:** 1.00  
- **Confusion Matrix:**  
  - TP: 1,550 | FN: 93 | FP: 688 | TN: 1.27M  

<p align="center">
  <img src="Images/last2.PNG" alt="Model Performance Dashboard" width="800">
</p>

---

## 💡 Business Recommendations

1. **Deploy the XGBoost Model in Production**  
   Its 94% recall ensures minimal undetected fraud cases.

2. **Apply Stricter Controls on TRANSFER & CASH_OUT**  
   These two transaction types account for 100% of detected fraud.

3. **Investigate High-Risk Accounts**  
   Start with top receivers and frequent senders with abnormal activity.

4. **Optimize Precision vs. Recall**  
   Review trade-offs between blocking legitimate transactions vs. catching all fraud.

---

## ⚙️ Assumptions & Notes

- Dataset sourced from the **PaySim credit card simulator**.  
- `step` column represents transaction time in hours.  
- Fraud rate appears higher in subset metrics due to grouping by specific dimensions.  
- Models trained using **class weighting** to handle the 0.13% imbalance.  

---

<p align="center">
  <i>Created by Aïmane Benkhadda — End-to-End Fraud Analytics Project (PostgreSQL · Python · Power BI)</i><br>
  <a href="mailto:aymanebenkhadda5959@gmail.com">aymanebenkhadda5959@gmail.com</a>
</p>

---

✅ **In short:**  
This project combines **SQL-based ETL**, **Python-based modeling**, and **Power BI visualization** into one complete analytical solution — the same kind of workflow a fraud analyst or data scientist would build at a real fintech company.
