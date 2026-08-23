-- keep, schema 1.
--
-- Migrations are manual and keep refuses to start against a version it does not expect
-- (docs/data-layer.md section 7). Run this, then start the service. Nothing migrates on boot:
-- a deploy that alters the database at three in the morning is the one failure a rollback does not undo.

CREATE TABLE keep_schema (version INTEGER NOT NULL);
INSERT INTO keep_schema (version) VALUES (1);

-- The C7 event record. event_id is the primary key and comes from the client, made when the event is
-- created rather than when it is sent: the client cannot tell a lost response from a request that never
-- arrived, so it retries, and the key is what makes the retry free.
CREATE TABLE events (
    event_id          TEXT PRIMARY KEY,
    device_id         TEXT NOT NULL,
    -- Present and null until there are accounts. The event is claimable: registering attaches an
    -- account to a device's history, and a subject that is one fixed column cannot become claimable
    -- later without rewriting the history C7 exists to keep.
    account_id        TEXT,
    puzzle_id         TEXT NOT NULL,
    -- Two dates on two different clocks. calendar_date is the system's -- August 22nd's puzzle is
    -- August 22nd's everywhere. played_on is the player's: stored in UTC, somebody in California
    -- playing at eleven at night is recorded as having played the next day, and the row does not carry
    -- what it would take to correct that.
    calendar_date     TEXT,
    played_on         TEXT,
    duration_ms       INTEGER NOT NULL,
    hints             INTEGER NOT NULL,
    errors            INTEGER NOT NULL,
    failed_checks     INTEGER NOT NULL,
    highest_technique TEXT,
    solved            BOOLEAN NOT NULL,
    assisted          BOOLEAN NOT NULL
);

-- Uncaught client errors. No IP and no geolocation (section 35): a user agent and a viewport are what
-- reproduce a rendering fault, and anything past that is collected because it was easy.
CREATE TABLE client_errors (
    error_id   TEXT PRIMARY KEY,
    device_id  TEXT NOT NULL,
    message    TEXT NOT NULL,
    stack      TEXT NOT NULL,
    page       TEXT NOT NULL,
    viewport   TEXT NOT NULL,
    user_agent TEXT NOT NULL
);

-- The health check runs a real query against keep_schema, which always has exactly one row. An index is
-- pointless on a one-row table; the point is that the table exists and the query does not error, which
-- SELECT 1 alone cannot say.
CREATE INDEX events_by_device ON events (device_id);
CREATE INDEX events_by_calendar_date ON events (calendar_date);
