"""Shared settings. Override with environment variables."""
import os
DB_URL = os.getenv("DATABASE_URL", "postgresql://retention:retention@localhost:5432/retention")
SQL_DIR = os.path.join(os.path.dirname(__file__), "..", "sql")
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")

# Churn definition: a customer who bought before the cutoff but makes NO purchase in the next HORIZON days.
HORIZON_DAYS = 30
TRAIN_CUTOFF = os.getenv("TRAIN_CUTOFF", "2019-12-15")   # features before, labels after
VALID_CUTOFF = os.getenv("VALID_CUTOFF", "2020-02-01")   # later period, used only to evaluate
SCORE_CUTOFF = os.getenv("SCORE_CUTOFF", "2020-04-01")   # "today": who is at risk now?
RISK_THRESHOLD = 0.80   # "High" risk / At-risk segment cut-off. Most buyers skip any given 30 days, so tune this to your base rate.
MEDIUM_RISK = 0.50
