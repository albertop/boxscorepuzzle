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

export function renderLineScore(score, offenseIsHome, labels = null) {
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
      // ⚠⚠ **The marker is drawn exactly as a run is drawn.** It carries `value` for the styling
      // and `unplayed` as a name only -- there is no rule on that class. It reads as not-a-value
      // because it is a letter among numerals, which is the same argument that retired the dimming:
      // if full contrast costs nothing in meaning, neither does full weight. One fewer thing with
      // special handling is one fewer place for the two to drift apart.
      row.append(
        el(
          "td",
          played ? "value" : "value unplayed",
          played ? String(byInning[i]) : text("board.inning_not_played"),
        ),
      );
    }
    row.append(el("td", "value rhe rhe-rule", String(runs)));
    row.append(el("td", "value rhe", String(hits)));
    row.append(el("td", "value rhe", String(errors)));
    return row;
  };

  // ⚠️ **A parameter of this renderer, never a second line score.** During play the rows are `AWAY`
  // and `HOME`, because the player has no clubs yet (§7). On the reveal they are the clubs, because the
  // player has just earned them — and a reveal drawn by a *copy* of this function is how a comparison
  // page came to show something other than what it was evaluating, twice. The labels change; nothing
  // else does.
  const offense = () =>
    side(
      labels ? labels.offense : text(offenseIsHome ? "side.home" : "side.away"),
      score.offense_by_inning,
      score.offense_runs,
      score.offense_hits,
      score.offense_errors,
    );
  const defense = () =>
    side(
      labels ? labels.defense : text(offenseIsHome ? "side.away" : "side.home"),
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

  const cellNode = (name, rowLabel) => {
    const cell = el("td", "cell");
    cell.dataset.cell = name;
    if (game.isBlank(name)) {
      const column = text(`column.${name.split(".")[1]}`);
      // ⚠️ **The context only, and set before the first paint.** The value is appended by `paint()`,
      // because an `aria-label` written once at render stops describing the element the moment the
      // element changes — and painting first left the opening state as bare context, so the very cell a
      // screen-reader user meets first was the one that said least.
      cell.dataset.label = `${rowLabel}, ${column}`;
      reachable(cell, { label: cell.dataset.label, selected: false });
    }
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
    for (const column of columns) row.append(cellNode(cellName(index, column), labels[index]));
    body.append(row);
  });
  table.append(body);

  const foot = el("tfoot");
  foot.append(totalsRow(columns, totalName, game, (name) => cellNode(name, text("board.totals"))));
  table.append(foot);

  wrapper.append(table);
  return wrapper;
}

/**
 * Make a cell reachable by something other than a finger.
 *
 * ⚠️ **Editable cells were `td` and `span` elements with click handlers and nothing else** — no focus,
 * no role, no keyboard activation, no accessible name, no selected state. A player using VoiceOver,
 * TalkBack, switch control or an attached keyboard could not *find* a blank, let alone fill one: the
 * keypad was focusable and useless, because it does nothing until a cell is selected. The board was
 * unusable before the first digit, and that needs no unusual setup — a phone and its own screen reader.
 *
 * The name is built from what the row and column already say, so a screen reader announces `SS, hits,
 * blank` rather than `blank`. It is assembled from the catalogue, not written here (C11).
 */
function reachable(node, { label, selected }) {
  node.tabIndex = 0;
  node.setAttribute("role", "button");
  node.setAttribute("aria-label", label);
  // The name is completed by `paint()` on every redraw; see the note there.
  node.setAttribute("aria-pressed", selected ? "true" : "false");
  node.addEventListener("keydown", (event) => {
    // Enter and Space are what `role="button"` promises. Anything else belongs to the page.
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    node.click();
  });
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
  const shown = value === null ? "" : isInnings ? inningsToDisplay(value) : String(value);
  node.textContent = shown;
  // ⚠️ **The accessible name is redrawn here or it is not redrawn at all.** An explicit `aria-label`
  // *replaces* the element's text as its name, so a label written once at render described the cell
  // until the first entry and then described nothing: a screen reader read `SS, H` whether the cell held
  // nothing, a 1 or a 17. `aria-pressed` says which cell is selected; it says nothing about what is in
  // it. On a board whose whole interaction is re-reading your own earlier entries, that is the one thing
  // the accessible path could not do.
  //
  // Derived in the same redraw as the visual state on purpose. Two paths computing one fact is how they
  // drift, and this pair had already drifted once.
  if (node.dataset.label) {
    node.setAttribute("aria-label", `${node.dataset.label}, ${shown === "" ? text("cell.blank") : shown}`);
  }
}

/* ---- the footnote line ----------------------------------------------------------------------- */

