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

  // The slot column's heading, and the prefix a footnote attribution puts before a slot reference.
  // ⚠️ **One key for both, because they are one mark.** The renderer spelled `#` inline in the
  // footnote line while reading this key for the heading, so a catalogue could rename the column and
  // not the reference pointing at it — two spellings of one thing on one screen, which is the defect
  // `side.home` was introduced to close, recurring six keys further down.
  // What a screen reader hears where the eye sees an empty cell. ⚠️ Spoken, never drawn: the board
  // shows an empty cell and says nothing, because a grid of numbers with the word "blank" in thirty of
  // them is unreadable. The two channels carry the same fact in the form each can use.
  "cell.blank": "blank",
  "board.slot": "#",
  // ⚠️ `board.footnote_repeat` (`×`) lived here for one hour and is gone with the form that needed
  // it. `#4×2` put the count *after* the slot as a multiplier; the line now prints `2 #4`, count first
  // and always, so there is no multiplier to mark. Deleted rather than left unused — a key nothing
  // asks for is a translation obligation nobody can discharge.
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
  // The fraction is composed from these rather than printed as `⅓`, because the face draws that glyph
  // badly at key size and a borrowed one rendered nothing. A language that writes thirds differently
  // changes them here.
  "keypad.fraction_bar": "⁄",
  "keypad.fraction_denominator": "3",

  "package.unreadable": "This puzzle could not be read.",

  // ---- finishing -------------------------------------------------------------------------------
  "done.check": "Check",
  // ⚠⚠ **The board never says which cells are wrong, or how many.** Marking turns probing into a
  // better strategy than deducing; a count is a binary search over the board. Both were rejected in
  // `serve-flow.md` and this is the sentence that has to survive somebody deciding to be helpful.
  //
  // So one sentence for every wrong board, whatever is wrong with it. It says the board does not
  // balance -- which is a fact about the whole -- and offers nothing to bisect.
  "done.not_yet": "It doesn't balance yet.",
  // Shown when blanks remain. Distinct from the above because *incomplete* and *wrong* are different
  // states and a player who has not finished is not being told they made a mistake.
  "done.incomplete": "There are still empty cells.",

  // ---- the reveal ------------------------------------------------------------------------------
  "reveal.title": "Solved",
  "reveal.time": "Your time",
  "reveal.errors": "Mistakes",
  // ⚠️ The clock is invisible during play (§26) and appears here for the first time. The label says
  // whose time it is, because the comparison against other players is the paid feature and this is
  // not it.
  "reveal.at": "at",
  "reveal.versus": "vs",
  "reveal.close": "Back to the board",
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

/**
 * Swap the active catalogue. **A partial one is refused, so the active catalogue is always complete.**
 *
 * ⚠️ **This accepted any object at all**, and the test named for it swapped in a complete copy of
 * English and compared its keys with the same complete English. It exercised nothing: there was no
 * refusal to trigger. The first partial translation would have installed successfully and failed
 * mid-render, at whichever key `text()` reached first — the swap advertised a boundary the code did not
 * have.
 *
 * Missing *and* unexpected keys are both refused. An extra key is a translation that thinks it is
 * providing something the product does not ask for, which means the two have drifted whichever way it
 * happened.
 */
export function useCatalog(replacement) {
  const wanted = new Set(Object.keys(CATALOGS.en));
  const given = new Set(Object.keys(replacement ?? {}));
  const missing = [...wanted].filter((key) => !given.has(key));
  const extra = [...given].filter((key) => !wanted.has(key));
  if (missing.length || extra.length) {
    throw new Error(`catalogue is incomplete: ${missing.length} missing, ${extra.length} unexpected`);
  }
  table = replacement;
}

export const CATALOGS = { en };
