-- Purge needs something to age a row by, and neither table had one.
--
-- `shares.shared_on` is the player's play date and is nullable; `client_errors` carried no date at all.
-- Both are what the client said, and a retention policy must not be steerable from a browser. This is
-- when the row arrived here.
--
-- Existing rows take the current time, so they start ageing from this migration rather than being
-- purged on the first run.
--
-- CURRENT_TIMESTAMP rather than now(): both engines have it, and 001 is written the same way.

ALTER TABLE shares        ADD COLUMN received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE client_errors ADD COLUMN received_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE INDEX shares_by_received        ON shares (received_at);
CREATE INDEX client_errors_by_received ON client_errors (received_at);

UPDATE keep_schema SET version = 2;
