-- Raw event log, same columns as the Kaggle REES46 CSV files.
CREATE TABLE IF NOT EXISTS events (
    event_time    timestamptz NOT NULL,
    event_type    text        NOT NULL,   -- view | cart | remove_from_cart | purchase
    product_id    bigint,
    category_id   bigint,
    category_code text,                   -- e.g. electronics.smartphone (often NULL)
    brand         text,
    price         numeric(10,2),
    user_id       bigint      NOT NULL,
    user_session  uuid
);

-- Indexes are created AFTER the bulk load (see load_data.py) because that is much faster.
CREATE TABLE IF NOT EXISTS load_log (file_name text PRIMARY KEY, rows_loaded bigint, loaded_at timestamptz DEFAULT now());

-- Per-user, per-cutoff feature table (filled by features.py from 03_features.sql)
CREATE TABLE IF NOT EXISTS user_features (
    cutoff date NOT NULL,
    user_id bigint NOT NULL,
    first_seen date, last_seen date,
    days_since_first_seen int, days_since_last_seen int,
    n_views int, n_carts int, n_removes int, n_purchases int,
    n_sessions int, active_days int,
    revenue numeric(12,2), avg_order_price numeric(10,2),
    first_purchase date, last_purchase date,
    days_since_last_purchase int, avg_gap_days numeric(8,2),
    n_categories int, n_brands int,
    views_30d int, carts_30d int, purchases_30d int, sessions_30d int,
    views_prev30 int, purchases_prev30 int,
    cart_sessions int, abandoned_cart_sessions int,
    share_below_cat_median numeric(5,4),
    churned_next_30d smallint,           -- 1 = no purchase in the 30 days after cutoff (purchasers only)
    PRIMARY KEY (cutoff, user_id)
);
