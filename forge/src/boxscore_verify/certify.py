"""The single gate a puzzle passes before it may be published.

⚠️ **`verify()` is not that gate and never was.** It answers a mathematical question — does the board
balance, is the completion unique, is it reachable without guessing, does the published half match the
source. Every one of those can be true of a board that could not have happened: this package's own
test suite contains a board with a row of noughts that passes all four layers and is not a baseball
game. The checks for that exist; nothing called them on the publication path.

So this composes them, and it **fails closed**: a check that cannot run is a rejection, never a pass.
That is the shape of half the defects this project has found — the absence of a check reading as the
presence of a passing one.

**Two of the checks need evidence the package cannot carry.** Provenance and correspondence to an
independent source are facts about where a game came from, and the verifier has no database and must
not grow one (§22, §33). The producer supplies them as `Evidence`; **omitting it is a rejection**, so
a writer cannot obtain publication by simply not knowing.

`CERTIFICATIONS` is a registry rather than a sequence of calls, because a boundary that lists its
checks by hand is the same defect one level up — `tests/test_certification.py` discovers the checks
that exist and asserts each is wired in, so adding one without registering it fails.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from boxscore_package.format import Package
from boxscore_verify.plausibility import faults, reveal_faults
from boxscore_verify.verify import UNSIGNED, Unsigned, Verdict, verify

ACCEPTED_SOURCES: Final = ("EVA", "EVN", "EVF")
"""Stated here as well as in the loader, and the duplication is deliberate.

§22 forbids the verifier importing from the generator, so the gate cannot read the loader's list. Two
copies of a rule drift — this project has watched it happen — so `tests/test_certification.py`
asserts the two agree rather than trusting that they do.
"""


@dataclass(frozen=True, slots=True)
class Evidence:
    """What the producer knows and the package cannot say for itself.

    Every field is required. A default would let a writer publish by omission, which is exactly the
    failure this boundary exists to prevent.
    """

    source_type: str
    is_deduced: bool
    official_hits: int
    official_runs: int


@dataclass(frozen=True, slots=True)
class Certification:
    puzzle_id: str
    refusals: tuple[str, ...]

    @property
    def publishable(self) -> bool:
        return not self.refusals


def check_mathematics(package: Package, evidence: Evidence, secret: bytes | Unsigned) -> list[str]:
    """§22's four layers plus the signature. Necessary, and on its own not sufficient."""
    del evidence
    verdict: Verdict = verify(package, secret=secret)
    if verdict.rejection is None:
        return []
    return [f"{verdict.rejection.layer}: {verdict.rejection.detail}"]


def check_board_is_possible(package: Package, evidence: Evidence, secret: bytes | Unsigned) -> list[str]:
    """Could this have been a baseball game — the class of check `verify()` cannot make."""
    del evidence, secret
    board = package.solution or package.puzzle
    return [f"implausible board: {fault.what}" for fault in faults(board)]


def check_reveal_is_complete(package: Package, evidence: Evidence, secret: bytes | Unsigned) -> list[str]:
    """The payoff screen, which no layer of §22 looks at and which named the wrong club four times."""
    del evidence, secret
    return [f"broken reveal: {fault.what}" for fault in reveal_faults(package)]


def check_provenance(package: Package, evidence: Evidence, secret: bytes | Unsigned) -> list[str]:
    """An accepted source, named rather than merely not excluded."""
    del package, secret
    refusals: list[str] = []
    if evidence.is_deduced:
        refusals.append("the game comes from a deduced event file (§32)")
    if evidence.source_type not in ACCEPTED_SOURCES:
        refusals.append(f"source {evidence.source_type!r} is not one of {list(ACCEPTED_SOURCES)}")
    return refusals


def check_independent_correspondence(package: Package, evidence: Evidence, secret: bytes | Unsigned) -> list[str]:
    """The board against a source that did not come from its own rows.

    Both totals used to be computed from the rows they were meant to anchor, so the identity checking
    them could not fail. These come from the game tables.
    """
    del secret
    board = package.solution or package.puzzle
    refusals: list[str] = []
    if board.line_score.offense_hits != evidence.official_hits:
        refusals.append(
            f"hits disagree with the official total: {board.line_score.offense_hits} against {evidence.official_hits}"
        )
    if board.line_score.offense_runs != evidence.official_runs:
        refusals.append(
            f"runs disagree with the official total: {board.line_score.offense_runs} against {evidence.official_runs}"
        )
    return refusals


CERTIFICATIONS: Final[dict[str, Callable[[Package, Evidence, bytes | Unsigned], list[str]]]] = {
    "mathematics": check_mathematics,
    "board_is_possible": check_board_is_possible,
    "reveal_is_complete": check_reveal_is_complete,
    "provenance": check_provenance,
    "independent_correspondence": check_independent_correspondence,
}


def certify_for_publication(
    package: Package,
    *,
    evidence: Evidence | None,
    secret: bytes | Unsigned,
) -> Certification:
    """Every check, all of them, or the puzzle is not published.

    Unlike `verify`, this does not stop at the first refusal: a writer discarding a candidate wants to
    know everything wrong with it, and a partial answer invites fixing one thing and re-running.
    """
    if evidence is None:
        # Fail closed. A producer that cannot say where the game came from has not shown it may
        # publish; it has only failed to look.
        return Certification(package.puzzle_id, ("no evidence supplied: provenance and correspondence unknown",))
    refusals: list[str] = []
    for name, check in CERTIFICATIONS.items():
        for refusal in check(package, evidence, secret):
            refusals.append(f"{name}: {refusal}")
    return Certification(package.puzzle_id, tuple(refusals))


__all__ = [
    "ACCEPTED_SOURCES",
    "CERTIFICATIONS",
    "UNSIGNED",
    "Certification",
    "Evidence",
    "certify_for_publication",
]
