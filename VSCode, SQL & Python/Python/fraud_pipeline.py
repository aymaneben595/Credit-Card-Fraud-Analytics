#!/usr/bin/env python3
# ===============================================================
# 🏆 FRAUD INTELLIGENCE PIPELINE — Power BI + ML Dashboard Ready
# ===============================================================
# Creates clean exports for two Power BI pages:
#   📄 Page 1 — Fraud Overview & Risk Insights
#   🤖 Page 2 — Model Performance & Quality
# ===============================================================

import os, time, logging
import pandas as pd, numpy as np
from sqlalchemy import create_engine, text
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier

# ---------------------------------------------------------------
# ✅ Logging setup
# ---------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------------------------------------------------------------
# ✅ PostgreSQL connection
# ---------------------------------------------------------------
DB_USER = os.getenv("PG_USER", "postgres")
DB_PASS = os.getenv("PG_PASS", "Aymaneb595.")
DB_HOST = os.getenv("PG_HOST", "localhost")
DB_PORT = os.getenv("PG_PORT", "5432")
DB_NAME = os.getenv("PG_DB", "ddb")
DB_SCHEMA = "fraud"
EXPORT_DIR = "exports"
os.makedirs(EXPORT_DIR, exist_ok=True)

DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def get_connection():
    from sqlalchemy.exc import OperationalError
    for i in range(5):
        try:
            engine = create_engine(DB_URL)
            with engine.connect() as c:
                c.execute(text(f"SET search_path TO {DB_SCHEMA};"))
            logging.info("✅ Connected to PostgreSQL")
            return engine
        except OperationalError:
            logging.warning("⏳ Retrying database connection...")
            time.sleep(2)
    raise SystemExit("❌ Could not connect to PostgreSQL")

engine = get_connection()

# ---------------------------------------------------------------
# ✅ Load Clean Data
# ---------------------------------------------------------------
logging.info("📥 Loading cleaned data from PostgreSQL...")
df = pd.read_sql(f"SELECT * FROM {DB_SCHEMA}.transactions_clean;", engine)
df.columns = df.columns.str.lower()
logging.info(f"✅ Loaded {len(df):,} rows with {len(df.columns)} columns")

# ---------------------------------------------------------------
# ✅ Create Data for Page 1 — Fraud Overview
# ---------------------------------------------------------------

# --- By Day ---
if "step" in df.columns:
    df["step_day"] = df["step"] % 7  # or replace with actual day mapping

fraud_by_day = (
    df.groupby("step_day", as_index=False)
      .agg(
          total_transactions=("isfraud", "count"),
          fraud_cases=("isfraud", "sum"),
          fraud_rate=("isfraud", "mean"),
          total_fraud_loss_usd=("amount", lambda x: x[df.loc[x.index, "isfraud"] == 1].sum())
      )
)
fraud_by_day["fraud_rate"] = (fraud_by_day["fraud_rate"] * 100).round(2)
fraud_by_day.to_csv(f"{EXPORT_DIR}/fraud_by_day.csv", index=False)
logging.info("💾 Exported fraud_by_day.csv")

# --- By Type ---
if "type" in df.columns:
    fraud_by_type = (
        df.groupby("type", as_index=False)
          .agg(
              total_transactions=("isfraud", "count"),
              fraud_cases=("isfraud", "sum"),
              fraud_rate=("isfraud", "mean"),
              total_fraud_loss_usd=("amount", lambda x: x[df.loc[x.index, "isfraud"] == 1].sum())
          )
    )
    fraud_by_type["fraud_rate"] = (fraud_by_type["fraud_rate"] * 100).round(2)
    fraud_by_type.to_csv(f"{EXPORT_DIR}/fraud_by_type.csv", index=False)
    logging.info("💾 Exported fraud_by_type.csv")

# --- By Sender / Receiver (for tables) ---
fraud_by_sender = (
    df.groupby("nameorig", as_index=False)
      .agg(
          total_transactions=("isfraud", "count"),
          fraud_cases=("isfraud", "sum"),
          total_amount=("amount", "sum"),
          total_fraud_loss_usd=("amount", lambda x: x[df.loc[x.index, "isfraud"] == 1].sum())
      )
)
fraud_by_sender["fraud_rate(%)"] = (fraud_by_sender["fraud_cases"] /
                                   fraud_by_sender["total_transactions"] * 100).round(2)
