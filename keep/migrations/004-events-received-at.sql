-- `events` gains the arrival stamp the other two tables already have.
--
-- ⚠️⚠️ **The two dates it already carries are the client's and cannot be used for this.**
-- `calendar_date` is the puzzle's day and `played_on` is the player's, both sent from a browser -- and a
-- retention policy that reads either of them is a retention policy a browser can steer. `received_at` is
-- what `keep` observed, written by `store.py` in UTC.
--
-- ⚠️ Existing rows take the empty string, exactly as 003 left `shares` and `client_errors`: the column is
-- NOT NULL because SQLite refuses one without a default, and nothing ever reads the default because the
-- application always supplies a value. **An empty string sorts before every real stamp**, so the rows
-- already in the table are purged on the first sweep -- which is correct: they are the operator's own
-- testing, and the alternative is inventing an arrival time for a row nobody recorded one for.

ALTER TABLE events ADD COLUMN received_at TEXT NOT NULL DEFAULT '';

CREATE INDEX events_by_received ON events (received_at);

UPDATE keep_schema SET version = 4;
