import psycopg2, os
from config import DB_URL, SQL_DIR
def connect(): return psycopg2.connect(DB_URL)
def run_sql_file(name, params=None):
    with connect() as con, con.cursor() as cur:
        cur.execute(open(os.path.join(SQL_DIR, name)).read(), params)
