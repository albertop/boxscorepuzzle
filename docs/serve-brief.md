# The engine's brief — one puzzle, three interfaces

**Standing direction for every session that touches `serve/`.** Not notes from one conversation. Read
this before writing engine code, the same way `docs/design-boxscore-puzzle.md` is read before proposing
architecture.

**Decisions go in this file as they are taken.** Not in commit messages. This project has already lost a
decision that way: the footnote question ended with three documents disagreeing and none of them
recording what had been decided, so the reasoning had to be reconstructed from a measurement.

---

## 1. One puzzle, three interfaces

**The same puzzle on every device. Same erased cells, same given values, same board, same solution — on
phone, tablet and desktop.**

This is not a style preference and it is not negotiable. It follows from what the product is:

- **Everyone solves the same puzzle today.** A phone version with fewer blanks or fewer columns is a
  different game, played by a subset of the players, on the same date.
- **The share grid has to mean the same thing.** A grid produced from an easier board says something
  the reader will misread, and there is no way to annotate it without leaking the solution (§7).
- **Streaks and percentiles have to be comparable.** A duration measured against a smaller board is not
  the same measurement, and the paid tier is comparison (§26).

So the puzzle is one thing and the interface is three. **Never the other way round.**

⚠️ **This closes off the tempting escape from a layout problem.** When the phone cannot fit something,
the answer is to change the board — for everyone — or to change the phone's *presentation* of it. It is
never to give the phone less puzzle. §6 already says the board changes rather than the puzzle getting
trivial; this says the same thing one level down.

## 2. What actually differs, and it is substantial

Three interfaces, not one interface with three stylesheets.

**Phone.** A custom on-screen keypad taking roughly a third of the height, vertical scroll with the
header and totals pinned, everything tight. Measured, not estimated: 375px minus margins, six data
columns, 44px touch targets, a 24px slot column, a 66px label column (§6).

**Tablet.** The whole board fits without scrolling. The keypad can sit *beside* the board instead of
beneath it, which changes where the eye goes between entering a number and reading a total. There is
room to keep the reference sheet open, where the phone has to fold it away.

**Desktop.** A physical keyboard exists. The player types digits and moves with tab and the arrow keys.
**That is a different interaction, not the phone engine with more air around it** — the touch keypad
stops being the input path and becomes at most a fallback. There is space for the reference sheet,
candidates mode and the timer without any of them crowding the board.

## 3. The architecture that follows

**A shared core and three presentation layers. Not three implementations.**

The core owns:

| | |
|---|---|
| **Puzzle state** | which cells are filled, with what |
| **Validation and deduction** | is this entry consistent, what does the board now determine |
| **The event record** | duration, hints, errors, highest technique — seam C7 |
| **Reading the package** | the JSON contract, parsed and refused at the boundary |

**The core knows nothing about screens.** No layout, no input handling, no CSS, no device detection.
That is C5 restated: the engine carries no chrome, so it is buildable and testable **with no interface
at all**. If a change to the core requires touching a layer, the boundary is in the wrong place.

Each layer owns layout and interaction for its device, **and nothing else**. A layer that validates an
entry, decides what a cell means, or reads the package has taken work that belongs to the core, and the
three layers will drift the moment it does. That is this project's named failure shape — two places
encoding one rule — arriving in the client.

## 4. Phone first

**The phone is the hard constraint, and what fits there defines the board.** The other two receive more
space, never more content.

Building tablet or desktop first produces a board that cannot be reduced: decisions get made with room
that the phone does not have, and every one of them has to be undone. Building the phone first means the
other two are additive, which is a direction that always works.

## 5. Before the engine: the signature split

**Whoever verifies must not be able to sign** (§33). That is the property Ed25519 was adopted for, and it
is what an HMAC could not express.

**Status: the split already holds structurally, and nothing enforces it.**

| | |
|---|---|
| `boxscore_package/format.py` | the format, parsing, and boundary validation. Imports nothing from signing, nothing from `cryptography` |
| `boxscore_package/signing.py` | signing and verification. Imports `format`, and only in that direction |
| `boxscore_package/__init__.py` | a docstring. Importing the package pulls in neither half |

Verified by import closure, not by reading: importing `boxscore_package.format` loads no signing module
and no cryptography module.

⚠️ **What is missing is the check.** Nothing fails if someone adds a signing import to `format.py` — and
a rule with no check is this project's most repeated defect. A test asserting the closure is what makes
the split a contract instead of a habit.

