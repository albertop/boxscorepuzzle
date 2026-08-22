"""The pre-push hook and CI must check the same things.

⚠️⚠️ **They are two hand-maintained copies of one list.** (v36-P3-10) The hook re-spells CI's
commands, and `CLAUDE.md` is explicit about what the hook is for: `main` is not protected
server-side and cannot be, so the hook is *the nearest available thing* — and its whole value is
that a push to `main` has already run what CI runs.

**It cannot be one list.** One is YAML consumed by GitHub, the other is shell run by git; neither can
import the other. So they are two copies asserted to agree, which is the same treatment
`ACCEPTED_SOURCES` gets for the one other rule that has to exist twice.

⚠️ **The comparison is over TOOLS, not over exact command lines.** Pinning the strings would make
this red on `-q`, on a reordered flag, on a path spelled differently — a guard failing on its own
phrasing while the rule holds, which this project has recorded twice. What must not happen is a check
existing on one side and not the other.

⚠️⚠️ **What this comparison is blind to, stated so nobody reads it as covered.** Comparing tools and
not flags means `pytest` and `pytest --cov` are the same entry. That is not an oversight — it is the
current, deliberate divergence: since 2026-08-22 the push workflows run `pytest` and the coverage
floor runs on the hook and in `weekly.yml` (`docs/ci.md`). **This file cannot see coverage leaving the
hook**, because the tool name would not change. `forge/pyproject.toml` holds `fail_under = 95` and
`test_the_coverage_floor_is_ninety_five.py` is what guards the number itself.

⚠️ **The scan reads the whole workflow directory rather than one named file**, which is stronger than
the version before the split: a new workflow cannot introduce a check the hook does not run, and
renaming a file does not silently empty the comparison — a directory yielding nothing fails.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOWS = _ROOT / ".github" / "workflows"
_HOOK = _ROOT / ".githooks" / "pre-push"

SETUP = {"sync", "playwright", "apt-get"}
"""Commands that prepare an environment rather than check anything.

The hook runs on a laptop that is already set up; CI starts from nothing. That difference is real and
is not drift, so these are named here rather than silently skipped."""


TOOLS: tuple[tuple[str, str], ...] = (
    (r"lint_discovery", "lint_discovery"),
    (r"run_browser_tests", "browser suite"),
    (r"\bruff\s+format\b", "ruff format"),
    (r"\bruff\s+check\b", "ruff check"),
    (r"\bmypy\b", "mypy"),
    (r"\bpytest\b", "pytest"),
)
"""What a command has to contain to count as running that check. **Order matters**: `ruff format` is
tested before `ruff check` so the more specific one wins."""


def _tool(command: str) -> str | None:
    """The thing a command actually runs, reduced to a name both files can be compared on."""
    text = command.strip()
    if any(word in text for word in SETUP):
        return None
    return next((name for pattern, name in TOOLS if re.search(pattern, text)), None)


def workflows() -> list[Path]:
    """Every workflow file, sorted so a failure message reads the same way twice."""
    return sorted(_WORKFLOWS.glob("*.yml"))


def _tools_in(paths: list[Path]) -> set[str]:
    found = {
        _tool(line.split("run:", 1)[1])
        for path in paths
        for line in path.read_text(encoding="utf-8").splitlines()
        if re.match(r"\s*run:", line)
    }
    return {one for one in found if one is not None}


def on_push() -> list[Path]:
    """The workflows GitHub runs on a push, found by their trigger rather than by their name.

    ⚠️ A name-based split (`ci-*.yml` runs on push) would be a second place stating the trigger, and
    renaming a file would move it between categories without changing what it does."""
    return [p for p in workflows() if re.search(r"^  push:", p.read_text(encoding="utf-8"), re.M)]


def scheduled() -> list[Path]:
    return [p for p in workflows() if re.search(r"^  schedule:", p.read_text(encoding="utf-8"), re.M)]


def hook_tools() -> set[str]:
    """⚠️ **Commented lines are not commands, and the first version of this counted them.**

    The filter accepted any line containing `uv run`, so commenting a check out of the hook left this
    test green — verified by doing it. A scan that reads comments as code is the defect this file was
    written to catch, appearing in the file itself on its first run.
    """
    found = {
        _tool(line)
        for line in _HOOK.read_text(encoding="utf-8").splitlines()
        if "uv run" in line and not line.lstrip().startswith("#")
    }
    return {one for one in found if one is not None}


class TestTheHookAndCiCheckTheSameThings:
    def test_neither_side_checks_something_the_other_does_not(self) -> None:
        ci, hook = _tools_in(on_push()), hook_tools()

        assert on_push(), "no workflow runs on a push, so this proves nothing"
        assert ci, "no checking command was found in the push workflows, so this proves nothing"
        assert ci == hook, (
            f"the hook and CI disagree about what gets checked.\n"
            f"  CI only:   {sorted(ci - hook)}\n"
            f"  hook only: {sorted(hook - ci)}\n"
            f"`main` is not protected server-side, so a check CI runs and the hook does not is a red "
            f"push that nothing local stops."
        )

    def test_the_weekly_run_is_the_complete_one(self) -> None:
        # ⚠️ **The push workflows are split by path, so any one of them checks less than everything.**
        # `docs/ci.md` claims the weekly run is the whole suite from a clean checkout — the
        # independent confirmation that the hook has not been skipped or disabled. A weekly run
        # missing a check makes that claim false, and nothing else would notice.
        weekly = scheduled()

        assert len(weekly) == 1, f"expected one scheduled workflow, found {[p.name for p in weekly]}"
        assert _tools_in(weekly) == hook_tools(), (
            f"the weekly run is not the complete one.\n"
            f"  missing: {sorted(hook_tools() - _tools_in(weekly))}\n"
            f"  extra:   {sorted(_tools_in(weekly) - hook_tools())}"
        )

    def test_the_scan_finds_the_tools_it_is_named_for(self) -> None:
        # ⚠️ A comparison of two empty sets is equal and says nothing. Both sides are asserted to hold
        # the checks this project actually has, so an extraction that silently stops matching goes red
        # rather than agreeing with itself.
        expected = {"ruff check", "ruff format", "lint_discovery", "mypy", "pytest", "browser suite"}
        push = _tools_in(on_push())

        assert push == expected, f"the push workflows no longer run {sorted(expected - push)}"
        assert hook_tools() == expected, f"the hook no longer runs {sorted(expected - hook_tools())}"

    def test_setup_commands_are_excluded_deliberately(self) -> None:
        # The hook runs on a machine that is already set up and CI starts from nothing; that difference
        # is real, and naming it is what stops it being used to excuse a missing check later.
        assert _tool("uv sync --frozen --group dev") is None
        assert _tool("uv run playwright install --with-deps chromium") is None
        assert _tool("sudo apt-get update && sudo apt-get install -y unixodbc-dev") is None
