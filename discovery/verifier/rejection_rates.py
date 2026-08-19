"""What the verifier rejects, over real generator output, by layer.

Three questions §22 cannot answer from its own text:

  **Which layer catches what.** The distribution says whether the generator is behaving: a batch
  where layer 3 rejects most is a generator stopping too early, one where layer 1 rejects most is a
  pool admitting boxscores it should not.

  **Does layer 4 ever catch something the first three passed?** That is the redundancy paying for
  itself, and if it happens it is the headline rather than a footnote.

  **Does any layer never reject anything?** A layer that never fires is either perfect or untested,
  and the difference matters a great deal.

Plus the question the verifier raised about itself: **how many boards that pass layer 3 also survive
a solver that reads one relation at a time.** Layer 3 runs interval propagation to a fixed point
across every relation at once, which no person does, so a board can pass it and still be underivable
by hand. The weak solver is the other end of that bracket.

⚠️ **This is the one place the two vocabularies meet.** The verifier shares no code with the
generator, so something has to turn what the generator produces into the package format. That
adapter lives here, in discovery, and not in either package.

Read-only against DGL. Run from `forge/`.
"""

import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

from measure import Loaded, load  # noqa: E402

from boxscore_forge.erasure import erase  # noqa: E402
from boxscore_forge.identity import puzzle_id  # noqa: E402
from boxscore_forge.publish import to_board as production_board  # noqa: E402
from boxscore_package.format import Board, LineScore, Package  # noqa: E402
from boxscore_package.signing import sign  # noqa: E402
from boxscore_verify.verify import LAYERS, Layer, Rejection, derivable_in_view, verify  # noqa: E402

TARGETS = (5, 7, 9, 11, 13)
SAMPLE_PER_DECADE = 5
SEED = 4
SECRET = b"a discovery-run secret, not the one that will sign anything published"


@dataclass(frozen=True)
class Outcome:
    game: str
    target: int
    rejection: Rejection | None
    caught_by_each: tuple[Layer, ...]
    weakly_derivable: bool | None


def to_board(loaded: Loaded, erased: frozenset[str] | None) -> Board:
    """Thin wrapper over the production adapter.

    ⚠️ This function used to *be* the adapter, and the production path imported it from here. It also
    copied every footnote value without consulting the erased set, so a footnote erasure vanished on
    the way into the package. Both are fixed by the conversion living in
    `boxscore_forge.publish`; this only unwraps `Loaded`.
    """
    return production_board(loaded.direction, erased)


def run(sample: list[Loaded]) -> list[Outcome]:
    outcomes: list[Outcome] = []
    for loaded in sample:
        source = to_board(loaded, None)
        for target in TARGETS:
            produced = erase(loaded.direction, target_chain=target, seed=SEED)
            if produced is None:
                continue
            package = sign(
                Package(
                    labels=("C",) * len(to_board(loaded, produced.erased).batting),
                    pitcher_labels=("C",) * len(to_board(loaded, produced.erased).pitching),
                    offense_is_home=loaded.offense_is_home,
                    puzzle_id=puzzle_id(loaded.game_id, f"offense{target}"),
                    puzzle=to_board(loaded, produced.erased),
                    solution=source,
                    metadata={"season": loaded.season, "target_chain": target},
                ),
                SECRET,
            )
            verdict = verify(package, secret=SECRET)
            # Every layer asked separately, not only the first to object. A layer that never fires
            # cannot be told apart from a layer that is never reached.
            caught = tuple(layer for layer, check in LAYERS.items() if check(package, SECRET) is not None)
            outcomes.append(
                Outcome(
                    game=loaded.game_id,
                    target=target,
                    rejection=verdict.rejection,
                    caught_by_each=caught,
                    weakly_derivable=derivable_in_view(package) if verdict.accepted else None,
                )
            )
    return outcomes


def report(outcomes: list[Outcome]) -> None:
    print(f"\n=== {len(outcomes)} PUZZLES FROM THE REAL GENERATOR ===")
    accepted = [outcome for outcome in outcomes if outcome.rejection is None]
    print(f"  accepted by all four layers : {len(accepted)} ({100.0 * len(accepted) / len(outcomes):.1f}%)")

    print("\n=== WHAT REJECTED, BY LAYER AND FAULT ===")
    faults: Counter[str] = Counter(
        f"{outcome.rejection.layer}:{outcome.rejection.fault}" for outcome in outcomes if outcome.rejection
    )
    if not faults:
        print("  nothing was rejected")
    for name, count in faults.most_common():
        print(f"  {name:<34} {count:>4}  ({100.0 * count / len(outcomes):.1f}%)")

    print("\n=== DOES EVERY LAYER EVER FIRE ===")
    print("  A layer that never rejects is either perfect or untested, and those are not the same.")
    fired: Counter[Layer] = Counter()
    for outcome in outcomes:
        for layer in outcome.caught_by_each:
            fired[layer] += 1
    for layer in LAYERS:
        count = fired[layer]
        note = "never fired on this sample" if count == 0 else ""
        print(f"  {layer:<14} {count:>4} {note}")

    print("\n=== DID LAYER 4 CATCH ANYTHING THE FIRST THREE PASSED ===")
    late = [
        outcome
        for outcome in outcomes
        if Layer.END_TO_END in outcome.caught_by_each
        and not ({Layer.IDENTITIES, Layer.UNIQUENESS, Layer.DERIVABILITY} & set(outcome.caught_by_each))
    ]
    if late:
        print(f"  ⚠️ YES — {len(late)}. This is the redundancy paying for itself and belongs in §22.")
        for outcome in late[:5]:
            print(f"    {outcome.game} at chain {outcome.target}: {outcome.rejection}")
    else:
        print("  No. Layer 4 confirmed the first three on every board and caught nothing they missed.")

    print("\n=== HOW MANY ACCEPTED BOARDS SURVIVE A ONE-RELATION-AT-A-TIME SOLVER ===")
    print("  Layer 3 propagates across every relation at once, which no person does. This is the")
    print("  lower bound on humanness against layer 3's upper one.")
    by_target: dict[int, list[bool]] = {}
    for outcome in accepted:
        if outcome.weakly_derivable is not None:
            by_target.setdefault(outcome.target, []).append(outcome.weakly_derivable)
    print(f"{'chain target':>13}{'accepted':>10}{'also weakly derivable':>24}")
    for target in sorted(by_target):
        values = by_target[target]
        print(f"{target:>13}{len(values):>10}{100.0 * sum(values) / len(values):>23.0f}%")
    everything = [value for values in by_target.values() for value in values]
    if everything:
        print(f"\n  overall: {100.0 * sum(everything) / len(everything):.0f}% of published boards survive both")


def _render(sample: list, folder: str) -> None:
    """Six boards to look at, written before the numbers are printed (see `discovery/render_step`)."""
    sys.path.insert(0, str(_ROOT / "discovery"))
    from render_step import write_examples  # noqa: PLC0415

    out = _ROOT / "discovery" / folder / "look-at-these.html"
    count = write_examples(sample, out)
    print()
    print(f"{count} boards written to {out} — look at them before trusting anything below")


def main() -> None:
    sample = load(SAMPLE_PER_DECADE, gated=True)
    print(f"{len(sample)} gated directions at the decided caps")
    print(f"decades: {dict(sorted(Counter((item.season // 10) * 10 for item in sample).items()))}")
    _render(sample, "verifier")
    report(run(sample))


if __name__ == "__main__":
    main()