⚠️ **And the mechanism that actually protects the browser is a different one.** The client is a browser
application: it will never import `boxscore_package` at all. What keeps verification out of it is
CLAUDE.md's rule that `forge/` and `serve/` share no code and that deployment ships `serve/` only. The
module split still matters, for a second reason: **it is what makes the format portable to the client
without dragging verification along with it.** When the JSON contract is re-expressed in the client's
language, `format.py` is the thing being read from — and it must not contain a verifier to copy by
accident.

**The client does not verify signatures.** Verification happens on the forge, before publication. A
signature checked in the browser proves nothing, because the code doing the checking arrived from the
same place as the thing being checked.

## 6. How this gets tested

**Devtools to iterate. A real phone to judge.** Those are different activities and only one of them
settles anything.

| | |
|---|---|
| **Chrome device mode** | the daily work — viewport width, column fit, scroll behaviour, whether the totals stay pinned, whether the keypad leaves enough board above it |
| **The operator's own phone**, against the dev server on the local IP | **anything being judged.** Not a checkpoint at the end; the way a decision is made |
| **Cloud real-browser services** | only for devices nobody owns, and only once the design is settled. Coverage, not judgement |

⚠️ **Devtools cannot reproduce what the phone decisions are actually about.** It does not give you the
system keyboard, scroll inertia, or the physical size of a touch target — and **the 44px target is
physical, not CSS pixels.** A device-mode viewport at 375px shows you the layout and tells you nothing
about whether a thumb can hit the cell. That is only verified with a finger.

**So: no design decision is taken without seeing it on a real device.** Not "verified afterwards" —
taken. A decision made in device mode and confirmed on the phone later is a decision made twice, and the
second one is the one that counts.

⚠️ **This project already paid for the desktop-viewer version of this mistake.** A prototype was reported
as not rendering; it was the cache. Time went into diagnosing a bug that did not exist, on the strength
of what one screen showed. The general form is the one CLAUDE.md names first — *look at the output* —
with the addition that **on which device** is part of the instruction, not an implementation detail of
it.

## 7. The share grid is not the engine's

§20 calls the share grid the main growth channel. That makes it important, and importance is exactly why
it will drift into the engine: it feels like part of the game, it is produced at the end of a solve, and
the engine is where the solve lives.

**It belongs above the engine, with the rest of the shell.** The division:

| | |
|---|---|
| **The engine** | produces the event record — seam C7 |
| **The shell** | reads that record and renders whatever is shareable |

The engine does not know what a share grid looks like, does not know the product exists, and does not
change when the grid changes. That is the same boundary as §5's environment separation, one level down:
a piece that only records cannot leak what it does not render, and **the grid must never leak the
solution or player names** (§7).

⚠️ **One thing is not yet decided, and it is named here rather than discovered in the code.** C7 records
duration, hints, errors and highest technique — all run-level. **If the grid turns out to be per-cell** —
a shape showing where the solve went well or badly, which is what makes these grids legible at a glance —
then the engine must emit **one additional derived value: a per-cell first-outcome vector**, in board
order, carrying nothing but *right first time / corrected / hinted*.

If that is needed, it is the **only** thing the engine emits for sharing, and three properties are not
negotiable: it is **derived**, never the solution or a subset of it; it carries **no values**, so a grid
cannot be read back into a board; and it is produced by the engine but **rendered by the shell**, so the
engine still does not know what a grid is.

**Until the grid's design exists, the engine emits the C7 record and nothing else.** Adding the vector
later is additive; taking a leaked value back is not.

## 8. The solution ships in the package, and that is accepted

**The answer is in the client, visible in devtools, by design.**

It follows from §23 with no room left: the day's puzzle is a static file, validation is client-side, and
the play path has no backend in it. A client that can validate an entry has the information to validate
it. There is no arrangement where the engine checks answers offline and does not hold them.

**This has been accepted since §9.** The streak is against yourself, nobody else's score is affected by
your cheating, and Wordle ran for years with the answer one click away in the page source.

⚠️ **The half that has to be written down is the second one.** The natural instinct on finding the answer
in the payload is to hide it — obfuscate it, hash it, fetch it on demand, check the entry server-side.
**Every one of those puts a network dependency in the play path, which §23 forbids**, and buys nothing:
obfuscation is a speed bump for the one player who wanted to look, and a server round-trip breaks the
game for everyone whenever the backend is down.

