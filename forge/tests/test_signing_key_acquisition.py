"""Where the publish path gets the signing key, and what it refuses. (v36-P3-29)

⚠️⚠️ **The document recommended persisting this key as a User-scope environment variable**, which hands
it to every process the account runs — every `npm install` postinstall, every pip build hook, every
script from every sibling project on a machine that holds several. **This is the one secret in the
project that cannot be rotated cheaply**: rotating invalidates every signature ever issued, so every
package and every manifest has to be reissued. What the permanent variable bought was avoiding
*"publish failed, you forgot to set it"* — which this script already raises loudly by design.

So the writer reads the key file at the moment of use, and no export is needed. These tests pin the
order and the refusals, because *where a secret comes from* is exactly the kind of thing that gets
loosened by a convenience patch and noticed by nobody.

⚠️ **Every key here is generated in the test.** §33: the real private key never enters a test, a
fixture, or the repository.
"""

import ast
import pathlib
import sys
from collections.abc import Iterator

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "forge" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import write_reference_puzzles as writer  # noqa: E402

# ⚠️⚠️ **Patched where the rule lives, not where it is called from.** These tests set
# `writer.KEY_FILE` and `writer.PINNED_PUBLIC_KEY`; the rule moved to `boxscore_forge.publication_key`
# on 2026-08-22 and patching the writer's names would have patched **nothing that the check reads**.
#
# **They failed loudly only by luck**: ruff removed the now-unused imports from the writer, so the
# attributes disappeared and `monkeypatch.setattr` raised. Had one survived as an unused import, every
# test here would have gone on passing while testing a copy of a path nobody consults. *Patch the module
# that owns the constant.*
from boxscore_forge import publication_key as keys  # noqa: E402


def _material() -> str:
    """64 hex characters of a key that exists for one test and is worth nothing to anybody."""
    return Ed25519PrivateKey.generate().private_bytes_raw().hex()


@pytest.fixture
def elsewhere(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[pathlib.Path]:
    """A key file under `tmp_path`, no inherited variable, and a pin these keys can satisfy.

    ⚠️ `delenv` first and unconditionally: this suite runs on the operator's laptop, where the real
    variable **is** set, and a test that silently read it would be testing the machine rather than
    the code — passing for the wrong reason on the one machine where it matters.

    ⚠️⚠️ **`PINNED_PUBLIC_KEY` is redirected too, and that is a finding rather than a workaround.**
    The first version of this file did not, and every acquisition test failed on *"does not match the
    key serve pins"* — the outage guard doing exactly its job against a key that is not the forge's.
    Redirecting the pin is what lets these tests use a throwaway key at all; the alternative is
    putting the real private key in a test, which §33 forbids and which is the thing this item is
    about. `test_reference_batch.py` is where the *real* pin is asserted.
    """
    monkeypatch.delenv(keys.KEY_VARIABLE, raising=False)
    path = tmp_path / ".boxscorepuzzle-signing-key"
    monkeypatch.setattr(keys, "KEY_FILE", path)
    monkeypatch.setattr(keys, "PINNED_PUBLIC_KEY", tmp_path / "pinned.hex")
    yield path


_ABSENT = object()
"""Sentinel for *the writer holds no key path at all*, which is the fixed shape."""


class _ConsultedError(Exception):
    """Raised by `_ExplodingPath` when the writer touches a key path of its own."""


class _ExplodingPath:
    """A stand-in for `Path` that refuses to be asked anything.

    ⚠️ **It raises rather than returning `False`.** Returning a falsey answer would send the writer
    down the *no key* branch and produce a refusal, which is a plausible outcome the test could mistake
    for correct behaviour. An exception cannot be mistaken for anything.
    """

    def exists(self) -> bool:
        message = "the writer called .exists() on a key path of its own"
        raise _ConsultedError(message)

    def read_text(self, *_args: object, **_kwargs: object) -> str:
        message = "the writer called .read_text() on a key path of its own"
        raise _ConsultedError(message)

    def __str__(self) -> str:
        return "<a path the writer should not have>"


def _pin(material: str) -> str:
    """Write the public half of `material` where the writer looks for the pin, and return it."""
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(material))
    keys.PINNED_PUBLIC_KEY.write_text(key.public_key().public_bytes_raw().hex(), encoding="utf-8")
    return material


