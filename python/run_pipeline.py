"""One command, end to end:  python run_pipeline.py ../data/sample/*.csv"""
import sys, glob
import load_data, train_churn, export_outputs
from db import run_sql_file
if __name__ == "__main__":
    run_sql_file("01_schema.sql")
    for f in sorted(g for p in sys.argv[1:] for g in glob.glob(p)): load_data.load_file(f)
    run_sql_file("02_indexes.sql"); run_sql_file("04_funnel_cohorts.sql")
    train_churn.run(); export_outputs.run()