So: **do not hide the solution, and do not treat its visibility as a defect to be fixed later.** If a
future feature genuinely needs an unspoofable result — a competitive tier, a prize — that is a *separate
verified mode* with its own path, and it does not get to make the daily puzzle depend on a server.

## 9. Not in the engine

No accounts, no payments, no PWA shell, no streaks, no sharing, no archive.

Those come after, and none of them belongs in a piece that should be **runnable with a JSON file and
nothing else**. That sentence is the test: if the engine needs a server, a session or a network call to
start, something has been added that does not belong to it.

This is also what keeps §23 true — the day's puzzle is a static file and the game survives backend
failure — because a play path with no backend in it cannot acquire one by accident.

## 10. What to report while building

**What the real packages force that the design did not anticipate.**

The design document has been wrong about the board five times, and **every one was found by rendering
something and reading it** — never by reasoning about it. The zero-heavy board, the phantom rows, the
three centre fielders, the suffix that three decisions were secretly reading, the comparison page with
its own `grid()`.

Building against the six real packages in `serve/data/puzzles/` is how the sixth one gets found now
instead of in February. Render early, render often, and read what comes out.

---

## What the real packages forced that the design did not say

Found by rendering the six and reading them, in the first session. Each is a fact about the board, not
a preference.

**1. The pinned totals row is an input surface.** §6 pins it "because the totals are consulted
constantly", which reads as a read-only anchor. **Every one of the six erases batting totals** — H and SO
most often — and four of six erase a pitching total. So the pinned row needs full 44px targets, and
tapping a pinned cell must not move the board underneath it. What is *never* erased is the footnote
totals row and LOB, because the row identity does not close without the first and the global identity
cannot be expressed at all without the second.

**2. The line score is ragged, and a dash is not a zero.** Two of the six have eight offensive innings
against nine defensive ones — the home side leading after the top of the ninth never bats. A grid
assuming 9×2 is wrong for a third of real games, and **printing `0` in the unplayed half states a fact
that did not happen** while leaving every total balanced. Nothing arithmetic catches that.

**3. Two sections means two headers and two totals rows.** §6 says "header and totals row stay pinned",
singular. Batting and pitching have different columns, so there are two of each and they compete for
the same edges. The first version made the section title sticky above the column headings: the moment
you scrolled, `BATTING` covered `PA AB R H BB SO` and the board lost the only thing that says what a
column is. **The section name is not the header row** — found by scrolling and looking.

**4. A bare slot reference in the footnote reads as a count.** A sacrifice hit by the second batter
printed as `SH: 2`, which reads as *two sacrifice hits*. It is now `SH: #2`. The board already calls
that column `#`.

**5. ⚠️ The package could not say which club batted last — schema 3.** The line score has an offensive
half and a defensive half, and nothing said which of the two was at home. The first phone layer drew
`Away` over the offensive row **with nothing telling it so**, and on the reference set it was wrong:
`126c0496` is the Browns at home, leading 3–1, not batting the bottom of the ninth. *A label sits
outside the arithmetic*, which is exactly why every column total balanced while the board said something
untrue.

**It is not derivable and the client must not try.** A ragged line score determines it — the home side
leading after the top of the ninth never bats again — and four of the six are nine and nine. A client
inferring it *where it could* would be right sometimes and silently wrong the rest of the time, which is
worse than not knowing. The forge reads it from the game, so the forge writes it: `offense_is_home`, and
a new schema because a board that cannot name its sides is not a board with one field missing.

**6. ⚠️ One package labels a shared slot `5a 3B` / `5b 3B` — the same position twice.** That is the shape
the operator flagged on the forge side: a third baseman being replaced by another third baseman is
nearly impossible, and the rule adopted was that the label is the position of **entry**. It may be
legitimate — a pinch hitter who then takes the position — but it is the exact pattern that was a bug
last time. **Reported, not worked around**, because a client that compensates for it becomes the second
place encoding the rule.

**7. ⚠️ The manifest is a pointer and must never be cached; the packages are immutable and should be.**
Found the moment the six were regenerated: the generation directory changed, the manifest was rewritten
to name it, and the browser went on serving the old manifest **and the old JavaScript modules** — so a
correct client refused the packages as the wrong schema and the failure read as a code defect. That is
the second time a cache has produced a phantom bug here.

The fix is two-sided and the sides are opposite. `<generation>/<id>.json` can never change — a new one
gets a new generation — so it caches hard. `manifest.json` is the only thing saying which generation is
current, and **a stale pointer is indistinguishable from a stale build**. `no-store`, always. Development
uses `tools/dev_server.py`, which turns caching off entirely and strips conditional-request headers, so
what the page runs is what is on disk; production caching is nginx's job and takes the shape above.

