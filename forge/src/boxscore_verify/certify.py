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

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from boxscore_package.format import BATTING_COLUMNS, Package
from boxscore_verify.expected_id import expected_puzzle_id
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

    ⚠️ **Evidence used to name no game.** It carried a source type, a deduced flag and two offensive
    totals, so evidence from a *different* game with the same runs and hits satisfied the gate. The
    package deliberately carries no game id (§7), and the identifier is the only thing that ties it to
    one — so the game and the batting team are here, and the gate recomputes the identifier from them.

    **Not every field it carries is independent, and saying which is the point.** The line score's
    R/H/E come from the same query that fills the line score, so comparing them catches corruption
    between loading and packaging and cannot catch a board that never happened. `official_at_bats` and
    `official_left_on_base` come from `retroGameLogs`, a table the board is not built from, and those
    two are the only correspondence in the strict sense.
    """

    game_id: str
    offense_team: str
    source_type: str
    is_deduced: bool
    official_hits: int
    official_runs: int
    official_errors: int
    official_defense_runs: int
    official_defense_hits: int
    official_defense_errors: int
    official_at_bats: int | None
    official_left_on_base: int | None


@dataclass(frozen=True, slots=True)
class Certification:
    puzzle_id: str
    refusals: tuple[str, ...]

    @property
    def publishable(self) -> bool:
        return not self.refusals


def check_mathematics(
    package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned
) -> list[str]:
    """§22's four layers plus the signature. Necessary, and on its own not sufficient."""
    del evidence
    verdict: Verdict = verify(package, secret=secret)
    if verdict.rejection is None:
        return []
    return [f"{verdict.rejection.layer}: {verdict.rejection.detail}"]


def check_board_is_possible(
    package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned
) -> list[str]:
    """Could this have been a baseball game — the class of check `verify()` cannot make."""
    del evidence, secret
    board = package.solution or package.puzzle
    return [f"implausible board: {fault.what}" for fault in faults(board)]


def check_reveal_is_complete(
    package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned
) -> list[str]:
    """The payoff screen, which no layer of §22 looks at and which named the wrong club four times."""
    del evidence, secret
    return [f"broken reveal: {fault.what}" for fault in reveal_faults(package)]


def check_evidence_is_about_this_package(
    package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned
) -> list[str]:
    """Does the evidence describe *this* puzzle, or merely some puzzle?

    Recomputed rather than compared to a value the producer supplies: an expected id handed over by
    the same code that set the package's id would agree with itself by construction.
    """
    del secret
    if not evidence.game_id or not evidence.offense_team:
        return ["the evidence names no game, so nothing binds it to this package"]
    expected = expected_puzzle_id(evidence.game_id, evidence.offense_team)
    if expected != package.puzzle_id:
        return [f"the evidence describes puzzle {expected}, this package is {package.puzzle_id}"]
    return []


def check_provenance(
    package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned
) -> list[str]:
    """An accepted source, named rather than merely not excluded."""
    del package, secret
    refusals: list[str] = []
    if evidence.is_deduced:
        refusals.append("the game comes from a deduced event file (§32)")
    if evidence.source_type not in ACCEPTED_SOURCES:
        refusals.append(f"source {evidence.source_type!r} is not one of {list(ACCEPTED_SOURCES)}")
    return refusals


def check_independent_correspondence(
    package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned
) -> list[str]:
    """The board against sources that did not come from its own rows.

    Two kinds of comparison, and conflating them is how this check was weaker than it looked.

    The **complete line score** is compared because it is signed and player-visible: a defensive run
    total or an error column altered in transport is a false historical claim even though no identity
    on the board would notice. But those values are loaded from the same query that fills the line
    score, so this catches corruption between loading and packaging and *cannot* catch fabrication.

    **At-bats and runners left on base come from the game log**, a table the board is not built from.
    They are the only strict correspondence here, and their absence is a refusal rather than a pass:
    1.5% of games have no game-log row, and a game that cannot be corroborated is discarded (§22),
    never published on the strength of the checks that did run.
    """
    del secret
    board = package.solution or package.puzzle
    score = board.line_score
    refusals: list[str] = []
    for what, on_the_board, official in (
        ("hits", score.offense_hits, evidence.official_hits),
        ("runs", score.offense_runs, evidence.official_runs),
        ("errors", score.offense_errors, evidence.official_errors),
        ("defensive runs", score.defense_runs, evidence.official_defense_runs),
        ("defensive hits", score.defense_hits, evidence.official_defense_hits),
        ("defensive errors", score.defense_errors, evidence.official_defense_errors),
    ):
        if on_the_board != official:
            refusals.append(f"{what} disagree with the official total: {on_the_board} against {official}")

    if evidence.official_at_bats is None or evidence.official_left_on_base is None:
        refusals.append("the game log has no row for this game, so nothing independent corroborates the board")
        return refusals
    # Named rather than indexed. The column order is part of the format and stated in one place;
    # a literal 1 here would be a second copy of it that nothing checks.
    at_bats = board.batting_totals[BATTING_COLUMNS.index("at_bats")]
    if at_bats is not None and at_bats != evidence.official_at_bats:
        refusals.append(f"at-bats disagree with the game log: {at_bats} against {evidence.official_at_bats}")
    if board.left_on_base is not None and board.left_on_base != evidence.official_left_on_base:
        refusals.append(
            f"runners left on base disagree with the game log: "
            f"{board.left_on_base} against {evidence.official_left_on_base}"
        )
    return refusals


CERTIFICATIONS: Final[dict[str, Callable[[Package, Evidence, Ed25519PublicKey | Unsigned], list[str]]]] = {
    "evidence_is_about_this_package": check_evidence_is_about_this_package,
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
    secret: Ed25519PublicKey | Unsigned,
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
