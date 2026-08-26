# What CI runs, where, and what it costs

*Written 2026-08-22, when the repository was running at roughly twice its free allowance and the
account had moved to the Free plan.*

This is the one place the CI decisions live. `CLAUDE.md` states the rule that `main` is not protected
and cannot be; this says what runs instead, why each piece is where it is, and what would reverse it.

---

## The five files

| File | Trigger | Skips when the push touches only | Runs |
|---|---|---|---|
| `.github/workflows/ci-forge.yml` | push and PR to `main` | `serve/`, `keep/`, `publish/`, `docs/`, any `.md` | ruff check, ruff format, the discovery ratchet, mypy, **pytest without coverage** |
| `.github/workflows/ci-browser.yml` | push and PR to `main` | `forge/`, `discovery/`, `publish/`, `docs/`, any `.md` | the browser suite in headless Chromium |
| `.github/workflows/ci-keep.yml` | push and PR to `main` | `forge/`, `discovery/`, `serve/`, `publish/`, `docs/`, any `.md` | ruff, mypy and the contract suite **against a Postgres service container**, with coverage |
| `.github/workflows/ci-publish.yml` | push and PR to `main` | `forge/`, `serve/`, `keep/`, `discovery/` — **not `docs/`** | ruff, mypy and the rotation suite, with coverage |
| `.github/workflows/weekly.yml` | Monday 06:00 UTC, and by hand | — | **all of the above, plus the coverage floor** |

`.githooks/pre-push` runs everything, with coverage, on the laptop, before any push to `main`. Enable
it with `git config core.hooksPath .githooks`.

---

## The order these five things run in, which is the part that matters

**The pre-push hook is the primary runner. CI is the safety net.** That is the reversal of the usual
arrangement and it is deliberate.

There is **one developer and one machine**. The hook runs the complete suite, with coverage, before a
push reaches `main` — so by the time CI starts, everything it is about to check has already passed on
the machine that wrote it. Under those conditions a full CI run on every push is a second execution
of a result already in hand, and it was costing about twice the free allowance to produce it.

⚠️ **An earlier version of this argument was wrong and is recorded because the shape recurs.** It ran:
*CI must be primary, because `--no-verify` skips the hook and somebody could push unchecked.* True in
a team. Here the "somebody" is the operator, and a developer who deliberately bypasses his own hook is
not a case a duplicate run protects against — he can ignore a red CI badge just as easily, since
nothing gates on it. That is `CLAUDE.md`'s *a justification is scoped, and it does not travel*: a
reason true where it was learned, silently false where it was reused.

**What CI still buys, and it is not nothing:**

- **A clean checkout.** `uv sync --frozen` installs from `uv.lock` into an empty environment. The
  laptop's virtualenv is warm and months old, so it cannot fail the way a fresh install can — a
  dependency that resolves only because something is already present is invisible there and red here.
- **Pull requests.** There are none today. When there are, the checks run on the branch.
- **A record.** A run history that is not one person's word for it.
- **The weekly run**, which is the answer to *has the hook been disabled, skipped, or quietly diverging
  for a month?* — the one question the hook cannot answer about itself.

---

## The rules, and what would reverse each one

**`paths-ignore` lists what cannot affect the job, never `paths` listing what does.** A `paths` list
forgets the next directory somebody adds, and forgets it *silently* — the new code simply never runs.
This direction fails the other way: an unlisted path runs the job, so the cost of forgetting is a
wasted run rather than an unchecked one.

**The two push workflows are split so that a `serve/` change does not pay for the Python suite.** This
is why they are two files rather than two jobs: `paths-ignore` is a property of a workflow, not of a
job, so a single file can only skip when *every* changed path is ignorable. That is the whole cut —
32% of measured pushes touched only `serve/` and were paying 9.5 minutes for a suite that could not
have been affected.

⚠️ **The split has an accepted cost, stated so it is not discovered as a surprise.** `forge/uv.lock`
and `forge/pyproject.toml` sit inside `ci-browser.yml`'s ignored path, and the browser job installs
from them. **A lockfile change alone will not run the browser suite.** The weekly run is where a broken
`playwright` pin surfaces. *Reverse this if a dependency break ever reaches `main` this way.*