**8. A retained generation the client cannot read is not a rollback target.** The writer keeps one
generation back, which is right — but the retained one is schema 2 and this client refuses it by design.
Rolling back would mean rolling back the client too. Recorded rather than resolved: it is only a real
problem once inventory exists, and the honest fix is that a schema change invalidates retained
generations rather than pretending they are usable.

## Typography

**Roboto Condensed, self-hosted, at three weights. One family, not two.**

**Tabular figures are the non-negotiable property**, and they are asserted rather than assumed: the test
measures ten `1`s against ten `8`s and requires the same pixel. Without them a `1` is narrower than an
`8`, so a column's width depends on the values in it and **the grid shifts as the player fills it** —
the most visible possible defect on a board that is ninety per cent numbers. Set on `body`, not on the
tables, because the scoreboard, the footnote line and the keypad are numbers too.

**One family at three weights, not a display face beside a body face.** The clubs use two because they
lay out full pages; this has 375 pixels, and two families on that width compete for the same small
space. The difference comes from weight and colour.

**Self-hosted, never linked.** §23 requires the day's puzzle to be playable with the backend down, and a
webfont fetched from a third party is a dependency in the play path. The failure is worse than a missing
glyph: the board would lay out in a fallback's metrics and **the columns would stop lining up**, which
is the one thing a grid of numbers cannot absorb. `tools/fetch_fonts.py` downloads and subsets — 68 KB
for three weights, against 208 KB for the plain latin subset — and **derives the character set from the
string catalogue and the packages** rather than from a typed list, because a hand-written list is a
second copy that goes stale the first time a string is added.

Both candidates are SIL Open Font License 1.1, checked before shipping: this product charges money, and
a licence that forbids that forbids launch. Nearly every club body face — Trade Gothic, Frutiger,
Tungsten, Akzidenz — is licensed, which is what settled the shortlist.

### ⚠️ The comparison I got wrong

IBM Plex Sans Condensed was the other candidate and I recommended it, on the character the instruction
named: its `1` has a foot serif where Roboto's is a bare stem, and its `I` and `l` are clearly distinct
where Roboto draws both as the same vertical stroke.

**The specimen contained `I` and `l` because I put them there.** This board never draws either one. The
cells hold digits; the labels are position abbreviations — `CF`, `SS`, `2B`, `RP-1` — and there is no
text cursor for a `1` to be mistaken for, because entry is by keypad and a cell shows a value, never a
caret. **The confusion the comparison was decided on cannot occur here.**

Judged on what the board actually renders, Roboto's narrower figures leave more air in six columns and
its fractions are cleaner on the keypad. The operator's preference was the better call, and the lesson
is the older one wearing new clothes: *a sample that evaluates the board is rendered with the board's
content*. A glyph specimen is not the board, and choosing from it imported a problem the board does not
have.

## Colour, and what each colour is allowed to mean

Four things carry meaning and no more. **Every one of them is spent, so a fifth has to displace
something rather than be added.**

| | |
|---|---|
| **Fenway green** | what is *given* — the scoreboard and the section headers, the parts the player never touches |
| **Amber** | the selected cell |
| **Cream** | the row and column that cell shares an equation with |
| **Blue** | what the player wrote, and the board's own footnote references |

**The keypad is neutral grey on purpose.** It was Fenway green for one render, and that said the keypad
and the scoreboard were the same kind of object when they are opposites: one is given and untouchable,
the other is where the player acts. It is also a third of the screen, and a third of the screen in
saturated green competes with the board.

⚠️ **Red is reserved for errors and is not spent on anything else.** Entered values were red for one
render, and it was wrong twice over: red is the one colour every player reads as *this is wrong*, so
spending it on "I typed this" leaves nothing for the case where no other colour works — and in a
deduction puzzle what the player types is not provisional. Once it balances it is as settled as what was
given, so red said *tentative* and said *incorrect*, and neither was true.

**Blue rather than the givens' black in bold**, and the totals row is what settled it: weight cannot
mark an entry there, because that row is bold already — and the real packages erase batting and pitching
totals, so it is an input surface, in the one row every column sum closes on. Colour works everywhere;
weight had a hole exactly where the board is most consulted. One blue for both meanings rather than two
a shade apart: the eye files two similar blues as one category and then discovers they are not.

