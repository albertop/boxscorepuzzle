# Review backlog

## Where everything stands

**Fifteen reviews, 71 findings, none rejected. One is open and it is not waiting on effort.**

| | Open | Why |
|---|---|---|
| **v05-P1-02** | how an erased footnote attribution is drawn | half closed. The mechanical half is done and guarded both ways; **the run that decides the drawing was stopped and the instrument rebuilt again** |

**Everything from v01 to v15 is closed except that one — seventy of seventy-one.**

⚠️ **The last five reviews were almost entirely about one instrument.** That is worth reading as a
pattern rather than a run of bad luck: **a measurement can be blind in a way that shows up as a
plausible value**, and no amount of care in the reading catches it — only a guard that fails when the
measurement is blind.

⚠️ **And v13 and v14 found the same shape one layer out, twice.** The instrument's own *stamp* was
blind: v13 found it read the tree hours after the run it describes and refused to publish on one of the
two questions it asks; v14 found that what it did hash were **labels rather than values** — the
identifier instead of the boxscore, the porcelain status line instead of the bytes that changed. A
provenance block that cannot distinguish two runs is an instrument that cannot distinguish, reporting as
though it had — the identical defect, in the part of the file that exists to certify the rest.

⚠️ **Worth naming as a class, because it now has four instances.** *A name is not the thing.* A
`game_id` is not a boxscore, a status line is not a diff, a heading string is not a denominator, and a
row-label suffix is not a lineup slot. Every one of them read correctly and identified nothing.

⚠️ **And v15 found the second class in the same three functions**: *the absence of a reading is not a
reading of absence.* An empty path list read as a clean tree, an unreadable file read as a file whose
contents were the string `<unreadable>`, and `out.parent.is_dir()` read as writability. This is the
fail-closed rule CLAUDE.md names first, and it keeps arriving in the code written to satisfy the
previous review — which is the useful part of the observation, not the rule itself.

## What is left

**`serve` runs in parallel with everything below it**, not after. It depends on none of them: since
schema 2 it has the contract it needed, and the group run, the drawing and the ladder are forge and
pack work that does not change what the client reads. It is at zero and February is the window.

### Ed25519 and the six packages — finished

Key pair, 128-hex signature, the envelope, **the signed manifest**, test keys generated per run, the
two modes mutually exclusive, ephemeral batches written outside `serve/`, and the production key
compared with the pinned public key **before the first filesystem mutation**. The public half is in
`serve/data/signing-public-key.hex`; the private half is on the laptop, documented in
`docs/signing-keys.md`, and never in Git.

The six reference packages are published: schema 2, 128-hex signatures, one slot reference per batting
row, signed manifest. Verified **from disk against the public key committed in the repository** rather
than against what the writer reported, with both tampering cases refused — altering the generation, and
removing one id from the list. ⚠️ **That second one is the attack package signatures cannot see**, since
every id left in the list still verifies.

**`serve` has a base to build against, and it is the format that exists.**

### The group run — stopped five times, and what each stop was

| | What the instrument could not do |
|---|---|
| v09-P2-02 | blockage could not **vary**: every other cell was given, so nothing could depend on the group |
| v11-P1-01 | blockage could not **fire where it mattered**: the baseline removed the group along with the erasure |
| v10-P2-01/03, v11-P2-01/02 | the **denominators did not match the questions**, and one was chosen by a heading string |
| v12-P1-01 | the **guard for the second fix accepted the implementation it replaced** |
| v13-P1-01 | the **stamp could not identify the run**: gathered at the end, naming no input, refusing on one question of two |
| v14-P1-01 | the **stamp digested labels, not values**: the same identifier over a different boxscore was the same digest |
| v15-P1-01 | the **stamp could report `clean` on a contradiction**: an empty path list outvoted a non-empty diff |

**Only the first produced a reported number**, and it reached the operator as a finding before anyone
noticed the column had one possible value. The other four were caught before a run completed — which is
the difference between a review that costs an afternoon and one that costs a decision.

The instrument now: measurements as pure functions in `metrics.py` that the tests **call**; report rows
carrying their own eligibility and denominators as callables; three erasure seeds with per-trial rates;
run-level coverage kept separate from group trials; **an immutable `RunIdentity` captured before the
first board**, carrying a code digest that includes the loader, the tracked and untracked tree states
digested from the diff and from file bytes, and **a per-board content digest listed in the artifact** so
the aggregate can be recomputed; **any disagreement between the two git snapshots reported as unknown
rather than clean**; a refusal that fires **before** the sample is loaded rather than after every solve,
with the destination proved writable by writing; a per-writer staging path extracted into `publish()` so
a collision can be forced in a test; and a refusal to publish when any repository question is unknown or
the identity names no inputs.

Result schema is **4**. Schema 3 artifacts digested labels, so they cannot be compared with these and
must not present as the same contract.

⚠️ **Every one of those fixes is guarded by a test that fails when the fix is reverted**, checked by
reverting each one and watching a named test go red — not by rereading the assertions. **That practice
paid for itself in v15**: two mutations left everything green, one because the mutation was bad and one
because a guard was missing.

### ▶ The run — going, at `44d9582` on a clean tree. **v15 did not stop it.**

| | |
|---|---|
| launched | 2026-08-19 09:37 |
| revision | `44d9582`, tracked **clean**, untracked **clean** |
| instrument | `4f894c5391eb` — measure, metrics **and the loader** |
| result schema | **4** |
| parameters | three seeds, eight directions per decade, the 25% gate, `≤13` batters, `≤4` pitchers, target 8 stalls |

**The first launch (09:22, `20e6e1f`) was stopped after ten minutes.** `v14-P1-01` lands on the artifact
it would have produced, and it had not yet finished loading. **The evidence would not have been wrong —
the tree was clean at a known commit, which pins everything the weak digest failed to pin — but the
stamp would have carried a claim the artifact did not support**, and a provenance nobody can check is a
claim rather than evidence. Ten minutes is the entire cost of that decision, and it is the argument for
reviewing an instrument before trusting a number rather than after.

⚠️ **The loader is the slow part, and it prints nothing.** Both launches sat with an empty log for their
first ten minutes: `load()` gates every candidate direction on zero density before the first board is
measured. An empty log early is the expected state, not a stall — the first line is the gated-direction
count.

**v15 landed mid-run and the run was left alone**, which is the opposite of the v14 call and rests on a
different fact. v14 changed what the stamp *would say about this run*. v15 closes **failure windows** —
a disagreement between two git snapshots, an unreadable file, an unwritable destination — and none of
them is open here: the tree was clean at capture, the destination is fine, and `format.py` is not on the
run's path. Its `instrument 4f894c5391eb` identifies the v14 file **by content**, which is recoverable
from `44d9582`, so the artifact stays checkable. Restarting would have cost twenty minutes and corrected
nothing.