**Coverage runs on the hook and weekly, not on every push.** It was about half the Python job's wall
time. The floor is `fail_under = 95` in `forge/pyproject.toml` and is spelled nowhere else.

⚠️ **What this gives up: a coverage number on a pull request.** *Reverse it the day there are pull
requests from anyone*, or the day the hook stops being run.

**Ubuntu only.** Nothing here is ever deployed on Windows. The reason the Windows job existed — a
redirected stream on the laptop is cp1252 — is now covered by
`forge/tests/test_reports_survive_a_redirected_stream.py`, a static check over every `print` argument
that runs on any platform, and by the fact that **the laptop is the Windows machine**: the hook runs
the whole suite there before every push. That class of defect appeared twice more on 2026-08-22 and
both were caught without the job. *Reverse it if anything ships to Windows.*

**The weekly run is a safety net and must never be described as a gate.** Neither is CI. `main` cannot
be protected server-side: GitHub gates branch protection *and* rulesets behind a paid plan for private
repositories, and this repository is private permanently (§16, `forge/` is trade secret). Both API
calls return `403 Upgrade to GitHub Pro or make this repository public`.

---

## The bill

GitHub Free gives a private repository **2,000 Actions minutes a month**. Nothing else in this
repository is near a limit: it is about 7 MB, uses no LFS, and stores no artifacts. Linux bills at 1×,
Windows at 2×.

Measured over six days of real pushes — 44 runs, 778 billed minutes — then simulated over the same
history:

| | minutes/month |
|---|---|
| as it was (both platforms, every push) | 3,852 |
| Windows out | 2,337 |
| + `paths-ignore` on the single workflow | 2,018 |
| + the split into two workflows | 1,348 |
| + coverage off the push runs, weekly instead | **~658** |

The first three rows are simulations over the real push history. **The last two are projections**, and
they rest on that history's shape: 32% of pushes touched only `serve/`, 14% touched only documents.

⚠️ **`paths-ignore` on one workflow saved far less than it looked like it would.** The first estimate
of that row was 1,365 and the real figure is 2,018. A workflow is skipped only when *every* changed
path is ignorable, so the 32% of pushes touching only `serve/` still paid for the Python job. The
error was assuming a per-job property from a per-workflow one — and it is the reason the split exists.

**Owed: the real minutes, before and after, once a full month has run.** These are projections until
then. The account's per-product billing breakdown needs `gh auth refresh -h github.com -s user`, which
only the operator can run; until it has been read, *Actions is the whole bill* is inference from the
repository's shape rather than a measurement.

---

## ⚠⚠ Why `ci-publish.yml` does not ignore `docs/`, when every other workflow does

**`docs/calendar.md` states `ROLLOVER_OFFSET_HOURS = -8` once, for the three trees that have to spell
it.** §33 forbids them sharing code and `forge` must never reach the VPS at all, so the rule is shared by
pointing at a document — and `publish`'s suite asserts its constant against that line.

⚠️ **Ignoring `docs/` would leave the one check that keeps three copies in agreement silent on the only
change that can break it.** The cost is that a documentation-only push pays for one small suite; the
alternative is a guard that runs on everything except its own subject.

**And `keep/` and `publish/` joined `ci-forge.yml`'s ignore list the same day.** Before that a
`keep`-only change paid for the whole Python suite — §33 forbids the cross-import, so nothing in those
trees can change what the forge job checks.

---

## ⚠️⚠️ Why `keep`'s suite refuses to run without a database

Its Postgres arm **fails rather than skips**. Without a server `PostgresStore` is 80% covered and the
suite is 92% — **under its own 95% floor, while looking green**. So the floor only held on a machine
that happened to have Docker running, which is a guarantee true where it was written and nowhere else.

⚠️ **The tempting repair was a fake connection.** It would have taken `PostgresStore` to 100% and
proved nothing about Postgres — coverage theatre, and the number would then lie in exactly the place it
is relied on. **Postgres is production; its store is tested against Postgres.**

The hook starts a `keep-test-pg` container if one is not already up; CI uses a service container.

---

## ⚠⚠ What the hook checks is not what the push delivers — established 2026-08-23

