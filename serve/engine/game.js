/**
 * Puzzle state and the event record. **No DOM, no layout, no device.**
 *
 * This is the half of the engine a test can drive with a JSON file and nothing else — which is the
 * test `docs/serve-brief.md` §9 states for whether something belongs here at all. If a function in this
 * file needs a screen, it is in the wrong file.
 *
 * ⚠️ **You can never lose** (§8). Nothing here ends a game, limits attempts, or runs a clock down. A
 * wrong entry is recorded and left on the board; whether the player is *told* it is wrong is a product
 * decision that belongs to the layer, not to the core.
 *
 * ⚠️ **Store events, not state** (C7, irreversible). The record accumulates what happened — how long,
 * how many hints, how many first-wrong entries — because aggregate state loses history that cannot be
 * reconstructed afterwards. Persistence belongs to the shell; the engine hands over a plain object.
 */

import { createClock } from "./clock.js";
import {
  BATTING_COLUMNS,
  FOOTNOTE_COLUMNS,
  PITCHING_COLUMNS,
  battingCell,
  battingTotalCell,
  footnoteCell,
  footnoteTotalCell,
  pitchingCell,
  pitchingTotalCell,
} from "./columns.js";

/**
 * Every cell on the board, in the order the board reads, with where it came from.
 *
 * The layer walks this to draw; it never derives geometry from the package itself. One description of
 * what a board is, in one place.
 */
export function describeCells(puzzle) {
  const cells = [];
  const add = (name, section, row, column, given, answer) =>
    cells.push({ name, section, row, column, given, answer });

  const walk = (grid, answers, columns, section, nameOf) => {
    grid.forEach((row, index) =>
      row.forEach((value, position) => {
        const column = columns[position];
        add(nameOf(index, column), section, index, column, value, answers[index][position]);
      }),
    );
  };

  walk(puzzle.puzzle.batting, puzzle.solution.batting, BATTING_COLUMNS, "batting", battingCell);
  walk(puzzle.puzzle.footnotes, puzzle.solution.footnotes, FOOTNOTE_COLUMNS, "footnotes", footnoteCell);
  walk(puzzle.puzzle.pitching, puzzle.solution.pitching, PITCHING_COLUMNS, "pitching", pitchingCell);

  const walkTotals = (row, answers, columns, section, nameOf) =>
    row.forEach((value, position) =>
      add(nameOf(columns[position]), section, null, columns[position], value, answers[position]),
    );

  walkTotals(puzzle.puzzle.battingTotals, puzzle.solution.battingTotals, BATTING_COLUMNS, "batting_totals", battingTotalCell);
  walkTotals(puzzle.puzzle.footnoteTotals, puzzle.solution.footnoteTotals, FOOTNOTE_COLUMNS, "footnote_totals", footnoteTotalCell);
  walkTotals(puzzle.puzzle.pitchingTotals, puzzle.solution.pitchingTotals, PITCHING_COLUMNS, "pitching_totals", pitchingTotalCell);

  return cells;
}

/**
 * Is this a session this game could have written?
 *
 * ⚠️ **Local storage is untrusted input.** It survives across versions of this code, it is editable by
 * hand, and a tab killed mid-write can leave half a value. `restore()` used to assume the shape and
 * `{"entries":{},"hinted":7}` threw `TypeError` from `for...of` over a number — before `draw()`, so the
 * shell cleared the board and rethrew, and **the player got no board at all until they cleared site
 * data.** That is worse than losing a session: the store exists to be optional, and this made it a boot
 * dependency.
 *
 * ⚠️ **And the two shapes that did not throw were worse.** `entries: "nope"` restored quietly, because
 * `Object.entries` on a string yields index pairs that match no cell. `{"batting[0].hits": "five"}`
 * installed the *string* as a cell's value — past the whole-number rule `enter()` enforces, into a board
 * that would then draw it. A silent poisoning is harder to notice than a crash and lasts longer.
 *
 * The rule lives here rather than in the store because it is this type's shape. A key-value store should
 * not know what a session looks like, and if it did there would be two definitions of one thing.
 */
