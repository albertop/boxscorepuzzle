/**
 * The phone shell: it takes a puzzle and a root element and turns them into a playable board.
 *
 * ⚠⚠ **Split out of `main.js` so it can be driven by a test, and the reason is a test that claimed
 * to do it and did not.** The completion suite was documented as *"boot the real shell against a
 * package, solve it through the keypad"* while importing `createGame`, `renderSection` and
 * `renderKeypad` and calling them itself — useful component assertions under a description that
 * promised the lifecycle. So a green suite could sit beside a broken finish path: the keypad being
 * removed after a check, the board being redrawn without selection, *See the boxscore* replacing the
 * pad, a restored finished session opening the reveal. None of it was exercised. v31-P2-01.
 *
 * `main.js` could not be imported without running it — it fetches a manifest at the top level and
 * mounts into `#app`. Everything here takes its boundaries as arguments instead: the **root element**,
 * the **clock**, the **store** and the **document**. That is what makes the shell testable, and it is
 * also what a second interface will need (§33: one core, three screens).
 */

import { battingCell, footnoteCell, pitchingCell, sectionOf } from "../../engine/columns.js";
import { createClock, followAttention } from "../../engine/clock.js";
import { createGame } from "../../engine/game.js";
import { browserStorage, createStore } from "../../engine/store.js";
import { checkBoard, renderReference, renderReveal } from "./finish.js";
import { text } from "../../engine/strings.js";
import {
  applyKey,
  columnsFor,
  isInningsCell,
  paint,
  renderFootnotes,
  renderKeypad,
  renderLineScore,
  renderSection,
  totalNameFor,
} from "./board.js";