**The hook runs before the transfer, against the working tree, and the transfer sends whatever the
branch tip is when it gets there.** Those are three different moments, and the suite takes thirteen
minutes with coverage.

**The evidence, because this was first mistaken for a second push.** GitHub records **one** PushEvent:

```
2026-08-23T14:42:29Z  actor=albertop  before=fc61c9f  head=942393a
```

The local remote-tracking reflog records `update by push` → **`2efeb52`** at 14:42:27Z, two seconds
earlier. **Same push. It reported one commit and delivered three.** Two commits made *while the hook was
running* went to `main` in a push that had been invoked before they existed.

✔ **So there is no delivery path that skips the hook**, which was the thing worth ruling out: one push,
one hook run, `git worktree list` shows a single tree, and there is no `post-commit` hook, alias or
autopush anywhere in the configuration.

⚠⚠ **What there is instead is a hook whose subject is not its payload.** `.githooks/pre-push` reads
stdin only to see whether `refs/heads/main` is among the refs — **it discards both SHAs**, they are
`_local_sha` and `_remote_sha` — and then runs the suite against `$(git rev-parse --show-toplevel)`.
So it does not test the commits being pushed. It tests **whatever is on disk while it runs**, and on a
thirteen-minute run that is a moving target: the tree gained two commits under it.

**Nothing broke here** — the two were documentation and a `todo.md` entry, and the suite that mattered
had already passed. **The guarantee is weaker than it reads**, which is the finding: *the hook passed*
does not mean *what was pushed passed*.

⬜ **Not fixed, and the repair is not obvious.** Checking out the pushed SHA into a temporary tree would
make the hook test its payload and would also make it slower and stateful. Refusing to run when the tree
is dirty or when HEAD moves mid-run is cheaper and narrower. **Which one is right depends on whether the
hook is meant to gate a *push* or to check a *machine*,** and that is the same question the
hook-primary arrangement above turns on — so it is recorded here rather than decided in passing.

⚠️ **The operational rule that costs nothing meanwhile: do not commit while a push is running.** It was
done twice on 2026-08-23, by me, without noticing.

---

## ⚠️⚠️ One forge test needs Docker, and it skips rather than failing when there is none

**Two tests need one.** `forge/tests/test_nginx_serves_what_is_declared.py` starts nginx over `serve/`
and checks every URL the route table and the cache table declare;
`forge/tests/test_the_proxy_reaches_keep.py` **builds `deploy/keep.Dockerfile`** and runs it beside a
Postgres and an nginx on their own network, to post an event through the edge. **Without a container
runtime both skip, with the reason printed** — `docker is not runnable here`, or what `docker info` said.

⚠️ **The second one builds an image**, which is the slowest thing in the suite by a wide margin on a
cold runner. It is the only place `keep` is installed the way production installs it, and that is what
caught `psycopg` being a dev extra — so the cost buys something nothing else can.

⚠️ **A skip that reads like a pass is the shape this project keeps closing**, so the distinction matters:
the run says *there is no Docker*, never *the routes are fine*. GitHub's `ubuntu-latest` has Docker, so
`ci-forge.yml` runs it for real; a machine without one is told what it did not check.

⚠️ **No fifth workflow.** The test lives in `forge/tests/` and runs with the forge suite. The
`deploy/` tree holds a configuration file and nothing executable, so there is nothing to lint, type or
test on its own — the check that matters is this one, and it belongs where the declarations it compares
already are.

## ⚠️⚠️ One forge test depends on `serve/` and on `tools/`, and the path filters cannot see that

`forge/tests/test_dev_server_routes.py` starts `tools/dev_server.py` and asks it for pages under
`serve/ui/phone/`; `forge/tests/test_nginx_serves_what_is_declared.py` does the same through nginx and
also reads `docs/calendar.md` and `deploy/nginx/`. **`ci-forge.yml` skips `serve/`-only and
documents-only changes**, so a commit that renamed `play.html` — or edited the cache table — would not
run either of them there.

**What still catches it:** the pre-push hook runs every tree on every push, `ci-browser.yml` runs on
`serve/` changes and would fail on the missing page, and the weekly run is complete. **What does not
catch it is the workflow that owns the test**, and that is the honest shape of a path filter: it
partitions by directory and a dependency that crosses one is invisible to it.

