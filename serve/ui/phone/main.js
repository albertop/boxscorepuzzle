/**
 * The entry point: pick a puzzle, hand it to the shell.
 *
 * ⚠️ **This file is deliberately the only part that cannot be imported without running.** It fetches
 * at the top level and mounts into `#app`, which is what an entry point is for. Everything that draws
 * lives in `shell.js` and takes its boundaries as arguments, so a test can drive the real thing — see
 * the note there.
 *
 * ⚠️ **Which puzzle, and the caching rule that goes with it, moved to `daily.js`.** The landing page
 * has to load the same puzzle this page loads — it decides whether to say *Play* or *See the
 * boxscore* — and a second copy of that rule is the defect this project meets most often.
 */

import { PackageError } from "../../engine/package.js";
import { boot } from "./shell.js";
import { loadPuzzle } from "./daily.js";
import { localIso, shortDate, text } from "../../engine/strings.js";
import { applyHead } from "./head.js";

// The tab, the bookmark and the search result, from the catalogue rather than the markup
// (v36-P2-17). Before anything is fetched: a page whose puzzle fails to load still has a name.
//
// ⚠️ **Today's date, so a tab among twenty says which one this is.** It comes from the clock rather
// than from the package, which is deliberate: the title must be right before the fetch resolves, and
// a board that fails to load should still be `August 22 — boxscore puzzle` rather than nameless.
applyHead("board", { date: shortDate(localIso(new Date())) });

try {
  const loaded = await loadPuzzle();
  // ⚠️⚠️ **The only route to the development test mode, and it is a dynamic import inside the branch.**
  // A normal load never fetches `testmode.js` at all — the file is not part of the page unless the
  // parameter is there, which is a stronger property than a module that loads and declines to act.
  // `serve/tests/engine.test.js` asserts this shape by reading this file; changing it to a top-level
  // import turns that test red.
  const mode = new URLSearchParams(location.search).get("test");
  const test = mode ? await import("./testmode.js") : null;
  const shell = boot({ ...loaded, fresh: test?.startsFresh(mode) === true });
  if (test) test.applyTestMode(mode, { ...shell, history });
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
