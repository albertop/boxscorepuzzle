/**
 * The phone layer: layout and interaction, and nothing else.
 *
 * ⚠️ **This file must not decide what a cell means.** It reads `describeCells` and asks the game; it
 * never validates an entry, computes a total or interprets the package. A layer that does any of those
 * is the second place encoding one rule, and the three layers drift the moment one of them does
 * (`docs/serve-brief.md` §3).
 */

import {
  BATTING_COLUMNS,
  FOOTNOTE_COLUMNS,
  PITCHING_COLUMNS,
  battingTotalCell,
  footnoteCell,
  inningsToDisplay,
  pitchingTotalCell,
} from "../../engine/columns.js";
import { text } from "../../engine/strings.js";

const el = (tag, className, content) => {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined) node.textContent = content;
  return node;
};

/* ---- line score ------------------------------------------------------------------------------ */

export function renderLineScore(score, offenseIsHome) {
  const innings = Math.max(score.offense_by_inning.length, score.defense_by_inning.length);
  const table = el("table");
  const head = el("tr");
  head.append(el("th", "side", ""));
  for (let i = 1; i <= innings; i += 1) head.append(el("th", null, String(i)));
  for (const key of ["runs", "hits", "errors"]) {
    const cell = el("th", key === "runs" ? "rhe rhe-rule" : "rhe", text(`linescore.${key}`));
    head.append(cell);
  }
  table.append(head);

  const side = (label, byInning, runs, hits, errors) => {
    const row = el("tr");
    row.append(el("td", "side", label));
    for (let i = 0; i < innings; i += 1) {
      // ⚠️ A half-inning that was never played prints a dash, never a zero. The home side leading
      // after the top of the ninth does not bat, and a 0 there is a claim about a thing that did not
      // happen — the arithmetic would still balance, which is why nothing arithmetic catches it.
      const played = i < byInning.length;
      row.append(el("td", played ? "value" : "unplayed", played ? String(byInning[i]) : text("board.inning_not_played")));
    }
    row.append(el("td", "value rhe rhe-rule", String(runs)));
    row.append(el("td", "value rhe", String(hits)));
    row.append(el("td", "value rhe", String(errors)));
    return row;
  };

  const offense = () =>
    side(
      text(offenseIsHome ? "linescore.home" : "linescore.away"),
      score.offense_by_inning,
      score.offense_runs,
      score.offense_hits,
      score.offense_errors,
    );
  const defense = () =>
    side(
      text(offenseIsHome ? "linescore.away" : "linescore.home"),
      score.defense_by_inning,
      score.defense_runs,
      score.defense_hits,
      score.defense_errors,
    );
  // ⚠️ **The visiting side goes on top**, because that is where a line score puts the team that bats
  // first and a player reads the shape before the labels. So when the offence is the home team the two
  // rows swap — the package's field order is not the printing order, and assuming it was is how the
  // board came to claim the batting team was away.
  table.append(...(offenseIsHome ? [defense(), offense()] : [offense(), defense()]));
  return table;
}

/* ---- the grid -------------------------------------------------------------------------------- */

function headerRow(columns, withSlot) {
  const row = el("tr");
  if (withSlot) row.append(el("th", null, text("board.slot")));
  row.append(el("th", null, ""));
  for (const column of columns) row.append(el("th", null, text(`column.${column}`)));
  return row;
}

function totalsRow(columns, nameOf, game, cellNode) {
  const row = el("tr");
  row.append(el("td", null, ""));
  row.append(el("td", "label", text("board.totals")));
  for (const column of columns) row.append(cellNode(nameOf(column), game));
  return row;
}

/**
 * One section of the board — batting or pitching — with its own header and its own pinned totals.
 *
 * §6's measurement: rows on screen do not bind, because with the active section's totals pinned they
 * never scroll away and 70% of steps touch rows within a five-row window. That is why this is two
 * scrolling sections rather than one paginated board.
 */
