/**
 * The tutorial's entry point.
 *
 * ⚠️ **It fetches nothing, and that is the point rather than an accident.** The tutorial teaches on a
 * made-up board, so it needs no package, no manifest, no store and no network — which means it cannot
 * fail the way the other two pages can. The one screen a stranger is most likely to open first is the
 * one with nothing to go wrong.
 */

import { renderTutorial } from "./tutorial.js";
import { applyHead } from "./head.js";
import { startUplink } from "../../engine/uplink.js";

// The tab, the bookmark and the search result, from the catalogue rather than the markup
// (v36-P2-17). Before anything is fetched: a page whose puzzle fails to load still has a name.
applyHead("tutorial");

// ⚠️ **Even here, where nothing is fetched.** The tutorial cannot fail the way the other two pages
// can, which is an argument about *likelihood* and not about coverage: an uncaught error on the screen a
// stranger opens first is the one there is least chance of hearing about any other way.
startUplink();

renderTutorial({ root: document.getElementById("tutorial") });
