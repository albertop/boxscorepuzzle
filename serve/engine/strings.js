/**
 * Every user-facing string, in one place. Seam C11.
 *
 * ⚠️ **Zero user-facing strings in code, from day one, including generated text.** Spanish is a
 * nice-to-have that can slip without affecting launch (§13); this catalog is not, because retrofitting
 * it means finding every literal in three presentation layers after they exist.
 *
 * The rule is mechanical: **if a player can read it, it is here.** Column headings, the reveal, error
 * messages, the reference sheet. A string that only a developer reads — a console warning, a thrown
 * `Error` — stays where it is thrown, and `serve/tests/` asserts the distinction so it cannot rot into
 * "most strings are in the catalog".
 */

const en = {
  "column.plate_appearances": "PA",
  "column.at_bats": "AB",
  "column.runs": "R",
  "column.hits": "H",
  "column.walks": "BB",
  // ⚠️ `SO`, not `K`. A printed boxscore labels the column `SO`; `K` is scorer's notation, what
  // goes in the notebook rather than in the paper. The argument that fixed the column order was
  // convention, and it applies to the label with equal force. Decided when the order was fixed
  // (§6) and deferred because it touched the package schema; done now, while schema 3 is being
  // cut, because doing it today costs nothing and doing it later costs a version.
  "column.strikeouts": "SO",
  "column.outs": "IP",
  "column.earned_runs": "ER",
  "column.hit_by_pitch": "HBP",
  "column.sacrifice_flies": "SF",
  "column.sacrifice_hits": "SH",
  "column.catcher_interference": "CI",

  "board.slot": "#",
  // ⚠️ **Which side, not just which half of the game.** `BATTING` alone left the two sections unnamed:
  // a player cannot tell whose batting order they are reconstructing, and the board is one team's
  // offence against the other's pitching. Four keys rather than an interpolation, because a language
  // that puts the side after the noun cannot be produced by gluing two strings together.
  "board.batting": "BATTING",
  "board.pitching": "PITCHING",
  "board.totals": "Totals",
  "board.left_on_base": "LOB",
  // The mark for an occurrence the board knows happened and the player has not yet placed.
  "footnote.unattributed": "?",
  // The mark a printed boxscore puts where a half-inning was never played. Not a zero — that states a
  // fact that did not happen — and not a dash, which reads as *nothing here* rather than *not played*.
  "board.inning_not_played": "x",

  "linescore.runs": "R",
  "linescore.hits": "H",
  "linescore.errors": "E",
  // ⚠️ **One spelling for one name.** The scoreboard said `Away` and the section header said
  // `AWAY BATTING`, which is two names for one thing on one screen — the same defect as `CI` against
  // `reached_on_interference`, in type instead of in code. The scoreboard and the header now share
  // these two keys, so they cannot drift.
  //
  // These also replaced `offense`/`defense` → "Away"/"Home", which was a **fabricated label**: nothing
  // in the package said which side batted last, and on the reference set the guess was wrong.
  "side.home": "HOME",
  "side.away": "AWAY",

  "keypad.clear": "Clear",
  "keypad.third": "⅓",
  "keypad.two_thirds": "⅔",

  "package.unreadable": "This puzzle could not be read.",
};

let table = en;

/**
 * A string by key. **An unknown key throws**, rather than rendering the key or an empty cell.
 *
 * ⚠️ A catalog that falls back to the key is a catalog that stops being complete without telling
 * anyone: the missing entry ships, renders as `board.totals`, and nobody notices until a screenshot.
 * The same reasoning as fail-closed at a boundary — the absence of a translation must not read as the
 * presence of one.
 */
export function text(key) {
  if (!Object.hasOwn(table, key)) throw new Error(`no string for ${key}`);
  return table[key];
}

export function keys() {
  return Object.keys(table);
}

/** For tests and, later, a language chosen at boot. */
export function useCatalog(replacement) {
  table = replacement;
}

export const CATALOGS = { en };
