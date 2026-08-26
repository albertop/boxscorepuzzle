"""Shared fixtures.

The balanced boxscore is a real game, not invented numbers: Chicago Cubs at Atlanta Braves,
8 August 1968, Retrosheet game ATL196808080. The Cubs' offense against the Braves' pitching is one
direction of that game, and it passes the roster caps with 9 batters and 2 pitchers.

Invented test data cannot catch an identity that is stated wrongly, because the data would be built
to satisfy the wrong statement. A real game can.

Note the leadoff batter's sacrifice hit. It is the one row in this game whose identity does not
close on `PA = AB + BB` alone, which makes it the row that matters most here: nine rows in ten look
as though the footnote columns are decoration.
"""

import os
import re
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from hypothesis import settings

from boxscore_forge.boxscore import (
    BatterFootnotes,
    BattingLine,
    Direction,
    LineScore,
    PitchingLine,
    TeamFootnotes,
)

# Composite generation of a whole balanced boxscore is not fast, and a per-example deadline tuned
# for trivial strategies turns into a flaky failure that says nothing about the code.
settings.register_profile("forge", deadline=timedelta(seconds=5))

# ⚠⚠ **No deadline on a shared runner, because a deadline is an assertion about *performance* and a
# shared runner cannot support one.** The Windows job failed on
# `DeadlineExceeded: Test took 6362.99ms` against this 5s limit — on a machine where the whole suite
# took 18m25s against 80s on the laptop and 4m on the Linux runner. Nothing about the code was slower;
# the machine was. Keeping the deadline there would make the build fail on the runner's mood, and a
# check that fires on noise is one people learn to re-run rather than read.
#
# ⚠️ **The deadline stays on locally, which is the point of it.** A test that suddenly takes six
# seconds on the laptop is a finding. `CI` is set by GitHub Actions and by essentially every runner.
settings.register_profile("ci", deadline=None)
settings.load_profile("ci" if os.environ.get("CI") else "forge")

_NO_FOOTNOTES = BatterFootnotes(hit_by_pitch=0, sacrifice_flies=0, sacrifice_hits=0, catcher_interference=0)


@pytest.fixture
def cubs_at_braves_1968() -> Direction:
    """Chicago Cubs offense against Atlanta Braves pitching, 8 August 1968. Cubs won 4-0."""
    batting = (
        BattingLine(plate_appearances=5, at_bats=4, runs=1, hits=1, walks=0, strikeouts=0),
        BattingLine(plate_appearances=5, at_bats=5, runs=0, hits=2, walks=0, strikeouts=1),
        BattingLine(plate_appearances=5, at_bats=4, runs=1, hits=2, walks=1, strikeouts=0),
        BattingLine(plate_appearances=4, at_bats=4, runs=0, hits=1, walks=0, strikeouts=1),
        BattingLine(plate_appearances=4, at_bats=4, runs=0, hits=0, walks=0, strikeouts=1),
        BattingLine(plate_appearances=4, at_bats=3, runs=0, hits=2, walks=1, strikeouts=0),
        BattingLine(plate_appearances=4, at_bats=4, runs=0, hits=1, walks=0, strikeouts=0),
        BattingLine(plate_appearances=4, at_bats=4, runs=0, hits=1, walks=0, strikeouts=0),
        BattingLine(plate_appearances=4, at_bats=4, runs=2, hits=1, walks=0, strikeouts=2),
    )
    footnotes = (
        BatterFootnotes(hit_by_pitch=0, sacrifice_flies=0, sacrifice_hits=1, catcher_interference=0),
        *([_NO_FOOTNOTES] * 8),
    )
    pitching = (
        PitchingLine(outs=20, hits=10, runs=4, earned_runs=4, walks=1, strikeouts=3),
        PitchingLine(outs=7, hits=1, runs=0, earned_runs=0, walks=1, strikeouts=2),
    )
    return Direction(
        batting=batting,
        batting_totals=BattingLine(plate_appearances=39, at_bats=36, runs=4, hits=11, walks=2, strikeouts=5),
        batter_footnotes=footnotes,
        footnote_totals=BatterFootnotes(hit_by_pitch=0, sacrifice_flies=0, sacrifice_hits=1, catcher_interference=0),
        team_footnotes=TeamFootnotes(left_on_base=8),
        pitching=pitching,
        pitching_totals=PitchingLine(outs=27, hits=11, runs=4, earned_runs=4, walks=2, strikeouts=5),
        line_score=LineScore(
            offense_by_inning=(1, 0, 1, 0, 0, 0, 2, 0, 0),
            defense_by_inning=(0, 0, 0, 0, 0, 0, 0, 0, 0),
            offense_runs=4,
            offense_hits=11,
            offense_errors=0,
            defense_runs=0,
            defense_hits=3,
            defense_errors=0,
        ),
    )


DOCKER_PREFIX = "bxcpze"
"""The prefix on every image, container and network this suite creates. **Declared once.**

⚠️⚠️ **So a stray one can be found and removed by name.** These tests build images and start containers
on a machine that is also somebody's laptop; a run killed part-way leaves them behind, and a run that
names things after itself is one `docker ps --filter name=bxcpze` away from being cleaned up. Without a
shared prefix that sweep has to know every name, which is a second list of the same facts.

⚠️ **Uncommon on purpose.** `bsp` collides with anything; this string appears nowhere else on a normal
machine, so the filter cannot match a container somebody else is depending on.
"""


_ROOT = Path(__file__).resolve().parents[2]
"""The repository root. `deploy/` is a sibling of `forge/`."""