fraud_by_sender.to_csv(f"{EXPORT_DIR}/fraud_by_sender.csv", index=False)

fraud_by_receiver = (
    df.groupby("namedest", as_index=False)
      .agg(
          total_transactions=("isfraud", "count"),
          fraud_cases=("isfraud", "sum"),
          total_amount=("amount", "sum"),
          total_fraud_loss_usd=("amount", lambda x: x[df.loc[x.index, "isfraud"] == 1].sum())
      )
)
fraud_by_receiver["fraud_rate(%)"] = (fraud_by_receiver["fraud_cases"] /
                                     fraud_by_receiver["total_transactions"] * 100).round(2)
fraud_by_receiver.to_csv(f"{EXPORT_DIR}/fraud_by_receiver.csv", index=False)

logging.info("💾 Exported fraud_by_sender.csv & fraud_by_receiver.csv")

# ---------------------------------------------------------------
# ✅ MACHINE LEARNING SECTION — Page 2 (Model Performance)
# ---------------------------------------------------------------
logging.info("🤖 Training ML models...")

# --- Features ---
features = [
    "amount", "oldbalanceorg", "newbalanceorig",
    "oldbalancedest", "newbalancedest",
    "balance_delta", "balance_change_ratio",
    "is_cashout", "is_payment", "is_transfer", "is_cashin", "is_merchant"
]
df = df.dropna(subset=features + ["isfraud"])

X, y = df[features], df["isfraud"]
X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, test_size=0.2, random_state=42)

# --- Scaling ---
scaler = StandardScaler()
X_train_s, X_test_s = scaler.fit_transform(X_train), scaler.transform(X_test)

# --- Define models ---
models = {
    "Logistic Regression": LogisticRegression(max_iter=4000, class_weight="balanced"),
    "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=18, class_weight="balanced", n_jobs=-1),
    "XGBoost": XGBClassifier(
        n_estimators=300, max_depth=7, learning_rate=0.1,
        scale_pos_weight=10, n_jobs=-1, tree_method="hist", eval_metric="logloss"
    )
}

metrics_list = []
for name, model in models.items():
    logging.info(f"🚀 Training {name}...")
    model.fit(X_train_s if "Regression" in name else X_train, y_train)

    X_eval = X_test_s if "Regression" in name else X_test
    preds = model.predict(X_eval)
    probs = model.predict_proba(X_eval)[:, 1]
    auc = roc_auc_score(y_test, probs)
    report = classification_report(y_test, preds, output_dict=True)

    metrics = {
        "model_name": name,
        "accuracy": report["accuracy"],
        "precision_fraud": report["1"]["precision"],
        "recall_fraud": report["1"]["recall"],
        "f1_fraud": report["1"]["f1-score"],
        "auc": auc
    }
    metrics_list.append(metrics)

# --- Save model metrics ---
metrics_df = pd.DataFrame(metrics_list)
metrics_df.to_csv(f"{EXPORT_DIR}/model_metrics.csv", index=False)
logging.info("💾 Exported model_metrics.csv")

# --- Confusion Matrix (for XGBoost only) ---
best_model = models["XGBoost"]
preds_best = best_model.predict(X_test)
cm = confusion_matrix(y_test, preds_best)
cm_df = pd.DataFrame(cm, columns=["Pred_0", "Pred_1"], index=["Actual_0", "Actual_1"])
cm_df.to_csv(f"{EXPORT_DIR}/confusion_matrix.csv")
logging.info("💾 Exported confusion_matrix.csv")

# --- Save scored dataset (for histograms, risk visuals) ---
df["fraud_score_xgb"] = best_model.predict_proba(X)[:, 1]
df.to_csv(f"{EXPORT_DIR}/transactions_scored.csv", index=False)
logging.info("💾 Exported transactions_scored.csv")

logging.info("✅✅✅ Pipeline completed — All Power BI files ready!")

# ===============================================================
# 📂 FINAL EXPORTS (for Power BI Dashboard)
# ---------------------------------------------------------------
#  Page 1: Business Insights
#     - fraud_by_day.csv
#     - fraud_by_type.csv
#     - fraud_by_sender.csv
#     - fraud_by_receiver.csv
#
#  Page 2: Model Performance
#     - transactions_scored.csv
#     - model_metrics.csv
#     - confusion_matrix.csv
# ===============================================================
