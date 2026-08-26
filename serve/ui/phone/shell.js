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
 * `main.js` could not be imported without running it — it fetches a pointer at the top level and
 * mounts into `#app`. Everything here takes its boundaries as arguments instead: the **root element**,
 * the **clock**, the **store** and the **document**. That is what makes the shell testable, and it is
 * also what a second interface will need (§33: one core, three screens).
 */

import { battingCell, footnoteCell, pitchingCell, sectionOf } from "../../engine/columns.js";
import { createClock, followAttention } from "../../engine/clock.js";
import { createGame } from "../../engine/game.js";
import { browserStorage, createStore } from "../../engine/store.js";
import { deviceId, localDate } from "../../engine/device.js";
import { eventId } from "../../engine/outbox.js";
import { checkBoard, formatDuration, renderReference, renderReveal } from "./finish.js";
import { shareResult as shareResult_ } from "./share-result.js";
import { applySolvedTitle } from "./head.js";
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
  // ⚠️ `storage` first, and `store` derived from it. Two calls to `browserStorage()` would probe
  // `localStorage` twice and — when it refuses — hand back **two different** do-nothing objects, so the
  // session and the device identity would be looking at unrelated places that both forget.
  storage = browserStorage(),
  store = createStore(storage),
  doc = document,
  fresh = false,
  calendarDate = null,
  now = new Date(),
  // ⚠️ **Optional, and the board plays without it** (§23). A shell handed no outbox records nothing
  // and draws exactly the same game — which is what every test written before C3 relies on, and what a
  // second interface does before it has wiring of its own.
  outbox = null,
  // ⚠️ **Optional for the same reason as `outbox`** (§23). A shell handed no share queue still shares:
  // the sheet opens, the image goes out, and nothing is recorded. **The share must never wait on the
  // backend** -- it is the only growth mechanism the product has, and friction here is friction on it.
  shares = null,
  device = null,
}) {
  const app = root;
  app.replaceChildren();
  // ⚠️ **The session is restored before the board is drawn**, so the player never sees an empty grid
  // fill itself in. §27: the puzzle stays open all day and saves itself.
  // ⚠️⚠️ **The identity is assembled here because this is where the storage and the clock are.** C7's
  // event is the engine's to produce and the engine must not reach for either: it does not know what day
  // it is (C4) and it has no storage of its own.
  //
  // ⚠⚠ `calendarDate` comes from the loader, and since E1 it is **the date on the signed pointer** —
  // written by the forge at generation, copied into the served root by `publish.rotate`. It is not
  // computed here and it must never be: the alternative is `localDate(now)`, which would be *the
  // player's* date wearing the calendar's name and would be wrong for anybody across a rollover.
  //
  // ⚠️ The default stays `null` rather than becoming required, because a caller that has no pointer
  // — the tutorial's made-up board, a test — has no honest date to give, and `null` says so. What
  // changed is that the *player's* path always has one.
  const game = createGame(puzzle, clock, {
    deviceId: deviceId(storage),
    calendarDate,
    playedOn: localDate(now),
  });
  // ⚠️ A refused session is discarded rather than left to be re-read on every visit. Nothing here waits
  // on it: `restore` returns false and the player gets today's board, empty, which is the outcome §23
  // asks for when anything about persistence goes wrong.
  // ⚠️ **`fresh` forgets the session instead of restoring it**, which is how the development test mode
  // starts from an unplayed board without a reload. It is one branch here rather than a second notion
  // of *unplayed* somewhere else: what comes back is a board booted the ordinary way that simply had
  // nothing to restore.
  if (fresh) store.forget(puzzle.id);
  else if (!game.restore(store.load(puzzle.id))) store.forget(puzzle.id);

  // ⚠️ **Saved on every change, not on a timer and not on unload.** `beforeunload` does not fire
  // reliably on a phone — a swiped-away tab is killed, not closed — so anything waiting for it is a
  // session that survives on a desktop and vanishes on the device the board was designed for.
  const remember = () => store.save(puzzle.id, game.snapshot());

  /**
   * Put this game's C7 record in the upload queue (C3).
   *
   * ⚠️ **Wrapped, because a queue that throws must not take the reveal with it.** §23 is the whole
   * rule: the game works with the backend down, and *the backend being down* includes the code that
   * talks to it being broken.
   */
  const queue = () => {
    try {
      const record = game.record();
      // ⚠️ **Stamped here rather than inside `record()`.** The engine produces the event; the id is
      // about *delivery*, and C4 keeps the engine ignorant of everything outside the board.
      outbox?.add({ event_id: eventId(record), ...record });
    } catch {
      // Deliberately empty. There is nowhere to report an upload failure to that is not the same queue.
    }
  };

  let selected = null;

  app.append(renderLineScore(puzzle.puzzle.lineScore, puzzle.offenseIsHome));

  const scroller = document.createElement("div");
  scroller.className = "scroller";
  app.append(scroller);

  let keypad = null;
  /**
   * One input, from wherever it came. **The keypad and the keyboard call this and nothing else.**
   *
   * ⚠️⚠️ **`applyKey` does not fork, and the reason is written in `board.js`.** Two paths into
   * `game.enter` — one for a button, one for a key — is the shape every serious defect in this project
   * has had. The thirds branch running ahead of its own flag, and the digit cap existing in one of the
   * two places it was written, were both that, and both were found by a person pressing keys.
   */
  const press = (key) => {
    if (!selected) return;
    applyKey(game, selected, key);
    repaint();
    remember();
  };

  /**
   * The blanks, in the order the board draws them. **The keyboard's world.**
   *
   * ⚠️ **Blank cells only, and that is the operator's decision.** A board is mostly given cells and
   * walking them is walking where nothing can be typed — `select()` already refuses them, so arrowing
   * over one would land on a cell that then refuses to be selected.
   */
  const walkable = () => [...scroller.querySelectorAll(".cell")]
    .map((node) => node.dataset.cell)
    .filter((name) => game.isBlank(name));

  /** The blank `step` places along from the selected one, or the first when nothing is selected. */
  const neighbour = (step) => {
    const names = walkable();
    if (names.length === 0) return null;
    const at = selected === null ? -1 : names.indexOf(selected);
    if (at === -1) return names[0];
    // ⚠️ Wraps. The last blank's *next* is the first: a board is a loop of unfilled cells, and stopping
    // dead at the end makes the player reach for the mouse — which is the alternative, not the input.
    return names[(at + step + names.length) % names.length];
  };

  const goTo = (name) => {
    if (name === null) return;
    select(name);
    // ⚠️ **Scrolled into view, because the board is taller than the screen.** Arrowing to a cell nobody
    // can see is arrowing to nowhere, and the totals row is pinned so the target can sit under it.
    scroller.querySelector(`[data-cell="${name}"]`)?.scrollIntoView({ block: "nearest" });
  };

  const select = (name) => {
    // ⚠️⚠️ **`null` deselects, and it used to fall out of the guard below.** `isBlank(null)` is false, so
    // the keyboard's Escape did nothing at all: `selected` kept its value, the amber stayed, and the
    // next digit landed in a cell the player believed they had left. A sentinel that a guard silently
    // swallows is worse than one that is refused.
    if (name !== null && !game.isBlank(name)) return;
    selected = name;
    // The visible half of the same rule the handler enforces: the thirds keys apply to one kind of
    // cell, so they are only offered on that kind.
    keypad?.allowThirds(name !== null && isInningsCell(name));
    for (const node of scroller.querySelectorAll(".cell")) {
      const isSelected = node.dataset.cell === name;
      node.classList.toggle("selected", isSelected);
      // The amber says *this one* to the eye; `aria-pressed` says it to everything else. A state that
      // only one of them can read is a state half the players cannot see.
      if (node.hasAttribute("aria-pressed")) node.setAttribute("aria-pressed", isSelected ? "true" : "false");
      // The row and column a selected cell shares an equation with. Shown because a deduction is
      // always about a line, and finding it by eye on a 44px grid is the tedious part.
      const other = node.dataset.cell !== name;
      const sameRow = name !== null && node.dataset.cell.split(".")[0] === name.split(".")[0];
      // ⚠️ **Same column *within the same block*.** `hits` names a batting column and a pitching column,
      // so comparing the column alone lit the pitching grid from a batting selection — two grids that
      // share a word and no equation. The offence's hits and what the opposing staff allowed are
      // related, but by the cross-team identity, not by being one column.
      const sameColumn =
        name !== null &&
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
    // ⚠️⚠️ **The keypad's state is derived here too, with the cells.** It used to be refreshed only in
    // the key handler, so anything that changed the board another way left the pad describing a board
    // that no longer existed — the development `fill` produced a full board with a dead *Check*, which
    // is precisely the state that makes `fill` useless for testing the ending.
    //
    // Both are the same kind of fact: what the pad offers is a function of the board, exactly as what
    // a cell shows is. One place derives both, so a second caller cannot forget half of it.
    keypad?.allowCheck(game.blanks().every((name) => game.value(name) !== null));
    keypad?.showHints(game.hintsLeft());
  };

  // ⚠⚠ **One class for the finished state, applied wherever the game can become finished.** The
  // stylesheet had `.app-finished td.cell { cursor: default }` and **nothing ever added that class** —
  // a rule that could not fire, with a comment describing behaviour that did not happen. `solved` was
  // the only class the shell set and it means *the reveal is open*, which is a different fact: after
  // the player closes the reveal the cells correctly have no role, no tab stop and no listener, and a
  // mouse still offered them as clickable. v31-P3-01.
  const markFinished = () => app.classList.add("app-finished");

  // ⚠️⚠️ **One way in and one way out, because `aria-modal` was a claim nothing was making true.**
  //
  // Both panels tell assistive technology `role="dialog"` and `aria-modal="true"`, which says *every
  // surface behind this one is unavailable*. Opening was `app.append(panel)` and closing was
  // `panel.remove()`, so none of it was: the board's controls kept their tab stops, the opener kept
  // focus **behind** the overlay — so a second Enter appended a second dialog — and closing dropped
  // focus to the top of the document. The accessibility tree and the DOM described different screens
  // with nothing checking that they agree, which is this project's usual defect wearing an ARIA
  // attribute. v34-P2-01.
  //
  // Lifecycle lives here rather than in the renderers: the shell is what appends them, what knows
  // whether one is already open, and the only thing that can put focus back where it came from.
  let panel = null;

  const dismiss = () => {
    if (!panel) return;
    const { node, hidden, opener } = panel;
    panel = null;
    for (const sibling of hidden) sibling.inert = false;
    node.remove();
    // ⚠️ **The opener is gone on the solve path.** `rebuildChrome()` removes *Check* before the reveal
    // is appended, so there is nothing to return to — a keyboard user would land at the top of the
    // document holding nothing. The control that replaced it is the honest destination.
    const back = opener?.isConnected ? opener : app.querySelector(".again");
    back?.focus();
  };

  const present = (build, opener) => {
    // Refuse rather than replace. A second panel stacked on the first is never what was asked for, and
    // replacing would silently discard a reveal the player was reading.
    if (panel) return;
    const node = build();
    // Snapshot before appending, so the new panel is not in its own hidden set.
    const hidden = [...app.children];
    for (const sibling of hidden) sibling.inert = true;
    app.append(node);
    panel = { node, hidden, opener };

    node.addEventListener("keydown", (event) => {
      if (event.key === "Escape") dismiss();
    });
    const close = node.querySelector(".reveal-close");
    close?.addEventListener("click", dismiss);
    // ⚠️ The close button rather than the heading. It is always present and always actionable, and a
    // screen reader announces the dialog's `aria-label` on entry either way — so this costs nothing and
    // leaves the user on a control instead of on text they cannot act from.
    //
    // ⚠️⚠️ **`preventScroll`, because focusing scrolls, and the panel was opening past its own
    // heading.** The close button sits at the foot of the sheet, so the browser scrolled it into view
    // the moment it took focus — the player pressed *See the boxscore* and arrived mid-table, with
    // *You rebuilt it* and their own time already above the fold. **The focus decision above is still
    // right; what was wrong is a side effect of it**, and the two are separable.
    close?.focus({ preventScroll: true });
    // Explicit rather than relying on a fresh element starting at zero: the sheet is rebuilt each time
    // and a future `scrollIntoView` anywhere in the panel would move it again, silently.
    node.querySelector(".reveal-sheet")?.scrollTo?.({ top: 0 });
  };

  // ⚠️ **The opener is passed, never read from `document.activeElement`.** A pointer press does not
  // focus the button it presses, so the active element at this moment is the body on every mouse and
  // touch path — the caller is the only thing that knows what opened this. Read from `activeElement`
  // it would have restored focus to `<body>` and the test asserting restoration would still pass,
  // because focusing the body silently succeeds.
  const showReveal = (record, opener = null) => {
    app.classList.add("solved");
    present(() => renderReveal(puzzle, record, { onShare: () => shareResult(record) }), opener);
  };

  // ⚠️ **The whole of Share is `share-result.js` now**, because the landing page offers it too and a
  // second copy of this sequence is the failure mode this repository is named after. What stayed here
  // is the four things the shell holds and that module does not.
  const shareResult = (record) => shareResult_({ puzzle, game, record, shares, device, outbox });

  // ⚠️⚠️ **The keypad exists while the board is an input surface and not afterwards.** A finished board
  // takes no entries, so a pad under it is a control that does nothing — and the alternative, leaving
  // it there disabled, is a row of dead keys occupying a third of the screen at the moment the player
  // is looking at their own finished work.
  //
  // What replaces it is the way back to the clipping. Closing the reveal must not throw away the thing
  // the player earned, and there is no other route to it once the pad is gone.
  /**
   * The one control a finished board offers, and the chrome it replaces.
   *
   * ⚠️⚠️ **The reference goes when the game does, and that reverses a decision recorded here.** The
   * superseded reasoning, kept because it was not silly: *a finished board is still a boxscore
   * somebody may want to read the rules against, and the pad that used to be the other route to them
   * is gone.* True of the board as an object. **It is false about the moment**: the player has
   * finished, the cells take no entries, and a button offering the rules of a puzzle that is over is
   * one more thing between them and the thing they earned.
   *
   * ⚠️ **And it was costing the screen it sat on.** The footer strip and the way back to the clipping
   * were two bands stacked at the bottom of a phone, which put *See the boxscore* against the edge —
   * clipped on the operator's own handset. Removing the strip moves the button up by its whole height.
   *
   * ⚠️ **Built once, and it used to be built twice** — here and in `rebuildChrome`, the same six lines
   * for the board that opens finished and the board that finishes while you watch. Two copies of one
   * control is how the two states drift into offering different things.
   */
  function finishedChrome() {
    markFinished();
    // ⚠⚠ **The one place a finished game becomes an event, because there are two ways to finish and
    // they used to differ in everything.** A board that finishes while you watch and a board that reopens
    // finished both arrive here; queueing from the check handler would have recorded only the first.
    //
    // ⚠️ **A reopened board therefore queues again, and that is harmless by construction** — `eventId`
    // is the device and the puzzle, so the second call offers the queue an id it already holds, or one
    // already delivered and gone. The duplicate is impossible rather than deduplicated afterwards.
    //
    // ⚠️ **`add` is synchronous, returns immediately and is not awaited.** Nothing about drawing the
    // reveal waits on a network that may not be there.
    queue();
    // ⚠️ **Both paths, because there are two and they used to differ.** A board that finishes while you
    // watch and a board that reopens finished both come through here now; a title set on one of them
    // only would leave a reopened solve advertising itself as today's unplayed puzzle.
    applySolvedTitle();
    app.querySelector(".keypad")?.remove();
    // The whole strip, not only the verdict: the reference lived in it and has nothing to say now.
    footer.remove();
    const again = doc.createElement("button");
    again.type = "button";
    again.className = "app-button again";
    again.textContent = text("done.see_boxscore");
    again.addEventListener("click", () => showReveal(game.record(), again));
    app.append(again);
    return again;
  }

  // ⚠️ **Only the pad is decided here; the finished chrome waits.** `finishedChrome` takes the footer
  // away, and the footer is created below — calling it from this branch read it before its `const` and
  // threw `Cannot access 'footer' before initialization` on every restored finished board. Caught by
  // running the suite, which is the only reason this is a note rather than a defect.
  if (!game.isFinished()) {
    keypad = renderKeypad(press, () => check());
    app.append(keypad);
  }

  // ⚠️ **The end of the game, which for a long time did not exist.** A player could fill every cell and
  // nothing happened — no verdict, no ending, and the `reveal` block shipped in every package and was
  // drawn nowhere. Kept as the reason this path was built before the rest of the finish work.
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
  reference.addEventListener("click", () => present(renderReference, reference));

  const footer = doc.createElement("div");
  footer.className = "footer";
  footer.append(reference, verdict);
  app.append(footer);

  /** Swap the keypad for the way back to the clipping, in place, when the game ends mid-session. */
  function rebuildChrome() {
    finishedChrome();
  }

  // ⚠⚠ **A finished board reopens finished.** Completion and its frozen duration are part of the
  // session now, so a solved puzzle came back looking unplayed: the reveal was gone, the clock resumed
  // for a visible page, and the next *Check* recorded a longer time than the player earned. The clock
  // is sealed by `restore` and cannot be restarted; this is the other half, which is drawing what the
  // player already earned instead of asking them to press Check again. v30-P1-03.
  if (game.isFinished()) {
    // Footer and all. Same call the mid-session finish makes, so a board that reopens finished and a
    // board that finishes while you watch cannot offer different things — which is what two copies of
    // this chrome used to make possible.
    //
    // ⚠️⚠️ **The reveal is NOT opened here, and it used to be.** Reopening drew the boxscore over the
    // board immediately, so *See the board* on the landing page led to the reveal — the one screen it
    // does not name. **Arriving here is a request for the board**; the reveal is what `See the
    // boxscore` in the footer is for, and it is one tap away.
    //
    // ⚠️ **This does not reopen v30-P1-03.** That finding was the clock resuming on a solved puzzle and
    // the board coming back looking unplayed. The clock is sealed by `restore` and the chrome is drawn
    // by the line above; neither depended on the reveal being on screen.
    finishedChrome();
  }

  /**
   * The keyboard. **What beta 1 is for** — `beta-0.md`: a physical keyboard is a different and better
   * interaction, and it is why desktop comes before tablet.
   *
   * ⚠️⚠️ **Every branch ends in `press()`, which is `applyKey`.** Nothing here decides what a digit
   * means; it decides which key is a digit. The rule itself stays in `board.js`, in the one testable
   * place, and `engine/` is not touched at all — `game.js` already exposed everything a keyboard needs.
   *
   * ⚠️ **A second digit CONCATENATES**, and that is not a new rule: `grow` appends and replaces past two
   * digits, capped at 99, because board totals exceed nine — a batting row reads 29, 31 — and replacing
   * would put them out of reach. Moving to another cell starts fresh because the next cell's value is
   * what `grow` is given.
   *
   * ⚠️ **Enter does NOT Check.** It confirms the cell and moves to the next blank. `Check` is a
   * commitment — it records a failed attempt on the event record — and one keystroke away from a
   * commitment is a commitment pressed by accident.
   *
   * ⚠️ **Nothing is bound while a panel is open.** The reveal and the reference sheet make their
   * siblings `inert`, and a board that kept typing underneath a boxscore would be editing a game the
   * player has finished reading.
   */
  const typed = (event) => {
    if (panel || game.isFinished()) return;
    if (event.ctrlKey || event.metaKey || event.altKey) return;

    const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[event.key];
    if (step !== undefined) {
      event.preventDefault();
      goTo(neighbour(step));
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      select(null);
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      // Confirm is *move on*: the value is already in the game, so the only thing left is the cursor.
      goTo(neighbour(1));
      return;
    }
    if (event.key === "Backspace" || event.key === "Delete") {
      event.preventDefault();
      press({ clear: true });
      return;
    }
    if (event.key >= "0" && event.key <= "9" && event.key.length === 1) {
      event.preventDefault();
      // ⚠️ Nothing selected: the first digit lands on the first blank rather than being swallowed. A
      // key that does nothing on a board full of empty cells reads as a broken keyboard.
      if (selected === null) goTo(neighbour(1));
      press({ digit: Number(event.key) });
    }
  };
  doc.addEventListener("keydown", typed);

  const attention = followAttention({ clock, save: remember, doc, target: app });
  // `pagehide` rather than `beforeunload`: it is the one a phone actually fires when a tab is
  // discarded. Cheap insurance over the save that already happened on the last entry.
  // ⚠️⚠️ **This listener fires last, and it once undid a deletion.** The development `reset` used to
  // forget the session and navigate; `pagehide` then fired `away()` → `remember()` on the way out and
  // wrote the board straight back, so it returned exactly as it had been. Found by running it in a
  // browser — the unit test passed, because a fake `location` fires no unload.
  //
  // `reset` no longer navigates (it boots `fresh` instead), so nothing needs to detach and the
  // function that did was deleted rather than kept. **The note stays**: anything that deletes a
  // session and then leaves the page has to reckon with this line.
  doc.defaultView?.addEventListener("pagehide", () => attention.away());

  draw();
  repaint();
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
    location: doc.defaultView?.location,
  };
}
