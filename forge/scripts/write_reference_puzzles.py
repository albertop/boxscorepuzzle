"""Six real puzzles, all the way through the pipeline and onto disk.

**The first publishable artefact this project has produced.** Everything before it measured.

Pool -> erasure -> four validation layers -> signed package -> file, and then read back from the file
and verified again with the real secret. A package that validates in the process that made it and
fails when read from disk is precisely the class of defect this project keeps finding, so the round
trip is the point rather than a formality.

They exist so `serve` has something real to build against from day one instead of invented data.
Spread across the chain 5-11 curve and across decades, and they include the two cases the tutorial
has to teach: a suffixed label and a live footnote.

Read-only against DGL. Run from `forge/`.
"""

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "discovery" / "verifier"))

from measure import Loaded, load  # noqa: E402

from boxscore_forge.erasure import erase  # noqa: E402
from boxscore_forge.identity import puzzle_id  # noqa: E402
from boxscore_forge.publish import to_board  # noqa: E402
from boxscore_package.format import Package, Reveal, read, write  # noqa: E402
from boxscore_package.signing import sign  # noqa: E402
from boxscore_verify.certify import Evidence, certify_for_publication  # noqa: E402

TARGETS = (5, 6, 7, 8, 9, 10)
"""Stall counts, not chain lengths.

Chain measures how long a solve is: a chain-10 board is ten subtractions in single file and one was
solved by hand in under a minute. A stall is the moment propagation runs dry and something beyond
direct substitution is needed. **No band is implied here** — these are six different boards for the
client to be built against, not a difficulty scale.
"""
GATE = 0.25
SEED = 6
OUT = _ROOT / "serve" / "data" / "puzzles"

SECRET_VARIABLE = "BOXSCORE_SIGNING_SECRET"
FALLBACK_SECRET = b"reference-puzzles-only, replace before anything is published"
"""A stand-in so this script runs without a configured environment.

It is **not** the publishing secret and must never become one. The real one arrives through the
environment; section 33's protection is worth nothing if the key that signs the inventory sits in the
repository. These six files are reference data for the client, not inventory.
"""


def reveal_for(loaded: Loaded) -> Reveal:
    """The answer to the mystery, which section 23 requires to be in the file."""
    # ⚠️ The teams come from the same query as the roster. `game_id[:3]` is the *home* club, and
    # labelling it as the offence is right only when the home side batted — which is how four of the
    # first six files claimed a lineup for a team it never played for. The names and the code have to
    # come from one source or nothing checks that they agree.
    return Reveal(
        batter_names=tuple(f"{first} {last}".strip() or "Unknown" for first, last in loaded.names),
        pitcher_names=tuple(f"{first} {last}".strip() or "Unknown" for first, last in loaded.pitcher_names),
        offense_team=loaded.offense_team,
        defense_team=loaded.defense_team,
        played_on=f"{loaded.game_id[3:7]}-{loaded.game_id[7:9]}-{loaded.game_id[9:11]}",
        card="",
    )


def build(loaded: Loaded, target: int, secret: bytes) -> Package | None:
    """Generate one puzzle and put it through the publication gate, not a subset of the checks."""
    produced = erase(loaded.direction, target_stalls=target, seed=SEED)
    if produced is None:
        return None
    package = sign(
        Package(
            puzzle_id=puzzle_id(loaded.game_id, loaded.offense_team),
            puzzle=to_board(loaded.direction, produced.erased),
            solution=to_board(loaded.direction, None),
            labels=loaded.labels,
            pitcher_labels=loaded.pitcher_labels,
            reveal=reveal_for(loaded),
            metadata={
                "note": "reference data for serve, not inventory",
                "difficulty_model": "stalls",
                "target_stalls": target,
                "stalls": produced.solution.stalls,
                # Descriptive telemetry. Chain is recorded because every earlier measurement used it
                # and they have to stay comparable — it is not what the board was selected on.
                "chain_length": produced.solution.chain_length,
                "blanks": len(produced.erased),
                "families": sorted(family.value for family in produced.solution.families_used),
                "batters": len(loaded.direction.batting),
                "pitchers": len(loaded.direction.pitching),
                "seed": SEED,
                "game_id": loaded.game_id,
                "season": loaded.season,
            },
        ),
        secret,
    )
    # ⚠️ The gate, not `verify()`. Assembling a subset of the checks at each call site is the defect
    # this boundary exists to remove, and this writer was one of the sites doing it.
    certified = certify_for_publication(package, evidence=evidence_for(loaded), secret=secret)
    if not certified.publishable:
        print(f"  refused {loaded.game_id} at {target} stalls: {'; '.join(certified.refusals)}")
        return None
    return package


