/**
 * The tutorial. `docs/serve-flow.md` §1b. Five steps, one per relation family, and **skippable**.
 *
 * ⚠️⚠️ **Skippable reverses §8, and skippable is not thinner.** A compulsory tutorial is a barrier in
 * front of someone who has not yet decided whether they are interested, and the ones who do not want it
 * leave before seeing a board — the outcome that rule existed to prevent, one screen earlier. It also
 * stopped being the only place the rules are stated when §3b's reference sheet shipped. None of that is
 * a reason to teach less: the sheet reminds someone who has met the relations, and this is where they
 * meet them.
 *
 * ⚠️ **The board here is NOT the board, and the player is told so.** Four batters, one pitcher, three
 * columns; a real one is six columns and up to thirteen rows, and `renderSection` cannot draw three
 * columns because the column set is fixed by the product (§6). This project's rule — *a sample that
 * evaluates the board is rendered with the board's renderer* — exists so that a judgement is never made
 * on a board that does not exist. Nothing is judged here; this illustrates a relation, and a
 * thirteen-row board would teach the relation and the crowding at once. **The headings still come from
 * the catalogue**, so the one thing that could silently disagree with the real board cannot.
 *
 * ⚠️ **No account, no progress tracking, no persistence of which step was reached.** Every piece of
 * machinery here sits on the path between a stranger and their first board. Remembering step 3 needs
 * storage, a key, an identity to key it by, and a rule for when it is stale — all spent on a visitor
 * who has not yet seen a puzzle, and invisible to them as anything but delay.
 */

import { INNINGS, inningsToDisplay } from "../../engine/columns.js";
import { fill, text } from "../../engine/strings.js";
import { ROUTES, withSearch } from "./daily.js";

/**
 * The made-up game, and **it is consistent across all five relations** — the same numbers answer every
 * step, because a board whose arithmetic only works one step at a time teaches that the relations are
 * unrelated tricks.
 *
 *   #1  PA 3  AB 3  BB 0        the pitcher: 2 innings (6 outs), 1 walk, 1 run
 *   #2  PA 2  AB 1  BB 1        left on base: 2
 *   #3  PA 2  AB 2  BB 0
 *   #4  PA 2  AB 2  BB 0
 *   ——  PA 9  AB 8  BB 1
 *
 *   row identity   #2: 2 = 1 + 1
 *   column         AB: 3 + 1 + 2 + 2 = 8
 *   cross-team     the walk the batters drew is the walk the pitcher gave
 *   global         9 = 6 outs + 1 run + 2 left on base
 *   batting order   3, 2, 2, 2 — down the slots it never goes up
 */
// ⚠️⚠️ **The plate-appearance column reads 3, 3, 2, 2 so the batting-order step has room to narrow.**
//
// It was 3, 2, 2, 2, and the last step then bounded a cell between two neighbours that both held 2 —
// `2 ≤ ? ≤ 2`, two equal bounds, a **determined** value. That demonstrates the answer rather than the
// rule: on a real board the order *narrows a range* and something else closes it, and a player shown
// the degenerate case learns that the relation produces numbers.
//
// ⚠️ Ten plate appearances over four slots is what a lineup actually does with them: turns are dealt
// round in order, so the first two slots bat three times and the last two bat twice. Nine over four
// gives 3, 2, 2, 2 — correct, and flat exactly where the lesson needs a step.
//
// Everything else moved with it, because the board has to satisfy all five relations on the numbers it
// draws and a test reads them back out of the DOM to check: the second batter's AB goes 1 → 2 so his
// row still closes, the totals go 9 → 10 and 8 → 9, and left-on-base goes 2 → 3 so `PA = Outs + R +
// LOB` still holds at 10 = 6 + 1 + 3.
const BATTERS = [
  { slot: 1, plate_appearances: 3, at_bats: 3, walks: 0 },
  { slot: 2, plate_appearances: 3, at_bats: 2, walks: 1 },
  { slot: 3, plate_appearances: 2, at_bats: 2, walks: 0 },
  { slot: 4, plate_appearances: 2, at_bats: 2, walks: 0 },
];
const TOTALS = { plate_appearances: 10, at_bats: 9, walks: 1 };
const PITCHER = { outs: 6, walks: 1, runs: 1 };
const LEFT_ON_BASE = 3;