⚠️ **Not fixed by widening `ci-forge.yml`'s triggers.** That would run the whole forge suite on every
`serve/` commit and give back most of what `paths-ignore` was for. The test is cheap and its real
guarantee is the hook; this paragraph exists so the next person to read a green forge badge after a
`serve/` change knows what it did not run.

## ⚠️⚠️ The share-image guard runs on the hook and **not in CI** — decided 2026-08-26

`forge/tests/test_the_share_image_is_not_the_screen.py` rasterises the share image at 375×812 and at
1440×900 and requires the same PNG, byte for byte. It needs **chromium and a running dev server**, and
it lives in `forge/tests/` while everything it watches is in `serve/`.

**So `ci-forge.yml`'s `paths-ignore: serve/**` means it does not run in exactly the case it watches** —
a `serve/`-only change. Green for ever by construction, which is the shape recorded three times in
`CLAUDE.md`. That is stated here rather than fixed, and the choice was made with the alternatives priced.

### What was not done, and what each would have cost

| | |
|---|---|
| **drop `serve/**` from `ci-forge.yml`** | the whole Python suite on every `serve/` commit, plus chromium. **32% of measured pushes touch only `serve/`** — it gives back most of what the split above was for |
| **add a step to `ci-browser.yml`** | that workflow runs the in-page suite through `run_browser_tests.py`. This is a pytest test needing `forge`'s environment, so the job would install Python twice |

### Why the hook

**Because this is the expensive class the hook-primary arrangement already exists for.** One developer,
one machine: the hook runs everything before a push reaches `main`, and CI is the safety net rather than
the gate — the reversal is deliberate and is stated at the top of this file. A test that needs a browser
and a server is exactly what that decision put on the laptop.

⚠️ **And what CI buys is the `--frozen` install into an empty environment**, the one thing the warm venv
of months cannot fail at. This test does not exercise that: it needs a browser binary that the laptop and
the runner both already have, and its subject is a stylesheet.

### ⚠️ The cost, which is real and is not new

**A `git push --no-verify` leaves this test unrun and CI would not see it.** That is true of the whole
suite and not of this test in particular — it is the standing cost of the hook being primary, already
recorded above under what stops a push. **What is new is only that one more guard now sits on that side
of the line.**

### What would reverse it

**The day a pull request arrives from anybody but the operator.** The hook is one machine checking
itself; a contributor's branch has no hook, and a guard that only exists locally guards nothing about
code somebody else wrote.

**Or the day the hook stops being run** — `core.hooksPath` unset on a new checkout, a second machine, or
a habit of `--no-verify`. The hook's whole value is that it is unconditional in practice; the moment it
is not, every check that lives only there has to move.

⚠️ Neither is a judgement call about cost. Both are **facts about who pushes and whether the hook ran**,
and either one makes this paragraph wrong rather than merely expensive.

## The guard

`forge/tests/test_the_hook_runs_what_ci_runs.py` asserts that the hook and the push workflows check
the same set of tools, and that the weekly run is the complete one. It reads **the whole workflow
directory**, so a new workflow cannot introduce a check the hook does not run, and it compares **tool
names, not command lines**, so it does not go red on a reordered flag.

⚠️⚠️ **And it was blind to whole trees until 2026-08-22.** `keep` arrived and the tool sets did
not change — it runs the same ruff, mypy and pytest — so the guard stayed green **while nothing ran
`keep` at all**, and would have stayed green with it in the hook and out of CI. *A guard comparing the
wrong dimension reports an agreement it never looked for.* `test_every_tree_with_a_project_is_checked_by_both`
now asks whether every tree with a `pyproject.toml` is named by the hook **and** by a push workflow.

⚠️ **That one needed a word boundary before it worked.** `"keep" in text` matches **`keeps`**, which
`ci-forge.yml` says in a comment about the gate — so deleting `ci-keep.yml` outright left it passing.
Found by deleting the workflow and watching nothing break, which is the only way that class is found,
and it is the `sign(` that matched inside `verify_signature(` again.

