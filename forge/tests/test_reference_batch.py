"""Selecting a batch and committing it, which is where a duplicate used to be invisible.

Two defects, one shape: a number that stood in for a fact nobody checked. `written` counted builds
and was read as files, and per-file atomic renames were described as making the batch atomic.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_KEY = Ed25519PrivateKey.generate()
"""The manifest is signed now, so publishing needs a key. Generated per run: a test key in the
repository is a key anybody can sign with."""

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
            writer._publish(staging, 3, _KEY)

        assert not (tmp_path / "manifest.json").exists()

    def test_a_complete_batch_publishes_a_manifest_naming_every_puzzle(self, tmp_path: Path) -> None:
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])

        generation = writer._publish(staging, 2, _KEY)

        manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["generation"] == generation
        assert manifest["puzzles"] == ["aaa", "bbb"]
        assert sorted(path.name for path in (tmp_path / generation).iterdir()) == ["aaa.json", "bbb.json"]

    def test_the_same_contents_resolve_to_the_same_generation(self, tmp_path: Path) -> None:
        # §21: regenerating produces the same thing rather than a new thing. The generation is derived
        # from the contents, so an unchanged batch republishes as a no-op instead of accumulating.
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        first = writer._publish(staging, 2, _KEY)
        _, again = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        writer.OUT = tmp_path

        second = writer._publish(again, 2, _KEY)

        assert first == second
        assert [path.name for path in tmp_path.iterdir() if path.is_dir()] == [first]

    def test_changed_contents_take_a_new_generation(self, tmp_path: Path) -> None:
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        first = writer._publish(staging, 2, _KEY)
        _, changed = self._stage(tmp_path, ["aaa.json", "ccc.json"])
        writer.OUT = tmp_path

        second = writer._publish(changed, 2, _KEY)

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
        first = writer._publish(staging, 2, _KEY)
        # What a reader captured before the next publish.
        held = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
        _, changed = self._stage(tmp_path, ["aaa.json", "ccc.json"])
        writer.OUT = tmp_path

        writer._publish(changed, 2, _KEY)

        assert held["generation"] == first
        for puzzle in held["puzzles"]:
            assert (tmp_path / first / f"{puzzle}.json").exists(), "the reader's generation was deleted under it"

    def test_only_one_generation_back_is_kept(self, tmp_path: Path) -> None:
        # Retention is not accumulation. The commit path collects nothing; the run after next sweeps
        # what no live manifest can name.
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        first = writer._publish(staging, 2, _KEY)
        for names in (["aaa.json", "ccc.json"], ["aaa.json", "ddd.json"]):
            _, more = self._stage(tmp_path, names)
            writer.OUT = tmp_path
            writer._publish(more, 2, _KEY)

        assert not (tmp_path / first).exists()
        assert len([path for path in tmp_path.iterdir() if path.is_dir()]) == 2

    def test_a_concurrent_staging_directory_is_not_swept(self, tmp_path: Path) -> None:
        # The sweep used to delete every directory that was not the new generation, which includes
        # another publisher's staging area mid-run.
        writer, staging = self._stage(tmp_path, ["aaa.json", "bbb.json"])
        other = tmp_path / ".staging-other"
        other.mkdir()
        (other / "work.json").write_text("{}", encoding="utf-8")

        writer._publish(staging, 2, _KEY)

        assert (other / "work.json").exists()

    def test_the_pending_manifest_is_named_per_process(self) -> None:
        # A fixed pending name is a collision point, and nothing makes the single-writer assumption
        # true. Asserted on the source rather than by racing two publishers.
        source = (_SCRIPTS / "write_reference_puzzles.py").read_text(encoding="utf-8")

        assert "getpid()" in source
        assert '{MANIFEST}.pending"' not in source


class TestTheWriterWillNotSignWithAKeyAnybodyHas:
    """⚠️ **The repository key and the fixtures mode are gone, not guarded.**

    Both existed because an HMAC key is symmetric: a convenient one in the tree let the script run, and
    anything it signed was forgeable by whoever held the tree — so the mode had to be made loud instead
    of removed. With a key pair the problem dissolves. A *generated* key signs a throwaway batch
    perfectly well and is worth nothing to an attacker, because the public half that would verify it
    goes nowhere, and `serve` holds a different one and **refuses the batch itself**.

    Removing code beats hardening it, and these assert that the code is gone rather than behaving.
    """

    def _source(self) -> str:
        return (_SCRIPTS / "write_reference_puzzles.py").read_text(encoding="utf-8")

    def test_no_key_material_lives_in_the_script(self) -> None:
        source = self._source()

        assert "FIXTURE_SECRET" not in source
        assert "--fixtures" not in source
        assert "BOXSCORE_SIGNING_SECRET" not in source

    def test_a_missing_key_is_an_error_rather_than_a_quieter_mode(self) -> None:
        source = self._source()

        assert "raise SystemExit(message)" in source
        assert "BOXSCORE_SIGNING_KEY" in source

    def test_the_throwaway_key_is_generated_and_never_stored(self) -> None:
        # The distinction that makes --ephemeral safe: the key exists for one run. A constant here
        # would be the old defect wearing the new name.
        source = self._source()
        generated = source.index("Ed25519PrivateKey.generate()")
        guard = source.index('ephemeral = "--ephemeral" in sys.argv')

        assert guard < generated
        assert "EPHEMERAL KEY" in source

    def test_it_says_serve_will_refuse_the_batch(self) -> None:
        # A mode that announces itself is not the same as one that cannot be mistaken for the real
        # thing. This says which it is.
        assert "refuse" in self._source()


class TestTheManifestIsSigned:
    """⚠️ **`sign_manifest` existed and the writer never called it** — a check that exists and is never
    invoked, one level above the code it protects, and the level where nothing else would notice.

    A signature per puzzle says each puzzle is genuine. Only the manifest signature says the *set* is:
    swapping it for one that points at a retained generation, omits ids, or names a generation that
    does not exist breaks no package signature at all, so every puzzle the client does receive still
    verifies while the release it was given is not the release that was published.
    """

    def _published(self, tmp_path: Path) -> dict:
        writer = _writer()
        writer.OUT = tmp_path
        staging = tmp_path / ".staging"
        staging.mkdir(parents=True)
        for name in ("aaa.json", "bbb.json"):
            (staging / name).write_text('{"puzzle_id": "x"}', encoding="utf-8")
        writer._publish(staging, 2, _KEY)
        return json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))

    def test_it_carries_a_signature(self, tmp_path: Path) -> None:
        from boxscore_package.signing import verify_manifest  # noqa: PLC0415

        manifest = self._published(tmp_path)

        assert "signature" in manifest
        verify_manifest(manifest, _KEY.public_key())

    def test_altering_the_generation_is_refused(self, tmp_path: Path) -> None:
        from boxscore_package.signing import SignatureError, verify_manifest  # noqa: PLC0415

        manifest = self._published(tmp_path)
        manifest["generation"] = "0000deadbeef"

        with pytest.raises(SignatureError):
            verify_manifest(manifest, _KEY.public_key())

    def test_omitting_a_puzzle_is_refused(self, tmp_path: Path) -> None:
        # The attack the packages cannot see: every id left in the list still has a valid signature.
        from boxscore_package.signing import SignatureError, verify_manifest  # noqa: PLC0415

        manifest = self._published(tmp_path)
        manifest["puzzles"] = manifest["puzzles"][:1]

        with pytest.raises(SignatureError):
            verify_manifest(manifest, _KEY.public_key())


class TestTheTwoKeyModesAreExclusive:
    def test_ephemeral_with_a_configured_key_is_refused(self) -> None:
        # ⚠️ The environment key used to win whenever it was set, so --ephemeral on a machine with the
        # production key configured asked for a throwaway trust domain and got the real one.
        source = (_SCRIPTS / "write_reference_puzzles.py").read_text(encoding="utf-8")

        assert "if ephemeral and material:" in source
        assert "Refusing to guess which trust" in source
