# The route to beta 0

**The chart map.** `beta-0.md` says what beta 0 *is* and what counts as done; this says **how to get
there from here**, in groups and subtasks, with what each one depends on and what makes it finished.

Written 2026-08-22, against the repository as it actually stands rather than as the documents describe
it. ⚠️ Where the two differ, this file says so.

---

## Where it stands — last checked **2026-08-23**

⚠️ **`CLAUDE.md` carries a pointer to this table and a test asserts the two call the same groups complete** — in both directions, because the front page overstating sends a session past work still to be done and understating sends it looking for code that already exists. **This one is the authority.**

| | | |
|---|---|---|
| **A** inventory and calendar | ✔ **met** | A3.2 (the curve) deferred by decision |
| **B** the hand-solve gate | ⬜ **not met** | B1 is done and mine; B2–B4 are the operator's: afternoons of solving by hand |
| **C** client identity and events | ✔ **met** | `outbox.js`, `report.js`, `uplink.js`; verified in a browser, and every mutation caught by a named test |
| **D** the data layer | ✔ **met** | `keep/`, 77 tests, 100% on both engines |
| **E** serving for real | ⬜ | **A and D are both done; nothing blocks it** |
| **F** deployment | ⬜ | |
| **G** the share | ⬜ | last to build, **exempt from being cut** |

⚠️ **The two things that gate beta 0 rather than merely being in it:** B3 — one board failing by hand
stops everything — and G, which cannot be dropped for time.

⚠️ **The gate has not run.** *These boards are solvable by a person* is still an assumption; the four
validation layers say the numbers agree with each other, which is a different claim.

---

## The seven deliverables, in one table

Each group ends with an artefact somebody can point at. **If a group finishes and there is nothing to
point at, it did not finish.**

| | deliverable |
|---|---|
| **A** | five months of dated, signed inventory, **and the runbook that produces the next five** |
| **B** | a verdict on whether the inventory is humanly solvable, and a difficulty scale that means something |
| **C** | a client producing a complete, identified event and surviving its own failures, with no backend |
| **D** | a running service that stores events and refuses to run wrong |
| **E** | the real routes and the real caching contract, running locally |
| **F** | `boxscorepuzzle.com` serving today's puzzle, monitored |
| **G** | an image a player sends in one tap that survives the trip and gives nothing away |

⚠️ **Each deliverable also says what it does *not* give**, in its own section. That half is the one that
gets skipped, and it is where the milestone's honest limits live — deliverable B does not produce a
difficulty threshold, F does not answer whether anyone passes it on, G does not produce a recruitment
rate.

---

## Where we actually are

⚠️ **Kept current rather than as written.** This table was a snapshot of the morning the plan was
written, and it stayed that way for a day while five of its rows stopped being true — which is the
defect v39-P3-01 found in `CLAUDE.md`, in the file people come to for the state of the work. **Last
checked against the tree: 2026-08-22, after v39.**

| | state |
|---|---|
| **Client** | landing, tutorial, board, keypad, hints, reference sheet, check, reveal, persistence — **built and tested** (283 browser tests) |
| **Packages** | schema 5, signed, four validation layers, `certify_for_publication()` — **built** |
| **Inventory** | **six reference puzzles** plus whatever `build_inventory.py` has produced; the calendar is the authority |
| **Calendar** | ✔ **built.** `boxscore_forge.calendar` — extend, void, replace, `for_serving`; committed to Git because it cannot be regenerated |
| **Batch generation** | ✔ **built.** `forge/scripts/build_inventory.py`, with `audit()` asserting era, placement and repeats |
| **`/today`** | ⬜ **does not exist.** `daily.js` reads the manifest and takes an id from the query string. **Group E** |
| **Device UUID** | ✔ **built.** `serve/engine/device.js`, its own key and its own lifetime |
| **Event upload** | ✔ **built.** `serve/engine/outbox.js` queues and drains; `report.js` reports uncaught errors |
| **Data layer** | ✔ **built.** `keep/`, 77 tests at 100% on both engines |
| **Share PNG** | ⬜ **does not exist.** The button is drawn and `disabled`. **Group G** |
| **Deployment** | ⬜ **does not exist.** `compose.yaml` is a dev server on a mounted tree, no image, no nginx. **Group F** |
| **Signed date pointers** | ✔ **built**, and ⚠️ **only the newest generation holds a complete schedule** — an older one was written before the later dates existed. That is what makes the newest generation the rotation's source |

### ✔ Three facts about the current code that shaped the plan — **all three closed 2026-08-22**

⚠️ **Kept rather than deleted, because they are why the groups are ordered the way they are.** Each one
now says what closed it; the reasoning underneath is what stops the next plan being written against the
documents instead of the tree.

**1. ✔ Closed — the publication path imported its loader from `discovery/`.** `write_reference_puzzles.py` does
`from measure import Loaded, load` — the SQL, the connection string, the era windows and the provenance
predicate all live in `discovery/difficulty-metrics/measure.py`, outside `mypy --strict` and inside the
ratcheted lint tree. The deferral is recorded in the file with its reason: **moving it is building the
inventory pipeline, not renaming a module.** That is group A, and it is the first subtask rather than a
cleanup at the end. ✔ *Done in A1: `boxscore_forge.pool`, `mypy --strict` clean, the ratchet down to 156.*

**2. ✔ Closed — `game.record()` had no date.** C7 in `CLAUDE.md` lists *puzzle_id, date, duration, hints, errors,
highest technique*. The record has `puzzle_id, duration_ms, hints, errors, failed_checks,
highest_technique, solved, assisted` — **no date of any kind.** A streak hangs off the calendar date and
an archive play is a different date from the puzzle's; neither is recoverable later, and C7 is
irreversible. **This is a group C subtask and it is cheap now.** ✔ *Done in C2: both dates, on two
different clocks, plus the device id and a null-and-claimable `account_id`.*

**3. ✔ Closed — `build_pack.py` targeted chain and asserted fifty.** The generator targets a stall
count; the pack producer was the last chain-targeted code in the tree, and group B could not start
against it. ✔ *Done in B1: re-axed onto stalls, and the fifty came from the superseded design.*

---

## Group A — inventory and calendar

**Blocks everything.** Nothing downstream can be tested against one day's puzzle.

### ✔ A1. Promote the loader out of `discovery/` — **done 2026-08-22**

- ✔ **A1.1** Move `Loaded` and `load()` into `forge/src/boxscore_forge/` (a `pool` module), with the SQL,
  the era windows, the provenance predicate and the caps. ✔ *Done: `boxscore_forge.pool`.*
