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

import { BATTING_COLUMNS, FOOTNOTE_COLUMNS, PITCHING_COLUMNS, PRINTED_BATTING, PRINTED_PITCHING } from "./columns.js";

export class PackageError extends Error {}

/**
 * Retrosheet's game id: `WS1191306130` — home club, date, and the game's number that day.
 *
 * ⚠️ **The trailing digit is not decoration.** `0` is a game played alone; `1` and `2` are the halves
 * of a doubleheader. Accepting an id without it would produce a link to whichever game Baseball
 * Reference has first, which for a fifth of the published boards is **the other game** — a boxscore
 * that contradicts the one the player just rebuilt.
 */
function retrosheetId(raw, where) {
  if (typeof raw !== "string" || !/^[A-Z0-9]{3}\d{8}[012]$/.test(raw)) {
    fail(`${where} ${JSON.stringify(raw)}, expected a Retrosheet game id like "WS1191306130"`);
  }
  return raw;
}

const READABLE = [6];
// ⚠️ **6, because the reveal gained the game's own id.** Version 5's reveal names both clubs and the
// date, which is everything the Baseball Reference link needs except the trailing digit that separates
// the two halves of a doubleheader — and **29 of 150 published boards are doubleheaders**. A version-5
// file cannot say which game it is, so it is not a version-6 file with a field missing: it is one whose
// reveal cannot answer the question the reveal is for.
// ⚠️ **5, because the reveal became a boxscore and version 4 cannot carry one.** Its `reveal` held the
// names of the rows the board drew, so the finished screen could only redraw the board the player had
// just filled in with names attached. A printed boxscore has both clubs, runs batted in, and the
// clubs' real names rather than three-letter codes. Every version-4 file changes status under this
// reader — it stops being readable — which is exactly the case that must not reuse a number.
//
// ⚠️ **4, not 3, because version 3 could describe a board nobody can finish.** A per-batter footnote
// cell was nullable there, which was right while those cells were erasable; they are given now and the
// line renders as read-only text. The reader accepted the null, the game counted it as a blank the
// player owes, and the UI offered nothing to fill it with. A nullable field becoming non-nullable
// changes what the document means, so it is a new version rather than a stricter reading of the old
// one — `schema: 3` must not mean two things depending on when the file was written.

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

function rows(raw, width, where, { complete = false } = {}) {
  if (!Array.isArray(raw)) fail(`${where} is ${typeof raw}, expected an array of rows`);
  return raw.map((row, index) => {
    if (!Array.isArray(row)) fail(`${where}[${index}] is ${typeof row}, expected an array`);
    // ⚠️ Exact width, not minimum. A short row reads the next column's value into this one and every
    // total still balances, which is the class of defect nothing arithmetic can catch.
    if (row.length !== width) fail(`${where}[${index}] has ${row.length} cells, expected ${width}`);
    return row.map((value, column) => {
      // ⚠️ **`complete` is the same guard `totals` below already carries, and it belonged here too.**
      // That one was written when a null footnote *total* made a board unfinishable. The per-batter
      // cells above it have exactly the same property now that the line is read-only, and the fix was
      // applied to the row underneath and not to the rows over it — a rule applied outward and not
      // inward, thirty lines apart. Measured on the retained generation: 14 of 33 blanks unreachable.
      // The message names the position, not one of the rules that reach here: `complete` now
      // covers the footnote line and the whole answer board, and a message naming the wrong one
      // sends the reader to the wrong contract.
      if (complete && value === null) fail(`${where}[${index}][${column}] is null and must be given`);
      return cell(value, `${where}[${index}][${column}]`);
    });
  });
}