⚠️ **The pale ground means one thing: empty and editable.** A filled cell keeps its border and goes
white, so only the digit carries the colour. Filled cells used to keep the pale ground, and a blue `5`
on pale blue read like an empty pale-blue cell at a glance. It also protects the three empty states —
plain, cream, amber — which are already close to the limit of what separates without looking twice.
**Check them on a device before adding a fourth.**

## ⚠️ Noticed in the render: a blank that is a lookup, not a deduction

The `H` total was erased, and the scoreboard prints `AWAY H 15` two centimetres above it. The cell was
copied, not deduced.

**It is not a bug.** `line_score.offense_hits = batting_totals.hits` is a real equation the solver
carries, in the `column_sum` family. But it is a **two-term** equation with one unknown — the cheapest
move on the board, and far cheaper than a column sum over nine rows — so the solver counts a step where
the player does a lookup.

Four cells are in this position: `batting_totals.R`, `batting_totals.H`, `pitching_totals.R` and
`pitching_totals.H`, all verified equal to their line-score counterpart in every reference solution.

**Measured on the six reference packages:** every single one erases exactly one of them — five times
`batting_totals.H`, once `pitching_totals.R`. Six of 204 blanks, 2.9%.

**What is not yet measured, and what would change if it were:** whether the rate holds across the pool,
and whether these steps inflate the reported chain length and stall count. If they do, the generator
should refuse to erase a total the scoreboard already prints, or the solver should not count the move —
which is a generator change, so the measurement is decision-bearing rather than curiosity. It needs the
database and belongs with forge work, not here.

⚠️ Worth naming for what it is: **filler wearing a new face.** The pruning experiment was about blanks
that add nothing to the solve, and this is the same thing appearing in the one place nobody looked —
the row that was assumed to be a read-only anchor until the real packages said otherwise.

## Rendering for judgement: use the package's own solution

⚠️ **A rendered board must balance.** The demo values in the first renders were invented — plausible
digits typed to show a colour — and a board that does not balance **trains the eye to accept boards that
do not balance**. Five defects in this project were found by a person reading a printed board, and every
one of them was a board that looked fine until it was read properly. A screenshot with made-up numbers
spends that instrument.

Fill from `game.cells()`'s own `answer`, and assert nothing was mistyped before believing the picture.

## ⚠️ A right answer reached by a wrong argument — the typeface

Recorded as such, because **the argument is what gets reused and the answer is not**.

I recommended IBM Plex over Roboto Condensed, and the recommendation was correct. The argument was not:
I decided it on a specimen containing `I` and `l`, which **this board never draws** — the cells hold
digits and the labels are position abbreviations. When the operator preferred Roboto I switched, still
without noticing that my reason had been wrong for a reason that did not rescue Roboto.

What actually mattered was in the same specimen and I let it ride: Roboto draws `1` as a bare stem with
no foot, and `1` is a character this board renders constantly. The operator saw it on the rendered board
and said so, and the check confirmed the face had loaded — so the bare `1` was the design, not a webfont
that failed to arrive.

**The lesson is the recorded one wearing new clothes**: a sample that evaluates the board is rendered
with the board's content. A glyph specimen is not the board, and choosing from one imported a
consideration the board does not have while burying the one it does.

## The erased footnote: drawn as a cell — `v05-P1-02`

**An erased footnote term is the same cell the player has been filling all along, drawn somewhere
else.** Same border, same pale ground, same blue when filled, same selection, same keypad. The label and
the slot reference stay text; only the number is a cell.

    LOB: 8    SH: 1 [ ]#7    HBP: 0 [ ]#4 [ ]#5

**Why the grid cell rather than a control of its own.** It costs nothing to explain — there is no new
vocabulary, no icon, no dropdown, no modal — and every new element on 375px competes with the board.
Four colours already carry meaning and a fifth would have to displace one.

**The reference is black.** It was blue, and blue means *the player typed this*; the reference is given.
Two meanings on one colour is why it did not read right.

**The touch target is the label and the box together.** Tapping `SH:` selects that term's first unknown,
so the box can stay 26px in a line of text while the thing a thumb aims at stays wide enough.

**Where it sits in the traversal: last, after the totals.** The footnotes are a separate block and a
player deals with them at the end. On the phone that is DOM order, which is what the selection walks.

