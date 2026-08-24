/**
 * Which puzzle, and how it is fetched. **One definition, because two pages need it.**
 *
 * ⚠️⚠️ **The engine does not know what day it is (C4), and neither does this — it *reads* the day.**
 * `today.json` is a signed pointer the forge wrote at generation and `publish.rotate` copied into the
 * served root once, that morning. So the day is decided server-side, by a process that is not on the
 * play path, and the browser follows a pointer it was handed. **The device clock never enters.** That
 * is E1.3 exactly: everyone gets the same puzzle on the same date, never derived from device-local
 * state.
 *
 * ⚠️⚠️ **`serve` therefore has no rollover arithmetic and no `ROLLOVER_OFFSET_HOURS`.** The plan
 * recorded a third spelling of that constant as owed here; it is not. The forge computes the date to
 * decide what to build, `publish` computes it to decide which pointer to copy, and this consumes it.
 * **A constant with no consumer asserts nothing about behaviour** — it would pass forever while the
 * code it claims to govern did not exist. Two trees compute the date and one reads it.
 *
 * ⚠️ **Hoisted out of `main.js` rather than copied into `landing.js`.** The landing page has to know
 * whether today's puzzle is finished, which means loading the same puzzle the board loads — and a
 * second copy of the rule below is the defect this project meets most often.
 */

import { PackageError, readPackage } from "../../engine/package.js";

const DATA = "/data/puzzles";
/**
 * ⚠️⚠️ **Absolute, and it was relative until E1.** The board page is now served at **two** addresses —
 * `/ui/phone/play.html` and `/p/<id>` — and a relative data path resolves against whichever one the
 * player arrived by. It happened to work at both, by the clamping rule that stops `..` climbing past
 * the root, which is the worst kind of working: correct by an accident nobody chose, on a line that
 * would break the moment the board moved one directory deeper.
 */

export const TODAY = "today.json";
export const YESTERDAY = "yesterday.json";
/**
 * The two days that exist on a public path, named once (`docs/calendar.md`).
 *
 * ⚠️ **Yesterday is a rollover boundary, not a second grace day.** Somebody who sits down at eleven at
 * night would otherwise lose the work at the rollover. It is playable and it does not keep a streak
 * alive; §27 and `docs/calendar.md` carry that pairing and it must be read as a pair.
 */
export const PUBLIC_DAYS = [TODAY, YESTERDAY];

/**
 * A dated pointer, checked before it is trusted to name a file.
 *
 * ⚠️⚠️ **This is `readManifest` with its subject changed, and the finding it came from travels with
 * it.** (v36-P3-23) The package got rigorous boundary validation and the document that *selects* the
 * package got none: a malformed one died as a `TypeError` on `.includes`, and an empty list fetched
 * `.../undefined.json` and failed inside `.json()` as a `SyntaxError`. Both entry points caught it and
 * rendered a sentence, so the player outcome survived — **but the console carried an unrelated error
 * and the page misdiagnosed its own failure.**
 *
 * ⚠️ And this is the one document served `no-store`: the most exposed thing in the tree to a
 * half-written deploy, and the last one that should be believed on sight.
 *
 * The `signature` is **not** checked here and that is decided, not overlooked: `docs/serve-brief.md` §5
 * — a browser verifying a signature it received from the same origin as the verifier is theatre. The
 * signature exists so an ingest step on the VPS can refuse a batch from the wrong key pair.
 */
export function readPointer(raw, where) {
  const fail = (why) => {
    throw new PackageError(`${where} ${why}`);
  };
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) fail("is not an object");
  for (const field of ["date", "puzzle_id"]) {
    if (typeof raw[field] !== "string" || raw[field] === "") {
      fail(`${field} is ${JSON.stringify(raw[field])}, expected a non-empty string`);
    }
  }
  // `YYYY-MM-DD`, because the value is shown to the player and is stamped on every C7 event. A pointer
  // carrying `"soon"` would travel into the event record and be unrecoverable there.
  if (!/^\d{4}-\d{2}-\d{2}$/.test(raw.date)) fail(`date is ${JSON.stringify(raw.date)}, expected YYYY-MM-DD`);

  // ⚠️⚠️ **`next_rotation` is optional and checked when present, and both halves are decided.**
  //
  // **Optional**, because a pointer written before `POINTER_SCHEMA` 2 does not carry it and is otherwise
  // perfectly serviceable — the field feeds a countdown, and a landing page that refuses to render
  // because it cannot say when tomorrow arrives has traded the product for an ornament. What an absent
  // value costs is the countdown line, which is exactly what it is worth.
  //
  // **Checked when present**, because the alternative is `Date.parse` returning `NaN` and a countdown
  // rendering `NaNh NaNm` — a malformed value producing a *displayed* wrong answer rather than a
  // refusal. Validate at the boundary, not downstream.
  if (raw.next_rotation !== undefined) {
    if (typeof raw.next_rotation !== "string" || Number.isNaN(Date.parse(raw.next_rotation))) {
      fail(`next_rotation is ${JSON.stringify(raw.next_rotation)}, expected an ISO instant`);
    }
  }
  return raw;
}