class TestWhereTheKeyComesFrom:
    def test_the_file_is_enough_with_no_variable_set(self, elsewhere: pathlib.Path) -> None:
        """The point of the change: a publish needs no export, so the key need not be inherited."""
        wanted = _pin(_material())
        elsewhere.write_text(wanted + "\n", encoding="utf-8")

        key, _ = writer.key_and_destination()

        assert key.private_bytes_raw().hex() == wanted

    def test_a_deliberate_export_wins_over_the_file(
        self, elsewhere: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An export is an instruction; a file in the home directory is only where the key is kept."""
        exported = _pin(_material())
        elsewhere.write_text(_material(), encoding="utf-8")
        monkeypatch.setenv(keys.KEY_VARIABLE, exported)

        key, _ = writer.key_and_destination()

        assert key.private_bytes_raw().hex() == exported

    def test_trailing_whitespace_in_the_file_is_not_a_different_key(self, elsewhere: pathlib.Path) -> None:
        """⚠️ The generator writes with `write_text` and editors add newlines. `from_private_bytes`
        would refuse the untrimmed string with *not hexadecimal*, which names the wrong problem."""
        wanted = _pin(_material())
        elsewhere.write_text(f"  {wanted}  \r\n", encoding="utf-8")

        key, _ = writer.key_and_destination()

        assert key.private_bytes_raw().hex() == wanted


class TestWhatItRefuses:
    def test_neither_source_is_an_error_naming_both(self, elsewhere: pathlib.Path) -> None:
        """⚠️ Fail closed, and say which two places were looked at — a message naming only the
        variable is what teaches the next person to export the secret."""
        with pytest.raises(SystemExit) as refusal:
            writer.key_and_destination()

        assert keys.KEY_VARIABLE in str(refusal.value)
        assert str(elsewhere) in str(refusal.value)

    def test_an_unreadable_key_file_is_an_error_rather_than_a_missing_key(self, elsewhere: pathlib.Path) -> None:
        """⚠️⚠️ The absence of a check must not read as the check passing.

        A directory where the file should be is unreadable as text. Falling through to *no signing
        key* would report the wrong problem and invite an export as the workaround — which is the
        exposure this whole item removes.
        """
        elsewhere.mkdir()

        with pytest.raises(SystemExit) as refusal:
            writer.key_and_destination()

        assert "could not be read" in str(refusal.value)

    # ⚠️ Wanted for its side effects, not its value: the fixture clears the inherited variable and
    # redirects both paths, so this refusal is about the flag rather than about the laptop.
    @pytest.mark.usefixtures("elsewhere")
    def test_ephemeral_still_refuses_to_guess_when_the_variable_is_exported(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv(keys.KEY_VARIABLE, _material())

        with pytest.raises(SystemExit) as refusal:
            monkeypatch.setattr(sys, "argv", ["writer", "--ephemeral"])
            writer.key_and_destination()

        assert "--ephemeral" in str(refusal.value)

    def test_ephemeral_is_not_blocked_by_the_key_file_merely_existing(
        self, elsewhere: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """⚠️ The asymmetry, asserted rather than assumed.

        The key file exists on every machine that has a key, so weighing it the way the variable is
        weighed would make `--ephemeral` impossible exactly where it is used.
        """
        elsewhere.write_text(_material(), encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["writer", "--ephemeral"])

        key, destination = writer.key_and_destination()

        assert key.private_bytes_raw().hex() != elsewhere.read_text(encoding="utf-8").strip()
        assert destination != writer.OUT, "an ephemeral batch must not target the served directory"


class TestTheWriterHoldsNoKeyPathOfItsOwn:
    """⚠️⚠️ The four CI failures of 2026-08-23, made visible on the machine that has the key.

    `main` was red for three consecutive pushes while the hook passed here every time, because
    `key_and_destination()` consulted **its own imported `KEY_FILE`** — a path outside any test's
    control. On this laptop that file exists, so the block read it and stayed quiet; on a runner it does
    not, so the block raised before the code under test was reached and four assertions about the
    temporary path failed.

    **The hook cannot see that class of defect by construction**: it runs on the one machine whose home
    directory makes the bad branch invisible. Leaving the repair to be proved by CI would leave the next
    one waiting for a report nobody reads.

    ⚠️ **Nothing here deletes, moves or renames `~/.boxscorepuzzle-signing-key`.** It is the one secret
    in this project that cannot be regenerated (`docs/signing-keys.md`), and a test strategy that needs
    it absent is one that will eventually be run by somebody who does not put it back.
    """

    def test_the_writer_consults_no_key_path_of_its_own(self, elsewhere: pathlib.Path) -> None:
        """**Absence or non-use — either satisfies this, and that is deliberate.**

        ⚠️⚠️ **It is written to survive the fix that makes it pass**, because a case that can never fail
        again is one the next reader deletes as noise, and its absence then reads as a passing check.
        The property is not *the import is gone*; it is **the writer never decides where the key lives**.
        So:

        - **Before the fix** the name is bound in the writer, this points it at a sentinel, and the dead
          acquisition block calls `.exists()` on it. Red — **on this laptop, with the real key in place.**
        - **After the fix** there is no such name to bind, the writer asks
          `boxscore_forge.publication_key` and nothing else. Green.
        - **If a future `from ... import KEY_FILE` reappears**, the name is bound again, the sentinel is
          installed again, and any use of it is red again. The case has teeth after the repair, which is
          the whole reason it is shaped this way rather than as *assert the import is absent*.

        `test_no_module_outside_publication_key_imports_the_key_path` is the static half and catches the
        import even when nothing reads it. This is the behavioural half: it catches a *use*.
        """
        held = getattr(writer, "KEY_FILE", _ABSENT)
        if held is _ABSENT:
            # The fixed shape: the writer holds no key path, so there is nothing that could be consulted.
            return

        monkeypatch_free_sentinel = _ExplodingPath()
        try:
            writer.KEY_FILE = monkeypatch_free_sentinel  # type: ignore[attr-defined]
            with pytest.raises(SystemExit):
                writer.key_and_destination()
        except _ConsultedError as consulted:
            pytest.fail(
                f"{consulted}. `key_and_destination()` decides where the key lives instead of asking "
                f"boxscore_forge.publication_key, so a machine without "
                f"{elsewhere.name} in its home directory takes a different branch than this one."
            )
        finally:
            writer.KEY_FILE = held  # type: ignore[attr-defined]


def test_no_module_outside_publication_key_imports_the_key_path() -> None:
    """⚠️⚠️ The half that carries this forward. **Broad, not narrow, and that was checked before choosing.**

    The narrow form — *`write_reference_puzzles.py` must not import `KEY_FILE`* — closes the instance
    and leaves the next writer free to reintroduce it. The broad form was available because **there are
    no legitimate importers**: every other consumer reaches the value as a module attribute
    (`keys.KEY_FILE`), which is what makes it patchable, and that is the point.

    ⚠️ **An AST walk, not a text search.** `docs/ci.md` records two failures of this exact guard shape
    here — `"keep" in text` matching `keeps`, and `sign(` matching inside `verify_signature(` — both
    found only by deleting the thing and watching nothing break. A parsed `ImportFrom` cannot match the
    tail of another name, and this one was verified the same way: by reintroducing the import and
    confirming it goes red.

    **What it is really protecting.** A `from ... import KEY_FILE` binds the value into the importer at
    import time, so a test that patches the module patches something the importer never reads — the
    defect is not the copy, it is that the copy is *unpatchable*. `docs/signing-keys.md` makes the file
    the operator's real private key, so the unpatchable copy is one that reads production key material
    on whichever machine happens to have it.
    """
    offenders: dict[str, list[int]] = {}
    for path in sorted((_ROOT / "forge").rglob("*.py")):
        if ".venv" in path.parts or path.name == "publication_key.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        lines = [
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            and (node.module or "").endswith("publication_key")
            and any(alias.name == "KEY_FILE" for alias in node.names)
        ]
        if lines:
            offenders[str(path.relative_to(_ROOT))] = lines

    assert not offenders, (
        f"KEY_FILE is imported by name in {offenders}. Importing it binds the value at import time, so "
        f"patching boxscore_forge.publication_key patches something that module never reads — and the "
        f"unpatched value is the operator's real signing key on any machine that has one. Reach it as "
        f"`publication_key.KEY_FILE`, or call `publication_key()` and let it own the rule."
    )
