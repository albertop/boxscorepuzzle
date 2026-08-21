/**
 * The landing page's entry point: load today's puzzle, hand it to the view.
 *
 * ⚠️ **The mirror of `main.js`, and deliberately as thin.** It fetches at the top level and mounts into
 * `#landing`, which is what an entry point is for; everything that draws lives in `landing.js` and takes
 * its boundaries as arguments, so a test can drive the real thing rather than a copy of it.
 */

import { PackageError } from "../../engine/package.js";
import { createStore } from "../../engine/store.js";
import { text } from "../../engine/strings.js";
import { loadPuzzle } from "./daily.js";
import { renderLanding } from "./landing.js";

const root = document.getElementById("landing");

try {
  const { puzzle } = await loadPuzzle();
  // ⚠️ The real store, because the label on the button depends on whether today is already finished —
  // and §23 requires that reading it can fail without taking the page down. `createStore` swallows a
  // storage that throws and answers null, which renders as *play* rather than as an error.
  renderLanding({ puzzle, root, store: createStore(localStorage) });
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
