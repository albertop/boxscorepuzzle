"""The puzzle package: the artefact that crosses between the generator and everything else.

⚠️ **This package belongs to neither side.** §22 requires the verifier to share no code with the
generator, so anything they genuinely both need — and a file format is exactly that — lives here
instead of in either of them. Nothing in this module reasons about a puzzle. It reads, writes, and
says what the fields are called. If logic ever appears here, the separation has been quietly undone.

**The board is stored as arrays, not as named cells.** A naming grammar would be a shared vocabulary
that one side invented and the other inherited, and inheriting a mistake is precisely what §22 is
guarding against. Arrays fix the column order and nothing else; each side names cells however it
likes internally.

**Two halves, and only one of them travels.** `puzzle` is what a player receives — erased cells are
null. `source` is the boxscore it was made from, which the forge keeps so that §22's fourth layer can
solve the published half from scratch and compare. **`source` must be stripped before serving**;
`published()` does that and is the only thing that should ever reach the VPS.

Innings pitched are stored as **outs**, not as the `x.y` the board displays. Every value in the
format is an integer, and one of §3's cross-team identities is stated in outs: the outs made by the
offense equal the outs recorded by the opposing pitchers.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Self

SCHEMA_VERSION: Final = 2
"""What this code writes. Version 1 stays readable — see `READABLE`."""

READABLE: Final = (SCHEMA_VERSION,)
"""⚠️ **Version 1 was frozen and this is not an amendment to it.** The contract calls version 1
append-only, and slot references are not an addition: without them a client cannot resolve `SH: 9b` to
a row, so the package means something different rather than something more. That is a new version.

Cutting it now is the point. Nothing is published, `serve` does not exist, and there is nothing to
migrate — **a version scheme first exercised under pressure is one that gets skipped.**

⚠️ **Version 1 was listed here and the promise was false.** A v1 signature is 64 hex of HMAC and this
parser accepts only the 128 of Ed25519, so an authentic v1 file was rejected at the boundary while
three places claimed it would parse — and no test caught it, because the schema tests build objects
and read `as_json()` without going through `from_json`. The fix is to drop the promise rather than
write a legacy verifier nobody will run: **no consumer of version 1 exists**, and keeping it would be a
mechanism preserved past its problem.
"""

BATTING_COLUMNS: Final = ("plate_appearances", "at_bats", "runs", "hits", "walks", "strikeouts")
"""PA, AB, R, H, BB, K — the six the board shows (§6). Order is part of the format."""

FOOTNOTE_COLUMNS: Final = ("hit_by_pitch", "sacrifice_flies", "sacrifice_hits", "catcher_interference")
"""HBP, SF, SH, CI — the footnote line, given complete and never erased (§6)."""

PITCHING_COLUMNS: Final = ("outs", "hits", "runs", "earned_runs", "walks", "strikeouts")
"""IP, H, R, ER, BB, K, with innings held as outs."""

SLOT_REFERENCE = re.compile(r"^[1-9][a-z]?$")
"""`9` where a lineup slot holds one row, `9a`/`9b` where it is shared — the string the board draws and
the footnote line prints, **produced once on the forge and never derived by a client**.

Deriving it there would be a second copy of a baseball rule, and a wrong one attaches a footnote term
to the wrong row: the row identity then fails while every column total still balances.
"""

PUZZLE_ID = re.compile(r"^[0-9a-f]{16}$")
"""Opaque, sixteen hex characters, as the format document states.