- ✔ **A1.2** Fix the signature that lies: `gated: bool = False` while the gate always applied. It is
  recorded in the docstring; make the parameter mean what it says or delete it. ✔ *Done: the default is `True`; deleting it recorded as a deferral with its price.*
- ✔ **A1.3** Bring it under `mypy --strict` and un-ratchet those lines from the discovery baseline. ✔ *Done: `mypy --strict` clean; ratchet 168 -> 156.*
- ✔ **A1.4** Leave `discovery/` importing the promoted module, **not a copy.** Every discovery script that
  calls `load()` must keep working — that is the regression surface. ✔ *Done: `measure.py` re-exports and `test_the_shim_exports_what_is_imported.py` asserts every name resolves.*
- ✔ **Met.** **Done when:** `write_reference_puzzles.py` has no `sys.path` insert into `discovery/`, the suite is
  green, and the discovery scripts that load still run.

✔ **Done.** `boxscore_forge.pool`; `measure.py` re-exports and 33 scripts are untouched;
`test_the_shim_exports_what_is_imported.py` parses every `from measure import` in the tree and asserts
each name resolves *and is the same object* the pool holds. It caught a real break on its first run —
`ruff --fix` had removed `ZERO_DENSITY_GATE` from `measure.py`, correctly, and one script imported it
through there.

⚠️ **What `mypy --strict` found once the code was in `src/`, invisible in `discovery/` for months:**
`_sum` was annotated `-> object` and fed three `Direction` arguments expecting `BattingLine`,
`BatterFootnotes` and `PitchingLine`. **The annotation was hiding three real type errors rather than
passing them.**

⚠️ **A1.2 resolved by counting first: 37 call sites, all `gated=True`, none `False`.** The default is
`True` now — an omitted argument must not silently widen the population to nine parts unshippable
boards. Deleting the parameter is recorded as a deferral with its price (37 call sites in scripts that
need a database), not as an oversight.

### A2. Batch generation

- ✔ **A2.1 done 2026-08-22.** `boxscore_forge.produce.produce()` is the per-board core — promoted out
  of `write_reference_puzzles.py` so both producers share one definition — and
  `scripts/build_inventory.py` is the batch driver. `boxscore_forge.publication_key` holds where the
  signing key comes from, for the same reason.
- ✔ **A2.2 done 2026-08-22 — and the answer removes work rather than adding it.** Two samples, 48
  directions, **48 boards: the pipeline loses none.** So the batch does not over-sample and needs no
  retry machinery. **~22 minutes for 150 boards.** What sizes the draw is duplicate games — `load()`
  returns both directions of one game about 10% of the time and the calendar refuses the second (§7) —
  so **draw ~1.15× the dates**. ⚠️ **235 attempts and the publication gate refused none**, recorded in
  `todo.md` as an open question about the gate rather than a clean bill of health.

  **✔ Confirmed at volume 2026-08-22:** the real 150-board run spent 566 more attempts and the gate
  refused **none of them**. Roughly **716 attempts, zero certification refusals**, which stops being a
  small-sample result.
- ✔ **A2.3 done.** The calendar is written after every assignment; a test interrupts the run at board 4 of 10 and requires the three already made to be on disk. *Previously:* ⚠️ **NOT done, and the successful run hides it.** `build()` writes the calendar **once, after the
  loop**. A crash at board 140 of 150 leaves 140 signed packages on disk and **loses every assignment**,
  because nothing was written yet. What works today is the *short-run* case — the run finishes, keeps its
  work, and exits non-zero (v38-P2-01) — which is not the same thing as surviving a crash. **Checkpoint
  the calendar as it goes.**
- ✔ **A2.4 done.** The same slice built into two calendars must produce the same ids in the same order. *Previously:* ⬜ **not asserted.** §21 needs the same game to yield the same puzzle id, and nothing runs a slice
  twice and compares. Trusting `puzzle_id()` is the thing the item says not to do.
- ✔ **Met** — two samples at 100% yield, 150 boards in 24 min, and running the window twice adds nothing. **Done when:** one command produces N validated packages with a recorded survival rate, and running it
  twice produces no duplicates.

### ✔ A3 (core). The calendar module — **done 2026-08-22**

`boxscore_forge.calendar`, written test-first, 26 tests, **100% coverage**, and every rule tested by its
refusal. `docs/calendar.md` is the artefact it implements. §21's two requirements turn out to be one
mechanism, and *one game, one puzzle* runs over the whole calendar including voided entries.

⚠️ **A guard of mine could not fail, and mutation is what found it.**
`test_an_existing_entry_is_never_replaced` used `next(...)` over a sorted list, so with the skip removed
from `extend()` the calendar held two entries for one date and the test stayed green — `sorted` is
stable and the original came first. Six mutations checked in total; all six now go red.

**What is left of A3** is the builder that feeds it: the weekday curve (deferred, see below), the
pre-1950 allowance, and the quota assertions.

### A3. The calendar

- ✔ **A3.1** The date → puzzle assignment, persisted, **extends and never rewrites** (§21). A played date
  cannot change; a future defective puzzle is replaced, a past one is marked void and left in place. ✔ *Done: `boxscore_forge.calendar`, 100% covered.*
- ⬜ **A3.2 deferred — operator's decision 2026-08-22: build the calendar with no curve.** Nobody knows
  which rung is Monday until the hand-solve pack comes back, and §21 makes applying a curve later a
  *reordering of future dates* rather than a rebuild. The `difficulty` field is absent rather than
  guessed (§7). Originally: difficulty by weekday — easy Monday, hard Saturday (§31) — and vary which relation families a
  level opens with, so no two Tuesdays start the same way.
- ✔ **A3.3 done.** `extend()` refuses a game the calendar has already spent, over the whole book and
  including voided entries. Verified on the real batch: **150 dates, 150 distinct games.**
- ✔ **A3.4 done, after violating it by seven times.** The draw is per era now and the dates are spread; the rebuilt calendar is 7 pre-1950 of 150 at 21 and 22 days apart. *The finding, kept because the shape recurs:* ❌ **the inventory built earlier that day violated it by seven times.**

  §6 is explicit and still decided: *pre-1950 boards must not exceed 5% of what the player sees*,
  roughly eighteen a year, so that Ruth is an **event rather than the scenery**. The batch is
  **51 of 150 pre-1950 — 34%, against a ceiling of 8.**

  ⚠️⚠️ **It is not bad luck, it is the sampler.** `load()` draws *n per decade* over twelve decades, so
  a stratified draw **guarantees** the pre-war half is over-represented: 1910s through 1940s is four
  decades of twelve, and the quota allows one board in twenty. **A calendar built from a decade-flat
  draw can never satisfy a decade-weighted quota by accident.**

  ⚠️ **Nothing caught it.** Not the gate, not the four layers, not the calendar's own refusals — a
  board from 1913 is perfectly valid and so is a calendar full of them. It was found by printing the
  decade distribution and reading it, which is the only thing that has ever found this class here.
