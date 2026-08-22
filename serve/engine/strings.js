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
  // ⚠️ No count on it, in either interface. The key going dead is the signal, and an accessible name
  // carrying a number the screen does not show would be two interfaces disagreeing.
  "keypad.hint": "Hint",
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
  // The heading, and the panel's accessible name. It says what the player did rather than what the
  // board is: the payoff is the object in front of them, not a verdict on their performance.
  "reveal.title": "You rebuilt it.",
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
  "reference.column_sum": "Totals = the sum of the rows above",
  "reference.global_name": "Each team, over the game",
  "reference.global": "PA = Outs + Runs + LOB",
  "reference.cross_team_name": "The two halves",
  "reference.cross_team": "Team H = hits allowed by the opposing pitchers (the same for BB, SO and R)",
  "reference.batting_order_name": "The batting order",
  // ⚠️⚠️ **The usable form of the rule, not its arithmetic.** Two earlier versions stated the
  // cycle as a formula and then as a worked example: correct, and both asked a player mid-solve to do
  // modular arithmetic. What a solver actually applies is the consequence — dealing round a circle
  // means the slots can only step down — so a single glance at the PA column says whether it is
  // possible. This is the one family nobody can infer from a board, so the sheet has to give the form
  // that gets used rather than the form that is true.
  "reference.batting_order": "Turns are dealt around the order, so going down the slots, plate appearances never go up.",
  "reference.innings_name": "Innings",
  "reference.innings": "Outs = 3 \u00d7 innings pitched",
  "reference.bounds_name": "And nothing can break these",
  "reference.bounds": "AB \u2265 H \u00b7 ER \u2264 R \u00b7 nothing below zero",

  // -------------------------------------------------------------------------------------------
  // What the page itself says it is: the tab, the bookmark, the search result. (v36-P2-17, P3-46/47)
  //
  // ⚠️⚠️ **All three pages shipped the identical hardcoded `<title>boxscore</title>`** — one one-word
  // title for three distinct pages, spelled in three HTML files *and* here, four copies of one
  // user-facing string. It was invisible to the C11 scans because those read `.js`, and this lived in
  // markup. **The `<title>` is the most player-visible string there is** — browser tab, history,
  // bookmark, and the headline of every search result — and "boxscore" alone competes with a
  // dictionary word while saying nothing about the product.
  //
  // ⚠️ **The language tag is a catalogue entry too**, so the page's `lang` and its words cannot
  // disagree. `<html lang="en">` is still written in the markup, because a crawler and a screen reader
  // both need it before any script has run; `applyHead` keeps it in step when the catalogue changes.
  "catalog.lang": "en",
  "page.landing.title": "boxscore — the daily baseball logic puzzle",
  "page.board.title": "Today’s puzzle — boxscore",
  "page.tutorial.title": "How to play — boxscore",
  // ⚠️ The board and the tutorial get their own sentence; the landing page composes its description
  // from the two it already shows, so the pitch a visitor reads and the pitch a search result shows
  // cannot drift apart. See `applyHead`.
  "page.board.description": "Rebuild today’s real major-league boxscore from the numbers that are left. One puzzle a day.",
  "page.tutorial.description": "The five relations that solve every board, one at a time. No baseball knowledge needed.",

  // -------------------------------------------------------------------------------------------
  // The landing page (`docs/serve-flow.md` §1). Every visit lands here, not only the first.
  // -------------------------------------------------------------------------------------------
  // ⚠️ **`boxscore puzzle`, not `boxscore`.** The word alone does not say it is a game — it is the
  // baseball term for the table itself — and it matches the domain, which is what somebody types when
  // they try to come back.
  "landing.name": "boxscore puzzle",
  // ⚠️ **It says what this is and what it is not, in that order.** The second sentence is not filler:
  // the first thing a visitor gets wrong about this product is thinking it is a trivia game, and that
  // mistake is the line separating it from Immaculate Grid (§2, anti-goals).
  "landing.tagline": "Rebuild a real baseball boxscore using nothing but logic.",
  // ⚠️ **The second sentence says *daily*, and it used to repeat the tagline.** It read "no trivia, no
  // guessing; every missing number can be worked out" — and *can be worked out* is what "nothing but
  // logic" above already says. **What was missing from the page entirely is that it is daily**, which
  // is the thing that makes it a product rather than a puzzle.
  "landing.not_trivia": "No trivia, no guessing. A new puzzle every day.",
  "landing.play": "Play today\u2019s puzzle",
  "landing.how_to_play": "How to play",
  // Shown in place of the tagline's call to action once today is done, beside the time.
  "landing.finished": "You rebuilt it.",

  // ⚠️⚠️ **A licence condition, not a courtesy.** Retrosheet's terms require this notice wherever their
  // data is used, and every board in this product is built from their event files. It is quoted
  // verbatim: paraphrasing an attribution clause is how a condition stops being met.
  "landing.retrosheet":
    "The information used here was obtained free of charge from and is copyrighted by Retrosheet. " +
    "Interested parties may contact Retrosheet at www.retrosheet.org.",

  // -------------------------------------------------------------------------------------------
  // The tutorial (`docs/serve-flow.md` §1b). Five steps, one per relation family, and skippable.
  // -------------------------------------------------------------------------------------------
  "tutorial.title": "How to play",
  "tutorial.progress": "Step {step} of {total}",
  "tutorial.back": "Back",
  "tutorial.next": "Next",
  "tutorial.skip": "Skip",
  // ⚠️ **Said out loud, because otherwise it reads as a bug.** The board in the tutorial is four
  // batters, one pitcher and three columns; a real one is six columns and up to thirteen rows. A
  // player who is not told will spend a step wondering why it looks wrong instead of watching the
  // relation work.
  "tutorial.made_up": "A made-up boxscore, smaller than a real one.",
  "tutorial.blank_prompt": "One number is missing. Here is how you get it.",
  "tutorial.step.row_identity":
    "Every time a batter comes to the plate it counts as a plate appearance \u2014 whether he hit, "
    + "walked or anything else. So a batter\u2019s PA is his AB plus his walks, plus the rare ways of "
    + "reaching that are neither.",
  "tutorial.step.column_sum":
    "The Totals row is the sum of the rows above it, column by column. It works downwards to find a "
    + "total, and upwards to find the one row you are missing.",
  "tutorial.step.cross_team":
    "A hit by a batter is a hit allowed by the pitcher who threw it. The two halves of this board are "
    + "the same game seen from opposite sides, so their totals have to agree \u2014 for H, BB, SO and R.",
  "tutorial.step.global":
    "Every plate appearance ends one of three ways: the batter is out, he scores, or he is still on "
    + "base when the inning ends. Nothing else can happen, so the team\u2019s PA is exactly its outs "
    + "plus its runs plus the men it left on base. "
    // ⚠️ The board never prints outs — the pitching column is innings pitched — so the sentence that
    // crosses the two belongs in the step that needs it, not only on the reference sheet.
    + "The board shows innings rather than outs, and an inning is three outs.",
  // ⚠️ Last on purpose. See `docs/serve-flow.md` §1b: the other four are visible in the grid, and
  // nothing on screen announces that turns are dealt around the order.
  "tutorial.step.batting_order":
    "Turns go around the lineup in order, one after another, and never skip. So reading down the "
    + "slots, plate appearances never go up \u2014 a batter lower in the order can never have batted "
    + "more times than the one above him.",
  // ⚠️⚠️ **The worked arithmetic is copy, and it was spelled in code.** (v36-P2-09) Four of these are
  // pure arithmetic and one reads "2 innings = 6 outs" — English words, 19px bold, on screen, in a
  // project whose C11 seam is mandatory from day one. All five are here rather than only the offender:
  // a rule that holds for one member of a set and not the others is a rule nobody can apply, and a
  // language that writes the bound the other way round needs the whole line, not a word of it.
  "tutorial.sum.row_identity": "2 = 1 + 1",
  "tutorial.sum.column_sum": "3 + 1 + 2 + 2 = 8",
  "tutorial.sum.cross_team": "1 = 1",
  "tutorial.sum.global": "2 innings = 6 outs \u00b7 9 \u2212 6 \u2212 1 = 2",
  "tutorial.sum.batting_order": "2 \u2264 ? \u2264 2",

  "tutorial.reference_hint":
    "All five stay one tap away while you play \u2014 the button marked The relations.",
  "tutorial.finish": "Start today\u2019s puzzle",

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

/**
 * `1913-08-17` as a reader reads it. The month names are the catalogue's, not any renderer's.
 *
 * ⚠️ **Here rather than in `finish.js`, because a second page needs it.** It was private to the reveal;
 * the landing page prints today's date on its button, and a copy of six lines is how one screen ends up
 * saying `August 17, 1913` while another says `17 August 1913` in the same language.
 */
export function longDate(iso) {
  const [year, month, day] = iso.split("-");
  return fill("date.long", { month: text(`month.${Number(month)}`), day: String(Number(day)), year });
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
