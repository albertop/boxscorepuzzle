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
from dataclasses import dataclass, replace
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

    def _sample(self, board: Direction, slots: tuple[int, ...] = (), name: str = "ATL196805110") -> object:
        return SimpleNamespace(
            game_id=name,
            offense_team="CHN",
            direction=board,
            slots=slots or tuple(range(1, len(board.batting) + 1)),
        )

    def test_the_stamp_names_the_inputs_and_not_only_their_count(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ A direction count is not the data. The database can change between runs while the
        revision and the source digest are identical, so two different samples carried one provenance.
        """
        module = _module("measure")
        boards = [self._sample(cubs_at_braves_1968)]

        identity = self._identity(module).with_inputs(boards)
        other = self._identity(module).with_inputs([*boards, self._sample(cubs_at_braves_1968, name="BOS197000000")])

        assert [name for name, _ in identity.directions] == ["ATL196805110:CHN"]
        assert identity.inputs != other.inputs, "the digest did not follow the sample"
        assert f"inputs             sha256 {identity.inputs} over 1 directions" in self._stamp(module, identity)

    def test_the_same_identifier_carrying_different_values_is_a_different_input(
        self, cubs_at_braves_1968: Direction
    ) -> None:
        """⚠️ **The defect: the digest covered the label, not the board.**

        `game_id:offense_team` is a name. Every batting, footnote and pitching value could change under
        it — a loader repair, a database reload, a corrected roster — and the digest would not move, so
        two runs over different boxscores carried one provenance. This is stated as the case it must
        distinguish: identical identifiers, one changed cell.
        """
        module = _module("measure")
        first, *rest = cubs_at_braves_1968.batting
        altered = replace(cubs_at_braves_1968, batting=(replace(first, hits=first.hits + 1), *rest))

        original = self._identity(module).with_inputs([self._sample(cubs_at_braves_1968)])
        changed = self._identity(module).with_inputs([self._sample(altered)])

        assert [name for name, _ in original.directions] == [name for name, _ in changed.directions]
        assert original.inputs != changed.inputs, "one changed hit did not move the input digest"

    def test_the_lineup_slots_are_part_of_the_input(self, cubs_at_braves_1968: Direction) -> None:
        # The slots are what `groups_in` partitions on, so a board with the same cells and different
        # slots is a different measurement.
        module = _module("measure")
        rows = len(cubs_at_braves_1968.batting)

        original = self._identity(module).with_inputs([self._sample(cubs_at_braves_1968)])
        regrouped = self._identity(module).with_inputs(
            [self._sample(cubs_at_braves_1968, slots=(1,) * 2 + tuple(range(3, rows + 1)))]
        )

        assert original.inputs != regrouped.inputs

    def test_the_artifact_lists_the_boards_its_digest_covers(self, cubs_at_braves_1968: Direction) -> None:
        """⚠️ The stamp said the identifiers sat beside the digest and printed only their count.

        An aggregate says two runs differ; it cannot say *which board* differs, and a digest nobody can
        recompute is a claim rather than evidence.
        """
        module = _module("measure")
        identity = self._identity(module).with_inputs([self._sample(cubs_at_braves_1968)])

        stamp = self._stamp(module, identity)

        name, digest = identity.directions[0]
        assert name in stamp and digest in stamp, "the artifact does not name the board it measured"
        assert stamp.strip().endswith("COMPLETE"), "the listing displaced the completion marker"

    def test_the_digest_does_not_depend_on_the_order_the_loader_returned(self, cubs_at_braves_1968: Direction) -> None:
        # Sorted before hashing, so a reordered sample is recognised as the same inputs rather than
        # reported as different ones.
        module = _module("measure")
        one = self._sample(cubs_at_braves_1968, name="A")
        two = self._sample(cubs_at_braves_1968, name="B")

        first = self._identity(module).with_inputs([one, two])
        reversed_order = self._identity(module).with_inputs([two, one])

        assert first.inputs == reversed_order.inputs

    def test_two_edits_to_one_path_are_two_different_trees(self) -> None:
        """⚠️ `_describe` hashed the porcelain status lines — status codes and paths, not bytes.

        Two different edits to the same file produced the same digest, which is the label-instead-of-
        contents defect again, in the field next to it.
        """
        module = _module("measure")

        one = module._describe(1, b"@@ -1 +1 @@ first edit")
        two = module._describe(1, b"@@ -1 +1 @@ second edit")

        assert one != two, "the tracked digest ignored what actually changed"
        assert module._describe(0, b"") == "clean"

    def test_bytes_with_no_file_count_are_unknown_and_never_clean(self) -> None:
        """⚠️ **`clean` was returned whenever the count was zero, whatever the bytes said.**

        A count and a preimage can disagree, and the stamp then said *clean* over a run that used an
        edited solver — the one outcome this field exists to make impossible.
        """
        module = _module("measure")

        assert module._describe(0, b"@@ -1 +1 @@ an edit the count did not see") == "unknown"
        assert module._describe(0, b"") == "clean", "an actually clean tree must still read clean"

    def test_the_conservative_direction_is_kept_rather_than_refused(self) -> None:
        # A count with no bytes over-reports: a file restored between the two calls. That costs an
        # unnecessary rerun, which is the right way to be wrong, so it stays dirty rather than unknown.
        module = _module("measure")

        assert module._describe(1, b"").startswith("1 files")

    def test_an_unreadable_untracked_file_is_unknown_rather_than_a_marker(self) -> None:
        """⚠️ It became the literal string `<unreadable>` and published anyway, so two different files
        nobody could read were one identity. Same rule as the diff: a failure to read is not a reading.
        """
        module = _module("measure")

        assert module._bytes_of(["no/such/file.py"]) is None
        assert module._describe(1, module._bytes_of(["no/such/file.py"])) == "unknown"

    def test_a_path_needing_quotes_survives_the_porcelain_parse(self) -> None:
        """⚠️ Sliced from the text form, porcelain quotes and escapes any awkward path, so
        `"src/a\tb.py"` arrived with its quotes attached, opened nothing, and became the marker above.
        `-z` is the only form that round-trips a filename.
        """
        module = _module("measure")
        raw = b"?? src/a\tb.py\x00 M forge/src/x.py\x00"

        assert module._porcelain_paths(raw) == ["src/a\tb.py"], "the tab was escaped away"

    def test_a_rename_does_not_desynchronise_the_walk(self) -> None:
        """A rename's source path is its own NUL-terminated record. Nothing needs the tracked paths
        here any more — they come out of the diff — but the extra record still has to be consumed, or
        `old.py` is read as a status line and `?? real-untracked.py` is lost with it."""
        module = _module("measure")
        raw = b"R  new.py\x00?? old.py\x00?? real-untracked.py\x00"

        assert module._porcelain_paths(raw) == ["real-untracked.py"], "a rename source was read as a record"

    def test_the_tracked_paths_come_out_of_the_diff_that_was_digested(self) -> None:
        """⚠️ **The two halves of the tracked digest used to be two commands.**

        v15 refused the one contradiction it could see — no paths with a non-empty diff — and accepted
        every other mixed pair without proving the paths and the bytes described one state. A single
        snapshot cannot contradict itself, so the question stops being detectable and starts being
        impossible.
        """
        module = _module("measure")
        diff = (
            b"diff --git a/forge/src/x.py b/forge/src/x.py\n"
            b"index 000..111 100644\n--- a/forge/src/x.py\n+++ b/forge/src/x.py\n@@ -1 +1 @@\n-a\n+b\n"
            b"diff --git a/discovery/y.py b/discovery/y.py\n@@ -1 +1 @@\n-c\n+d\n"
        )

        assert module._diff_files(diff) == 2
        assert module._diff_files(b"") == 0, "an empty diff names nothing, which is a clean tree"

    def test_a_diff_whose_paths_git_quotes_is_still_counted(self) -> None:
        """⚠️ **The version this replaces re-implemented git's quoting, and refused a valid diff.**

        Git writes `diff --git "a/…"` for a path carrying a tab, a quote, a backslash or — under the
        usual `core.quotePath` — an accented character. The parser matched only the bare
        `diff --git a/` form, so such a diff produced no paths: the count was zero, the bytes were not,
        and `_describe` refused the run. **An accented filename in a Spanish repository is enough**,
        which makes this a false refusal reachable on any afternoon.

        `diff --git ` is the part that does not vary, and a count is all the digest needed — the bytes
        already name the files.
        """
        module = _module("measure")
        quoted = (
            b'diff --git "a/forge/a\tb.py" "b/forge/a\tb.py"\n'
            b"@@ -1 +1 @@\n-a\n+b\n"
            b'diff --git "a/docs/resumen-espa\xc3\xb1ol.md" "b/docs/resumen-espa\xc3\xb1ol.md"\n'
            b"@@ -1 +1 @@\n-c\n+d\n"
        )

        assert module._diff_files(quoted) == 2, "a quoted header was not counted"
        assert module._describe(module._diff_files(quoted), quoted) != "unknown", "a valid diff was refused"

    def test_identify_digests_the_diffs_own_paths_and_not_the_status_listing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The half the test above cannot reach: that `identify` **calls** it.

        ⚠️ A helper that exists and is never called is indistinguishable from one that is broken, and
        testing `_diff_paths` alone would stay green while `identify` went on asking `git status`. So
        the two observations are made to disagree — status names `stale.py`, the diff names `fresh.py`
        — and the tracked digest must be the diff's.
        """
        module = _module("measure")
        diff = b"diff --git a/fresh.py b/fresh.py\n@@ -1 +1 @@\n-a\n+b\n"

        def observe(*arguments: str) -> bytes:
            return b" M stale.py\x00" if arguments[0] == "status" else diff

        monkeypatch.setattr(module, "_git_bytes", observe)
        monkeypatch.setattr(module, "_git", lambda *_: "abc1234")

        assert module.identify().tracked_changes == module._describe(1, diff)
        assert module.identify().tracked_changes != module._describe(2, diff)

    def test_two_different_untracked_trees_cannot_share_an_identity(self) -> None:
        """⚠️ **The encoding was not injective**, and no adversary was required.

        Path bytes and file bytes were concatenated with no lengths and no separators, so
        `{a: b"b", bc: b""}` and `{ab: b"b", c: b""}` produced the same preimage, the same digest and
        the same `2 files` label. Stated as the pair it must now separate.
        """
        module = _module("measure")

        one = module._describe(
            2, module._record(b"a") + module._record(b"b") + module._record(b"bc") + module._record(b"")
        )
        two = module._describe(
            2, module._record(b"ab") + module._record(b"b") + module._record(b"c") + module._record(b"")
        )

        assert one != two, "two different untracked trees still share one identity"

    def test_the_digest_keeps_more_than_thirty_two_bits(self) -> None:
        # Eight hex characters is small enough to search by varying a disposable file until the
        # displayed identity matches an approved one.
        module = _module("measure")

        digest = module._describe(1, b"content").split(", ")[1]

        assert len(digest) == 16

    def test_a_failed_diff_is_not_an_empty_diff(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """⚠️ The near miss worth keeping: `git diff --binary` returns bytes a text pipe cannot decode.

        Asked through the text helper it raised, and one step more gracefully it would have returned an
        empty string — which reads as *nothing changed*, publishing a dirty tree as clean. So the bytes
        helper returns `None` on failure, and `None` is unknown rather than empty.
        """
        module = _module("measure")
        monkeypatch.setattr(module, "_git_bytes", lambda *_: None)
        monkeypatch.setattr(module, "_git", lambda *_: " M forge/src/x.py")

        identity = module.identify()

        assert identity.tracked_changes == "unknown"
        assert identity.publishable is False

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


class TestTheRunRefusesBeforeItSpendsAnything:
    """⚠️ The gate sat after the sample, three seeds of erasure and every solve.

    Nothing after `identify()` can repair an `unknown` repository field, so the refusal was decided
    before the work began and discovered hours later. A guaranteed-discarded run that looks like a
    progressing experiment is worse than an immediate refusal.
    """

    def test_an_unidentified_run_never_reaches_the_loader(self, monkeypatch: pytest.MonkeyPatch) -> None:
        module = _module("measure")
        monkeypatch.setattr(module, "_git", lambda *_: "unknown")
        monkeypatch.setattr(module, "_git_bytes", lambda *_: None)
        monkeypatch.setattr(module, "load", lambda *_, **__: pytest.fail("the loader ran on an unpublishable run"))
        monkeypatch.setattr(sys, "argv", ["measure.py"])

        with pytest.raises(SystemExit, match="provenance is incomplete"):
            module.main()

    def test_a_missing_parent_is_found_before_the_loader(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # The same class as the gate above: knowable now, discovered in five hours otherwise.
        module = _module("measure")
        monkeypatch.setattr(module, "load", lambda *_, **__: pytest.fail("the loader ran for an unwritable output"))
        monkeypatch.setattr(sys, "argv", ["measure.py", "--output", "no/such/place/results.txt"])

        with pytest.raises(SystemExit, match="is not a directory"):
            module.main()

    def test_a_directory_sitting_at_the_output_is_found_before_the_loader(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️ **`out.parent.is_dir()` is not writability.** A directory at `out` passes an existence
        test and fails five hours later inside `publish()` — the operational cost `v14-P2-01` moved the
        provenance gate to avoid, one field over.
        """
        module = _module("measure")
        (tmp_path / "results.txt").mkdir()
        monkeypatch.setattr(module, "load", lambda *_, **__: pytest.fail("the loader ran for an unwritable output"))
        monkeypatch.setattr(sys, "argv", ["measure.py", "--output", str(tmp_path / "results.txt")])

        with pytest.raises(SystemExit, match="is a directory"):
            module.main()

    def test_the_probe_leaves_nothing_behind_when_the_destination_is_fine(self, tmp_path: Path) -> None:
        # The check is the operation itself, so it has to clean up after itself like `publish` does.
        module = _module("measure")

        module._refuse_unwritable(tmp_path / "results.txt")

        assert list(tmp_path.iterdir()) == []

    def test_the_probe_actually_writes_and_the_failure_is_consulted(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️ **Written because the guard above did not guard.** Removing the probe's write entirely
        left every destination test green: they check that a *directory* at `out` is refused, which the
        `is_dir()` branch answers without writing anything. So the claim "writability is proved by
        writing" had no test, which is the shape this project has recorded five times.

        Stated as what it forbids: the write is made to fail, and a refusal must follow. An
        implementation that stops writing never triggers it and fails here.
        """
        module = _module("measure")

        def refuse(*_: object, **__: object) -> None:
            message = "read-only file system"
            raise OSError(message)

        monkeypatch.setattr(Path, "write_bytes", refuse)

        with pytest.raises(SystemExit, match="cannot be written to"):
            module._refuse_unwritable(tmp_path / "results.txt")

    def test_the_probe_stays_in_the_destination_directory(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # `replace` is atomic only within a filesystem, so a probe elsewhere proves the wrong thing.
        module = _module("measure")
        seen: list[Path] = []
        original = Path.write_bytes

        def record(self: Path, data: bytes) -> int:
            seen.append(self)
            return original(self, data)

        monkeypatch.setattr(Path, "write_bytes", record)
        module._refuse_unwritable(tmp_path / "results.txt")

        assert seen and all(path.parent == tmp_path for path in seen)

    def test_the_preflight_never_moves_the_artifact_it_is_checking(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️ **v16 proved the destination by renaming it aside and restoring it in `finally`.**

        That made a read-only check destructive. `finally` does not run after a kill or a power cut, so
        an interruption in the microsecond between the two renames left the canonical artifact gone,
        under a name nobody looks for. **This instrument gets stopped by hand** — three times in one
        afternoon — so the window is not hypothetical.

        Stated as what it forbids: renaming `out` fails the test outright, and the preflight must
        complete anyway.
        """
        module = _module("measure")
        out = tmp_path / "results.txt"
        out.write_text("a previous run", encoding="utf-8")
        original = Path.replace

        def forbid_moving_the_artifact(self: Path, target: object) -> Path:
            if self == out:
                pytest.fail("the preflight moved the canonical artifact")
            return original(self, target)

        monkeypatch.setattr(Path, "replace", forbid_moving_the_artifact)
        module._refuse_unwritable(out)

        assert out.read_text(encoding="utf-8") == "a previous run"
        assert [entry.name for entry in tmp_path.iterdir()] == ["results.txt"], "the probe left debris"

    def _record_replaces(self, monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, Path, bool]]:
        """Every `replace`, with **whether its target existed at the moment of the call**.

        ⚠️ **That last field is the whole point, and the version this replaces did not have it.** It
        asserted `target.exists() is False or target.name != "results.txt"` *after* the preflight had
        already cleaned up in `finally`, so `exists()` was always false and the assertion was always
        true. Deleting the line that creates the target left the suite green — the guard proved a
        `replace` call had happened, not that it had replaced anything. Eighth of its kind here.
        """
        seen: list[tuple[Path, Path, bool]] = []
        original = Path.replace

        def record(self: Path, target: Path) -> Path:
            seen.append((self, Path(target), Path(target).exists()))
            return original(self, target)

        monkeypatch.setattr(Path, "replace", record)
        return seen

    def test_the_probe_replaces_a_file_that_is_actually_there(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # `publish` replaces something already present. A rename onto an absent path is a different
        # operation and answers a different question.
        module = _module("measure")
        replaced = self._record_replaces(monkeypatch)

        module._refuse_unwritable(tmp_path / "results.txt")

        assert replaced, "the probe never exercised a replace"
        source, target, existed = replaced[0]
        assert source.parent == tmp_path and target.parent == tmp_path
        assert existed, "the probe renamed onto an absent path, which proves nothing about replacing"

    def test_the_real_destination_is_the_thing_replaced_when_it_exists(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """⚠️ **A sibling cannot answer for `out`.** Windows lets a handle stay open for read and write
        while denying deletion, so a results file left open in a viewer passes the sibling replace and
        `os.access` alike, and fails hours later at the one operation nobody performed."""
        module = _module("measure")
        out = tmp_path / "results.txt"
        out.write_text("a previous run", encoding="utf-8")
        replaced = self._record_replaces(monkeypatch)

        module._refuse_unwritable(out)

        assert any(target == out and existed for _, target, existed in replaced), "`out` was never replaced"
        assert all(source != out for source, _, _ in replaced), "`out` was moved, which is the v17 defect"
        assert out.read_text(encoding="utf-8") == "a previous run", "the artifact did not survive its own check"

    def test_a_destination_that_refuses_replacement_is_found_before_the_loader(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # Only the real destination refuses, so a guard that merely probed the directory stays green
        # here and this one does not.
        module = _module("measure")
        out = tmp_path / "results.txt"
        out.write_text("a previous run", encoding="utf-8")
        original = Path.replace

        def refuse_only_the_destination(self: Path, target: Path) -> Path:
            if Path(target) == out:
                message = "the file is open in another process"
                raise OSError(message)
            return original(self, target)

        monkeypatch.setattr(Path, "replace", refuse_only_the_destination)
        monkeypatch.setattr(module, "load", lambda *_, **__: pytest.fail("the loader ran for an unpublishable run"))
        monkeypatch.setattr(sys, "argv", ["measure.py", "--output", str(out)])

        with pytest.raises(SystemExit, match="cannot be replaced"):
            module.main()

        assert out.read_text(encoding="utf-8") == "a previous run", "a refused check cost the previous result"
        assert [entry.name for entry in tmp_path.iterdir()] == ["results.txt"], "the copy was left behind"

    def test_output_without_a_path_says_so(self) -> None:
        # Scripts fail with an explanation, not an IndexError three frames down.
        module = _module("measure")

        with pytest.raises(SystemExit, match="--output needs a path"):
            module._destination(["measure.py", "--output"])

        assert module._destination(["measure.py"]).name == "results.txt"

    def test_publication_refuses_an_identity_that_names_no_inputs(self) -> None:
        """The preflight cannot ask this — nothing is loaded yet — but the publication gate must, or a
        stamp reading `inputs not yet loaded` would certify an artifact naming no data at all."""
        module = _module("measure")
        identity = module.RunIdentity(revision="abc", tracked_changes="clean", untracked="clean", instrument="0")

        module._refuse_unless_identified(identity)  # the preflight is satisfied
        with pytest.raises(SystemExit, match="names no inputs"):
            module._refuse_unless_identified(identity, expect_inputs=True)

    def test_an_identified_run_passes_the_gate(self) -> None:
        # A gate that refuses everything would satisfy the test above.
        module = _module("measure")

        module._refuse_unless_identified(
            module.RunIdentity(revision="abc", tracked_changes="clean", untracked="clean", instrument="0")
        )


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
    """⚠️ **The target here fell from 8 stalls to 1, and that is the finding rather than a repair.**

    When zero-valued footnote terms stopped being erasable, this board's stall ceiling collapsed: the
    three seeds now reach 7, 9 and **1**. Before, all three reached 8 comfortably. So most of what this
    board's stall count measured was the solver deducing zeros — values genuinely unknown to it, worth
    nothing to a player.

    The target is 1 because that is what every seed still reaches. Raising it to make the test look
    healthier would be relaxing a rule to reach a number, which §22 forbids for puzzles and which is no
    better here.
    """
    def test_an_erased_board_deduces_something_outside_the_group(self, cubs_at_braves_1968: Direction) -> None:
        # Not a claim that this board blocks — a claim that the comparison is capable of showing it.
        from boxscore_forge.solver import solve  # noqa: PLC0415

        puzzle = erase(cubs_at_braves_1968, target_stalls=1, seed=907)

        assert puzzle is not None
        shape, values = shape_of(cubs_at_braves_1968), cell_values(cubs_at_braves_1968)
        hidden = _hidden()
        treatment = solve(shape, {k: v for k, v in values.items() if k not in (puzzle.erased | hidden)})

        assert [step for step in treatment.deductions if step.cell not in hidden]

    @pytest.mark.parametrize("seed", [907, 908, 909])
    def test_each_seed_is_a_separate_trial(self, seed: int, cubs_at_braves_1968: Direction) -> None:
        # One erasure per board is one sample of the thing blockage measures, not a rate.
        assert erase(cubs_at_braves_1968, target_stalls=1, seed=seed) is not None
