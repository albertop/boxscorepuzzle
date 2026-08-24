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

### ⚠️⚠️ If that check says `False`

**Restore the key from backup. It cannot be regenerated.**

`serve` pins the public half in `serve/data/signing-public-key.hex`, and every package and every manifest
ever published was signed with the private half. A new pair is a **different** key: the client refuses
everything already deployed, which is an outage rather than a rejected file.

**With no backup, the only way forward is reissuing everything** — every package in every live
generation and every manifest, re-signed with a new pair, and the pinned public key changed in `serve`
in the same deploy. Hours, and every one of them avoidable.

⚠️ **This is the situation months between runs creates**: somebody sits down to top up the inventory,
finds no key, and does not know whether it can simply be made again. **It cannot.** That is the whole
reason this paragraph exists.

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

⚠⚠ **And the retry keeps §6's era quota, which it did not until v39-P1-02.** The allowance and the
spacing are planned over the **whole window** and reconciled against the pre-1950 boards already inside
it, so a second pass cannot grant itself a fresh 5%. Before that fix this very instruction was the way
to break the ceiling: a 150-day window that had spent all seven of its early boards took two more per
retry, landing them a day apart from the ones already there. **The recovery path was the defect.**

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

### What goes to the VPS

⚠️⚠️ **This step said *copy the generation directory; `forge/` never goes — packages only*, and that
stopped being the whole truth on 2026-08-24.** It is written for somebody who has forgotten everything
and follows it literally, and following it literally is what reintroduced the archive hole once already.
**Three things go, and the puzzles are only one of them:**

| | from | to | when |
|---|---|---|---|
| the private inventory | `forge/inventory/<generation>/` | the VPS's private path, **not** under the served root | every batch |
| `publish/` | the tree | the VPS | when it changes |
| `deploy/` | the tree | the VPS | when it changes |

**`forge/` itself never goes** (§16, §33) — not the generator, not the validator, not the calendar
builder, and **not the private signing key**. `publish/` and `deploy/` are not the generator: neither can
produce a puzzle and neither holds a key.

⚠️ **The public path is not one of these rows.** Nothing is copied *into* it by hand: the rotation puts
today's and yesterday's there and removes everything else. Copying a package into the served root
directly is how two days becomes three.
- ⚠️⚠️ **The generation directory itself is behind the wall, not just the manifest.** It holds all 150
  packages and **only two may be on a public path**. Following this runbook literally is what caught
  that: the line above used to read *copy the generation directory to the VPS* with only the manifest
  and pointers called out as private, which would have put the whole archive one URL away — the exact
  hole `docs/calendar.md` was written to close, reintroduced in the instructions for closing it.
- The full `manifest.json` and the `days/` pointers stay behind the wall too: `serve` reads them, the
  browser never does. ✔ **True as of E1, 2026-08-23** — `docs/calendar.md` owns
  the fact and says what `daily.js` currently does instead. **The rule above it is not marked and does
  not change:** *only two packages are public* is present and permanent.
- ⚠⚠ **After a top-up, the rotation reads `days/` from the *newest* generation and only that one.**
  Every build writes a complete pointer schedule, but an older generation's was written before the later
  dates existed — it has no pointer for them. **Each pointer names the generation that owns its package**
  (`entry.assigned`), so the newest tree resolves correctly into the older directories, which is why they
  all have to stay on the VPS.

  ⚠️ **This was wrong until v39-P1-01, and the first top-up would have been the first time it showed.**
  Every pointer was stamped with the generation being written, so old dates pointed at a file that does
  not exist — a 404 on a legitimately assigned date, signed by the forge so it read as authoritative.
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
- **A retry plans against the window, not against the gaps** (v39-P1-02), so the era quota and the
  three-week spacing survive however many passes it takes.
- **A pointer names the generation that produced its package** (v39-P1-01), so a top-up cannot re-point
  an older date at a file that was never written into the new directory.

