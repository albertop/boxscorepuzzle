-- `received_at` is written by `keep`, in UTC, and not by a database default.
--
-- ⚠️⚠️ **002 used `DEFAULT CURRENT_TIMESTAMP` and the same expression means two things.** In Postgres it
-- is a `timestamptz`, and casting it into a TEXT column renders it **in the session's timezone** -- the
-- first rows in production read `2026-08-24 23:28:02.569817-04`. In SQLite the same keyword yields
-- `2026-08-25 03:28:02`, in UTC, with no offset. **One migration, one column, two formats**, which is
-- this project's most-recorded defect wearing a database's clothes.
--
-- It also broke the purge: `received_at < cutoff` is a string comparison, and the cutoff is computed in
-- UTC with no offset. Four hours out, and only correct by accident of the year sorting first.
--
-- **So the value comes from one line of Python now** -- `_now()` in `store.py` -- and both engines store
-- the identical string. The default stays as an empty string because SQLite refuses to add a NOT NULL
-- column without one; nothing ever uses it, and `test_received_at_is_utc_from_the_application` is what
-- says so.
--
-- The existing rows are deleted rather than converted. They are eight rows of the operator's own testing
-- from before anybody was given the site, and mixing two formats in one column to preserve them would
-- keep the defect alive to save nothing.

DELETE FROM events;
DELETE FROM shares;
DELETE FROM client_errors;

-- ⚠️ The indexes first. Dropping a column an index names leaves the index broken, and SQLite refuses
-- the ALTER outright: `error in index shares_by_received after drop column`.
DROP INDEX shares_by_received;
DROP INDEX client_errors_by_received;

ALTER TABLE shares        DROP COLUMN received_at;
ALTER TABLE client_errors DROP COLUMN received_at;

ALTER TABLE shares        ADD COLUMN received_at TEXT NOT NULL DEFAULT '';
ALTER TABLE client_errors ADD COLUMN received_at TEXT NOT NULL DEFAULT '';

CREATE INDEX shares_by_received        ON shares (received_at);
CREATE INDEX client_errors_by_received ON client_errors (received_at);

UPDATE keep_schema SET version = 3;
