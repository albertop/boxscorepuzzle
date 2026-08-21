/**
 * A development affordance: reach a board's state without playing it.
 *
 * ⚠️⚠️ **This must never be able to affect a real player, and that is the whole design.** Four things
 * hold it, and each is a different kind of barrier so no single mistake removes them all:
 *
 *   1. **It is only reached behind an explicit query parameter.** `main.js` imports this module
 *      *dynamically*, inside the branch that reads `?test=`, so a normal load never fetches the file
 *      at all — a stronger property than a module that loads and declines to act.
 *   2. **An acceptance list, never an exclusion.** An unrecognised mode does nothing. `EXISTS` over a
 *      list of what is allowed is the rule this project wrote down after a filter that passed on
 *      absence, and it is the difference between an unknown value doing nothing and doing whatever the
 *      default branch happens to be.
 *   3. **No control anywhere in the interface reaches it.** Nothing is rendered, nothing is bound; the
 *      operator types a URL.
 *   4. **Anything it fills marks the game as assisted**, which reaches the C7 record. If the mode ever
 *      ran anywhere real, the history says so instead of carrying a fabricated perfect solve.
 *
 * ⚠️ **It writes through `game.enter()` — the keypad's own path — and adds no engine branch.** The
 * solution already ships inside the package (§23 requires it), so pre-filling needs no new data. If
 * validation or recording differed here by one step, the mode would stop testing the thing it exists
 * to test: it would be exercising a second implementation of entry.
 *
 *     ?test=reset    forget the saved session and reload, as though the board had never been played
 *     ?test=fill     every answer in place, Check not pressed — the completion path stays testable
 *     ?test=solved   filled and checked, so the reveal is one load away
 */

/**
 * ⚠️ The whole surface. A mode not in here does nothing, and adding one is a deliberate act rather
 * than a string that happens to reach a `switch`.
 */
export const MODES = ["reset", "fill", "solved"];

/**
 * Apply a mode, or do nothing at all.
 *
 * `shell` is what `boot()` returns. Nothing here reaches around it: the same handle a test uses.
 * Returns which mode ran, or `null` — so a caller, and the guard test, can tell.
 */
export function applyTestMode(mode, shell) {
  if (!MODES.includes(mode)) return null;

  if (mode === "reset") {
    // ⚠️⚠️ **Detached first, and the order is the whole of it.** Forgetting and then navigating puts
    // the session straight back: the outgoing page's `pagehide` fires the shell's save on the way out,
    // so the board returns exactly as it was. Found by running it — the unit test passed, because a
    // fake `location` fires no unload, and it now fires one.
    shell.detach();
    // ⚠️ The session is forgotten and the page is reloaded **without the parameter**, so what comes
    // back is a genuinely fresh board booted through the ordinary path — not a board this module
    // emptied by hand, which would be a second definition of *unplayed*.
    shell.store.forget(shell.game.puzzle.id);
    const url = new URL(shell.location.href);
    url.searchParams.delete("test");
    shell.location.replace(url.toString());
    return mode;
  }

  // ⚠️ **Marked before a single value is written.** Marking afterwards leaves a window in which the
  // board is full and the record still claims nobody helped — and a throw in the middle would leave it
  // there permanently.
  shell.game.markAssisted();
  const answers = new Map(shell.game.cells().map((cell) => [cell.name, cell.answer]));
  for (const name of shell.game.blanks()) shell.game.enter(name, answers.get(name));
  shell.repaint();
  shell.remember();

  // ⚠️ Through the shell's own Check handler rather than `game.finish()`. The point of `solved` is to
  // reach the *finished state*, and the finished state is everything that handler does — the verdict,
  // the redraw without selection, the keypad going away, the reveal. Calling `finish()` directly would
  // produce a game that is over and a screen that is not.
  if (mode === "solved") shell.check();
  return mode;
}
