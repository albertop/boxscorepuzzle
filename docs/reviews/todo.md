# Review backlog

## ⬜ 2026-08-23 - the pre-push hook does not test the commits it is gating

**`docs/ci.md` carries the full account and the evidence.** Recorded here because it is an open decision,
not because the reasoning belongs in two places.

**One push delivered three commits and reported one.** GitHub logs a single PushEvent,
`before=fc61c9f head=942393a`; the local reflog says `update by push` to `2efeb52` two seconds earlier.
Two commits made **while the hook was running** reached `main` in a push invoked before they existed.

⚠️ **No delivery path skips the hook** - one tree, one push, no `post-commit` hook, no alias, no autopush.
That was the thing worth ruling out and it is ruled out.

⚠️⚠️ **The gap is different and smaller and real:** the hook discards the SHAs it is handed and runs the
suite against the working tree, so it tests **what is on disk while it runs** rather than what is being
pushed. On a thirteen-minute run the tree moves. *The hook passed* does not mean *what was pushed
passed*.

⬜ **The repair is a judgement, which is why it is not made here.** Checking the pushed SHA into a
temporary tree makes the hook test its payload, and makes it slower and stateful. Refusing to run when
HEAD moves mid-run is cheaper and narrower. **Which is right depends on whether the hook gates a push or
checks a machine** - the same question the hook-primary arrangement turns on.

⚠️ **Costs nothing meanwhile: do not commit while a push is running.** Done twice that day, unnoticed.

---
## ⚠️⚠️ 2026-08-23 - the hook caught what my own runs could not: I was verifying with a different command

**`uv run python -m pytest` all session; the hook runs `uv run pytest`.** `python -m` puts the working
directory on `sys.path` and plain `pytest` does not — so `publish/tests/test_health.py` importing
`from tests.test_rotation import ...` passed thirty-three times locally and **the pre-push hook refused
the push** with `ModuleNotFoundError: No module named 'tests'`.

**The import was the defect and the command was the reason it survived.** Every "33 passed" reported
during E1b came from an environment the gate does not use. ⚠️ **This is the fourth instrument failure
this week and the only one the project's own machinery caught** — the mutation harness reading a dead run
as green, the stale `.pyc`, the watcher matching `failed` inside `xfailed`, and this. The others were
found by looking; this one was found by the hook doing exactly what it is for.

**Fixed in configuration rather than in the invocation**: `pythonpath = ["src", "."]` in `publish`'s
pytest config, so both commands behave identically, plus a `conftest.py` holding the shared fixture so
no test module imports another. **The implicitness was the problem** — an environment that depends on
how a command was typed is one where the gate and the check can differ without either being wrong.

⚠️ **What is not fixed: nothing checks that the two commands agree.** `forge` and `keep` have no
cross-test imports today, so the same defect there would be invisible in the same way. Not built — the
honest guard is to stop using `python -m` for verification, which is a habit rather than a test.

---
## ✔ 2026-08-23 - `publish/`, a fourth tree, and what the mutation run changed about its tests

**E1b's rotation.** `docs/calendar.md` carries the design and now the code that enforces it.

### Why a sibling rather than a directory inside `serve/`

The deciding argument was not tidiness. **Inside `serve/`, §33's *deployment ships `serve/` only* would
have survived by wording** while its meaning changed silently from *static assets* to *assets plus a
service*. As a sibling it becomes visibly false and has to be rewritten. **A sentence that stays true by
wording while changing in substance is worse than one that visibly needs rewriting.**

Three other things were checked because they might have decided it and did not:

- **The tree guard is neutral.** `_ROOT.glob("*/pyproject.toml")` takes the parent directory name, so
  either placement demands the hook and a push workflow name it. Checked before choosing.
- **No imports in either direction.** The rotation copies JSON; the browser reads it over HTTP.
- **The relationship is one `forge` already has**: it writes into `serve/data/puzzles/` from outside
  `serve/` and never needed to live inside.

⚠️ **And `docs/javascript-conventions.md` needed no change at all**, which was the point: it says its
rules apply to *the hand-written JavaScript under `serve/`*, and with the sibling that stays true and
complete. A Python project inside would have made it describe half a tree.

### ⚠️⚠️ What the mutation run changed, and it was the fixture rather than the assertion

Four cases were written for the delete. **Removing the delete entirely turned only two of them red.**

The set-equality case - the one written precisely because *today in public and yesterday in public* is
true of a rotation that never removes anything - **pointed at an empty directory**, so a single run had
nothing to remove and it passed with the delete gone. **The assertion was right and the fixture was
empty.** That is the distinction between a test that watches the delete and one that watches the copies,
and no amount of care about the assertion would have found it.

Given something stale to start with, three of the four now go red.

### ⚠️ One mutation survived, and it is not a defect

Building the public manifest from the directory rather than from what was copied changes nothing in any
reachable state: the delete runs first, so the two are equal unless the delete has already failed - and
if it fails it raises. **Recorded rather than papered over with a contrived test.** Building it from what
was placed is the safer of two equivalent choices because it cannot compound a delete failure, and that
is the whole of its value.

### ⬜ What this creates for F

`docs/runbook-inventory.md` §5 and `CLAUDE.md` §33 both say only packages reach the VPS. **They stop being
true when F ships**, and F1.5 in the plan records it. Untouched today by instruction: E1b is
localhost-only, and §5 presupposes a serving VPS.

---
## ❌❌ 2026-08-23 - `main` has been red in CI for days, and four tests pass here by reading the real signing key

**Found while checking which workflows a push runs.** The `forge` workflow is `completed/failure` on
`fc61c9f`, `acb9781` and `e8e77f3` - three consecutive pushes - while the pre-push hook passed on the
laptop every time. **`CLAUDE.md` names this exact outcome:** *the failure mode is a red `main` nobody has
looked at yet.* Nobody had.

```
FAILED tests/test_signing_key_acquisition.py::TestWhereTheKeyComesFrom::test_the_file_is_enough_with_no_variable_set
FAILED tests/test_signing_key_acquisition.py::TestWhereTheKeyComesFrom::test_trailing_whitespace_in_the_file_is_not_a_different_key
FAILED tests/test_signing_key_acquisition.py::TestWhatItRefuses::test_neither_source_is_an_error_naming_both
FAILED tests/test_signing_key_acquisition.py::TestWhatItRefuses::test_an_unreadable_key_file_is_an_error_rather_than_a_missing_key
```

### ⚠️⚠️ CORRECTED 2026-08-23 - the conclusion held, the mechanism I wrote did not

**The first version of this entry said the four tests "go green having exercised the real key instead of
the throwaway one the fixture wrote." That is false, and it is kept here named as false** because the
shape recurs: a mechanism inferred from a failure message, plausible, written down without being run.
**It was corrected by instrumenting it**, which is the only thing that could have.

**What is actually there.** `key_and_destination()` carries **a complete second copy of the acquisition
rule** at lines 398-430, reading the writer's own imported `KEY_FILE`. It computes `material` - and
`material` is **never used again**. Line 444 is `return publication_key(), OUT`: the real rule runs
afterwards and reads the *module* global, which is what the fixture patches.

So the duplicate is **dead logic with two live effects**:

- On this laptop `writer.KEY_FILE` exists, so it **opens and reads the operator's real private key** into
  a variable that is discarded. Then `publication_key()` runs against the patched path and the
  assertions are satisfied by the fixture's throwaway key, exactly as intended.
- On a runner the file is absent, so the same block **raises before `publication_key()` is ever
  reached**, with a message naming a path the test did not choose. Four assertions about the temporary
  path then fail.

```
writer.KEY_FILE           : C:\Users\aperd\.boxscorepuzzle-signing-key
publication_key.KEY_FILE  : C:\Users\aperd\.boxscorepuzzle-signing-key
after patching the module, writer still says: C:\Users\aperd\.boxscorepuzzle-signing-key
```

⚠️⚠️ **The conclusion is unchanged and is sharper for it: the suite passes here only because the real key
file happens to exist.** Its presence is what keeps the vestigial block quiet long enough for execution
to reach the code under test. **The hook cannot see that, because the hook runs where the key is.**

⚠️ **And the duplicate is a leftover.** The rule moved to `boxscore_forge.publication_key` on 2026-08-22;
line 440's own comment says *"This function keeps what is genuinely its own: choosing the destination,
and the `--ephemeral` trust domain"* - while forty lines above it are still doing the acquisition it
says it no longer keeps. **A mechanism kept past the problem it solved**, which is a rule this project
already carries.

### ⚠️⚠️ The comment above the patch describes this defect and the code kept it

Lines 32-39 of the test say, in bold: *"These tests set `writer.KEY_FILE` ... patching the writer's names
would have patched **nothing that the check reads**. ... **Patch the module that owns the constant.**"*

**The cure was applied in the wrong direction.** The patch moved to the module - and the *reader* is
still the writer's imported binding, so the same sentence is now true with the two sides swapped. A
defect written down, understood, and reintroduced by its own fix.

### ⚠️ Why neither the hook nor the reviews caught it

**The hook cannot**: it runs on the one machine that has the key, which is the condition that makes the
tests pass. **CI can and did** - it is the only checker without the key - and CI is a report nobody read.
This is the concrete cost of *detection without prevention*, and it is the first time that cost has been
paid rather than described.

### ✔ FIXED 2026-08-23 — a consolidation finished, not a deletion

**It was live, for one day.** `dd4974b` (2026-08-21) introduced the block as *the* acquisition rule.
`c8df7a7` (2026-08-22) created `boxscore_forge.publication_key`, moved the rule there and added
`return publication_key(), OUT` — **and left the original standing.** So this is the second half of a
move that was never completed, not dead code that never ran.

**Is `publication_key()` the only copy now? Yes.** `build_inventory.py` calls it; nothing else
implements it. There was no third copy, and after this there is one.

**What removing its effect left behind:** the two things line 440's comment already said the function
keeps — the destination, and the `--ephemeral` trust-domain refusal. Neither reads `material`. The
*no key at all* refusal is not repeated either: `publication_key()` raises it with the same words from
the module that owns the path, so the message names the file the rule actually consulted.

### How it is kept fixed, and why there are two guards

**`test_no_module_outside_publication_key_imports_the_key_path`** — the part that carries this forward.
**Broad rather than narrow, and that was checked before choosing**: the writer was the only importer of
the name, and every other consumer reaches it as a module attribute, which is what makes it patchable.
An **AST walk**, because `docs/ci.md` records two failures of this guard shape here — `"keep"` matching
`keeps`, `sign(` matching inside `verify_signature(` — and verified the way both were found: by
reintroducing the import and watching it go red.

**`test_the_writer_consults_no_key_path_of_its_own`** — the behavioural half, and ⚠⚠ **written to survive
the fix it proves.** A case that can never fail again is one the next reader deletes as noise, and the
absence then reads as a passing check. So it asserts the *property* rather than the repair: **absence or
non-use both satisfy it.** With no such name bound it passes trivially; if a future import binds one, the
sentinel is installed and any use of it is red again. The static guard catches the import; this catches a
*use*.

⚠️ **Both were red on this laptop with the real key in place, and green after** — which is the whole
point. Nothing was deleted, moved or renamed: `~/.boxscorepuzzle-signing-key` is the one secret that
cannot be regenerated, and a test strategy needing it absent is one somebody eventually runs without
putting it back.

---
## ⬜ 2026-08-23 — two on `MANIFEST_SCHEMA`, found while answering *which schema is that `1`*

**Noticed in passing during the v5 documentation pass, reported in conversation, and not written down
until asked** — which is the rule this file exists to enforce, broken in the same session that closed
three instances of it elsewhere. *A defect mentioned in prose and not recorded is a defect nobody will
find again until a review finds it.* **Recorded, not fixed.**

### a) `write_reference_puzzles.py:334` spells the manifest version as a literal

```python
document = sign_manifest(
    {"schema": 1, "generation": generation, "puzzles": sorted(path.stem for path in staged)}, key
)
```

`build_inventory.py` has `MANIFEST_SCHEMA = 1` and uses it in both the manifest and the per-date
pointers. This is the **second copy of the same number**, in the other writer, and the file imports
nothing from `build_inventory` today — so it is a copy that cannot be de-duplicated by adding an import
alone; one of the two has to move somewhere both can reach.

⚠⚠ **And this now makes a *document* false, which is what raises it above tidiness.**
`docs/package-format-v5.md` was given a sentence on 2026-08-23 telling a reader that the manifest's
schema *"is `MANIFEST_SCHEMA` in `forge/scripts/build_inventory.py`"* — stated as the one place it
lives. **It is not, while this literal exists.** A pointer to *the* definition, when there are two, is
worse than no pointer: it tells the next reader they have found the thing to change.

⚠️ **Neither writer's number is currently wrong**, and that is why nothing has failed. Both say `1`.
The defect is that nothing makes them agree — the shape this project meets most often, and the reason a
version bump is the moment it would surface.

### b) `MANIFEST_SCHEMA` carries no docstring

`CLAUDE.md`'s constants rule: a value encoding a decision *records the reason it holds that value, the
measurement that set it, and whether it is provisional.* `MANIFEST_SCHEMA = 1` records none of it and
sits between `write_pointers` and `DAYS`, both of which are documented at length.

⚠️ **This is why the question was asked at all.** `manifest.json` and a package both carry a key called
`schema`; one is `1` and the other is `5`, and nothing beside either says they are different formats
with independent version lines. **A reader who takes the `1` for a package version concludes the
inventory is four versions behind** — which is a plausible, wrong, and unprompted conclusion.

### What a fix has to decide, and why it is not being done here

**Where the constant lives.** `build_inventory.py` is a script and `write_reference_puzzles.py` is
another; neither imports the other, and §33 does not forbid it — they are both in `forge/`. The choices
are a shared module under `forge/src/`, or retiring the reference writer's manifest path if
`build_inventory` has superseded it. **That is a judgement about which writer survives**, not a rename,
and it belongs with whoever decides that.

---
## ⚠⚠ 2026-08-23 — a mutation restore that a stale `.pyc` survived, and the suite ran the mutant

**Found by accident, and it is the most dangerous harness failure of the three this week.**

A mutation run changed `SCHEMA_VERSION: Final = 5` to `6`, ran, and restored the file. `git diff` was
clean and `grep` showed `= 5`. **The next full run imported it as `6`** and reported ten failures against
code nobody had written.

⚠⚠ **Why the restore did not take: `5` and `6` are the same length.** CPython decides a `.pyc` is stale
from the source's **size and mtime**, and on Windows the mtime granularity is coarse enough that a
same-size rewrite inside the same tick looks unchanged. So the bytecode cache kept the mutant while
every text-level check — diff, grep, reading the file — agreed the source was correct.

**The two earlier harness failures were *silence*: a run that did not happen, read as a run that passed.
This one is worse.** The run happened, produced real output, and the output described a program that
exists nowhere. **Every text-level verification is blind to it by construction**, which is the shape
`CLAUDE.md` records as *ask what the instrument is supplying rather than measuring* — here the
interpreter was supplying the code.

### What to do about it

⬜ **Any harness that edits a `.py` and restores it must clear `__pycache__` after restoring**, or run
the child with `PYTHONDONTWRITEBYTECODE=1`. The second is better: it removes the class rather than
cleaning up after it, and costs nothing on a suite this size.

⚠️ **A same-length mutation is not exotic — it is the *normal* case.** `5`→`6`, `<`→`>`, `and`→`or`,
`True`→`​False` is not but `>=`→`<=` is. Every mutation this session that changed a Python file was at
risk, and the ones that reported *caught* were reporting truthfully only by luck of differing lengths.

⚠️ **Nothing in the repository has this defect** — the harnesses are scratch scripts, not committed
code. Recorded here because the next one will be written the same way.

---
## 2026-08-22 — ✔ v39: five findings, five closed — and ⬜ one number left to the operator

`docs/reviews/code_review_v39.md` carries the findings. All five were reproduced in the code before
anything was changed, and each fix was checked by reverting what its test asserts.

| | what it was | closed by |
|---|---|---|
| v39-P1-01 | a top-up stamped **every** date with the generation being written, so generation-A dates pointed into B — where their package does not exist | the pointer reads `entry.assigned`; the parameter is **gone**, so the wrong one cannot be passed |
| v39-P1-02 | the era quota and the spacing were computed over the **gaps**, so the runbook's own *re-run it* granted a fresh 5% each time | `_era_plan()` plans over the whole window and reconciles with what it already holds |
| v39-P2-01 | one out-of-range integer aborted the Postgres transaction and **every later request failed until restart**, health check included | rollback on every statement, re-raised; and the column's range checked at the boundary |
| v39-P2-02 | the line score was parsed twice and never compared, and a package with no reveal was accepted | both compared in `agreesWithTheAnswer()`; `reveal` required |
| v39-P3-01 | `CLAUDE.md` §6 still instructed a reader to erase the per-batter footnote cells | the bullet rewritten; the correction above it left intact |

### ⬜ What is not closed: a plausible ceiling on a reported duration

`CLAUDE.md` says *sanity-check client-reported durations before storing, so absurd values don't corrupt
percentiles.* **That check does not exist.** What was added is narrower and is a different thing: the
value must fit the `INTEGER` column, which is a fact about the schema. 2³¹-1 milliseconds is **twenty-five
days**, so a duration far past absurd is still accepted and would still skew a percentile.

⚠️ **Not invented here, because it is a number that shapes the product** (§7). §27 says the puzzle stays
open all day and the clock accumulates only while the page is visible, and yesterday's board is playable
too — so the honest bound is somewhere between *a few hours* and *two days*, and which one is the
operator's call. Until it exists, percentiles are what is at risk, and there are no percentiles yet.

### ⚠️ Two things found while fixing, both about the instruments rather than the code

**Three of the era-plan mutations survived on their own, and the pair did not.** Each half of the fix
defends against the other — fixed offsets leave a second allowance nowhere to land, and a reconciled
allowance leaves a drifting plan nothing to spend. So no single line has a test that goes red for it,
and `_era_plan`'s docstring says so rather than leaving the next reader to discover it. Reverting both
together turns two cases red with the finding's own numbers.

**A mutation harness reported five live mutations as caught, twice, for two different reasons** — once
because it spawned the wrong interpreter and read *playwright is not installed* as a dead run, once
because a nested `uv run` could not launch chromium. Both times the tell was identical: no summary line.
Same shape as the run that reported four survivors while `uv` was locked. **A run that did not happen is
not a run that passed**, and a harness that only looks for failures cannot tell the two apart.

⚠️ **And one restore failed with a transient `OSError` and left the working tree carrying the
mutation.** Caught by `git diff` and not by the harness, which had already moved on. A harness that can
leave a defect behind on its way out is worse than no harness: it retries and then *verifies* now.

---

## ⚠️⚠️ 2026-08-21 — v37, and the count in this file was wrong for the third time — **mine**

**v36 holds 70 findings: 1 P1, 20 P2, 49 P3.** Counted from the review file's own headings, which is
what the two previous claims said they had done and had not.

⚠️⚠️ **I wrote *"the count is stated against the review file's own headings rather than against a
running total, because the previous closing claim was a total asserted from two summaries and it was
wrong"* — and then took 61 from the review's own summary line.** The sentence describing the check is
the whole of what I did instead of the check. Third instance in this file, second one written while
correcting the first.

**What was actually done is better than what I claimed:** the group table was built from the findings
themselves and covers **P3-01 through P3-49 with no gap and nothing invented** — verified by set
difference against the review's headings, not by reading. **The work was complete; the prose count was
not.** The correct closing statement is 49 P3s, and for the P2s: **18 of 20 closed, `P2-18` and
`P2-19` open**, both of which need a production deployment shape that does not exist yet.

⚠️ **The lesson is not "count more carefully".** All three wrong counts were produced by summarising a
summary, and the cure is the one this project already uses everywhere else: **an independent source.**
The review file's headings are that source; a sentence in its introduction is not.

### `v37-P3-02` — **the worst of the four, and it is a guard that could not fire**

`test_line_score_anchors.py` collected every `LineScore(...)` construction and then asserted **outside
the loop**, so only the last was ever judged. `v36-P3-19` widened the finder from *first match* to
*every match* — and **widening it did nothing**, because the consumer still judged one call.

⚠️⚠️ **The comment above it read *"Every call, so a second `LineScore(...)` cannot carry the defect the
first one is clear of."*** A statement of the property, sitting on code that did not have it. Fixed,
and the mutation the reviewer describes — a second, defective construction that is **not** the last —
now fails naming `LineScore construction #1`. The companion inning-array test took `[0]` and had the
same shape.

### `v37-P3-01` — the fourth field `v36-P3-05` named, and the only one left mutable

`Package.metadata` stayed a caller-owned `dict` while `Solution.values`, `Puzzle.given` and
`Derivation.values` were frozen. **It is the one where mutability is worst**: `canonical_bytes` is
`published().as_json()`, so editing metadata after signing **changes the bytes the signature covers**
while the signature stays put — a valid signature over a package that is no longer what was signed.

Frozen as a view over a copy, list values normalised to tuples so `families` cannot be appended to
either, and `as_json()` hands out a detached copy. ⚠️ The round trip is asserted, because `from_json`
builds metadata from parsed JSON where arrays are lists: without normalising both sides **a package
read from disk would stop comparing equal to the one that wrote it**. Mutation: removing the freeze
turns 5 of the 8 new tests red.

### `v37-P3-04` — guidance in the publication path describing a repository that changed

Three claims in `write_reference_puzzles.py`, all of them the opposite of what is true:

- *"the two cases **the tutorial** has to teach"* — the tutorial fetches nothing at all. Fixed
  earlier the same day, and it is what produced v37's first draft finding about a dependency that does
  not exist.
- *"`FAMILY_OF` maps no `Identity` to the batting order… an operator decision, not taken here"* —
  **the decision was taken**, `Family.BATTING_ORDER` exists, and a published board lists it.
- *"the six packages… were drawn under 0.25 and will change the next time this runs"* — **they were
  redrawn under the decided gate**, which is what closed the consequence rather than only the cause.

⚠️ **A settled decision described as open is worse than a stale figure**, because a reader has no
number to check it against; it invites reopening something already decided. And the gate one goes
stale again the next time the batch is redrawn — **the provenance is not in the artefact**, and
recording the gate in package metadata is the durable answer. Recorded as an open decision.

### `v37-P3-03` — **deferred, with the cost stated rather than argued away**

The writer still imports `Loaded` and `load` from `discovery/`. `slot_references` and `to_board` were
promoted because each produces a **published, schema-validated field**; the loader carries the SQL, the
connection, the era windows and the provenance predicate, and §5 puts the pool rule in `discovery/` on
purpose. **Moving it is building the inventory pipeline, not renaming a module.**

**What the deferral costs, stated:** the publication path depends on a module outside `mypy --strict`
and inside the ratcheted lint tree, so a cleanup in `discovery/` can break publishing.
`test_the_writer_passes_its_own_gate.py` calls the writer's own `build()` with no database, so that
breakage is caught by the suite rather than by a failed publish.

⬜ **A third copy of the `Package` factory** now stands in the verify tests — `test_layers`,
`test_plausibility` and the new immutability file. Same shape as `refs()` in `v36-P3-08`; noted at the
new one rather than left to be found.



**Nine of v36's P2s verified resolved by reading the code, no tests run.** One new finding, and two
statements about state that were false when written.

### `v37-P3-01` — **accepted in its cause and rejected in its impact**

The claim: `_traits_survived` requires only **one** board with a suffixed slot reference and one with a
live footnote, which is fragile — *"la condición de tutorial puede colapsar sin un fallo de cobertura
explícito"*.

⚠️ **The impact is the opposite of what happens.** The gate raises `SystemExit` before `_publish`, so a
batch missing either trait **refuses to publish and leaves the previous generation serving**. It cannot
collapse silently; being an explicit failure is the entirety of what `v36-P2-06` added. A floor of one
means the writer *refuses* one discard sooner — an operational cost, not a correctness risk.

⚠️⚠️ **But the reviewer was reading a stale reason, and that is a real defect.** The docstring said
*"the two cases **the tutorial** has to teach"*. **The tutorial reads none of this** — `tutorial-main.js`
fetches no package, no manifest and no network, teaching on a made-up four-batter board, which is
deliberate and recorded there. The justification was true while the tutorial was going to be built on
real data and stopped being true when it was not. **A stale reason in a gate's own docstring is worse
than none**: it produced a confident finding about a dependency that does not exist.

**Who actually needs these boards:** `serve/tests/engine.test.js` searches the shipped packages for one
with a live footnote total in three places, and `board.js`'s substitution indentation keys off a slot
reference longer than one character. **Rendering coverage, not editorial coverage.** The docstring says
so now.

**Measured rather than assumed, since the finding is about redundancy:** the current batch carries
**three** boards with a shared slot and **five** with a live footnote. The comment claiming *exactly one
of the six* was true of the batch drawn under the old gate and went stale the moment it was redrawn — a
count in a comment cannot survive a regeneration, and it is gone.

✅ **Decided 2026-08-21: the floor stays at one.** Raising it to two was proposed by `v37-P3-01` and
rejected, **for the reason the proposal works against**: a higher floor makes the writer *refuse more
often*, and fragility was the concern behind it. It would also be a third quota over six boards that
already carry one-direction-per-game and distinct stall targets — and `CLAUDE.md` records a weighted
sample producing **zero** boards at a rung under exactly that pressure.

### ⚠️ v37's *Pendientes* section is false, and the source of it is inside v36's own file

It reports *"`v36` deja en estado abierto `P3: 44, none started`"*, citing `code_review_v36.md:1550`.
That line is the review's **own snapshot from the day it was written**, in a section headed *"Open, and
not started"* — accurate then, and now describing nothing: **all 44 P3s, all 16 P2s and the P1 are
closed.**

**Not corrected in the review file**, which is the reviewer's artefact and not mine to rewrite; recorded
here, where this project tracks state. ⚠️ **The general shape is one this file has already been caught
by today**: a status line inside a document that is not the status tracker gets read as current long
after it stopped being. The same paragraph shape produced the *"all sixteen P2s closed"* claim corrected
above.

---

## 2026-08-21 — the hand-solve pack: two parts, and layer 3b's question closes itself

### ⚠️ The two axes were being compared as one, and that is what the split fixes

**The ceiling measurement is the best of nine seeds per board** — what a board can be pushed to. **The
pack is what a single ordinary attempt produces.** Reading a 5-to-17 ceiling range as the range the
pack targets compares two different axes, and it is the operator's correction rather than a finding
against the instrument: both numbers were right about their own question.

**On the pack's own axis, 8 is already the 87th percentile and 12 is close to the reachable maximum.**

### Pack A — decided: rungs **5, 8, 11, 12**, four boards each

⚠️ **Only about 20% of boards reach 12**, so that rung is the one that may not fill. **If 12 does not
yield four boards, that is the finding** — reported as such, never quietly substituted with a lower
target. A pack that silently drops a rung is the shape `CLAUDE.md` records from the weighted draw that
produced zero boards at the easiest rung and reported quotas it had not met.

### ⬜ Pack B — only if A comes back soft, and only after a cheap run first

**Rung 17 may not exist at all.** Measuring whether 14 and 17 can be filled costs one short run;
generating twenty boards and discovering it halfway through costs the pack. The order is the point.

### The rest, as established

Stall count **off the page and in the sealed key** · formula strip carrying **all five** relations ·
survey box with the anchored 1–6 scale, the *how many times did you stop* line, and **separate**
columns for **had to guess**, **tedious** and **boring** · randomised order **asserted by `audit()`**,
not printed and believed · one board per game · footnote line given.

**And a final ranking sheet**: every board ordered easiest to hardest once all the sheets are filled.
⚠️ **That is the strongest reading available and it costs one page** — the comparison against the
ranking by stall count is the only thing that tests whether the stall scale corresponds to felt
difficulty, which is the question every difficulty figure in this file ultimately rests on.

### ⚠️ Not built at the end of a long run — a standing rule, not a preference

**The pack is the one measurement whose instrument is a person**, and the only artefact here that
cannot be re-run cheaply after a mistake: a board printed wrong is an afternoon of somebody's
attention spent on the wrong thing, and the key is sealed so the error is invisible until it is too
late. It gets a fresh session.

### ⚠️⚠️ Layer 3b: the question is closed — **operator decision, and a measurement that disagrees**

**Decided: 3b does not become a gate.** The operator's basis: with the gate actually applying and the
fifth family adopted, **every publishable board certifies under the weak solver** — so the question is
not *should we gate on this* but *there is nothing left for it to reject*. **The population that made
the question meaningful no longer exists**, which is a result rather than a scheduling problem. Two
changes closed a gap three separate measurements had been trying to size: **the gate actually
applying, and the fifth family**.

⚠️⚠️ **And one measurement disagrees, recorded here rather than left out.** Run against the six
published packages — drawn at the decided gate, with the batting-order constraint available —
`derivable_in_view` returns **3 certified of 6**:

| board | stalls | 3b |
|---|---|---|
| `0ed0aad8886544ca` | 7 | certified |
| `1dc57470b44caded` | 2 | certified |
| `fc453fed9409d918` | 5 | certified |
| `4f0744440236caef` | 12 | **uncertified** |
| `540c14cba5fb0d37` | 10 | **uncertified** |
| `734c7c793eed359b` | 3 | **uncertified** |

**Not monotonic** — it fails at 3 and at 12 and passes at 5 and 7 — which matches what this file
already recorded about the five-board pack.

⚠️ **The two are about different populations and that is the likely reconciliation**: these six are
**reference data**, chosen by a writer that targets one board per distinct stall count, not a
representative draw from the pool. A claim about *every publishable board* is a claim about the pool.
**It is written down because a decision recorded without the datum that contradicts it is how a
figure becomes unchallengeable**, and because anything derived from *3b rejects nothing* should be
checked against these six first.

---

## 2026-08-22 — instruments that build a configuration the product no longer has

**Prompted by `board-configurations` printing a median of 16 stalls against 6 under a heading reading
*what each configuration buys*.** The sweep asks the same question of every instrument, and the answer
is not one thing: **three kinds, wanting three treatments.**

### 1. Documents a correction — leave exactly as it is

**`zero-footnotes/measure.py`** keeps arms `all`, `non_zero` and `given`, and its own header says the
5-to-15 result *"is a correction, not a new result"*, with the mechanism spelled out. **The wrong arm
is kept and named as wrong**, which is what makes it evidence rather than a trap. Its table already
shows `7, 9, 1` for both `non_zero` and `given` against `14, 17, 14` for `all` — the whole difference,
visible in the output.

### 2. Reproduces a settled decision — needs the arm or the sentence

**`board-configurations/measure.py`** ✅ **fixed 2026-08-22, and re-run to see it.** Third arm
`footnotes>0` added, so the report explains itself. 48 gated directions, 576 measured ceilings:

| configuration | blanks | chain | **stalls** | five or more |
|---|---:|---:|---:|---:|
| `baseline` — the live board | 36 | 23 | **6** | 67% |
| `footnotes>0` | **36** | 22 | **6** | **67%** |
| `footnotes` | 71 | 64 | **16** | 100% |
| `footnotes+lob` | 71 | 63 | **16** | 100% |

⚠️⚠️ **`footnotes>0` is identical to the live board on every column that matters** — same blanks, same
stalls, same share reaching five, same search p90, same resolution, same cycles. Chain differs by one
and bounding steps by one, which is noise. **So the entire 6-to-16 gap is zeros**: the full-footnote
arms erase nearly twice as many cells, and all of the extra is terms that are nought because the thing
did not happen.

**The number a reader takes away is now the right one without reading a warning.** Labels kept as
well — **the label says the question is settled, the arm shows why**, and a label depends on someone
reading it.

⬜ **Four others carry a settled question in their premise, and none of them says so.** Reported rather
than changed, because each is a different call:

| instrument | what it assumes | why it is settled |
|---|---|---|
| `footnote-grouping/measure.py` | one footnote column against four | **its stated motivation is the corrected figure** — *"took the stall ceiling from 5 to 15 and the pool reaching five from 56% to 100%"*. And the question only arises **if the cells are open**; they are given |
| `footnote-groups/measure.py` | can an unassigned footnote be resolved | there is no unassigned footnote when the line is given |
| `footnotes-open-or-given/measure.py` | open against given, paired | ⚠️ **the arms are the right comparison** — this one would produce the settling numbers if run. What is stale is its header: *"the comparison has never been repeated on the canonical list"*. `zero-footnotes` repeated it |
| `scoreboard-blanks/measure.py` | do the four scoreboard duplicates inflate difficulty | decided: they are given, as `SCOREBOARD_DUPLICATES` |

⚠️ **`footnotes-open-or-given` is the interesting one and argues against a blanket rule.** Its
machinery is current and only its status sentence is wrong — a note fixes it. `footnote-grouping`
is the opposite: the machinery is fine and the *question* has gone, so a note leaves an instrument
nobody should run. **Same category, different repair.**

### 3. The only way a question could be reopened — leave, and protect

**`rbi-and-hr/measure.py`** measures what an RBI or a home-run column would buy. §6 records the
eight-column batting order as **decided and deliberately unbuilt**, and CLAUDE.md calls RBI and HR
*candidate* columns whose inclusion *"is a measurement rather than a decision"*. **The configuration it
builds does not exist on purpose**, and this instrument is the only path back to the question. Deleting
it would close a question the design deliberately left open.

