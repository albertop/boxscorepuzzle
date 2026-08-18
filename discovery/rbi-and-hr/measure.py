"""What RBI and home runs would add to the board, measured one column at a time.

§6 records a canonical batting order of `PA, AB, R, H, HR, RBI, BB, SO` as decided and deliberately
unbuilt. Two of those eight are not on the board today, and they do not bring the same things:

  RBI   no cross-team counterpart and no place in the row identity. It brings one column sum and
        nothing else. It is the column PA displaced (§6), so this measures what that cost.
  HR    an offense's home runs are the same events the opposing pitchers are charged with, so it
        brings a **fifth cross-team equation** — the only candidate that adds a link rather than a
        column. It also brings two bounds: `H >= HR` and, if RBI is present, `RBI >= HR`.

**The identities are not in question.** They hold across all 407,816 directions in the database: the
home-run cross balances in 100.00% of them in every decade from the 1910s to the 2020s, RBI is never
null, and neither bound is ever violated. What is in question is what they do to a *puzzle*.

**Where each one belongs is not an open question — a printed boxscore already answers it.** RBI is a
column of the batting line. Home runs are not: they are published on the footnote line, with the
doubles, triples, hit batsmen and sacrifices, attributed per batter. §6 already builds the footnote
line that way and says so. The canonical order recorded in §6, `PA, AB, R, H, HR, RBI, BB, SO`, puts
home runs somewhere a printed boxscore does not, which is why both placements are measured here rather
than only the column.

The pool corroborates the convention without being the reason for it:

  share of cells that are zero, per batter row, by decade
    PA 0%   AB 2%   R 63-70%   H 39-47%   BB 73-76%   SO 41-77%   RBI 70-77%   HR 89-98%

RBI sits in the same band as the columns already on the board. Home runs sit with the footnote terms,
which are zero on roughly nine rows in ten (§6). §5 rejects boards on zero density, so a column that is
92% noughts is a measured cost against the gate; a cross-team link is a measured gain in the solution
path. **What each placement is worth net is what this script exists to find out.**

**Every configuration solves the same boards.** The gate is applied once, on the six columns that
exist today, so the difference between configurations is the columns and nothing else. What the gate
would cost if it were recomputed over a wider board is reported separately, because mixing the two
would answer neither question.

⚠️ **The instrument is the production constraint system with its column tuples swapped**, not a second
copy of it — one predicate, one place. That makes a patch that fails to take effect the dangerous
outcome: every configuration would score alike and the honest conclusion would look like a measured
null. `_assert_the_instrument_changed` therefore checks the built system term by term, and raises.

Read-only against DGL. Run from `forge/`.
"""

import random
import statistics
import sys
from collections import Counter
from dataclasses import dataclass, replace
from functools import cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "discovery" / "pitcher-cap"))

from measure import Loaded, load  # noqa: E402

from boxscore_forge import bounds, erasure, publish, solver  # noqa: E402
from boxscore_forge import constraints as C  # noqa: E402
from boxscore_forge import identities as I  # noqa: E402
from boxscore_forge.boxscore import Direction, TeamFootnotes  # noqa: E402
from boxscore_forge.identities import Identity  # noqa: E402
from boxscore_forge.solver import Solution, Technique  # noqa: E402

SAMPLE_PER_DECADE = 3
GATE = 0.25
SEED = 20260818
TARGETS = tuple(range(4, 16))
RENDERED = 4

PHONE_WIDTH = 375
PAGE_MARGINS = 16
LABEL_COLUMN = 66
MINIMUM_TOUCH_TARGET = 44
"""§6's screen budget, restated so the width cost of a column is arithmetic rather than an opinion.

A cell narrower than the minimum touch target is not a tighter board, it is a board a thumb cannot
use. The renderer divides its table by a fixed six, so what a wide board looks like on the page is a
rendering artefact and this is the number that decides.
"""

