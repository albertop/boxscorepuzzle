/**
 * What happens when the player says they are done, and what they get for being right.
 *
 * ⚠️⚠️ **The board never says which cells are wrong, or how many.** Both were considered and both were
 * rejected in `serve-flow.md`, for reasons that are about the game rather than about taste:
 *
 *   - **Marking the wrong cells** makes probing beat deducing. A player who enters a guess and reads
 *     the marks is playing a better strategy than one who works it out, and the puzzle stops being a
 *     deduction puzzle the moment that is true.
 *   - **Counting them** is a binary search over the board. Fill half, check, halve again — the count
 *     hands the player an oracle that answers questions the boxscore never would.
 *
 * So there is one sentence for every wrong board, whatever is wrong with it, and it is a fact about
 * the whole: it does not balance. Nothing here may ever take a cell name.
 *
 * ⚠️ **The clock does not stop for a wrong answer, and attempts are unlimited.** §27 says there is no
 * fail state; what an error costs is time, and time is what gets measured and shared. A limit would
 * add a fail state through the back door, and stopping the clock would make errors free.
 *
 * ⚠️ **And the mistake count is gone from the reveal.** It was never decided anywhere — not in
 * `serve-flow.md` — and a number quantifying failure sits badly beside §27's rule that you cannot
 * lose. It is still in the C7 event record, where it is a measurement rather than a message.
 */

import {
  FOOTNOTE_COLUMNS,
  INNINGS,
  PRINTED_BATTING,
  PRINTED_PITCHING,
  inningsToDisplay,
} from "../../engine/columns.js";
import { ROUTES } from "./daily.js";
import { fill, longDate, text } from "../../engine/strings.js";
import { renderLineScore } from "./board.js";