⚠️ **The distinguishing test, since these three look alike from outside:** *if the answer came back the
other way tomorrow, would this instrument be the thing that told us?* For `rbi-and-hr`, yes. For
`zero-footnotes`, yes — and it already did. For `footnote-grouping`, no: it assumes the answer that
lost.

---

## 2026-08-22 — the Actions bill, measured before cutting, and a report owed in a month

**Six days, 55 runs, 143 jobs.** ⚠️ Derived from each job's start and finish timestamps, rounded up to
the minute and multiplied by the runner rate — **not** from the billing endpoint, which returns
`total_ms: 0` on every job while `run_duration_ms` is populated. A figure that decides a spend says
where it came from.

| job | runs | billed | share |
|---|---:|---:|---:|
| `CI / forge (ubuntu)` | 44 | 416 | 53% |
| `CI / forge (windows)` | 44 | **302** | **39%** |
| `CI / browser` | 44 | 46 | 6% |
| `Graph Update` | 11 | 14 | 2% |
| | | **778** | |

**130 billed minutes a day, ~3,890 a month, against a 2,000 free allowance.** That accounts for the
bill without looking further — ⚠️ **though it does not prove Actions is all of it**: the per-product
endpoints need the `user` scope this token lacks, so packages, LFS and Codespaces are unmeasured.
`gh auth refresh -h github.com -s user` is what would settle it.

### What changed

**Windows out** — 39% of the bill, and the platform it covered is the laptop, which runs the whole
suite through the hook before every push. ⚠️ **39%, not the two thirds the 2× rate suggests**: that
arithmetic needs similar wall time on both, and it was 3.5 minutes against 9.5, because Linux also runs
the coverage pass.

**`main` and pull requests only**, and **`paths-ignore` for `docs/**` and `**/*.md`**. ⚠️ The trigger
change saves **nothing today** — all 44 runs were pushes to `main`, and there are no branches or PRs —
it is the shape that stops a working branch costing a run per save later.

⚠️ **`paths-ignore` rather than `paths`, and the direction is the point.** A list of what *does* affect
the code forgets the next directory somebody adds, and forgets it silently. This way an unlisted path
runs CI by default: the failure mode is a wasted run rather than an unchecked one.

**Measured per push, not per commit**: 6 of 43 pushes changed only documents (14%). Per commit it looked
like 17%, and that would have been wrong — a push carrying twenty commits, one touching `forge/`, needs
the suite.

⬜ **Owed: minutes per workflow once a month has run.** Without the after, there is no way to know the
bill moved because of this rather than for some other reason — and the next surprise would be as
unexplained as this one.

### ⚠️⚠️ Branch protection: re-checked, and still impossible

`branches/main/protection` and `rulesets` both answer `403 Upgrade to GitHub Pro or make this
repository public`. Free plan, private repository, permanently (§16). **Checked against the API rather
than read off `CLAUDE.md`**, because that paragraph has been wrong before — it is right now.

⚠️ **And `CLAUDE.md` already says so.** The claim that it asserts protection is out of date: the file
carries the correction, including the record that it *used* to claim it. Nothing to fix there.

**Where the gap actually is, now that CI narrowed.** On a working branch the hook is the only check, so
`--no-verify` leaves that code unlooked-at until it reaches `main`. On `main` a `--no-verify` push
**still triggers CI** — so it is seen and not stopped. **Detection without prevention**, which is all a
free private repository allows. The failure mode is a red `main` nobody has looked at yet, not an
unchecked commit nobody can discover.

⬜ **A step-level `if` would not help and is the obvious wrong turn**: the runner starts, checks out and
installs before reaching the condition, so a skipped step bills like a run one. Only a skipped job or
workflow saves.

---

## 2026-08-22 — the restructure: three workflows, and the argument that was wrong

**Done.** `ci.yml` is now `ci-forge.yml`, `ci-browser.yml` and `weekly.yml`. **`docs/ci.md` is the one
place this is explained** — what runs where, what each decision cost, what would reverse it. It exists
because the reasoning was about to be spread across `CLAUDE.md`, `python-conventions.md` and three YAML
headers, which is the shape this project keeps being bitten by.

**Two files rather than two jobs, and that is forced.** `paths-ignore` is a property of a workflow, not
of a job: a single file skips only when *every* changed path is ignorable, so the 32% of pushes touching
only `serve/` were still paying 9.5 minutes for a Python suite that could not have been affected. That
is also the correction to my own estimate — I said the first `paths-ignore` cut would land at 1,365 and
it lands at **2,018**, from exactly this misreading of per-job as per-workflow.

**Coverage left the push runs** and now runs on the hook and weekly. The floor is still `fail_under = 95`
in one place.

### ⚠️⚠️ The argument for keeping CI primary was mine, and it was imported

I argued CI must stay the primary runner because `git push --no-verify` skips the hook and *somebody*
could push unchecked. The operator's answer: **there is one "somebody" and it is me.** A developer who
deliberately bypasses his own hook is not a case a duplicate CI run protects against — he can ignore a
red badge just as easily, since nothing gates on it.

That is `CLAUDE.md`'s *a justification is scoped, and it does not travel*, in its exact shape: a reason
that is true in a team, reused in a one-machine project where the premise it rests on does not exist.
Recorded here rather than only fixed, because nothing about the sentence looked wrong.

### What CI still buys, which is why it did not go entirely

- **A `--frozen` install from nothing.** The laptop's virtualenv is months old and cannot fail the way a
  clean resolve can. This is the one property the hook structurally cannot check.
- Pull requests, when there are any. A run history. And the weekly run, which answers the one question
  the hook cannot ask about itself: *has it been skipped or disabled for a month?*

### ⚠️ The accepted cost, written down so it is not discovered

`forge/uv.lock` and `forge/pyproject.toml` are inside `ci-browser.yml`'s ignored path and that job
installs from them, so **a lockfile change alone will not run the browser suite** until Monday. Reverse
the ignore if a dependency break ever reaches `main` this way.

⬜ **Owed, unchanged: minutes per workflow once a month has run**, before and after. The 658/month figure
is a projection over the old push history, not a measurement.

---

## 2026-08-22 — ⬜ four copies of one button, made knowingly

`.reveal-close` was restyled to match the rest of the app — it was the only full-width white-paper
outline button in the product, on the one screen a player reaches by earning it. It is now the same
dark-ground / outline pair the tutorial's footer uses.

**Which makes it a fourth copy of that look.** `.landing-play`, `.tutorial-back` and `.tutorial-next`
each spell it out in `landing.css`; `.reveal-close` and `.reveal-share` now spell it again in
`board.css`, because `play.html` does not load `landing.css`. Four places saying one thing with nothing
checking they agree is this project's most-recorded defect.

⬜ **The fix is a shared button rule the three pages can reach**, which means either a fourth stylesheet
on every page or component rules in `tokens.css` — and that file is currently variables only, which is a
property worth keeping. Not decided; not urgent; recorded before continuing rather than after a review
finds it.

⚠️ **The 1:2 split the tutorial uses does not survive here**, and it was tried: at 375px it leaves the
way back 121px and `Back to the board` breaks onto two lines beside a single-line neighbour. Equal
halves. **Found in a picture** — every computed style said 50px and agreed with itself.

---

## 2026-08-22 — ❌ the first real inventory is 34% pre-1950 against a 5% ceiling

**§6 is explicit and still decided:** *pre-1950 boards must not exceed 5% of what the player sees* —
about eighteen a year, so Ruth is **an event rather than the scenery**. The 150-board batch built today
is **51 pre-1950, 34%, against a ceiling of 8.**

⚠️⚠️ **It is the sampler, not luck.** `load()` draws *n per decade* across twelve decades, so a
decade-flat draw **cannot** satisfy a decade-weighted quota except by accident: 1910s–1940s is a third
of the draw and the quota allows a twentieth of the calendar.

⚠️ **Nothing in the pipeline could catch it.** A 1913 board is perfectly valid, and so is a calendar
made entirely of them — the gate, the four layers and the calendar's own refusals all pass. **Found by
printing the decade distribution and reading it**, which is the only thing that has ever found this
class in this project.

⚠️ **And the run reported `assigned 150 of 150`.** A3.5 asks for quotas asserted after construction
rather than printed and believed; there is no assertion, so the summary was true about the count and
silent about the composition.

⬜ **The fix has two halves, and only the first is obvious.** The builder needs an era weight in the
draw *and* an assertion after selection. ⚠️ **Weighting the draw alone is not enough** — it would make
the violation rarer rather than impossible, which is the shape `CLAUDE.md` records from the pack that
reported quotas it had not met.

⚠️ **A related question this raises rather than settles:** §10's re-measurement notes that pre-1950 is
29% of the *pool* naturally, and that the quota *"remains available as a preference about what the
player meets; it is no longer a fix for a broken distribution."* It is still a decided quota, so it
binds — but whether five months of beta 0 should carry eight pre-war boards or a different number is a
product question, and the number is the operator's.

---

## 2026-08-22 — ✔ the first yield measurement, and ⚠️⚠️ a gate that refused nothing in 235 attempts

**Run:** `build_inventory.py --measure --per-decade 1` and `--per-decade 3`, gate `0.30`, caps ≤13
batters and ≤6 pitchers, stall targets counted down from 12. Two samples so the first was not believed
on its own.

| | 12 directions | 36 directions | together |
|---|---:|---:|---:|
| produced | 12 of 12 | 36 of 36 | **48 of 48 — 100%** |
| attempts | 55 | 180 | 235 |
| refused by the erasure | 43 | 144 | 187 |
| **refused by the gate** | **0** | **0** | **0** |
| seconds per published board | 13.6 | 9.0 | — |
| **150 boards** | ~34 min | **~22 min** | — |

**What 100% means and does not.** Of the directions that pass §5's gate and the roster caps, every one
produced a publishable board at *some* target between 12 and 1. It is **not** 100% of the pool — the gate
keeps about 11% before any of this runs — and it says nothing about whether the boards are good. It says
**the pipeline loses no boards**.

⚠️ **The consequence is a design decision, not a statistic: the batch does not need to over-sample.** 150
dates costs about 150 directions, not fifteen hundred, so the retry-and-top-up machinery that would have
been written against a guessed yield is not needed.

**Loading has a large fixed cost.** ~19-20 seconds whatever the size: 1.67s per direction at twelve,
0.53s at thirty-six. At 150 it is noise. ⚠️ **I said the bottleneck was loading rather than building
before the run finished; it is building, by seven to one.** Stated as a finding when it was a guess about
a process that had not yet printed anything.

**What actually sizes the batch is duplicate games, not yield.** `load()` can return both directions of
one game and the calendar refuses the second (§7): **3 of 36 drawn twice (92% usable), 7 of 72 (90%)**.
So **draw about 1.15× the number of dates.**

### ⚠️⚠️ And the gate refused nothing

**235 production attempts, zero refusals from `certify_for_publication`.** Every one of the 187 failures
was the erasure not reaching a target.

**The four validation layers rejected nothing.** That is a plausible result — §5's zero-density gate is
what does the filtering, and it keeps about 11% of the pool before any of this runs, so what survives it
may genuinely be publishable. **And a check that never fires is indistinguishable from one that is
broken**, which is this project's own rule and the reason this is written down rather than enjoyed.

⚠️ **What is already known and does not settle it.** `test_the_writer_passes_its_own_gate.py` proves the
gate has teeth on a real package: it takes a board the writer built and refuses it when the producer's
metadata is put back. So the gate *can* refuse. What is unknown is whether it refuses anything in the
population the batch producer will actually feed it.

⬜ **What would settle it**, in order of cost:

1. ✔ **A larger sample — done, and it did not change.** 235 attempts rather than 55. At that size the
   result stops being small-sample noise and starts being a statement about the pipeline.
2. **Per-check counts rather than a total.** `certify_for_publication` runs a registry of checks;
   knowing *which* never fires is more useful than knowing none did. `produce()` already returns the
   refusal strings, so this is a tally rather than new machinery.
3. ⚠️ **If it still refuses nothing at volume, that is a finding about the gate and not a clean bill of
   health.** The honest reading would be that the erasure and the gate overlap almost entirely on gated
   boards — which is worth knowing before anybody trusts the gate to catch a generator defect.

**Not a blocker for A2**, and it must not become one silently either: the batch can be built while this
is open, but the answer changes how much §22's four layers are worth in this pipeline.

---

## 2026-08-22 — ⬜ the 375px cap is three copies and no test

**Measured while writing `beta-0.md`:** at 1400×900 the board holds at 375px, centred, cell 44.8px, table
359px — identical to 375×812. It does not stretch, which is the requirement beta 0 needs.

⚠️⚠️ **The number is spelled three times and asserted nowhere.** `serve/ui/phone/board.css:74`,
`board.css:599` and `landing.css:18` each carry `max-width: 375px`; the browser suite's only width
assertion is for the `(max-width: 359px)` media query. **This is the width §6's entire six-column argument
rests on**, and it is three places with nothing checking they agree.

⚠️ **It is also a presentation constant living outside `tokens.css`**, which `CLAUDE.md` names as the one
place they go.

⬜ **The fix is a token and a test.** Not beta 0 work — but **beta 1 is desktop**, which is the milestone
that edits exactly this property, and discovering three disagreeing files then is the expensive order.

---

## 2026-08-22 — ⬜ the share button is drawn and does nothing

The reveal now carries a *Share* button beside *Back to the board*, `disabled`, with the three-node web
share mark. Operator's instruction: put it in the UX now even though it has no use yet.

**Disabled rather than merely unwired**, because a button that looks pressable and does nothing makes
the player doubt whether their result was recorded — which is the one thing the reveal exists to tell
them.

⬜ **What it needs to become real:** the share grid, which §7 says must never leak the solution or a
player's name, and §26 which says comparison is the paid feature. Neither is built. `docs/serve-flow.md`
is where the grid's content gets decided.

---

## ⚠️⚠️ READ FIRST — which pool every discovery figure describes

**2026-08-21.** Two separate defects touched the pool every instrument samples. Neither made a *number*
wrong; both make a *comparison* wrong if you do not know about them.

### 1. Twelve instruments measured at a gate of `0.25` against a decided `0.30`

They spelled the gate by hand and disagreed with `boxscore_domain`. **A stricter gate is not a smaller
sample of the same thing** — it removes precisely the boards that compress least, so those figures
describe a **livelier population than production draws from**. They read `ZERO_DENSITY_GATE` now, each
says at its own `GATE` which gate produced its figures, and the twelve are listed further down.

### 2. `load(gated=...)` did nothing, and its docstring said the opposite of the truth — `v36-P2-20`

⚠️⚠️ **This one is a hazard to reasoning rather than to data, and it has already misled once.**
`gate_clause` was built unconditionally and `eligibility()` interpolated it unconditionally, so **every
sample `load()` ever returned was gated.** Meanwhile the signature said `gated: bool = False` and the
docstring said *off by default*.

**Read the signature and you conclude the opposite of the truth**: that the eight call sites omitting
the flag measured the unfiltered pool, and therefore that every absolute figure in the tree is wrong.
They did not, and it is not. **No figure needs re-running on this account.** The flag is read now, and
the eight name it explicitly so nothing they measured moves.

⚠️ **What it does mean is that eight instruments got a population they never asked for.** Whether each
*should* have been ungated is a live question, not a defect with a known fix — see below. The sharpest
case is `zero-density-gate/`: the instrument that **chose the 30% threshold** was handed a sample the
threshold had already filtered.

### What is **not** affected

**The six published packages are correct.** `write_reference_puzzles.py` passes `gated=True` and now
the decided gate, and the boards were regenerated on 2026-08-21 — the divergence was in `discovery/`
only, and the reference writer's own `0.25` literal is fixed and the batch redrawn.

### The rule this leaves behind

**Any figure compared against a recorded one inherits whichever of these two applied to it.** Before
comparing a new run against a number in this file, check which gate the instrument used and which
population it drew — the annotation is at each instrument's own `GATE`, which is where it travels with
the code rather than only with this page.

---

## 2026-08-23 — ✔ v40: three findings, three closed

`docs/reviews/code_review_v40.md` carries them. ⚠️ **All three are in the tree that is three days old**,
which is where a full static pass would be expected to land and is the reason the review was asked for.

| | what | closed by |
|---|---|---|
| **v40-P1-01** | `inspect()` never read `today.json`'s `puzzle_id`, so **zero packages was healthy** as long as a current-dated pointer survived — the one state F3 exists for | `_pointer()` returns date **and** id, both pointers are followed to their package, and five cases cover it including the empty public path |
| **v40-P2-01** | the rotation wrote public files in place, so a failed write **destroyed the pointer it was replacing** | `_place()` writes a `.pending` sibling and `replace()`s it; four fault-injected cases assert the old bytes survive |
| **v40-P3-01** | `weekly.yml` omitted `publish/`, and the completeness guard compares **tool names**, which `keep` already supplies | the weekly run installs and checks `publish`; the tree guard now asks the **scheduled** workflow as well as the hook and the push workflows |

⚠️⚠️ **P3-01 is the failure shape this project keeps meeting**, and it is worth naming as a shape rather
than as a missing workflow step: **a guard that asserts *which tools run* cannot answer *which trees they
run over*,** and it reports success either way. It is the same defect as a check that never fires — and
it is the *second* time this exact guard had it, after `keep` arrived in August and was checked by
neither side while the tool sets agreed.

⚠️ **Both repairs were verified by breaking them.** The tree guard was re-run with `publish` renamed out
of `weekly.yml` and went red naming the tree and the side; the rotation cases inject an `OSError` inside
the write rather than reasoning about truncation.

⚠️ **And the P2 fix contained a fresh instance of the same class, caught by its own test.** The sweep for
leftover pending files was first folded into the loop that globs `*.json` — which cannot match a name
ending in `.pending`, so the branch could never run. **A check that cannot fire, inside the fix for a
check that did not exist.** It is a separate sweep now, and the test that found it is the one asserting
a leftover is actually removed.

---

## 2026-08-23 — ⬜⬜ Pack A cannot be built, and the reason is a result about the inventory

**The pack refused itself: nine boards against a `WANTED` of sixteen.** The audit did exactly what it
exists for — `CLAUDE.md`: *anything acting as a launch gate is asserted, not printed* — and the refusal
is the finding rather than an obstacle to it.

### The arithmetic, which settles it without judgement

`derivable_in_view` is layer 3b, the weak solver: one relation in view at a time, never carrying a
narrowed range from one to the next. Measured over the **shipping** inventory, at stall rungs:

| rung | boards | certified | uncertified |
|---|---|---|---|
| 5 | 5 | **0** | 5 |
| 8 | 16 | 4 | 12 |
| 11 | 24 | 1 | 23 |
| 12 | 30 | **0** | 30 |
| | **75** | **4** | **71** |

`UNCERTIFIED_SHARE = 1/3` caps the pack at five uncertified boards, the audit tolerates ±2, and the
pool holds **four** certified boards in total. **The ceiling is eleven and `WANTED` is sixteen** — so no
seed, no ordering and no re-run reaches it. The nine the run produced is that ceiling minus the per-rung
half-quota cap.

### The number the constraint was sized against came from a retired axis

`choose()` said *layer 3b certifies 100% of the easiest boards and 91% of the hardest*. **That figure is
chain 11 and chain 13**, and the generator stopped targeting chain in August. This file already records
the fifty-board pack aborting on the *opposite* symptom — *0 uncertified where it wanted about 17* — on
the same axis, which is the same constant meeting the same stale population from the other side.

⚠️⚠️ **A justification is scoped and it does not travel.** The cap exists to stop *uncertified* and
*hard* becoming one variable. In this population certification barely varies at all — 100%, 75%, 96%,
100% uncertified across the four rungs — so **there is no correlation left to confound**, and the cap
now does the damage it was written to prevent: a pack two-thirds certified samples a 5% corner of what
ships.

### ⬜ The share is the operator's, and nothing was lowered

§7: a number that shapes the experiment is not invented in a source file. `TARGETS`, `QUOTAS` and
`WANTED` were not touched either. The pack producer now **reports the pool before it refuses**, which is
what made this diagnosable at all.

### ⚠️⚠️ And the larger half is not about the pack

`derivable_in_view`'s own docstring states the question it was built to answer: *whether it should
become a gate is a question about how many currently-passing boards survive it — if nearly all do, the
concern was theoretical; if many fail, the gap between the two solvers is real.*

**Many fail. 71 of 75.** That is the measurement, and it has been sitting in the inventory unread.

⚠️ **Do not read it as "95% of shipping boards are unsolvable by a person."** The weak solver is a
*lower* bound on a person and a deliberately harsh one — it never carries a narrowed range between
relations. What the number says is that **the bracket between the two solvers is wide**, where the
chain-axis measurement suggested it was narrow. Checked before believing it: the weak solver deduces 31
of 36 blanks, 36 of 40, 43 of 47 and stalls a handful short — it is working, not returning an empty
result that reads as a real zero.

**B3, the hand-solve gate, is the only instrument that can settle this**, and this raises how much rests
on it.

### The two defects found on the way, both fixed

- ⚠️⚠️ **`choose()` called `audit()` and defeated the fix that moved it.** `main()` calls `report()` and
  then `audit()`, with a comment saying that a refusal which does not name its population is half a
  check. The raise sat one level down, so the terminal printed a bare refusal exactly as before. **The
  repair was made in the caller while the thing being repaired sat in the callee.** It cost a diagnosis
  by hand.
- ⚠️ **The stale 91% is corrected in both comments that carried it**, with the axis named, rather than
  deleted — the fifty-board history is what makes the inversion legible.
---

## 2026-08-23 — ⬜ The replacement draw is not randomised, and four of five came from one club

**Noticed while checking the calendar diff, recorded before continuing.** The five replaced dates are
spread across five months and the era quota holds; what is concentrated is the *source*:

| date | withdrawn | replacement |
|---|---|---|
| 2026-09-01 | `WS1191310032` (1913) | `WS1191306130` |
| 2026-11-01 | `BAL197409111` (1974) | `BOS195408111` |
| 2026-11-04 | `SLN192310072` (1923) | `WS1191306140` |
| 2026-11-26 | `SLN192310071` (1923) | `WS1191306201` |
| 2027-01-08 | `WS1193305312` (1933) | `WS1191306070` |

**All four pre-1950 replacements are Washington, June 1913.** Each is a different game and *one game,
one puzzle* holds; the era was inherited on purpose, which is why they are all pre-1950. What was not
intended is that they are all from one club in one month.

**The cause is in `replace_dates` and it is structural, not luck.** It draws per date and takes the
**first** board that produces. `load()` returns the same ordering for the same window, so every
replacement walks the same head of the same list and differs only by which games are already spent.
**N replacements therefore come from one corner of the pool**, and the more dates are replaced at once
the more concentrated it gets.

⚠️ **Not fixed here, deliberately.** The five boards are produced, verified and signed; re-running the
draw to improve a variety property would discard a validated state for something nothing has decided.
The fix is a seeded shuffle of the sample before the loop, the way `build_pack.choose()` does it.

⬜ **And whether it matters is a product question, not a bug.** §31 asks for variety in *techniques*;
nothing anywhere says a calendar may not repeat a club. A player reaching four reveals from Washington
1913 across five months is the thing to have an opinion about, and it is the operator's.
---

## 2026-08-23 — ✔ Pack A built: sixteen boards, and the cap that actually held it was not the one blamed

**The operator removed the certification quota.** `choose()` fills each rung to quota without
consulting `certified`; `report()` prints the count so the mix is *observed* rather than assumed.

| | |
|---|---|
| boards | **16**, four at each of rungs 5, 8, 11, 12 |
| certified by 3b | **0 of 16** (pool: 5 of 75) |
| pre-1950 | 0, against an allowance of 2 |
| substitution / live footnote | 12 / 10 — both traces the tutorial needs |

### ⚠️⚠️ A false explanation the outcome appeared to validate

The pack came out at nine of sixteen and the first account of it — mine, and repeated to the operator
— was *five uncertified allowed plus four certified available equals nine*. **The pool holds five
certified, not four.** The arithmetic was wrong and it produced the right number, which is why nobody
looked further.

**There were two caps.** `UNCERTIFIED_SHARE` was the overall one; a per-rung `ceiling_here = wanted // 2`
sat inside `choose()` and allowed two uncertified boards per rung whatever the share said. Raising the
share alone stalls at **eleven** — measured at 0.50, 0.67, 0.75, 0.90 and 1.00, all eleven, the same
rungs every time. From 0.50 upward the per-rung ceiling is what binds.

⚠️ **This is a third relative of the shapes already in `CLAUDE.md`** — an instrument measuring its own
output, and a metric pointed at the wrong thing. This one is neither: **the reasoning was wrong and its
prediction matched.** No amount of re-reading the result distinguishes it, because the result agrees.
Only enumerating the mechanisms separately — both caps, and the actual certified count — separated them.
**A number that comes out right is not evidence that the reason is right.**

### Why the quota had to go rather than move

It protected against *uncertified* and *hard* becoming one variable. Against this population it
**creates** that confound: 5 certified in the pool, **4 of them at rung 8**, so at 1/3 the pack came out
rung 8 = 3 certified, rung 11 = 1, rung 12 = 0 — rung 8 is the certified rung. Unfiltered, every rung is
uncertified, certification stops varying, and there is nothing left to confound. It is also the mix that
ships, which is what B3 has to sample.

Two audit assertions went with it — the ~1/3 share and the refusal of a wholly-uncertified rung — and
three tests now assert the opposite, including that a **wholly certified** pack still passes. A check
that only accepted today's mix would be asserting the pool's composition under the name of a property of
the pack.

### ⚠️ `check_pdf.py` had been refusing every pack on a stale column name

It required a `stalls` column in the key; `write_key` renamed it `stall_target` when the generator left
the chain axis. So it exited with *the key has no 'stalls' column* — **true about a column that no longer
exists**, from a checker whose own docstring is about failing closed.

**Failing closed on a stale expectation is still not running the check.** The leak scan never executed,
and a pack could have gone to print unexamined because the instrument was complaining about a name. Fixed
to `stall_target`; it now reads 16 streams, 16 board pages, and confirms every page carries the three
required items and names no difficulty.

⚠️ The two places that must agree are `write_key`'s header and that tuple, and **nothing asserts they
do**. Recorded, not solved.

### Verified by looking at it

Board 01 and its solution were rendered and read by eye, not asserted about. The board is legible: slot
column with `2a`/`2b`/`8a`/`8b`, twelve-inning line score, footnote line, formula strip, survey box, and
no stall count, teams, date or game id anywhere. The solution's arithmetic checks: PA 61 = Outs 36 +
Runs 10 + LOB 15, and H/BB/SO/R cross 18/10/10/10 against the pitching half.

⬜ **One observation for the operator:** on paper the footnote line is small grey text under the line
score. §6 requires live footnotes to be *visually prominent*, and that rule is about the phone board
rather than this sheet — but the pack is where a person first meets a live footnote, and nine rows in ten
have every term at zero.

### Where the artefacts are

`discovery/hand-solve/` — `boards.pdf`, `solutions.pdf`, `key.csv`, `recording-sheet.csv`,
`provenance.json`.

⚠️⚠️ **`key.csv` is the only one not in Git**, by `.gitignore` line 42, alongside `ceiling-key.csv`. It
holds the stall target per board and it is the whole point of the experiment that it stays shut until the
sheets are done. **It exists only on the laptop**, which §33 names a single point of failure — losing it
loses the pack's calibration, though not the boards.

The `fifty-` artefacts were not touched: `fifty-boards.pdf`, `fifty-solutions.pdf`, `fifty-key.csv`,
`fifty-recording-sheet.csv` and `fifty-pack-run.log` still carry their August 18 and 20 timestamps.
---

## 2026-08-23 — ✔ The browser suite's headless hang: **a pipe nobody was reading**

**The runner started the development server with `stdout=subprocess.PIPE` and read it only in the
teardown.** The server writes one line per request. A pipe nobody drains fills its operating-system
buffer — 64 KB on Windows, roughly a thousand of those lines — and then the **server** blocks inside
`write()` on its next request and stops answering. The browser waits forever for a response that the
server can no longer send.

**The suite was making about a thousand requests.** That is the whole of *one test away from silence*:
the wall was a byte count, and every test added moved the run closer to it.

### Why it disguised itself so well

- **The position moved**, so it looked like a defect in whichever test was running at the thousandth
  request. Three suspects were investigated and cleared in turn.
- **It did not reproduce in an ordinary browser**, because that server was writing to a terminal.
- **Every isolated probe passed** — 80 `no-store` fetches, 20 `loadPuzzle` calls, every page and pointer
  — because a hundred requests never fill a buffer. *The instrument that reproduces a threshold has to
  cross it.*
- **Raising the timeout did nothing**, correctly: a deadlock is not slowness. 120s → 300s → 900s.
- `communicate()` in the teardown is the one place that reads the pipe, and by then the run it would
  have explained has already failed.

⚠️⚠️ **The near-miss is worth more than the fix.** The structural answer proposed — split the suite
across two pages, since the runner drives one — **would have worked, and would have been wrong.** Two
pages make two servers' worth of requests against the same unread pipe: the ceiling moves and the next
thousand requests find it again, with the same disguise. **A remedy that makes a symptom rarer is the
hardest kind of wrong answer to detect, because it is confirmed by exactly the evidence that would
confirm a correct one.**

### What found it

**Bisecting by difference, not by suspicion.** A probe was written that ran the *same* suite headless
and finished. Then the runner's features were added to the probe one at a time — the console handler,
the `pageerror` handler that calls `page.evaluate` — and it kept finishing. What was left was how the
two started the server: `DEVNULL` in the probe, `PIPE` in the runner.

### The fix, and it is a fix rather than an accommodation

A daemon thread drains the pipe into a bounded `deque`; the teardown prints from the deque. ⚠️
**Discarding the output is not the fix and was the previous defect** (v36-P3-11): both streams went to
`DEVNULL`, so a stolen port or a crash inside `dev_server.py` presented as a bare
`ERR_CONNECTION_REFUSED` with the one explanation thrown away. **Keeping it *and* reading it is what
neither version did.**

**Proved rather than assumed.** The retired test is back and the real runner reports **281 passed**. A
temporary suite making **4000 extra requests** — several times the old buffer — was then added and the
run reported **282 passed**. The ceiling is gone, not higher.

### What it cost, and the instruments that stayed

**An afternoon**, most of it on the wrong test. The runner said *the browser suite never finished* with
an empty console, which reads exactly like a module that failed to load. Three instruments were built
while chasing it and all three are keepers:

- **`serve/tests/harness.js` publishes `globalThis.__running`** before each test. A suite's lines are
  appended to the page only when the whole suite finishes, so *the last thing rendered* named a suite
  several tests too early.
- **`tools/run_browser_tests.py` prints it and the last rendered lines** on timeout — each behind its
  own `page.evaluate` timeout, because the first version was not, and on a wedged page the *reporter*
  hung. **An instrument that can hang on the failure it exists to describe removes the timeout's own
  signal.**
- **The timeout is 900s.** It was 120s and fired on a run that was merely slow, which is its own false
  report. It is sized for a slow CI runner with room and is not what fixed anything.

### ⚠️ The one thing this does not close

`tools/dev_server.py` still logs a line per request, and nothing bounds how much a *different* consumer
of that process might buffer. The runner is the only one today. If a second ever starts it, the same
rule applies and is not enforced anywhere: **a subprocess pipe is drained or it is not created.**
---

## 2026-08-23 — ✔ E1: `/today` and `/p/<id>`, and what it retired

`/p/<id>` is canonical (C6) and `/today` is a static page that reads the signed pointer and replaces
itself with it. `?p=` is gone; `?test=` stays, because it selects a development *mode* rather than a
puzzle.

### The decision that shaped everything else: no executable on the play path

**`/today` is how every player reaches the board**, and §23 forbids a backend dependency there. A
process answering that address is a process whose failure removes the only door into the game. `publish`
is allowed to be an executable precisely because it is **not** on that path: it runs once a day, writes
files and exits, and if it dies the previous day's files still serve.

⚠️ **The cost is real and is named where the page is: this is not a 302.** A redirect *status* needs
either a request-time reader — the dependency above — or a daily nginx reload, which is a moving part in
F. What is given up is a cacheable, crawler-friendly redirect on a page nobody links to twice.

### The failure modes, which are the part that matters

| | what happens |
|---|---|
| `today.json` absent | `NoPuzzle`, and the page says **`day.none`** — *there is no puzzle at this address today* |
| `today.json` malformed | the same, through `readPointer`, which is `readManifest` with its subject changed (v36-P3-23 travels with it) |
| `/p/<id>` unknown | refused. **v36-P3-45, closed** |
| pointer names a package that is not public | refused, not substituted |
| pointer is **stale** | **served, deliberately** |

⚠️⚠️ **Staleness stays undetected client-side and the reason is written beside the code.** Noticing that
`today.json` is a day old requires knowing what today is — the exact thing E1.3 forbids as a basis for
choosing a puzzle. A player whose laptop is a day fast would be shown an error about a file that is
perfectly current. `publish.health.inspect()` already compares the pointer's date to the serving date:
**one observer with the right clock, not every visitor with their own.**

