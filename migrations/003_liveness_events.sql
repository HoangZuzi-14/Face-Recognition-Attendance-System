-- Liveness analytics schema for recognition_events.
-- Runtime migration is implemented idempotently in app.database.init_db().

-- Add these columns to recognition_events when they are missing:
-- liveness_score REAL
-- liveness_label TEXT
-- attack_type TEXT
-- liveness_reasons TEXT
-- recognition_score REAL

-- Expected decision values for liveness-aware events:
-- ACCEPT
-- REJECT_SPOOF
-- REJECT_UNKNOWN
-- CHALLENGE_REQUIRED
