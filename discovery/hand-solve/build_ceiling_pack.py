"""Five boards at the stall ceiling — the hardest this board family can be made, in theory.

Not a band and not a spread: the top. Stalls are the variable the operator defined, and the only one
that measures where thinking is actually required — a stall is a *transition* into bounding, the
moment propagation runs dry and something beyond direct substitution is needed to restart it.

**These are not publishable boards.** They are the ceiling, and they will carry a lot of blanks. If
they read as tedious rather than hard, that is the finding rather than a failure of the pack: it says
the ceiling is not a target and the useful range is narrower than the measurement suggests. If they
read as solvable and interesting, there is headroom above every standard discussed so far. Either
answer is worth more than another decimal place on the measurements still owed.

⚠️ **The evidence that named this ceiling is owed a regeneration.** 16 to 18 stalls was measured with
the duplicated candidate list from v03-P1-02 — every footnote cell appeared twice, so footnotes entered
at roughly half the rate production gives them — and with the pre-v03-P2-01 solver. Neither should move
it much: the before-and-after on P2-01 was null on every field except `hardest_search`, on 2% of boards.
**So these five are generated here with the current corrected code and their stall counts are measured
now**, not read out of the old results file, and the report says whether they land where the old run
would have predicted.

The pack's rules are unchanged, and they are what make the answers usable:

  the stall count is never on the page      seeing "12 stalls" anchors the rating to the number
  the order is randomised                   the first boards become the reference for the rest
  nothing else that implies difficulty      no chain, no era, no team, no game id

Read-only against DGL. Run from `forge/`.
"""

import csv
import random
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import build_pack  # noqa: E402
from build_pack import Candidate, build_pdf, write_sheet  # noqa: E402
from measure import Loaded, load  # noqa: E402

from boxscore_forge.constraints import cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import DEFAULT_ORDERING, ORDERINGS, erasable  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.publish import to_board  # noqa: E402
from boxscore_forge.solver import Solution, Technique, solve  # noqa: E402
from boxscore_package.format import Package as PuzzlePackage  # noqa: E402
from boxscore_verify.verify import UNSIGNED, derivable_in_view, verify  # noqa: E402

WANTED = 5
GATE = 0.25
SEED = 118
SAMPLE_PER_DECADE = 4


@dataclass(frozen=True)
class Ceiling:
    loaded: Loaded
    stalls: int
    blanks: int
    erased: frozenset[str]


def stalls_in(solution: Solution) -> int:
    """Transitions into bounding. One halt is one stall however many steps it lasts."""
    count = 0
    previous = False
    for step in solution.deductions:
        bounding = step.technique is Technique.BOUNDING
        count += bounding and not previous
        previous = bounding
    return count


def ceiling_of(loaded: Loaded, seed: int) -> Ceiling | None:
    """Erase until nothing more can go, and keep the erasure that stalled the most.

    A full walk rather than a descending search on `erase(target_stalls=...)`. `erase` stops at the
    first erasure that *reaches* a target, which is the right thing when a target is wanted and the
    wrong thing here: the most-stalling board is not necessarily the first one over a line.
    """
    direction = loaded.direction
    shape = shape_of(direction)
    values = cell_values(direction)
    rng = random.Random(seed)  # noqa: S311
    candidates = ORDERINGS[DEFAULT_ORDERING](erasable(direction), direction, rng)

    erased: set[str] = set()
    best: Ceiling | None = None
    for cell in candidates:
        trial = erased | {cell}
        solution = solve(shape, {name: value for name, value in values.items() if name not in trial})
        if not solution.is_complete:
            continue
        erased = trial
        stalls = stalls_in(solution)
        if best is None or stalls > best.stalls:
            best = Ceiling(loaded=loaded, stalls=stalls, blanks=len(erased), erased=frozenset(erased))
    return best


def to_candidate(found: Ceiling) -> Candidate | None:
    """The board as the pack prints it, or nothing if any layer refuses it.

    ⚠️ **Verified rather than assumed.** These are the most-erased boards the generator can make, which
    is exactly where a puzzle stops being derivable — checking here is not a formality.
    """
    source = to_board(found.loaded.direction, None)
    board = to_board(found.loaded.direction, found.erased)
    package = PuzzlePackage(puzzle_id="0000000000000fff", puzzle=board, solution=source)
    if not verify(package, secret=UNSIGNED).accepted:
        return None
    notes = found.loaded.direction.batter_footnotes
    return Candidate(
        loaded=found.loaded,
        target=found.stalls,
        puzzle=board,
        solution=source,
        certified=derivable_in_view(package),
        has_substitution=any("-" in label for label in found.loaded.labels),
        has_live_footnote=any(
            note.hit_by_pitch or note.sacrifice_flies or note.sacrifice_hits or note.catcher_interference
            for note in notes
        ),
    )


