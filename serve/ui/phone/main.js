/**
 * The entry point: pick a puzzle, hand it to the shell.
 *
 * ⚠️ **This file is deliberately the only part that cannot be imported without running.** It fetches
 * at the top level and mounts into `#app`, which is what an entry point is for. Everything that draws
 * lives in `shell.js` and takes its boundaries as arguments, so a test can drive the real thing — see
 * the note there.
 *
 * ⚠️ **The engine does not know what day it is** (C4). This loader decides which puzzle, and for now it
 * reads the manifest and takes an id from the query string so every reference package can be looked at.
 * The real `/today` route is shell work and does not live here.
 */

import { PackageError, readPackage } from "../../engine/package.js";
import { boot } from "./shell.js";
import { text } from "../../engine/strings.js";

const DATA = "../../data/puzzles";

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
async function loadPuzzle() {
  const manifest = await (await fetch(`${DATA}/manifest.json`, { cache: "no-store" })).json();
  const wanted = new URLSearchParams(location.search).get("p");
  const id = manifest.puzzles.includes(wanted) ? wanted : manifest.puzzles[0];
  const raw = await (await fetch(`${DATA}/${manifest.generation}/${id}.json`)).json();
  return { puzzle: readPackage(raw), manifest, id };
}

try {
  boot(await loadPuzzle());
} catch (error) {
  const app = document.getElementById("app");
  app.replaceChildren();
  const message = document.createElement("p");
  message.style.padding = "1rem";
  // The player sees the catalogued sentence; the console keeps what actually went wrong.
  message.textContent = text("package.unreadable");
  app.append(message);
  if (error instanceof PackageError) console.error("package refused:", error.message);
  else throw error;
}
