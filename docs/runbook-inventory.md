# Runbook — adding new games to the app

**How to top up the puzzle inventory.** Written 2026-08-22, `docs/beta-0-plan.md` A5.

⚠️⚠️ **This is written for somebody who has forgotten all of it, because that is who runs it.** §33
alerts below three months of runway and a batch covers five, so **the interval between two runs is
measured in months by design**. Nothing here assumes you remember why anything is the way it is.

⚠️ **Followed literally once before it was believed.** A runbook that has never been executed by doing
exactly what it says — and nothing the author remembers — is a guess.

**What that run changed**, because it is the argument for doing it:

- **Step 5 would have published the archive.** It said *copy the generation directory to the VPS* and
  named only the manifest and the pointers as private. The directory holds all 150 packages. **The hole
  `docs/calendar.md` exists to close, reintroduced in the instructions for closing it** — and invisible
  while writing, because every individual sentence was true.
- Every command in step 0 and step 3 was run as written, on this machine, and the outputs below are
  from that run rather than from memory.

---

## 0. Before you start

Each of these is checkable in a few seconds, and each one has cost a run when it was assumed.

| check | how | what wrong looks like |
|---|---|---|
| Retrosheet reachable | `uv run python -c "import pyodbc; pyodbc.connect('DSN=LocalServer;DATABASE=DGL;Encrypt=no;TrustServerCertificate=yes', timeout=8)"` | a timeout, not an error message |
| the signing key is present | `python -c "import os,pathlib; print(bool(os.environ.get('BOXSCORE_SIGNING_KEY')) or (pathlib.Path.home()/'.boxscorepuzzle-signing-key').exists())"` | `False` |
| the working tree is clean | `git status --short` | the calendar shows as modified before you began |
| how much runway is left | `uv run python -c "import sys,pathlib,datetime as dt; sys.path.insert(0,'src'); from boxscore_forge.calendar import read; c=read(pathlib.Path('calendar.json')); print(max(e.date for e in c), (dt.date.fromisoformat(max(e.date for e in c))-dt.date.today()).days, 'days')"` | fewer than 90 |

⚠️ **The key is never in the repository** (§16, §33). It is an environment variable or
`~/.boxscorepuzzle-signing-key`, and if neither exists the build refuses to start rather than signing
with something else. **Do not paste it anywhere to check it** — the command above prints a boolean.

---

## 1. Measure before you build

```
cd forge
uv run python scripts/build_inventory.py --measure --per-decade 2
```

**What it prints when it is working**, and every line matters:

```
loading up to 2 directions per decade, gate 0.3
  24 directions in 19.4s (0.81s each)

produced 24 of 24 directions (100%)
  213.1s building, 8.9s per direction
  attempts by outcome: {'erasure': 96, 'published': 24}
  refusals by check: none
  ~9.7s per published board; 150 boards ~= 24 min
```

- **`produced N of N (100%)`** is the expected result. The pipeline has never lost a board: two samples
  of 48 directions produced 48 boards.
- **`erasure`** counts targets a board could not reach. Four or five per board is normal — the producer
  counts down from 12 stalls and takes the first that works.
- **`refusals by check: none`** has been true for roughly 1,235 attempts. ⚠️ **It is an open question
  about the gate rather than a clean bill of health** (`docs/reviews/todo.md`); if it ever says anything
  else, stop and read it before building.

⚠️⚠️ **`--per-decade`, not a total.** The pool spans twelve decades, so `--per-decade 2` draws about 24
directions. Asking for 12 once meant 144 and a run still going ten minutes later.

---

## 2. Build

```
uv run python scripts/build_inventory.py --days 150 --from 2027-01-29
```

**`--from` is the day after your last assigned date**, which step 0 printed. **`--days 150` is five
months** (§33), and generating fewer saves nothing: it is the same batch run and the same calendar, and
it buys a reload in the middle of a beta.

**Expect about 25 to 30 minutes.** ⚠️ **Do not pipe it through `tail` or `head`** — a pipe withholds all
of it until the process exits, which reads exactly like a hang. Redirect to a file if you want a record:
`> ../batch.log 2>&1` and `type ..\batch.log` in another window.

**What it prints when it is working:**

```
0 dates already assigned, 0 games spent
filling 150 of the 150 days from 2027-01-29
  era quota (§6): 7 pre-1950, 143 from 1950 on
  pre-1950: 12 directions for 7 dates (3 per decade)
  1950 on: 168 directions for 143 dates (21 per decade)

assigned 150 of 150 dates from 180 directions
  packages in .../forge/inventory/gen6a8a23f2
  27.9 min building (11.2s per board)
  attempts by outcome: {'erasure': 519, 'published': 150, 'duplicate game': 11}
  refusals by check: none
  audit: 7 pre-1950 of 150 (ceiling 7), no repeats
  manifest: 150 packages; 150 dated pointers in days/
```

---

## 3. What to check before publishing