**What it has to answer**, and nothing beyond it: how many completions a hidden slot group admits, how
often propagation-plus-bounding recovers it, and how often hiding it stops the rest of an erased board
from progressing. The first decides whether a **generator constraint** is needed, the third decides the
erased-attribution drawing.

**No further measurement after this one unless something is broken.**

### Then, in order

1. **`serve` — the engine**, in parallel from now. The board with pinned totals and scrolling, the
   numeric keypad with the thirds keys for innings, row grouping with the slot column, the footnote
   line, and the end-of-game reveal drawing the real boxscore. No accounts, no payments, no PWA shell:
   C5 says the engine carries no chrome, so it can be built in isolation, and it holds the most
   unknowns.
2. **The group run** — *running*.
3. **The generator constraint**, if the data calls for one.
4. **The erased-attribution drawing**, once the group run says how many candidates a blank separates.
5. **The ladder pack**, and the operator solves it.

**No further measurements after the group run unless something is broken.** Several open questions will
keep imperfect numbers, and that is the correct state to build in.

## ✅ The footnote question is settled, on a comparison that isolates the treatment

The rerun landed. One canonical order over the union with *given* obtained by filtering it, so the
shared cells keep their relative order **by construction**; zero-ceiling boards kept; the cohort
asserted complete.

| | given | open |
|---|---|---|
| median ceiling | **4.5** | **15.5** |
| minimum | **0** | 11 |
| coverage at 5 stalls | **50%** | **100%** |
| coverage at 11 | 4% | 100% |

**48 of 48 boards higher with the footnotes open**, and this time unanimity means something: with the
ordering identical for every shared cell, it is no longer compatible with a trajectory bias.

**Both repairs are visible in the numbers.** A board with a ceiling of **0** appears — the case where
the given treatment can erase nothing that produces a single stall, the most informative one for the
question, previously discarded as a failure. 48 pairs from 48 directions rather than 47. And the given
medians fall slightly, which is the upward bias correcting.

**So the per-batter footnote cells are erasable**, and what follows from it stands: v05-P1-02 is real
work, the erased attribution needs a drawing, and the design document was the wrong one.

**Unblocked by this:** the generator constraint if the group run calls for one, the erased-attribution
drawing, and the ladder pack.

**What is not a review finding and blocks publication:** the ladder pack — 19, 16, 13, 9 and 6 stalls,
rungs filled from boards of similar reach so the ladder varies stalls and not headroom, `audit()`
reporting the uncertified share per rung rather than requiring it. And the operator solving it.

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

### v04-P2-01, P2-03 and P2-04 — closed

- **`family_counts` and `families_used` can no longer disagree.** One counted `from_identity` and the
  other counted a global-assisted bound, so the same immutable result said a family was required and
  returned zero for it. The contract is *participation*, and a test asserts the two agree on a real
  board — named if and only if counted.
- **The comparator requires the same cohort.** It compared the intersection and asked only that it be
  non-empty, so a change that removed exactly the boards it affects would have reported a clean null
  over the survivors — the false null the instrument exists to prevent, through the door it left open.
  Duplicate keys are refused rather than silently overwritten, and `--allow-partial` is labelled a
  diagnostic.
- **Provenance is projected from the row that qualified**, through a `CROSS APPLY`, instead of two
  unordered `TOP 1` subqueries that were not bound to it. The duplicated `EXISTS` is **removed rather
  than kept as a belt** — two places encoding one predicate is the defect this file spent the day
  closing.

### Before the run — what the instrument owed, and now carries

Two things stood between the corrected instrument and a result worth believing, and both are the same
lesson arriving early for once.

**Several erasures per board.** Whether a group gates progress depends on which cells are blank, and
the erasure decides that — so one seed made every board contribute a single observation while the
report presented a population share. **Third instance of this shape**, after the stall ceiling from one
greedy path and open-against-given from one ordering. The other two were corrected *after* the number
had been believed; this one before the run.

Blockage counts **any** erasure that stops outside progress rather than a majority: a board a player
can meet is a board that can be dealt, so the question is whether an unfair one exists, not whether it
is typical. `trials` and `stopped` carry the spread beside it, because one of three and three of three
are the same boolean and different findings.

**Only blockage needs the seeds.** Completions and derivability are read off the complete board with
the group hidden, no erasure involved, so tripling their cost would have changed nothing.

**And the output carries what produced it** — result schema, revision, sample, seeds, target, and the
definition of each metric. ⚠️ **A results file with no provenance cannot be told from a stale one**, and
the file previously on disk was exactly that: output from an instrument whose blockage column could not
vary, with nothing inside it saying so. `result schema 2` is what distinguishes the two now.

## v12 — verified, none rejected. **All four closed.**

| Finding | State | What it was |
|---|---|---|
| P1-01 the guard accepted the implementation it replaced | **closed** | `assert ... in (True, False)` |
| P2-01 coverage counted group evaluations as erasures | **closed** | nine successes for one call on a nine-group board |
| P2-02 provenance published as complete without identifying the code | **closed** | `--dirty` does not see untracked files |
| P2-03 every run staged through the same pending filename | **closed** | an atomic rename does not protect preparation |

### v12-P1-01 — the fifth tautological guard, in the class that exists to prove the fix

`assert metrics.stops_progress(...) in (True, False)` is satisfied by the corrected function **and by
the one it replaced**, so reverting the fix would have left the named guard green. The project records
a fix as closed under the rule that it must have a test that fails without it, and this one did not
satisfy that rule.

It uses a deterministic fake solver now and asserts exact outcomes both ways, plus a case that
demonstrates **the old construction compared a board with itself** on the same input where the
production function must disagree. Derivability likewise asserts a known-derivable and a
known-underivable board rather than membership in the set of booleans.

⚠️ **Five guards of this shape in one day**, and the pattern is always the same: a test written
immediately after the fix, asserting what the fixed code obviously does rather than what the broken
code obviously did not. **The question that catches it is not "does this assert the right thing" but
"would this have failed yesterday".**

### v12-P2-01 — a denominator and a coverage figure are different numbers

`erase` runs once per direction and seed, before the direction becomes slot groups. Reporting
`groups × seeds` as *erasures attempted* counted group-erasure evaluations, and summing `group.trials`
claimed one successful erasure once per group on its board — nine successes for one call on a
nine-group direction. The repeated count is the right denominator for a per-group per-erasure rate and
the wrong measure of how often the eraser worked; both are printed now, each labelled as what it is.

### v12-P2-02 — a stamp that cannot identify the code must not publish

