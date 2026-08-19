"""Six real puzzles as a player would meet them, printed as plain text.

Every measurement so far describes boards without anyone having looked at one. This prints them:
the puzzle with its blanks, the boxscore it came from, and the solution path step by step with how
much choice the player had at each turn.

If the puzzle is not worth playing, none of the metrics matter.

Boards are chosen deliberately rather than sampled: two easy, two mid, one erased all the way to its
compressibility ceiling, and one zero-heavy board that compresses far — the shape the measurements
say scores well and may well be boring. That last one is the interesting one.

Read-only against DGL. Run from `forge/`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bootstrap import bootstrap, require  # noqa: E402

bootstrap()

import random
import sys
from pathlib import Path

from measure import Loaded, load

from boxscore_forge.constraints import cell_values, shape_of
from boxscore_forge.erasure import erasable
from boxscore_forge.errors import ContradictionError
from boxscore_forge.identities import find_violations
from boxscore_forge.solver import Solution, Technique, solve

BATTING_HEADERS = (("plate_appearances", "PA"), ("at_bats", "AB"), ("runs", "R"), ("hits", "H"), ("walks", "BB"), ("strikeouts", "SO"))
PITCHING_HEADERS = (("outs", "IP"), ("hits", "H"), ("runs", "R"), ("earned_runs", "ER"), ("walks", "BB"), ("strikeouts", "SO"))
FOOTNOTE_LABELS = (("hit_by_pitch", "HBP"), ("sacrifice_flies", "SF"), ("sacrifice_hits", "SH"), ("catcher_interference", "CI"))
BLANK = "  ·"
SEED = 20260819

# Boards with more nought than this leave the pool. Not chosen for being near the measured median —
# a median has no properties, it is only where the sample fell. Chosen because between 30% and 35%
# the boards passing through have a median of three runs, and because 30% still leaves 21 years of
# calendar against a requirement of five months of forward inventory. With that much slack a generous
# threshold buys nothing and a strict one costs almost nothing.
GATE = 0.30


def _innings(outs: int) -> str:
    return f"{outs // 3}.{outs % 3}"


def _cell(values: dict[str, int], key: str, *, as_innings: bool = False) -> str:
    if key not in values:
        return BLANK
    return f"{_innings(values[key]):>3}" if as_innings else f"{values[key]:>3}"


def render(loaded: Loaded, given: dict[str, int], *, title: str) -> str:
    """The board exactly as the player sees it. Blanks are the cells they have to work out."""
    direction = loaded.direction
    score = direction.line_score
    lines = [f"  {title}", f"  {loaded.game_id}   {loaded.season}", ""]

    # The two sides need not be the same length — a home team already ahead does not bat in the
    # ninth — so the header spans whichever ran longer.
    width = max(len(score.offense_by_inning), len(score.defense_by_inning))
    header = "".join(f"{n:>3}" for n in range(1, width + 1))
    lines.append(f"  {'':<10}{header}  |{'R':>4}{'H':>4}{'E':>4}")
    for label, innings, runs, hits, errors in (
        ("OFFENSE", score.offense_by_inning, score.offense_runs, score.offense_hits, score.offense_errors),
        ("DEFENSE", score.defense_by_inning, score.defense_runs, score.defense_hits, score.defense_errors),
    ):
        padded = "".join(f"{r:>3}" for r in innings) + "  x" * (width - len(innings))
        lines.append(f"  {label:<10}{padded}  |{runs:>4}{hits:>4}{errors:>4}")
    lines.append("")

    lines.append(f"  {'BATTING':<10}" + "".join(f"{short:>4}" for _, short in BATTING_HEADERS))
    for index, label in enumerate(loaded.labels):
        row = "".join(f" {_cell(given, f'batting[{index}].{field}')}" for field, _ in BATTING_HEADERS)
        lines.append(f"  {label:<10}{row}")
    totals = "".join(f" {_cell(given, f'batting_totals.{field}')}" for field, _ in BATTING_HEADERS)
    lines.append(f"  {'-' * 34}")
    lines.append(f"  {'TOTALS':<10}{totals}")
    lines.append("")

    lines.append(f"  {'PITCHING':<10}" + "".join(f"{short:>4}" for _, short in PITCHING_HEADERS))
    for index in range(len(direction.pitching)):
        row = "".join(
            f" {_cell(given, f'pitching[{index}].{field}', as_innings=field == 'outs')}"
            for field, _ in PITCHING_HEADERS
        )
        lines.append(f"  {'P' + str(index + 1):<10}{row}")
    totals = "".join(
        f" {_cell(given, f'pitching_totals.{field}', as_innings=field == 'outs')}" for field, _ in PITCHING_HEADERS
    )
    lines.append(f"  {'-' * 34}")
    lines.append(f"  {'TOTALS':<10}{totals}")
    lines.append("")

    notes = [
        f"{short}: {', '.join(loaded.labels[i] for i, f in enumerate(direction.batter_footnotes) if getattr(f, field))}"
        for field, short in FOOTNOTE_LABELS
        if getattr(direction.footnote_totals, field)
    ]
    notes.append(f"LOB: {direction.team_footnotes.left_on_base}")
    lines.append("  " + "     ".join(notes))
    return "\n".join(lines)


def render_path(solution: Solution) -> str:
    """Every deduction in order, with how much choice there was and what it cost to find."""
    lines = [
        "  SOLUTION PATH",
        f"  {'#':>3} {'cell':<34}{'=':>4}  {'from':<22}{'ready':>6}{'live':>6}{'find':>7}{'add':>5}  note",
    ]
    for number, step in enumerate(solution.deductions, start=1):
        origin = str(step.from_identity) if step.from_identity else "bounding"
        note = "trivial" if step.is_trivial else ""
        if step.technique == Technique.BOUNDING:
            note = (note + " bounded").strip()
        search = f"{step.search_cost:>7.2f}" if step.search_cost is not None else f"{'-':>7}"
        resolution = f"{step.resolution_cost:>5}" if step.resolution_cost is not None else f"{'-':>5}"
        lines.append(
            f"  {number:>3} {step.cell:<34}{step.value:>4}  {origin:<22}"
            f"{step.equations_solvable:>6}{step.equations_live:>6}{search}{resolution}  {note}"
        )
    lines.append("")
    lines.append(
        f"  chain {solution.chain_length}   hardest to find {solution.hardest_search or 0:.2f}   "
        f"most additions (p90) {solution.ninetieth_percentile_resolution or 0}   "
        f"trivial {solution.trivial_share or 0:.0%}   "
        f"families {', '.join(sorted(f.value for f in solution.families_used))}"
    )
    return "\n".join(lines)


def erase_to_chain(loaded: Loaded, target: int, rng: random.Random) -> tuple[dict[str, int], Solution]:
    """Erase greedily until the solve is `target` steps deep, which is the difficulty control.

    This is a sketch of the erasure algorithm, not the algorithm: order is random, and it stops at
    the first pattern reaching the target rather than looking for a good one.
    """
    shape = shape_of(loaded.direction)
    values = cell_values(loaded.direction)
    order = erasable(loaded.direction)
    rng.shuffle(order)

    erased: set[str] = set()
    best = solve(shape, values)
    for cell in order:
        trial = erased | {cell}
        puzzle = {k: v for k, v in values.items() if k not in trial}
        try:
            solution = solve(shape, puzzle)
        except ContradictionError:
            continue
        if not solution.is_complete:
            continue
        erased, best = trial, solution
        if best.chain_length >= target:
            break
    return {k: v for k, v in values.items() if k not in erased}, best


def zero_density(loaded: Loaded) -> float:
    values = cell_values(loaded.direction)
    grid = [values[cell] for cell in erasable(loaded.direction)]
    return sum(1 for value in grid if value == 0) / len(grid)


def main() -> None:
    rng = random.Random(SEED)
    everything = [item for item in load(6) if not find_violations(item.direction)]

    # The gate, applied.
    pool = sorted((item for item in everything if zero_density(item) < GATE), key=lambda item: item.game_id)
    print(f"{len(everything)} directions, {len(pool)} below {GATE:.0%} zero density")

    picks = [
        ("EASY — a handful of blanks, every one a single subtraction", pool[0], 3),
        ("EASY — slightly longer, still nothing to hunt for", pool[1], 5),
        ("MID — the row identity starts carrying weight", pool[2], 10),
        ("MID — longer, and the pitching cross opens it", pool[3], 12),
        ("HARD — twenty steps deep, where the global identity turns up", pool[4], 20),
        ("HARD — the same depth on a different game", pool[5], 20),
    ]

    out = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    solved_text: list[str] = []
    for title, loaded, target in picks:
        given, solution = erase_to_chain(loaded, target, rng)
        blanks = len(erasable(loaded.direction)) - sum(
            1 for cell in erasable(loaded.direction) if cell in given
        )
        block = [
            "=" * 78,
            render(loaded, given, title=f"{title}   [{blanks} blanks]"),
            "",
            "  " + "-" * 74,
            "",
            render(loaded, cell_values(loaded.direction), title="THE ANSWER"),
            "",
            "  " + "-" * 74,
            "",
            render_path(solution),
            "",
        ]
        solved_text.append("\n".join(block))

    (out / "sample-boards.txt").write_text("\n".join(solved_text), encoding="utf-8")

    # One to solve by hand, with nothing after it to spoil the answer.
    # Seventh board of the pool, so the sample has to have one. Saying which filters emptied it
    # is the difference between a decision tool and an IndexError.
    require(pool, 7, "the operator's unanswered board", "gated pool, identities balanced")
    puzzle_only, _ = erase_to_chain(pool[6], 12, random.Random(SEED + 7))
    (out / "solve-this-one.txt").write_text(
        "\n".join(
            [
                render(pool[6], puzzle_only, title="FOR THE OPERATOR — no answer in this file"),
                "",
                "  Every blank is deducible without guessing. Column totals rule, each batter's",
                "  row satisfies PA = AB + BB + HBP + SF + SH + CI, the offense's H/R/BB/K equal",
                "  what the pitchers are charged with, and PA = Outs + R + LOB for the team.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"wrote {out / 'sample-boards.txt'} and {out / 'solve-this-one.txt'}")


if __name__ == "__main__":
    main()