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

## Where v02 stands

**All ten findings are closed.** The no-go was on the P1s and the artifacts; what remains blocking
publication is not a review finding but the hand-solve pack itself. **Nothing is labelled easy, medium
or hard until it comes back.**

| Finding | State |
|---|---|
| P1-01 adapter | closed — production module, per-section test |
| P1-02 chain targets | closed — writers select on stalls |
| P1-03 duplicate `audit()` | closed — one audit, `F811` in scope |
| P1-04 provenance fails open | closed — acceptance list, 0 games affected today |
| P1-05 manufactured anchor | closed — three fields, 0.001% of the pool |
| P1-06 no publication gate | closed — `certify_for_publication`, writers wired |
| P2-01 global identity admission | closed — fixed, and **nothing moved** |
| P2-02 stall attribution | closed — and it found a character dimension |
| P2-03 documents disagree with code | closed |
| P2-04 non-atomic regeneration | closed |

**What the P1s cost the pool: nothing measurable.** Provenance rejects 0 games, the anchor check
rejects 2 in 397,142. Every decision about caps, gate and composition stands on that side — which is a
result rather than an absence of one, because it was not knowable before the checks existed.

**No review finding is open.** What blocks publication now is work rather than repair, and it is
listed at the end of this file under *What is actually left*.

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

**Wired.** `write_reference_puzzles.py` now gates on `certify_for_publication()` and nothing else,
both when generating and again on the package read back from disk — a package that certifies in the
process that made it and fails when read from a file is the class of defect this project keeps
finding. The loader carries the evidence the gate requires (source type, official hits, official runs)
rather than the writer assuming it.

### v02-P1-02 — the writers selected boards by the retired proxy

`erase()` gained `target_stalls` and the callers kept passing `target_chain`, so the artefacts were
still chosen by the measure the project had already shown was length rather than difficulty.

**What I did.** The reference writer targets stalls, and its metadata records
`difficulty_model: "stalls"`, the requested and actual stall counts, the seed, the blank count and the
families — with `chain_length` kept as **descriptive telemetry**, labelled as such, because every
earlier measurement used it and they have to stay comparable.

**No band is implied.** The six sit at 5 through 10 stalls because six different boards are more
useful to build a client against than six of the same, not because those are difficulty tiers. Five
was an example the operator gave, and nothing is labelled easy, medium or hard until the pack returns.

### v02-P2-01 — the global identity was admitted before the simpler families were exhausted

`constraints.py` says the global identity waits until the simpler families are spent, and `_next_step`
recombined the two equation sets on its first line. So a `PA = Outs + R + LOB` move could be recorded
while a column sum was still available. The board reached the right numbers; the **recorded path** was
not one a player would follow, and that path is where chain length, family usage and stall position
come from.

**What I did.** Propagation runs over the non-global system first and only falls through to the whole
system when that finds nothing. Bounding still narrows against everything, because a range is not a
family and holding the global identity out of it would model a player who can bound with some
relations and not others. Two tests: a simpler move is taken first when both are available, and the
global identity is still reached when it is the only route — a rule that made it unreachable would be
worse than the defect.

### ⚠️ The five verdicts

Measured on the same 96 boards, before and after, at a stall target of 8:

| | Before | After |
|---|---|---|
| Stalls p50 | 8.0 | 8.0 |
| Chain p50 | 25.0 | 25.0 |
| Families, mean | 3.188 | 3.177 |
| Stall position | 52% | 52% |

**Nothing moved.** The families mean shifts by 0.011, which is one board in ninety-six using one
fewer family — noise at this sample size and in the direction the fix predicts.

1. **The ceiling at 10 — stands.** It was decided on family saturation at chain 11 against 8, and the
   family count is unchanged to two decimal places.
2. **The pitcher cap at 4 — stands.** This was the one to watch: it rested on cross-team 100% → 78%
   and global 51% → 78%, exactly the distribution in question. The mean family count per board does
   not move, so the distribution behind those figures does not either.
3. **The gate at 25% — stands.** It never depended on the solution path; it is a property of the
   board before any erasure.
4. **`row_first` — stands.** Chosen on trivial-step share and blanks per chain, both unchanged.
5. **The chain-versus-stall comparison — stands.** Both numbers are identical before and after, so
   the finding that chain measures length rather than difficulty is untouched.

