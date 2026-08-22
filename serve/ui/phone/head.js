/**
 * What the page says it is before anyone reads it: the tab, the bookmark, the search result.
 *
 * ⚠️⚠️ **All three pages shipped `<title>boxscore</title>`, hardcoded, identical.** (v36-P2-17) One
 * one-word title for three distinct pages, spelled in three HTML files *and* in the catalogue — four
 * copies of one user-facing string, in a project where C11 is mandatory from day one. It survived
 * because every C11 guard reads `.js` and this lived in markup: **the seam's blind spot was a file
 * extension.**
 *
 * ⚠️ **The `<title>` element is gone from the markup rather than kept and checked.** A copy with a
 * guard over it is still two places saying one thing, which is this project's most-met defect; the
 * cost is that the tab shows the URL for the moment before this module runs, and that is the smaller
 * of the two. The `lang` attribute goes the other way and **stays in the markup**, because a crawler
 * and a screen reader both need it before any script has run — `applyHead` only keeps it in step.
 *
 * ⚠️⚠️ **What this does not fix, stated so nobody reads it as fixed.** A crawler that does not execute
 * JavaScript sees no title and no description, because it sees no body either — the landing page's
 * whole indexable content is client-rendered and gated behind a package fetch (v36-P2-18, open). This
 * module puts the strings in one place and delivers them to every reader that runs scripts, which is
 * every human. **Making them visible to a crawler is server-rendering, and that is the other item.**
 */

import { fill, text } from "../../engine/strings.js";

/**
 * The description each page offers, composed where composing is safer than repeating.
 *
 * ⚠️ The landing page's is built from the two sentences it already shows the visitor, rather than a
 * third copy of the same pitch: `serve-flow.md` §1 says those are what a visitor must meet first, and
 * a description that drifts from the page is worse than none. Joining two whole sentences with a
 * space survives translation; interpolating clauses would not.
 */
const DESCRIPTION = {
  landing: () => `${text("landing.tagline")} ${text("landing.not_trivia")}`,
  board: () => text("page.board.description"),
  tutorial: () => text("page.tutorial.description"),
};

/**
 * Give the document its title, its description and its language, from the catalogue.
 *
 * ⚠️ **The distinguishing part of each title goes first**, because a tab among twenty is about eleven
 * characters wide and that is all a reader gets. `August 22 — boxscore puzzle` says which tab it is;
 * `boxscore puzzle — August 22` truncates to the landing page's tab exactly.
 *
 * @param {"landing" | "board" | "tutorial"} page which of the three shipped pages this is.
 * @param {Record<string, string>} values placeholders for the title, when it has any.
 */
export function applyHead(page, values = null) {
  const describe = DESCRIPTION[page];
  // Fail loudly rather than titling the page after a missing key. A typo here would otherwise ship a
  // page whose tab reads `page.bord.title`, which no test looks at and every player does.
  if (describe === undefined) throw new Error(`no head strings for page ${page}`);

  // `fill` refuses a missing placeholder, so a title gaining one and a caller that does not know is a
  // loud failure rather than a tab reading `{date} — boxscore puzzle`.
  document.title = values === null ? text(`page.${page}.title`) : fill(`page.${page}.title`, values);
  document.documentElement.lang = text("catalog.lang");

  // Created if absent, updated if present — the markup carries none, and a second `<meta>` would leave
  // two descriptions for a scraper to choose between.
  let meta = document.head.querySelector('meta[name="description"]');
  if (meta === null) {
    meta = document.createElement("meta");
    meta.name = "description";
    document.head.append(meta);
  }
  meta.content = describe();
}

/**
 * The title a finished board carries, once the player has earned it.
 *
 * ⚠️ **No time in it, and that is decided rather than left out.** The reveal prints the time, so a
 * screenshot of the *page* carries it either way. A title carries further: into history, into
 * bookmarks, and into screenshots of the **window** — the tab strip, which is the part of a shared
 * screen people forget is visible. **A background tab would go on announcing the result** while the
 * player is doing something else. §26 shares the time because the player chose to; this would be the
 * browser doing it unasked.
 *
 * ⚠️ Only the title changes. The description still describes the page, which is what a description is
 * for, and a solved board is the same page.
 */
export function applySolvedTitle() {
  document.title = text("page.solved.title");
}
