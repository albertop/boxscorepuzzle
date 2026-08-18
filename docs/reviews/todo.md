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


---

# Code review v02 — accepted, repair in progress

All ten findings accepted. **No-go stands: no pack, no reference packages and no difficulty labels
until the P1s are closed and the artifacts regenerated.**

## Closed

### v02-P1-03 — a duplicate `audit()` disabled the strict quota

`build_pack.py` defined `audit()` twice and Python kept the later one, so the strict uncertified share
from the v01 fix was not running: a pack could pass with anywhere from 10% to 50% uncertified boards.

**What I did.** Kept the strict definition and **folded in the two rules only the later one carried** —
no rung entirely uncertified, no page order monotonic in difficulty. Deleting the second function on
its own would have lost two guarantees while fixing one.

**Made self-enforcing.** Ruff's `F811` catches a duplicate definition, and `discovery/` is now inside
the lint scope because that is where it happened — a rule that cannot see the file is not a rule.
Verified against a deliberate duplicate rather than assumed.

### v02-P1-01 — the adapter lived in a discovery experiment and dropped footnote erasures

The production path imported its `Direction` → `Board` conversion from
`discovery/verifier/rejection_rates.py`, and that conversion consulted the erased set for batting and
pitching rows while copying every footnote value unconditionally. The generator could erase a footnote,
grade a solution path that used it as an unknown, and the package would hand the value back — the
verifier validating an easier board than the one measured, with the metadata describing neither.

**What I did.** `boxscore_forge.publish.to_board` is the one conversion, owned by the side that
*produces* a package — §22 forbids the verifier sharing code with the generator, and the format belongs
to neither. The erased set is applied through a single `cell()` rule used by every section, so the bug
cannot recur in the shape it took: a section with its own handling. Every caller now imports it;
`rejection_rates.to_board` is a two-line wrapper that only unpacks `Loaded`.

**Test.** `tests/test_publish_adapter.py`, **written per section rather than as one blanket check**, so
a section added later without the rule fails here instead of shipping quietly. Batting cell, batting
total, pitching cell, pitching total, footnote cell, footnote total, team footnote — plus that an empty
erased set gives the whole board and that naming a line-score cell does *not* blank it, since the anchor
is never erased.

### v02-P1-04 — the source gate passed on absence

The pool filtered provenance with `NOT EXISTS` over an exclusion list, and a game with **no**
provenance row satisfies "not excluded". A partial import, a new season or an identifier mismatch
turned *source unknown* into *source approved* silently, and those games pass every arithmetic
identity while breaking §32's source policy.

**What I did.** `EXISTS` over an **acceptance list** — `ACCEPTED_SOURCES = ("EVA", "EVN", "EVF")`.
A source kind nobody has seen yet is now excluded by not being named, rather than admitted because
nobody remembered to exclude it. That is the general form of the fix, not only this instance.

**Tests.** Four on the loader and one per PowerShell script that queries the pool, because the
predicate was copied across four files this project and two copies drifted. They assert the exclusion
form does not come back, that a provenance row is required, and that `EVR` and the deduced kinds are
absent from the acceptance list.

They read the query text rather than execute it — the predicate is SQL against a database, and a test
needing a DSN is a test that gets skipped in CI and then never runs. **Weaker than executing it, and
said so in the file.** What it does catch is the shape of the mistake returning, which is how it
arrived: the same words in a different file.

**Coverage, and it rejects nothing today.** Of 203,908 games: **0 missing provenance**, 3,465 deduced,
1,872 excluded source, **198,571 accepted (97.4%)**. So the fail-open case does not currently fire and
the pool does not shrink — which is the useful answer rather than a disappointing one. The old filter
was not admitting unknown-source games *yet*; it was one incomplete import away from doing so, and the
completeness it depended on was never stated or checked. **P1-06 is unblocked from this side.**

### v02-P1-05 — the anchor was manufactured from what it anchors, in three places

`offense_hits` was `sum(line.hits for line in batting)`, and the verifier then checked that the batting
hits equalled the line score's hits — both numbers from the same rows. An omitted batter, a duplicate
or a join fan-out satisfied every hit identity while the board stopped corresponding to the historical
boxscore.