export function isSession(saved) {
  if (saved === null || typeof saved !== "object" || Array.isArray(saved)) return false;

  const { entries, hinted, firstWrong, elapsed, finishedAt } = saved;
  if (entries !== undefined) {
    if (entries === null || typeof entries !== "object" || Array.isArray(entries)) return false;
    // The same rule `enter()` applies. A cell holds a whole number or it holds nothing.
    for (const value of Object.values(entries)) {
      if (!Number.isInteger(value) || typeof value === "boolean" || value < 0) return false;
    }
  }
  for (const names of [hinted, firstWrong]) {
    if (names === undefined) continue;
    if (!Array.isArray(names) || names.some((name) => typeof name !== "string")) return false;
  }
  if (elapsed !== undefined && (!Number.isFinite(elapsed) || elapsed < 0)) return false;
  // ⚠️ `null` is a real value here — a board still being played — so absence and null are both
  // accepted and anything else is refused. A negative or non-finite duration is a corrupted session,
  // and §23 says a refused session gives the player today's board rather than an error.
  if (finishedAt !== undefined && finishedAt !== null && (!Number.isFinite(finishedAt) || finishedAt < 0)) {
    return false;
  }
  return true;
}

/**
 * A playable game over a validated puzzle.
 *
 * ⚠️ **The clock is injected and it is an accumulated duration, not a start time.** This computed
 * `now() - startedAt`, which is wall-clock from construction — so a player who paused for lunch came
 * back to a duration including lunch. `docs/serve-flow.md` §5 requires the opposite: only time with the
 * board open counts, because the number is shared and a number including lunch means nothing.
 *
 * The engine still has no hidden dependency on when it runs (C4, one field over), and it knows nothing
 * about *why* the clock stopped: page visibility and the inactivity timeout are the shell's business.
 */
export const HINTS_PER_GAME = 3;
/**
 * How many cells a player may be given. **A game rule, so it lives with the game and not with the
 * shell** — a limit a screen enforces is a limit the next screen has to remember.
 *
 * ⚠️⚠️ **Hints were rejected outright and the decision is reversed.** The original reasoning was §22's
 * guarantee: every board ships solvable without guessing, so a hint is a crutch for a board that
 * should not need one. That reasoning is still true and it was answering the wrong question — it never
 * considered **comparison**, which is what the number is for. The crossword's answer settles it: a hint
 * does not corrupt a shared result if it is shared *alongside* the time. One minute with three hints
 * and one minute with none are two different results and every reader takes them as two.
 *
 * ⚠️ **Three, and the count is not measured — it is a shape.** Few enough that spending one is a
 * decision, enough that being stuck twice does not end the game. It is `PROVISIONAL` in the sense
 * `docs/python-conventions.md` means: chosen, not derived, and the fifty-board hand-solve is what will
 * say whether it is right.
 */

