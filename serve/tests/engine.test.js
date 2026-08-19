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

  test("the C7 record carries every field, including the ones not yet computed", () => {
    const game = createGame(puzzle, () => 1000);
    const record = game.record(4000);
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
  // count, so a row carrying two of one term could not be expressed. 10,207 of 373,917 admissible
  // directions carry such a row — 2.73%, and 5.25% in the 1910s. Those boards cannot be solved, and
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