**The whole body of measurement survives**, and that is worth stating rather than leaving implicit:
the defect was real and its effect was not.

### v02-P2-02 — the stall report could not name what broke a stall

It recorded the *bounding* deduction's identity, and a bounding deduction has none: it narrows against
a fixed point over the whole board rather than through one relation. So every stall came back as
"bounding only" on 100% of boards. **A figure that reaches 100% is almost never a figure** — it is an
instrument that does not distinguish.

**What I did.** Attribute the restart to the **first propagation step after** the stall. That matches
what a player experiences: subtraction runs out, they bound something, and then a particular identity
opens up again. A stall the board never recovers from by propagation is named `bounded to the end`
rather than folded into the families, because hiding a different thing inside a distribution is how
the previous version managed to say nothing.

**And it answers the question the review said was unsupported:**

| Stalls | What restarts them |
|---|---|
| 5 | column_sum 60%, row_identity 40% |
| 8 | row_identity 54%, column_sum 46% |
| 12 | row_identity 63%, column_sum 37% |

**Stalls do not all break the same way**, which was the outcome worth having: had one family broken
90% of them, the player would learn what to reach for by the tenth day. And the mix **shifts with
difficulty** — column sums dominate the easy end, the row identity the hard end. That is a character
dimension nobody knew existed, sitting exactly where the thinking happens rather than in the family
set the board merely *contains*.

*Neither cross-team nor the global identity ever restarts a stall in this sample. Worth knowing before
anything is built on the distribution: the two families that most distinguish boards are not the ones
that break the hard moments.*

### v02-P2-03 — the contracts described a board the code had left behind

`CLAUDE.md` and `docs/package-format-v1.md` are presented as current contracts, so a contributor
following them would have reintroduced the two-pitcher cap, restored the footnote line, or kept
grading on chain length. Each drift already existed in the code.

**Fixed:** the cap reads ≤4 pitchers everywhere it appeared; the footnote entry says the per-batter
cells are erasable and the totals row and LOB are not, with the reason; and chain is named as telemetry
with stalls as the difficulty variable. The format document gains a difficulty-metadata section so a
reader of an older artefact knows not to compare it, and states that **no difficulty label exists yet**.

**Sweeping rather than fixing only the two the review named found two more.** The rule against
proposing to stop or defer had been stated as being in `CLAUDE.md` and was not. And **progressive
reveal was still specified in two places after being dropped** — rows are labelled by position
throughout and the real boxscore is drawn complete at the end, which also releases row-level
validation, since it existed only to know when to reveal.

### v02-P2-04 — regeneration deleted the published set before a replacement existed

A loader error, an exhausted pool, an interrupt or a full disk left `serve/data/puzzles` empty or
half-written. Everything is now built and certified in a sibling staging directory, and the published
files are replaced only once the batch is whole. A failed run leaves staging behind as evidence and
the published set untouched.

**The staging directory was not sufficient on its own.** The first version deleted the published set
and then moved files in, leaving a window with nothing published — the same defect one step smaller.
It now replaces first and deletes the leftovers afterwards: `Path.replace` is an atomic rename within
a filesystem, so a reader sees the old file or the new one and never a truncated one.

## v04 — verified, none rejected

| Finding | Verdict | What was confirmed |
|---|---|---|
| P1-01 the manifest commit destroys the snapshot readers are following | real | and the sweep also eats a concurrent publisher's staging directory |
| P1-02 signed packages behind an unsigned manifest | real | the release inventory is the one thing no signature covers |
| P2-01 provenance projected by two unordered `TOP 1` queries | real, **latent** | 0 of 203,908 games have more than one provenance row |
| P2-02 the ceiling pack overclaims "ceiling" | real | one seed, one ordering, one greedy path per direction |
| P2-03 the comparator can null over a changed cohort | real | intersection compared, duplicates collapsed silently |
| P2-04 `families_used` and `family_counts` contradict each other | real | `family_counts` reads only `from_identity` |

### P1-01 — the atomic rename was necessary and is not sufficient

