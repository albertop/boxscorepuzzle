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
    def from_json(cls, raw: dict[str, Any]) -> Self:
        return cls(
            offense_by_inning=tuple(raw["offense_by_inning"]),
            defense_by_inning=tuple(raw["defense_by_inning"]),
            offense_runs=raw["offense_runs"],
            offense_hits=raw["offense_hits"],
            offense_errors=raw["offense_errors"],
            defense_runs=raw["defense_runs"],
            defense_hits=raw["defense_hits"],
            defense_errors=raw["defense_errors"],
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
    def from_json(cls, raw: dict[str, Any]) -> Self:
        return cls(
            batting=tuple(tuple(row) for row in raw["batting"]),
            batting_totals=tuple(raw["batting_totals"]),
            footnotes=tuple(tuple(row) for row in raw["footnotes"]),
            footnote_totals=tuple(raw["footnote_totals"]),
            left_on_base=raw["left_on_base"],
            pitching=tuple(tuple(row) for row in raw["pitching"]),
            pitching_totals=tuple(raw["pitching_totals"]),
            line_score=LineScore.from_json(raw["line_score"]),
        )


@dataclass(frozen=True, slots=True)
class Package:
    """What the forge produces for one puzzle.

    `metadata` is deliberately loose: seam C3 requires rich metadata on every puzzle even when
    nothing reads it, and a format that had to be revised every time a new field was wanted would
    make that expensive. It is opaque to this module and to the verifier.
    """

    puzzle_id: str
    puzzle: Board
    source: Board | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    schema: int = SCHEMA_VERSION
    signature: str | None = None

    def published(self) -> Self:
        """The half that travels: no source boxscore, because it is the answer key."""
        return type(self)(
            puzzle_id=self.puzzle_id,
            puzzle=self.puzzle,
            source=None,
            metadata=self.metadata,
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
        if self.source is not None:
            document["source"] = self.source.as_json()
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
                source=Board.from_json(raw["source"]) if raw.get("source") is not None else None,
                metadata=raw.get("metadata", {}),
                schema=schema,
                signature=raw.get("signature"),
            )
        except (KeyError, TypeError) as error:
            message = f"puzzle package is missing or malformed: {error}"
            raise PackageError(message) from error


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
