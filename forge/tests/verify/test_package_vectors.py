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
    manifest = json.loads((_ROOT / "serve" / "data" / "puzzles" / "manifest.json").read_text(encoding="utf-8"))
    path = _ROOT / "serve" / "data" / "puzzles" / manifest["generation"] / f"{VECTORS['package']}.json"
    return json.loads(path.read_text(encoding="utf-8"))


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
