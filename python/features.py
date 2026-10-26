"""Build the per-user feature table for one or more cutoffs (heavy lifting is done in SQL)."""
import sys, pandas as pd
from sqlalchemy import create_engine, text
from db import run_sql_file
from config import DB_URL
from config import TRAIN_CUTOFF, VALID_CUTOFF, SCORE_CUTOFF

def build(cutoff):
    run_sql_file("03_features.sql", {"cutoff": cutoff}); print(f"features built for cutoff {cutoff}")

def read(cutoff) -> pd.DataFrame:
    eng = create_engine(DB_URL.replace("postgresql://", "postgresql+psycopg2://"))
    return pd.read_sql(text("SELECT * FROM user_features WHERE cutoff = CAST(:c AS date)"), eng, params={"c": cutoff})

if __name__ == "__main__":
    for c in (sys.argv[1:] or [TRAIN_CUTOFF, VALID_CUTOFF, SCORE_CUTOFF]): build(c)