- ✔ **A3.5 done.** `audit()` refuses a calendar over the era ceiling or carrying a repeated game, date or puzzle id, and it runs before the manifest is written. *Previously:* ⬜ **not implemented, and its absence is exactly why A3.4 went unnoticed.** The item says assert
  the quotas after construction rather than print them and believe them. There is no assertion, so the
  run reported `assigned 150 of 150` and was wrong about what it had assigned.
- ✔ **Met** — 150 dates, 150 games, 7 pre-1950 at 21 and 22 days apart, `audit()` clean. **Done when:** five months of dates are assigned **within every quota**, the guard rejects a second
  direction of a published game, and re-running the builder changes nothing.

### A4. Packaging in bulk

- ✔ **A4.1** Generation directory and manifest at 150+ puzzles. The manifest is schema 1 and lists every
  id; check that shape still makes sense at scale, since the client fetches it uncached on every load. ✔ *Done: `write_manifest()` over the files on disk, 150 packages.*
- ✔ **A4.2** ⚠️ **The manifest must not leak the future.** It currently lists every published puzzle. With
  a calendar, listing tomorrow's id is handing out tomorrow's puzzle — the file is public and
  unauthenticated (§23). **Decide what the client is allowed to see.** ✔ *Done: decided and reframed: today's and yesterday's are public, everything else is not (`docs/calendar.md`).*
- ✔ **A4.3 done.** 150 packages signed with the pinned key; `boxscore_forge.publication_key` refuses to
  return a key `serve` would not accept, and never prints private material.
- ⚠️ **A4 was reframed on 2026-08-22 and its output survives.** The question it answered — *what may the
  client see* — turned out to be the smaller half: it worried about **tomorrow** leaking, and **the past
  is the product**. The artefacts still fit: the generation manifest was already decided to be
  server-side rather than browser-facing, and the per-date pointers were already decided not to be
  deployed. **What changes is the daily step**, which copies **two** days out rather than one, and the
  public manifest, which lists those two.
- ✔ **A4.1 done.** The generation directory (`forge/inventory/<gen>`, 1.4 MB, median 9.7 KB a package),
  a signed `manifest.json` over the files **on disk**, and 150 signed per-date pointers in `days/`.
  *Previously:* ⬜ **partial — no manifest is written**, which stopped being true once A4.2 was decided.
- ✔ **Met** — 150 packages signed with the pinned key, manifest and pointers written after the audit. **Done when:** a generation of five months is written, signed, and verifies from a clean checkout.

⚠️ **A4 is not the end of group A.** What A1–A4 produce is one batch, built by whoever had the whole
pipeline in their head that week. **A5 is what makes it a process.**

### ⚠⚠ A6 — what v39 found in this group, after it was marked met (2026-08-22)

**Two P1s, both reachable through the documented procedure, and both invisible on the first batch**
because the first batch is one window built once. `docs/reviews/code_review_v39.md` has the report.

- ✔ **A top-up signed old dates into the wrong generation.** `write_pointers` stamped the generation it
  was currently writing onto **every** date, so the second run claimed generation-A dates lived in B —
  where their package does not exist. `Entry.assigned` had carried the right answer since the calendar
  existed and nothing read it. The parameter is **gone** now rather than corrected.
- ✔ **A retry granted itself a fresh era allowance.** The quota and the spacing were computed over the
  *gaps*, so A5's own instruction — *re-run it if it comes up short* — was the way to break A3.4: seven
  pre-1950 boards became thirteen, one day apart. `_era_plan()` plans over the whole window and
  reconciles with what the window already holds.
- ✔ **`audit()` now asserts placement, not only the count.** A3.5 closed the count; nothing checked that
  `spread()` had done its job, and seven early boards on seven consecutive days satisfy the ceiling and
  defeat exactly what it is for. **Counting is not placing** — the same sentence `spread()` was written
  under, one level up.

⚠️ **What this says about A being *met*.** It is: the deliverable exists and the first batch is real.
What the group had not been exercised on is its **second** run, which is the one the runbook describes
and the one nobody had done. A group is met against the work it did, not against every future call of
it — and that gap is where both P1s were.

### ✔ A5. The runbook — **written and followed literally, 2026-08-22**

**How to add new games to the app**, written for the person who will actually run it: **the operator,
three months later, having forgotten all of it.** That is not a rhetorical framing — §33 alerts below
three months of runway, so **the interval between two runs is measured in months by design**, and
whatever is obvious today will not be obvious then.

- ✔ **A5.1 Preconditions**, each one checkable before anything starts: the Retrosheet database reachable,
  the signing key present (⚠️ and **where it is not** — never in the repository), a clean working tree,
  and how much runway is left right now. ✔ *Done: run as written.*
- ✔ **A5.2 The commands, in order**, with **what each one prints when it is working.** A step whose success
  looks like silence is a step nobody can tell failed.

  ⚠️ **Three instances of exactly that, all from the first measurement run, all before it produced a
  number.** They belong in the runbook because each one cost minutes of not knowing whether anything was
  happening:

  1. **Python buffers stdout when it is not a terminal**, so the run printed nothing for eight minutes
     while working. Every line flushes now.
  2. **`load(n)` is `n` per decade**, over twelve decades — `--directions 12` asked for about 144
     directions. The option is `--per-decade` now. ⚠️ *A name that misdescribes a scale factor of twelve
     is the same defect as `gated: bool = False`: read far more often than it is passed.*
  3. **Piping a live run through `tail` withholds all of it until the process exits.** An instrumentation
     mistake rather than a script one, and the runbook has to say *do not pipe this* or the operator will
     conclude the command hangs. ✔ *Done: run as written; three silences recorded.*
- ✔ **A5.3 What to check before publishing**: the survival rate, the era share, the weekday spread, and
  ⚠️ **the one-game-one-puzzle guard's report** — the check no package can perform on itself. ✔ *Done: run as written.*
- ✔ **A5.4 What to do when the yield is short.** The likely outcome, not the exceptional one: the gate keeps
  11% of the pool. Say whether to widen the era window, lower the target, or run again — and ⚠️ **what
  must never be done, which is quietly dropping a rung to fill a quota.** ✔ *Done: written from the real refusal message.*