Replacing `manifest.json` atomically stops a reader seeing a torn pointer. It does not make *fetch the
manifest* and *fetch a puzzle* one transaction: a reader holding generation A gets a 404 when the
publisher commits B and immediately deletes A, and a cached manifest stretches that window far beyond
the filesystem operation. **The test I wrote asserts the unsafe behaviour** — `not (tmp_path / first).
exists()` right after `_publish` returns — so it encodes the defect as the contract.

Two more in the same sweep, both mine: the cleanup deletes every directory that is not the new
generation, which includes **another publisher's staging directory**, and `manifest.json.pending` is a
fixed name, so two publishers collide on it. Nothing makes the single-writer assumption true.

### P1-02 — the one thing no signature covers

Each package authenticates itself. The manifest decides *which* packages are the release, and it is
unsigned: omit ids, point at a retained generation, point at nothing. Every package the client does
receive still passes its own check, so the indicator says authentic while the release is not.

⚠️ **This is entangled with v03-P2-04 and must not be solved by adding a second shared secret to
`serve`** — the review says so and it is right. The signing migration and this are one piece of work.
The anti-rollback half, a monotonic release sequence, is independent and can be specified now.

### P2-01 — real, latent, and exactly the shape this project keeps producing

Eligibility uses `EXISTS` over the accepted sources with `is_deduced = 0`. The evidence *projected* for
certification comes from two separate `SELECT TOP 1` subqueries with no `ORDER BY` and no acceptance
predicate. Three places, one rule, and the projection is not bound to the row that qualified.

**Measured: every game has exactly one provenance row — 0 of 203,908 with more than one.** So it cannot
fire today, which is the reason to fix it rather than to close it: a check that cannot fire is
indistinguishable from one that is broken, and "one row per game" is an invariant nobody asserts.

### P2-02 — the same overclaim I corrected an hour earlier, one level up

`19` is the highest value seen on **one greedy path per direction, one seed, one ordering, 48
directions**. It is not a per-board maximum, not a sample bound, and not a family ceiling — stall count
depends on which cells are absent and is not known to be monotonic in blank count. The script and the
pack say "ceiling" and "the top". **Rename before the pack is solved**, since a solver anchored to a
wrong upper endpoint is the one thing the pack cannot recover from.

### P2-03 — the instrument built to prevent a false null still has a path to one

`compare()` keys rows by `(game_id, seed)` into a dict, which drops duplicates without a word, then
compares the intersection and treats one shared key as sufficient. If a change removes exactly the
boards it affects, the comparison reports a clean null over the survivors. Exact key-set equality by
default; partial comparison behind a flag and labelled non-experimental.

### P2-04 — one solve, two answers

`families_used` counts a global-assisted bound as having used the global family. `family_counts` reads
`from_identity`, which is `None` for every bounding step, so the same immutable result says the family
was required and returns a count of zero. No consumer today, and that is exactly when to fix it.

## v03 — verified, none rejected

Seven findings, every one checked against the code rather than against the report. **No no-go was
declared, and one is aimed at a measurement that was running while the review was read.**

| Finding | Verdict | State | What was confirmed |
|---|---|---|---|
| P1-02 three erasable definitions | real | **closed** | one stale, one duplicating every footnote cell |
| P2-01 global identity still partial | real | **closed** | two docstrings in one call chain state the opposite rule |
| P1-01 evidence is not bound to a game | real | **closed** | `Evidence` carries no game or puzzle id, and `is_deduced` is rebuilt from the source name |
| P2-02 duplicate staged puzzle | real | **closed** | `seen` is built after both entries are appended |
| P2-03 envelope accepts malformed values | real | **closed** | `schema: true` passes, because `True == 1` |
| P2-04 HMAC lets the server forge | real | *blocked on a dependency* | symmetric key, asymmetric architecture |
| P2-05 the RBI/HR run is not paired | real | **closed — does not apply** | one seed, and zero density counts the grid only |

**The order is the operator's:** P1-02 first because it invalidates evidence everything else is measured
on top of, then P2-01 with the before-and-after redone, then P1-01, and P2-05 when the re-run comes.

### v03-P2-01 — closed, and the null is a real null this time

