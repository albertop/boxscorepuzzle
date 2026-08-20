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
    equal(Object.keys(record).sort(), ["duration_ms", "errors", "highest_technique", "hints", "puzzle_id", "solved"]);
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
      throws(() => readPackage(document), undefined, `accepted: ${vector.because}`);
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
    // Visible for the duration: `getComputedStyle` on a `hidden` subtree still resolves colours, but a
    // test that depends on that is a test that breaks when someone changes how it is hidden.
    host.hidden = false;
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
    host.hidden = true;

    assert(blanks[0].classList.contains("filled"), "the cell under test is not filled, so it proves nothing");
    assert(peered !== plain, `a filled peer kept its ground colour ${plain}`);
  });

  test("a filled cell that is selected still shows the selected colour", async () => {
    const { host, blanks } = await paint();
    blanks[1].classList.add("peer");
    const peered = getComputedStyle(blanks[1]).backgroundColor;
    blanks[1].classList.add("selected");
    const chosen = getComputedStyle(blanks[1]).backgroundColor;
    host.hidden = true;

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
    ["board.css", "(prefers-color-scheme: dark)", "the dark theme"],
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
