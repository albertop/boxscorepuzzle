"""The group instrument's three measurements, called rather than read.

⚠️ **Every test written for this instrument so far asserted on source text or on trace activity, and
every one of them passed while the thing it guarded was broken.** Three faults reached a reported
number that way:

  a metric that could not vary — blockage on a board where every other cell was given;
  a metric that could not fire where it mattered — a baseline that removed the group along with the
  erasure, so the comparison was a board against itself on exactly the published states in question;
  denominators chosen by the *title string* of a report heading.

So these call `metrics.py` and `report()` directly. A test that greps for `group.completions == 1`
proves the fragment exists somewhere, not that it governs the table.
"""

import importlib.util
import io
import sys
from collections.abc import Callable
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from boxscore_forge.boxscore import Direction
from boxscore_forge.constraints import cell_values, footnote_cell, shape_of
from boxscore_forge.erasure import erase
from boxscore_forge.identities import FOOTNOTE_COLUMNS

_GROUPS = Path(__file__).resolve().parents[2] / "discovery" / "footnote-groups"


def _module(name: str) -> object:
    for extra in (_GROUPS, _GROUPS.parents[0] / "difficulty-metrics", Path(__file__).resolve().parents[1] / "src"):
        if str(extra) not in sys.path:
            sys.path.insert(0, str(extra))
    spec = importlib.util.spec_from_file_location(f"fg_{name}", _GROUPS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hidden() -> frozenset[str]:
    """The first batting row's footnote cells — one slot group, whichever board it is on."""
    return frozenset(footnote_cell(0, column) for column in FOOTNOTE_COLUMNS)


@dataclass(frozen=True)
class _Solved:
    """What `solve` returns, reduced to what these metrics read."""

    values: dict
    deductions: tuple = ()


def _fake_solve(marker: str, needs: frozenset[str]) -> Callable[[object, dict], _Solved]:
    """A solver that settles `marker` only when every cell in `needs` was given.

    ⚠️ **A fake rather than a real board, because the assertion has to be exact.** The test this
    replaces called the production function and asserted the result was `True` or `False` — which the
    corrected implementation and the broken one both satisfy, so reverting the fix would have left the
    guard green. This one distinguishes them.
    """

    def solve(shape: object, given: dict) -> _Solved:  # noqa: ARG001
        settled = dict(given)
        if needs <= set(given):
            settled[marker] = 1
        return _Solved(values=settled)

    return solve


class TestTheBaselineRestoresTheGroup:
    """⚠️ The defect: the baseline removed every cell in the sampled erasure, and footnote cells **are**
    erasable. When the erasure had already hidden the group, baseline and treatment were the same board
    and blockage was forced false — on precisely the states the question is about.
    """

    def _setup(self) -> tuple[object, frozenset[str], frozenset[str], dict]:
        metrics = _module("metrics")
        hidden = frozenset({"footnotes[0].hit_by_pitch"})
        # The adversarial case: the erasure already contains the group.
        erased = hidden | {"batting[1].hits"}
        values = {"batting[0].hits": 1, "batting[1].hits": 2, "footnotes[0].hit_by_pitch": 0}
        return metrics, hidden, erased, values

    def test_it_is_true_when_restoring_the_group_unlocks_an_outside_cell(self, monkeypatch: pytest.MonkeyPatch) -> None:
        metrics, hidden, erased, values = self._setup()
        monkeypatch.setattr(metrics, "solve", _fake_solve("batting[1].hits", hidden))

        assert metrics.stops_progress(None, values, erased, hidden) is True

    def test_it_is_false_when_the_group_unlocks_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The other direction. A predicate that always said True would pass the test above.
        metrics, hidden, erased, values = self._setup()
        monkeypatch.setattr(metrics, "solve", _fake_solve("batting[1].hits", frozenset()))

        assert metrics.stops_progress(None, values, erased, hidden) is False

    def test_the_broken_baseline_would_have_said_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The guard, stated as the thing it rejects.

        With the old construction the baseline excluded all of `erased`, so on this input it never
        held the group and could not settle the outside cell — the two closures matched and blockage
        came out false. The production function is handed the same input and must disagree.
        """
        metrics, hidden, erased, values = self._setup()
        monkeypatch.setattr(metrics, "solve", _fake_solve("batting[1].hits", hidden))

        broken_baseline = metrics.solve(None, {k: v for k, v in values.items() if k not in erased})
        broken_treatment = metrics.solve(None, {k: v for k, v in values.items() if k not in (erased | hidden)})

        assert set(broken_baseline.values) == set(broken_treatment.values), "the old construction differed"
        assert metrics.stops_progress(None, values, erased, hidden) is True, "the fix is not in place"


class TestCardinalityAndDerivabilityAreDifferentQuestions:
    def test_a_complete_board_has_exactly_one_completion(self, cubs_at_braves_1968: Direction) -> None:
        from boxscore_forge.publish import to_board  # noqa: PLC0415

        metrics = _module("metrics")

        assert metrics.completions(to_board(cubs_at_braves_1968, _hidden())) == 1

    def test_a_group_the_board_determines_is_derivable(self, cubs_at_braves_1968: Direction) -> None:
        # Exact, not membership in {True, False} — which the broken implementation also satisfied.
        metrics = _module("metrics")
        shape, values = shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968)

        assert metrics.derivable(shape, values, _hidden()) is True

    def test_a_board_the_solver_cannot_finish_is_not_derivable(self, cubs_at_braves_1968: Direction) -> None:
        # The counterexample: hide enough that propagation and bounding cannot close it.
        metrics = _module("metrics")
        shape, values = shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968)
        far_too_much = frozenset(values) - {"line_score.offense_runs"}

        assert metrics.derivable(shape, values, far_too_much) is False


class TestTheDenominatorsAreDeclaredNotInferred:
    """⚠️ Which population a table used was decided by whether its heading began with `DERIVABLE` or
    `HIDING`. Renaming a heading silently restored the unconditional denominator, and no test would
    have failed — the fragment stayed in the file.
    """

    def _groups(self, module: object) -> list[object]:
        return [
            # unique and derivable, three trials, one of which blocked
            module.Group(rows=1, terms=2, completions=1, derivable=True, trials=3, stopped=1, used=2),
            # ambiguous: not a solver failure, and must not count against derivability
            module.Group(rows=1, terms=2, completions=2, derivable=False, trials=3, stopped=0, used=0),
            # unmeasured: no erasure reached the target, and must not count as a negative
            module.Group(rows=1, terms=2, completions=1, derivable=True, trials=0, stopped=0, used=0),
        ]

    def test_derivability_excludes_the_ambiguous_group(self) -> None:
        module = _module("measure")
        groups = self._groups(module)
        row = next(r for r in module.ROWS if r.title.startswith("DERIVABLE"))

        eligible = [g for g in groups if row.eligible(g)]

        assert len(eligible) == 2, "an ambiguous group entered the conditional denominator"
        assert sum(row.numerator(g) for g in eligible) == 2

    def test_blockage_excludes_the_unmeasured_group_and_counts_trials(self) -> None:
        module = _module("measure")
        groups = self._groups(module)
        row = next(r for r in module.ROWS if r.title.startswith("TRIALS WHERE HIDING"))

        eligible = [g for g in groups if row.eligible(g)]

        assert len(eligible) == 2, "a group with no successful erasure entered the denominator"
        assert sum(row.denominator(g) for g in eligible) == 6, "the denominator is trials, not groups"
        assert sum(row.numerator(g) for g in eligible) == 1

    def test_every_row_declares_its_own_eligibility(self) -> None:
        # The structural guarantee: no row can inherit a denominator from its display copy.
        module = _module("measure")

        assert all(callable(row.eligible) for row in module.ROWS)
        assert len({row.title for row in module.ROWS}) == len(module.ROWS)

    def test_the_report_prints_numerator_and_denominator(self) -> None:
        module = _module("measure")
        captured = io.StringIO()

        with redirect_stdout(captured):
            module.report(self._groups(module), module.Coverage(directions=1, attempted=3, reached=2))
        printed = captured.getvalue()

        assert "[1/6]" in printed, "the blockage cell did not print its trial counts"
        assert "2 reached 8 stalls" in printed, "the run-level coverage line is missing"
        assert "group-erasure trials: 6" in printed, "group trials were not distinguished from erasures"
        assert "groups with no successful erasure: 1" in printed


class TestTheArtifactDeclaresItself:
    def _identity(self, module: object, **overrides: object) -> object:
        fields = {
            "revision": "abc1234",
            "tracked_changes": "clean",
            "untracked": "clean",
            "instrument": "0" * 12,
        }
        return module.RunIdentity(**{**fields, **overrides})

    def _stamp(self, module: object, identity: object) -> str:
        return module.provenance(identity, module.Coverage(directions=1, attempted=3, reached=3), groups=2, trials=3)

    def test_the_stamp_carries_the_schema_and_a_completion_marker(self) -> None:
        module = _module("measure")

        stamp = self._stamp(module, self._identity(module))

        assert f"result schema      {module.RESULT_SCHEMA}" in stamp
        assert stamp.strip().endswith("COMPLETE"), "an interrupted run must not look finished"

    def test_the_stamp_renders_what_it_was_handed_rather_than_asking_git(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """⚠️ The defect: the stamp was assembled *after* every board had been measured.

        Hours of solving separate the code that ran from the tree `git` is asked about, so an edit
        landing mid-run was recorded as the state the run began in — the exact change the stamp exists
        to expose. Capture is `identify()`, before measurement; `provenance` only formats.

        The guard is stated as what it forbids: `_git` is made to fail, and the stamp must be
        unaffected. A version that called `git` itself would print `unknown` here.
        """
        module = _module("measure")
        monkeypatch.setattr(module, "_git", lambda *_: pytest.fail("provenance asked the repository"))

        stamp = self._stamp(module, self._identity(module, revision="deadbee"))

        assert "deadbee" in stamp
        assert "unknown" not in stamp

    def test_the_stamp_separates_tracked_edits_from_untracked_files(self) -> None:
        # ⚠️ `--dirty` does not see untracked files, and counting both together made an ordinary edit
        # read as an unknown file. Two questions, two lines.
        module = _module("measure")

        stamp = self._stamp(module, self._identity(module, tracked_changes="2 files, aa11bb22", untracked="clean"))

        assert "tracked changes    2 files, aa11bb22" in stamp
        assert "untracked files    clean" in stamp
        assert "instrument         sha256" in stamp, "the instrument is not identified by content"

    def test_the_stamp_names_the_inputs_and_not_only_their_count(self) -> None:
        """⚠️ A direction count is not the data. The database can change between runs while the
        revision and the source digest are identical, so two different samples carried one provenance.
        """
        module = _module("measure")
        boards = [SimpleNamespace(game_id="ATL196805110", offense_team="CHN")]

        identity = self._identity(module).with_inputs(boards)
        other = self._identity(module).with_inputs([*boards, SimpleNamespace(game_id="X", offense_team="Y")])

        assert identity.directions == ("ATL196805110:CHN",)
        assert identity.inputs != other.inputs, "the digest did not follow the sample"
        assert f"inputs             sha256 {identity.inputs} over 1 directions" in self._stamp(module, identity)

    def test_the_digest_does_not_depend_on_the_order_the_loader_returned(self) -> None:
        # Sorted before hashing, so a reordered sample is recognised as the same inputs rather than
        # reported as different ones.
        module = _module("measure")
        one = SimpleNamespace(game_id="A", offense_team="X")
        two = SimpleNamespace(game_id="B", offense_team="Y")

        first = self._identity(module).with_inputs([one, two])
        reversed_order = self._identity(module).with_inputs([two, one])

        assert first.inputs == reversed_order.inputs

    @pytest.mark.parametrize(
        ("field", "publishable"),
        [("revision", False), ("tracked_changes", False), ("untracked", False), ("instrument", True)],
    )
    def test_either_repository_question_failing_refuses_publication(self, field: str, *, publishable: bool) -> None:
        """⚠️ Only `revision unknown` used to block. A failed `git status` published a result that
        could not say whether an untracked file had shadowed an imported dependency — the absence of a
        check reading as the presence of a passing one.
        """
        module = _module("measure")

        assert self._identity(module, **{field: "unknown"}).publishable is publishable
        assert self._identity(module).publishable is True, "a clean identity must publish"


class TestPublicationCannotCollideOrLeaveDebris:
    """⚠️ An atomic final rename protects the destination, not the preparation.

    Two overlapping runs sharing one staging name can truncate each other or move the other's bytes
    into the canonical path. The guard has to force the collision: a test that greps for `getpid`
    proves a fragment exists, not that the name is what keeps the runs apart.
    """

    def test_two_publications_to_one_destination_stage_different_paths(self, tmp_path: Path) -> None:
        module = _module("measure")
        out = tmp_path / "results.txt"

        first = module.publish(out, "first", pid=101, nonce=lambda: "aaaa")
        second = module.publish(out, "second", pid=102, nonce=lambda: "bbbb")

        assert first != second
        assert out.read_text(encoding="utf-8") == "second"

    def test_the_nonce_separates_runs_that_share_a_pid(self, tmp_path: Path) -> None:
        # A pid is reused by the operating system, so it is not by itself a distinguisher.
        module = _module("measure")
        out = tmp_path / "results.txt"

        first = module.publish(out, "first", pid=101, nonce=lambda: "aaaa")
        second = module.publish(out, "second", pid=101, nonce=lambda: "bbbb")

        assert first != second

    def test_the_staging_file_shares_the_destination_directory(self, tmp_path: Path) -> None:
        # `replace` is atomic only within a filesystem; a staging path elsewhere is a copy that can
        # half-arrive.
        module = _module("measure")
        out = tmp_path / "nested" / "results.txt"
        out.parent.mkdir()

        assert module.publish(out, "text", pid=1, nonce=lambda: "cc").parent == out.parent

    def test_nothing_is_left_behind_when_the_replace_fails(self, tmp_path: Path) -> None:
        """The failing case, not the passing one: a partial file beside the real one is what the
        staging name exists to prevent, and `finally` is the only thing removing it."""
        module = _module("measure")
        out = tmp_path / "results.txt"
        out.mkdir()  # a directory where the file should be, so `replace` cannot succeed

        with pytest.raises(OSError):
            module.publish(out, "text", pid=1, nonce=lambda: "dd")

        assert [entry.name for entry in tmp_path.iterdir()] == ["results.txt"]
        assert not list(out.iterdir()), "the staging file survived a failed replace"


class TestBlockageCanStillBeObserved:
    def test_an_erased_board_deduces_something_outside_the_group(self, cubs_at_braves_1968: Direction) -> None:
        # Not a claim that this board blocks — a claim that the comparison is capable of showing it.
        from boxscore_forge.solver import solve  # noqa: PLC0415

        puzzle = erase(cubs_at_braves_1968, target_stalls=8, seed=907)

        assert puzzle is not None
        shape, values = shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968)
        hidden = _hidden()
        treatment = solve(shape, {k: v for k, v in values.items() if k not in (puzzle.erased | hidden)})

        assert [step for step in treatment.deductions if step.cell not in hidden]

    @pytest.mark.parametrize("seed", [907, 908, 909])
    def test_each_seed_is_a_separate_trial(self, seed: int, cubs_at_braves_1968: Direction) -> None:
        # One erasure per board is one sample of the thing blockage measures, not a rate.
        assert erase(cubs_at_braves_1968, target_stalls=8, seed=seed) is not None