`narrow` takes its relations explicitly, bounding runs the same two phases as propagation, and a bound
that only came out with the global relation carries `needed_global_identity` — a field of its own, not
a value in `from_identity`, because a bound is not derived *from* one relation and naming one would
invent the provenance that produced the "bounding only 100%" figure. Search cost is measured over the
phase that supplied the move.

**Measured before and after on the same 192 boards.** Stalls, chain, blanks, families, global share and
stall position all unmoved — and board by board, only `hardest_search` changed, on 4 of 192.

**The comparator caught itself first.** Its first version listed five fields to diff while the rows
carried nine, and it printed "not one board changed on any field" while `hardest_search` had moved on
four. It now derives the field list from the rows: a comparison that chooses which of its own
measurements to look at is the failure it exists to catch.

**And the flag never fires on real data** — not one of 768 bounding steps across 72 boards needed the
global relation. That is why the tests assert the mechanism rather than the outcome: hiding
`left_on_base` is a case non-global bounding cannot reach and global bounding can, and the other three
cells of the relation are covered by column sums. The null is a null rather than a hole.

### v03-P2-04 — open, blocked by a dependency. **Not pending by priority.**

A MAC cannot express the property §33 needs. The note in `signing.py` justified HMAC by saying no
third party needs to verify — which is about *who verifies*, when the requirement is about *who can
produce*. Every verifier of an HMAC is also a signer, so the verification secret on the VPS **is** the
forge's signing authority: a deployment backup or a diagnostic dump is enough to mint a package with
altered answers that the service cannot distinguish from a real one.

**The false justification is out of the code.** `signing.py` now states what the signature actually
guarantees — that the message came from someone holding the key, not that it came from the forge — and
that this contradicts the architecture. The defect is still there; it has stopped being disguised as a
decision, which is the part that could be fixed today.

**It has a date, and the date is not a preference.** The fix must land **before `serve` exists**. The
day the VPS verifies packages is the day the verification key leaves the laptop, and the defect goes
from theoretical to real at that moment. Until then there is exactly one key and it is on the machine
that is allowed to sign.

**Decided: schema 1 is not amended.** Frozen means frozen — the fact that nothing has shipped is not a
licence to edit a version that has been declared closed, because a format that gets edited whenever it
is convenient is not a contract. The Ed25519 envelope is therefore a new schema version, and what that
costs — a reader that must handle both, or a clean break while there are no consumers — is the call to
make when the dependency is unblocked, not before.

**Blocking:** Ed25519 is not in the standard library and `cryptography` is not installed. `uv` is not
on this environment's PATH; `ensurepip` can bootstrap `pip` into the venv, but installing that way
would leave `uv.lock` describing an environment that no longer exists, and the lockfile is the
reproducibility guarantee rather than a build artefact. **`uv add cryptography` is the one step this
is waiting on.** Hand-rolling the primitive is not an alternative: a homemade Ed25519 would be worse
than the defect it repairs.

**The shape of the fix**, so it is not redesigned later: private key on the forge, public key deployed
to `serve`, `key_id` in the signed envelope for rotation, signature 128 hex rather than 64. And rotate
the current shared secret before production if it has ever left the local reference-fixture workflow.

### v03-P2-05 — closed, does not apply

**The finding is correct and the question it would settle is already answered by data it cannot
touch.** The variants call `row_first` with one seed over candidate lists of different lengths, so the
common cells do not keep their order and part of any difference between configurations is the shuffle;
and `zero_density` counts the grid only while the report called it every cell.

What a paired re-run would fix is *how many blanks each configuration needs to reach a stall target*.
That comparison only matters when choosing between configurations that add something. **None of them
does:** the constraint graph carries 78 independent cycles in all six, identical. Neither RBI nor home
runs adds a single cycle — the home-run cells appear only in home-run equations, so the block hangs off
the board disconnected. That is topology. It does not depend on the erasure order, the seed, or the
zero-density denominator, which is precisely why the defect cannot reach it.

So the comparison is not re-run. Recorded as *does not apply* rather than *fixed*, so it is not
reopened later on the belief that a doubt was left standing.

**Carried forward instead.** If total bases, doubles or triples are ever measured, that comparison has
to be paired from the start: one stable priority permutation for the cells the configurations share,
separately controlled insertion points for the new ones, several seeds, and paired per-game deltas with
spread rather than medians alone. State whether zero density is grid-only or all-erasable-cells, and
apply the same denominator to every placement. **The lesson applied forwards, not backwards.**

