/**
 * How long the player has actually been at the board.
 *
 * **An accumulated duration that grows, never `now − started`** (`docs/serve-flow.md` §5, §6). The clock
 * stops when the page is hidden and after a spell of inactivity, so a start timestamp would count the
 * lunch break — and a time that includes lunch means nothing to the person it is shared with.
 *
 * ⚠️ **`snapshot()` cannot express a start time, and that is the point.** It returns a number of
 * milliseconds. There is no representation of *when* anything began, so no future caller can persist one
 * by accident and no reader can reconstruct one. The rule is enforced by the shape rather than by a
 * comment asking for care.
 *
 * ⚠️ **`now` is injected**, so a test can move time without waiting and the engine keeps no hidden
 * dependency on when it runs — C4, one field over.
 *
 * The clock knows nothing about *why* it was stopped. Page visibility and the inactivity timeout are the
 * shell's business; this only counts.
 */
/**
 * How long the board may sit untouched before the clock stops. **Deliberately generous.**
 *
 * ⚠️ **The reason matters more than the number** (`docs/serve-flow.md` §5). In a deduction puzzle it is
 * normal to stare at the board without touching anything, and **that staring is play** — a short timeout
 * would discount exactly the thinking the game is about. If this figure is wrong it should be wrong in
 * this direction.
 *
 * ⚠️ **The clock does not apply it.** This module only counts; deciding that five minutes of silence
 * means *away* is the shell's judgement, made where the events are. The value lives here because it is
 * about time rather than about layout, and `serve`'s other constants file is a stylesheet.
 */
export const IDLE_MS = 5 * 60 * 1000;

/**
 * Run the clock while the player is here, hold it while they are not.
 *
 * **Two signals, together** (`docs/serve-flow.md` §5). Visibility catches the app switch, the minimise
 * and the screen lock; the idle timeout catches the tab left open on a desk. ⚠️ **Neither alone is
 * enough**: a hidden tab is obviously away, and a visible one is not obviously present.
 *
 * ⚠️ **This is a module and not fifteen lines in the shell, because of what the shell costs.** `main.js`
 * boots the application, so the suite cannot import it — and every rule written there is unguarded by
 * construction rather than untested by oversight. That has already cost this project a keypad control
 * doing something other than what was printed on it, and a digit cap that existed in one of the two
 * places it was written. Both were found by a person pressing keys.
 *
 * Everything it touches is injected: the clock, the save, the document whose visibility it reads, and
 * the element whose events count as presence. Returns a `stop` for a caller that has to take it apart.
 */
export function followAttention({ clock, save, doc, target, idleMs = IDLE_MS, setTimer = setTimeout, clearTimer = clearTimeout }) {
  let idle = null;

  const active = () => {
    clock.run();
    clearTimer(idle);
    idle = setTimer(away, idleMs);
  };

  function away() {
    clearTimer(idle);
    idle = null;
    clock.hold();
    // ⚠️ Written down **at the moment it stops**, because what happens next may be the tab being
    // killed rather than closed. A save waiting for `beforeunload` is a session that survives on a
    // desktop and vanishes on the device the board was designed for.
    save();
  }

  const onVisibility = () => (doc.hidden ? away() : active());
  const events = ["pointerdown", "keydown"];

  doc.addEventListener("visibilitychange", onVisibility);
  for (const event of events) target.addEventListener(event, active, { passive: true });
  if (!doc.hidden) active();

  return {
    away,
    stop() {
      clearTimer(idle);
      doc.removeEventListener("visibilitychange", onVisibility);
      for (const event of events) target.removeEventListener(event, active);
    },
  };
}

export function createClock({ now = () => Date.now(), elapsed = 0, running = false } = {}) {
  let accumulated = Math.max(0, Number(elapsed) || 0);
  /** When the current running span began, or `null` while held. **Never persisted.** */
  let since = running ? now() : null;

  const closeSpan = () => {
    if (since === null) return;
    // ⚠️ A backwards clock adds nothing rather than subtracting. System time can move — a manual
    // change, an NTP correction — and a negative span would hand the player a shorter time than they
    // played, which is the one direction the number must not move by accident.
    accumulated += Math.max(0, now() - since);
    since = null;
  };

  return {
    /** Start counting, or keep counting. Calling it twice does not start a second span. */
    run() {
      since ??= now();
    },

    /** Stop counting and keep what was counted. */
    hold() {
      closeSpan();
    },

    isRunning: () => since !== null,

    /** Milliseconds at the board, whether running or held. */
    elapsed() {
      return since === null ? accumulated : accumulated + Math.max(0, now() - since);
    },

    /**
     * Put back a duration a previous session counted.
     *
     * ⚠️ **One path, because `game.restore()` was dropping it silently.** The saved snapshot carried
     * `elapsed` and the game ignored it, so a reload returned the board exactly as it was left and the
     * clock at zero — a shared time shorter than the game took, which is the one direction it must not
     * move by accident. A restore that reads a field and does nothing with it is indistinguishable from
     * one that never had it.
     */
    restore(elapsed) {
      accumulated = Math.max(0, Number(elapsed) || 0);
      // A clock restored while running keeps running, from now rather than from whenever it last began.
      if (since !== null) since = now();
    },

    /**
     * What gets written down: a duration, and nothing else.
     *
     * ⚠️ Deliberately not `{ accumulated, since }`. A snapshot carrying `since` would let a reload count
     * the time the tab was closed, which is the defect this whole module exists to prevent.
     */
    snapshot() {
      return { elapsed: this.elapsed() };
    },
  };
}
