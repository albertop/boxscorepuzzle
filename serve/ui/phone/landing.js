/**
 * The landing page. `docs/serve-flow.md` §1.
 *
 * ⚠️⚠️ **Every visit lands here, not only the first**, and that is a decision rather than an oversight.
 * The obvious alternative — greet the newcomer, send the returning player straight to the board — is
 * wrong: the archive, the streak and the subscription all live on this page once they exist, and a
 * player routed past it would never meet any of them. A landing page only the newcomer sees is a
 * landing page for a product with no second week.
 *
 * ⚠️ **The example is drawn with the board's own renderers.** `renderLineScore` and `renderSection`,
 * over a real package, with `onSelect` null so nothing is a control. A hand-drawn imitation would be a
 * second definition of the board that drifts the first time the board changes, and nothing would
 * notice — the page advertising the product would quietly stop showing it. Its height is limited in
 * CSS, which is presentation rather than a different board.
 *
 * ⚠️ **Takes its boundaries as arguments** (`doc`, `store`, `today`, `go`) for the reason `shell.js`
 * does: a test drives the real thing rather than a copy of it. `landing-main.js` is the only part that
 * cannot be imported without running.
 */

import { battingCell, battingTotalCell } from "../../engine/columns.js";
import { createGame, isSession } from "../../engine/game.js";
import { longDate, text } from "../../engine/strings.js";
import { columnsFor, renderLineScore, renderSection } from "./board.js";
import { ROUTES, withSearch } from "./daily.js";
import { formatDuration } from "./finish.js";

/** `2026-08-21` from a Date, in local time. ⚠️ Not `toISOString()`, which is UTC and is the previous
 * day for most of the Americas every evening — a daily puzzle dated tomorrow at 8pm is a bug the
 * operator would see and nobody else could reproduce. */
const localIso = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;

export function renderLanding({ puzzle, root, store, doc = document, today = new Date(), go = null }) {
  const page = doc.createElement("div");
  page.className = "landing";
  root.replaceChildren(page);

  // ---- what this is, and what it is not ---------------------------------------------------------
  const name = doc.createElement("h1");
  name.className = "landing-name";
  name.textContent = text("landing.name");

  const tagline = doc.createElement("p");
  tagline.className = "landing-tagline";
  tagline.textContent = text("landing.tagline");

  // ⚠️ A separate line, not a clause. The first thing a visitor assumes about a baseball puzzle is
  // that it asks what they know; every screen after this one depends on them arriving without that
  // idea. It is the line between this and Immaculate Grid (§2, anti-goals).
  const notTrivia = doc.createElement("p");
  notTrivia.className = "landing-not-trivia";
  notTrivia.textContent = text("landing.not_trivia");

  page.append(name, tagline, notTrivia);

  // ---- the example, in the board's own hand -----------------------------------------------------
  const example = doc.createElement("div");
  example.className = "landing-example";
  // A game object with nothing entered: every erased cell is blank, which is what a board looks like
  // before it is solved. Never restored from the store — the example is not the player's session.
  const untouched = createGame(puzzle);
  example.append(renderLineScore(puzzle.puzzle.lineScore, puzzle.offenseIsHome));
  example.append(
    renderSection({
      title: `${text(puzzle.offenseIsHome ? "side.home" : "side.away")} ${text("board.batting")}`,
      columns: columnsFor.batting,
      rows: puzzle.puzzle.batting,
      labels: puzzle.labels,
      slots: puzzle.slotReferences,
      cellName: battingCell,
      totalName: battingTotalCell,
      game: untouched,
      // Null, so `renderSection` draws cells that are not controls at all — no listener, no tab stop,
      // no `role="button"`. An example a screen reader offers to press is a promise the page cannot
      // keep, and it is the same rule a finished board follows.
      onSelect: null,
    }),
  );
  // ⚠️ Hidden from assistive technology, and the caption carries the meaning instead. The example is a
  // picture of a board: to the eye it says *this is what you get*, and read aloud it is ninety numbers
  // and thirty announcements of the word blank before the play button.
  example.setAttribute("aria-hidden", "true");

  const caption = doc.createElement("p");
  caption.className = "landing-caption";
  caption.textContent = text("landing.example_caption");
  page.append(example, caption);

  // ---- the way in ------------------------------------------------------------------------------
  const session = store?.load(puzzle.id) ?? null;
  // ⚠️ **Asked of the engine, never read off the snapshot.** Whether a board is finished is
  // `game.isFinished()` — a snapshot field this page interpreted itself would be a second copy of that
  // rule, on the one screen where being wrong means offering a solved puzzle as if it were new.
  const restored = createGame(puzzle);
  if (session && isSession(session)) restored.restore(session);
  const finished = restored.isFinished();

  const play = doc.createElement("a");
  play.className = "landing-play";
  play.href = withSearch(ROUTES.board);
  // ⚠️ **The label changes when today is done.** Otherwise a returning player is offered a puzzle they
  // have already solved, every day, which reads as the product not knowing who they are. `done.see_boxscore`
  // rather than a second key: it is the same sentence the board uses for the same act.
  play.textContent = finished ? text("done.see_boxscore") : text("landing.play");

  const when = doc.createElement("span");
  when.className = "landing-date";
  when.textContent = longDate(localIso(today));
  play.append(when);
  page.append(play);

  if (finished) {
    const done = doc.createElement("p");
    done.className = "landing-done";
    const verdict = doc.createElement("span");
    verdict.className = "landing-done-verdict";
    verdict.textContent = text("landing.finished");
    const time = doc.createElement("span");
    time.className = "landing-done-time";
    time.textContent = formatDuration(restored.record().duration_ms);
    done.append(verdict, time);
    page.append(done);
  }

  const how = doc.createElement("a");
  how.className = "landing-how";
  how.href = withSearch(ROUTES.tutorial);
  how.textContent = text("landing.how_to_play");
  page.append(how);

  // ⚠️⚠️ **Empty and deliberate. Do not remove as unused** (C9, C8, C10). The archive, the streak and
  // the subscription land in this order, below the way in and above nothing. The slot exists now so
  // that adding them is an append rather than a redesign of the one page every visit passes through —
  // the same discipline as the seams: the shape is present before the feature is.
  const later = doc.createElement("div");
  later.className = "landing-later";
  page.append(later);

  // A test — and a future streak panel — needs to drive this without going through a real anchor.
  if (go) {
    for (const link of [play, how]) {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        go(link.getAttribute("href"));
      });
    }
  }

  return { page, play, how, later, finished, game: restored };
}
