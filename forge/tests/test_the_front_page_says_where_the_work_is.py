"""The status table in `CLAUDE.md` agrees with the one in `docs/beta-0-plan.md`.

⚠️⚠️ **Written because they drifted, and the drift was invisible from either side.** `CLAUDE.md` said
*design complete at the "what and why" level, implementation starting* while four groups were built and
deployed-shaped, so a session opening cold concluded nothing existed and went looking in the wrong
place. The paragraph above it made three claims about the code that were all false by then. **Neither
file was wrong about itself.** This is the project's most-met defect — two places that should say the
same thing, with nothing checking that they agree — sitting on the front page.

⚠️ **A date is not the guard.** The heading carries one so a reader can judge how much to trust the row,
which is detection; this is the part that fails closed. Both are wanted for the same reason CI is a
report and the hook is the gate: knowing is not the same as being stopped.

⚠️⚠️ **The hook is the only thing that runs this.** `ci-forge.yml` skips a push that touches only
documents, and a change to either of these tables is exactly that — so on a `--no-verify` push nothing
looks. Named here rather than assumed, because a reader could reasonably believe CI covers it.
"""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_FRONT_PAGE = _ROOT / "CLAUDE.md"
_PLAN = _ROOT / "docs" / "beta-0-plan.md"

_FRONT_PAGE_HEADING = "## Where the work is"
_PLAN_HEADING = "## Where it stands"

_ROW = re.compile(r"^\|\s*\*\*([A-G])\*\*[^|]*\|([^|]*)\|")
"""One group's row: the letter in bold, then the status cell.

⚠️ Anchored on the **bold letter**, so a row in some other table that happens to start with a pipe
cannot match, and a body cell mentioning a group cannot either. This project has twice been caught by a
pattern matching the tail of another name; the bold markers are the delimiters here."""

_DONE = "✔"


def _table_under(path: Path, heading: str) -> dict[str, str]:
    """The group rows of the one table under `heading`, as `{letter: status cell}`.

    ⚠️ **Scoped to the section rather than to the whole file.** Both documents hold other tables, and a
    scan over everything would pick up rows that are not about progress at all — which is a check that
    reports on the wrong thing while looking like it works.
    """
    text = path.read_text(encoding="utf-8")
    assert heading in text, f"{path.name} has no section headed {heading!r}; this test cannot find the table"
    section = text.split(heading, 1)[1].split("\n## ", 1)[0]
    return {match[1]: match[2].strip() for line in section.splitlines() if (match := _ROW.match(line))}


class TestTheFrontPageAgreesWithThePlan:
    def test_both_tables_are_found_and_cover_every_group(self) -> None:
        # ⚠️ First, because every assertion below is vacuous over an empty dict. A parse that silently
        # matched nothing would make the whole file a check that cannot fire.
        front = _table_under(_FRONT_PAGE, _FRONT_PAGE_HEADING)
        plan = _table_under(_PLAN, _PLAN_HEADING)

        assert set(front) == set("ABCDEFG"), f"the front page's table covers {sorted(front)}"
        assert set(plan) == set("ABCDEFG"), f"the plan's table covers {sorted(plan)}"

    def test_the_same_groups_are_complete_in_both(self) -> None:
        """⚠️⚠️ Both directions, because each is a different failure.

        The front page claiming a group is finished when it is not sends a cold session past work that
        still has to be done. The front page *understating* is the drift that actually happened, and it
        sent one looking for code that already existed.
        """
        front = _table_under(_FRONT_PAGE, _FRONT_PAGE_HEADING)
        plan = _table_under(_PLAN, _PLAN_HEADING)

        front_done = {letter for letter, cell in front.items() if _DONE in cell}
        plan_done = {letter for letter, cell in plan.items() if _DONE in cell}

        assert front_done == plan_done, (
            f"CLAUDE.md calls {sorted(front_done)} complete and docs/beta-0-plan.md calls "
            f"{sorted(plan_done)} met. The plan is the authority; the front page is a pointer."
        )

    def test_the_front_page_says_when_it_was_last_checked(self) -> None:
        # ⚠️ Detection rather than prevention, and it is worth having anyway: without a date a reader
        # cannot tell a current status line from one that has been wrong for a month, which is the state
        # this section was in.
        heading = next(
            line
            for line in _FRONT_PAGE.read_text(encoding="utf-8").splitlines()
            if line.startswith(_FRONT_PAGE_HEADING)
        )

        assert re.search(r"\d{4}-\d{2}-\d{2}", heading), f"no date in {heading!r}"

    @pytest.mark.parametrize("path", [_FRONT_PAGE, _PLAN])
    def test_neither_table_marks_the_gate_complete(self, path: Path) -> None:
        """⚠️⚠️ B is the one row whose value is a claim about the *product*, not about the work.

        The hand-solve pack is the only verification of human derivability there is, and it is the
        operator's. **B1 is done and B1 is mine**, so a status cell reading `B1 ✔` in a column that
        means *is this group met* was a true sentence in a place where it says something false. It was
        there, and it is the reason this case is narrower than the one above.
        """
        heading = _FRONT_PAGE_HEADING if path == _FRONT_PAGE else _PLAN_HEADING

        assert _DONE not in _table_under(path, heading)["B"], (
            f"{path.name} marks B complete. The hand-solve gate is outstanding and it blocks beta 0; "
            f"B1 being done is not the group being met."
        )
