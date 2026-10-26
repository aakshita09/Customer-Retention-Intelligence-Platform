-- Session-level funnel by month: view -> cart -> purchase (strict order of stages).
CREATE OR REPLACE VIEW funnel_monthly AS
WITH s AS (
    SELECT user_session, MIN(event_time) AS t,
           BOOL_OR(event_type = 'view') AS v, BOOL_OR(event_type = 'cart') AS c, BOOL_OR(event_type = 'purchase') AS p
    FROM events GROUP BY user_session)
SELECT date_trunc('month', t)::date AS month,
       COUNT(*)                         AS sessions,
       COUNT(*) FILTER (WHERE v)        AS viewed,
       COUNT(*) FILTER (WHERE v AND c)  AS added_to_cart,
       COUNT(*) FILTER (WHERE v AND c AND p) AS purchased
FROM s GROUP BY 1 ORDER BY 1;

-- Same funnel by top-level category (view/cart/purchase of that category inside one session).
CREATE OR REPLACE VIEW funnel_by_category AS
WITH s AS (
    SELECT split_part(category_code, '.', 1) AS category, user_session,
           BOOL_OR(event_type = 'view') AS v, BOOL_OR(event_type = 'cart') AS c, BOOL_OR(event_type = 'purchase') AS p
    FROM events WHERE category_code IS NOT NULL GROUP BY 1, 2)
SELECT category,
       COUNT(*) FILTER (WHERE v) AS viewed,
       COUNT(*) FILTER (WHERE v AND c) AS added_to_cart,
       COUNT(*) FILTER (WHERE v AND c AND p) AS purchased
FROM s GROUP BY 1 ORDER BY viewed DESC;

-- Purchase cohorts: first-purchase month vs. months later with at least one purchase.
CREATE OR REPLACE VIEW cohort_retention AS
WITH pm AS (
    SELECT DISTINCT user_id, date_trunc('month', event_time)::date AS m
    FROM events WHERE event_type = 'purchase'),
c AS (SELECT user_id, MIN(m) AS cohort FROM pm GROUP BY user_id),
size AS (SELECT cohort, COUNT(*) AS cohort_size FROM c GROUP BY cohort)
SELECT c.cohort, ((EXTRACT(year FROM pm.m) - EXTRACT(year FROM c.cohort)) * 12
                 + EXTRACT(month FROM pm.m) - EXTRACT(month FROM c.cohort))::int AS month_index,
       COUNT(DISTINCT pm.user_id) AS active_users, size.cohort_size,
       ROUND(COUNT(DISTINCT pm.user_id)::numeric / size.cohort_size, 4) AS retention
FROM pm JOIN c USING (user_id) JOIN size ON size.cohort = c.cohort
GROUP BY c.cohort, month_index, size.cohort_size ORDER BY 1, 2;

-- Time from first to second purchase (days), for the "where do first-time buyers stall" question.
CREATE OR REPLACE VIEW second_purchase_gap AS
WITH d AS (
    SELECT user_id, event_time::date AS d FROM events WHERE event_type = 'purchase' GROUP BY 1, 2),
r AS (SELECT user_id, d, ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY d) AS n FROM d)
SELECT a.user_id, a.d AS first_purchase, b.d AS second_purchase, b.d - a.d AS gap_days
FROM r a LEFT JOIN r b ON b.user_id = a.user_id AND b.n = 2
WHERE a.n = 1;
