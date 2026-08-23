/**
 * The landing page's entry point: load today's puzzle, hand it to the view.
 *
 * ⚠️ **The mirror of `main.js`, and deliberately as thin.** It fetches at the top level and mounts into
 * `#landing`, which is what an entry point is for; everything that draws lives in `landing.js` and takes
 * its boundaries as arguments, so a test can drive the real thing rather than a copy of it.
 */

import { PackageError } from "../../engine/package.js";
import { browserStorage, createStore } from "../../engine/store.js";
import { text } from "../../engine/strings.js";
import { loadPuzzle } from "./daily.js";
import { renderLanding } from "./landing.js";
import { applyHead } from "./head.js";
import { startUplink } from "../../engine/uplink.js";

// The tab, the bookmark and the search result, from the catalogue rather than the markup
// (v36-P2-17). Before anything is fetched: a page whose puzzle fails to load still has a name.
applyHead("landing");

const root = document.getElementById("landing");

/**
 * ⚠️⚠️ **`browserStorage()`, and outside the `try` below. Both halves matter.** (v35-P2-01)
 *
 * This read the global `localStorage` directly. `createStore` guards `getItem`, `setItem` and
 * `removeItem` — it cannot guard the property access that produces the object, and in a browser with
 * storage denied **reading `window.localStorage` throws before `createStore` is ever called**.
 * `browserStorage()` exists for exactly that: its `try` wraps the access, and it answers with something
 * that accepts everything and remembers nothing. The board has always used it; the new default entry
 * page did not, so the defensive path regressed on the one screen every visit now passes through.
 *
 * **And it is acquired here rather than inside the `try`, because that catch means something else.**
 * Left where it was, a storage `SecurityError` would have been caught by the package handler and shown
 * the visitor *this puzzle cannot be read* — a true failure reported as an entirely different one, on a
 * page whose puzzle was fine. §23 says play survives a backend failure; a page that misdiagnoses its
 * own failure is worse than one that falls over, because the report sends the reader somewhere else.
 */
const storage = browserStorage();
const store = createStore(storage);

// ⚠️ **The landing page reports its own errors and drains the queue too** (C3, C4). Every visit lands
// here, so a visitor who never opens a board is still the visit where yesterday's undelivered event goes
// out — and an exception on this page is the one most likely to stop somebody reaching the game at all.
startUplink({ storage });

try {
  const { puzzle } = await loadPuzzle();
  renderLanding({ puzzle, root, store });
} catch (error) {
  root.replaceChildren();
  const message = document.createElement("p");
  message.className = "landing-tagline";
  // The visitor sees the catalogued sentence; the console keeps what actually went wrong.
  message.textContent = text("package.unreadable");
  root.append(message);
  if (error instanceof PackageError) console.error("package refused:", error.message);
  else throw error;
}
