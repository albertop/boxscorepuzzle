/**
 * The engine, driven against **the six real packages** rather than fixtures.
 *
 * ⚠️ A fixture is written by whoever writes the test, so it agrees with whatever the test already
 * believes. The design document has been wrong about the board five times and every one was found by
 * looking at something real. These load `serve/data/puzzles/`.
 */

import { BATTING_COLUMNS, FOOTNOTE_COLUMNS, PITCHING_COLUMNS, inningsFromDisplay, inningsToDisplay } from "../engine/columns.js";
import { createGame } from "../engine/game.js";
import { PackageError, readPackage } from "../engine/package.js";
import { CATALOGS, keys, text, useCatalog } from "../engine/strings.js";
import { assert, equal, suite, test, throws } from "./harness.js";

const MANIFEST = "../data/puzzles/manifest.json";

async function loadAll() {
  // ⚠️ `no-store`, for the reason the phone loader carries in full: the manifest is a pointer and a
  // stale pointer sends the tests at a retired generation, which reads as a schema failure in code
  // that is correct. That happened on the first regeneration.
  const manifest = await (await fetch(MANIFEST, { cache: "no-store" })).json();
  const generation = manifest.generation;
  const loaded = [];
  for (const id of manifest.puzzles) {
    const raw = await (await fetch(`../data/puzzles/${generation}/${id}.json`)).json();
    loaded.push({ id, raw });
  }
  return loaded;
}

const packages = await loadAll();

suite("The six real packages parse, and their shape is the contract", () => {
  test("there are six of them and each carries a distinct id", () => {
    assert(packages.length === 6, `manifest lists ${packages.length} puzzles`);
    equal(new Set(packages.map((p) => p.id)).size, 6, "two puzzles share an id");
  });

  for (const { id, raw } of packages) {
    test(`${id} parses and keeps its widths`, () => {
      const puzzle = readPackage(raw);
      equal(puzzle.id, id, "the file name and the puzzle_id disagree");
      for (const row of puzzle.puzzle.batting) equal(row.length, BATTING_COLUMNS.length, "batting width");
      for (const row of puzzle.puzzle.pitching) equal(row.length, PITCHING_COLUMNS.length, "pitching width");
      for (const row of puzzle.puzzle.footnotes) equal(row.length, FOOTNOTE_COLUMNS.length, "footnote width");
      equal(puzzle.labels.length, puzzle.puzzle.batting.length, "one label per batting row");
      equal(puzzle.slotReferences.length, puzzle.puzzle.batting.length, "one slot reference per batting row");
      equal(puzzle.pitcherLabels.length, puzzle.puzzle.pitching.length, "one label per pitching row");
    });
  }

  test("⚠️ the side that batted cannot be inferred from the line score alone", () => {
    // Why the field exists rather than being derived. A ragged line score determines it — the home
    // side leading after the top of the ninth never bats again — and a square one does not. If most of
    // the reference set is square, a client that inferred it would be guessing on most boards.
    const square = packages
      .map(({ raw }) => readPackage(raw))
      .filter((p) => p.puzzle.lineScore.offense_by_inning.length === p.puzzle.lineScore.defense_by_inning.length);
    assert(square.length > 0, "every reference package is ragged, so this reasoning needs rechecking");
    for (const p of square) assert(typeof p.offenseIsHome === "boolean", "a square board carries no side");
  });

  test("the roster caps §6 states are respected by every real package", () => {
    for (const { id, raw } of packages) {
      const puzzle = readPackage(raw);
      assert(puzzle.puzzle.batting.length <= 13, `${id} has ${puzzle.puzzle.batting.length} batters`);
      assert(puzzle.puzzle.pitching.length <= 4, `${id} has ${puzzle.puzzle.pitching.length} pitchers`);
    }
  });

  test("⚠️ the two half-innings can differ in length, and that is real baseball", () => {
    // The home side leading after the visitors bat in the ninth never bats again. Two of the six are
    // like this. A validator demanding equal lengths would reject a third of real games — this asserts
    // the reference set actually contains the case, so the tolerance is not being kept for a
    // possibility nobody has seen.
    const ragged = packages
      .map(({ raw }) => readPackage(raw).puzzle.lineScore)
      .filter((score) => score.offense_by_inning.length !== score.defense_by_inning.length);
    assert(ragged.length > 0, "no reference package exercises the ragged line score");
    for (const score of ragged) {
      assert(
        Math.abs(score.offense_by_inning.length - score.defense_by_inning.length) === 1,
        "the halves differ by more than one inning, which is not the case this tolerance is for",
      );
    }
  });

  test("⚠️ the pinned totals row contains blanks — it is an input surface, not a reference", () => {
    // The first thing the real packages forced that the design did not say. §6 pins the totals row
    // "because the totals are consulted constantly", which reads as a read-only anchor. Every one of
    // the six erases batting totals, and four of six erase a pitching total. So the pinned row needs
    // full touch targets and tapping it must not move the board underneath.
    let erasedTotals = 0;
    for (const { id, raw } of packages) {
      const board = readPackage(raw).puzzle;
      erasedTotals += board.battingTotals.filter((value) => value === null).length;
      erasedTotals += board.pitchingTotals.filter((value) => value === null).length;
      // What is genuinely never erased, and why: without these the row identity does not close and the
      // global identity cannot be expressed at all (§6).
      for (const value of board.footnoteTotals) assert(value !== null, `${id} erased a footnote total`);
      assert(board.leftOnBase !== null, `${id} erased LOB, which kills the global identity`);
    }
    assert(erasedTotals > 0, "no reference package erases a total, so the pinned row is read-only after all");
  });

  test("per-batter footnote cells are erasable, whatever the forge docstring says", () => {
    // ⚠️ `FOOTNOTE_COLUMNS` in `forge/src/boxscore_package/format.py` is documented as "given complete
    // and never erased (§6)". The real packages disagree with it, and §6 agrees with the packages.
    // Two places stating one rule differently — recorded in the backlog rather than fixed from here.
    const erased = packages
      .map(({ raw }) => readPackage(raw).puzzle.footnotes.flat().filter((value) => value === null).length)
      .reduce((a, b) => a + b, 0);
    assert(erased > 0, "no reference package erases a per-batter footnote cell");
  });
});