def _serve_environment() -> dict[str, str]:
    """The `serve` service's nginx variables, **read from `deploy/compose.yaml`**.

    ⚠️⚠️ **Three tests spelled `NGINX_ENVSUBST_FILTER=^KEEP_` and the compose file spelled it a fourth
    time.** Four places encoding one fact, and the failure is silent in the direction that matters: a
    test passing its own filter proves nginx works **with that filter**, never with the deployment's. The
    day they differ, the suite is green about a configuration nobody runs.

    ⚠️ Parsed with a regex rather than a YAML library because `forge` has no YAML dependency and this
    reads two lines. **It asserts it found them** -- a parse that silently returns nothing would hand
    every test an empty environment and nginx would start on an unsubstituted template.
    """
    compose = (_ROOT / "deploy" / "compose.yaml").read_text(encoding="utf-8")
    wanted = ("NGINX_ENVSUBST_FILTER", "NGINX_ENTRYPOINT_LOCAL_RESOLVERS")
    found: dict[str, str] = {}
    for name in wanted:
        match = re.search(rf"^\s*{name}:\s*\"?([^\"\n]+?)\"?\s*$", compose, re.MULTILINE)
        if match is None:
            message = f"{name} is not in deploy/compose.yaml; the tests would run a different nginx"
            raise AssertionError(message)
        found[name] = match.group(1)
    return found


NGINX_ENVIRONMENT = _serve_environment()
"""What the deployment gives nginx, so a test starts the container the deployment starts.

⚠️ `KEEP_SHARED_TOKEN` is deliberately **not** here: each test makes its own, because a token committed
to the repository is a token, and `docs/signing-keys.md` records why that is never done."""


def nginx_environment_flags() -> list[str]:
    """`-e NAME=VALUE` for every nginx variable the deployment sets.

    ⚠️ **Returns the flags, not the values.** The first version returned `NAME=VALUE` strings spliced
    after a single `-e`, so the second variable reached `docker run` as an image name and every test
    died with exit 125. A helper that hands back half of a flag pair is a helper whose caller has to
    remember the other half.
    """
    flags: list[str] = []
    for name, value in NGINX_ENVIRONMENT.items():
        flags += ["-e", f"{name}={value}"]
    return flags


def nginx_base_image() -> str:
    """The nginx image `deploy/serve.Dockerfile` builds on, **read from it**.

    ⚠️⚠️ **Two tests spelled `nginx:1.27-alpine` while the Dockerfile said something else.** A test that
    runs the config on a different nginx than the one shipped is green about a build nobody deploys --
    and the version moved to 1.30.4 with nothing complaining. **It asserts it found the line**: a regex
    that silently matched nothing would hand back an empty image name and the failure would describe
    something else entirely.
    """
    dockerfile = (_ROOT / "deploy" / "serve.Dockerfile").read_text(encoding="utf-8")
    match = re.search(r"^FROM\s+(nginx:\S+)", dockerfile, re.MULTILINE)
    if match is None:
        message = "no FROM nginx: line in deploy/serve.Dockerfile; the tests would run some other nginx"
        raise AssertionError(message)
    return match.group(1)


_INVENTORY = Path(__file__).resolve().parents[2] / "forge" / "inventory"


def _generations() -> set[str]:
    """The generation directories that exist right now, or an empty set when there is no inventory."""
    return {path.name for path in _INVENTORY.iterdir() if path.is_dir()} if _INVENTORY.is_dir() else set()


@pytest.fixture(autouse=True, scope="session")
def _the_suite_does_not_write_into_the_real_inventory() -> Iterator[None]:
    """⚠️⚠️ **The suite must not touch `forge/inventory/`. It wrote 214 directories into it on 2026-08-26.**

    `build_inventory` computes that path from `_ROOT`, and the tests redirect the builder by patching
    `_ROOT` to a temporary tree. **A tidy-up hoisted the path into a module-level constant** --
    `INVENTORY = _ROOT / "forge" / "inventory"` -- which is evaluated at IMPORT time, so the patch stopped
    reaching it and every test that produced a generation wrote into the operator's real inventory.

    ⚠️⚠️ **Twenty-six tests went red and fourteen did not: they wrote.** The red ones were diagnosed, the
    constant was reverted and the suite went green -- and nobody asked what the green ones had been doing
    while the path was wrong. **A test that passes while writing to the wrong place is indistinguishable
    from a test that passes.** That is the whole reason this exists as a check rather than as care.

    ⚠️⚠️ **And it nearly reached production.** `forge/inventory/` is rsynced to the VPS, and `rotate.py`
    searches generations **newest first** -- so 45 junk generations carrying `days/` pointers sorted ahead
    of the three real ones and would have shadowed **100 calendar dates**. The rotation would have served
    a test fixture's puzzle, signed, valid, and passing every health check.

    ⚠️ **Session-scoped and counted, not mocked.** A fixture that redirected the path would protect the
    suite and say nothing about a script run by hand; this asks the directory what happened, which is the
    only question that catches every route to it.
    """
    before = _generations()
    yield
    appeared = _generations() - before
    if appeared:
        listed = ", ".join(sorted(appeared)[:6])
        message = (
            f"the suite wrote {len(appeared)} generation(s) into {_INVENTORY}: {listed}. "
            f"Tests build inventories in tmp_path; a path resolved at import time ignores that redirect. "
            f"This directory is rsynced to the VPS and rotate.py reads the NEWEST generation first."
        )
        raise AssertionError(message)
