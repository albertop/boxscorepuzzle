"""The footnote line, against the canonical strings the browser renderer also runs.

⚠️ **The two renderers had drifted in three ways at once.** The PDF pack printed no count and no `#`
and put `LOB` last; the phone board printed the term *total* then `#`-prefixed slots and put `LOB`
first. A board with `SH` total 2 across slots 2 and 9b came out `SH: 2, 9b` from one and
`SH: 2 #2, #9b` from the other. **Reading the PDF alone suggested they agreed**, which is exactly why
this is data both sides run rather than a comparison somebody performs.

§33 forbids `forge/` and `serve/` sharing a function, so they share the file — the same arrangement as
the package conformance vectors. What it forbids is the two disagreeing.

⚠️ **The format change is a correctness fix, not a tidy-up.** `SH: 2` was a slot reference that reads
as a count, and a row carrying two of one term could not be expressed at all. Over the admissible pool,
**4,040 of 100,742 directions carry at least one such row — 4.01%**, rising to 8.31% in the 1920s.
Those boards are unsolvable, and every total balances on them, which is why no validation layer saw it.
"""

import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from boxscore_package.format import Board, LineScore

_ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads((_ROOT / "serve" / "tests" / "footnote-line-vectors.json").read_text(encoding="utf-8"))


def _renderer() -> ModuleType:
    for extra in (_ROOT / "discovery" / "hand-solve", _ROOT / "discovery" / "difficulty-metrics"):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    import build_pack  # noqa: PLC0415

    return build_pack


def _board(case: dict[str, Any]) -> Board:
    rows = len(case["footnotes"])
    return Board(
        batting=((0,) * 6,) * rows,
        batting_totals=(0,) * 6,
        footnotes=tuple(tuple(row) for row in case["footnotes"]),
        footnote_totals=tuple(sum(row[i] for row in case["footnotes"]) for i in range(4)),
        pitching=((0,) * 6,),
        pitching_totals=(0,) * 6,
        left_on_base=case["left_on_base"],
        line_score=LineScore(
            offense_by_inning=(0,),
            defense_by_inning=(0,),
            offense_runs=0,
            offense_hits=0,
            offense_errors=0,
            defense_runs=0,
            defense_hits=0,
            defense_errors=0,
        ),
    )


def _slots(case: dict[str, Any]) -> tuple[int, ...]:
    """The lineup slots that produce this case's references — `9a`/`9b` from two rows in slot 9.

    ⚠️ Derived rather than stated, because `slot_references()` is the one definition of that mapping and
    a test carrying its own copy would pass while the two disagreed.
    """
    return tuple(int(reference[0]) for reference in case["slot_references"])


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda c: c["name"])
def test_the_pdf_renderer_produces_the_canonical_line(case: dict[str, Any]) -> None:
    build_pack = _renderer()
    slots = _slots(case)

    assert build_pack.slot_references(slots) == tuple(case["slot_references"]), (
        "the case's slot references are not what slot_references() produces for these slots"
    )
    assert build_pack.footnote_line(_board(case), slots) == case["expected"]


def test_every_case_says_why() -> None:
    # A case without a reason is a rule nobody can evaluate when it starts failing.
    for case in VECTORS["cases"]:
        assert case.get("why"), f"{case['name']} carries no reason"


def test_the_cases_cover_both_the_one_and_the_many() -> None:
    """⚠️ A file of single-occurrence cases would pass a renderer that never prints a count above one.

    That renderer is the one this change exists to replace, so the file has to contain the case it
    could not express.
    """
    values = [value for case in VECTORS["cases"] for row in case["footnotes"] for value in row]

    assert any(value == 1 for value in values), "no case carries a single occurrence"
    assert any(value > 1 for value in values), "no case carries more than one of a term in one row"


class TestEveryPrintedTermCarriesBoth:
    """The parity rule: a non-zero term renders **a count and at least one slot reference**.

    ⚠️ Stated as what it forbids. A renderer that dropped the count would satisfy every string
    comparison above only if the vectors happened to cover the shape it broke; this fails on any term
    rendered with one half and not the other, including a term the vectors do not contain.
    """

    @pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda c: c["name"])
    def test_a_rendered_term_has_a_count_and_a_slot(self, case: dict[str, Any]) -> None:
        build_pack = _renderer()
        line = build_pack.footnote_line(_board(case), _slots(case))

        terms = [part for part in line.split("   ") if not part.startswith("LOB:")]
        expected_terms = sum(1 for column in range(4) if any(row[column] for row in case["footnotes"]))
        assert len(terms) == expected_terms, f"{len(terms)} terms rendered against {expected_terms} non-zero"

        for term in terms:
            for carrier in term.split(": ", 1)[1].split(", "):
                count, _, slot = carrier.partition(" ")
                assert count.isdigit() and int(count) > 0, f"{carrier!r} has no count"
                assert slot.startswith("#") and len(slot) > 1, f"{carrier!r} has no slot reference"