BASE_BATTING = ("plate_appearances", "at_bats", "runs", "hits", "walks", "strikeouts")
BASE_PITCHING = ("outs", "hits", "runs", "earned_runs", "walks", "strikeouts")
BASE_FOOTNOTES = ("hit_by_pitch", "sacrifice_flies", "sacrifice_hits", "catcher_interference")
BASE_CROSS = ("hits", "runs", "walks", "strikeouts")

_PRISTINE_EQUATIONS = C.equations
_PRISTINE_INEQUALITIES = C.inequalities
_PATCHED_MODULES = (I, C, erasure, publish, bounds, solver)


@dataclass(frozen=True, slots=True)
class WideBattingLine:
    """Every candidate column at once. Which of them exist is the configuration's business."""

    plate_appearances: int
    at_bats: int
    runs: int
    hits: int
    walks: int
    strikeouts: int
    runs_batted_in: int
    home_runs: int


@dataclass(frozen=True, slots=True)
class WideFootnotes:
    hit_by_pitch: int
    sacrifice_flies: int
    sacrifice_hits: int
    catcher_interference: int
    home_runs: int


@dataclass(frozen=True, slots=True)
class WidePitchingLine:
    outs: int
    hits: int
    runs: int
    earned_runs: int
    walks: int
    strikeouts: int
    home_runs: int


@dataclass(frozen=True, slots=True)
class Variant:
    """One board configuration: which columns exist, and where home runs live if they do.

    `home_runs_in` is why this is a dataclass rather than four tuples. A home-run column and a
    home-run footnote carry the same identities at different widths, and the comparison between them
    is one of the things being measured rather than something settled in advance.
    """

    name: str
    batting: tuple[str, ...] = BASE_BATTING
    pitching: tuple[str, ...] = BASE_PITCHING
    footnotes: tuple[str, ...] = BASE_FOOTNOTES
    cross_team: tuple[str, ...] = BASE_CROSS
    home_runs_in: str = ""

    @property
    def has_home_runs(self) -> bool:
        return bool(self.home_runs_in)

    def home_run_cell(self, index: int) -> str:
        if self.home_runs_in == "column":
            return C.batting_cell(index, "home_runs")
        return C.footnote_cell(index, "home_runs")

    def home_run_total(self) -> str:
        if self.home_runs_in == "column":
            return C.batting_total_cell("home_runs")
        return C.footnote_total_cell("home_runs")


VARIANTS = (
    Variant("base - six columns"),
    Variant("+RBI column", batting=(*BASE_BATTING, "runs_batted_in")),
    Variant(
        "+HR column",
        batting=(*BASE_BATTING, "home_runs"),
        pitching=(*BASE_PITCHING, "home_runs"),
        cross_team=(*BASE_CROSS, "home_runs"),
        home_runs_in="column",
    ),
    Variant(
        "+HR footnote",
        pitching=(*BASE_PITCHING, "home_runs"),
        footnotes=(*BASE_FOOTNOTES, "home_runs"),
        home_runs_in="footnote",
    ),
    Variant(
        "+RBI column +HR footnote (as printed)",
        batting=(*BASE_BATTING, "runs_batted_in"),
        pitching=(*BASE_PITCHING, "home_runs"),
        footnotes=(*BASE_FOOTNOTES, "home_runs"),
        home_runs_in="footnote",
    ),
    Variant(
        "+RBI +HR columns (the section 6 order)",
        batting=(*BASE_BATTING, "home_runs", "runs_batted_in"),
        pitching=(*BASE_PITCHING, "home_runs"),
        cross_team=(*BASE_CROSS, "home_runs"),
        home_runs_in="column",
    ),
)