/**
 * LOB, HBP, SF, SH and CI, **given** and read-only, attributed per batter and labelled by the lineup
 * slot rather than by name — a name would hand the player a row before they earned it (§7).
 *
 * ⚠️ **These were erasable cells for a week and are text again, on a measurement.** The cells were
 * opened because a run said they took the median board from 5 stalls to 15; the run was counting the
 * solver deducing zeros. With them given, coverage at every target is the same as with them erasable,
 * because **96% of the pool's footnote terms are zero** and most boards have not one term to erase.
 *
 * The cell drawing that lived here — `v05-P1-02`, the last open item across ten reviews — is **deleted
 * rather than disabled**, with the four-line block and its 24% of the screen. A drawing kept for a case
 * that no longer exists is a mechanism kept past its problem.
 *
 * ⚠️ The totals row is still never erased and the count is still always known, so nothing here invents
 * uncertainty: a term whose total is zero did not happen and is not printed at all. §6 warns that nine
 * boards in ten carry nothing on this line and that players learn to stop reading it, which is why a
 * live term is marked and an empty one is not printed.
 */
export function renderFootnotes(puzzle, game) {
  const line = el("div", "footnotes");
  const terms = [];

  for (const column of FOOTNOTE_COLUMNS) {
    const total = game.value(footnoteTotalCell(column));
    // A term that did not happen is not printed. Nine boards in ten look like this.
    if (total === null || total === 0) continue;

    // ⚠️ **`<count> #<slot>`, and the count prints even when it is one.** The old form printed the
    // term total and then bare slot references — `SH: 2` was a *slot*, not a count, and a row carrying
    // two of one term could not be expressed at all. Measured over the gated pool: 4,019 of 100,226
    // directions carry such a row (4.01%, 8.31% in the 1920s). Those boards cannot be solved:
    // `PA = AB + BB + HBP + SF + SH + CI` has no other route to the value, and every total still
    // balances, which is why nothing in the four layers saw it.
    //
    // A format that shows the count only when it exceeds one is ambiguous again — the same trap as a
    // slot letter appearing only when the slot is shared, which made the old form unambiguous by
    // accident rather than by design.
    const holders = [];
    puzzle.puzzle.footnotes.forEach((_, row) => {
      const value = game.value(footnoteCell(row, column));
      if (value > 0) holders.push(`${value} ${text("board.slot")}${puzzle.slotReferences[row]}`);
    });

    const term = el("span", "term live");
    term.append(el("span", "term-label", `${text(`column.${column}`)}: `));
    term.append(el("span", "who", holders.join(", ")));
    terms.push(term);
  }

  // ⚠️ **LOB last, and it used to be first here while the PDF put it last.** One of three ways the two
  // renderers had drifted — with no count and no `#` being the other two — none of which a reading of
  // either page alone would show. `serve/tests/footnote-line-vectors.json` is the one string both are
  // now answerable to; §33 forbids them sharing the function, so they share the data.
  terms.push(el("span", "term lob", `${text("board.left_on_base")}: ${puzzle.puzzle.leftOnBase}`));
  terms.forEach((term, index) => {
    // Real text nodes, not CSS spacing: the separator is part of the canonical string the two
    // renderers are compared on, so it has to survive `textContent`.
    if (index > 0) line.append(document.createTextNode("   "));
    line.append(term);
  });
  return line;
}

/**
 * A typed digit appended to what is already in the cell. **At most two digits, and never a leading zero.**
 *
 * ⚠️ **Two rules, and the innings path obeyed neither.** The grid path capped at 99; the innings path
 * grew without any bound at all, so `IP` accepted `8444` — four digits in a cell 44px wide, and a value
 * no baseball game has produced. One function now, because the same rule written twice is the shape
 * every serious defect in this project has had.
 *
 * ⚠️ **The leading zero is refused explicitly, not left to `Number()`.** `Number("05")` is 5, so the
 * old code happened to be right — by a coercion, not by a rule. A reader could not tell whether the
 * behaviour was intended, and the next person to reach for `parseInt` or string concatenation would
 * have lost it silently.
 *
 * Filling past two digits **replaces** rather than refusing: a player who typed the wrong number can
 * keep typing, which is the behaviour a phone keypad has everywhere else. §27 has no fail state and
 * this is the same principle one level down.
 */
export function grow(current, digit) {
  if (current === null || current === 0) return digit;
  const grown = Number(`${current}${digit}`);
  return grown > 99 ? digit : grown;
}

/* ---- keypad ---------------------------------------------------------------------------------- */