⚠️ **`day.none` is a different sentence from `package.unreadable` on purpose.** *Nothing there* and
*there and refused* are different facts, and telling somebody their board is corrupt sends them to
reload rather than to come back tomorrow — the soft-404 wearing a sentence.

### E1.2 did not owe a third `ROLLOVER_OFFSET_HOURS`, and the sentence replaced the debt

`serve` **consumes** the calendar date. A third constant would have no consumer and its assertion would
pass forever while testing nothing. **Two trees compute the date, one reads it.** The reading side is
asserted differently: no player-page source may reach for `ROLLOVER` or `getTimezoneOffset`, and
`calendarDate` may never be fed the player's own date. ⚠️ It does **not** ban `localDate` — `shell.js`
uses it for `playedOn`, a different quantity on a different clock, and the first version of that test
banned the function and went red on correct code.

### What it retired

- `readManifest` and its two tests. **No code under `serve/` opens a manifest now.** It presupposed the
  browser reading one, which is the thing being retired; the deployment-side check that reads a manifest
  belongs to F and will be written against the operator's needs rather than the browser's.
- `?p=`, from `daily.js`, `withSearch` and every caller.
- The four E1 markings — `docs/calendar.md` (the owner), `docs/runbook-inventory.md` §5,
  `write_manifest`'s docstring, `docs/beta-0-plan.md` §761 — **and a fifth that was never on the list**:
  `docs/serve-flow.md` §6 still carried *what time midnight is is still open*, settled the day before.
  ⚠️ **The four were tracked because somebody wrote them down as owed. The fifth went stale by itself,
  and no list of things to un-mark can hold that.**

### ⚠️⚠️ The served tree held six packages and the model allows two

`serve/data/puzzles/` is written by `publish.rotate` now, so what the browser loads on the laptop is
byte-for-byte what it loads on the VPS. The six reference packages moved to a private inventory under
`forge/reference-inventory/`, gitignored the way `forge/inventory/` is, and **three of the six were
withdrawn cards** — partial accounts the register excludes — so the local board came from a game the
rules forbid. The set was regenerated from the clean pool.

⚠️ **The browser suite's package sample dropped from six to two**, and that is not a coverage regression
to work around: a suite asserting properties over six *public* packages was asserting them over an
inventory that may not exist.

### Two defects the regeneration exposed, both real

- ⚠️⚠️ **A test bounded a staff's outs by the wrong side of the line score.** The board draws one club's
  batters and **the other club's pitchers**, so the innings that bound their outs are the ones the
  *offence* batted. The test used `defense_by_inning`, **copied from the certifier's sentence** — where
  it is correct, because `check_independent_correspondence` bounds a *different grid*, the reveal's
  unshared half. One rule, two grids, and the sentence travelled without its subject. It passed for
  months because both halves are nine innings in an ordinary game; the first board where they differ — a
  home club leading after the top of the ninth and never batting — made it fire, **on correct data**.
- ⚠️ **A conformance vector produced its condition only by luck.** *A repeated slot reference* set
  `slot_references[1]` to `"1"`, which repeats only if the board holds `"1"` at index 0. A regenerated
  board opening `1a`, `1b` made it stop testing anything. It writes **both** entries now.

### ⚠️ `check_pdf.py` and the runner, in passing

Both were refusing or timing out on healthy input. See the Pack A entry and the browser-suite entry.
---

## 2026-08-24 — ⚠️⚠️ `/p/<id>` shipped as a blank page, and the route test passed on it

**E1's canonical URL did not work.** `play.html` names its assets relatively — `main.js`, `board.css` —
and a page served at `/p/409f...` resolves those against `/p/`. The dev server's prefix rewrite matched
`startswith("/p/")`, so `/p/main.js` was answered with **`play.html` itself**: the browser asked for a
module and was handed HTML, refused it on MIME, and rendered **an empty `#app` with no stylesheet.**

**Two independent halves, both wrong:**

| | |
|---|---|
| the pages named their assets relatively | so nothing could resolve from a second address |
| the rewrite matched a bare prefix | so every one of those wrong addresses answered **200** with the wrong body |

Either alone is visible. Together they produce a 200 for everything and a working-looking route.

### ⚠️⚠️ The test passed throughout, and it is the shape this project records most

`test_the_page_is_the_same_one_the_direct_address_serves` compared the bytes at `/p/<id>` against
`play.html` and they matched — **exactly, always, by construction of the rewrite.** The assertion was
true and the page was dead.

**It asked *does this address serve the board page* and never *does the board page work here*.** That is
the working-instrument-aimed-one-question-short shape `CLAUDE.md` already carries from the reveal's
width checks: correct question, real DOM, true answer, and the property under judgement was not the one
being measured.

⚠️ **And `daily.js` had already met it.** Its data path was made absolute at E1 *for this exact reason* —
the board page is served at two addresses, so a relative path depends on which one. **The HTML was not
carried with it.** The fix was applied to one of the two things that name files, and the other was not
looked at.

### ⚠️⚠️ The sweep the instance demanded, and it found a second immediately

**One instance found by accident means the class was never swept.** Two questions were asked of the
whole tree.

**Anything else naming a file relatively?** — **yes, and it was worse.** `ROUTES` in `daily.js` held
`play.html`, `index.html`, `tutorial.html`. Linked from the landing page at `/`, those resolve to
`/play.html` and `/tutorial.html`: **both buttons dead, on the address every visit lands at**, which is
the entire way into the game. And `/tutorial` had **no production URL at all** while
`docs/serve-flow.md` §1b says the tutorial is reachable from the landing page at any time.

⚠️ **Safe, and checked rather than assumed:** `import "./board.js"` and CSS `url(...)` resolve against
the **importing module's** or the **stylesheet's** URL, not the document's, so they are unaffected by
which address served the page. Every one of them is under `/ui/phone/`.

**Any other test comparing bytes instead of asking whether the artefact functions?** — the ROUTES one,
and it was worse than a byte comparison: it fetched `../ui/phone/${file}`, **supplying the directory
whose absence was the defect.** It could not have failed. It asserts the shape now — every value
absolute, none ending `.html` — and `forge/tests/test_nginx_serves_what_is_declared.py` requests them
from a server that has the routes, which is the only place the question is real.

**Verified by breaking it**: with the filenames put back, the nginx test reports *the client links to
play.html and nginx answers 400*.

### What closed it

- **Every page names its assets absolutely.** `/ui/phone/...`, not `main.js`.
- **The rewrite is anchored**, `^/p/[0-9a-f]+/?$` — the same pattern `idInPath` uses, in both
  implementations. A prefix that swallows everything under it is a soft-404 by another name: every
  wrong address answering 200 with something that is not what was asked for.
- **The test asks for what the page names.** It reads the modules and stylesheets out of the served HTML
  and requires each to answer 200 with something that is not markup. Verified by putting the relative
  paths back: it goes red naming `fonts.css`.

⚠️ **Verified in a browser as well**, because the failure was a blank screen and no status code showed
it: through nginx, `/today` → `/p/<id>` renders 169 cells with the stylesheet applied. The Browser pane
was not displayed in that session, so this is DOM evidence rather than a picture — stated rather than
glossed.

---

## 2026-08-24 — ⬜ The board's tab shows the player's date, not the puzzle's

`main.js` sets the title with `shortDate(localIso(new Date()))` — **the visitor's own clock**, in
user-facing text, on a board whose pointer may name a different day. On the development tree the pointer
is 2026-09-02 and the tab reads *August 24*.

⚠️ **It is the same class as `calendarDate`** — a date wearing the wrong clock — and it is deliberate in
one respect: the title is applied **before** the puzzle loads, so a page whose puzzle fails still has a
name (v36-P2-17). The honest fix is a generic title first and the calendar date once loaded, which
touches the boot ordering.

**Noticed while verifying E3's routes and written down rather than fixed**, because it is not E3. In
production the two agree for most players most of the time and disagree across the rollover — which is
the window `yesterday.json` exists for, so it is exactly when somebody is looking.
---

## 2026-08-24 — ✔ The nginx test was flaky in CI on its first run, and the probe asked the wrong question

**`ConnectionResetError: [Errno 104] Connection reset by peer`**, on the first request, on a server that
was seconds from being fine. The local hook had just passed.

**The readiness loop waited for `socket.create_connection` to succeed.** That succeeds the moment
**Docker's** port forwarder binds — before nginx inside the container is accepting anything. The
forwarder accepts the TCP connection and then resets it.

⚠⚠ **It asked *is the port open* when the question is *does nginx answer*.** That is the near-neighbour
shape, in code written the same day as two other instances of it, by somebody who had just written the
rule down twice. **Knowing the rule does not apply it** — the same sentence this file already carries
about the fourth regex instance.

⚠️ **And it is exactly what CI buys.** A warm image on the laptop starts in a blink; a cold runner does
not. `docs/ci.md`: what CI still buys is the thing the laptop cannot test.

**Fixed by making the probe a real HTTP request**, retried on `OSError` and `HTTPException`, with the
budget raised to 60s for a cold pull. ⚠️ The failure message says *never answered an HTTP request*
rather than *never started*, because those are different facts.
---

## Where everything stands

**40 reviews**, the last of them v40. ⚠⚠ **The finding total is deliberately not stated any more.**

This paragraph read *"twenty-nine reviews, 135 findings"* for ten reviews after it stopped being true, and
the section below already records that **the count in this file has been wrong three times — mine.** A
number nothing checks, restated by hand, in a document about checking things.

**So the two halves are separated.** The review count is asserted and checked: `test_the_review_count_is_the_number_of_reviews.py`
reads `docs/reviews/` and compares. **The finding total is dropped rather than re-derived**, because
re-deriving it produces a fourth number nobody can verify either — and a wrong count in a backlog is worse
than no count, since it reads as a measurement.

**What is true and is worth keeping:** no finding has been rejected outright; the first two **P1**s were
both in an instrument built to check a decision rather than in the product; and two are **declined on the
environment**, each with its reason and its reactivation condition in `non-issue.md`.

### ⚠️⚠️ The standing observation: seven findings, one piece of work, five distinct shapes

**v26 and v27 are seven findings across five passes, all against the batting-order work, and every one
was in the instrument rather than in the hypothesis.** The idea was right from the first sentence. What
kept being wrong was the apparatus measuring it, and no two were wrong the same way:

| pass | what was wrong |
|---|---|
| v26 first | the cohort had no zero-density gate — **the lesson written hours earlier, not applied** |
| v26 second | the clustering table hid every category with zero exceptions, and **overturned a recorded conclusion** |
| v27 first | the relations encoded monotonicity, not the cycle: `6 5 4 4 4 4 4 4 4` was accepted |
| v27 second | the corrected model was exact and **deduced nothing** — 0 of 9 — and no test could see it |
| v27 third | the inversion survived **one property away** from where it was fixed |
| v27 fourth | the guard named *a deduced companion is an edge* **never created one** |
| v27 fifth | the sweep built to catch blind guards **was one**, and the report never paired |
| v27 sixth | the ceiling table **censored the ceilings**, and the specimen rule was not a postcondition |
| v27 seventh | the cap ran on **the wrong denominator**, and two new guards could not fail |
| v27 eighth | an **absent observation** could satisfy the contrast quota a measured zero was for |
| v27 ninth | **the delta did not fix it** — I strengthened a closed finding instead |

⚠️ **Four of the seven were invisible in output that looked entirely reasonable.** That is the shape
this project keeps meeting and it has a new member: *a model can be exactly right and have no
operational consequence*, and **satisfaction tests cannot tell those apart because they never ask the
solver anything.**

⚠️ **The run was stopped three times.** Each stop cost a few minutes; the artifact would have been
quoted for months. The cheap thing was stopping, not the measurement.

⚠️ **Earlier, the same pattern one floor down.** v23's findings and both defects the operator found by
playing share one cause: **a rule written in `main.js` is unguarded by construction**, because the suite
does not import a file whose job is to boot the application. Different file, same sentence — the guard
cannot reach where the rule lives.

⚠️ **v05-P1-02, open across ten reviews, is closed twice over.** It was fixed by drawing the erased
footnote term as the grid's own cell — and then **deleted along with the case it existed for**, when the
pool run closed the footnote cells again. Both halves are recorded, because a fix later removed for a
good reason reads in the history exactly like one that was abandoned.

⚠️ **v10 to v18 were almost entirely about one instrument too**, which is why the arc above reads as a
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

⚠️ **And v18 says something about the method rather than the code.** Reverting a fix is how the last six
reviews found what the assertions did not — but **a revert that removes two things at once cannot tell
which of them the guard is watching.** v17's probe mutation deleted both the file creation and the
replace, went red, and was believed; deleting only the creation left the suite green and was the case
that mattered. *The revert has to be the smallest change that undoes the claim*, not the whole block.

⚠️ **v16 adds the third, and it is the one no amount of care in the reading catches**: *a digest is only
as strong as its encoding.* Paths and file bytes were concatenated with no lengths and no separators, so
two entirely different untracked trees produced one identity — and **the code looks right**. There is no
missing check to spot, no branch that fails open, nothing to notice while rereading. It was found by
constructing the collision, which is the only way this class can be found. ⚠️ **The review's own example
did not collide**; the finding was right and its demonstration was wrong, which is its own small lesson
about accepting a worked example instead of running it.

## ⚖️ Findings not fixed as stated live in `non-issue.md`

**The reviewer cannot see the environment: one laptop, the operator and Claude.** Findings whose failure
mode needs a more complex setup — a second developer, a shared build agent, a hostile contributor — are
declined rather than built, and **the decision goes in `docs/reviews/non-issue.md`** with what would have
to change for it to become real.

⚠️ **The test is *does this need a second actor?*** — not *is this unlikely*. `v16-P2-01` is why: it
arrived wrapped in an attack scenario that is out of scope here, and the defect underneath needed no
adversary at all.

Declined so far: `v16-P1-01`'s launcher half, `v17-P2-01`'s digest widths. Both in `non-issue.md`.

## ⚠⚠ v29 second pass — the first P1, and the instrument could not have overturned anything

**Four more findings, all against the confirmation run rather than the product.** The adoption was
already decided; what these say is that **nothing built to check it could have contradicted it.**

### ⚠⚠⚠ v29-P1-02: the run would have rejected the mechanism without measuring it

`_package()` built the measurement package **without a reveal**. `certify_for_publication` requires
one — §23 puts the answer in the file — so every row would have been `publishable=False` for a reason
with nothing to do with the treatment. `_covered()` counts only publishable rows, and criterion 1
says **zero added overturns the adoption**. The instrument was set to return the verdict *reject*
before it measured anything.

⚠⚠ **And the same defect had been found and fixed forty minutes earlier, in the end-to-end test.** The
gate refused that fixture for exactly this, the fix was written down in the test, and it was not
carried to the runner. **A lesson applied in one file and not the next** is the shape this project
keeps meeting — and this is the third instance today, after the ruff scope and the sweep's own
baseline.

Closed two ways. The package now takes `reveal_for` from the production writer rather than
reassembling one, so there is a single place that knows what a reveal is made of. And **`_preflight()`
runs before the expensive half**: it puts an *unerased* board through the gate — nothing blank, no
treatment, no erasure, no solver — and refuses to continue if that cannot publish, because then the
fault is in how the file assembles a package and every row would carry it.

Checked by removing the reveal again: the run stops in a second with *the instrument is at fault, not
the treatment*. With it restored, an unerased board passes the gate.

⚠️ **The general form is worth more than the fix.** An expensive measurement should prove its own
instrument works before spending the afternoon, and the cheapest proof is the trivial case — the one
where the treatment cannot be the explanation.

### ⚠⚠⚠ v29-P1-01: the criterion was wired to a treatment that contains the control

`confirm.py` compared `plain` against `fallback` and made `gained − lost` the headline, with *anything
at or below zero overturns the adoption*.

**`lost` was impossible by construction.** `erase_with_lineup_fallback` makes the identical plain call
first and returns that exact puzzle when it succeeds, so **every direction covered by `plain` is
covered by `fallback`**. `plain − fallback` is structurally empty — an observed zero and a
mathematically-necessary zero are the same number on the page. The per-seed table did not repair it,
because the containment holds for every seed independently.

⚠⚠ **A pre-registered criterion that cannot be violated is not a criterion.** It is this project's
oldest defect — a check that never fires — built into the *arm* rather than into the threshold, and
written inside a file whose own docstring said it existed to stop exactly that. The pre-registration
was the safeguard, and the safeguard had the defect.

Fixed by separating the two questions, which is what let the containment hide:

| arm | question | `lost` |
|---|---|---|
| `plain` vs `on` | what the constraint costs as a treatment | **real, can be positive** |
| `plain` vs `fallback` | what the product gains from the adopted design | meaningless — monotone by design, and now says so |

⚠️ **The pre-registration was rewritten, and that is only defensible because of one fact:** the run
was stopped before it wrote a single row. `confirm.json` never existed and the process output is
literally `[killed]`. **Correcting an instrument that has produced nothing is not adjusting a
reading** — but the difference rests entirely on that, so it was verified before anything was touched.

### v29-P2-03: `certified` meant the arithmetic verifier, not the publication gate

The instrument said it measured boards that can publish, defined coverage as passing certification,
and called `verify()`. Production publishes through `certify_for_publication()`, which also applies
plausibility and independent evidence. **A board can pass every arithmetic layer and be refused for
roster plausibility or a disagreeing official total.** Now both are recorded, under names that cannot
be confused: `verified` and `publishable`. Signatures stay skipped and the phrase *all five layers* is
gone, because an unsigned run cannot claim it.

### v29-P2-04: the filler cohort was wider than the criterion that names it

The third criterion is causal deductions against division filler **on the gained boards at the hard
end**. The report summed every certified row at all five targets and all three seeds — including common
boards and fallback rows whose wrapper returned the *plain* result. **Those carry zero division by
construction and dilute the very share being tested.** The cohort is now spelled out field by field.

### v29-P2-05: the filler decision changed its unit halfway through

`gained` is identified per **direction**; the cohort then returned every qualifying row per **seed**,
and `len(cohort)` was the denominator. **A direction that succeeded under all three seeds cast three
votes and one that succeeded under a single seed cast one.** The claim being tested — *nine of eleven*
— is per direction, so the weighting could reverse the majority **without the set of useful directions
changing at all**: an adoption decided by how often a seed happened to work.

Fixed by fixing the unit: `DECISION_UNIT = "direction"`, one deterministic row per gained direction,
chosen by `SEED_FOR_DECISION = min(SEEDS)` — **a rule that cannot see the outcome**. Taking the best,
the worst, or the one with least filler would be choosing the observation after seeing it, which is
the move this whole file exists to avoid. The seed rows are still printed, with the counted one
marked, because a reduction nobody can see is a reduction nobody can check.

### v29-P2-02: the end-to-end test skipped instead of failing, and called the wrong boundary

Added in the first pass to prove a fallback board reaches publication. If the fallback returned
`unreachable` or `discarded_filler` it called `pytest.skip()` — **a successful suite outcome**, so the
v29-P2-01 regression could return without the suite going red. And it called `verify()` rather than
the gate, so a defect in plausibility or evidence refuses every fallback board in production while the
test stays green. A missing fallback board is now a failed precondition, the target is pinned rather
than searched, and the boundary asserted is the one the production writer calls.

## ⚠⚠ v29 first pass — the adoption was true in the imports and false in the outcome

Two findings, both closed. **The first would have made the confirmation run report the opposite of the
truth, and it was caught while that run was in flight.** The run was stopped.

### v29-P2-01: layers 2 and 4 searched a weaker system than the one that erased

The lineup was wired into layer 3 and 3b. **Layers 1, 2 and 4 still called `relations(board)` with no
slots.** So the fallback erased cells the batting order determines, and then layer 2 — which cannot see
the order — found alternatives the player could never choose and rejected the board as
`MULTIPLE_SOLUTIONS`. **A board unique *because of* the adopted clue was discarded before the new
derivability step ever ran.** One that stayed unique under the other four families passed by accident.

⚠⚠ **Nothing was red, and that is the whole shape of it.** Every test passed. The reference writer
fills its slots with whatever boards it finds, so a run in which the adopted branch published *nothing*
looks exactly like a run in which it published. And `TestTheVerifierCanActuallyCertifyTheseBoards`
tested the value step in isolation and read the two derivability call sites — **it asserted the
presence of imports and function calls, never an outcome.**

⚠️ **The confirmation run was measuring against this.** It would have reported near-zero certified
fallback boards, and the pre-registered reading says *if most of them fail, the adoption is not
supported by boards that can ship*. The instrument would have overturned the decision on an artefact
of the instrument. **Stopped mid-run rather than finished and interpreted.**

Closed by deriving the slots in every layer whose model can speak about the order — 1, 2, 3, 3b and 4
— and by a test that takes a real board the plain erasure **cannot** reach, produced by the fallback,
through all five layers. Reverting layer 2 makes it fail with `MULTIPLE_SOLUTIONS`, which is the
reviewer's reproduction exactly.

✅ **And layer 1 now catches the phantom row as bad data rather than as an underivable puzzle**, which
is the better answer and the more specific message: it names the slots instead of reporting a stalled
solve.

### ⚠⚠ v29-P3-01: the source disagreed with itself, and closing it took four passes

`lineup_fallback.py` opened with **`EXPERIMENTAL. NOT ADOPTED. NOTHING HERE MAY REACH PUBLICATION`**
for one commit after `write_reference_puzzles.py` started calling it. `erasure.py` said passing slots
was experimental. `open-decisions.md` — the file named for open decisions — recorded both the
constraint and the verifier step as not adopted.

⚠️ **This is not stale prose in an archived review.** It is the module contract anyone reads before
touching the file, and it said the opposite of what the caller said. **A later correction could have
undone the adoption while honestly following the repository.**

⚠⚠ **It took four passes to close, and each pass found a *different* sentence that had been true when
written.** That is the finding, not the individual sentences:

| pass | what was still false |
|---|---|
| first | the module header, `erasure.py`'s parameter docstring, `open-decisions.md` |
| second | `boxscore_domain`'s section header, `erasure.py`'s `noqa` comment |
| third | a bullet saying **the verifier can now replay it**, sitting inside a list headed *what this module does NOT establish* |
| fourth | `division_against_chain` claiming the value is **zero on every board production produces** |

The third is a structural version of the defect rather than a wording one: the bullet's *text* was
correct and its *position* made it a denial. **A list is a claim about every item in it**, and editing
one item edits that claim — which is not visible while editing the item.

The fourth is the sharpest. The sentence said the ratio is always zero, **inside the function whose
entire purpose is to put a ceiling on a non-zero one**. It was true while the constraint was fenced
off, and adoption falsified it without touching the line.

✅ **The general form:** a statement is not made safe by having been checked once. Every one of these
was accurate when written and silently false after a decision moved around it.

### v29-P3-01, as originally found

`lineup_fallback.py` opened with **`EXPERIMENTAL. NOT ADOPTED. NOTHING HERE MAY REACH PUBLICATION`**
for one commit after `write_reference_puzzles.py` started calling it. `erasure.py` said passing slots
was experimental. `open-decisions.md` — the file named for open decisions — recorded both the constraint
and the verifier step as not adopted.

⚠️ **This is not stale prose in an archived review.** It is the module contract anyone reads before
touching the file, and it said the opposite of what the caller said. **A later correction could have
undone the adoption while honestly following the repository.**

One current statement plus dated history: the module says adopted and records what it used to say and
why that mattered; `open-decisions.md` gains a superseding section with the struck rows left visible;
and the test-local `EXPERIMENTAL` identifier is now `FALLBACK`, since an identifier describing a
retired state is a statement about the code and it was the wrong one.

## ✅ v28 — a full-tree review, five findings, all five closed

Not a delta review: `forge/src`, `forge/scripts`, `serve/engine`, `serve/ui`, `tools` and `discovery`,
with both suites and the artifact templates.

### ⚠⚠ v28-P2-01: the weak solver turned lower bounds into exact values

`_bound_one_relation()` computed both ends of a finite window for every relation, then — for an
inequality — reset `low` to zero and **left `high` alone**. Right only for a positive coefficient,
where `c*x + rest <= k` caps `x` from above. With a **negative** coefficient the same relation is a
*lower* bound and says nothing about how large the cell may be, so keeping the equality-derived `high`
collapsed an open range onto one fabricated number.

`H - AB <= 0` is `AB >= H`. With `H = 0` it recorded **`AB = 0`** — false on any row with a hit.

⚠⚠ **`narrow()`, in the same module, has always had the rule right.** One rule, two implementations,
disagreeing. Both sides now derive the same way: the bound that always holds, plus the opposite one
only for an equality.

⚠️ **The agreement test existed and did not fire.** `test_it_never_claims_more_than_the_strong_solver`
asserts exactly this property — on **one** erasure, which never produced a blank whose only relation
was a negative-coefficient inequality. A sample of one is how a predicate stays wrong through a
passing suite. Now eight varied erasures.

⚠️ **Layer 3b is report-only, so nothing invalid published — but every 3b figure came from this
predicate**, including the 33% certified reported for the hand-solve pack. Those need re-running once
the pack comes back.

### ⚠⚠ v28-P2-02: the provenance rebuild could publish an empty table

`load_provenance.ps1` dropped and recreated `dbo.retroGameProvenance` **before** the first insert, with
no precondition and no transaction. An empty or mistyped `-ZipDirectory` replaced the canonical table
with an empty one and reported zero rows **as a result rather than as a failure**. An interrupted batch
left it half full.

⚠️ Every cohort in the project inner-joins this table, so an empty one reads as *no game has
admissible provenance*. **The filter passes on absence** — the shape this project keeps meeting.

Closed three ways: preconditions checked **before the connection is opened**, so a refusal cannot touch
the database at all; a shrink guard refusing a load materially smaller than what is there, with
`-Force` as the deliberate override; and a **staging table swapped in under a transaction**, so the
canonical table is only ever replaced by one already validated.

**Verified against the live database, and the table never moved from 203,908 rows:** an empty directory
is refused before connecting, and one zip of 116 is refused as *a drop of 99.4%*. The swap itself was
rehearsed on throwaway tables — rolled back, the original survives intact and the staging table is
gone; committed, the new rows are in. `DROP` plus `sp_rename` inside a transaction is atomic on this
server, which was the one assumption that could not be made.

### ⚠⚠ v28-P2-04: the repair for P2-02 made the loader work exactly once

The staging table named its default constraint `DF_retroGameProvenanceStaging_loaded_at`. **`sp_rename`
renames a table and not its constraints**, so after the swap the *canonical* table carried a
staging-only constraint name — and the next rebuild's `CREATE TABLE ...Staging` collided with it,
because constraint names are schema-scoped rather than table-scoped.

⚠️ **The transaction meant provenance was never at risk, and that is exactly why it would have gone
unnoticed.** The failure is deterministic, silent until someone needs a refresh, and lands *before* any
row is staged — a rebuild path that works once looks identical to one that works, until the second
time.

Reproduced before fixing: rebuild 1 succeeded, the constraint was confirmed sitting on the canonical
table under the staging name, rebuild 2 failed with *There is already an object named
'DF_..._loaded_at'*. Fixed by letting the server generate the name — unique per creation, and nothing
reads it. **Verified with three consecutive rebuilds**, all of which now succeed with the default still
in place, and the refusal paths re-checked afterwards.

⚠️ A fix for a data-integrity defect that introduces an operational one is still a regression. This is
the second thing today found in a repair rather than in the original — the mutation sweep's own blind
spot was the first.

### ⚠️ v28-P2-03: the discovery renderer drew a different clue surface from the product

It built the footnote line from position labels and a truthiness test: `SH: P` where the board says
`SH: 2 #9b`. Multiplicity gone, and the reference replaced by a label two rows can share — while its
own docstring says *the board exactly as the player sees it*. Every discovery eye-check ran on weaker
clues than the product gives, including the batting-order specimens.

Now a **third consumer** of `serve/tests/footnote-line-vectors.json`, with a test that all three
renderers agree case for case. ✅ The hand-solve pack was **not** affected — it has its own canonical
`footnote_line()`, confirmed by reading the PDF the operator is solving.

### v28-P3-01 and v28-P3-02

The footnote-height instrument counted `.cell`, which the line has not contained for months, so every
row reported zero and the table sorted by a constant. It now counts live terms and carriers and says
on the page when no package carries one. First real reading: **the block is 43px regardless of
carriers.**

`check_pdf.py` skipped its key check when the named key did not exist, so a typo printed full success.
A named key must now be a readable non-empty CSV; omitting it stays the only PDF-only mode. All five
modes verified, and the real key was never opened — a synthetic one was used.

## ✅ FIXED, and the first diagnosis of it was wrong: every load paid ~20 minutes to a parameter type

**The symptom.** Watching a run of `arms.py`: the client had burned **0.09 seconds of CPU in four
minutes**. It was not computing, it was waiting. The server was chaining 12-14 second queries, one per
direction, and a 48-direction sample is 96 of them — roughly **twenty minutes of database wait before
a single board is measured**. Every discovery script calling `load()` had been paying it.

### ⚠⚠ The wrong answer first, because its shape is the finding

The plan summary showed two `Clustered Index Scan` operators over `dbo.retroSubstitutionsReg`, an
unindexed 1.76M-row table hit by the two correlated subqueries that find where a substitute entered.
That was reported to the operator as the cause. **It is real, it is worth an index, and it is the
smaller half.**

The full plan says something else. `retroDailyReg` — 5,325,173 rows, clustered on exactly the
`(GAME_ID, IDX)` this query filters by — was **scanned**, and the residual predicate reads:

```
CONVERT_IMPLICIT(nvarchar(12), retroDailyReg.GAME_ID, 0) = [@P1]
AND CONVERT_IMPLICIT(nvarchar(3),  retroDailyReg.TEAM_ID, 0) = [@P2]
```

pyodbc sends every Python `str` as `nvarchar`. `GAME_ID` and `TEAM_ID` are `varchar`, and `nvarchar`
wins the type precedence, so **the conversion lands on the column**. The database collation is
`SQL_Latin1_General_CP1_CI_AS` — a *SQL* collation, which gets no `GetRangeThroughConvert` (0
appearances in the plan, checked). The index cannot be used at all.

⚠️ **What produced the wrong answer was reading a list of operator *types* and calling it the plan.**
"Two clustered index scans of a 1.76M-row table" was true and led straight to a fix that would not
have worked; the line naming *which table each operator touched* was one query away and said
`retroDailyReg` was scanned. **A summary consistent with the wrong answer is not evidence for it.**
This is the project's own rule — verify against the real artifact — applied to a query plan.

### The measurement, and how it was kept honest

Both arms on the real table, same query, same values:

| | best of three |
|---|---|
| `nvarchar`, what pyodbc sends | **827 ms** |
| `varchar` via `setinputsizes` | **0.1 ms** |

⚠️ **The first run of this test proved nothing and looked like it proved everything:** 8044x, and
*both arms returned 0 rows* — the probe pair did not exist. A seek that finds nothing is fast, and so
is a parameter mangled into never matching. The test cannot tell those apart. Re-run with a pair drawn
from the table, asserting both arms return the **same non-zero count**, which they do: 12 rows each.

### Fixed

`_rows()` in `discovery/difficulty-metrics/measure.py` types the two parameters as the columns are
declared. Verified through the real function against the old call path: same 12 rows, **0.17 ms
against 381.8 ms**.

### Still worth doing, separately — the operator's database

The two scans of `retroSubstitutionsReg` are real and the parameter fix does not touch them. That
subquery correlates column to column (`s.GAME_ID = d.GAME_ID`), both `varchar`, so **no conversion is
involved and an index would seek**:

```sql
CREATE NONCLUSTERED INDEX IX_retroSubstitutionsReg_GAME_SUB
    ON dbo.retroSubstitutionsReg (GAME_ID, SUB_ID)
    INCLUDE (EVENT_ID, SUB_FLD_CD);
```

⚠️ **It belongs in the loader script, not only in the database.** CLAUDE.md is explicit that the
processed Retrosheet database is *not* backed up and the loader is — so an index created by hand is
lost the next time the database is rebuilt from Retrosheet's files, and the cost returns with nobody
remembering why.

## ⚠⚠ OPEN, found in passing: ruff says it checks `discovery/` and nothing ever points it there

`forge/pyproject.toml` carries `extend-include = ["../discovery/**/*.py"]`, and the per-file-ignores
block below it carries a ⚠️ comment about exempting discovery's `print` calls — written by someone who
believed the directory was being linted. **It is not.** `extend-include` widens which files ruff will
*accept*; it does not make `ruff check .` from `forge/` walk out of `forge/`. No path argument anywhere
names `discovery`, and there is no CI workflow at all.

**Pointing ruff at it reports 194 findings** — which is what a rule that has never once run looks like.

⚠️ **This is the project's own named failure mode, in its own configuration file.** A check that never
fires is indistinguishable from one that is broken, and this one is worse than absent: the exemption
comment is positive evidence that it works. The `# noqa: E402` directives scattered through the
discovery scripts are the same evidence — 15 of them are flagged `RUF100`, *unused*, meaning they were
written to silence a checker that was never going to speak.

**What the 194 are, before anyone reads the number as 194 defects:**