export function boot({
  puzzle,
  root = document.getElementById("app"),
  clock = createClock(),
  store = createStore(browserStorage()),
  doc = document,
}) {
  const app = root;
  app.replaceChildren();
  // ⚠️ **The session is restored before the board is drawn**, so the player never sees an empty grid
  // fill itself in. §27: the puzzle stays open all day and saves itself.
  const game = createGame(puzzle, clock);
  // ⚠️ A refused session is discarded rather than left to be re-read on every visit. Nothing here waits
  // on it: `restore` returns false and the player gets today's board, empty, which is the outcome §23
  // asks for when anything about persistence goes wrong.
  if (!game.restore(store.load(puzzle.id))) store.forget(puzzle.id);

  // ⚠️ **Saved on every change, not on a timer and not on unload.** `beforeunload` does not fire
  // reliably on a phone — a swiped-away tab is killed, not closed — so anything waiting for it is a
  // session that survives on a desktop and vanishes on the device the board was designed for.
  const remember = () => store.save(puzzle.id, game.snapshot());

  let selected = null;

  const score = document.createElement("div");
  score.className = "linescore";
  score.append(renderLineScore(puzzle.puzzle.lineScore, puzzle.offenseIsHome));
  app.append(score);

  const scroller = document.createElement("div");
  scroller.className = "scroller";
  app.append(scroller);

  let keypad = null;
  const select = (name) => {
    if (!game.isBlank(name)) return;
    selected = name;
    // The visible half of the same rule the handler enforces: the thirds keys apply to one kind of
    // cell, so they are only offered on that kind.
    keypad?.allowThirds(isInningsCell(name));
    for (const node of scroller.querySelectorAll(".cell")) {
      const isSelected = node.dataset.cell === name;
      node.classList.toggle("selected", isSelected);
      // The amber says *this one* to the eye; `aria-pressed` says it to everything else. A state that
      // only one of them can read is a state half the players cannot see.
      if (node.hasAttribute("aria-pressed")) node.setAttribute("aria-pressed", isSelected ? "true" : "false");
      // The row and column a selected cell shares an equation with. Shown because a deduction is
      // always about a line, and finding it by eye on a 44px grid is the tedious part.
      const other = node.dataset.cell !== name;
      const sameRow = node.dataset.cell.split(".")[0] === name.split(".")[0];
      // ⚠️ **Same column *within the same block*.** `hits` names a batting column and a pitching column,
      // so comparing the column alone lit the pitching grid from a batting selection — two grids that
      // share a word and no equation. The offence's hits and what the opposing staff allowed are
      // related, but by the cross-team identity, not by being one column.
      const sameColumn =
        node.dataset.cell.split(".")[1] === name.split(".")[1] &&
        sectionOf(node.dataset.cell) === sectionOf(name);
      // ⚠️ **The footnote line takes the amber and nothing else.** The highlight answers *which cells
      // does this one share an equation with*, and it answers it by lying along a row or a column — a
      // shape the grid has and the line does not. Tinting `#5a` and `#5b` because they share a column
      // showed a relation the line's own layout does not express, so the cue said something the eye
      // could not follow. Selected, yes; related, not here.
      const inLine = node.closest(".footnotes") !== null;
      node.classList.toggle("peer", !inLine && other && (sameRow || sameColumn));
    }
  };

  const draw = () => {
    scroller.replaceChildren();
    scroller.append(
      renderSection({
        // The same two keys the scoreboard uses, so one name cannot be spelled two ways on one screen.
        title: `${text(puzzle.offenseIsHome ? "side.home" : "side.away")} ${text("board.batting")}`,
        columns: columnsFor.batting,
        rows: puzzle.puzzle.batting,
        labels: puzzle.labels,
        slots: puzzle.slotReferences,
        cellName: battingCell,
        totalName: totalNameFor.batting,
        game,
        // ⚠️ `null` once the game has ended, and `renderSection` then draws cells that are not
        // controls at all — no listener, no tab stop, no `role="button"`. See `cellNode`.
        onSelect: game.isFinished() ? null : select,
      }),
    );
    scroller.append(renderFootnotes(puzzle, game));
    scroller.append(
      renderSection({
        // The other side, always: the board is one team batting against the other's staff.
        title: `${text(puzzle.offenseIsHome ? "side.away" : "side.home")} ${text("board.pitching")}`,
        columns: columnsFor.pitching,
        rows: puzzle.puzzle.pitching,
        labels: puzzle.pitcherLabels,
        slots: null,
        cellName: pitchingCell,
        totalName: totalNameFor.pitching,
        game,
        onSelect: game.isFinished() ? null : select,
      }),
    );
    // ⚠️ **Not on a finished board.** `selected` still holds whichever cell the player was in when
    // they pressed Check, and re-applying it paints the amber ground and `aria-pressed="true"` on a
    // cell that is no longer a control — an input affordance on a board that takes no input. Cleared
    // when the game ends rather than guarded here alone, so nothing can put it back.
    if (selected && !game.isFinished()) select(selected);
  };

  const repaint = () => {
    for (const node of scroller.querySelectorAll(".cell")) paint(node, game);
    const footnotes = scroller.querySelector(".footnotes");
    footnotes.replaceWith(renderFootnotes(puzzle, game));
  };

  // Every blank filled. Recomputed after each entry, because that is the only thing that changes it.
  const boardIsFull = () => game.blanks().every((name) => game.value(name) !== null);

  // ⚠⚠ **One class for the finished state, applied wherever the game can become finished.** The
  // stylesheet had `.app-finished td.cell { cursor: default }` and **nothing ever added that class** —
  // a rule that could not fire, with a comment describing behaviour that did not happen. `solved` was
  // the only class the shell set and it means *the reveal is open*, which is a different fact: after
  // the player closes the reveal the cells correctly have no role, no tab stop and no listener, and a
  // mouse still offered them as clickable. v31-P3-01.
  const markFinished = () => app.classList.add("app-finished");

  const showReveal = (record) => {
    app.classList.add("solved");
    app.append(renderReveal(puzzle, record));
  };

  // ⚠️⚠️ **The keypad exists while the board is an input surface and not afterwards.** A finished board
  // takes no entries, so a pad under it is a control that does nothing — and the alternative, leaving
  // it there disabled, is a row of dead keys occupying a third of the screen at the moment the player
  // is looking at their own finished work.
  //
  // What replaces it is the way back to the clipping. Closing the reveal must not throw away the thing
  // the player earned, and there is no other route to it once the pad is gone.
  if (game.isFinished()) {
    markFinished();
    const again = doc.createElement("button");
    again.type = "button";
    again.className = "again";
    again.textContent = text("done.see_boxscore");
    again.addEventListener("click", () => showReveal(game.record()));
    app.append(again);
  } else {
    keypad = renderKeypad(
      (key) => {
        if (!selected) return;
        applyKey(game, selected, key);
        repaint();
        remember();
        keypad.allowCheck(boardIsFull());
        keypad.showHints(game.hintsLeft());
      },
      () => check(),
    );
    app.append(keypad);
  }

  // ⚠⚠ **The end of the game, and until now there was not one.** A player could fill every cell and
  // nothing happened — no verdict, no ending, and the `reveal` block shipped in every package and was
  // drawn nowhere. That is the product's payoff and it was the one thing never delivered.
  const verdict = doc.createElement("p");
  verdict.className = "verdict";
  // Announced rather than merely painted: a player using a screen reader gets the same answer, and it
  // is the only answer the board is allowed to give.
  verdict.setAttribute("role", "status");
  verdict.setAttribute("aria-live", "polite");

  function check() {
    const result = checkBoard(game);
    // ⚠️ **The clock keeps running on a wrong board, and there is no attempt limit.** §27: no fail
    // state. What a mistake costs is time, which is what gets measured and shared — a limit would add
    // a fail state through the back door and stopping the clock would make errors free.
    if (result.state !== "solved") {
      verdict.textContent = result.message;
      verdict.dataset.state = result.state;
      return;
    }
    verdict.textContent = "";
    delete verdict.dataset.state;
    // ⚠️ `finish()` before the reveal is drawn, so the time shown is the time at the moment the board
    // was completed rather than however long the animation took.
    const record = game.finish();
    remember();
    selected = null;
    // ⚠️ Redrawn, because the board has just stopped being an input surface: the cells lose their
    // handlers and the keypad is replaced by the way back to the clipping. Without this the player
    // closes the reveal onto a board that still invites entries into a game that is over.
    draw();
    rebuildChrome();
    showReveal(record);
  }

  // ⚠️ The strip is still here and now carries only the verdict. The key moved into the pad; the
  // sentence did not, because a message that replaces a keypad key is a message nobody reads.
  // ⚠️⚠️ **In the chrome and not in the keypad, and both were rendered before choosing.** There is one
  // spare slot and there are two buttons, so the question was never *keypad or chrome* for each: it was
  // which one gets the slot.
  //
  // **The alternative was drawn and it decides itself.** *The relations* is thirteen characters and a
  // pad key is 66px: it wraps onto two lines inside the key, beside a row where every other key is one
  // short word. *Hint* plus a digit is the same shape as *Clear*.
  //
  // The reasons agree with the picture rather than standing in for it. The hint acts on the selected
  // cell, so it belongs among the keys that act on the selected cell; the reference acts on nothing and
  // is permanent context. And the reference has to stay reachable on a **finished** board, where there
  // is no keypad at all.
  const reference = doc.createElement("button");
  reference.type = "button";
  reference.className = "reference-key";
  reference.textContent = text("reference.title");
  reference.addEventListener("click", () => app.append(renderReference()));

  const footer = doc.createElement("div");
  footer.className = "footer";
  footer.append(reference, verdict);
  app.append(footer);

  /** Swap the keypad for the way back to the clipping, in place, when the game ends mid-session. */
  function rebuildChrome() {
    markFinished();
    app.querySelector(".keypad")?.remove();
    // ⚠️ The verdict goes and the reference stays: a finished board is still a boxscore somebody may
    // want to read the rules against, and the pad that used to be the other route to them is gone.
    verdict.remove();
    const again = doc.createElement("button");
    again.type = "button";
    again.className = "again";
    again.textContent = text("done.see_boxscore");
    again.addEventListener("click", () => showReveal(game.record()));
    app.append(again);
  }

  // ⚠⚠ **A finished board reopens finished.** Completion and its frozen duration are part of the
  // session now, so a solved puzzle came back looking unplayed: the reveal was gone, the clock resumed
  // for a visible page, and the next *Check* recorded a longer time than the player earned. The clock
  // is sealed by `restore` and cannot be restarted; this is the other half, which is drawing what the
  // player already earned instead of asking them to press Check again. v30-P1-03.
  if (game.isFinished()) {
    // The verdict has nothing to say about a finished board; the reference strip stays.
    verdict.remove();
    showReveal(game.record());
  }

  const attention = followAttention({ clock, save: remember, doc, target: app });
  // `pagehide` rather than `beforeunload`: it is the one a phone actually fires when a tab is
  // discarded. Cheap insurance over the save that already happened on the last entry.
  const onHide = () => attention.away();
  doc.defaultView?.addEventListener("pagehide", onHide);

  /**
   * Stop watching, and stop saving. **Every path that can write a session, closed together.**
   *
   * ⚠️⚠️ **Written because forgetting a session and then navigating puts it straight back.** The
   * development `reset` cleared the store and called `location.replace`, and the outgoing page's
   * `pagehide` fired `away()` → `remember()` on the way out — so the board came back exactly as it
   * had been, finished. Found by running it in a browser; the unit test passed, because a fake
   * `location` fires no unload.
   *
   * The two listeners have to go together: `attention.stop()` alone leaves `pagehide` attached, which
   * is the one that fires last and therefore the one that wins.
   */
  const detach = () => {
    attention.stop();
    doc.defaultView?.removeEventListener("pagehide", onHide);
  };

  draw();
  keypad?.allowCheck(boardIsFull());
  keypad?.showHints(game.hintsLeft());
  // ⚠️ Returned rather than only stashed on `globalThis`. The globals stay because the browser
  // console is how this board gets poked at during development; a caller that has the handle does not
  // have to reach through a global to use it.
  globalThis.__game = game;
  globalThis.__puzzle = puzzle;
  globalThis.__store = store;
  // ⚠️ `repaint`, `remember` and `location` are here for the development test mode, which drives the
  // shell through this handle rather than reaching around it. `location` is passed rather than read
  // from the global so a test can hand in a fake and nothing navigates.
  return {
    game,
    clock,
    store,
    app,
    check,
    showReveal,
    repaint,
    remember,
    detach,
    location: doc.defaultView?.location,
  };
}
