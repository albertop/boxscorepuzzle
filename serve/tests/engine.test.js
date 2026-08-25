/**
 * The engine, driven against **the packages actually on the public path** rather than fixtures.
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
import { CATALOGS, fill, keys, text, useCatalog } from "../engine/strings.js";
import { assert, equal, suite, test, throws } from "./harness.js";

const MANIFEST = "../data/puzzles/manifest.json";

/**
 * Every package on the public path. **Two since E1, and it was six.**
 *
 * ⚠️⚠️ **The suite was driven against whatever happened to be served, and what was served was wrong.**
 * `serve/data/puzzles` held six signed packages; `docs/calendar.md` allows **two**, today's and
 * yesterday's. Nothing had escaped — there is no VPS yet — but the tree the browser reads is the one
 * the access model is about, and it was the model inverted.
 *
 * **So the count dropped when the tree was corrected, and that is not a coverage regression to work
 * around.** A suite asserting properties over six public packages was asserting them over an inventory
 * that may not exist. Where variety is genuinely needed the boards below are built rather than drawn:
 * a fixture that is a real signed package *is* a puzzle, and four of them in the deployed tree is four
 * puzzles nobody may have.
 *
 * ⚠️ The manifest is flat now — `{schema, puzzles}` with no generation, written by `publish.rotate`
 * from the files it actually placed. The public path holds `<id>.json`; `<generation>/<id>.json` is the
 * private inventory's shape and never travels.
 */
async function loadAll() {
  // ⚠️ `no-store`, for the reason the phone loader carries in full: a cached pointer serves yesterday's
  // board after the rotation has run, which is indistinguishable from a rotation that did not run.
  const manifest = await (await fetch(MANIFEST, { cache: "no-store" })).json();
  const loaded = [];
  for (const id of manifest.puzzles) {
    const raw = await (await fetch(`../data/puzzles/${id}.json`)).json();
    loaded.push({ id, raw });
  }
  return loaded;
}

const packages = await loadAll();

/**
 * Run `body` and answer with whatever escaped from a listener, instead of letting it reach the page.
 *
 * ⚠⚠ **This exists because "assert it does not throw" is not a test in a browser.** An exception
 * thrown inside a DOM listener does **not** propagate out of `click()` or `dispatchEvent()`: it is
 * reported to the window as an uncaught error and the caller carries on. So a case that presses a
 * button and then asserts something stays green whatever the handler did — and a mutation run proved
 * it, by making two "never throws" guards escape while both cases still passed.
 *
 * What actually caught them was `run_browser_tests.py`, which treats any page error as fatal. That is
 * a real signal and a poor one to rely on: **the whole suite dies with no named failure**, so the
 * report says nothing about which guard broke. This catches the escape, marks it handled so the run
 * survives, and hands it back to be asserted on by name.
 */
const escapingFrom = async (body) => {
  const escaped = [];
  const onError = (event) => {
    escaped.push(String(event.error?.message ?? event.message));
    // Marks the error handled, so playwright does not see a page error and kill the run.
    event.preventDefault();
  };
  window.addEventListener("error", onError);
  try {
    body();
    // The error event is delivered as a task, so a microtask turn is not enough to see it.
    await new Promise((resolve) => setTimeout(resolve, 0));
  } finally {
    window.removeEventListener("error", onError);
  }
  return escaped;
};

// Loaded here rather than inside the suite: `suite()` takes a synchronous callback, and top-level await
// is what this module already uses for the packages themselves.
const vectors = await (await fetch("./package-vectors.json", { cache: "no-store" })).json();
const vectors_footnote = await (await fetch("./footnote-line-vectors.json", { cache: "no-store" })).json();

