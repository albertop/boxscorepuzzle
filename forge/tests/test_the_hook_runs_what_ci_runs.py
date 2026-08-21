"""The pre-push hook and CI must check the same things.

⚠️⚠️ **They are two hand-maintained copies of one list.** (v36-P3-10) The hook re-spells CI's
commands, and `CLAUDE.md` is explicit about what the hook is for: `main` is not protected
server-side and cannot be, so the hook is *the nearest available thing* — and its whole value is
that a push to `main` has already run what CI runs.

Today they match command by command. **The agreement is maintained by hand**, and there is already a
deliberate divergence — CI runs Windows without coverage while the hook always measures it — which
proves the two lists can differ without anything noticing. A sixth CI step that never reaches the
hook leaves the hook passing while checking *less than CI does*: the fail-open it exists to prevent,
against the project's own rule that one predicate lives in one place.

**It cannot be one list.** One is YAML consumed by GitHub, the other is shell run by git; neither can
import the other. So they are two copies asserted to agree, which is the same treatment
`ACCEPTED_SOURCES` gets for the one other rule that has to exist twice.

⚠️ **The comparison is over TOOLS, not over exact command lines.** Pinning the strings would make
this red on `-q`, on a reordered flag, on a path spelled differently — a guard failing on its own
phrasing while the rule holds, which this project has recorded twice. What must not happen is a check
existing on one side and not the other.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_CI = _ROOT / ".github" / "workflows" / "ci.yml"
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


def ci_tools() -> set[str]:
    """Every checking command in the workflow, however its step is named."""
    found = {
        _tool(line.split("run:", 1)[1])
        for line in _CI.read_text(encoding="utf-8").splitlines()
        if re.match(r"\s*run:", line)
    }
    return {one for one in found if one is not None}


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
        ci, hook = ci_tools(), hook_tools()

        assert ci, "no checking command was found in the workflow, so this proves nothing"
        assert ci == hook, (
            f"the hook and CI disagree about what gets checked.\n"
            f"  CI only:   {sorted(ci - hook)}\n"
            f"  hook only: {sorted(hook - ci)}\n"
            f"`main` is not protected server-side, so a check CI runs and the hook does not is a red "
            f"push that nothing local stops."
        )

    def test_the_scan_finds_the_tools_it_is_named_for(self) -> None:
        # ⚠️ A comparison of two empty sets is equal and says nothing. Both sides are asserted to hold
        # the checks this project actually has, so an extraction that silently stops matching goes red
        # rather than agreeing with itself.
        expected = {"ruff check", "ruff format", "lint_discovery", "mypy", "pytest", "browser suite"}

        assert ci_tools() == expected, f"the workflow no longer runs {sorted(expected - ci_tools())}"
        assert hook_tools() == expected, f"the hook no longer runs {sorted(expected - hook_tools())}"

    def test_setup_commands_are_excluded_deliberately(self) -> None:
        # The hook runs on a machine that is already set up and CI starts from nothing; that difference
        # is real, and naming it is what stops it being used to excuse a missing check later.
        assert _tool("uv sync --frozen --group dev") is None
        assert _tool("uv run playwright install --with-deps chromium") is None
        assert _tool("sudo apt-get update && sudo apt-get install -y unixodbc-dev") is None
        # And a check is never mistaken for setup.
        assert _tool("uv run pytest --cov --cov-report=term-missing") == "pytest"