/** `mm:ss`, or `h:mm:ss` past an hour. The first thing the player sees of a clock they never saw run. */
export function formatDuration(milliseconds) {
  const total = Math.max(0, Math.round(milliseconds / 1000));
  const seconds = String(total % 60).padStart(2, "0");
  const minutes = Math.floor(total / 60) % 60;
  const hours = Math.floor(total / 3600);
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${seconds}` : `${minutes}:${seconds}`;
}

/**
 * What a press of *Check* means, as a value rather than as a side effect.
 *
 * ⚠️ Separated from the drawing so the rule can be tested without a DOM, and so the one place that
 * decides *what the player is told* is one place. `state` is `incomplete`, `wrong` or `solved` — and
 * there is deliberately no fourth carrying detail.
 */
export function checkBoard(game) {
  // ⚠⚠ **The verdict comes from the engine and the wording is decided here.** This used to compute
  // the verdict too, which put the rule in the shell while the C7 record lives in the engine — and the
  // engine, having no notion of *check*, recorded a mistake on every keystroke of a two-digit answer.
  // `game.check()` is the moment an entry becomes an answer; this is the moment it becomes a sentence.
  const { state } = game.check();
  if (state === "incomplete") return { state, message: text("done.incomplete") };
  if (state === "wrong") return { state, message: text("done.not_yet") };
  return { state, message: "" };
}



/**
 * The boxscore the player just reconstructed, laid out the way a newspaper printed one.
 *
 * ⚠️⚠️ **This replaced a results card, and then replaced the first attempt at replacing it.** The first
 * attempt put the board's own six columns in monospace with the names attached down the left, and that
 * is a legend, not a boxscore — the player is shown the thing they just filled in, relabelled. A
 * printed boxscore is a different object and schema 5 exists to carry one: **both clubs**, **runs
 * batted in**, and the clubs' **real names** instead of `SLA`.
 *
 * **The layout is the modern printed one**: the two batting grids, visitor first; the footnote line;
 * then the pitchers of both clubs in one block, which is where a newspaper puts them.
 *
 * **Monospace, because that is what a printed boxscore used.** The columns then align by themselves
 * rather than by a grid, and it puts visible distance between the reveal and the board's modern face —
 * the player is looking at a clipping, not at the thing they were just typing into.
 *
 * ⚠️ **No aged-paper texture and no newsprint ground.** At 375px there is no room for decoration, and a
 * textured background lowers contrast exactly where the player wants to read names.
 */
export function renderReveal(puzzle, record, { onShare } = {}) {
  // ⚠️⚠️ **Required, and a missing one is an error rather than a quieter screen.** If this panel is on
  // screen the game is finished, and a finished game can always be shared — **there is no state where
  // the reveal exists and sharing is impossible.** So a caller without an action is a bug in the
  // caller, and rendering a dead button instead of saying so hides it behind something that looks
  // deliberate. The absence of a check must not read as the presence of a passing one.
  if (typeof onShare !== "function") {
    throw new TypeError("renderReveal needs onShare: the reveal is only shown on a finished game");
  }
  const reveal = puzzle.reveal;
  const panel = document.createElement("div");
  panel.className = "reveal";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-modal", "true");
  panel.setAttribute("aria-label", text("reveal.title"));

  const sheet = document.createElement("div");
  sheet.className = "reveal-sheet";
  panel.append(sheet);

  // ⚠️ **The verdict and the result are one band, not three stacked lines.** `Solved` sits to the left
  // and the two figures are boxed together on the right, so the labels and their values read as one
  // block rather than as a heading followed by two unrelated rows. The time was legible on its own and
  // the hint count was not; grouping them makes the pair the unit, which is what a shared result is.
  const head = document.createElement("div");
  head.className = "reveal-head";

  // ⚠️⚠️ **The verdict and the share are one column, and the share sits directly under the sentence
  // that earns it.** It was at the foot of the sheet beside *Back to the board*, which put the only
  // growth mechanism the product has below a printed boxscore the player has to scroll past — and
  // beside the control whose whole job is to leave. **Two buttons in a row make the reader choose
  // between them; one under the verdict is an offer, and the way out is somewhere else entirely.**
  const verdict = document.createElement("div");
  verdict.className = "reveal-verdict";

  const title = document.createElement("h2");
  title.className = "reveal-title";
  title.textContent = text("reveal.title");
  verdict.append(title);
  head.append(verdict);

  const result = document.createElement("div");
  result.className = "reveal-result";
  head.append(result);
  sheet.append(head);

  // ⚠️ The clock, appearing for the first time. Invisible during play (§26) because a visible timer
  // changes how people play; shown here because it is what the comparison feature will compare.
  const time = document.createElement("p");
  time.className = "reveal-time";
  const label = document.createElement("span");
  label.className = "reveal-time-label";
  label.textContent = text("reveal.time");
  const figure = document.createElement("span");
  figure.className = "reveal-time-figure";
  figure.textContent = formatDuration(record.duration_ms);
  time.append(label, figure);
  result.append(time);

  // ⚠️⚠️ **Beside the time, because that is the whole argument for allowing hints at all.** The
  // decision against them was reversed on the crossword's reasoning: a hint does not corrupt a shared
  // result *if it is shared alongside the time*. One minute with three hints and one minute with none
  // are two different results and every reader takes them as two. Printed here whether or not any were
  // used, so a clean solve says so rather than being the absence of a line nobody knows to look for.
  const hints = document.createElement("p");
  hints.className = "reveal-hints";
  const hintLabel = document.createElement("span");
  hintLabel.className = "reveal-hints-label";
  hintLabel.textContent = text("reveal.hints");
  const hintFigure = document.createElement("span");
  hintFigure.className = "reveal-hints-figure";
  hintFigure.textContent = record.hints === 0 ? text("reveal.no_hints") : String(record.hints);
  // A clean solve is styled quietly and a spend is not. The state is on the row rather than read from
  // the text, so the stylesheet never has to parse a word out of a catalogue it does not own.
  if (record.hints === 0) hints.dataset.state = "none";
  hints.append(hintLabel, hintFigure);
  result.append(hints);

  // ⚠️⚠️ **The failures, not the attempts, and this was the other way round for one commit.** Showing
  // `failed + 1` under the label *Tries* made a clean solve read `1` instead of `0` — tidier, and
  // worse in the two ways that matter.
  //
  // **`Checks failed` says exactly what it means.** Under *Tries* the player has to subtract to learn
  // how many times the board came back wrong.
  //
  // ⚠️ **And it collapsed the distinction it exists for.** Solved first time read `1`; failed once
  // read `2` — two adjacent numbers for very different results, on the line whose whole job is
  // separating somebody probing from somebody correcting. `0` against `1` separates at a glance.
  //
  // The C7 field and this line are the same number now, which is also one fewer thing to disagree.
  const tries = document.createElement("p");
  tries.className = "reveal-tries";
  const triesLabel = document.createElement("span");
  triesLabel.className = "reveal-tries-label";
  triesLabel.textContent = text("reveal.tries");
  const triesFigure = document.createElement("span");
  triesFigure.className = "reveal-tries-figure";
  const failed = record.failed_checks ?? 0;
  // ⚠️ **`None`, not `0`, and the row above is why.** A clean solve and a spotless board are the same
  // kind of news, so they are said the same way — a bare `0` beside `None` reads as two different
  // kinds of statement about the same solve. It is also the figure people misread fastest: `0` next to
  // a clock is a number waiting to be compared against something.
  triesFigure.textContent = failed === 0 ? text("reveal.no_failures") : String(failed);
  // A board that never came back wrong is the quiet state, as no hints is on the row above.
  if (failed === 0) tries.dataset.state = "none";
  tries.append(triesLabel, triesFigure);
  result.append(tries);

  const clipping = document.createElement("div");
  clipping.className = "clipping";
  sheet.append(clipping);

  // ⚠️ **Unconditional, and it was `if (reveal)` until v39-P2-02.** The reader now refuses a package
  // without a reveal, so the guard could never be false — and a branch that cannot be taken is
  // indistinguishable from one that is broken. It was also what made the defect quiet: an absent reveal
  // drew an empty panel at the moment the player finished, rather than being refused at the boundary.
  clipping.append(...clippingFor(puzzle, reveal));

  // ⚠️ **A row of two, which is the shape the tutorial's footer already uses.** The way out and the
  // way onward, secondary then primary, left then right.
  const actions = document.createElement("div");
  actions.className = "reveal-actions";

  const close = document.createElement("button");
  close.type = "button";
  close.className = "app-button app-button--filled reveal-close";
  close.textContent = text("reveal.close");

  // ⚠️⚠️ **Live since G, and it is never `disabled`.** It was drawn and disabled for weeks while there
  // was nothing behind it, with a comment arguing that a control which looks pressable and does nothing
  // is worse than one plainly not ready. That was right then. **What retires it is not that the feature
  // arrived — it is that the state cannot occur:** this panel is only shown on a finished game, and a
  // finished game is always shareable.
  //
  // ⚠️ **Re-entry is guarded by a flag, not by the `disabled` attribute.** Building the image fetches
  // three stylesheets and three faces, and a second press during that would start a second build and,
  // on the native path, a second sheet. But a button that greys out for a second with no explanation
  // reads as broken, and on the fallback path the player would watch it die and come back for no
  // visible reason. The guard is invisible and the control stays live.
  const share = document.createElement("button");
  share.type = "button";
  share.className = "app-button app-button--filled reveal-share";
  // ⚠️ The icon is decorative and the label carries the meaning, so it is hidden from the accessibility
  // tree — a screen reader announcing "image, Share" reads the same thing twice.
  share.append(shareIcon(), document.createTextNode(text("reveal.share")));
  let sharing = false;
  share.addEventListener("click", async () => {
    // ⚠️ A second press while the first is still building is ignored, not queued and not refused
    // visibly. Nothing about the button changes, because nothing about what it offers has changed.
    if (sharing) return;
    sharing = true;
    try {
      await onShare();
    } finally {
      sharing = false;
    }
  });

  // ⚠️⚠️ **A link, not a button, and that is not a style choice.** It leaves the site: a middle click,
  // a long press and *open in new tab* all have to work, and every one of them is something a browser
  // gives an `<a href>` for free and nothing gives a `<button>` at all. Drawn to match `close` so the
  // pair reads as a row.
  //
  // ⚠️ **`rel="noopener"` with `target="_blank"`.** Without it the opened page gets a handle on this
  // one through `window.opener` and can navigate it — a page the player left could replace the game
  // behind them.
  const reference = document.createElement("a");
  reference.className = "app-button reveal-reference";
  reference.href = referenceUrl(reveal.gameId);
  reference.target = "_blank";
  reference.rel = "noopener noreferrer";
  reference.textContent = text("reveal.reference");

  // ⚠️ **The share goes under the verdict; the foot carries the two ways out.** The share was here,
  // beside `Back to the board`, and moving it left this row for what it should have held all along:
  // the way back to the board and the way on to the game itself.
  // ⚠️⚠️ **The way out of the loop, and it is what this whole change is for.** Three screens pushed
  // inward and none pushed out: the landing sent you to the board, the finished board sent you to the
  // boxscore, and the boxscore sent you back to the board. A player who finished had no exit that was
  // not a return.
  const home = document.createElement("a");
  home.className = "app-button reveal-home";
  home.href = ROUTES.landing;
  home.textContent = text("reveal.home");

  // ⚠️ **The share is under the verdict, not in the foot.** Placed there when it went live: it belongs
  // to the sentence that earns it, and a share beside the way out makes the player choose between
  // leaving and telling somebody.
  verdict.append(share);

  // ⚠️⚠️ **Two rows, and the split is by kind rather than by fitting.** The first row is where you can
  // go *inside* the product; the second leaves it for somebody else's site. Three across at 375px puts
  // every label on two lines, and `See the game` beside two in-product controls reads as a third of the
  // same kind when it is not.
  const inside = document.createElement("div");
  inside.className = "reveal-actions-row";
  inside.append(close, home);
  actions.append(inside, reference);
  sheet.append(actions);
  // ⚠️ **Built here, wired by the shell.** This used to call `panel.remove()` itself, which closes the
  // panel and nothing else — it cannot restore the focus the shell moved, cannot un-inert what the
  // shell hid, and cannot know a panel is open. Two half-owners of one lifecycle. See `present()` and
  // `dismiss()` in `shell.js`; v34-P2-01.

  return panel;
}

/**
 * Baseball Reference's page for this exact game.
 *
 * ⚠️⚠️ **Built from the id and never from the date and the clubs**, which is why schema 6 carries it.
 * The path is `/boxes/<home club>/<game id>.shtml`, and the id ends in the game's number that day —
 * `0` alone, `1` and `2` for the halves of a doubleheader. **29 of the 150 published boards are
 * doubleheaders**, so an id assembled from teams and date would send a fifth of players to the other
 * game: a boxscore that contradicts the one they just rebuilt, offered as the reward for rebuilding it.
 *
 * ⚠️ **`gameId[0..3]` is the HOME club.** Not the offence — `offenseIsHome` says which side batted, and
 * reading the first three characters as the offence is how four early packages claimed a lineup for a
 * team that never played for it.
 *
 * ⚠️ No validation here: `package.js` refuses an id that is not Retrosheet-shaped at the boundary, so
 * a check in this function would be a second place enforcing one rule — and the one that runs later,
 * where a failure lands on the finished screen instead of on the load.
 */
function referenceUrl(gameId) {
  return `https://www.baseball-reference.com/boxes/${gameId.slice(0, 3)}/${gameId}.shtml`;
}