Checked because the identifier reaches filenames and will reach URLs. An id that is not what the
contract says is not a smaller problem than a malformed board — it is the same problem somewhere the
board's own validation never looks.
"""

SIGNATURE = re.compile(r"^[0-9a-f]{128}$")
"""Ed25519, hex — 64 bytes, so 128 characters. It was 64 for HMAC-SHA256, and the length changing is
part of why this is schema 2 rather than an amendment to schema 1. A signature of the wrong
*type* used to reach the comparison, which raises
rather than refusing — a malformed file crashing the verifier instead of being rejected by it."""


class PackageError(Exception):
    """The file is not a puzzle package, or is a version this code does not know."""


def _cells(raw: object, width: int, where: str, *, complete: bool = False) -> tuple[int | None, ...]:
    """One row of the grid, checked at the boundary rather than three layers later.

    A package that is valid JSON and malformed as a board must produce a controlled `PackageError`
    here, not a `TypeError` inside the arithmetic. The distinction matters because the second one
    reads as a crash and the first one reads as a rejection.
    """
    if not isinstance(raw, list):
        message = f"{where} is {type(raw).__name__}, expected a list of {width} values"
        raise PackageError(message)
    if len(raw) != width:
        message = f"{where} holds {len(raw)} values, expected {width}"
        raise PackageError(message)
    for index, value in enumerate(raw):
        # bool is an int in Python and never a cell value, so it is excluded explicitly.
        if value is None:
            if complete:
                message = f"{where}[{index}] is empty, and this part of the board is never erased"
                raise PackageError(message)
        elif not isinstance(value, int) or isinstance(value, bool):
            message = f"{where}[{index}] is {value!r}, expected a whole number or null"
            raise PackageError(message)
    return tuple(raw)


def _rows(raw: object, width: int, where: str) -> tuple[tuple[int | None, ...], ...]:
    if not isinstance(raw, list):
        message = f"{where} is {type(raw).__name__}, expected a list of rows"
        raise PackageError(message)
    return tuple(_cells(row, width, f"{where}[{index}]") for index, row in enumerate(raw))


def _whole_number(raw: object, where: str) -> int:
    if not isinstance(raw, int) or isinstance(raw, bool):
        message = f"{where} is {raw!r}, expected a whole number"
        raise PackageError(message)
    return raw


def _innings(raw: object, where: str) -> tuple[int, ...]:
    if not isinstance(raw, list):
        message = f"{where} is {type(raw).__name__}, expected a list of innings"
        raise PackageError(message)
    return tuple(_whole_number(value, f"{where}[{index}]") for index, value in enumerate(raw))


@dataclass(frozen=True, slots=True)
class LineScore:
    """The board's anchor: always shown complete, never erased (§6)."""

    offense_by_inning: tuple[int, ...]
    defense_by_inning: tuple[int, ...]
    offense_runs: int
    offense_hits: int
    offense_errors: int
    defense_runs: int
    defense_hits: int
    defense_errors: int

    def as_json(self) -> dict[str, Any]:
        return {
            "offense_by_inning": list(self.offense_by_inning),
            "defense_by_inning": list(self.defense_by_inning),
            "offense_runs": self.offense_runs,
            "offense_hits": self.offense_hits,
            "offense_errors": self.offense_errors,
            "defense_runs": self.defense_runs,
            "defense_hits": self.defense_hits,
            "defense_errors": self.defense_errors,
        }

    @classmethod
    def from_json(cls, raw: object) -> Self:
        """The line score is the board's anchor and is always complete (§6), so every field is required."""
        if not isinstance(raw, dict):
            message = f"the line score is {type(raw).__name__}, expected an object"
            raise PackageError(message)
        missing = [
            field
            for field in (
                "offense_by_inning",
                "defense_by_inning",
                "offense_runs",
                "offense_hits",
                "offense_errors",
                "defense_runs",
                "defense_hits",
                "defense_errors",
            )
            if field not in raw
        ]
        if missing:
            message = f"the line score is missing {', '.join(missing)}"
            raise PackageError(message)
        return cls(
            offense_by_inning=_innings(raw["offense_by_inning"], "line_score.offense_by_inning"),
            defense_by_inning=_innings(raw["defense_by_inning"], "line_score.defense_by_inning"),
            offense_runs=_whole_number(raw["offense_runs"], "line_score.offense_runs"),
            offense_hits=_whole_number(raw["offense_hits"], "line_score.offense_hits"),
            offense_errors=_whole_number(raw["offense_errors"], "line_score.offense_errors"),
            defense_runs=_whole_number(raw["defense_runs"], "line_score.defense_runs"),
            defense_hits=_whole_number(raw["defense_hits"], "line_score.defense_hits"),
            defense_errors=_whole_number(raw["defense_errors"], "line_score.defense_errors"),
        )


