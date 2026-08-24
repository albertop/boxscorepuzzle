"""The browser guard's module list must name every module `serve/ui/phone/` ships.

⚠️⚠️ **It named five of fifteen, and the ten it missed included the file that gained date arithmetic.**
`engine.test.js`'s *no source under serve/ computes a calendar date* is the assertion behind E1.2's claim
that `serve` owes no third `ROLLOVER_OFFSET_HOURS`. It iterated a hand-written list of five modules;
`landing.js` was not on it, and `landing.js` is where the countdown's `Date.parse` and subtraction went.

**The guard was green and the property it names was unchecked in two thirds of the tree.** Nothing about
the test looked wrong -- a list of modules beside a loop reads as deliberate scope, not as an omission.

⚠️ **A browser cannot enumerate a directory**, which is why the list exists at all and why this check is
here rather than there: `forge` can read the filesystem. Same arrangement as
`test_every_page_declares_itself.py`.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PHONE = _ROOT / "serve" / "ui" / "phone"
_SUITE = _ROOT / "serve" / "tests" / "engine.test.js"


def _listed() -> set[str]:
    source = _SUITE.read_text(encoding="utf-8")
    block = re.search(r"const PLAYER_MODULES = \[(.*?)\];", source, re.DOTALL)
    assert block, "engine.test.js no longer declares PLAYER_MODULES; the guard it feeds names nothing"
    return set(re.findall(r'"([^"]+\.js)"', block[1]))


def test_the_sweep_finds_modules_to_check() -> None:
    """⚠️ A check over an empty set passes forever. Assert the subject exists before comparing it."""
    assert len(_listed()) >= 10
    assert len(list(_PHONE.glob("*.js"))) >= 10


def test_every_shipped_module_is_on_the_list() -> None:
    """The half that failed: a module added to the directory and not to the list is never scanned."""
    shipped = {path.name for path in _PHONE.glob("*.js")}
    missing = shipped - _listed()
    assert not missing, f"{sorted(missing)} ship under ui/phone/ and the date guard never reads them"


def test_the_list_names_nothing_that_is_gone() -> None:
    """⚠️ And the other direction, which fails differently: a name that no longer exists.

    The browser test fetches each entry, so a stale name is a 404 whose body is an error page -- and an
    error page contains neither `ROLLOVER` nor `getTimezoneOffset`, so **the scan passes on it**. A
    deleted module would leave the list looking complete while one entry checked nothing at all.
    """
    shipped = {path.name for path in _PHONE.glob("*.js")}
    stale = _listed() - shipped
    assert not stale, f"{sorted(stale)} are on the date guard's list and no longer exist"