**The per-field test found two more.** `offense_runs` and `defense_runs` were summed from the inning
array the verifier compares them against, so that identity could not fail either. Writing the test the
way the review asked — per field rather than for hits — is what turned one known defect into three.

**What I did.** All three come from the game tables now: hits from `retroGamesReg`, runs from
`retroGameLogs`, both different files from the daily rows. And the loader **rejects** a direction where
they disagree rather than only preferring the loaded value, because loading an anchor and not comparing
it looks identical from the outside.

**Cost: 2 directions in 397,142 — 0.001%**, both in the 2020s. Scattered rather than clustered, so it
is data noise rather than a loader problem, and the pool does not move.

### v02-P1-06 — the publication path called `verify()` and nothing else

`verify()` answers a mathematical question: does the board balance, is the completion unique, is it
reachable without guessing, does the published half match its source. All four can be true of a board
that could not have happened — this package's own test suite holds one that passes every layer and is
not a baseball game. The checks for that existed and the publication path never called them.

**What I did.** `boxscore_verify.certify.certify_for_publication()` composes five checks: the four
§22 layers plus the signature, board plausibility, reveal plausibility, provenance, and correspondence
to an independent source. It **fails closed** — a check that cannot run is a refusal, never a pass —
and unlike `verify()` it does not stop at the first refusal, because a writer discarding a candidate
wants everything wrong with it rather than the first thing.

**Evidence is required, not optional.** Provenance and independent correspondence are facts about
where a game came from, and §22 forbids the verifier growing a database to learn them. The producer
supplies them; **omitting them is a refusal**, so a writer cannot obtain publication by not looking.

**The test discovers the checks rather than listing them**, which is what the review asked for: it
walks the module for `check_*` functions and asserts each is in the registry, and walks the
plausibility module for public `*_faults` and asserts the gate calls each. Adding a check without
wiring it in fails on its own. It also asserts the two copies of the accepted-source list agree —
they exist twice because §22 forbids the verifier importing from the generator, and two copies of a
rule drift.

It caught one thing while being written: the discovery originally swept private helpers too, which
would have made the gate depend on how plausibility is implemented rather than on what it offers.

**Still open on this item:** the writers do not call it yet. `write_reference_puzzles.py` still gates
on `verify()` plus a reveal check, which is the subset the finding is about.

## Open, in the agreed order

5. **v02-P1-02** — migrate the writers to `target_stalls`; chain becomes descriptive telemetry.
6. **v02-P2-01** — two-phase fixed point so the global identity waits until non-global deductions are
   exhausted.

   ⚠️ **This one owes a before-and-after on the same boards**, not new figures: stall counts, family
   distribution, chain length, stall position. The recorded path is the source of all four, so if the
   solver has been admitting the global identity too early, every measurement built on that path
   inherits the error.

   **Decisions that rest on those numbers and need re-examining if they move:** the ceiling at 10
   (family saturation at 11 versus 8), the pitcher cap at 4 (cross-team 100% → 78%, global 51% → 78% —
   *exactly* the distribution in question), the zero-density gate at 25%, the `row_first` ordering, and
   the chain-versus-stall comparison itself. If nothing moves, say so plainly: that is a useful result
   and it means the body of measurement stands.
7. **v02-P2-02** — attribute a stall's restart to the first *subsequent* propagation deduction's family,
   since the bounding step itself carries no identity.
8. **v02-P2-03** — reconcile `CLAUDE.md` and `docs/package-format-v1.md` with the executable rules. The
   visible drift is the two-pitcher cap and the footnote line.
9. **v02-P2-04** — generate reference packages into a temporary directory, certify there, and replace
   the published set only on success. Never delete the last known-good set first.

## Void rather than confirming anything

The **grouped-versus-separate footnote comparison** was measured through the adapter that restores
footnote values, so the boards graded and the boards measured were different objects. The decision went
to **separate** on a reason the numbers cannot touch — no printed boxscore carries a grouped footnote
column, and §2 commits to the canonical format.

And **five stalls was an example, not a standard.** Nothing is labelled easy, medium or hard until the
pack comes back.