- ✔ **A5.5 How to deploy the new generation**, and **how to roll back.** ⚠️ Not near the daily rollover. ✔ *Done: **corrected by following it** - it would have published the archive.*
- ✔ **A5.6 Why re-running is safe.** §21: puzzle ids derive from the game, the calendar extends and never
  rewrites, so a run that half-finished is resumed rather than cleaned up. **State it explicitly** —
  somebody who is unsure whether a second run will duplicate things will hesitate at exactly the moment
  the runway is short.

⚠️✔ **Followed literally on 2026-08-22, and it changed step 5.** The deploy step said *copy the generation
directory to the VPS* and named only the manifest and the pointers as private — **the directory holds all
150 packages.** It would have published the archive: the hole `calendar.md` exists to close, reintroduced
in the instructions for closing it, and invisible while writing because every individual sentence was
true.

⚠️ **A runbook that has never been followed literally is a guess.** It gets executed once, from a clean
checkout, by doing exactly what it says and nothing the author remembers — and corrected wherever it was
wrong. **The same rule as every other instrument here: the version that has not been run is not evidence.**

⚠️ **And it will drift from the code**, because prose and commands are two places saying one thing. The
cheapest defence is that the commands it names are the ones a test invokes; at minimum, the runbook names
the scripts by path so a rename breaks a grep rather than nothing.

### ✔ Status 2026-08-22: **Deliverable A is met**

**Every A item is done except A3.2, which is deferred by the operator's decision**, and A3.2 is the
difficulty curve — it waits for the hand-solve pack and §21 makes applying it later a reordering of
future dates rather than a rebuild.

| | |
|---|---|
| **A1** loader out of `discovery/`, under `mypy --strict` | ✔ |
| **A2** shared producer, yield measured, resumable, deterministic | ✔ |
| **A3** calendar: extends, one game one puzzle, era quota sampled and asserted | ✔ (A3.2 deferred) |
| **A4** generation manifest and signed per-date pointers, access model decided | ✔ |
| **A5** the runbook, written **and followed literally** | ✔ |

**The inventory:** 150 dates, 2026-09-01 to 2027-01-28, 150 distinct games, 7 pre-1950 at 4.7% spaced 21
and 22 days apart, `audit()` clean, 24.1 minutes. Stalls 1–13 with a median of 9 across all twelve rungs,
so a later curve has material to reorder. **The runbook produces the next five months.**

⚠️ **What is still true and is not an A item:** the hand-solve gate has not run, so *these boards are
solvable by a person* remains an assumption. That is group B, and B3 is a gate on beta 0.

---

<details><summary>The earlier status, kept because the era finding is a shape worth finding again</summary>

### ⚠️⚠️ Status 2026-08-22: the batch ran and **Deliverable A is not met**

**What exists:** 150 dates, 2026-09-01 to 2027-01-28, one game each, 150 signed packages, 25.1 minutes
from 168 directions. Verified against the artefacts rather than the run's own summary — contiguous, no
holes, every date has a package, **zero game ids survive into what deploys**.

**What the difficulty spread looks like**, which matters because a later curve has to have material to
reorder: stalls 1–13 with a median of 9, and all twelve rungs represented. 39% of boards needed the
lineup clue. **11 of 150 (7%) depend on the batting-order family** — the first time that number has been
answerable at all, since `FAMILY_OF` gained the fifth family the day before.

**Why it is still not met, in order of weight:**

1. ❌ **34% pre-1950 against §6's 5% ceiling** (A3.4). The calendar has to be rebuilt or reweighted.
2. ⚠️ **No quota assertion** (A3.5), which is why the run said `150 of 150` and was wrong about what it
   had assigned.
3. ⚠️ **No crash resumability** (A2.3): the calendar is written once at the end.
4. ⬜ **No manifest** (A4.1/A4.2), **no idempotence assertion** (A2.4), **no runbook** (A5).

⚠️ **The 150 dates are assigned and committed, and that is deliberate.** §21 lets a *future* date be
replaced, so reweighting the eras replaces entries rather than rebuilding the file — and the calendar is
the one artefact here that cannot be recomputed, so having it on disk and in Git beats having it correct
and only in memory.

</details>

### ▶ Deliverable A — **five months of dated, signed inventory, and the runbook that produces the next five**

**Two things, and the second is what makes the first repeatable.**

**The inventory:** a generation directory and a calendar — roughly 150 validated packages, each assigned
to a date, signed, verifying from a clean checkout, with the one-game-one-puzzle guard refusing a second
direction over **everything ever published**.

**The runbook** (`docs/runbook-inventory.md`): how to add new games to the app, **followed literally once
before it is believed.**

⚠️ **The runbook is not documentation of the deliverable; it is half of it.** Five months of inventory
with no repeatable way to make more is a product with a five-month expiry date — and the moment it needs
running is the moment the inventory health check goes amber (F3), which is precisely when nobody wants to
be rediscovering how the generator is invoked. **§33's three-month alert is only useful if there is
something to do about it.**

**What it makes possible that nothing before it did:** every other group can be tested against a daily
game that lasts more than a day. Group B has an inventory to draw a sample from; E has something to
route `/today` at; F has something to deploy. **And the product stops having an expiry date.**

⚠️ **What it does not give:** any evidence that a person can solve these boards. Four validation layers
say the numbers agree with each other. **That is group B, and it is a gate rather than a follow-up.**

---

 ✔ *Done: written.*## Group B — the hand-solve gate

**Depends on A.** It draws from the shipping inventory. **It is a gate on beta 0** (`beta-0.md`), and it
is pass-or-stop rather than a rate.

### ✔ B1. Re-axis the pack producer — **done 2026-08-22**

- ✔ **B1.1 done.** `TARGETS` are stall rungs **(5, 8, 11, 12, four each)** and `WANTED` is 16, not fifty
  on the chain axis. **`build_pack.py` was the last chain-targeted thing in the tree**, and its own
  docstring had said so for weeks: *"the target variable is now stalls… this pack must not be printed
  until `erase` can take a stall target."* It can. Correcting the documents and leaving the producer
  would have been the visible half of a fix with the working half untouched.
- ✔ **B1.2 done.** `audit()` still asserts and its rejecting tests still pass; the two that named the
  chain axis in their own titles were renamed with it, so the retired word does not survive in the one
  place a reader checks what the pack measures.
- ✔ **Met:** the producer builds a stall-targeted pack and the audit rejects a missing rung — verified by
  reverting the rungs to chain and watching `test_a_pack_that_meets_every_quota` go red.

