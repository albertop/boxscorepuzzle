"""`python -m publish` — the command the daily job runs.

⚠️⚠️ **A job that cannot be invoked is not a job**, and the rotation was a function with no entry point
until 2026-08-23. F3 schedules this and E1 built the development tree with it; two ways to start one step
— a cron line here, a script there — is the two-places defect on the code that enforces the access model.

⚠️ **Driven through `main()` with a patched `sys.argv`, not by importing `rotate` again.** What is under
test is the wiring: which arguments reach it, what the exit code is, and whether the health verdict is
read at all. Calling `rotate()` directly would test the thing that already has a suite.
"""

import json
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

import pytest

from publish.__main__ import main
from publish.rotate import MANIFEST, TODAY, YESTERDAY
from tests.conftest import FIRST as _FIRST
from tests.conftest import deploy_client as _deploy


def _client(tmp_path: Path) -> str:
    """Where `deploy_client` put the client. See `_run`, and v42-P2-01."""
    return str(tmp_path / "serve" / "engine" / "package.js")


def _run(monkeypatch: pytest.MonkeyPatch, *arguments: str, client: str | None = None) -> None:
    """⚠️ `--client` is always passed, because its default is the deployed site on the backend network.

    v42-P2-01 replaced a path derived from `--public` with an explicit one; a test that let the default
    stand would be asking a URL that does not resolve here, and the health check would report *no client
    is deployed* about a tree that has one.
    """
    if client is not None:
        arguments = (*arguments, "--client", client)
    monkeypatch.setattr("sys.argv", ["publish", *arguments])
    main()


class TestItRotates:
    def test_a_named_date_publishes_that_day_and_the_one_before(
        self, inventory: Callable[..., Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        private = inventory(tmp_path, days=6)
        public = _deploy(tmp_path / "serve")
        when = _FIRST + timedelta(days=3)

        _run(
            monkeypatch,
            "--inventory",
            str(private),
            "--public",
            str(public),
            "--date",
            when.isoformat(),
            client=_client(tmp_path),
        )

        assert json.loads((public / TODAY).read_text(encoding="utf-8"))["date"] == when.isoformat()
        assert (
            json.loads((public / YESTERDAY).read_text(encoding="utf-8"))["date"]
            == (when - timedelta(days=1)).isoformat()
        )
        served = {found.stem for found in public.glob("*.json") if found.name not in {MANIFEST, TODAY, YESTERDAY}}
        assert len(served) == 2

    def test_it_says_what_it_did(
        self,
        inventory: Callable[..., Path],
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """⚠️ `docs/beta-0-plan.md` A5.2: **a step whose success looks like silence is a step nobody can
        tell failed.** This runs unattended, so what it prints is the whole of what the operator has."""
        private = inventory(tmp_path, days=6)
        when = _FIRST + timedelta(days=3)

        _run(
            monkeypatch,
            "--inventory",
            str(private),
            "--public",
            str(_deploy(tmp_path / "serve")),
            "--client",
            _client(tmp_path),
            "--date",
            when.isoformat(),
        )

        printed = capsys.readouterr().out
        assert when.isoformat() in printed, "the run did not say which day it published"
        assert "health: green" in printed, "the run did not say the public path is sound"

    def test_without_a_date_it_asks_the_clock(
        self, inventory: Callable[..., Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """⚠️⚠️ **The default is the point of the whole command**: the day is decided server-side, once,
        by this. `--date` exists to reproduce a day, never to choose one — a fixed development tree needs
        it, and a pointer the forge never wrote cannot be published whatever it says."""
        private = inventory(tmp_path, days=6)
        public = _deploy(tmp_path / "serve")
        chosen = _FIRST + timedelta(days=2)
        monkeypatch.setattr("publish.__main__.serving_date", lambda: chosen)

        _run(monkeypatch, "--inventory", str(private), "--public", str(public), client=_client(tmp_path))

        assert json.loads((public / TODAY).read_text(encoding="utf-8"))["date"] == chosen.isoformat()


class TestItRefuses:
    def test_a_date_with_no_pointer_exits_with_the_reason(
        self, inventory: Callable[..., Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """⚠️ The message and a non-zero exit, never a traceback: this runs unattended and the operator
        reads a log line."""
        private = inventory(tmp_path, days=6)

        with pytest.raises(SystemExit, match="rotation refused"):
            _run(
                monkeypatch,
                "--inventory",
                str(private),
                "--public",
                str(_deploy(tmp_path / "serve")),
                "--client",
                _client(tmp_path),
                "--date",
                date(2030, 1, 1).isoformat(),
            )

    def test_the_public_path_left_unhealthy_is_a_failure(
        self, inventory: Callable[..., Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """⚠️⚠️ **The rotation writing files and the public path being correct are different claims.**
        Asking `inspect()` here turns the second one into an exit code the job's own log carries, rather
        than a red dashboard nobody is looking at yet — which is the state F3 exists for and the one
        `inspect()` could not see until v40-P1-01.
        """
        private = inventory(tmp_path, days=6)
        public = _deploy(tmp_path / "serve")
        when = _FIRST + timedelta(days=3)
        # A rotation that finishes and leaves a third package: more than the access model allows.
        _run(
            monkeypatch,
            "--inventory",
            str(private),
            "--public",
            str(public),
            "--date",
            when.isoformat(),
            client=_client(tmp_path),
        )
        (public / "an-extra-package.json").write_text("{}", encoding="utf-8")
        monkeypatch.setattr("publish.__main__.rotate", lambda *_a: _NOTHING)

        with pytest.raises(SystemExit, match="not healthy"):
            _run(
                monkeypatch,
                "--inventory",
                str(private),
                "--public",
                str(public),
                "--date",
                when.isoformat(),
                client=_client(tmp_path),
            )


class _Nothing:
    """A rotation that reports having done nothing, so the health check is what decides.

    ⚠️ Needed because a real rotation would sweep the extra package the test just planted — which is the
    rotation working. What is under test is the *reading of the verdict*, and it has to be reachable
    without breaking the thing that keeps it green.
    """

    published: tuple[str, ...] = ()
    retired: tuple[str, ...] = ()
    kept: tuple[str, ...] = ()


_NOTHING = _Nothing()