/**
 * The share mark: three nodes and two links, the web's shared vocabulary for sending something on.
 *
 * ⚠️ **Inline SVG rather than a font or a file.** An icon font would be a second face to load for one
 * glyph, and a separate file is a request the reveal would wait on. It is drawn in `currentColor`, so
 * it follows the button's text through every theme without a second colour to keep in step.
 *
 * ⚠️ **The three-node mark, not the square-with-an-arrow.** The latter is Apple's and reads as a
 * system affordance on iOS and as nothing anywhere else; this one is what the web uses and what an
 * Android handset shows for the same act. The product is phone-first on both.
 *
 * ⚠️⚠️ **Exported since the landing gained a Share, and the alternative was a second copy of a drawing.**
 * Two surfaces offer this act and they must offer the same mark: a player who learns the icon on the
 * reveal has to recognise it on the landing. A hand-drawn twin would drift the first time either is
 * touched and nothing would notice — this project's most-recorded defect, in a shape where the symptom
 * is *the same button looks like two different buttons*, which is exactly how it was found.
 *
 * ⚠️ `doc` for the reason every other renderer here takes it: a test drives the real thing.
 */
export function shareIcon(doc = document) {
  const svg = doc.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "2");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  for (const [cx, cy] of [[18, 5], [6, 12], [18, 19]]) {
    const node = doc.createElementNS("http://www.w3.org/2000/svg", "circle");
    node.setAttribute("cx", String(cx));
    node.setAttribute("cy", String(cy));
    node.setAttribute("r", "3");
    svg.append(node);
  }
  for (const [x1, y1, x2, y2] of [[8.6, 10.5, 15.4, 6.5], [8.6, 13.5, 15.4, 17.5]]) {
    const link = doc.createElementNS("http://www.w3.org/2000/svg", "line");
    link.setAttribute("x1", String(x1));
    link.setAttribute("y1", String(y1));
    link.setAttribute("x2", String(x2));
    link.setAttribute("y2", String(y2));
    svg.append(link);
  }
  return svg;
}

