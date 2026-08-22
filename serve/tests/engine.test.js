/**
 * The engine, driven against **the six real packages** rather than fixtures.
 *
 * ⚠️ A fixture is written by whoever writes the test, so it agrees with whatever the test already
 * believes. The design document has been wrong about the board five times and every one was found by
 * looking at something real. These load `serve/data/puzzles/`.
 */

import {
  BATTING_COLUMNS,
  FOOTNOTE_COLUMNS,
  PITCHING_COLUMNS,
  INNINGS,
  inningsFromDisplay,
  inningsToDisplay,
  sectionOf,
} from "../engine/columns.js";
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

// Loaded here rather than inside the suite: `suite()` takes a synchronous callback, and top-level await
// is what this module already uses for the packages themselves.
const vectors = await (await fetch("./package-vectors.json", { cache: "no-store" })).json();
const vectors_footnote = await (await fetch("./footnote-line-vectors.json", { cache: "no-store" })).json();

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
      // From the shared file, not spelled again. The pitcher cap moved from 4 to 6 and this line held
      // one of twenty-six copies of it; a forge test asserts the shared numbers still equal the
      // constants module, so the two cannot drift apart in silence.
      const { batters, pitchers } = vectors.caps;
      assert(puzzle.puzzle.batting.length <= batters, `${id} has ${puzzle.puzzle.batting.length} batters`);
      assert(puzzle.puzzle.pitching.length <= pitchers, `${id} has ${puzzle.puzzle.pitching.length} pitchers`);
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

  /** Fill every blank with its answer except the named one, which gets `wrong`. */
  const boardWith = (game, wrongAt, wrong) => {
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    for (const name of game.blanks()) game.enter(name, name === wrongAt ? wrong : answers.get(name));
  };

  test("⚠️⚠️ typing a correct two-digit answer is not a mistake", async () => {
    // **The keypad appends digits and calls `enter()` after each press**, so a correct answer of 12
    // arrives as `1` and then `12`. Recording on entry filed that intermediate `1` as a wrong answer
    // before the player had finished typing — and totals and pitcher outs are routinely two digits, so
    // ordinary play corrupted the C7 record at collection time. v30-P2-01.
    //
    // ⚠️ Driven through `applyKey`, which is the path the keypad actually takes. The old test called
    // `enter()` with an already-complete wrong value and could not see this.
    const { applyKey } = await import("../ui/phone/board.js");
    const game = createGame(puzzle);
    // ⚠️ **Not an innings cell.** `applyKey` reads a digit on `.outs` as a whole *inning*, so typing
    // `2` then `1` at an answer of 21 outs means twenty-one innings and writes 63. That is the pad
    // working as designed — innings are entered whole-then-third — and it is a different path from the
    // one this test is about. Picking the cell without excluding it made the test fail on its own
    // fixture rather than on the code.
    const twoDigit = game
      .blanks()
      .filter((name) => !name.endsWith(".outs"))
      .find((name) => game.cells().find((cell) => cell.name === name).answer >= 10);
    assert(twoDigit, "no plain blank in the fixture needs two digits; this test cannot fire");
    const answer = game.cells().find((cell) => cell.name === twoDigit).answer;

    for (const digit of String(answer)) applyKey(game, twoDigit, { digit: Number(digit) });

    equal(game.value(twoDigit), answer, "the digits did not assemble");
    equal(game.check().state, "incomplete", "the rest of the board is not filled, so this is not a verdict");
    equal(game.record().errors, 0, "typing a correct answer one digit at a time was counted as a mistake");
  });

  test("a wrong entry is recorded once, at the check, and never punished", () => {
    // ⚠️ **Check is where an entry becomes an answer.** A set, not a counter: the same cell wrong at
    // two checks is one mistake made once, and counting twice makes hesitation look like ignorance.
    const game = createGame(puzzle);
    const name = game.blanks()[0];
    const wrong = game.cells().find((cell) => cell.name === name).answer + 7;
    boardWith(game, name, wrong);

    equal(game.record().errors, 0, "an entry was counted before the player asked");
    equal(game.check().state, "wrong");
    equal(game.check().state, "wrong", "a second check");
    equal(game.record().errors, 1, "hesitation was counted as two mistakes");
    // §8: there is no fail state. The wrong value stays on the board and the game continues.
    equal(game.value(name), wrong, "the engine removed a wrong entry");
    assert(!game.record().solved, "solved with a wrong entry on the board");
  });

  test("a wrong value corrected before the check is not a mistake", () => {
    // ⚠️ The decision this boundary makes, stated as a test so it is a decision rather than a
    // side effect. Nothing told the player they were wrong — the board never marks a cell — so a value
    // they replaced before asking is one they worked out themselves.
    const game = createGame(puzzle);
    const name = game.blanks()[0];
    const answer = game.cells().find((cell) => cell.name === name).answer;
    boardWith(game, name, answer + 7);
    game.enter(name, answer);

    equal(game.check().state, "solved");
    equal(game.record().errors, 0, "a self-corrected value was counted as a mistake");
  });

  test("an incomplete board records nothing, because it is not an answer", () => {
    const game = createGame(puzzle);
    const name = game.blanks()[0];
    game.enter(name, game.cells().find((cell) => cell.name === name).answer + 7);

    equal(game.check().state, "incomplete");
    equal(game.record().errors, 0, "a half-filled board counted a mistake");
  });

  test("a hint fills the answer and is not an error", () => {
    const game = createGame(puzzle);
    const name = game.blanks()[0];
    const answer = game.hint(name);
    equal(game.value(name), answer, "the hint did not land");
    equal(game.record().hints, 1);
    equal(game.record().errors, 0, "a hint was counted as a mistake");
  });

  test("the C7 record carries every field, including the ones not yet computed", async () => {
    // ⚠️ The second argument is a **clock**, not a `now`. It used to be `now`, and the duration was
    // `now() - startedAt` — wall-clock from construction, which counted every minute the tab sat
    // unwatched. `docs/serve-flow.md` §5 wants only time at the board.
    const { createClock } = await import("../engine/clock.js");
    const t = { value: 1000 };
    const clock = createClock({ now: () => t.value });
    const game = createGame(puzzle, clock);
    clock.run();
    t.value = 4000;

    const record = game.record();
    // ⚠️ **The exact field set, and `assisted` earned its place by breaking this test.** C7 is
    // irreversible: a field that appears only sometimes is a field consumers forget to check for, and
    // a board a development affordance filled in would otherwise be recorded as a perfect instant
    // solve. Always present, `false` on every real game.
    equal(
      Object.keys(record).sort(),
      ["assisted", "duration_ms", "errors", "highest_technique", "hints", "puzzle_id", "solved"],
    );
    equal(record.assisted, false, "an ordinary game reported itself as assisted");
    equal(record.duration_ms, 3000, "duration is not measured from the injected clock");
    equal(record.puzzle_id, puzzle.id);
  });

  test("⚠️ the traversal reaches no footnote cell, because none is blank", () => {
    // This used to assert the opposite ordering rule — footnotes last — and it was the check that
    // reported the reversal honestly, by refusing to pass on a board with no footnote blank. The rank
    // it guarded is gone; what remains worth forbidding is the cells coming back without anyone
    // deciding to bring them back, which would now interleave them with the batting grid in silence.
    const game = createGame(puzzle);
    const order = game.traversal();

    equal(new Set(order), new Set(game.blanks()), "the traversal lost or invented a blank");
    equal(order.filter((name) => name.startsWith("footnote")), [], "a footnote cell is blank again");
  });

  test("the totals rows come after their grid", () => {
    // A traversal that put everything in one bucket would satisfy the test above, which now only ever
    // counts an empty set. This is the one asserting the order is still an order.
    const game = createGame(puzzle);
    const order = game.traversal();
    const rank = (name) => (name.includes("_totals.") ? 2 : 1);

    const ranks = order.map(rank);
    equal(ranks, [...ranks].sort((a, b) => a - b), "the two blocks are interleaved");
    assert(new Set(ranks).size === 2, `only ${new Set(ranks).size} of the two blocks are present`);
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

suite("Innings are thirds, one conversion writes two notations, and the directions are inverses", () => {
  test("the board's notation and the printed one differ only where a whole inning is", () => {
    const outs = [0, 1, 2, 3, 12, 19, 20, 27];

    equal(
      outs.map((one) => inningsToDisplay(one, INNINGS.BOARD)),
      ["0", "0.1", "0.2", "1", "4", "6.1", "6.2", "9"],
      "the board's notation changed",
    );
    // ⚠️ The reveal is a printed boxscore and a newspaper writes `9.0`. Both notations are correct
    // about their own surface; what was wrong was two formulas producing them.
    equal(
      outs.map((one) => inningsToDisplay(one, INNINGS.PRINTED)),
      ["0.0", "0.1", "0.2", "1.0", "4.0", "6.1", "6.2", "9.0"],
      "the printed notation changed",
    );
  });

  test("⚠️ the notation is required, because inheriting one is how the copies drifted", () => {
    // The function had no parameter, so every caller got the board's answer and the reveal grew a
    // hand-written copy to get the other one. That is how `4` and `9.0` came to be in one product.
    for (const missing of [undefined, null, "", true, "Printed"]) {
      throws(() => inningsToDisplay(12, missing), "notation", `${JSON.stringify(missing)} was accepted`);
    }
  });

  test("every outs value the board can hold survives a round trip, in both notations", () => {
    for (let outs = 0; outs <= 60; outs += 1) {
      for (const notation of [INNINGS.BOARD, INNINGS.PRINTED]) {
        equal(inningsFromDisplay(inningsToDisplay(outs, notation)), outs, `outs ${outs} as ${notation}`);
      }
    }
  });

  test("⚠️ the parser accepts the other side's output", () => {
    // It refused `.0` — the exact string the format's own Python reference implementation emits, in a
    // module claiming to be the one place that converts. A notation choice must not become a data
    // question.
    equal(inningsFromDisplay("4.0"), 12, "the printed form was rejected");
    equal(inningsFromDisplay("4"), 12, "the board's form was rejected");
    equal(inningsFromDisplay("0.0"), 0, "zero printed was rejected");
  });

  test("a fraction baseball does not write is refused", () => {
    for (const bad of ["6.3", "6.5", "6.", ".1", "six", ""]) {
      equal(inningsFromDisplay(bad), null, `${JSON.stringify(bad)} was accepted`);
    }
  });

  test("⚠️⚠️ a staff's outs are bounded by the innings, not required to divide by three", () => {
    // **This asserted `outs % 3 === 0` over the reference packages and the rule is false.** When the
    // offense is the home club and wins on a walkoff, the defending staff records 0-2 outs in the
    // final inning: 25 or 26 outs, `8.1` IP. Ordinary baseball, and the forge supports it — the
    // certifier bounds staff outs by `3*(innings-1) <= outs <= 3*innings` *because* the last
    // half-inning is not always completed, and nothing in the pool filter excludes walkoffs.
    //
    // It passed only because none of these six happens to be one. The first regenerated set that
    // includes a walkoff would have failed CI **on correct data**, and sent the reader hunting for a
    // defect that does not exist. v36-P2-16.
    for (const { id, raw } of packages) {
      const puzzle = readPackage(raw);
      const outs = puzzle.solution.pitchingTotals[0];
      // The innings the DEFENCE batted, which is what the offence's staff had to record outs for --
      // and the same quantity `check_independent_correspondence` bounds in the certifier.
      const innings = puzzle.puzzle.lineScore.defense_by_inning.length;

      // >= at the bottom, not >. A home side that wins without batting in the ninth leaves the
      // visiting staff on exactly 3*(innings-1): 24 outs in a 9-inning game, which is the very first
      // reference package. The first version of this assertion said `>` and failed on it -- the same
      // off-by-one, in the test written to replace an assertion that stated a false rule.
      assert(
        outs >= 3 * (innings - 1) && outs <= 3 * innings,
        `${id}: staff pitched ${inningsToDisplay(outs, INNINGS.PRINTED)} across ${innings} innings batted`,
      );
    }
  });
});

suite("The shared conformance vectors — the same file the Python reader runs", () => {
  /**
   * ⚠️ **They exist because the two readers enforced different contracts while both claiming v3.**
   * Python defaulted labels it never counted; this reader accepted a null footnote total it then
   * rendered nowhere, and slot references whose grammar and uniqueness it never checked.
   *
   * **Shared data, not shared code**: forge/ and serve/ import nothing from each other. A vector both
   * sides accept, or both reject, proves nothing by itself — what the file forbids is the two
   * disagreeing, so a change made to one reader and not the other turns one of them red.
   */
  const apply = (document, path, value) => {
    const parts = [];
    for (const chunk of path.split(".")) {
      const [name, ...rest] = chunk.split("[");
      parts.push(name, ...rest.map((index) => Number(index.replace("]", ""))));
    }
    let target = document;
    for (const part of parts.slice(0, -1)) target = target[part];
    const last = parts.at(-1);
    // `null` in a vector means *absent*, not a JSON null: absence and an explicit null are different
    // documents and both readers have to answer both.
    if (value === null && typeof last === "string") delete target[last];
    else target[last] = value;
  };

  // Whatever is published: the vectors are about the schema, not about a particular board, and an
  // id pinned here broke every one of them the first time a regeneration renamed it.
  const reference = packages[0];

  test("there is a published package for the vectors to mutate", () => {
    assert(reference !== undefined, "the manifest lists no packages");
  });

  for (const vector of vectors.vectors) {
    test(`${vector.expect}: ${vector.name}`, () => {
      const document = structuredClone(reference.raw);
      for (const [path, value] of vector.mutate) apply(document, path, value);
      if (vector.expect === "accept") {
        readPackage(document);
        return;
      }
      // ⚠️⚠️ **The error's TYPE, not a pattern over its words.** (v36-P3-28) With no pattern at all
      // `throws` passes on any exception, so a refactor making `readPackage` die with a `TypeError`
      // three layers in would keep every reject vector green — and *a controlled rejection naming
      // the field, never an uncontrolled TypeError* is the exact distinction these vectors exist for.
      //
      // ⚠️ A first attempt matched a list of field names, which is **a second copy of the schema**
      // living in the test: it went red on `offense_is_home` because that list was already out of
      // date on the day it was written. The type is the contract; the wording is not.
      const error = throws(() => readPackage(document), undefined, `accepted: ${vector.because}`);
      assert(
        error instanceof PackageError,
        `${vector.because}: refused with ${error.constructor.name} rather than a PackageError — `
          + `an uncontrolled throw is not a controlled rejection: ${error.message}`,
      );
    });
  }

  test("the vectors exercise both answers", () => {
    // A file of nothing but rejections would pass a reader that refuses everything.
    const answers = new Set(vectors.vectors.map((v) => v.expect));
    equal([...answers].sort(), ["accept", "reject"], "the vectors only ever expect one answer");
  });
});

suite("A cell's block, because a column name alone does not identify a column", () => {
  test("⚠️ `hits` in batting and `hits` in pitching are different columns", () => {
    // The defect this exists for: selecting a batting cell tinted the pitching grid's column, because
    // both are called `hits`. They share a word and no equation — the offence's hits and what the
    // opposing staff allowed are related by the cross-team identity, not by being one column.
    equal(sectionOf("batting[3].hits"), "batting");
    equal(sectionOf("pitching[0].hits"), "pitching");
    assert(sectionOf("batting[3].hits") !== sectionOf("pitching[0].hits"), "the two grids read as one");
  });

  test("a totals row belongs to its own grid, where its column sum closes", () => {
    equal(sectionOf("batting_totals.hits"), "batting");
    equal(sectionOf("pitching_totals.hits"), "pitching");
    equal(sectionOf("footnote_totals.hit_by_pitch"), "footnote");
  });

  test("every cell the engine describes resolves to a block", () => {
    // Derived from the engine rather than from a list here, so a section added tomorrow is covered.
    const game = createGame(readPackage(packages[0].raw));
    const sections = new Set(game.cells().map((cell) => sectionOf(cell.name)));

    assert(sections.size >= 3, `only ${sections.size} blocks: ${[...sections]}`);
    for (const name of game.cells().map((c) => c.name)) {
      assert(sectionOf(name).length > 0 && !sectionOf(name).includes("["), `${name} resolved to ${sectionOf(name)}`);
    }
  });
});

suite("The footnote line is given, and says so", () => {
  test("⚠️ no footnote cell is erasable in any reference package", () => {
    // The decision, asserted at the level the client meets it. The cells were opened on a measurement
    // that was counting the solver deducing zeros, and closed on the pool run that reproduced the old
    // baseline exactly. A package carrying a footnote blank would now be a generator that regressed.
    for (const { id, raw } of packages) {
      const board = readPackage(raw).puzzle;
      const blanks = board.footnotes.flat().filter((value) => value === null).length;
      assert(blanks === 0, `${id} erases ${blanks} footnote cells; that decision was reversed`);
    }
  });

  test("a term that did not happen is not printed, and a live one is marked", async () => {
    // §6: nine boards in ten carry nothing here and players learn to stop looking, so the prominence is
    // the mechanism. Both halves asserted — an empty term absent, a live term marked.
    const { renderFootnotes } = await import("../ui/phone/board.js");
    // Found by asking, not named: an id pinned here survived one regeneration by luck while the
    // vectors' pinned id did not, and the requirement is "a board with a live term", not this board.
    const withLiveTerm = packages
      .map(({ raw }) => readPackage(raw))
      .find((p) => p.puzzle.footnoteTotals.some((total) => total > 0));
    assert(withLiveTerm !== undefined, "no reference package has a live footnote term, so this proves nothing");
    const puzzle = withLiveTerm;
    const game = createGame(puzzle);

    const line = renderFootnotes(puzzle, game);
    const terms = [...line.querySelectorAll(".term")].filter((n) => !n.classList.contains("lob"));

    assert(terms.length > 0, "the chosen board printed no term at all, so this test proves nothing");
    for (const node of terms) {
      // ⚠️ **Read from the carriers, because the total left the label.** This summed nothing and
      // asserted `Number("") > 0` after the format changed — it failed loudly, which is the only reason
      // it is a corrected test rather than a silent one. The label is now `SH: ` and the numbers live
      // beside the slots, so the term's total is what its carriers add up to.
      const counts = node.querySelector(".who").textContent.split(", ").map((c) => Number(c.split(" ")[0]));
      const total = counts.reduce((sum, n) => sum + n, 0);
      assert(counts.every((n) => n > 0), `a carrier with count ${counts} was printed`);
      assert(total > 0, `a term with total ${total} was printed`);
      assert(node.classList.contains("live"), "a printed term is not marked live");
    }
  });

  test("the line carries no editable cell at all", async () => {
    // Deleted rather than disabled: a drawing kept for a case that no longer exists is a mechanism kept
    // past its problem, and this is the check that says it is actually gone.
    const { renderFootnotes } = await import("../ui/phone/board.js");
    const puzzle = readPackage(packages[0].raw);

    const line = renderFootnotes(puzzle, createGame(puzzle));

    equal(line.querySelectorAll(".cell").length, 0, "the footnote line still draws cells");
    equal(line.querySelectorAll("[data-cell]").length, 0, "the footnote line still names board cells");
  });
});

suite("⚠️ Every blank the game asks for can be reached on the board", () => {
  test("no accepted package holds a blank with no editable element to fill it", async () => {
    // ⚠️ **The seam three layers were disagreeing across, stated once.** The reader said a null
    // per-batter footnote cell was valid, `createGame` counted it among the blanks the player owes, and
    // the footnote line renders as read-only text with no editable element in it. Reproduced on the
    // retained generation before this was written: 33 blanks, 14 of them footnotes, 0 editable elements
    // in the line. Every visible blank fillable and the board never completes.
    //
    // ⚠️ **Written as the rule, not as the instance.** "Reject a footnote blank" is already a
    // conformance vector. This is the property that vector protects, and it fails for any future cell
    // the engine counts and no interface draws — which is the shape the defect will take next time.
    const { renderSection, renderFootnotes, columnsFor, totalNameFor } = await import("../ui/phone/board.js");
    const { battingCell, pitchingCell } = await import("../engine/columns.js");

    for (const { id, raw } of packages) {
      const puzzle = readPackage(raw);
      const game = createGame(puzzle);
      const drawn = new Set();
      const sections = [
        { columns: columnsFor.batting, rows: puzzle.puzzle.batting, labels: puzzle.labels,
          slots: puzzle.slotReferences, cellName: battingCell, totalName: totalNameFor.batting },
        { columns: columnsFor.pitching, rows: puzzle.puzzle.pitching, labels: puzzle.pitcherLabels,
          slots: null, cellName: pitchingCell, totalName: totalNameFor.pitching },
      ];
      for (const section of sections) {
        const node = renderSection({ title: "t", ...section, game, onSelect: () => {} });
        for (const el of node.querySelectorAll("[data-cell]")) drawn.add(el.dataset.cell);
      }
      for (const el of renderFootnotes(puzzle, game).querySelectorAll("[data-cell]")) drawn.add(el.dataset.cell);

      const blanks = game.blanks();
      assert(blanks.length > 0, `${id} has no blanks at all, so this test proves nothing about it`);
      const unreachable = blanks.filter((name) => !drawn.has(name));
      equal(unreachable, [], `${id} asks for ${unreachable.length} blanks the board cannot draw`);
    }
  });
});

suite("⚠️ The footnote line, against the strings the PDF renderer also runs", () => {
  // ⚠️ **The two renderers had drifted in three ways at once** and reading either page alone showed
  // none of them: the PDF printed no count and no `#` and put LOB last, while this one printed the term
  // *total* then `#`-prefixed slots and put LOB first. A board with SH total 2 across slots 2 and 9b
  // came out `SH: 2, 9b` from one and `SH: 2 #2, #9b` from the other.
  //
  // §33 forbids forge/ and serve/ sharing a function, so they share this file. What it forbids is the
  // two disagreeing.
  //
  // ⚠️ **And the format change is a correctness fix.** `SH: 2` was a slot reference that reads as a
  // count, so a row carrying two of one term could not be expressed. 4,019 of 100,226 admissible
  // directions carry such a row — 4.01%, and 8.31% in the 1920s. Those boards cannot be solved, and
  // every total balances on them.
  const cases = vectors_footnote.cases;

  const fakePuzzle = (c) => ({
    slotReferences: c.slot_references,
    puzzle: {
      footnotes: c.footnotes,
      footnoteTotals: [0, 1, 2, 3].map((i) => c.footnotes.reduce((sum, row) => sum + row[i], 0)),
      leftOnBase: c.left_on_base,
    },
  });

  // A game that answers for the cells the renderer asks about, and throws on anything else — so a
  // renderer reading the source board instead of the puzzle fails here rather than passing quietly.
  const fakeGame = (c) => ({
    value: (name) => {
      const totals = [0, 1, 2, 3].map((i) => c.footnotes.reduce((sum, row) => sum + row[i], 0));
      const total = name.match(/^footnote_totals\.(.+)$/);
      if (total) return totals[FOOTNOTE_COLUMNS.indexOf(total[1])];
      const cell = name.match(/^footnotes\[(\d+)\]\.(.+)$/);
      if (cell) return c.footnotes[Number(cell[1])][FOOTNOTE_COLUMNS.indexOf(cell[2])];
      throw new Error(`the renderer asked for ${name}, which is not on the footnote line`);
    },
  });

  for (const c of cases) {
    test(`the browser renderer produces the canonical line: ${c.name}`, async () => {
      const { renderFootnotes } = await import("../ui/phone/board.js");

      equal(renderFootnotes(fakePuzzle(c), fakeGame(c)).textContent, c.expected, c.why);
    });
  }

  test("⚠️ every printed term carries a count and at least one slot reference", async () => {
    // The parity rule, stated as what it forbids: a term rendered with one half and not the other
    // fails here even for a shape the cases above do not contain.
    const { renderFootnotes } = await import("../ui/phone/board.js");
    let checked = 0;

    for (const c of cases) {
      const line = renderFootnotes(fakePuzzle(c), fakeGame(c));
      for (const term of line.querySelectorAll(".term:not(.lob)")) {
        for (const carrier of term.querySelector(".who").textContent.split(", ")) {
          const [count, slot] = carrier.split(" ");
          assert(/^[1-9][0-9]*$/.test(count), `${carrier} has no count`);
          assert(slot !== undefined && slot.length > 1, `${carrier} has no slot reference`);
          checked += 1;
        }
      }
    }
    assert(checked > 0, "no term was printed at all, so this test proves nothing");
  });
});

suite("⚠️ A cell takes two digits, and a two-digit value never starts with a zero", () => {
  // The rule for the batting grid, and the same code path serves every cell that is a plain integer.
  // ⚠️ **It was written twice and only one copy had a cap.** The grid path stopped at 99; the innings
  // path grew without any bound, so `IP` accepted `8444` — four digits in a cell 44px wide.
  //
  // ⚠️ **And the leading zero was right by coercion rather than by rule.** `Number("05")` is 5, so the
  // old code behaved correctly and said nothing about why. A reader could not tell it was intended, and
  // the next person to reach for `parseInt` would have lost it without a test going red.
  const cases = [
    { current: null, digit: 7, want: 7, why: "an empty cell takes the digit" },
    { current: 0, digit: 5, want: 5, why: "a two-digit value never starts with a zero" },
    { current: 0, digit: 0, want: 0, why: "and zero itself is still a value a player can enter" },
    { current: 1, digit: 0, want: 10, why: "a zero in the second position is a real number" },
    { current: 8, digit: 4, want: 84, why: "two digits is the limit, not one" },
    { current: 84, digit: 4, want: 4, why: "past two digits the cell restarts rather than refusing" },
    { current: 99, digit: 1, want: 1, why: "the boundary itself" },
  ];

  for (const { current, digit, want, why } of cases) {
    test(`grow(${current}, ${digit}) is ${want} — ${why}`, async () => {
      const { grow } = await import("../ui/phone/board.js");

      equal(grow(current, digit), want);
    });
  }

  test("nothing a player can type reaches three digits", async () => {
    // Stated as what it forbids, over every reachable pair rather than the seven above: a cap that
    // held for the cases someone thought of is the cap that failed here in the first place.
    const { grow } = await import("../ui/phone/board.js");
    const wrong = [];

    for (let current = 0; current <= 99; current += 1) {
      for (let digit = 0; digit <= 9; digit += 1) {
        const grown = grow(current, digit);
        if (grown > 99 || grown < 0) wrong.push(`grow(${current}, ${digit}) = ${grown}`);
      }
    }
    equal(wrong, [], "a reachable entry left the two-digit range");
  });
});

suite("⚠️ What a screen reader hears follows what the cell holds", () => {
  // ⚠️ **An explicit `aria-label` *replaces* the element's text as its name.** The label was written
  // once at render with the row and column, and `paint()` never touched it — so a screen reader read
  // `SS, H` whether the cell held nothing, a 1 or a 17. `aria-pressed` says which cell is selected and
  // nothing about what is in it, and on a board whose whole interaction is re-reading your own earlier
  // entries, that is the one thing the accessible path could not do.
  //
  // Derived in the same redraw as the visual state, because two paths computing one fact is how they
  // drift — and this pair had already drifted.
  const board = async () => {
    const { renderSection, paint: repaint, columnsFor, totalNameFor } = await import("../ui/phone/board.js");
    const { battingCell } = await import("../engine/columns.js");
    const puzzle = readPackage(packages[0].raw);
    const game = createGame(puzzle);
    const node = renderSection({
      title: "t",
      columns: columnsFor.batting,
      rows: puzzle.puzzle.batting,
      labels: puzzle.labels,
      slots: puzzle.slotReferences,
      cellName: battingCell,
      totalName: totalNameFor.batting,
      game,
      onSelect: () => {},
    });
    return { node, game, repaint };
  };

  test("the name follows entering, changing and clearing", async () => {
    const { node, game, repaint } = await board();
    const cell = node.querySelector(".cell.blank");
    assert(cell, "no blank cell to test");
    const seen = [];
    const read = () => seen.push(cell.getAttribute("aria-label"));

    read();
    for (const value of [5, 12, null]) {
      game.enter(cell.dataset.cell, value);
      repaint(cell, game);
      read();
    }

    const base = seen[0].replace(/, [^,]+$/, "");
    equal(seen, [`${base}, blank`, `${base}, 5`, `${base}, 12`, `${base}, blank`]);
  });

  test("every blank cell names a state from the moment it is drawn", async () => {
    // ⚠️ The opening state was the one that said least: `paint()` ran before the base label existed,
    // so the first cell a screen-reader user meets announced bare context.
    const { node } = await board();
    const blanks = [...node.querySelectorAll(".cell.blank")];

    assert(blanks.length > 0, "no blanks on this board, so the test proves nothing");
    const bare = blanks.filter((cell) => !/, (blank|[\d.]+)$/.test(cell.getAttribute("aria-label") ?? ""));
    equal(bare.map((cell) => cell.dataset.cell), [], "a blank cell was drawn with no state in its name");
  });

  test("an innings cell reads the way it is written, not as outs", async () => {
    const { node, game, repaint } = await board();
    const cell = node.querySelector(".cell.blank");
    game.enter(cell.dataset.cell, 25);
    repaint(cell, game);

    // The batting grid is whole numbers; the point is that the name carries the *rendered* value, which
    // is what makes `8.1` correct on an outs cell rather than `25`.
    assert(cell.getAttribute("aria-label").endsWith(", 25"), cell.getAttribute("aria-label"));
    equal(cell.textContent, "25", "the name and the text disagree");
  });
});

suite("⚠️ A thirds key means one thing, and only where it means it", () => {
  // ⚠️ **The branch ran before the flag it depends on.** `key.thirds` was handled ahead of the innings
  // check, so a thirds key on any plain-integer cell computed `floor(current / 3) * 3 + thirds` and
  // wrote the result as a whole number — `1⁄3` on an empty hits cell entered `1`. A control performing
  // an operation other than the one printed on it, into a board that deliberately withholds correctness
  // feedback, so the wrong value travels into every deduction after it.
  //
  // Guarded in the handler **and** disabled in the pad. A control prevented only by being greyed out is
  // one that works again the moment anything reaches it another way.
  test("the shell and the keypad ask the same question", async () => {
    const { isInningsCell } = await import("../ui/phone/board.js");

    assert(isInningsCell("pitching[0].outs"), "an outs cell is measured in thirds");
    for (const name of ["batting[0].hits", "pitching[0].hits", "batting_totals.runs", "pitching[1].walks"]) {
      assert(!isInningsCell(name), `${name} is a plain integer and must not take thirds`);
    }
  });

  test("⚠️ a thirds key leaves every plain-integer cell exactly as it was", async () => {
    // The handler's own refusal, not the pad's. ⚠️ This rule lived in `main.js`, which the suite does
    // not import — so it was unguarded by construction, which is how the branch came to run ahead of
    // the flag it depends on. Driven through `applyKey` now, where a test can reach it.
    const { applyKey } = await import("../ui/phone/board.js");
    const puzzle = readPackage(packages[0].raw);
    const game = createGame(puzzle);
    const plain = game.blanks().filter((name) => !name.endsWith(".outs"));

    assert(plain.length > 0, "no plain-integer blanks on this board, so the test proves nothing");
    const damaged = [];
    for (const name of plain) {
      for (const seed of [null, 0, 4, 17]) {
        game.enter(name, seed);
        for (const thirds of [1, 2]) applyKey(game, name, { thirds });
        if (game.value(name) !== seed) damaged.push(`${name}: ${seed} became ${game.value(name)}`);
      }
      game.enter(name, null);
    }
    equal(damaged, [], "a thirds key changed a cell that is not measured in thirds");
  });

  test("a thirds key adjusts an outs cell, and replaces rather than accumulating", async () => {
    // The other half: a guard that refused everything would satisfy the test above.
    const { applyKey } = await import("../ui/phone/board.js");
    const puzzle = readPackage(packages[0].raw);
    const game = createGame(puzzle);
    const outs = game.blanks().find((name) => name.endsWith(".outs"));
    assert(outs !== undefined, "no blank outs cell on this board, so this proves nothing");

    applyKey(game, outs, { digit: 8 });
    const whole = game.value(outs);
    applyKey(game, outs, { thirds: 1 });
    const third = game.value(outs);
    applyKey(game, outs, { thirds: 2 });
    const swapped = game.value(outs);

    equal(whole, 24, "eight whole innings is twenty-four outs");
    equal(third, 25, "a third did not adjust the outs");
    equal(swapped, 26, "the thirds accumulated instead of replacing");
  });

  test("the pad offers the thirds keys only for an outs cell", async () => {
    const { renderKeypad } = await import("../ui/phone/board.js");
    const pad = renderKeypad(() => {});
    const thirds = [...pad.querySelectorAll("button.thirds")];

    assert(thirds.length === 2, `${thirds.length} thirds keys, expected 2`);
    equal(thirds.map((key) => key.disabled), [true, true], "the pad opens with thirds available");
    pad.allowThirds(true);
    equal(thirds.map((key) => key.disabled), [false, false], "an outs cell did not enable them");
    equal(thirds.map((key) => key.getAttribute("aria-disabled")), ["false", "false"], "the name disagrees");
    pad.allowThirds(false);
    equal(thirds.map((key) => key.disabled), [true, true], "leaving an outs cell did not disable them");
  });
});

suite("⚠️ The highlight paints over a filled cell", () => {
  // ⚠️ **A defect no assertion about classes could have caught.** `paint()` set `filled`, `peer` and
  // `selected` correctly and the board still showed nothing on the cells the player had written in —
  // because `.cell.blank.filled` is three classes and `.cell.peer` is two, so the **ground outranked the
  // state whatever the source order**. The player saw the highlight everywhere except where their eye
  // was. Only a computed style can see it, which is why the real stylesheets are loaded by this page.
  //
  // Ground says *what kind of cell this is*; state says *where you are now*. A state that cannot paint
  // over ground is not a state.
  const paint = async () => {
    const { renderSection, paint: repaint, columnsFor, totalNameFor } = await import("../ui/phone/board.js");
    const { battingCell } = await import("../engine/columns.js");
    const puzzle = readPackage(packages[0].raw);
    const game = createGame(puzzle);

    const host = document.getElementById("board");
    host.replaceChildren(
      renderSection({
        title: "t",
        columns: columnsFor.batting,
        rows: puzzle.puzzle.batting,
        labels: puzzle.labels,
        slots: puzzle.slotReferences,
        cellName: battingCell,
        totalName: totalNameFor.batting,
        game,
        onSelect: () => {},
      }),
    );
    // ⚠️⚠️ **This used to set `host.hidden = false` here and `true` again at the end of each test, and
    // that restore was a hardcoded copy of the page's initial state.** When `#board` stopped being
    // `hidden` and started rendering off-screen, these three lines put it back to `display: none` for
    // every test that ran afterwards — so the focus assertions failed against a board that no test in
    // this file had hidden on purpose. Two places encoding one fact, and the copy won.
    //
    // The board renders now, permanently and off-screen, so nothing needs revealing for the duration.
    const blanks = [...host.querySelectorAll(".cell.blank")];
    assert(blanks.length >= 2, "this package has fewer than two blanks, so the test proves nothing");
    for (const cell of blanks.slice(0, 2)) {
      game.enter(cell.dataset.cell, 1);
      repaint(cell, game);
    }
    return { host, blanks };
  };

  test("a filled cell in the active row or column still shows the peer colour", async () => {
    const { host, blanks } = await paint();
    const plain = getComputedStyle(blanks[0]).backgroundColor;
    blanks[0].classList.add("peer");
    const peered = getComputedStyle(blanks[0]).backgroundColor;

    assert(blanks[0].classList.contains("filled"), "the cell under test is not filled, so it proves nothing");
    assert(peered !== plain, `a filled peer kept its ground colour ${plain}`);
  });

  test("a filled cell that is selected still shows the selected colour", async () => {
    const { host, blanks } = await paint();
    blanks[1].classList.add("peer");
    const peered = getComputedStyle(blanks[1]).backgroundColor;
    blanks[1].classList.add("selected");
    const chosen = getComputedStyle(blanks[1]).backgroundColor;

    assert(blanks[1].classList.contains("filled"), "the cell under test is not filled, so it proves nothing");
    assert(chosen !== peered, `a filled selected cell painted as a peer, ${chosen}`);
  });
});

suite("⚠️ The clock counts time at the board, not time since the tab opened", () => {
  // `docs/serve-flow.md` §5: only time with the board open counts, because the number is shared and one
  // that includes lunch means nothing to the person reading it.
  //
  // ⚠️ **The engine used to compute `now() - startedAt`.** That is wall-clock from construction, so a
  // player who left the tab open overnight came back to a fourteen-hour game. The defect was not that
  // nobody stopped the clock — there was no clock to stop.
  const at = (t) => () => t.value;

  test("a held clock counts nothing, and keeps what it counted", async () => {
    const { createClock } = await import("../engine/clock.js");
    const t = { value: 1000 };
    const clock = createClock({ now: at(t) });

    clock.run();
    t.value = 4000;
    equal(clock.elapsed(), 3000, "a running clock did not count");
    clock.hold();
    t.value = 999999;
    equal(clock.elapsed(), 3000, "a held clock kept counting");
    clock.run();
    t.value = 1000999;
    equal(clock.elapsed(), 4000, "resuming did not continue from where it stopped");
  });

  test("⚠️ the snapshot cannot express a start time", async () => {
    // Stated as what the shape forbids rather than as what a caller should remember. A snapshot
    // carrying `since` would let a reload count the hours the tab was closed, which is the whole reason
    // this module exists — so there is no field that could carry it.
    const { createClock } = await import("../engine/clock.js");
    const t = { value: 5000 };
    const clock = createClock({ now: at(t) });
    clock.run();
    t.value = 8000;

    equal(Object.keys(clock.snapshot()), ["elapsed"]);
    equal(clock.snapshot().elapsed, 3000);
  });

  test("running twice does not start a second span", async () => {
    const { createClock } = await import("../engine/clock.js");
    const t = { value: 0 };
    const clock = createClock({ now: at(t) });
    clock.run();
    t.value = 100;
    clock.run();
    t.value = 200;

    equal(clock.elapsed(), 200, "a second run() restarted or doubled the span");
  });

  test("⚠️ a clock that moves backwards adds nothing rather than subtracting", async () => {
    // System time can move: a manual change, an NTP correction. A negative span would hand the player a
    // shorter time than they played, which is the one direction the number must not move by accident.
    const { createClock } = await import("../engine/clock.js");
    const t = { value: 10000 };
    const clock = createClock({ now: at(t) });
    clock.run();
    t.value = 4000;

    assert(clock.elapsed() >= 0, `elapsed went negative: ${clock.elapsed()}`);
    clock.hold();
    t.value = 5000;
    clock.run();
    t.value = 6000;
    equal(clock.elapsed(), 1000, "the backwards span was not discarded");
  });

  test("the game reports the clock's duration, and freezes it on finish", async () => {
    const { createClock } = await import("../engine/clock.js");
    const t = { value: 0 };
    const clock = createClock({ now: at(t) });
    const game = createGame(readPackage(packages[0].raw), clock);

    clock.run();
    t.value = 7000;
    equal(game.record().duration_ms, 7000);
    game.finish();
    t.value = 999999;
    equal(game.record().duration_ms, 7000, "the duration moved after the board was finished");
  });
});

suite("⚠️ A malformed saved session never costs the player their board", () => {
  // ⚠️ **Local storage is untrusted input**: it outlives versions of this code, it is editable by hand,
  // and a tab killed mid-write leaves half a value. The store's own comment used to promise that
  // "malformed storage reads as absent" — a claim about the *session* made by a function that only
  // knows about *bytes*. The claim was broader than the check, which is the shape this project keeps
  // paying for.
  const game = () => createGame(readPackage(packages[0].raw));

  const malformed = [
    { why: "kills the board: for...of over a number", saved: { entries: {}, hinted: 7, firstWrong: [], elapsed: 0 } },
    { why: "the same, one field over", saved: { entries: {}, firstWrong: 42 } },
    { why: "silent: Object.entries on a string yields index pairs", saved: { entries: "nope" } },
    { why: "silent and worse: a string installed as a cell value", saved: { entries: { "batting[0].hits": "five" } } },
    { why: "a fractional cell value is not a cell value", saved: { entries: { "batting[0].hits": 1.5 } } },
    { why: "true is an integer to nobody", saved: { entries: { "batting[0].hits": true } } },
    { why: "a negative count is not a count", saved: { entries: { "batting[0].hits": -1 } } },
    { why: "names must be names", saved: { hinted: [1, 2] } },
    { why: "a duration cannot run backwards", saved: { elapsed: -5 } },
    { why: "nor be a word", saved: { elapsed: "ages" } },
    { why: "an array is not a session", saved: [1, 2, 3] },
    { why: "and neither is null", saved: null },
  ];

  for (const { why, saved } of malformed) {
    test(`refused: ${why}`, () => {
      const g = game();
      const blanks = g.blanks().length;
      let threw = null;

      try {
        equal(g.restore(saved), false, "a malformed session was accepted");
      } catch (error) {
        threw = error;
      }

      equal(threw, null, `restore threw instead of refusing: ${threw?.message}`);
      equal(g.blanks().length, blanks, "a refused session still changed the board");
    });
  }

  test("⚠️ a refusal leaves the game exactly as it was, not emptier", async () => {
    // `restore()` cleared its three maps and *then* repopulated, so a shape that threw part-way left
    // the player's board gone and no session to put back. The check happens before anything is cleared.
    const g = game();
    const blank = g.blanks()[0];
    g.enter(blank, 4);

    equal(g.restore({ entries: {}, hinted: 7 }), false);
    equal(g.value(blank), 4, "a refused session wiped work the player had already done");
  });

  test("a well-formed session is still accepted, so the guard is not refusing everything", () => {
    const g = game();
    const blank = g.blanks()[0];

    equal(g.restore({ entries: { [blank]: 3 }, hinted: [], firstWrong: [], elapsed: 900 }), true);
    equal(g.value(blank), 3);
    equal(g.record().duration_ms, 900);
  });

  test("an absent session is a refusal, not a crash", () => {
    // What `store.load()` returns when there is nothing there, handed straight to `restore()` by the
    // shell. It has to be the ordinary case rather than one the caller checks for.
    equal(game().restore(null), false);
    equal(game().restore(undefined), false);
  });

  test("⚠️ names that no longer exist are dropped, not refused", async () => {
    // The board changes shape between generations. A session naming a cell that is gone is stale, not
    // malformed — refusing it would throw away a perfectly good session over one obsolete key.
    const g = game();
    const blank = g.blanks()[0];

    equal(g.restore({ entries: { [blank]: 2, "batting[99].hits": 5 } }), true);
    equal(g.value(blank), 2, "the live entry was lost with the dead one");
  });
});

suite("⚠️ The clock follows the player, not the tab", () => {
  // `docs/serve-flow.md` §5, and a module rather than fifteen lines in `main.js` — which the suite
  // cannot import, so a rule written there is unguarded by construction. That has already cost a keypad
  // control doing something other than what it printed, and a digit cap in one of the two places it was
  // written.
  const rig = () => {
    const listeners = new Map();
    const on = (kind) => ({
      hidden: false,
      addEventListener(event, fn) {
        listeners.set(`${kind}:${event}`, fn);
      },
      removeEventListener(event) {
        listeners.delete(`${kind}:${event}`);
      },
    });
    const doc = on("doc");
    const target = on("target");
    const fire = (key) => listeners.get(key)?.();
    const timers = [];
    const setTimer = (fn) => {
      timers.push(fn);
      return timers.length;
    };
    const clearTimer = () => {};
    return { doc, target, fire, listeners, timers, setTimer, clearTimer, runIdle: () => timers.at(-1)?.() };
  };

  const stub = () => {
    let running = false;
    let saves = 0;
    return {
      clock: { run: () => (running = true), hold: () => (running = false), isRunning: () => running },
      save: () => (saves += 1),
      get running() {
        return running;
      },
      get saves() {
        return saves;
      },
    };
  };

  test("a visible board starts the clock, and a hidden one stops it", async () => {
    const { followAttention } = await import("../engine/clock.js");
    const r = rig();
    const s = stub();
    followAttention({ clock: s.clock, save: s.save, doc: r.doc, target: r.target, ...r });

    assert(s.running, "the clock did not start on a visible board");
    r.doc.hidden = true;
    r.fire("doc:visibilitychange");
    assert(!s.running, "hiding the page did not stop the clock");
    r.doc.hidden = false;
    r.fire("doc:visibilitychange");
    assert(s.running, "returning did not restart the clock");
  });

  test("⚠️ a board that opens hidden does not start counting", async () => {
    // A tab restored into the background on a phone is exactly this, and it is the case a check written
    // as `on visibilitychange` alone would miss entirely.
    const { followAttention } = await import("../engine/clock.js");
    const r = rig();
    const s = stub();
    r.doc.hidden = true;
    followAttention({ clock: s.clock, save: s.save, doc: r.doc, target: r.target, ...r });

    assert(!s.running, "a board opened in a hidden tab started its clock");
  });

  test("⚠️ silence stops the clock, and touching the board starts it again", async () => {
    // The second signal. Visibility alone cannot see the tab left open on a desk, which is the case
    // that produces an absurd shared time.
    const { followAttention } = await import("../engine/clock.js");
    const r = rig();
    const s = stub();
    followAttention({ clock: s.clock, save: s.save, doc: r.doc, target: r.target, ...r });

    r.runIdle();
    assert(!s.running, "the idle timeout did not stop the clock");
    r.fire("target:pointerdown");
    assert(s.running, "a touch did not resume the clock");
    r.runIdle();
    assert(!s.running, "the timeout did not re-arm after activity");
  });

  test("⚠️ the session is written down at the moment the clock stops", async () => {
    // What happens next may be the tab being killed rather than closed, and a save waiting for
    // `beforeunload` is a session that survives on a desktop and vanishes on a phone.
    const { followAttention } = await import("../engine/clock.js");
    const r = rig();
    const s = stub();
    followAttention({ clock: s.clock, save: s.save, doc: r.doc, target: r.target, ...r });

    equal(s.saves, 0, "starting the clock wrote a session");
    r.doc.hidden = true;
    r.fire("doc:visibilitychange");
    equal(s.saves, 1, "hiding the page did not save");
    r.runIdle();
    equal(s.saves, 2, "the idle timeout did not save");
  });

  test("the timeout is generous, because staring at the board is play", async () => {
    // §5: a short timeout would discount exactly the thinking the game is about. Asserted as a floor,
    // not as a number, so tuning it upward does not fail.
    const { IDLE_MS } = await import("../engine/clock.js");

    assert(IDLE_MS >= 3 * 60 * 1000, `${IDLE_MS}ms is short enough to discount thinking`);
  });
});

suite("⚠️ A session survives a reload, and a broken store never stops the game", () => {
  // `docs/serve-flow.md` §6. ⚠️ **C7 is irreversible**: storing aggregate state instead of the session
  // loses history that cannot be reconstructed, which is why this exists before anything reads it.
  const fakeStorage = () => {
    const held = new Map();
    return {
      getItem: (k) => (held.has(k) ? held.get(k) : null),
      setItem: (k, v) => held.set(k, String(v)),
      removeItem: (k) => held.delete(k),
      _held: held,
    };
  };

  test("what is saved comes back: entries, mistakes, and the duration", async () => {
    const { createStore } = await import("../engine/store.js");
    const { createClock } = await import("../engine/clock.js");
    const store = createStore(fakeStorage());
    const puzzle = readPackage(packages[0].raw);

    const t = { value: 0 };
    const first = createGame(puzzle, createClock({ now: () => t.value }));
    first.clock.run();
    const blank = first.blanks()[0];
    const answer = first.puzzle.solution.batting.flat()[0];
    first.enter(blank, answer === 0 ? 1 : 0);
    first.enter(blank, 6);
    t.value = 12000;
    store.save(puzzle.id, first.snapshot());

    const second = createGame(puzzle, createClock({ now: () => 0 }));
    second.restore(store.load(puzzle.id));

    equal(second.value(blank), 6, "the entry did not come back");
    equal(second.record().errors, first.record().errors, "the mistakes did not come back");
    equal(second.record().duration_ms, 12000, "the clock came back at zero");
  });

  test("⚠️ one puzzle, one key — tomorrow carries nothing across", async () => {
    const { createStore, keyFor } = await import("../engine/store.js");
    const storage = fakeStorage();
    const store = createStore(storage);

    store.save("aaaaaaaaaaaaaaaa", { entries: { "batting[0].hits": 1 } });
    store.save("bbbbbbbbbbbbbbbb", { entries: { "batting[0].hits": 9 } });

    equal(store.load("aaaaaaaaaaaaaaaa").entries["batting[0].hits"], 1);
    equal(store.load("bbbbbbbbbbbbbbbb").entries["batting[0].hits"], 9);
    assert(keyFor("aaaaaaaaaaaaaaaa") !== keyFor("bbbbbbbbbbbbbbbb"), "two puzzles share one key");
    equal(store.load("cccccccccccccccc"), null, "an unplayed puzzle reported a session");
  });

  test("⚠️ malformed storage reads as absent, never as half a session", async () => {
    // Half a session applied to the day's board is worse than none: the player meets entries they did
    // not make, with no way to tell which are theirs.
    const { createStore, keyFor } = await import("../engine/store.js");
    const storage = fakeStorage();
    const store = createStore(storage);

    for (const junk of ["", "{", "null", "[1,2,3]", '"a string"', "7"]) {
      storage.setItem(keyFor("x"), junk);
      equal(store.load("x"), null, `${JSON.stringify(junk)} was not treated as absent`);
    }
  });

  test("⚠️ a store that throws never reaches the caller", async () => {
    // §23: with the backend down the game still works, and a full or disabled store is the same class
    // of failure one layer closer. The failure a player forgives is a lost session, not a dead board.
    const { createStore } = await import("../engine/store.js");
    const hostile = {
      getItem: () => {
        throw new Error("SecurityError");
      },
      setItem: () => {
        throw new Error("QuotaExceededError");
      },
      removeItem: () => {
        throw new Error("nope");
      },
    };
    const store = createStore(hostile);

    equal(store.load("x"), null, "a throwing read escaped");
    equal(store.save("x", { entries: {} }), false, "a throwing write escaped");
    equal(store.forget("x"), false, "a throwing delete escaped");
  });

  test("browserStorage() returns something usable even where localStorage is refused", async () => {
    // ⚠️ Private browsing throws on *access*, not on use, so the reference itself is taken inside a
    // try. A shell reading it at module scope crashes before drawing anything — the whole board lost to
    // a setting about saving.
    const { browserStorage } = await import("../engine/store.js");
    const storage = browserStorage();

    storage.setItem("boxscorepuzzle.session.v1.probe-test", "1");
    storage.removeItem("boxscorepuzzle.session.v1.probe-test");
    assert(typeof storage.getItem === "function", "browserStorage returned nothing usable");
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

  test("⚠️ a replacement catalogue changes the footnote markers, not only the term names", async () => {
    // ⚠️ **The completeness test cannot see this.** It asserts the catalogue has every key; it says
    // nothing about whether the renderer asks for them. `#` was spelled inline here while the slot
    // column's heading read `board.slot` from the catalogue, and `×` had no key at all — so a catalogue
    // could translate `HBP` and leave both marks beside it in English, and every key test still passed.
    //
    // Driven through a catalogue whose markers differ from English, which is the only way to tell a
    // rendered string that came from the catalogue from one that happens to match it.
    const { renderFootnotes } = await import("../ui/phone/board.js");
    const live = packages
      .map(({ raw }) => readPackage(raw))
      .find((p) => p.puzzle.footnoteTotals.some((total) => total > 0));
    assert(live !== undefined, "no reference package has a live footnote term, so this proves nothing");

    const before = renderFootnotes(live, createGame(live)).textContent;
    try {
      useCatalog({ ...CATALOGS.en, "board.slot": "§" });
      const after = renderFootnotes(live, createGame(live)).textContent;

      assert(before.includes("#"), "the English render carries no slot prefix, so this proves nothing");
      assert(after.includes("§"), "the slot prefix did not come from the catalogue");
      assert(!after.includes("#"), "an English slot prefix survived a replacement catalogue");
    } finally {
      // Restored whatever happens: a leaked catalogue would silently change every test after this one.
      useCatalog(CATALOGS.en);
    }
  });

  test("a replacement catalogue is complete, or the swap is refused", () => {
    // ⚠️ The version this replaces swapped in a *complete* copy and compared it with the same complete
    // catalogue — it could not fail, because there was no refusal in the code to trigger. Stated now as
    // what it forbids: a partial catalogue installs, and the failure surfaces mid-render at whichever
    // key `text()` reaches first.
    const before = keys();
    useCatalog({ ...CATALOGS.en });
    equal(keys().sort(), before.sort(), "the catalogue lost keys on a swap");

    const { "board.totals": _dropped, ...partial } = CATALOGS.en;
    throws(() => useCatalog(partial), "incomplete", "a catalogue missing a key was installed");
    throws(() => useCatalog({ ...CATALOGS.en, "board.nothing": "x" }), "incomplete", "an unexpected key was installed");
    throws(() => useCatalog({}), "incomplete");

    // And the refusal is atomic: a rejected swap leaves the previous catalogue in place.
    equal(keys().sort(), before.sort(), "a refused swap still changed the active catalogue");
    useCatalog(CATALOGS.en);
  });
});

suite("⚠️⚠️ The stylesheet's rules survive being parsed, not merely being written", () => {
  // ⚠️⚠️ **A stylesheet fails by doing nothing.** The line score's narrow-device rule was silently dead
  // twice in one afternoon: first an edit closed a comment block early, so the prose that followed
  // parsed as CSS and the parser discarded everything up to the next recoverable token — including the
  // rule. Then the note written to explain that closed the comment again, because it quoted the very
  // character pair that ends a CSS comment. **Prose about CSS syntax, inside CSS, is executable.**
  //
  // Neither raised anything. The file contained the rule both times; `document.styleSheets` did not,
  // and the page simply drew a twelve-inning board at full size on a 320px screen — the one case the
  // rule exists for. Reading the source and believing it is what failed, so this asks the parser.
  const REQUIRED = [
    ["board.css", "(max-width: 359px)", "the line score's narrow-device size (§6, MAX_INNINGS)"],
    // ⚠️ `tokens.css`, not `board.css`. The palette moved there so the tutorial page — which links
    // the tokens and not the board — stops rendering white while the two pages either side of it
    // are dark. v36-P2-13.
    ["tokens.css", "(prefers-color-scheme: dark)", "the dark theme, on every page rather than one"],
  ];

  test("every media rule the board depends on is present after parsing", async () => {
    for (const [file, condition, why] of REQUIRED) {
      const text = await (await fetch(`../ui/phone/${file}`, { cache: "reload" })).text();
      const style = document.createElement("style");
      style.textContent = text;
      document.head.append(style);
      const conditions = [...style.sheet.cssRules]
        .filter((rule) => rule.type === CSSRule.MEDIA_RULE)
        .map((rule) => rule.conditionText);
      style.remove();

      assert(
        conditions.includes(condition),
        `${file} lost ${condition} — ${why}. The parser kept ${conditions.length} media rules: ` +
          `${conditions.join(", ") || "none"}. Look for a comment closed early.`,
      );
    }
  });

  test("no rule is lost anywhere in a stylesheet, whatever the cause", async () => {
    // ⚠️ The check above names two rules and would not notice a third going missing. This one is
    // blind to *which* rule: it counts what the parser kept against what the file declares, so a
    // truncated stylesheet fails even when the survivor list looks reasonable.
    for (const file of ["board.css", "tokens.css"]) {
      const text = await (await fetch(`../ui/phone/${file}`, { cache: "reload" })).text();
      const style = document.createElement("style");
      style.textContent = text;
      document.head.append(style);
      const kept = style.sheet.cssRules.length;
      style.remove();

      // Every top-level block in the source, with comments removed so their braces do not count.
      const stripped = text.replace(/\/\*[\s\S]*?\*\//g, "");
      let depth = 0;
      let declared = 0;
      for (const char of stripped) {
        if (char === "{") {
          if (depth === 0) declared += 1;
          depth += 1;
        } else if (char === "}") depth -= 1;
      }

      assert(depth === 0, `${file} has unbalanced braces once comments are stripped (${depth})`);
      equal(kept, declared, `${file}: the parser kept ${kept} top-level rules of ${declared} declared`);
    }
  });
});

suite("⚠️⚠️ The half-inning marker is a given, so it has to be legible", () => {
  // ⚠️⚠️ **The `x` says the home side did not bat.** That makes their outs 24 rather than 27 and feeds
  // the global identity directly, so a marker the player cannot read is a **lost given, not a faint
  // decoration**. It shipped at 2.21:1 against the scoreboard ground — below WCAG's 3.0 floor for any
  // content, let alone 4.5 for text this size — from a dim colour and `opacity: .7` together.
  //
  // ⚠️ **A dimmed-but-accessible variant does not exist on this ground.** Against `--fenway`, pure
  // black reaches only 4.27:1, so nothing darker than the panel can pass; a neutral grey must be
  // `#f5f5f5` or brighter, which is the digit's own brightness. The marker is therefore as bright as a
  // digit and distinguished by weight — and by being a letter among numerals.
  const FLOOR = 4.5;

  const channels = (value) => value.match(/\d+(\.\d+)?/g).map(Number);
  const luminance = ([r, g, b]) =>
    0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b);
  const chan = (value) => {
    const v = value / 255;
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
  };
  const flatten = (fg, bg, alpha) => fg.map((v, i) => v * alpha + bg[i] * (1 - alpha));
  const contrast = (a, b) => {
    const [hi, lo] = [luminance(a), luminance(b)].sort((p, q) => q - p);
    return (hi + 0.05) / (lo + 0.05);
  };

  const drawn = async (innings) => {
    const { renderLineScore } = await import("../ui/phone/board.js");
    // ⚠️ The home side one half-inning short, or no marker is drawn at all and the test passes on a
    // board that never contained its subject.
    const table = renderLineScore(
      {
        offense_by_inning: Array.from({ length: innings }, () => 1),
        defense_by_inning: Array.from({ length: innings - 1 }, () => 0),
        offense_runs: 11, offense_hits: 16, offense_errors: 2,
        defense_runs: 9, defense_hits: 14, defense_errors: 1,
      },
      false,
    );
    // ⚠️ The frame comes from `renderLineScore` now. This page used to build the
    // `.linescore` wrapper itself, which is the harness supplying a property of the thing under
    // test — it happened to match, and a sample cannot judge what the sample provides.
    const frame = table;
    document.body.append(frame);
    return { table: frame.querySelector("table"), frame };
  };

  test("the not-played marker meets the contrast floor, and so does a played digit", async () => {
    const { table, frame } = await drawn(12);
    const marker = table.querySelector("td.unplayed");
    const played = table.querySelector("td.value");

    assert(marker, "no not-played marker was rendered, so this test proves nothing");

    const ground = channels(getComputedStyle(table).backgroundColor);
    const effective = (cell) =>
      flatten(channels(getComputedStyle(cell).color), ground, Number(getComputedStyle(cell).opacity));
    const markerRatio = contrast(effective(marker), ground);
    const playedRatio = contrast(effective(played), ground);
    frame.remove();

    assert(markerRatio >= FLOOR, `the x renders at ${markerRatio.toFixed(2)}:1, under ${FLOOR}`);
    assert(playedRatio >= FLOOR, `a played digit renders at ${playedRatio.toFixed(2)}:1, under ${FLOOR}`);
  });

  // ⚠⚠ **A test asserting the marker looked *different* from a value was deleted here, deliberately.**
  // It pinned an interim design — the same colour at a lighter weight — and the decision went the other
  // way: the marker is drawn exactly as a run is drawn, because it reads as not-a-value by being a
  // letter among numerals. Keeping the test would have frozen a choice already reversed, and a guard
  // that outlives its decision fails honest changes.
  //
  // ⚠️ The contrast test above stays, because it is about the panel rather than about the marker. If
  // the scoreboard's colours ever move, every cell on it is checked — the `x` included, for free.
});

suite("⚠️⚠️ The end of the game, and what the board may never say", () => {
  // ⚠️⚠️ **The board never says which cells are wrong, or how many.** Both were considered and both
  // were rejected in `serve-flow.md`, for reasons about the game rather than about taste: marking the
  // wrong cells makes probing beat deducing, and counting them is a binary search over the board.
  //
  // These are the tests that have to survive somebody deciding to be helpful. They assert what the
  // message must NOT contain, which is the only form that catches a well-meant improvement.

  const solvedGame = async (raw) => {
    const { createGame } = await import("../engine/game.js");
    const { readPackage } = await import("../engine/package.js");
    const puzzle = readPackage(raw);
    const game = createGame(puzzle);
    return { puzzle, game };
  };

  test("an unfinished board is called unfinished, not wrong", async () => {
    // ⚠️ Two states, not one. A player who has not finished has not made a mistake, and telling them
    // they have is both false and discouraging at the only moment they might stop.
    const { checkBoard } = await import("../ui/phone/finish.js");
    const { game } = await solvedGame(packages[0].raw);

    const result = checkBoard(game);

    equal(result.state, "incomplete");
    assert(result.message.length > 0, "an incomplete board got no message");
  });

  test("a full but wrong board gets one sentence and it names nothing", async () => {
    const { checkBoard } = await import("../ui/phone/finish.js");
    const { game } = await solvedGame(packages[0].raw);
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    const blanks = game.blanks();
    // Every cell right except one, which is the case a marking implementation would give away.
    blanks.forEach((name, index) => game.enter(name, answers.get(name) + (index === 0 ? 1 : 0)));

    const result = checkBoard(game);

    equal(result.state, "wrong");
    for (const name of blanks) {
      assert(!result.message.includes(name), `the verdict names the cell ${name}`);
      const column = name.split(".")[1];
      assert(!result.message.includes(column), `the verdict names the column ${column}`);
    }
    assert(!/\d/.test(result.message), `the verdict contains a number: ${result.message}`);
  });

  test("the same sentence whatever is wrong, and however much", async () => {
    // ⚠️ **One message for one wrong cell and for thirty.** A message that varied with the number of
    // mistakes is a count wearing a different hat — the player reads two runs and subtracts.
    const { checkBoard } = await import("../ui/phone/finish.js");
    const one = await solvedGame(packages[0].raw);
    const many = await solvedGame(packages[0].raw);
    const answers = new Map(one.game.cells().map((cell) => [cell.name, cell.answer]));
    const blanks = one.game.blanks();

    blanks.forEach((name, index) => one.game.enter(name, answers.get(name) + (index === 0 ? 1 : 0)));
    blanks.forEach((name) => many.game.enter(name, answers.get(name) + 1));

    equal(checkBoard(one.game).message, checkBoard(many.game).message);
  });

  test("a solved board is solved and carries no message to display", async () => {
    const { checkBoard } = await import("../ui/phone/finish.js");
    const { game } = await solvedGame(packages[0].raw);
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    for (const name of game.blanks()) game.enter(name, answers.get(name));

    const result = checkBoard(game);

    equal(result.state, "solved");
    equal(result.message, "");
  });

  test("⚠️ the clock does not stop for a wrong board, and there is no attempt limit", async () => {
    // §27: no fail state. What a mistake costs is time, which is what gets measured and shared. A
    // limit would add a fail state through the back door and stopping the clock would make errors free.
    const { checkBoard } = await import("../ui/phone/finish.js");
    const { createClock } = await import("../engine/clock.js");
    const { createGame } = await import("../engine/game.js");
    const { readPackage } = await import("../engine/package.js");

    let now = 0;
    // ⚠️ `run()`, because a clock is created held and the shell starts it through `followAttention`.
    // The first version of this test omitted it and failed reporting *the clock stopped: 0ms* — which
    // was true and was about the test rather than the code. Checked against the running application
    // before changing anything: it starts the clock on load and it advances.
    const clock = createClock({ now: () => now });
    clock.run();
    const game = createGame(readPackage(packages[0].raw), clock);
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    game.blanks().forEach((name, index) => game.enter(name, answers.get(name) + (index === 0 ? 1 : 0)));

    for (let attempt = 0; attempt < 5; attempt += 1) {
      now += 1000;
      equal(checkBoard(game).state, "wrong", "an attempt was refused");
    }

    assert(clock.elapsed() >= 5000, `the clock stopped: ${clock.elapsed()}ms`);
  });
});

suite("⚠️⚠️ A finished board stays finished, and its time stays what was earned", () => {
  /** A game over the reference puzzle with a clock this test moves by hand. */
  const gameWithClock = async (start = 0) => {
    const { createGame } = await import("../engine/game.js");
    const { createClock } = await import("../engine/clock.js");
    const { readPackage } = await import("../engine/package.js");
    let now = 1_000_000;
    const clock = createClock({ now: () => now, elapsed: start });
    const puzzle = readPackage(packages[0].raw);
    return { game: createGame(puzzle, clock), clock, puzzle, advance: (ms) => (now += ms) };
  };

  const solve = (game) => {
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    for (const name of game.blanks()) game.enter(name, answers.get(name));
  };

  test("⚠️⚠️ a solved board restored from its session does not restart its clock", async () => {
    // **The reopen path is the one persistence exists for**, and it rewrote the number the player
    // earned. `finish()` froze the duration in memory only: `snapshot()` never carried it, so a
    // restored game had `finishedAt === null`, the shell started the clock for a visible page, and the
    // next Check froze a larger value. Duration is the metric that gets compared and shared.
    const first = await gameWithClock();
    first.clock.run();
    first.advance(90_000);
    solve(first.game);
    const earned = first.game.finish().duration_ms;
    const saved = first.game.snapshot();

    const second = await gameWithClock();
    assert(second.game.restore(saved), "the session was refused");
    // Everything the shell does to a visible board, and then some.
    second.clock.run();
    second.advance(600_000);

    equal(second.game.isFinished(), true, "a finished board came back unfinished");
    equal(second.game.record().duration_ms, earned, "ten minutes of being open were added to a finished game");
    equal(second.game.finish().duration_ms, earned, "checking again re-froze the clock at a later time");
  });

  test("⚠️ the clock is sealed rather than held, so a tap cannot restart it", async () => {
    // `hold()` stops the clock and the next `run()` starts it. `followAttention` calls `run()` on every
    // pointer press and whenever the page becomes visible, so holding is not enough on a board whose
    // duration is already the answer.
    const { game, clock, advance } = await gameWithClock();
    clock.run();
    advance(30_000);
    solve(game);
    const earned = game.finish().duration_ms;

    clock.run();
    advance(300_000);

    equal(clock.isSealed(), true, "the clock was not sealed by finishing");
    equal(clock.elapsed(), earned, "a sealed clock counted five more minutes");
  });

  test("an unfinished session still restores a running clock, which is the ordinary case", async () => {
    // ⚠️ The negative case. A seal that applied to every restore would freeze the clock of a board the
    // player is halfway through, and nothing in the suite would notice because every other assertion
    // here is about a *finished* board.
    const first = await gameWithClock();
    first.clock.run();
    first.advance(45_000);
    first.game.enter(first.game.blanks()[0], 1);
    const saved = first.game.snapshot();

    const second = await gameWithClock();
    second.game.restore(saved);
    second.clock.run();
    second.advance(15_000);

    equal(second.game.isFinished(), false, "an unfinished board came back finished");
    equal(second.clock.isSealed(), false, "an unfinished board came back with a sealed clock");
    equal(second.game.record().duration_ms, 60_000, "the restored clock did not keep counting");
  });

  test("a session with a malformed completion is refused rather than trusted", async () => {
    // §23: a refused session gives the player today's board, never an error. A negative duration is a
    // corrupted session and the field is validated like every other part of the shape.
    const { isSession } = await import("../engine/game.js");

    assert(isSession({ entries: {}, finishedAt: 90_000 }), "a real completion was refused");
    assert(isSession({ entries: {}, finishedAt: null }), "an unfinished board was refused");
    assert(isSession({ entries: {} }), "an absent completion was refused");
    assert(!isSession({ entries: {}, finishedAt: -1 }), "a negative duration was accepted");
    assert(!isSession({ entries: {}, finishedAt: "90000" }), "a string duration was accepted");
    assert(!isSession({ entries: {}, finishedAt: Infinity }), "an infinite duration was accepted");
  });

  test("⚠️ the errors recorded before finishing survive the reopen", async () => {
    // The C7 record is irreversible: what is not collected cannot be reconstructed. A restore that
    // brought back the board and dropped its mistakes would lose them silently.
    const first = await gameWithClock();
    const answers = new Map(first.game.cells().map((cell) => [cell.name, cell.answer]));
    const blanks = first.game.blanks();
    for (const name of blanks) first.game.enter(name, answers.get(name) + (blanks.indexOf(name) < 2 ? 1 : 0));
    equal(first.game.check().state, "wrong");
    const saved = first.game.snapshot();

    const second = await gameWithClock();
    second.game.restore(saved);

    equal(second.game.record().errors, 2, "the reopen lost the mistakes");
  });
});

suite("⚠️ Three hints, spent on the cell the player chose", () => {
  const fresh = async () => {
    const { createGame, HINTS_PER_GAME } = await import("../engine/game.js");
    const { readPackage } = await import("../engine/package.js");
    const puzzle = readPackage(packages[0].raw);
    return { game: createGame(puzzle), puzzle, HINTS_PER_GAME };
  };

  test("a hint fills the named cell with its answer and is not a mistake", async () => {
    const { game } = await fresh();
    const name = game.blanks()[4];
    const answer = game.cells().find((cell) => cell.name === name).answer;

    equal(game.hint(name), answer);

    equal(game.value(name), answer, "the hint did not fill the cell");
    equal(game.isHinted(name), true);
    equal(game.record().hints, 1);
    equal(game.check().state, "incomplete");
    equal(game.record().errors, 0, "a hint was counted as a mistake");
  });

  test("⚠️⚠️ the allowance is enforced by the engine, not by the key being disabled", async () => {
    // A control prevented only by being greyed out works again the moment anything reaches it another
    // way — the note the thirds keys already carry. The next interface will not remember the limit;
    // the engine does.
    const { game, HINTS_PER_GAME } = await fresh();
    const blanks = game.blanks();

    for (let i = 0; i < HINTS_PER_GAME; i += 1) game.hint(blanks[i]);

    equal(game.hintsLeft(), 0);
    throws(() => game.hint(blanks[HINTS_PER_GAME]), "no hints left");
    equal(game.record().hints, HINTS_PER_GAME, "a refused hint was still counted");
  });

  test("hinting the same cell twice is one hint, because it was already given", async () => {
    const { game } = await fresh();
    const name = game.blanks()[0];

    game.hint(name);
    game.hint(name);

    equal(game.record().hints, 1, "the same cell cost two hints");
    equal(game.hintsLeft(), 2);
  });

  test("⚠️ a hint survives the reload and still counts", async () => {
    // C7 is irreversible: a hint the reopen forgets is a shared result that overstates the solve.
    const { game, puzzle } = await fresh();
    const { createGame } = await import("../engine/game.js");
    const name = game.blanks()[1];
    game.hint(name);

    const second = createGame(puzzle);
    assert(second.restore(game.snapshot()), "the session was refused");

    equal(second.record().hints, 1, "the reopen lost the hint");
    equal(second.isHinted(name), true, "the reopen forgot which cell was given");
    equal(second.hintsLeft(), 2);
  });

  test("⚠️⚠️ a hand-edited session cannot buy more than the allowance", async () => {
    // The session is player-writable storage. Without a cap on the way in, an edited one hands out
    // unlimited answers and the record still reads as a legitimate result.
    const { game, puzzle, HINTS_PER_GAME } = await fresh();
    const { createGame } = await import("../engine/game.js");
    const forged = { ...game.snapshot(), hinted: game.blanks().slice(0, 12) };

    const second = createGame(puzzle);
    second.restore(forged);

    equal(second.record().hints, HINTS_PER_GAME, "a forged session bought extra hints");
  });

  test("⚠️ a hinted cell is painted in its own ink, not the player's", async () => {
    // The finished board has to show which cells were not deduced. Blue would claim work the player
    // did not do; black would hide the spend from the person looking at their own result.
    const { renderSection, columnsFor, totalNameFor } = await import("../ui/phone/board.js");
    const { battingCell } = await import("../engine/columns.js");
    const { game, puzzle } = await fresh();
    const hinted = game.blanks()[0];
    const typed = game.blanks().find((n) => n.startsWith("batting[") && n !== hinted);
    game.hint(hinted);
    game.enter(typed, game.cells().find((c) => c.name === typed).answer);

    const grid = renderSection({
      title: "x",
      columns: columnsFor.batting,
      rows: puzzle.puzzle.batting,
      labels: puzzle.labels,
      slots: puzzle.slotReferences,
      cellName: battingCell,
      totalName: totalNameFor.batting,
      game,
      onSelect: () => {},
    });
    document.getElementById("board").append(grid);
    const ink = (name) => getComputedStyle(grid.querySelector(`.cell[data-cell="${name}"]`)).color;

    assert(grid.querySelector(`.cell[data-cell="${hinted}"]`).classList.contains("hinted"));
    assert(!grid.querySelector(`.cell[data-cell="${typed}"]`).classList.contains("hinted"));
    assert(ink(hinted) !== ink(typed), `a hinted cell is the same colour as an entered one: ${ink(hinted)}`);

    grid.remove();
  });

  test("⚠️ clearing a hinted cell stops it being painted as hinted", async () => {
    // The class is derived on every repaint rather than set when the hint is spent. A class applied at
    // the moment of the hint would outlive the fact it describes.
    const { game } = await fresh();
    const name = game.blanks()[0];
    game.hint(name);
    game.enter(name, null);

    equal(game.value(name), null);
    // ⚠️ Still spent: the answer was seen. The allowance does not refund.
    equal(game.record().hints, 1, "clearing the cell refunded the hint");
  });
});

suite("⚠️ The reference sheet, which costs no hint", () => {
  test("it carries all five relations and the bounds", async () => {
    // ⚠️⚠️ **Five, and the printed strip on the hand-solve pack carries four.** That strip predates the
    // batting order, which is the one relation a player cannot infer from looking at a board. The gap
    // is recorded in todo.md; the pack must not move while it is being solved, and the screen has no
    // such constraint.
    const { renderReference } = await import("../ui/phone/finish.js");
    const panel = renderReference();
    const text = panel.textContent;

    for (const rule of ["PA = AB + BB + HBP + SF + SH + CI", "PA = Outs + Runs + LOB", "Outs = 3"]) {
      assert(text.includes(rule), `the sheet is missing ${rule}`);
    }
    // ⚠️ **Asserted on the family being present, not on the wording of its rule.** The batting-order
    // line has been rewritten twice — formula, worked example, and now the consequence a solver
    // actually applies — and a test pinned to a phrase turns every copy edit into a red suite while
    // proving nothing about the thing that matters: that the one family nobody can infer from a board
    // is on the sheet at all.
    const names = [...panel.querySelectorAll("dt")].map((dt) => dt.textContent);
    assert(names.includes("The batting order"), `the sheet is missing the batting order: ${names}`);
    assert(/AB \u2265 H|AB ≥ H/.test(text), "the sheet is missing the bounds");
    equal(panel.querySelectorAll("dt").length, panel.querySelectorAll("dd").length, "a rule with no name");
  });

  test("⚠️ opening it spends no hint and changes no cell", async () => {
    const { boot } = await import("../ui/phone/shell.js");
    const { readPackage } = await import("../engine/package.js");
    const { createStore } = await import("../engine/store.js");
    const puzzle = readPackage(packages[0].raw);
    const root = document.createElement("div");
    document.getElementById("board").append(root);
    const kept = new Map();
    const shell = boot({
      puzzle,
      root,
      store: createStore({
        getItem: (k) => kept.get(k) ?? null,
        setItem: (k, v) => kept.set(k, v),
        removeItem: (k) => kept.delete(k),
      }),
    });
    const before = shell.game.blanks().map((n) => shell.game.value(n)).join(",");

    root.querySelector(".reference-key").click();

    assert(root.querySelector(".reference"), "the reference button opened nothing");
    equal(shell.game.record().hints, 0, "opening the reference cost a hint");
    equal(shell.game.blanks().map((n) => shell.game.value(n)).join(","), before, "it changed the board");
    root.remove();
  });
});

suite("⚠️⚠️ The development test mode, and the four things that keep it away from a player", () => {
  const bootShell = async ({ session = null, fresh = false } = {}) => {
    const { boot } = await import("../ui/phone/shell.js");
    const { createStore } = await import("../engine/store.js");
    const { readPackage } = await import("../engine/package.js");
    const puzzle = readPackage(packages[0].raw);
    const root = document.createElement("div");
    document.getElementById("board").append(root);
    const kept = new Map();
    const store = createStore({
      getItem: (k) => kept.get(k) ?? null,
      setItem: (k, v) => kept.set(k, v),
      removeItem: (k) => kept.delete(k),
    });
    if (session) store.save(puzzle.id, session);
    // ⚠️ A `history` nothing navigates with. The mode drops the parameter from the address bar, and a
    // test that let it touch the real one would rewrite the suite's own URL.
    const wrote = [];
    const shell = boot({ puzzle, root, store, fresh });
    return {
      ...shell,
      puzzle,
      root,
      wrote,
      kept,
      location: { href: "http://x/ui/phone/index.html?p=1&test=reset" },
      history: { replaceState: (state, title, url) => wrote.push(url) },
      teardown: () => root.remove(),
    };
  };

  test("⚠️⚠️ an unrecognised mode does nothing at all", async () => {
    // **An acceptance list, never an exclusion.** The rule this project wrote down after a filter that
    // passed on absence: an unknown value must do nothing rather than fall into a default branch.
    const { applyTestMode } = await import("../ui/phone/testmode.js");
    const shell = await bootShell();
    const before = shell.game.blanks().map((n) => shell.game.value(n)).join(",");

    for (const mode of [null, undefined, "", "Fill", "solved ", "reset;fill", "__proto__", "true", "1"]) {
      equal(applyTestMode(mode, shell), null, `${JSON.stringify(mode)} was accepted as a mode`);
    }

    equal(shell.game.blanks().map((n) => shell.game.value(n)).join(","), before, "an unknown mode wrote to the board");
    equal(shell.game.record().assisted, false, "an unknown mode marked the game");
    equal(shell.wrote.length, 0, "an unknown mode touched the address bar");
    shell.teardown();
  });

  test("⚠️⚠️ nothing in the interface reaches it", async () => {
    // The mode has no control, no binding and no affordance. A board rendered normally must contain no
    // route to it — not a button, not a link, not a data attribute somebody could click.
    const shell = await bootShell();

    const suspicious = [...shell.root.querySelectorAll("*")].filter((node) =>
      /test|reset|fill|solved/i.test(node.className || "") || /\?test=/.test(node.getAttribute?.("href") ?? ""),
    );

    equal(suspicious.length, 0, `the board renders a route to the test mode: ${suspicious.map((n) => n.className)}`);
    shell.teardown();
  });

  test("⚠️⚠️ the entry point reaches it only inside the parameter's branch, and only dynamically", async () => {
    // ⚠️ **Read from the source, because this is a claim about reachability rather than behaviour.** A
    // top-level `import` would put the module in every page load, which is what the dynamic import
    // exists to prevent — and no assertion about a running page can see the difference.
    const source = await (await fetch("../ui/phone/main.js", { cache: "no-store" })).text();

    assert(!/^\s*import\b[^\n]*testmode/m.test(source), "main.js imports the test mode at the top level");
    // ⚠️ The essential property, not one exact spelling: every *import* of the module is guarded by
    // `mode`. Two earlier versions of this assertion were wrong in opposite directions — one pinned to
    // a single line and failed on a refactor that kept the property, the other scanned every line
    // naming the file and failed on the comment explaining the rule. Code lines that import it, and
    // nothing else.
    const imports = source
      .split("\n")
      .filter((line) => !line.trim().startsWith("//"))
      .filter((line) => /import\s*\(/.test(line) && /testmode/.test(line));
    equal(imports.length, 1, `expected one guarded import of the test mode, found ${imports.length}`);
    assert(
      /\bmode\b\s*\?/.test(imports[0]) || /if \(mode\)/.test(imports[0]),
      `the import is not behind the parameter: ${imports[0].trim()}`,
    );
    // And the parameter is read from the query string rather than from anything a page can set.
    assert(/URLSearchParams\(location\.search\)\.get\("test"\)/.test(source), "the switch is not the query parameter");
  });

  test("⚠️ fill writes through the keypad's own path, so it tests the real one", async () => {
    const { applyTestMode } = await import("../ui/phone/testmode.js");
    const shell = await bootShell();

    equal(applyTestMode("fill", shell), "fill");

    equal(shell.game.blanks().filter((n) => shell.game.value(n) === null).length, 0, "the board is not full");
    equal(shell.game.isSolved(), true);
    // ⚠️ Stopped short of finishing on purpose: the completion path is the thing most often being
    // tested, and a mode that pressed Check would remove it from reach.
    equal(shell.game.isFinished(), false, "fill finished the game");
    assert(shell.root.querySelector(".keypad"), "fill removed the keypad");
    assert(!shell.root.querySelector(".reveal"), "fill opened the reveal");
    equal(shell.game.record().errors, 0, "filling recorded mistakes");
    shell.teardown();
  });

  test("⚠️⚠️ anything it fills is marked, so the C7 record cannot claim a solve nobody did", async () => {
    // **The constraint that matters if this ever runs anywhere real.** A board filled from the
    // solution is, to the rest of the engine, a perfect instant solve.
    const { applyTestMode } = await import("../ui/phone/testmode.js");
    const shell = await bootShell();

    applyTestMode("solved", shell);

    equal(shell.game.record().assisted, true, "a pre-filled board reported itself as an ordinary solve");
    equal(shell.game.record().solved, true);
    shell.teardown();
  });

  test("⚠️ the mark survives the reload, so a reopen cannot launder the board", async () => {
    const { applyTestMode } = await import("../ui/phone/testmode.js");
    const first = await bootShell();
    applyTestMode("fill", first);
    const saved = first.store.load(first.puzzle.id);
    first.teardown();

    const second = await bootShell({ session: saved });

    equal(second.game.record().assisted, true, "the reopen laundered a pre-filled board");
    second.teardown();
  });

  test("⚠️ solved reaches the finished state through the shell's own Check handler", async () => {
    // Not `game.finish()`: the point is the finished *screen*, and that is everything the handler does.
    const { applyTestMode } = await import("../ui/phone/testmode.js");
    const shell = await bootShell();

    applyTestMode("solved", shell);

    assert(shell.root.querySelector(".reveal"), "solved did not open the boxscore");
    assert(!shell.root.querySelector(".keypad"), "solved left the keypad in place");
    assert(shell.root.querySelector(".again"), "solved left no way back to the boxscore");
    equal(shell.game.isFinished(), true);
    shell.teardown();
  });

  test("⚠️⚠️ a saved session does not survive a fresh boot, which is what every mode gets", async () => {
    // **The forgetting is `boot({ fresh })`, not something the mode does by hand.** What comes back has
    // to be a board booted the ordinary way that simply had nothing to restore, or *unplayed* would
    // have two definitions.
    //
    // ⚠️ The earlier design forgot the session and then navigated, and the outgoing page's `pagehide`
    // wrote it straight back. Nothing navigates now, which removes the race rather than working around
    // it — see the note on that listener in `shell.js`.
    const first = await bootShell();
    const name = first.game.blanks()[0];
    first.game.enter(name, first.game.cells().find((c) => c.name === name).answer);
    first.remember();
    const saved = first.store.load(first.puzzle.id);
    assert(saved, "nothing was saved to forget");
    first.teardown();

    const second = await bootShell({ session: saved, fresh: true });

    equal(second.store.load(second.puzzle.id), null, "a fresh boot left the session behind");
    assert(second.game.blanks().every((n) => second.game.value(n) === null), "a fresh boot restored entries");
    equal(second.game.record().assisted, false);
    second.teardown();
  });

  test("⚠️ every mode drops the parameter from the address bar without navigating", async () => {
    // A refresh should give a playable board, not the same test action again — and `reset` in
    // particular would otherwise wipe whatever had just been typed, on every pull-to-refresh.
    const { applyTestMode } = await import("../ui/phone/testmode.js");

    for (const mode of ["reset", "fill", "solved"]) {
      const shell = await bootShell({ fresh: true });
      applyTestMode(mode, shell);

      equal(shell.wrote.length, 1, `${mode} did not clean the address bar`);
      assert(!shell.wrote[0].includes("test="), `${mode} left the parameter on: ${shell.wrote[0]}`);
      assert(shell.wrote[0].includes("p=1"), `${mode} dropped the puzzle: ${shell.wrote[0]}`);
      shell.teardown();
    }
  });

  test("reset leaves an unplayed board and does nothing else", async () => {
    const { applyTestMode } = await import("../ui/phone/testmode.js");
    const shell = await bootShell({ fresh: true });

    equal(applyTestMode("reset", shell), "reset");

    assert(shell.game.blanks().every((n) => shell.game.value(n) === null), "reset wrote to the board");
    equal(shell.game.record().assisted, false, "reset marked a board it did not fill");
    assert(shell.root.querySelector(".keypad"), "reset left no keypad");
    shell.teardown();
  });
});

suite("⚠️⚠️ The shell itself, driven through the keypad it renders", () => {
  /**
   * **`boot()` from `shell.js`, not the pieces it uses.** The suite below this one asserts component
   * properties and used to be described as a shell test; nothing exercised the completion lifecycle
   * the shell owns — the pad going away, the board redrawn without selection, *See the boxscore*
   * taking its place, a restored session opening the reveal. v31-P2-01.
   *
   * The boundaries are all handed in: a detached root, a clock this test moves by hand, and a store
   * backed by an object so one case cannot see another's session.
   */
  const bootShell = async (raw, { session = null, now = { at: 7_000_000 } } = {}) => {
    const { boot } = await import("../ui/phone/shell.js");
    const { createClock } = await import("../engine/clock.js");
    const { createStore } = await import("../engine/store.js");
    const { readPackage } = await import("../engine/package.js");
    const puzzle = readPackage(raw);
    const root = document.createElement("div");
    document.getElementById("board").append(root);
    const kept = new Map();
    const store = createStore({
      getItem: (key) => kept.get(key) ?? null,
      setItem: (key, value) => kept.set(key, value),
      removeItem: (key) => kept.delete(key),
    });
    // ⚠️ **Seeded through the store's own `save`, never by writing a key this test invents.** The
    // first version keyed it `s.<id>`; the store keys it `boxscorepuzzle.session.v1.<id>`, so nothing
    // was ever restored and two cases failed on the fixture rather than on the shell. A test that
    // spells a key the code owns is a second copy of that key.
    if (session) store.save(puzzle.id, session);
    const shell = boot({ puzzle, root, store, clock: createClock({ now: () => now.at }) });
    return { ...shell, puzzle, root, now, kept, teardown: () => root.remove() };
  };

  /** Type one value the way a thumb does: pick the cell, clear it, press keys. */
  const type = (root, name, value) => {
    root.querySelector(`.cell[data-cell="${name}"]`).click();
    const keys = [...root.querySelectorAll(".keypad button")];
    keys[12].click();
    const digit = (d) => keys[d === 0 ? 9 : d - 1].click();
    if (name.startsWith("pitching") && name.endsWith(".outs")) {
      for (const d of String(Math.floor(value / 3))) digit(Number(d));
      if (value % 3) keys[9 + (value % 3)].click();
    } else {
      for (const d of String(value)) digit(Number(d));
    }
  };

  const fill = (shell, { wrongAt = null } = {}) => {
    const answers = new Map(shell.game.cells().map((cell) => [cell.name, cell.answer]));
    shell.game.blanks().forEach((name, index) => {
      type(shell.root, name, answers.get(name) + (index === wrongAt ? 1 : 0));
    });
  };

  const press = (root, selector) => root.querySelector(selector).click();

  test("⚠️ a live board offers a keypad and a Check key that is dead until the board is full", async () => {
    const shell = await bootShell(packages[0].raw);
    const check = shell.root.querySelector(".keypad button.check");

    equal(check.disabled, true, "Check was live on an empty board");
    fill(shell);
    equal(shell.root.querySelector(".keypad button.check").disabled, false, "Check stayed dead on a full board");

    shell.teardown();
  });

  test("⚠️⚠️ a wrong board keeps the pad, and the verdict names nothing", async () => {
    const shell = await bootShell(packages[0].raw);
    fill(shell, { wrongAt: 2 });

    press(shell.root, ".keypad button.check");

    const verdict = shell.root.querySelector(".verdict");
    equal(verdict.dataset.state, "wrong");
    equal(verdict.textContent, "Something doesn't add up yet.");
    assert(shell.root.querySelector(".keypad"), "a wrong board lost its keypad");
    assert(!shell.root.querySelector(".reveal"), "a wrong board opened the reveal");
    // ⚠️ The rule the whole ending exists to protect: no cell is named and no count is given.
    const wrongCell = shell.game.blanks()[2];
    assert(!verdict.textContent.includes(wrongCell.split(".")[1]), "the verdict named a column");
    assert(!/\d/.test(verdict.textContent), `the verdict carries a number: ${verdict.textContent}`);

    shell.teardown();
  });

  test("⚠️⚠️ finishing replaces the pad, kills the board, and opens the boxscore", async () => {
    // The whole lifecycle in one pass, through the real handlers.
    const shell = await bootShell(packages[0].raw);
    fill(shell);

    press(shell.root, ".keypad button.check");

    assert(shell.root.querySelector(".reveal"), "solving did not open the reveal");
    assert(!shell.root.querySelector(".keypad"), "the keypad survived the end of the game");
    assert(!shell.root.querySelector(".verdict"), "the verdict survived the end of the game");
    // ⚠️ **The reference stays and the verdict goes.** A finished board is still a boxscore somebody
    // may want to read the rules against, and the keypad that was the other route to them is gone.
    assert(shell.root.querySelector(".reference-key"), "a finished board lost the reference sheet");
    equal(shell.root.querySelector(".again")?.textContent, "See the boxscore");
    assert(shell.app.classList.contains("app-finished"), "the finished class was never applied");
    const cells = [...shell.root.querySelectorAll("td.cell")];
    equal(cells.filter((c) => c.getAttribute("role") === "button").length, 0, "cells are still controls");
    assert(!shell.root.querySelector(".cell.selected"), "a cell is still selected on a finished board");

    shell.teardown();
  });

  test("⚠️ closing the reveal and reopening it uses the frozen record, not a new reading", async () => {
    const shell = await bootShell(packages[0].raw);
    fill(shell);
    press(shell.root, ".keypad button.check");
    const first = shell.root.querySelector(".reveal-time-figure").textContent;

    press(shell.root, ".reveal-close");
    assert(!shell.root.querySelector(".reveal"), "the reveal did not close");
    // An hour of the page being open, then back to the boxscore.
    shell.now.at += 3_600_000;
    press(shell.root, ".again");

    equal(shell.root.querySelector(".reveal-time-figure").textContent, first, "the shared time moved");

    shell.teardown();
  });

  // -------------------------------------------------------------------------------------------
  // v34-P2-01. `role="dialog"` with `aria-modal="true"` is a promise to assistive technology that
  // everything behind the panel is unavailable. Nothing was keeping it: the board kept its tab stops,
  // the opener kept focus behind the overlay, and a second activation appended a second dialog.
  //
  // ⚠️ **These assert the DOM facts the attribute claims**, not the attribute. A test that checked for
  // `aria-modal="true"` would have passed on every version of this code, including the broken one.
  // -------------------------------------------------------------------------------------------

  test("⚠️ opening a panel moves focus into it and takes the board out of reach", async () => {
    const shell = await bootShell(packages[0].raw);

    press(shell.root, ".reference-key");
    const opened = shell.root.querySelector(".reference");

    assert(opened.contains(document.activeElement), "focus stayed behind the panel it opened");
    equal(document.activeElement.className, "reveal-close", "focus did not land on an actionable control");
    const behind = [...shell.root.children].filter((child) => child !== opened);
    assert(behind.length > 0, "nothing was behind the panel, so this proves nothing");
    assert(behind.every((child) => child.inert), "the board behind the modal is still focusable");

    shell.teardown();
  });

  test("⚠️⚠️ activating the opener again cannot stack a second dialog", async () => {
    const shell = await bootShell(packages[0].raw);

    press(shell.root, ".reference-key");
    // The exact failure: the opener kept focus behind the overlay, so a keyboard user pressing Enter
    // twice appended two panels and closing one left the other.
    press(shell.root, ".reference-key");

    equal(shell.root.querySelectorAll(".reference").length, 1, "a second dialog was appended over the first");

    shell.teardown();
  });

  test("⚠️ closing a panel restores focus to whatever opened it", async () => {
    const shell = await bootShell(packages[0].raw);
    const opener = shell.root.querySelector(".reference-key");

    opener.click();
    press(shell.root, ".reveal-close");

    assert(!shell.root.querySelector(".reference"), "the panel did not close");
    // ⚠️ `assert(a === b)`, not `equal(a, b)`: every DOM node stringifies to `{}`, so the `equal` form
    // of this line passed against a build with the focus restoration deleted. See `harness.js`.
    assert(document.activeElement === opener, "focus did not return to the opener");
    assert([...shell.root.children].every((child) => !child.inert), "the board is still inert after closing");

    shell.teardown();
  });

  test("⚠️ Escape closes a panel, and closes exactly one", async () => {
    const shell = await bootShell(packages[0].raw);
    const opener = shell.root.querySelector(".reference-key");

    opener.click();
    shell.root
      .querySelector(".reference")
      .dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));

    assert(!shell.root.querySelector(".reference"), "Escape did not close the panel");
    assert(document.activeElement === opener, "Escape closed the panel without restoring focus");

    shell.teardown();
  });

  test("⚠️⚠️ the reveal after Check takes focus, whose opener no longer exists", async () => {
    // The complementary failure, and the one with no opener to return to: `rebuildChrome()` removes
    // *Check* before the reveal is appended, so a keyboard user arrived at the payoff holding nothing.
    const shell = await bootShell(packages[0].raw);
    fill(shell);

    press(shell.root, ".keypad button.check");

    const reveal = shell.root.querySelector(".reveal");
    assert(reveal.contains(document.activeElement), "the reveal opened without taking focus");
    assert(!shell.root.querySelector(".keypad button.check"), "Check survived completion, so this is not that path");

    press(shell.root, ".reveal-close");
    equal(document.activeElement.className, "again", "closing left focus nowhere; the opener was gone");

    shell.teardown();
  });

  test("⚠️⚠️ a restored finished session opens finished, with no pad and no way to type", async () => {
    // The ordinary reopen, which is the path persistence exists for and the one that used to hand back
    // an editable board and a running clock.
    const first = await bootShell(packages[0].raw);
    fill(first);
    press(first.root, ".keypad button.check");
    const earned = first.root.querySelector(".reveal-time-figure").textContent;
    const saved = first.store.load(first.puzzle.id);
    first.teardown();

    const second = await bootShell(packages[0].raw, { session: saved, now: { at: 9_000_000 } });

    assert(second.root.querySelector(".reveal"), "a finished session reopened without its boxscore");
    equal(second.root.querySelector(".reveal-time-figure").textContent, earned, "the restored time is not the earned one");
    assert(!second.root.querySelector(".keypad"), "a finished session came back with a keypad");
    equal(second.game.isFinished(), true);
    equal(second.clock.isSealed(), true, "the restored clock was not sealed");

    second.teardown();
  });

  test("⚠️ an unfinished session comes back playable, which is the case the others could hide", async () => {
    // The control. Every assertion above is about a board that has stopped; a shell that refused to
    // build a keypad at all would pass all of them.
    const first = await bootShell(packages[0].raw);
    const name = first.game.blanks()[0];
    type(first.root, name, first.game.cells().find((c) => c.name === name).answer);
    const saved = first.store.load(first.puzzle.id);
    first.teardown();

    const second = await bootShell(packages[0].raw, { session: saved });

    equal(second.game.isFinished(), false);
    assert(second.root.querySelector(".keypad"), "a half-played session came back without a keypad");
    assert(!second.root.querySelector(".reveal"), "a half-played session opened the reveal");
    equal(second.game.value(name), first.game.cells().find((c) => c.name === name).answer, "the entry was lost");

    second.teardown();
  });
});

suite("⚠️ The finished board is a record, not a surface", () => {
  /**
   * **Components, assembled here.** ⚠️ This said *"boot the real shell against a package, solve it
   * through the keypad"* and did neither: it calls `createGame`, `renderSection` and `renderKeypad`
   * itself and never touches the shell. The assertions below are worth having and none of them is
   * evidence about the completion lifecycle. That is the suite above, which drives `boot()`.
   */
  const played = async (index = 0, { solve = true } = {}) => {
    const { readPackage } = await import("../engine/package.js");
    const { createGame } = await import("../engine/game.js");
    const { renderSection, renderKeypad, columnsFor, totalNameFor } = await import("../ui/phone/board.js");
    const { battingCell, pitchingCell } = await import("../engine/columns.js");
    const puzzle = readPackage(packages[index].raw);
    const game = createGame(puzzle);
    if (solve) {
      const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
      for (const name of game.blanks()) game.enter(name, answers.get(name));
      game.check();
      game.finish();
    }
    return { puzzle, game, renderSection, renderKeypad, columnsFor, totalNameFor, battingCell, pitchingCell };
  };

  const section = (parts, onSelect) =>
    parts.renderSection({
      title: "x",
      columns: parts.columnsFor.batting,
      rows: parts.puzzle.puzzle.batting,
      labels: parts.puzzle.labels,
      slots: parts.puzzle.slotReferences,
      cellName: parts.battingCell,
      totalName: parts.totalNameFor.batting,
      game: parts.game,
      onSelect,
    });

  test("⚠️⚠️ a cell drawn without a selector is not a control in any sense", async () => {
    // **Dead, not disabled.** A cell that keeps `role="button"` and a tab stop announces itself as
    // pressable to everything that is not a pair of eyes, and a screen reader offering to press a cell
    // that cannot change is worse than one that does not offer. So the handler, the role and the tab
    // stop all go together.
    const parts = await played();
    const live = section(parts, () => {});
    const done = section(parts, null);

    const controls = (grid) => [...grid.querySelectorAll("td.cell")].filter((c) => c.getAttribute("role") === "button");
    assert(controls(live).length > 0, "the live board has no reachable cells, so this proves nothing");
    equal(controls(done).length, 0, "a finished board still offers cells as buttons");
    equal([...done.querySelectorAll("td.cell")].filter((c) => c.tabIndex === 0).length, 0, "cells kept a tab stop");
  });

  test("⚠️ a click on a finished cell changes nothing, because there is nothing listening", async () => {
    // ⚠️ **The reason this matters is the clock, not tidiness.** §26 shares the finished duration; a
    // board that still accepts entries either runs a clock under a number already reported or stops it
    // arbitrarily, and both make the shared time mean nothing.
    const parts = await played();
    const done = section(parts, null);
    const before = parts.game.blanks().map((name) => parts.game.value(name)).join(",");
    const cell = done.querySelector("td.cell.blank");

    cell.click();
    cell.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));

    equal(parts.game.blanks().map((name) => parts.game.value(name)).join(","), before, "a finished board took an entry");
    assert(!done.querySelector(".cell.selected"), "a finished board selected a cell");
  });

  test("⚠️ what the player deduced stays blue", async () => {
    // The record of their own work is what going back to the board is for. If everything turns the
    // givens' colour on completion, the board stops being theirs at the moment it became worth keeping.
    const parts = await played();
    const done = section(parts, null);
    const filled = [...done.querySelectorAll("td.cell.filled")];

    assert(filled.length > 0, "no cell is marked as filled on a solved board");
    // ⚠️ The section draws the totals row too, and its blanks live in `batting_totals` rather than in
    // `batting`. Counting only the grid made this fail on its own arithmetic: 31 against 28.
    const blanks = [...parts.puzzle.puzzle.batting.flat(), ...parts.puzzle.puzzle.battingTotals];
    equal(filled.length, blanks.filter((v) => v === null).length, "not every blank the player filled is blue");
  });

  test("⚠️ the finished duration does not move again, whatever the page does", async () => {
    const { createClock } = await import("../engine/clock.js");
    const { readPackage } = await import("../engine/package.js");
    const { createGame } = await import("../engine/game.js");
    let now = 5_000_000;
    const clock = createClock({ now: () => now });
    const game = createGame(readPackage(packages[0].raw), clock);
    clock.run();
    now += 120_000;
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    for (const name of game.blanks()) game.enter(name, answers.get(name));
    const earned = game.finish().duration_ms;

    clock.run();
    now += 3_600_000;

    equal(game.record().duration_ms, earned, "an hour of the page being open joined the shared time");
    equal(clock.isRunning(), false);
  });

  test("the keypad is still built for a board that is being played", async () => {
    // ⚠️ The control. Every assertion above is about absence, and a suite of absences passes against a
    // shell that renders nothing at all.
    const parts = await played(0, { solve: false });
    const pad = parts.renderKeypad(() => {}, () => {});

    assert(pad.querySelectorAll("button").length >= 13, "the keypad lost its keys");
    assert(pad.querySelector("button.check"), "the keypad has no Check key");
    equal(parts.game.isFinished(), false, "the unsolved fixture came back finished");
  });
});

suite("⚠️ The reveal is a printed boxscore, not the board with names attached", () => {
  const finished = async (raw) => {
    const { createGame } = await import("../engine/game.js");
    const { readPackage } = await import("../engine/package.js");
    const { renderReveal } = await import("../ui/phone/finish.js");
    const puzzle = readPackage(raw);
    const game = createGame(puzzle);
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    for (const name of game.blanks()) game.enter(name, answers.get(name));
    return { puzzle, panel: renderReveal(puzzle, game.finish()) };
  };

  /** The clubs in printing order — visitor first, which is what a line score and a boxscore both use. */
  const sides = (puzzle) => {
    const box = puzzle.reveal.boxscore;
    return puzzle.offenseIsHome
      ? { visitor: box.defense, home: box.offense }
      : { visitor: box.offense, home: box.defense };
  };

  const grids = (panel) => [...panel.querySelectorAll(".clipping-batting")];

  test("⚠⚠ every cell carries a value, because it draws the solution and not the puzzle", async () => {
    // ⚠⚠ **An early version drew `puzzle.puzzle`, which is the board with its blanks.** The finished
    // boxscore printed `null` in every cell the player had just filled and every pitcher's innings
    // read `0.0`. Nothing threw and the panel looked structurally right; only reading the rendered
    // text showed it. This asserts the content of the grid rather than its shape.
    for (const { raw } of packages) {
      const { panel } = await finished(raw);

      for (const cell of panel.querySelectorAll(".clipping-grid td")) {
        assert(cell.textContent.trim().length > 0, "an empty cell in the finished boxscore");
        assert(!cell.textContent.includes("null"), `a null in the finished boxscore: ${cell.textContent}`);
        assert(!cell.textContent.includes("undefined"), `an undefined: ${cell.textContent}`);
      }
    }
  });

  test("⚠️ both clubs are printed, which is what makes it a boxscore rather than a legend", async () => {
    // The whole point of schema 5. A single batting grid is the board relabelled; two is a boxscore.
    for (const { raw } of packages) {
      const { puzzle, panel } = await finished(raw);
      const { visitor, home } = sides(puzzle);

      equal(grids(panel).length, 2, "the reveal does not print both clubs");
      // ⚠️ Visitor first, and asserted against `offenseIsHome` rather than against the package's field
      // order. The package stores offence and defence; the printing order is visitor and home, and
      // assuming the two coincide is how the board once claimed the batting team was away.
      const [first, second] = grids(panel).map((g) => g.querySelector(".clipping-team").textContent);
      assert(first.includes(visitor.city), `${first} is not the visiting club`);
      assert(second.includes(home.city), `${second} is not the home club`);
    }
  });

  test("⚠️ the clubs are named in full, never by their three-letter key", async () => {
    for (const { raw } of packages) {
      const { puzzle, panel } = await finished(raw);
      const { visitor } = sides(puzzle);
      const heading = panel.querySelector(".clipping-head").textContent;

      assert(heading.includes(`${visitor.city} ${visitor.nickname}`), `no club name in ${heading}`);
      // The code belongs on the line score, where 52px is all there is, and nowhere else.
      const named = panel.querySelector(".clipping-batting .clipping-team").textContent;
      assert(!named.includes(visitor.code), `the batting grid is headed by a code: ${named}`);
    }
  });

  test("⚠️ the winner is named first, which is not the same as the visitor being first", async () => {
    for (const { raw } of packages) {
      const { puzzle, panel } = await finished(raw);
      const score = puzzle.solution.lineScore;
      const box = puzzle.reveal.boxscore;
      const winner = score.offense_runs > score.defense_runs ? box.offense : box.defense;
      const heading = panel.querySelector(".clipping-head").textContent;

      assert(heading.startsWith(`${winner.city} ${winner.nickname}`), `${heading} does not lead with the winner`);
      assert(heading.includes(String(Math.max(score.offense_runs, score.defense_runs))), `no score in ${heading}`);
    }
  });

  test("the date reads as a date rather than as a field", async () => {
    const { puzzle, panel } = await finished(packages[0].raw);
    const printed = panel.querySelector(".clipping-date").textContent;

    assert(!printed.includes(puzzle.reveal.playedOn), `the reveal prints the ISO date: ${printed}`);
    assert(printed.includes(puzzle.reveal.playedOn.slice(0, 4)), `no year in ${printed}`);
  });

  test("⚠️ the line score is labelled with the clubs, drawn by the board's own renderer", async () => {
    // ⚠️ A *parameter* of `renderLineScore`, never a copy of it: a comparison page written with its
    // own grid twice showed something other than what it was evaluating. During play the rows say
    // AWAY and HOME because the player has no clubs; here they say which clubs.
    for (const { raw } of packages) {
      const { puzzle, panel } = await finished(raw);
      const labels = [...panel.querySelectorAll(".linescore td.side")].map((c) => c.textContent);
      const { visitor, home } = sides(puzzle);

      equal(labels, [visitor.code, home.code], "the reveal's line score is not labelled with the clubs");
    }
  });

  test("⚠️ runs batted in are shown — the one column the board never asked for", async () => {
    // The reason the reveal is worth drawing at all: it tells the player something instead of
    // repeating what they worked out. If this heading goes missing the reveal is a summary again.
    const { puzzle, panel } = await finished(packages[0].raw);
    // Scoped to one grid: the selector without a scope matches the header row of both clubs and
    // returns twelve headings, which is a test failing on its own selector rather than on the code.
    const headings = [...grids(panel)[0].querySelectorAll("tr:first-child th")].map((c) => c.textContent);

    equal(headings.slice(1), ["AB", "R", "H", "RBI", "BB", "SO"]);
    assert(!headings.includes("PA"), "PA is a board column and belongs on no boxscore");
    // And it carries real values, not a column of zeros.
    const rbi = puzzle.reveal.boxscore.offense.batting.reduce((sum, row) => sum + row.rbi, 0);
    assert(rbi > 0, "the fixture cannot show this: nobody drove in a run");
  });

  test("both grids carry every row of their club and a totals line", async () => {
    const { puzzle, panel } = await finished(packages[0].raw);
    const { visitor, home } = sides(puzzle);

    // Header, one row per player, totals.
    equal(grids(panel)[0].querySelectorAll("tr").length, visitor.batting.length + 2);
    equal(grids(panel)[1].querySelectorAll("tr").length, home.batting.length + 2);
    equal(panel.querySelectorAll(".clipping-batting .clipping-totals").length, 2);
  });

  test("⚠️ the totals are the sum of the rows printed above them", async () => {
    // ⚠️ **The one place in this product where summing from the rows is right, and it is worth saying
    // why.** A total loaded from the rows it verifies verifies nothing — that defect is on the record.
    // Here there is nothing to verify: the package's totals cover six board columns for one club, and
    // this grid has RBI and a club the board never carried. So the test computes it the same way the
    // renderer does, which makes it a check that the arithmetic ran rather than a check of the source.
    for (const { raw } of packages) {
      const { puzzle, panel } = await finished(raw);
      const { visitor } = sides(puzzle);
      const totals = [...grids(panel)[0].querySelectorAll(".clipping-totals td")]
        .slice(1)
        .map((cell) => Number(cell.textContent));
      const columns = ["ab", "r", "h", "rbi", "bb", "so"];

      equal(
        totals,
        columns.map((column) => visitor.batting.reduce((sum, row) => sum + row[column], 0)),
      );
    }
  });

  test("⚠️ the batting totals still agree with the line score, which is an independent source", async () => {
    // The check that would catch a fabricated half. `offense.batting` is verified against the board on
    // the forge; the *other* club's is verified nowhere — and the line score, which comes from the
    // game table rather than from these rows, is the one thing here that can speak about it.
    for (const { raw } of packages) {
      const { puzzle } = await finished(raw);
      const score = puzzle.solution.lineScore;
      const box = puzzle.reveal.boxscore;

      equal(box.offense.batting.reduce((sum, row) => sum + row.r, 0), score.offense_runs, "offensive runs");
      equal(box.offense.batting.reduce((sum, row) => sum + row.h, 0), score.offense_hits, "offensive hits");
      equal(box.defense.batting.reduce((sum, row) => sum + row.r, 0), score.defense_runs, "defensive runs");
      equal(box.defense.batting.reduce((sum, row) => sum + row.h, 0), score.defense_hits, "defensive hits");
    }
  });

  test("both clubs' pitchers are in one block, grouped and headed", async () => {
    const { puzzle, panel } = await finished(packages[0].raw);
    const { visitor, home } = sides(puzzle);
    const block = panel.querySelector(".clipping-pitching");
    const clubs = [...block.querySelectorAll(".clipping-club th")].map((c) => c.textContent);

    equal(clubs, [`${visitor.city} ${visitor.nickname}`, `${home.city} ${home.nickname}`]);
    // Every pitcher of both clubs, and no totals row — a total across two clubs counts half-innings.
    equal(
      block.querySelectorAll("tr").length - 1 - clubs.length,
      visitor.pitching.length + home.pitching.length,
    );
    assert(!block.querySelector(".clipping-totals"), "a totals row across two clubs means nothing");
  });

  test("the innings column prints thirds rather than outs", async () => {
    const { puzzle, panel } = await finished(packages[0].raw);
    const first = panel.querySelector(".clipping-pitching tr:nth-child(3) td:nth-child(2)");
    const { visitor } = sides(puzzle);
    const outs = visitor.pitching[0].outs;

    // ⚠️ Against the shared conversion, not against a third copy of the formula. This re-implemented
    // it, so it agreed with `finish.js`'s hand-written version rather than with the definition — the
    // harness supplying the property under test, in miniature.
    equal(first.textContent, inningsToDisplay(outs, INNINGS.PRINTED));
  });

  test("⚠️ each row carries the name the player earned and the position they solved against", async () => {
    // Both, not the name alone: the player spent the game thinking of that row as `cf`, and a list of
    // names with no positions cannot be mapped onto the board they just filled.
    const { puzzle, panel } = await finished(packages[0].raw);
    const { visitor } = sides(puzzle);
    const first = panel.querySelector(".clipping-batting tr:nth-child(2) .clipping-who").textContent;

    assert(first.includes(visitor.batting[0].name), `no name in "${first}"`);
    // ⚠️ `label`, not `position`. The package says `position` for a batter and `role` for a
    // pitcher; the reader maps both to one name so the renderer draws one kind of row. Reading the
    // package's spelling here got `undefined`, which is the snake_case bug in miniature.
    assert(first.includes(visitor.batting[0].label.toLowerCase()), `no position in "${first}"`);
  });

  test("⚠️ the footnote line names its club, because the package carries one club's footnotes", async () => {
    // The other club has its own and no package holds them. An unprefixed line would read as a
    // statement about both and be silently false about one — a label sitting outside the arithmetic.
    const { puzzle, panel } = await finished(packages[0].raw);
    const notes = panel.querySelector(".clipping-notes").textContent;
    const offense = puzzle.reveal.boxscore.offense;

    assert(notes.startsWith(`${offense.city} ${offense.nickname}`), `the footnotes name no club: ${notes}`);
    assert(notes.includes(puzzle.solution.leftOnBase.toString()), "LOB is missing from the footnotes");
    assert(!notes.includes("#"), `the reveal still prints a slot reference: ${notes}`);
  });

  test("⚠️ the footnote carriers are named, not numbered", async () => {
    // During play the line says `SH: 1 #2` because the player has no names. Here they do, and a
    // printed boxscore wrote `Sacrifice hit—Shotton`. The slot reference existed to point at a row
    // without naming anyone, and that reason is gone at this point.
    const withFootnote = packages.find(({ raw }) =>
      raw.solution.footnotes.some((row) => row.some((value) => value > 0)),
    );
    assert(withFootnote, "no reference package carries a live footnote; this test cannot fire");
    const { puzzle, panel } = await finished(withFootnote.raw);
    const notes = panel.querySelector(".clipping-notes").textContent;
    const carrier = puzzle.reveal.boxscore.offense.batting[
      puzzle.solution.footnotes.findIndex((row) => row.some((value) => value > 0))
    ];

    assert(notes.includes(carrier.name), `${carrier.name} carries a footnote and is not named: ${notes}`);
  });

  test("⚠⚠ the mistake count is not shown", async () => {
    // Dropped deliberately: it was never decided in `serve-flow.md`, and a number quantifying failure
    // sits badly beside §27's rule that you cannot lose. It stays in the C7 record, where it is a
    // measurement rather than a message.
    const { createGame } = await import("../engine/game.js");
    const { readPackage } = await import("../engine/package.js");
    const { renderReveal } = await import("../ui/phone/finish.js");
    const puzzle = readPackage(packages[0].raw);
    const game = createGame(puzzle);
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    const blanks = game.blanks();
    // ⚠️ **Filled wrong, checked, then fixed and checked again**, because *check* is where an entry
    // becomes an answer. Entering a wrong value and correcting it without ever asking is not a mistake
    // the game saw, so a test that only entered would now record nothing and prove nothing.
    for (const name of blanks) game.enter(name, answers.get(name) + (blanks.indexOf(name) < 3 ? 1 : 0));
    equal(game.check().state, "wrong", "the fixture did not produce a wrong board");
    for (const name of blanks) game.enter(name, answers.get(name));
    equal(game.check().state, "solved");
    const record = game.finish();
    const panel = renderReveal(puzzle, record);

    equal(record.errors, 3, "the event record lost the mistakes");
    assert(!panel.querySelector(".reveal-errors"), "the reveal shows a mistake count");
    assert(!panel.textContent.includes("3 mistakes"), "the reveal counts mistakes");
  });

  test("a duration renders as minutes and seconds, and past an hour gains one", async () => {
    const { formatDuration } = await import("../ui/phone/finish.js");

    equal(formatDuration(0), "0:00");
    equal(formatDuration(9_000), "0:09");
    equal(formatDuration(62_000), "1:02");
    equal(formatDuration(3_600_000), "1:00:00");
    equal(formatDuration(3_661_000), "1:01:01");
  });
});

suite("The landing page, which every visit lands on", () => {
  const mount = async (raw, { session = null, today = new Date("2026-08-21T12:00:00") } = {}) => {
    const { renderLanding } = await import("../ui/phone/landing.js");
    const { createStore } = await import("../engine/store.js");
    const { readPackage } = await import("../engine/package.js");
    const puzzle = readPackage(raw);
    const root = document.createElement("div");
    document.getElementById("board").append(root);
    const kept = new Map();
    const store = createStore({
      getItem: (key) => kept.get(key) ?? null,
      setItem: (key, value) => kept.set(key, value),
      removeItem: (key) => kept.delete(key),
    });
    if (session) store.save(puzzle.id, session);
    const went = [];
    const view = renderLanding({ puzzle, root, store, today, go: (href) => went.push(href) });
    return { ...view, root, puzzle, went, teardown: () => root.remove() };
  };

  /** A finished session for this package: every blank correct, and the clock frozen. */
  const solvedSession = async (raw) => {
    const { createGame } = await import("../engine/game.js");
    const { readPackage } = await import("../engine/package.js");
    const game = createGame(readPackage(raw));
    for (const cell of game.cells()) {
      if (game.isBlank(cell.name)) game.enter(cell.name, cell.answer);
    }
    // ⚠️ `finish()`, not `check()`. `check()` returns a verdict and records mistakes; **`finish()` is
    // what stops the clock and sets `finishedAt`**, which is the only thing `isFinished()` reads. The
    // first version of this fixture called `check()` and produced a snapshot of a solved board that
    // was not a finished one — a fixture that looks like the state under test and is not it.
    game.check();
    game.finish();
    return game.snapshot();
  };

  test("it says what this is and what it is not, and shows a board", async () => {
    const view = await mount(packages[0].raw);

    assert(view.page.querySelector(".landing-name").textContent.length > 0, "the product is not named");
    assert(view.page.querySelector(".landing-tagline").textContent.length > 0, "no tagline");
    // ⚠️ Its own line, and asserted separately. The first thing a visitor assumes about a baseball
    // puzzle is that it asks what they know; every screen after this depends on them arriving without
    // that idea, and it is the line between this and Immaculate Grid.
    assert(view.page.querySelector(".landing-not-trivia").textContent.length > 0, "nothing says it is not trivia");
    assert(view.page.querySelector(".landing-how"), "there is no way to the tutorial");

    view.teardown();
  });

  test("⚠️ the example is drawn by the board's own renderers, not by a copy", async () => {
    // A hand-drawn imitation would drift the first time the board changed and nothing would notice —
    // the page advertising the product would quietly stop showing it. This asserts the real thing was
    // used, which is what makes drift impossible rather than merely unlikely.
    const view = await mount(packages[0].raw);
    const example = view.page.querySelector(".landing-example");

    assert(example.querySelector(".linescore table"), "the scoreboard is not the board's line score");
    assert(example.querySelector("table.grid"), "the grid is not the board's section");
    assert(example.querySelectorAll("td.cell.blank").length > 0, "the example has no holes in it");

    view.teardown();
  });

  test("⚠️ nothing in the example is a control", async () => {
    // The cells are drawn with `onSelect` null, which is the same rule a finished board follows: an
    // example a screen reader offers to press is a promise this page cannot keep.
    const view = await mount(packages[0].raw);
    const example = view.page.querySelector(".landing-example");

    equal(example.querySelectorAll('[role="button"]').length, 0, "the example offers cells as buttons");
    equal(example.querySelectorAll("[tabindex]").length, 0, "the example is in the tab order");
    equal(example.getAttribute("aria-hidden"), "true", "the example is read out cell by cell before the button");

    view.teardown();
  });

  test("the way in carries today's date, and goes to the board", async () => {
    const view = await mount(packages[0].raw);

    assert(view.play.querySelector(".landing-date").textContent.includes("2026"), "the button has no date");
    view.play.click();
    equal(view.went.length, 1, "the button went nowhere");
    assert(view.went[0].startsWith("play.html"), `the button did not go to the board: ${view.went[0]}`);

    view.teardown();
  });

  test("⚠️⚠️ a finished day is offered as a boxscore to read, never as a puzzle to solve", async () => {
    // Without this the product offers a returning player a puzzle they already solved, every day,
    // which reads as it not knowing who they are.
    const fresh = await mount(packages[0].raw);
    const label = fresh.play.textContent;
    fresh.teardown();

    const done = await mount(packages[0].raw, { session: await solvedSession(packages[0].raw) });

    assert(done.finished, "the landing page did not notice a finished session");
    assert(done.play.textContent !== label, "the button says the same thing whether or not today is done");
    assert(done.page.querySelector(".landing-done"), "a finished day shows no result");
    assert(done.page.querySelector(".landing-done-time").textContent.includes(":"), "no time is shown");

    done.teardown();
  });

  test("⚠️ whether the day is finished is asked of the engine, not read off the snapshot", async () => {
    // A landing page that interpreted the saved shape itself would be a second copy of `isFinished()`,
    // on the one screen where being wrong means offering a solved puzzle as new. A snapshot that is
    // *not* finished must render as *play* even though a session exists.
    const { createGame } = await import("../engine/game.js");
    const { readPackage } = await import("../engine/package.js");
    const game = createGame(readPackage(packages[0].raw));
    const [first] = game.blanks();
    game.enter(first, 1);

    const view = await mount(packages[0].raw, { session: game.snapshot() });

    assert(!view.finished, "an unfinished session was treated as a finished day");
    assert(!view.page.querySelector(".landing-done"), "an unfinished session showed a result");

    view.teardown();
  });

  test("a landing page whose storage throws still offers the puzzle (§23)", async () => {
    const { renderLanding } = await import("../ui/phone/landing.js");
    const { createStore } = await import("../engine/store.js");
    const { readPackage } = await import("../engine/package.js");
    const hostile = {
      getItem() { throw new Error("no storage"); },
      setItem() { throw new Error("no storage"); },
      removeItem() { throw new Error("no storage"); },
    };
    const root = document.createElement("div");
    document.getElementById("board").append(root);

    const view = renderLanding({ puzzle: readPackage(packages[0].raw), root, store: createStore(hostile) });

    assert(view.play, "a storage failure took the way in with it");
    root.remove();
  });

  test("⚠️ the slot the archive and the streak land in is present and empty", async () => {
    // C8, C9, C10: the shape is present before the feature is, so adding them is an append rather than
    // a redesign of the one page every visit passes through. Do not delete as unused.
    const view = await mount(packages[0].raw);

    assert(view.later, "the reserved slot is gone");
    equal(view.later.childElementCount, 0, "something moved into the reserved slot without a decision");

    view.teardown();
  });
});

suite("The tutorial: five steps, skippable, and teaching on a board that adds up", () => {
  const mount = async ({ start = 0 } = {}) => {
    const { renderTutorial } = await import("../ui/phone/tutorial.js");
    const root = document.createElement("div");
    document.getElementById("board").append(root);
    const went = [];
    const view = renderTutorial({ root, start, go: (href) => went.push(href) });
    return { ...view, root, went, teardown: () => root.remove() };
  };

  /**
   * Every number the tutorial has drawn, by cell name, read back out of the DOM.
   *
   * ⚠️ **The pitching cell is innings and is parsed as outs, with the board's own parser.** Reading it
   * as a plain number made `2` mean two, and the global identity then failed by four — which is
   * exactly what a player would experience, and is how the missing *an inning is three outs* sentence
   * was found. `inningsFromDisplay` rather than a local conversion: a test that re-implements the rule
   * it is checking agrees with itself.
   */
  const shown = (view) => {
    const values = {};
    for (const cell of view.page.querySelectorAll(".tcell")) {
      const raw = cell.textContent;
      if (raw === "") values[cell.dataset.cell] = null;
      else values[cell.dataset.cell] = cell.dataset.cell === "p.outs" ? inningsFromDisplay(raw) : Number(raw);
    }
    return values;
  };

  test("it is five steps, it says which one, and the skip is a real control", async () => {
    const view = await mount();

    equal(view.total, 5, "the tutorial no longer has one step per relation family");
    assert(view.page.querySelector(".tutorial-progress").textContent.length > 0, "the step is not numbered");
    // ⚠️ Present and visible. §1b: a skip the visitor has to hunt for is a compulsory tutorial wearing
    // a disguise, which is the rule the reversal removed.
    assert(view.skip && !view.skip.hidden, "the skip is missing or hidden");
    assert(view.page.querySelector(".tutorial-made-up").textContent.length > 0, "nobody says the board is invented");
    assert(!view.page.querySelector(".tutorial-made-up").hidden, "the first step does not say the board is invented");

    view.teardown();
  });

  test("⚠️ the board is called made-up once, not on all five steps", async () => {
    // It is a caveat about the board rather than part of any relation, and five repetitions teach the
    // eye to skip the line above the board — which is where each step's own sentence lives.
    //
    // ⚠️ **Both halves.** Removing it outright is the other reading and it is wrong while no first
    // screen exists to carry it: a four-batter, three-column board is visibly not a boxscore, and a
    // player who is not told spends a step deciding whether the tutorial is broken.
    for (const step of [1, 2, 3, 4]) {
      const view = await mount({ start: step });
      assert(
        view.page.querySelector(".tutorial-made-up").hidden,
        `step ${step + 1} repeats the made-up caveat`,
      );
      view.teardown();
    }
  });

  test("⚠️ the batting order is taught last", async () => {
    // The other four are visible in the grid. Nothing on screen announces that turns are dealt around
    // the lineup, so it needs the most setup and gets the player who has seen four relations work.
    const view = await mount({ start: 4 });

    equal(view.page.querySelector(".tutorial-title").textContent, "The batting order", "the order changed");

    view.teardown();
  });

  test("⚠️⚠️ the made-up board satisfies all five relations, on the numbers it actually draws", async () => {
    // **The test that matters.** A tutorial teaching arithmetic that does not hold is the worst defect
    // available here, and no screenshot catches a subtle one — the board looks exactly as convincing
    // either way. Read out of the DOM at the last step, where every hole has been filled.
    const view = await mount({ start: 5 });
    const v = shown(view);

    for (const row of [0, 1, 2, 3]) {
      equal(
        v[`b${row}.plate_appearances`],
        v[`b${row}.at_bats`] + v[`b${row}.walks`],
        `row ${row + 1}: PA is not AB + BB`,
      );
    }
    for (const column of ["plate_appearances", "at_bats", "walks"]) {
      const sum = [0, 1, 2, 3].reduce((total, row) => total + v[`b${row}.${column}`], 0);
      equal(v[`t.${column}`], sum, `the ${column} total is not the sum of the rows`);
    }
    equal(v["t.walks"], v["p.walks"], "the walks the batters drew are not the walks the pitcher gave");
    equal(
      v["t.plate_appearances"],
      v["p.outs"] + v["p.runs"] + v.lob,
      "PA is not outs + runs + left on base",
    );
    for (const row of [1, 2, 3]) {
      assert(
        v[`b${row}.plate_appearances`] <= v[`b${row - 1}.plate_appearances`],
        `slot ${row + 1} batted more often than slot ${row}, which the order forbids`,
      );
    }

    view.teardown();
  });

  test("⚠️⚠️ left on base is a value on every step, never a hole", async () => {
    // **§6: the footnote line is given, complete, and never erased** — `erasable()` excludes LOB and
    // every per-batter footnote cell from every board this product publishes.
    //
    // It was the fourth step's hole, so a new player's first screens showed LOB as an empty box
    // indistinguishable from an editable cell, and one whole step deduced a number that always arrives
    // with its value. **A tutorial that teaches the opposite of the game is worse than no tutorial**,
    // and this was on the first screen anybody sees.
    for (let step = 0; step <= 5; step += 1) {
      const view = await mount({ start: step });
      const value = shown(view).lob;

      assert(value !== null && value !== undefined, `step ${step + 1} draws LOB as a blank`);
      view.teardown();
    }
  });

  test("⚠️ every hole on the board is filled by exactly one step", async () => {
    // A hole no step explains leaves a player at the end of the wizard with an incomplete board,
    // concluding they missed something. Read out of the DOM rather than off the STEPS list — the list
    // is what would be wrong.
    const blanksAt = [];
    for (let step = 0; step <= 5; step += 1) {
      const view = await mount({ start: step });
      const values = shown(view);

      assert(Object.keys(values).length > 0, `step ${step + 1} drew no cells at all`);
      blanksAt.push(new Set(Object.keys(values).filter((name) => values[name] === null)));
      view.teardown();
    }

    equal(blanksAt[5].size, 0, "the finished board still has a hole in it");
    for (let step = 0; step < 5; step += 1) {
      const filled = [...blanksAt[step]].filter((name) => !blanksAt[step + 1].has(name));
      equal(filled.length, 1, `step ${step + 1} fills ${filled.length} cells rather than exactly one`);
    }
  });

  test("⚠️ a cell given in one step is never a hole in a later one", async () => {
    // The board has to stay consistent across the five or it teaches that the relations are unrelated
    // tricks. This is the failure the second step was rewritten to avoid: the column sum was taught
    // over PA, which shows all four plate-appearance cells as facts, and step five then turned one of
    // them back into an unknown.
    const givenSoFar = new Set();
    for (let step = 0; step < 5; step += 1) {
      const view = await mount({ start: step });
      const values = shown(view);
      const hole = Object.keys(values).find((name) => values[name] === null);

      assert(hole !== undefined, `step ${step + 1} has no hole at all`);
      assert(!givenSoFar.has(hole), `step ${step + 1} makes a hole of ${hole}, which an earlier step gave`);
      for (const [name, value] of Object.entries(values)) {
        if (value !== null) givenSoFar.add(name);
      }
      view.teardown();
    }
  });

  test("the last screen hands over the reference sheet, then the puzzle", async () => {
    const view = await mount({ start: 5 });

    // So the player leaves knowing the button exists: a sheet nobody has been shown is a sheet nobody
    // opens, and it is what made skipping this safe.
    equal(view.page.querySelectorAll(".tutorial-reference dt").length, 5, "the five relations are not listed");
    view.next.click();
    equal(view.went.length, 1, "the last button went nowhere");
    assert(view.went[0].startsWith("play.html"), `it did not lead to the board: ${view.went[0]}`);

    view.teardown();
  });

  test("skip leaves for the landing page rather than the board", async () => {
    const view = await mount();

    view.skip.click();

    equal(view.went.length, 1, "skip went nowhere");
    assert(view.went[0].startsWith("index.html"), `skip did not return to the landing: ${view.went[0]}`);
    view.teardown();
  });

  test("⚠️ Back on the first step leaves, rather than doing nothing", async () => {
    // A disabled Back on step one is a dead control; the honest meaning of *back* there is *out*.
    const view = await mount();

    view.back.click();

    equal(view.went.length, 1, "Back on the first step did nothing at all");
    assert(view.went[0].startsWith("index.html"), `Back did not return to the landing: ${view.went[0]}`);
    view.teardown();
  });

  test("⚠️⚠️ the tutorial persists nothing and fetches nothing", async () => {
    // Every piece of machinery here sits on the path between a stranger and their first board.
    // Remembering step 3 needs storage, a key, an identity to key it by and a staleness rule — all
    // spent on a visitor who has not yet seen a puzzle. Asserted against the source, because the
    // absence of a feature is exactly what a behavioural test cannot see.
    const source = await (await fetch("../ui/phone/tutorial.js")).text();
    const entry = await (await fetch("../ui/phone/tutorial-main.js")).text();

    for (const forbidden of ["localStorage", "sessionStorage", "createStore", "fetch("]) {
      assert(!source.includes(forbidden), `the tutorial reached for ${forbidden}`);
      assert(!entry.includes(forbidden), `the tutorial's entry point reached for ${forbidden}`);
    }
  });
});

suite("⚠️ The boundary checks the pointer too, and a finished board is immutable in the engine", () => {
  test("a malformed manifest is refused by name, not by TypeError", async () => {
    // v36-P3-23. The package gets rigorous validation and the pointer selecting it got none: a bad
    // manifest died on `.includes`, and an empty `puzzles` array fetched `.../undefined.json` and
    // failed inside `.json()`. Both entry points catch and show `package.unreadable`, so the player
    // outcome survived — while the console carried an unrelated error and **the page misdiagnosed its
    // own failure**, the same shape as a storage error reported as an unreadable puzzle.
    const { readManifest } = await import("../ui/phone/daily.js");

    for (const [raw, because] of [
      [null, "null"],
      [[], "an array"],
      [{ puzzles: ["a"] }, "no generation"],
      [{ generation: "", puzzles: ["a"] }, "an empty generation"],
      [{ generation: "g" }, "no puzzles"],
      [{ generation: "g", puzzles: [] }, "an empty puzzle list"],
      [{ generation: "g", puzzles: [1] }, "an id that is not a string"],
    ]) {
      const error = throws(() => readManifest(raw), /manifest/, `accepted ${because}`);
      assert(error instanceof PackageError, `${because}: refused with ${error.constructor.name}`);
    }
  });

  test("the real manifest still reads", async () => {
    // ⚠️ The other half: a check that refuses everything is as useless as one that refuses nothing.
    const { readManifest } = await import("../ui/phone/daily.js");
    const raw = await (await fetch("../data/puzzles/manifest.json")).json();

    assert(readManifest(raw) === raw, "the shipped manifest is refused by its own reader");
  });

  test("⚠️ a date that is not a date is refused at the boundary, not inside the reveal", () => {
    // v36-P3-24. `played_on` was checked as "a string", so `"yesterday"` parsed and `longDate` then
    // computed `month.NaN` and threw **inside renderReveal** — in `check()`'s success path, on the one
    // screen the player reaches once, after they have solved the board.
    for (const bad of ["yesterday", "1913-13-01", "1913-08-32", "13-08-1913", "1913-8-1", ""]) {
      const document = structuredClone(packages[0].raw);
      document.reveal.played_on = bad;
      throws(() => readPackage(document), /played_on/, `accepted ${JSON.stringify(bad)}`);
    }
    // And a real one still passes.
    assert(readPackage(packages[0].raw).reveal.playedOn.length === 10);
  });

  test("⚠️ a card that is not text is refused even though nothing reads it", () => {
    // v36-P3-25. A field with no consumer is exactly where a pass-through waits: there is no test to
    // go red first, which is the story `reveal()`'s own header tells about `raw.reveal` one field up.
    for (const bad of [{}, [], 7, true]) {
      const document = structuredClone(packages[0].raw);
      document.reveal.card = bad;
      throws(() => readPackage(document), /card/, `accepted ${JSON.stringify(bad)}`);
    }
  });

  test("⚠️⚠️ a finished board refuses entries, clears and hints in the engine", async () => {
    // v36-P3-26. The clock was sealed *in the engine* because "sealing is a fact about the clock
    // rather than a promise every future shell has to keep" — and the board's immutability got the
    // opposite treatment: only the phone layer removed the handlers. `__game.enter(...)` from a
    // console changed a finished board, the next visibility-save persisted it under the frozen
    // `finishedAt`, and `record().solved` could flip on a result already reported.
    const { createGame } = await import("../engine/game.js");
    const { readPackage: read } = await import("../engine/package.js");
    const game = createGame(read(packages[0].raw));
    const [first] = game.blanks();
    for (const cell of game.cells()) {
      if (game.isBlank(cell.name)) game.enter(cell.name, cell.answer);
    }
    game.check();
    game.finish();

    throws(() => game.enter(first, 1), /finished/, "a finished board took an entry");
    throws(() => game.clear(first), /finished/, "a finished board took a clear");
    throws(() => game.hint(first), /finished/, "a finished board gave a hint");
    assert(game.record().solved, "the record changed under the refusals");
  });

  test("⚠️ restore installs nothing into a given cell", async () => {
    // v36-P3-27. `restore()` filtered on the cell existing, not on it being blank, so a hand-edited
    // session's junk entry on a given cell survived every snapshot round trip — harmless while
    // `valueOf` prefers the given, and waiting for the first consumer that reads `entries` directly.
    const { createGame } = await import("../engine/game.js");
    const { readPackage: read } = await import("../engine/package.js");
    const puzzle = read(packages[0].raw);
    const game = createGame(puzzle);
    const given = game.cells().find((cell) => !game.isBlank(cell.name));

    assert(given !== undefined, "this package has no given cells, so it proves nothing");
    game.restore({ entries: { [given.name]: 999 }, hinted: [], elapsed: 0 });

    equal(game.snapshot().entries[given.name], undefined, "a given cell kept an entry from a session");
  });
});

suite("⚠️⚠️ A given cell may not contradict the answer", () => {
  // v36-P2-08. `isSolved()` walks every cell, givens included, so one wrong given makes it
  // permanently false: *Check* answers "Something doesn't add up yet" for ever on a board where every
  // blank the player owes is correct. The board gives no per-cell feedback by design, so the player
  // cannot find it — an unwinnable day that renders perfectly.
  //
  // ⚠️ It is also the cheapest tamper available. The client verifies no signature by design (§23), so
  // one edited byte in a static file bricks a day for everyone. A refusal here makes that a visible
  // failure instead of a silent one.
  const tampered = (raw, mutate) => {
    const copy = structuredClone(raw);
    mutate(copy);
    return copy;
  };

  test("a grid cell that disagrees with the solution is refused", () => {
    const document = tampered(packages[0].raw, (copy) => {
      const row = copy.puzzle.batting.findIndex((cells) => cells.some((value) => value !== null));
      const column = copy.puzzle.batting[row].findIndex((value) => value !== null);
      copy.puzzle.batting[row][column] = copy.solution.batting[row][column] + 1;
    });

    throws(() => readPackage(document), "the solution says");
  });

  test("a totals cell that disagrees with the solution is refused", () => {
    const document = tampered(packages[0].raw, (copy) => {
      const column = copy.puzzle.pitching_totals.findIndex((value) => value !== null);
      copy.puzzle.pitching_totals[column] = copy.solution.pitching_totals[column] + 1;
    });

    throws(() => readPackage(document), "the solution says");
  });

  test("left on base is never erased, so a disagreement there is malformed", () => {
    const document = tampered(packages[0].raw, (copy) => {
      copy.puzzle.left_on_base = copy.solution.left_on_base + 1;
    });

    throws(() => readPackage(document), "left_on_base");
  });

  test("⚠️ a blank is not a disagreement, and every real package still reads", () => {
    // The other half: the check must not refuse the erasure it exists alongside. Every published
    // package is full of nulls where the solution has numbers, and all of them must still open.
    for (const { id, raw } of packages) {
      const puzzle = readPackage(raw);
      assert(puzzle.puzzle.batting.flat().includes(null), `${id} has no blanks, so it proves nothing`);
    }
  });
});

suite("⚠️⚠️ One conversion, two notations — and no file spells the arithmetic twice", () => {
  const MIRRORS = ["board.js", "finish.js", "shell.js", "landing.js", "tutorial.js", "testmode.js"];
  const ENGINE = ["game.js", "clock.js", "store.js", "package.js", "strings.js"];

  /**
   * Statements that turn outs into innings, or innings back into outs, themselves.
   *
   * ⚠️ **The shape, not a spelling.** What the five copies had in common was dividing something by
   * three *and* taking its remainder by three — `f"{outs // 3}.{outs % 3}"` in four of them and
   * `` `${Math.floor(outs / 3)}.${outs % 3}` `` in the fifth. A scan for one literal template would
   * have missed a rewrite that kept the defect. A lone `% 3` is ordinary arithmetic and is spared.
   *
   * ⚠️ **`* 3` counts as the division's partner**, because the keypad's inverse spells the same
   * representation the other way round: `Math.floor(current / 3) * 3 + key.thirds`. Nobody hunting for
   * copies of a formatter finds the parser, which is how that one survived four reviews.
   */
  const convertsItself = (line) => {
    if (line.trim().startsWith("//") || line.trim().startsWith("*")) return false;
    const divides = /\/\s*3\b/.test(line);
    const partners = /%\s*3\b/.test(line) || /\*\s*3\b/.test(line);
    return divides && partners;
  };

  test("the arithmetic lives in columns.js and nowhere else", async () => {
    // ⚠️ The mirror of `forge/tests/test_one_innings_conversion.py`, which cannot see this tree: §33
    // keeps `serve/` and `forge/` sharing no code, so the conversion exists twice by necessity and is
    // held to the same values by `package-vectors.json`. Two guards, named in each other's docstrings.
    const offenders = [];
    for (const file of MIRRORS) {
      const source = await (await fetch(`../ui/phone/${file}`)).text();
      source.split("\n").forEach((line, index) => {
        if (convertsItself(line)) offenders.push(`ui/phone/${file}:${index + 1}  ${line.trim()}`);
      });
    }
    for (const file of ENGINE) {
      const source = await (await fetch(`../engine/${file}`)).text();
      source.split("\n").forEach((line, index) => {
        if (convertsItself(line)) offenders.push(`engine/${file}:${index + 1}  ${line.trim()}`);
      });
    }

    assert(
      offenders.length === 0,
      "the outs-to-innings arithmetic is spelled outside columns.js again:\n  " + offenders.join("\n  "),
    );
  });

  test("⚠️ the scan catches the copies that existed, and spares what it must", () => {
    // Both halves. The first three are the real lines that were in the tree; the rest are ordinary
    // code that a wider scan would have condemned, and a guard that cries wolf gets switched off.
    for (const copy of [
      "const inningsOf = (outs) => `${Math.floor(outs / 3)}.${outs % 3}`;",
      "    game.enter(name, Math.floor(current / 3) * 3 + key.thirds);",
      "    game.enter(name, grow(Math.floor(current / 3), key.digit) * 3 + (current % 3));",
    ]) {
      assert(convertsItself(copy), `the scan would not have caught: ${copy}`);
    }

    for (const innocent of [
      "      equal(outs % 3, 0, `${id} staff pitched`);",
      "  const whole = Math.floor(outs / 3);",
      "  const share = division / total;",
      "  const rung = value * 3;",
      "  // const inningsOf = (outs) => `${Math.floor(outs / 3)}.${outs % 3}`;",
    ]) {
      assert(!convertsItself(innocent), `false positive on: ${innocent}`);
    }
  });

  // ⚠️ **What the player meets is asserted in the two places that can reach it**, rather than a third
  // time here: the reveal's own test compares its cell against `inningsToDisplay(outs, PRINTED)`, and
  // the innings suite pins both notations across the range. A copy here would have needed this suite
  // to borrow another one's fixtures, which is how a test ends up agreeing with a helper.
});

suite("⚠️⚠️ C11 over what the player actually reads, not over what the catalogue holds", () => {
  const UI = ["board.js", "finish.js", "shell.js", "landing.js", "tutorial.js", "main.js",
              "landing-main.js", "tutorial-main.js", "testmode.js", "daily.js"];

  /**
   * The words a line writes onto the screen without going through the catalogue.
   *
   * ⚠️ **Catalogue calls are removed first, then what is left is examined.** The first version scanned
   * the raw right-hand side and reported every key — `text("landing.name")` looks exactly like copy to
   * a regular expression, because the key *is* letters in quotes. A guard that fires on the correct
   * case as loudly as on the defect is one that gets switched off.
   *
   * ⚠️ **One definition, used by the scan and by the test of the scan.** The check below asserts this
   * function catches the real defect and spares the real code; written twice, the two would drift and
   * the confirmation would be about a function nobody runs.
   */
  const spelledOut = (line) => {
    if (line.trim().startsWith("//") || line.trim().startsWith("*")) return [];
    const assignment = /\.textContent\s*=\s*(.+)$/.exec(line);
    if (assignment === null) return [];
    const rhs = assignment[1]
      // ⚠️ Interpolated expressions are code, not copy. `${batter.slot}` inside a template is an
      // identifier, and leaving them in made every template in the tree look like English.
      .replace(/\$\{[^}]*\}/g, "")
      // A catalogue key is letters in quotes and looks exactly like copy to a regular expression.
      .replace(/\b(?:text|fill)\(\s*(?:"[^"]*"|'[^']*'|`[^`]*`)/g, "KEY(");

    const quoted = [...rhs.matchAll(/"([^"]*)"|'([^']*)'|`([^`]*)`/g)]
      .flatMap(([, a, b, c]) => [a, b, c])
      .filter((one) => one !== undefined && /[A-Za-z]/.test(one));

    // ⚠️⚠️ **Two shapes, and the narrowing is a decision that has to be stated rather than tuned in.**
    // A bare word in quotes is usually a domain identifier being compared — `column === "outs"` is the
    // real line that made the first version cry wolf, and `outs` there is a column key, not copy. What
    // is copy is either a **phrase** (letters with a space between them) or a literal that **is** the
    // whole right-hand side, which is a sentence being assigned however short it is.
    //
    // ⚠️ This is a heuristic and is written down as one. It would miss a single bare word smuggled
    // through a ternary — `x ? "Close" : y`. The alternative was a scan that fires on every comparison
    // in the file, and **a check that fires when nothing is wrong gets switched off**, which is worse
    // than a narrow one that holds. The catalogue tests cover the other direction.
    const whole = rhs.trim().replace(/;$/, "");
    return quoted.filter(
      (one) => /[A-Za-z]\s+\S/.test(one) || whole === `"${one}"` || whole === `'${one}'` || whole === `\`${one}\``,
    );
  };

  test("no string with letters in it is written straight onto the screen", async () => {
    // ⚠️⚠️ **The existing C11 tests check the catalogue; this checks the code.** They assert every
    // column has a heading and that a replacement catalogue changes what renders — both true while a
    // renderer spells its own copy beside them. v36-P2-09 was exactly that: the tutorial's worked
    // arithmetic went on screen at 19px bold and one line read `2 innings = 6 outs` in a source file,
    // in a project where C11 is mandatory from day one and Spanish is the reason it exists.
    //
    // The rule matches the seam's own words — **if a player can read it, it is in the catalogue** — so
    // what is forbidden is a literal with letters reaching `textContent`. A literal with none (`""`,
    // `":"`, `"#"`) is punctuation rather than language and has nothing to translate.
    const offenders = [];
    for (const file of UI) {
      const source = await (await fetch(`../ui/phone/${file}`)).text();
      source.split("\n").forEach((line, index) => {
        for (const word of spelledOut(line)) offenders.push(`${file}:${index + 1}  ${word}`);
      });
    }

    assert(
      offenders.length === 0,
      `player-visible words spelled in code instead of the catalogue:\n  ${offenders.join("\n  ")}`,
    );
  });

  const PAGES = ["index.html", "play.html", "tutorial.html"];

  /**
   * ⚠️⚠️ **The seam's blind spot was a file extension.**
   *
   * Every C11 guard above reads `.js`, and all three shipped pages carried
   * `<title>boxscore</title>` — hardcoded, identical, and a fourth copy of a string that was already
   * in the catalogue (v36-P2-17). Nothing fired, because markup is not code to a scan that reads
   * code. The `<title>` is the most player-visible string there is: tab, history, bookmark, and the
   * headline of every search result.
   *
   * The elements checked are the ones that carry copy. `<meta charset>`, `viewport` and `lang` carry
   * identifiers rather than language and are not translated — `lang` in particular **must** be in the
   * markup, because a crawler and a screen reader need it before any script runs.
   */
  const copyInMarkup = (source) =>
    [
      ...[...source.matchAll(/<title>([^<]*)<\/title>/gi)].map(([, one]) => `<title>${one}`),
      ...[...source.matchAll(/<meta\s+name="(description|og:[a-z:]+)"[^>]*content="([^"]+)"/gi)].map(
        ([, name, one]) => `<meta ${name}>${one}`,
      ),
      ...[...source.matchAll(/(?:aria-label|placeholder|alt|title)="([^"]*[A-Za-z]\s+\S[^"]*)"/gi)].map(
        ([, one]) => `attribute: ${one}`,
      ),
    ].filter((one) => /[A-Za-z]/.test(one.split(">").slice(1).join(">") || one));

  test("no shipped page spells a player-visible string in its markup", async () => {
    const offenders = [];
    for (const page of PAGES) {
      const source = await (await fetch(`../ui/phone/${page}`)).text();
      for (const one of copyInMarkup(source)) offenders.push(`${page}  ${one}`);
    }

    assert(
      offenders.length === 0,
      `player-visible words spelled in markup instead of the catalogue:\n  ${offenders.join("\n  ")}`,
    );
  });

  test("⚠️ the markup scan catches the defect it was written for, and spares what belongs there", () => {
    // The exact line all three pages carried, and the exact lines they still carry.
    equal(copyInMarkup("<title>boxscore</title>").length, 1);
    equal(copyInMarkup('<meta name="description" content="Rebuild a real boxscore.">').length, 1);
    equal(copyInMarkup('<img alt="A finished boxscore sheet">').length, 1);

    // ⚠️ The other half, and the half that decides whether this guard survives: a scan that fires on
    // `<html lang="en">` or the viewport would be switched off within a week, and `lang` is required
    // to be in the markup by the same reasoning that took the title out of it.
    equal(
      copyInMarkup(
        [
          "<!doctype html>",
          '<html lang="en">',
          '<meta charset="utf-8">',
          '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
          '<link rel="stylesheet" href="tokens.css">',
          '<div id="landing"></div>',
        ].join("\n"),
      ).length,
      0,
    );
  });

  test("every shipped page declares a language, and it is the catalogue's", async () => {
    for (const page of PAGES) {
      const source = await (await fetch(`../ui/phone/${page}`)).text();
      assert(/<html lang="en">/.test(source), `${page} has no lang attribute (v36-P3-46)`);
    }
    equal(text("catalog.lang"), "en");
  });

  test("⚠️ the scan catches the defect it was written for, and spares the code around it", async () => {
    // A guard that finds nothing looks exactly like a broken one, and this one is a regular expression
    // over source — the instrument this project has been burned by twice, both times for matching the
    // wrong thing. Both halves are asserted, and the second is the one that matters: every version of
    // this scan that was wrong was wrong by matching too much.
    equal(
      spelledOut('    sum.textContent = finished ? "" : "2 innings = 6 outs";').join("|"),
      "2 innings = 6 outs",
      "the scan would not have caught the string it was written for",
    );
    equal(
      spelledOut('    close.textContent = "Close";').join("|"),
      "Close",
      "a whole-right-hand-side sentence escaped the scan",
    );

    for (const innocent of [
      '    cell.textContent = "";',
      // The line that made the first version cry wolf: a column key in a comparison, not copy.
      '    cell.textContent = innings && column === "outs" ? inningsOf(row[column]) : String(row[column]);',
      '    name.textContent = text("landing.name");',
      '    cell.textContent = text(`printed.${column}`);',
      "    slot.textContent = `${text(\"board.slot\")}${batter.slot}`;",
      '    next.textContent = finished ? text("tutorial.finish") : text("tutorial.next");',
      '    cell.textContent = printed(name) ?? String(valueOf[name]());',
      '    // message.textContent = "a commented-out literal";',
    ]) {
      equal(spelledOut(innocent).length, 0, `false positive on: ${innocent}`);
    }
  });
});

suite("⚠️ Storage is acquired the one safe way, on every entry point", () => {
  test("⚠️⚠️ no entry point reads the global localStorage directly", async () => {
    // v35-P2-01. `createStore` guards `getItem`, `setItem` and `removeItem`; it cannot guard the
    // property access that produces the object, and **reading `window.localStorage` throws outright**
    // in a browser with storage denied. `browserStorage()` exists for that — its `try` wraps the
    // access — and the landing page, the new default entry, went straight to the global instead.
    //
    // ⚠️ Written over every entry point rather than over the one that was wrong. A guard naming
    // `landing-main.js` has to be written again for the next page, and there are three now.
    for (const file of ["main.js", "landing-main.js", "tutorial-main.js"]) {
      const source = await (await fetch(`../ui/phone/${file}`)).text();
      const code = source
        .split("\n")
        .filter((line) => !line.trim().startsWith("*") && !line.trim().startsWith("//"));

      for (const line of code) {
        assert(
          !/\blocalStorage\b/.test(line) || /browserStorage/.test(line),
          `${file} reaches for the global localStorage: ${line.trim()}`,
        );
      }
    }
  });

  test("the landing page renders on the storage a denied browser gets", async () => {
    // What `browserStorage()` answers with when the access throws: accepts everything, remembers
    // nothing. The page must be whole on it — §23 keeps the play path free of backend dependencies,
    // and the way in is the whole of this page.
    const { renderLanding } = await import("../ui/phone/landing.js");
    const { createStore } = await import("../engine/store.js");
    const { readPackage } = await import("../engine/package.js");
    const forgetful = { getItem: () => null, setItem: () => {}, removeItem: () => {} };
    const root = document.createElement("div");
    document.getElementById("board").append(root);

    const view = renderLanding({ puzzle: readPackage(packages[0].raw), root, store: createStore(forgetful) });

    assert(view.play, "the way in is missing when nothing can be remembered");
    assert(view.how, "the way to the tutorial is missing when nothing can be remembered");
    assert(!view.finished, "a storage that remembers nothing reported a finished day");
    root.remove();
  });
});

suite("⚠️ Every page agrees on where the other pages are", () => {
  test("no navigation target is spelled by hand", async () => {
    // A page that spells a sibling's filename is a link that breaks silently when the file is renamed:
    // the browser shows a 404 and no test is watching. Three pages now link to each other.
    const { ROUTES } = await import("../ui/phone/daily.js");
    const known = new Set(Object.values(ROUTES));

    for (const file of ["landing.js", "tutorial.js"]) {
      const source = await (await fetch(`../ui/phone/${file}`)).text();
      const spelled = [...source.matchAll(/["'`]([\w-]+\.html)["'`]/g)].map((match) => match[1]);
      for (const target of spelled) {
        assert(known.has(target), `${file} spells ${target} by hand instead of using ROUTES`);
      }
    }
  });

  test("the pages that ROUTES names all exist", async () => {
    const { ROUTES } = await import("../ui/phone/daily.js");

    for (const [name, file] of Object.entries(ROUTES)) {
      const response = await fetch(`../ui/phone/${file}`);
      assert(response.ok, `ROUTES.${name} points at ${file}, which is not served`);
    }
  });
});
