"""Generate the measuring instrument: one self-contained HTML page with real boards in it.

This is not the product and none of it goes to `serve/`. Its only job is to answer how many data
rows fit on a real phone once everything that costs vertical space is present — pinned header,
pinned totals, line score, footnote line, and the custom keypad that section 9 requires and that
eats most of the budget.

Real values from real directions, because section 6 says to prototype in a browser rather than in
Figma precisely so that real numbers get their real widths. Boards are chosen to include the wide
case (double digits in several columns), a live footnote, and a ten-batter roster.

Read-only against DGL. Run from `forge/`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bootstrap import bootstrap, require

bootstrap()

import json
import sys
from pathlib import Path

from measure import Loaded, load

from boxscore_forge.identities import find_violations
from boxscore_package.innings import Innings, to_display

BATTING = (
    ("plate_appearances", "PA"),
    ("at_bats", "AB"),
    ("runs", "R"),
    ("hits", "H"),
    ("walks", "BB"),
    ("strikeouts", "K"),
)
PITCHING = (("outs", "IP"), ("hits", "H"), ("runs", "R"), ("earned_runs", "ER"), ("walks", "BB"), ("strikeouts", "K"))
FOOTNOTES = (
    ("hit_by_pitch", "HBP"),
    ("sacrifice_flies", "SF"),
    ("sacrifice_hits", "SH"),
    ("catcher_interference", "CI"),
)

# Real surnames from the register, chosen to span the measured length distribution: 98.7% of
# batter appearances have a surname of ten characters or fewer, and these include the tail.
SAMPLE_NAMES = ["Aparicio", "Yastrzemski", "Robinson", "Schoendienst", "Mazeroski", "Kaline"]


def double_digit_columns(loaded: Loaded) -> int:
    """How many columns carry a two-digit value somewhere. The wide case is about breadth, not one
    freak number: a board where several columns are wide is what tests the width budget."""
    wide = 0
    for index, _ in enumerate(BATTING):
        column = [row[index] for row in ([getattr(line, f) for f, _ in BATTING] for line in loaded.direction.batting)]
        column.append([getattr(loaded.direction.batting_totals, f) for f, _ in BATTING][index])
        if any(value >= 10 for value in column):
            wide += 1
    return wide


def to_json(loaded: Loaded, note: str) -> dict[str, object]:
    direction = loaded.direction
    score = direction.line_score
    return {
        "id": loaded.game_id,
        "season": loaded.season,
        "note": note,
        "labels": list(loaded.labels),
        "offenseIsHome": loaded.offense_is_home,
        "batting": [[getattr(line, field) for field, _ in BATTING] for line in direction.batting],
        "battingTotals": [getattr(direction.batting_totals, field) for field, _ in BATTING],
        "pitching": [
            # ⚠️ The shared conversion, in the board's notation, because this page is a prototype
            # OF THE BOARD. Its own copy of the formula printed `4.0` where the board prints `4`,
            # so the prototype was judged on a notation the product does not use.
            [
                to_display(line.outs, Innings.BOARD),
                line.hits,
                line.runs,
                line.earned_runs,
                line.walks,
                line.strikeouts,
            ]
            for line in direction.pitching
        ],
        "pitchingTotals": [
            to_display(direction.pitching_totals.outs, Innings.BOARD),
            direction.pitching_totals.hits,
            direction.pitching_totals.runs,
            direction.pitching_totals.earned_runs,
            direction.pitching_totals.walks,
            direction.pitching_totals.strikeouts,
        ],
        "lineScore": {
            "offense": list(score.offense_by_inning),
            "defense": list(score.defense_by_inning),
            "offenseRHE": [score.offense_runs, score.offense_hits, score.offense_errors],
            "defenseRHE": [score.defense_runs, score.defense_hits, score.defense_errors],
        },
        "footnotes": [
            f"{short}: {', '.join(loaded.labels[i] for i, f in enumerate(direction.batter_footnotes) if getattr(f, field))}"
            for field, short in FOOTNOTES
            if getattr(direction.footnote_totals, field)
        ]
        + [f"LOB: {direction.team_footnotes.left_on_base}"],
        "pitcherLabels": list(loaded.pitcher_labels),
        # One composed name, from the loader. The pair this used to split was joined here without
        # the strip or the fallback the reference writer applied to the same data.
        "names": list(loaded.names),
        "revealed": dict(enumerate(loaded.names)),
    }


def main() -> None:
    # ⚠️ `gated=True` states what this call has always received (v36-P2-20). The flag did nothing
    # until 2026-08-21, so omitting it never meant ungated; naming it keeps this figure reproducible.
    pool = [item for item in load(20, gated=True) if not find_violations(item.direction)]
    taken: set[str] = set()

    def claim(candidates: list[Loaded], note: str) -> tuple[Loaded, str] | None:
        for item in candidates:
            key = f"{item.game_id}|{item.labels}"
            if key not in taken:
                taken.add(key)
                return item, note
        return None

    has_footnote = [
        item
        for item in pool
        if any(
            f.hit_by_pitch or f.sacrifice_flies or f.sacrifice_hits or f.catcher_interference
            for f in item.direction.batter_footnotes
        )
    ]
    require(pool, 1, "the board prototype", "roster caps, identities balanced")
    widest = sorted(pool, key=double_digit_columns, reverse=True)
    ten = [item for item in pool if len(item.direction.batting) == 10]
    three_pitchers = [item for item in pool if len(item.direction.pitching) == 3]

    wanted = [
        (widest, f"widest — {double_digit_columns(widest[0])} of 6 columns carry a two-digit value"),
        (ten, "ten batters, the tallest roster the caps allow"),
        (has_footnote, "carries a live footnote"),
        (three_pitchers, "three pitching rows, the tallest pitching half"),
    ]
    chosen = [claimed for candidates, note in wanted if (claimed := claim(candidates, note))]
    boards = [to_json(item, note) for item, note in chosen]

    # ⚠️ **Beside the script, not wherever the operator was standing.** (v36-P3-03) This defaulted
    # to `.`, so the artefacts landed in the caller's working directory — and this project's rule
    # is *reproducible from the script alone, no reliance on the caller's working directory*. Both
    # of these use `bootstrap()` for imports and then undercut it for output. `argv[1]` still
    # overrides, which is what the argument is for.
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
    template = (out / "template.html").read_text(encoding="utf-8")
    # ⚠️⚠️ **`</` is escaped, because the injection point is inside a `<script>` block.** (v36-P3-33)
    # The template's runtime rendering escapes properly, but that runs *after* the browser has parsed
    # the element — and `json.dumps` does not escape `/`, so a string holding `</script>` closes the
    # block before any of the page's own escaping exists. The values are player names from
    # `dbo.retroMaster`; no Retrosheet surname does this, and the fix removes the assumption rather
    # than resting on it.
    payload = json.dumps(boards, indent=1).replace("</", "<\\/")
    (out / "board.html").write_text(template.replace("/*BOARDS*/", payload), encoding="utf-8")
    for board in boards:
        print(f"  {board['id']} {board['season']}: {board['note']}, {len(board['labels'])} batting rows")
    print(f"wrote {out / 'board.html'}")


if __name__ == "__main__":
    main()
