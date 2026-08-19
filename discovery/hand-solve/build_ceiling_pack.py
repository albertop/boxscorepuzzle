"""Five boards at two rungs — the top of the range and the median — built the way production builds.

**Two at 8 stalls and three at 5**, so the ceiling and the board that will ship most days are judged in
one sitting and against each other. The median is the more important of the two and is the one the
previous version of this pack did not contain at all.

⚠️ **These are erased by `erase(target_stalls=...)`, not by searching for a maximum.** Every earlier
version of this file walked a greedy path per ordering per seed and kept whichever erasure stalled the
most. That was right when the question was *how hard can a board of this family get*, and it is wrong
now: a board found by maximising stalls is over-erased by construction, and **no published board is
ever made that way**. The generator stops at the first erasure that reaches its target, so that is what
a person judging a publishable board has to be given. Judging a board that does not ship is the exact
error of the last several rounds.

⚠️ **The pitcher cap moved from 4 to 6 and these are generated at 6.** The two facts that make this
pack worth running are consequences: at ≤6 a board reaching 8 stalls is **33% of the pool rather than
5%**, so the high rung stops being atypical by construction; and a six-pitcher board spreads its blanks
over more rows, which is the direct answer to whether twelve blanks reads as sparse. **At least one of
the five has six pitchers**, asserted rather than hoped for — it is the new case and it should be seen
before it becomes half of what ships.

The pack's rules are unchanged, and they are what make the answers usable:

  the stall count is never on the page      seeing "8 stalls" anchors the rating to the number
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

from boxscore_domain import MEDIAN_STALL_CEILING, PITCHER_CAP  # noqa: E402
from boxscore_forge.erasure import DEFAULT_ORDERING, Puzzle, erase  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.publish import to_board  # noqa: E402
from boxscore_package.format import Board  # noqa: E402
from boxscore_package.format import Package as PuzzlePackage  # noqa: E402
from boxscore_verify.verify import UNSIGNED, derivable_in_view, verify  # noqa: E402

COMPOSITION: dict[int, int] = {8: 2, MEDIAN_STALL_CEILING: 3}
"""Stall target to how many boards of it. **The ceiling and the median, judged together.**

8 is the top of what the pool reaches comfortably at the new cap; 5 is the median ceiling, unchanged by
the cap change, and therefore what most published boards will be. A pack of nothing but hard boards
tells you where the top is and nothing about the product.
"""

WANTED = sum(COMPOSITION.values())
GATE = 0.25
"""Tighter than `ZERO_DENSITY_GATE`, deliberately and only here.

The decided pool gate is 30%. This pack puts boards in front of a person to judge, so it draws from the
cleaner end — a board rejected for zero density is not the board being asked about. **Stated rather
than left as a bare number that looks like it disagrees with the constants module.**"""
SEED = 118
SAMPLE_PER_DECADE = 6
SIX_PITCHER_BOARDS = 1
"""How many of the five must carry the new maximum. **Asserted in `audit()`.**

Not a preference. Six pitchers is the case the cap change introduces and the one nobody has seen on a
page, and a pack that happened not to contain it would answer a question about the old board.
"""

SEEDS = (1, 2, 3, 4, 5)
"""Tried in order until one reaches the target. `erase` is deterministic per seed (§21), so a board
that fails on all five is a board that cannot carry this target rather than one that was unlucky."""

WATCHED = "WAS201307070"
"""⚠️ **The one board with a human verdict attached to a measured number.**

The operator solved it and found it hard. It measured **19 stalls with 79 blanks** — on the scale that
counted the solver deducing footnote zeros, and via the maximising search this file no longer uses. So
the honest comparison now is not a stall count but *which targets it can carry and at what blank
count*, which is what gets reported.