/**
 * What one keypad press does to one cell. **The whole input rule, in one testable place.**
 *
 * ⚠️ **It lived in the shell, where nothing could reach it.** `main.js` is not imported by the test
 * suite — it boots the application — so every rule written there was unguarded by construction. That is
 * how the thirds branch came to run ahead of the flag it depends on, and how the digit cap came to exist
 * in one of the two places it was written. Both were found by a person pressing keys.
 *
 * The shell keeps what is genuinely its own: which cell is selected, and when to repaint.
 */
export function applyKey(game, name, key) {
  if (key.clear) {
    game.enter(name, null);
    return;
  }
  const innings = isInningsCell(name);
  if (key.thirds !== undefined) {
    // ⚠️ **The guard that was missing.** A thirds key on a plain-integer cell computed
    // `floor(current / 3) * 3 + thirds` and wrote a whole number: `1⁄3` on an empty hits cell entered
    // `1`. A control doing something other than what is printed on it, into a board that deliberately
    // withholds correctness feedback — so the value travels into every deduction after it.
    //
    // The pad disables these keys too. Both, because a control prevented only by being greyed out works
    // again the moment anything reaches it another way.
    if (!innings) return;
    // Innings are entered as whole innings then a third, the way they are written. The thirds keys
    // adjust the current entry rather than appending a digit, because `6` then `⅓` is `6.1` and not
    // sixty-one.
    const current = game.value(name) ?? 0;
    game.enter(name, Math.floor(current / 3) * 3 + key.thirds);
    return;
  }
  if (innings) {
    // The whole innings grow; the thirds are held above. This had no cap while the grid path had one.
    const current = game.value(name) ?? 0;
    game.enter(name, grow(Math.floor(current / 3), key.digit) * 3 + (current % 3));
    return;
  }
  game.enter(name, grow(game.value(name), key.digit));
}

/**
 * Whether a cell is measured in thirds of an inning. **The only cell a thirds key means anything for.**
 *
 * ⚠️ Exported so the handler and the keypad ask one question. They asked two: the shell computed this
 * for the digit branch and the thirds branch ran before it, so `1⁄3` on a *hits* cell wrote a whole `1`.
 */
export const isInningsCell = (name) => name.startsWith("pitching") && name.endsWith(".outs");

/**
 * The phone's input. **A custom keypad, not the system keyboard**: the system one covers the board,
 * offers letters nobody needs, and cannot carry the thirds keys innings are entered with.
 *
 * Returns the pad and `allowThirds`, which the shell calls on every selection. ⚠️ **The buttons are
 * disabled and the handler still refuses**: a control that is only prevented by being greyed out is a
 * control that works again the moment anything reaches it another way — a keyboard, a test, a future
 * layer. Presentation says *not here*; the handler is what makes it true.
 */
export function renderKeypad(onKey, onCheck) {
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

  // ⚠️⚠️ **Check sits in the pad's last slot, and this used to be an argument against.** The note that
  // stood here said a button ending the game must not sit under the thumb, because that is a game
  // ended by accident. What answers it is not the position but the gate: the key is **disabled for the
  // whole time the player is filling cells**, so the only moment it can be pressed by accident is the
  // instant after the last digit.
  //
  // ⚠️ **And that accident costs nothing, which is why the trade holds.** §27 has no fail state: an
  // unwanted press on a complete-but-wrong board says the board does not balance and records the cells
  // that were wrong — exactly what a deliberate press would have done a second later. The clock does
  // not stop and attempts are unlimited.
  const check = el("button", "check", text("done.check"));
  check.addEventListener("click", () => onCheck());
  pad.append(check);
  pad.allowThirds = (allowed) => {
    for (const key of pad.querySelectorAll("button.thirds")) {
      key.disabled = !allowed;
      // The name has to say it too: a disabled button a screen reader announces as available is a
      // control that reads as broken rather than as inapplicable.
      key.setAttribute("aria-disabled", allowed ? "false" : "true");
    }
  };
  /**
   * Whether the board can be checked at all: **every blank filled, and nothing about whether it is
   * right.**
   *
   * ⚠️ A disabled key here tells the player their board is incomplete, which is a fact they can
   * already read off the grid — unlike *which* cells are wrong or *how many*, which the board may
   * never say. Completeness is not a step toward the answer; correctness is.
   */
  pad.allowCheck = (allowed) => {
    check.disabled = !allowed;
    // The name has to say it too: a disabled control a screen reader announces as available reads as
    // broken rather than as inapplicable. Same rule as the thirds keys.
    check.setAttribute("aria-disabled", allowed ? "false" : "true");
  };

  pad.allowThirds(false);
  pad.allowCheck(false);
  return pad;
}

export const columnsFor = { batting: BATTING_COLUMNS, pitching: PITCHING_COLUMNS };
export const totalNameFor = { batting: battingTotalCell, pitching: pitchingTotalCell };
