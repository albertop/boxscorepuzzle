"""No `subprocess` call decodes with whatever the machine's locale happens to be.

⚠️⚠️ **`text=True` alone means *cp1252 on Windows*, and it cost a five-minute timeout reported as the
wrong thing entirely.** A migration carrying `⚠️` and em dashes was piped into `psql`; the thread writing
stdin died with `UnicodeEncodeError: 'charmap' codec can't encode characters` **still holding the pipe**,
so `psql` waited for input that would never arrive and the call was killed at 300 seconds. What the suite
reported was `TimeoutExpired` — true, useless, and pointing at the container rather than at the encoding.

⚠️ **This is `CLAUDE.md`'s recorded cp1252 class in a place its guard cannot reach.** That guard is a
static check over every `print` argument; this is a subprocess's stdin and stdout. Nine calls in the
repository had the defect and none had ever been hit, because nothing non-ASCII had crossed one before.

**Decidable, so it is a test rather than a discipline**: the two properties are visible in the call site.
"""

from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_CALLS = ("subprocess.run", "subprocess.Popen", "subprocess.check_output", "subprocess.check_call")
_TEXT = ("text", "universal_newlines")


def _offenders() -> list[str]:
    found = []
    for path in sorted(_ROOT.rglob("*.py")):
        if any(part in {".venv", "__pycache__", "node_modules", ".git"} for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or ast.unparse(node.func) not in _CALLS:
                continue
            named = {keyword.arg for keyword in node.keywords}
            if named & set(_TEXT) and "encoding" not in named:
                found.append(f"{path.relative_to(_ROOT).as_posix()}:{node.lineno}")
    return found


def test_the_sweep_finds_subprocess_calls_to_check() -> None:
    """⚠️ A check over an empty set passes forever. This asserts there is a subject before judging it."""
    total = 0
    for path in sorted(_ROOT.rglob("*.py")):
        if any(part in {".venv", "__pycache__", "node_modules", ".git"} for part in path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        total += sum(1 for node in ast.walk(tree) if isinstance(node, ast.Call) and ast.unparse(node.func) in _CALLS)
    assert total > 5, f"only {total} subprocess calls found; this test would pass over almost nothing"


def test_every_text_mode_subprocess_names_utf8() -> None:
    """The rule. ⚠️ Seen red by removing `encoding` from the call that produced the finding."""
    offenders = _offenders()

    assert not offenders, (
        "these decode with the machine's locale rather than UTF-8, which is cp1252 on Windows: " + ", ".join(offenders)
    )
