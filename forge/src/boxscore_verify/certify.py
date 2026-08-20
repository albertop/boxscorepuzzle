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


def check_mathematics(package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned) -> list[str]:
    """§22's four layers plus the signature. Necessary, and on its own not sufficient."""
    del evidence
    verdict: Verdict = verify(package, secret=secret)
    if verdict.rejection is None:
        return []
    return [f"{verdict.rejection.layer}: {verdict.rejection.detail}"]


def check_board_is_possible(package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned) -> list[str]:
    """Could this have been a baseball game — the class of check `verify()` cannot make."""
    del evidence, secret
    # ⚠️ **`package.solution or package.puzzle` fell back to a board full of blanks.** Plausibility
    # asks whether this could have been a game, and half the cells being unknown is not an answer to
    # that — the fallback made the check weaker exactly when the solution was missing, which is when it
    # was most needed. The solution is required now, so there is nothing to fall back to.
    return [f"implausible board: {fault.what}" for fault in faults(package.solution)]


def check_reveal_is_complete(package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned) -> list[str]:
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


def check_provenance(package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned) -> list[str]:
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
    board = package.solution
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
    # The `is not None` guard here meant *compare only if we were given one*. LOB is always given now,
    # so the comparison against the game log always runs — which is what it was for.
    if board.left_on_base != evidence.official_left_on_base:
        refusals.append(
            f"runners left on base disagree with the game log: "
            f"{board.left_on_base} against {evidence.official_left_on_base}"
        )
    return refusals


def check_printed_boxscore_corresponds(
    package: Package, evidence: Evidence, secret: Ed25519PublicKey | Unsigned
) -> list[str]:
    """The half of the printed boxscore no board carries, against the anchors that can speak about it.

    ⚠️⚠️ **This check did not exist and `format.py` delegated to it by name.** Schema 5 gave the reveal
    both clubs; `check_reveal_agrees` compares the half the board also carries, cell by cell, and its
    docstring said the other half "belongs to `certify_for_publication`, against the game log". It did
    not. `Evidence` carried no rows, no certification looked at them, and **the publication gate
    certified a package whose `defense.batting` and `offense.pitching` were whatever the producer put
    there.** The fixture in `tests/reveals.py` names those rows `Not A Real Player` and
    `test_a_sound_package_is_publishable` expected the gate to accept it, which made the gap a
    demonstration rather than a hypothesis. **The absence of a check reading as the presence of a
    passing one**, written the same day as the rule about it.

    **What can be checked, and it is real.** The unshared grids are the *other direction* of the same
    game, so the line score speaks about them — and the line score's totals come from `retroGamesReg`,
    a different table from the `retroDailyReg` rows the printed sheet is built from:

      - the defence's batters scored the runs and made the hits the line score attributes to the
        defence, and
      - the offence's pitchers allowed exactly those same runs and hits, because they are the same
        events counted from the other side. That is §3's cross-team identity, applied to the direction
        the board does not show.
      - the offence's pitchers recorded the outs the defence's batters made, which is bounded by the
        innings the defence actually batted.

    A fabricated grid, a stale join, a side swap or a partial loader result breaks at least one of
    these. The all-zero fixture broke three.

    ⚠️⚠️ **What is not checked, and why the boundary stops here.** A swap of two rows within a club
    passes every assertion here, and so would a fabricated line whose club totals happen to hold.

    **That is deliberate, and the shape of the finished sheet is the reason.** It has two halves that
    are not the same kind of thing: one *was* the game and is validated to the extreme, and the other
    **was not used for the game at all** — it is on the page because a boxscore shows both teams.
    That half is offered as-is. Certifying it row by row would make §22 a second Retrosheet validator
    without protecting the guarantee it exists for. v30-P1-02, retracted on that ground.

    ⚠️ **An earlier version of this docstring reached the same conclusion by claiming no row-level
    source exists.** It was wrong: `retroEventsReg` is the play-by-play, and recomposing each printed
    line from it reproduced 114 of 115 rows across the six reference packages exactly. The check is
    buildable and is out of scope, which is a different sentence — and the difference is the one this
    project keeps paying for. `docs/reviews/non-issue.md` carries the record.

    So this check is the whole of the gate for those grids, and it says so rather than forwarding the
    rest to a check nobody intends to write.
    """
    # ⚠️ `evidence` is unused and that is a statement, not an oversight: the anchors this check needs
    # are the *line score*, which travels inside the package, and there is no row-level source in
    # `Evidence` to compare against. Kept in the signature because the registry calls every
    # certification the same way, and a check that quietly took a different shape would be one the
    # registry could stop wiring in without anything noticing.
    del evidence, secret
    reveal = package.reveal
    if reveal is None:
        # `check_reveal_is_complete` owns the absent case and refusing twice would double-count it.
        return []
    printed = reveal.boxscore
    score = package.solution.line_score
    refusals: list[str] = []

    for where, rows in (
        ("offense.batting", printed.offense.batting),
        ("offense.pitching", printed.offense.pitching),
        ("defense.batting", printed.defense.batting),
        ("defense.pitching", printed.defense.pitching),
    ):
        if not rows:
            refusals.append(f"the printed boxscore has no rows for {where}")
    if refusals:
        # The sums below would all read zero against a real total and bury the actual fault in noise.
        return refusals

    # The defence's own batting, and the offence's staff counting the same events from the other side.
    batted, pitched = printed.defense.batting, printed.offense.pitching
    for what, found, official in (
        ("the defence's batters scored", sum(row.runs for row in batted), score.defense_runs),
        ("the defence's batters hit", sum(row.hits for row in batted), score.defense_hits),
        ("the offence's pitchers allowed, in runs", sum(row.runs for row in pitched), score.defense_runs),
        ("the offence's pitchers allowed, in hits", sum(row.hits for row in pitched), score.defense_hits),
    ):
        if found != official:
            refusals.append(f"{what} {found}, and the line score says {official}")

    # ⚠️ A bound rather than an equality, because the last half-inning is not always completed: a home
    # side that scores the winning run stops batting. So the staff recorded three outs for every inning
    # the defence finished, and between none and three in the one it may not have.
    innings = len(score.defense_by_inning)
    outs = sum(row.outs for row in pitched)
    if innings and not (3 * (innings - 1) <= outs <= 3 * innings):
        refusals.append(
            f"the offence's pitchers recorded {outs} outs across {innings} innings the defence batted, "
            f"which is outside {3 * (innings - 1)} to {3 * innings}"
        )
    return refusals

CERTIFICATIONS: Final[dict[str, Callable[[Package, Evidence, Ed25519PublicKey | Unsigned], list[str]]]] = {
    "evidence_is_about_this_package": check_evidence_is_about_this_package,
    "mathematics": check_mathematics,
    "board_is_possible": check_board_is_possible,
    "reveal_is_complete": check_reveal_is_complete,
    "provenance": check_provenance,
    "independent_correspondence": check_independent_correspondence,
    "printed_boxscore_corresponds": check_printed_boxscore_corresponds,
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
