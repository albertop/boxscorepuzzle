"""Only Retrosheet tables. **`dbo.retro*` and nothing else, in anything that queries.**

⚠️⚠️ **The rule exists because its one violation was invisible.** The loader joined `dbo.regPeople` for
player names — a table from another collection in the same database — and it resolved 98.4% of
identifiers. A join that resolves most rows looks exactly like a join that resolves all of them, and
the 316 it missed were published under a fabricated `Unknown` rather than rejected.

**Every other collection in this database is one query away and several look like they would do.**
`bdb*` is Lahman, `fg*` is FanGraphs, `mlb*` and `dgl*` are others again. They disagree with Retrosheet
about player identifiers, about which games exist and about what a season is — and a board built from
two of them is internally consistent and corresponds to nothing. §22's four layers cannot see it: they
check that the numbers agree with each other.

**So the boundary is the collection, not the correctness of any one join.** A guard naming a single
forbidden table has to be written again for the next one, which is why this replaces the `dbo.regPeople`
assertion that used to live in `test_reveal_names.py`. One predicate, one place.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

SEARCHED = ("discovery", "forge")
"""Where SQL is written. `serve/` has no database and must never gain one (§33)."""

THIS_FILE = Path(__file__).name
"""⚠️ **A guard cannot be its own subject.** This file names forbidden tables in order to forbid them.
`test_reveal_names.py` records the same trap: its first version searched for a bare `regPeople` and
fired on the docstring explaining why the table was removed. Exactly one file is exempt, asserted."""

QUALIFIED = re.compile(r"\bdbo\.(\w+)")
SOURCE = re.compile(r"\b(?:FROM|JOIN)\s+([A-Za-z_(][\w.]*)")
COMMON_TABLE = re.compile(r"(\w+)\s+AS\s*\(", re.IGNORECASE)
SQL_BLOCK = re.compile(r'"""(.*?)"""', re.DOTALL)


def queries(source: str) -> list[str]:
    """The SQL in a file: triple-quoted blocks containing a `SELECT`.

    ⚠️⚠️ **The scan reads SQL, not Python, and the first version did not.** It matched `FROM|JOIN`
    case-insensitively across whole files and fired on every `from x import y` and on English prose —
    *from the*, *from one*, *from scratch*. That is the condition this project has written down twice:
    **a check that fires on everything carries no information**, exactly like one that never fires. It
    was caught by running it, not by reading it.

    Upper case only, and only inside a block that contains a `SELECT`. Python's keyword is lower case
    and every query here is written in capitals, which separates the two languages without parsing
    either.
    """
    return [block for block in SQL_BLOCK.findall(source) if "SELECT" in block]


def python_files() -> list[Path]:
    found = [
        path
        for directory in SEARCHED
        for path in (_ROOT / directory).rglob("*.py")
        if ".venv" not in path.parts and "__pycache__" not in path.parts and path.name != THIS_FILE
    ]
    assert found, "the scan found no Python at all, which means it is searching the wrong place"
    return found


def test_every_qualified_table_is_a_retrosheet_one() -> None:
    """`dbo.X` must be `dbo.retroX` — the direct form, and the one the defect took."""
    strays: list[str] = []
    for path in python_files():
        for block in queries(path.read_text(encoding="utf-8")):
            strays += [
                f"{path.relative_to(_ROOT)}: dbo.{name}"
                for name in QUALIFIED.findall(block)
                if not name.startswith("retro")
            ]

    assert not strays, "tables outside the Retrosheet collection are being read:\n  " + "\n  ".join(strays)


def test_no_query_reads_an_unqualified_table() -> None:
    """A bare `FROM someTable` is the same defect with the schema left off.

    ⚠️ **Common table expressions and derived tables are not tables.** A guard that could not tell them
    apart would fire on `FROM admissible` and `JOIN shape` — correct SQL in the pool query — and get
    loosened until it said nothing. CTE names are collected from the whole file, because a query is
    often assembled from constants and the `WITH` need not share a string with the `FROM` that uses it.
    """
    strays: list[str] = []
    for path in python_files():
        source = path.read_text(encoding="utf-8")
        defined = {name.lower() for name in COMMON_TABLE.findall(source)}
        for block in queries(source):
            strays += [
                f"{path.relative_to(_ROOT)}: FROM/JOIN {target}"
                for target in SOURCE.findall(block)
                if not target.startswith("(") and target.lower() not in defined and not target.startswith("dbo.retro")
            ]

    assert not strays, "queries read something that is not a qualified Retrosheet table:\n  " + "\n  ".join(strays)


def test_exactly_one_file_is_exempt_from_the_scan() -> None:
    """⚠️ **The exemption is asserted, not trusted.** A guard that skips files is one skipped file away
    from guarding nothing."""
    exempt = [path for path in (_ROOT / "forge").rglob("*.py") if path.name == THIS_FILE]

    assert len(exempt) == 1, f"the exempt name matches {len(exempt)} files: {exempt}"


def test_the_patterns_reject_and_accept_the_right_things() -> None:
    """⚠️⚠️ **The failing cases, because a scan that finds nothing looks exactly like a broken one.**

    Both halves are asserted: what must be caught, and what must not. The second half is the one that
    matters — every version of this guard that was wrong was wrong by matching too much.
    """
    # Caught.
    assert QUALIFIED.findall("SELECT * FROM dbo.bdbBatting b") == ["bdbBatting"]
    assert QUALIFIED.findall("SELECT 1 JOIN dbo.fgTeamsBatting t") == ["fgTeamsBatting"]
    assert SOURCE.findall("SELECT 1 FROM mlbTeams") == ["mlbTeams"]

    # Not caught, and each of these is a false positive an earlier version produced.
    assert SOURCE.findall("SELECT 1 FROM (SELECT 1) x")[0].startswith("(")
    assert COMMON_TABLE.findall("WITH admissible AS (SELECT 1)") == ["admissible"]
    assert SOURCE.findall("from pathlib import Path") == [], "the scan reads Python imports as tables"
    assert SOURCE.findall("a rule carried over from the earlier run") == [], "the scan reads English prose"
    assert queries('"""A docstring naming dbo.bdbBatting and FROM clauses."""') == [], "a docstring is not a query"
