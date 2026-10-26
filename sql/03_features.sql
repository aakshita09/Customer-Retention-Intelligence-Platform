-- Behavioural features for every user, using ONLY events before :cutoff.
-- The label looks at the 30 days AFTER the cutoff. Parameters: %(cutoff)s (date).
DELETE FROM user_features WHERE cutoff = %(cutoff)s::date;

INSERT INTO user_features
WITH ev AS (
    SELECT * FROM events
    WHERE event_time <  %(cutoff)s::date
      AND event_time >= %(cutoff)s::date - interval '400 days'
),
cat_median AS (   -- typical purchase price per category, used as a price-sensitivity proxy
    SELECT category_code, percentile_cont(0.5) WITHIN GROUP (ORDER BY price) AS med
    FROM ev WHERE event_type = 'purchase' AND category_code IS NOT NULL AND price > 0
    GROUP BY category_code
),
base AS (
    SELECT user_id,
        MIN(event_time)::date AS first_seen,
        MAX(event_time)::date AS last_seen,
        COUNT(*) FILTER (WHERE event_type = 'view')               AS n_views,
        COUNT(*) FILTER (WHERE event_type = 'cart')               AS n_carts,
        COUNT(*) FILTER (WHERE event_type = 'remove_from_cart')   AS n_removes,
        COUNT(*) FILTER (WHERE event_type = 'purchase')           AS n_purchases,
        COUNT(DISTINCT user_session)                              AS n_sessions,
        COUNT(DISTINCT event_time::date)                          AS active_days,
        COALESCE(SUM(price) FILTER (WHERE event_type = 'purchase'), 0)  AS revenue,
        AVG(price)          FILTER (WHERE event_type = 'purchase')      AS avg_order_price,
        MIN(event_time) FILTER (WHERE event_type = 'purchase')::date    AS first_purchase,
        MAX(event_time) FILTER (WHERE event_type = 'purchase')::date    AS last_purchase,
        COUNT(DISTINCT category_code) FILTER (WHERE event_type = 'purchase') AS n_categories,
        COUNT(DISTINCT brand)         FILTER (WHERE event_type = 'purchase') AS n_brands,
        COUNT(*) FILTER (WHERE event_type='view'     AND event_time >= %(cutoff)s::date - 30) AS views_30d,
        COUNT(*) FILTER (WHERE event_type='cart'     AND event_time >= %(cutoff)s::date - 30) AS carts_30d,
        COUNT(*) FILTER (WHERE event_type='purchase' AND event_time >= %(cutoff)s::date - 30) AS purchases_30d,
        COUNT(DISTINCT user_session) FILTER (WHERE event_time >= %(cutoff)s::date - 30)       AS sessions_30d,
        COUNT(*) FILTER (WHERE event_type='view'     AND event_time >= %(cutoff)s::date - 60 AND event_time < %(cutoff)s::date - 30) AS views_prev30,
        COUNT(*) FILTER (WHERE event_type='purchase' AND event_time >= %(cutoff)s::date - 60 AND event_time < %(cutoff)s::date - 30) AS purchases_prev30
    FROM ev GROUP BY user_id
),
sess AS (         -- carts that never turned into a purchase in the same session
    SELECT user_id,
        COUNT(*) FILTER (WHERE has_cart)                       AS cart_sessions,
        COUNT(*) FILTER (WHERE has_cart AND NOT has_purchase)  AS abandoned_cart_sessions
    FROM (SELECT user_id, user_session,
                 BOOL_OR(event_type = 'cart') AS has_cart,
                 BOOL_OR(event_type = 'purchase') AS has_purchase
          FROM ev GROUP BY user_id, user_session) x
    GROUP BY user_id
),
price AS (
    SELECT e.user_id, AVG((e.price < m.med)::int) AS share_below_cat_median
    FROM ev e JOIN cat_median m USING (category_code)
    WHERE e.event_type = 'purchase' GROUP BY e.user_id
),
lbl AS (          -- did they buy in the 30 days after the cutoff?
    SELECT DISTINCT user_id FROM events
    WHERE event_type = 'purchase'
      AND event_time >= %(cutoff)s::date AND event_time < %(cutoff)s::date + interval '30 days'
)
SELECT %(cutoff)s::date, b.user_id,
    b.first_seen, b.last_seen,
    %(cutoff)s::date - b.first_seen, %(cutoff)s::date - b.last_seen,
    b.n_views, b.n_carts, b.n_removes, b.n_purchases, b.n_sessions, b.active_days,
    b.revenue, b.avg_order_price, b.first_purchase, b.last_purchase,
    %(cutoff)s::date - b.last_purchase,
    CASE WHEN b.n_purchases > 1 THEN (b.last_purchase - b.first_purchase)::numeric / (b.n_purchases - 1) END,
    b.n_categories, b.n_brands,
    b.views_30d, b.carts_30d, b.purchases_30d, b.sessions_30d, b.views_prev30, b.purchases_prev30,
    COALESCE(s.cart_sessions, 0), COALESCE(s.abandoned_cart_sessions, 0),
    p.share_below_cat_median,
    CASE WHEN b.n_purchases > 0 THEN (l.user_id IS NULL)::int END
FROM base b
LEFT JOIN sess  s ON s.user_id = b.user_id
LEFT JOIN price p ON p.user_id = b.user_id
LEFT JOIN lbl   l ON l.user_id = b.user_id;
