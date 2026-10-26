CREATE INDEX IF NOT EXISTS ix_events_user_time ON events (user_id, event_time);
CREATE INDEX IF NOT EXISTS ix_events_type_time ON events (event_type, event_time);
CREATE INDEX IF NOT EXISTS ix_events_session   ON events (user_session);
ANALYZE events;