| | count | what it is |
|---|---|---|
| `PLR2004`, `S311`, `E402` | 119 | the discovery idiom — magic numbers in a measurement, a seeded RNG, bootstrap-then-import. **Exempt by path, the way `tests/**` already is.** |
| `RUF100` | 15 | `noqa` for a checker that never ran |
| the rest | ~60 | ordinary findings, including one **unused import** and four unsorted import blocks |

**Not fixed here.** The fix is a decision about which rules the discovery idiom is exempt from, plus
somewhere for the check to actually run — and *somewhere it actually runs* is the whole finding, so
wiring it into a config that nothing invokes would repeat the defect rather than close it. There is no
CI workflow in this repository yet; that is the same gap seen from the other side.

## What is left

**`serve` runs in parallel with everything below it**, not after. It depends on none of them: it has
the contract it needs, and the group run, the drawing and the ladder are forge and pack work that does
not change what the client reads.

⚠️ **This paragraph said `serve` was at zero and named February as the window, long after both stopped
being true.** It has an engine, a phone board, 82 browser tests and six real packages at **schema 4**,
not 2. The current state and everything missing from it are in *What is actually left* at the end of
this file; the sections below are the record of how the forge got here and are history rather than
status.

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
| v16-P1-01 | the **stamp mixed two snapshots**: status and diff were separate observations of a tree that can change between them |
| v17-P2-02 | the **stamp refused a valid diff**: the path parser could not read a filename git had quoted |

**Only the first produced a reported number**, and it reached the operator as a finding before anyone
noticed the column had one possible value. The other four were caught before a run completed — which is
the difference between a review that costs an afternoon and one that costs a decision.

The instrument now: measurements as pure functions in `metrics.py` that the tests **call**; report rows
carrying their own eligibility and denominators as callables; three erasure seeds with per-trial rates;
run-level coverage kept separate from group trials; **an immutable `RunIdentity` captured before the
first board**, carrying a code digest that includes the loader, the tracked and untracked tree states
digested from the diff and from file bytes, and **a per-board content digest listed in the artifact** so
the aggregate can be recomputed; **the tracked paths taken from the binary diff itself**, so the two
halves of that digest are one observation and cannot disagree; **length-prefixed records and sixteen hex
characters**, so two different trees cannot share an identity; a refusal that fires **before** the sample
is loaded rather than after every solve, with the destination proved writable by writing and an existing
destination proved replaceable by renaming it; a per-writer staging path extracted into `publish()` so a
collision can be forced in a test; and a refusal to publish when any repository question is unknown or
the identity names no inputs.

Result schema is **4**. Schema 3 artifacts digested labels, so they cannot be compared with these and
must not present as the same contract.

⚠️ **Every one of those fixes is guarded by a test that fails when the fix is reverted**, checked by
reverting each one and watching a named test go red — not by rereading the assertions. **That practice
paid for itself in v15**: two mutations left everything green, one because the mutation was bad and one
because a guard was missing.

### ▶ The run — **measuring**, at `44d9582` on a clean tree

| | |
|---|---|
| launched | 2026-08-19 09:37 |
| revision | `44d9582`, tracked **clean**, untracked **clean** |
| instrument | `4f894c5391eb` — measure, metrics **and the loader** |
| result schema | **4** |
| parameters | three seeds, eight directions per decade, the 25% gate, `≤13` batters, `≤4` pitchers, target 8 stalls |
| gated sample | **240 directions** |
| progress | measuring since ~10:35; the log reports every 20 boards |

**The first launch (09:22, `20e6e1f`) was stopped after ten minutes.** `v14-P1-01` lands on the artifact
it would have produced, and it had not yet finished loading. **The evidence would not have been wrong —
the tree was clean at a known commit, which pins everything the weak digest failed to pin — but the
stamp would have carried a claim the artifact did not support**, and a provenance nobody can check is a
claim rather than evidence. Ten minutes is the entire cost of that decision, and it is the argument for
reviewing an instrument before trusting a number rather than after.

**The gate returned 240 directions**, and measurement started at roughly the one-hour mark.

⚠️ **The loader is the slow part by a wide margin, and it prints nothing while it works.** Both launches
sat with an empty log for their first *hour*, not the ten minutes first assumed: `load()` gates every
candidate direction on zero density before the first board is measured. An empty log early is the
expected state, not a stall. **Worth carrying forward as a fact about this instrument** — the next person
watching it, including me in a later session, will otherwise read the silence as a hang and kill it.

**v15, v16, v17 and v18 all landed mid-run and the run was left alone each time**, which is the
opposite of the v14 call and rests on a different fact. v14 changed what the stamp *would say about this run*. v15 closes **failure windows** —
a disagreement between two git snapshots, an unreadable file, an unwritable destination — and none of
them is open here: the tree was clean at capture, the destination is fine, and `format.py` is not on the
run's path. Its `instrument 4f894c5391eb` identifies the v14 file **by content**, which is recoverable
from `44d9582`, so the artifact stays checkable. Restarting would have cost twenty minutes and corrected
nothing.

The same reasoning holds for v16, with one addition worth stating: **its digest fix changes what future
stamps mean, not what this one says.** A collision between two untracked trees is a property of the
encoding, and this run's untracked set is one file whose identity nobody needs to distinguish from
another. **And the result schema moves to 5 because of it.** Two files claiming schema 4 with
eight-hex and sixteen-hex tree digests would be two contracts under one number, which is exactly what
the version exists to prevent — the improvement v14 took, applied to a change that is about identity
rather than about a metric. This run will produce a schema 4 artifact, correctly labelled as one.

**v17 and v18 changed only the preflight and the diff parser**, both of which ran to completion before
this run started measuring. Nothing they touch is on the path of a run already past `identify()` and
`load()`, so there was nothing to reconsider.

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

## v18 — verified, none rejected. **One finding, and it was half mine.**

The reviewer ran under the stated environment for the first time, and returned **one** actionable
finding instead of three or four. That is the rule working: the personas that had been producing
adversary and concurrency findings reported nothing, in writing, rather than reaching for something.

### v18-P2-01 — the third attempt at the destination preflight, and the guard that let it through

**The tautological guard first, because it is the reason the gap survived.** The v17 test asserted

```python
assert target.exists() is False or target.name != "results.txt"
```

*after* `_refuse_unwritable` had cleaned up in `finally` — so `exists()` was always false and the whole
line was always true. Deleting the statement that creates the probe target left the suite green,
verified by running it: the guard proved a `replace` **call** had happened, not that it had replaced
anything. **Eighth of its kind in this project, and written an hour before it was caught.**

⚠️ **The mutation that would have caught it was one I did not run.** I reverted "the probe only creates,
never replaces" as *both* lines at once, and it went red. Removing only the write — the smaller,
sneakier revert — was the one that mattered. **A mutation that removes two things at once cannot tell
which of them the guard is watching.**

**And the finding underneath.** v17's probe replaces one sibling with another, which answers a question
about the *directory*. `publish` ends in `pending.replace(out)`, against that specific file, and Windows
lets a handle stay open for read and write while denying deletion — so a results file left open in a
viewer passes the sibling replace and `os.access` alike, and fails hours later at the one operation
nobody performed.

**Three versions, each getting one half right:**

| | exercises the real target | safe against a kill |
|---|---|---|
| v16 — rename aside and back | ✅ | ❌ the file can be lost |
| v17 — replace one sibling with another | ❌ | ✅ |
| v18 — replace `out` with a byte-for-byte copy of itself | ✅ | ✅ |

The third has no disappearance window because **`out` is never the source of a rename**: a crash before
the replace leaves the original untouched, and a crash during it leaves an atomically identical file.
The v17 guard that forbids moving the artifact still holds and still means something.

## v17 — verified, none rejected. **Two fixed, one declined; and one v16 repair withdrawn.**

Three findings. **The interesting one is that a v16 fix had to be taken back out** — it closed a late
failure by introducing a way to lose a finished result, which is a worse trade than the one it replaced.

### v17-P1-01 — the preflight moved the artifact it was checking. **v16-P2-02 is withdrawn**

v16 proved an existing destination by renaming it aside and restoring it in `finally`. **That made a
read-only check destructive.** `finally` does not run after a kill, a crash or a power cut, so an
interruption in the microsecond between the two renames leaves the canonical artifact **gone** — sitting
under a name nobody looks for.

⚠️ **This instrument gets stopped by hand.** Three times in one afternoon. The window is not
hypothetical, and losing a completed five-hour result to a Ctrl-C is worse than discovering an
unwritable destination late.

The finding also describes a lost-update race between two concurrent runs. **That half is out of scope**
— it needs a second process nobody here starts — but it does not need to be argued, because the repair
for the reachable half removes it too.

**The preflight now replaces one probe with another, in the destination's own directory, and never
touches `out`.** That exercises the operation `publish` performs without putting the previous result at
risk. What it cannot see is an ACL belonging to `out` itself; `os.access` covers the read-only case, and
the remainder is not worth a lost result.

⚠️ **Worth recording as a shape, not just an incident.** v16-P2-02 was a correct finding and its repair
was reviewed, tested and mutation-checked — and it was still a net loss, because *the cost of the fix
landed somewhere the finding was not looking.* A repair is not finished when it closes the case; it is
finished when what it costs has been weighed against what it saved.

### v17-P2-02 — the stamp refused a diff git had written perfectly well

`_diff_paths` matched only headers beginning `diff --git a/`. Git writes `diff --git "a/…"` for any path
carrying a tab, a quote, a backslash or — under the usual `core.quotePath` — an accented character. Such
a diff yielded no paths: the count was zero, the bytes were not, and `_describe` correctly refused the
run as unreadable.

**An accented filename in a Spanish repository is enough**, which makes this a false refusal reachable
on any afternoon — and the fail-closed guard from v15 is what turns a parsing gap into a stopped run.

**The fix is to stop parsing a presentation format.** `_describe` now takes a count and the raw bytes:
`diff --git ` is the part of the header that does not vary, a count is all the digest ever needed, and
**the bytes already name the files.** Parsing git's quoting rules more cleverly would have been the same
bug with more code.

### v17-P2-01 — declined. See `non-issue.md`

64-bit and 48-bit digest widths are collision-feasible **for an actor generating candidates**. Nothing
generates candidates here, and at 48 bits four hundred real boards collide with probability around
3 × 10⁻¹³. Declined on the threat rather than the cost, with the reactivation condition recorded.

## v16 — verified, none rejected. **Three closed; the fourth closed as far as it goes.**

Four findings. **v15 fixed what the digests refused; v16 found what they could not distinguish** — and
one of the four is the first finding in this run of reviews that no amount of rereading would have
caught.

### v16-P2-01 — two different untracked trees, one identity. **Verified by building the collision.**

Path bytes and file bytes were concatenated with no lengths and no separators, and `_describe` then
prepended another delimiter-free join of the same paths. The encoding is not injective before SHA-256
ever runs:

| tree | digest |
|---|---|
| `{a: b"b", bc: b""}` | `2 files, 591a8d49` |
| `{ab: b"b", c: b""}` | `2 files, 591a8d49` |

Same count, same label, same digest. **No adversary is required** — two innocent trees suffice, which is
why this is a correctness defect and not only a security one. Every field is now length-prefixed, and
the digest keeps **sixteen** hex characters rather than eight, because 32 bits is small enough to search
by varying a disposable file until the displayed identity matches an approved one.

⚠️ **The review's example did not collide.** `aa`+`X` gives `aaX` and `a`+`aaX` gives `aaaX`. The finding
was correct and its demonstration was not, and the difference only appeared because it was run. A worked
example in a review is a claim like any other.

### v16-P1-01 — two snapshots of a tree that can change between them. **Closed for tracked, residue recorded**

`git status` and `git diff` are two observations. v15 refused the one contradiction it could see — no
paths with a non-empty diff — and accepted every other mixed pair without proving the paths and the
bytes described one state.

**The tracked half is now structurally impossible to get wrong:** the paths come out of the binary diff
itself, so there is one snapshot and it cannot contradict itself. The v15 guard stays, because it still
covers untracked.

⚠️ **What is not fixed, and will not be without a launcher.** Untracked files are invisible to `diff` by
definition, so the listing and the bytes remain two observations. And Python imports the instrument
before `identify()` runs, so the bytes that execute are read a moment before the bytes that are hashed.
Closing either means running the worker from an immutable snapshot — a launcher that captures a
manifest, starts the process from a clean worktree matching it, and publishes only from there.

**Recorded as residual risk rather than built**, on the same footing as §22's note that the verifier's
independence has a limit: the exposure is a millisecond window on the operator's own laptop with no
concurrent editor, and the mechanism to close it is larger than the instrument it would protect. It is
written here so it is a known limit and not an assumption.

### v16-P2-02 — the preflight proved the directory, not the destination. **Withdrawn by `v17-P1-01`**

Creating a fresh sibling and renaming it proves the parent permits creation. `publish` ends in
`pending.replace(out)`, and on Windows an existing `out` can be read-only, held open by another process
without delete sharing, or carry an ACL of its own while the sibling probe succeeds happily. **A results
file left open in an editor is the realistic case**, and it failed only inside `publish`, hours later.

An existing destination was renamed away and back — the same right `replace` needs — and restored in
`finally`.

⚠️ **`v17-P1-01` withdrew that.** `finally` does not run after a kill, so the repair could lose the
previous result entirely. The preflight now replaces one probe with another and never touches `out`;
`os.access` covers the read-only case, and a target-specific ACL is not worth a lost five-hour result.

### v16-P2-03 — `2.0 == 2`, so the constructor accepted a schema its parser refuses

`__post_init__` asked only `self.schema not in READABLE`. Python makes `2.0 == 2`, so `schema=2.0`
passed, `written_as` returned the float, and `as_json()` emitted `"schema": 2.0` — a document
`from_json` correctly rejects, because *it* checks `isinstance(schema, int)` and excludes `bool`.

**The type could build output outside the language its own parser accepts.** That sentence is already
written in this file, about slot references, three months of reviews ago. It arrived one field over for
the same reason it arrived the first time: **the rule had two copies and not one home.** There is now a
`_check_schema` called by construction and by parsing, and the test parameterises `2.0`, `"2"`, `True`,
`1` and `None`, with `None` separated out because absence is the one legitimate value.

### ⚠️ The seventh guard that did not guard — and the second bad mutation

| Mutation | What it turned out to be |
|---|---|
| tracked paths from status again | **a real hole.** `test_the_tracked_paths_come_out_of_the_diff` exercised `_diff_paths` **alone**, so it would have stayed green while `identify` went on asking `git status`. A helper that exists and is never called is indistinguishable from one that is broken |
| the rename source not consumed | **a bad mutation.** With `-z`, an unconsumed source path yields a status of `ol`, which is not `??`, so it is dropped either way. The input could not distinguish the two implementations — which made the guard tautological, not the fix wrong |

The first is closed by making the two observations **disagree**: status names `stale.py`, the diff names
`fresh.py`, and the tracked digest must be the diff's. The second by feeding a source path that begins
with `?? `, which is the only input where consuming the record changes the answer.

**Both were found by reverting, and neither would have been found by reading.** That is now the third
review in a row where the revert found something the assertions did not.

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

## ⚠️ Noticed while rendering the engine: a blank the scoreboard already answers

`line_score.offense_hits = batting_totals.hits` and three siblings — `batting_totals.R`,
`pitching_totals.R`, `pitching_totals.H` — are two-term equations. When the generator erases one, the
player reads the number off the scoreboard; the solver records a deduction. **Every one of the six
reference packages erases exactly one of the four**: five times `batting_totals.H`, once
`pitching_totals.R`. Six of 204 blanks, 2.9%.

Not a bug — the relation is real and in the `column_sum` family. The question is whether a blank with a
lookup in it should count towards a stall or a chain, and whether the rate holds across the pool.
**Filler wearing a new face**, in the row that was assumed to be a read-only anchor until the real
packages showed it carries blanks.

**Needs the database, so it is forge work.** What would change: the generator refusing to erase a total
the scoreboard prints, or the solver not counting the move. Recorded before continuing rather than
mentioned in passing.

## v19 — verified, none rejected. **All nine closed.**

### v19-P2-04 — the CSS rule with no class to attach to

`.term.live` and `.term.zero` were declared in the stylesheet and **never applied by the renderer**. Both
rules were dead, so a real hit batsman had exactly the hierarchy of a category that never happened.

⚠️ **This is a check that never fires, in type rather than in code**, and it lands on the one thing §6
calls out by name: nine boards in ten carry nothing on that line, players learn to stop looking, and *the
prominence is the mechanism*. It went missing when `renderFootnotes` was rewritten to stop printing false
question marks — a fix that removed a defect and a feature in the same edit.

Guarded now by a DOM test that reads the total out of the rendered label and requires the matching class,
and that requires **both** states to occur on the board it uses. Checked by reverting: the guard goes red.

### v19-P1-01 — the instrument deleted its own strongest evidence

`scoreboard-blanks` returned an empty list the moment either arm's `erase()` came back `None`. A pair
where the `before` arm reached a target *only because a scoreboard duplicate was erasable* vanished
entirely — and that pair is the finding. The report would then have summarised the survivors and called
it a null.

**The false-null failure this project built an instrument to prevent, arriving through the door that
instrument left open.** Each arm now records `reached`, reachability is reported before any summary of
what reached, and the chain and stall comparison is restricted to pairs where both arms produced a board
rather than silently losing the rest. ⚠️ The zero-footnote instrument, written the same week, already did
this correctly — so the rule was known and applied unevenly.

### v19-P3-01, P3-02 — an assertion on third-party input, and missing `slots=True`

`assert found is not None` validated a Google Fonts response. `python -O` removes it and the next line
raises `AttributeError` instead of explaining. Now an explicit refusal. And both result dataclasses gain
`slots=True`, with `asdict` replacing a `__dict__` read that the flag would have broken.

### v19-P2-03 — two readers of one schema, and the shared vectors that stop it recurring

The Python reader and the client enforced **different v3 contracts while both claiming to read v3**.
Python defaulted `labels`, `pitcher_labels` and `metadata` and never counted the labels; the client
required label counts but accepted a **null footnote total**, and slot references whose grammar and
uniqueness it never checked.

⚠️ **The null total is the unsolvable board again, reached from the schema side**: the client counted it
among the blanks and `renderFootnotes` skips a term whose total is unknown, so the cell existed, had to
be filled, and had nowhere to be filled from.

**The durable half is `serve/tests/package-vectors.json` — shared data, not shared code.** Sixteen
mutations of a real package, each with the reason it is accepted or refused, run by the Python suite and
by the browser suite. `forge/` and `serve/` still import nothing from each other, which §33 requires; the
file is what makes two implementations answerable to one contract without becoming one implementation.

⚠️ **It found a divergence on its first run** — Python still accepted a package with no `metadata` — which
is the strongest thing that could be said for it. A vector both sides agree on proves nothing; **what the
file forbids is the two disagreeing.**

### v19-P2-02 — the board could not be used before the first digit

Editable cells were elements with click handlers and nothing else: no focus, no role, no keyboard, no
accessible name, no selected state. The keypad *was* focusable and useless, because it does nothing until
a cell is selected. A player using VoiceOver, TalkBack or a switch could not find a blank at all — and
that needs no unusual setup, just a phone and its own screen reader.

Blanks are now buttons: focusable, Enter and Space, `aria-pressed` tracking the selection, and a name
built from the row label and the column heading out of the catalogue, so a reader announces `SS, hits`
rather than `blank`. **Given cells are deliberately not focusable** — forty stops that lead nowhere is
its own defect.

### v19-P2-01 — the instrument deciding a board feature had no tests

⚠️ **And writing them found the ninth tautological guard, mine, in the same hour.** Two of the four new
tests rebuilt the instrument's own filtering inside the test and passed while a revert reordered every
arm. A guard that reconstructs what it guards is testing itself.

Fixed by extracting `walks()` and injecting the eraser, so the tests **call** the instrument. All four
reverts now go red: inverting the non-zero predicate, ordering each arm separately, recording a failure
as reached, and dropping a failed row.

### v19-P3-03, P3-04 — a swap that could not refuse, and docstrings describing retired rules

`useCatalog()` accepted any object, and the test named for it swapped in a *complete* copy of English and
compared it with the same complete English — it could not fail, because there was no refusal in the code
to trigger. Missing and unexpected keys are both refused now, and the refusal is atomic.

And the format module still said the per-batter footnote cells were "given complete and never erased" and
that labels carried suffixes. Both were reversed weeks ago; the real packages disagreed with the
docstrings in silence.

## ⚠️⚠️ The pool answered: the footnote cells bought **nothing**

72 directions, 2 seeds, 5 targets, 3 arms, 2160 rows, one canonical walk per trial.

| target | footnotes fully erasable | erasable if non-zero | **footnotes given** |
|---:|---:|---:|---:|
| 5 | 100% | 53% | **54%** |
| 8 | 100% | 21% | **21%** |
| 11 | 100% | 1% | **1%** |
| 15 | 65% | 0% | **0%** |
| 19 | 4% | 0% | **0%** |

**Pair by pair, non-zero and given are identical on every field in 653 of 720 trials — 91%.** The 67
that differ, differ **only in the blank count**: same stalls, same reachability, one extra cell to fill.
Opening the footnote cells buys a blank and no difficulty.

### The old figure reproduces exactly, which is what makes this a correction rather than a new result

The measurement that opened these cells said: *with the footnote line given the median board stalls 5
times and only **56%** reach five; with them open it is 15 and **every** board reaches five.*

Both halves are confirmed and both were counting zeros. Today: **54% reach five with footnotes given** —
the same 56% — and **100% with zeros erasable**. The gap was never difficulty. It was the solver
deducing values that were zero because the thing did not happen.

### What this invalidates, stated as invalidated

- The **stall ceiling** and its 27% convergence
- The **coverage** figures at every target
- The **5-versus-15 gap**, which was the entire argument for opening these cells
- ⚠️ **The ladder — 19, 16, 13, 9 and 6 stalls — cannot be built.** At 19 stalls the real arms reach
  **0%** and even the zero-counting arm reaches 4%. The rungs are stall counts taken in the inflated
  world, and the hand-solve pack was specified in them.
- The **group run's** blocking percentages, measured at a target of 8 stalls that only 21% of boards now
  reach

### The decision this supports, and it is the operator's

**The footnote cells go back to given.** `non_zero` and `given` differ by one board out of 144 at the
only target either reaches often, and by nothing at all elsewhere. Keeping them erasable costs the
footnote-cell drawing, up to 24% of the phone screen, and the cap discussion — for a blank with no
deduction in it.

⚠️ **If that is the call, `v05-P1-02`'s drawing becomes dead code and §6 reverts** — the per-batter cells
were opened on this measurement and it did not hold. Recorded here rather than acted on: it removes a
board feature, and §7 says a value that shapes the product is presented as a proposal.

## ⚠️⚠️ Every stall figure in this project counted zeros — the correction

**Priority A1, and it invalidates numbers rather than adding one.**

A footnote term worth zero was erasable. When `HBP`, `SF`, `SH` and `CI` are all zero for a batter the
row identity is `PA = AB + BB` — the terms contribute nothing *because they did not happen* — so an
erased zero asks the player to type `0` into a category that never occurred. The solver deduced it,
correctly, and **recorded a stall**.

**On the reference fixture, 35 of its 36 footnote cells are zero.**

### The measurement that settles it, on one board, three treatments, same seeds

| treatment | candidate cells | stall ceiling per seed | max |
|---|---:|---|---:|
| footnotes fully erasable — **what every figure was measured under** | 110 | 14, 17, 14 | 17 |
| footnotes erasable only where non-zero — **now** | 75 | 7, 9, 1 | 9 |
| footnotes **given entirely** | 74 | 7, 9, 1 | **9** |

⚠️ **The last two rows are identical.** On this board, opening the footnotes bought *nothing at all*
once the zeros were excluded — not "most of the gap was zeros", **all of it**. One board, and one whose
footnote line is almost entirely empty, so the pool measurement still has to run. But the direction is
not in doubt.

### What this invalidates

Everything derived from a stall count taken with zeros erasable:

- the **stall ceiling** and its 27% convergence
- the **coverage** figures at each target
- the **5-versus-15** gap that was the whole argument for opening the footnote cells
- the **ladder rungs** — 19, 16, 13, 9, 6 — which are stall counts
- the **group run's** blocking percentages, which were measured at a target of 8 stalls

### How it was found, which is the part worth keeping

**The operator solved a 19-stall board with the footnote terms visible and found it hard.** So the
difficulty was there without them, and the measurement said the opposite. No test could have caught it —
the solver was working correctly and the values were genuinely unknown to it. They were just worth zero.
Recorded in `CLAUDE.md` as a class of its own: *a working instrument pointed at the wrong thing*, as
distinct from the broken instruments the earlier entries describe.

### Open, and it may close the question for good

If the pool measurement agrees with the board above, **erasable footnotes were never worth anything** and
they go back to given — which also removes the drawing, the 24% of screen, and the cap discussion in one
move. ⚠️ A second reason to expect little: with only non-zero terms erasable, the *positions* of the
blanks announce which rows carry the term. `HBP: 3` above three boxes means each box is 1.

## ⚠⚠ OPEN — the batting-order recommendation was given, reversed under one push, and both
versions were overstated

**Full record: `docs/reviews/batting-order-reversal.md`.** The operator asked for it because he could
no longer tell whether an answer came from evidence or from him pushing, and that objection is correct.

The short version, for anyone reading only this file:

- **No measurement was re-run between the two recommendations.** `arms.json` is byte-identical. Only
  the partition changed.
- **Position 1 (do not adopt)** rested on a pooled table that mixes two populations answering different
  questions, plus **one board selected by sorting descending on the very phenomenon being judged** —
  and that board was not even in the target-8 set. The deciding partition was in the file the whole
  time and **was not run before the recommendation was given**. That is the defect, and it does not
  depend on anyone's motives.
- **Position 2 (adopt where the board needs it)** was then overstated in the direction the pressure
  pointed: `+11 −2` was best-of-three bookkeeping (per seed it is +5 to +9, and one seed loses six),
  and `9 of 11` is `10 of 15` counted per walk.
- **The position the evidence supports is neither.** The gained subgroup is **eleven directions**, and
  that is not enough to spend a second verifier implementation on. The next step is a larger,
  **pre-registered** sample of that subgroup — not an implementation.

⚠️ **Nothing measured here touches human derivability.** Layer 3 has the batting-order *relations* but
no value-producing lineup move, so any board leaning on the constraint is currently refused as
underivable.

## ⚠⚠ v27 eighth and ninth passes — one P3, and a ninth pass spent saying I had not fixed it

### v27-P3-16: an absent observation could fill the slot reserved for a measured zero

The specimen classifier asked `any(row.pa_by_lineup > 0 for ... if row.reached)`. **`False` meant two
different things.** The treatment reached the target using no lineup arithmetic — a genuine contrast,
which is exactly what the pool is for. Or the treatment **never reached the target at all**, produced
no qualifying row, and fell through to the same branch. Both went into `negative`.

The second kind could then be picked as the promised contrast, and `_specimen_pages()` would write
`arm on_total_erasable never reached 5 stalls` where a board should be — while the summary announced a
complete two-positive/one-contrast set. **The eye-check the adoption decision rests on could quietly
be one page short and still report itself complete.**

⚠️ **This is the measured-zero-against-absent-observation defect**, which this project has met before
as a null result read off medians with no per-item count. It arrives dressed differently every time.

Fixed by putting **eligibility before composition**: `_classify_specimen()` returns `None` unless
*both* rendered arms produced a page at the target, so the promised comparison is known to exist
before anything decides what kind of comparison it is.

### ⚠⚠ The ninth pass exists because my eighth-pass delta did not touch the defect

The review's ninth pass is one paragraph long and says the classifier is unchanged. It was. **What I
had actually shipped was a new sweep mutation for `v27-P2-13` — a finding already closed** — while the
open P3 sat untouched. Useful reinforcement of something that did not need it, delivered as though it
were the correction.

That is a whole review pass spent telling me I had not done the thing. The check that would have
caught it is not subtle: **read the finding, then read the diff, and ask whether the diff touches the
file the finding names.** It named `arms.py:518`. The diff touched `mutation_sweep.py:112`.

**Closed now, and guarded three ways** — `forge/tests/test_specimen_eligibility.py` covers an unreached
treatment, an unreached baseline, a missing page against rows that claim otherwise, and a row at
another target; the genuine contrast and the genuine positive are both asserted **so the fix cannot
pass by closing the pool entirely**; and all three parts are in the mutation sweep, which now stands at
**sixteen claims**.

## ⚠⚠ v27 sixth and seventh passes — five findings, and three of them are guards I had just written

**All five fixed.** The seventh pass is the one worth reading, because three of its findings are in
code written the same hour, and one of them is a mutation check that agreed with a blind guard.

### v27-P2-13 — the cap ran on a different denominator than the one it was measured with

`LINEUP_DIVISION_SHARE_CAP = 0.20` came from two boards at **9 division steps over a chain length of
24 and 26** — 0.375 and 0.346. `division_share()` divided by `len(solution.deductions)` instead.
Those are not the same quantity: `chain_length` is the longest run of steps each waiting on the one
before, a **depth**; the deduction count is every cell recovered. On one specimen they are 20 and 37.

⚠️ **So the cap would have kept the two boards it exists to discard.** 9/37 is 0.24 and 9/50 is 0.18,
both at or under a threshold set from 0.38. The only protection against the known filler-heavy shape
was silently absent. **A provisional threshold may be soft; its unit may not.**

Fixed as `division_against_chain()`, which carries the accurate name at the call site, plus a test that
**changes its verdict when the denominator changes** — the previous test asserted the ratio equalled
`lineup / len(deductions)` and passed because its board had zero lineup steps, so `0/a == 0/b` agreed
with both implementations and could distinguish neither.

⚠️ Recorded and not hidden: the unit is a ratio, not a share, and is **not bounded by 1** — the
numerator counts steps and the denominator is a depth. That is a weakness of the unit, and it is on the
list the pre-registered confirmation run has to settle.

### ⚠⚠ v27-P2-14 — a guard that could not fail, and a mutation check that agreed with it

`test_production_erasure_still_passes_no_batting_order` scanned `erasure.py` for a `shape_of` call
carrying a **keyword** named `slots`. The real call is `shape_of(direction, slots)` — *positional*. The
assertion could never be false, and it inspected no caller of `erase()` at all, so a production builder
could start passing a lineup and the safety test would stay green.

⚠⚠ **The part that matters is how it was "verified".** The mutation used to check it changed that call
to `slots=slots` — **the one change the guard can see, and not the risk it names.** That is the same
defect as the guard, one level up: *checking a guard against the mutation it happens to catch is not
checking it.* The rule in `CLAUDE.md` says to ask what change the guard would let through. I asked what
change it would catch.

Replaced with a walk over every first-party call to `erase` across the source tree, refusing `slots`
anywhere outside the experimental module, with a positive control proving the finder sees the one call
that is allowed to pass it. **Re-checked by creating a real production module that calls
`erase(..., slots=lineup)`** — it fails.

### v27-P2-15 — the import walk pointed the wrong way

The publication guard computed what `certify_for_publication` imports. Real wiring points the other
way: a producer imports the fallback **and** imports certification. That bridge leaves certification's
own import set untouched, so the guard was blind to the exact mistake it named, by construction.

Replaced with a scan for any first-party module whose dependency closure reaches **both** endpoints.
**Re-checked by creating that bridge module** — it fails. A stricter "nothing imports the experiment at
all" test sits beside it and is documented to be deleted deliberately when research code legitimately
imports it, so the fence weakening is visible rather than silent.

⚠️ **Still open as a design note, not a finding:** a graph guard survives only until someone
refactors imports. The durable form is making experimental provenance **unrepresentable** as an
ordinary publishable result — a distinct result type that only research code accepts. Recorded in
`batting-order-plan.md`; not built, because the freeze is at steps 1 and 2.

### v27-P2-11 — the ceiling table censored the ceilings

`_ceiling()` was built from `_pairs()`, which keeps only walks *both* arms reached **at the same
target**. A walk that ran to 8 under the treatment and stopped at 6 under the baseline contributed
neither number — and that is precisely the population a ceiling gain lives in. With 73 treated
target-8 reaches against 53 baseline ones, at least twenty walks could never influence the table
summarising exactly that.

⚠️ **Any ceiling figure previously reported from this instrument is void**, including the "44
directions, both medians 8" line. `Row` now carries `walk_max_stalls`, the terminal maximum over the
whole accepted walk, recorded independently of target reach. The existing `arms.json` predates the
field, and the table now prints **NOT ANSWERABLE** rather than reverting to the censored answer.

### v27-P3-12 — the specimen rule was a comment, not a postcondition

`if uses_lineup or not contrast` accepted lineup-positive boards as they arrived, so three in a row
filled the quota and the contrast could never enter — while the summary still printed a rule promising
one. The artifact happening to contain a contrast was draw order, not the safeguard. Now two pools are
collected to the end of the sample and `_choose_specimens()` **raises** if either cannot supply its
share, because a specimen file that quietly lost its contrast is an eye-check on one population
presented as an eye-check on two.