const BATTING_COLUMNS = ["plate_appearances", "at_bats", "walks"];
const PITCHING_COLUMNS = ["outs", "walks", "runs"];

/**
 * The five, in the order they are taught.
 *
 * ⚠️ **The batting order is last and that is the whole reason for the order.** The other four are
 * visible in the grid — a row, a column, two facing sections, the whole game — and nothing on screen
 * announces that turns are dealt around the lineup. It needs the most setup, so it gets the player who
 * has already watched four relations work.
 *
 * `hole` names the cell this step leaves blank; `lit` names the cells the relation reads to fill it.
 * `name`, `body`, `rule` and `sum` are all **catalogue keys** — `sum` was a literal until v36-P2-09,
 * which is 19px of player-visible copy, one of them carrying the English words *innings* and *outs*.
 * Every earlier step's hole is filled by the time a later step draws, so the board is visibly rebuilt
 * across the five — which is the thing the product is called.
 */
const STEPS = [
  // ⚠️⚠️ **First, and it demonstrates nothing.** No hole, no worked line, no formula: the wizard used
  // to open on a relation, which answers *how* to a player who has not been told *what*. This screen
  // is the one a stranger decides on, and a relation put here makes it a wall.
  //
  // The board is drawn with every later step's cell already blank, which is the point — it is a
  // picture of the thing being described rather than an illustration of a rule.
  { name: "tutorial.step.what_this_is_name", body: "tutorial.step.what_this_is",
    rule: null, hole: null, lit: [], sum: null },
  { name: "reference.row_identity_name", body: "tutorial.step.row_identity",
    rule: "reference.row_identity", hole: "b1.plate_appearances",
    lit: ["b1.at_bats", "b1.walks"], sum: "tutorial.sum.row_identity" },
  // ⚠️ **The AB column, not PA, and the reason is the last step.** Teaching the column sum over PA
  // would show all four plate-appearance cells as *given*, and step five then turns one of them back
  // into a hole — a cell that was a fact in step two and an unknown in step five. The board has to
  // stay consistent across the five or it teaches that the relations are unrelated tricks.
  { name: "reference.column_sum_name", body: "tutorial.step.column_sum",
    rule: "reference.column_sum", hole: "t.at_bats",
    lit: ["b0.at_bats", "b1.at_bats", "b2.at_bats", "b3.at_bats"],
    sum: "tutorial.sum.column_sum" },
  { name: "reference.cross_team_name", body: "tutorial.step.cross_team",
    rule: "reference.cross_team", hole: "p.walks", lit: ["t.walks"], sum: "tutorial.sum.cross_team" },
  // ⚠️ **The sum crosses innings into outs out loud, because the board does not show outs.** The
  // pitching column is `IP` and reads `2`; this step asks the player to subtract 6. A test comparing
  // the identity against the numbers actually drawn is what found the gap — the step was arithmetically
  // right about a quantity the screen never displayed, which is the one kind of error that reads as
  // perfectly clear.
  // ⚠️⚠️ **The hole is the innings cell, and it used to be LOB — which taught the opposite of the
  // game.** §6: the footnote line is given, complete, never erased, and `erasable()` says so in code —
  // the per-batter cells and LOB are excluded from every board this product publishes. **A player's
  // first screens showed LOB as an empty box identical to an editable cell**, so the tutorial spent a
  // step deducing a number that always arrives with its value.
  //
  // ⚠️ **`p.outs` is erasable on a real board** — `erasable()` includes every pitching column — and it
  // makes the conversion load-bearing in the direction the board actually needs. The player computes
  // `10 − 1 − 3 = 6` **outs** and then has to write **2** in a cell headed `IP`. Solving for LOB never
  // required crossing innings into outs at all; it just happened to mention it.
  { name: "reference.global_name", body: "tutorial.step.global",
    rule: "reference.global", hole: "p.outs",
    lit: ["t.plate_appearances", "p.runs", "lob"], sum: "tutorial.sum.global" },
  { name: "reference.batting_order_name", body: "tutorial.step.batting_order",
    rule: "reference.batting_order", hole: "b2.plate_appearances",
    lit: ["b1.plate_appearances", "b3.plate_appearances"], sum: "tutorial.sum.batting_order" },
];