⚠️⚠️ **And the axis was the smaller half.** The pack called `erase()` **directly**, while production goes
through `erase_with_lineup_fallback` — and **39% of the boards in the live inventory needed that fallback
to reach their target.** A pack built without it grades a population the player never meets, and this is
the artefact that decides whether the boards are humanly derivable at all.

`CLAUDE.md`'s rule — *a sample that evaluates the board is rendered with the board's renderer, never a
copy of it* — applies to **producing** as well as rendering, and this is where it matters most. ⚠️ The
guard written the same morning covered `scripts/` and not `discovery/`, where the pack lives. **It covers
it now**, and both mutations go red: erasing directly kills the new guard, reverting the rungs kills the
quota test.

### ⚠️ What is left of B is the operator's, and B1 was what blocked it

**B1 was mine and it is done.** B2, B3 and B4 are afternoons of somebody solving boards by hand — the one
measurement in this project whose instrument is a person. **Until B1 landed the pack could not be built
at all**: it would have produced boards against a retired axis, or failed its own audit.

⚠️ **B3 is a gate on beta 0, not a step after it.** One board failing by hand stops the milestone.

### B2. Pack A — calibration, sixteen boards

- Rungs 5, 8, 11, 12, four each. Stall count off the page and in the sealed key. Formula strip with all
  five relations. Survey box with the 1–6 scale, the *how many times did you stop* line, and separate
  columns for **had to guess**, **tedious**, **boring**. Randomised order asserted by `audit()`. One
  board per game. Footnote line given. A final ranking sheet.
- ⚠️ **If rung 12 does not yield four boards, that is the finding** — reported, never quietly
  substituted with a lower target.
- ⚠️ **Not built at the end of a long run.** It gets a fresh session: the instrument is a person, the key
  is sealed, and a board printed wrong is an afternoon spent on the wrong thing.

### B3. The derivability sample — the gate

- **B3.1** Sheets with no survey and no ranking: *did it solve without guessing*. Cheap per board, which
  is what makes a larger N affordable.
- **B3.2** Stratify over what could break the assumption: stall rungs weighted hard, era, roster shape
  (⚠️ especially boards that only became eligible when the pitcher cap went to six), and boards that
  depend on the **batting order** family.
- **B3.3** ⬜ **N and the stratum quotas are open**, and `audit()` asserts them after selection.
- **Done when:** every board in the sample solved by hand without guessing. **One failure stops the
  milestone** — it falsifies the assumption the publication rule rests on.

### B4. The stranger's ten

- Ten boards across the curve, solved by somebody who knows baseball and nothing about this project. It
  is the one contrast the operator cannot give himself. **Calibration, not a gate.**

### ▶ Deliverable B — **a verdict on whether the inventory is humanly solvable, and a difficulty scale that means something**

Two artefacts. **The gate's verdict:** every board in the stratified sample solved by hand without
guessing — or a stop, with the board that failed. **And Pack A's sheets plus the ranking**, which is the
only thing that tests whether the stall scale corresponds to felt difficulty.

**What it makes possible:** shipping at all. Until this exists, *the puzzle is solvable* is an assumption
the four layers cannot check.

⚠️ **What it does not give:** a difficulty threshold. The operator is a sample of one with complete
command of the identities; what he finds easy will be easy for very few. **The absolute question is
answered by beta 0's own event records**, which is group C.

---

## Group C — the client: identity, the event, and errors

**Can start in parallel with A.** ⚠️ **C1 is the one thing with an asymmetric cost — every event before
it exists is unattributable, and C7 is irreversible.**

### ✔ C1. The device UUID — **done 2026-08-22**, `serve/engine/device.js`

- ✔ **C1.1 done.** A random UUID in `localStorage`, created once, surviving reloads. ⚠️ `crypto.randomUUID`
  needs a secure context and `http://` on the local network is how this board gets looked at during
  development, so there is a `getRandomValues` fallback and a `Math.random` one below it — **not
  cryptographic and it does not need to be**: the id names a device to a counter, authorises nothing, and
  what it must be is unlikely to collide.
- ✔ **C1.2 done.** ⚠️ Its own key and its own lifetime — **not inside the per-puzzle session**, which is keyed
  `boxscorepuzzle.session.v1.<id>` and is disposable.
- ✔ **C1.3 done.** ⚠️ Survive the storage failing. `browserStorage()` already handles a refused storage; a device
  with no storage plays anonymously rather than not at all (§23).
- ✔ **Met**, and a refused storage returns a fresh id each call — the honest outcome, since there is
  nothing to tie those events to. Previously: the UUID persists across reloads and across finishing a puzzle, and a blocked storage
  does not break the game.

### ✔ C2. The event record gains what C7 promised — **done 2026-08-22**

- ✔ **C2.1 done.** ⚠️ **Add the date.** C7 lists it and `record()` has none. Both the puzzle's calendar date and
  the date it was played — they differ for archive play and neither is recoverable later.
- ✔ **C2.2 done.** Add the device UUID, and the account field as `null` — the schema is claimable from the first
  row (`data-layer.md` §6), and that cannot be retrofitted.
- ✔ **Met.** 244 browser tests. Previously: a finished game produces a record carrying identity and both dates, asserted in a test.

⚠️⚠️ **Three things the verification found, and they belong here because each is a shape rather than a
bug.** The obvious timezone assertion — that `localDate` differs from `toISOString` — **passes or fails on
the machine's zone**, so it reports the environment rather than the code. **The mutation harness read an
empty or errored run as green**, which is absence-of-a-check-reading-as-a-pass *inside the harness written
to check for it*, and it made four mutations look survivable. And the identity test **supplied every
field**, so a `playedOn ?? calendarDate` fallback — the exact confusion the two fields exist to prevent —
passed unnoticed: **a test that gives every field cannot see a wrong default.**

⚠️ **`calendar_date` is `null` until `/today` exists** (E1). Null is the honest value; the tempting
alternative is the player's local date wearing the calendar's name, which is wrong for archive play and
across every rollover.

### ✔ C3. Upload, queued and offline-first — **done 2026-08-22**, `serve/engine/outbox.js`

- ✔ **C3.1 done.** ⚠⚠ **Write first, send after, and delete only on confirmation.** The item is in
  `localStorage` before any request is made and leaves only when the server names its id, so a phone
  swiped away mid-flight still holds it. `add()` is synchronous, kicks a drain and does not await it.
- ✔ **C3.2 done.** `follow()` drains on `online` and on `visibilitychange` — ⚠️ **not `beforeunload`**,
  which a phone does not fire when a tab is discarded.
