"""Score everyone at the SCORE_CUTOFF, assign segments, and publish tables for Power BI
(into PostgreSQL AND as CSV files)."""
import os, joblib, numpy as np, pandas as pd
from sqlalchemy import create_engine, text
import features
from train_churn import engineer, num
from segments import assign_segments, ACTIONS
from config import DB_URL, OUT_DIR, SCORE_CUTOFF, RISK_THRESHOLD, MEDIUM_RISK

def run():
    art = joblib.load(os.path.join(OUT_DIR, "churn_model.joblib")); model, cols = art["model"], art["cols"]
    df, _ = engineer(features.read(SCORE_CUTOFF)); df = df.reset_index(drop=True)
    buyers = df.n_purchases > 0; p = pd.Series(np.nan, index=df.index)
    p[buyers] = model.predict_proba(num(df[buyers], cols))[:, 1]
    df["churn_probability"] = p; df["segment"] = assign_segments(df, p.fillna(0))
    df["yearly_value"] = (df.revenue / (df.days_since_first_seen.clip(lower=60) / 365)).round(2)
    df["revenue_at_risk"] = (df.churn_probability.fillna(0) * df.yearly_value).round(2)
    df["risk_band"] = pd.cut(df.churn_probability, [0, MEDIUM_RISK, RISK_THRESHOLD, 1.0], labels=["Low","Medium","High"], include_lowest=True).astype(object)
    df["recommended_action"] = df.segment.map(ACTIONS)
    keep = ["user_id","segment","churn_probability","risk_band","revenue_at_risk","yearly_value","recommended_action","n_purchases","revenue",
            "avg_order_price","days_since_last_purchase","days_since_first_seen","n_sessions","sessions_30d","cart_sessions","abandoned_cart_sessions","share_below_cat_median","first_seen","last_purchase"]
    cust = df[keep].copy()
    seg = (cust.groupby("segment").agg(customers=("user_id","count"), avg_revenue=("revenue","mean"), avg_churn_prob=("churn_probability","mean"),
           revenue_at_risk=("revenue_at_risk","sum")).reset_index().round(3))
    eng = create_engine(DB_URL.replace("postgresql://", "postgresql+psycopg2://"))
    funnel = pd.read_sql("SELECT * FROM funnel_monthly", eng); fcat = pd.read_sql("SELECT * FROM funnel_by_category", eng)
    coh = pd.read_sql("SELECT * FROM cohort_retention", eng); gap = pd.read_sql("SELECT * FROM second_purchase_gap", eng)
    gap_bins = pd.cut(gap.gap_days, [-1,7,14,30,60,90,1e9], labels=["0-7d","8-14d","15-30d","31-60d","61-90d","90d+"]).astype(object).fillna("No 2nd purchase")
    gap_sum = gap_bins.value_counts().rename_axis("gap_bucket").reset_index(name="customers")
    tables = {"customer_scores": cust, "segment_summary": seg, "funnel_monthly_out": funnel, "funnel_by_category_out": fcat,
              "cohort_retention_out": coh, "second_purchase_gap_summary": gap_sum,
              "feature_importance": pd.read_csv(os.path.join(OUT_DIR, "feature_importance.csv"))}
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, t in tables.items():
        t.to_sql(name, eng, if_exists="replace", index=False); t.to_csv(os.path.join(OUT_DIR, f"{name}.csv"), index=False)
    print(seg.sort_values("customers", ascending=False).to_string(index=False))
    print(f"\n{int((cust.churn_probability >= RISK_THRESHOLD).sum())} customers at/above {RISK_THRESHOLD:.0%} risk; wrote {len(tables)} tables + CSVs to {os.path.abspath(OUT_DIR)}")

if __name__ == "__main__": run()
