"""Rebuild PaySim aggregates and evaluate three models on a chronological holdout."""
import argparse
import csv
import io
import logging
import os
import shutil
import zipfile
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd
import psycopg2
from dotenv import load_dotenv
from filelock import FileLock
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, precision_recall_curve, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SQL = HERE.parent / "SQL" / "fraud_pipeline.sql"
TYPES = ["CASH_IN", "CASH_OUT", "DEBIT", "PAYMENT", "TRANSFER"]
HEADERS = "step type amount nameOrig oldbalanceOrg newbalanceOrig nameDest oldbalanceDest newbalanceDest isFraud isFlaggedFraud".split()
SEED = 42
MAX_TRAIN_NEGATIVES = 200_000

@contextmanager
def source_stream(source):
    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            files = [n for n in archive.namelist() if n.lower().endswith(".csv")]
            if len(files) != 1:
                raise ValueError("Supply a ZIP containing exactly one PaySim CSV.")
            with archive.open(files[0]) as binary, io.TextIOWrapper(binary, encoding="utf-8-sig", newline="") as stream:
                yield stream
    else:
        with source.open(encoding="utf-8-sig", newline="") as stream:
            yield stream

def load_database(conn, source):
    with conn.cursor() as cur, source_stream(source) as stream:
        if next(csv.reader(stream), []) != HEADERS:
            raise ValueError("Unexpected PaySim CSV header or column order.")
        cur.execute("""CREATE TEMP TABLE incoming (
            step integer NOT NULL CHECK (step > 0),
            type varchar(20) NOT NULL CHECK (type IN ('CASH_IN','CASH_OUT','DEBIT','PAYMENT','TRANSFER')),
            amount numeric NOT NULL CHECK (amount >= 0 AND amount < 'Infinity'::numeric AND amount=round(amount,2)),
            nameorig varchar(50), oldbalanceorg numeric, newbalanceorig numeric, namedest varchar(50),
            oldbalancedest numeric, newbalancedest numeric,
            isfraud integer NOT NULL CHECK (isfraud IN (0,1)),
            isflaggedfraud integer NOT NULL CHECK (isflaggedfraud IN (0,1))) ON COMMIT DROP""")
        cur.copy_expert("COPY incoming FROM STDIN WITH (FORMAT CSV)", stream)
        cur.execute("SELECT EXISTS(SELECT 1 FROM incoming)")
        if not cur.fetchone()[0]:
            raise ValueError("The source contains no transactions.")
        cur.execute(SQL.read_text(encoding="utf-8"))

def prepare(chunk):
    chunk = chunk.rename(columns=str.lower)
    if chunk[["step","type","amount","isfraud"]].isna().any().any():
        raise ValueError("A required transaction value is missing.")
    steps = pd.to_numeric(chunk.step)
    labels = pd.to_numeric(chunk.isfraud)
    amount = pd.to_numeric(chunk.amount).to_numpy(dtype="float64")
    if not (steps.between(1, 2**31-1) & steps.eq(np.floor(steps))).all() or not labels.isin([0,1]).all():
        raise ValueError("Invalid simulation step or fraud label.")
    if not np.isfinite(amount).all() or (amount < 0).any() or (amount > 9e13).any():
        raise ValueError("Invalid transaction amount.")
    cents = np.rint(amount * 100)
    if not np.allclose(cents, amount*100, atol=0.0001, rtol=0):
        raise ValueError("Transaction amounts must be specified to the cent.")
    types = pd.Categorical(chunk.type, categories=TYPES).codes
    if (types < 0).any():
        raise ValueError("Unexpected PaySim transaction type.")
    return pd.DataFrame({"step":steps.to_numpy(dtype="int32"), "type":types,
                         "cents":cents.astype("int64"), "label":labels.to_numpy(dtype="uint8")})

