/**
 * The share: a board whose answers have been replaced, and the record that one was made.
 *
 * **`docs/serve-flow.md` §7b is the design and it is easy to get backwards.** The share is a picture of
 * the *board*, never of the reveal — the reveal prints names, teams and date, so a screenshot of it
 * publishes the whole answer (§7, G1.1).
 *
 * ⚠️⚠️ **The random digits are what protect the puzzle. The blur is typography.** A blur is
 * concealment, and concealment invites reversal: deblurring is solved, the image is small, the glyph
 * set is ten digits in a known face and the grid positions are fixed. **Replace the values first and
 * the attack has nothing to reach** — anyone who reverses the blur perfectly recovers noise, and has no
 * way to tell it is noise. The identities do not balance, but they do not balance the way a wrong guess
 * does not balance, so the recipient cannot distinguish *I recovered the answer* from *I recovered
 * garbage that looks like one*.
 *
 * ⚠️ **So an implementation that blurs the real values is broken and looks identical to one that is
 * not** (G1.2). That is what `maskAnswers` exists to make impossible: the board is drawn from a game
 * whose answers are already gone, rather than drawn and then obscured.
 */

/**
 * A game with the player's own entries replaced by digits that are not theirs.
 *
 * ⚠️⚠️ **A facade over the real game, never a copy of it.** `paint()` and `renderSection()` ask a game
 * three questions — `isBlank`, `value`, `isHinted` — and this answers two of them exactly as the real
 * one does. **The board in the image is the board**, drawn by the board's own renderer, which is this
 * project's standing rule about samples: a variant is a parameter of the real renderer and never a
 * second one. `landing.js` draws its example the same way.
 *
 * ⚠️ **Given cells are untouched.** They were on the screen before the player arrived and are on every
 * copy of the puzzle; hiding them would hide nothing and would stop the image reading as a boxscore.
 *
 * ⚠️⚠️ **A replacement keeps the digit count of what it replaces.** `7` becomes a digit and `11`
 * becomes two, because the column widths are what make the artefact read as a finished boxscore rather
 * than as a wall of arbitrary numbers — and because a value whose *length* leaked would say which cells
 * held big numbers, which is information about the board.
 *
 * ⚠️ **And it is never the real value.** A random digit equal to the answer is not a leak on its own —
 * the recipient cannot tell which — but on a board of forty cells some would land right by chance, and
 * an implementation that permitted it could not be distinguished from one that had failed to mask at
 * all. Refusing the collision costs one redraw and removes the doubt.
 *
 * @param {object} game the finished game
 * @param {() => number} random unit interval, injectable so a test can pin what it draws
 */
export function maskAnswers(game, random = Math.random) {
  const masked = new Map();
  for (const cell of game.cells()) {
    if (cell.given !== null) continue;
    const real = game.value(cell.name);
    if (real === null) continue;
    masked.set(cell.name, someOtherNumberOfTheSameWidth(real, random));
  }
  // ⚠️ `Object.create` over the real game rather than a literal with three methods: anything the
  // renderer asks for that is not overridden here reaches the game itself, so a renderer that starts
  // consulting a fourth method keeps working instead of failing on an incomplete stand-in.
  return Object.create(game, {
    value: { value: (name) => (masked.has(name) ? masked.get(name) : game.value(name)) },
    /**
     * ⚠️⚠️ **No cell is hinted in the image, and that is a decision rather than an omission.** A hint
     * marks the cell it was spent on, so a shared board would say *this exact cell defeated me* — the
     * shape of the erasure is the puzzle, and pointing at one of its cells is a solution aid handed out
     * for free. The **count** goes on the artefact beside the time (§3); the **positions** do not.
     */
    isHinted: { value: () => false },
  });
}

/**
 * A number of the same width as `real`, drawn at random, never equal to it.
 *
 * The width is the digit count of the printed value. Innings are printed as `6.2` and are stored as
 * outs, so the printed width is what the renderer decides — this works on the stored integer, and a
 * masked out-count of the same magnitude prints at the same width.
 */
function someOtherNumberOfTheSameWidth(real, random) {
  const width = String(real).length;
  const low = width === 1 ? 0 : 10 ** (width - 1);
  const high = 10 ** width - 1;
  // ⚠️ A single-digit real value has ten candidates and nine of them are allowed, so this terminates
  // immediately in practice. It is a loop rather than an arithmetic dodge because the dodge — pick from
  // `high - 1` and step over the real value — is the kind of off-by-one that produces a mask that is
  // never one particular digit, which is a bias nobody would notice.
  for (;;) {
    const candidate = low + Math.floor(random() * (high - low + 1));
    if (candidate !== real) return candidate;
  }
}

/**
 * The record `keep` stores. **`docs/keep-api.md` `POST /shares` is the contract.**
 *
 * ⚠️⚠️ **This measures intent and never reach.** The browser cannot tell whether a share was
 * delivered: `navigator.share` resolves when the sheet closes — on some platforms whether or not
 * anything was sent — and a clipboard copy says nothing about whether it was ever pasted. A record
 * means *the player pressed Share and the mechanism responded*.
 *
 * ⚠️ `event_id` is present and null when the game's own record has not been made, never left out: a
 * field that appears only sometimes is one consumers forget to check for, and `keep` refuses an absent
 * one by name.
 */
export function shareRecord({ deviceId, puzzleId, eventId = null, channel, at }) {
  return {
    share_id: `${deviceId ?? "anonymous"}:${puzzleId}`,
    device_id: deviceId ?? "anonymous",
    puzzle_id: puzzleId,
    event_id: eventId,
    channel,
    shared_on: at ?? null,
  };
}
