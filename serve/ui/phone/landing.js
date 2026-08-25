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
import { localDate } from "../../engine/device.js";
import { localIso, longDate, text } from "../../engine/strings.js";
import { columnsFor, renderLineScore, renderSection } from "./board.js";
import { ROUTES, withSearch } from "./daily.js";
import { formatDuration, shareIcon } from "./finish.js";

export function renderLanding({
  puzzle,
  root,
  store,
  doc = document,
  today = new Date(),
  go = null,
  // ⚠️⚠️ **Share is offered here and it is the second half of the exit.** A player who finishes leaves
  // through `Go home` and arrives at a page that congratulates them and offers no way to tell anybody —
  // so the one growth mechanism the product has would sit on a screen they have already left. The
  // button is on both, and `share-result.js` is the one path under both.
  //
  // ⚠️ **Optional, and its absence hides the button rather than breaking it.** §23: the landing renders
  // with no store, no queue and no network. A share needs a rasteriser and a send path; when the caller
  // has not wired them there is nothing to press, which is different from a control that fails.
  onShare = null,
  // ⚠️ The three fields `record()` needs. See `restored` below: without them the share it produces names
  // an event that does not exist.
  deviceId = null,
  calendarDate = null,
}) {
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
  // ⚠️⚠️ **The same identity the board builds its game with, and this used to pass NONE.**
  // `createGame(puzzle)` gives a game whose `record()` has `device_id`, `calendar_date` and `played_on`
  // all null -- and the share built from it takes its `event_id` from
  // `${record.device_id ?? "anonymous"}:${record.puzzle_id}`. **Three of the first five shares in
  // production reached `keep` as `anonymous:<puzzle>`, matching no event that exists.**
  //
  // ⚠️ **A value that looks like a link and points at nothing** is worse than a null: the column was
  // populated, so nothing looked wrong, and 60% of the shares were unattributable. The share is the one
  // growth mechanism the product has, and measuring it is what beta 0 is for.
  //
  // ⚠️ `playedOn` is today because this button only exists on a day already finished -- the landing
  // offers no share for any other date.
  const restored = createGame(puzzle, undefined, { deviceId, calendarDate, playedOn: localDate(today) });
  if (session && isSession(session)) restored.restore(session);
  const finished = restored.isFinished();

  const play = doc.createElement("a");
  play.className = "app-button landing-play";
  play.href = withSearch(ROUTES.board);
  // ⚠️ **The label changes when today is done.** Otherwise a returning player is offered a puzzle they
  // have already solved, every day, which reads as the product not knowing who they are.
  //
  // ⚠️⚠️ **`landing.see_board`, and it deliberately stops sharing a key with the board.** This was
  // `done.see_boxscore`, with a comment calling the shared sentence deliberate — *the same sentence the
  // board uses for the same act*. **It is not the same act.** From here the player goes to the BOARD,
  // and the finished board is what then offers the boxscore. The old label named the second step from
  // the first step's button.
  play.textContent = finished ? text("landing.see_board") : text("landing.play");

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

  // ⚠️⚠️ **Beside the way in, not below the congratulation, and the two placements are not equivalent.**
  // Where `Play today's puzzle` sits is the one thing on this page a returning player is looking for; a
  // share under the verdict two blocks down is a control they scroll past. On a finished day the row is
  // the two things there are to do — read what you built, or tell somebody you built it.
  //
  // ⚠️ It is *only* on a finished day. Offering a share before there is a result to share would be a
  // button that either lies or refuses, and a returning player meets it on every unfinished morning.
  let share = null;
  if (finished && onShare) {
    share = doc.createElement("button");
    share.type = "button";
    share.className = "app-button landing-share";
    // ⚠️⚠️ **The reveal's own icon, imported rather than redrawn.** A player learns this mark on the
    // reveal and has to recognise it here; two hand-drawn twins drift the first time either is touched
    // and nothing notices. It is decorative — `aria-hidden` on the svg — and `reveal.share` carries the
    // meaning, which is why both surfaces share the catalogue key as well as the drawing.
    share.append(shareIcon(doc), doc.createTextNode(text("reveal.share")));
    // ⚠️⚠️ **Guarded against re-entry, exactly as the reveal's is.** `navigator.share` takes a moment
    // and a second press during it opens a second sheet on some platforms and rejects the first on
    // others — and it queues a second row for one act. Disabled *during* the send and never before it:
    // if this button is on screen the game is over and it can always be shared.
    let sharing = false;
    share.addEventListener("click", async () => {
      if (sharing) return;
      sharing = true;
      share.disabled = true;
      try {
        await onShare(restored);
      } finally {
        sharing = false;
        share.disabled = false;
      }
    });
    const row = doc.createElement("div");
    row.className = "landing-way-row";
    row.append(play, share);
    way.append(row, how);
  } else {
    way.append(play, how);
  }
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

  return { page, play, share, how, later, finished, game: restored };
}
