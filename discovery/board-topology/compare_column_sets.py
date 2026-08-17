"""Compare candidate column sets by how interconnected their constraint graph is.

Boards under test, all on the real Cubs-at-Braves 1968 direction:
  A  current            AB R H RBI BB K, team footnotes
  B  PA for RBI         PA AB R H BB K, team footnotes (row identity only where it closes alone)
  C  PA + per-player    PA AB R H BB K, footnotes attributed per batter
  D  PA for RBI, K out  PA AB R H BB SO->dropped, control for "is RBI the best thing to drop"
"""

import itertools
import random
from dataclasses import dataclass, field

PA = [5, 5, 5, 4, 4, 4, 4, 4, 4]
AB = [4, 5, 4, 4, 4, 3, 4, 4, 4]
R = [1, 0, 1, 0, 0, 0, 0, 0, 2]
H = [1, 2, 2, 1, 0, 2, 1, 1, 1]
RBI = [0, 1, 2, 1, 0, 0, 0, 0, 0]
BB = [0, 0, 1, 0, 0, 1, 0, 0, 0]
SO = [0, 1, 0, 1, 1, 0, 0, 0, 2]
FOOTNOTE_PER_ROW = [1, 0, 0, 0, 0, 0, 0, 0, 0]  # kessd101's sacrifice hit
COLUMN_DATA = {"pa": PA, "at_bats": AB, "runs": R, "hits": H, "rbi": RBI, "walks": BB, "strikeouts": SO}

PITCH = {"outs": [20, 7], "hits": [10, 1], "runs": [4, 0], "earned": [4, 0], "walks": [1, 1], "so": [3, 2]}


@dataclass
class Board:
    name: str
    columns: list[str]
    row_identities: bool
    per_player_footnotes: bool
    equations: list[frozenset[str]] = field(default_factory=list)
    values: dict[str, int] = field(default_factory=dict)

    def build(self) -> "Board":
        for column in self.columns:
            cells = [f"bat[{i}].{column}" for i in range(9)]
            for index, cell in enumerate(cells):
                self.values[cell] = COLUMN_DATA[column][index]
            self.values[f"bat_tot.{column}"] = sum(COLUMN_DATA[column])
            self.equations.append(frozenset([*cells, f"bat_tot.{column}"]))

        for column, data in PITCH.items():
            cells = [f"pit[{i}].{column}" for i in range(2)]
            for index, cell in enumerate(cells):
                self.values[cell] = data[index]
            self.values[f"pit_tot.{column}"] = sum(data)
            self.equations.append(frozenset([*cells, f"pit_tot.{column}"]))

        for offense, defense in (("hits", "hits"), ("runs", "runs"), ("walks", "walks"), ("strikeouts", "so")):
            if offense in self.columns:
                self.equations.append(frozenset([f"bat_tot.{offense}", f"pit_tot.{defense}"]))

        self.values["ls.offense_runs"] = sum(R)
        self.values["ls.offense_hits"] = sum(H)
        self.equations.append(frozenset(["ls.offense_runs", "bat_tot.runs"]))
        self.equations.append(frozenset(["ls.offense_hits", "bat_tot.hits"]))

        for name, value in (("fn.lob", 8), ("fn.hbp", 0), ("fn.sf", 0), ("fn.sh", 1), ("fn.xi", 0)):
            self.values[name] = value

        if "pa" in self.columns:
            # Forward and backward counts are now two equations, both over the team's PA total.
            self.equations.append(frozenset(["bat_tot.pa", "bat_tot.at_bats", "bat_tot.walks", "fn.hbp", "fn.sf", "fn.sh", "fn.xi"]))
            self.equations.append(frozenset(["bat_tot.pa", "pit_tot.outs", "bat_tot.runs", "fn.lob"]))
        else:
            self.equations.append(
                frozenset(["bat_tot.at_bats", "bat_tot.walks", "fn.hbp", "fn.sf", "fn.sh", "fn.xi",
                           "pit_tot.outs", "bat_tot.runs", "fn.lob"])
            )

        if self.row_identities:
            for i in range(9):
                if self.per_player_footnotes:
                    for suffix in ("hbp", "sf", "sh", "xi"):
                        self.values[f"bat[{i}].{suffix}"] = FOOTNOTE_PER_ROW[i] if suffix == "sh" else 0
                    self.equations.append(
                        frozenset([f"bat[{i}].pa", f"bat[{i}].at_bats", f"bat[{i}].walks",
                                   f"bat[{i}].hbp", f"bat[{i}].sf", f"bat[{i}].sh", f"bat[{i}].xi"])
                    )
                elif FOOTNOTE_PER_ROW[i] == 0:
                    self.equations.append(frozenset([f"bat[{i}].pa", f"bat[{i}].at_bats", f"bat[{i}].walks"]))
        return self