def configure(variant: Variant) -> None:
    """Swap the column tuples in every module that imported them, and rebuild the system.

    `from x import Y` binds Y in the importing module's own globals, so setting it on one module is
    not setting it everywhere. Each name is written to every module that has it, and a module that
    does not is skipped rather than guessed at.
    """
    for module in _PATCHED_MODULES:
        for name, value in (
            ("BATTING_COLUMNS", variant.batting),
            ("PITCHING_COLUMNS", variant.pitching),
            ("FOOTNOTE_COLUMNS", variant.footnotes),
            ("CROSS_TEAM_COLUMNS", variant.cross_team),
        ):
            if hasattr(module, name):
                setattr(module, name, value)

    _PRISTINE_EQUATIONS.cache_clear()
    _PRISTINE_INEQUALITIES.cache_clear()

    @cache
    def variant_equations(shape: C.BoardShape) -> tuple[C.Equation, ...]:
        return (*_repair_row_identities(_PRISTINE_EQUATIONS(shape)), *_extra_equations(variant))

    @cache
    def variant_inequalities(shape: C.BoardShape) -> tuple[C.Inequality, ...]:
        return (*_PRISTINE_INEQUALITIES(shape), *_extra_bounds(variant, shape))

    for module in _PATCHED_MODULES:
        if hasattr(module, "equations"):
            module.equations = variant_equations
        if hasattr(module, "inequalities"):
            module.inequalities = variant_inequalities


def _repair_row_identities(system: tuple[C.Equation, ...]) -> tuple[C.Equation, ...]:
    """Take home runs back out of `PA = AB + BB + HBP + SF + SH + CI`.

    ⚠️ **The footnote block is not a drawer for sparse quantities; it is the row identity.** The
    production builder subtracts every footnote column from plate appearances, which is right for the
    four ways of reaching base without an at-bat and wrong for a home run, which *is* an at-bat.
    Putting home runs on the footnote line without this would make the identity false and every board
    would fail validation — loudly, but for the wrong reason.

    Done as a transform on the built system rather than by patching the private builder, so the result
    can be asserted term by term.
    """
    repaired = []
    for equation in system:
        if equation.origin is not Identity.ROW_PLATE_APPEARANCES:
            repaired.append(equation)
            continue
        terms = tuple(term for term in equation.terms if not term.cell.endswith(".home_runs"))
        repaired.append(replace(equation, terms=terms))
    return tuple(repaired)


def _extra_equations(variant: Variant) -> tuple[C.Equation, ...]:
    """The cross-team link a home-run footnote needs, which the column tuples cannot express.

    `_cross_team_equations` reads the offense's side off the *batting* totals, so a home-run column
    gets its cross for free and a home-run footnote does not. Same identity, different cell name.
    """
    if variant.home_runs_in != "footnote":
        return ()
    return (
        C.Equation(
            (C.Term(variant.home_run_total(), 1), C.Term(C.pitching_total_cell("home_runs"), -1)),
            0,
            Identity.CROSS_TEAM_TOTAL,
        ),
    )


def _extra_bounds(variant: Variant, shape: C.BoardShape) -> tuple[C.Inequality, ...]:
    """`H >= HR` and `RBI >= HR`, per batter and on the totals row.

    Both hold on every direction in the database. A home run is a hit, and it drives in at least the
    man who hit it.
    """
    if not variant.has_home_runs:
        return ()
    extra: list[C.Inequality] = []
    over = ["hits"] + (["runs_batted_in"] if "runs_batted_in" in variant.batting else [])
    for index in range(shape.batter_count):
        for column in over:
            extra.append(
                C.Inequality(
                    (C.Term(C.batting_cell(index, column), 1), C.Term(variant.home_run_cell(index), -1)),
                    Identity.HITS_WITHIN_AT_BATS,
                )
            )
    for column in over:
        extra.append(
            C.Inequality(
                (C.Term(C.batting_total_cell(column), 1), C.Term(variant.home_run_total(), -1)),
                Identity.HITS_WITHIN_AT_BATS,
            )
        )
    return tuple(extra)