### v03-P2-03 — closed

The board was validated at the boundary and the envelope around it was not.

- **`schema: true` was read as version 1**, because Python makes `True == 1` and the check was `!=`.
  Now the value must be an `int` that is not a `bool`.
- **`from_json` took `dict` in its signature and trusted it.** A list root raised `AttributeError` from
  `raw.get` three frames later. `read()` guarded the root and the method did not, so a public boundary
  was safe only when entered through one particular door. The method checks now, and the tests go
  through it directly rather than only through `read`.
- **The identifier and the signature are checked against the shapes the format document states** —
  sixteen lower-case hex, and sixty-four for the HMAC. A signature of the wrong type reached
  `hmac.compare_digest`, which raises rather than refusing: the verifier crashing on a malformed file
  instead of rejecting it. A path-like identifier is the case that matters most, since the id reaches
  filenames and will reach URLs.

**And the two claims about the identifier are joined.** The forge produces it and the format states its
shape; a test asserts a real one satisfies the pattern, so they cannot drift into being two unrelated
statements about the same string.

Every fixture that used `puzzle_id="p"` now uses a contract-shaped id. A fixture that could not exist
in the wild is not testing the boundary, and updating them is what surfaced that `read` and `from_json`
disagreed about who checks the root.

### v03-P2-02 — closed

**The duplicate.** Every append goes through `claim()`, which refuses a game already in the batch, and
the two required traits go through it too — a direction can carry a substitution *and* a live footnote,
and taking them first and deduplicating afterwards is exactly how one game entered twice. `_publish`
counts staged *files* against the expected number rather than trusting the build counter, because two
builds and one file is what a collision looks like.

**The batch atomicity, which per-file renames could not give.** A generation is a directory named by a
digest of its own contents, immutable once written, and `manifest.json` naming the current generation
is replaced last. That one rename is the commit; everything before it can fail without changing what is
published. A reader follows the manifest and sees a whole batch or the previous whole batch.

Names could not have solved it: a puzzle's name is a function of its game (§21), so a regenerated
puzzle lands on top of its predecessor rather than beside it.

And the layout is now a written contract in `docs/package-format-v1.md`, set before `serve` exists so
nothing has to be migrated. Verified end to end: six packages published, and a second run resolves to
the same generation and republishes as a no-op.

### v03-P1-01 — closed

Evidence carries the game and the batting team, and the gate **recomputes** the identifier from them —
comparing against one the producer supplies would agree with itself. `expected_puzzle_id` is a second
derivation in `boxscore_verify` rather than an import, per §22, with a property test that the two agree
on arbitrary input rather than on one example.

`is_deduced` is the provenance row's own value. It was being rebuilt as `source_type.startswith("ED")`.

**Correspondence now says what each half establishes.** All six R/H/E fields are compared because they
are signed and player-visible — but they come from the same query that fills the line score, so that
half catches corruption in transport and cannot catch fabrication. At-bats and runners left on base
come from `retroGameLogs`, a table the board is not built from, and are the only strict correspondence
in the gate. Absence of a game-log row is a refusal.

**What it costs and what it catches.** 1.52% of directions refused, almost all of them games with no
game-log row, concentrated in the 1930s to 1960s. At-bats disagree on **1 direction in 407,816** and
runners left on base on **20** — twenty-one real correspondence failures that no §22 layer can see.

### v03-P1-02 — closed

All three definitions are gone; every instrument consumes `boxscore_forge.erasure.erasable()`.

**The failure form now fails on its own.** All three orderings reject a candidate list naming a cell
twice, with a test per ordering that a repeat raises *and* that the canonical list is accepted — a
guard that rejects everything is not a guard. A third test states that the canonical list carries the
footnote cells, so no instrument has to re-derive the fact that caused this.

**Wider than the review named.** The grid-only definition was also feeding `compressibility.py`, which
is §5's viability constraint. That ceiling was measured over a smaller board than production erases,
so the compressibility numbers and the +0.79 correlation with zero density are both measured low.