`git describe --dirty` does not see untracked files, so an untracked helper changed the result while
the revision read clean. The stamp asks for untracked state explicitly and carries a **hash of
`measure.py` and `metrics.py` as they ran** — a commit says what was committed, a hash says what ran.
And a run whose revision comes back `unknown` **refuses to publish**, rather than occupying the name a
decision gets read from.

### v12-P2-03 — the same class already removed once

Every run staged through `results.txt.pending`. An atomic final rename protects the destination and not
the preparation, which is exactly the finding closed in the reference publisher two days ago. Staging
is per process with a nonce, cleaned in `finally`.

## v15 — verified, none rejected. **All three closed, plus two of three further improvements.**

Three findings, all inside the v14 repairs. **v14 fixed what the digests covered; v15 found what they
did when they could not cover anything.**

### v15-P1-01 — `clean` was what an empty path list meant, whatever the bytes said

`_describe` returned `clean` the moment its path list was empty and never looked at `contents`. Paths
and bytes come from **two commands against a mutable working tree**: `git status` can report nothing
tracked while `git diff` carries a change made between the two calls, and the stamp then certifies a
clean tree over a run that used an edited solver, eraser or verifier — none of which the three-file
instrument hash covered.

**The two directions are not symmetric, and only one is dangerous.** Contents without paths
under-reports and is now `unknown`. Paths without contents over-reports and is kept dirty, because a
dirty digest over a tree that has since been restored costs one unnecessary rerun, which is the right
way to be wrong.

**An unreadable untracked file became the literal string `<unreadable>` and published anyway**, so two
different files nobody could read were one identity. Same rule as the diff: a failure to read is not a
reading. It returns `None`, and `None` is unknown.

**And porcelain is parsed with `-z`.** In the text form git quotes and escapes any awkward path, so
`"src/a\tb.py"` arrived with its quotes attached, opened nothing, and became that marker — the failure
feeding itself. A rename's source path is its own NUL-terminated record and is consumed rather than read
as the next status line.

### v15-P2-01 — an existence test standing in for writability

The early gate asked `out.parent.is_dir()`. A directory sitting at `out`, a read-only parent, a full
disk — every one passes and fails five hours later inside `publish()`, which is exactly the cost
`v14-P2-01` moved the provenance gate to avoid, one field over. **The only check that answers the
question is the operation**, so it now writes a uniquely named probe in the destination's own directory,
replaces it, and removes both.

Also here: the publication gate requires the identity to **name its inputs**, which the preflight cannot
ask because nothing is loaded yet — otherwise a stamp reading `inputs not yet loaded` would certify an
artifact that names no data. And `--output` with no value says so instead of raising `IndexError`.

### v15-P2-02 — the annotation and the constructor described different languages

The v13 repair accepted a list and canonicalised it to a tuple, while the field stayed annotated
`tuple[str, ...] | None`. A typed producer could not use the supported path without an error, and a
mutable container was admitted into a frozen object whose entire purpose is that a signed package cannot
change after signing.

**Resolved by refusing rather than converting.** No caller passes a list, and `from_json` converts at the
parse boundary — which is where a conversion belongs, and is why JSON's list still round-trips. One
contract in three places instead of two contracts in two.

### ⚠️ The sixth guard that did not guard, and this time reverting found it

Every fix in v13, v14 and v15 was checked by reverting it and watching a named test go red. In v15 two
mutations left the suite green:

| Mutation | What it turned out to be |
|---|---|
| `status == "??"` → `startswith("?")` | a **bad mutation** — behaviourally identical, since no other status starts with `?`. Re-run against the real revert (`-z` parsing → `splitlines()`), two tests failed |
| the probe's **write** removed entirely | **a real hole.** Every destination test exercises the `is_dir()` branch and none of them the writing, so "writability is proved by writing" had no test at all |

The second is this project's named shape, in code written to close a finding about the same shape. The
guard now states what it forbids: the write is made to fail and a refusal must follow, so an
implementation that stops writing never triggers it and fails there.

**And the first is worth keeping as method.** A mutation that changes nothing observable is not evidence
the guard is weak; it is evidence the mutation was not a revert. Reverting has to mean *the previous
implementation*, not *a nearby edit*.

## v14 — verified, none rejected. **All three closed, plus two of three further improvements.**

Three findings, all downstream of v13's closures. The pattern is worth stating: **v13 built the right
mechanism and v14 found it was measuring the wrong thing.** A fix that is structurally correct and
substantively empty is harder to see than a missing fix, because the mechanism is there to point at.

### v14-P1-01 — the digests covered the names, not the things

**The input digest hashed `game_id:offense_team`.** That is a label. Every batting, footnote and
pitching value, and every lineup slot — everything `groups_in` actually reads — could change under the
same label and the digest would not move. A loader repair, a database reload or a corrected roster
produces a different measurement under an identical provenance. The v13 test changed the *sample* by
adding a direction; it never held the identifiers fixed and changed a board, which is the only case that
distinguishes the two implementations.

Now digested per direction over `cell_values(direction)` and `loaded.slots` — **scoped to what the
measurement consumes**, not to everything the loader carries, so the digest cannot move for reasons that
cannot change a number.

**The artifact printed a count where it promised a list.** The docstring said the identifiers sat beside
the digest so it could be checked; `provenance()` rendered `over N directions`. The aggregate says two
runs differ and cannot say *which board* differs. The stamp now lists every `identifier digest` pair.

**The tree digest hashed porcelain status lines.** Status codes and paths, not bytes — so two different
edits to the same file were the same dirty tree. Tracked changes are now digested from `git diff
--binary HEAD` and untracked files from their own bytes.

**And `source_hashes()` covered `measure.py` and `metrics.py` only.** The loader that chooses the sample
and builds every board lives in a sibling discovery directory, so neither that hash nor the revision's
dependency graph reached it. Added.

⚠️ **One near miss worth keeping.** The first attempt asked the *text* helper for `diff --binary`, whose
output no text pipe can decode: the reader thread died and the caller raised. One step more graceful and
it would have returned an empty string — and **an empty diff reads as *nothing changed***, so a failure
to read the tree would have published a dirty tree as clean. The bytes helper returns `None` on failure,
and `None` is unknown rather than empty, with a test that injects the failure.

### v14-P2-01 — a refusal that fired after the work it was meant to save

`identify()` knows before any data is loaded whether the repository questions were answerable, and
nothing later can repair an `unknown` field. The check nevertheless ran after the sample, three seeds of
erasure across every direction, every solve and the rendered report — so a transient `git` failure
consumed the run's full length before refusing to publish, presenting for hours as a progressing
experiment that was never eligible.

Moved immediately after `identify()`, with the pre-publication check kept because a publication path
that trusts an earlier check is one refactor from having no check. **The guard replaces `load` with a
function that fails the test if called.** The output destination is validated in the same place, for the
same reason.

