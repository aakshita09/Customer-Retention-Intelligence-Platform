"""Train and honestly evaluate the churn model.
Train on cutoff A, test on a LATER cutoff B (time-based split, so no future information leaks), score cutoff C.
"""
import json, os, joblib, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.inspection import permutation_importance
import features
from config import TRAIN_CUTOFF, VALID_CUTOFF, SCORE_CUTOFF, OUT_DIR

FEATS = ["days_since_first_seen","days_since_last_seen","days_since_last_purchase","n_views","n_carts","n_removes","n_purchases",
 "n_sessions","active_days","revenue","avg_order_price","avg_gap_days","n_categories","n_brands","views_30d","carts_30d",
 "purchases_30d","sessions_30d","views_prev30","purchases_prev30","cart_sessions","abandoned_cart_sessions","share_below_cat_median"]

def engineer(df):
    d = df.copy()
    d["view_trend"] = (d.views_30d - d.views_prev30) / (d.views_prev30 + 1)
    d["purchase_trend"] = d.purchases_30d - d.purchases_prev30
    d["cart_abandon_rate"] = d.abandoned_cart_sessions / d.cart_sessions.replace(0, np.nan)
    d["recency_vs_gap"] = d.days_since_last_purchase / d.avg_gap_days.astype(float).replace(0, np.nan)   # overdue vs own rhythm
    d["purchases_per_week"] = d.n_purchases / (d.days_since_first_seen / 7 + 1)
    return d, FEATS + ["view_trend","purchase_trend","cart_abandon_rate","recency_vs_gap","purchases_per_week"]

def purchasers(df): return df[df.n_purchases > 0].copy()
def num(d, cols): return d[cols].astype(float)

def top_decile_lift(y, p):
    k = max(1, len(y) // 10); idx = np.argsort(-p)[:k]; return float(y[idx].mean() / y.mean())

def run():
    for c in (TRAIN_CUTOFF, VALID_CUTOFF, SCORE_CUTOFF): features.build(c)
    tr, cols = engineer(purchasers(features.read(TRAIN_CUTOFF))); va, _ = engineer(purchasers(features.read(VALID_CUTOFF)))
    Xtr, ytr, Xva, yva = num(tr, cols), tr.churned_next_30d.astype(int), num(va, cols), va.churned_next_30d.astype(int)
    print(f"train: {len(tr):,} purchasers, churn rate {ytr.mean():.1%} | test: {len(va):,}, churn rate {yva.mean():.1%}")

    models = {
      "logistic_regression": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(max_iter=1000, class_weight="balanced")),
      "gradient_boosting": HistGradientBoostingClassifier(max_depth=4, learning_rate=0.06, max_iter=300, l2_regularization=1.0, random_state=0),
    }
    report = {}
    for name, m in models.items():
        m.fit(Xtr, ytr); p = m.predict_proba(Xva)[:, 1]
        report[name] = {"roc_auc": roc_auc_score(yva, p), "pr_auc": average_precision_score(yva, p),
                        "brier": brier_score_loss(yva, p), "top_decile_lift": top_decile_lift(yva.values, p)}
        print(name, {k: round(v, 3) for k, v in report[name].items()})
    base = float(yva.mean()); report["baseline_churn_rate"] = base
    best = max(("logistic_regression","gradient_boosting"), key=lambda n: report[n]["roc_auc"]); model = models[best]; report["selected"] = best
    print("selected:", best)

    imp = permutation_importance(model, Xva, yva, scoring="roc_auc", n_repeats=5, random_state=0)
    fi = pd.DataFrame({"feature": cols, "importance": imp.importances_mean}).sort_values("importance", ascending=False)
    os.makedirs(OUT_DIR, exist_ok=True)
    fi.to_csv(os.path.join(OUT_DIR, "feature_importance.csv"), index=False); json.dump(report, open(os.path.join(OUT_DIR, "model_metrics.json"), "w"), indent=2)
    joblib.dump({"model": model, "cols": cols}, os.path.join(OUT_DIR, "churn_model.joblib"))
    print(fi.head(8).to_string(index=False)); return model, cols

if __name__ == "__main__": run()
