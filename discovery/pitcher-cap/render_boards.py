"""Boards to look at, because two of the open questions cannot be settled by a correlation.

**Does a four-pitcher board read as noise?** Every metric says the extra rows earn their place — the
pitching section goes from 24% to 29% of the solution path and trivial steps fall. None of that
speaks to whether four pitching rows of two or three visible cells each *look* like clutter. That is
a judgement, and the only way to make it is to see the board.

**Is a high resolution p90 good or bad?** Resolution counts how many known numbers a step combines.
More of them may be depth or may be tedium, and the direction has never been decided. Two boards at
the same chain length, one with a high resolution and one with a low one, put the question where it
can be answered.

Boards are erased by the real algorithm at the real settings, so what is rendered is what a player
would meet. Read-only against DGL. Run from `forge/`.
"""

import json
import statistics
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "discovery" / "board-prototype"))

from build import to_json  # noqa: E402
from measure import Loaded, load  # noqa: E402

from boxscore_forge.erasure import Puzzle, erase  # noqa: E402
from boxscore_forge.identities import BATTING_COLUMNS, PITCHING_COLUMNS, find_violations  # noqa: E402

TARGET_CHAIN = 11
SEED = 7


def blanks(puzzle: Puzzle, loaded: Loaded) -> dict[str, object]:
    """Turn erased cell names into the column indices the renderer draws."""
    batting = [
        [index for index, column in enumerate(BATTING_COLUMNS) if f"batting[{row}].{column}" in puzzle.erased]
        for row in range(len(loaded.direction.batting))
    ]
    pitching = [
        [index for index, column in enumerate(PITCHING_COLUMNS) if f"pitching[{row}].{column}" in puzzle.erased]
        for row in range(len(loaded.direction.pitching))
    ]
    return {
        "batting": batting,
        "pitching": pitching,
        "battingTotals": [
            index for index, column in enumerate(BATTING_COLUMNS) if f"batting_totals.{column}" in puzzle.erased
        ],
        "pitchingTotals": [
            index for index, column in enumerate(PITCHING_COLUMNS) if f"pitching_totals.{column}" in puzzle.erased
        ],
    }


def render(loaded: Loaded, puzzle: Puzzle, note: str) -> dict[str, object]:
    board = to_json(loaded, note)
    board["blanks"] = blanks(puzzle, loaded)
    return board


def main() -> None:
    pool = [item for item in load(4, gated=True, max_batters=13, max_pitchers=4) if not find_violations(item.direction)]
    solved: list[tuple[Loaded, Puzzle]] = []
    for loaded in pool:
        puzzle = erase(loaded.direction, target_chain=TARGET_CHAIN, seed=SEED)
        if puzzle is not None:
            solved.append((loaded, puzzle))
    print(f"{len(solved)} of {len(pool)} directions reached a chain of {TARGET_CHAIN}")

    by_pitchers: dict[int, list[tuple[Loaded, Puzzle]]] = {}
    for loaded, puzzle in solved:
        by_pitchers.setdefault(len(loaded.direction.pitching), []).append((loaded, puzzle))

    boards: list[dict[str, object]] = []

    # The clutter question. Four pitching rows against two, same chain, same algorithm.
    for count in (4, 2):
        wanted = 3 if count == 4 else 1
        for loaded, puzzle in by_pitchers.get(count, [])[:wanted]:
            visible = sum(
                1
                for row in range(len(loaded.direction.pitching))
                for column in PITCHING_COLUMNS
                if f"pitching[{row}].{column}" not in puzzle.erased
            )
            boards.append(
                render(
                    loaded,
                    puzzle,
                    f"{count} pitching rows — {visible} of {count * 6} pitching cells left visible, "
                    f"chain {puzzle.solution.chain_length}",
                )
            )

    # The resolution question. Same chain, opposite ends of the resolution distribution.
    with_resolution = [
        (loaded, puzzle)
        for loaded, puzzle in solved
        if puzzle.solution.ninetieth_percentile_resolution is not None
    ]
    with_resolution.sort(key=lambda pair: pair[1].solution.ninetieth_percentile_resolution or 0)
    if len(with_resolution) >= 2:
        resolutions = [pair[1].solution.ninetieth_percentile_resolution or 0 for pair in with_resolution]
        print(f"resolution p90 across the sample: {min(resolutions)} to {max(resolutions)}, "
              f"median {statistics.median(resolutions):.0f}")
        low_loaded, low_puzzle = with_resolution[0]
        high_loaded, high_puzzle = with_resolution[-1]
        boards.append(
            render(
                low_loaded,
                low_puzzle,
                f"LOW resolution — p90 of {low_puzzle.solution.ninetieth_percentile_resolution}, "
                f"chain {low_puzzle.solution.chain_length}: few numbers per step",
            )
        )
        boards.append(
            render(
                high_loaded,
                high_puzzle,
                f"HIGH resolution — p90 of {high_puzzle.solution.ninetieth_percentile_resolution}, "
                f"chain {high_puzzle.solution.chain_length}: many numbers combined per step",
            )
        )

    out = Path(__file__).resolve().parent
    template = (_ROOT / "discovery" / "board-prototype" / "template.html").read_text(encoding="utf-8")
    (out / "boards.html").write_text(template.replace("/*BOARDS*/", json.dumps(boards, indent=1)), encoding="utf-8")
    for board in boards:
        print(f"  {board['season']}: {board['note']}")
    print(f"wrote {out / 'boards.html'}")


if __name__ == "__main__":
    main()