### v14-P2-02 — the container repair had no regression guard

v13-P2-01 was recorded closed on a manual check. Reverting `_check_slot_references` to accept any
`Sequence`, or removing the tuple canonicalisation, would have left every boundary test green: the
existing ones test a *short* tuple and an *empty* one, both of which fail on length whatever the
container is.

⚠️ **The backlog's wording was the problem, not just the missing test.** "Verified both ways" was true
of a manual check and reads as an automated one — which is how a ledger stops corresponding to the
repository. Two `Package(...)` tests now hold it: a bare string is refused by type, and a list is stored
as a tuple whose serialisation does not change when the caller mutates what it passed.

### Further improvements

**Taken:** the result schema is now 4, so label-digesting artifacts cannot present as this contract; and
the output destination is checked alongside the early provenance gate.

**Not taken:** a lint command naming both trees belongs with the CI workflow, which does not exist yet.
`per-file-ignores` now covers `../discovery`, which is what made the T201 noise stop hiding real
findings, but **nothing still runs ruff over that tree automatically.**

## v13 — verified, none rejected. **All three closed.**

Three findings, all in the group instrument, all about the part of it that certifies the rest.

### v13-P1-01 — the stamp described a different run from the one it stamped

Three faults in one block, and they compound:

**Gathered at the end.** `provenance()` called `git` itself, after every board had been measured. A run
of this instrument takes hours, which is ample time for `measure.py`, the branch or the working tree to
change — so an edit landing mid-run was recorded as the state the run *finished* in, which is precisely
the change the stamp exists to expose. Capture is now `identify()`, called first thing in `main` and
frozen; `provenance()` only formats what it is handed. **The guard is stated as what it forbids**: `_git`
is monkeypatched to fail the test if it is called at all, so a version that asks the repository again
cannot pass.

**It named no input.** The stamp carried a direction *count*. The database can change between runs while
the revision and the source digest are byte-identical, so two different samples arrived under one
provenance and nothing in the artifact could tell them apart. `with_inputs()` now digests the sampled
directions immediately after `load()` and **records the sorted identifiers beside the digest**, so the
digest can be checked rather than trusted. Sorted before hashing, so a reordered sample reads as the
same inputs.

**It refused on one question of two.** Only `revision unknown` blocked publication. A failed `git status`
published a result that could not say whether an untracked file had shadowed an imported dependency —
the absence of a check reading as the presence of a passing one, which is the failure mode CLAUDE.md
names first. `publishable` now requires all three, parameterised over each field. And tracked edits are
separated from untracked files, each with a digest of its own contents: counting them together made an
ordinary edit read as an unknown file, and two different dirty trees with the same count identical.

### v13-P2-01 — the container was never checked, only its contents

`_check_slot_references` took a `Sequence[str]` and validated length, per-item grammar and uniqueness. A
`str` **is** a `Sequence`, so a nine-row package given `"123456789"` passed all three — nine characters,
each matching `^[1-9][a-z]?$`, all distinct. A `list` passed too, which defeats the frozen dataclass: the
caller keeps a reference and can mutate the package after construction.

It now takes `object`, rejects `str` and anything that is not a tuple or list by name, and
`__post_init__` canonicalises to a tuple through `object.__setattr__`. **Superseded by `v15-P2-02`:
the canonicalisation is gone and a list is refused outright, because accepting one made the field's
annotation and its constructor say different things.**

⚠️ **Closed on a manual check, which v14-P2-02 correctly refused.** This paragraph said "verified both
ways", which was true of a session command and reads as a test. Two `Package(...)` guards at the
boundary now hold it, each confirmed to fail when its half of the repair is reverted.

### v13-P2-02 — a staging name that could not be tested

The per-writer staging path was correct and unreachable. Inline in `main`, behind a database sample and
an hour of solving, neither the uniqueness of the name nor the cleanup on failure could be exercised —
the only guard available was a grep for `getpid`, which is the shape of check this project has recorded
failing five times.

Extracted into `publish(out, text, pid, nonce)`, with `pid` and `nonce` as parameters for exactly that
reason: **a test that cannot force a collision cannot show the name is what prevents one.** Four guards
now hold it — two publications to one destination stage different paths, the nonce separates runs that
share a pid, the staging file lives in the destination's own directory because `replace` is atomic only
within a filesystem, and a failed `replace` leaves nothing behind.

## v11 — verified, none rejected. **All four closed.**

| Finding | State | What it was |
|---|---|---|
| P1-01 the counterfactual baseline left the group hidden | **closed** | and it invalidated the run in flight |
| P2-01 unequal and zero trial exposure | **closed** | one boolean over one, two or three trials |
| P2-02 report titles chose statistical denominators | **closed** | `_eligible()` matched on the heading string |
| P2-03 the stamp did not identify the code that ran | **closed** | a loose ref, no dirty state, no owned artifact |

### v11-P1-01 — the same blindness, one level in

The baseline removed every cell in the sampled erasure. **Footnote cells are erasable**, so when the
erasure had already hidden the group, baseline and treatment were the same board and blockage was
forced false — **on exactly the published states the question is about**. A low rate could not be told
from a baseline that never revealed the assignment.

⚠️ **This is the third time this instrument produced a number that could not have been anything else**,
and the second time it was the blockage metric. First it could not vary at all; then it could not fire
where it mattered. Each fix was correct and each left the next one standing, which is what makes the
class worth naming rather than the bug: **a measurement can be blind in a way that shows up as a
plausible value.**

The run in flight when this landed was stopped. It was measuring the same thing the same way.

### v11-P2-02 — display copy deciding statistics

`_eligible()` chose a population by testing whether a heading began with `DERIVABLE` or `HIDING`.
Renaming a heading would have restored the unconditional denominator with nothing failing — the
fragment stays in the file, and the tests looked for the fragment. **Formatting deciding a statistical
question is the same shape as formatting deciding a domain rule**, which this project has now had four
times.

Each row carries its eligibility, numerator and denominator as callables, and the tests call `report()`
over a mixed set and assert both halves of every fraction.

### What the tests changed to

Every test written for this instrument until now asserted on **source text** or on **trace activity**,
and every one passed while the thing it guarded was broken. The measurements are pure functions in
`metrics.py` and the tests call them — including a constructed adversarial case where the erasure
contains the group, and an assertion that the *old* construction compared a board with itself.

## v10 — verified, none rejected. **All four closed.**

| Finding | State | What it was |
|---|---|---|
| P2-01 blockage observed a dependency instead of testing one | **closed** | the strongest blockage read as none |
| P2-02 an unmeasured trial counted as a negative | **closed** | `erase` returning nothing became an empty erasure |
| P2-03 a conditional rate with an unconditional denominator | **closed** | every group counted against derivability |
| P3-01 the two construction paths had different error contracts | **closed** | a non-string reference raised `TypeError` |