def evidence_for(loaded: Loaded) -> Evidence:
    """What the producer knows and the package cannot say for itself."""
    return Evidence(
        source_type=loaded.source_type,
        is_deduced=loaded.source_type.startswith("ED"),
        official_hits=loaded.official_hits,
        official_runs=loaded.official_runs,
    )


def _publish(staging: Path) -> None:
    """Swap the staged batch in, one atomic rename at a time.

    ⚠️ **Replace first, delete afterwards.** `Path.replace` is an atomic rename within a filesystem, so
    a reader sees either the old file or the new one and never a truncated one. Deleting the published
    set first and then moving files in would leave a window with nothing published at all — the same
    defect one step smaller than the one the staging directory fixes.
    """
    written = set()
    for finished in staging.glob("*.json"):
        finished.replace(OUT / finished.name)
        written.add(finished.name)
    for stale in OUT.glob("*.json"):
        if stale.name not in written:
            stale.unlink()
    staging.rmdir()


def main() -> None:
    secret = os.environ.get(SECRET_VARIABLE, "").encode() or FALLBACK_SECRET
    sample = load(4, gated=True, gate=GATE, max_batters=13, max_pitchers=4)

    with_substitution = [item for item in sample if any("-" in label for label in item.labels)]
    with_footnote = [
        item
        for item in sample
        if any(
            note.hit_by_pitch or note.sacrifice_flies or note.sacrifice_hits or note.catcher_interference
            for note in item.direction.batter_footnotes
        )
    ]
    if not with_substitution or not with_footnote:
        message = "the sample carries no substitution or no live footnote; widen it"
        raise SystemExit(message)

    wanted = [with_substitution[0], with_footnote[0]]
    seen = {item.game_id for item in wanted}
    for item in sorted(sample, key=lambda entry: entry.season):
        if len(wanted) == len(TARGETS):
            break
        if item.game_id not in seen:
            seen.add(item.game_id)
            wanted.append(item)

    # ⚠️ The last known-good set is not deleted first. A loader error, an exhausted candidate pool,
    # an interrupted process or a full disk used to leave `serve/data/puzzles` empty or half-written,
    # and the pattern would be unsafe to reuse for a real inventory pipeline. Everything is built and
    # certified in a sibling directory and the published set is replaced only once the batch is whole.
    OUT.mkdir(parents=True, exist_ok=True)
    staging = OUT.parent / f"{OUT.name}.staging"
    if staging.exists():
        for leftover in staging.iterdir():
            leftover.unlink()
        staging.rmdir()
    staging.mkdir()

    written = 0
    for loaded, target in zip(wanted, TARGETS, strict=False):
        package = build(loaded, target, secret)
        if package is None:
            print(f"  discarded {loaded.game_id} at chain {target}")
            continue
        path = staging / f"{package.puzzle_id}.json"
        write(path, package.published())

        # The round trip. Read back from the file, not from the object that wrote it.
        restored = read(path)
        # The reveal is the payoff and no verifier layer can see it — a wrong team breaks no
        # equation. Checked here, on the file, for the same reason the round trip is.
        # The same gate on the way back in. A package that certifies in the process that made it and
        # fails when read from disk is the class of defect this project keeps finding.
        again = certify_for_publication(restored, evidence=evidence_for(loaded), secret=secret)
        if not again.publishable:
            message = f"{path.name} certified in memory and failed from disk: {'; '.join(again.refusals)}"
            raise SystemExit(message)
        if "game_id" in restored.metadata:
            message = f"{path.name} still carries game_id after publishing"
            raise SystemExit(message)

        written += 1
        print(
            f"  {path.name}  {restored.metadata['stalls']:>2} stalls "
            f"({restored.metadata['batters']}b/{restored.metadata['pitchers']}p)  "
            f"{len(restored.labels)} labels  verified from disk"
        )

    if written != len(TARGETS):
        # The staging directory is left behind deliberately: it is evidence of what the failed run
        # produced, and the published set is untouched.
        message = f"wrote {written} puzzles, wanted {len(TARGETS)} — published set left as it was"
        raise SystemExit(message)

    _publish(staging)
    print(f"{written} puzzles in {OUT}, each read back and verified with the real secret")


if __name__ == "__main__":
    main()