suite("A malformed package is refused at the boundary, naming the field", () => {
  const good = () => structuredClone(packages[0].raw);

  test("a short row is refused rather than read one column across", () => {
    const raw = good();
    raw.puzzle.batting[0] = raw.puzzle.batting[0].slice(0, 5);
    throws(() => readPackage(raw), "puzzle.batting\\[0\\] has 5 cells, expected 6");
  });

  test("a non-integer cell is refused, including a boolean", () => {
    const raw = good();
    raw.puzzle.batting[0][0] = true;
    throws(() => readPackage(raw), "expected a whole number or null");
  });

  test("a missing line score field is refused", () => {
    const raw = good();
    delete raw.puzzle.line_score.defense_hits;
    throws(() => readPackage(raw), "line_score.defense_hits");
  });

  test("an unreadable schema is refused, including the version this replaced", () => {
    const raw = good();
    // ⚠️ Schema 2 is refused rather than tolerated. A v2 package has no `offense_is_home`, and there is
    // no honest default: `true` and `false` are both claims about a real game, so a client that
    // defaulted would render a false statement rather than admit it does not know.
    raw.schema = 2;
    throws(() => readPackage(raw), "package schema 2");
    // JSON has no integer type, so `3.0` arrives as the number 3 and is legitimately schema 3. What
    // must not pass is a non-integer: 3.5 is not a version.
    const half = good();
    half.schema = 3.5;
    throws(() => readPackage(half), "package schema 3.5");
  });

  test("⚠️ a package that cannot say which side batted last is refused", () => {
    // The finding this schema exists for. The client had been labelling the offensive half `Away`
    // with nothing telling it so, and on the reference set that was wrong.
    for (const bad of [undefined, null, 0, 1, "true"]) {
      const raw = good();
      raw.offense_is_home = bad;
      throws(() => readPackage(raw), "offense_is_home", `${JSON.stringify(bad)} was accepted`);
    }
  });

  test("metadata that is not an object is refused (seam C3)", () => {
    const raw = good();
    raw.metadata = [1, 2, 3];
    throws(() => readPackage(raw), "metadata");
  });

  test("a solution of a different shape is refused", () => {
    const raw = good();
    raw.solution.batting = raw.solution.batting.slice(0, 3);
    throws(() => readPackage(raw), "rows and batting has");
  });

  test("the served identifier is opaque and never the Retrosheet game id", () => {
    for (const { id } of packages) assert(/^[0-9a-f]{16}$/.test(id), `${id} is not an opaque sixteen-hex id`);
  });
});