⚠️ **Asked for by name through `load(also=...)`, not hoped for.** A stratified draw out of a pool in
the hundreds of thousands would never contain it, so the "not in this sample" branch would be the whole
instrument — and a check that never fires is indistinguishable from one that is broken. It still faces
the gate, the caps and the provenance rule like every other board, and it is **watched, not favoured**:
it competes for a slot on the same terms as anything else.
"""


@dataclass(frozen=True, slots=True)
class Reached:
    """One board erased to one target, by the production path."""

    loaded: Loaded
    target: int
    puzzle: Puzzle
    seed: int
    """Which seed produced it. Recorded so the board can be rebuilt exactly (§21)."""


def blanks_in(board: Board) -> int:
    """Every cell the player has to fill, across both grids and both totals rows.

    ⚠️ The footnote line is given in full, so it contributes nothing — counted anyway rather than
    omitted, because a count that silently skips a section is how a board looks sparser than it is.
    """
    return (
        sum(cell is None for row in board.batting for cell in row)
        + sum(cell is None for row in board.pitching for cell in row)
        + sum(cell is None for cell in board.batting_totals)
        + sum(cell is None for cell in board.pitching_totals)
        + sum(cell is None for row in board.footnotes for cell in row)
    )


def reach(loaded: Loaded, target: int) -> Reached | None:
    """The first seed that carries this board to this target, or nothing.

    Nothing is a discard, not a failure: §22 throws candidates away silently and never relaxes a rule
    to reach a number.
    """
    for seed in SEEDS:
        puzzle = erase(loaded.direction, target_stalls=target, seed=seed, ordering=DEFAULT_ORDERING)
        if puzzle is not None:
            return Reached(loaded=loaded, target=target, puzzle=puzzle, seed=seed)
    return None


def to_candidate(found: Reached) -> Candidate | None:
    """The board as the pack prints it, or nothing if any layer refuses it.

    ⚠️ **Verified rather than assumed.** Checking here is not a formality: these go in front of a person
    as publishable boards, and a board that fails a layer is not one.
    """
    source = to_board(found.loaded.direction, None)
    board = to_board(found.loaded.direction, found.puzzle.erased)
    package = PuzzlePackage(
        labels=("C",) * len(board.batting),
        pitcher_labels=("C",) * len(board.pitching),
        offense_is_home=True,
        puzzle_id="0000000000000fff",
        puzzle=board,
        solution=source,
    )
    if not verify(package, secret=UNSIGNED).accepted:
        return None
    notes = found.loaded.direction.batter_footnotes
    return Candidate(
        loaded=found.loaded,
        target=found.target,
        puzzle=board,
        solution=source,
        certified=derivable_in_view(package),
        has_substitution=len(set(found.loaded.slots)) < len(found.loaded.slots),
        has_live_footnote=any(
            note.hit_by_pitch or note.sacrifice_flies or note.sacrifice_hits or note.catcher_interference
            for note in notes
        ),
    )


def _pitchers(candidate: Candidate) -> int:
    return len(candidate.puzzle.pitching)


def choose(found: list[Reached], rng: random.Random) -> list[Candidate]:
    """Fill each target's quota, one board per game, with the six-pitcher case guaranteed a place.

    ⚠️ **The six-pitcher board is placed first, not hoped into the result.** Filling the quotas and then
    checking would leave the assertion in `audit()` failing on perfectly good packs for a reason the
    selection could have prevented — a quota nobody arranged to meet is a quota that fails at random.
    """
    chosen: list[Candidate] = []
    seen: set[str] = set()
    remaining = dict(COMPOSITION)

    def take(item: Reached) -> bool:
        if remaining.get(item.target, 0) == 0 or item.loaded.game_id in seen:
            return False
        candidate = to_candidate(item)
        if candidate is None:
            return False
        seen.add(item.loaded.game_id)
        remaining[item.target] -= 1
        chosen.append(candidate)
        return True

    # ⚠ **Scarcest target first.** Deterministic either way, but ordering by ascending target fills the
    # abundant rung before the scarce one, and every game consumed there is a game the scarce rung
    # cannot use — which is precisely how an earlier pack ended with zero boards at one of its rungs and
    # reported its composition as though it had them. Descending, so 8 stalls picks before 5.
    ordered = sorted(found, key=lambda item: (-item.target, item.loaded.game_id))
    crowded = [item for item in ordered if len(item.loaded.direction.pitching) == PITCHER_CAP]
    placed = 0
    for item in crowded:
        if placed == SIX_PITCHER_BOARDS:
            break
        placed += take(item)
    for item in ordered:
        take(item)

    rng.shuffle(chosen)
    return chosen


def audit(chosen: list[Candidate]) -> None:
    """Asserted, not printed. A pack that claims its quotas and does not meet them fails silently.

    That has already happened once in this project, when weighted sampling produced zero boards at the
    easiest rung and the pack reported its composition and was believed.
    """
    if len(chosen) != WANTED:
        message = f"{len(chosen)} boards, wanted {WANTED}"
        raise SystemExit(message)
    counts = {target: sum(1 for c in chosen if c.target == target) for target in COMPOSITION}
    if counts != COMPOSITION:
        message = f"composition is {counts}, wanted {COMPOSITION}"
        raise SystemExit(message)
    games = {candidate.loaded.game_id for candidate in chosen}
    if len(games) != WANTED:
        message = f"{len(games)} distinct games across {WANTED} boards; a solver would see a lineup twice"
        raise SystemExit(message)
    crowded = sum(1 for candidate in chosen if _pitchers(candidate) == PITCHER_CAP)
    if crowded < SIX_PITCHER_BOARDS:
        message = (
            f"{crowded} boards with {PITCHER_CAP} pitchers, wanted {SIX_PITCHER_BOARDS}; the case the "
            f"cap change introduces is not in the pack, so the pack answers a question about the old board"
        )
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
        writer.writerow(["board", "game_id", "season", "stalls", "blanks", "pitchers", "certified_by_3b"])
        for index, candidate in enumerate(chosen, start=1):
            writer.writerow(
                [
                    f"{index:02d}",
                    candidate.loaded.game_id,
                    candidate.loaded.season,
                    candidate.target,
                    blanks_in(candidate.puzzle),
                    _pitchers(candidate),
                    "yes" if candidate.certified else "no",
                ]
            )


def main() -> None:
    rng = random.Random(SEED)  # noqa: S311
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE, also=(WATCHED,))
        if not find_violations(item.direction)
    ]
    if not sample:
        message = f"no directions survived the {GATE:.0%} gate at {SAMPLE_PER_DECADE} per decade"
        raise SystemExit(message)
    targets = sorted(COMPOSITION, reverse=True)
    print(f"{len(sample)} gated directions, erasing to targets {targets} with seeds {SEEDS}", flush=True)

    found: list[Reached] = []
    for number, loaded in enumerate(sample, start=1):
        for target in targets:
            reached = reach(loaded, target)
            if reached is not None:
                found.append(reached)
        if number % 10 == 0:
            print(f"  {number}/{len(sample)} erased, {len(found)} board-target pairs so far", flush=True)
    if not found:
        message = "no direction reached any target at all"
        raise SystemExit(message)

    chosen = choose(found, rng)
    audit(chosen)

    build_pdf(_HERE / "ceiling-boards.pdf", chosen, answers=False)
    build_pdf(_HERE / "ceiling-solutions.pdf", chosen, answers=True)
    write_key(_HERE / "ceiling-key.csv", chosen)
    write_sheet(_HERE / "ceiling-recording-sheet.csv", len(chosen))

    # Plain text on purpose. Every long run here is redirected to a file, Windows gives a redirected
    # stream cp1252, and a report that dies on its own warning sign loses the compute that produced it.
    print()
    for target in targets:
        reaching = {item.loaded.game_id for item in found if item.target == target}
        share = len(reaching) / len({item.loaded.game_id for item in found})
        print(f"coverage at {target} stalls: {len(reaching)} boards ({share:.0%} of those reaching any target)")
    print(f"chosen (printed order): targets {[c.target for c in chosen]}")
    print(f"   blanks:   {[blanks_in(c.puzzle) for c in chosen]}")
    print(f"   pitchers: {[_pitchers(c) for c in chosen]}")
    print(f"   batters:  {[len(c.puzzle.batting) for c in chosen]}")
    print(f"uncertified by layer 3b: {sum(1 for c in chosen if not c.certified)} of {len(chosen)}")
    print(f"wrote ceiling-boards.pdf, ceiling-solutions.pdf, ceiling-key.csv, ceiling-recording-sheet.csv in {_HERE}")

    watched = [item for item in found if item.loaded.game_id == WATCHED]
    print()
    if watched:
        print(f"THE ONE BOARD WITH A HUMAN VERDICT: {WATCHED}")
        print("   measured 19 stalls / 79 blanks under the maximising search, on the scale that counted")
        print("   zeros, and the operator solved it and found it hard. Built the way production builds:")
        for item in sorted(watched, key=lambda i: -i.target):
            board = to_board(item.loaded.direction, item.puzzle.erased)
            print(f"   target {item.target}: reached with {blanks_in(board)} blanks (seed {item.seed})")
    else:
        print(f"{WATCHED} was asked for by name and did not come back, so the one measured-and-judged")
        print("   board could not be re-measured. It was rejected by the gate, the caps, the provenance")
        print("   rule or an identity check. Said rather than omitted: its absence is not a null result.")
    print(f"(build_pack's own targets are {build_pack.TARGETS}, which are chain rungs and not used here)")


if __name__ == "__main__":
    main()
