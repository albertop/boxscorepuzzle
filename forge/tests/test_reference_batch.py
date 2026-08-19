"""Selecting a batch and committing it, which is where a duplicate used to be invisible.

Two defects, one shape: a number that stood in for a fact nobody checked. `written` counted builds
and was read as files, and per-file atomic renames were described as making the batch atomic.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _writer() -> object:
    """Import the script without running it. It is a script, not a package, so it is loaded by path."""
    sys.path.insert(0, str(_SCRIPTS))
    spec = importlib.util.spec_from_file_location("write_reference_puzzles", _SCRIPTS / "write_reference_puzzles.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Direction:
    def __init__(self, game_id: str) -> None:
        self.game_id = game_id


class TestClaimingAGame:
    def test_a_game_is_taken_once(self) -> None:
        writer = _writer()
        wanted: list[object] = []
        seen: set[str] = set()

        assert writer.claim(wanted, seen, _Direction("SLN19680808"))
        assert len(wanted) == 1

    def test_the_same_game_is_refused_the_second_time(self) -> None:
        # ⚠️ The defect. A direction can carry a substitution and a live footnote, and both required
        # traits were appended before the deduplication set existed. Both derive the same identifier,
        # so the second overwrote the first and the counter still said six.
        writer = _writer()
        wanted: list[object] = []
        seen: set[str] = set()
        writer.claim(wanted, seen, _Direction("SLN19680808"))

        assert not writer.claim(wanted, seen, _Direction("SLN19680808"))
        assert len(wanted) == 1

    def test_a_different_game_is_taken(self) -> None:
        # The other half. A guard that refuses everything would pass the test above on its own.
        writer = _writer()
        wanted: list[object] = []
        seen: set[str] = set()
        writer.claim(wanted, seen, _Direction("SLN19680808"))

        assert writer.claim(wanted, seen, _Direction("BOS19680808"))
        assert len(wanted) == 2


class TestCommittingTheBatch:
    """The manifest is the commit. Everything before it can fail without changing what is published."""

    def _stage(self, tmp_path: Path, names: list[str]) -> tuple[object, Path]:
        writer = _writer()
        writer.OUT = tmp_path
        staging = tmp_path / ".staging"
        staging.mkdir(parents=True)
        for name in names:
            (staging / name).write_text(f'{{"puzzle_id": "{Path(name).stem}"}}', encoding="utf-8")
        return writer, staging

    def test_a_short_batch_is_refused_and_nothing_is_published(self, tmp_path: Path) -> None:
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])

        with pytest.raises(SystemExit, match="staged files, wanted 3"):
            writer._publish(staging, 3)

        assert not (tmp_path / "manifest.json").exists()

    def test_a_complete_batch_publishes_a_manifest_naming_every_puzzle(self, tmp_path: Path) -> None:
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])

        generation = writer._publish(staging, 2)

        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["generation"] == generation
        assert manifest["puzzles"] == ["aaa", "bbb"]
        assert sorted(path.name for path in (tmp_path / generation).iterdir()) == ["aaa.json", "bbb.json"]

    def test_the_same_contents_resolve_to_the_same_generation(self, tmp_path: Path) -> None:
        # §21: regenerating produces the same thing rather than a new thing. The generation is derived
        # from the contents, so an unchanged batch republishes as a no-op instead of accumulating.
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        first = writer._publish(staging, 2)
        _, again = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        writer.OUT = tmp_path

        second = writer._publish(again, 2)

        assert first == second
        assert [path.name for path in tmp_path.iterdir() if path.is_dir()] == [first]

    def test_changed_contents_take_a_new_generation(self, tmp_path: Path) -> None:
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        first = writer._publish(staging, 2)
        _, changed = self._stage(tmp_path, ["aaa.json", "ccc.json"])
        writer.OUT = tmp_path

        second = writer._publish(changed, 2)

        assert second != first
        assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))["generation"] == second

    def test_a_reader_holding_the_previous_manifest_can_still_read_all_of_it(self, tmp_path: Path) -> None:
        """⚠️ **The test this replaces asserted the opposite**, and so encoded the defect as the
        contract: it required the previous directory to be gone the moment `_publish` returned.

        An atomic rename stops a reader seeing a torn manifest. It does not make *fetch the manifest*
        and *fetch a puzzle* one transaction, and a cached manifest stretches the gap between them far
        past the rename. Deleting the superseded generation at commit turns an ordinary release into a
        404 for everyone holding the old pointer.
        """
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        first = writer._publish(staging, 2)
        # What a reader captured before the next publish.
        held = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        _, changed = self._stage(tmp_path, ["aaa.json", "ccc.json"])
        writer.OUT = tmp_path

        writer._publish(changed, 2)

        assert held["generation"] == first
        for puzzle in held["puzzles"]:
            assert (tmp_path / first / f"{puzzle}.json").exists(), "the reader's generation was deleted under it"

    def test_only_one_generation_back_is_kept(self, tmp_path: Path) -> None:
        # Retention is not accumulation. The commit path collects nothing; the run after next sweeps
        # what no live manifest can name.
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        first = writer._publish(staging, 2)
        for names in (["aaa.json", "ccc.json"], ["aaa.json", "ddd.json"]):
            _, more = self._stage(tmp_path, names)
            writer.OUT = tmp_path
            writer._publish(more, 2)

        assert not (tmp_path / first).exists()
        assert len([path for path in tmp_path.iterdir() if path.is_dir()]) == 2

    def test_a_concurrent_staging_directory_is_not_swept(self, tmp_path: Path) -> None:
        # The sweep used to delete every directory that was not the new generation, which includes
        # another publisher's staging area mid-run.
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        other = tmp_path / ".staging-other"
        other.mkdir()
        (other / "work.json").write_text("{}", encoding="utf-8")

        writer._publish(staging, 2)

        assert (other / "work.json").exists()

    def test_the_pending_manifest_is_named_per_process(self) -> None:
        # A fixed pending name is a collision point, and nothing makes the single-writer assumption
        # true. Asserted on the source rather than by racing two publishers.
        source = (_SCRIPTS / "write_reference_puzzles.py").read_text(encoding="utf-8")

        assert "getpid()" in source
        assert '{MANIFEST}.pending"' not in source
