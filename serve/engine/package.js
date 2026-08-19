/**
 * Reading a puzzle package, and refusing a malformed one **at the boundary**.
 *
 * ⚠️ **Validate at the boundary, not downstream.** Row widths, integer-or-null cells, complete line
 * score fields and object-shaped metadata are checked here, before any arithmetic. A malformed package
 * must produce a controlled rejection naming the field, never an uncontrolled `TypeError` three layers
 * later when a row turns out to be one cell short.
 *
 * ⚠️ **The client does not verify signatures**, and this file contains no verifier by design. See
 * `docs/serve-brief.md` §5: a signature checked in the browser proves nothing, because the code doing
 * the checking arrived from the same place as the thing being checked. Verification happens on the
 * forge before publication.
 *
 * The engine knows nothing about screens (C5) and nothing about what day it is (C4). This function
 * takes parsed JSON and returns a puzzle; a loader decides which one.
 */

import { BATTING_COLUMNS, FOOTNOTE_COLUMNS, PITCHING_COLUMNS } from "./columns.js";

export class PackageError extends Error {}

const READABLE = [2];

const LINE_SCORE_SCALARS = [
  "offense_runs",
  "offense_hits",
  "offense_errors",
  "defense_runs",
  "defense_hits",
  "defense_errors",
];

const fail = (message) => {
  throw new PackageError(message);
};

const isWholeNumber = (value) => Number.isInteger(value) && value >= 0;

/** A cell: a whole number, or `null` for a blank. Anything else is malformed, including `true`. */
function cell(value, where) {
  if (value === null) return null;
  if (!isWholeNumber(value)) fail(`${where} is ${JSON.stringify(value)}, expected a whole number or null`);
  return value;
}

function rows(raw, width, where) {
  if (!Array.isArray(raw)) fail(`${where} is ${typeof raw}, expected an array of rows`);
  return raw.map((row, index) => {
    if (!Array.isArray(row)) fail(`${where}[${index}] is ${typeof row}, expected an array`);
    // ⚠️ Exact width, not minimum. A short row reads the next column's value into this one and every
    // total still balances, which is the class of defect nothing arithmetic can catch.
    if (row.length !== width) fail(`${where}[${index}] has ${row.length} cells, expected ${width}`);
    return row.map((value, column) => cell(value, `${where}[${index}][${column}]`));
  });
}

function totals(raw, width, where) {
  if (!Array.isArray(raw) || raw.length !== width) {
    fail(`${where} has ${Array.isArray(raw) ? raw.length : typeof raw} cells, expected ${width}`);
  }
  return raw.map((value, column) => cell(value, `${where}[${column}]`));
}

function lineScore(raw) {
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) {
    fail(`line_score is ${Array.isArray(raw) ? "an array" : typeof raw}, expected an object`);
  }
  const score = {};
  for (const field of LINE_SCORE_SCALARS) {
    if (!isWholeNumber(raw[field])) fail(`line_score.${field} is ${JSON.stringify(raw[field])}, expected a whole number`);
    score[field] = raw[field];
  }
  // ⚠️ **The two half-innings have different lengths and that is not an error.** A home side leading
  // after the visitors bat in the ninth never bats again, so `offense_by_inning` can be one shorter
  // than `defense_by_inning`. Two of the six reference packages are like this. A validator demanding
  // equal lengths would reject a third of real baseball.
  for (const field of ["offense_by_inning", "defense_by_inning"]) {
    if (!Array.isArray(raw[field]) || raw[field].length === 0) {
      fail(`line_score.${field} is ${JSON.stringify(raw[field])}, expected a non-empty array`);
    }
    score[field] = raw[field].map((value, inning) => {
      if (!isWholeNumber(value)) fail(`line_score.${field}[${inning}] is ${JSON.stringify(value)}, expected a whole number`);
      return value;
    });
  }
  return score;
}

function board(raw, where) {
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) fail(`${where} is not an object`);
  const batting = rows(raw.batting, BATTING_COLUMNS.length, `${where}.batting`);
  const pitching = rows(raw.pitching, PITCHING_COLUMNS.length, `${where}.pitching`);
  const footnotes = rows(raw.footnotes, FOOTNOTE_COLUMNS.length, `${where}.footnotes`);
  if (footnotes.length !== batting.length) {
    fail(`${where}.footnotes has ${footnotes.length} rows and batting has ${batting.length}`);
  }
  return {
    batting,
    battingTotals: totals(raw.batting_totals, BATTING_COLUMNS.length, `${where}.batting_totals`),
    pitching,
    pitchingTotals: totals(raw.pitching_totals, PITCHING_COLUMNS.length, `${where}.pitching_totals`),
    footnotes,
    footnoteTotals: totals(raw.footnote_totals, FOOTNOTE_COLUMNS.length, `${where}.footnote_totals`),
    // ⚠️ LOB is a team scalar and is never erased: without it the board cannot express the global
    // identity at all (§6). `null` here is a malformed package, not a blank cell.
    leftOnBase: isWholeNumber(raw.left_on_base) ? raw.left_on_base : fail(`${where}.left_on_base is not a whole number`),
    lineScore: lineScore(raw.line_score),
  };
}

const strings = (raw, length, where) => {
  if (!Array.isArray(raw) || raw.length !== length) {
    fail(`${where} has ${Array.isArray(raw) ? raw.length : typeof raw} entries, expected ${length}`);
  }
  return raw.map((value, index) => (typeof value === "string" ? value : fail(`${where}[${index}] is not a string`)));
};

/**
 * A validated puzzle, or a `PackageError` naming the field that was wrong.
 *
 * The returned object is the engine's whole world: a board with blanks, the solution, the row labels,
 * the slot references, and the metadata seam C3 requires be present even when unused.
 */
export function readPackage(raw) {
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) fail("the package is not an object");
  if (!Number.isInteger(raw.schema) || typeof raw.schema === "boolean" || !READABLE.includes(raw.schema)) {
    fail(`package schema ${JSON.stringify(raw.schema)}, this client reads ${JSON.stringify(READABLE)}`);
  }
  if (typeof raw.puzzle_id !== "string" || !/^[0-9a-f]{16}$/.test(raw.puzzle_id)) {
    fail(`puzzle_id is ${JSON.stringify(raw.puzzle_id)}, expected sixteen hex characters`);
  }
  const puzzle = board(raw.puzzle, "puzzle");
  const solution = board(raw.solution, "solution");
  if (solution.batting.length !== puzzle.batting.length || solution.pitching.length !== puzzle.pitching.length) {
    fail("the solution does not have the same shape as the puzzle");
  }
  if (raw.metadata !== undefined && (raw.metadata === null || typeof raw.metadata !== "object" || Array.isArray(raw.metadata))) {
    fail("metadata is present and is not an object");
  }
  return {
    id: raw.puzzle_id,
    schema: raw.schema,
    puzzle,
    solution,
    labels: strings(raw.labels, puzzle.batting.length, "labels"),
    pitcherLabels: strings(raw.pitcher_labels, puzzle.pitching.length, "pitcher_labels"),
    // ⚠️ **Produced once on the forge, never derived here.** Which rows share a lineup slot is a fact
    // about the game, and a client that recomputed it would be the second place encoding one rule.
    slotReferences: strings(raw.slot_references, puzzle.batting.length, "slot_references"),
    metadata: raw.metadata ?? {},
    reveal: raw.reveal ?? null,
  };
}