## ⚠⚠ v27 fifth pass — two P2s, and the first one is the worst finding in this review

### v27-P2-09: the mutation sweep had the exact defect it was built to catch

`caught` was `returncode != 0`, and the sweep **never checked that the unmutated suite passes**. One
unrelated failing test, a collection error, a bad flag — anything making pytest non-zero for its own
reasons — and all ten mutations report `CAUGHT` from that same failure, `failures` stays empty, and the
script prints its strongest possible result while proving nothing about any mutation.

⚠️ **A tool written to stop guards that cannot fail, that could not fail.** It was written in the same
hour as the rule *check your own guard by asking what change it would let through* — and that question
was not asked of the checker. The rule was applied one level down and not at the level it was written.

Closed two ways, and **verified by planting the failure**: a green baseline runs first and the sweep
aborts without it; and the exit code is *read* rather than tested for truthiness, since pytest returns
`1` for "a test failed" and `2`–`5` for interrupted, internal error, usage error and no-tests-collected
— states where the mutation was never judged at all, now reported as `BROKEN` rather than counted as a
success. With an always-failing test planted, the sweep aborts and exits 1; before the fix it printed
*all 10 claims are guarded*.

### v27-P2-10: `Row` was made pairable and the report did not pair

Each table selected reached rows per arm independently, and **reachability is changed by the
treatment** — so the arms contributed different directions, seeds and target mixtures to figures
printed side by side. A walk reaching 8 stalls only under `on_total_erasable` put its blanks into that
arm's median with no counterpart in `off`. Any difference could have been *which trials survived*.

Coverage stays unpaired — failing to reach **is** its outcome. Every other table is now restricted to
walks both arms completed, keyed by direction and seed, reporting the paired delta **with the per-item
count**: how many went up, down and unchanged, because two walks moving opposite ways leave every
median untouched.

⚠️ **The run did not have to be repeated.** `arms.json` is written before any formatting, so a defect
in the report cost a second of re-reading. `--report-only` now exists for exactly that.

### ⚠⚠ And two more found by doing the eye-check the rules require

**The specimens were drawn by position in the sample, so all three showed boards where the treatment
does nothing.** 73% of reached walks in that run used lineup arithmetic; the three rendered used none.
A sample meant to show a phenomenon has to contain it. Selection is now by whether the *drawn arm* used
it, keeping one contrast board deliberately.

**And the first version of that filter said `arm != BASELINE`**, which includes `on_total_given` — an
arm that is never drawn. It would have picked boards for a phenomenon the reader cannot see on the
page. Caught by rendering and looking, one commit after the fix it was part of.

⚠️ Also: pages were joined on two newlines, the same separator a board uses before its own solution
path, so the file could not be split back into pages by eye or by code. Now an explicit rule.

## ⚠⚠ v27 fourth pass — and the change of method it forced

**The finding.** `test_a_deduced_companion_is_an_edge_and_moves_the_depth` gave only the team total,
left both rows of the shared slot unresolved, and asserted they were absent. That is the *unsplittable
sum* — a different guarantee, which already had its own test. **It never created a deduced companion**,
so reverting the transport it was named for left it green. A guard that cannot fail is indistinguishable
from one that is broken, and this one was named for the exact defect it could not see.

Rebuilt against the real case: row 9's plate appearances fall out of the row identity by propagation,
then lineup arithmetic derives row 8 as *the slot total less row 9*, at depth 2 and depending on it.

### ⚠⚠ What actually needed fixing was how I was working

**Five passes in a row found defects in code written minutes earlier. The reviewer was doing the
checking I should have done**, and shipping-then-waiting is not a method.

`discovery/batting-order/mutation_sweep.py` reverts each claim of this work in turn — ten of them, each
the *smallest* change that undoes one thing — and requires the suite to notice. **It found one on its
first run, which I would otherwise have handed over:** flipping the verifier's spread bound from
`<= 1` to `== 1` — which would reject every board whose plate appearances divide evenly by nine — left
the entire suite green.

⚠️ **The reason is worth more than the fix.** The cross-implementation test compares *which rows* each
relation is about. `equality` does not change the rows. **A structural comparison is blind to semantics
by construction**, and it was the only thing standing between the two implementations and a silent
divergence. The gap is closed by asserting the two fields the structure cannot carry: the constant and
the equality flag.

**All ten claims are guarded now, checked rather than believed.** The sweep is kept and is meant to run
after touching the constraint, the solver, or their tests — not as a habit, as a step.

## ⚠⚠ v27 third pass: the fix left the inversion alive one property away

**Stopped the run a third time.** Both findings are in fields the experiment was persisting.

### The cheapest move was still being counted as the dearest

`Solution.bounding_steps` counted `not has_a_comparable_cost`. That **was** the same as
`technique is BOUNDING`, for years — while bounding was the only step with no comparable cost.
`LINEUP_ARITHMETIC` has none either, because reading a total and dividing by nine combines no terms. So
a total-visible board reported **nine bounding steps while using zero**, and `stalls`, which checks the
technique, said zero on the same solution. **Two public metrics disagreeing about one board.**

⚠⚠ **This is the exact inversion `LINEUP_ARITHMETIC` was introduced to remove, surviving one property
away from where it was fixed.** I corrected the solver and the instrument's classifier and left a proxy
that had meant the same thing until that moment.

**An equivalence held by circumstance is a second definition of the thing**, and it breaks the instant
the circumstance changes — silently, because both readings were true for as long as anyone had looked.
The lesson is not about this line: it is that adding a third value to an enumeration invalidates every
place that tested for the other two by proxy. `has_a_comparable_cost` was the only such proxy; it was
audited rather than assumed.

### The graph did not describe the arithmetic

A shared slot is computed as *the slot's total less the rows already known*, and the move recorded only
the team total. On a substitution-heavy board an edge and its depth were lost, so `chain_length`
**understated the path that produced the number**. The value was right; the recorded graph was not the
one that reached it — and an instrument comparing chains across arms reads exactly that graph.

⚠️ **It also recorded the total when the total was a given.** Propagation records only cells that were
*deduced*, because a given was never reached. Two conventions for one graph, in a file that already had
one.

## ⚠⚠ v27 second pass: the model was exact and **deduced nothing**

**Measured, not argued: with the total given, the solver reached 0 of 9 slots.**

The corrected relations describe the feasible set perfectly — monotone, spread of one. And interval
propagation cannot *reach* it. With a total of 39 every slot's domain is `0..39`, each adjacent
inequality compares two intervals that already overlap, and the fixed point leaves all nine untouched.

⚠⚠ **A model can be exactly right and deduce nothing, and every test I wrote was blind to it.** They
asked whether a vector *satisfies* the relations. None of them called `solve()`. **Satisfaction tests
cannot establish solver behaviour** — that is the whole finding, and it is a new shape for this file:
not a wrong rule, not two places disagreeing, but a correct rule with no operational consequence and a
test suite that could not tell.

⚠️ **And the classification would have inverted the answer.** Every deduction reached through an
inequality is `BOUNDING`, and `arms.py` read bounding-PA as *reasoning* and everything else as *filler*.
So even had the intervals cornered a cell, the total-visible arm would have recorded reading-one-number-
and-dividing-by-nine as a **stall** — the exact opposite of the distinction the experiment exists to
draw.

**Both fixed together, because they are one question.** `Technique.LINEUP_ARITHMETIC` is a third
technique, ordered *first* as the cheapest move on the board, and `_lineup_moves()` does the arithmetic
directly: `divmod(total, 9)`, then a slot with one open row has that row. A slot with two open rows is
left as a **sum** rather than split, which is the hypothesis's own warning arriving in the solver.

The tests call `solve()` now, including the containment: **production passes no slots and deduces none
of them.**

### ⚠⚠ Open, and stated rather than worked around: the verifier cannot follow

The constraint is in the verifier's **relations**, so it will *reject* a board that breaks the cycle. It
has **no twin of the lineup step**, because its solver narrows intervals and intervals cannot reach the
cyclic distribution — the same wall, on the other side of §22.

**So a board erased leaning on this constraint would be refused by layer 3 as underivable.** The arms
run therefore measures stalls, blanks, coverage, technique and families, and **says nothing about
derivability**. That limit is printed in the run's own output rather than left for a reader to infer.

Closing it means an independent value-aware step in `boxscore_verify`, written from the rule rather than
from the generator's copy. **Not built, and not needed until the operator decides the constraint ships.**

## ⚠⚠ v27: what I implemented was monotonicity, not the batting order

**The constraint accepted a board no lineup can produce, and the experiment built on it was already
running.** Stopped mid-flight.

Eight adjacent inequalities `PA(n) >= PA(n+1)` are **monotonicity**. The batting order is a *cycle*: the
first slot has batted either as often as the last or **exactly one more**, never two. So
`6 5 4 4 4 4 4 4 4` satisfies every relation I emitted and is impossible in a game — for a total of 39
the cycle predicts `5 5 5 4 4 4 4 4 4`.

⚠️ **The docstrings described the rule and the code described a weaker one.** Both implementations, both
sets of comments, and the whole three-arm experiment were named for the cyclic rule. And every test
passed, because **none of them tried a monotone-but-impossible vector** — I tested a real cyclic
distribution, a flat one and a rise, which is the shape of the thing rather than its boundary.

⚠️ **And the two independent implementations agreed perfectly**, which is what makes this worth
recording. §22's duplication catches a mistake in *one* side. It cannot catch **the same misreading made
twice** — and the cross-implementation test I wrote to make them answerable to one rule was comparing
them to each other rather than to the rule. That is the residual risk §22 already names, arriving.

**The fix is one bound**: `PA(slot 1) - PA(slot 9) <= 1`. With it every slot holds one of two adjacent
values and there is at most one cut point, so the column sum then determines all nine. `Inequality` had
no constant — every bound in the system compared two quantities directly — so it has one now, and
`bounds.py` propagates it.

### The other three

**v27-P2-03 — an incomplete lineup was accepted and quietly weakened the model.** Only the *count* of
slot labels was checked, so `(1,2,3,4,5,6,7,8,8)` passed: nine labels, nine rows, eight distinct values,
**seven** relations instead of eight, and no error to read. That is the silent-underconstraint failure
the count check existed to prevent, one step further in. Both sides now require all nine positions;
duplicates stay legal because they are substitutions.

**v27-P2-02 — the expensive artifact could not pair a trial.** `Row` said *one direction, one seed, one
arm, one target* and stored neither the seed nor the offensive side. Three seeds run per direction, so
the ambiguity was guaranteed rather than unlucky, and two directions of one game were
indistinguishable. Caught **before** the run was spent, which is the only reason it cost nothing.

**v27-P3-04 — the decision summary still published the superseded 75.1%.** The detailed section had been
corrected to 83.4% and the summary had not, so the two contradicted each other in one file — at exactly
the line an operator reads when taking the decision.

## ⚠️⚠️ The batting order holds 99.9950% on the pool that ships — and the measurement was wrong twice first

**The claim:** the order is cyclic and cannot be skipped, so given the team's PA total the nine per-slot
values follow. 38 plate appearances is four turns of nine plus two, so slots 1 and 2 have 5 and the rest
have 4.

| population | directions | exceptions | |
|---|---|---|---|
| **the production pool** (gated) | 100,226 | **5** | **99.9950%** — the pool rule is decided from this |
| ungated, same rules otherwise | 371,802 | 35 | 99.9906% — structural evidence, not about what ships |

⚠️ **This is the outcome the instruction named in advance, and its verdict stands: a constraint true
99.995% of the time is not a constraint, it is a trap.** The solver would deduce a value that is wrong on
the exceptional board, and §22's guarantee would break where **no identity check could catch it** — the
board balances perfectly and is about a different game.

**The pool rule is therefore the answer, and it costs five directions out of 100,226.** Reject a direction
whose slot distribution does not match what its total predicts: one comparison against a function of a
single number.

### ⚠️⚠️ v26 found the measurement wrong five times across two passes

**Two of the five are the second pass, and one of those overturned a recorded conclusion** — the
clustering table above. Recorded together because the pattern is the point: **every one was a defect in
the instrument, none in the hypothesis**, and four of the five were invisible in an output that looked
entirely reasonable.

**v26-P2-01 — no zero-density gate.** The first run measured 371,802 directions: the ungated population,
while the decision is about the 100,226 the generator ships from. **That is the same defect fixed twice
in `footnote-multiplicity` hours earlier**, by the same hand, in a script written after the lesson was
recorded — *a research denominator and the generator have to mean the same thing.* Writing a rule down
is not applying it.

**v26-P2-02 — `offense_is_home` was labelled "batting last".** They are not the same fact: when the home
team leads after the top of the ninth **they do not bat at all**, and the visitors made the last plate
appearance. The reported split was the home/away split, which is near enough 50/50 to look like an
answer. **A name is not the thing** — the fifth instance of that class here. Retrosheet marks the
unplayed half `x` at the end of the home line score, so the fact was available and simply not asked for.

**v26-P3-03 — the prose and the predicate disagreed.** The docstring said "exactly one step down" while
`faults()` accepted zero. A total divisible by nine is whole turns and every slot is equal, so
`4 4 4 4 4 4 4 4 4` is the cleanest case and the wording called it a violation. **The code was right and
the sentence was wrong**, which is the harder direction to notice because the numbers looked correct.

### ⚠️⚠️ And correcting the second one exposed something nobody was looking for

Fixing "batted last" made it 16.8% of the pool instead of ~50%, which did not make sense — so it was
checked rather than accepted:

| | directions | batted last | **the offense won** |
|---|---|---|---|
| ungated | 371,802 | 49.2% | 50.4% |
| **the pool** | 100,226 | **16.8%** | **84.1%** |

**§5's zero-density gate selects the winning team's offense five times out of six.** A team that scores
more has fewer zeros, so the gate prefers it — and the winner is usually the side that did *not* bat
last, either a home team already ahead after the top of the ninth or a winning visitor.

⚠️ **Every board the generator ships is overwhelmingly a winning team's batting line.** That is a
property of the pool nobody chose and nothing recorded, and it is not obviously wrong — but it is a
systematic sameness in what the player meets, which §31 cares about. **Not a decision to take here.**
It was found by disbelieving a number that came out of a correction, which is the only reason it was
found at all.

### ⚠️⚠️ Where the exceptions are — and the first answer was read off a table that hid half of it

**I recorded "nowhere". That was wrong, and v26's second pass is why it is now known.**

`_report()` iterated the categories that *had* exceptions, so any category with **none** vanished from
the table entirely. All five production exceptions are non-extra-innings directions, so the honest line
is `True: 0/6,276` beside `False: 5/93,950`; what printed was the second alone — which reads as a
neutral partial split rather than as the one-sided result it is. **The absence of a reading is not a
reading of absence**, in the one table whose entire job is to say whether failures cluster.

**With every category printed, one dimension does cluster.** On the 35-exception ungated arm, which is
the better sample:

| | exceptions | directions | rate |
|---|---|---|---|
| before 1960 | 22 | 112,431 | **0.0196%** |
| 1960 onward | 13 | 259,371 | **0.0050%** |

**Roughly four times more common before 1960**, and monotone across the decades. Every other dimension
is genuinely flat: extra innings 0.01% either way, home offense 0.01% either way, and — on the
*corrected* definition — batted last 0.01% either way.

⚠️ **This strengthens the transcription-noise reading rather than weakening it.** A rule of baseball
would not fade as record-keeping improved; a scoring-error rate would. **But it is a gradient where I
said there was none**, and it was invisible until zero-count categories were printed.

**Still unresolved, and still the right call for a person:** the five have not been examined
individually, and the distinction that matters — a real batting-out-of-order call against a scoring
error — cannot be made from any distribution, however complete.

### The excluded populations

**Deduced files: 3 of 6,551 — five times the pool's rate.** A violation there confirms §32's exclusion
rather than refuting the hypothesis, which is why they are a separate arm.

⚠️ **The Negro Leagues arm is empty for a reason that is not §32.** All 1,872 `EVR` games are in
`retroGamesReg` and **not one has a `retroGameLogs` row**, so the game-log join removes them before the
source rule applies. Two exclusions, and the join is the stricter.

⚠️ **That arm was broken on its first run**, asking for a deduced game with an accepted source type — an
empty intersection, since deduced files carry `EDA`/`EDN`/`EDF`. The report said *the filters in this
script are wrong*: a broken arm describing itself as a broken script. It replaces the provenance rule
whole now and refuses to run if that rule has moved.

### What it would buy

⚠️ **Less than nine cells a board, for the hypothesis's own reason turned around.** The constraint
determines PA per **slot**; the board has a row per **player**. A slot held by one man all game has its
row determined by the team total; a slot shared by a starter and a substitute yields only their **sum**,
which constrains two cells without fixing either.

**83.4% of batting rows are alone in their slot** — 826,039 of 990,202 in the post-rule pool.

⚠️ **The earlier 75.1% was the ungated population**, and `_what_it_buys()` also measured the *pre*-rule
cohort while its heading claimed the post-rule one (v26-P3-05). The five rule-excluded directions are
removed now, and the exclusion is derived from the run rather than written down.

### ⚠⚠ And "determined outright" is the wrong thing to want

**The operator caught this and it changes what the measurement is for.** I read the 83.4% as the payoff:
the constraint determines those cells, so the board gets easier. **Determining cells is filler.** With
the team's PA total given, the player computes nine slots from one number — four turns and a remainder —
and types nine cells without thinking.

**With the total erased it works the other way.** Each slot bounds the next and the player has to chain,
and it bounds **in both directions**: knowing slots 3 and 6 puts 4 and 5 between them without fixing
either. That restricts without determining, which is what produces a stall. **So the rule is good and
what needs controlling is the total.**

### What is built, and what is still running

**The constraint is implemented twice**, as §22 requires — once in the generator and once in the
verifier, written from the rule rather than from each other. ⚠️ **Opt-in: without slots neither emits
anything**, so production is untouched and stays untouched until the operator decides. A default of one
row per slot would be wrong on every board carrying a substitution, and wrong silently.

**Three arms are running** on a stratified sample, one canonical walk filtered per arm, with the pool
rule applied: `off`, `on_total_given`, `on_total_erasable`. **The comparison that answers the question is
`off` against `on_total_erasable`**; the middle arm exists so the choice about the total is visible
rather than assumed. The instrument is `discovery/batting-order/arms.py`.

## v25 — verified, none rejected. **Both closed.**

### v25-P2-01 — a malformed saved session could take the board away. **Real, and worse than reported.**

`load()` accepted any object; `restore()` assumed a shape. Reproduced against the running board, and it
found a third case the review did not name:

| saved | what happened |
|---|---|
| `{"entries":{},"hinted":7}` | **`TypeError` before `draw()`** — the shell cleared `#app` and rethrew, so **no board at all** until site data was cleared |
| `{"entries":"nope"}` | restored quietly; `Object.entries` on a string yields index pairs that match no cell |
| `{"entries":{"batting[0].hits":"five"}}` | **the string was installed as a cell's value**, past the whole-number rule `enter()` enforces, into a board that would draw it |

⚠️ **The two silent ones are the worse pair by this project's own standard.** A crash is noticed; a
poisoned board is not, and it lasts.

⚠️⚠️ **And the claim that failed was mine, in a comment I had written an hour earlier.** `store.load()`
promised that "malformed storage reads as absent, never as an error and never as a partial session" —
a statement about the *session*, made by a function that only knows about *bytes*. **The claim was
broader than the check**, which is the shape this project keeps paying for. The comment now promises
what it can: parseability.

**`isSession()` lives in `game.js`**, because it is that type's shape and a key-value store should not
know what a session looks like. Two boundaries, one rule.

⚠️ **And `restore()` was not atomic.** It cleared its three maps and *then* repopulated, so a shape that
threw part-way left the game **emptier than it found it** — the player's work gone and no session to put
back. It refuses before clearing now, and refuses rather than throwing, because §23 makes the store
optional and no caller should have to wrap a restore to keep the board alive.

Twelve malformed shapes are vectors; reverting the guard turns fourteen tests red.

### v25-P3-01 — the ledger still described the state before the work. **Fixed.**

*What is actually left* said `snapshot()` and `restore()` were called by nothing, that there was no
`localStorage` anywhere and no clock wired. All true when written, all false by the time it was read.

⚠️ **The useful half of the finding is not that it was stale.** Other names in the same item —
`finish()`, `record()`, the reveal — genuinely remain unwired, so **one unchecked sentence was covering
a finished seam and an unbuilt consumer at once.** A ledger is only worth keeping when those two are not
the same line. Split by actual status.

## v24 — no findings.

A clean pass over v23's fixes: the accessible name is derived from the same rendered value as the
visible cell on every `paint()`, and the thirds rule lives in the importable `applyKey()` path with the
disabled controls mirroring it.

⚠️ **It records a residual risk worth keeping in view.** The DOM tests read attributes and rendered
values; **no real screen reader has ever been pointed at this board.** That is a validation gap rather
than a defect, and it belongs with the fifty-board hand-solve as a thing only a person can close. Both
are the same shape: an instrument agreeing with itself is not the same as the experience being right.

⚠️ **This review was committed without being read** — it arrived untracked and went in with `git add -A`
during the persistence commit. Recorded because a review that nobody read is indistinguishable from one
that found nothing, and only the file's own contents tell them apart.

## v23 — verified, none rejected. **Both closed.**

Both reproduced in the running board before anything was changed, in one pass.

### v23-P2-02 — a keypad control did something other than what was printed on it. **The one that corrupts data.**

The `key.thirds` branch ran **before** the innings flag it depends on, so on any plain-integer cell it
computed `floor(current / 3) * 3 + thirds` and wrote the result as a whole number. **`1⁄3` on an empty
hits cell entered `1`.**

⚠️ **The damage is larger than the keystroke** because §2 deliberately withholds correctness feedback:
the board says nothing until *done*, so an accidental value travels into every deduction after it. When
the guard is reverted the test names **21 affected cells** — batting, pitching and both totals rows.

**Closed in both layers: the handler refuses and the pad disables the keys.** Both, because a control
prevented only by being greyed out works again the moment anything reaches it another way — a keyboard,
a test, a later interface.

### v23-P2-01 — the accessible name never reported the value. **Real.**

An explicit `aria-label` **replaces** the element's text as its accessible name. It was written once at
render with the row and column, and `paint()` never touched it — so a screen reader read `SS, H` whether
the cell held nothing, a 1 or a 17. `aria-pressed` says which cell is selected and nothing about what is
in it.

⚠️ **On a board whose entire interaction is re-reading your own earlier entries, that is the one thing
the accessible path could not do.** The sighted path could.

Recomputed in the same redraw as the visual state, because two paths computing one fact is how they
drift and this pair had already drifted. ⚠️ **And the opening state was the one that said least**:
`paint()` ran before the base label existed, so the first cell a screen-reader user meets announced bare
context. Fixed by ordering, and asserted over every blank rather than the one that was checked by hand.

### ⚠️⚠️ What both findings share, and both of the operator's defects too

**A rule written in `main.js` is unguarded by construction.** The suite does not import it — it boots the
application — so every rule that lived there was untestable in principle rather than untested by
oversight:

| rule | what it cost |
|---|---|
| the thirds branch ahead of its flag | `1⁄3` wrote `1` into any cell |
| the digit cap, written twice | only the grid copy had one, so `IP` took `8444` |

Both were found by a person pressing keys, which is the check this project keeps rediscovering. The
whole input rule is `applyKey()` in `board.js` now, and the shell keeps what is genuinely its own:
which cell is selected, and when to repaint.

⚠️ **I found this hole while trying to mutation-check my own fix** — the guard was in `main.js`, so
reverting it broke nothing and the tests I had written covered the predicate and the pad rather than the
refusal. The mutation check is what found it, not the writing of it.

## v22 — verified, none rejected. **All three closed.**

### v22-P2-01 — the constructor wrote what its own reader refused. **Real, and reproduced.**

Schema 4 had the two board profiles at both JSON readers and **none at the constructor.** Built a
package with one null answer cell: **accepted, serialised with the null, and refused by
`Package.from_json` on its own output.**

⚠️ **A format that cannot read back what it writes is not a format**, and the asymmetry is invisible
to anyone who only ever round-trips valid data. A `str` passed as `solution` was accepted too and died
in `as_json()` with an `AttributeError` — an uncontrolled failure three steps from its cause.

**Fixed with `check_profile()`, one function called from `Board.from_json` and `Package.__post_init__`.**
It takes `object` rather than `Board` deliberately: a frozen dataclass does not check its own field
types, so **the `isinstance` mypy calls unreachable is the one that caught the string.** A type is a
promise; that is the check.

⚠⚠ **My reason for leaving the constructor lax was a justification scoped to a test's convenience.**
I argued it kept a verifier layer testable. What it actually preserved was the exact asymmetry v21
required removing — and `todo.md` recorded the constructor fix as closed while it was not. The layer
stayed testable anyway, on a complete board whose line score disagrees with its source, which is a more
realistic malformation than the one it replaced.

**Two verifier faults then became unreachable and moved rather than vanished**: an erased footnote total
and an erased left-on-base, both refused by the format now. Named where they stood, because **deleting a
fault and enforcing it earlier look identical in a diff.** The comment beside one still asserted that
per-batter footnote cells are erasable — true for about a week, three decisions ago.

### v22-P2-02 — the repaired instrument still measured a different cohort. **Real.**

⚠⚠ **Second repair to the same instrument, and the first one solved most of the problem.** It took
`SHAPE_CTE` and the zero-density gate from the loader and left behind the **game-log join**, the
**`VisLineScore` requirement** and the **season window** — so it counted directions `load()` cannot
return while calling the number the production pool.

**Sharing part of a cohort is worse than sharing none**, because the partial version looks like the
whole one. This is CLAUDE.md's own rule arriving inside my repair of the defect it describes: *a fix
that solves most of a problem reads like one that solves all of it.*

`eligibility()` is that entire `FROM`/`JOIN`/`WHERE` now, one string, used by the loader and the
instrument. **The loader's SQL is byte-identical** — compared against `HEAD`'s rendered block rather
than asserted, after the operator asked what SQL was being changed in the forge. The answer was none,
and that had to be shown rather than claimed.

**The re-measurement moved the absolute counts and not the ratio:** 4,019 of 100,226 against 4,040 of
100,742, still **4.01%**, decades identical to two decimals. ⚠️ **That is knowable only afterwards.** A
denominator describing a cohort you did not measure is wrong whether or not the quotient survives.

### v22-P3-01 — the instrument ran its aggregate twice. **Fixed.**

Once for the row, once more on a fresh cursor only to read `cursor.description`.

## ⚠⚠ Two interface defects the operator found by playing

Both were invisible to every test in the suite, for different reasons worth separating.

### The highlight did not paint on a filled cell

`.cell.blank.filled` is three classes and `.cell.peer` is two, so **the ground outranked the state
whatever the source order.** The player saw the highlight on every given cell and every empty one, and
nothing on the cells they had actually written in — which is where the eye is.

⚠️ **No assertion about classes could have caught it: the classes were all correct.** `paint()` set
`filled`, `peer` and `selected` exactly as intended. Only a computed style can see a cascade, so the
test page now loads the real stylesheets and two tests read backgrounds. Mutation-checked by restoring
the broken specificity.

**Ground says what kind of cell this is; state says where you are now.** A state that cannot paint over
ground is not a state.

### A cell took four digits

The growth rule was written twice and **only the grid copy had a cap**, so `IP` accepted `8444` — four
digits in a cell 44px wide. `grow()` is one function in `board.js` now, which also makes it testable: it
lived in `main.js`, which the suite does not import.

⚠️ **And the leading-zero rule was right by coercion rather than by rule.** `Number("05")` is 5, so
the old code behaved correctly and said nothing about why. A reader could not tell it was intended, and
the next person to reach for `parseInt` would have lost it with nothing going red. It is a line and a
test now, plus one that walks all thousand reachable pairs — **the cap that held for the cases someone
thought of is the cap that failed here.**

**IP is the exception and keeps four characters:** two whole digits, a point, one decimal. The whole
part is capped by `grow()` and the thirds replace rather than compound, so the fractional position
cannot grow.

⚠️ **A method note.** My first attempt to test this pressed `⅓` while the key carries `1⁄3` — a
different codepoint. Nothing was pressed and the log came back clean. **A test that tests nothing reads
exactly like one that passes**, and only the unchanged cell text gave it away.

## v21 — verified, none rejected. **Both closed.**

### v21-P1-01 — schema 4 did not require the solution it needs. **Real, and reproduced.**

Three shapes, all confirmed in the browser before anything was changed:

| document | Python | browser |
|---|---|---|
| no `solution` | builds, signs, serialises, re-parses | **refuses at boot** |
| `left_on_base` null | accepts | refuses |
| a null answer under a visible blank | accepts | **accepts** |

The third is the one the player meets. `batting[0].at_bats` came back **blank and counted as correct**,
and entering `0` was **not** correct — a cell simultaneously unanswerable and done. Fill the rest and the
board reports solved with a hole in it.

⚠️ **The first two are the producer/consumer split schema 4 was cut to remove, inside schema 4.** That
is worth more than the fix: cutting a version does not by itself make the two sides agree, and the
document arguing for the cut carried an optional field on one side and a required one on the other.

**Fixed as two board profiles**, in `__post_init__`, in `from_json`, and in the browser reader: a puzzle
may be blank in the batting and pitching grids and their totals; an answer board may not be blank
anywhere; the footnote line and LOB are given in both. Four shared conformance vectors, all five
mutations verified refused in the browser with the real package still accepted.

⚠️ **Tightened in place rather than cut as version 5, and the reason was re-derived rather than
carried.** The test used: **does the change alter the status of any artifact that exists?** Twelve
schema-4 packages across two generations, accepted before and after. Nothing changes meaning, so
`schema: 4` does not come to mean two things. Had one file flipped it would have been version 5.

**What the type change then surfaced.** mypy found **seven branches in the verifier** that existed for
the missing-solution case and could no longer be reached. Each was read before deletion, because a dead
branch can carry a live rule:

- `certify.py` had `package.solution or package.puzzle` in two places — **a fallback onto a board full
  of blanks.** Plausibility asks whether this could have been a game, and half the cells being unknown
  is not an answer; the fallback made the check weakest exactly when it was most needed.
- The LOB comparison against the game log was guarded by `is not None`, so it **only ran when a value
  happened to be there**. It always runs now.
- `_structure_faults`' erased-LOB fault moved to the parse boundary. Written down, because deleting a
  fault and enforcing it earlier look identical in a diff.
- `to_board` now **refuses** to erase LOB instead of obliging. §6 never erases it and `erasable()` never
  offers it, so the request could only come from a test — and the adapter built a board both readers
  reject at their boundary, three layers from the cause.

And the module docstring said `published()` strips the solution while `published()`'s own docstring
explained why it no longer does — two places in one file, contradicting each other, with the field
renamed as well.

### v21-P2-01 — my instrument reported a gated pool without applying the gate. **Real, and the numbers were wrong.**

⚠⚠ **The docstring said it plainly and the query did not do it.** It read "counted against the pool the
board actually draws from — the zero-density gate, the roster caps and the provenance rule", printed
`gate applied downstream (30%)`, and imported `ZERO_DENSITY_GATE` **only to put in a label.** Its `shape`
CTE computed roster sizes and none of the twelve zero counts the gate divides by.

Second defect in the same report: `total_many` summed the per-term counts, so a row carrying two
different repeated terms was counted twice.

**Re-measured with the loader's own cohort. The corrected figures are worse, not better:**

| | published | measured |
|---|---|---|
| directions affected | 2.73% | **4.01%** |
| worst decade | 5.25% (1910s) | **8.31% (1920s)**, 8.02% (1910s) |
| best decade | 1.52% | 2.02% |

The gate removes low-scoring games, and less offence means fewer sacrifices — so the defect is *more*
common in the pool that ships than in the database at large. **The decision is unchanged and better
supported.** Sixteen copied figures replaced across six files, with a sweep asserting none survives.

**Fixed at the cause, not with another assertion.** `SHAPE_CTE` and `zero_density_clause()` are hoisted
out of the loader, and the instrument takes both. There is one cohort definition now, so a measurement
and the generator cannot describe different pools again.

## ⚠⚠ The reveal read the wrong table, and the wrong column of the right one

**Found by the operator asking whether `dbo.regPeople` was used anywhere.** It was, in two places, and
both were wrong in a way nothing could detect.

### The table

`regPeople` does not belong to the Retrosheet collection — it is a different dataset that happens to
carry a `key_retro` column. Matched against the players the pool actually contains:

| table | matched | of |
|---|---|---|
| `dbo.regPeople` | 19,703 | 20,019 |
| **`dbo.retroMaster`** | **20,019** | 20,019 |

⚠️ **A join that resolves 98.4% looks exactly like one that resolves 100%.** The 316 it missed fell
through the `LEFT JOIN`, hit `f"{first} {last}".strip() or "Unknown"` with both fields empty, and were
published as `Unknown` — **losing the surname as well**. The placeholder-name check in `plausibility`
could not see it, because `Unknown` is not blank. Nothing rejected a board over it.

### The column

`retroMaster.first` is the **full legal given name** — `Henry Louis` for Hank Aaron, `John Franklin` for
Home Run Baker. `nickname` is what the man was called. §7 says the reveal *is* the real boxscore, so a
name built from `first` prints something no boxscore, no broadcast and no player ever used.