function totals(raw, width, where, { complete = false } = {}) {
  if (!Array.isArray(raw) || raw.length !== width) {
    fail(`${where} has ${Array.isArray(raw) ? raw.length : typeof raw} cells, expected ${width}`);
  }
  return raw.map((value, column) => {
    // ⚠️ **`complete` exists because a null footnote total made the board unfinishable.** The reader
    // accepted it as a blank, `createGame` counted it among the blanks, and the footnote line skips a
    // term whose total is unknown — so the cell existed, had to be filled, and had nowhere to be filled
    // from. The unsolvable-board defect again, reached from the schema side. §6 says that row is never
    // erased; the client now says so too.
    if (complete && value === null) fail(`${where}[${column}] is null and must be given`);
    return cell(value, `${where}[${column}]`);
  });
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

/**
 * A board. **`complete` is the answer board, where no cell anywhere may be missing.**
 *
 * ⚠️ **Two profiles, because one nullable rule for both was wrong in a way the player meets.** A puzzle
 * carries blanks in the batting and pitching grids and their totals; an answer board carries none. Read
 * with one rule, a null answer under a visible blank was accepted by both readers — and `isCorrect()`
 * then returned true for a cell still drawn empty, while entering any number was necessarily wrong.
 * Reproduced before this was written: the cell read blank, counted as correct, and rejected `0`.
 */
/**
 * Every number the puzzle *gives* must be the number the solution holds.
 *
 * ⚠️⚠️ **Only the shape was compared, so a given cell could contradict the answer.** (v36-P2-08)
 * `game.isSolved()` walks every cell, givens included, comparing what the board holds against the
 * answer — so one wrong given makes `isSolved()` permanently false and *Check* answers "Something
 * doesn't add up yet" for ever, on a board where every blank the player owes is correct.
 *
 * **The player has no way to find it.** The board gives no per-cell feedback by design (§2: marking
 * makes probing beat deducing), so an unwinnable day is indistinguishable from a hard one. This is the
 * class this file's own header calls *the unsolvable-board defect, reached from the schema side*.
 *
 * ⚠️ And it is the cheapest tamper available: the client verifies no signatures by design (§23, and
 * a browser checking a signature from the same origin as the verifier is theatre), so one edited byte
 * in a static file bricks a day for everyone. A refusal at the boundary turns that into a package the
 * client declines to open, which is a visible failure rather than a silent one.
 */
function agreesWithTheAnswer(puzzle, solution) {
  const grids = [
    ["batting", puzzle.batting, solution.batting],
    ["pitching", puzzle.pitching, solution.pitching],
    ["footnotes", puzzle.footnotes, solution.footnotes],
  ];
  for (const [name, given, answer] of grids) {
    given.forEach((row, index) =>
      row.forEach((value, column) => {
        if (value !== null && value !== answer[index][column]) {
          fail(`puzzle.${name}[${index}][${column}] gives ${value} and the solution says ${answer[index][column]}`);
        }
      }),
    );
  }
  const rows = [
    ["batting_totals", puzzle.battingTotals, solution.battingTotals],
    ["pitching_totals", puzzle.pitchingTotals, solution.pitchingTotals],
    ["footnote_totals", puzzle.footnoteTotals, solution.footnoteTotals],
  ];
  for (const [name, given, answer] of rows) {
    given.forEach((value, column) => {
      if (value !== null && value !== answer[column]) {
        fail(`puzzle.${name}[${column}] gives ${value} and the solution says ${answer[column]}`);
      }
    });
  }
  // ⚠️ Never erased (§6) and therefore always a given: a disagreement here is a malformed package
  // rather than a blank.
  if (puzzle.leftOnBase !== solution.leftOnBase) {
    fail(`puzzle.left_on_base is ${puzzle.leftOnBase} and the solution says ${solution.leftOnBase}`);
  }
  // ⚠⚠ **The line score, which this compared nothing of until v39-P2-02.** Both halves were parsed,
  // independently and correctly, and then never checked against each other — the two-places-that-should-
  // agree shape, inside the function whose entire job is checking that they do.
  //
  // ⚠️ **It is the board's anchor and it is never erased** (§6), so unlike a grid cell there is no
  // *blank* case to allow: every value is a given and any disagreement is a malformed package. One
  // edited digit here makes a valid daily arithmetically impossible while the checker goes on grading
  // against the untouched solution — a board nobody can solve, refusing every correct answer, with no
  // sign that anything is wrong.
  for (const field of LINE_SCORE_SCALARS) {
    if (puzzle.lineScore[field] !== solution.lineScore[field]) {
      fail(`puzzle.line_score.${field} is ${puzzle.lineScore[field]} and the solution says ${solution.lineScore[field]}`);
    }
  }
  for (const field of ["offense_by_inning", "defense_by_inning"]) {
    const given = puzzle.lineScore[field];
    const answer = solution.lineScore[field];
    // ⚠️ Length first: comparing element by element over a short array agrees about every inning it
    // has and says nothing about the ones it does not, which is a check that passes on a truncation.
    if (given.length !== answer.length) {
      fail(`puzzle.line_score.${field} has ${given.length} innings and the solution has ${answer.length}`);
    }
    given.forEach((value, inning) => {
      if (value !== answer[inning]) {
        fail(`puzzle.line_score.${field}[${inning}] is ${value} and the solution says ${answer[inning]}`);
      }
    });
  }
}

function board(raw, where, { complete = false } = {}) {
  if (raw === null || typeof raw !== "object" || Array.isArray(raw)) fail(`${where} is not an object`);
  const batting = rows(raw.batting, BATTING_COLUMNS.length, `${where}.batting`, { complete });
  const pitching = rows(raw.pitching, PITCHING_COLUMNS.length, `${where}.pitching`, { complete });
  const footnotes = rows(raw.footnotes, FOOTNOTE_COLUMNS.length, `${where}.footnotes`, { complete: true });
  if (footnotes.length !== batting.length) {
    fail(`${where}.footnotes has ${footnotes.length} rows and batting has ${batting.length}`);
  }
  return {
    batting,
    battingTotals: totals(raw.batting_totals, BATTING_COLUMNS.length, `${where}.batting_totals`, { complete }),
    pitching,
    pitchingTotals: totals(raw.pitching_totals, PITCHING_COLUMNS.length, `${where}.pitching_totals`, { complete }),
    footnotes,
    footnoteTotals: totals(raw.footnote_totals, FOOTNOTE_COLUMNS.length, `${where}.footnote_totals`, {
      complete: true,
    }),
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
  return raw.map((value, index) =>
    typeof value === "string" && value.length > 0 ? value : fail(`${where}[${index}] is ${JSON.stringify(value)}`),
  );
};

/**
 * One slot reference per batting row: `9` where a lineup slot holds one row, `9a`/`9b` where shared.
 *
 * ⚠️ **The grammar and the uniqueness were checked on the forge and not here.** A document with a
 * malformed or repeated reference passed the client boundary, and a repeat is the one thing this field
 * exists to prevent: two rows answering to `#5` makes a footnote attribution ambiguous, which is the
 * whole reason the field was added in schema 2. Two readers of one schema, disagreeing about it.
 */
const slotReferences = (raw, rows) => {
  const values = strings(raw, rows, "slot_references");
  for (const [index, value] of values.entries()) {
    if (!/^[1-9][a-z]?$/.test(value)) fail(`slot_references[${index}] is ${JSON.stringify(value)}, expected a slot with an optional letter`);
  }
  if (new Set(values).size !== values.length) fail(`slot_references repeats a value: ${JSON.stringify(values)}`);
  return values;
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
  // ⚠️ `complete: true`. An answer board with a hole is worse than a missing one — a missing one is
  // refused on the line above, while a holed one was accepted by both readers.
  const solution = board(raw.solution, "solution", { complete: true });
  if (solution.batting.length !== puzzle.batting.length || solution.pitching.length !== puzzle.pitching.length) {
    fail("the solution does not have the same shape as the puzzle");
  }
  agreesWithTheAnswer(puzzle, solution);
  // Required and object-shaped, as the document states — not defaulted. Seam C3 makes it deliberately
  // loose in *content*; that is not the same as optional.
  if (raw.metadata === null || typeof raw.metadata !== "object" || Array.isArray(raw.metadata)) {
    fail(`metadata is ${Array.isArray(raw.metadata) ? "an array" : typeof raw.metadata}, expected an object`);
  }
  // ⚠️ **The client cannot work this out and must not try.** Which club batted last is determined by
  // a ragged line score — the home side leading after the top of the ninth never bats again — and
  // undetermined by a square one. Four of the six reference packages are nine and nine. A client that
  // inferred it *where it could* would label the board correctly sometimes and silently wrongly the
  // rest of the time, and a label sits outside the arithmetic, so every total would still balance.
  // Schema 3 exists so the forge, which reads it from the game, says it.
  if (typeof raw.offense_is_home !== "boolean") {
    fail(`offense_is_home is ${JSON.stringify(raw.offense_is_home)}, expected true or false`);
  }
  return {
    id: raw.puzzle_id,
    schema: raw.schema,
    offenseIsHome: raw.offense_is_home,
    puzzle,
    solution,
    labels: strings(raw.labels, puzzle.batting.length, "labels"),
    pitcherLabels: strings(raw.pitcher_labels, puzzle.pitching.length, "pitcher_labels"),
    // ⚠️ **Produced once on the forge, never derived here.** Which rows share a lineup slot is a fact
    // about the game, and a client that recomputed it would be the second place encoding one rule.
    slotReferences: slotReferences(raw.slot_references, puzzle.batting.length),
    metadata: raw.metadata,
    reveal: reveal(raw.reveal, puzzle),
  };
}

/**
 * The reveal, **checked and renamed like every other field.**
 *
 * ⚠️⚠️ **This used to be `raw.reveal ?? null` — passed through untouched, in `snake_case`, while the
 * rest of the package was mapped.** It was defensible while the block was opaque to the engine and
 * nothing read it. Nothing read it because it was drawn nowhere; the moment it was drawn, the
 * exception became one client holding two naming conventions, and it cost a bug the same day:
 * `reveal.offenseTeam` reads `undefined`, renders an empty heading, throws nothing, and does it on the
 * one screen a player reaches once. Two spellings of one field with nothing checking they agree is
 * this project's named failure shape, and the fix is one convention rather than a comment warning
 * about two.
 *
 * ⚠️ **And it is validated here rather than trusted.** From schema 5 this block is a whole boxscore
 * the finished screen draws directly. A malformed one would print `undefined` down a column at the
 * moment the player finishes — the same defect as the null cells, reached from the reveal side. §22:
 * validate at the boundary, so a bad package is a controlled rejection rather than a `TypeError`
 * three layers later.
 */
/**
 * A calendar date, `YYYY-MM-DD`, refused at the boundary rather than downstream.
 *
 * ⚠️ The pattern is deliberately not a full calendar check — `2026-02-31` matches. What it guarantees
 * is the shape `longDate` can split and index a month name with, which is the failure that reached the
 * reveal. A month of `13` would render as a missing catalogue key and throw there instead; that is a
 * narrower hole and it is named here rather than left as an assumption.
 */
const isoDate = (raw, where) => {
  if (typeof raw !== "string" || !/^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/.test(raw)) {
    fail(`${where} is ${JSON.stringify(raw)}, expected a date as YYYY-MM-DD`);
  }
  return raw;
};

function reveal(raw, board) {
  // ⚠⚠ **Required, and this returned `null` for a missing one until v39-P2-02.** From schema 5 the
  // reveal is the complete boxscore the finished screen draws, and the publication gate will not pass a
  // package without one — so an absent reveal is not a draft the client should open, it is a corrupted
  // file. Accepting it let a player solve the entire board and reach a payoff panel with **the boxscore
  // missing**, silently, on the one screen they reach once and the one thing they earned.
  //
  // ⚠️ The optional shape was defensible while nothing drew this block. It stopped being defensible
  // the moment something did, and nothing went red — which is the whole argument for refusing at the
  // boundary rather than tolerating an absence downstream.
  if (raw === undefined || raw === null) {
    fail("reveal is missing; a published package carries the complete boxscore the finished screen draws");
  }
  if (typeof raw !== "object" || Array.isArray(raw)) {
    fail(`reveal is ${JSON.stringify(raw)}, expected an object`);
  }
  // ⚠️ **Counted against the board, never against itself.** The first version of this passed
  // `raw.batter_names.length` as the expected length, which is a check that cannot fail — the
  // condition this project has written down as indistinguishable from a broken check. One name per
  // row is the property the field exists for: a short list is rows the reveal cannot name.
  const batters = board.batting.length;
  const pitchers = board.pitching.length;
  return {
    batterNames: strings(raw.batter_names, batters, "reveal.batter_names"),
    pitcherNames: strings(raw.pitcher_names, pitchers, "reveal.pitcher_names"),
    offenseTeam: text(raw.offense_team, "reveal.offense_team"),
    defenseTeam: text(raw.defense_team, "reveal.defense_team"),
    // ⚠️⚠️ **A date, not merely a string.** (v36-P3-24) This was `text(...)`, so `"yesterday"` parsed
    // fine and `longDate` then computed `month.NaN` and threw **inside `renderReveal`** — which sits in
    // `check()`'s success path, on the one screen the player reaches once, after they have solved the
    // board. A controlled rejection at the boundary is what `reveal()` promises; an exception at the
    // payoff is the opposite of it.
    playedOn: isoDate(raw.played_on, "reveal.played_on"),
    // ⚠️⚠️ **Checked for shape, not merely for being a string.** It becomes a URL the player is invited
    // to follow at the one moment they have finished, so a malformed id is a 404 handed over as the
    // payoff. `text()` would accept `"yesterday"` exactly as `playedOn` used to — the defect one line
    // up, which reached `renderReveal` and threw on the success path.
    //
    // The shape is Retrosheet's: three characters for the **home** club, `YYYYMMDD`, and a trailing
    // `0`, `1` or `2`. The digit is the whole reason this field exists.
    gameId: retrosheetId(raw.game_id, "reveal.game_id"),
    // ⚠️ **Validated even though nothing reads it.** (v36-P3-25) `raw.card ?? ""` accepted an object,
    // an array, anything — and this function's own header tells the story of `raw.reveal` one field
    // up, where a pass-through incubated until something rendered `undefined` as a heading. A field
    // with no consumer is exactly where that waits: there is no test to go red first.
    card: text(raw.card ?? "", "reveal.card"),
    boxscore: {
      // ⚠️ **The half the board also carries is counted against the board.** `offense.batting` is
      // the batting grid with runs batted in added, and `defense.pitching` is the pitching grid; the
      // forge refuses a package where they disagree, and the client counts the rows rather than
      // assuming the forge ran. The other half — `offense.pitching`, `defense.batting` — is on no
      // board, so `null` here means *no row count to check against* rather than *do not check*.
      offense: printedSide(raw.boxscore?.offense, "reveal.boxscore.offense", batters, null),
      defense: printedSide(raw.boxscore?.defense, "reveal.boxscore.defense", null, pitchers),
    },
  };
}

/** One club of the printed sheet: who it is, who batted, who pitched. */
function printedSide(raw, where, batters, pitchers) {
  if (typeof raw !== "object" || raw === null || Array.isArray(raw)) {
    fail(`${where} is ${JSON.stringify(raw)}, expected an object`);
  }
  // ⚠️ **A blank name is refused, never replaced by the code.** Falling back to `SLA` would put the
  // abbreviation back on the one screen schema 5 exists to take it off, and it would do it silently.
  return {
    code: nonEmpty(raw.code, `${where}.code`),
    city: nonEmpty(raw.city, `${where}.city`),
    nickname: nonEmpty(raw.nickname, `${where}.nickname`),
    batting: printedRows(raw.batting, `${where}.batting`, PRINTED_BATTING, "position", batters),
    pitching: printedRows(raw.pitching, `${where}.pitching`, PRINTED_PITCHING, "role", pitchers),
  };
}

function printedRows(raw, where, columns, labelField, expected) {
  if (!Array.isArray(raw)) fail(`${where} is ${JSON.stringify(raw)}, expected a list of rows`);
  if (expected !== null && raw.length !== expected) {
    fail(`${where} has ${raw.length} rows and the board has ${expected}`);
  }
  if (raw.length === 0) fail(`${where} is empty; a printed boxscore has rows`);
  return raw.map((row, index) => {
    const at = `${where}[${index}]`;
    if (typeof row !== "object" || row === null) fail(`${at} is ${JSON.stringify(row)}, expected an object`);
    const line = { name: text(row.name, `${at}.name`), label: text(row[labelField], `${at}.${labelField}`) };
    for (const column of columns) {
      if (!isWholeNumber(row[column])) {
        fail(`${at}.${column} is ${JSON.stringify(row[column])}, expected a whole number`);
      }
      line[column] = row[column];
    }
    return line;
  });
}

const text = (value, where) => {
  if (typeof value !== "string") fail(`${where} is ${JSON.stringify(value)}, expected a string`);
  return value;
};

const nonEmpty = (value, where) => {
  const found = text(value, where);
  if (!found.trim()) fail(`${where} is blank; a printed boxscore has to name the club`);
  return found;
};
