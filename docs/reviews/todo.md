# Code review v01 — accepted findings

Source: `code_review_v01.md` (2026-08-18). Every finding was accepted; `non-issue.md` records the one
scope correction rather than a rejection.

Each item closes only when the fix is in place **and** a test exists that fails without it. CLAUDE.md's
rule applies: a check that never fires cannot be told apart from a check that is broken.

---

## v01-P1-1 — Loader shape and row queries used different predicates

**Status: fixed.**

The shape query counted a row that contributed anything; the row query loaded only rows with
`B_PA > 0`. A pinch runner scores without batting, so he was counted towards the roster cap and then
left off the board, taking his run with him.

Worse than a miscount: the loader sums its own totals, so the board stayed self-consistent and the
identities still balanced. This is the exact failure mode CLAUDE.md now names.

**What I did.** Defined the predicate once, as `CONTRIBUTED` in `discovery/difficulty-metrics/measure.py`,
and interpolated it into both queries. Two copies of a rule drifted apart within a day of each other;
there is now one.

**Evidence it was real, and that it is fixed.** The loader sweep cross-checks loaded totals against
`retroGameLogs`, which is a different table. Before: **8 directions in 480 disagreed on runs**. After:
**zero**. That also closes the eight discrepancies left open this morning — they were this bug.

---

## v01-P1-2 — Package JSON parsed without boundary validation

**Status: fixed.**

`Board.from_json` and `Package.from_json` turned raw JSON into tuples with no checks at all — the
review is exact: not one `len()` and not one `isinstance`. A package that was valid JSON and
malformed as a board died later as a `TypeError` inside the arithmetic instead of being rejected.

**What I did.** Validation at the boundary in `boxscore_package/format.py`: exact row widths against
the column tuples, cells that are a whole number or null, footnote rows matching the lineup, the
footnote line complete because §6 never erases it, every line score field present, and metadata that
is an object. Everything raises `PackageError`, which is a rejection rather than a crash.

Two details worth naming. **A bool is an `int` in Python**, so `true` in a JSON cell would have become
a 1 on the board; it is excluded explicitly. And the `from_json` signatures now take `object` rather
than `dict[str, Any]` — the annotation was a polite fiction over parsed JSON, and typing it honestly
is what makes the guards reachable instead of dead code the checker flags.

**Tests.** `tests/verify/test_boundary.py` — wrong row width, a string cell, a bool cell, a section
that is not a list, a hole in the footnote line, footnote rows that do not match the lineup, a line
score missing a field, metadata as a list. Plus the other half: a well-formed package still reads,
because a boundary check that rejects valid input is worse than none.

## v01-P1-3 — Signature verification passes when the secret is missing

**Status: fixed.**

`check_signature()` returned success when `secret is None`. A publish or import path with an unset
secret verified nothing and reported a pass — CLAUDE.md's "the absence of a check reading as the
presence of a passing one", exactly.

**What I did.** `secret` is now a **required** keyword argument with no default, so no call site can
forget it, and `None` raises. Skipping the check is possible only by passing the `UNSIGNED` sentinel,
which makes the skip a thing a caller says out loud. Every test and discovery call site was updated
to say it.

`None` stays in the signature deliberately: a misconfigured secret arrives as `None` at runtime
whatever the annotations claim, and that is the one place able to catch it.

**Tests.** A missing secret raises rather than passing; `verify` has no default to forget and the
parameter is keyword-only; and the deliberate opt-out still works.

## v01-P2-4 — Two names for catcher's interference across the boundary

**Status: fixed.**

The model called the fourth footnote term `reached_on_interference`; the package schema called it
`catcher_interference`. No data moved wrongly, because the adapter writes positionally — which is
precisely what made it worth fixing rather than reassuring. A reader taking the column **by name**
would have displayed or validated the wrong concept while the tuple order kept agreeing with itself.

**What I did.** Renamed to `catcher_interference` everywhere — model, identities, discovery, tests,
docs. CLAUDE.md already settled that CI is the correct baseball abbreviation, so the schema's term
was the right one to keep.

**Test.** The model's dataclass fields are asserted equal to the package's column tuples, for all
three sections. Two vocabularies at a boundary cannot drift apart silently again.

## v01-P2-5 — Discovery scripts depend on ambient import path state

**Status: fixed.**

Some scripts patched `sys.path`, others imported `measure` or `compressibility` and relied on being
launched from `forge/`. The README's own commands failed without a `PYTHONPATH` — I hit it myself
running `build.py` earlier today.

**What I did.** `discovery/bootstrap.py` computes the root from its own file and puts the forge
package and the shared helpers on the path, idempotently. Seven scripts now call it and their ad-hoc
`sys.path` lines are gone.

The rule behind it, now in CLAUDE.md: **a discovery result that cannot be re-run identically is not
evidence.**

## v01-P2-6 — Hand-solve pack can violate its own quotas

**Status: fixed.**

`choose()` filled the chain quotas and then, if a required trait was missing, appended a board and
dropped `chosen[-2]` — an arbitrary earlier board, not one picked to preserve the rung, the era
allowance or the uncertified share. The pack is a launch gate whose constraints were **printed and
believed** rather than checked.

**What I did.** Two changes. The trait fix now *swaps* rather than appends: the replacement takes the
place of a board at the same chain target, the same certification and the same side of 1950, so every
quota survives. And `audit()` runs after selection and raises unless the pack is what it claims —
fifty boards, every rung at its quota, the uncertified share within two, the era allowance, one board
per game, and both cases the tutorial has to teach.

**Tests.** Eight, and seven of them are the audit *rejecting*: a missing rung, too few boards, the
uncertified share drifting, the era allowance exceeded, a repeated game, no suffixed label, no live
footnote. An audit that never fires cannot be told apart from one that is broken — and the missing
rung is not hypothetical, it happened when weighted sampling produced zero boards at chain 5.

## v01-P2-7 — Generated HTML interpolates values without escaping

**Status: fixed.**

Both renderers built HTML from database values — labels, surnames, notes, game ids — and the
prototype handed them to `innerHTML`. Not production-facing, but these pages are how boards get
judged, so a value carrying markup would corrupt a decision long before it ran anything.

**What I did.** An `esc()` in each renderer, applied to every interpolated value: 14 call sites in the
flat Python renderer, 10 in the prototype's JavaScript. The board select already used
`new Option(...)`, which sets text rather than markup, so it was left alone.

Verified by rebuilding the fifty-board pack end to end — the escaping is on the path every board
takes.

## v01-P3-8 — Discovery scripts index fixed positions after filtering

**Status: fixed.**

`pool[6]` and `widest[0]` after a gate, an era window and an identity filter. Safe on today's data,
and an `IndexError` with no explanation the day a filter tightens.

**What I did.** `require(sample, minimum, what, filters)` in the shared bootstrap raises a message
naming what was being measured, how many directions it needed, how many it got, and which filters
were applied. Both sites now call it before indexing.


---

## What the round cost, and what it says

Eight findings, all real, all fixed, each with a test that fails without the fix. Two things worth
recording beyond the fixes.

**The review caught a defect that was live.** v01-P1-1 was contaminating a measurement running at the
time it was read. My own fix that morning had been applied to one of the two queries because the
replacement pattern missed the `d.` prefix — a half-applied fix reads exactly like a whole one. The
re-measurement was killed and restarted.

**And it closed a number I had left open.** The loader sweep's eight unexplained disagreements with
the game log were this bug. They went to zero. Leaving them open rather than explaining them away is
what made them useful when the cause turned up.

Full suite after the round: **248 tests, 97.46% coverage, ruff and mypy clean.**
