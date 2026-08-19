"""A reveal name is the name the man was called, and it is composed in one place.

⚠️ **The source table was wrong and nothing could see it.** The loader joined `dbo.regPeople`, which
does not belong to the Retrosheet collection at all — it is another dataset that happens to carry a
`key_retro` column. It matched **19,703 of the 20,019 players the pool contains**; the other 316 fell
through a `LEFT JOIN` and were published as `Unknown`. `dbo.retroMaster`, the Retrosheet master file
keyed by the same identifier the daily rows carry, matches **20,019 of 20,019**.

⚠️ **And `nickname`, never `first`.** In the master file `first` is the full legal given name — `Henry
Louis` for Hank Aaron, `John Franklin` for Home Run Baker — and `nickname` is what the man was called.
A reveal built from `first` prints a name no boxscore, no broadcast and no player ever used, and §7
says the reveal is the real boxscore.

⚠️ **A surname alone is the answer when it is all that is known**, and the old code got that right:
`f"{first} {last}".strip()` gave the surname when the given name was missing. 113 of the players in the
pool are in that position — identifiers carrying `u` in the fifth position, Retrosheet's mark for *first
name unknown*, each appearing in two to five rows.

What the old code lost was the other case. Its `or "Unknown"` fired only when **both** fields were
empty, which is what a missing `regPeople` row produced — so those 316 players were published as
`Unknown` with **the surname thrown away too**. The placeholder-name check in `plausibility` could not
catch it, because `Unknown` is not blank.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def _loader() -> object:
    for extra in (_ROOT / "discovery" / "difficulty-metrics", _ROOT / "forge" / "src"):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    spec = importlib.util.spec_from_file_location(
        "reveal_names_loader", _ROOT / "discovery" / "difficulty-metrics" / "measure.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("nickname", "last", "expected"),
    [
        ("Hank", "Aaron", "Hank Aaron"),
        ("Home Run", "Baker", "Home Run Baker"),
        # ⚠️ The 113: the surname alone, which is all that is recorded about them.
        (None, "Pitts", "Pitts"),
        ("", "Pitts", "Pitts"),
        ("  Andy  ", "  Abad  ", "Andy Abad"),
    ],
)
def test_the_name_is_the_one_he_was_called(nickname: str | None, last: str | None, expected: str) -> None:
    assert _loader().full_name(nickname, last) == expected


def test_nothing_known_stays_empty_rather_than_becoming_a_placeholder() -> None:
    """⚠️ Empty on purpose, so the check that rejects a blank reveal name still means something.

    `Unknown` here would satisfy `plausibility.faults` — it is not blank — and would publish a given
    name the man never had. Leaving it empty makes the existing check the thing that fires.
    """
    assert _loader().full_name(None, None) == ""


def test_the_loader_reads_the_retrosheet_master_and_not_the_other_dataset() -> None:
    """⚠️ The table itself, asserted, because the wrong one produced plausible names for 98.4% of rows.

    A join that resolves most identifiers looks exactly like a join that resolves all of them, and the
    316 it missed were published as a fabricated name rather than rejected.
    """
    source = (_ROOT / "discovery" / "difficulty-metrics" / "measure.py").read_text(encoding="utf-8")

    # ⚠️ **The qualified table name, not the bare word.** The first version searched for `regPeople`
    # anywhere in the file and fired on the docstring that explains why the table was replaced — a guard
    # that forbids describing the defect it guards against. What is forbidden is reading the table.
    assert "dbo.regPeople" not in source, "the loader still reads a table outside the Retrosheet collection"
    assert source.count("dbo.retroMaster m ON m.playerID = d.PLAYER_ID") == 2, "both row queries join the master"
    assert "m.first" not in source, "the loader reads the legal given name, which is not what he was called"


def test_no_consumer_reassembles_the_name() -> None:
    """One rule, one place. ⚠️ Two consumers used to join a `(first, last)` pair differently — the
    reference writer with `.strip() or "Unknown"`, the prototype builder with neither."""
    for path in (
        _ROOT / "forge" / "scripts" / "write_reference_puzzles.py",
        _ROOT / "discovery" / "board-prototype" / "build.py",
    ):
        source = path.read_text(encoding="utf-8")
        assert "{first} {last}" not in source, f"{path.name} still composes a name of its own"
