"""The Python reader, against the conformance vectors the browser reader also runs.

⚠️ **They exist because the two readers enforced different contracts while both claiming to read v3.**
Python defaulted labels it never counted; the client accepted a null footnote total it then rendered
nowhere, and slot references whose grammar and uniqueness it never checked. A package could be built,
signed and certified on the forge and refused by the browser — and a document the browser accepted could
produce a board that cannot be finished.

**Shared data, not shared code.** `forge/` and `serve/` still import nothing from each other, which §33
requires. Each side applies the same mutations to the same real package with its own reader, which is
what makes two implementations answerable to one contract without becoming one implementation.

⚠️ A vector both sides accept, or both reject, proves nothing by itself. **What the file forbids is the
two disagreeing** — so the same JSON is run here and in `serve/tests/engine.test.js`, and a change to
one reader that is not made to the other turns one of them red.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from boxscore_package.format import PackageError, read

_ROOT = Path(__file__).resolve().parents[3]
VECTORS = json.loads((_ROOT / "serve" / "tests" / "package-vectors.json").read_text(encoding="utf-8"))


def _reference() -> dict[str, Any]:
    public = _ROOT / "serve" / "data" / "puzzles"
    manifest = json.loads((public / "manifest.json").read_text(encoding="utf-8"))
    # ⚠️ Whatever is published, not a named id: the id is derived from the game and regeneration renames
    # it, which broke every vector on a missing file rather than on anything about the contract.
    #
    # ⚠⚠ **Flat since E1**, and the manifest no longer carries a generation. The public path holds
    # `<id>.json`; `<generation>/<id>.json` is the *private* inventory's shape and never travels
    # (`docs/calendar.md`). This was reading the private shape out of a directory that is now the
    # served one -- which is the whole reason the served one had six packages in it.
    return json.loads((public / f"{manifest['puzzles'][0]}.json").read_text(encoding="utf-8"))


def _apply(document: dict[str, Any], path: str, value: object) -> None:
    """Set `path` — `a.b[0][1]` — to `value`, or delete the key when `value` is None at the top level.

    ⚠️ `None` means *absent*, not *null*: every vector that wants a null says so through a value the
    schema forbids in that position. Absence and an explicit null are different documents and the
    readers must answer both.
    """
    parts: list[str | int] = []
    for chunk in path.split("."):
        name, _, rest = chunk.partition("[")
        parts.append(name)
        parts.extend(int(index) for index in rest.rstrip("]").split("][") if index)

    target: Any = document
    for part in parts[:-1]:
        target = target[part]
    last = parts[-1]
    if value is None and isinstance(last, str):
        target.pop(last, None)
    else:
        target[last] = value


@pytest.mark.parametrize("vector", VECTORS["vectors"], ids=lambda v: v["name"])
def test_the_python_reader_agrees_with_the_shared_contract(vector: dict[str, Any], tmp_path: Path) -> None:
    document = _reference()
    for path, value in vector["mutate"]:
        _apply(document, path, value)
    file = tmp_path / "package.json"
    file.write_text(json.dumps(document), encoding="utf-8")

    if vector["expect"] == "accept":
        read(file)  # a raise here is the failure
        return
    with pytest.raises(PackageError):
        read(file)


def test_the_vectors_exercise_both_answers() -> None:
    """A file of nothing but rejections would pass a reader that refuses everything."""
    expectations = {vector["expect"] for vector in VECTORS["vectors"]}

    assert expectations == {"accept", "reject"}, f"the vectors only ever expect {expectations}"


def test_every_vector_says_why() -> None:
    # A vector without a reason is a rule nobody can evaluate when it starts failing.
    for vector in VECTORS["vectors"]:
        assert vector.get("because"), f"{vector['name']} carries no reason"


def test_the_shared_caps_still_equal_the_constants_module() -> None:
    """⚠️ The other half of "one predicate, one place": share the definition, or assert they agree.

    The client cannot import `boxscore_domain` — §33 ships `serve/` alone and forbids the cross-import —
    so the caps reach it as data. That makes two places holding one rule, which is the shape every
    serious defect in this project has had. The pairing is not left to habit: raising a cap in the
    module and not in the JSON turns this red.
    """
    from boxscore_domain import BATTER_CAP, PITCHER_CAP  # noqa: PLC0415

    assert VECTORS["caps"] == {"batters": BATTER_CAP, "pitchers": PITCHER_CAP}
