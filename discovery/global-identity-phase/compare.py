"""The same boards, before and after the global identity's phase boundary is completed.

v02-P2-01 fixed propagation's phase order and reported that nothing moved. v03-P2-01 found the
boundary is only half there, in two places:

  telemetry   `_scan_size` counts live and solvable equations over the *whole* system before the
              phase that supplied the move is known, so a deduction found without the global
              identity still carries a search cost that counted a global equation.
  bounding    `_bounding_moves` says the global identity stays out of the narrowing. `narrow`, which
              it calls three lines later, says the global identity is in there with everything else,
              and builds from the full system. The code follows the second.

**The second docstring's justification is what settles it.** It argues that withholding is
unnecessary because *which puzzles needed it is recorded on the family axis*. That is true of
propagation and false of bounding: a bounding deduction carries `from_identity=None`, so the global
identity can corner a cell without appearing in `families_used` at all. The reason given for not
withholding does not hold where it is being applied.

**This script does not decide that. It measures what changes.** Run it on the commit before the
repair and again after, then compare the two JSON files — same boards, same seeds, same targets.

  python ../discovery/global-identity-phase/compare.py before.json
  ... apply the repair ...
  python ../discovery/global-identity-phase/compare.py after.json
  python ../discovery/global-identity-phase/compare.py --against before.json after.json

Five numbers, the same five v02-P2-01 closed on: stalls, chain length, families used, where in the
solve the first stall falls, and — new, because it is the one the repair is aimed at — how often the
global family appears at all.

⚠️ **A null result is the expected outcome and is worth as much as a change.** What must not happen
is reporting one without having run both halves, which is why the comparison reads two files rather
than trusting a remembered number.

Read-only against DGL. Run from `forge/`.
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

from measure import load  # noqa: E402

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402
from boxscore_forge.erasure import erase  # noqa: E402
from boxscore_forge.identities import Family, find_violations  # noqa: E402
from boxscore_forge.solver import Technique  # noqa: E402

SAMPLE_PER_DECADE = 8
GATE = ZERO_DENSITY_GATE
"""§5's zero-density gate, from the one place it is decided.

⚠️⚠️ **This read `GATE = 0.25` and the figures this script has published were measured at 0.25**, not at
the decided 0.30 — recorded here rather than in a commit message so a stale number is interpretable
instead of mysterious, and so a re-run's difference from it is explainable rather than a new
discrepancy. Fourteen instruments carried the literal; twelve of them, including this one, were
silently stricter than the pool the board actually draws from.

⚠️ **A stricter gate is not a smaller sample of the same thing.** It removes the zero-heavy boards,
which are the ones that compress least, so every figure about coverage, reachable stall targets or
chain length was taken over a livelier population than production. See `docs/reviews/todo.md` for the
two instruments whose disagreement this explains.
"""
SEEDS = (1, 2)
TARGET_STALLS = 8


def _stall_position(solution: object) -> float | None:
    """How far into the solve the first stall falls, as a share of the steps."""
    deductions = solution.deductions  # type: ignore[attr-defined]
    for index, step in enumerate(deductions):
        if step.technique is Technique.BOUNDING:
            return index / len(deductions)
    return None


def measure() -> list[dict[str, object]]:
    sample = load(SAMPLE_PER_DECADE, gated=True, gate=GATE)
    sample = [item for item in sample if not find_violations(item.direction)]
    if not sample:
        message = f"no directions survived the {GATE:.0%} gate at {SAMPLE_PER_DECADE} per decade"
        raise SystemExit(message)
    print(f"{len(sample)} gated directions, target {TARGET_STALLS} stalls, seeds {SEEDS}", flush=True)

    rows: list[dict[str, object]] = []
    for item in sample:
        for seed in SEEDS:
            puzzle = erase(item.direction, target_stalls=TARGET_STALLS, seed=seed)
            if puzzle is None:
                continue
            solution = puzzle.solution
            rows.append(
                {
                    "game_id": item.game_id,
                    "seed": seed,
                    "blanks": len(puzzle.erased),
                    "stalls": solution.stalls,
                    "chain": solution.chain_length,
                    "families": sorted(family.value for family in solution.families_used),
                    "family_count": len(solution.families_used),
                    "used_global": Family.GLOBAL_IDENTITY.value in {family.value for family in solution.families_used},
                    "stall_position": _stall_position(solution),
                    "steps": len(solution.deductions),
                    "hardest_search": solution.hardest_search,
                }
            )
        print(f"  {len(rows)} solved", end="\r", flush=True)
    print("")
    return rows


def summarise(rows: list[dict[str, object]]) -> dict[str, float]:
    positions = [row["stall_position"] for row in rows if row["stall_position"] is not None]
    return {
        "boards": len(rows),
        "stalls": statistics.median([row["stalls"] for row in rows]),
        "chain": statistics.median([row["chain"] for row in rows]),
        "blanks": statistics.median([row["blanks"] for row in rows]),
        "families": statistics.fmean([row["family_count"] for row in rows]),
        "global_share": statistics.fmean([float(row["used_global"]) for row in rows]),
        "stall_position": statistics.fmean(positions) if positions else float("nan"),
    }


def _keyed(path: Path) -> dict[tuple[str, int], dict]:
    """Rows by (game, seed), refusing duplicates rather than silently keeping the last one."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    keyed: dict[tuple[str, int], dict] = {}
    for row in rows:
        key = (row["game_id"], row["seed"])
        if key in keyed:
            message = f"{path.name} holds {key} twice; a dict would have kept whichever came last"
            raise SystemExit(message)
        keyed[key] = row
    return keyed