Read off the corrected loader rather than assumed: `Home Run Baker`, `Bunny Brief`, `Stuffy McInnis`,
`Chief Bender`, `Tris Speaker`, `Tiny Osborne`.

### A surname alone is the answer, not a failure

113 players in the pool have neither a nickname nor a given name on record. Their identifiers carry `u`
in the fifth position — Retrosheet's mark for *first name unknown* — and each appears in two to five
rows: one-game men from the early era. `Pitts` is what is known, and `Pitts` is what prints. The old
code already got this case right; what it lost was the other one.

⚠️ **An unknown name is now left empty rather than filled with a placeholder**, so the
plausibility check that rejects a blank reveal name is the thing that fires. A fallback string would
satisfy that check while publishing a fact nobody has.

### And the composition was in two places with two rules

`write_reference_puzzles.py` joined the `(first, last)` pair with `.strip() or "Unknown"`;
`board-prototype/build.py` joined the same pair with neither. **One rule, two places, disagreeing
exactly on the players with no given name.** `full_name()` lives in the loader now and nothing
downstream reassembles it — a test asserts no consumer composes its own.

### The guard forbade describing the defect it guards against

Its first version asserted `"regPeople" not in source` and fired on the docstring explaining why the
table was replaced. It forbids `dbo.regPeople` now — the join, not the word. Small, and the same shape
as every over-broad check recorded here: a rule that cannot distinguish its subject from a mention of
its subject.

## ⚠⚠ The footnote line could not say *two*, and 4.01% of the pool was unsolvable

**Found by a person reading a printed page**, which is the only thing that has ever found this class of
defect here. The line printed `SH: 2` — a *slot reference* that reads as a count. `9a` and `1, 9b`
escaped the ambiguity only because a letter or a comma gave them away, so **the format was unambiguous
by accident rather than by design**.

And the count was absent entirely. `SH: 2` said *a sacrifice in slot 2* and had no way to say *two
sacrifices in slot 2*.

### Measured before deciding

| term | rows with more than one | of the rows carrying it | max |
|---|---|---|---|
| sacrifice_hits | 2,820 | 5.62% | 4 |
| hit_by_pitch | 610 | 2.04% | 3 |
| sacrifice_flies | 700 | 1.99% | 3 |
| catcher_interference | 5 | 0.88% | 2 |

⚠️ **The denominator that decides is directions, not rows.** One unreadable row breaks the whole board,
so a per-row rate understates the damage by the number of rows on a board — 0.27% of rows reads like a
rounding error. **4,019 of 100,226 admissible directions carry at least one: 4.01%.** It clusters where
the pool is thinnest: **8.31% in the 1920s and 8.02% in the 1910s** against 2.02% in the 2020s, because the sacrifice was a
dead-ball-era habit.

Those boards cannot be solved. `PA = AB + BB + HBP + SF + SH + CI` has no other route to the value, and
**every total still balances**, which is why none of the four layers saw it — the arithmetic was right
and only the presentation was lossy.

### The format

`SH: 1 #2` / `SH: 2 #9a` / `SH: 1 #2, 1 #9b` — count, then `#`, then the slot. **The count prints even
when it is one**, because a format showing it only sometimes is ambiguous again: the same trap as the
slot letter that appears only when a slot is shared.

### ⚠️ And the two renderers had drifted in three ways, not one

The operator retracted a claim that they differed, having extracted the PDF and found it consistent. The
retraction over-corrected: **reading one renderer's output cannot show a divergence between two.** They
differed in the count, in the `#`, and in whether `LOB` came first or last. A board with `SH` total 2
across slots 2 and 9b produced `SH: 2, 9b` from the PDF and `SH: 2 #2, #9b` from the phone.

§33 forbids the two sharing a function, so they share **`serve/tests/footnote-line-vectors.json`** — six
canonical strings, run by both suites, the same arrangement as the package vectors. Plus a **parity
rule**: every printed term carries a count *and* at least one slot reference, which fails on a term
rendered with one half and not the other, including shapes the vectors do not contain. Mutation-checked
by removing the count: 4 parity failures beyond the 4 string comparisons, so it is not riding on them.

**`board.footnote_repeat` (`×`) was deleted an hour after being added.** The old form put the count after
the slot as a multiplier; there is no multiplier now. A catalogue key nothing asks for is a translation
obligation nobody can discharge.

### ⚠⚠ A guard for the report that dies on its own decoration — fourth occurrence

`print("⚠ ...")` raises `UnicodeEncodeError` on a redirected Windows stream, **after the compute and
before the numbers reach anyone.** The first instance cost a run. The second was caught by review in a
file whose own comment thirty lines above explained the hazard. The third was a new script written an
hour after that correction. **The fourth was the diagnostic written to find the third**, which died the
same way while listing the offending characters.

A comment was not stopping it. `forge/tests/test_reports_survive_a_redirected_stream.py` walks the
runnable trees and fails on a `print` literal cp1252 cannot encode — reaching inside f-strings, where
most report lines live, and **ignoring docstrings and comments**, which carry these characters
everywhere and never reach a stream. It found **8 more scripts** with the same latent failure, none of
which anyone knew about.

⚠️ **And silencing its lint finding re-created the noqa-inside-a-string defect.** `query = f"""  # noqa:
S608` puts the comment *inside the SQL*. That is the defect that already cost this project an hour of
compute, repeated by the same hand in the same session. Moved to the closing line and **verified by
running the script**, not by reading the diff.

## The five-board pack came back — built the production way, at ≤6 pitchers

72 gated directions, 104 board-target pairs, erased by `erase(target_stalls=...)` rather than by
searching for a maximum. **That change matters more than the numbers below:** every earlier version of
this pack kept whichever greedy walk stalled most, which is not how any published board is made.

| board | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| target stalls | 5 | 5 | 8 | 5 | 8 |
| blanks | 32 | 30 | 40 | 31 | 38 |
| pitchers | 4 | 4 | **6** | 3 | 3 |
| batters | 9 | 10 | 12 | 9 | 11 |

Composition and the six-pitcher quota asserted in `audit()`, order shuffled, stall count off the page.

### ⚠️ The twelve-blank worry does not arise

**Boards built the production way carry 30 to 40 blanks, not 12.** Twelve came from the maximising
search, and the maximising search is not a generator. The question was worth asking and it is answered
by the change of method rather than by the cap.

### ✅ ~~Coverage at 8 stalls does not match the cap measurement, and the difference is not explained~~

~~The cap comparison reported **33%**. Here 36 of 72 directions reach 8 stalls — **50%** of the sample,
56% of those reaching any target. Same gate, same caps.~~

**Closed on 2026-08-21. The premise was false in both halves: not the same gate, and not the same
caps.** The two instruments were measuring two different populations, so there was never a
disagreement to explain — there was a comparison nobody had checked the terms of.

| | cap comparison — **33%** | hand-solve pack — **50%** |
|---|---|---|
| instrument | `discovery/pitcher-cap/measure_pitching.py` | `discovery/hand-solve/build_pack.py` |
| gate | `load(..., gated=True)` with **no `gate=`** → the default, **0.30** | `gate=GATE` where `GATE = 0.25` |
| roster | `min_pitchers=count, max_pitchers=count` — **exactly** *N* | the ordinary caps — **at most** |
| sample | 5 per decade | 8 per decade |

⚠️ **The gate difference is invisible at the call site, which is why "same gate" was written down and
believed.** One instrument states its gate and the other omits the argument, and an omitted argument
looks like *no gate* rather than like *the default gate* — `load`'s signature is
`gate: float = ZERO_DENSITY_GATE`. Nothing in either script is wrong; the two lines simply do not say
what they have in common, and the comparison was made from the outside.

⚠️ **The sign is consistent with the gate, and that is not the same as being explained by it.** A
stricter gate removes the zero-heavy boards, which are the ones that compress least, so the 0.25 arm
draws a livelier population and should reach 8 stalls *more* often — 50% against 33%. But the
exactly-*N* roster is a second uncontrolled variable moving at the same time, and **no run separates
them.** This is the confound `CLAUDE.md` describes: the report reads exactly as clean either way, and
looking harder at the output cannot decide it.

**What this changes:** the entry stops being an unexplained disagreement between two correct
instruments — the shape this project treats as a defect — and becomes two figures about two
populations, each interpretable on its own. **Neither number is a measurement of the other's
quantity**, and any future comparison of the two has to re-run one of them under the other's terms.

#### Group I — the key that cannot be rotated was being handed to every process on the laptop

`P3-29` `docs/signing-keys.md` recommended persisting `BOXSCORE_SIGNING_KEY` with
`SetEnvironmentVariable(..., "User")`, *so a publish never fails for a forgotten shell*. A User-scope
variable is inherited by **every process the account runs** — every `npm install` postinstall, every
pip build hook, every script from every sibling project on a machine that holds several. One
compromised dependency reads `os.environ` and the holder can sign inventory `serve` accepts.

⚠️⚠️ **Checked rather than assumed, and it is live on this machine: User scope holds the key, 64
characters.** Machine scope does not. So this is an exposure that exists, not a recommendation that
might be followed.

**And it is the one secret here that cannot be rotated cheaply** — rotating invalidates every
signature ever issued, so every package and every manifest has to be reissued. What the permanent
variable bought was avoiding a loud fail-closed error the writer raises by design: **a permanent
exposure to buy nothing.**

**The writer reads `~/.boxscorepuzzle-signing-key` at publish time now**, so no export is needed at
all and the key is in one process for the length of one publish. An exported variable still wins,
because that is a deliberate instruction. ⚠️ `--ephemeral` weighs **only** the variable: an export says
*publish for real*, a file in the home directory says only *this is where the key is kept*, and
weighing the file would make `--ephemeral` impossible on the one machine that has a key.

**Verified with the variable cleared from the process**: the writer acquires the key, it matches the
pin `serve` holds, and the destination is production. So removing the variable costs nothing.

⬜ **The operator has to clear the variable; nothing here does it.** The command is in
`docs/signing-keys.md`. ⚠️ And clearing it does not un-expose a key that was already exposed — if it
sat in User scope on a machine that has run untrusted install hooks, the conservative reading is
rotation rather than deletion. That is a judgement about this machine's history.

⚠️ **Two existing tests were reading the laptop instead of the code, and only one of them failed.**
`test_neither_is_an_error` passed `key=None` and, with a real key file present, found the production
key and did not raise. Its helper now redirects `KEY_FILE`. The second, `test_ephemeral_with_a_
configured_key_is_refused`, asserted the **source text** `"if ephemeral and material:"` — so renaming a
local turned it red while the behaviour was unchanged, and it would have stayed green if the condition
had been kept and the refusal deleted. Rewritten to exercise the refusal.

#### Group H — the rule was written and then not applied to the place it was written from

`P3-05` three frozen result containers handed out a **mutable `dict`** — `frozen=True` freezes the
binding, not the value. `Puzzle` holds `given` *and* the `Solution` proving that board is derivable;
mutating the mapping leaves the pair describing two different boards. They are `MappingProxyType` over
a **copy** now, and the copy is the point: a proxy over a dict the caller still holds is the same
defect with one step added. ⚠️ The first version of the `Solution` test **could not fail** — it went
through `solve()`, which builds its own dict, so removing the copy left it green while the other two
went red. Rewritten to construct directly. Cost measured rather than assumed: 1.25 ms per solve
against 1.30 ms with the freeze switched off — **inside the noise**.

`P3-08` `refs()` stood in **seven files byte for byte**, and its own docstring records that it once
invented a tenth batting-order slot, which no lineup has. The key pair stood in four. Both live in
`tests/verify/helpers.py` now. ⚠️ Imported rather than made fixtures: `refs()` has 42 call sites and a
fixture would mean editing 42 signatures to gain nothing the import gives.

⚠️⚠️ **And the same item carried two hand-written rebuilders of `Board`** — `conftest.swapped()` and an
identical `test_layers.replacing()`, each naming all eight fields. That is precisely the defect
`test_rebuilders_carry_every_field.py` exists for, whose docstring records `offense_is_home` being
added and **both** `Package` rebuilders silently dropping it. **The guard was looking only at
`boxscore_package`**, so two fresh instances sat in the test tree the rule is enforced from — *a rule
applied outward does not automatically apply inward*. One rebuilder now, using `dataclasses.replace`,
and the sweep reaches it: reintroducing a hand list with one field missing turns it red.

`P3-37` **`slot_references` produced a published, schema-validated field from inside a discovery
instrument**, imported by the production writer — the exact pattern `publish.py`'s own docstring
records as fixed ("a research experiment supplying the conversion for the artefact that ships"). It
is in `boxscore_forge/publish.py` now, under `mypy --strict` and outside the ratcheted tree. ⚠️ Five
call sites across `discovery/` and the test tree were repointed, and **the rewrite was caught by
running rather than by reading**: ruff removed the now-unused re-export and three suites failed to
import.

⬜ **The pool loader itself is not moved and that is deliberate.** It carries the SQL, the connection
and the era windows; promoting it is the inventory pipeline's work rather than a rename.

### ⚠️⚠️ One game, one id, two different boards — §21's first idempotence rule does not hold today

**Found by regenerating the six on 2026-08-21.** `1dc57470b44caded` appears in both generations: same
game, same direction, same `puzzle_id` — and a **different puzzle**. It was a 3-stall board with 30
blanks; it is now a 2-stall board with 21.

Nothing is broken in the sense of a failing check. `puzzle_id` derives from the game and the offensive
club (§21), which is exactly what makes it stable — but **the board is not determined by the id**. The
writer asks each candidate for the highest stall target not already claimed by the batch, so *which*
board a package holds depends on **what else was in the batch**, and the seed is shared across the run.

⚠️ **`CLAUDE.md` §3 states the rule this breaks:** *the same Retrosheet game always yields the same
puzzle with the same ID.* Half of that holds. The id is idempotent; the puzzle is not.

**For reference data this costs nothing** — the six exist so `serve` has something real to build
against. **For inventory it is the shape §21's fourth rule exists to prevent:** a played date can never
change, and a regeneration that renames nothing while silently rewriting the board is worse than one
that produces a new id, because nothing downstream can notice. A player's stored progress, their C7
event record and the shared grid all hang off an id that no longer means one board.

**Not fixed here, and it is not a writer fix.** The candidate ordering and the target claiming are
batch-level decisions; making the board a function of the game alone means the *generator* takes the
target from the game rather than from what the batch has left. **That is the calendar's problem and it
inherits it at construction**, alongside the one-game-one-puzzle rule it already has to carry.

⬜ **Decide before the calendar is built, not after inventory exists.**

### ⚠️ The client was judged against a pool it will not ship — closed by regenerating

**2026-08-21.** The consequence recorded under group G's `P3-36` is closed. The six were redrawn at the
decided gate and the difference is not cosmetic: **median zero density 21% → 29%, five of six new
boards above the old set's maximum**, median blanks 30 → 37, and the roster reaching **12 batters**
against 10 before. The stall targets spread from 1–10 to 2–12, and one board depends on the batting
order — the first published board to use the fifth family.

**Looked at, not only measured.** Every board photographed at 375px: no horizontal overflow, pinned
header and totals intact, the footnote line and pitching section reached by scrolling as designed. The
twelve-batter board renders without crowding. ⚠️ The numeric check and the pictures were both taken
because `CLAUDE.md` records a case where the numbers said *fine* and the sheet was unreadable.

⚠️ **The regeneration wrote 0 of 6 on its first attempt, from a defect introduced in this same review
cycle.** `check_no_leaking_metadata` (v36-P2-10) was registered on the publication gate; `build()` was
handing that gate the **working** package, which carries `game_id` deliberately and never ships. Every
candidate was refused. `canonical_bytes` had already settled which object is the package of record —
the signature is computed over `published()` — so the writer was disagreeing with its own signer.
Fixed, and `forge/tests/test_the_writer_passes_its_own_gate.py` now calls the writer's own `build()`
without a database. **The gate's two directions were already tested; the call site was not**, and the
existing fixture builds a package it calls *"the way production builds it"* with no metadata at all.

### The stall ceiling, re-run at the decided gate — **6, against a recorded 5**

**2026-08-21.** `discovery/board-configurations/measure.py` at `ZERO_DENSITY_GATE`, 48 gated
directions, four per decade across twelve decades, 432 measured ceilings.

| | p50 | p90 | max | reach five or more |
|---|---|---|---|---|
| **the live board** (footnotes given, §6) | **6** | 10 | 12 | **67%** |

`MEDIAN_STALL_CEILING` is recorded as **5**, *"unchanged by the pitcher cap change"*. At the decided
gate the median board reaches **6**.

⚠️ **Not changed in `boxscore_domain`, and the reason is the same one that applies to the coverage
run.** A looser gate admits *more* zero-heavy boards, which compress least, so the median should have
moved **down** if the gate were the cause. It moved up. **One run at one gate does not establish what
moved it**, and `STALL_TARGETS` is already marked `PROVISIONAL` pending the hand-solve pack — which is
the thing that decides whether the stall scale corresponds to felt difficulty at all. Changing a
decided constant on a figure whose cause is unidentified would be inventing a parameter that shapes
the product.

**Both re-runs agree with each other on the shape**: 67% of boards reach a ceiling of five or more
here, and 71% can be erased to a five-stall target in the coverage run. Two instruments, two
definitions, one answer — **the pool is not thin in the middle.**

### ⚠️⚠️ And the instrument still offers a deleted option as a live choice

Its comparison table prints three rows — `baseline`, `footnotes`, `footnotes+lob` — with the footnote
arms reporting a median of **16** stalls against the baseline's 6. **Those two configurations were
decided against, and their production machinery was deleted rather than disabled.** `erasable_for()`
is where it survives: `erasable()` returns no footnote cell, and that function adds them back.

**Their numbers are the zero-counting ones.** With `HBP`, `SF`, `SH` and `CI` all zero for a batter the
row identity is `PA = AB + BB`, so an erased term asks the solver to deduce a value that exists only
because the thing did not happen — **96% of the pool's footnote terms are zero.** So `16 against 6` is
not a board ten stalls harder; it is a board with ten more zeros to type, and the pool run that settled
this found coverage identical at every target with the cells open and given.

⚠️ **The hazard is that the table reads as a live comparison.** Anyone running this instrument today
sees the corrected error restated as a current result, in the format of a decision aid. The two arms
are **labelled in the docstring and in the printed table** now — the header says which single row is
real — and nothing may draw a conclusion from them.

⚠️ **And labelling them broke the build, which is the fourth instance of a rule this project keeps
re-breaking.** The header line went in as `print("  ⚠ ONLY \`baseline\` ...")`, and a redirected
stream on Windows is cp1252 — `UnicodeEncodeError` **after the compute, before the numbers reach
anyone**. `test_reports_survive_a_redirected_stream.py` caught it on the pre-push hook, which is what
that guard exists for and the reason it stopped being a comment. Plain text now.

⬜ **Whether the two arms are deleted is an operator decision.** Keeping them lets the recorded figures
be reproduced, which is the argument that kept every other superseded instrument intact; deleting them
is what `CLAUDE.md` says was done everywhere else for this particular option.

### ⚠️ Coverage per stall target, re-run at the decided gate — and the move is **not** the gate

**2026-08-21.** `discovery/stall-targeted/measure.py` at `ZERO_DENSITY_GATE`, 48 gated directions, four
per decade across twelve decades, footnotes given, caps ≤13/≤6.

| stalls | boards | **of pool** | blanks p50 | p10–p90 | chain | trivial |
|---|---|---|---|---|---|---|
| 5 | 68 | **71%** | 31 | 28–36 | 17 | 14% |
| 6 | 58 | 60% | 33 | 30–37 | 19 | 12% |
| 7 | 49 | 51% | 35 | 31–40 | 21 | 11% |
| 8 | 39 | **41%** | 36 | 33–41 | 24 | 10% |
| 9 | 29 | 30% | 37 | 34–42 | 26 | 9% |
| 10 | 19 | 20% | 39 | 37–45 | 29 | 7% |
| 11 | 8 | 8% | 40 | 38–46 | 32 | 7% |
| 12 | 0 | **0%** | — | — | — | — |

**Against what was recorded:** `write_reference_puzzles.py` says *"on the corrected scale only **54%**
of boards reach five stalls and **21%** reach eight"*, and `CLAUDE.md` records coverage at eight stalls
as **33%** at the ≤6 pitcher cap. The new run says **71%** and **41%**.

⚠️⚠️ **The direction contradicts the gate hypothesis, so the gate is not the explanation.** 0.30 is
*looser* than 0.25: it admits more zero-heavy boards, which are the ones that compress least, so
coverage should have gone **down**. It went up at every target. **Whatever moved these numbers, it is
not the gate**, and this run does not establish what did — the caps, the sample and the scale have all
changed at least once since those figures were taken, and no run isolates them.

**Recorded as a new measurement rather than as a correction of the old ones.** Both are visible, the
old ones keep their instruments and their conditions, and **the difference is stated as unexplained
rather than attributed.** A confound has no signature in the output, so reading harder cannot decide
it; only a run that varies one thing can.

⬜ **What this does decide, and it is the thing the re-run was for:** at the decided gate the pool is
**not thin at the top** — 41% of boards reach eight stalls and 8% reach eleven — and **nothing reaches
twelve.** A ladder with a rung above eleven has no inventory behind it.

⚠️ **One thing found by reading the output rather than the numbers.** The report's own header said
*"footnotes erasable"*. It has been wrong since the zero-fill correction — `erasable()` returns the
grid and no footnote cell — and it is worse in a report than in a docstring: a reader would conclude
these figures are on the superseded scale that counted the solver deducing zeros, and discount them.
**It nearly worked on me while re-running this.** Fixed to say *footnotes given (§6)*.

### Which recorded figures the gate divergence actually moves — comparative against absolute

**The distinction saves most of the work, and it is the right one.** A measurement that ran both arms
on one population carries the same bias in both, so **the comparison survives even when the population
was not the publishable one.** An absolute figure has nothing to cancel against.

**Comparative — these survive, and nothing needs re-running:**

| figure | why it holds |
|---|---|
| footnote cells erasable against given | both arms drawn from one sample; the correction that closed it was about *what the solver counted*, not about which boards it counted |
| four pitchers against six | both arms from one draw at one gate; what moved the conclusion was the zero-fill correction |
| batting order on against off | `discovery/batting-order/` does not use `load()` at all — it builds its own query and **honours the gate flag correctly**, reporting the gated and ungated arms separately and saying which decides |
| erasure orderings, global-identity phase, footnote grouping | ordering and phase comparisons within one sample |

**Absolute — these describe a pool, and the pool they describe is the `0.25` one:**

| figure | instrument | gate in force |
|---|---|---|
| coverage per stall target (`22% → 33%`, `coverage at 8 stalls`) | `pitcher-cap/measure_pitching.py` | **0.30** — this one already describes the decided pool |
| the median stall ceiling of **5** | `board-configurations/measure.py` | **0.25** |
| reachable targets and blanks per target | `stall-targeted/measure.py` | **0.25** |
| independent-cell counts | `independent-cells/` | **0.25** |
| scoreboard-blank prevalence, footnote-group sizes | `scoreboard-blanks/`, `footnote-groups/` | **0.25** |
| the zero-density distribution and the `+0.79` correlation | `difficulty-metrics/compressibility.py` | **0.30**, and see below |

⚠️⚠️ **One of these is worse than annotated and is a finding rather than a caveat.**
`difficulty-metrics/zero_density_gate.py` — **the instrument that chose the 30% threshold** — called
`load(25)` believing the docstring's *off by default*, and received a sample the gate had already
filtered at 0.30. **A threshold chosen from data the threshold had already removed.** That is the
baseline-removes-what-it-tests shape `CLAUDE.md` names, and no number in its output distinguishes it.
`compressibility.py` has the same defect in a milder form: a correlation computed on a **truncated**
zero-density range is systematically attenuated, so the `+0.79` is a lower bound rather than an
estimate — which does not weaken the conclusion drawn from it, since that conclusion was *this
correlates too strongly to rank on*.

✅ **Both re-runs are done, 2026-08-21** — the **stall ceiling** and **coverage per target** at the
decided gate, because the ladder's rungs come from the first and the inventory question from the
second. See the two entries above. ⚠️ **Neither difference is attributable to the gate**: both moved in
the direction a *looser* gate cannot explain. Everything else stays annotated: it informs, nothing rests on it, and the
comparative forms hold anyway.

⬜ **And a decision that is not mine:** each of the eight instruments that omitted `gated` now says
`gated=True`, which preserves exactly what it measured. **Whether `zero_density_gate.py` should be
ungated is a real question about what that instrument is for**, and changing it changes what a
published figure means.

### ⚠️ Which gate produced which figure — the record that keeps the centralisation from destroying information

**2026-08-21. Seventeen instruments in `discovery/` spelled the zero-density gate as a literal: fourteen
at `0.25`, three at `0.30`, and only three of the seventeen said why.** They read `ZERO_DENSITY_GATE`
from `boxscore_domain` now, so **the code no longer matches the numbers twelve of them produced.**

⚠️ **A stricter gate is not a smaller sample of the same thing.** It removes precisely the boards that
compress least, so every figure these twelve published about coverage, reachable stall targets, chain
length or family usage describes a **livelier population than production draws from.** The figures are
not withdrawn and not re-run — the same treatment as the four-family and zero-fill corrections — but a
figure traceable to one of these was measured at **0.25**:

`board-configurations/measure.py` · `difficulty-weights/measure.py` · `footnote-grouping/measure.py` ·
`footnote-groups/measure.py` · `footnotes-open-or-given/measure.py` · `global-identity-phase/compare.py` ·
`independent-cells/measure.py` · `independent-cells/prune.py` · `rbi-and-hr/measure.py` ·
`scoreboard-blanks/measure.py` · `stall-targeted/measure.py` · `zero-footnotes/measure.py`

**Measured at 0.30 all along, so nothing but the source of the number changed:**
`batting-order/arms.py` · `innings/pool.py` · `sample-boards/render.py`

**Deliberately stricter, and now named rather than merely different:** the two `hand-solve` packs read
`HAND_SOLVE_ZERO_DENSITY_GATE = 0.25`, whose reason lives with it — the packs put boards in front of a
person to judge, and a board rejected for zero density is not the board being asked about.

⚠️ **Anything else in `docs/` carrying a gated figure should be read against this list rather than
against the current source.** Each script now says the same thing at its own `GATE`, so the annotation
travels with the instrument instead of only with this page.

### ⚠⚠ Layer 3b certified none of the five, and difficulty does not explain it

**5 of 5 uncertified.** Checked before treating it as a property of the boards: **3b is not broken** — it
passes on 4 of the 6 reference packages and on 6 of 6 in the retained generation.

But the obvious explanation fails. Against the reference set, where the stall target is recorded:

| target stalls | 1 | 2 | 3 | 4 | 5 | 7 |
|---|---|---|---|---|---|---|
| blanks | 17 | 23 | 30 | 28 | 34 | 34 |
| layer 3b | pass | pass | **fail** | pass | pass | **fail** |

**Not monotonic.** It fails at 3 and at 7 and passes at 5, so "harder boards exceed the weak solver" is
not what is happening, and 5-of-5 at targets 5 and 8 is not accounted for. Six boards is not a
distribution and neither is five.

⚠️ **No further measurement is being run for it**, and that is deliberate. `todo.md` already records
that a chain of measurements has to end at a decision: the question 3b poses is *should it become a
gate*, and **the hand-solve answers that better than any distribution could** — if the operator solves
boards 3b rejects, 3b is too strict to gate on, and that experiment is already set up. A rate would only
tell us how often to ask the question we are about to answer directly.

### The one board with a human verdict

`WAS201307070` reaches **target 8 with 39 blanks** and **target 5 with 33**.

⚠️ **This is not "the 19 became an 8".** The old figure was a *different erasure of the same direction*
— 79 blanks, found by maximising — measured on the scale that counted zeros. What can be said is
narrower and still useful: the direction the operator judged hard carries both of the pack's rungs
comfortably, and the board he actually solved was **twice as erased as anything the pack now prints**.

## What is actually left

Not review findings — the things the repairs unblocked, and what each one is waiting on.

### Waiting on a person, and only a person

**1. Solving the five boards.** The pack is built and printed (two at 8 stalls, three at 5, one with six
pitchers, 30–40 blanks each). Everything under *Waiting on the hand-solve* is blocked on it.

⚠️ **It is not a review step.** Layer 3 propagates intervals to fixed point across forty-odd
simultaneous relations, which is stronger than any person, so a board can pass it and be underivable by
hand. Solving by hand is the only verification of human derivability that exists, and the only check the
common-author risk does not touch.

**2. Reading the five batting-order exceptions.** They are listed in full in
`discovery/batting-order/result.log`. ⚠️ **The distinction that matters cannot come from the
distribution**: a real batting-out-of-order call is a fact about baseball, a scoring error is a fact
about the data, and both look identical as a rate. Five games is a morning's reading, and the answer
changes what the pool rule *means* rather than whether it works.

