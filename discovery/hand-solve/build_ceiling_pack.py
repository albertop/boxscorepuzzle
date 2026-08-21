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
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import build_pack  # noqa: E402
from build_pack import Candidate, build_pdf, write_sheet  # noqa: E402
from measure import Loaded, load  # noqa: E402

from boxscore_domain import BATTER_CAP, HAND_SOLVE_ZERO_DENSITY_GATE, MEDIAN_STALL_CEILING, PITCHER_CAP  # noqa: E402
from boxscore_forge.constraints import cell_values, shape_of  # noqa: E402
from boxscore_forge.erasure import DEFAULT_ORDERING, Puzzle, erase  # noqa: E402
from boxscore_forge.identities import find_violations  # noqa: E402
from boxscore_forge.publish import (  # noqa: E402
    slot_references,
    to_board,
)
from boxscore_forge.solver import solve  # noqa: E402
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
GATE = HAND_SOLVE_ZERO_DENSITY_GATE
"""Tighter than `ZERO_DENSITY_GATE`, deliberately and only for the hand-solve packs.

This pack puts boards in front of a person to judge, so it draws from the cleaner end — a board
rejected for zero density is not the board being asked about, and the corrected pool is abundant enough
to afford it. **The reason and the number now live together in `boxscore_domain`**, because a deviation
with its reason attached is not the defect a bare literal is.
"""
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
    loaded = found.loaded
    source = to_board(loaded.direction, None)
    board = to_board(loaded.direction, found.puzzle.erased)
    # ⚠️ **The loader's own values, not placeholders.** This built the package with `("C",) * n` labels
    # and `offense_is_home=True`, and omitted `slot_references` entirely — which the schema requires, so
    # the run died here **after** finishing every erasure. Two costs, not one: the compute, and a
    # verification that would have been running against a package no generator produces.
    package = PuzzlePackage(
        labels=loaded.labels,
        pitcher_labels=loaded.pitcher_labels,
        slot_references=slot_references(loaded.slots),
        offense_is_home=loaded.offense_is_home,
        puzzle_id="0000000000000fff",
        puzzle=board,
        solution=source,
    )
    if not verify(package, secret=UNSIGNED, source=source).accepted:
        return None
    notes = loaded.direction.batter_footnotes
    return Candidate(
        loaded=loaded,
        target=found.target,
        puzzle=board,
        solution=source,
        certified=derivable_in_view(package),
        has_substitution=len(set(loaded.slots)) < len(loaded.slots),
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


def report_certification(found: list[Reached], chosen: list[Candidate], targets: list[int]) -> None:
    """Whether "5 of 5 uncertified" is a confound this pack introduced or a fact about the pool.

    ⚠️⚠️ **The pack cannot answer its own question without this.** The primary question is *is 5 stalls
    already hard*. If every 5-stall board in the pack is one layer 3b refuses, then a verdict of "hard"
    has two explanations the pack cannot separate: the stall level, or the uncertified status. And 3b
    failing is itself a difficulty signal — it means the board needs a narrowed range carried from one
    relation to the next, which is real work for a person.

    ⚠️ **A confound has no signature in the results**, so reading the filled sheets afterwards cannot
    catch it. It can only be seen here, while the pack is being built. What distinguishes the two cases
    is the *candidate population*: if almost every board reaching a target is uncertified, then the two
    labels name one population and selection introduced nothing. If certified candidates existed and
    were passed over, the pack chose its own confound.
    """
    print("certification of the candidates each target was drawn from:")
    # ⚠️ Certification is only computed when a `Reached` becomes a `Candidate`, so the pool has to be
    # converted to be counted. `to_candidate` returns None for a board the verifier rejects; those are
    # not in the drawable pool either, so they are excluded from both sides of the ratio.
    for target in targets:
        pool = [candidate for item in found if item.target == target if (candidate := to_candidate(item))]
        picked = [item for item in chosen if item.target == target]
        certified = sum(1 for item in pool if item.certified)
        if not pool:
            print(f"   {target} stalls: no drawable candidates, which should be impossible here")
            continue
        print(
            f"   {target} stalls: {certified}/{len(pool)} candidates certified "
            f"({certified / len(pool):.0%}); chosen {sum(1 for c in picked if c.certified)}/{len(picked)}"
        )


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


ERASURES = _HERE / "ceiling-erasures.json"
"""Where the expensive half is written, **before anything is formatted**.

⚠️ **This exists because the first run at the new cap finished every erasure and then died in
`to_candidate` over a missing schema field.** Seventy-two directions, a hundred and one board-target
pairs, and none of it survived — the script held the whole result in memory and wrote nothing until the
last step. That is the same defect that cost this project three hours of compute once already, and the
zero-footnote instrument was fixed for exactly it: **persist rows before formatting them.**

A cache is only safe if it refuses to be reused when it no longer applies, so the file carries a stamp
of everything that decides what is in it. Any difference and it is ignored rather than trusted — a
stale cache silently answering a different question is worse than no cache.
"""


def _stamp(sample: list[Loaded]) -> dict[str, object]:
    """What must be identical for a saved erasure to still be the answer to this run's question."""
    return {
        "batter_cap": BATTER_CAP,
        "pitcher_cap": PITCHER_CAP,
        "gate": GATE,
        "sample_per_decade": SAMPLE_PER_DECADE,
        "targets": sorted(COMPOSITION),
        "seeds": list(SEEDS),
        "ordering": DEFAULT_ORDERING,
        "directions": sorted(f"{item.game_id}:{item.offense_team}" for item in sample),
    }


def _save(sample: list[Loaded], found: list["Reached"]) -> None:
    ERASURES.write_text(
        json.dumps(
            {
                "stamp": _stamp(sample),
                "erasures": [
                    {
                        "game_id": item.loaded.game_id,
                        "offense_team": item.loaded.offense_team,
                        "target": item.target,
                        "seed": item.seed,
                        "erased": sorted(item.puzzle.erased),
                    }
                    for item in found
                ],
            },
            indent=1,
        ),
        encoding="utf-8",
        newline=chr(10),
    )


def _restore(sample: list[Loaded]) -> list["Reached"] | None:
    """The saved erasures, or nothing if anything about this run differs from the one that saved them."""
    if not ERASURES.exists():
        return None
    saved = json.loads(ERASURES.read_text(encoding="utf-8"))
    if saved.get("stamp") != _stamp(sample):
        print("a saved erasure set exists and does not match this run's inputs; erasing again", flush=True)
        return None
    by_direction = {(item.game_id, item.offense_team): item for item in sample}
    restored: list[Reached] = []
    for row in saved["erasures"]:
        loaded = by_direction[row["game_id"], row["offense_team"]]
        # ⚠️ Re-solved rather than trusted. The stall count is what the board is selected on, and a
        # cache that carried the number instead of the cells would let a solver change go unnoticed —
        # the erasure is the expensive part, and solving one board is not.
        shape = shape_of(loaded.direction)
        values = cell_values(loaded.direction)
        erased = frozenset(row["erased"])
        given = {name: value for name, value in values.items() if name not in erased}
        solution = solve(shape, given)
        if not solution.is_complete or solution.stalls < row["target"]:
            print(f"  saved erasure for {row['game_id']} no longer reaches {row['target']}; erasing again")
            return None
        puzzle = Puzzle(shape=shape, given=given, erased=erased, solution=solution)
        restored.append(Reached(loaded=loaded, target=row["target"], puzzle=puzzle, seed=row["seed"]))
    print(f"restored {len(restored)} board-target pairs from {ERASURES.name}", flush=True)
    return restored


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

    found = _restore(sample)
    if found is None:
        found = []
        for number, loaded in enumerate(sample, start=1):
            for target in targets:
                reached = reach(loaded, target)
                if reached is not None:
                    found.append(reached)
            if number % 10 == 0:
                print(f"  {number}/{len(sample)} erased, {len(found)} board-target pairs so far", flush=True)
        # ⚠️ **Written here, before selection, verification or rendering.** Everything below can fail;
        # none of it should cost the erasures.
        _save(sample, found)
        print(f"wrote {len(found)} board-target pairs to {ERASURES.name} before formatting anything")
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
    report_certification(found, chosen, targets)
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