/**
 * The clipping itself, as a list of blocks.
 *
 * ⚠️ **Visitor first, everywhere.** A printed boxscore puts the club that bats first on top — line
 * score, batting grids, pitchers. `offenseIsHome` is the only thing that says which club that is, and
 * it is in the package precisely because a client cannot infer it: a square line score determines
 * nothing, and four of the six reference packages are nine innings and nine.
 */
function clippingFor(puzzle, reveal) {
  const score = puzzle.solution.lineScore;
  const home = puzzle.offenseIsHome ? reveal.boxscore.offense : reveal.boxscore.defense;
  const visitor = puzzle.offenseIsHome ? reveal.boxscore.defense : reveal.boxscore.offense;
  const homeRuns = puzzle.offenseIsHome ? score.offense_runs : score.defense_runs;
  const visitorRuns = puzzle.offenseIsHome ? score.defense_runs : score.offense_runs;

  const heading = document.createElement("p");
  heading.className = "clipping-head";
  // ⚠️ **The winner is named first**, which is how a result line is written and is not the same as
  // visitor-first. A tie is impossible in a completed game, so there is no third case to handle — and
  // if one ever arrives the order simply follows the line score, which is a true statement either way.
  heading.textContent =
    homeRuns > visitorRuns
      ? `${clubName(home)} ${homeRuns}${text("reveal.score_separator")}${clubName(visitor)} ${visitorRuns}`
      : `${clubName(visitor)} ${visitorRuns}${text("reveal.score_separator")}${clubName(home)} ${homeRuns}`;

  const date = document.createElement("p");
  date.className = "clipping-date";
  date.textContent = longDate(reveal.playedOn);

  // ⚠️ **The real renderer with the labels as a parameter, never a second line score.** A comparison
  // page written with its own grid twice showed something other than what it was evaluating. Here the
  // labels change and nothing else does: during play the rows are `AWAY` and `HOME` because the player
  // has no clubs, and here they are the clubs, because the player has just earned them.
  const line = renderLineScore(puzzle.solution.lineScore, puzzle.offenseIsHome, sideLabels(reveal));

  const notes = footnoteBlock(puzzle, reveal);

  return [heading, date, line, battingGrid(visitor), battingGrid(home), notes, pitchingGrid(visitor, home)];
}