- ✔ **C3.3 done.** Every item carries the id `keep` deduplicates on. ⚠️ **For events it is the device
  and the puzzle rather than a fresh UUID**, so a reopened board offers an id the queue already holds:
  the duplicate is impossible rather than deduplicated afterwards. **The cost is written down where the
  id is** — a device records one event per puzzle ever, so a deliberate replay of an archived board
  records nothing, and that is the line to change if replays are ever meant to count.
- ✔ **Done, and verified in a browser rather than only asserted:** solving with the endpoint absent
  leaves one queued event; reloading reopens the board finished, sends **one** POST per queue, and the
  event id is the same one. §23 held throughout — the 501 changed nothing about the game.

⚠️⚠️ **Two decisions inside it that are easy to get wrong in the safe-looking direction.**

**A refusal the client cannot fix by waiting is dropped; everything else stays**, and the line is only
400, 413 and 422 — *the server understood the item and refused its content*. The tempting
simplification is *any 4xx is permanent*, and it would mean **a 404 discards every event recorded
before F wires the proxy**, silently. That is the one loss C7 can never recover from.

**One malformed item must not hold the queue behind it.** `keep` refuses a batch whole — correctly —
so a single bad record would block every good one after it forever. A refused batch is retried item by
item, which finds the poisoned one and keeps the rest.

⚠️ **And a bug the tests found rather than the design:** a drain arriving while another was in flight
answered *nothing to do*, which is what "two at once must not send twice" seemed to ask for. But `add()`
kicks — so **an event queued during a flight was never drained**, and sat until the next visit. A call
arriving mid-flight now books one pass behind the current one.

### ✔ C4. Uncaught client errors — **done 2026-08-22**, `serve/engine/report.js`

- ✔ **C4.1 done.** Both handlers, carrying device id, message, stack, viewport and user agent. ⚠️ **The
  path, never the query string** — a query is the one part of a URL that carries whatever somebody put
  in it, and `location.href` was the obvious field and the wrong one.
- ✔ **C4.2 done.** Every path is inside a `try`, nothing is awaited, nothing calls `preventDefault`.
- ✔ **C4.3 done, by two measures.** A cap per page load **and** a signature, because the cap alone would
  not stop the first five reports being five copies of one fault — which is the shape a render loop
  actually produces.
- ✔ **Done, and verified in a browser:** a thrown error and a rejected promise both land in the queue
  with the right fields and no query string, and both survive a reload with the endpoint refusing.

⚠⚠ **The two "never throws" cases were hollow until a mutation run said so.** An exception thrown
inside a DOM listener does **not** propagate out of `click()` or `dispatchEvent()` — it is reported to
the window and the caller carries on — so *press the button and assert something* stays green whatever
the handler did. What caught the mutation was the browser runner treating any page error as fatal,
which is a real signal and a poor one to rely on: **the suite dies with no named failure.** The cases
now install a window error listener, mark the escape handled and assert on it by name.

⚠️ **And the mutation harness read those two dead runs as survivals**, because it looked for `FAIL`
lines and a killed suite prints none. Same shape as the run that reported four survivors while `uv` was
locked and the suite never ran: **a run that died is not a run that passed.**

### ✔ Deliverable C — **a client that produces a complete, identified event and survives its own failures, with no backend at all**

A finished game yields a C7 record carrying the device UUID, an account field that is `null` and
claimable, and **both dates**. It queues in `localStorage`, drains when there is a connection, and
delivers exactly one event across a reload mid-flight. Uncaught errors report themselves and can never
block the play path.

**What it makes possible:** the moment a data layer exists, **events recorded before it existed still
arrive**, carrying the identity they were created under. That is the whole reason this group precedes D.

⚠️ **What it does not give:** anywhere for the events to go. They accumulate locally until D exists —
which is the design working, not a gap.

---

## Group D — the data layer

**Depends on C for its shape and on nothing else.** Designed in `data-layer.md`; this is building it.

### ✔ D1. The service — **done 2026-08-22**, `keep/`

- ✔ **D1.1 done.** One API, engine behind an interface. Postgres in production, SQLite for development and tests.
- ✔ **D1.2 done.** ⚠️ **One contract suite parameterised on the backend**, not two suites. A suite green on
  SQLite says nothing about Postgres and says it convincingly.
- ✔ **D1.3 done.** Shared-token auth that **fails closed at startup** — no token, no service. Constant-time
  comparison; the token never in a log or a URL.

### ✔ D2. Schema and migrations — **done**, `keep/migrations/001-initial.sql`

- ✔ **D2.1 done.** Events, devices, and the claimable subject: device UUID always, account when one exists.
- ✔ **D2.2 done.** ⚠️ **Migrations are manual; startup refuses an unexpected schema version.** Neither half works
  alone — manual without the check gives silent drift, the check without manual gives a deploy the power
  to alter data at 3am.
- ✔ **D2.3 done.** §35 only: no real name, no IP, no geolocation, no filled cells.

### ✔ D3. Endpoints — **done**

- ✔ **D3.1–D3.3 done.** Event upload. **D3.2** Client error reports. **D3.3** Health, running
  `SELECT 1 FROM <a known table> LIMIT 1` — ⚠️ testing that the query does not error, **not** the row
  count.
- ✔ **Met, and verified against a real Postgres in Docker rather than skipped: 77 tests, 100% coverage.**
  Previously: the contract suite passes on both engines, the service refuses to start without a token
  and against a wrong schema version, and health goes red when the database is stopped.

### ✔ Status: **Deliverable D is met**

**`keep` exists**: `keep/` beside `forge/` and `serve/`, **no runtime dependencies**, three routes, 77
tests at 100% coverage across both engines. ⚠️ Its Postgres arm **fails rather than skips**: without a
server `PostgresStore` is 80% covered and the suite is 92%, under its own floor **while looking green**,
so the floor only held on a machine that happened to have Docker running.

⚠️⚠️ **The mutation that survived is the one worth keeping.** `INSERT OR REPLACE` keeps exactly one row
too, so **every count-based test passed with it** — while it overwrites the original with the retry's
values. A queued event whose clock kept running would rewrite what happened. **C7 stores what happened
and the first telling is the one that did**, so there is now a test that a retry never rewrites what it
is retrying — pinning both engines to the same *meaning* rather than the same row count.

⚠️ **The token is checked before the schema, and that order is asserted.** A missing token is the failure
whose absence is silent; a wrong-shaped database at least shows up in a query error.

