/**
 * Whether the screen is wide, as a class on the app's own root — **never as a bare media query.**
 *
 * ⚠️⚠️ **This exists because a media query reaches the share image and a class cannot.** The finding,
 * measured on 2026-08-26 rather than deduced:
 *
 * `share-image.js` lays the sheet out **in the real document**, off-screen, to measure its height — and
 * then draws it inside an SVG, which is a **separate document with its own 375px viewport**. A media
 * query is therefore evaluated twice against two different widths. With a probe rule
 * `@media (min-width: 800px)` added to `board.css` and the page at 1440:
 *
 * | | phone 375 | desktop 1440 |
 * |---|---|---|
 * | the rule matched in the page | no | **yes** |
 * | the rule matched inside the SVG | no | **no** |
 * | height of the produced PNG | 1864 | **2872** |
 * | ink across the row at 75% of the height | 710 px | **0 px** |
 *
 * **The image came out a third taller with the boxscore drawn small at the top and blank paper below**,
 * because the height was measured under one set of rules and the content drawn under another. It does
 * not even look broken: `.share-sheet`'s background stretches, so the empty part is white rather than
 * transparent.
 *
 * ⚠️ **And the share is the only growth mechanism the product has.** G3 was closed by sending the image
 * from a real phone through WhatsApp, iMessage and X. A wide layout would expire that verification with
 * nothing saying so.
 *
 * **The measurement stage hangs off `document.body`, not off the app root** (`share-image.js`), so a
 * rule written as `#app.wide .cell { … }` cannot reach it. That is the whole of the protection, and it
 * costs nothing while there is no desktop layout to rewrite.
 *
 * ⚠️⚠️ **`board.css` carries the opposite-looking precedent and it is not one.** Its `max-width: 359px`
 * rule says the breakpoint is a literal *because a media query condition is evaluated before the cascade
 * and cannot read a custom property*. **That justifies the literal, not the media query** — and the
 * class removes the constraint entirely, because `matchMedia` is called from JavaScript, which can read
 * the token. See the note beside that rule.
 */

/** The class the layout hangs from. ⚠️ On the app's own root, which the measurement stage is not inside. */
export const WIDE = "wide";

/**
 * The width at which the layout changes, read from `tokens.css`, or `null` when nobody has decided.
 *
 * ⚠️⚠️ **`--wide-from` is deliberately not declared yet.** Where the breakpoint is — or whether there is
 * one at all — is `beta-1-plan.md`'s **C-iii**, and it is the operator's. **An open decision must not be
 * enforced as though the answer were always yes**, so with no token there is no breakpoint and the class
 * is never applied. Declaring the token is the whole of turning it on.
 */
export function wideFrom(doc = document) {
  const declared = getComputedStyle(doc.documentElement).getPropertyValue("--wide-from").trim();
  if (!declared) return null;
  // ⚠️⚠️ **Matched whole, because `parseInt` reads the digits off the front and stops.**
  // `Number.parseInt("48em", 10)` is 48 — finite, positive, and wrong: a breakpoint written in ems would
  // have been silently reinterpreted as pixels. The first version of this check tested `isFinite` and
  // passed `48em` without a word, which is the regex-matching-a-prefix shape this project has recorded
  // four times, in a number instead of a name.
  const pixels = /^(\d+)px$/.exec(declared);
  // ⚠️ Refused rather than guessed. A token this cannot read is a decision somebody made, and treating
  // it as absent would make a configured breakpoint look like an unconfigured one.
  if (pixels === null || Number(pixels[1]) <= 0) {
    throw new Error(`--wide-from is ${JSON.stringify(declared)}; expected a pixel width like 800px`);
  }
  return Number(pixels[1]);
}

/**
 * Keep `root`'s class in step with the viewport. Returns a function that stops watching.
 *
 * ⚠️ **It watches rather than reading once.** A window resized across the breakpoint, a laptop docked to
 * a monitor and a phone turned sideways are the same event, and a layout that only reads on load is
 * wrong until the next navigation.
 */
export function followWidth(root, { doc = document, matcher = null } = {}) {
  const from = wideFrom(doc);
  if (from === null) return () => {};

  const query = matcher ?? doc.defaultView.matchMedia(`(min-width: ${from}px)`);
  const apply = () => root.classList.toggle(WIDE, query.matches);
  apply();
  query.addEventListener("change", apply);
  return () => query.removeEventListener("change", apply);
}