/** `St. Louis Browns`. Two fields in the package so a narrow row can print the city alone. */
const clubName = (side) => `${side.city} ${side.nickname}`;

/**
 * What the line score's two rows are called, once the player has the clubs.
 *
 * ⚠⚠ **The three-letter code, and the first version of this said the city on the strength of a claim
 * I had not measured.** The label column is 52px. Measured against the reference set with the real
 * font: the widest **city is 82px** (Philadelphia) and the widest **nickname 67px** (Guardians), so
 * neither fits, and `Boston` alone overflowed by 5px in the first render. The **code is 30px at its
 * widest** and fits with room left over. Widening the column instead would take the width out of the
 * innings, which is worse at nine and breaks at the twelve `MAX_INNINGS` allows.
 *
 * ⚠️ **And `SLA` here is not the `SLA` schema 5 removed.** That argument was about a *heading* whose
 * only naming of the club was the code. Here both clubs are printed in full in the result line
 * directly above and in the batting grids directly below, in the same visitor-then-home order, so the
 * code is a key into names on the same screen twice rather than a name. **A justification is scoped
 * and does not travel** — re-derived here rather than carried across, which is the rule this nearly
 * broke in the opposite direction.
 */
const sideLabels = (reveal) => ({
  offense: reveal.boxscore.offense.code,
  defense: reveal.boxscore.defense.code,
});

