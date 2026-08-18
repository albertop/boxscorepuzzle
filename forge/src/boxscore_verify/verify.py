"""§22's four layers, each able to reject on its own.

    1. Validate the boxscore against all identities before admitting it to the pool
    2. Prove solution uniqueness
    3. Require the solver to finish without guessing
    4. Solve the published puzzle from scratch and compare against the original boxscore

Plus the operating rule §22 states alongside them: **sign every published puzzle and check the
signature before serving**, which §33 extends from corruption to an interrupted upload.

**Nothing publishes without passing all of them, and a failure is a discard, never a repair.** With
thousands of candidates, throwing away 30% costs nothing, and a repaired puzzle is a puzzle whose
provenance nobody can state.

**The layers overlap on purpose.** Layer 4 re-solves a board layer 2 already proved unique and layer
3 already derived, which is redundant exactly the way a second altimeter is redundant. If layer 4
ever catches something the first three passed, that is the redundancy earning its keep and is worth
saying loudly rather than quietly fixing.

⚠️ **Shares no code with the generator (§22).** Everything it needs it states for itself, from the
design document. The one thing both sides genuinely need — the file format — lives in
`boxscore_package`, which belongs to neither.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from boxscore_package.format import Board, Package
from boxscore_package.signing import SignatureError
from boxscore_package.signing import verify as verify_signature
from boxscore_verify.reason import ContradictionError, UndecidedError, derive, derive_in_view, narrow, solutions
from boxscore_verify.rules import all_cells, line_score_faults, relations, values_of


class Unsigned:
    """Deliberate opt-out from the signature check, for tests and discovery only.

    ⚠️ It exists so that *skipping* the check is a thing a caller says out loud. The previous version
    took `secret=None` and returned success, which meant a publish path with a misconfigured secret
    verified nothing and reported a pass — the absence of a check reading as the presence of a
    passing one. `None` is now an error and this sentinel is the only way past.
    """

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "UNSIGNED"


UNSIGNED: Final = Unsigned()


class Layer(StrEnum):
    """Which check rejected. The distribution across a batch says whether the generator is behaving."""

    SIGNATURE = "signature"
    IDENTITIES = "identities"
    UNIQUENESS = "uniqueness"
    DERIVABILITY = "derivability"
    END_TO_END = "end_to_end"


class Fault(StrEnum):
    """§22's four failure types, plus the two the operating rules add.

    They are kept distinct because they mean different things about the pipeline: bad data is
    Retrosheet's, no solution and multiple solutions are the erasure's, not derivable is the
    generator's stopping rule, and corruption is the transfer's.
    """

    BAD_DATA = "bad_data"
    MALFORMED = "malformed"
    NO_SOLUTION = "no_solution"
    MULTIPLE_SOLUTIONS = "multiple_solutions"
    NOT_DERIVABLE = "not_derivable"
    MISMATCH = "mismatch"
    CORRUPTED = "corrupted"
    UNDECIDED = "undecided"


@dataclass(frozen=True, slots=True)
class Rejection:
    layer: Layer
    fault: Fault
    detail: str


@dataclass(frozen=True, slots=True)
class Verdict:
    puzzle_id: str
    rejection: Rejection | None = None

    @property
    def accepted(self) -> bool:
        return self.rejection is None


def verify(package: Package, *, secret: bytes | Unsigned | None) -> Verdict:
    """Run every layer in order and stop at the first that rejects.

    Stopping early is right for a discard — the puzzle is gone either way — and the layer that caught
    it is the interesting fact. Running the rest would only say what else is wrong with something
    nobody will publish.

    `None` is in the signature only so that it can be **rejected**: a misconfigured secret arrives
    as `None` at runtime whatever the annotations say, and this is the one place that can catch it.

    `secret` has no default on purpose. A publish or import path cannot forget it, and passing `None`
    — which is what a misconfigured secret looks like — raises rather than quietly skipping the
    integrity layer. Tests and discovery pass `UNSIGNED` to say so deliberately.
    """
    if secret is None:
        message = "no signing secret: pass UNSIGNED to verify without one, deliberately"
        raise ValueError(message)
    for check in LAYERS.values():
        rejection = check(package, secret)
        if rejection is not None:
            return Verdict(puzzle_id=package.puzzle_id, rejection=rejection)
    return Verdict(puzzle_id=package.puzzle_id)


def check_signature(package: Package, secret: bytes | Unsigned | None) -> Rejection | None:
    """Checked first: nothing else is worth computing about a file that arrived damaged."""
    if secret is None:
        message = "no signing secret: pass UNSIGNED to skip this layer, deliberately"
        raise ValueError(message)
    if isinstance(secret, Unsigned):
        return None
    try:
        verify_signature(package, secret)
    except SignatureError as error:
        return Rejection(Layer.SIGNATURE, Fault.CORRUPTED, str(error))
    return None


def check_identities(package: Package, _: bytes | Unsigned | None) -> Rejection | None:
    """Layer 1: the boxscore balances, and the puzzle is a board of the same game.

    The structural half is not decoration. §6 gives the line score and the footnote line complete and
    never erased, so a puzzle that erased one is malformed rather than hard, and a puzzle whose line
    score disagrees with its source is not a puzzle about that game at all.
    """
    if package.source is None:
        return Rejection(Layer.IDENTITIES, Fault.MALFORMED, "no source boxscore to verify against")

    faults = _structure_faults(package.puzzle, package.source)
    if faults:
        return Rejection(Layer.IDENTITIES, Fault.MALFORMED, "; ".join(faults))

    faults = line_score_faults(package.source)
    if faults:
        return Rejection(Layer.IDENTITIES, Fault.BAD_DATA, "; ".join(faults))

    missing = [cell for cell in all_cells(package.source) if cell not in values_of(package.source)]
    if missing:
        return Rejection(
            Layer.IDENTITIES,
            Fault.MALFORMED,
            f"the source boxscore is incomplete: {len(missing)} cells absent, first {missing[0]}",
        )

    known = values_of(package.source)
    broken: list[str] = []
    for relation in relations(package.source):
        total = sum(coefficient * known[cell] for cell, coefficient in relation.terms)
        if relation.equality and total != relation.constant:
            broken.append(f"{relation.origin} is off by {total - relation.constant}")
        elif not relation.equality and total > relation.constant:
            broken.append(f"{relation.origin} exceeded by {total - relation.constant}")
    if any(value < 0 for value in known.values()):
        broken.append("a cell holds a negative value")
    if broken:
        return Rejection(Layer.IDENTITIES, Fault.BAD_DATA, "; ".join(broken))
    return None


def check_uniqueness(package: Package, _: bytes | Unsigned | None) -> Rejection | None:
    """Layer 2: exactly one board completes the puzzle.

    None means the erasure produced a contradiction; two means cells came out that were not forced,
    which is the case a player meets as a board with no right answer to find.
    """
    board = package.puzzle
    try:
        found = solutions(relations(board), all_cells(board), values_of(board), limit=2)
    except ContradictionError:
        return Rejection(Layer.UNIQUENESS, Fault.NO_SOLUTION, "the given cells contradict each other")
    except UndecidedError as error:
        return Rejection(Layer.UNIQUENESS, Fault.UNDECIDED, str(error))
    if not found:
        return Rejection(Layer.UNIQUENESS, Fault.NO_SOLUTION, "no completion exists")
    if len(found) > 1:
        differing = sorted(cell for cell in found[0] if found[0][cell] != found[1][cell])
        return Rejection(
            Layer.UNIQUENESS,
            Fault.MULTIPLE_SOLUTIONS,
            f"at least two completions, differing at {len(differing)} cells, first {differing[0]}",
        )
    return None


def check_derivability(package: Package, _: bytes | Unsigned | None) -> Rejection | None:
    """Layer 3: reachable without a guess.

    §22 calls unique-but-underivable the worst failure because it looks correct: the puzzle passes
    every arithmetic check and the player is nonetheless reduced to trying values. Uniqueness alone
    is not sufficient, and this is the layer that says so.
    """
    board = package.puzzle
    try:
        reached = derive(relations(board), all_cells(board), values_of(board))
    except ContradictionError:
        return Rejection(Layer.DERIVABILITY, Fault.NO_SOLUTION, "narrowing emptied a cell")
    if not reached.is_complete:
        return Rejection(
            Layer.DERIVABILITY,
            Fault.NOT_DERIVABLE,
            f"stalls with {len(reached.unresolved)} cells unresolved, first {reached.unresolved[0]}",
        )
    return None


def check_end_to_end(package: Package, _: bytes | Unsigned | None) -> Rejection | None:
    """Layer 4: solve the published board from scratch and compare against the original.

    Deliberately redundant with layers 2 and 3, and deliberately not reusing their results. It is the
    only layer that compares against the *boxscore* rather than against the constraints, so it is the
    one that catches a puzzle which is perfectly consistent and about a different game — a given cell
    quietly altered after generation, for instance.
    """
    if package.source is None:  # pragma: no cover - layer 1 already rejected this
        return Rejection(Layer.END_TO_END, Fault.MALFORMED, "no source boxscore to compare against")
    board = package.puzzle
    try:
        found = solutions(relations(board), all_cells(board), values_of(board), limit=1)
    except ContradictionError:
        return Rejection(Layer.END_TO_END, Fault.NO_SOLUTION, "the published board cannot be completed")
    except UndecidedError as error:
        return Rejection(Layer.END_TO_END, Fault.UNDECIDED, str(error))
    if not found:
        return Rejection(Layer.END_TO_END, Fault.NO_SOLUTION, "the published board cannot be completed")

    original = values_of(package.source)
    solved = found[0]
    differing = sorted(cell for cell in original if solved.get(cell) != original[cell])
    if differing:
        first = differing[0]
        return Rejection(
            Layer.END_TO_END,
            Fault.MISMATCH,
            f"solving gives a different boxscore at {len(differing)} cells; {first} "
            f"solved to {solved.get(first)} against {original[first]}",
        )
    return None


def _structure_faults(puzzle: Board, source: Board) -> list[str]:
    faults: list[str] = []
    if len(puzzle.batting) != len(source.batting):
        faults.append(f"{len(puzzle.batting)} batting rows against {len(source.batting)} in the source")
    if len(puzzle.pitching) != len(source.pitching):
        faults.append(f"{len(puzzle.pitching)} pitching rows against {len(source.pitching)} in the source")
    if len(puzzle.footnotes) != len(puzzle.batting):
        faults.append(f"{len(puzzle.footnotes)} footnote rows against {len(puzzle.batting)} batters")
    if puzzle.line_score != source.line_score:
        faults.append("the puzzle's line score differs from the source's")
    if any(value is None for row in puzzle.footnotes for value in row):
        faults.append("a footnote cell is erased, and §6 gives the footnote line complete")
    if any(value is None for value in puzzle.footnote_totals):
        faults.append("a footnote total is erased, and §6 gives the footnote line complete")
    if puzzle.left_on_base is None:
        faults.append("left on base is erased, and without it the global identity cannot be expressed")
    return faults


def tally(verdicts: Iterable[Verdict]) -> dict[str, int]:
    """Rejections by layer and fault, which is what says whether the generator is behaving.

    A batch where layer 3 rejects most is a generator stopping too early; one where layer 1 rejects
    most is a pool admitting boxscores it should not. **Anything at all in layer 4 is the headline**,
    because it means the first three passed something they should have caught.
    """
    counts: dict[str, int] = {"accepted": 0}
    for verdict in verdicts:
        if verdict.rejection is None:
            counts["accepted"] += 1
            continue
        key = f"{verdict.rejection.layer}:{verdict.rejection.fault}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def derivable_in_view(package: Package) -> bool:
    """Layer 3b, **reported rather than enforced**: derivable by the weak solver too.

    Layer 3 certifies that no guess is needed by a propagator that holds every relation in mind at
    once. This asks the same question of a solver that holds one relation at a time, which is a lower
    bound on what a person can do where layer 3 is an upper one.

    It is not in `LAYERS` and does not reject anything. Whether it should become a gate is a question
    about how many currently-passing boards survive it — if nearly all do, the concern was
    theoretical; if many fail, the gap between the two solvers is real and worth gating on. That
    measurement comes before the decision, not after.
    """
    board = package.puzzle
    try:
        return derive_in_view(relations(board), all_cells(board), values_of(board)).is_complete
    except ContradictionError:  # pragma: no cover - a contradictory board is rejected at layer 2
        return False


LAYERS: dict[Layer, Callable[[Package, bytes | Unsigned | None], Rejection | None]] = {
    Layer.SIGNATURE: check_signature,
    Layer.IDENTITIES: check_identities,
    Layer.UNIQUENESS: check_uniqueness,
    Layer.DERIVABILITY: check_derivability,
    Layer.END_TO_END: check_end_to_end,
}
"""Every layer, in the order they run, and each callable on its own.

§22's wording is that each layer can reject on its own, so each one is reachable on its own. That is
not only for tests: a batch run that wants to know *how many* boards each layer would have caught,
rather than which caught first, needs to call them individually.
"""


__all__ = [
    "LAYERS",
    "UNSIGNED",
    "Fault",
    "Layer",
    "Rejection",
    "Unsigned",
    "Verdict",
    "check_derivability",
    "check_end_to_end",
    "check_identities",
    "check_signature",
    "check_uniqueness",
    "derivable_in_view",
    "narrow",
    "tally",
    "verify",
]
