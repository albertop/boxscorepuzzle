/**
 * The board's vocabulary: which columns exist, in which order, and how a cell is named.
 *
 * ⚠️ **These tuples are a copy of `forge/src/boxscore_package/format.py`, and the order is part of the
 * format** — the package stores arrays, so a column tuple in a different order silently reads every
 * value as a different statistic. Two places encoding one rule is this project's named failure shape,
 * and the only reason there are two is that the client cannot import Python. `serve/tests/` asserts
 * the widths against the six real packages, which is the check that makes the copy survivable.
 *
 * Cell names match the forge's `constraints.py` exactly, so a cell can be named identically on both
 * sides of the boundary and a bug report can quote one string.
 */

/** PA, AB, R, H, BB, SO — the six the board shows (§6). RBI was dropped for PA. */
export const BATTING_COLUMNS = ["plate_appearances", "at_bats", "runs", "hits", "walks", "strikeouts"];

/** IP, H, R, ER, BB, SO, with innings held as outs and rendered as thirds. */
export const PITCHING_COLUMNS = ["outs", "hits", "runs", "earned_runs", "walks", "strikeouts"];

/**
 * HBP, SF, SH, CI — the footnote line, **given in full: nothing here is erasable** (§6).
 *
 * ⚠️ The cells were opened, then closed again by the pool run — coverage was identical with them
 * erasable and with them given, because 96% of the pool's footnote terms are zero and the solver was
 * counting itself deducing them. This comment claimed the opposite until someone read it.
 */
export const FOOTNOTE_COLUMNS = ["hit_by_pitch", "sacrifice_flies", "sacrifice_hits", "catcher_interference"];

/**
 * The columns a **printed boxscore** carries, which are not the columns the board plays with.
 *
 * `AB R H RBI` is what a newspaper set, plus the two the player deduced. ⚠️ **`PA` is absent and `RBI`
 * is present, and that is the whole reason the reveal is worth drawing.** §6 spends a board column on
 * `PA` because `PA` is what breaks the constraint forest; `RBI` earns none of that — no cross-team
 * counterpart, no place in the row identity — which is exactly why it is the one number on the
 * finished sheet the puzzle never asked for.
 *
 * ⚠️ **Here rather than in the reader or the renderer, because both need it and one list is the
 * point.** They are the keys of `reveal.boxscore.*.batting` and `.pitching` in schema 5, so the order
 * is part of the format the same way the board's is.
 */
export const PRINTED_BATTING = ["ab", "r", "h", "rbi", "bb", "so"];
export const PRINTED_PITCHING = ["outs", "h", "r", "er", "bb", "so"];

export const battingCell = (row, column) => `batting[${row}].${column}`;
export const battingTotalCell = (column) => `batting_totals.${column}`;
export const footnoteCell = (row, column) => `footnotes[${row}].${column}`;
export const footnoteTotalCell = (column) => `footnote_totals.${column}`;
export const pitchingCell = (row, column) => `pitching[${row}].${column}`;
export const pitchingTotalCell = (column) => `pitching_totals.${column}`;

/**
 * Which block of the board a cell belongs to: `batting`, `pitching` or `footnotes`.
 *
 * ⚠️ **A column name alone does not identify a column.** `hits` names a batting column *and* a pitching
 * column, and `batting[3].hits` and `pitching[0].hits` sit in different equations entirely — one is the
 * offence's hits, the other is what the opposing staff allowed. Anything that asks "is this the same
 * column" has to ask "in the same block" first, or it will relate two grids that share nothing but a
 * word. A name is not the thing, one more time.
 *
 * A totals row belongs to its own grid, because that is where its column sum closes.
 */
export const sectionOf = (name) => name.split(/[[.]/)[0].replace("_totals", "");

/**
 * Which notation a surface writes. **Named at the call site, never inferred.**
 *
 * ⚠️⚠️ **Two notations, one conversion, and they are not a contradiction.** Both are correct about
 * their own surface, and each used to have a comment defending it as though the other were a mistake:
 *
 *   `PRINTED` — the reveal. A newspaper boxscore writes `9.0`, and the reveal exists to be that
 *   object. In a column where some rows read `4.1`, the trailing digit is what makes the column line up.
 *
 *   `BOARD` — the grid the player types into. The keypad offers `.1` and `.2`, so a whole inning is
 *   entered as `4`; padding it to `4.0` would show a form the keypad never produces.
 *
 * A string rather than a boolean, because `inningsToDisplay(outs, true)` sends the next reader here to
 * find out what `true` means about a boxscore.
 */
export const INNINGS = { PRINTED: "printed", BOARD: "board" };

/**
 * Innings held as outs, written the way the asked-for surface writes them.
 *
 * ⚠️ **The notation is required.** It had none, so every caller inherited the board's and the reveal
 * quietly grew a hand-written copy to get the other one — which is how `4` and `9.0` came to be on
 * screen in the same product. Stating it costs one word and removes the question.
 *
 * ⚠️ **Mirrors `forge/src/boxscore_package/innings.py`**, which cannot be imported here (§33) and
 * carries the same two notations. `serve/tests/package-vectors.json` is what keeps the two answerable
 * to the same values rather than to each other.
 *
 * `to` and `from` are inverses over every value the board can hold, in both notations, which the tests
 * assert rather than assume — `6.1` and `6.2` are the only fractions baseball writes, and a naive
 * `outs / 3` produces `6.333`.
 */
/**
 * The two halves of an innings value, and how to replace one of them.
 *
 * ⚠️ **Here rather than in the keypad handler, because three is the representation.** `board.js` did
 * `Math.floor(current / 3) * 3 + key.thirds` and `grow(...) * 3 + (current % 3)` inline — the same
 * `3` that `inningsToDisplay` spends, in a file that is about which key was pressed. It is the
 * *inverse* of the conversion rather than a copy of it, which is exactly the relationship that makes a
 * number end up in two places: nobody looking for copies of a formatter finds the parser.
 *
 * If the representation ever changes, it changes in one file.
 */
export const withThirds = (outs, thirds) => Math.floor(outs / 3) * 3 + thirds;
export const withWholeInnings = (outs, whole) => whole * 3 + (outs % 3);
export const wholeInningsOf = (outs) => Math.floor(outs / 3);

export const inningsToDisplay = (outs, notation) => {
  if (notation !== INNINGS.PRINTED && notation !== INNINGS.BOARD) {
    throw new Error(`inningsToDisplay needs a notation from INNINGS, got ${JSON.stringify(notation)}`);
  }
  const whole = Math.floor(outs / 3);
  const thirds = outs % 3;
  return thirds === 0 && notation === INNINGS.BOARD ? String(whole) : `${whole}.${thirds}`;
};

/**
 * ⚠️ **Both notations parse.** This accepted `.1` and `.2` and refused `.0` — so it rejected the exact
 * string the format's own Python reference implementation emits, while the module it lives in claimed
 * to be the one place that converts. `4` and `4.0` are the same twelve outs written for two surfaces.
 *
 * `.3` through `.9` are still refused: three outs is a whole inning, and silently reinterpreting `4.3`
 * would put a number on the board that nobody typed.
 */
export const inningsFromDisplay = (text) => {
  const match = /^(\d+)(?:\.([012]))?$/.exec(text.trim());
  if (match === null) return null;
  return Number(match[1]) * 3 + Number(match[2] ?? 0);
};