/**
 * One club's batting, headed by its name, ruled above the totals.
 *
 * ⚠️ A real `<table>` rather than padded text. Monospace makes the columns *look* like a printed
 * boxscore; a table makes them *be* columns, so a screen reader gets rows and headers instead of one
 * run-on line, and a long name pushes its own column rather than shearing the alignment of the rest.
 *
 * ⚠️ **The totals are summed here, and this is the one place in the product where that is right.**
 * Everywhere else a total is loaded from an independent source, because a total summed from the rows
 * it verifies verifies nothing — that defect is on the record. Here there is nothing to verify: the
 * package's own totals cover the board's six columns for one club, and this grid has `RBI` and a club
 * the board never carried. A totals row is arithmetic over what is printed above it, so it is computed
 * from what is printed above it.
 */
function battingGrid(side) {
  const table = document.createElement("table");
  table.className = "clipping-grid clipping-batting";
  table.append(headRow(clubName(side), PRINTED_BATTING));
  for (const row of side.batting) table.append(playerRow(row, PRINTED_BATTING));
  table.append(totalsRow(side.batting, PRINTED_BATTING));
  return table;
}

/**
 * Both clubs' pitchers in one block, which is where a newspaper puts them.
 *
 * ⚠️ **No totals row here, deliberately.** A pitching block covering two clubs has nothing a total
 * would mean: adding one club's innings to the other's produces the number of half-innings played,
 * which is arithmetic that is true and says nothing. The batting grids get totals because each covers
 * one club.
 */
function pitchingGrid(visitor, home) {
  const table = document.createElement("table");
  table.className = "clipping-grid clipping-pitching";
  table.append(headRow(text("printed.pitchers"), PRINTED_PITCHING));
  for (const side of [visitor, home]) {
    table.append(clubRow(clubName(side), PRINTED_PITCHING.length));
    for (const row of side.pitching) table.append(playerRow(row, PRINTED_PITCHING, { innings: true }));
  }
  return table;
}

function headRow(name, columns) {
  const row = document.createElement("tr");
  const first = document.createElement("th");
  first.className = "clipping-team";
  first.scope = "col";
  first.textContent = name;
  row.append(first);
  for (const column of columns) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = text(`printed.${column}`);
    row.append(cell);
  }
  return row;
}

/** A club's name inside the shared pitching block, spanning the row. */
function clubRow(name, width) {
  const row = document.createElement("tr");
  row.className = "clipping-club";
  const cell = document.createElement("th");
  cell.scope = "rowgroup";
  cell.colSpan = width + 1;
  cell.textContent = name;
  row.append(cell);
  return row;
}

function playerRow(row, columns, { innings = false } = {}) {
  const line = document.createElement("tr");
  const who = document.createElement("td");
  who.className = "clipping-who";
  // Name then position, lower case, which is how a printed boxscore wrote it. The label is what the
  // player solved against, so keeping it beside the name is what lets them map one onto the other.
  who.textContent = `${row.name} ${row.label.toLowerCase()}`.trim();
  line.append(who);
  for (const column of columns) {
    const cell = document.createElement("td");
    // ⚠️ The shared conversion, asking for the printed notation. This was a third hand-written copy
    // of the formula, and the drift it caused was visible: `4` on the board, `9.0` here.
    cell.textContent =
      innings && column === "outs" ? inningsToDisplay(row[column], INNINGS.PRINTED) : String(row[column]);
    line.append(cell);
  }
  return line;
}

function totalsRow(rows, columns) {
  const line = document.createElement("tr");
  line.className = "clipping-totals";
  const label = document.createElement("td");
  label.className = "clipping-who";
  label.textContent = text("board.totals");
  line.append(label);
  for (const column of columns) {
    const cell = document.createElement("td");
    cell.textContent = String(rows.reduce((sum, row) => sum + row[column], 0));
    line.append(cell);
  }
  return line;
}