⚠️⚠️ **And it asked two sides where there are three, which cost the same defect a second time.**
(v40-P3-01) `publish` arrived on 2026-08-23 with its own push workflow and its own hook block, so the
hook and CI both named it and the guard was green — **while `weekly.yml` never installed it at all.**
The tool-set comparison could not see it either: `keep` already contributes ruff, ruff format, mypy and
pytest, so a second project running exactly those is invisible to a set of names.

**The weekly run is the one this document calls complete**, so a tree missing from it makes the claim
false about precisely what the weekly run exists to catch — a hook that has been skipped or disabled.
The guard asks the scheduled workflow now, alongside the hook and the push workflows, and the weekly
job installs and checks `publish`. Verified by renaming `publish` out of `weekly.yml` and watching the
guard name both the tree and the side.

⚠⚠ **And blind to the *invocation* as well, which is the same blindness one level up.** On 2026-08-23 a
suite was verified all day with `uv run python -m pytest` while the hook runs `uv run pytest`. **They are
different commands**: `python -m` puts the working directory on `sys.path` and plain `pytest` does not,
so `publish`'s tests passed thirty-three times locally and the hook refused the push with
`ModuleNotFoundError`. The guard compares **tool names** — `pytest` is `pytest` either way — so it could
not have seen it, and neither could a guard comparing flags.

⚠️ **What caught it was the hook itself**, doing what it is for. Checked afterwards and clean: no
workflow and no line of the hook uses `python -m`, so the divergence was a verification habit rather
than a difference in the machinery. **`forge` resolves `from tests.…` through `tests/__init__.py`,
`keep` has no cross-test imports, and `publish` now declares `pythonpath = ["src", "."]`** — two
mechanisms for one property, named here so neither reads as broken.

⚠️ **It is blind to flags by construction, which is exactly where the current divergence lives.**
`pytest` and `pytest --cov` are one entry, so this test cannot see coverage leaving the hook. That is
named here and in the test's own docstring rather than left to be discovered.

---

## ⚠️⚠️ What stops a push, in practice — two conditions found on 2026-08-24

**Neither was `ghcr.io`.** F1's network dependency is real and recorded above; these are different and
both cost an afternoon before being named.

### 1. The assistant's shell cannot reach Docker. **A standing condition, not an incident.**

The hook starts a Postgres container so `keep`'s Postgres arm runs rather than skipping. The assistant's
sandboxed shell **cannot reach `npipe:////./pipe/dockerDesktopLinuxEngine`**, so every push it runs fails
at that step with `the daemon is not running`.

**Every push from an assistant session must run with the sandbox disabled**, or it fails for a reason
that has nothing to do with the code.

⚠️⚠️ **The diagnosis was wrong first, and the way it was wrong is the lesson.** Two signals agreed on it:
`docker info` said *the daemon is not running* — **which is the client's message, not a fact about the
daemon** — and `com.docker.service` read `Stopped`, which is irrelevant under the WSL2 backend. The
operator was asked to start a service that was not the problem. **Neither signal asked the only question
that decides it:** is a container running. `docker ps` outside the sandbox answered in one attempt.

### 2. The Postgres fixture's teardown kept its own list of tables

`shares` went into `001-initial.sql` and not into
`DROP TABLE IF EXISTS events, client_errors, keep_schema`. The table survived between tests, every
Postgres case after the first died on `DuplicateTable`, and coverage fell to 94.87% against a 95% floor.

⚠️⚠️ **It is the same shape as the three hand-maintained `.gitignore` lines that let `fifty-key.csv`
through, on the same day, in the same session.** Three names spelled in one place and created in
another, with nothing checking they agree. **Knowing the rule does not apply it** — this project has
said so since the fourth regex.

**And the teardown can enumerate, so it does.** It reads `pg_tables` for the current schema and drops
what is there. The migration is now the only place a table is ever named, and a fifth one is dropped by
existing rather than by somebody remembering a line in a fixture. **That is the difference from the
`.gitignore` case, where the repair was a glob and a test rather than a longer list** — both replaced a
maintained list with something derived.

⚠️ **Only the hook could have caught it.** The SQLite arm passed all 78 cases, because its fixture builds
a fresh in-memory database per test and has no teardown to forget. The engine that shares production's
semantics is the one that needed a shared fixture.
