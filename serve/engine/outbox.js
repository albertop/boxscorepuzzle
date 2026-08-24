/**
 * The queue between a finished game and `keep`. **Nothing in the play path waits on it** (§23).
 *
 * ⚠️⚠️ **Write first, send after, and delete only on confirmation.** The order is the whole design.
 * An item is in `localStorage` before any request is made, so a phone that is swiped away mid-flight
 * still holds it; it leaves storage only when the server says which ids it now holds. **A reload
 * during a request therefore re-sends**, which is exactly why every item carries an id the server
 * deduplicates on (`docs/keep-api.md`).
 *
 * ⚠️ **`add()` is synchronous and returns immediately.** It kicks a drain and does not await it. A
 * caller that awaited delivery would put the network in the play path, which §23 forbids — the daily
 * plays with `keep` down, with the backend absent, and on a plane.
 *
 * ⚠️⚠️ **A refusal the client cannot fix by waiting is dropped; everything else stays.** The line is
 * narrow on purpose: only 400, 413 and 422 — *the server understood the item and refused its content*.
 * A 404 stays queued, because a route can appear with the next deploy and beta 0 will run against a
 * `serve` that does not proxy these paths yet; dropping on 404 would discard every event recorded
 * before deployment, silently, which is the one loss C7 cannot recover from.
 */

import { newId } from "./device.js";

export const OUTBOX_PREFIX = "boxscorepuzzle.outbox.v1.";

/**
 * The three paths on **`serve`**, not on `keep`.
 *
 * ⚠️ The browser never reaches `keep`: its port is not published and the shared token must not travel
 * to a browser (`data-layer.md` §4). `serve` proxies these, adding the token at the edge — the same
 * arrangement as the health check and the payment webhook.
 */
export const EVENTS_PATH = "/api/events";
export const ERRORS_PATH = "/api/errors";
export const SHARES_PATH = "/api/shares";

/**
 * The statuses that mean *this item will never be accepted*.
 *
 * ⚠️ Deliberately not "any 4xx". 401 means the deployment's token is wrong, 408 and 429 are the server
 * asking for patience, 404 means a route that does not exist **yet** — all of them are fixed by a
 * change on the other side, and none is a reason to throw away a game somebody played.
 */
const REFUSED_FOREVER = new Set([400, 413, 422]);

/**
 * A queue, given somewhere to put it and something to send with.
 *
 * @param {Storage} storage the same object `createStore` and `deviceId` are given.
 * @param {object} options
 * @param {string} options.name the envelope key `keep` expects: `events` or `errors`.
 * @param {string} options.path where to post it on `serve`.
 * @param {string} options.idField `event_id` or `error_id` — what the server deduplicates on.
 * @param {number} options.capacity how many items to keep before the oldest are dropped.
 * @param {Function} [options.send] the transport, injected so this is testable without a network.
 */