**`audit:` is the line that matters** and the build refuses to finish without it passing. It asserts the
era ceiling and that no game, date or puzzle id repeats.

⚠️⚠️ **`assigned 150 of 150` is not enough on its own, and that is not hypothetical.** The first real
batch printed exactly that and was **34% pre-1950 against a 5% ceiling** — true about the count, silent
about the composition. `audit()` exists because of that run.

Check by hand as well, because reading the artefact is what has caught every serious defect here:

```
uv run python -c "import sys,pathlib,collections; sys.path.insert(0,'src'); from boxscore_forge.calendar import read; c=read(pathlib.Path('calendar.json')); pre=[e for e in c if int(e.game_id[3:7])<1950]; print(len(c),'dates,',len({e.game_id for e in c}),'games,',len(pre),'pre-1950'); print([e.date for e in pre])"
```

- **dates == games.** One game, one puzzle (§7): the reveal prints both clubs, so publishing both
  directions gives the second board away inside the first one's reveal.
- **the pre-1950 dates are about three weeks apart.** §6 asks for that in those words, so Ruth is an
  event rather than the scenery. Counting them is not enough — seven on seven consecutive days passes a
  tally and defeats the rule.

---

## 4. When the yield is short

**This is the likely outcome, not the exceptional one.** §5's gate keeps about 11% of the pool before
anything runs.

The build **exits non-zero** and says so:

```
6 of 150 dates unfilled. The 144 boards produced are written and their dates are
assigned, so re-running fills the gaps. If it comes up short again, raise
DRAW_MARGIN (1.15) - the draw, not the yield, is what runs out.
```

**Re-run the same command.** It is a window, not a count: the gaps inside it fill and nothing outside it
is touched, however many times it runs. The boards already made are kept — the failure is the exit code,
not the work.

**If it comes up short twice**, raise `DRAW_MARGIN` in `scripts/build_inventory.py`. What runs out is the
*draw*: `load()` returns both directions of one game about 10% of the time and the calendar refuses the
second.

⚠️⚠️ **Never lower a target to fill a quota.** Dropping a rung, widening the era window past §6, or
loosening the gate makes the number go up and the inventory worse — and `audit()` will catch the era one
but not the others. This project has already shipped a pack that reported quotas it had not met.

---

## 5. Deploy

⚠️⚠️ **Only two packages are public: today's and yesterday's** (`docs/calendar.md`). Everything else is on
no public path — a static file on a public path cannot be sold, and §9 sells the archive. **The daily
rotation is what enforces it**, and a rotation that fails once leaks the archive one day at a time.

- Copy the generation directory to the VPS. **`forge/` never goes** (§16, §33) — packages only.
- ⚠️⚠️ **The generation directory itself is behind the wall, not just the manifest.** It holds all 150
  packages and **only two may be on a public path**. Following this runbook literally is what caught
  that: the line above used to read *copy the generation directory to the VPS* with only the manifest
  and pointers called out as private, which would have put the whole archive one URL away — the exact
  hole `docs/calendar.md` was written to close, reintroduced in the instructions for closing it.
- The full `manifest.json` and the `days/` pointers stay behind the wall too: `serve` reads them, the
  browser never does.
- ⚠️ **Not near the daily rollover.** Most outages are self-inflicted deployments, and the rollover is
  the one moment something has to fire on time.
- **Commit `forge/calendar.json`.** It is the one artefact here that cannot be regenerated — §21 makes
  the assignment fixed and never recomputed, so there is nothing to recompute it from, and §33 names Git
  as the backup for a laptop that is a single point of failure.

**Rolling back** is redeploying the previous generation directory: packages are immutable and named by
an opaque id, so an old one is still valid. ⚠️ **The calendar does not roll back** — a date that was
assigned stays assigned (§21). If a *future* date's puzzle is wrong, replace that entry; if a *past*
one is, void it and leave the assignment.

---

## 6. Why re-running is safe

**Say it plainly because hesitating here is expensive:** running the build twice adds nothing the second
time.

- **Puzzle ids derive from the game, never from the date** (§21), so the same game always yields the
  same puzzle.
- **The calendar writes only dates with no entry**, so a second run over the same window has nothing to
  write. Idempotence and *extends rather than rewrites* are the same mechanism.
- **A crash keeps what it made.** The calendar is written after every assignment, so a run that dies at
  board 140 of 150 keeps all 140 and the next run fills the rest.

⚠️ **The one thing that is not safe is deleting `forge/calendar.json` to start over.** It is the
irreproducible artefact; the packages are not. If a batch is wrong, replace the future entries.

---

## What this runbook does not cover

- **The hand-solve gate.** Fifty-ish boards solved by a person is the only verification of human
  derivability that exists (`beta-0.md`), and no command produces it.
- **The daily rotation on the VPS**, which is deployment work (group E) rather than inventory work.
- **The difficulty curve.** Deferred until the hand-solve pack returns; applying it later is a
  reordering of future dates, which §21 supports.