⚠⚠ **v39-P2-01, closed 2026-08-22 — one bad row was an outage.** A failed statement leaves the Postgres
transaction *aborted*, and Postgres then refuses every later statement on that connection. `keep` reuses
one, so a single out-of-range integer took down every upload, every error report **and the health
check**, until the process was restarted. Every statement rolls back and re-raises now — re-raises,
because rolling back and reporting success would make a lost write look like a stored one and the client
would drop it from its queue on the strength of that. The column's range is checked at the boundary too,
so the ordinary cause never reaches the driver.

⬜ **What is still missing there, and it is the operator's call:** `CLAUDE.md` asks for a *sanity check
on client-reported durations so absurd values do not corrupt percentiles*. What exists is the column's
range — twenty-five days — which is a fact about the schema rather than a judgement about the game. A
ceiling on plausible play is a number that shapes the product (§7).

⬜ **What is not built here and belongs to F:** the Dockerfile, and the container running with its port
unpublished.

### ▶ Deliverable D — **a running service that stores events and refuses to run wrong**

The data layer, against the Postgres already on the VPS, with a contract suite **green on both engines**.
It will not start without its shared token, will not start against an unexpected schema version, and its
health endpoint goes red when the database is stopped rather than when the container dies.

**What it makes possible:** the events from deliverable C have a destination, and the error reports have
one — so beta 0 stops being deployable-blind.

⚠️ **What it does not give:** any of the subscription side. No accounts, no `canAccess()`, no Stripe.
Those are beta 3 and the schema is shaped so they are an addition rather than a migration.

---

## Group E — serving for real

**Depends on A** (there is a calendar to serve) **and on D** (there is somewhere to post).

⚠⚠ **Start with E1b, and the numbering is left alone rather than renamed.** E1b is what enforces the
access model, and everything else in this group is built on top of *which files exist on which path* —
so writing the routes first means writing them before knowing what they are allowed to reach. It is also
the part whose failure is worst: **a rotation that fails once leaks the archive one day at a time,
silently and permanently**, because anything fetched once is gone. The routes can be wrong and fixed;
this cannot.

*(E1 keeps its number because `docs/` and the review history already refer to it. The order of work is
E1b, then E1, then E2, then E3.)*

### ⚠️⚠️ E1b. Two public paths, and the rotation that keeps them two — **do this first**

**The access model changed while group A was being built** (`docs/calendar.md`). Static delivery (§23)
and paid access (§9) are in tension, and the resolution is **two paths rather than one**:

- **Today's and yesterday's packages are public static files.** Unauthenticated, cached, backend-down
  safe. §23 unchanged.
- **Everything else is on no public path.** An endpoint checks the subscription before returning a past
  puzzle. §9 becomes enforceable for the first time.

⚠️ **Yesterday is deliberate and is not generosity**: somebody starting at eleven at night loses their
work at midnight otherwise. **Two days is not an archive**, so it does not compete with what is sold.

- **E1b.1** The rotation: when today arrives, **the day before yesterday leaves the public path.**
- **E1b.2** ⚠️⚠️ **A rotation that fails once leaks the archive one day at a time** — slowly, silently,
  and permanently, since anything fetched once is gone. **The inventory health endpoint asserts the
  public path holds no more than two packages** and Kuma watches it (F3).
- **E1b.3** The public manifest lists **those two**. The full generation manifest stays behind the wall
  as the deployment's integrity record.
- **E1b.4** ⚠️ `canAccess()` is a **display** decision. It runs in the browser over files the browser
  can already fetch. **The enforcement is which files exist on a public path**, and a reader of C8 could
  reasonably believe otherwise.

✔ **Decided 2026-08-22: yesterday is playable and does not count for the streak** (`docs/calendar.md`,
and §27 beside the grace day). **The two rules have to be read together** — the window is meaningless
without knowing what it does to a streak, and *playable* and *counts* are different things. Two
forgiveness mechanisms stacked make a streak nearly unbreakable, and an unbreakable streak stops being
worth keeping.

⚠️ **E1b.5 follows from it and is code, not prose:** a game finished on yesterday's board records its
event like any other — C7 stores what happened — and the streak calculation is what excludes it. The
event carries **both dates** already (C2), so nothing new has to be stored for this to be computable.

### E1. `/today` and `/p/<id>` — **second, after E1b**

- **E1.1** C6: `/p/<id>` canonical, `/today` redirects. `daily.js` currently takes an id from the query
  string — that is development scaffolding and it goes.
- **E1.2** ⚠️ **The engine still does not know what day it is** (C4). A loader decides, server-side.
  ✔ **And which clock it decides with is settled**: `docs/calendar.md` — the day rolls at **08:00 UTC**,
  a fixed `UTC-8`, which is 03:00 Eastern and midnight Pacific in winter. §36 carried this open as *local
  midnight or UTC* and **UTC is the worst answer available**: it lands at 20:00 Eastern, so a player who
  sits down at 19:45 loses the board fifteen minutes later. The forge already computes the same date
  (`serving_date()`); `serve` spells the offset again, which §33 prescribes and no test can check across
  the two trees.
- **E1.3** Everyone gets the same puzzle on the same date — **never derived from device-local state.**

### E2. The caching contract

- **E2.1** `manifest.json` never cached; `<generation>/<id>.json` cached for a year (it is immutable).
- **E2.2** ⚠⚠ **The enforcement is the absent id; the cache rule is the belt.** Packages are named by
  an opaque id and the public manifest lists **two**, so tomorrow's puzzle cannot be requested by anyone
  who cannot name it — and no intermediary or CDN can prefetch a URL it cannot construct. **Cache only
  the current day, never the week** on top of that.

  ⚠️ **Written in that order deliberately.** The other way round, the cache header looks like the thing
  holding the line, and the next person to meet a slow first load relaxes it believing the exposure is a
  cache setting.

### E3. nginx

- Server block, TLS via certbot, rate limit per IP **without persisting IPs**, and the data layer
  reachable only on the internal network.

### ▶ Deliverable E — **the real routes and the real caching contract, running locally**

`/p/<id>` canonical and `/today` redirecting, with the day decided **server-side** and never from
device-local state — everyone gets the same puzzle on the same date. `manifest.json` never cached,
`<generation>/<id>.json` cached for a year, and **only the current day cached ahead**.

**What it makes possible:** what runs on the laptop is now the shape that will run on the VPS, so
deployment is moving a known-good thing rather than discovering the difference in production.

⚠️ **What it does not give:** a live site. Everything here is still on `localhost`.

---

## Group F — deployment

### F1. Images

