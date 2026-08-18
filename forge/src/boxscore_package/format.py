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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, Self

SCHEMA_VERSION: Final = 1

BATTING_COLUMNS: Final = ("plate_appearances", "at_bats", "runs", "hits", "walks", "strikeouts")
"""PA, AB, R, H, BB, K — the six the board shows (§6). Order is part of the format."""

FOOTNOTE_COLUMNS: Final = ("hit_by_pitch", "sacrifice_flies", "sacrifice_hits", "catcher_interference")
"""HBP, SF, SH, CI — the footnote line, given complete and never erased (§6)."""

PITCHING_COLUMNS: Final = ("outs", "hits", "runs", "earned_runs", "walks", "strikeouts")
"""IP, H, R, ER, BB, K, with innings held as outs."""


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
    schema: int = SCHEMA_VERSION
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
            metadata={key: value for key, value in self.metadata.items() if key not in LEAKING_METADATA},
            schema=self.schema,
            signature=self.signature,
        )

    def as_json(self) -> dict[str, Any]:
        document: dict[str, Any] = {
            "schema": self.schema,
            "puzzle_id": self.puzzle_id,
            "puzzle": self.puzzle.as_json(),
            "metadata": self.metadata,
        }
        document["labels"] = list(self.labels)
        document["pitcher_labels"] = list(self.pitcher_labels)
        if self.solution is not None:
            document["solution"] = self.solution.as_json()
        if self.reveal is not None:
            document["reveal"] = self.reveal.as_json()
        if self.signature is not None:
            document["signature"] = self.signature
        return document

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> Self:
        schema = raw.get("schema")
        if schema != SCHEMA_VERSION:
            message = f"puzzle package schema {schema!r}, this code reads {SCHEMA_VERSION}"
            raise PackageError(message)
        try:
            return cls(
                puzzle_id=raw["puzzle_id"],
                puzzle=Board.from_json(raw["puzzle"]),
                solution=Board.from_json(raw["solution"]) if raw.get("solution") is not None else None,
                labels=tuple(_strings(raw.get("labels", []), "labels")),
                pitcher_labels=tuple(_strings(raw.get("pitcher_labels", []), "pitcher_labels")),
                reveal=Reveal.from_json(raw["reveal"]) if raw.get("reveal") is not None else None,
                metadata=_metadata(raw.get("metadata", {})),
                schema=schema,
                signature=raw.get("signature"),
            )
        except (KeyError, TypeError) as error:
            message = f"puzzle package is missing or malformed: {error}"
            raise PackageError(message) from error


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
    if not isinstance(raw, dict):
        message = f"{path} does not hold a puzzle package"
        raise PackageError(message)
    return Package.from_json(raw)


def write(path: Path, package: Package) -> None:
    path.write_text(json.dumps(package.as_json(), indent=1, sort_keys=True), encoding="utf-8")
