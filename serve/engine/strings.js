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
  "keypad.hint": "Hint",
  // The accessible name, which has to carry the count: a key announced as "Hint" says nothing about
  // whether pressing it will do anything.
  "keypad.hint_left": "Hint, {left} left",
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
  "done.not_yet": "Something doesn't add up yet.",
  // Shown when blanks remain. Distinct from the above because *incomplete* and *wrong* are different
  // states and a player who has not finished is not being told they made a mistake.
  "done.incomplete": "Still a few cells to go.",

  // ---- the reveal ------------------------------------------------------------------------------
  "reveal.title": "Solved",
  "reveal.time": "Your time",
  // ⚠️ The clock is invisible during play (§26) and appears here for the first time. The label says
  // whose time it is, because the comparison against other players is the paid feature and this is
  // not it.
  "reveal.close": "Back to the board",
  // ⚠️ Beside the time, because a shared result has to carry both. One minute with three hints and one
  // minute with none are two different results, and that is the whole reason hints are allowed at all.
  "reveal.hints": "Hints used",
  "reveal.no_hints": "None",
  // ⚠️ The way back to the clipping from a finished board. It replaces the keypad, because a board that
  // cannot be typed into does not need one — and the boxscore has to stay reachable or closing the
  // reveal would throw away the thing the player earned.
  "done.see_boxscore": "See the boxscore",
  // ⚠️ `reveal.at` and `reveal.versus` are gone. They composed `SLA vs BOS at 1913-08-17` — a heading
  // that named the clubs by their Retrosheet keys and dated the game the way a database does. From
  // schema 5 the package carries the real names, and the heading is a result line: winner first, the
  // way a newspaper set it.
  "reveal.score_separator": ", ",
  "reveal.batting_columns": "AB R H RBI BB SO",
  "reveal.pitching_columns": "IP H R ER BB SO",
  // Not drawn from these — the renderer reads the column list — but a translator needs to see the
  // canonical order somewhere, and the headings below are what actually appear.
  "printed.ab": "AB",
  "printed.r": "R",
  "printed.h": "H",
  "printed.rbi": "RBI",
  "printed.bb": "BB",
  "printed.so": "SO",
  "printed.outs": "IP",
  "printed.er": "ER",
  "printed.pitchers": "Pitching",
  // ⚠️ The footnote line is prefixed with the club it describes, because the package carries footnotes
  // for **one** club: they belong to the board's batting side and the other half of the game has its
  // own, which no package holds. A line printed without the prefix would read as a statement about
  // both clubs and be silently false about one of them.
  // ⚠️ A colon, not a dash. The terms below already use a dash — `SH—Balenti` — and the first version
  // used one here too, so the line read `St. Louis Browns — SH—Balenti`: two dashes doing two
  // different jobs in eight characters. Found by reading the rendered line, which is the only way this
  // kind of thing is ever found.
  "printed.notes_for": "{team}:",
  // What a printed boxscore put between a term and its carriers: `Sacrifice hit—Shotton`. Tight, with
  // no spaces, because the line is a run-on and the separator is what breaks it into readable pieces.
  "printed.note_separator": "—",

  // ---- the reference sheet ---------------------------------------------------------------------
  // ⚠️⚠️ **The same set the printed strip carries, plus the batting order, which the printed strip does
  // not have.** The strip predates the fifth family. That is a defect in the hand-solve pack and it is
  // recorded in `todo.md`; the pack is not being regenerated because it must not move while it is being
  // solved. On screen there is no such constraint, so the screen carries all five.
  //
  // ⚠️ **This is not a hint and does not cost one.** It is the information §8's tutorial teaches, made
  // available when it is needed instead of only once at the start. A game that measures whether you
  // remembered `PA = Outs + Runs + LOB` is measuring memory, not deduction.
  "reference.title": "The relations",
  "reference.close": "Close",
  "reference.row_identity_name": "Every batting row",
  "reference.row_identity": "PA = AB + BB + HBP + SF + SH + CI",
  "reference.column_sum_name": "Every column",
  "reference.column_sum": "Totals = the rows above them",
  "reference.global_name": "Each team, over the game",
  "reference.global": "PA = Outs + Runs + LOB",
  "reference.cross_team_name": "The two halves",
  "reference.cross_team": "Team H = hits allowed by the opposing pitchers (the same for BB, SO and R)",
  "reference.batting_order_name": "The batting order",
  "reference.batting_order": "PA dealt round nine slots: each gets T \u00f7 9, and the first T mod 9 get one more",
  "reference.innings_name": "Innings",
  "reference.innings": "Outs = 3 \u00d7 innings pitched",
  "reference.bounds_name": "And nothing can break these",
  "reference.bounds": "AB \u2265 H \u00b7 ER \u2264 R \u00b7 nothing below zero",

  // ---- dates -----------------------------------------------------------------------------------
  // ⚠️ Month names rather than `1913-08-17`. The reveal is the one screen written for a reader rather
  // than for a parser, and an ISO date on it reads as a field that escaped. Keyed by number so the
  // renderer indexes rather than parses, and so a language that orders the parts differently changes
  // `date.long` alone.
  "date.long": "{month} {day}, {year}",
  "month.1": "January",
  "month.2": "February",
  "month.3": "March",
  "month.4": "April",
  "month.5": "May",
  "month.6": "June",
  "month.7": "July",
  "month.8": "August",
  "month.9": "September",
  "month.10": "October",
  "month.11": "November",
  "month.12": "December",
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

/**
 * A string with its placeholders filled. **An unfilled placeholder throws**, like an unknown key.
 *
 * ⚠️ Same reasoning as `text`: a template that ships with `{month}` still in it is a catalogue that
 * stopped being complete without telling anyone, and it renders as something a reader will read as a
 * bug in the data rather than in the copy. The absence of a value must not read as the presence of one.
 */
export function fill(key, values) {
  return text(key).replace(/\{(\w+)\}/g, (_, name) => {
    if (!Object.hasOwn(values, name)) throw new Error(`no value for {${name}} in ${key}`);
    return values[name];
  });
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