- **F1.1** A Dockerfile for `serve` — ⚠️ **`serve/` only.** Generator code must never reach the VPS.
- **F1.2** A Dockerfile for the data layer.
- **F1.3** No secrets in images. Containers unprivileged. The data layer's port **not published**.
- **F1.3b** ⚠⚠ **nginx proxies `/api/events` and `/api/errors` to `keep`, adding the shared token.**
  The client posts to `serve` because the browser must never reach `keep` — its port is unpublished and
  the token must not travel to a browser (`data-layer.md` §4). **Until this exists the two paths 404**,
  which is exactly why a 404 leaves the queue intact: every event and error recorded before deployment
  is waiting to be delivered by the first visit after it, and dropping them would be permanent.
- **F1.4** ⚠️ The VPS holds the **public** signing key. The private key never leaves the laptop.

### F2. The VPS

- DNS record, certbot, compose file, the existing nginx and Postgres. ⚠️ **Do not deploy near the daily
  rollover**, and have a rollback that is one command.

### F3. Health checks in Uptime Kuma

- Free daily · subscription · data layer (proxied — ⚠️ **unreachable is unhealthy**, never 200 with
  *unknown*) · **puzzle inventory**, which is the one nobody would think of: `serve` can be perfectly up
  with an empty directory. Threshold in one place, status only, no detail.

### ▶ Deliverable F — **boxscorepuzzle.com serving today's puzzle, monitored**

The site live over TLS on the operator's domain, `serve` and the data layer in their own containers on
the existing Docker network, the data layer's port unpublished, and **four Uptime Kuma checks** — the
free daily, the subscription side, the data layer proxied, and the puzzle inventory's runway.

**What it makes possible:** friends and family can play. This is the first moment the product exists
outside the laptop.

⚠️ **What it does not give:** the answer to the milestone's larger question. At this point beta 0 can
tell you whether people play and whether they come back. **Whether they pass it on is group G**, and it
is why G cannot be cut for time.

---

## Group G — the share

**Last to build, and ⚠️ it does not get cut** (`beta-0.md`). Fifth is a dependency — the PNG draws from
the finished game — not a priority.

### G1. The image

- **G1.1** ⚠️⚠️ **It is not a picture of the reveal.** The reveal prints names, teams and date;
  screenshotting it publishes the whole answer. §7: never the solution, never player names.
- **G1.2** ⚠️ **Replace the values first, then blur.** The blur is typography, not security — deblurring
  is solved and the glyph set is ten digits in a known typeface. An implementation that blurs real values
  is broken and looks identical to one that is not.
- **G1.3** The time and the failed-check count, **using the same catalogue keys as the reveal** — one
  number must not have two names in the artefact whose purpose is comparison.

### G2. One tap

- `navigator.share` where it exists, clipboard where it does not. **Any friction here is friction on the
  only growth mechanism the product has.**

### G3. ⚠️ Verified by sending, not by generating

- **G3.1** Send it through **WhatsApp, iMessage and X**, open it on a real phone, look at what arrived.
- **G3.2** ⚠️ **A local harness supplies the compression, the colour profile, the aspect ratio and the
  scaling** — every property under test. Generate-and-inspect is what every other visual check in this
  project has failed at.
- **Done when:** the image survives all three apps intact and a recipient who has not played learns
  nothing about the board.

### ▶ Deliverable G — **an image a player sends in one tap that survives the trip and gives nothing away**

A PNG carrying the grid, the time and the failed-check count in the reveal's own words — **not a picture
of the reveal**, with values replaced before any blur — shared through `navigator.share` in one tap, and
**verified by being sent through WhatsApp, iMessage and X and opened on a real phone.**

**What it makes possible:** beta 0 answers the question it exists for. §20 calls the shared grid the main
growth channel, and this is the only chance to test it before a paying product rests on it.

⚠️ **What it does not give:** a recruitment rate. The recipients are friends of friends. *Does the
artefact survive the trip* is fully answered here; *does it recruit* is not, and the two must not be
reported as one verdict.

---

## The order, and what can overlap

```
A ──────────────────────────────► B (gate)
│                                  │
├─► C (client) ──► D (data layer) ─┤
│                     │            │
│                     ▼            ▼
└──────────────► E (serving) ──► F (deploy) ──► G (share)
```

- **A is the critical path.** B, E and F all wait on it.
- **C can start today** and should, because C1's cost is asymmetric.
- **D depends on C** only for the event's shape.
- **G is last and exempt from cutting.**

⚠️ **Two things gate the milestone rather than merely being in it:** B3 — one board failing by hand stops
everything — and G, which cannot be dropped for time.

---

## What was open before starting — four of five closed

| | |
|---|---|
| ⬜ **B3's N and stratum quotas** | **still open** (`beta-0.md` scope question 1). It is a gate on beta 0, and the number is the operator's |
| ✔ **A4.2 — what the manifest may reveal** | closed, and the first answer was the smaller half. The manifest stopped listing the future; **the past is the product**, so the enforcement is which files are on a public path — today's and yesterday's, nothing else (`docs/calendar.md`) |
| ✔ **The data layer's name** | `keep` |
| ✔ **Whether SQLite is supported or only convenient** | a development convenience, **not supported**; a difference between the engines is a bug in the *tests* (`docs/keep-api.md`) |
| ✔ **The API surface** | `docs/keep-api.md`, written before the service rather than after |

---

## What is open now — last checked **2026-08-23**

⚠️ **Only genuinely open items belong in this table.** A ✔ row under a heading that says *open* is the
same defect one level down, and there was one here.

| | whose call |
|---|---|
| ⬜ **B3's N and stratum quotas** | the operator's. **It gates beta 0** |
| ⬜ **A plausible ceiling on a reported duration** | the operator's (§7). `CLAUDE.md` asks for the sanity check and it does not exist; what `keep` has is the column's range, which is twenty-five days. `docs/reviews/todo.md` |
| ⬜ **Event retention** | indefinite because nobody has decided otherwise, recorded so the absence is not read as a decision (`docs/keep-api.md`) |
| ⬜ **A second payment processor** | undecided, not rejected: *none until there is evidence of a blocked customer* |

✔ **Closed since this list was written**, and recorded so neither is reopened by someone reading an old
copy: **what clock defines the day** — the day rolls at 08:00 UTC, a fixed `UTC-8` (`docs/calendar.md`,
§36) — and **whether yesterday counts for the streak** — it does not. ⚠️ The second is *decided and not
built*: E1b.5 is the code and it is not written. **Decided and built are different columns**, and
collapsing them is how a plan starts describing itself instead of the tree.