/**
 * A pointer that is absent is **absent**, and that is a different answer from one that is malformed.
 *
 * ⚠️⚠️ **`yesterday.json` legitimately does not exist on the calendar's first day**, so a missing
 * pointer cannot be an error by itself. `null` is the honest value and every caller has to decide what
 * it means where it stands: for `today` it means there is no puzzle today; for `yesterday` it means
 * there is no second day yet.
 */
export async function fetchPointer(name) {
  // ⚠️ `no-store`. A pointer is the one thing in this tree that changes daily, and a cached one serves
  // yesterday's board after the rotation has run — indistinguishable from a rotation that did not run.
  const response = await fetch(`${DATA}/${name}`, { cache: "no-store" });
  if (!response.ok) return null;
  let raw;
  try {
    raw = await response.json();
  } catch (error) {
    throw new PackageError(`${name} is not JSON: ${error.message}`);
  }
  return readPointer(raw, name);
}

/** Today's pointer, or `null` if there is none. Named so `/today` can ask for it without loading a board. */
export function todayPointer() {
  return fetchPointer(TODAY);
}

/**
 * Thrown when there is nothing to serve. **Never a fallback to another package.**
 *
 * ⚠️⚠️ **The fallback is what this exists to forbid.** (v36-P3-45) The loader used to take an unknown
 * `?p=` and serve `manifest.puzzles[0]` instead — a soft-404: a 200 carrying *a different puzzle as if
 * it were the one asked for*, and an unbounded duplicate-URL space. With `/p/<id>` routed and shared
 * links in play, that is a person following a friend's link and solving somebody else's board while
 * believing they solved this one. **The absence of the requested puzzle must not read as the presence
 * of another.**
 */
export class NoPuzzle extends Error {
  constructor(message) {
    super(message);
    this.name = "NoPuzzle";
  }
}

/**
 * The id in `/p/<id>`, or `null` on any other path.
 *
 * ⚠️ Anchored and character-classed rather than split on `/`: a package id is hex from the forge, and
 * a path segment that is anything else is not a request for a puzzle. `docs/calendar.md` records that
 * the opaque id is load-bearing twice — it stops a player looking the *game* up, and it stops anyone
 * enumerating the *future* — so accepting a loose segment here would widen a surface chosen narrow.
 */
export function idInPath(pathname = location.pathname) {
  const found = /^\/p\/([0-9a-f]+)\/?$/.exec(pathname);
  return found ? found[1] : null;
}

/**
 * Today's puzzle, or the one `/p/<id>` names if it is one of the two public days.
 *
 * ⚠️⚠️ **A stale pointer is served, deliberately, and this is the paragraph that has to stop somebody
 * adding the check.** Detecting staleness means comparing the pointer's date against *today's* — and
 * knowing what today is, in the browser, is precisely what E1.3 forbids as a basis for choosing a
 * puzzle. Any client-side staleness test reintroduces the device clock through the back door: a player
 * whose laptop is a day fast would be shown an error about a file that is perfectly current.
 *
 * **Staleness is detected server-side and it already is** — `publish.health.inspect()` compares the
 * pointer's date to the serving date and turns red, which is what F3 exposes to monitoring. That is the
 * right place: one observer with the right clock, not every visitor with their own.
 *
 * ⚠️ The public path is **flat** — `<id>.json`, not `<generation>/<id>.json`. The generation lives in
 * the pointer because the *rotation* needs it to find the file in the private inventory; nothing the
 * browser does requires it.
 */