def _assert_the_instrument_changed(variant: Variant, shape: C.BoardShape) -> dict[str, int]:
    """Prove the swap took effect, before a single board is solved.

    A patch that silently does not apply produces five identical configurations and a conclusion of
    "the columns change nothing" that looks measured and is an artefact. Every claim below is checked
    against the built system rather than against the intent.
    """
    system = C.equations(shape)
    rules = C.inequalities(shape)
    cells = C.all_cells(shape)

    for column in variant.batting:
        if C.batting_cell(0, column) not in cells:
            message = f"{variant.name}: batting column {column} is not in the board"
            raise AssertionError(message)
    for column in variant.footnotes:
        if C.footnote_cell(0, column) not in cells:
            message = f"{variant.name}: footnote column {column} is not in the board"
            raise AssertionError(message)

    # The row identity must carry exactly PA, AB, BB and the four true footnote terms, whatever else
    # the footnote block holds. This is the assertion that catches a home run being counted as a way
    # of reaching base without batting.
    for equation in [e for e in system if e.origin is Identity.ROW_PLATE_APPEARANCES]:
        named = {term.cell.rsplit(".", 1)[1] for term in equation.terms}
        if named != {"plate_appearances", "at_bats", "walks", *BASE_FOOTNOTES}:
            message = f"{variant.name}: the row identity carries {sorted(named)}"
            raise AssertionError(message)

    crosses = [e for e in system if e.origin is Identity.CROSS_TEAM_TOTAL]
    hr_crosses = [e for e in crosses if any(term.cell.endswith(".home_runs") for term in e.terms)]
    if len(hr_crosses) != int(variant.has_home_runs):
        message = f"{variant.name}: expected {int(variant.has_home_runs)} home-run crosses, built {len(hr_crosses)}"
        raise AssertionError(message)
    if hr_crosses:
        terms = {term.cell for term in hr_crosses[0].terms}
        if terms != {variant.home_run_total(), C.pitching_total_cell("home_runs")}:
            message = f"{variant.name}: the home-run cross links {sorted(terms)}"
            raise AssertionError(message)

    paired = 2
    hr_bounds = [
        r for r in rules if len(r.terms) == paired and any(t.cell.endswith(".home_runs") for t in r.terms)
    ]
    per_row = 0 if not variant.has_home_runs else (2 if "runs_batted_in" in variant.batting else 1)
    expected_bounds = per_row * (shape.batter_count + 1)
    if len(hr_bounds) != expected_bounds:
        message = f"{variant.name}: expected {expected_bounds} home-run bounds, built {len(hr_bounds)}"
        raise AssertionError(message)

    return {
        "cells": len(cells),
        "equations": len(system),
        "crosses": len(crosses),
        "inequalities": len(rules),
        "cycles": C.independent_cycles(shape),
    }


def board_of(loaded: Loaded, variant: Variant) -> Direction:
    """The wide board. Every candidate column is built; the configuration decides which are read."""
    del variant
    direction = loaded.direction
    batting = tuple(
        WideBattingLine(
            plate_appearances=line.plate_appearances,
            at_bats=line.at_bats,
            runs=line.runs,
            hits=line.hits,
            walks=line.walks,
            strikeouts=line.strikeouts,
            runs_batted_in=rbi,
            home_runs=home_runs,
        )
        for line, rbi, home_runs in zip(direction.batting, loaded.batter_rbi, loaded.batter_home_runs, strict=True)
    )
    footnotes = tuple(
        WideFootnotes(
            hit_by_pitch=note.hit_by_pitch,
            sacrifice_flies=note.sacrifice_flies,
            sacrifice_hits=note.sacrifice_hits,
            catcher_interference=note.catcher_interference,
            home_runs=home_runs,
        )
        for note, home_runs in zip(direction.batter_footnotes, loaded.batter_home_runs, strict=True)
    )
    pitching = tuple(
        WidePitchingLine(
            outs=line.outs,
            hits=line.hits,
            runs=line.runs,
            earned_runs=line.earned_runs,
            walks=line.walks,
            strikeouts=line.strikeouts,
            home_runs=home_runs,
        )
        for line, home_runs in zip(direction.pitching, loaded.pitcher_home_runs, strict=True)
    )
    return Direction(
        batting=batting,
        batting_totals=_totals(WideBattingLine, batting),
        batter_footnotes=footnotes,
        footnote_totals=_totals(WideFootnotes, footnotes),
        team_footnotes=TeamFootnotes(left_on_base=direction.team_footnotes.left_on_base),
        pitching=pitching,
        pitching_totals=_totals(WidePitchingLine, pitching),
        line_score=direction.line_score,
    )