suite("The game: state, entries and the C7 record", () => {
  const puzzle = readPackage(packages[0].raw);

  test("every blank in the package is a blank in the game, and no given one is", () => {
    const game = createGame(puzzle);
    const blanks = game.blanks();
    // ⚠️ Counting the grids alone gets this wrong, which is how the pinned-totals finding surfaced:
    // the totals rows carry blanks too, and the player has to fill them.
    const board = puzzle.puzzle;
    const counted = [
      ...board.batting.flat(),
      ...board.footnotes.flat(),
      ...board.pitching.flat(),
      ...board.battingTotals,
      ...board.footnoteTotals,
      ...board.pitchingTotals,
    ];
    equal(blanks.length, counted.filter((value) => value === null).length, "blank count");
    for (const name of blanks) assert(game.value(name) === null, `${name} starts with a value`);
  });

  test("a given cell cannot be entered or cleared", () => {
    const game = createGame(puzzle);
    const given = game.cells().find((cell) => cell.given !== null).name;
    throws(() => game.enter(given, 1), "is given");
    throws(() => game.clear(given), "is given");
  });

  test("entering the answer everywhere solves it, and nothing else does", () => {
    const game = createGame(puzzle);
    assert(!game.isSolved(), "an unsolved board reported solved");
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    for (const name of game.blanks()) game.enter(name, answers.get(name));
    assert(game.isSolved(), "every answer entered and the board is not solved");
  });

  test("a wrong entry is recorded once and never punished", () => {
    const game = createGame(puzzle);
    const name = game.blanks()[0];
    const wrong = game.cells().find((cell) => cell.name === name).answer + 7;
    equal(game.enter(name, wrong), false, "a wrong entry reported correct");
    equal(game.enter(name, wrong), false, "still wrong");
    equal(game.record().errors, 1, "hesitation was counted as two mistakes");
    // §8: there is no fail state. The wrong value stays on the board and the game continues.
    equal(game.value(name), wrong, "the engine removed a wrong entry");
    assert(!game.record().solved, "solved with a wrong entry on the board");
  });

  test("a hint fills the answer and is not an error", () => {
    const game = createGame(puzzle);
    const name = game.blanks()[0];
    const answer = game.hint(name);
    equal(game.value(name), answer, "the hint did not land");
    equal(game.record().hints, 1);
    equal(game.record().errors, 0, "a hint was counted as a mistake");
  });

  test("the C7 record carries every field, including the ones not yet computed", () => {
    const game = createGame(puzzle, () => 1000);
    const record = game.record(4000);
    equal(Object.keys(record).sort(), ["duration_ms", "errors", "highest_technique", "hints", "puzzle_id", "solved"]);
    equal(record.duration_ms, 3000, "duration is not measured from the injected clock");
    equal(record.puzzle_id, puzzle.id);
  });

  test("a snapshot restores exactly what it saved and ignores cells that no longer exist", () => {
    const game = createGame(puzzle);
    const name = game.blanks()[0];
    game.enter(name, 3);
    const saved = { ...game.snapshot(), entries: { ...game.snapshot().entries, "batting[99].hits": 5 } };
    const fresh = createGame(puzzle);
    fresh.restore(saved);
    equal(fresh.value(name), 3, "the entry did not survive the round trip");
    equal(fresh.snapshot().entries["batting[99].hits"], undefined, "a stale cell was restored");
  });
});

suite("Innings are thirds, and the two directions are inverses", () => {
  test("outs render the way a printed boxscore writes them", () => {
    equal([0, 1, 2, 3, 19, 20].map(inningsToDisplay), ["0", "0.1", "0.2", "1", "6.1", "6.2"]);
  });

  test("every outs value the board can hold survives a round trip", () => {
    for (let outs = 0; outs <= 60; outs += 1) {
      equal(inningsFromDisplay(inningsToDisplay(outs)), outs, `outs ${outs}`);
    }
  });

  test("a fraction baseball does not write is refused", () => {
    for (const bad of ["6.3", "6.5", "6.", ".1", "six", ""]) {
      equal(inningsFromDisplay(bad), null, `${JSON.stringify(bad)} was accepted`);
    }
  });

  test("the real packages' pitching totals are whole innings", () => {
    // Three outs per inning times the innings pitched by the whole staff has to be a whole number of
    // outs; a staff total ending in a third means somebody's row is wrong.
    for (const { id, raw } of packages) {
      const outs = readPackage(raw).solution.pitchingTotals[0];
      equal(outs % 3, 0, `${id} staff pitched ${inningsToDisplay(outs)} innings`);
    }
  });
});

suite("C11: no user-facing string is in code", () => {
  test("every column has a heading and an unknown key throws", () => {
    for (const column of [...BATTING_COLUMNS, ...PITCHING_COLUMNS, ...FOOTNOTE_COLUMNS]) {
      assert(text(`column.${column}`).length > 0, `no heading for ${column}`);
    }
    // ⚠️ Stated as what it forbids: a catalog falling back to the key ships an incomplete translation
    // that renders as `board.totals` and nobody notices until a screenshot.
    throws(() => text("board.nothing_here"), "no string for");
  });

  test("a replacement catalog is complete or the swap is refused", () => {
    const before = keys();
    useCatalog({ ...CATALOGS.en });
    equal(keys().sort(), before.sort(), "the catalog lost keys on a swap");
    useCatalog(CATALOGS.en);
  });
});