export async function loadPuzzle(pathname = location.pathname) {
  const wanted = idInPath(pathname);
  const pointers = [];
  for (const name of PUBLIC_DAYS) {
    const pointer = await fetchPointer(name);
    if (pointer !== null) pointers.push(pointer);
  }
  if (pointers.length === 0) {
    throw new NoPuzzle(`no ${TODAY}: there is nothing to serve`);
  }

  const chosen = wanted === null ? pointers[0] : pointers.find((pointer) => pointer.puzzle_id === wanted);
  if (chosen === undefined) {
    // ⚠️ The requested id is not one of the two public days. It may be a real past puzzle — the archive
    // is what §9 sells — a retired one, or a typo, and **this cannot tell them apart and must not
    // pretend to.** What it can say is that this address has nothing behind it today.
    throw new NoPuzzle(`${wanted} is not one of the ${pointers.length} public days`);
  }

  // ⚠⚠ **No `cache:` mode, and asking for `force-cache` here was wrong twice.** A package is
  // immutable and should be cached for a year — but that is a *response header the server sets* (E2.1),
  // not something the client demands, and a request mode cannot make a response cacheable. It also hung
  // the headless suite outright while working in a normal browser, which is the worse half: a client
  // instruction that behaves differently depending on whether a cache exists.
  const response = await fetch(`${DATA}/${chosen.puzzle_id}.json`);
  if (!response.ok) {
    // ⚠️⚠️ **A pointer naming a package that is not there.** The health check calls this a 404 on the
    // only game the product has; from in here it is the same refusal as an absent pointer, because the
    // alternative is serving something else.
    throw new NoPuzzle(`${chosen.puzzle_id} is named by ${chosen.date} and is not on the public path`);
  }
  return {
    puzzle: readPackage(await response.json()),
    calendarDate: chosen.date,
    id: chosen.puzzle_id,
    // ⚠️⚠️ **The instant the day turns, read rather than computed, and that is the whole point of the
    // field.** E1.2 settled that `serve` consumes calendar facts and derives none, and a browser test
    // refuses any player-page source that reaches for `ROLLOVER_OFFSET_HOURS` or a timezone offset. A
    // countdown needs the boundary; computing it here would be a third spelling of a constant that
    // exists in two trees, in the tree that is not allowed to know it.
    //
    // ⚠️ `null` rather than absent when the pointer predates it, so a caller destructuring this gets a
    // value that says *no* instead of `undefined`, which reads as a field nobody set.
    nextRotation: chosen.next_rotation ?? null,
  };
}

/**
 * Where the pages live, named once — **canonical URLs, not filenames.**
 *
 * ⚠️⚠️ **These were `play.html`, `index.html` and `tutorial.html`, and under E3's routing both landing
 * buttons were dead.** A relative filename resolves against the *page's* address: from `/`, `play.html`
 * is `/play.html`, which is not a route and which nginx answers with 404. **The entire way into the
 * game, on the address every visit lands at.**
 *
 * ⚠️⚠️ **And the test could not see it, because the test supplied the missing part.** It fetched
 * `../ui/phone/${file}` — prefixing the directory whose absence *is* the defect. That is the shape
 * `CLAUDE.md` records from the text dump that padded its own columns: an instrument supplying the
 * property under judgement, so the sample cannot judge it.
 *
 * ⚠️ **`board` is `/today` rather than `/p/<id>`**, because a link cannot know today's id — the pointer
 * does. `/today` resolves it and replaces itself with the canonical board URL.
 *
 * These are the addresses `tools/dev_server.py`'s `ROUTES` and `deploy/nginx/boxscorepuzzle.conf` both
 * serve, and `forge/tests/test_nginx_serves_what_is_declared.py` requires every one of them to answer.
 */
export const ROUTES = { board: "/today", landing: "/", tutorial: "/tutorial" };

/**
 * Carry `?test=` across a navigation.
 *
 * ⚠️⚠️ **`?p=` is gone and its removal is the whole of E1.1.** It selected a package by query string,
 * which was development scaffolding from before there was a calendar: it made every reference package
 * reachable by hand. With `/p/<id>` canonical (C6) the id belongs in the path, and leaving the
 * parameter would have been a second way to ask the same question — one of them unrouted, neither
 * checked against the other.
 */
export function withSearch(route, search = location.search) {
  const carried = new URLSearchParams();
  const from = new URLSearchParams(search);
  if (from.has("test")) carried.set("test", from.get("test"));
  const query = carried.toString();
  return query ? `${route}?${query}` : route;
}