**And the repointing was verified by compiling and walking the AST, not by reading the diff.** The
rename left three uses of `erasable` as a list value in `compressibility.py` — it compiles cleanly and
dies at runtime on `zip` over a function. Same shape as the `sed` that renamed a dataclass field.

**Still owed:** regenerating everything measured on the old trajectory — the stall ceiling, the 100%
coverage with footnotes open, and compressibility. Queued behind the runs in flight.

### v03-P1-02 — what it was: `erasable()` already includes the footnotes, and one instrument adds them again

`stall-targeted/measure.py` builds its candidate list as `list(erasable(direction))` plus every
footnote cell, and `erasable()` has carried those since the v02 round. **Every footnote cell is in the
list twice.** The duplicates are no-ops against the erased set, so nothing is wrong with the boards;
what is wrong is the trajectory. `_row_first` buckets by row, so `footnotes[3]` holds eight entries
instead of four and keeps taking round-robin turns that erase nothing — footnote cells therefore enter
at roughly half the rate production gives them, and every seeded order downstream shifts with them.

`difficulty-metrics/measure.py` carries a third definition, `erasable_cells()`, which says the
footnotes are given. That was true when it was written and has not been true since.

**So the stall model's numbers were measured on a board no generator produces.** Not wrong boards —
a different erasure path over the right boards. Everything read off that run is suspect until it is
regenerated: the ceiling, the blanks at each target, the pool coverage, the family mix.

### v03-P2-01 — the two docstrings say opposite things and the code follows one

`_bounding_moves` says *the global identity stays out of the narrowing for the same reason it stays
out of propagation's first pass*. It then calls `narrow`, whose own docstring says *the global identity
is in here with everything else*, and which builds from `equations(shape)`. The second is what runs.

This is the project's named failure shape at its shortest range: two places that should agree, three
lines apart, and nothing checking. The v02 repair fixed propagation's phase order and did not reach
bounding — and separately, `_scan_size` is computed over the whole system *before* the phase that
supplied the move is known, so a local deduction's search cost counts a global equation the player is
not expected to have reached for.

### v03-P2-05 — aimed at the measurement that was running

Two claims, both correct. The variants call `row_first` with one seed over candidate lists of
different lengths, so the common cells do not keep their order and part of any difference between
configurations is the shuffle rather than the columns — the script's own docstring says *the columns
and nothing else*, and that is overstated. And `zero_density` counts the batting and pitching grids
only, so a home-run **column** contributes its 92% of noughts and the identical per-batter home-run
**footnote** contributes nothing, while the report calls it density over each configuration's own cells.

Grid-only is not itself wrong — it is exactly the denominator §5's gate uses in SQL. What is wrong is
the label, and the conclusion it invites: the footnote placement does not *avoid* zero density, the
gate simply does not look there. Both numbers are needed, each named.

**The run in flight is not discarded.** What it can answer stands: what each configuration builds, the
width arithmetic, and whether the home-run cross ever resolves a cell. What needs the paired re-run is
any claim that one configuration reaches a target in fewer blanks than another.

### v02-P2-01's closure is reopened by its own method

It reported that stalls, chain, families and stall position did not move, on 96 boards, and closed on
that. **Every one of those was a median.** Two boards moving in opposite directions leave a median
where it was, so the evidence never distinguished "nothing changed" from "the changes cancelled" —
and the repair it was closing was only half applied, which is v03-P2-01.

The five verdicts that hang off it — the ceiling at 10, the pitcher cap at 4, the gate at 25%, and the
two composition decisions — are therefore restated rather than assumed. `discovery/global-identity-phase`
runs the same boards before and after and reports **how many individual boards changed on each field**,
not only the aggregates. A null that survives that is a null; the earlier one was not tested for it.

## Noticed in passing

### The starter's label is still picked by priority, so a man who moved positions is misnamed

Spotted by eye: `ACY192107310 IN4` shows **two `3B` and no starting `CF`**, which cannot be a starting
nine.

The raw flags say why. The man in slot 6 carries **both `3B` and `CF`** — he started in centre and moved
to third when the slot-2 third baseman was replaced, which is why a fresh `CF` enters at slot 2. The
`CASE` resolves his two flags by a fixed priority that puts `3B` ahead of `CF`, so he is named for the
position he *moved to*.

