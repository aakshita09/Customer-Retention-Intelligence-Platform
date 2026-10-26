"""Rule-based customer segments. Priority order matters: the first matching rule wins."""
import numpy as np, pandas as pd
from config import RISK_THRESHOLD

ORDER = ["Churned","New users","At risk","High-value","Price-sensitive","Repeat customers","First-time buyers"]

def assign_segments(df: pd.DataFrame, churn_prob: pd.Series | None = None) -> pd.Series:
    buyers = df.n_purchases > 0
    hv_cut = df.loc[buyers, "revenue"].quantile(0.9) if buyers.any() else np.inf     # top 10% of buyers
    p = churn_prob if churn_prob is not None else pd.Series(0.0, index=df.index)
    churned = buyers & (df.days_since_last_purchase > 90)                              # no purchase for 90+ days
    conds = [
        churned,
        ~buyers,
        buyers & (p >= RISK_THRESHOLD),
        buyers & (df.revenue >= hv_cut) & (df.n_purchases >= 3),
        buyers & (df.share_below_cat_median.fillna(0) >= 0.75) & (df.n_purchases >= 2),  # mostly buys below category median price
        df.n_purchases >= 2,
        df.n_purchases == 1,
    ]
    return pd.Series(np.select(conds, ORDER[:7], default="First-time buyers"), index=df.index, name="segment")

ACTIONS = {
 "Churned": "Low-cost reactivation email, then suppress",
 "New users": "Welcome series and a first-order nudge",
 "At risk": "Personal win-back offer within 7 days",
 "High-value": "Early access and loyalty perks",
 "Price-sensitive": "Price-drop alerts and bundles (no blanket codes)",
 "Repeat customers": "Cross-sell from categories they already buy",
 "First-time buyers": "Post-purchase tips and a second-order reminder",
}