@dataclass(frozen=True, slots=True)
class Board:
    """A board, whole or partly erased.

    `None` in a grid cell means the player has to work it out. The footnote line, the footnote
    totals, the team footnote and the line score are never `None` in a well-formed puzzle — §6 gives
    them complete — but the format does not enforce that, because a verifier that trusts the format
    to reject malformed input is a verifier that checks nothing.
    """

    batting: tuple[tuple[int | None, ...], ...]
    batting_totals: tuple[int | None, ...]
    footnotes: tuple[tuple[int | None, ...], ...]
    footnote_totals: tuple[int | None, ...]
    left_on_base: int | None
    pitching: tuple[tuple[int | None, ...], ...]
    pitching_totals: tuple[int | None, ...]
    line_score: LineScore

    def as_json(self) -> dict[str, Any]:
        return {
            "batting": [list(row) for row in self.batting],
            "batting_totals": list(self.batting_totals),
            "footnotes": [list(row) for row in self.footnotes],
            "footnote_totals": list(self.footnote_totals),
            "left_on_base": self.left_on_base,
            "pitching": [list(row) for row in self.pitching],
            "pitching_totals": list(self.pitching_totals),
            "line_score": self.line_score.as_json(),
        }

    @classmethod
    def from_json(cls, raw: object) -> Self:
        if not isinstance(raw, dict):
            message = f"a board is {type(raw).__name__}, expected an object"
            raise PackageError(message)
        batting = _rows(raw.get("batting"), len(BATTING_COLUMNS), "batting")
        footnotes = _rows(raw.get("footnotes"), len(FOOTNOTE_COLUMNS), "footnotes")
        if len(footnotes) != len(batting):
            message = f"{len(footnotes)} footnote rows against {len(batting)} batting rows"
            raise PackageError(message)
        left_on_base = raw.get("left_on_base")
        return cls(
            batting=batting,
            batting_totals=_cells(raw.get("batting_totals"), len(BATTING_COLUMNS), "batting_totals"),
            footnotes=footnotes,
            # The footnote line is given complete and never erased (§6), so a null in it is
            # malformed rather than difficult.
            footnote_totals=_cells(raw.get("footnote_totals"), len(FOOTNOTE_COLUMNS), "footnote_totals", complete=True),
            left_on_base=None if left_on_base is None else _whole_number(left_on_base, "left_on_base"),
            pitching=_rows(raw.get("pitching"), len(PITCHING_COLUMNS), "pitching"),
            pitching_totals=_cells(raw.get("pitching_totals"), len(PITCHING_COLUMNS), "pitching_totals"),
            line_score=LineScore.from_json(raw.get("line_score", {})),
        )


LEAKING_METADATA: Final = frozenset({"game_id", "retrosheet_id", "season", "date", "teams"})
"""Metadata keys that would hand over the mystery, removed by `published()`.

⚠️ Found while writing the schema down. The opaque puzzle id exists so that nothing in the URL names
the teams or the date (§7), and `metadata` is deliberately loose so seam C3 can carry anything — which
means the loose half is the hole. An id that reveals nothing beside a metadata block holding
`game_id` protects nothing.
"""


@dataclass(frozen=True, slots=True)
class Reveal:
    """What the player earns: the names, the teams, the date, and the card (§7, §29).

    ⚠️ **This is the answer to the mystery and it ships inside the package.** §23 requires the game to
    work with the backend down, so the client cannot fetch the reveal when a row is completed — it has
    to be holding it already. §9 accepts that a determined player can read it in devtools, and that is
    a deliberate trade rather than an oversight: the alternative is a network dependency in the play
    path, which is the one thing §23 forbids.

    Nothing here may reach the board's labels, and nothing here may be encoded in the puzzle id.
    """

    batter_names: tuple[str, ...]
    pitcher_names: tuple[str, ...]
    offense_team: str
    defense_team: str
    played_on: str
    card: str = ""

    def as_json(self) -> dict[str, Any]:
        return {
            "batter_names": list(self.batter_names),
            "pitcher_names": list(self.pitcher_names),
            "offense_team": self.offense_team,
            "defense_team": self.defense_team,
            "played_on": self.played_on,
            "card": self.card,
        }

    @classmethod
    def from_json(cls, raw: object) -> Self:
        if not isinstance(raw, dict):
            message = f"reveal is {type(raw).__name__}, expected an object"
            raise PackageError(message)
        return cls(
            batter_names=tuple(_strings(raw.get("batter_names"), "reveal.batter_names")),
            pitcher_names=tuple(_strings(raw.get("pitcher_names"), "reveal.pitcher_names")),
            offense_team=_text(raw.get("offense_team"), "reveal.offense_team"),
            defense_team=_text(raw.get("defense_team"), "reveal.defense_team"),
            played_on=_text(raw.get("played_on"), "reveal.played_on"),
            card=_text(raw.get("card", ""), "reveal.card"),
        )