def compare(before: Path, after: Path) -> None:
    """Two files, board by board. A median that holds can still hide every board moving."""
    left, right = _keyed(before), _keyed(after)
    shared = sorted(left.keys() & right.keys())
    # ⚠️ **An instrument that cannot compare must say so, not raise `StatisticsError` three frames
    # down.** Two disjoint files under `--allow-partial` reached `summarise([])` and `shared[0]`.
    if not shared:
        message = (
            f"{before.name} holds {len(left)} boards and {after.name} holds {len(right)}, and they "
            f"share none. There is nothing to compare; the two runs used different samples."
        )
        raise SystemExit(message)
    # ⚠️ **This compared the intersection and asked only that it be non-empty.** A database change, a
    # partial run or a solver failure can remove exactly the boards a change affects, and the
    # comparison would then report a clean null over the survivors — which is the false null this
    # instrument exists to prevent, arriving through the door it left open.
    if left.keys() != right.keys():
        only_left = sorted(left.keys() - right.keys())
        only_right = sorted(right.keys() - left.keys())
        if "--allow-partial" not in sys.argv:
            message = (
                f"the cohorts differ: {len(only_left)} only in {before.name}, {len(only_right)} only in "
                f"{after.name}. Pass --allow-partial to compare the intersection anyway, which is a "
                f"diagnostic and not an experiment."
            )
            raise SystemExit(message)
        print(
            f"NOTE: PARTIAL — {len(only_left)} boards only before, {len(only_right)} only after. "
            f"Not an experimental result."
        )

    print(f"\n=== {before.name} AGAINST {after.name} ===")
    print(f"{len(shared)} boards in both, {len(left) - len(shared)} only before, {len(right) - len(shared)} only after")
    print(f"{'':<18}{'before':>10}{'after':>10}{'moved':>8}")
    for field in ("stalls", "chain", "blanks", "families", "global_share", "stall_position"):
        was = summarise([left[key] for key in shared])[field]
        now = summarise([right[key] for key in shared])[field]
        print(f"{field:<18}{was:>10.3f}{now:>10.3f}{'yes' if abs(was - now) > 1e-9 else 'no':>8}")

    # ⚠️ The number a median cannot show. Two boards moving in opposite directions leave every
    # summary unchanged, and reporting "nothing moved" off that would be the same class of mistake
    # as a check that never fires.
    print("")
    # ⚠️ Every field that was collected, derived from the rows rather than listed by hand. The first
    # version of this named five fields and the rows carried seven: it printed "not one board changed
    # on any field" while `hardest_search` had moved on four boards. A comparison that chooses which
    # of its own measurements to look at is the failure it exists to catch.
    fields = sorted(set(left[shared[0]]) - {"game_id", "seed"})
    changed = Counter()
    for key in shared:
        for field in fields:
            if left[key][field] != right[key][field]:
                changed[field] += 1
    print(f"compared {len(fields)} fields: {', '.join(fields)}")
    if not changed:
        print("Board by board: not one board changed on any field. The null is a real null.")
    else:
        for field, count in changed.most_common():
            print(f"  {field}: {count} of {len(shared)} boards changed ({count / len(shared):.0%})")
        moved = {key for key in shared if any(left[key][f] != right[key][f] for f in ("stalls", "chain"))}
        for key in sorted(moved)[:5]:
            print(
                f"    {key[0]} seed {key[1]}: stalls {left[key]['stalls']}->{right[key]['stalls']}, "
                f"chain {left[key]['chain']}->{right[key]['chain']}, "
                f"families {left[key]['families']} -> {right[key]['families']}"
            )


def main() -> None:
    if "--against" in sys.argv:
        index = sys.argv.index("--against")
        # Arity before indexing: `--against` with one path used to raise IndexError rather than say so.
        if len(sys.argv) < index + 3:
            message = "usage: compare.py --against <before.json> <after.json>"
            raise SystemExit(message)
        for path in (Path(sys.argv[index + 1]), Path(sys.argv[index + 2])):
            if not path.exists():
                message = f"{path} does not exist"
                raise SystemExit(message)
        compare(Path(sys.argv[index + 1]), Path(sys.argv[index + 2]))
        return
    if len(sys.argv) != 2:
        message = "give one output path, or --against <before.json> <after.json>"
        raise SystemExit(message)
    out = Path(sys.argv[1])
    rows = measure()
    if not rows:
        # The two ways to get here are different problems, and one message for both hides which.
        message = (
            "no rows: every erasure failed to reach the target on a non-empty sample. If the sample "
            "was empty the loader would have said so above."
        )
        raise SystemExit(message)
    out.write_text(json.dumps(rows, indent=1, sort_keys=True), encoding="utf-8")
    summary = summarise(rows)
    print(f"wrote {len(rows)} rows to {out}")
    for field, value in summary.items():
        print(f"  {field:<16}{value:>10.3f}")


if __name__ == "__main__":
    main()