def choose(found: list[Ceiling], rng: random.Random) -> list[Candidate]:
    """The five highest stall counts, one board per game, then shuffled."""
    chosen: list[Candidate] = []
    seen: set[str] = set()
    for item in sorted(found, key=lambda entry: -entry.stalls):
        if len(chosen) == WANTED:
            break
        if item.loaded.game_id in seen:
            continue
        candidate = to_candidate(item)
        if candidate is None:
            continue
        seen.add(item.loaded.game_id)
        chosen.append(candidate)
    rng.shuffle(chosen)
    return chosen


def audit(chosen: list[Candidate]) -> None:
    """Asserted, not printed. A pack that claims its quotas and does not meet them fails silently.

    The order check is the one that matters most here. Five boards sorted by stall count would make
    the first page the reference for every rating after it, and the 1-6 scale is the whole reason the
    pack exists.
    """
    if len(chosen) != WANTED:
        message = f"{len(chosen)} boards, wanted {WANTED}"
        raise SystemExit(message)
    games = {candidate.loaded.game_id for candidate in chosen}
    if len(games) != WANTED:
        message = f"{len(games)} distinct games across {WANTED} boards; a solver would see a lineup twice"
        raise SystemExit(message)
    stalls = [candidate.target for candidate in chosen]
    if stalls == sorted(stalls) or stalls == sorted(stalls, reverse=True):
        message = f"the boards are in stall order {stalls}; reshuffle, or the first page anchors the rest"
        raise SystemExit(message)
    if any(not candidate.puzzle.batting for candidate in chosen):
        message = "a chosen board has no batting rows"
        raise SystemExit(message)


def write_key(path: Path, chosen: list[Candidate]) -> None:
    """The stall count, out of git and unopened until every sheet is filled."""
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["board", "game_id", "season", "stalls", "blanks", "certified_by_3b"])
        for index, candidate in enumerate(chosen, start=1):
            blanks = sum(cell is None for row in candidate.puzzle.batting for cell in row)
            blanks += sum(cell is None for row in candidate.puzzle.pitching for cell in row)
            blanks += sum(cell is None for cell in candidate.puzzle.batting_totals)
            blanks += sum(cell is None for cell in candidate.puzzle.pitching_totals)
            blanks += sum(cell is None for row in candidate.puzzle.footnotes for cell in row)
            writer.writerow(
                [
                    f"{index:02d}",
                    candidate.loaded.game_id,
                    candidate.loaded.season,
                    candidate.target,
                    blanks,
                    "yes" if candidate.certified else "no",
                ]
            )


def main() -> None:
    rng = random.Random(SEED)  # noqa: S311
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
        if not find_violations(item.direction)
    ]
    if not sample:
        message = f"no directions survived the {GATE:.0%} gate at {SAMPLE_PER_DECADE} per decade"
        raise SystemExit(message)
    print(f"{len(sample)} gated directions; walking each to its stall ceiling", flush=True)

    found: list[Ceiling] = []
    for number, loaded in enumerate(sample, start=1):
        reached = ceiling_of(loaded, SEED)
        if reached is not None:
            found.append(reached)
        if number % 10 == 0:
            print(f"  {number}/{len(sample)} walked, best so far {max(c.stalls for c in found)}", flush=True)
    if not found:
        message = "no direction produced a derivable erasure at all"
        raise SystemExit(message)

    chosen = choose(found, rng)
    audit(chosen)

    build_pdf(_HERE / "ceiling-boards.pdf", chosen, answers=False)
    build_pdf(_HERE / "ceiling-solutions.pdf", chosen, answers=True)
    write_key(_HERE / "ceiling-key.csv", chosen)
    write_sheet(_HERE / "ceiling-recording-sheet.csv", len(chosen))

    everything = sorted((item.stalls for item in found), reverse=True)
    print("")
    print(f"ceiling across the sample: {everything[:10]}")
    print(f"chosen (printed order): {[candidate.target for candidate in chosen]}")
    print(f"blanks: {[sum(cell is None for row in c.puzzle.batting for cell in row) for c in chosen]} in the batting grid")
    print(f"uncertified by layer 3b: {sum(1 for c in chosen if not c.certified)} of {len(chosen)}")
    print(f"wrote ceiling-boards.pdf, ceiling-solutions.pdf, ceiling-key.csv, ceiling-recording-sheet.csv in {_HERE}")
    print(f"(build_pack's own targets are {build_pack.TARGETS}, which are chain rungs and not used here)")


if __name__ == "__main__":
    main()
