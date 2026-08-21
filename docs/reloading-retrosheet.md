# Reloading the Retrosheet dataset

**The scenario: an external pipeline reloads every `dbo.retro*` table.** That pipeline is not part of
this repository and this document does not describe it. It describes **what this project has to do
around it**, because two things it owns do not travel with the tables, and one guarantee quietly
depends on the tables not changing.

Written after measuring the live database rather than from the design. Where a check is a report
rather than a gate, it says so — that distinction is the difference between a procedure and a hope.

---

## What the pipeline does not carry

**`dbo.retroGameProvenance` is not a Retrosheet table.** It is built by this repository, from the zips,
and the pipeline will not produce it. Nothing else here is derived from the database at load time — the
test suite reads committed JSON, not SQL, so **no test breaks because the dataset moved**, and that is
worth knowing before spending an afternoon on the wrong thing.

⚠️ **The provenance table is the only thing standing between the pool and 3,451 reconstructed games.**
Its whole information content is `is_deduced`. Deduced games are reconstructions from partial
information — §32 excludes them because reconstructions are where boxscores that do not balance come
from — and they are **indistinguishable from real ones by the time the data reaches SQL Server**,
because the DGL loader concatenates `<season>*.E??` into one `<season>.EVE` and the file of origin is
gone. The zips are the only place that distinction still exists.

*(The `source_type IN (...)` half of the gate excludes nothing and never has: all 1,872 `EVR` games
lack a `retroGameLogs` row and the pool query joins that table, so the join already excludes them
completely. Recorded in `docs/reviews/todo.md`; it does not affect this procedure.)*

---

## The one hard coupling: the zips, not the load order

`load_provenance.ps1` **never queries `dbo.retro*`**. It reads `-ZipDirectory` and nothing else. So:

- **Before or after the pipeline runs makes no difference.** There is no ordering constraint.
- **Both must come from the same download.** This is the whole risk. A stale zip directory produces a
  provenance table that is internally perfect, passes every guard the loader has, and **describes a
  different dataset** — internal consistency without correspondence, which is this project's recurring
  defect and not a hypothetical one.

Default: `C:\Users\aperd\Documents\DGLv2\retrosheet\downloads\zip\events-reg` (116 zips today). If the
pipeline loads from anywhere else, pass `-ZipDirectory` explicitly to match it.

---

## Before the reload

**1. Is the hand-solve pack still being solved?**

⚠️ `discovery/hand-solve/` holds boards printed from specific games with a sealed answer key. A reload
can change a board underneath a key that is already printed, and the pack is the §22 launch gate for
human derivability — a wrong key does not fail loudly, it produces a wrong measurement of the one thing
no test can check. **Finish the pack, or treat it as void and rebuild it after.**

**2. Keep the zips the pipeline loads from.** Not a copy of some earlier download. The same files.

---

## The procedure

**3. Let the external pipeline load `dbo.retro*`.**

**4. Rebuild provenance, dry first.**

```bash
pwsh discovery/retrosheet-coverage/load_provenance.ps1 -DryRun
```

Counts only, nothing written. Read `games found` and `of them deduced` and check they are in the
neighbourhood of **203,908** and **3,465**. A wildly different number here is a wrong `-ZipDirectory`,
and this is the cheapest place to find that out.

**5. Rebuild it for real.**

```bash
pwsh discovery/retrosheet-coverage/load_provenance.ps1
```

It builds a staging table, checks it, and swaps it in inside one transaction. If anything fails it
prints `ROLLED BACK - the previous table is intact` and the old table survives. Three refusals happen
*before* the database is touched at all: an empty zip directory, event files with no `id,` line, and a
set containing no `EVA` or `EVN` game.

⚠️ **The shrink guard is one-directional and that is deliberate.** It refuses a load more than 2%
smaller than the existing table (`ShrinkTolerance`, default `0.02` — **provisional, chosen rather than
measured**) and lets any growth through, because a rebuild that adds a season must pass. `-Force` is the
override; use it only when a shrink is genuinely intended.

**6. Read the last line.**

```
games with no provenance : 0
```

**It must be 0.** Anything else means the provenance table and `retroGamesReg` describe different
downloads, and every game without a row is silently dropped from the pool by the `CROSS APPLY` — **a
missing season looks exactly like a season that produced no admissible boards.**

⚠️ **This is a report, not a gate.** It is computed *after* the transactional swap commits, so a
non-zero answer arrives when the table is already canonical. Nothing rolls back on it and nothing acts
on it. If it is non-zero, fix the zip directory and run step 5 again — the loader will not stop you, and
there is nothing to undo.

---

## After: what may have moved under something already published

**7. Regenerate the reference batch and compare the generation.**

```bash
uv run --project forge python forge/scripts/write_reference_puzzles.py
```

A generation id is a hash of the batch's names and payloads. **An unchanged id means the data did not
move under those boards**, and republishing is a no-op by construction (§21). A **new** generation
directory means the source data changed, and then step 8 applies.

**8. ⚠️⚠️ The idempotence guarantee is about the id, not about the content.**

`puzzle_id` is `sha256(namespace | game_id | offense_team)`. **The boxscore is not in it.** So when
Retrosheet corrects a game — which is much of what a new dataset is *for* — the same game yields **the
same id carrying a different board**. §21's promise that a game always yields the same puzzle holds
only while the game's data holds still, and a reload is exactly when it does not.

Nothing detects this on its own. The signature over the payload changes, but only a comparison looks at
it, and there is no comparison against what is already published — the calendar that would own it does
not exist yet.

§21's rule when a published puzzle is found to have changed:

| Where the date sits | What happens |
|---|---|
| **Future date** | Replace the puzzle |
| **Past date, already played** | **Mark void** — excluded from streaks and stats — and **leave the assignment.** Streaks and shared results hang from that date |

**9. Discovery figures are stale, and nothing marks them.** Pool counts, coverage percentages, era
distributions — every measured number under `discovery/` describes the dataset it was run against. They
are not gates and nothing breaks, but a figure quoted after a reload is a figure about the previous
download. Re-run what a pending decision depends on; leave the rest.

---

## What does not need doing

- **The test suite.** It reads committed JSON, never the database. Run it if you like, but a dataset
  reload is not a reason to.
- **Reordering anything.** Provenance before or after the tables is the same.
- **Touching `serve/`.** It receives packages and knows nothing about generating them (§33).

---

## The gap this procedure works around

Steps 6 and 8 are both *"look at a number and act on it"*, and this project's rule is that anything
acting as a gate is asserted rather than printed. Two assertions would remove the judgement:

- Move the orphan count **inside the transaction, before the swap**, and throw on non-zero. Where it
  sits now it can only ever describe a table it is no longer able to refuse.
- A comparison of a regenerated package against the published one, refusing a changed payload under an
  unchanged id unless the change is declared. **This belongs to the calendar** — which is also where
  *one game, one puzzle* lands — and neither exists yet.

Until then the procedure is the check, which is why it is written down.
