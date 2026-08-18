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


STYLE = """
/* Deliberately dumb. The prototype's page is a full-viewport flex column with a scroll container,
   sticky heads and a pinned anchor row, and it renders twice in at least one real browser — which
   makes it useless for judging what a board looks like. Nothing here depends on viewport height,
   overflow or stickiness: the boards are blocks in normal document flow, at the phone width they
   are meant to be seen at, one after another down the page. */
body { font: 13px/1.1 -apple-system, "Segoe UI", system-ui, sans-serif; background: #fafafa;
       color: #111; margin: 0; padding: 16px; }
h1 { font-size: 15px; margin: 0 0 4px; }
p.intro { font-size: 12px; color: #444; margin: 0 0 20px; max-width: 640px; }
section { width: 375px; margin: 0 0 28px; background: #fff; border: 1px solid #bbb; }
h2 { font-size: 12px; font-weight: 700; padding: 6px 8px; margin: 0; background: #333; color: #fff; }
p.note { font-size: 11px; color: #444; padding: 5px 8px; margin: 0; border-bottom: 1px solid #ddd; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; }
table.line td, table.line th { border: 1px solid #ddd; height: 16px; font-size: 9px;
                               text-align: center; padding: 0 1px; }
table.line th.side, table.line td.side { width: 38px; text-align: left; font-weight: 700; padding-left: 4px; }
table.line .summary { border-left: 2px solid #999; }
table.line tr.ours { background: #eef4ff; }
div.foot { font-size: 11px; padding: 3px 6px; border-bottom: 1px solid #ccc; }
table.grid th, table.grid td { text-align: center; vertical-align: middle; border: 1px solid #ccc;
                               font-variant-numeric: tabular-nums; padding: 0; }
table.grid th.label, table.grid td.label { text-align: left; width: 66px; padding-left: 4px;
                                           font-size: 11px; overflow: hidden; white-space: nowrap; }
table.grid td.cell, table.grid th.col { width: calc((100% - 66px) / 6); }
table.grid td.cell { height: 44px; font-size: 15px; }
table.grid td.blank { background: #f4f4f4; }
table.grid thead th { background: #ddd; height: 22px; font-size: 11px; }
table.grid tr.section td { background: #333; color: #fff; font-size: 10px; text-align: left;
                           padding-left: 4px; height: 16px; letter-spacing: .05em; }
table.grid tr.totals td { background: #ddd; font-weight: 700; height: 34px; }
"""


def _cells(values: list[object], blank: list[int]) -> str:
    return "".join(
        f"<td class='cell{' blank' if index in blank else ''}'>{'' if index in blank else value}</td>"
        for index, value in enumerate(values)
    )


def _board_html(board: dict[str, object]) -> str:
    score = board["lineScore"]  # type: ignore[index]
    innings = max(len(score["offense"]), len(score["defense"]))  # type: ignore[index,call-overload]
    head = (
        "<tr><th class='side'></th>"
        + "".join(f"<th>{index + 1}</th>" for index in range(innings))
        + "<th class='summary'>R</th><th>H</th><th>E</th></tr>"
    )
    ours = board["offenseIsHome"]
    rows = ""
    for side, by_inning, rhe, is_ours in (
        ("AWAY", score["defense"] if ours else score["offense"], score["defenseRHE"] if ours else score["offenseRHE"], not ours),  # type: ignore[index]
        ("HOME", score["offense"] if ours else score["defense"], score["offenseRHE"] if ours else score["defenseRHE"], ours),  # type: ignore[index]
    ):
        cells = "".join(
            f"<td>{by_inning[index] if index < len(by_inning) else 'x'}</td>"  # type: ignore[index]
            for index in range(innings)
        )
        summary = "".join(
            f"<td class='{'summary' if position == 0 else ''}'><b>{value}</b></td>"
            for position, value in enumerate(rhe)  # type: ignore[arg-type]
        )
        rows += f"<tr class='{'ours' if is_ours else ''}'><td class='side'>{side}</td>{cells}{summary}</tr>"

    blanks = board["blanks"]  # type: ignore[index]
    grid = "<thead><tr><th class='label'></th>" + "".join(
        f"<th class='col'>{name}</th>" for name in ("PA", "AB", "R", "H", "BB", "K")
    ) + "</tr></thead><tbody><tr class='section'><td colspan='7'>BATTING</td></tr>"
    for index, row in enumerate(board["batting"]):  # type: ignore[arg-type]
        label = board["labels"][index]  # type: ignore[index]
        grid += f"<tr><th class='label'>{label}</th>{_cells(row, blanks['batting'][index])}</tr>"  # type: ignore[index]
    grid += (
        "<tr class='totals'><td class='label'>TOTALS</td>"
        + _cells(board["battingTotals"], blanks["battingTotals"])  # type: ignore[arg-type,index]
        + "</tr><tr class='section'><td colspan='7'>PITCHING</td></tr>"
        + "<tr><th class='label'></th>"
        + "".join(f"<th class='col'>{name}</th>" for name in ("IP", "H", "R", "ER", "BB", "K"))
        + "</tr>"
    )
    for index, row in enumerate(board["pitching"]):  # type: ignore[arg-type]
        # SP and RP-n, never a bare P — the pitcher who batted is already a `P` row in the batting
        # section above, and the same label meaning two things in two sections is worse than none.
        label = board["pitcherLabels"][index] if board.get("pitcherLabels") else f"P{index + 1}"  # type: ignore[index,union-attr]
        grid += f"<tr><th class='label'>{label}</th>{_cells(row, blanks['pitching'][index])}</tr>"  # type: ignore[index]
    grid += (
        "<tr class='totals'><td class='label'>TOTALS</td>"
        + _cells(board["pitchingTotals"], blanks["pitchingTotals"])  # type: ignore[arg-type,index]
        + "</tr></tbody>"
    )

    footnotes = "; ".join(board["footnotes"])  # type: ignore[arg-type]
    return (
        f"<section><h2>{board['season']}</h2><p class='note'>{board['note']}</p>"
        f"<table class='line'>{head}{rows}</table><div class='foot'>{footnotes}</div>"
        f"<table class='grid'>{grid}</table></section>"
    )


def page(boards: list[dict[str, object]]) -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<title>Four pitching rows, and high against low resolution</title>"
        f"<style>{STYLE}</style></head><body>"
        "<h1>Boards to look at</h1>"
        "<p class='intro'>Erased by the real algorithm at a chain target of 11, ordering "
        "<code>row_first</code>, drawn at the 375px width the board is designed for. Shaded cells "
        "are the blanks the player fills. Two questions: whether four pitching rows read as noise "
        "beside two, and whether a high resolution p90 is depth or arithmetic.</p>"
        + "".join(_board_html(board) for board in boards)
        + "</body></html>"
    )


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
        # One per decade at most. The first version of this took the first three and drew three
        # boards from the same 1954 season, which judges a decade rather than a pitching section.
        spread: list[tuple[Loaded, Puzzle]] = []
        seen_decades: set[int] = set()
        for candidate in by_pitchers.get(count, []):
            decade = (candidate[0].season // 10) * 10
            if decade not in seen_decades:
                seen_decades.add(decade)
                spread.append(candidate)
        for loaded, puzzle in spread[:wanted]:
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
    (out / "boards.html").write_text(page(boards), encoding="utf-8")
    for board in boards:
        print(f"  {board['season']}: {board['note']}")
    print(f"wrote {out / 'boards.html'}")


if __name__ == "__main__":
    main()