/**
 * The footnote line, below the batting grids, as printed boxscores carry it.
 *
 * ⚠️ **Prefixed with the club, because the package carries footnotes for one club only.** They belong
 * to the board's batting side; the other club has its own and no package holds them. An unprefixed
 * line would read as a statement about both clubs and be silently false about one — a label sitting
 * outside the arithmetic, which is exactly the kind nothing arithmetic can catch.
 *
 * ⚠️ **Named carriers rather than slot references.** During play the line says `SH: 1 #2` because the
 * player has no names; here they do, and a printed boxscore wrote `Sacrifice hit — Shotton`. The slot
 * reference existed to point at a row without naming anyone, and that reason is gone at this point.
 */
function footnoteBlock(puzzle, reveal) {
  const block = document.createElement("p");
  block.className = "clipping-notes";
  const names = reveal.boxscore.offense.batting.map((row) => row.name);
  const parts = [];

  // The footnote line is given in full and never erased (§6), so puzzle and solution agree here — but
  // it reads from the solution anyway, so that one rule about where a finished boxscore comes from
  // holds for every part of this panel rather than for most of it.
  FOOTNOTE_COLUMNS.forEach((column, index) => {
    const carriers = [];
    puzzle.solution.footnotes.forEach((row, batter) => {
      const count = row[index];
      if (count > 0) carriers.push(count > 1 ? `${names[batter] ?? ""} ${count}` : (names[batter] ?? ""));
    });
    if (carriers.length > 0) {
      parts.push(`${text(`column.${column}`)}${text("printed.note_separator")}${carriers.join(", ")}`);
    }
  });
  parts.push(`${text("board.left_on_base")}${text("printed.note_separator")}${puzzle.solution.leftOnBase}`);

  const prefix = document.createElement("span");
  prefix.className = "clipping-notes-team";
  prefix.textContent = fill("printed.notes_for", { team: clubName(reveal.boxscore.offense) });
  block.append(prefix, ` ${parts.join(".  ")}`);
  return block;
}

/**
 * The reference sheet: the five relations and the bounds, on demand.
 *
 * ⚠️⚠️ **This exists because a player could not remember the formulas mid-game, and that is friction
 * rather than difficulty.** A game that measures whether you remembered `PA = Outs + Runs + LOB` is
 * measuring memory as well as deduction, and only one of those is the product.
 *
 * ⚠️ **It costs no hint and is not one.** A hint hands over an answer; this hands over the rules,
 * which §8's tutorial already teaches on first play. The difference is that the tutorial teaches them
 * once and this is there at the moment they are wanted.
 *
 * ⚠️ **It carries five families and the printed strip carries four.** `build_pack.FORMULAS` predates
 * the batting order, and the batting order is precisely the one that cannot be inferred from looking
 * at a board — the operator lost a solve to exactly that. The strip is a launch-gate artefact that must
 * not move while it is being solved, so the gap is recorded in `todo.md` and closed here.
 */
export function renderReference() {
  const panel = document.createElement("div");
  panel.className = "reveal reference";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-modal", "true");
  panel.setAttribute("aria-label", text("reference.title"));

  const sheet = document.createElement("div");
  sheet.className = "reveal-sheet";
  panel.append(sheet);

  const title = document.createElement("h2");
  title.className = "reveal-title";
  title.textContent = text("reference.title");
  sheet.append(title);

  const list = document.createElement("dl");
  list.className = "reference-list";
  // ⚠️ Ordered by how often a solve reaches for them, not by the order the design document lists them:
  // the row identity and the column sums carry most boards, and the bounds are what a player checks
  // last. A reference read under pressure is read from the top.
  for (const key of ["row_identity", "column_sum", "global", "cross_team", "batting_order", "innings", "bounds"]) {
    const name = document.createElement("dt");
    name.textContent = text(`reference.${key}_name`);
    const rule = document.createElement("dd");
    rule.textContent = text(`reference.${key}`);
    list.append(name, rule);
  }
  sheet.append(list);

  const close = document.createElement("button");
  close.type = "button";
  close.className = "app-button app-button--filled reveal-close";
  close.textContent = text("reference.close");
  sheet.append(close);
  // ⚠️ Wired by the shell, for the reason on the other renderer's close button.

  return panel;
}