export function createOutbox(storage, { name, path, idField, capacity, send = post }) {
  const key = `${OUTBOX_PREFIX}${name}`;
  /** The pass in the air, and the one call booked behind it. See `drain()` for why there are two. */
  let running = null;
  let follower = null;
  /**
   * ⚠️ **Items a full or blocked storage refused.** A device in private browsing would otherwise queue
   * nothing and deliver nothing; this keeps them for as long as the tab lives, which is the most that
   * can honestly be promised when there is nowhere to write them down.
   */
  let unstored = [];

  const identify = (item) => item?.[idField];

  const read = () => {
    try {
      const raw = storage.getItem(key);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      // ⚠️ A hand-edited or half-written queue reads as empty rather than throwing on the play path.
      // The same rule as the session store: malformed persistence may cost a session, never a board.
      return Array.isArray(parsed) ? parsed.filter((item) => typeof identify(item) === "string") : [];
    } catch {
      return [];
    }
  };

  const write = (items) => {
    try {
      storage.setItem(key, JSON.stringify(items));
      return true;
    } catch {
      return false;
    }
  };

  const all = () => [...read(), ...unstored];

  /**
   * Take the settled ids out, **re-reading first** so an item queued during the flight is not lost.
   * A queue held in a variable across an await is a queue that clobbers whatever arrived meanwhile.
   */
  const settle = (ids) => {
    const gone = new Set(ids);
    unstored = unstored.filter((item) => !gone.has(identify(item)));
    write(read().filter((item) => !gone.has(identify(item))));
  };

  const deliver = async (items) => {
    try {
      const answer = await send(path, { [name]: items });
      if (answer?.ok) return { stored: answer.stored ?? [], refused: false };
      return { stored: [], refused: REFUSED_FOREVER.has(answer?.status) };
    } catch {
      // ⚠️ A thrown fetch is the ordinary offline case. It is not a refusal and nothing is dropped.
      return { stored: [], refused: false };
    }
  };

  const pass = async () => {
    const queued = all();
    if (queued.length === 0) return { sent: [], dropped: [] };

    const first = await deliver(queued);
    const sent = [...first.stored];
    const dropped = [];

    if (first.refused) {
      if (queued.length === 1) {
        dropped.push(identify(queued[0]));
      } else {
        // ⚠️⚠️ **One malformed item must not hold the queue behind it.** `keep` refuses a batch whole —
        // correctly, since a client cannot be told *some of that landed* without being told which — but
        // that makes one bad record a permanent blockage in front of every good one after it. Sending
        // them alone finds the poisoned one and keeps the rest, and the id makes the extra attempt free.
        for (const item of queued) {
          const alone = await deliver([item]);
          if (alone.stored.length > 0) sent.push(identify(item));
          else if (alone.refused) dropped.push(identify(item));
        }
      }
    }

    settle([...sent, ...dropped]);
    return { sent, dropped };
  };

  /**
   * Drain, serialised.
   *
   * ⚠️⚠️ **Single flight, and a *follower* rather than a refusal — the refusal was a bug.** The first
   * version answered `{sent: [], dropped: []}` while another pass was running, which is what "two at
   * once must not send twice" seemed to ask for. But `add()` kicks, so **an event queued while a flight
   * was in the air was answered *nothing to do* and then never drained** — it sat in storage until the
   * next `online` or `visibilitychange`, and on a device that stayed connected the whole time, until the
   * next visit. Exactly the shape this project keeps meeting: a guard that returns a plausible answer
   * for a case it was never thinking about.
   *
   * So a call arriving mid-flight books **one** pass after the current one, and every caller that
   * arrives before it starts shares it. At most two passes exist, no two ever overlap, and nothing that
   * was queued before the last pass started can be left behind.
   */
  function drain() {
    if (!running) return start();
    if (!follower) {
      // ⚠️ `catch` rather than `then` alone: a pass that rejects must not strand every later drain on a
      // promise chain that never continues. Nothing here is allowed to be the reason a queue stops.
      follower = running.catch(() => {}).then(() => {
        follower = null;
        return start();
      });
    }
    return follower;
  }

  function start() {
    running = (async () => {
      try {
        return await pass();
      } finally {
        running = null;
      }
    })();
    return running;
  }

  const kick = () => {
    // ⚠️ Not awaited, and its rejection is swallowed here rather than reaching an unhandled promise —
    // which the error reporter would then post, making a failed upload report itself as a bug.
    void drain().catch(() => {});
  };

  return {
    key,

    /**
     * Queue one item. **Returns whether it was accepted**, and no caller may refuse to continue because
     * it was not.
     *
     * ⚠️ An item already queued under the same id is not queued twice. The id is the identity of the
     * thing, not of the attempt.
     */
    add(item) {
      const id = identify(item);
      // An item with no id can never be deduplicated and `keep` would refuse it forever. Refused here
      // rather than queued: a queue that cannot drain is worse than a lost item, because it also blocks
      // everything behind it.
      if (typeof id !== "string" || id === "") return false;
      if (all().some((each) => identify(each) === id)) return true;

      // ⚠️ **The oldest go first when the cap is reached.** The queue only grows while delivery is
      // failing, and the older an undelivered item is the more likely its context has gone — a puzzle
      // rotated out of the archive, a stack trace from a build no longer deployed.
      if (write([...read(), item].slice(-capacity))) {
        unstored = unstored.filter((each) => identify(each) !== id);
      } else {
        unstored = [...unstored, item].slice(-capacity);
      }
      kick();
      return true;
    },

    /** What is waiting, storage and memory together. For tests, and for a status line that may exist later. */
    pending: () => all(),

    drain,

    /**
     * Drain now, and whenever the browser suggests it might work.
     *
     * ⚠️ **`visibilitychange`, not `beforeunload`.** A swiped-away tab on a phone is killed rather than
     * closed, so anything waiting for an unload event delivers on a desktop and silently never on the
     * device the board was designed for.
     */
    follow(target = globalThis) {
      const wake = () => kick();
      target.addEventListener?.("online", wake);
      target.addEventListener?.("visibilitychange", wake);
      kick();
      return () => {
        target.removeEventListener?.("online", wake);
        target.removeEventListener?.("visibilitychange", wake);
      };
    },
  };
}

