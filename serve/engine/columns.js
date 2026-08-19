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

/** HBP, SF, SH, CI — the footnote line. **Per-batter cells are erasable; the totals row is not** (§6). */
export const FOOTNOTE_COLUMNS = ["hit_by_pitch", "sacrifice_flies", "sacrifice_hits", "catcher_interference"];

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
 * Innings held as outs, rendered as a printed boxscore renders them.
 *
 * `to` and `from` are inverses over every value the board can hold, which the tests assert rather than
 * assume — `6.1` and `6.2` are the only fractions baseball writes, and a naive `outs / 3` produces
 * `6.333`.
 */
export const inningsToDisplay = (outs) => {
  const whole = Math.floor(outs / 3);
  const thirds = outs % 3;
  return thirds === 0 ? String(whole) : `${whole}.${thirds}`;
};

export const inningsFromDisplay = (text) => {
  const match = /^(\d+)(?:\.([12]))?$/.exec(text.trim());
  if (match === null) return null;
  return Number(match[1]) * 3 + Number(match[2] ?? 0);
};