const valueOf = {
  lob: () => LEFT_ON_BASE,
};
for (const [row, batter] of BATTERS.entries()) {
  for (const column of BATTING_COLUMNS) valueOf[`b${row}.${column}`] = () => batter[column];
}
for (const column of BATTING_COLUMNS) valueOf[`t.${column}`] = () => TOTALS[column];
for (const column of PITCHING_COLUMNS) valueOf[`p.${column}`] = () => PITCHER[column];

/**
 * Outs as a boxscore prints innings pitched.
 *
 * ⚠️⚠️ **`inningsToDisplay`, because the hand-written version disagreed with the board.** This read
 * `${whole}.${thirds}` and printed six outs as `2.0`; the board prints `2`, because a whole number of
 * innings carries no fraction. A tutorial teaching a notation the real board does not use is worse
 * than one that teaches nothing — the player learns a form and then meets a different one. Third copy
 * of a rule in this file to be replaced by the definition, and the only one that was actually wrong.
 */
const printed = (name) => (name === "p.outs" ? inningsToDisplay(PITCHER.outs, INNINGS.BOARD) : null);

export function renderTutorial({ root, doc = document, go = null, start = 0 }) {
  let step = start;

  const page = doc.createElement("div");
  page.className = "tutorial";
  root.replaceChildren(page);

  const leave = (route) => {
    const href = withSearch(route);
    if (go) go(href);
    else doc.defaultView.location.assign(href);
  };

  // ---- the bar: progress, and a skip nobody has to hunt for -------------------------------------
  const bar = doc.createElement("div");
  bar.className = "tutorial-bar";
  const progress = doc.createElement("p");
  progress.className = "tutorial-progress";
  const skip = doc.createElement("button");
  skip.type = "button";
  skip.className = "tutorial-skip";
  skip.textContent = text("tutorial.skip");
  // ⚠️ **Visible, and that is the decision rather than the styling.** A skip the visitor has to hunt
  // for is a compulsory tutorial wearing a disguise, which is the rule §1b reversed.
  skip.addEventListener("click", () => leave(ROUTES.landing));
  bar.append(progress, skip);

  const title = doc.createElement("h1");
  title.className = "tutorial-title";

  const made = doc.createElement("p");
  made.className = "tutorial-made-up";
  // Said out loud, or the smaller board reads as a bug and the player spends the step on that.
  made.textContent = text("tutorial.made_up");

  const stage = doc.createElement("div");
  stage.className = "tutorial-stage";

  // ⚠️ A `div`, not a `p`: the first screen's text is three paragraphs and a `<p>` inside a `<p>` is
  // not a thing the parser will build. Every other step is a single paragraph and reads identically.
  const body = doc.createElement("div");
  body.className = "tutorial-body";

  const sum = doc.createElement("p");
  sum.className = "tutorial-sum";

  const rule = doc.createElement("p");
  rule.className = "tutorial-rule";

  // ---- the two buttons --------------------------------------------------------------------------
  const nav = doc.createElement("div");
  nav.className = "tutorial-nav";
  const back = doc.createElement("button");
  back.type = "button";
  back.className = "tutorial-back";
  back.textContent = text("tutorial.back");
  const next = doc.createElement("button");
  next.type = "button";
  next.className = "tutorial-next";
  nav.append(back, next);

  // ⚠️⚠️ **The reference list sits BELOW the buttons, and that is a measurement rather than a taste.**
  // With it inside `stage`, the last screen ran to 897px and put *Start today's puzzle* at y=823 on an
  // 812px viewport — the one call to action the whole tutorial exists to reach, below the fold, found
  // by asking the browser for the button's rectangle rather than by looking at the screenshot, which
  // showed a tidy page that simply ended. The way out goes above it; the five relations are reference
  // material and can be scrolled to.
  const tail = doc.createElement("div");
  tail.className = "tutorial-tail";
  page.append(bar, title, made, stage, body, sum, rule, nav, tail);

  back.addEventListener("click", () => {
    if (step === 0) return leave(ROUTES.landing);
    step -= 1;
    draw();
  });
  next.addEventListener("click", () => {
    if (step >= STEPS.length) return leave(ROUTES.board);
    step += 1;
    draw();
  });

  /**
   * One cell of the made-up board.
   *
   * ⚠️⚠️ **A cell that a later step will ask for is blank now.** The first version drew the board
   * complete except for the current hole, which meant step one displayed the answers to steps two
   * through five as plain given facts. The player is told *here is how you get this number* about a
   * number the same screen has already printed four times over — and the demonstration is worthless,
   * because nothing was ever unknown.
   *
   * It was found by a test asserting that no step makes a hole of a cell an earlier step gave, not by
   * looking at the screen: every version of this board looks equally convincing, which is exactly the
   * condition under which a rendered sample cannot be trusted.
   *
   * So the board opens with all five holes empty and fills one per step. That also makes the thing the
   * product is named after literally true on screen: it is rebuilt, in front of the player, from
   * nothing but the relations.
   */
  const cellNode = (name, { hole, lit, solved, pending }) => {
    const cell = doc.createElement("td");
    cell.className = "tcell";
    cell.dataset.cell = name;
    if (name === hole) {
      cell.classList.add("hole");
      cell.textContent = "";
    } else if (pending.includes(name)) {
      // A later step's subject: empty, and not marked, because nothing is claimed about it yet.
      cell.classList.add("pending");
      cell.textContent = "";
    } else {
      cell.textContent = printed(name) ?? String(valueOf[name]());
      if (lit.includes(name)) cell.classList.add("lit");
      if (solved.includes(name)) cell.classList.add("solved");
    }
    return cell;
  };

  const grid = (state) => {
    const wrapper = doc.createElement("div");

    const table = doc.createElement("table");
    table.className = "tgrid";
    const head = doc.createElement("tr");
    head.append(doc.createElement("th"));
    for (const column of BATTING_COLUMNS) {
      const th = doc.createElement("th");
      // The catalogue's heading, so the one thing that could disagree with the real board cannot.
      th.textContent = text(`column.${column}`);
      head.append(th);
    }
    table.append(head);

    for (const [row, batter] of BATTERS.entries()) {
      const tr = doc.createElement("tr");
      const slot = doc.createElement("th");
      slot.className = "tslot";
      slot.textContent = `${text("board.slot")}${batter.slot}`;
      tr.append(slot);
      for (const column of BATTING_COLUMNS) tr.append(cellNode(`b${row}.${column}`, state));
      table.append(tr);
    }

    const totals = doc.createElement("tr");
    totals.className = "ttotals";
    const label = doc.createElement("th");
    label.textContent = text("board.totals");
    totals.append(label);
    for (const column of BATTING_COLUMNS) totals.append(cellNode(`t.${column}`, state));
    table.append(totals);
    wrapper.append(table);

    const pitching = doc.createElement("table");
    pitching.className = "tgrid tpitching";
    const phead = doc.createElement("tr");
    phead.append(doc.createElement("th"));
    for (const column of PITCHING_COLUMNS) {
      const th = doc.createElement("th");
      th.textContent = text(`column.${column}`);
      phead.append(th);
    }
    pitching.append(phead);
    const prow = doc.createElement("tr");
    const plabel = doc.createElement("th");
    plabel.className = "tslot";
    plabel.textContent = text("board.pitching");
    prow.append(plabel);
    for (const column of PITCHING_COLUMNS) prow.append(cellNode(`p.${column}`, state));
    pitching.append(prow);
    wrapper.append(pitching);

    // ⚠️⚠️ **The footnote line is text, because that is what the real board draws.** `renderFootnotes`
    // emits `LOB: 3` as one bold run — `.footnotes .term.lob` is a font weight and nothing else, no
    // border and no box. The tutorial drew the value in a bordered cell identical to an editable one,
    // so the first board a player ever sees told them LOB is a thing you fill in. It is a given (§6),
    // and it is not even shaped like an input.
    //
    // ⚠️ The value keeps `data-cell` so the tests that read every number back out of the DOM still
    // find it — the identity check needs LOB, and a footnote drawn as prose that no test can read is
    // the arithmetic guarantee quietly losing a term.
    const line = doc.createElement("p");
    line.className = "tfootnote";
    const term = doc.createElement("span");
    term.textContent = `${text("board.left_on_base")}: `;
    const value = doc.createElement("span");
    value.className = "tlob";
    value.dataset.cell = "lob";
    value.textContent = String(valueOf.lob());
    if (state.lit.includes("lob")) value.classList.add("lit");
    line.append(term, value);
    wrapper.append(line);

    return wrapper;
  };

  function draw() {
    const finished = step >= STEPS.length;
    // Every earlier hole is filled by now, marked as the thing the player just worked out; every later
    // one is still empty, because a step cannot demonstrate a number the screen has already given.
    // ⚠️ `filter(Boolean)`: the first step has no hole, so both lists would carry a `null` that matches
    // no cell — harmless in `includes`, and exactly the kind of thing that stays harmless until
    // something reads the length.
    const solved = STEPS.slice(0, step).map((one) => one.hole).filter(Boolean);
    const pending = STEPS.slice(step + 1).map((one) => one.hole).filter(Boolean);
    const current = finished ? null : STEPS[step];

    // ⚠️ The whole bar, not its contents. Emptying the progress line and hiding the skip left a 44px
    // band of nothing above the last screen — a control-height gap where the eye still expects a
    // control.
    bar.hidden = finished;
    progress.textContent = finished
      ? ""
      : fill("tutorial.progress", { step: String(step + 1), total: String(STEPS.length) });
    skip.hidden = finished;
    title.textContent = finished ? text("tutorial.title") : text(current.name);
    // ⚠️⚠️ **The first step only. It used to appear on all five.**
    //
    // It is a caveat about the board, not part of any relation, and repeating it five times taught the
    // eye to skip the line above the board — which is where the step's own sentence lives. Saying it
    // once is enough.
    //
    // ⚠️ **Once, not never.** Removing it outright was the other reading and it is wrong until a first
    // screen exists to carry it: a four-batter, three-column board is visibly not a boxscore, and a
    // player who is not told spends a step deciding whether the tutorial is broken instead of watching
    // the relation work. It moves to that screen when there is one.
    made.hidden = finished || step > 0;
    // ⚠️ **Split on a blank line, so a step may carry more than one paragraph.** The alternative was
    // one `textContent` and a seven-line block on the screen a stranger decides from. Every other step
    // holds a single paragraph and comes out as one child, unchanged.
    body.replaceChildren(
      ...(finished ? text("tutorial.reference_hint") : text(current.body)).split("\n\n").map((part) => {
        const paragraph = doc.createElement("p");
        paragraph.textContent = part;
        return paragraph;
      }),
    );
    // ⚠️ **Hidden when the step has none, not merely empty.** The finish screen already emptied these
    // and hid them together; the first step is the second case, and an empty-but-present line leaves a
    // gap where the eye expects the worked example every other screen has.
    sum.textContent = finished || !current.sum ? "" : text(current.sum);
    sum.hidden = finished || !current.sum;
    rule.textContent = finished || !current.rule ? "" : text(current.rule);
    rule.hidden = finished || !current.rule;
    next.textContent = finished ? text("tutorial.finish") : text("tutorial.next");
    next.classList.toggle("tutorial-finish", finished);

    // ⚠️ **The finished board is drawn, complete.** The five steps have been rebuilding it in front of
    // the player, and stopping one cell short would end the demonstration on the one screen where it
    // pays off. It is also the only state in which every relation can be checked against what is
    // actually drawn, which is what the arithmetic test reads.
    stage.replaceChildren(
      finished
        ? grid({ hole: null, lit: [], solved: STEPS.map((one) => one.hole), pending: [] })
        : grid({ hole: current.hole, lit: current.lit, solved, pending }),
    );
    tail.replaceChildren(...(finished ? [referenceList(doc)] : []));
  }

  draw();
  return { page, next, back, skip, stepIndex: () => step, total: STEPS.length };
}

/**
 * The last screen is the reference sheet's own contents.
 *
 * ⚠️ **So the player leaves knowing the button exists.** A sheet nobody has been shown is a sheet
 * nobody opens, and it is the thing that made skipping this tutorial safe in the first place.
 */
function referenceList(doc) {
  const list = doc.createElement("dl");
  list.className = "tutorial-reference";
  // ⚠️ **The steps that carry a relation, which is no longer all of them.** The first screen says what
  // the game is and states no rule, so it has no `rule` key — and this sheet is the five relations, not
  // the six screens. It is the same list §3b puts one tap away during play, and a `How this works` entry
  // in it would be a heading with nothing under it on the surface a player consults mid-solve.
  for (const one of STEPS.filter((step) => step.rule)) {
    const name = doc.createElement("dt");
    name.textContent = text(one.name);
    const rule = doc.createElement("dd");
    rule.textContent = text(one.rule);
    list.append(name, rule);
  }
  return list;
}