def max_overlap(board: Board) -> tuple[int, list[tuple[int, int]]]:
    best, examples = 0, []
    for a, b in itertools.combinations(board.equations, 2):
        shared = a & b
        if len(shared) > best:
            best, examples = len(shared), [(sorted(a), sorted(b), sorted(shared))]
    return best, examples


def degrees(board: Board) -> dict[str, int]:
    counts: dict[str, int] = {}
    for equation in board.equations:
        for cell in equation:
            counts[cell] = counts.get(cell, 0) + 1
    return counts


def cyclomatic(board: Board) -> int:
    """Independent cycles in the bipartite cell/equation graph: edges - nodes + components."""
    cells = degrees(board)
    nodes = len(cells) + len(board.equations)
    edges = sum(len(equation) for equation in board.equations)
    parent = {**{c: c for c in cells}, **{f"eq{i}": f"eq{i}" for i in range(len(board.equations))}}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for index, equation in enumerate(board.equations):
        for cell in equation:
            a, b = find(cell), find(f"eq{index}")
            if a != b:
                parent[a] = b
    components = len({find(n) for n in parent})
    return edges - nodes + components


def solvable(board: Board, erased: set[str]) -> bool:
    """T1 and T2 only: repeatedly take any equation with exactly one unknown left."""
    unknown = set(erased)
    while True:
        for equation in board.equations:
            missing = equation & unknown
            if len(missing) == 1:
                unknown -= missing
                break
        else:
            return not unknown


def survey(board: Board, sizes: range, trials: int = 4000) -> dict[int, float]:
    rng = random.Random(20260817)
    candidates = sorted(cell for cell in degrees(board) if cell.startswith("bat[") or cell.startswith("bat_tot."))
    result = {}
    for size in sizes:
        wins = sum(solvable(board, set(rng.sample(candidates, size))) for _ in range(trials))
        result[size] = 100.0 * wins / trials
    return result


BOARDS = [
    Board("A current            ", ["at_bats", "runs", "hits", "rbi", "walks", "strikeouts"], False, False),
    Board("B PA for RBI, team fn", ["pa", "at_bats", "runs", "hits", "walks", "strikeouts"], True, False),
    Board("C PA for RBI, per-row", ["pa", "at_bats", "runs", "hits", "walks", "strikeouts"], True, True),
    # Control: is RBI really the right thing to drop? Keep it and drop strikeouts instead.
    Board("D PA for K, per-row  ", ["pa", "at_bats", "runs", "hits", "walks", "rbi"], True, True),
]

for board in BOARDS:
    board.build()
    best, examples = max_overlap(board)
    counts = degrees(board)
    histogram: dict[int, int] = {}
    for value in counts.values():
        histogram[value] = histogram.get(value, 0) + 1
    print(f"\n=== {board.name} | {len(board.equations)} equations, {len(counts)} cells")
    print(f"    max pairwise overlap : {best}")
    print(f"    cells by degree      : {dict(sorted(histogram.items()))}")
    print(f"    cells in 2+ equations: {sum(n for d, n in histogram.items() if d >= 2)}")
    print(f"    independent cycles   : {cyclomatic(board)}")
    if best >= 2:
        a, b, shared = examples[0]
        print(f"    overlap example      : {shared}")
    print(f"    solvable by T1/T2 after erasing N batting cells (% of 4000 random draws):")
    for size, pct in survey(board, range(2, 13)).items():
        print(f"        {size:2d} cells: {pct:5.1f}%")