export function createGame(puzzle, clock = createClock()) {
  const cells = new Map(describeCells(puzzle).map((cell) => [cell.name, cell]));
  const entries = new Map();
  /** Cells whose first entry was wrong. A set, not a counter: entering the same wrong value twice is
   * one mistake made once, and a counter would make hesitation look like ignorance. */
  const firstWrong = new Set();
  const hinted = new Set();
  /** Frozen at the moment the board was finished, so a record taken later reports the same duration. */
  let finishedAt = null;

  const require = (name) => cells.get(name) ?? raise(name);
  const raise = (name) => {
    throw new Error(`no such cell: ${name}`);
  };

  const valueOf = (name) => {
    const cell = require(name);
    return cell.given !== null ? cell.given : (entries.get(name) ?? null);
  };

  return {
    puzzle,

    /** Every cell, for a layer that needs to draw the whole board. */
    cells: () => [...cells.values()],

    /** The blanks — what the player is actually being asked for. */
    blanks: () => [...cells.values()].filter((cell) => cell.given === null).map((cell) => cell.name),

    /**
     * The blanks in the order a player moves through them: **each grid, then its totals row.**
     *
     * ⚠️ **This is not the same as the order they are drawn in**, and that is deliberate. Two orders
     * answer two questions, and the reason they differ is written here rather than discovered later
     * when they disagree.
     *
     * ⚠️ **The order lives in the core, not in a layer.** Three presentation layers each deciding what
     * comes next is three answers to one product question, and they would drift on the first change.
     * The phone has no keyboard traversal yet — that arrives with desktop, where a tab key exists — so
     * today this is a contract with a test and no consumer, which is the cheap half of building it now.
     *
     * ⚠️ **There was a third rank here, putting the footnotes last.** The footnote line is given now,
     * so no footnote cell is ever blank and that branch could not fire — a rank that ranks nothing,
     * indistinguishable from one that is broken. Deleted rather than left as a comment, because a
     * mechanism kept past its problem becomes a constraint on everything added after it. What keeps it
     * honest is the test asserting the traversal reaches no footnote at all, which fails loudly if the
     * cells are ever opened again rather than quietly interleaving them with the batting grid.
     */
    traversal() {
      const rank = (cell) => (cell.section.endsWith("_totals") ? 2 : 1);
      return [...cells.values()]
        .filter((cell) => cell.given === null)
        .map((cell, index) => ({ cell, index }))
        .sort((a, b) => rank(a.cell) - rank(b.cell) || a.index - b.index)
        .map(({ cell }) => cell.name);
    },

    isBlank: (name) => require(name).given === null,
    value: valueOf,

    /**
     * Put a value in a blank. Returns whether it matches the solution.
     *
     * ⚠️ Returning the verdict is not the same as showing it. The engine knows because it holds the
     * solution — it has to, since there is no backend in the play path (brief §8) — and the layer
     * decides what the player sees.
     */
    enter(name, value) {
      const cell = require(name);
      if (cell.given !== null) throw new Error(`${name} is given and cannot be entered`);
      if (value !== null && !(Number.isInteger(value) && value >= 0)) {
        throw new Error(`${name} entry ${JSON.stringify(value)} is not a whole number`);
      }
      if (value === null) entries.delete(name);
      else entries.set(name, value);
      // ⚠️⚠️ **A keystroke is not an attempt, and this recorded one as if it were.** The keypad appends
      // digits and calls `enter()` after each press, so a *correct* answer of 12 arrived as `1` and
      // then `12` — and the intermediate `1` was filed as a wrong entry before the player had finished
      // typing. Totals and pitcher outs are routinely two digits, so ordinary play corrupted the C7
      // error record at collection time, where it can never be reconstructed. v30-P2-01.
      //
      // Errors are recorded by `check()` instead: the one moment the player asserts the board is done
      // is the one moment an entry is an answer rather than a keystroke. A player who types a wrong
      // value and fixes it before checking made no mistake the game ever saw, which is the honest
      // reading — nothing told them, so they deduced it.
      return value !== null && value === cell.answer;
    },

    clear(name) {
      const cell = require(name);
      if (cell.given !== null) throw new Error(`${name} is given and cannot be cleared`);
      entries.delete(name);
    },

    /**
     * Fill a blank with its answer and record that it was given away, never counted as a mistake.
     *
     * ⚠️ **The selected cell, never a random one** — that is the shell's business, but it is the reason
     * this takes a name. A random cell is a lottery: it may hand over the one the player was about to
     * get, or the one that unlocks the board, and the player controls neither. Revealing the cell they
     * chose rewards knowing *where you are stuck*, which is part of solving.
     *
     * ⚠️ **The limit is enforced here and refuses rather than returning quietly.** The keypad's hint key
     * goes dead at zero, and a control being disabled is not a rule — the next interface would have to
     * remember it too.
     */
    hint(name) {
      const cell = require(name);
      if (cell.given !== null) throw new Error(`${name} is given and needs no hint`);
      if (hinted.size >= HINTS_PER_GAME && !hinted.has(name)) {
        throw new Error(`no hints left: ${HINTS_PER_GAME} is the whole allowance`);
      }
      entries.set(name, cell.answer);
      hinted.add(name);
      return cell.answer;
    },

    /** How many are left. The shell shows it on the key, because a spend the player cannot count is a
     * spend they will not make. */
    hintsLeft: () => Math.max(0, HINTS_PER_GAME - hinted.size),

    /** Whether this cell was given away rather than deduced. Read by `paint()`; see the colour note. */
    isHinted: (name) => hinted.has(name),

    isCorrect: (name) => valueOf(name) === require(name).answer,

    /** Every blank filled with its answer. There is no other ending. */
    isSolved: () => [...cells.values()].every((cell) => valueOf(cell.name) === cell.answer),

    /**
     * What pressing *Check* means: the verdict, and the moment an entry counts as an answer.
     *
     * ⚠️⚠️ **The three states are all it ever returns, and that is a product rule rather than an
     * omission.** The board never says which cells are wrong or how many: marking makes probing beat
     * deducing, and a count is a binary search over the board. So this returns `incomplete`, `wrong`
     * or `solved` and there is deliberately no fourth carrying detail.
     *
     * ⚠️ **Recording lives here and phrasing lives in the shell.** The engine holds the record, so it
     * decides what a mistake *is*; `checkBoard` in `finish.js` decides what the player is told. The
     * rule used to be split the other way round and errors were counted per keystroke.
     */
    check() {
      const blanks = [...cells.values()].filter((cell) => cell.given === null);
      if (blanks.some((cell) => valueOf(cell.name) === null)) return { state: "incomplete" };
      // ⚠️ A set, not a counter: the same cell wrong across two checks is one mistake, and counting
      // twice would make hesitation look like ignorance.
      for (const cell of blanks) {
        if (valueOf(cell.name) !== cell.answer) firstWrong.add(cell.name);
      }
      return { state: this.isSolved() ? "solved" : "wrong" };
    },

    /** Whether this board has been finished. Restored with the session, so a reopen knows. */
    isFinished: () => finishedAt !== null,

    /**
     * Stop the clock and keep the duration. Calling it twice reports the first ending, not the second.
     *
     * ⚠️⚠️ **And the freeze survives a reload, which it did not.** `finishedAt` lived only in memory:
     * `snapshot()` saved entries, hints and elapsed time but not completion, so a solved board
     * reopened with `finishedAt === null`, the shell started its clock for a visible page, and the
     * next *Check* froze a larger number. Duration is the metric that gets compared and shared, so the
     * ordinary reopen — the path persistence exists for — quietly rewrote what the player earned.
     * v30-P1-03.
     */
    finish() {
      if (finishedAt === null) {
        clock.seal();
        finishedAt = clock.elapsed();
      }
      return this.record();
    },

    /**
     * The C7 event record. Present in full from day one even where a field is not yet computed,
     * because storing aggregate state instead loses history that can never be reconstructed.
     */
    record() {
      return {
        puzzle_id: puzzle.id,
        duration_ms: finishedAt ?? clock.elapsed(),
        hints: hinted.size,
        errors: firstWrong.size,
        // ⚠️ Present and null on purpose. What a *player* used is not observable from entries alone —
        // the engine can see the board, not the reasoning — and inventing a value would put a number
        // in the record that nobody can defend. The seam exists; the measurement does not yet.
        highest_technique: null,
        solved: this.isSolved(),
      };
    },

    /** The clock this game counts on, for a shell that has to stop and start it. */
    clock,

    /** Enough to restore a session, and nothing else. The shell decides where it goes. */
    snapshot: () => ({
      entries: Object.fromEntries(entries),
      hinted: [...hinted],
      firstWrong: [...firstWrong],
      // ⚠️ **The frozen duration, not a flag.** A boolean would say the board was finished and leave
      // the shell to ask the clock how long it took — and the clock has kept running since. The
      // number is the thing that has to survive, so the number is what is stored; `null` is a board
      // still being played and is the only other value.
      finishedAt,
      // ⚠️ The duration travels with the entries because they are one session. Saved separately they
      // would be two writes that can disagree, and a board restored with somebody else's clock is a
      // shared time that is simply wrong.
      elapsed: clock.elapsed(),
    }),

    /**
     * Put a saved session back, or refuse it. **Returns whether anything was restored.**
     *
     * ⚠️ **Checked before anything is cleared.** This wiped the three maps and then repopulated them, so
     * a shape that threw part-way left the game *emptier than it found it* — the player's board gone and
     * no session to put back. Atomic now: a bad session leaves a game that is exactly as it was.
     *
     * ⚠️ **It refuses rather than throwing.** The store is optional by design (§23) and a caller must
     * never have to wrap a restore to keep the board alive.
     */
    restore(saved) {
      if (!isSession(saved)) return false;
      entries.clear();
      hinted.clear();
      firstWrong.clear();
      for (const [name, value] of Object.entries(saved.entries ?? {})) if (cells.has(name)) entries.set(name, value);
      // ⚠️ **Capped on the way in.** A session is player-writable storage; without this a hand-edited
      // one hands out unlimited answers and the record still reads as a legitimate result. §23 says a
      // refused session costs nothing, and a truncated hint list costs less than an uncapped one.
      for (const name of (saved.hinted ?? []).slice(0, HINTS_PER_GAME)) if (cells.has(name)) hinted.add(name);
      for (const name of saved.firstWrong ?? []) if (cells.has(name)) firstWrong.add(name);
      finishedAt = saved.finishedAt ?? null;
      // ⚠️ The duration is part of the session, not a separate thing the shell remembers to carry.
      // Left out, a reload gave the board back with the clock at zero.
      if (saved.elapsed !== undefined) clock.restore(saved.elapsed);
      // ⚠️⚠️ **Sealed, not held, and the difference is the finding.** The shell calls `followAttention`,
      // which starts the clock on a visible page and on every pointer press — so a *held* clock under a
      // restored finished board resumes on the first tap and the next *Check* freezes a larger number
      // than the player earned. Sealing is a fact about the clock rather than a promise every future
      // shell has to keep. v30-P1-03.
      if (finishedAt !== null) clock.seal();
      return true;
    },
  };
}
