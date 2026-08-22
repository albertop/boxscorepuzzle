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
  // ⚠️ Hidden from assistive technology. The example is a *picture* of a board: to the eye it says
  // "this is what you get", and read aloud it is ninety numbers and thirty announcements of the word
  // blank before the play button. The tagline above carries the meaning for a reader who cannot see
  // it — which is what the caption below it used to do, before the caption said nothing new.
  example.setAttribute("aria-hidden", "true");

  // ⚠️ **The caption is gone.** It read "A real game, most of it missing. You put it back" — the first
  // half repeats the tagline and the second describes what the fade already shows. A line that
  // restates the picture beneath it is a line the eye learns to skip, and it was sitting between the
  // example and the only button on the page.
  page.append(example);

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

  // ⚠️⚠️ **Directly under the button, in the same block.** It used to sit at the bottom of the page,
  // after the reserved slot, separated from everything. **Somebody arriving without knowing what this
  // is presses the big button, meets an empty board, and leaves** — they have to see the way in
  // *before* they choose, not after they have already chosen wrong.
  //
  // ⚠️ No underline: next to a filled button, an underlined link reads as small print rather than as
  // the second of two choices. It keeps its own 44px target.
  const how = doc.createElement("a");
  how.className = "landing-how";
  how.href = withSearch(ROUTES.tutorial);
  how.textContent = text("landing.how_to_play");

  const way = doc.createElement("div");
  way.className = "landing-way";
  way.append(play, how);
  page.append(way);

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


  // ⚠️⚠️ **Empty and deliberate. Do not remove as unused** (C9, C8, C10). The archive, the streak and
  // the subscription land in this order, below the way in and above nothing. The slot exists now so
  // that adding them is an append rather than a redesign of the one page every visit passes through —
  // the same discipline as the seams: the shape is present before the feature is.
  const later = doc.createElement("div");
  later.className = "landing-later";
  page.append(later);

  // ⚠️⚠️ **Retrosheet's attribution is a condition of using their data, not a courtesy**, and every
  // board in this product is built from their event files. Quoted verbatim from the catalogue —
  // paraphrasing an attribution clause is how a condition stops being met.
  //
  // Small and grey at the end of the page, which is where a licence notice belongs and where the legal
  // links will join it. `<footer>` rather than a `<p>`, so it is a landmark a screen reader can skip.
  const footer = doc.createElement("footer");
  footer.className = "landing-footer";
  footer.textContent = text("landing.retrosheet");
  page.append(footer);

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