### v10-P2-01 — using a value and needing it are different claims

Blockage marked a group when some outside deduction *recorded a dependency* on it. That is evidence one
solver path used the value. **When hiding the group prevents the outside deduction from happening at
all, no such step exists** — so the strongest possible blockage read as no blockage.

It is a counterfactual now: the same erased puzzle solved with the assignment available and with it
additionally hidden, and blockage is an outside cell the baseline reaches and the treatment does not.
*Used* survives as its own reading, because the weaker claim is still worth having and folding it into
the stronger one is how the two got confused.

### v10-P2-02 and P2-03 — the denominators

An `erase` that reached nothing became an empty erasure and therefore a measured negative, biasing the
rate downward — **selectively**, since boards that resist erasure are not a random subset. `blocked` is
three-valued now and unmeasured trials are excluded and counted in a coverage line.

And derivability is conditional on there being one completion. Ambiguous groups were contributing
negatives to a rate whose denominator should hold only the groups where there is something to derive,
which conflates *no unique assignment* with *a unique assignment the solver cannot reach* — again, two
findings with different fixes.

### v10-P3-01 — the same field, two error contracts

The element type check lived in the parser, so `Package(slot_references=(1,))` handed a non-string to
the regex and raised a bare `TypeError`. Both paths are supported, so neither is the exception. Moved
into the shared helper, with the offending index in the message.

⚠️ **And the first attempt at that fix silently did nothing** — a `str.replace` whose pattern did not
match, without an assertion on the count. Caught by the tests, which is the second line of defence and
not the first.

## v09 — verified, none rejected

| Finding | Verdict | What was confirmed |
|---|---|---|
| P2-02 the group run cannot observe what it reports | real, **and it invalidates a result I reported** | `had_to_resolve` is structurally impossible |
| P1-01 an untrusted key can replace production inventory | real | both banners print, and the key is never compared to the pinned one |
| P2-01 the default constructor emits documents its own reader refuses | real | `__post_init__` returns early on the normal path |

### v09-P2-02 — I reported a structural zero as a measurement

`groups_in()` hides one slot group's footnote cells and **leaves every other cell given**. So every
cell the solver deduces is one of the hidden ones, the generator behind `any(...)` is empty, and
`had_to_resolve` **cannot be true on any board**.

⚠️ **I read that column as "0% everywhere: the assignment never blocks the rest of the board" and said
so.** It is not a finding about puzzles. It is a metric that has one possible value, reported as though
it had two — the project's own *a check that never fires* defect, in the output rather than in a guard,
where it is harder to see because it looks like data.

**And `unique` conflates two questions.** It is true when the restricted human solver finishes *and*
reproduces the hidden values, so a false result means either several assignments exist or one exists
and the implemented techniques did not reach it. The report calls the share "uniquely solvable", which
is only one of those. Mathematical uniqueness needs the enumerator at `limit=2`; human derivability is
a second axis, not the same one.

**What survives from the run:** the technique split — one-row groups resolve by propagation, two-row
and larger by bounding, 100% either way on 2,038 and 121 cases. That one is measured. The rest of the
table is either underpowered or structurally fixed.

### v09-P1-01 — two banners, and no comparison with the key that matters

**Both print.** Replacing the fixtures block left its `print` lines behind, so an ephemeral run
announces itself correctly and then says it was signed with a key that lives in the repository. One of
those is false, and an operator classifying the artifacts reads both.

**And the writer never compares the key it signs with against `serve/data/signing-public-key.hex`** —
zero references to it. Signing with a valid Ed25519 key that is not *the* key produces a batch that
self-verifies, replaces the live manifest, and is refused by `serve`: an outage reported as a
successful certified commit. Ephemeral and production also publish through the same `OUT`, so the
untrusted mode can overwrite the trusted namespace.

**Refusing at read time preserves integrity and not availability**, which is the distinction the fix
turns on.

### v09-P2-01 — the constructor and the parser apply different rules

`__post_init__` returns early when `schema is None`, which is the normal path, so a package with no
references serialises as schema 2 and `from_json` refuses it. Duplicates and malformed values pass
construction too. The reference writer's read-back catches it for that one caller; the shared type
still lets any other producer build a file the shared reader rejects.

## v09 — verified, none rejected. **All three closed.**

| Finding | State | What it was |
|---|---|---|
| P1-01 an untrusted key could replace production inventory | **closed** | both modes published through `serve/`, and the key was never compared with the pinned one |
| P2-01 the constructor emitted documents its own reader refuses | **closed** | `__post_init__` returned early on the normal path |
| P2-02 the group instrument could not observe what it reported | **closed** | `had_to_resolve` was structurally impossible |

### v09-P1-01 — refusing at read time preserves integrity, not availability

Both modes wrote to `serve/data/puzzles`, so an `--ephemeral` run — no key needed, and anyone who can
execute the writer can start one — replaced the live manifest with one signed by a key `serve` does not
hold. **`serve` refusing it correctly is the outage**: the inventory goes dark while the publisher
reports a certified commit. Ephemeral batches now write outside `serve/` entirely, which is stronger
than a reader that rejects them.

And a production key is compared with `serve/data/signing-public-key.hex` **before the first filesystem
mutation**. Self-verification used the public half of the key that had just signed, which proves the
batch is internally consistent and nothing about the deployed reader — a valid Ed25519 key that is not
*the* key produced the same outage by accident.

The stale fixtures banner was the smallest fault and the most revealing: replacing that block left its
`print` lines behind, so an ephemeral run announced itself correctly **and then said it was signed with
a key living in the repository**. One of those was false and an operator classifying artifacts read both.

### v09-P2-02 — a check that never fires, in the output

`had_to_resolve` hid one slot group's footnote cells and left every other cell given, so every deduction
was a hidden cell and no later one could depend on them. **It read `0%` on every board and was reported
as a finding** — *the assignment never blocks the rest of the board* — before anyone noticed the column
had one possible value.

⚠️ **This is the project's named defect in the place hardest to see it.** A guard that never fires looks
like a guard; a *number* that cannot vary looks like data, and data is what decisions are made from.
`tests/test_group_metrics.py` asserts both directions: a complete board deduces nothing outside the
group, and an erased one does.

And `unique` conflated cardinality with derivability. Several completions is a **generator constraint**;
one completion the solver misses is a **technique question**. Two axes now — the verifier's enumerator
at `limit=2`, and the restricted solver.

## v08 — verified, none rejected. **Six of seven closed.**

