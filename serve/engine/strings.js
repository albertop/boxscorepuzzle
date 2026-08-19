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
  "column.strikeouts": "K",
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
  "board.batting_home": "HOME BATTING",
  "board.batting_away": "AWAY BATTING",
  "board.pitching_home": "HOME PITCHING",
  "board.pitching_away": "AWAY PITCHING",
  "board.totals": "Totals",
  "board.left_on_base": "LOB",
  "board.inning_not_played": "—",

  "linescore.runs": "R",
  "linescore.hits": "H",
  "linescore.errors": "E",
  // ⚠️ These used to be `offense` → "Away" and `defense` → "Home", which was a **fabricated label**:
  // nothing in the package said which side batted last, and on the reference set the guess was wrong.
  // Now they name a side and the caller decides which row gets which, from `offense_is_home`.
  "linescore.home": "Home",
  "linescore.away": "Away",

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