export function renderSection({ title, columns, rows, labels, slots, cellName, totalName, game, onSelect }) {
  const wrapper = el("div");
  wrapper.append(el("div", "section-title", title));

  const table = el("table", "grid");
  const group = el("colgroup");
  const slotCol = el("col", "slot");
  group.append(slotCol, el("col", "label"));
  for (const _ of columns) group.append(el("col"));
  table.append(group);

  const cellNode = (name) => {
    const cell = el("td", "cell");
    cell.dataset.cell = name;
    paint(cell, game);
    cell.addEventListener("click", () => onSelect(name));
    return cell;
  };

  const head = el("thead");
  head.append(headerRow(columns, true));
  table.append(head);

  const body = el("tbody");
  rows.forEach((_, index) => {
    const row = el("tr");
    const reference = slots ? slots[index] : "";
    row.append(el("td", "slot", reference));
    // ⚠️ **Indentation marks a row that did not start, and the suffix is not what says so.** Reading
    // the row label to decide this is what broke three separate decisions when the suffix was removed;
    // the slot reference carries a letter only where a slot is shared, and the first row of a shared
    // slot is the starter.
    const shared = slots && reference.length > 1;
    const firstOfSlot = !slots || index === 0 || slots[index][0] !== slots[index - 1][0];
    row.append(el("td", `label${shared && !firstOfSlot ? " substitute" : ""}`, labels[index]));
    for (const column of columns) row.append(cellNode(cellName(index, column)));
    body.append(row);
  });
  table.append(body);

  const foot = el("tfoot");
  foot.append(totalsRow(columns, totalName, game, cellNode));
  table.append(foot);

  wrapper.append(table);
  return wrapper;
}

/** A cell's appearance, derived from the game. The layer asks; it does not decide. */
export function paint(node, game) {
  const name = node.dataset.cell;
  const blank = game.isBlank(name);
  const value = game.value(name);
  node.classList.toggle("blank", blank);
  node.classList.toggle("given", !blank);
  const isInnings = name.startsWith("pitching") && name.endsWith(".outs");
  node.textContent = value === null ? "" : isInnings ? inningsToDisplay(value) : String(value);
}

/* ---- the footnote line ----------------------------------------------------------------------- */

/**
 * LOB, HBP, SF, SH and CI, attributed per batter and **labelled by the lineup slot, never by name** —
 * a name would hand the player a row before they earned it (§7).
 *
 * ⚠️ A term whose per-batter cell is erased is shown as a question, not omitted. The blank is part of
 * the puzzle: the measurement says a group carrying a live term blocks the rest of the board in the
 * majority of trials, so hiding the fact that a term exists would remove the deduction entirely.
 */
export function renderFootnotes(puzzle, game) {
  const line = el("div", "footnotes");
  line.append(el("span", "lob", `${text("board.left_on_base")}: ${puzzle.puzzle.leftOnBase}`));

  for (const column of FOOTNOTE_COLUMNS) {
    const holders = [];
    let unknown = false;
    puzzle.puzzle.footnotes.forEach((_, row) => {
      const value = game.value(footnoteCell(row, column));
      if (value === null) unknown = true;
      // ⚠️ **`#` in front, because a bare slot reference collides with a count.** Rendered without it,
      // a sacrifice hit by the second batter printed as `SH: 2`, which reads as *two sacrifice hits* —
      // the footnote stating a fact it is not stating. The board already calls this column `#`.
      else if (value > 0) holders.push(`#${puzzle.slotReferences[row]}${value > 1 ? `×${value}` : ""}`);
    });
    const total = game.value(`footnote_totals.${column}`);
    if (total === 0 && !unknown) continue;

    const term = el("span", `term ${unknown ? "unknown" : holders.length ? "live" : "zero"}`);
    term.append(document.createTextNode(`${text(`column.${column}`)}: `));
    term.append(el("span", "who", holders.join(", ") || (unknown ? "?" : "0")));
    if (unknown && holders.length) term.append(document.createTextNode(" +?"));
    line.append(term);
  }
  return line;
}

/* ---- keypad ---------------------------------------------------------------------------------- */

/**
 * The phone's input. **A custom keypad, not the system keyboard**: the system one covers the board,
 * offers letters nobody needs, and cannot carry the thirds keys innings are entered with.
 */
export function renderKeypad(onKey) {
  const pad = el("div", "keypad");
  for (const digit of [1, 2, 3, 4, 5, 6, 7, 8, 9, 0]) {
    const key = el("button", null, String(digit));
    key.addEventListener("click", () => onKey({ digit }));
    pad.append(key);
  }
  for (const [label, thirds] of [[text("keypad.third"), 1], [text("keypad.two_thirds"), 2]]) {
    const key = el("button", "thirds", label);
    key.addEventListener("click", () => onKey({ thirds }));
    pad.append(key);
  }
  const clear = el("button", "wide", text("keypad.clear"));
  clear.addEventListener("click", () => onKey({ clear: true }));
  pad.append(clear);
  return pad;
}

export const columnsFor = { batting: BATTING_COLUMNS, pitching: PITCHING_COLUMNS };
export const totalNameFor = { batting: battingTotalCell, pitching: pitchingTotalCell };