def transactions(source, conn):
    parts = []
    if source is not None:
        with source_stream(source) as stream:
            for chunk in pd.read_csv(stream, usecols=["step","type","amount","isFraud"], chunksize=250_000):
                parts.append(prepare(chunk))
    else:
        with conn.cursor(name="paysim_reader") as cur:
            cur.execute("SELECT step,type,amount::double precision,isfraud FROM fraud.transactions_clean")
            while batch := cur.fetchmany(100_000):
                parts.append(prepare(pd.DataFrame(batch, columns=["step","type","amount","isfraud"])))
    if not parts:
        raise ValueError("The source contains no transactions.")
    data = pd.concat(parts, ignore_index=True)
    if data.empty:
        raise ValueError("The source contains no transactions.")
    return data.sort_values(["step","type","cents","label"],ignore_index=True)

def summarize(data):
    day = ((data.step - 1) // 24 + 1).rename("simulation_day")
    flagged = data.cents.where(data.label.eq(1), 0)
    groups = data.assign(fraud_cents=flagged).groupby([day, "type"], sort=True)
    activity = groups.agg(transactions=("label","size"), fraud_cases=("label","sum"),
                          fraud_cents=("fraud_cents","sum")).reset_index()
    activity["type"] = activity["type"].map(dict(enumerate(TYPES)))
    return activity

def chronological_split(data):
    counts = data.step.value_counts().sort_index()
    cum = counts.cumsum().to_numpy()
    ends = [int(counts.index[np.searchsorted(cum, len(data)*fraction)]) for fraction in (0.6,0.8)]
    train = data.loc[data.step <= ends[0]]
    valid = data.loc[data.step.between(ends[0]+1, ends[1])]
    test = data.loc[data.step > ends[1]]
    if any(x.label.nunique() != 2 for x in (train,valid,test)):
        raise ValueError("Each chronological partition must contain both classes and cover distinct hours.")
    return train,valid,test

def features(d):
    hour = (d.step.to_numpy()-1) % 24
    angle = hour * (2*np.pi/24)
    return np.column_stack([np.log1p(d.cents.to_numpy()/100),np.sin(angle),np.cos(angle),
                            *(d.type.to_numpy()==i for i in range(len(TYPES)))]).astype("float32")

def evaluate(data):
    train, valid, test = chronological_split(data)
    negatives = train.loc[train.label.eq(0)]
    sample = pd.concat([train.loc[train.label.eq(1)], negatives.sample(min(len(negatives),MAX_TRAIN_NEGATIVES),
                        random_state=SEED)]).sample(frac=1,random_state=SEED)
    x_train, x_valid, x_test = (features(d) for d in (sample,valid,test))
    models = {
        "Logistic regression": make_pipeline(StandardScaler(),LogisticRegression(max_iter=600,random_state=SEED)),
        "Random forest": RandomForestClassifier(n_estimators=100,max_depth=13,min_samples_leaf=12,n_jobs=4,random_state=SEED),
        "XGBoost": XGBClassifier(n_estimators=160,max_depth=5,learning_rate=0.08,tree_method="hist",
                                 eval_metric="logloss",n_jobs=4,random_state=SEED),
    }
    metrics = []
    for name, model in models.items():
        logging.info("Fitting %s",name)
        model.fit(x_train,sample.label)
        validation_scores = model.predict_proba(x_valid)[:,1]
        precision,recall,thresholds = precision_recall_curve(valid.label,validation_scores)
        f1 = 2*precision[:-1]*recall[:-1]/np.maximum(precision[:-1]+recall[:-1],1e-15)
        best = np.flatnonzero(f1==f1.max())[-1]
        threshold = float(thresholds[best])
        probs = model.predict_proba(x_test)[:,1]
        tn,fp,fn,tp = (int(n) for n in confusion_matrix(test.label,probs>=threshold,labels=[0,1]).ravel())
        metrics.append(dict(model_name=name,train_end=int(train.step.max()),valid_end=int(valid.step.max()),
            test_start=int(test.step.min()),test_end=int(test.step.max()),train_rows=len(train),fit_rows=len(sample),
            valid_rows=len(valid),test_rows=len(test),threshold=threshold,validation_f1=float(f1[best]),
            tn=tn,fp=fp,fn=fn,tp=tp,accuracy=(tn+tp)/len(test),precision_fraud=tp/(tp+fp) if tp+fp else 0,
            recall_fraud=tp/(tp+fn),f1_fraud=2*tp/(2*tp+fp+fn),
            average_precision=average_precision_score(test.label,probs),auc=roc_auc_score(test.label,probs)))
    result = pd.DataFrame(metrics).sort_values(["validation_f1","model_name"],ascending=[False,True]).reset_index(drop=True)
    result["validation_rank"] = np.arange(1,len(result)+1)
    return result

def format_amount(table):
    out = table.copy()
    # Format from integer cents so CSVs reconcile to two decimals.
    out["fraud_amount"] = out.pop("fraud_cents").map(lambda n: f"{n//100}.{n%100:02}")
    return out

def publish_reports(tables, output, conn):
    """Restore the previous exports if replacement or the database commit fails."""
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output) as temp:
        stage = Path(temp)
        filenames = [name + ".csv" for name in tables]
        for filename, table in zip(filenames, tables.values()):
            table.to_csv(stage / filename, index=False, lineterminator="\n")

        with FileLock(str(output / ".publish.lock")):
            previous = stage / "previous"
            previous.mkdir()
            replaced = []
            for filename in filenames:
                destination = output / filename
                if destination.exists():
                    shutil.copyfile(destination, previous / filename)
            try:
                for filename in filenames:
                    (stage / filename).replace(output / filename)
                    replaced.append(filename)
                if conn is not None:
                    conn.commit()
            except BaseException:
                for filename in reversed(replaced):
                    backup = previous / filename
                    if backup.exists():
                        backup.replace(output / filename)
                    else:
                        (output / filename).unlink()
                raise