/**
 * The default transport.
 *
 * ⚠️ **An `ok` response whose body will not parse leaves everything queued**, rather than assuming it
 * landed. The cost is a re-send the server deduplicates; the alternative is dropping an event on a
 * proxy's HTML error page, which is the failure that cannot be undone.
 */
async function post(path, body) {
  const answer = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let stored = [];
  try {
    stored = (await answer.json())?.stored ?? [];
  } catch {
    stored = [];
  }
  return { ok: answer.ok, status: answer.status, stored: Array.isArray(stored) ? stored : [] };
}

/** 500 finished games is more than a year of daily play, at roughly 300 bytes each. */
export function eventOutbox(storage, send) {
  return createOutbox(storage, { name: "events", path: EVENTS_PATH, idField: "event_id", capacity: 500, send });
}

/**
 * The id one finished game gets.
 *
 * ⚠️⚠️ **Derived from the device and the puzzle rather than a fresh UUID**, and the cost is worth
 * stating. `keep-api.md` asks that the id be made when the event is *created* and not when it is
 * *sent*; a UUID satisfies that and this satisfies it more strongly — a board reopened after a reload,
 * or a reveal shown twice, produces **the same id**, so the duplicate is impossible rather than merely
 * deduplicated. It needs no ledger of what has already been queued and no new field in the session,
 * both of which would be a second mechanism for one problem.
 *
 * ⚠️ **What it costs:** a device records exactly one event per puzzle, ever. A deliberate replay of an
 * archived board would be silently discarded. Nothing in §27 says a replay should count — yesterday's
 * board does not count for the streak either — so the safer direction is the one taken. **If replays
 * are ever meant to record, this is the line that changes**, into a fresh id per play.
 */
export const eventId = (record) => `${record.device_id ?? "anonymous"}:${record.puzzle_id}`;

/**
 * The error outbox. **Smaller, because a render loop is what it has to survive** — and one report is
 * worth less on its own than one event is.
 */
export function errorOutbox(storage, send) {
  return createOutbox(storage, { name: "errors", path: ERRORS_PATH, idField: "error_id", capacity: 40, send });
}

/**
 * The share outbox. **The growth mechanism's only measurement, so it queues like everything else.**
 *
 * ⚠️⚠️ **It must not block the share.** The player presses Share, the sheet opens, and the record goes
 * in this queue — a network round trip between the press and the sheet would put latency on the one
 * action the product's growth depends on (G2: *any friction here is friction on the only growth
 * mechanism the product has*). §23 is the same rule from the other side: the play path never waits on
 * the backend.
 *
 * ⚠️ **Small, like the error queue and unlike the event queue.** A device produces at most one share
 * per puzzle (see `shareId`), so a queue that survived a fortnight offline would hold a fortnight of
 * them; 40 is far past any real backlog and short of anything that costs storage.
 */
export function shareOutbox(storage, send) {
  return createOutbox(storage, { name: "shares", path: SHARES_PATH, idField: "share_id", capacity: 40, send });
}

export { newId as reportId };