⚠️ **The one thing that is not safe is deleting `forge/calendar.json` to start over.** It is the
irreproducible artefact; the packages are not. If a batch is wrong, replace the future entries.

---

## 6b. ⚠️⚠️ Verify the deploy from outside — do not skip this

**The whole access model is one sentence — *only two packages are public* — and nothing so far has
checked that it is true.** Step 5 says the rotation enforces it; this is what confirms the rotation
worked.

⚠️ **It is the one thing here that breaks irreversibly.** A file downloaded once has already left. A
rotation that failed is not something you find out about later and repair — you find out that the
archive has been readable for however long, and it stays read.

**Two requests, from a machine that is not the VPS:**

```
curl -sS -o NUL -w "today:            %{http_code}
" https://boxscorepuzzle.com/p/<today-id>.json
curl -sS -o NUL -w "two days ago:     %{http_code}
" https://boxscorepuzzle.com/p/<older-id>.json
```

**What right looks like:**

```
today:            200
two days ago:     404
```

⚠️ **`403` is also wrong.** It means the file is there and something is declining to serve it — one
configuration change away from being public, and it says the rotation did not run. **The package must
not be on the public path at all.**

Get the two ids from the calendar:

```
uv run python -c "import sys,pathlib,datetime as dt; sys.path.insert(0,'src'); from boxscore_forge.calendar import read; c={e.date: e.puzzle_id for e in read(pathlib.Path('calendar.json'))}; t=dt.date.today(); print('today  ', c.get(t.isoformat())); print('2 days ', c.get((t-dt.timedelta(days=2)).isoformat()))"
```

⚠️ **Before the calendar's first date arrives, both print `None`** — the whole window is in the future
and there is nothing public yet. That is the correct answer and not a fault; it also means **this step
cannot be rehearsed before launch**, so run it the first day there is something to serve.

⚠️ **From outside, not from the VPS.** A request made on the server can reach a path the internet
cannot, and one made from inside a network can pass a rule that exists at its edge — which would confirm
exactly the wrong thing.

**This is also what F3's inventory health check asserts continuously** (`docs/beta-0.md`): the public
path holds no more than two packages. **This step is the one-off; that check is the standing one**, and
neither replaces the other — this catches a bad deploy now, that catches a rotation that stops later.

---

## 6c. Check the committed calendar names the deployed generation

**They can drift silently, and the calendar is the artefact that cannot be regenerated.** If generation
`X` is on the VPS and a calendar referencing `Y` is in Git, nothing complains: every package is
individually valid and the calendar is internally consistent.

```
uv run python -c "import sys,pathlib,collections; sys.path.insert(0,'src'); from boxscore_forge.calendar import read; print(collections.Counter(e.assigned for e in read(pathlib.Path('calendar.json'))))"
```

Compare against the generation directory actually deployed. **More than one generation in the counter is
normal** — a top-up adds a new one and the old dates keep theirs — but **every generation named there
must still be on the VPS**, because those dates' packages live in it.

⚠️ **This is the check that catches a partial deploy**, which otherwise surfaces months later as one
date serving nothing.

---

## What this runbook does not cover

- **The hand-solve gate**, which is the only verification of human derivability that exists
  (`docs/beta-0.md`) and which no command produces. ⚠️ **It is not "fifty boards"** — that number and its
  chain axis are both from a retired design. The gate is **Pack A's sixteen** (four each at stall rungs
  5, 8, 11, 12) **plus a derivability-only sample over the shipping inventory**, whose N is still open.
  `CLAUDE.md` says the same thing in the same words; if these two ever disagree, `beta-0.md` is the
  decision and the others are copies.
- **The daily rotation on the VPS**, which is deployment work (group E) rather than inventory work.
- **The difficulty curve.** Deferred until the hand-solve pack returns; applying it later is a
  reordering of future dates, which §21 supports.