def run(source=None, output=HERE/"exports", use_postgres=False):
    load_dotenv(ROOT/".env")
    conn = None
    try:
        if use_postgres or source is None:
            conn = psycopg2.connect(dbname=os.environ["PG_DB"],user=os.environ["PG_USER"],password=os.getenv("PG_PASS"),
                                    host=os.getenv("PG_HOST","localhost"),port=os.getenv("PG_PORT","5432"))
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_lock(hashtext('paysim-fraud-analytics'))")
            if source is not None:
                load_database(conn,source)
        data = transactions(source,conn)
        activity = summarize(data)
        if conn is not None and source is not None:
            with conn.cursor() as cur:
                cur.execute("SELECT simulation_day,type,transactions,fraud_cases,(fraud_amount*100)::bigint FROM fraud.vw_activity ORDER BY 1,2")
                if cur.fetchall()!=list(activity.sort_values(["simulation_day","type"]).itertuples(index=False,name=None)):
                    raise ValueError("SQL aggregation disagrees with the source CSV.")
        metrics = evaluate(data)
        tables = {"activity": format_amount(activity), "model_metrics":metrics,
                  "confusion_matrix":metrics[["model_name","tn","fp","fn","tp"]]}
        for field,name in [("simulation_day","fraud_by_day"),("type","fraud_by_type")]:
            sums = activity.groupby(field,as_index=False)[["transactions","fraud_cases","fraud_cents"]].sum()
            sums["fraud_rate"] = sums.fraud_cases/sums.transactions
            tables[name] = format_amount(sums)
        publish_reports(tables, Path(output), conn)
        logging.info("Published %s transactions and %s simulated fraud labels",len(data),int(data.label.sum()))
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input",type=Path,help="Original PaySim CSV or single-CSV ZIP. Omit to read PostgreSQL.")
    cli.add_argument("--postgres",action="store_true",help="Also reload and verify the PostgreSQL schema.")
    cli.add_argument("--output-dir",type=Path,default=HERE/"exports")
    args = cli.parse_args()
    logging.basicConfig(level=logging.INFO,format="%(message)s")
    run(args.input,args.output_dir,args.postgres)