| Finding | State | What it was |
|---|---|---|
| P2-01 the v2 contract described what the producer stopped emitting | **closed** | suffixed labels and a nullable LOB, in the document `serve` builds against |
| P1-02 contradictions skipped the global identity | **closed** | the phase split for *choosing* moves was applied to *validating* |
| P1-01 the writer committed an unsigned manifest | **closed** | `sign_manifest` existed and was never called |
| P1-04 `--ephemeral` could sign with the production key | **closed** | the environment key won whenever it was set |
| P1-03 version 1 is not readable despite the promise | **decided, migration owed** | dropping it makes `slot_references` required, which 32 fixtures do not supply |
| P2-02, P2-03 | open, small | |

**All seven are in code written the same day.** Three are the project's own named patterns turned on
itself: *a justification travels* (the phase split), *a check that exists and is never invoked*
(`sign_manifest`), and *a mechanism kept past its problem* (version 1 compatibility).

### v08-P1-01 — the level where nothing else would notice

`sign_manifest()` was written, with a docstring explaining why package signatures do not authenticate
the selected set, and the writer committed a plain dictionary. The signature is one level **above** the
code it protects, which is where an omission has nothing beneath it to fail.

Tests now tamper with the generation and with the puzzle list separately, because the second is the
attack the packages cannot see: every id left in the list still verifies.

### v08-P1-03 — decided, and the consequence is larger than the line

Dropping version 1 is right: no consumer exists, and the alternative is a legacy HMAC verifier nobody
would run. But **the version follows the payload**, so a package without slot references *is* a version
1 package — and dropping the version makes the field required, which 32 fixtures do not supply.

Left behind a `TODO` naming the finding rather than 32 red tests or a blind pattern across fixtures at
the end of a session. The migration is mechanical and wants to be watched.

## v07 — verified, none rejected, both closed

| Finding | Verdict | What was confirmed |
|---|---|---|
| P1-01 the control confounds assignment with term volume | real | both cohorts built with `terms >= 2` |
| P2-01 the suffix guard accepts more than one digit | real | `-\d` matches `PH-2` and misses `PH-10` |

### v07-P1-01 — the control had the confound it exists to remove

The named control compares a one-row group against a two-row group to isolate **assignment**: term
count fixed, only the number of possible carriers changing. It was implemented as `terms >= 2` on both
sides — and a multi-row group has more chances to contain events, so its term distribution is heavier.
A lower rate could then come from carrying more terms, from assignment ambiguity, or from both, **and
the text beside it claimed it could tell them apart**.

Exactly two terms on both sides now, and repeated at three, with the stratified `(rows, terms)` table
named as authoritative and the control described as one slice of it rather than as a separate result.

### v07-P2-01 — a guard green on the numbers a long game produces

`-\d` matches one digit, so `P-10` and `PH-12` passed a check meant to reject every numbered label —
and those are exactly the values a substitution-heavy game produces, which is where the grouping
matters most. The pattern takes any width now, and the can-it-fire case is **synthetic and carries both
widths**: one historical file cannot define the adversarial space, which is what the first version
leaned on.

## v06 — verified, none rejected. **All five are in code written today.**

| Finding | Verdict | What was confirmed |
|---|---|---|
| P1-01 open-versus-given is not paired by trajectory | real, **and it undercuts the decision it was run for** | the list is filtered *before* it is ordered |
| P1-02 zero-stall outcomes are dropped as failures | real | `... if ceiling else None`, and 48 directions produced 47 pairs |
| P2-01 the group report aggregates what it must not | real | `min(group.terms, 4)`, and technique keyed on rows alone |
| P2-02 surface parity is prefix-sensitive and batting-only | real | rejects `LABEL: ref`, not `LABEL: other, ref` |
| P2-03 a prototype still shows suffixed labels | real | `3B-2`, `P-2`, `P-3`, `PH-2`, `PH-3`, `PH-4` |

### v06-P1-01 — I rebuilt the confound I had been taught, in the measurement that answered the question

`walk()` filters the footnote cells out of the candidate list **and then orders it**. `_row_first`
buckets by row, so the two treatments have buckets of different lengths, the same seed produces
different shuffles, and **the common cells do not keep their order**. The two walks differ in the
treatment *and* in the erasure trajectory.

This is v03-P2-05 exactly — the finding the operator explained, that I recorded as a lesson to carry
forward, and whose fix I wrote down in this file: *one stable priority permutation for the cells the
configurations share, separately controlled insertion for the new ones.* I then wrote the measurement
without it.

⚠️ **What it costs is not the number, it is the conclusion.** *Footnotes stay erasable* rests on that
run, and so does everything that followed from it — that P1-02 is real work, that an erased attribution
needs a representation, that the design document was the wrong one. **47 of 47 in one direction is
strong, and unanimity cannot repair a confound**: if the given treatment's order is systematically
worse, every board moves the same way. The claim is not refuted; it is unsupported.

**The fix is the one already written down**: one deterministic priority over the union, the given order
obtained by filtering that order, several matched seeds, and paired deltas with counts.

### v06-P1-02 — a zero is an outcome, not a failure

`walk()` returns `None` when the ceiling is zero, which is exactly the board where the given treatment
made no progress — the most informative case for the question being asked — and the caller drops the
whole pair. 48 directions produced 47. **The bias removes the weakest results of the weaker treatment**,
so given-footnote reach and median ceiling are both overstated.

A real failure needs a status of its own; a zero needs to be counted.

### v06-P2-01 — the report aggregates the two dimensions its own contract separates

`min(group.terms, 4)` files every group of four or more terms under *four*, and the technique section
keys on rows alone. The instruction was explicit: **not "three or more" and not "two or more terms" —
if solvability falls, where it falls is the finding.** An aggregate can look reassuring while one
`(rows, terms)` cell fails, which is the threshold the whole run exists to find.

### v06-P2-02 — a guard weaker than the sentence above it

The negative check rejects `LABEL: reference` and passes `LABEL: other, reference`, so a leak in any
position but the first survives. The positive check asserts only that a label appears, so any reference
under it satisfies. And the table half enumerates `board.batting` while the module docstring claims
every erased cell — pitching and the line score are not compared at all.

### v06-P2-03 — a prototype showing a visual language the product no longer has

`substitute-grouping-sample.html` still renders `3B-2`, `P-2`, `PH-4`. I said in conversation that it
was not comparable and **did not mark it in the file**, which is the difference between a note and a
guard. Regenerate it or move it out of the active set.

## v05 — verified, none rejected

