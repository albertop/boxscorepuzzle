"""Does the loader produce real boards? A sweep, and a handful of boards to look at.

⚠️ **Built after a defect that no automated test could have caught with the tests that existed.**
Retrosheet's `B_G = 1` means a player appeared, not that he batted, so the loader put non-batting
pitchers on the board as rows of noughts. Every identity balanced, all four §22 layers passed it, and
a human reading a printed board found it.

The gap was not depth. It was that **everything tested internal consistency and nothing tested
correspondence to reality**. A fabricated board and a real one both satisfy §3.

Three kinds of check here, and only the first existed before:

  identities        the board's arithmetic closes — already covered by the verifier
  loader invariants what the loader promised about *which rows* it selected and in what order
  plausibility     whether the result could have been a baseball game at all

Plus the rule the defect argues for: **a measurement that produces a distribution should also produce
a few rendered examples, checked by eye, before the numbers are trusted.** Every serious error in this
project was found by looking rather than by computing — the zero-heavy board, the totals row showing
pitching, the zero-filled error columns, and this one. `--render` writes them out.

Read-only against DGL. Run from `forge/`.
"""

import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "discovery" / "verifier"))

from measure import CONNECTION, Loaded, load  # noqa: E402
from rejection_rates import to_board  # noqa: E402

from boxscore_verify.plausibility import faults  # noqa: E402

SAMPLE_PER_DECADE = 40


def loader_invariants(sample: list[Loaded]) -> Counter[str]:
    """What the loader promised about which rows it took, and in what order.

    Stated as checks rather than left implicit in a `WHERE` clause: a filter is a decision that
    nothing re-reads, and this one was wrong for months.
    """
    broken: Counter[str] = Counter()
    for item in sample:
        batting = item.direction.batting
        # NOT "every row batted". A pinch runner scores without a plate appearance, and the rule
        # that dropped him is the defect this sweep exists to catch. The invariant is that the row
        # contributed something — the same predicate the loader selects on.
        if any(
            line.plate_appearances == 0
            and line.runs == 0
            and line.hits == 0
            and line.walks == 0
            and line.strikeouts == 0
            and not any(
                getattr(note, field)
                for field in ("hit_by_pitch", "sacrifice_flies", "sacrifice_hits", "catcher_interference")
            )
            for line, note in zip(batting, item.direction.batter_footnotes, strict=True)
        ):
            broken["a batting row that contributed nothing"] += 1
        if len(batting) < 9:
            broken["fewer than nine batters"] += 1
        if batting and batting[0].plate_appearances < max(line.plate_appearances for line in batting):
            # Informational, not a fault. The leadoff hitter bats first and usually most often, but
            # he can be lifted in the fourth and finish with fewer plate appearances than the man
            # batting fifth who played all nine. Measured at 2.5%, which is what substitution looks
            # like; a jump towards 50% would mean the ordering had broken again.
            broken["(expected minority) the first row is not the most frequent batter"] += 1
        if len(item.labels) != len(batting):
            broken["labels do not match the lineup"] += 1
        if len(item.pitcher_labels) != len(item.direction.pitching):
            broken["pitcher labels do not match the pitching rows"] += 1
        if item.pitcher_labels and item.pitcher_labels[0] != "SP":
            broken["the first pitching row is not the starter"] += 1
    return broken


def against_an_independent_source(sample: list[Loaded]) -> Counter[str]:
    """Cross-check the loaded totals against the game log, which is a different table.

    Checking `retroDailyReg` against itself would have agreed with the defect. The game log carries
    at-bats and left-on-base per team from Retrosheet's own game-level file, so a disagreement means
    the rows the loader chose are not the rows the game had.
    """
    import pyodbc  # noqa: PLC0415

    broken: Counter[str] = Counter()
    query = """
    SELECT CASE WHEN ? = 1 THEN HomeAB ELSE VisAB END, CASE WHEN ? = 1 THEN HomeLOB ELSE VisLOB END,
           CASE WHEN ? = 1 THEN HomeRunsScore ELSE VisRunsScored END
    FROM dbo.retroGameLogs WHERE GAME_ID = ?
    """
    with pyodbc.connect(CONNECTION) as connection:
        for item in sample:
            home = 1 if item.offense_is_home else 0
            row = connection.cursor().execute(query, home, home, home, item.game_id).fetchone()
            if row is None or row[0] is None:
                broken["no game log row"] += 1
                continue
            at_bats, left_on_base, runs = row
            if item.direction.batting_totals.at_bats != at_bats:
                broken["at-bats disagree with the game log"] += 1
            if left_on_base is not None and item.direction.team_footnotes.left_on_base != left_on_base:
                broken["left on base disagrees with the game log"] += 1
            if runs is not None and item.direction.batting_totals.runs != runs:
                broken["runs disagree with the game log"] += 1
    return broken


def plausibility(sample: list[Loaded]) -> Counter[str]:
    broken: Counter[str] = Counter()
    for item in sample:
        for fault in faults(to_board(item, None), max_batters=13):
            broken[fault.what] += 1
    return broken


def render_a_few(sample: list[Loaded], out: Path) -> None:
    """Six boards written out to be looked at. Not a test — the step before trusting the numbers."""
    sys.path.insert(0, str(_ROOT / "discovery" / "pitcher-cap"))
    from render_boards import page  # noqa: PLC0415
    from render_boards import render as render_board  # noqa: PLC0415

    from boxscore_forge.erasure import erase  # noqa: PLC0415

    boards = []
    for item in sample[:: max(len(sample) // 6, 1)][:6]:
        puzzle = erase(item.direction, target_chain=9, seed=3)
        if puzzle is None:
            continue
        boards.append(render_board(item, puzzle, f"{len(item.direction.batting)} batters, chain 9"))
    out.write_text(page(boards), encoding="utf-8")


def report(name: str, broken: Counter[str], total: int) -> None:
    print(f"\n=== {name.upper()} ===")
    if not broken:
        print(f"  clean across {total} directions")
        return
    for what, count in broken.most_common():
        print(f"  ⚠️ {what:<48} {count:>5}  ({100.0 * count / total:.2f}%)")


def main() -> None:
    sample = load(SAMPLE_PER_DECADE, gated=True, max_batters=13, max_pitchers=4)
    print(f"{len(sample)} directions, {SAMPLE_PER_DECADE} per decade")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")

    report("loader invariants", loader_invariants(sample), len(sample))
    report("plausibility", plausibility(sample), len(sample))
    report("against the game log", against_an_independent_source(sample), len(sample))

    out = Path(__file__).resolve().parent / "look-at-these.html"
    render_a_few(sample, out)
    print(f"\nsix boards written to {out} — look at them before trusting anything above")


if __name__ == "__main__":
    main()