def _totals(model: type, rows: tuple[object, ...]) -> object:
    return model(**{column: sum(getattr(row, column) for row in rows) for column in model.__annotations__})


def zero_density(direction: Direction, variant: Variant) -> float:
    """§5's gate quantity, recomputed over the configuration's own cells."""
    counted = 0
    zeros = 0
    for rows, totals, columns in (
        (direction.batting, direction.batting_totals, variant.batting),
        (direction.pitching, direction.pitching_totals, variant.pitching),
    ):
        for row in (*rows, totals):
            for column in columns:
                counted += 1
                zeros += getattr(row, column) == 0
    return zeros / counted


@dataclass(frozen=True, slots=True)
class Trajectory:
    """One board erased as far as it will go, under one configuration."""

    variant: str
    game_id: str
    season: int
    blanks_at: dict[int, int]
    ceiling: int
    zero_density: float
    erasable: int
    restarts: tuple[str, ...]
    home_run_deductions: int
    home_run_cross_deductions: int
    home_run_restarts: int


def stalls_in(solution: Solution) -> int:
    """Transitions into bounding. One halt is one stall however many steps it lasts."""
    count = 0
    previous = False
    for step in solution.deductions:
        bounding = step.technique is Technique.BOUNDING
        count += bounding and not previous
        previous = bounding
    return count


def restarted_by(solution: Solution) -> tuple[str, ...]:
    """The family of the first propagation step after each stall — what the player had to see."""
    resolved: list[str] = []
    previous = False
    for index, step in enumerate(solution.deductions):
        if step.technique is Technique.BOUNDING and not previous:
            resolved.append(_family_after(solution, index))
        previous = step.technique is Technique.BOUNDING
    return tuple(resolved)


def _family_after(solution: Solution, stall_at: int) -> str:
    for step in solution.deductions[stall_at:]:
        if step.technique is not Technique.BOUNDING and step.from_identity is not None:
            family = I.FAMILY_OF[step.from_identity].value
            return f"{family} (home runs)" if step.cell.endswith(".home_runs") else family
    return "bounded to the end"


def _home_run_work(solution: Solution) -> tuple[int, int]:
    """How much of the solve touched home runs, and how much of that was the new cross.

    ⚠️ **This is the question the cross-team link was added to answer.** A fifth cross-team equation
    that never resolves a cell is width spent on nothing, whatever the identity says.
    """
    touched = sum(step.cell.endswith(".home_runs") for step in solution.deductions)
    by_cross = sum(
        step.cell.endswith(".home_runs") and step.from_identity is Identity.CROSS_TEAM_TOTAL
        for step in solution.deductions
    )
    return touched, by_cross


def walk_the_board(loaded: Loaded, variant: Variant, seed: int) -> Trajectory | None:
    """Erase until nothing more can go, recording where each stall target was first reached.

    The full walk rather than an early break, because the ceiling is one of the answers: a column
    that lets a board reach twelve stalls where it reached eight is worth something different from
    one that only shifts the blank count at a target nobody has chosen yet.
    """
    direction = board_of(loaded, variant)
    if I.find_violations(direction):
        return None
    shape = C.shape_of(direction)
    values = C.cell_values(direction)
    rng = random.Random(seed)  # noqa: S311
    candidates = erasure.ORDERINGS[erasure.DEFAULT_ORDERING](erasure.erasable(direction), direction, rng)

    blanks_at: dict[int, int] = {}
    erased: set[str] = set()
    ceiling = 0
    best: Solution | None = None
    for cell in candidates:
        trial = erased | {cell}
        solution = solver.solve(shape, {name: value for name, value in values.items() if name not in trial})
        if not solution.is_complete:
            continue
        erased = trial
        stalls = stalls_in(solution)
        if stalls > ceiling:
            ceiling, best = stalls, solution
        for target in TARGETS:
            if stalls >= target and target not in blanks_at:
                blanks_at[target] = len(erased)
    if best is None:
        return None
    touched, by_cross = _home_run_work(best)
    restarts = restarted_by(best)
    return Trajectory(
        variant=variant.name,
        game_id=loaded.game_id,
        season=loaded.season,
        blanks_at=blanks_at,
        ceiling=ceiling,
        zero_density=zero_density(direction, variant),
        erasable=len(candidates),
        restarts=restarts,
        home_run_deductions=touched,
        home_run_cross_deductions=by_cross,
        home_run_restarts=sum("home runs" in restart for restart in restarts),
    )