| Finding | Verdict | State | What was confirmed |
|---|---|---|---|
| P1-03 the writer signs with a repository-known fallback | real | **closed** | no executable boundary enforced the comment |
| P2-01 `ambiguity()` now measures duplicate positions | real | **closed** | it grouped by `labels`, which no longer disambiguate |
| P2-02 search-cost thresholds are in an obsolete unit | real | **closed** | normalised 0–1 compared against 5, 10, 20 |
| P2-03 the prototypes need ~405px, not 375 | real | **closed** | 375px section plus 14px body padding, and no viewport meta |
| P2-04 the new guards do not exercise what they claim | real, mine | **closed** | see below |
| P1-02 the renderers hand back erased footnotes | real | **half closed** | mechanical half done; the representation waits on the group run |
| P1-01 lineup slots do not cross the package boundary | real | open, **needs a schema decision** | `Package` carries no slots and they cannot be reconstructed |

**Five of seven closed.** What is left is one half-finished repair whose remaining half is a design
question the running measurement answers, and one that cannot be done without deciding what happens to
a schema the format document calls frozen.

### v05-P1-03 — closed

A missing `BOXSCORE_SIGNING_SECRET` made the writer sign with a key that lives in this repository,
write into `serve/data/puzzles`, and pass the same certification path as a real batch — so anyone
holding the repository could forge a package indistinguishable from forge output, and nothing
executable enforced the comment saying otherwise.

A missing secret is an error now. The repository key is reachable only through `--fixtures`, which
prints what it is. The tests assert the *ordering* — that the fixture key cannot be assigned on any
path that has not first tested the flag — rather than that the flag exists.

### v05-P2-01 — closed

`ambiguity()` grouped by position label and erased the group's footnote cells as one domain. Sound
while a repeated label meant a shared slot; with bare labels, **42.1% of repeated labels span more than
one slot**, so it would have built a domain over men who never replaced each other and reported the
solver's reaction as footnote ambiguity.

Unwired and left as a **named refusal** rather than deleted, so a reader who remembers it learns why.
What replaces it is an invariant rather than an experiment: a reference names exactly one row.

### v05-P2-02 — closed

Thresholds of 5, 10 and 20 against a metric that runs 0 to 1 — a raw count from an earlier solver whose
numbers outlived it. **Every answer was 0.0% whatever the data said**, so the section could neither
support nor refute the claim it exists to test. Compared against the real steps' own median and p90
now, with the metric's range printed beside it.

### v05-P2-03 — closed

Each prototype claimed 375px and needed about 405. All four now carry a document shell, the viewport
declaration, border-box sizing and a section that is 375px including borders. A test asserts the four
properties per file, with a can-it-fire case.

### v05-P2-04 — closed

The position table had no `started_at` column, so every "starter" case ran the fallback and the branch
that fixed the two-third-basemen defect was untested; it now leads the table. The cell-equals-footnote
test assigned both names from one expression; it reads the two real consumers now — the cell the table
draws and the string the line prints.

⚠️ **A third tautology was written while fixing these and caught before commit**, by asking what change
the guard would let through rather than rereading what it asserts.

### v05-P1-02 — the printed board is easier than the board that was graded

`erasable()` includes the per-batter footnote cells, `to_board` correctly turns an erased one into
`None`, and stalls, chain and layer 3b are all measured with it unknown. Then `build_pack` prints the
footnote line from **`loaded.direction`** — the complete source — while the grid beside it draws
`candidate.puzzle`. **A value removed for grading is handed back on the page.**

This is not v02-P1-01 again. That fixed `Direction → Board`; this is `Board → the human-visible
artifact`, one boundary further out, and the same shape.

⚠️ **The ceiling pack built this evening is affected**, and so would the ladder be. Any answer about
perceived difficulty, tedium or layer 3b would be about a board nobody solved. **Do not print a pack
until the footnote line comes from `candidate.puzzle.footnotes`** — which also needs a visible
representation for an erased attribution, since a blank in a sparse line has to be resolvable rather
than merely absent.

And the documents disagree in a way that makes recurrence easy: `CLAUDE.md` says the per-batter
footnotes are erasable, and a still-active design section says the footnote line is complete and never
erased.

### v05-P2-04 — two guards written today that do not guard

Both are mine and both were written in the commits that closed other findings.

- **`_position` is called with three arguments** in the parameterisation, so `started_at` defaults to
  `None` and every "starter" case exercises the fallback path. **The branch that fixed the
  two-third-basemen defect is not covered by the test written for it.**
- **`test_the_cell_and_the_footnote_are_the_same_string_for_the_same_row` assigns both names from the
  same expression.** It is a tautology: it stays green if `board_table` or `footnote_line` stops
  calling `slot_references` entirely, which is the only thing it was meant to prevent.
- The AST guard matches a punctuation literal with `in` against a name containing `label`, and misses
  `startswith`, indexing, regexes and aliases — and exempts by basename, so a new renderer with the
  same filename inherits the exemption.

**This is a check that never fires, written by someone who had just recorded that a check which never
fires is indistinguishable from a broken one.** The rule was known and applied to other people's code
in the same session.

## v04 — verified, none rejected

| Finding | Verdict | State | What was confirmed |
|---|---|---|---|
| P2-02 the ceiling pack overclaims "ceiling" | real | **closed** | one seed, one ordering, one greedy path per direction |
| P1-01 the manifest commit destroys the snapshot readers are following | real | open | and the sweep also eats a concurrent publisher's staging directory |
| P1-02 signed packages behind an unsigned manifest | real | open, **with v03-P2-04** | the release inventory is the one thing no signature covers |
| P2-01 provenance projected by two unordered `TOP 1` queries | real, **latent** | open | 0 of 203,908 games have more than one provenance row |
| P2-03 the comparator can null over a changed cohort | real | open | intersection compared, duplicates collapsed silently |
| P2-04 `families_used` and `family_counts` contradict each other | real | open | `family_counts` reads only `from_identity` |

### ⛔ The ceiling pack built tonight is unusable

Not because of the search — nine paths, a 21 lower bound and a 27% convergence figure all stand. Because
of **v05-P1-02**: its printed footnote line comes from the complete source while its grid draws the
erased puzzle, so the page is easier than the board its key describes. **The 21 is a valid number from
an invalid artifact.** Nothing about perceived difficulty, tedium or layer 3b can be read from it, and
no pack is printed until P1-02 is closed.

### v04-P2-02 — closed

Every ordering against three seeds, nine paths per board, keeping the best per board, and the prose
says **highest observed** with the sample size beside it rather than *ceiling* or *the top*.

**The rename was not the finding; the number was.** Nine paths raised the maximum from 19 to 21, and
the convergence figure the run now prints says **27% of boards found their best in the second half of
the search** — so nine starts were not enough either, and the figure stays a lower bound. One path was
a sample of size one from the space of erasure sets, and that is now measured rather than argued.


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

