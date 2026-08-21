/**
 * The tutorial's entry point.
 *
 * ⚠️ **It fetches nothing, and that is the point rather than an accident.** The tutorial teaches on a
 * made-up board, so it needs no package, no manifest, no store and no network — which means it cannot
 * fail the way the other two pages can. The one screen a stranger is most likely to open first is the
 * one with nothing to go wrong.
 */

import { renderTutorial } from "./tutorial.js";

renderTutorial({ root: document.getElementById("tutorial") });