def report_structure(structures: dict[str, dict[str, int]]) -> None:
    print("")
    print("=== WHAT EACH CONFIGURATION BUILDS ===")
    print("A 13-batter, 4-pitcher board. Cycles are the topological number section 6 guards above zero.")
    print(f"{'configuration':<40}{'cells':>7}{'eqs':>6}{'crosses':>9}{'bounds':>8}{'cycles':>8}")
    for name, built in structures.items():
        print(
            f"{name:<40}{built['cells']:>7}{built['equations']:>6}{built['crosses']:>9}"
            f"{built['inequalities']:>8}{built['cycles']:>8}"
        )

    print("")
    print("=== WIDTH, WHICH IS ARITHMETIC ===")
    usable = PHONE_WIDTH - 2 * PAGE_MARGINS - LABEL_COLUMN
    print(f"{PHONE_WIDTH}px less {2 * PAGE_MARGINS}px of margin and a {LABEL_COLUMN}px label leaves {usable}px.")
    print(f"A cell must be at least {MINIMUM_TOUCH_TARGET}px, so the board holds {usable // MINIMUM_TOUCH_TARGET}.")
    print(f"{'configuration':<40}{'columns':>9}{'px each':>9}{'fits':>7}")
    for variant in VARIANTS:
        widest_section = max(len(variant.batting), len(variant.pitching))
        each = usable / widest_section
        fits = "yes" if each >= MINIMUM_TOUCH_TARGET else "NO"
        print(f"{variant.name:<40}{widest_section:>9}{each:>9.1f}{fits:>7}")
    print("  Footnote cells are not in this table: the footnote line carries no column and needs no")
    print("  touch target, which is the whole reason §6 puts the sparse terms there.")


def report(results: list[Trajectory], boards: int) -> None:
    print("")
    print("=== WHAT EACH CONFIGURATION COSTS AND REACHES ===")
    print("Same boards throughout. Zero density is recomputed over the configuration's own cells;")
    print(f"the gate stands at {GATE:.0%} and the sample was selected on the six columns that exist today.")
    print(f"{'configuration':<40}{'boards':>7}{'zeros p50':>11}{'over gate':>11}{'erasable':>10}{'ceiling p50':>12}")
    for variant in VARIANTS:
        group = [r for r in results if r.variant == variant.name]
        if not group:
            print(f"{variant.name:<40}{0:>7}")
            continue
        over = sum(r.zero_density >= GATE for r in group) / len(group)
        print(
            f"{variant.name:<40}{len(group):>7}{statistics.median([r.zero_density for r in group]):>11.1%}"
            f"{over:>11.0%}{statistics.median([r.erasable for r in group]):>10.0f}"
            f"{statistics.median([r.ceiling for r in group]):>12.0f}"
        )

    print("")
    print("=== BLANKS NEEDED TO REACH A STALL TARGET, AND HOW MUCH OF THE POOL GETS THERE ===")
    for variant in VARIANTS:
        group = [r for r in results if r.variant == variant.name]
        if not group:
            continue
        blanks_line = []
        reach_line = []
        for target in TARGETS:
            reached = [r.blanks_at[target] for r in group if target in r.blanks_at]
            blanks_line.append(f"{statistics.median(reached):>5.0f}" if reached else f"{'-':>5}")
            reach_line.append(f"{len(reached) / len(group):>5.0%}")
        print(f"  {variant.name}")
        print(f"{'stalls':>12} " + "".join(f"{t:>5}" for t in TARGETS))
        print(f"{'blanks p50':>12} " + "".join(blanks_line))
        print(f"{'of pool':>12} " + "".join(reach_line))

    print("")
    print("=== DOES THE HOME-RUN CROSS FIRE? ===")
    print("Counted on each board's hardest solve. A cross-team equation that never resolves a cell is")
    print("width spent on nothing, whatever the identity says.")
    print(f"{'configuration':<40}{'HR cells deduced':>18}{'by the cross':>16}{'stalls restarted':>18}")
    for variant in VARIANTS:
        group = [r for r in results if r.variant == variant.name] if variant.has_home_runs else []
        if not group:
            continue
        touched = sum(r.home_run_deductions for r in group)
        crossed = sum(r.home_run_cross_deductions for r in group)
        share = f"{crossed} ({crossed / touched:.0%})" if touched else "0"
        print(
            f"{variant.name:<40}{touched:>18}{share:>16}"
            f"{sum(r.home_run_restarts for r in group):>18}"
        )

    print("")
    print("=== WHAT RESTARTS A STALL ===")
    for variant in VARIANTS:
        group = [r for r in results if r.variant == variant.name]
        if not group:
            continue
        families: Counter[str] = Counter()
        for board in group:
            families.update(board.restarts)
        total = sum(families.values()) or 1
        shown = ", ".join(f"{name} {count / total:.0%}" for name, count in families.most_common(5))
        print(f"  {variant.name:<40}{shown}")
    print(f"\n({boards} boards, one seed, every configuration on the same games)")


