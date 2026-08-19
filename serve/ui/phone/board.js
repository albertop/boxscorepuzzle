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
  footnoteTotalCell,
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
  // Whatever the game actually had. Nine is the usual number and not a rule: extra innings exist, and a
  // scoreboard hard-coded to nine would silently drop the innings that decided the game.
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
      text(offenseIsHome ? "side.home" : "side.away"),
      score.offense_by_inning,
      score.offense_runs,
      score.offense_hits,
      score.offense_errors,
    );
  const defense = () =>
    side(
      text(offenseIsHome ? "side.away" : "side.home"),
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

  // ⚠️ **The label and the column row are one header, not two things.** Kept as separate elements they
  // scrolled independently, competed for `top: 0`, and the section name covered the column names — and
  // even fixed, a title floating above a table reads as a caption for the page rather than as part of
  // the board. Inside the head they are a single sticky block with one background.
  const head = el("thead");
  const titleRow = el("tr");
  const titleCell = el("th", "section-title", title);
  titleCell.colSpan = columns.length + 2;
  titleRow.append(titleCell);
  head.append(titleRow);
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
  node.classList.toggle("filled", blank && value !== null);
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
export function renderFootnotes(puzzle, game, onSelect) {
  const line = el("div", "footnotes");
  line.append(el("span", "term lob", `${text("board.left_on_base")}: ${puzzle.puzzle.leftOnBase}`));

  for (const column of FOOTNOTE_COLUMNS) {
    // ⚠️ **The totals row is never erased, so the count is always known** (§6 — the row identity does
    // not close without it). The version this replaces printed `?` whenever any per-batter cell in a
    // column was blank, which produced `HBP: ?` on a game with no hit batsmen at all. Nothing invents
    // uncertainty the arithmetic has already removed.
    const total = game.value(footnoteTotalCell(column));
    if (total === null) continue;

    const known = [];
    const unknown = [];
    puzzle.puzzle.footnotes.forEach((_, row) => {
      const name = footnoteCell(row, column);
      if (game.isBlank(name)) unknown.push({ name, slot: puzzle.slotReferences[row] });
      else if (game.value(name) > 0) known.push(`#${puzzle.slotReferences[row]}${game.value(name) > 1 ? `×${game.value(name)}` : ""}`);
    });
    // ⚠️ **A term with nothing to show and nothing to fill is not printed.** §6 warns that nine boards
    // in ten have every term at zero and that players learn to stop reading the line; a row of empty
    // labels is how that habit is taught.
    if (total === 0 && unknown.length === 0) continue;

    // ⚠️ **`live` and `zero` were declared in the stylesheet and never applied.** Both rules were
    // dead, so a real hit batsman had exactly the hierarchy of a term that never happened. §6 warns
    // that nine boards in ten carry nothing here and that players therefore learn to stop looking —
    // the prominence *is* the mechanism, and it went missing when this function was rewritten.
    const term = el("span", `term ${total > 0 ? "live" : "zero"}`);
    const label = el("span", "term-label", `${text(`column.${column}`)}: ${total}`);
    term.append(label);
    if (known.length) term.append(el("span", "who", known.join(", ")));
    for (const { name, slot } of unknown) {
      // The same cell the player has been filling all along, drawn somewhere else. `paint` and the
      // selection find it by `data-cell` exactly as they find one in the grid.
      const cell = el("span", "cell");
      cell.dataset.cell = name;
      paint(cell, game);
      cell.addEventListener("click", () => onSelect(name));
      term.append(cell, el("span", "who", `#${slot}`));
    }
    // Tapping the label selects the term's first unknown, so the target is the label and the box
    // together and the box can stay small in a line of text.
    if (unknown.length) label.addEventListener("click", () => onSelect(unknown[0].name));
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
  for (const thirds of [1, 2]) {
    // ⚠️ Composed from digits rather than printed as `⅓`: see the note in board.css. The catalogue
    // still owns the pieces, so a language that writes a third differently changes them there.
    const key = el("button", "thirds");
    const frac = el("span", "frac");
    frac.append(el("span", "num", String(thirds)), el("span", "bar", text("keypad.fraction_bar")), el("span", "den", text("keypad.fraction_denominator")));
    key.append(frac);
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