**The `_position` fix did not reach this.** It reads `SUB_FLD_CD` for men who *entered*, and a starter
who merely moved has no entry of his own to read — so the half of the defect that involved substitutes
was corrected and the half that involves starters was not. Same shape as the fixes this backlog keeps
recording: the remaining case is the one carried along by a change that looked complete.

**The rule that follows, and it uses the table already joined.** A starter with more than one fielding
flag moved during the game. If he appears in `retroSubstitutionsReg` with a fielding code, that code is
the position he moved *to*, so his starting position is the other flag. The check that would have caught
this is a plausibility assertion, not an arithmetic one: **a starting nine has exactly one man per
fielding position**, and any board showing two of one and none of another is wrong however well it
balances.

**Not fixed here.** It needs the moved-to lookup, and the assertion above wants measuring across the
pool before it becomes a gate — it may reject real boards in eras with sparse fielding records.


### I rebuilt the driver that ignores a non-zero exit

`compressibility.py` died two thirds of the way through its report with a `UnicodeEncodeError`: a `⚠️`
in a `print`, stdout redirected to a file, and Windows defaulting the stream to cp1252. Fifty minutes of
compute produced three sections of a report and no correlation figures.

**The part that matters is not the crash.** The run was launched as `cmd > log 2>&1; echo "exit $?"`, so
the shell's own exit status came from `echo` and was always zero. The task notification said *completed
(exit code 0)*. The real status was 1, printed inside the log where nothing was looking.

That is verbatim one of the seven entries in `CLAUDE.md`'s record — *a driver that reported COMPLETE on
a non-zero exit* — and it was rebuilt today, in the command form used to launch three measurements in a
row. The other two happened to finish.

**Fixed by construction, not by care.** Long runs are launched without a trailing command, so the
harness reports the process's own status, and with `PYTHONIOENCODING=utf-8` so a report cannot die on
its own output. A discovery script that prints `⚠️` — most of them do — is not portable to a redirected
stream on this machine otherwise.


### A maximum compared against a median, repeated without either of us noticing

The ceiling pack was reported as landing *higher* than the earlier run — 19 against 16 to 18. Those are
not the same statistic: 19 is a **maximum over 48 boards** and 16 to 18 were **medians** of per-board
ceilings across configurations. The comparison says nothing. What is true is that the ceiling pack found
a maximum of 19 with the canonical list; what the duplicated list would have given was never measured.

Recorded because it survived being stated, read and repeated. A number carried from one report to
another loses the definition that made it meaningful, and nothing in the pipeline re-attaches it.


### The row label is not the position the row represents — **fixed**

Spotted by eye on a printed board: `DH-1, DH-2` and `CF-1, CF-2, CF-3` in one lineup. **Three centre
fielders in a game is not a thing that happens**, and no arithmetic check can see it — the board
balances perfectly with the labels wrong.

**Cause.** `_batting_labels` suffixes repeats of a label, and the label comes from a `CASE` over the
`F_*_G` flags in `retroDailyReg`. Those flags mean *appeared at this position at some point in the
game*, not *this is the position this row represents*, and the `CASE` picks whichever flag comes first
in a fixed priority — fielding positions ahead of `B_G_PH` and `B_G_PR`. So a pinch hitter who then
took over in centre is a `CF`, and three men who each spent an inning there become `CF-1`, `CF-2`,
`CF-3`.

**The right source is `dbo.retroSubstitutionsReg`**, which carries `SUB_FLD_CD` — the position the
entering player came in at. It is already joined for the pitcher order and was never used for batters.

**Measured:** across 400,000 substituted batting rows, the current label disagrees with the entry
position on **28,011 of them, 7.0%**. The largest groups are `DH` for a man who entered as `PH` (6,092)
and as `PR` (3,851), and outfielders labelled by a position they moved to rather than entered at
(`CF`→`RF` 3,465, `LF`→`RF` 2,205, `LF`→`CF` 1,704).

⚠️ **This is the class of defect the four §22 layers cannot see**, and the second one found by looking
at a rendered board rather than by computing anything.

