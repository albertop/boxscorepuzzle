/**
 * Which puzzle, and how it is fetched. **One definition, because two pages now need it.**
 *
 * ⚠️ **The engine does not know what day it is (C4).** This is the loader that decides, and for now it
 * reads the manifest and takes an id from the query string so every reference package can be looked at.
 * The real `/today` route is server work and does not live here.
 *
 * ⚠️ **Hoisted out of `main.js` rather than copied into `landing.js`.** The landing page has to know
 * whether today's puzzle is finished, which means it has to load the same puzzle the board loads — and
 * a second copy of the caching rule below is exactly the defect this project meets most often. The two
 * pages ask the same question and get their answer from one place.
 */

import { PackageError, readPackage } from "../../engine/package.js";

const DATA = "../../data/puzzles";

/**
 * The manifest, checked before it is trusted to name a file.
 *
 * ⚠️⚠️ **The package gets rigorous boundary validation and the pointer that selects it got none.**
 * (v36-P3-23) A malformed manifest died as a `TypeError` on `.includes`, and an empty `puzzles` array
 * fetched `.../undefined.json` and failed inside `.json()` as a `SyntaxError`. Both entry points catch
 * and render `package.unreadable`, so the player outcome survived — **but the console carried an
 * unrelated error and the page misdiagnosed its own failure**, which is the shape recorded a day
 * earlier when a storage `SecurityError` was reported as an unreadable puzzle.
 *
 * ⚠️ And this is the one file served `no-store`: the most exposed thing in the tree to a half-written
 * deploy, and the only one that had no check at all.
 */
export function readManifest(raw) {
  const fail = (why) => {
    throw new PackageError(`manifest ${why}`);
  };
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) fail("is not an object");
  if (typeof raw.generation !== "string" || raw.generation === "") {
    fail(`generation is ${JSON.stringify(raw.generation)}, expected a non-empty string`);
  }
  if (!Array.isArray(raw.puzzles) || raw.puzzles.length === 0) {
    fail(`puzzles is ${JSON.stringify(raw.puzzles)}, expected a non-empty array`);
  }
  if (!raw.puzzles.every((id) => typeof id === "string" && id !== "")) {
    fail("puzzles holds something that is not a puzzle id");
  }
  return raw;
}

/**
 * The manifest is a **pointer** and the packages are **immutable**, so they cache differently.
 *
 * ⚠️ **Found the moment the six were regenerated.** The generation directory changed, the manifest was
 * rewritten to name it — and the browser kept serving the old manifest, so the client loaded packages
 * from a retired generation and refused them as the wrong schema. The code was correct and the page was
 * wrong, which is the shape `docs/serve-brief.md` §6 already records once: a prototype reported as *not
 * rendering* that was the cache.
 *
 * A package at `<generation>/<id>.json` can never change — a new one gets a new generation — so it is
 * safe to cache hard. The manifest is the only thing that says which generation is current, and a stale
 * pointer is indistinguishable from a stale build. `no-store`, always.
 *
 * This is the read side of §33's rule that the calendar extends rather than rewrites, and of the
 * caching rule in CLAUDE.md: cache the day's puzzle, never the pointer to it.
 */
export async function loadPuzzle(search = location.search) {
  const manifest = readManifest(await (await fetch(`${DATA}/manifest.json`, { cache: "no-store" })).json());
  const wanted = new URLSearchParams(search).get("p");
  // ⚠️ **An unknown `?p=` falls back to the first puzzle, and that is a development convenience with
  // a decision attached.** (v36-P3-45) Serving different content under the requested id with a 200 is
  // a soft-404 and an unbounded duplicate-URL space; once `/p/<id>` routes exist (C6) a shared link
  // to a retired or mistyped id would render *a different puzzle as if it were the one asked for* —
  // the absence of the requested puzzle reading as the presence of another. The decision is recorded
  // beside C6 in `docs/serve-brief.md` so it is taken rather than invented during the route work.
  const id = manifest.puzzles.includes(wanted) ? wanted : manifest.puzzles[0];
  const raw = await (await fetch(`${DATA}/${manifest.generation}/${id}.json`)).json();
  return { puzzle: readPackage(raw), manifest, id };
}

/**
 * Where the board lives, named once.
 *
 * ⚠️ Both the landing page and the tutorial send the player here, and a page that spells a sibling's
 * filename is a link that breaks silently when the file is renamed — the browser shows a 404 and no
 * test is watching. `serve/tests/engine.test.js` asserts every navigation target is one of these.
 */
export const ROUTES = { board: "play.html", landing: "index.html", tutorial: "tutorial.html" };

/** Carry `?p=` and `?test=` across a navigation, so a specific package survives the landing page. */
export function withSearch(route, search = location.search) {
  const carried = new URLSearchParams();
  const from = new URLSearchParams(search);
  for (const key of ["p", "test"]) {
    if (from.has(key)) carried.set(key, from.get(key));
  }
  const query = carried.toString();
  return query ? `${route}?${query}` : route;
}