suite("The public packages parse, and their shape is the contract", () => {
  test("there are six of them and each carries a distinct id", () => {
    // ⚠️⚠️ **Two, and the number is asserted rather than left to whatever is there.** `docs/calendar.md`:
    // today's and yesterday's are public and everything else is on no public path at all. A suite that
    // accepted any count would pass on the six-package tree this replaced — and on a rotation that had
    // silently stopped deleting, which is the failure that leaks the archive one day at a time.
    assert(packages.length === 2, `the public path holds ${packages.length} packages, and two may be`);
    equal(new Set(packages.map((p) => p.id)).size, 2, "two puzzles share an id");
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


  test("⚠️⚠️ a line score clue that contradicts the answer is refused", () => {
    // v39-P2-02. Both halves were parsed, independently and correctly, and then never compared — the
    // two-places-that-should-agree shape, inside the function whose whole job is checking that they do.
    //
    // ⚠️ The line score is the board's anchor and is never erased (§6), so there is no *blank* case to
    // allow: every value is a given. One edited digit made a valid daily arithmetically impossible
    // while the checker went on grading against the untouched solution — a board nobody can solve,
    // refusing every correct answer, with nothing to say anything was wrong.
    const raw = good();
    raw.puzzle.line_score.offense_runs += 1;
    throws(() => readPackage(raw), "line_score.offense_runs");
  });

  test("⚠️ an edited inning is refused, and so is a truncated one", () => {
    const perInning = good();
    perInning.puzzle.line_score.offense_by_inning[0] += 1;
    throws(() => readPackage(perInning), "offense_by_inning\\[0\\]");

    // ⚠️ **Length before values.** Comparing element by element over a short array agrees about every
    // inning it has and says nothing about the ones it does not — a check that passes on a truncation.
    const short = good();
    short.puzzle.line_score.defense_by_inning = short.puzzle.line_score.defense_by_inning.slice(0, 4);
    throws(() => readPackage(short), "defense_by_inning has 4 innings");
  });

  test("⚠️ every line score scalar is compared, not a sample of them", () => {
    // A comparison that covers most fields reads exactly like one that covers all of them, and the
    // uncovered one is where an edit lands unnoticed.
    for (const field of ["offense_runs", "offense_hits", "offense_errors", "defense_runs", "defense_hits", "defense_errors"]) {
      const raw = good();
      raw.puzzle.line_score[field] += 1;
      throws(() => readPackage(raw), `line_score.${field}`, `${field} is not compared against the solution`);
    }
  });

  test("⚠️⚠️ a package with no reveal is refused rather than opened", () => {
    // v39-P2-02. From schema 5 the reveal is the complete boxscore the finished screen draws, and the
    // publication gate will not pass a package without one — so an absent reveal is a corrupted file,
    // not a draft the client should open. Accepting it let a player solve the whole board and reach a
    // payoff panel with the boxscore missing, silently, on the one screen they reach once.
    for (const missing of [undefined, null]) {
      const raw = good();
      if (missing === undefined) delete raw.reveal;
      else raw.reveal = null;
      throws(() => readPackage(raw), "reveal is missing", `a package with reveal ${missing} was accepted`);
    }
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
      [
        "account_id",
        "assisted",
        "calendar_date",
        "device_id",
        "duration_ms",
        "errors",
        "failed_checks",
        "highest_technique",
        "hints",
        "played_on",
        "puzzle_id",
        "solved",
      ],
    );
    equal(record.assisted, false, "an ordinary game reported itself as assisted");
    // ⚠️ **Null rather than absent, on a game given no identity.** C7 lists these and the schema has to
    // carry them from the first row: an event whose subject is one fixed column cannot become claimable
    // later without rewriting history, which is what C7 exists to prevent.
    equal(record.device_id, null, "a game with no storage invented a device");
    equal(record.account_id, null, "there are no accounts yet");
    equal(record.calendar_date, null, "the engine does not know what day it is (C4)");
    equal(record.failed_checks, 0, "a game nobody checked reports a failed attempt");
    equal(record.duration_ms, 3000, "duration is not measured from the injected clock");
    equal(record.puzzle_id, puzzle.id);
  });

  test("⚠️ the record carries the identity it is given, on two different clocks", async () => {
    // ⚠️⚠️ **The two dates use two different clocks and neither is recoverable once written.**
    // `calendar_date` is the system's — August 22nd's puzzle is August 22nd's everywhere — and comes
    // from the loader. `played_on` is the **player's**: stored in UTC, somebody in California playing at
    // eleven at night is recorded as having played the next day, and every question about when people
    // play stops being answerable rather than merely wrong.
    const game = createGame(puzzle, undefined, {
      deviceId: "d-1",
      calendarDate: "2026-09-01",
      playedOn: "2026-08-31",
    });

    const record = game.record();
    equal(record.device_id, "d-1");
    equal(record.calendar_date, "2026-09-01");
    equal(record.played_on, "2026-08-31", "the player's date was replaced by the calendar's");
    equal(record.account_id, null, "an account appeared before there are accounts");
  });

  test("⚠️⚠️ a missing played-at date is null, never the calendar's", async () => {
    // **The mutation that found this test missing:** `identity.playedOn ?? identity.calendarDate`. It
    // looks like a sensible fallback and it is the exact confusion the two fields exist to prevent —
    // the player's clock silently replaced by the system's, in a row nothing can correct afterwards.
    //
    // ⚠️ The earlier test always supplied both, so the fallback was never reached and the mutation
    // passed. **A test that gives every field cannot see a wrong default.**
    const game = createGame(puzzle, undefined, { calendarDate: "2026-09-01" });

    equal(game.record().played_on, null, "the calendar's date was recorded as when somebody played");
    equal(game.record().calendar_date, "2026-09-01");
  });

  test("⚠️⚠️ a full board that does not balance is one try, and an incomplete one is none", () => {
    // **The signal `errors` cannot carry.** `firstWrong` is a set of cells, so a player who fixes one
    // number and re-checks adds nothing to it — twenty presses of Check look identical to one. This
    // counts the presses, which is what separates somebody probing from somebody correcting.
    const game = createGame(puzzle);

    // ⚠️ An incomplete board first, and it must count nothing: pressing Check on a half-filled board is
    // a mistake about the state, not an attempt at the answer.
    equal(game.check().state, "incomplete");
    equal(game.record().failed_checks, 0, "an incomplete board counted as a try");

    // Every blank filled wrongly, then checked twice with nothing changed in between.
    for (const name of game.blanks()) game.enter(name, 9);
    equal(game.check().state, "wrong", "a board of nines balanced");
    equal(game.check().state, "wrong");

    equal(game.record().failed_checks, 2, "the same board submitted twice counted as one attempt");
  });

  test("⚠️ a solved board is not a failed check", () => {
    // The other half. A counter that never stopped counting would make every finish read as one more
    // attempt than the player made, and the reveal adds the successful one back.
    const game = createGame(puzzle);
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    for (const name of game.blanks()) game.enter(name, answers.get(name));

    equal(game.check().state, "solved");
    equal(game.record().failed_checks, 0, "the check that worked was counted as a failure");
  });

  test("⚠️ the count survives a reload, because a shared result must not improve on refresh", () => {
    const game = createGame(puzzle);
    for (const name of game.blanks()) game.enter(name, 9);
    game.check();
    game.check();

    const restored = createGame(puzzle);
    assert(restored.restore(game.snapshot()), "the session was refused");

    equal(restored.record().failed_checks, 2, "a reload reset the attempts to zero");
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

suite("The device identity: its own key, its own lifetime, and a storage that may refuse", () => {
  const fakeStorage = () => {
    const held = new Map();
    return {
      getItem: (key) => held.get(key) ?? null,
      setItem: (key, value) => held.set(key, value),
      removeItem: (key) => held.delete(key),
      held,
    };
  };

  test("the same browser gets the same id twice", async () => {
    const { deviceId } = await import("../engine/device.js");
    const storage = fakeStorage();

    equal(deviceId(storage), deviceId(storage), "a second call invented a new device");
  });

  test("⚠️ it lives under its own key, not inside a puzzle session", async () => {
    // The per-puzzle session is disposable — cleared when a board is finished with, rewritten on every
    // entry. A device identity inside it would be thrown away with whichever board it happened to sit in.
    const { deviceId, DEVICE_KEY } = await import("../engine/device.js");
    const { PREFIX } = await import("../engine/store.js");
    const storage = fakeStorage();
    deviceId(storage);

    equal([...storage.held.keys()], [DEVICE_KEY]);
    equal(DEVICE_KEY.startsWith(PREFIX), false, "the device id is filed under the session prefix");
  });

  test("⚠️⚠️ a storage that refuses everything still plays, anonymously", async () => {
    // §23: `browserStorage()` answers with something that accepts and remembers nothing when
    // `localStorage` is blocked. The device then looks new on every call, which is the honest outcome —
    // there is nothing to tie its events to — and the game must not care.
    const { deviceId } = await import("../engine/device.js");
    const refused = { getItem: () => null, setItem: () => {}, removeItem: () => {} };

    const first = deviceId(refused);
    const second = deviceId(refused);

    equal(typeof first, "string", "a refused storage stopped the id being made at all");
    equal(first === second, false, "a storage that remembers nothing returned a stable id");
  });

  test("the id looks like a UUID whatever made it", async () => {
    // `crypto.randomUUID` needs a secure context and `http://` on the local network is how this board
    // gets looked at during development, so the fallback path has to produce the same shape.
    const { deviceId } = await import("../engine/device.js");

    const shape = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
    equal(shape.test(deviceId(fakeStorage())), true, "the id is not a version 4 UUID");
  });

  test("⚠️⚠️ the played-at date is the player's, never UTC", async () => {
    // Stored in UTC, somebody in California playing at eleven at night is recorded as having played the
    // following day. **The information is gone once the row is written**, not merely wrong: nothing in
    // the row says which way to correct it.
    //
    // ⚠️⚠️ **The obvious assertion here — that `localDate` differs from `toISOString()` — passes or
    // fails on the machine's timezone**, which is a test that reports the environment rather than the
    // code. On a UTC runner the two agree and nothing is wrong. So this asserts the local calendar
    // components always, and only checks the divergence where the offset guarantees one.
    const { localDate } = await import("../engine/device.js");
    const lateEvening = new Date(2026, 7, 22, 23, 30);

    equal(localDate(lateEvening), "2026-08-22", "the date was not read from the local calendar");

    // West of UTC, 23:30 on the 22nd is already the 23rd in UTC. This is where the loss happens.
    if (lateEvening.getTimezoneOffset() > 0) {
      equal(lateEvening.toISOString().slice(0, 10), "2026-08-23", "the premise of this test is wrong");
      equal(localDate(lateEvening) === lateEvening.toISOString().slice(0, 10), false);
    }
  });

  test("single digits are padded, so the date sorts as a string", async () => {
    const { localDate } = await import("../engine/device.js");

    equal(localDate(new Date(2026, 0, 5)), "2026-01-05");
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
      // ⚠️⚠️ **The innings the OFFENCE batted, and this read `defense_by_inning` until 2026-08-23.**
      //
      // The board shows one club's batters and **the other club's pitchers** (§5: the offensive team
      // needs ≤13 batters, the defensive team ≤6 pitchers). Those pitchers faced the batters on this
      // board, so the innings that bound their outs are the ones the *offence* batted.
      //
      // ⚠️⚠️ **The wrong side came from copying a sentence out of the certifier**, where
      // `check_independent_correspondence` genuinely says *the innings the defence batted* — because it
      // is bounding a **different grid**: the reveal's unshared half, the other direction of the same
      // game, which the board does not draw. One rule, two grids, and the sentence travelled without
      // its subject. `CLAUDE.md`: *a justification is scoped, and it does not travel* — re-derive the
      // reason in the new place rather than carrying the conclusion across.
      //
      // **It passed for months because both grids had the same length.** Nine innings each side is the
      // ordinary game. The first reference package where they differ — a home club leading after the
      // top of the ninth and never batting, so eight entries against nine — is what made it fire, and
      // it fired on *correct data*, which is the expensive direction.
      const innings = puzzle.puzzle.lineScore.offense_by_inning.length;

      // >= at the bottom, not >. The last half-inning is not always completed: an offence that is the
      // home club and scores the winning run stops batting, leaving the staff on 3*(innings-1). The
      // first version of this assertion said `>` and failed on exactly that.
      assert(
        outs >= 3 * (innings - 1) && outs <= 3 * innings,
        `${id}: staff pitched ${inningsToDisplay(outs, INNINGS.PRINTED)} to a side that batted ${innings} innings`,
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
  const bootShell = async (raw, { session = null, now = { at: 7_000_000 }, outbox = null, storage = null } = {}) => {
    const { boot } = await import("../ui/phone/shell.js");
    const { createClock } = await import("../engine/clock.js");
    const { createStore } = await import("../engine/store.js");
    const { readPackage } = await import("../engine/package.js");
    const puzzle = readPackage(raw);
    const root = document.createElement("div");
    document.getElementById("board").append(root);
    const kept = new Map();
    const backing = storage ?? {
      getItem: (key) => kept.get(key) ?? null,
      setItem: (key, value) => kept.set(key, value),
      removeItem: (key) => kept.delete(key),
    };
    const store = createStore(backing);
    // ⚠️ **Seeded through the store's own `save`, never by writing a key this test invents.** The
    // first version keyed it `s.<id>`; the store keys it `boxscorepuzzle.session.v1.<id>`, so nothing
    // was ever restored and two cases failed on the fixture rather than on the shell. A test that
    // spells a key the code owns is a second copy of that key.
    if (session) store.save(puzzle.id, session);
    const shell = boot({
      puzzle,
      root,
      store,
      storage: backing,
      outbox,
      clock: createClock({ now: () => now.at }),
    });
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
    // ⚠️⚠️ **The whole footer goes, reference included, and this asserted the opposite until
    // 2026-08-22.** The superseded reasoning is kept because it was not silly: *a finished board is
    // still a boxscore somebody may want to read the rules against, and the keypad that was the other
    // route to them is gone.* True of the board as an object, false about the moment — the player has
    // finished, the cells take no entries, and the rules of a puzzle that is over are one more thing
    // between them and the thing they earned.
    //
    // ⚠️ It also cost the screen it sat on: two bands stacked at the bottom of a phone put *See the
    // boxscore* against the edge, clipped on a real handset.
    assert(!shell.root.querySelector(".footer"), "the footer strip survived the end of the game");
    assert(!shell.root.querySelector(".reference-key"), "a finished board still offers the relations");
    equal(shell.root.querySelector(".again")?.textContent, "See the boxscore");
    assert(shell.app.classList.contains("app-finished"), "the finished class was never applied");
    const cells = [...shell.root.querySelectorAll("td.cell")];
    equal(cells.filter((c) => c.getAttribute("role") === "button").length, 0, "cells are still controls");
    assert(!shell.root.querySelector(".cell.selected"), "a cell is still selected on a finished board");

    shell.teardown();
  });

  /** A queue that records what it was given, standing in for the real outbox. */
  const collectingOutbox = () => {
    const added = [];
    return {
      added,
      add: (item) => {
        // ⚠️ The real outbox refuses an id it already holds, and this stands in for it. Without that
        // the reopen test below would pass on a queue that behaves differently from the shipped one.
        if (added.some((each) => each.event_id === item.event_id)) return true;
        added.push(item);
        return true;
      },
    };
  };

  /**
   * ⚠️⚠️ **The other half of this list is `keep/src/keep/reading.py::_EVENT_FIELDS`.**
   *
   * `keep` refuses an unknown field *and* refuses a missing one, so a record that is nearly right is a
   * batch that never drains — and the failure appears on the server weeks later rather than here.
   * Nothing can check the two agree from one side: `keep`'s workflow ignores `serve/**` by design, so a
   * change here would not even run its suite. What this buys is that a change to the record goes red
   * **here**, next to the note saying which file has to change with it.
   */
  const EVENT_FIELDS = [
    "account_id",
    "assisted",
    "calendar_date",
    "device_id",
    "duration_ms",
    "errors",
    "event_id",
    "failed_checks",
    "highest_technique",
    "hints",
    "played_on",
    "puzzle_id",
    "solved",
  ];

  test("⚠️⚠️ finishing queues exactly one event, carrying the whole C7 record", async () => {
    const outbox = collectingOutbox();
    const shell = await bootShell(packages[0].raw, { outbox });
    fill(shell);

    press(shell.root, ".keypad button.check");

    equal(outbox.added.length, 1, "finishing queued the wrong number of events");
    equal(Object.keys(outbox.added[0]).sort(), EVENT_FIELDS, "the queued record is not the shape keep accepts");
    equal(outbox.added[0].solved, true, "a solved board was queued as unsolved");
    assert(outbox.added[0].event_id.endsWith(shell.puzzle.id), "the event id does not name the puzzle");

    shell.teardown();
  });

  test("⚠️⚠️ a board that reopens finished queues the same event, not a second one", async () => {
    // There are two ways to finish and they used to differ in everything, so the queueing sits at the
    // single point both pass through — which means a reopened board offers the queue an event too. What
    // makes the repeat harmless is the id: it is the device and the puzzle, so the queue already has it.
    const outbox = collectingOutbox();
    // ⚠⚠ **One storage across both boots, and it is the point rather than plumbing.** `bootShell`
    // makes a fresh one per call, so two boots would be two *devices* — and the id being the device and
    // the puzzle, the second event would legitimately be a different one. The test would then be
    // asserting that a cleared browser looks like a new device, which is true and is not this.
    const held = new Map();
    const storage = {
      getItem: (key) => held.get(key) ?? null,
      setItem: (key, value) => held.set(key, value),
      removeItem: (key) => held.delete(key),
    };
    const shell = await bootShell(packages[0].raw, { outbox, storage });
    fill(shell);
    press(shell.root, ".keypad button.check");
    const first = outbox.added[0].event_id;
    const session = shell.game.snapshot();
    shell.teardown();

    // The reload: a fresh shell over the same storage and the saved session, which is how a finished
    // board comes back.
    const again = await bootShell(packages[0].raw, { outbox, storage, session });

    assert(again.game.isFinished(), "the session did not come back finished, so this proves nothing");
    equal(outbox.added.length, 1, "a reopened finished board queued a second event");
    equal(outbox.added[0].event_id, first, "the reopened board produced a different id");

    again.teardown();
  });

  test("⚠️ a board with no outbox plays exactly the same", async () => {
    // §23, and it is what every test written before C3 relies on. A shell handed nothing to send with
    // records nothing and draws the same game.
    const shell = await bootShell(packages[0].raw);
    fill(shell);

    press(shell.root, ".keypad button.check");

    assert(shell.root.querySelector(".reveal"), "a shell with no outbox failed to finish the game");

    shell.teardown();
  });

  test("⚠️⚠️ an outbox that throws does not stop the reveal", async () => {
    // The queue is not on the play path and must not be able to get onto it. §23 holds through the code
    // that talks to the backend as well as through the backend itself.
    const exploding = {
      add: () => {
        throw new Error("the queue is broken");
      },
    };
    const shell = await bootShell(packages[0].raw, { outbox: exploding });
    fill(shell);

    const escaped = await escapingFrom(() => press(shell.root, ".keypad button.check"));

    equal(escaped, [], "the queue's failure escaped into the click handler");
    assert(shell.root.querySelector(".reveal"), "a broken queue swallowed the boxscore the player earned");

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
    // ⚠️ `contains`, not `===`. Every button in the product carries `.app-button` plus its own name, so
    // an exact-match assertion breaks the day a shared look arrives — which is what it did.
    assert(
      document.activeElement.classList.contains("reveal-close"),
      `focus did not land on an actionable control: ${document.activeElement.className}`,
    );
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
    // ⚠️ `contains`, not `===`. Every button carries `.app-button` plus its own name.
    assert(
      document.activeElement.classList.contains("again"),
      `closing left focus nowhere; the opener was gone: ${document.activeElement.className}`,
    );

    shell.teardown();
  });

  test("⚠️⚠️ a restored finished session opens on the BOARD, sealed, with no pad and the boxscore one tap away", async () => {
    // The ordinary reopen, which is the path persistence exists for and the one that used to hand back
    // an editable board and a running clock (v30-P1-03).
    //
    // ⚠️⚠️ **It used to draw the reveal over the board on arrival, and that was wrong for the way in.**
    // The landing's `See the board` goes here, and it landed the player on the boxscore — the one screen
    // its label does not name. **Arriving is a request for the board.** The reveal is what the footer's
    // `See the boxscore` is for.
    //
    // ⚠️ **v30-P1-03 is not reopened by this and the test says which half is which.** That finding was
    // the clock resuming and the board coming back editable; both are asserted below and both still
    // hold. Only the automatic opening of the reveal is gone.
    const first = await bootShell(packages[0].raw);
    fill(first);
    press(first.root, ".keypad button.check");
    const earned = first.root.querySelector(".reveal-time-figure").textContent;
    const saved = first.store.load(first.puzzle.id);
    first.teardown();

    const second = await bootShell(packages[0].raw, { session: saved, now: { at: 9_000_000 } });

    assert(!second.root.querySelector(".reveal"), "reopening drew the boxscore over the board again");
    assert(!second.root.querySelector(".keypad"), "a finished session came back with a keypad");
    equal(second.game.isFinished(), true);
    equal(second.clock.isSealed(), true, "the restored clock was not sealed");

    // ⚠️ And the way to it, because removing the automatic open is only right while the manual one
    // exists. A finished board with no route to the reveal would throw away what the player earned.
    const again = second.root.querySelector(".again");
    assert(again, "a finished board offers no way to the boxscore it earned");
    press(second.root, ".again");
    assert(second.root.querySelector(".reveal"), "the way to the boxscore does not open it");
    equal(second.root.querySelector(".reveal-time-figure").textContent, earned, "the restored time is not the earned one");

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
    return { puzzle, panel: renderReveal(puzzle, game.finish(), { onShare: async () => {} }) };
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
    const panel = renderReveal(puzzle, record, { onShare: async () => {} });

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
  const mount = async (
    raw,
    { session = null, today = new Date("2026-08-21T12:00:00"), onShare = undefined } = {},
  ) => {
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
    const shared = [];
    const view = renderLanding({
      puzzle,
      root,
      store,
      today,
      go: (href) => went.push(href),
      onShare: onShare === undefined ? (game) => shared.push(game) : onShare,
    });
    return { ...view, root, puzzle, went, shared, teardown: () => root.remove() };
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

  test("⚠️⚠️ a finished day offers the way back to the board AND the way to tell somebody", async () => {
    // **This is the exit out of the loop, and both halves of it.** Three screens pushed inward and none
    // pushed out: the landing sent you to the board, the finished board to the boxscore, the boxscore
    // back to the board. `Go home` is the exit; it arrives at a page that congratulates the player and
    // — before this — offered them nothing to do with it. The one growth mechanism the product has was
    // on the screen they had just left.
    const view = await mount(packages[0].raw, { session: await solvedSession(packages[0].raw) });

    assert(view.finished, "the fixture is not a finished session");
    assert(view.share !== null, "a solved day offers no share; the exit leads to a dead end");
    equal(view.play.textContent.startsWith(text("landing.see_board")), true, "the way in is still an offer to play");

    // ⚠️ **Side by side, in the place the single button occupies otherwise.** Where `Play today’s
    // puzzle` sits is the one thing a returning player looks for; a share two blocks below the verdict
    // is a control they scroll past. The placement is the feature, so the test asserts the container.
    const row = view.page.querySelector(".landing-way-row");
    assert(row !== null, "there is no row; the two controls are stacked somewhere else");
    equal(row.contains(view.play), true, "the way in is not in the row");
    equal(row.contains(view.share), true, "the share is not beside it");

    view.teardown();
  });

  test("⚠️⚠️ the landing's share carries the reveal's own mark, not a second drawing of it", async () => {
    // **A player learns the icon on the reveal and has to recognise it on the landing.** Two hand-drawn
    // twins are one edit away from being two different buttons for one act, and nothing would notice —
    // which is how this was found: the operator looked at the landing and said the icon was missing.
    //
    // The assertion is that the two are the **same drawing**, not that each has one. `shareIcon()` is
    // exported from `finish.js` and both call it; comparing the rendered markup is what catches a copy.
    const { shareIcon } = await import("../ui/phone/finish.js");
    const view = await mount(packages[0].raw, { session: await solvedSession(packages[0].raw) });

    const drawn = view.share.querySelector("svg");
    assert(drawn !== null, "the landing's share has no mark; the reveal's has one");
    equal(drawn.outerHTML, shareIcon().outerHTML, "the landing draws a different mark from the reveal");
    // ⚠️ Decorative: the label carries the meaning, so a screen reader must not read the mark as well.
    equal(drawn.getAttribute("aria-hidden"), "true");
    assert(view.share.textContent.includes(text("reveal.share")), "the mark replaced the label");

    view.teardown();
  });

  test("⚠️ an unfinished day offers no share, because there is no result to share", async () => {
    // A share before there is a result is a button that either lies or refuses, and a returning player
    // meets it every unfinished morning. The absence is the assertion.
    const view = await mount(packages[0].raw);

    equal(view.finished, false);
    assert(view.share === null, "an unsolved day offers a share");
    assert(view.page.querySelector(".landing-way-row") === null, "the finished-day row is drawn anyway");
    equal(view.play.textContent.startsWith(text("landing.play")), true);

    view.teardown();
  });

  test("⚠️⚠️ the share is guarded against a second press and is never disabled before the first", async () => {
    // `navigator.share` takes a moment; a second press during it opens a second sheet on some platforms
    // and queues a second row for one act. **Disabled during the send and never before it** — if the
    // button is on screen the game is over and the result can always be shared. The reveal’s share
    // carries the same rule, and it is the rule the operator asked for by name.
    let release = null;
    const calls = [];
    const view = await mount(packages[0].raw, {
      session: await solvedSession(packages[0].raw),
      onShare: (game) => {
        calls.push(game);
        return new Promise((resolve) => {
          release = resolve;
        });
      },
    });

    equal(view.share.disabled, false, "the share is disabled before it has been pressed");
    view.share.click();
    await Promise.resolve();
    equal(calls.length, 1);
    equal(view.share.disabled, true, "the share stays live during its own send");

    view.share.click();
    await Promise.resolve();
    equal(calls.length, 1, "a second press during the send started a second share");

    release();
    await Promise.resolve();
    await Promise.resolve();
    equal(view.share.disabled, false, "the share never comes back");

    view.teardown();
  });

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
    assert(view.went[0].startsWith("/today"), `the button did not go to the board: ${view.went[0]}`);

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

suite("The tutorial: six steps, skippable, and teaching on a board that adds up", () => {
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
    // ⚠️ `[data-cell]`, not `.tcell`. LOB is drawn as text rather than as a cell — the real board's
    // footnote line is a bold run, not a box — so a query keyed on the grid's class silently lost the
    // one term the global identity needs, and the check below would have compared PA against outs and
    // runs alone while reading as though it covered all three.
    for (const cell of view.page.querySelectorAll("[data-cell]")) {
      const raw = cell.textContent;
      if (raw === "") values[cell.dataset.cell] = null;
      else values[cell.dataset.cell] = cell.dataset.cell === "p.outs" ? inningsFromDisplay(raw) : Number(raw);
    }
    return values;
  };

  test("it is five steps, it says which one, and the skip is a real control", async () => {
    const view = await mount();

    // One screen saying what the game is, then one per relation family.
    equal(view.total, 6, "the tutorial is no longer an opening screen plus one step per relation");
    assert(view.page.querySelector(".tutorial-progress").textContent.length > 0, "the step is not numbered");
    // ⚠️ Present and visible. §1b: a skip the visitor has to hunt for is a compulsory tutorial wearing
    // a disguise, which is the rule the reversal removed.
    assert(view.skip && !view.skip.hidden, "the skip is missing or hidden");
    view.teardown();
  });

  test("⚠️ nothing on any screen calls the board made up", async () => {
    // **Removed 2026-08-22, and the reasoning it overrides is worth keeping.** The line read "This one
    // is made up and smaller than a real board", and before that it stood on all five relation
    // screens. Its own note argued it could not go: *a four-batter, three-column board is visibly not
    // a boxscore, and a player who is not told spends a step deciding whether the tutorial is broken.*
    //
    // ⚠️ The operator saw the screen with the line on it and took it off. What replaces it is the
    // opening paragraph, which says what a real board is — *a real boxscore with most of its numbers
    // taken out* — so the difference is stated as the subject rather than as a caveat about the
    // illustration. This test exists so the element does not return without that being a decision.
    for (let step = 0; step <= 6; step += 1) {
      const view = await mount({ start: step });
      assert(!view.page.querySelector(".tutorial-made-up"), `screen ${step + 1} carries the caveat again`);
      view.teardown();
    }
  });

  test("⚠️ the batting order is taught last", async () => {
    // The other four are visible in the grid. Nothing on screen announces that turns are dealt around
    // the lineup, so it needs the most setup and gets the player who has seen four relations work.
    const view = await mount({ start: 5 });

    equal(view.page.querySelector(".tutorial-title").textContent, "The batting order", "the order changed");

    view.teardown();
  });

  test("⚠️⚠️ the made-up board satisfies all five relations, on the numbers it actually draws", async () => {
    // **The test that matters.** A tutorial teaching arithmetic that does not hold is the worst defect
    // available here, and no screenshot catches a subtle one — the board looks exactly as convincing
    // either way. Read out of the DOM at the last step, where every hole has been filled.
    const view = await mount({ start: 6 });
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
    for (let step = 0; step <= 6; step += 1) {
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
    for (let step = 0; step <= 6; step += 1) {
      const view = await mount({ start: step });
      const values = shown(view);

      assert(Object.keys(values).length > 0, `step ${step + 1} drew no cells at all`);
      blanksAt.push(new Set(Object.keys(values).filter((name) => values[name] === null)));
      view.teardown();
    }

    equal(blanksAt[6].size, 0, "the finished board still has a hole in it");
    // ⚠️ **The first screen fills nothing, and that is the assertion rather than an exemption.** It
    // says what the game is and demonstrates no relation, so moving off it must leave the board exactly
    // as it was — a step 1 that quietly solved a cell would be teaching by sleight of hand.
    equal(
      [...blanksAt[0]].filter((name) => !blanksAt[1].has(name)).length,
      0,
      "the opening screen filled a cell, so it is demonstrating something after all",
    );
    for (let step = 1; step < 6; step += 1) {
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
    // From the second screen: the first demonstrates no relation and so has no hole of its own.
    for (let step = 1; step < 6; step += 1) {
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
    const view = await mount({ start: 6 });

    // So the player leaves knowing the button exists: a sheet nobody has been shown is a sheet nobody
    // opens, and it is what made skipping this safe.
    equal(view.page.querySelectorAll(".tutorial-reference dt").length, 5, "the five relations are not listed");
    view.next.click();
    equal(view.went.length, 1, "the last button went nowhere");
    assert(view.went[0].startsWith("/today"), `it did not lead to the board: ${view.went[0]}`);

    view.teardown();
  });

  test("skip leaves for the landing page rather than the board", async () => {
    const view = await mount();

    view.skip.click();

    equal(view.went.length, 1, "skip went nowhere");
    assert(view.went[0].startsWith("/"), `skip did not return to the landing: ${view.went[0]}`);
    view.teardown();
  });

  test("⚠️ Back on the first step leaves, rather than doing nothing", async () => {
    // A disabled Back on step one is a dead control; the honest meaning of *back* there is *out*.
    const view = await mount();

    view.back.click();

    equal(view.went.length, 1, "Back on the first step did nothing at all");
    assert(view.went[0].startsWith("/"), `Back did not return to the landing: ${view.went[0]}`);
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
  test("a malformed pointer is refused by name, not by TypeError", async () => {
    // v36-P3-23, carried across to the document that replaced the manifest as the thing selecting a
    // package. The finding is the same and so is the reason: the package gets rigorous validation and
    // the pointer selecting it got none, so a bad one died on `.includes` and an empty list fetched
    // `.../undefined.json` and failed inside `.json()`. Both entry points catch and show a sentence,
    // so the player outcome survived — while **the page misdiagnosed its own failure**.
    const { readPointer } = await import("../ui/phone/daily.js");

    for (const [raw, because] of [
      [null, "null"],
      [[], "an array"],
      [{ puzzle_id: "a" }, "no date"],
      [{ date: "", puzzle_id: "a" }, "an empty date"],
      [{ date: "2026-09-02" }, "no puzzle id"],
      [{ date: "2026-09-02", puzzle_id: "" }, "an empty puzzle id"],
      [{ date: "2026-09-02", puzzle_id: 1 }, "an id that is not a string"],
      // ⚠️ The date's *shape*, not just its type. It is shown to the player and stamped on every C7
      // event, so `"soon"` would travel into the event record and be unrecoverable there.
      [{ date: "soon", puzzle_id: "a" }, "a date that is not a date"],
      [{ date: "2026-9-2", puzzle_id: "a" }, "a date that is not zero-padded"],
    ]) {
      const error = throws(() => readPointer(raw, "today.json"), /today\.json/, `accepted ${because}`);
      assert(error instanceof PackageError, `${because}: refused with ${error.constructor.name}`);
    }
  });

  test("the real pointers still read", async () => {
    // ⚠️ The other half: a check that refuses everything is as useless as one that refuses nothing.
    const { readPointer, PUBLIC_DAYS } = await import("../ui/phone/daily.js");

    for (const name of PUBLIC_DAYS) {
      const raw = await (await fetch(`../data/puzzles/${name}`)).json();
      assert(readPointer(raw, name) === raw, `the shipped ${name} is refused by its own reader`);
    }
  });

  test("⚠️⚠️ the loader names one board, refuses an unknown one, and never computes a date", async () => {
    // **v36-P3-45, and closing it is what E1 is for.** The loader took an unknown `?p=` and served
    // `manifest.puzzles[0]` instead — a soft-404: a 200 carrying *a different puzzle as if it were the
    // one asked for*. With shared links that is a person solving somebody else's board while believing
    // they solved this one, and **the absence of the requested puzzle reading as the presence of
    // another** is the shape this project records most often.
    //
    // The second assertion is the control: a loader that refused every path would satisfy the first.
    // The third is C4 and E1.3 — `calendarDate` is the date on the signed pointer, never
    // `localDate(now)`, which would be *the player's* date wearing the calendar's name.
    const { loadPuzzle, NoPuzzle, idInPath } = await import("../ui/phone/daily.js");
    const pointer = await (await fetch("../data/puzzles/today.json", { cache: "no-store" })).json();

    let refused = null;
    try {
      await loadPuzzle("/p/deadbeefdeadbeef");
    } catch (error) {
      refused = error;
    }
    const loaded = await loadPuzzle("/");

    assert(refused instanceof NoPuzzle, `an unknown id gave ${refused?.constructor.name ?? "a board"}`);
    equal(loaded.id, pointer.puzzle_id, "the default path did not load the board the pointer names");
    equal(loaded.calendarDate, pointer.date, "the calendar date did not come from the pointer");
    equal(idInPath(`/p/${pointer.puzzle_id}`), pointer.puzzle_id, "the id was not read out of the path");
    equal(idInPath("/"), null, "a path that names no puzzle produced one");
    equal(idInPath("/p/NOTHEX"), null, "a segment that is not an opaque id was accepted");
  });

  /**
   * Every module `serve/ui/phone/` ships. **Named here because a browser cannot list a directory**, and
   * checked against the real one by `forge/tests/test_the_date_guard_sweeps_every_module.py`.
   */
  const PLAYER_MODULES = [
    "board.js",
    "daily.js",
    "finish.js",
    "head.js",
    "landing-main.js",
    "landing.js",
    "main.js",
    "share-image.js",
    "share-result.js",
    "share-send.js",
    "shell.js",
    "testmode.js",
    "today.js",
    "tutorial-main.js",
    "tutorial.js",
  ];

  test("⚠️⚠️ no source under serve/ computes a calendar date", async () => {
    // **The reason `serve` owes no third `ROLLOVER_OFFSET_HOURS`**, asserted rather than asserted-in-a-
    // comment. Two trees compute the date — the forge decides what to build, `publish` decides which
    // pointer to copy — and this one reads it. A constant here would have no consumer, and its
    // assertion would pass forever while testing nothing.
    //
    // ⚠⚠ **`localDate(` is NOT forbidden, and the first version of this test forbade it and went red
    // on correct code.** `shell.js` uses it for `playedOn` — *when did this person sit down*, in the
    // player's own zone — which is a different quantity from *which puzzle*, on a different clock, and
    // `device.js` says so at length. **A test that bans the function bans the right answer along with
    // the wrong one.**
    //
    // So the assertion is on the pairing rather than on the name: nothing anywhere may compute a
    // rollover, and `calendarDate` may never be fed the player's date.
    // ⚠️⚠️ **Every module under `ui/phone/`, and the list was five of fifteen.** Ten files this guard
    // names as its subject were never read, `landing.js` among them. **A list maintained by hand beside
    // a directory**, which is the shape the page list two suites over has as well — and a browser cannot
    // enumerate a directory to fix it here. `forge/tests/test_the_date_guard_sweeps_every_module.py` is
    // what asserts this list names every file, in both directions, and it was seen red by deleting an
    // entry and by leaving a stale one.
    for (const module of PLAYER_MODULES) {
      const source = await (await fetch(`../ui/phone/${module}`)).text();
      const code = source.replace(/\/\*[\s\S]*?\*\/|\/\/.*$/gm, "");
      for (const forbidden of ["ROLLOVER", "getTimezoneOffset"]) {
        assert(!code.includes(forbidden), `${module} reaches for ${forbidden} to work out what day it is`);
      }
      assert(
        !/calendarDate\s*[:=]\s*localDate/.test(code),
        `${module} feeds the player's own date to calendarDate, which is the calendar wearing the wrong clock`,
      );
    }
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

  // ⚠️ `today.html` was absent from this list and it is the page that kept a hardcoded title
  // longest — the guard existed for exactly that defect and did not look at the file that still
  // had it. A list of pages maintained by hand beside a directory of pages.
  const PAGES = ["index.html", "play.html", "tutorial.html", "today.html"];

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
   *
   * ⚠️⚠️ **AND THAT LAST SENTENCE TURNED OUT TO COVER MORE THAN `lang`.** The declarative head — the
   * title, the description and the `og:`/`twitter:` tags — is read by scrapers and search crawlers that
   * **do not run scripts**, so `applyHead` setting them at runtime reaches every human and no machine.
   * A share carries a URL beside its image, and with those tags absent the card is a bare domain.
   *
   * **So they are in the markup, and this scan no longer reports them.** What replaces the report is
   * stricter than it was: the test below asserts each one **equals the catalogue's value**, so the
   * markup holds a copy that cannot drift rather than a copy nobody checks. C11 is *no user-facing
   * string is spelled in code* — a copy the catalogue owns and a guard compares is not a second
   * spelling, and a copy nothing compares is exactly what v36-P2-17 was.
   *
   * ⚠️ **The exemption is by tag, not by file.** `aria-label`, `placeholder`, `alt` and `title=` are
   * still refused everywhere: they are read by a human through a running page, which is the case
   * `applyHead` already serves.
   */
  const HEAD_TAGS_A_CRAWLER_NEEDS = ["description", "og:title", "og:description", "og:site_name", "og:image:alt"];
  const copyInMarkup = (source) =>
    [
      // ⚠️ `<title>` and the declarative metas are deliberately absent from this list. See the note
      // above and `the declarative head repeats the catalogue exactly` below, which is what covers them.
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

  test("⚠️⚠️ the declarative head repeats the catalogue exactly, never a second wording", async () => {
    // **This is what lets the markup hold a copy at all.** The head has to be static because a scraper
    // does not run scripts; the copy is only acceptable while something compares it, and this is that
    // something. Drift here is a search result and a share card saying what the page does not.
    const { text } = await import("../engine/strings.js");
    const TITLES = {
      "index.html": "page.landing.title",
      "tutorial.html": "page.tutorial.title",
      "play.html": "page.landing.title",
      "today.html": "page.landing.title",
    };

    for (const page of PAGES) {
      const source = await (await fetch(`../ui/phone/${page}`)).text();
      const title = /<title>([^<]*)<\/title>/i.exec(source);
      assert(title !== null, `${page} ships no <title>; a search result then shows whatever is inferred`);
      equal(title[1], text(TITLES[page]), `${page} titles itself outside the catalogue`);

      const meta = (name) =>
        (new RegExp(`<meta\\s+(?:name|property)="${name}"[^>]*content="([^"]*)"`, "i").exec(source) ?? [])[1];

      // ⚠️ The preview and the tab must agree. A card that says something the page does not is a
      // promise broken in one click, and it is invisible to anyone who does not share.
      equal(meta("og:title"), title[1], `${page}'s preview and tab disagree about the page`);
      equal(meta("og:description"), meta("description"), `${page}'s preview and search result disagree`);
      assert(meta("description"), `${page} ships no description`);
    }
  });

  test("⚠️ the markup scan catches the defect it was written for, and spares what belongs there", () => {
    // ⚠️ **The title is no longer reported by this scan and the confirmation says so**, rather than
    // being quietly deleted: a crawler needs it in the markup, and the test above is what holds it to
    // the catalogue. What this scan still refuses is copy a *running page* would put there.
    equal(copyInMarkup("<title>boxscore</title>").length, 0);
    equal(copyInMarkup('<meta name="description" content="Rebuild a real boxscore.">').length, 0);

    // ⚠️⚠️ **What is left is the half `applyHead` can serve, and the line between them is who reads it.**
    // A crawler reads the head before any script runs, so the head is markup and the test above holds it
    // to the catalogue. Everything below is read by a human through a *running* page — there is no
    // moment at which a screen reader has the `alt` and not the module that could have set it.
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

  test("⚠️⚠️ every screen's tab is distinguishable from the others when truncated", async () => {
    // **The property the per-screen titles exist for.** All three pages once carried the identical
    // `boxscore — the daily baseball logic puzzle`, so a tab among twenty said nothing about which one
    // it was — and the tab is what gets bookmarked and what shows in history.
    //
    // ⚠️ **Truncated, not whole.** A narrow tab shows about eleven characters. Titles that differ only
    // after that point are identical to the reader, which is why the distinguishing part goes first:
    // `boxscore puzzle — August 22` and the landing page's title are the same tab.
    const { CATALOGS } = await import("../engine/strings.js");
    const en = CATALOGS.en;
    const shown = [
      en["page.landing.title"],
      en["page.tutorial.title"],
      en["page.board.title"].replace("{date}", "August 22"),
      en["page.solved.title"],
    ].map((title) => title.slice(0, 11));

    equal(new Set(shown).size, shown.length, `two screens share a tab: ${shown.join(" | ")}`);
    for (const title of shown) assert(title.trim().length > 0, "a screen has no title at all");
  });

  test("⚠️ the board's tab names the day, and the solved one names no time", async () => {
    const { CATALOGS, fill } = await import("../engine/strings.js");
    const en = CATALOGS.en;

    // The date is a placeholder rather than a fixed word, so the tab says which board this is.
    assert(en["page.board.title"].includes("{date}"), "the board's tab does not name the day");
    equal(fill("page.board.title", { date: "August 22" }), "August 22 — boxscore puzzle");

    // ⚠️ **Decided, not omitted.** The reveal prints the time; a title carries it into history,
    // bookmarks and screenshots of the window — the tab strip, which is the part of a shared screen
    // people forget is visible, and which goes on announcing the result from a background tab. §26
    // shares the time because the player chose to.
    assert(!/\d/.test(en["page.solved.title"]), "the solved tab carries a figure");
  });

  test("⚠️ every page's tab uses the name the landing page shows", async () => {
    // A page saying one name and its tab another leaves neither sticking, and the tab is the half that
    // gets bookmarked.
    const { CATALOGS } = await import("../engine/strings.js");
    const en = CATALOGS.en;

    for (const key of ["page.landing.title", "page.board.title", "page.solved.title", "page.tutorial.title"]) {
      assert(en[key].includes("boxscore puzzle"), `${key} does not use the product's name`);
    }
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

  test("⚠️⚠️ ROUTES holds canonical URLs, and nothing here supplies a directory", async () => {
    // **The previous version fetched `../ui/phone/${file}`, and that is why it passed on dead links.**
    // It prefixed the directory whose absence was the defect — an instrument supplying the property
    // under judgement, so the sample could not judge it. Under E3's routing `play.html` linked from `/`
    // resolves to `/play.html`, which is a 404, and **both landing buttons were dead.**
    //
    // ⚠️ This asserts the *shape* rather than fetching. A fetch from this page would resolve these
    // against `/tests/`, which is the same mistake wearing a different directory;
    // `forge/tests/test_nginx_serves_what_is_declared.py` is where they are actually requested, from a
    // server that has the routes.
    const { ROUTES } = await import("../ui/phone/daily.js");

    const named = Object.entries(ROUTES);
    assert(named.length > 0, "ROUTES is empty, so this proves nothing");
    for (const [name, url] of named) {
      assert(url.startsWith("/"), `ROUTES.${name} is ${url}, which resolves against whatever page links it`);
      assert(!url.endsWith(".html"), `ROUTES.${name} is ${url}: an implementation path, not a canonical URL`);
    }
  });
});

suite("C3 — the upload queue: written down before it is sent, and deleted only when it lands", () => {
  const fakeStorage = () => {
    const held = new Map();
    return {
      getItem: (key) => held.get(key) ?? null,
      setItem: (key, value) => held.set(key, value),
      removeItem: (key) => held.delete(key),
      held,
    };
  };

  /**
   * Let every kicked pass finish.
   *
   * ⚠️ **A macrotask, not `Promise.resolve()`.** `add()` kicks a drain that is not awaited, so the
   * number of microtask turns between queueing and delivery is an implementation detail — a test that
   * counts them asserts the shape of the code rather than the behaviour, and goes red on a refactor
   * that is correct.
   */
  const settled = () => new Promise((resolve) => setTimeout(resolve, 0));

  const build = async (storage, send, capacity = 10) => {
    const { createOutbox } = await import("../engine/outbox.js");
    return createOutbox(storage, { name: "events", path: "/api/events", idField: "event_id", capacity, send });
  };

  /** Everything in the envelope landed. What `keep` says when it is up and the batch was well formed. */
  const accepts = async (path, body) => ({
    ok: true,
    status: 200,
    stored: body.events.map((each) => each.event_id),
  });

  const anEvent = (id) => ({ event_id: id, device_id: "d-1", puzzle_id: "p-1", solved: true });

  test("⚠️⚠️ the item is in storage before anything is sent", async () => {
    // C3.1, and the whole ordering of the module. A queue that sends first and writes on success loses
    // the item to a phone swiped away mid-request — which is the case it exists for.
    const storage = fakeStorage();
    const seen = [];
    let outbox = null;
    outbox = await build(storage, async () => {
      // Read at the moment of the send: the only way to observe the order rather than assert it.
      seen.push(storage.getItem(outbox.key));
      return { ok: true, status: 200, stored: [] };
    });

    outbox.add(anEvent("e-1"));
    await outbox.drain();

    assert(seen.length > 0, "nothing was sent at all");
    assert(String(seen[0]).includes("e-1"), "the item was sent before it was written down");
  });

  test("⚠️⚠️ finishing offline and coming back delivers exactly one event", async () => {
    // **C3's own acceptance condition.** The first attempt throws the way a dead network does; the
    // second succeeds. What must not happen is two events at the far end — and what must not happen
    // either is none.
    const storage = fakeStorage();
    let online = false;
    const delivered = [];
    const outbox = await build(storage, async (path, body) => {
      if (!online) throw new TypeError("Failed to fetch");
      delivered.push(...body.events);
      return { ok: true, status: 200, stored: body.events.map((each) => each.event_id) };
    });

    outbox.add(anEvent("e-1"));
    await settled();
    equal(delivered.length, 0, "an offline send delivered something");
    equal(outbox.pending().length, 1, "an offline send lost the event");

    online = true;
    await outbox.drain();
    await settled();

    equal(delivered.length, 1, "the event was delivered more or fewer times than once");
    equal(outbox.pending().length, 0, "a delivered event stayed in the queue");
  });

  test("⚠️⚠️ a reload mid-flight leaves the event queued, because deletion waits for the answer", async () => {
    // The half of the acceptance condition one process cannot show by itself: the queue is what
    // survives, so a request that never comes back must leave the item exactly where it was. The
    // re-send that follows is what the server-side id is for.
    const storage = fakeStorage();

    // A send that never resolves is what a killed tab looks like from the inside.
    const first = await build(storage, () => new Promise(() => {}));
    first.add(anEvent("e-1"));
    void first.drain();

    // The reload: a second outbox over the same storage.
    const delivered = [];
    const second = await build(storage, async (path, body) => {
      delivered.push(...body.events);
      return { ok: true, status: 200, stored: body.events.map((each) => each.event_id) };
    });
    equal(second.pending().length, 1, "the event did not survive the reload");
    await second.drain();

    equal(delivered.length, 1, "the reloaded page did not deliver the event");
  });

  test("⚠️ only the ids the server names are removed", async () => {
    // `stored` rather than a count is why `keep` answers this way: a partial success must not force the
    // client to re-send everything, which would reintroduce the duplicate the id exists to prevent.
    const storage = fakeStorage();
    const outbox = await build(storage, async () => ({ ok: true, status: 200, stored: ["e-1"] }));

    outbox.add(anEvent("e-1"));
    outbox.add(anEvent("e-2"));
    await settled();

    equal(
      outbox.pending().map((each) => each.event_id),
      ["e-2"],
      "the queue did not keep exactly what the server declined to name",
    );
  });

  test("⚠️⚠️ a batch refused for one bad member keeps every good one", async () => {
    // `keep` refuses a batch whole — correctly, since a client cannot be told *some of that landed*
    // without being told which — and that makes one malformed record a permanent blockage in front of
    // everything behind it. Retrying alone finds the poisoned one and drops only that.
    const storage = fakeStorage();
    const delivered = [];
    const outbox = await build(storage, async (path, body) => {
      if (body.events.some((each) => each.event_id === "bad")) return { ok: false, status: 400, stored: [] };
      delivered.push(...body.events.map((each) => each.event_id));
      return { ok: true, status: 200, stored: body.events.map((each) => each.event_id) };
    });

    outbox.add(anEvent("e-1"));
    outbox.add(anEvent("bad"));
    outbox.add(anEvent("e-2"));
    await settled();

    // ⚠️ **The end state, not one pass's report.** `add()` kicks, so how the three items are split
    // across passes is timing; what has to be true is that both good events arrive and only the bad one
    // is thrown away. A test asserting the split would be asserting the scheduler.
    equal(delivered.sort(), ["e-1", "e-2"], "a good event was thrown away with the bad one");
    equal(outbox.pending().length, 0, "the poisoned event stayed in the queue and blocks it forever");
  });

  test("⚠️⚠️ a 404 keeps everything, because a route can arrive with the next deploy", async () => {
    // The dangerous simplification is *any 4xx is permanent*. Beta 0 runs against a `serve` that does
    // not proxy these paths until F is done; dropping on 404 would discard every event recorded before
    // deployment, silently, which is the one loss C7 can never recover from.
    const storage = fakeStorage();
    const outbox = await build(storage, async () => ({ ok: false, status: 404, stored: [] }));

    outbox.add(anEvent("e-1"));
    const outcome = await outbox.drain();

    equal(outcome.dropped, [], "a 404 threw the event away");
    equal(outbox.pending().length, 1, "a 404 emptied the queue");
    await settled();
  });

  test("a server error keeps everything too", async () => {
    const storage = fakeStorage();
    const outbox = await build(storage, async () => ({ ok: false, status: 503, stored: [] }));

    outbox.add(anEvent("e-1"));
    await outbox.drain();

    equal(outbox.pending().length, 1, "an outage emptied the queue");
  });

  test("⚠️ an ok response whose body will not parse leaves the queue alone", async () => {
    // The alternative is assuming it landed, which drops an event on a proxy's HTML error page. The
    // cost of this direction is a re-send the server deduplicates.
    const storage = fakeStorage();
    const outbox = await build(storage, async () => ({ ok: true, status: 200, stored: undefined }));

    outbox.add(anEvent("e-1"));
    await outbox.drain();

    equal(outbox.pending().length, 1, "an unreadable answer was read as a delivery");
  });

  test("⚠️ the same id is queued once, however many times it is offered", async () => {
    const storage = fakeStorage();
    const outbox = await build(storage, async () => ({ ok: false, status: 503, stored: [] }));

    outbox.add(anEvent("e-1"));
    outbox.add(anEvent("e-1"));

    equal(outbox.pending().length, 1, "one event was queued twice");
  });

  test("an item with no id is refused rather than queued", async () => {
    // It could never be deduplicated and `keep` would refuse it forever, so it would sit at the head of
    // the queue blocking everything behind it. A lost item is the smaller failure.
    const storage = fakeStorage();
    const outbox = await build(storage, accepts);

    equal(outbox.add({ device_id: "d-1" }), false, "an event with no id was accepted");
    equal(outbox.pending().length, 0);
  });

  test("⚠️ the cap drops the oldest, not the newest", async () => {
    const storage = fakeStorage();
    const outbox = await build(storage, async () => ({ ok: false, status: 503, stored: [] }), 2);

    outbox.add(anEvent("e-1"));
    outbox.add(anEvent("e-2"));
    outbox.add(anEvent("e-3"));

    equal(
      outbox.pending().map((each) => each.event_id),
      ["e-2", "e-3"],
      "the cap dropped the wrong end of the queue",
    );
  });

  test("⚠️⚠️ a storage that refuses everything still delivers, for as long as the tab lives", async () => {
    // §23 again: private browsing and a denied origin must not mean a device that records nothing at
    // all. What cannot be promised is survival of a reload, and nothing claims it.
    const refused = {
      getItem: () => null,
      setItem: () => {
        throw new DOMException("QuotaExceededError");
      },
      removeItem: () => {},
    };
    const delivered = [];
    const outbox = await build(refused, async (path, body) => {
      delivered.push(...body.events);
      return { ok: true, status: 200, stored: body.events.map((each) => each.event_id) };
    });

    outbox.add(anEvent("e-1"));
    await settled();

    equal(delivered.length, 1, "a blocked storage stopped the event being delivered at all");
    equal(outbox.pending().length, 0, "the in-memory copy outlived its delivery");
  });

  test("⚠️ an item queued during a flight is not clobbered by the one that settles", async () => {
    // The queue is re-read after the response rather than written back from a variable captured before
    // it. Held across an await, it overwrites whatever arrived meanwhile.
    const storage = fakeStorage();
    let release = null;
    let calls = 0;
    const outbox = await build(storage, (path, body) => {
      calls += 1;
      // Only the first send is held open — the pass booked behind it must be able to finish, or this
      // test would hang on the very mechanism it is checking.
      if (calls > 1) return Promise.resolve({ ok: false, status: 503, stored: [] });
      return new Promise((resolve) => {
        release = () => resolve({ ok: true, status: 200, stored: body.events.map((each) => each.event_id) });
      });
    });

    outbox.add(anEvent("e-1"));
    const flight = outbox.drain();
    outbox.add(anEvent("e-2"));
    release();
    await flight;

    equal(
      outbox.pending().map((each) => each.event_id),
      ["e-2"],
      "the event queued mid-flight was deleted with the one that settled",
    );
  });

  test("⚠️ two drains at once send once", async () => {
    // `online`, `visibilitychange` and `add` all kick. Without a single-flight guard the same items go
    // twice — deduplicated at the far end, but a double this side chose to send.
    const storage = fakeStorage();
    let calls = 0;
    const outbox = await build(storage, async (path, body) => {
      calls += 1;
      return accepts(path, body);
    });

    outbox.add(anEvent("e-1"));
    await Promise.all([outbox.drain(), outbox.drain()]);
    await settled();

    // ⚠️ **One request, not one pass.** Later passes run and find the queue empty, which costs nothing
    // — `pass()` returns before it reaches the transport. What must never happen is the same event being
    // put on the wire twice by this side.
    equal(calls, 1, "the same event was sent twice");
  });

  test("an empty queue sends nothing", async () => {
    let calls = 0;
    const outbox = await build(fakeStorage(), async (path, body) => {
      calls += 1;
      return accepts(path, body);
    });

    await outbox.drain();

    equal(calls, 0, "an empty queue made a request");
  });

  test("a malformed queue in storage reads as empty rather than throwing", async () => {
    const { OUTBOX_PREFIX } = await import("../engine/outbox.js");
    const storage = fakeStorage();
    storage.setItem(`${OUTBOX_PREFIX}events`, "{not json");
    // ⚠️ A transport that never succeeds, so the assertion is about the queue rather than about how
    // many microtask turns pass before a successful delivery empties it.
    const outbox = await build(storage, async () => ({ ok: false, status: 503, stored: [] }));

    equal(outbox.pending(), []);
    outbox.add(anEvent("e-1"));
    await settled();
    equal(outbox.pending().length, 1, "a malformed queue stopped a new event being queued");
  });

  test("⚠️ follow() drains on a connection and on the page becoming visible, and can be stopped", async () => {
    const storage = fakeStorage();
    let calls = 0;
    const outbox = await build(storage, async () => {
      calls += 1;
      return { ok: false, status: 503, stored: [] };
    });
    outbox.add(anEvent("e-1"));
    await settled();
    const before = calls;
    const target = new EventTarget();

    const stop = outbox.follow(target);
    await settled();
    const afterFollow = calls;
    target.dispatchEvent(new Event("online"));
    await settled();
    target.dispatchEvent(new Event("visibilitychange"));
    await settled();
    const watching = calls;
    stop();
    target.dispatchEvent(new Event("online"));
    await settled();

    assert(afterFollow > before, "follow() did not drain when it was installed");
    assert(watching > afterFollow, "neither event drained the queue");
    equal(calls, watching, "the listeners were still attached after stop()");
  });

  test("⚠️⚠️ the event id is the device and the puzzle, so one game can only ever be one event", async () => {
    // The alternative is a fresh UUID per call, which makes a reopened board a second event that
    // percentiles would count — a game that never happened. The cost is written down where the id is:
    // a deliberate replay records nothing.
    const { eventId } = await import("../engine/outbox.js");

    equal(eventId({ device_id: "d-1", puzzle_id: "p-1" }), eventId({ device_id: "d-1", puzzle_id: "p-1" }));
    assert(
      eventId({ device_id: "d-1", puzzle_id: "p-1" }) !== eventId({ device_id: "d-2", puzzle_id: "p-1" }),
      "two devices share an event id",
    );
    assert(
      eventId({ device_id: "d-1", puzzle_id: "p-1" }) !== eventId({ device_id: "d-1", puzzle_id: "p-2" }),
      "two puzzles share an event id",
    );
  });

  test("a device with no storage still produces an id rather than one beginning 'undefined'", async () => {
    const { eventId } = await import("../engine/outbox.js");

    equal(eventId({ device_id: null, puzzle_id: "p-1" }), "anonymous:p-1");
  });

  test("the two queues have separate keys, so neither overwrites the other", async () => {
    const { errorOutbox, eventOutbox } = await import("../engine/outbox.js");
    const storage = fakeStorage();
    const dead = async () => ({ ok: false, status: 503, stored: [] });

    assert(eventOutbox(storage, dead).key !== errorOutbox(storage, dead).key, "the two queues share one key");
  });
});

suite("C4 — uncaught client errors: reported, rate-limited, and never in the way", () => {
  const collector = () => {
    const items = [];
    return {
      add: (item) => {
        items.push(item);
        return true;
      },
      items,
    };
  };

  const aWindow = () => {
    const target = new EventTarget();
    target.location = { pathname: "/p/abc", search: "?secret=1", href: "https://example.test/p/abc?secret=1" };
    target.innerWidth = 375;
    target.innerHeight = 812;
    target.navigator = { userAgent: "a browser" };
    return target;
  };

  const throwAt = (target, message, stack = "at draw (board.js:1:1)") => {
    // ⚠️ A synthetic `error` event rather than a real throw: a genuine uncaught exception inside a test
    // fails the harness before the handler can be observed, and the handler is what is under test.
    const event = new Event("error");
    event.message = message;
    event.error = { message, stack };
    target.dispatchEvent(event);
  };

  test("⚠️ an uncaught error is queued with exactly what §35 allows", async () => {
    const { watchForErrors } = await import("../engine/report.js");
    const outbox = collector();
    const target = aWindow();
    const stop = watchForErrors({ outbox, deviceId: "d-1", target, id: () => "x-1" });

    throwAt(target, "boom");
    stop();

    equal(outbox.items.length, 1, "the error was not reported");
    const report = outbox.items[0];
    // ⚠️ The field set, not a sample of it. `keep`'s reader refuses an unknown field and refuses a
    // missing one, so a report that is nearly right is a batch that never drains.
    equal(Object.keys(report).sort(), [
      "device_id",
      "error_id",
      "message",
      "page",
      "stack",
      "user_agent",
      "viewport",
    ]);
    equal(report.device_id, "d-1");
    equal(report.viewport, "375x812");
    equal(report.page, "/p/abc");
    assert(report.message.includes("boom"), `the message was lost: ${report.message}`);
  });

  test("⚠️⚠️ the query string never travels", async () => {
    // §35 keeps browsing history out, and a query is the one part of a URL carrying whatever somebody
    // put in it. `location.href` was the obvious field and is the wrong one.
    const { watchForErrors } = await import("../engine/report.js");
    const outbox = collector();
    const target = aWindow();
    const stop = watchForErrors({ outbox, deviceId: "d-1", target, id: () => "x-1" });

    throwAt(target, "boom");
    stop();

    assert(!JSON.stringify(outbox.items[0]).includes("secret"), "the query string reached the report");
  });

  test("⚠️⚠️ a render loop reports once", async () => {
    // C4.3. The cap alone would not stop the first five reports being five copies of one fact, which is
    // the shape a loop actually produces.
    const { watchForErrors } = await import("../engine/report.js");
    const outbox = collector();
    const target = aWindow();
    let made = 0;
    const stop = watchForErrors({
      outbox,
      deviceId: "d-1",
      target,
      id: () => `x-${(made += 1)}`,
    });

    for (let index = 0; index < 200; index += 1) throwAt(target, "boom");
    stop();

    equal(outbox.items.length, 1, "one repeated fault was reported more than once");
  });

  test("⚠️ distinct faults stop at the cap", async () => {
    const { watchForErrors } = await import("../engine/report.js");
    const outbox = collector();
    const target = aWindow();
    let made = 0;
    const stop = watchForErrors({
      outbox,
      deviceId: "d-1",
      target,
      limit: 3,
      id: () => `x-${(made += 1)}`,
    });

    for (let index = 0; index < 20; index += 1) throwAt(target, `boom ${index}`, `at frame${index} ()`);
    stop();

    equal(outbox.items.length, 3, "the per-load cap did not hold");
  });

  test("a rejected promise is reported too, whatever was thrown", async () => {
    // A rejection's reason is often not an `Error` — a string, an object, a fetch response — and
    // assuming `.message` gives `undefined` for exactly the cases that are hardest to diagnose.
    const { watchForErrors } = await import("../engine/report.js");
    const outbox = collector();
    const target = aWindow();
    const stop = watchForErrors({ outbox, deviceId: "d-1", target, id: () => "x-1" });

    const event = new Event("unhandledrejection");
    event.reason = "just a string";
    target.dispatchEvent(event);
    stop();

    equal(outbox.items.length, 1, "a rejection was not reported");
    assert(outbox.items[0].message.includes("just a string"), outbox.items[0].message);
  });

  test("⚠️⚠️ an outbox that throws does not take the page with it", async () => {
    // A reporter that can break the game is worse than no reporter: one broken render would become a
    // broken board, and the fault would be in the thing watching for faults. Dispatching runs the
    // handler synchronously, so a throw surfaces here and fails this test.
    const { watchForErrors } = await import("../engine/report.js");
    const exploding = {
      add: () => {
        throw new Error("the queue is broken");
      },
    };
    const target = aWindow();
    const stop = watchForErrors({ outbox: exploding, deviceId: "d-1", target, id: () => "x-1" });

    const escaped = await escapingFrom(() => throwAt(target, "boom"));
    stop();

    equal(escaped, [], "the reporter let its own failure out into the page");
  });

  test("⚠️ a long stack is truncated rather than sent whole", async () => {
    const { watchForErrors } = await import("../engine/report.js");
    const outbox = collector();
    const target = aWindow();
    const stop = watchForErrors({ outbox, deviceId: "d-1", target, id: () => "x-1" });

    throwAt(target, "boom", "x".repeat(50_000));
    stop();

    assert(outbox.items[0].stack.length <= 4000, `the stack was ${outbox.items[0].stack.length} characters`);
  });

  test("stop() detaches, so a second interface can unmount", async () => {
    const { watchForErrors } = await import("../engine/report.js");
    const outbox = collector();
    const target = aWindow();

    watchForErrors({ outbox, deviceId: "d-1", target, id: () => "x-1" })();
    throwAt(target, "boom");

    equal(outbox.items.length, 0, "the handlers were still attached after stop()");
  });
});

suite("The uplink: one storage, one device, both queues, in the one place three interfaces share", () => {
  const heldStorage = () => {
    const held = new Map();
    return {
      held,
      storage: {
        getItem: (key) => held.get(key) ?? null,
        setItem: (key, value) => held.set(key, value),
        removeItem: (key) => held.delete(key),
      },
    };
  };

  test("⚠️ everything hangs off the one storage object it was handed", async () => {
    // Two calls to `browserStorage()` hand back two different do-nothing objects when storage refuses,
    // so the session, the device id and the queues would forget in three separate places.
    const { startUplink } = await import("../engine/uplink.js");
    const { DEVICE_KEY } = await import("../engine/device.js");
    const { held, storage } = heldStorage();

    const uplink = startUplink({
      storage,
      target: new EventTarget(),
      send: async () => ({ ok: true, status: 200, stored: [] }),
    });
    uplink.stop();

    equal(held.get(DEVICE_KEY), uplink.device, "the uplink's device id is not the one in the storage it was given");
  });

  test("⚠️⚠️ an error thrown during boot is reported, because the watcher is installed first", async () => {
    const { startUplink } = await import("../engine/uplink.js");
    const { storage } = heldStorage();
    const target = new EventTarget();
    target.location = { pathname: "/" };
    target.navigator = { userAgent: "a browser" };
    const uplink = startUplink({ storage, target, send: async () => ({ ok: false, status: 503, stored: [] }) });

    const event = new Event("error");
    event.message = "boom";
    event.error = { message: "boom", stack: "at boot" };
    target.dispatchEvent(event);

    equal(uplink.errors.pending().length, 1, "an error during boot was not queued");
    uplink.stop();
  });

  test("⚠️ the three entry points all start it, because every visit is a chance to drain", async () => {
    // The landing page is where every visit lands (`serve-flow.md` §1), so it is where yesterday's
    // undelivered event goes out even for somebody who never opens a board. A rule each interface has
    // to remember is one the third will forget; this asserts all three remembered.
    for (const file of ["main.js", "landing-main.js", "tutorial-main.js"]) {
      const source = await (await fetch(`../ui/phone/${file}`)).text();
      assert(/startUplink\(/.test(source), `${file} never starts the uplink, so it reports nothing`);
    }
  });
});

suite("⚠️⚠️ The share image is actually produced, with the real stylesheets", () => {
  test("a real package rasterises to a PNG", async () => {
    // **`share-image.js` had NO test, and prose broke it in production.** The sheets are concatenated
    // into a `<style>` inside an SVG `foreignObject`, which is parsed as XML -- so one bare `<` ends the
    // element early and the whole SVG is refused. Two CSS comments written the same day contained
    // `<button>` and `<a>`, and **both share buttons stopped working on the live site**: the only growth
    // mechanism the product has, broken by a comment.
    //
    // ⚠️ **Nothing static could have caught it.** The CSS was valid, the JavaScript was valid, the
    // package was valid, and every existing test passed. What was missing was *doing the thing*: build
    // the image from the real sheets and see whether it comes out.
    const { shareImage } = await import("../ui/phone/share-image.js");
    const { createGame } = await import("../engine/game.js");
    const puzzle = readPackage(packages[0].raw);

    const blob = await shareImage(puzzle, createGame(puzzle), { random: () => 0.5 });

    equal(blob.type, "image/png");
    assert(blob.size > 2000, `the image is ${blob.size} bytes, which is too small to be a board`);
  });

  test("⚠️⚠️ a stylesheet containing markup characters still produces an image", async () => {
    // The regression itself, as a case. A comment mentioning `<button>` is ordinary prose in a
    // stylesheet and must never be able to break a share.
    //
    // ⚠️ Injected into the real sheet rather than into a copy of the builder: the defect lived in how
    // the builder consumes the sheets, so a test that assembles its own SVG would be testing itself.
    const { shareImage } = await import("../ui/phone/share-image.js");
    const { createGame } = await import("../engine/game.js");
    const puzzle = readPackage(packages[0].raw);

    const hostile = document.createElement("style");
    // Every character that ends a node in XML, in the places CSS legitimately carries them.
    hostile.textContent = [
      "/* an `<a>` and a `<button>` in one rule, and A & B */",
      '.share-hostile::after { content: "<not markup> & ]]> "; }',
    ].join(String.fromCharCode(10));
    document.head.append(hostile);
    try {
      const blob = await shareImage(puzzle, createGame(puzzle), { random: () => 0.5 });
      equal(blob.type, "image/png");
      assert(blob.size > 2000, "the image came out too small to be a board");
    } finally {
      hostile.remove();
    }
  });
});

suite("The share: what leaves the device, and what must not", () => {
  const puzzle = readPackage(packages[0].raw);

  /** A finished game: every blank filled with its answer, which is the only ending there is. */
  const solved = () => {
    const game = createGame(puzzle);
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    for (const name of game.blanks()) game.enter(name, answers.get(name));
    return game;
  };

  test("⚠️⚠️ not one of the player's answers survives into the shared board", async () => {
    // **The whole design, and the test that says it holds.** `serve-flow.md` §7b: the random digits
    // are what protect the puzzle and the blur is typography. An implementation that blurred the real
    // values would look identical to this one in every screenshot and would leak the answer to anyone
    // with a deconvolution script.
    const { maskAnswers } = await import("../engine/share.js");
    const game = solved();
    const masked = maskAnswers(game);

    const blanks = game.blanks();
    assert(blanks.length > 0, "the board has no blanks, so this test would pass over nothing");
    for (const name of blanks) {
      assert(masked.value(name) !== game.value(name), `${name} still holds the player's answer`);
    }
  });

  test("a given cell is untouched, because hiding it would hide nothing", async () => {
    const { maskAnswers } = await import("../engine/share.js");
    const game = solved();
    const masked = maskAnswers(game);

    const given = game.cells().filter((cell) => cell.given !== null);
    assert(given.length > 0, "no given cells, so this test would pass over nothing");
    for (const cell of given) equal(masked.value(cell.name), game.value(cell.name), cell.name);
  });

  test("⚠️ a replacement keeps the digit count, so the columns still line up", async () => {
    const { maskAnswers } = await import("../engine/share.js");
    const game = solved();
    const masked = maskAnswers(game);

    for (const name of game.blanks()) {
      equal(
        String(masked.value(name)).length,
        String(game.value(name)).length,
        `${name} changed width, which would say how big the real value was`,
      );
    }
  });

  test("⚠️⚠️ no cell is marked hinted, because that would point at the one that beat them", async () => {
    const { maskAnswers } = await import("../engine/share.js");
    const game = createGame(puzzle);
    const first = game.blanks()[0];
    game.hint(first);
    assert(game.isHinted(first), "the hint did not register, so this test proves nothing");

    equal(maskAnswers(game).isHinted(first), false, "the shared board admits which cell was hinted");
  });

  test("the record is the shape keep refuses anything else", async () => {
    const { shareRecord } = await import("../engine/share.js");
    const record = shareRecord({ deviceId: "d-1", puzzleId: "p-1", channel: "native", at: "2026-08-31" });

    equal(record.share_id, "d-1:p-1", "derived from device and puzzle, like the event id");
    equal(record.event_id, null, "present and null rather than absent");
    assert("event_id" in record, "event_id must be present -- keep refuses an absent one by name");
    equal(record.channel, "native");
  });

  test("⚠️ the share sheet is preferred, and only when it takes the file", async () => {
    const { sendShare } = await import("../ui/phone/share-send.js");
    const file = new File([new Blob(["x"])], "b.png", { type: "image/png" });
    const seen = [];
    const navigatorRef = {
      canShare: ({ files }) => files.length === 1,
      share: async (payload) => seen.push(payload),
    };

    equal(await sendShare(file, "1:23", { navigatorRef }), "native");
    equal(seen.length, 1, "the sheet was not opened");
    assert(seen[0].url.endsWith("/"), "the share points at the site, never at /p/<id>");
    // ⚠️ The time is in the sentence, and it is the player's. A share reading `in {time}` would go to
    // a stranger once, and there is no second first impression -- `fill` throws rather than ship it.
    assert(seen[0].text.includes("1:23"), `the elapsed time is missing: ${seen[0].text}`);
    assert(!seen[0].text.includes("{"), `an unfilled placeholder survived: ${seen[0].text}`);
  });

  test("⚠️⚠️ a browser that cannot take a file falls back rather than opening a sheet that fails", async () => {
    const { sendShare } = await import("../ui/phone/share-send.js");
    const file = new File([new Blob(["x"])], "b.png", { type: "image/png" });
    const written = [];
    // Every mobile browser has `navigator.share`; far fewer accept `files`. The ones that do not reject
    // AFTER the sheet has opened, which the player watches happen.
    const navigatorRef = { canShare: () => false, share: async () => assert(false, "the sheet opened") };

    equal(
      await sendShare(file, "1:23", { navigatorRef, clipboardRef: { write: async (items) => written.push(items) } }),
      "clipboard",
    );
    equal(written.length, 1, "nothing reached the clipboard");
  });

  test("⚠️⚠️ the clipboard write begins before the image exists, or the gesture is already gone", async () => {
    // **v42-P2-03.** `shareResult` used to await the rasteriser -- three stylesheets, three fonts, an
    // SVG serialise and a canvas -- and only then call `sendShare`, which called `clipboard.write()`.
    // On a browser that gates image clipboard writes on transient activation the write is refused,
    // several tasks after the click that authorised it. The player waits for the image and gets
    // nothing: the handler is `async`, so there is no failure state on screen.
    //
    // ⚠️⚠️ **The old tests could not see it**, and that is the finding rather than the bug. They called
    // `sendShare` with a file already in hand and a mock clipboard with no activation rule, so the
    // ordering under test never existed in them. **This asserts the order, which is the property.**
    const { sendShare } = await import("../ui/phone/share-send.js");

    let resolveImage = null;
    const image = new Promise((resolve) => {
      resolveImage = resolve;
    });
    let calledBeforeTheImage = null;
    const clipboardRef = {
      write: (items) => {
        calledBeforeTheImage = true;
        // The promise form: `ClipboardItem` holds the pending image, and this resolves later.
        return Promise.resolve(items);
      },
    };
    const navigatorRef = { canShare: () => false, share: async () => assert(false, "the sheet opened") };

    const sent = sendShare(image, "1:23", { navigatorRef, clipboardRef });
    // Let `sendShare` run up to its first real await. If it awaited the image first, `write` has not
    // been called and never will be until the line below.
    await Promise.resolve();
    await Promise.resolve();

    assert(calledBeforeTheImage, "clipboard.write() waited for the image; the click's activation is gone by then");

    resolveImage(new File([new Blob(["x"])], "b.png", { type: "image/png" }));
    equal(await sent, "clipboard");
  });

  test("⚠️ the native branch may await the image, because only the clipboard is activation-gated", async () => {
    // The other half, so the fix is not read as *never await anywhere*. `canShare({files})` must be
    // given a file to answer at all, and the share sheet is opened by the browser rather than written
    // to a gated surface. The probe is empty: `canShare` asks about the type, not the bytes.
    const { sendShare } = await import("../ui/phone/share-send.js");
    const seen = [];
    const navigatorRef = {
      canShare: ({ files }) => {
        seen.push(files[0].type);
        return true;
      },
      share: async (payload) => seen.push(payload.files[0].size),
    };

    const file = new File([new Blob(["xyz"])], "b.png", { type: "image/png" });
    equal(await sendShare(Promise.resolve(file), "1:23", { navigatorRef }), "native");

    equal(seen[0], "image/png", "canShare was asked about something other than a PNG");
    equal(seen[1], 3, "the sheet was handed the probe instead of the real image");
  });

  test("⚠️ a cancelled sheet is not an error -- the mechanism worked", async () => {
    const { sendShare } = await import("../ui/phone/share-send.js");
    const file = new File([new Blob(["x"])], "b.png", { type: "image/png" });
    const abort = Object.assign(new Error("cancelled"), { name: "AbortError" });
    const navigatorRef = {
      canShare: () => true,
      share: async () => {
        throw abort;
      },
    };

    equal(await sendShare(file, "1:23", { navigatorRef }), "native");
  });

  test("⚠️ anything that is not a cancellation is a real fault and travels", async () => {
    const { sendShare } = await import("../ui/phone/share-send.js");
    const file = new File([new Blob(["x"])], "b.png", { type: "image/png" });
    const navigatorRef = {
      canShare: () => true,
      share: async () => {
        throw new TypeError("the platform broke");
      },
    };

    let raised = null;
    try {
      await sendShare(file, "1:23", { navigatorRef });
    } catch (error) {
      raised = error;
    }
    assert(raised instanceof TypeError, "a genuine failure was swallowed as a cancellation");
  });
});


suite("The reveal's share button is never disabled, because the state cannot occur", () => {
  const puzzle = readPackage(packages[0].raw);

  const finished = () => {
    const game = createGame(puzzle);
    const answers = new Map(game.cells().map((cell) => [cell.name, cell.answer]));
    for (const name of game.blanks()) game.enter(name, answers.get(name));
    return game.finish();
  };

  test("⚠️⚠️ the button is live the moment the panel exists", async () => {
    // **If this panel is on screen the game is finished, and a finished game can always be shared.**
    // The button was drawn and `disabled` for weeks while there was nothing behind it; what retires
    // that is not that the feature arrived, it is that there is no state left where the reveal exists
    // and sharing is impossible.
    const { renderReveal } = await import("../ui/phone/finish.js");
    const panel = renderReveal(puzzle, finished(), { onShare: async () => {} });

    equal(panel.querySelector(".reveal-share").disabled, false, "the share button rendered disabled");
  });

  test("⚠️⚠️ a caller with no action is refused rather than given a quieter screen", async () => {
    // A dead button that looks deliberate hides a bug in the caller. **The absence of a check must not
    // read as the presence of a passing one** -- so this throws by name instead of degrading.
    const { renderReveal } = await import("../ui/phone/finish.js");

    throws(() => renderReveal(puzzle, finished()), "needs onShare");
    throws(() => renderReveal(puzzle, finished(), { onShare: "not a function" }), "needs onShare");
  });

  test("⚠️ a second press while the first is still building is ignored, and nothing greys out", async () => {
    // The guard is a flag rather than the `disabled` attribute: a button that greys out for a second
    // with no explanation reads as broken, and on the clipboard path the player would watch it die and
    // come back for no visible reason.
    const { renderReveal } = await import("../ui/phone/finish.js");
    let started = 0;
    let release = () => {};
    const held = new Promise((resolve) => {
      release = resolve;
    });
    const panel = renderReveal(puzzle, finished(), {
      onShare: async () => {
        started += 1;
        await held;
      },
    });
    const button = panel.querySelector(".reveal-share");

    button.click();
    button.click();
    equal(started, 1, "a second press started a second share");
    equal(button.disabled, false, "the button greyed out while sharing");

    release();
    await held;
    // One more turn so the `finally` runs before the last press is judged.
    await Promise.resolve();
    button.click();
    equal(started, 2, "the button did not come back after the first share finished");
  });
});