**What it damages.** Not solvability — the arithmetic is untouched and the suffixes keep the labels
unique, so footnote attribution (`HBP: SS`) still points at one row. It damages **§7**, where the label
is the row's only identity during play, and it damages the hand-solve packs specifically: a
baseball-literate solver who reads `CF-3` stops trusting the board, and trust is what those packs are
measuring. **Both packs should be rebuilt after the fix**, the five-board ceiling pack included.

**Decided: where he played, not how he arrived.** The label has a deductive function rather than a
biographical one — it is what tells the player which row an `SF: SS` belongs to, and `PH` distinguishes
nothing because every substitute hitter is one. A printed boxscore prints the fielding position too
when a pinch hitter stays in. So: the position he entered the field at if there was one, then any
position he is recorded at, and `PH` or `PR` only when he never occupied one — there they are the whole
truth rather than a provenance tag. `DH` loses to `PH` for the man who batted for the designated hitter
without taking the slot, which was the largest single group in the 7%.

**Footnote attribution was verified rather than assumed, and it was already right.** The terms come per
player from `retroDailyReg` and `footnote_line` indexes `loaded.labels[index]` by row, so `SF: CF-2`
already names the row and carries the suffix. What was wrong was only which position the label named —
but that is enough: a footnote in the wrong row puts the term inside the wrong row identity while every
column total still balances, so the arithmetic breaks where §22 cannot look. `tests/test_row_labels.py`
asserts both halves, including that swapping the term between two rows leaves the totals untouched and
fails *both* row identities.

**Still owed: both packs rebuilt** — the fifty and the ceiling five.


### `extend-include` claims discovery is linted and nothing lints it

`forge/pyproject.toml` adds `../discovery/**/*.py` to ruff's file patterns, with a comment saying the
duplicate `audit()` lived outside the lint scope and the rule that catches it could not see the file.
The pattern makes discovery *lintable*; it does not put it in any command's argument list, and there is
no CI workflow yet. Run explicitly, `ruff check ../discovery/` reports 597 errors — 403 of them `T201`,
because a discovery script's interface *is* printing and the `per-file-ignores` entry that exempts
`scripts/*.py` was never extended to it.

So the config reads as a guarantee and is not one, which is this project's own failure shape: two places
that should agree, and nothing checking. **`F811` genuinely does fire** — that was proved against a
deliberate duplicate — but it fires only when someone remembers to point ruff at the directory.

**Not fixed here.** The fix is a `per-file-ignores` entry for `../discovery/**` covering `T201`, `E402`
(the `sys.path` preamble every script needs) and `S311`, and then a lint command that names both trees —
which belongs with the CI workflow, and CI does not exist yet. Recorded so it is not rediscovered.

## What is actually left

Not review findings — these are the things the repairs unblocked.

1. **The fifty-board hand-solve pack.** Boards spanning a range of stall counts, the count in the key
   rather than on the page, randomised order, the `stalls` column in `key.csv`, and the PDF check
   green. **`build_pack.py` still targets chain and its `audit()` still speaks in chain rungs** — that
   is the last chain-targeted producer.
2. **What the pack answers**, in order of what it settles: whether the marked 1–6 tracks stall count
   at all — if it does not, stalls are measuring something the player does not experience, and that is
   as important as the chain finding was; whether the uncertified third is felt, which decides layer
   3b; and whether the boards are interesting, which the *tedious* and *boring* ticks answer.
3. **The RBI and HR columns**, with `SO` for `K` and the canonical order, and a measurement of what
   they buy — all of it recorded in §6 and none of it built.
4. **The generator at volume, the calendar builder, and signed packaging in batch.** Nothing in the
   forge yet produces an inventory; the six reference packages are a format sample.
5. **`serve` is at zero.** Six real packages exist for it to be built against, and February is the
   window.

**Nothing is labelled easy, medium or hard until the pack comes back.** Five stalls was an example the
operator gave, not a standard.

## Void rather than confirming anything

The **grouped-versus-separate footnote comparison** was measured through the adapter that restores
footnote values, so the boards graded and the boards measured were different objects. The decision went
to **separate** on a reason the numbers cannot touch — no printed boxscore carries a grouped footnote
column, and §2 commits to the canonical format.

And **five stalls was an example, not a standard.** Nothing is labelled easy, medium or hard until the
pack comes back.
