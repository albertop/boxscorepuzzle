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

## 6. Not in the engine

No accounts, no payments, no PWA shell, no streaks, no sharing, no archive.

Those come after, and none of them belongs in a piece that should be **runnable with a JSON file and
nothing else**. That sentence is the test: if the engine needs a server, a session or a network call to
start, something has been added that does not belong to it.

This is also what keeps §23 true — the day's puzzle is a static file and the game survives backend
failure — because a play path with no backend in it cannot acquire one by accident.

## 7. What to report while building

**What the real packages force that the design did not anticipate.**

The design document has been wrong about the board five times, and **every one was found by rendering
something and reading it** — never by reasoning about it. The zero-heavy board, the phantom rows, the
three centre fielders, the suffix that three decisions were secretly reading, the comparison page with
its own `grid()`.

Building against the six real packages in `serve/data/puzzles/` is how the sixth one gets found now
instead of in February. Render early, render often, and read what comes out.

---

## Decisions taken

Recorded here as they are made, with the date and the reason.

**2026-08-19 — one puzzle, three interfaces.** The operator's decision, stated above. The alternative
considered and rejected: a reduced board on phone. Rejected because the share grid, streaks and
percentiles all assume one puzzle per day, and a per-device board silently breaks all three.

**2026-08-19 — phone first.** Because the phone is the binding constraint and the other two are
additive from it.

**2026-08-19 — the client does not verify signatures.** Verification is a forge property; a browser
verifying a package it received from the same origin as the verifier is theatre.