def render_examples(sample: list[Loaded], out: Path) -> None:
    """Boards to look at. The numbers are not trusted until a few have been read by eye."""
    import render_boards  # noqa: PLC0415

    boards = []
    for variant in VARIANTS:
        configure(variant)
        for name, value in (
            ("BATTING_COLUMNS", variant.batting),
            ("PITCHING_COLUMNS", variant.pitching),
            ("FOOTNOTE_COLUMNS", variant.footnotes),
        ):
            if hasattr(render_boards, name):
                setattr(render_boards, name, value)
        for loaded in sample[:RENDERED]:
            direction = board_of(loaded, variant)
            if I.find_violations(direction):
                continue
            puzzle = erasure.erase(direction, target_stalls=8, seed=SEED)
            if puzzle is None:
                continue
            boards.append(render_boards.render(replace(loaded, direction=direction), puzzle, f"{variant.name}"))
            break
    out.write_text(render_boards.page(boards, title="RBI and home runs, one column at a time"), encoding="utf-8")


def main() -> None:
    sample = load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
    if not sample:
        message = f"no directions survived the {GATE:.0%} gate at {SAMPLE_PER_DECADE} per decade"
        raise SystemExit(message)
    print(f"{len(sample)} gated directions, gate {GATE:.0%}, selected on the six columns that exist today", flush=True)
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")

    widest = C.BoardShape(batter_count=13, pitcher_count=4, offense_innings=9, defense_innings=9)
    structures: dict[str, dict[str, int]] = {}
    results: list[Trajectory] = []
    for number, variant in enumerate(VARIANTS, start=1):
        configure(variant)
        # Before any board: a patch that did not take effect must stop the run rather than produce a
        # sixth identical column of numbers.
        structures[variant.name] = _assert_the_instrument_changed(variant, widest)
        print(f"  [{number}/{len(VARIANTS)}] {variant.name}: instrument checked, walking {len(sample)} boards",
              flush=True)
        for loaded in sample:
            walked = walk_the_board(loaded, variant, SEED)
            if walked is not None:
                results.append(walked)
        print(f"        done, {len(results)} trajectories so far", flush=True)

    report_structure(structures)
    report(results, len(sample))

    out = Path(__file__).resolve().parent / "look-at-these.html"
    render_examples(sample, out)
    configure(VARIANTS[0])
    print(f"\nboards written to {out} - read them before trusting anything above")


if __name__ == "__main__":
    main()
