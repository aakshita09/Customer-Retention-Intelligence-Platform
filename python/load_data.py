"""Load Kaggle CSVs into PostgreSQL in chunks (never holds a full month in memory).
   python load_data.py ../data/sample/*.csv            # or the real 2019-Oct.csv ...
   python load_data.py 2019-Oct.csv --sample-users 0.1  # keep 10% of users (deterministic) for laptops
"""
import argparse, io, os, glob
import pandas as pd
from db import connect, run_sql_file

COLS = ["event_time","event_type","product_id","category_id","category_code","brand","price","user_id","user_session"]

def load_file(path, chunksize=500_000, sample_users=1.0):
    name = os.path.basename(path)
    with connect() as con, con.cursor() as cur:
        cur.execute("SELECT 1 FROM load_log WHERE file_name=%s", (name,))
        if cur.fetchone(): print(f"skip {name} (already loaded)"); return
        total = 0
        for chunk in pd.read_csv(path, chunksize=chunksize, usecols=COLS):
            chunk = chunk.dropna(subset=["user_id"])
            chunk = chunk[chunk.price.fillna(0) >= 0]
            if sample_users < 1:   # keep a stable subset of users so their full history stays intact
                chunk = chunk[(chunk.user_id % 1000) < int(sample_users * 1000)]
            buf = io.StringIO(); chunk[COLS].to_csv(buf, header=False, index=False); buf.seek(0)
            cur.copy_expert(f"COPY events ({','.join(COLS)}) FROM STDIN WITH (FORMAT csv)", buf)
            total += len(chunk); print(f"  {name}: {total:,} rows", end="\r")
        cur.execute("INSERT INTO load_log (file_name, rows_loaded) VALUES (%s,%s)", (name, total))
    print(f"loaded {name}: {total:,} rows" + " " * 20)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("files", nargs="+"); ap.add_argument("--sample-users", type=float, default=1.0)
    a = ap.parse_args()
    run_sql_file("01_schema.sql")
    files = sorted(f for p in a.files for f in glob.glob(p))
    for f in files: load_file(f, sample_users=a.sample_users)
    run_sql_file("02_indexes.sql"); run_sql_file("04_funnel_cohorts.sql"); print("done: tables, indexes and views ready")
