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

import { BATTING_COLUMNS, FOOTNOTE_COLUMNS, PITCHING_COLUMNS } from "../../engine/columns.js";
import { text } from "../../engine/strings.js";
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
  const blanks = game.blanks();
  const empty = blanks.filter((name) => game.value(name) === null);
  if (empty.length > 0) return { state: "incomplete", message: text("done.incomplete") };
  if (!game.isSolved()) return { state: "wrong", message: text("done.not_yet") };
  return { state: "solved", message: "" };
}

/** Innings held as outs, printed the way a boxscore prints them. */
const inningsOf = (outs) => `${Math.floor(outs / 3)}.${outs % 3}`;

/**
 * The boxscore the player just reconstructed, laid out the way a newspaper printed one.
 *
 * ⚠️⚠️ **This replaced a results card, and the difference is the whole point.** The payoff is not being
 * told *Solved* — it is seeing the object, whole, with the names that were withheld while it was being
 * worked out (§7). A list of positions and surnames down the left is a legend; a boxscore is a boxscore.
 *
 * **Monospace, because that is what a printed boxscore used.** The columns then align by themselves
 * rather than by a grid, and it puts visible distance between the reveal and the board's modern face —
 * the player is looking at a clipping, not at the thing they were just typing into.
 *
 * ⚠️ **No aged-paper texture and no newsprint ground.** At 375px there is no room for decoration, and a
 * textured background lowers contrast exactly where the player wants to read names. If the columns,
 * the monospace and the rules read as a clipping, nothing else is needed.
 */
export function renderReveal(puzzle, record) {
  // ⚠️ **`snake_case`, because the reveal passes through the reader untouched.** `readPackage` maps
  // every other field into the client's own shape and deliberately does not map this one, so writing
  // `reveal.offenseTeam` here reads `undefined` and renders an empty heading — with no error, on the
  // one screen nobody had ever seen. Checked against a real package rather than assumed.
  const reveal = puzzle.reveal;
  const panel = document.createElement("div");
  panel.className = "reveal";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-modal", "true");
  panel.setAttribute("aria-label", text("reveal.title"));

  const sheet = document.createElement("div");
  sheet.className = "reveal-sheet";
  panel.append(sheet);

  const title = document.createElement("h2");
  title.className = "reveal-title";
  title.textContent = text("reveal.title");
  sheet.append(title);

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
  sheet.append(time);

  const clipping = document.createElement("div");
  clipping.className = "clipping";
  sheet.append(clipping);

  if (reveal) {
    const heading = document.createElement("p");
    heading.className = "clipping-head";
    // `AWAY vs HOME at DATE`, composed from the catalogue rather than written as a sentence, so a
    // language that orders it differently changes the strings and not this file.
    heading.textContent =
      `${reveal.offense_team} ${text("reveal.versus")} ${reveal.defense_team} ` +
      `${text("reveal.at")} ${reveal.played_on}`;
    clipping.append(heading);
  }

  const score = document.createElement("div");
  score.className = "linescore";
  score.append(renderLineScore(puzzle.puzzle.lineScore, puzzle.offenseIsHome));
  clipping.append(score);

  // ⚠⚠ **`solution`, not `puzzle`.** The first version drew `puzzle.puzzle`, which is the board *with
  // its blanks* — so the finished boxscore printed `null` in every cell the player had just filled in,
  // and every pitcher's innings read `0.0`. It threw nothing and the panel looked structurally right;
  // only reading the rendered text showed it. The reveal is the completed object by definition, and
  // the completed object is `solution`. The line score above is the same either way: §6 gives it
  // complete and never erases it.
  const done = puzzle.solution;

  clipping.append(
    grid({
      team: reveal?.offense_team ?? "",
      columns: BATTING_COLUMNS,
      rows: done.batting,
      totals: done.battingTotals,
      names: reveal?.batter_names ?? [],
      labels: puzzle.labels,
      className: "clipping-batting",
    }),
  );
  clipping.append(
    grid({
      team: reveal?.defense_team ?? "",
      columns: PITCHING_COLUMNS,
      rows: done.pitching,
      totals: done.pitchingTotals,
      names: reveal?.pitcher_names ?? [],
      labels: puzzle.pitcherLabels,
      className: "clipping-pitching",
      innings: true,
    }),
  );
  clipping.append(footnoteBlock(puzzle));

  const close = document.createElement("button");
  close.type = "button";
  close.className = "reveal-close";
  close.textContent = text("reveal.close");
  sheet.append(close);
  close.addEventListener("click", () => panel.remove());

  return panel;
}

/**
 * One half of the clipping: a team, its rows, and its totals under a rule.
 *
 * ⚠️ A real `<table>` rather than padded text. Monospace makes the columns *look* like a printed
 * boxscore; a table makes them *be* columns, so a screen reader gets rows and headers instead of one
 * run-on line, and a long name pushes its own column rather than shearing the alignment of the rest.
 */
function grid({ team, columns, rows, totals, names, labels, className, innings = false }) {
  const table = document.createElement("table");
  table.className = `clipping-grid ${className}`;

  const head = document.createElement("tr");
  const teamCell = document.createElement("th");
  teamCell.className = "clipping-team";
  teamCell.scope = "col";
  teamCell.textContent = team;
  head.append(teamCell);
  for (const column of columns) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = text(`column.${column}`);
    head.append(cell);
  }
  table.append(head);

  rows.forEach((row, index) => {
    const line = document.createElement("tr");
    const who = document.createElement("td");
    who.className = "clipping-who";
    // Name then position, lower case, which is how a printed boxscore wrote it. The label is what the
    // player solved against, so keeping it beside the name is what lets them map one onto the other.
    who.textContent = `${names[index] ?? ""} ${(labels[index] ?? "").toLowerCase()}`.trim();
    line.append(who);
    row.forEach((value, column) => {
      const cell = document.createElement("td");
      cell.textContent = innings && column === 0 ? inningsOf(value) : String(value);
      line.append(cell);
    });
    table.append(line);
  });

  const totalsRow = document.createElement("tr");
  totalsRow.className = "clipping-totals";
  const totalsLabel = document.createElement("td");
  totalsLabel.className = "clipping-who";
  totalsLabel.textContent = text("board.totals");
  totalsRow.append(totalsLabel);
  totals.forEach((value, column) => {
    const cell = document.createElement("td");
    cell.textContent = innings && column === 0 ? inningsOf(value) : String(value);
    totalsRow.append(cell);
  });
  table.append(totalsRow);

  return table;
}

/**
 * The footnote block, below the grids, as printed boxscores carry it.
 *
 * ⚠️ Named carriers rather than slot references. During play the line says `SH: 1 #2` because the
 * player has no names; here they do, and a printed boxscore wrote `Sacrifice hit — Shotton`. The slot
 * reference existed to point at a row without naming anyone, and that reason is gone at this point.
 */
function footnoteBlock(puzzle) {
  const block = document.createElement("p");
  block.className = "clipping-notes";
  const names = puzzle.reveal?.batter_names ?? [];
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
    if (carriers.length > 0) parts.push(`${text(`column.${column}`)} — ${carriers.join(", ")}`);
  });
  parts.push(`${text("board.left_on_base")} — ${puzzle.solution.leftOnBase}`);

  block.textContent = parts.join(".  ");
  return block;
}