def _text(raw: object, where: str) -> str:
    if not isinstance(raw, str):
        message = f"{where} is {type(raw).__name__}, expected a string"
        raise PackageError(message)
    return raw


def _strings(raw: object, where: str) -> list[str]:
    if not isinstance(raw, list):
        message = f"{where} is {type(raw).__name__}, expected a list of strings"
        raise PackageError(message)
    return [_text(value, f"{where}[{index}]") for index, value in enumerate(raw)]


@dataclass(frozen=True, slots=True)
class Package:
    """What the forge produces for one puzzle.

    `metadata` is deliberately loose: seam C3 requires rich metadata on every puzzle even when
    nothing reads it, and a format that had to be revised every time a new field was wanted would
    make that expensive. It is opaque to this module and to the verifier.
    """

    puzzle_id: str
    puzzle: Board
    solution: Board | None = None
    """The completed board. Ships with the puzzle — see `Reveal` for why, and §9 for the trade."""

    labels: tuple[str, ...] = ()
    """One per batting row: the position, suffixed by order of appearance where it repeats (§5, §7)."""

    pitcher_labels: tuple[str, ...] = ()
    """`SP`, then `RP-1` onwards in order of appearance. Never a bare `P` (§5)."""

    reveal: Reveal | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    slot_references: tuple[str, ...] | None = None
    """Required. Typed optional only so the field can carry a default position in the dataclass; a
    package without it raises at construction."""
    """One per batting row, in row order. Required from schema 2; absent in version 1 packages.

    **Pitching rows carry none, deliberately.** Those are the *opposing* team's pitchers and have no
    place in this batting order, so a slot there would name a row that does not exist.
    """

    schema: int | None = None
    """The version this package *is*, checked against the payload rather than trusted.

    ⚠️ **A version is a statement about the payload, not a stamp applied to it.** A package carrying
    slot references is a version 2 package and one without them is a version 1 package, so the two
    cannot disagree: `written_as` derives it. Set it explicitly only to assert what a parsed document
    claimed.
    """

    def __post_init__(self) -> None:
        """⚠️ **This returned early when `schema` was `None`, which is the normal path.**

        So the ordinary constructor produced a package with no references, `written_as` labelled it
        schema 2, `as_json()` omitted the field, and `from_json()` refused the result. The type could
        build a document its own reader rejects — an asymmetric contract every producer would have to
        rediscover.

        Frozen dataclasses need `object.__setattr__` for defaulting; the alternative was a factory
        nobody is obliged to use.
        """
        if self.slot_references is None:
            message = "a package needs one slot reference per batting row; schema 1 is gone"
            raise PackageError(message)
        # The guard refuses anything but a tuple, so there is nothing left to canonicalise here. The
        # version that accepted a list and converted it made the annotation and the constructor
        # disagree; refusing is the shorter way to have one contract, and it keeps a mutable container
        # out of a frozen object whose point is that a signed package cannot change afterwards.
        _check_slot_references(self.slot_references, len(self.puzzle.batting))
        if self.schema is not None:
            _check_schema(self.schema, "a package cannot be schema")

    @property
    def written_as(self) -> int:
        """⚠️ **One version, so nothing derives it any more.**

        This returned 1 for a package without slot references, which was right while both versions
        existed: a version is a statement about the payload. Version 1 is gone — its signatures are
        HMAC and this parser only accepts Ed25519, so the compatibility promise was false and no
        consumer needed it — and with one version left, deriving would only manufacture a document
        this code cannot read back.
        """
        # `is not None`, never truthiness: an empty tuple is a real value and used to read as absent.
        return self.schema if self.schema is not None else SCHEMA_VERSION

    signature: str | None = None

    def published(self) -> Self:
        """The shape that travels.

        ⚠️ **It no longer removes the solution**, and that reversal is worth stating. The earlier
        version stripped it as an answer key, which contradicts §23: with the backend down the client
        cannot fetch a name when a row is completed, so the reveal and the solution have to be in the
        file. What travels instead loses the metadata keys that would give the game away, because a
        deliberately opaque id beside a `game_id` in the metadata protects nothing.
        """
        return type(self)(
            puzzle_id=self.puzzle_id,
            puzzle=self.puzzle,
            solution=self.solution,
            labels=self.labels,
            pitcher_labels=self.pitcher_labels,
            reveal=self.reveal,
            # ⚠️ Carried through. Dropping it here would publish a version 1 package from a version 2
            # one silently — the client would lose the only thing that resolves a footnote, and the
            # version field would follow the payload down without complaining.
            slot_references=self.slot_references,
            metadata={key: value for key, value in self.metadata.items() if key not in LEAKING_METADATA},
            schema=self.schema,
            signature=self.signature,
        )

    def as_json(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema": self.written_as,
            "puzzle_id": self.puzzle_id,
            "puzzle": self.puzzle.as_json(),
            "metadata": self.metadata,
        }
        document["labels"] = list(self.labels)
        document["pitcher_labels"] = list(self.pitcher_labels)
        if self.slot_references is not None:
            document["slot_references"] = list(self.slot_references)
        if self.solution is not None:
            document["solution"] = self.solution.as_json()
        if self.reveal is not None:
            document["reveal"] = self.reveal.as_json()
        if self.signature is not None:
            document["signature"] = self.signature
        return document

    @classmethod
    def from_json(cls, raw: object) -> Self:
        """The envelope, checked here rather than by whoever happens to call this.

        ⚠️ **`read()` guarded the root object and this did not**, so a list or a string reaching this
        method raised `AttributeError` from `raw.get` instead of `PackageError`. A public boundary that
        is only safe when entered through one particular door is not a boundary.

        And `schema` was compared with `!=`, which accepts `true`: Python makes `True == 1`. A JSON
        document declaring `"schema": true` was read as a version 1 package.
        """
        if not isinstance(raw, dict):
            message = f"puzzle package is {type(raw).__name__}, expected an object"
            raise PackageError(message)
        _check_schema(raw.get("schema"), "puzzle package schema")
        try:
            # Hoisted so the slot references can be checked against the board they belong to: one per
            # batting row is the property, and it cannot be stated without the rows.
            puzzle = Board.from_json(raw["puzzle"])
            return cls(
                puzzle_id=_matching(raw.get("puzzle_id"), PUZZLE_ID, "puzzle_id"),
                puzzle=puzzle,
                solution=Board.from_json(raw["solution"]) if raw.get("solution") is not None else None,
                labels=tuple(_strings(raw.get("labels", []), "labels")),
                pitcher_labels=tuple(_strings(raw.get("pitcher_labels", []), "pitcher_labels")),
                reveal=Reveal.from_json(raw["reveal"]) if raw.get("reveal") is not None else None,
                slot_references=_slot_references(raw.get("slot_references"), len(puzzle.batting)),
                metadata=_metadata(raw.get("metadata", {})),
                # Not stored. `written_as` derives the version from the payload, and a document
                # whose declared version disagreed with its content was rejected above — so keeping
                # the parsed number would only let a round trip differ from its original.
                schema=None,
                signature=_matching(raw.get("signature"), SIGNATURE, "signature", optional=True),
            )
        except (KeyError, TypeError) as error:
            message = f"puzzle package is missing or malformed: {error}"
            raise PackageError(message) from error