**3. Pointing a real screen reader at the board** (v24's residual risk). The DOM tests read attributes;
nothing has ever read the board aloud. ⚠️ Same shape as the two above: **an instrument agreeing with
itself is not the same as the experience being right.**

### Decisions the measurements are now waiting on

**The batting-order pool rule.** 5 of 100,226 directions break the cycle. Adopting the rule makes the
constraint exact and costs those five; not adopting it means the solver never gets the constraint, since
a rule true 99.995% of the time is a trap rather than a weaker rule.

⚠️ **The number that decides this is not yet in.** The three-arm run is measuring `off` against
`on_total_erasable` — whether the constraint *adds* deduction once the PA total is erased. On the
post-rule pool, 826,039 of 990,202 rows (83.4%) are alone in their slot, but **that is the filler case
and not the payoff**: with the total given those nine cells are typed, not deduced. Do not take this
decision off the 83.4%.

⚠️ **This line said 75.1% until v27 caught it** — the ungated figure, after the detailed section had
already been corrected. A decision summary carrying a superseded denominator is worse than none: it is
read at exactly the moment the decision is taken, and it contradicted the authoritative section in the
same file.

⚠️ **The winner bias, which nobody chose and nothing had recorded.** §5's zero-density gate selects the
**winning team's offense 84% of the time** — more runs means fewer zeros. So every board the generator
ships is overwhelmingly a winning batting line, and the losing team's board is rare by construction.
Whether that matters is a §31 question about what the player meets, and it is **not** a defect to fix
quietly: the gate is doing exactly what it was designed to do, and this is a consequence of it that was
never stated. Found by disbelieving a number that came out of an unrelated correction.

### Waiting on the hand-solve

1. **The ladder's rungs.** Reporting them will be a **correction, not a change of plan**: the earlier
   rungs were set against stall counts that included the solver deducing zeros.
2. **Nothing is labelled easy, medium or hard.** Five stalls was an example the operator gave, not a
   standard.
3. **Whether the marked 1–6 tracks stall count at all.** If it does not, stalls measure something the
   player does not experience — which would be as important as the chain finding was.
4. ⚠️ **Whether layer 3b becomes a gate.** It certified **none of the five**, and difficulty does not
   explain it: against the reference set it fails at targets 3 and 7 and passes at 5. **No further
   measurement is being run for it on purpose** — the question is *should it gate*, and if the operator
   solves boards 3b rejects then it is too strict. A rate would only say how often to ask a question
   about to be answered directly.

### Owed measurements

5. ⚠⚠ **Every recorded discovery result was measured at ≤4 pitchers.** The scoreboard-duplicate
   question, the erasure orderings, the stall-target coverage, the independent-cell counts. The scripts
   follow the decided caps now, so a rerun measures the new board; **the conclusions do not carry, and a
   justification does not travel.** Nothing here is wrong yet — it is unverified at the cap that ships.
6. **The scoreboard-duplicate question was never re-run.** The instrument was fixed — a failed arm is a
   row rather than a missing one — and the measurement it was fixed for has not been taken.
7. ✅ **Coverage at 8 stalls: answered. They never measured the same quantity** — and the number that
   decided the pitcher cap has no recorded run behind it. See the section at the end of this file.

### `serve` — the engine is ahead of the shell

8. **The shell has caught up with the engine. What is left is a backend, not a screen.**

   ✅ **The session.** Survives a reload: `store.js` keyed one-puzzle-one-key, restored before the board
   is drawn, saved on every entry and at the moment the clock stops. The clock is an accumulated
   duration excluding hidden and idle spans, invisible during play (§26). A malformed saved session is
   refused atomically and costs nothing but the session.

   ✅ **The ending, which used to be the whole of this item.** *Check* gives one of three answers and
   never names a cell or a count. A solved board draws the reveal — a **printed boxscore**, both clubs,
   `AB R H RBI BB SO`, the clubs' real names, schema 5 carries it. A finished board is **read-only**:
   no keypad, no cells that are controls, and the clock is **sealed** rather than held, so no tap can
   restart a duration that has already been earned. Reopening the same day returns to exactly that.

   ✅ **Three hints**, spent on the cell the player chose, drawn in a third ink, counted beside the time
   on the reveal. ⚠️ This item used to read *"`hint()` is dead by decision"*; `serve-flow.md` §3 was
   reversed on 2026-08-20 and keeps the superseded reasoning.

   ✅ **A reference sheet** on a button (§3b): the five relations and the bounds, costing no hint.

   ⬜ **The C7 record is computed and goes nowhere.** It travels inside the snapshot, so it survives a
   reload; there is no endpoint to upload it to, because `serve/` has none. ⚠️ **C7 is irreversible** —
   storing aggregate state instead of the event record loses history that cannot be reconstructed — so
   the shape being right already is the part that mattered. It now carries `assisted`, which is `false`
   on every real game and `true` on anything the development test mode filled in.

9. **Seams §C requires in v1 and that do not exist:** C6 routes (`/p/<id>` canonical, `/today` — today
   it is `?p=`), C4 a loader that decides the day (there is no calendar; it takes `manifest.puzzles[0]`,
   which is not a date), C8 `canAccess`, C9 reserved ad slots, C10 the two-phase boot. **C11 is done**,
   but the catalogue holds `en` only.
10. **Product surfaces:** the share (§7) and the landing page with its tutorial.
    ✅ **The landing page and the tutorial are built** (2026-08-20). `serve-flow.md` §1 and §1b carry
    the design and the pages carry it out — every
    visit lands, the button changes when today is played, five wizard steps on a made-up four-batter
    board, the batting order last because it is the only relation invisible in a real board.
    ⚠️ **The tutorial is skippable, reversing §8.** A compulsory one is a barrier in front of someone who
    has not decided yet, and the reference sheet (§3b) ended its status as the only place the rules are
    stated. The old rule is kept as superseded in `design-boxscore-puzzle.md` and in `CLAUDE.md`.

    ⬜ **The share is what is left of this item**, and it is blocked on §36 rather than on effort: what
    the grid encodes without leaking the solution or the names. The precondition it was waiting on —
    a first-time visitor who can learn the rules — is met.

    ⚠️ **Three defects the build found, kept because each is a shape rather than an incident.**
    `renderLineScore` returned a bare table and **five call sites wrapped it in `.linescore`
    themselves**; the sixth was the landing page, which did not, and the scoreboard silently stopped
    being green — a renderer that does not own its own appearance has an appearance that is a
    convention, and a convention is what the next caller does not know about. The tutorial drew every
    step's board complete except that step's hole, so **step one displayed the answers to steps two
    through five**; found by a test asserting no step makes a hole of a cell an earlier step gave, not
    by looking, because every version of the board looks equally convincing. And its innings formatter
    was a hand-written copy that printed six outs as `2.0` where the board prints `2`.
    ⚠️ **The share is designed and is deliberately not next.** §36's *what it encodes without leaking*
    closed on 2026-08-20: a **PNG of the board**, the player's own cells replaced with random digits and
    then blurred, the given cells real, carrying the time and the hints used (`serve-flow.md` §7b). The
    random digits are the protection and the blur is typography — reversing the blur recovers noise the
    recipient cannot distinguish from an answer.
    ⚠️ **The tutorial and the landing page ship before it.** The game currently drops straight onto the
    board, one of the five relation families cannot be inferred by looking at it, and a growth channel
    pointed at a game the first-time visitor cannot read optimises the wrong step.
    **Hints are surfaced** (count beside the time). **Errors are not, deliberately**: marking makes
    probing beat deducing and a count is a binary search over the board. The mistake count stays in the
    C7 record, where it is a measurement rather than a message.
11. **Tablet and desktop.** The brief says neither starts before the phone has been used on a phone.
    ✅ **That precondition is met**: `docker compose up` publishes on every interface, and the operator
    has played on a handset. Whether to start either is his call and neither is started.
    ⚠️ The shell was made bootable with its boundaries injected (`shell.js`, taking root, clock, store
    and document) for the test mode, and that is most of what a second interface needs from it.
12. ⚠️ **What the directory name promises and does not hold.** `CLAUDE.md` says `serve/` carries "app,
    nginx, docker, endpoints". **There is still no way to deploy this.**

    A `compose.yaml` at the repository root runs `tools/dev_server.py` in a container and publishes it
    on the network — that is the **development** environment and nothing more. ⚠️ **It is not the
    production shape and must not be mistaken for one**: no nginx, no image, no caching contract, not
    one endpoint. A full nginx configuration was written and **deleted rather than kept**, because a
    half-built production config that nobody runs drifts; what it established is two sentences at the
    end of this file.

    The backend is absent too (accounts, OAuth, payments, devices, percentiles), though §23 guarantees
    play does not depend on it.

### Built but not finished, in the forge

13. **`build_pack.py` still targets chain and its `audit()` still speaks in chain rungs.** The last
    chain-targeted producer, and it builds the fifty-board pack that is the launch gate.
14. **The RBI and HR columns**, with the canonical order, and a measurement of what they buy — recorded
    in §6 and not built.
15. **The generator at volume, the calendar builder, and signed packaging in batch.** Nothing in the
    forge produces an inventory; the six packages are a format sample, not a pool.

## v20 — verified, none rejected. **All three closed.**

### v20-P1-01 — a schema-3 board the reader accepts and no interface can finish. **Real, and reproduced.**

Loaded the retained generation's first package through the browser reader before touching anything:
**accepted, 33 blanks, 14 of them footnotes, 0 editable elements in the rendered footnote line.** Every
visible blank can be filled and the board never completes. `serve/data/puzzles/5dce9f673a0f/` carries 91
such cells across six packages; the current generation carries none.

⚠️ **Not declined as a development-environment edge case, and the distinction matters.** *How* the file
gets loaded — a rollback, a mixed deployment — is environmental and would not survive the standing rule.
The defect is not that. It is that **the reader accepts a document no renderer can satisfy**: the schema
says the blank is valid, `createGame` says the player owes it, and the UI offers nothing to enter it
with. Three layers, one contract, three answers.

**Fixed as schema 4, not as a tightening of 3.** A nullable field becoming non-nullable changes what the
document *means*. Tightening 3 in place would make `schema: 3` mean one thing in a file written last
week and another in a file written today — this project's named failure shape wearing the version number
as a disguise. It is also what already happened twice here: v1 was replaced rather than given a legacy
verifier, and v2 was replaced when `offense_is_home` became required.

⚠️ **The guard already existed one row lower down and was never applied upward.** `totals()` in
`package.js` has carried a `complete` flag since a null footnote *total* made a board unfinishable —
with a comment describing this exact defect. The per-batter cells above it acquired the same property
when the line became read-only, and the fix was not carried up. **A rule applied outward and not
inward, thirty lines apart in one file.**

Closed at four places, not one: `_rows(..., complete=True)` at the parse boundary, the same rule in
`Package.__post_init__` so the generator cannot build what its own reader refuses, `rows(..., {complete})`
on the client, and **a shared conformance vector for a null per-batter footnote cell** — which the
sixteen existing vectors did not cover, though they covered the total.

**And a test for the rule rather than the instance.** *Every blank the game asks for has an editable
element on the board*, checked across every reference package by rendering both sections and the
footnote line and comparing the drawn `data-cell` names against `game.blanks()`. The vector forbids this
instance; this forbids the next cell the engine counts and no interface draws.

**Both stale docstrings corrected.** `Board`'s and `erasable()`'s. ⚠️ `erasable()`'s *summary line* still
read "The grid, and the footnote line's per-batter cells" — naming something the function no longer
returns, which is the worst place for a stale docstring because the body under it was right.

### v20-P3-01 — nineteen discovery records off the data-shape convention. **Fixed.**

Eighteen frozen records gained `slots=True`. ⚠️ **The nineteenth got `slots=True` and deliberately not
`frozen=True`**: `board-topology`'s `Board` fills `values` and `equations` in place, so its whole purpose
is to be mutated after construction. `frozen` would have *passed* — it blocks attribute assignment, not
mutation of a mutable field's contents — which is exactly why it would be the wrong label. A guarantee
the class does not make.

Checked for what `slots` breaks before applying: the only `vars()` calls in the tree are on forge
objects that were not touched.

### v20-P3-02 — the footnote attribution bypassed the catalogue. **Fixed.**

`#` and `×` were spelled inline. ⚠️ **`board.slot: "#"` already existed in the catalogue and the slot
column's heading was reading it** — so one screen carried two spellings of one mark, one translatable
and one not. That is the defect `side.home` was introduced to close, recurring six keys further down.
`board.footnote_repeat` is new.

**Tested through a replacement catalogue whose markers differ from English**, because the completeness
test asserts the catalogue *has* every key and says nothing about whether the renderer asks for them.

### Left standing

**`discovery/` carries 80 ruff findings** under the project's own config — unchanged by this work
(measured before and after). ⚠️ A first count said 680 and claimed I had added four: that run resolved
`per-file-ignores` against the wrong root, so `T201` fired on every `print` in a tree that exempts it.
**The instrument was wrong, not the code.** Recorded because a lint comparison run from the wrong
directory is the same class as a comparison whose orderings differ.

## ⚠⚠ The pitcher cap: ≤4 was wrong, and it was wrong for two independent reasons

**Raised to ≤6.** Coverage at 8 stalls 22% → 33%, the pitching section's share of stalls 34% → 45%,
41% more directions in the pool with the 1990s and 2000s reachable, global identity required on 70% of
boards against 55%, cross-team 80% against 88%. **The median ceiling is unchanged at 5**, so the ladder's
range does not move — what moves is how much of the pool reaches it comfortably. A 6-stall board goes
from the top third of the pool to about half of it.

**Reason one: a justification reused rather than re-derived.** The screen-cost argument was retired by
the working-set finding — rows do not bind, because the active section's totals stay pinned — and it was
retired *for the batter cap*. Nobody re-derived it for pitchers, so it went on holding up a cap whose
support had already been removed. This is the recorded failure form `narrow` produced, arriving again.

**Reason two: a confound with no signature in the output.** The comparison that chose 4 ran while stalls
counted the solver deducing footnote terms worth zero. **A pitching row carries no footnote terms at
all**, so pitcher-heavy boards had fewer zeros inflating their scores. The comparison was biased against
exactly the boards it was judging, and its report read exactly as clean as an honest one.

### What was built so the number cannot drift again

**A constants module, `forge/src/boxscore_domain/`.** Configuration rather than a bag of numbers: each
value carries the reason it holds that value and, where one exists, the measurement that set it. The
four that were **chosen rather than measured are marked `PROVISIONAL`** in the same place, because
presenting a measured cap and an eyeballed threshold in one typeface hides the difference.

**Presentation constants are a separate file** — `serve/ui/phone/tokens.css`, linked before `board.css`.
§33 keeps the forge ignorant of screens and the service ignorant of generating; one shared constants
file imported by both sides for the convenience of one is the first thing that would break it.

**A guard, because one definition was not enough on its own.** The erasable set was given a single
definition and the copies were not removed by that act — nothing stopped them existing. So
`forge/tests/test_constants_are_not_copied.py` walks the source trees and fails on a cap spelled as a
literal, in the same family as the guard rejecting decisions made by inspecting a label's formatting.
It found **17 files** still restating the caps.

⚠️ **Its own test caught its one soft edge.** The first version matched any comparison against a length,
and `len(row) != 6` — the column count, which is six and is not the pitcher cap — was structurally
identical to `len(board.pitching) <= 6`. A guard firing on everything carries no information, exactly like
one that never fires. It now reads **ordering** operators only: a cap is a bound and is asked with `<` or
`<=`; a width is asked with `==` or `!=`.

**And the verifier checked one cap and not the other.** `plausibility.faults` has enforced the batter cap
since the file existed; the pitcher cap was held up only by whichever `load()` call passed the right
argument, which is not a check on the publication path at all. Raising the cap without closing that would
have been documentation rather than a change. Verified by reverting the new guard, not by rereading it:
disabling the comparison fails exactly the test written for it.

### Not changed, and why

**Four instruments keep their `max_pitchers=4`** — `pool-at-4-pitchers/` and `pitcher-cap/`. Their
results are published numbers; rewriting the argument would make them unreproducible and silently
reattribute them to a board family they never measured. They are named in the guard's exemption list, and
the literal is now the documentation of what they measured.

⚠⚠ **Every other recorded discovery result was measured at ≤4 and does not automatically carry to
≤6.** The scoreboard-duplicate question, the erasure orderings, the stall-target coverage figures, the
independent-cell counts — all of them describe a board family with at most four pitching rows. Their
scripts now follow the decided caps, so a rerun measures the new board; **the recorded conclusions do
not, and a justification does not travel.**

## Noticed while making the client green again after the regeneration

**Two tests pinned a package id, and the id is derived from the game.** `serve/tests/package-vectors.json`
named `9f42acb60c536afd`; regeneration renamed it and all sixteen conformance vectors failed on a missing
file rather than on anything about the contract — at exactly the moment they were most worth reading. A
second pin, in the footnote suite, named a board that happened to survive the same regeneration, so it
looked fine while carrying the identical defect. **Both now ask for what they need** — the manifest's
first package, and *a* package with a live footnote term — and the second asserts one exists, so an
empty find is a failure rather than a pass.

**`traversal()` ranked footnotes last, and no footnote is blank any more.** The branch could not fire.
Deleted rather than commented out, with the test rewritten from *footnotes come last* to *the traversal
reaches no footnote at all* — which fails loudly if the cells are ever reopened instead of silently
interleaving them with the batting grid.

**The watched board was hoped for, not asked for.** `build_ceiling_pack.py` reported where
`WAS201307070` — the one board with a human verdict against a measured number — lands on the corrected
scale, but only if a stratified draw of four directions per decade happened to contain it out of a pool
in the hundreds of thousands. It never would. The `else` branch was the whole instrument. `load()` now
takes `also=(...)`, which adds named games to the draw **while still applying the gate, the caps and
the provenance rule**, so a named board cannot be smuggled past a filter and a board that does not come
back was genuinely rejected. Deduplicated on game *and* offensive team, because a game is two boards.

**A warning sign printed into a cp1252 stream, one screen below the comment saying not to.** The
`WATCHED` block used `⚠️` directly under a comment explaining that every long run here is redirected,
that Windows gives a redirected stream cp1252, and that a report dying on its own warning sign loses the
compute that produced it. The rule was applied outward and not inward, in the same file, within thirty
lines. Now plain text.

### Not fixed, recorded

**`discovery/` carries 19 lint findings under the project's own ruff config.** `extend-include` pulls it
into scope deliberately — the duplicate `audit()` that disabled a launch-gate check lived there — but
nothing runs ruff over it in a gate, so the findings accumulated: unused `noqa` directives, an unsorted
import block, two long lines, `PLR0911` on `_position`, and several `PLR2004` magic values. None is a
defect on its own. Together they are the "a check that fires on everything carries no information"
condition, one step before the scope stops being read at all. **Not fixed here because it is unrelated
to the work in hand and would bury it.**

## Void rather than confirming anything

The **grouped-versus-separate footnote comparison** was measured through the adapter that restores
footnote values, so the boards graded and the boards measured were different objects. The decision went
to **separate** on a reason the numbers cannot touch — no printed boxscore carries a grouped footnote
column, and §2 commits to the canonical format.

And **five stalls was an example, not a standard.** Nothing is labelled easy, medium or hard until the
pack comes back.

## ⚠️ The reveal is a printed boxscore now, and the package cannot fill one

The end of the game draws the completed board as a clipping — monospace, a rule under the header and
above the totals, names beside the positions the player solved against, footnotes naming carriers. That
part is rendering and it is done.

**But it is not the boxscore a newspaper printed, and the gap is in the package rather than in the
client.** A schema-4 payload carries, checked against a real file rather than assumed:

- **Six batting columns and six pitching columns** — `PA AB R H BB SO` and `IP H R ER BB SO`. **No RBI
  and no HR.** Both exist in the forge's loader as deliberate §6 candidate columns and neither is
  carried into `BattingLine`, so they are not in the package to draw.
- **One direction only.** A game is two puzzles (§5), and the payload holds the offensive team's
  batting against the defensive team's pitching. The other team's batting and this team's pitching are
  **the other puzzle**, and printing them at the end of this one would spoil a board that has not been
  played.

So the reveal shows the object the player reconstructed, complete, and stops exactly there. **That is
defensible and it is also a decision nobody took.** The two questions are separable:

1. **Extra columns for the reveal only** — RBI and HR would make it read as a boxscore rather than as
   the board with names. They are already in the loader; the cost is package size and a `reveal`
   block that carries a second, wider table. **It cannot be the same table**: the six columns are what
   §22 layer 4 checks against, and widening them widens what has to be verified.
2. **The other half of the game.** Only safe once both directions of that game have been played, which
   the calendar knows and the package does not. Probably never worth it.

**Not decided here.** Recorded because the reveal now looks like it is missing something, and the next
person to notice will look in `finish.js`, where there is nothing to find.

## Recorded and not built: the service's real caching contract

The reveal work put a full nginx configuration in `serve/` for about twenty minutes — caching rules,
rate limiting, security headers, an unprivileged container — and it was **deleted rather than
disabled**, because the operator's instruction was the development environment and that was production
infrastructure. What it encoded is worth keeping as two sentences, because both were learned the
expensive way:

- **`manifest.json` is a pointer and must never be cached, at any layer.** A stale pointer is
  indistinguishable from a stale build: the client fetches packages from a retired generation and
  refuses them as the wrong schema, which reads exactly like a code defect. That has cost two
  debugging sessions.
- **`<generation>/<id>.json` is immutable and can be cached for a year.** A package at that path can
  never change; a new one gets a new generation directory (§21).

Two more findings from the twenty minutes, both worth having written down before the VPS exists:

- **nginx builds an absolute `Location` from the port it is listening on.** Behind a published port
  that came back as `:8080`, which nothing on the host answers, so a redirect from `/` landed on a
  dead link *from a phone and not from the laptop*. `absolute_redirect off;`. The same applies behind
  any TLS terminator.
- **The data directory needs an acceptance list, not an exclusion list.** Two `location` rules for the
  manifest and the packages, and a `return 404` for everything else under `data/` — otherwise a stray
  key, an editor backup or a half-written package is served by the catch-all. This is the
  `EXISTS`-over-an-acceptance-list rule, and it also means `signing-public-key.hex` is not fetchable,
  which is correct: the client does not verify signatures (`serve-brief.md` §5) and the forge reads
  that file off the laptop as a pin.

**Not scheduled.** It belongs with the VPS, and nothing about it should be half-built in the meantime.

## The complete boxscore is a package question and is not urgent

The footnote line on the reveal is prefixed with the club it describes — `St. Louis Browns: SH—Balenti.
LOB—8` — because **the package carries footnotes for one club only.** They belong to the board's
batting side; the other club has its own and no package holds them. Without the prefix the line would
read as a statement about both clubs and be silently false about one, which is a label sitting outside
the arithmetic.

Schema 5 gave the reveal both clubs' batting and pitching. It did **not** give it the other club's
`HBP/SF/SH/CI` or its left-on-base, so the footnote line cannot cover both. **That is another package
field if it is ever wanted**, and the prefix is the honest solution until then. Decided: not urgent.


## ⚠️⚠️ The batting order met a person, and found the cost nobody had written down

**2026-08-20.** The operator was solving `126c049659c4a61c` (SLA–BOS, 17 August 1913) and stopped,
because the board looked impossible: the totals row said **PA = 40**, nine slots cannot hold 40 with
any slot below four, and slot 9 showed a **given** PA of **3**.

**The board is sound and the reasoning was sound.** The real distribution is
`[4,4,4,4,4,4,4,4,3]`, total 35 — which is *exactly* the cyclic split of 35 — and the given 3 is
correct. The 40 was **entered**: `batting_totals[PA]` is a blank on this board and its answer is 35.
The pool rule was re-run against both distributions and behaves: it accepts the real one and rejects
the implied one, naming the slots. The board postdates adoption. None of the three failure hypotheses
held.

### What it exposed, which is not a defect and is not nothing

**A given cell can now contradict an entered total, and the board will never say which side is wrong.**

With four families every contradiction resolved *inside one visible equation* — a row, a column, a
cross-team pair — so a player who reached one could re-read the equation and find their own error in
it. **The fifth family is different in kind.** It relates a *given* cell to a *team total the player
computed*, across nine rows, with no equation drawn anywhere on screen. When the two disagree, the two
readings are:

- *I have the total wrong*, or
- *this board should never have been produced*,

and **§27's no-marking rule guarantees the board says nothing that distinguishes them.** That rule is
right and is not in question — marking makes probing beat deducing. But it was decided when every
contradiction was local, and this one is not.

### Why this is the tutorial's problem and not the board's

⚠️ **`batting-order-reversal.md` already records the operator's own distinction**: the first four
families are baseball bookkeeping that a fan recognises without being told, and the batting order is
**logic over a sequence** — true because the order is cyclic, which is reasoning about cycles rather
than knowing baseball. §8 gained a step for it on that basis.

**This is the evidence for how much weight that step carries.** The rule is not merely uninferable
from the board; **misapplying it produces a board that looks broken**, and the player has no way back.
The tutorial has to teach not only *the cycle exists* but *what it feels like when your own total is
the thing that is wrong* — because that is the failure mode, and it happened to the person who
designed the constraint, on his fourth board.

### What is NOT proposed here

- **Not marking the cell.** Probing would beat deducing and the rule holds.
- **Not a count.** Binary search over the board.
- **Not a batting-order-specific hint.** A cue that fires only for the fifth family tells the player
  which family they got wrong, which is the same leak in a smaller box.

**Left open deliberately.** The honest options are all in the tutorial and in the copy of the *does not
balance* message, and neither should be designed from one incident. **Recorded so the fifty-board
hand-solve is watched for it**: if more than one solver stalls this way, the frequency is the finding
and the design follows from it. If nobody else does, this was one board and a rule three days old.


## ✅ Coverage at 8 stalls reconciled — and the figure that decided the pitcher cap is unsourced

**The 33% and the 50% are different quantities and both are correct.** Two differences, found by
reading the instruments rather than by re-running anything:

| | `stall-targeted` / `pool-at-4-pitchers` | `build_ceiling_pack` |
|---|---|---|
| unit | a **(direction, seed) pair** | a **direction** |
| seeds | 2 and 3 | **5, best-of** — `reach()` returns the first that carries the board |

A best-of-five over directions is necessarily larger than a per-pair rate, so the pack's number
**cannot** be compared with the others and the gap is not evidence of anything.

### The size of the gap is right, and there is a committed artefact that shows it

`confirm.json` — 2,160 rows from the pre-registered batting-order run — records `reached` per
(direction, seed), so **both units can be computed from one file**. At target 8:

| arm | by direction, best of 3 seeds | by (direction, seed) pair |
|---|---|---|
| `plain` | **60%** (29/48) | **37%** (53/144) |
| `on` | 79% (38/48) | 51% (73/144) |
| `fallback` | 81% (39/48) | 52% (75/144) |

**`plain` is the closest analogue to the cap instruments, and its two units are 37% and 60% — which
bracket both of the numbers that would not reconcile.** The unit alone moves this quantity by 23
points on the same data. That is the whole discrepancy, demonstrated rather than argued.

### ⚠️⚠️ But the number itself has no run behind it

**`22% → 33% coverage at 8 stalls` appears in three documents and in no output file.** Searched: every
committed `.txt`, `.log`, `.json` and `.csv` under `discovery/`, and the gitignored run logs in the
working tree. The commit that introduced the claim — `8183966`, *the pitcher cap goes to 6* — changed
`max_pitchers=4` to `PITCHER_CAP` in fifteen scripts, added `discovery/ceiling-pack.log` **with zero
bytes**, and added no results.

It was measured in a terminal and the output was not kept.

⚠️ **This is the project's own rule, broken in the place the rule is written down.**
`docs/python-conventions.md` requires a constant to record *"the measurement that set it, **with the
figures**, not a reference to a conversation or a commit"* — **and it uses `22% -> 33% coverage at 8
stalls` as its worked example of a properly cited number.** The example cannot be reproduced. Both the
rule and its illustration have been corrected: the rule now asks for the artefact as well as the
figures, and the example is one that has a file behind it.

### What this does and does not threaten

**It does not overturn the ≤6 pitcher cap**, and the reason is that the decision never rested on this
figure alone. What is independently sourced:

- **41% more directions in the pool, with the 1990s and 2000s reachable** —
  `discovery/pitcher-cap/cap_gate_sweep_results.txt`, committed, a direct pool count.
- **Both reasons the ≤4 argument was broken**: a justification retired for the batter cap and never
  re-derived for pitchers, and a comparison run while stalls counted the solver deducing footnote
  zeros. Neither is a coverage figure; both stand on their own.

**What is now unsupported is the citation, not the cap.** The figure stays in the documents marked as
unsourced rather than deleted — it is probably right, and quietly removing a number is how a record
stops being one.

### If it is ever wanted properly

`discovery/stall-targeted/measure.py` measures stalls and would answer it; it needs the cap as a
parameter and its output committed. **Not scheduled, and deliberately.** It would re-derive a number
supporting a decision already taken on other evidence, and nothing would be built differently either
way — which is this project's own test for whether a measurement should run.


# 🔬 Investigation: is the batting order a reasoning tool or an erasure permit?

**Not a bug.** Nothing is broken and nothing is unsafe. This is a question about what the constraint
*does*, and it is open because the number that was supposed to answer it answers a different question.
Recorded here rather than as a review finding, because what it needs is a measurement and a decision,
not a repair. (Raised as v30-P1-01.)

## The question, in one line

When a board reaches its stall target **only** with the batting order on, is that because the solver
**used the cyclic rule to deduce something**, or because the rule let the generator **erase more cells**
that the ordinary equations then resolved anyway?

- **Reasoning tool** — the rule settles cells nothing else settles. The adoption case holds as stated.
- **Erasure permit** — the rule settles nothing; it only raises the blank count, and column sums and
  row identities do the visible work. Then the gained boards are *boards with more blanks*, which the
  plain path could also reach by asking for more blanks, and the fallback is complexity for nothing.

## Why the confirmation did not answer it

Criterion 3 reported **"346 causal deductions against 2 division steps, 0.6% filler"**. The 346 is
computed as `len(deductions) - division`: every column sum, propagation, cross-team, global-identity
and bounding step in the solve, **whether or not the batting order contributed to any of them**.
Subtracting one technique from the total says nothing about causation.

The label has been corrected — `confirm.py` says `other_steps` now and states the limit — but **the
decision built on it has not been re-derived.** The share is a real measure of *filler*, which is what
the pre-registration asked for. It is not evidence that the rule did any of the remaining work.

⚠️ **A dependency graph cannot substitute.** Bounding carries no originating identity, so a bounded
cell cannot be attributed to the relation that made it bounded. The counterfactual is the only
authority available.

## What decided the adoption, and what did not

⚠️⚠️ **The adoption was decided by a person, and that is not in question here.** The operator solved the
five hand-solve boards with the constraint active and reported that it makes them harder — because the
player has to hold one more rule in their head, not because it resolves more cells. That verdict is in
`batting-order-reversal.md`, with the note that no metric in the document captures it.

So this investigation cannot overturn the adoption. **What it can change is the mechanism**, which is
the "what would be built differently" test this project requires before a measurement runs:

| result | what changes |
|---|---|
| the rule settles cells nothing else does | nothing. `erase_with_lineup_fallback` stands, and `LINEUP_DIVISION_SHARE_CAP` is guarding the right thing. |
| the rule settles nothing load-bearing | the fallback is a second erasure path earning its keep through blank count. Ask the plain path for more blanks instead, delete the fallback, and the cap with it. |

## The design

**The verifier already does both halves**, which is why this is small: `boxscore_verify.reason.derive`
and `rules.relations` both take `slots` and default to `()`. Solving the identical erased board twice —
once with the lineup relations and once without — changes the relation set and **nothing else**. No
re-erasure, no re-seeding, no re-ordering, so there is no trajectory confound to control for.

⚠️ Run through `boxscore_verify`, not the generator's solver: §22 keeps them apart, and a question
about what a *solver* can derive should be asked of the independent one.

**Population.** The gained cohort from `confirm.json` — directions that reach 8 stalls with the
fallback and not plain — one board per direction, the seed already recorded there.

**Two readings, and the first is the one that decides.**

1. **Binary, per board: does the identical erasure still solve completely without the lineup
   relations?** If it does, the rule settled nothing that was load-bearing on that board. This is the
   answer to *tool or permit* and it needs no threshold.
2. **Magnitude, per board: how many cells settle only with the relations on?** Reported as *cells
   downstream of the relation* — it includes the cascade, because a cell the rule settles unlocks
   others, and that cascade is the point rather than an artefact. **It must not be reported as "cells
   the rule directly resolved"**, which is the mistake this whole entry exists because of.

**Pre-registered reading, written before the run:** if **more than half** the gained boards still solve
completely without the relations, the fallback is an erasure permit on this evidence and the mechanism
goes back on the table. Fewer than half and it stands. **The number is recorded either way**, and a
result near the boundary is reported as near the boundary rather than rounded into a verdict.

⚠️ **And a rendered sample, checked by eye, before the numbers are trusted** — a handful of boards with
the cells that stopped settling marked. Every measurement here produces one; this project's record is
that distributions hide what a rendered board shows.

## Until it runs

`lineup_fallback.py` says the confirmation ran and all three criteria held. **Criteria 1 and 2 hold as
stated; criterion 3 measures filler and not causation**, and the module now says so rather than leaving
"all three" to be read as more than it is.

## ⚠️ The printed formula strip is missing the batting order

`discovery/hand-solve/build_pack.FORMULAS` carries four families and the bounds: the row identity,
column totals, the global identity, the cross-team link, `Outs = 3 x innings`, `AB >= H`, `ER <= R`.
**It does not carry the batting order**, which was adopted after the strip was written.

⚠️⚠️ **That is the one relation a player cannot infer from looking at a board** — `batting-order-plan.md`
records the operator's own distinction: the first four are baseball bookkeeping a fan recognises, and
the fifth is logic over a cyclic sequence. The strip's own docstring says it "doubles as the first real
test of §8's permanent reference sheet", so a reference sheet missing the rule nobody can infer is the
worst gap it could have.

**The cost is not hypothetical.** On 2026-08-20 the operator stopped on a board he believed was
impossible, reasoning correctly from the cyclic rule against a total he had entered wrongly. He had the
rule in his head; a solver working from the strip would not have it at all.

**Not fixed, and the reason is the launch gate.** The pack is printed and being solved, and it must not
move while it is being solved — a mid-flight change makes the fifty boards two experiments. Fix it in
the next pack, and check the same thing then: **every relation the boards can require is on the strip.**

The on-screen reference sheet (`serve-flow.md` §3b) carries all five and is not affected.


## 2026-08-20 — what closed, in one place

A long day. The individual findings are recorded above and in the review files; this is the shape of
what moved, so the next session does not have to reconstruct it from commits.

### The reveal became the product's payoff

**Schema 5.** The reveal was the board relabelled — six columns of one club, in monospace, with names
attached. It is a printed boxscore now: both clubs, `AB R H RBI BB SO`, the clubs' real names from
`retroTeams` keyed by team *and season*, footnotes naming carriers. ⚠️ **`RBI` is the point**: it is the
one number on the finished sheet the puzzle never asked for, so the reveal tells the player something
instead of repeating what they worked out.

⚠️⚠️ **One game, one puzzle** came with it and is not optional. The reveal prints both clubs, and the
other club's half **is the other direction's board** — publishing both hands the second away inside the
first one's reveal. Asserted over a batch; **the calendar inherits it** the moment it exists.

### The ending, and a rule about the clock

*Check* moved into the keypad and is dead until the board is full. A finished board is a **record, not a
surface**: no keypad, no cell that is a control, and the clock is **sealed** — `hold()` stops it and the
next tap starts it again, which is how a solved board reopened and quietly rewrote the time it had
earned.

**Three hints**, reversing `serve-flow.md` §3 on an argument the original never engaged with: a hint does
not corrupt a comparison if it is shared *alongside* the time.

### Infrastructure that was claimed and did not exist

**CI runs** — ruff, the discovery ratchet, mypy, the suite with the coverage floor, and the browser
suite headless, on Ubuntu **and Windows**. ⚠️ **`main` is not protected and cannot be**: GitHub gates
branch protection and rulesets behind a paid plan for private repositories. `CLAUDE.md` said all three
were true and none was; it now says what is actually enforced, and `.githooks/pre-push` is the opt-in
local substitute that is deliberately not called protection.

**`discovery/`'s 199 lint findings had never been reported once** — ruff's config included the tree and
no invocation ever pointed at it. They are a per-rule ratchet now.

### Three figures that said more than they measured

`causal` for a subtraction (346), `causal` for a technique count (47, which does not reproduce at all),
and `coverage at 8 stalls` for a figure with no committed run (22% → 33%). ⚠️ **The instrument was sound
in two of the three.** What failed was the sentence, and nothing checks a sentence — which is why each
correction is in the document that carried the number rather than in a changelog.

---

## ⚠️ `retroGameProvenance`: the clause that excludes the Negro Leagues fires on nothing

Raised by the operator, who said 203,908 rows is a heavy way to say *exclude the Negro Leagues for
ever*. He is right, and the measurement says something sharper than his objection: **that clause does
not exclude them. Something else already did, and the clause has never removed a single game.**

The pool query's source gate reads:

```sql
CROSS APPLY (SELECT TOP 1 p.source_type, p.is_deduced FROM dbo.retroGameProvenance p
             WHERE p.GAME_ID = g.GAME_ID AND p.is_deduced = 0 AND p.source_type IN (...)) AS prov
JOIN dbo.retroGameLogs l ON l.GAME_ID = g.GAME_ID
```

Measured against the live database:

| | |
|---|---|
| Rows in `retroGameProvenance` | 203,908 — one per game in `retroGamesReg`, exactly |
| `EVR` (Negro Leagues) games | 1,872 |
| **`EVR` games with a `retroGameLogs` row** | **0** |
| Games where the `source_type` letter ≠ home league initial | **0 of 203,908** |
| Deduced games | 3,465 |
| **Deduced games that DO have a game-log row** | **3,451 — the entire real exposure** |

**The `JOIN dbo.retroGameLogs` is what excludes the Negro Leagues**, and it does so completely, because
Retrosheet publishes no game logs for them. Remove `source_type IN (...)` and the pool does not change
by one game. ⚠️ **This is the recorded failure mode, not a new one:** *a check that never fires is
indistinguishable from a check that is broken.* It reads like the thing enforcing §32's exclusion, it
is named in three documents as that thing, and the exclusion is a side effect of a join written for
another purpose entirely.

**And the letter carries nothing either.** `EVA`/`EVN`/`EVF` is the home team's league in every one of
203,908 rows, with zero exceptions — already in `retroGameLogs.HomeTeamLeague` and in `retroTeams.league`.

**So the table's whole information content is `is_deduced`: 3,451 game IDs.** `extract_deduced_game_ids.ps1`
already writes exactly that list, one per line.

### The counterargument, which is why this is not simply "delete it"

A list of 3,451 bad ids is an **exclusion list**, and this project has a rule against exactly that: a
filter is written as `EXISTS` over an acceptance list, never `NOT EXISTS` over an exclusion list,
because **the exclusion form passes on absence**. A game missing from a bad-id list is admitted; a game
missing from `retroGameProvenance` is refused, because `CROSS APPLY` drops it. The 203,908 rows are the
price of failing closed, and that is a real thing being bought — it is not accidental weight.

What is *not* bought is the `source_type` clause. That one is redundant twice over.

### The operational half — what happens on the next Retrosheet load

**Today the table and `retroGamesReg` agree exactly: 0 games without a provenance row.**

⚠️ **Correction to the first version of this entry, which said nothing checks that.** The loader's final
block computes `games_with_no_provenance` and prints it as its last line. It is a **report, not a gate**:
it runs *after* the transactional swap has committed, so a non-zero answer arrives when the table is
already in place, and nothing acts on it. This project's rule is that anything acting as a gate is
asserted rather than printed — the number exists and the assertion does not, which is a smaller gap than
the one first recorded here and a different one to close.

Two ways of breaking the agreement are silent:

1. **New data loaded, provenance not rebuilt.** The new games have no provenance row, `CROSS APPLY`
   drops them, and the season is simply invisible to the pool. Fail-closed in direction — and **silent**,
   so a whole season missing looks exactly like a season that produced no admissible boards.
2. **Retrosheet revises a file.** A game shipped as `.EDN` becomes `.EVN` when a scoresheet is found.
   The stale table still calls it deduced and it is excluded for ever. The reverse also holds: a game
   whose provenance stays put but whose boxscore is corrected.

The loader's own guards do not cover this. `$staged -ne $origin.Count`, the shrink check
(`ShrinkTolerance`, default **0.02**) and *"every staged game is deduced"* all describe **one load**; none
can see the table not being reloaded at all. Staleness has no signature in them, and the shrink check is
one-directional by design — a rebuild that *adds* a season is exactly what it must let through.

**Proposed, not built:** promote that last printed line to an assertion, and put the same one wherever the
pool is loaded. In the loader it has to move **inside the transaction, before the swap**, or it can only
ever report a table that is already canonical. Failing loudly with the count and the seasons affected.

⚠️ **The zips are the coupling, not the tables.** The script reads `-ZipDirectory` and never queries
`dbo.retro*` at all, so running it before or after the tables load makes no difference — what matters is
that both are built from the *same* download. A stale zip directory produces a provenance table that is
internally perfect and describes a different dataset, which is this project's usual shape.

The operator decides whether the assertion lives in the loader, in the publication gate, or in both.


---

## ⚠️ `era-after-gate.md` is measured at a cap that was replaced

Found while analysing the postseason (`discovery/retrosheet-coverage/postseason.md`), not while looking
for it.

That document's whole funnel is computed at **≤2 pitchers**. The decided cap is **≤6**. Re-running the
same predicates:

| | at ≤2 (the document) | at ≤6 (decided) |
|---|---:|---:|
| Admissible directions | 12,218 | **102,228** |
| 2010s | 50 | **11,287** |
| 2020s | 12 | **7,780** |

**A 225× change in the decade the document calls starved**, because ≤2 selects complete games and modern
baseball hardly produces them. The pool is now *heaviest* after 1970: the 1990s, 2000s and 2010s are the
three largest decades at 11.2%, 12.2% and 11.0%, against the 1910s at 6.9%.

⚠️ **Everything the document decides is therefore costed against a starvation that no longer exists.**
Its three levers — stratify the calendar by era, raise the gate to 35%, loosen the pitcher cap towards 3
— were priced to buy back a modern era that the pitcher cap already bought. The third one is the same
lever, already pulled, further than proposed.

**Not corrected in place**, because it is a measurement document and rewriting one in passing is how a
correction gets lost. It needs a re-run and a dated note saying which numbers were superseded and why,
in the file that carries them.

⚠️ Note the shape: **the instrument was never broken.** The funnel was correct at ≤2 and it is still
correct at ≤2. What expired was the parameter, and nothing in the document can notice that — the same
failure as the three figures corrected on 2026-08-20, where the measurement was sound and the sentence
around it was not.

## The postseason, a season cut, and the zip dependency — analysed, not decided

Full analysis in `discovery/retrosheet-coverage/postseason.md`. The short form, so it is findable:

- **The postseason is worth 0.73%** — 751 admissible directions against 102,228 — and its boards survive
  the project's own gate **worse** than regular boards of the same decade (14.1% against 23.2% in the
  2010s). The modern skew in its era profile is the supply of playoff games, not the boards.
- **The only argument that survives is the reveal**: 319 of the 751 are World Series games, and §7 now
  prints the real boxscore. That is a product decision worth taking on its own terms.
- **A season cut could delete the provenance table and the zip dependency entirely** — but at **1969+**,
  not 1952. Negro League games run to **1961** and deduced games to **1968**. 1969+ leaves 63,691
  directions, 94.5 years of calendar, against a requirement of five months.
- ⚠️ **The cut is a weaker guarantee than the table**, and the difference should be stated when it is
  decided: the table asserts *this game came from a scored file*; a cut asserts *no game in this era came
  from a deduced file*, which is a claim about Retrosheet's future behaviour.


---

## 2026-08-21 — v36, and the question of what has to be measured again

61 findings (1 P1, 16 P2, 44 P3). Eight closed in the first pass; the rest are listed with the
disposition in `code_review_v36.md`. This entry records the two things that outlive the review file:
**what the P1 means for everything this session reported**, and **which measurements survive**.

### ⚠️⚠️ The ratchet was blind, so every lint claim in today's commits is void

`tools/lint_discovery.py` run with an interpreter that has no ruff exits 1 with empty stdout — the same
code ruff uses for *findings found* — and `json.loads(stdout or "[]")` turned that into **zero
findings**, which beats every baseline. It printed *"these rules improved"* and returned 0.

**Five commit messages today said "ratchet at zero" on the strength of that.** Run properly, four rules
had grown, all four from this session's own work. The tool now refuses to run unless ruff answers
`--version`, and treats exit 1 with empty stdout as fatal.

⚠️ **The lesson is not "check the interpreter".** It is that a tool reporting success while unable to
report at all is indistinguishable from one reporting success — and this project's own instrument for
catching that shape had it. Nothing in the output distinguished the two states.

### ⚠️ Which measurements have to be re-run: **none**, and each answer was checked rather than assumed

This is the question worth asking after a review this size, so the reasoning is here rather than in a
commit message.

| Finding | Could it have contaminated a measurement? | Checked how |
|---|---|---|
| **P2-03** — the batting-order instrument died on `ImportError` | **No.** The break came from the postseason rename, *after* the adoption decision; and the rename did not move the population — the regular season's **executable SQL is byte-identical**, comments aside | Compared the rendered cohort against `HEAD` with comments stripped, at the time of the change; the instrument's own "the provenance rule moved" guard now runs and passes |
| **PLR1704** — the `season` parameter shadowed by a loop variable | **No.** Every use after the shadow wanted the *year*, which is what the shadow held: two `team_name(...)` calls and the `Loaded` field, all of which mean the calendar year | Read all three uses; the queries are built before the loop, so `season.daily` was already interpolated |
| **P2-16** — a test asserting a staff's outs always divide by three | **No, and this is the one that could have.** The false rule lives **only in a client test**. No pool filter, no plausibility rule, and `eligibility()` has no innings condition at all — so **the pool has never excluded walkoffs** | `grep` for `% 3` across `forge/src` and `discovery`: three hits, all display formatters, none a filter |
| **P2-15** — innings notation in three copies with two rules | **No.** Nothing in production or discovery parses a displayed innings string back; `from_display` / `inningsFromDisplay` appear only in tests | `grep` over `forge`, `discovery`, `serve`, `tools` |
| **P2-06** — the tutorial's traits never checked on what shipped | **No.** The published six satisfy the gate today | Ran the new gate against the shipped batch |
| **P2-07** — the cap's boundary test never called the implementation | **No.** The implementation was correct; only the test was decoration, so no board was wrongly kept or discarded | The mutation that the rewritten test now catches is a change to the code, not a record of one |

**So no discovery run and no forge measurement needs repeating.** What does need repeating is the
*lint* claim, which has been repeated correctly.

### ✅ One conversion, two notations — done 2026-08-21

The formula lived in five copies outside tests and had already drifted in front of the player: `4` on
the board, `9.0` on the reveal. **The fix is one function with the notation as a parameter, not one
notation everywhere** — both are correct about their own surface.

`Innings.PRINTED` writes `9.0`: the reveal is a printed boxscore and a newspaper writes it that way,
and in a column where some rows read `4.1` the trailing digit is what makes the column line up.
`Innings.BOARD` writes `9`: the keypad offers `.1` and `.2`, so padding a whole inning would show the
player a form they cannot type. **The two docstrings that used to defend opposite rules say this where
they live**, so the next reader does not try to reconcile them.

Every caller now asks: the board, the reveal, the tutorial, the board prototype and the sample
renderer. ⚠️ **The keypad's inverse arithmetic moved too** — `Math.floor(current / 3) * 3 + thirds`
spells the same representation backwards, and *nobody hunting for copies of a formatter finds the
parser*, which is how it survived four reviews.

⚠️ **Both parsers accept both notations now.** The client's refused `.0` — the exact string the
format's own Python reference implementation emits — so a notation choice had become a data question.

**Two guards, because the copies drifted on their own and remembering was already shown not to work.**
`forge/tests/test_one_innings_conversion.py` walks the AST for the *shape* — a division by three and its
remainder or multiple on the same subject in one statement — rather than for a spelling, so a rewrite
that keeps the defect is still caught. `serve/tests/engine.test.js` carries the mirror, because §33
keeps the two trees sharing no code. **Each has its own test proving it fires on a re-introduced copy,
and its own test proving it spares ordinary arithmetic**; both were verified by putting a real copy back
into a real file. Each guard names the other, since neither can see the other's tree.

### ⬜ Still to do: re-check the hand-solve pack's fidelity once it is free

⚠️ **The pack was deliberately not touched** — it cannot move while it is being solved. It calls
`to_display(outs)` with no notation, and the parameter's default is `PRINTED`, **so its boards are byte
identical**. `test_one_innings_conversion.py` asserts both halves of that: the default still yields
`9.0`, and `build_pack.py` still takes the default. If either changes, the pack's boards change
underneath a printed answer key.

**What remains open is a judgement, not a bug.** The pack prints `9.0` and the board prints `9`. The
pack is §22's launch gate and its boards are supposed to feel like the product, so **if the two end up
on different notations that is a real difference between what is being judged and what will ship** —
and the fifty-board hand-solve is the only verification of human derivability that exists.

Re-check it once the pack is finished, rather than assuming it: either the pack moves to
`Innings.BOARD`, or the difference is recorded as accepted with the reason. **Not before** — a board
that changes mid-solve invalidates the sheet already filled in against it.

### Superseded: the old note under this heading

⚠️ `innings.py` prints twelve outs as `4.0`; `columns.js` prints `4`; `finish.js` has a third
hand-written copy printing `9.0` on the reveal. **Five copies of the formula exist outside tests.** The
player meets `4` on the board and the tutorial, then `9.0` on the reveal.

**The hand-solve pack uses the Python rule**, and the pack is the §22 launch gate whose boards are
supposed to feel like the product. That is a fidelity claim the notation split quietly weakens.

⚠️ **The pack must not move while it is being solved**, so this is deliberately not a fix. It is here so
that whichever notation wins — an operator decision, since the two docstrings carry contradictory design
arguments (column alignment against *the way a printed boxscore writes them*) — the pack's fidelity is
re-checked rather than assumed. v36-P2-15.

### ⚠️⚠️ ~~v36's P2s are closed — all sixteen~~ — **twelve, and this heading was wrong**

**Corrected 2026-08-21, and the correction matters more than the count.** This said *all sixteen* while
four were untouched, in the file people read to learn what is done. That is the shape `CLAUDE.md`
records against its own *"`main` is protected"* paragraph: **a false claim is worst in the place the
rules are looked up.**

⚠️ **And *sixteen* was wrong too — there are 20.** `P2-01` to `P2-20`.

| still open | what it is | state |
|---|---|---|
| `P2-17` | all three pages shipped an identical hardcoded `<title>boxscore</title>` | ✅ **closed 2026-08-21** with `P3-46/47` — `applyHead()` takes the title, description and language from the catalogue |
| `P2-18` | the landing page's whole indexable content is client-rendered behind a package fetch | ⬜ **open.** Needs server-rendering; `P3-49`'s share preview depends on it |
| `P2-19` | `serve/tests/` ships to production under the deployment rule | ⬜ **open, and not yet buildable** — there is no production shape at all: no Dockerfile, no nginx. It belongs with the URL contract recorded in `serve-brief.md` |
| `P2-20` | `load()`'s `gated` flag is dead and the docstring promises the opposite | ✅ **closed 2026-08-21** — see the banner at the top of this file |

⚠️ **How the miscount happened is worth more than the miscount.** The closing paragraph listed nine
findings by number and leaned on *"eight closed in the first pass"* for the rest — **a total asserted
from two sources neither of which enumerates the whole set.** Nine plus eight is seventeen against
sixteen findings, so the arithmetic never checked out; nobody added it up, because the sentence read
as a summary rather than as a claim. **A count is a claim, and this project's rule is that a claim
gets checked against an independent source** — here, the review file's own headings.

### ✅ Twelve of v36's P2s are closed, 2026-08-21

`P2-01` the bounding loop is bounded, with a cap measured over 10,442 real calls (worst: 5 passes on a
143-cell board) and a `ContradictionError` on exhaustion; the seeding is **deliberately unchanged**,
because copying the verifier's finite cap would narrow harder and silently move the pool ·
`P2-02` the constructor holds the parser's rules for `puzzle_id` and `signature`, with the round trip
nobody was performing now asserted · `P2-04` the hook reads the refs from stdin, so `git push origin
main` from a feature branch no longer prints a reassuring skip · `P2-08` a given cell may not
contradict the solution, in **both** runtimes · `P2-10` the publication gate refuses a package whose
metadata still names the game · `P2-11` the database identifiers are bound parameters · `P2-12` the
package records whether a board reached its target only with the batting-order clue · `P2-15` and
`P2-16` closed with the innings work above.

⚠️ **Three of them were only reachable because a test was not doing what it said.** The lineup cap's
boundary test asserted its own restatement of the rule over two literals, so flipping `>` to `>=` in
the implementation left all 1014 tests green — verified by doing it. The tutorial-trait gate's first
predicate could not fail. And a scan written for C11 fired on catalogue keys until it was narrowed.
**Each fix now has a test that fires on the defect and a test that spares the code around it.**

### ✅ Both design questions decided — yes to both, 2026-08-21

**1. Layer 4 takes the source boxscore.** `verify(package, *, secret, source)`, no default, `None`
refused the way a missing secret is. ⚠️ **The decisive check: §22's worked example — two batters' hits
exchanged — now fails at `END_TO_END` / `MISMATCH`** with *"solving gives a different boxscore at 2
cells; bat[0].hits solved to 0 against 1"*. It passed before, because a corrupted artefact carries the
swap in both halves and the layer compared one against the other. **Four layers consulting one answer
were one layer.** The old behaviour is kept as a test — handing layer 4 the package's own copy accepts
the corrupted board — so the regression cannot return quietly.

⚠️ **What it buys, stated rather than assumed:** independence between *the file* and *the game in
memory*. In `write_reference_puzzles.py` both descend from one `Loaded` object, so a loader defect is
still the residual risk §22 records under the common-author heading. Closing that needs a second read
from the database, not a signature change.

**2. The batting order is the fifth `Family`.** Verified reporting: a fallback board at target 7 now
lists `batting_order` among its families. The old figures are **marked, not re-run** — they counted a
smaller set, the same treatment as the zero-fill correction — in `CLAUDE.md` beside the axis itself.

#### What the three post-fix checks found

| | |
|---|---|
| **The swapped-hits case** | ✅ **Caught.** The layer does what §22 says it does |
| **Layer 4 over everything published** | 6 packages, 1 generation, **0 rejected**. ⚠️ **With a caveat that matters**: `game_id` is stripped from a published file (§7), so the direction cannot be reloaded by id and the only source available here is the package's own solution. This confirms every published puzzle solves back to the answer that ships with it; it **cannot** answer whether the generator wrote that answer wrong. Only the writer holds the source, so the strong version of this check runs at generation time from now on |
| **Share of inventory needing the batting order** | ⚠️ **Not computable retroactively, and that is the honest answer.** The six predate both the `lineup` field and the fifth family; their metadata records the four-family axis, where `batting_order` could never appear. **The number exists from the next generation onward.** My first attempt to compute it from the files returned `[]` for all six — a broken instrument, caught before reporting: it mixed the verifier's cell namespace (`bat[0].hits`) with the forge's solver (`batting[0].hits`), which is exactly the separation §22 requires and therefore exactly the mistake that produces silence rather than an error |

### ⬜ Superseded: the questions as they stood

⚠️ **1. `Fault.NO_SOLUTION` at layer 2 and `Fault.MISMATCH` at layer 4 are now unreachable through the
type.** Both meant *the puzzle and the solution disagree*, and `P2-08` makes that unconstructible: if
every given equals the solution and the solution passes layer 1, the solution **is** a completion, so
"no completion exists" cannot arise; and `verify()` compares the solved board against
`package.solution` — the package's own answer — so a mismatch cannot either.

The refusal moved **earlier and into both runtimes**, which is strictly better. But it means layer 4 is
not the end-to-end check §22 describes: *take the published puzzle, solve from scratch, compare against
the original boxscore*. It has never taken the original boxscore; it takes the package's own. Making it
one would mean passing the source direction into `verify()` — a signature change to the verifier and a
real strengthening. **The branches are left in place as defence in depth pending that decision**, and
the layer tests now record where each case actually goes.

⚠️ **2. Should the batting order be a fifth `Family`?** `FAMILY_OF` maps no `Identity` to it, so
`Solution.families_used` excludes every lineup step and package metadata cannot say a board needed it.
`P2-12` works around this by recording `"lineup": "plain" | "fallback"` instead.

**Adding a fifth family is not a local change.** §4 and §31 name four equation families as the axis
difficulty is reported on, and every figure taken so far is against those four. The player already
meets five relations — the reference sheet and the tutorial both teach the batting order as one — so
the product and the measurement axis disagree about how many there are. That is worth resolving, and
resolving it re-bases the reporting.

### v36's P3s — grouped, and worked group by group

⚠️ **They are 49, not 44**: `P3-45` to `P3-49` were added to the review after the count was quoted.

| Group | Items | State |
|---|---|---|
| **A. Checks that do not check** | 12, 13, 14, 15, 16, 17, 18, 19, 28, 38 | ✅ done |
| **B. The client's boundary, and immutability** | 23, 24, 25, 26, 27, 45 | ✅ done |
| **C. Escaping in instruments** | 32, 33, 34 | ✅ done |
| **D. Reproducible from the script alone** | 02, 03, 07 | ✅ done |
| **E. Stale docs and dead code** | 04, 06, 20, 22, 35, 44 | ✅ done |
| **F. Tooling, CI, container** | 01, 09, 10, 11, 30, 31, 43 | ✅ done |
| **G. Measurement correctness** | 21, 36, 40, 41, 42 | ✅ four fixed, one recorded |
| **H. Structure and typing** | 05, 08, 37 | ✅ |
| **I. Security documentation** | 29 | ✅ fixed in the doc *and* in the writer |
| **J. Page basics** | 39, 46, 47 | ✅ and `P2-17` with them |
| **K. Decisions to record, not code** | 48, 49 | ✅ recorded in `serve-brief.md` |

**Grouped before starting rather than taken one at a time.** Several are the same shape, and doing a
category together is both faster and a cleaner record than forty-nine commits.

#### ⚠️ Group A — one of them was not a P3, and is reported rather than absorbed

**P3-16** said two plausibility tests assert the same thing under a comment promising two cases. True.
But **the second case is one the code deliberately refuses to check**: a row with no plate appearance
carrying numbers is the pinch runner who scored without batting, and a filter demanding a plate
appearance **deleted him and his run with him** — a real defect, recorded in `CLAUDE.md`. Writing the
"missing" test would have asserted the rule that caused it. The duplicate and its false claim are
deleted instead. *(This is what led to the ghost-runner question recorded further down: the ghost
runner is the case the pinch-runner reasoning does **not** settle.)*

**Two were worse than filed.** `P3-17`'s test passed `evidence=None`, which returns **before any check
runs**, so its fixture could not produce the prefixes its name promised even in principle — removing
the prefixing left the suite green. And `P3-19` stopped being cosmetic **because of this week's own
work**: the line-score anchor guard returned on the *first* `LineScore(...)` call, and the postseason
change added a season seam to that loader.

The rest: `P3-13` a fail-open where an empty names tuple checked no row at all · `P3-15` a rotation,
not the named mutation, was what fired the assertion — reverting the mutation left it green · `P3-38`
the identity set lived in **three hand-written lists** tied by subset assertions that fire only on
removal, while the real drift is addition; `UNMAPPED` makes the rule an equality · `P3-28` the reject
vectors accepted *any* throw, and a first patch of mine matched a list of field names, **a second copy
of the schema inside the test** · `P3-12`, `P3-14`, `P3-18`.

#### Group B — the boundary, and a rule that lived in one interface

**`P3-26` is the one that mattered.** The clock is sealed *in the engine*, on the stated argument that
sealing is a fact about the clock rather than a promise every future shell has to keep — and the
board's immutability got the opposite treatment. Only the phone layer removed the handlers, so
`__game.enter(...)` from a console changed a finished board, the next save persisted it under the
frozen `finishedAt`, and `record().solved` could flip on a result already reported. **Tablet and
desktop are planned**, and a rule every interface must remember is one the third forgets.

`P3-23` the package is validated rigorously and **the pointer selecting it was not** — and it is the
one file served `no-store` · `P3-24` `played_on` was "a string", so a bad date threw **inside the
reveal**, in `check()`'s success path · `P3-25` a field nothing reads, which is where a pass-through
waits because no test goes red first · `P3-27` `restore()` and `enter()` applied different rules.

**`P3-45` is a decision, recorded beside C6 in `serve-brief.md`:** an unknown `?p=` serves the first
puzzle with a 200. Harmless as a development convenience; the moment `/p/<id>` exists, a link to a
retired or mistyped id renders **a different puzzle as if it were the one asked for**. Unknown ids are
refused, never substituted — decided now so it is not invented during the route work.

**Every fix in both groups is verified by mutation** where a mutation exists.

### Still open from v36

### ✅ v36 is closed — **70 findings**, and four more were found by closing them

**All 49 P3s, 18 of the 20 P2s, and the P1.** `P2-18` and `P2-19` stay open: both need a production
deployment shape that does not exist yet.

⚠️⚠️ **This said 61 — 44 P3s and 16 P2s — while claiming to have counted the review's own headings.**
The claim was the substitute for the check; the numbers came from the review's introduction, which is
a summary. Corrected against `grep '^### v36-P[123]-'`, and the group table below turns out to cover
**P3-01 to P3-49 with no gap and nothing invented** — the work was complete and the prose was not.
Third wrong count in this file, second written while correcting the previous one. See the v37 entry.

**Four findings were not in the review.** The P1's blind ratchet voided five commit messages; the
regeneration exposed one game yielding two different boards under one id; `P2-17` and `P2-20` were
open while this file said every P2 was closed; and `load()`'s gate flag had been decoration for as
long as it existed. **Every one came from acting on a finding rather than from reading the review**,
which is the argument for closing them rather than triaging them.

#### Group J — the seam's blind spot was a file extension

`P3-39` **the batting totals row and the pitching totals row announced the identical name.** Both
said *"Totals, hits, blank"*, and `role="button"` means the table-header context a screen reader would
otherwise fall back on is not reliably announced — on cells **every reference package leaves blank**,
so among the most edited on the board. They carry their section now, read back from the real DOM:
`HOME BATTING Totals, PA, blank` against `AWAY PITCHING Totals, BB, blank`. Composed from the
catalogue keys the section heading already uses, so it needed no new string. Sixteen column headers
carry `scope="col"`; the two section headings carry `scope="colgroup"`, which is what a heading
spanning a column group is for.

⚠️⚠️ **`P3-46` and `P3-47` could not be done without `P2-17`, which this file said was closed.** All
three pages shipped an identical hardcoded `<title>boxscore</title>` — **four copies of one
user-facing string**, in a project where C11 is mandatory from day one. It survived every C11 guard
because **markup is not code to a scan that reads code.**

`applyHead(page)` takes the title, the description and the language from the catalogue. ⚠️ **The
`<title>` element leaves the markup rather than staying as a copy with a guard over it** — two places
saying one thing with a guard between them is the arrangement this project keeps finding defects in,
and the cost is a moment of URL in the tab. **`lang` goes the other way and stays in the markup**,
because a crawler and a screen reader both need it before any script has run.

**The C11 scan reads markup now**, which is where the defect hid. Mutation: put the title back in one
page and remove `lang` from another, two go red. And what it must *not* fire on is asserted too — a
guard flagging `<html lang="en">` or the viewport gets switched off within a week.

⬜ **What this does not fix, stated so nobody reads it as fixed.** A crawler that does not execute
JavaScript still sees nothing, because the pages have no server-rendered body — `P2-18`, open. This
puts the strings in one place and delivers them to every reader that runs scripts, which is every
human.

#### Group K — two decisions recorded in `serve-brief.md`, neither of them code

`P3-48` **the URL and status-code contract**, because URLs are the one thing that cannot be renamed
after indexing, only redirected from. `/` answers **200** by rewrite; `/p/<id>` is **200**; `/today`
is **302 and not 301**, because its target changes daily and a 301 is cached by browsers and
intermediaries effectively forever; implementation paths are never reachable alternates. ⚠️ `/today`
carries the manifest's `no-store` rule **for the manifest's reason** — it is the same pointer wearing
a URL, and a stale pointer is indistinguishable from a stale build.

`P3-49` **the link preview.** Static OG tags from the same catalogue keys as the titles, and
`og:image` is **static branding, never board state** — two independent reasons, either of which
decides it. The scraper fetches server-side without the sharer's session, so a dynamic image cannot
reflect their board **even in principle**; and §7's no-leak rule extends to a static image trivially
and to a dynamic one never, because that surface is fetched **by the platform rather than by the
player** and would not appear in any test a person performs.

⬜ Recorded rather than built: server-rendered `og:*` needs the pages to have server-rendered content,
which is `P2-18`.

**Groups H through K: 9 items.**

#### Group G — two of these were about numbers that have been published

⚠️ **`P3-40`: the p90 was the maximum on any board with fewer than ten costed steps**, which is the
exact degenerate value it exists to avoid — `CLAUDE.md` §1 says *p90, never max; the max is 8 or 9 on
every board*. `int(0.9n) == n - 1` for every `n <= 10`. It was also off the other way on long solves:
`int(0.9 * 20)` is 18, the nineteenth of twenty values.

**Measured rather than assumed:** over `cubs_at_braves_1968` at every target from 1 to 12 across five
seeds, **4 of 34 boards fall below the floor, all of them at target 1 or 2** — two of the six rungs in
`STALL_TARGETS`. So the two easiest rungs reported a maximum under a name promising otherwise, against
a metric whose maximum barely varies. Nearest rank now, with the floor named where the number is made.

⚠️ **`P3-36`: `GATE = 0.25` in the reference writer overrode the decided `ZERO_DENSITY_GATE = 0.30`** —
no note, no measurement, no `PROVISIONAL` marker, which is everything the constants convention requires
of a value that shapes the product. **The literal-copy guard could not see it**, because 0.25 is a
different number for the same knob rather than a copy of the same one: the drift that guard is blind to
by construction.

**⬜ Consequence, and it is not fixed by the code change.** The six packages now in
`serve/data/puzzles/` **were drawn under 0.25** — a stricter pool than the one every published
measurement describes — so the client has been developed and its layout judged against boards **less
zero-heavy than the ones that will ship**. The writer uses the decided gate now, so the next batch
differs. Whether to regenerate before more of `serve` is built against these six is an operator call;
it needs the database and the signing key.

`P3-21` printed a rung table starting at nine innings while the cohort holds five-to-eight-inning
games — counted in every denominator, printed as no row, so the shares did not sum to 100%.
`P3-42` stored a scan taken over `system + global_equations` on a bounding step that had succeeded
without the global relation, overstating what the puzzle demanded in the one field meant to say it.

**⬜ `P3-41` is recorded, not fixed, and the review says so itself: "nothing unilateral".** A plain
board's difficulty is graded by a solver given no lineup slots, while the published board prints
`9a`/`9b` and a player who knows the divide-by-nine trick can use them. Correctness and derivability
are unaffected — only the classification the calendar will consume is optimistic-high. **The fix is a
calibration, not an edit**: when the hand-solve pack measures stalls against felt difficulty, include
plain boards where lineup shortcuts exist, so the grading surface and the player's surface are compared
on the same boards.


---

## ⬜ Open question: the ghost runner and the global identity

**Not a task. A question with its reasoning, written down so it is neither lost nor re-derived.**

### What it is

From 2020 onward, an extra inning starts with **a runner already on second who did not get there by
batting**. No plate appearance put him on base.

The global identity is `PA = Outs + Runs + LOB`. If the ghost runner scores, there is a **run no plate
appearance explains**. If he is stranded, there is a **left-on-base with no PA behind it**. Either way
the right-hand side is larger than the left, and the identity would not close.

### ⚠️ What it is not — and this is the part that is already settled

**It is not the pinch runner**, which is the case `plausibility._batting_row_faults` deliberately does
not test, and which `v36-P3-16` was nearly "fixed" into asserting.

The distinction is exact: **the pinch runner's chain contains a plate appearance.** The original batter
spent his PA and reached base; the runner only changes who occupies it and who eventually scores. The
identity never notices, because nothing was added to the right-hand side that the left-hand side did
not already account for.

**The ghost runner has no plate appearance anywhere in the chain.** That is why he is a different
question rather than the same one again.

### What is unknown

**Whether Retrosheet records the placement in a way that closes the identity anyway.** They may log it
as an event that accounts for the runner, or count LOB differently in that inning. **Nobody has
looked.** The answer is a property of the data, not of the rule.

### What would settle it

Games from **2020 onward that went to extra innings**: does the global identity close?

- **If it closes** — nothing to do, and the reason is recorded here so the question does not come back.
- **If it does not** — those games leave the pool. Every extra-inning game from 2020 on, which under
  `MAX_INNINGS = 12` is a narrow band and a real one.

⚠️ **Check the batting order in the same run.** The ghost runner is the player who made the previous
inning's last out, so he consumes no turn and the cyclic distribution should be unaffected — **that is
a prediction, not a measurement**, and the instrument to test it already segments extra innings as an
arm (`discovery/batting-order/measure.py`).

### Why it waits

It costs a database run and the P3 batch is in progress.

**And it is not urgent, for a reason worth stating rather than assuming: if the identity does not
close, those boards are already failing layer 1.** The pool is not silently shipping broken puzzles
either way. What the measurement would change is whether **a band of modern games is being quietly
discarded by a check nobody knew was doing it** — which is a question about inventory and about the
eras the product can reach, not about correctness.

⚠️ The pool's window is `(1910, 2029)`, so those seasons are in scope today. This is not a question
about a future the pool cannot reach yet.