⚠️ **The drawing was not cosmetic: without it the board could not be finished.** Columns whose total is
zero were skipped entirely, so their erased cells were rendered nowhere — **18 of one board's 39 blanks
had no element to tap**. Asked of the engine rather than eyeballed: every blank now resolves to a node.

## ⚠️ What the drawing exposed: a third of every board is typing zeros

Rendering it made the real problem visible, which is the point of rendering it.

| | blanks | footnote blanks | in a **zero-total** column | share of all blanks |
|---|---:|---:|---:|---:|
| six reference packages | 204 | 91 | **61** | **30%** |

**A column whose total is zero has every cell zero.** There is nothing to deduce and nothing to look
up: the player types a zero because the board asks, not because anything follows from it. On screen it
is now the largest single element — four wrapped lines of empty boxes under a nine-row grid.

**This is the same shape as the scoreboard duplicate, an order of magnitude larger.** That one was 2.9%
of blanks and was removed from the erasable set on the argument that a lookup counted as a deduction is
a lookup counted as difficulty. This is 30%, and it is not even a lookup.

The group run agrees from the other direction: a slot group carrying **no** live term blocks the rest of
the board in only **6%** of trials, against 57–74% for a group with one.

**The proposal, not yet implemented because it is a generator change and it needs the same before-and-
after the scoreboard duplicates are getting:** exclude from `erasable()` any footnote cell whose
column total is zero — same place, same shape, beside `SCOREBOARD_DUPLICATES`. Note the rule is about
the *column*, not the cell: a zero in a column totalling three is a real deduction, because working out
that this batter is not one of the three is the deduction.

## Still open, and what would close each

**Nothing here is waiting on effort.** Each needs a judgement or a piece that does not exist yet.

**The three empty states, on a real device.** Plain, cream on the active row or column, amber on the
active cell. That is correct and close to the limit of what separates at a glance, and device mode
cannot answer it — the question is about a thumb's distance from a screen, not about pixels. **Check
before adding a fourth.**

**Whether the share grid is per-cell**, and therefore whether the engine must emit a derived
first-outcome vector. Until that design exists the engine emits the C7 record and nothing else; adding
the vector later is additive, taking a leaked value back is not. See §7.

**⚠️ The six reference packages predate the scoreboard-duplicate exclusion** and still carry an erased
`H` total. Regenerating needs the database.

**Tablet and desktop do not exist.** Phone first was the decision and the other two are additive from
it. Neither should start before the phone has been used on a phone.

## Decisions taken

Recorded here as they are made, with the date and the reason.

**2026-08-19 — one puzzle, three interfaces.** The operator's decision, stated above. The alternative
considered and rejected: a reduced board on phone. Rejected because the share grid, streaks and
percentiles all assume one puzzle per day, and a per-device board silently breaks all three.

**2026-08-19 — phone first.** Because the phone is the binding constraint and the other two are
additive from it.

**2026-08-19 — the client does not verify signatures.** Verification is a forge property; a browser
verifying a package it received from the same origin as the verifier is theatre.

**2026-08-19 — a real device decides, devtools iterates.** No design decision is taken without seeing it
on the operator's phone. Device mode does not reproduce the system keyboard, scroll inertia, or the
physical size of a 44px target.

**2026-08-19 — the share grid lives in the shell, not the engine.** The engine produces the C7 event
record; whatever renders a shareable result reads it. Left open, deliberately and in writing: whether the
grid is per-cell, and therefore whether the engine must emit a derived first-outcome vector. Until that
design exists the engine emits the C7 record and nothing else.

**2026-08-19 — the sections name their side, and the package has to say which.** `AWAY BATTING` over
one section and `HOME PITCHING` over the other, because the board is one team's offence against the
other's staff and a player could not tell whose batting order they were reconstructing. This forced
schema 3: the client cannot infer which side batted last and must not guess. The line score also swaps
its rows so the visiting side prints on top, which is where a line score puts the team that bats first.

**2026-08-19 — the section header's ground is the dark green `rgb(31, 54, 46)`.** Chosen by rendering
three candidates as a parameter of the real renderer, and the two losers were **deleted** rather than
left live — three options in a stylesheet is three things every future change has to keep working. The
finding worth keeping: the first two candidates were a near-black green and a near-black grey, and *at
near-black the hue does not read*. They were indistinguishable in situ, so "take it from the
scoreboard's family" bought nothing until the green was allowed to be green.

**2026-08-19 — the solution ships in the package and stays visible.** Hiding it means a network
dependency in the play path, which §23 forbids, and it buys nothing §9 has not already accepted.