def _check_schema(value: object, where: str) -> None:
    """The version rule, in one place, used by construction **and** by parsing.

    ⚠️ **They applied different subsets, and the constructor's was the weaker one.** `__post_init__`
    asked only `not in READABLE`, and Python makes `2.0 == 2`, so `schema=2.0` passed, `written_as`
    returned the float, and `as_json()` emitted `"schema": 2.0` — a document `from_json` correctly
    refuses. **The type could once again build output outside the language its own parser accepts**,
    which is the sentence already written above this class about slot references, arriving one field
    over because the rule had two copies instead of one home.

    `bool` is excluded explicitly: `True == 1`, and a JSON document declaring `"schema": true` was once
    read as a version 1 package.
    """
    if not isinstance(value, int) or isinstance(value, bool) or value not in READABLE:
        message = f"{where} {value!r}; this code reads {list(READABLE)}"
        raise PackageError(message)


def _check_slot_references(values: object, rows: int) -> None:
    """The complete rule, in one place, used by construction **and** by parsing.

    ⚠️ **These applied different subsets.** `__post_init__` checked the count and `from_json` checked
    the count, the syntax and the duplicates — so a producer could build a package with a malformed or
    repeated reference, serialise it happily, and hand `serve` a document the shared reader refuses.
    The reference writer's read-back caught that for one caller; the shared type has to be unable to
    produce output outside the language its own parser accepts, or every producer rediscovers the
    guard independently.
    """
    # ⚠️ **The container is checked before its contents.** Widening this to `Sequence[object]` kept
    # the element guard reachable and left the outer shape unchecked — and a `str` **is** a Sequence,
    # so a nine-row package given `"123456789"` passed the length, the per-character grammar and the
    # uniqueness test.
    #
    # ⚠️ **A tuple, and only a tuple.** The first repair accepted a list and canonicalised it, which
    # left the field's annotation saying `tuple[str, ...]` while the constructor took something else:
    # a typed producer could not use the supported path without an error, and a mutable container was
    # admitted into a frozen object whose whole purpose is that a signed package cannot change
    # afterwards. Two contracts for one field is this project's named failure shape, and the cheap way
    # to have one is to refuse — no caller passes a list, and `from_json` converts at the parse
    # boundary, which is where a conversion belongs.
    if not isinstance(values, tuple):
        message = f"slot_references is {type(values).__name__}, expected a tuple of strings"
        raise PackageError(message)
    if len(values) != rows:
        message = f"{len(values)} slot references for {rows} batting rows"
        raise PackageError(message)
    for index, value in enumerate(values):
        # ⚠️ **The parameter is `Sequence[object]` on purpose.** Typing it `tuple[str, ...]` made
        # mypy call this branch unreachable — correct about the annotation and wrong about the world,
        # because `__post_init__` receives whatever a caller passed. An annotation that promises more
        # than the boundary can check turns a real guard into dead code.
        #
        # The type check lived in the parser only, so a direct `Package(...)` carrying `1` or
        # `None` reached the regex and raised a bare `TypeError`: the same malformed field with a
        # different error contract depending on which supported path built it, and neither path is
        # the exception.
        if not isinstance(value, str):
            message = f"slot reference {index} is {value!r}, expected a string"
            raise PackageError(message)
        if not SLOT_REFERENCE.fullmatch(value):
            message = f"slot reference {value!r} is not a slot with an optional letter"
            raise PackageError(message)
    if len(set(values)) != len(values):
        # A duplicate makes a footnote unresolvable, which is the one thing the field exists to do.
        message = f"slot_references repeats a value: {list(values)}"
        raise PackageError(message)