**The regeneration is done, and it is the good kind of null.** The stall model barely moved: 100% pool
coverage at every target from 5 to 12 before and after, blanks within 0 to 2 cells, chain one or two
lower, and the restart mix keeping its shape — column sums early, row identity taking over as the count
rises. **The duplicated list wasted compute and did not distort the conclusions**, which was not
knowable before it was corrected.

**Compressibility moved, and the conclusion it supported got stronger.** Against zero density it is
**+0.890** on the board the generator actually erases, where the demotion from ranking metric to
viability constraint was decided on +0.79 from the grid-only definition. The measurement was wrong and
the conclusion was right. Recorded in §5.

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

## What today's session found outside the reviews

Four defects that no review named, all found by rendering a board and reading it, and one pattern that
covers three of them.

### The batting rows did not correspond to a boxscore — four corrections, now one change

1. **The label named the wrong position.** A `CASE` over the `F_*_G` flags resolved by fixed priority,
   so a man who started in centre and moved to third was named for where he ended: a board with **two
   `3B` and no starting `CF`**, impossible for a starting nine and invisible to every §22 layer. The
   rule is **the position of entry** — `SUB_FLD_CD` for substitutes, the starting lineup for starters —
   one rule with two sources, and `retroGamesReg` carried the second all along. Verified end to end.
2. **The suffix is gone.** It existed so footnotes could name a unique row, and the reference moved to
   the lineup slot, which identifies a row without help. Two `CF` in different slots now read `CF`.
3. **Footnotes reference the slot**, from `slot_references` — the same call the slot cell prints, so
   `9b` in a cell cannot sit beside `9c` in a note.
4. **Rows grouped by slot**, substitutes indented with a rule between slots, and a slot column carrying
   the full reference. The PDF board is eight columns; the width came out of the label, not the board.

### The pattern: three decisions were reading a formatting convention

`indented()`, the pack's substitution filter and the reference writer all asked `"-" in label` when
each was asking about the **lineup slot**. They agreed while the suffix existed and **failed together
in the commit that removed it** — one silently, until the fifty-board pack aborted.

**The `audit()` that asserts rather than prints is what turned that into a message** instead of fifty
boards without a single substitution. That decision was made days earlier and paid for itself here.

Guarded now: `tests/test_no_label_formatting_decisions.py` walks every source file and refuses a
decision made on a label's formatting, with its own can-it-fire test using the exact broken expression.

### And two runs that owed numbers

- **The ceiling is not a ceiling.** Nine paths per board instead of one raised the maximum from 19 to
  21, and **27% of boards found their best in the second half of the search** — so nine was not enough
  either, and the figure remains a lower bound.
- **Nothing distinguishes at the extreme of its range.** At maximum compression 100% of boards need all
  four families; at a mid target the same measure opens into five combinations. Second metric to teach
  it, which is what makes it general rather than a quirk of difficulty.

### The fifty-board pack is not the pack that is wanted

It aborted twice today, and the second abort is the useful one: **0 uncertified boards where it wanted
about 17.** The diagnosis is not that layer 3b became trivial.

`TARGETS = (5, 7, 9, 11)` are **chain** rungs, and a chain-11 board carries about twenty-five blanks
where the observed stall maximum is twenty-one stalls at thirty-five. The gap was already measured —
**91% certified at chain 11 and 71% at chain 13** — so the whole pack sits below where 3b starts
failing. It is not broken; it is measuring the easy half of the range.

**So it is not migrated, it is replaced.** The pack that is wanted is the stall ladder — **19, 16, 13,
9 and 6** — which does not exist yet.

⚠️ **The rungs must be filled from boards of similar reach, or the ladder measures two things.** A
board whose observed maximum is 21 erased down to 6 stalls has structural room to spare; a board whose
maximum is 7 erased to 6 is squeezed to its limit. **Both are labelled "6 stalls" and there is no
reason to think they feel alike** — and nobody knows which of the two is representative, which is
exactly why they must not be mixed.

If the five rungs are filled from boards with widely different maxima, then stall count and *headroom*
vary together across the ladder and no answer separates them. The fix is cheap and the input already
exists: the ceiling run computes a per-board maximum, so **select boards within a narrow band of
maxima and let only the erasure target vary between rungs.** Then the one thing that changes from rung
to rung is the number of stalls, which is the thing being measured.

⚠️ **And the one-third uncertified quota stops making sense on a ladder.** With fixed rungs the
uncertified share is a **measured property of each rung** rather than something the pack imposes: the
19 rung carries boards 3b will not certify — the five at the top demonstrated it, four of five
uncertified — and the 6 rung will be almost entirely certified. The gap appears distributed by rung,
which is better evidence than a quota invented in advance. `audit()` must assert the rungs and the
composition, and **report** the uncertified share per rung rather than requiring a number.

## Noticed in passing

### One rule, two sources: the label is the position of *entry*

⚠️ **"Where he played, not how he arrived" was underspecified**, and this board is what showed it: a man
who played two positions has no single "where he played", so the `CASE` fell back on a fixed priority,
which is arbitrary. `ACY192107310 IN4` came out with **two `3B` and no starting `CF`** — impossible for
a starting nine, and no identity on the board can see it.

**The rule is the position of entry, and it is one rule rather than two.** A substitute enters at the
position `SUB_FLD_CD` records. A starter enters at the position the starting lineup records. Same rule,
different source, and the second source was never used: `retroGamesReg` carries
`{AWAY,HOME}_LINEUP{1..9}_{BAT_ID,FLD_CD}`, and for this game the away slot-6 code is **8 — centre
field**, exactly the man the `CASE` was calling a third baseman.

With it the board resolves itself: the slot-6 starter is `CF` because he began there, and the man
entering at slot 2 is `CF` because he entered there. Two centre fielders in different slots, which is
what the game did and what a printed boxscore prints.

**Recorded as knowingly lost:** a printed boxscore shows *both* positions — `lf,1b` — and one label
cannot. The entry position is the right one to keep, and the movement is information the board is
discarding on purpose rather than by oversight.

**The check that would have caught it** is a plausibility assertion rather than an arithmetic one: a
starting nine has exactly one man per fielding position. Worth measuring across the pool before it
becomes a gate, since sparse early-era fielding records may fail it honestly.



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

**Half fixed.** `per-file-ignores` now carries `"../discovery/**/*.py" = ["T201", "S105"]`, and
`discovery/footnote-groups/` lints and formats clean — which is what made the five real findings in it
visible at all, since they had been sitting under twenty-five reports of a script printing.

**Still open:** the rest of the tree reports **209** findings, led by `PLR2004`, `E402` (the `sys.path`
preamble every script needs) and `E501`. Those are real style debt rather than noise, so they are not
being ignored away; they need a pass. And **nothing still runs ruff over `../discovery` automatically** —
that belongs with the CI workflow, and CI does not exist yet.

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
