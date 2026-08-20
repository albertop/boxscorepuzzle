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
      const correct = value !== null && value === cell.answer;
      if (value !== null && !correct && !firstWrong.has(name)) firstWrong.add(name);
      return correct;
    },

    clear(name) {
      const cell = require(name);
      if (cell.given !== null) throw new Error(`${name} is given and cannot be cleared`);
      entries.delete(name);
    },

    /** Fill a blank with its answer and record that it was given away, never counted as a mistake. */
    hint(name) {
      const cell = require(name);
      if (cell.given !== null) throw new Error(`${name} is given and needs no hint`);
      entries.set(name, cell.answer);
      hinted.add(name);
      return cell.answer;
    },

    isCorrect: (name) => valueOf(name) === require(name).answer,

    /** Every blank filled with its answer. There is no other ending. */
    isSolved: () => [...cells.values()].every((cell) => valueOf(cell.name) === cell.answer),

    /** Stop the clock and keep the duration. Calling it twice reports the first ending, not the second. */
    finish() {
      if (finishedAt === null) {
        clock.hold();
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
      // ⚠️ The duration travels with the entries because they are one session. Saved separately they
      // would be two writes that can disagree, and a board restored with somebody else's clock is a
      // shared time that is simply wrong.
      elapsed: clock.elapsed(),
    }),

    restore(saved) {
      entries.clear();
      hinted.clear();
      firstWrong.clear();
      for (const [name, value] of Object.entries(saved.entries ?? {})) if (cells.has(name)) entries.set(name, value);
      for (const name of saved.hinted ?? []) if (cells.has(name)) hinted.add(name);
      for (const name of saved.firstWrong ?? []) if (cells.has(name)) firstWrong.add(name);
      // ⚠️ The duration is part of the session, not a separate thing the shell remembers to carry.
      // Left out, a reload gave the board back with the clock at zero.
      if (saved.elapsed !== undefined) clock.restore(saved.elapsed);
    },
  };
}