def _slot_references(raw: object, rows: int) -> tuple[str, ...]:
    """One reference per batting row. Required: schema 1 is gone and there is no version without it."""
    if not isinstance(raw, list):
        message = f"slot_references is {raw!r}, expected {rows} strings, one per batting row"
        raise PackageError(message)
    _check_slot_references(tuple(raw), rows)
    return tuple(raw)


def _matching(raw: object, pattern: re.Pattern[str], where: str, *, optional: bool = False) -> Any:  # noqa: ANN401
    """A string of the shape the contract states, or a refusal naming the field.

    `optional` allows absence, never a wrong shape: a package may be unsigned, and a package whose
    signature is a number or an empty string is malformed rather than unsigned.
    """
    if raw is None and optional:
        return None
    if not isinstance(raw, str) or not pattern.fullmatch(raw):
        message = f"{where} is {raw!r}, expected {pattern.pattern}"
        raise PackageError(message)
    return raw


def _metadata(raw: object) -> dict[str, Any]:
    """Loose by design (seam C3), but it has to be an object — a list here breaks every reader."""
    if not isinstance(raw, dict):
        message = f"metadata is {type(raw).__name__}, expected an object"
        raise PackageError(message)
    return raw


def read(path: Path) -> Package:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        message = f"{path} is not valid JSON: {error}"
        raise PackageError(message) from error
    # The root check lives in `from_json` now, where every caller gets it. Kept here only to name
    # the file in the message, which a caller reading a path wants and the method cannot know.
    if not isinstance(raw, dict):
        message = f"{path} does not hold a puzzle package"
        raise PackageError(message)
    return Package.from_json(raw)


def write(path: Path, package: Package) -> None:
    path.write_text(json.dumps(package.as_json(), indent=1, sort_keys=True), encoding="utf-8")
