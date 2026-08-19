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

import hashlib
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "discovery" / "verifier"))

from measure import Loaded, load, slot_references  # noqa: E402

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
MANIFEST = "manifest.json"

SECRET_VARIABLE = "BOXSCORE_SIGNING_SECRET"
FIXTURE_SECRET = b"reference-puzzles-only, replace before anything is published"
"""⚠️ **This key is in the repository, so anything signed with it is forged as easily as it is made.**

It used to be a silent fallback: no `BOXSCORE_SIGNING_SECRET` in the environment and the writer signed
with this anyway, into `serve/data/puzzles`, through the same certification path as a real batch. A CI
job or a developer running the script without the variable produced packages indistinguishable from
forge output, and nothing executable enforced the comment saying they were not production.

It is now reachable only through `--fixtures`, which is loud, and the environment secret is required
otherwise. A missing secret is an error, never a quieter mode.
"""
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
            slot_references=slot_references(loaded.slots),
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
    """What the producer knows and the package cannot say for itself.

    ⚠️ **`is_deduced` is the provenance row's own value now.** It used to be rebuilt here as
    `source_type.startswith("ED")`, which is a second copy of a rule the database already states — so a
    deduced record filed under an accepted source type would have passed §32's exclusion.
    """
    return Evidence(
        game_id=loaded.game_id,
        offense_team=loaded.offense_team,
        source_type=loaded.source_type,
        is_deduced=loaded.is_deduced,
        official_hits=loaded.official_hits,
        official_runs=loaded.official_runs,
        official_errors=loaded.direction.line_score.offense_errors,
        official_defense_runs=loaded.direction.line_score.defense_runs,
        official_defense_hits=loaded.direction.line_score.defense_hits,
        official_defense_errors=loaded.direction.line_score.defense_errors,
        official_at_bats=loaded.official_at_bats,
        official_left_on_base=loaded.official_left_on_base,
    )


def claim(wanted: list[Loaded], seen: set[str], item: Loaded) -> bool:
    """Take a direction for the batch, or refuse it because its game is already in.

    ⚠️ **The two required traits used to be taken first and deduplicated afterwards.** A direction can
    carry a substitution *and* a live footnote, and the two picks were appended before `seen` existed,
    so one game could enter the batch twice. Both entries derive the same identifier — §21 makes the
    identifier a function of the game and the batting team — so the second wrote over the first, and
    the counter said six because it was counting attempts rather than files.

    One entry point for every append, so a caller cannot forget the check by taking a different route.
    """
    if item.game_id in seen:
        return False
    seen.add(item.game_id)
    wanted.append(item)
    return True


def _choose(sample: list[Loaded], with_substitution: list[Loaded], with_footnote: list[Loaded]) -> list[Loaded]:
    """One direction per game, with both required traits present.

    Every append goes through `claim`, the two required traits included — one direction can carry a
    substitution *and* a live footnote, and taking them first and deduplicating afterwards is how the
    same game entered the batch twice.
    """
    wanted: list[Loaded] = []
    seen: set[str] = set()
    claim(wanted, seen, with_substitution[0])
    if not claim(wanted, seen, with_footnote[0]):
        following = next((item for item in with_footnote[1:] if item.game_id not in seen), None)
        if following is None:
            message = "only one game in the sample carries a live footnote and it is already in the batch"
            raise SystemExit(message)
        claim(wanted, seen, following)
    for item in sorted(sample, key=lambda entry: entry.season):
        if len(wanted) == len(TARGETS):
            break
        claim(wanted, seen, item)
    if len(wanted) != len(TARGETS):
        message = f"only {len(wanted)} distinct games in the sample, wanted {len(TARGETS)}"
        raise SystemExit(message)
    return wanted


def _generation(names: list[str], payloads: list[bytes]) -> str:
    """A name for the batch, derived from its contents.

    Deterministic on purpose: §21 wants regenerating to produce the same thing rather than a new
    thing, so an unchanged batch resolves to the same generation and republishing is a no-op. No clock
    is involved, which also keeps the run reproducible.
    """
    digest = hashlib.sha256()
    for name, payload in sorted(zip(names, payloads, strict=True)):
        digest.update(name.encode())
        digest.update(payload)
    return digest.hexdigest()[:12]


def _current_generation(manifest: Path) -> str:
    """The generation the published manifest names, or nothing if there is no readable manifest."""
    if not manifest.exists():
        return ""
    try:
        return str(json.loads(manifest.read_text(encoding="utf-8")).get("generation", ""))
    except (json.JSONDecodeError, OSError):
        # A manifest we cannot read names nothing we can protect. Retaining everything would be the
        # safe reading, but a directory that grows without bound is its own failure; the sweep below
        # keeps only what this run publishes.
        return ""


def _publish(staging: Path, expected: int) -> str:
    """Swap the whole batch in with one atomic rename, or leave the published set untouched.

    ⚠️ **Per-file renames cannot make a *batch* atomic, and the previous version claimed they could.**
    They fix truncation — a reader sees the old file or the new one, never half of one — and they fix
    the window where nothing is published. They do not fix a crash between the third file and the
    fourth, which leaves three puzzles from one generation beside three from another. Names cannot
    save it either: a puzzle's name is a function of its game, so a regenerated puzzle lands on top of
    its predecessor rather than beside it.

    So a generation is written to a directory of its own, which is immutable once complete, and the
    **manifest naming the current generation is replaced last**. That one rename is the commit. A
    reader follows the manifest and therefore sees a whole batch or the previous whole batch, and
    files no manifest names are ignored until they are swept.

    This is the contract `serve` will read against, and it is being set now because `serve` does not
    exist yet and nothing has to be migrated.
    """
    staged = sorted(staging.glob("*.json"))
    if len(staged) != expected:
        message = f"{len(staged)} staged files, wanted {expected} — published set left as it was"
        raise SystemExit(message)
    if len({path.name for path in staged}) != expected:
        message = "two staged puzzles share an identifier — published set left as it was"
        raise SystemExit(message)

    payloads = [path.read_bytes() for path in staged]
    generation = _generation([path.name for path in staged], payloads)
    home = OUT / generation
    if home.exists():
        # Same contents as a generation already on disk. §21's idempotence, arriving as a no-op.
        for path in staged:
            path.unlink()
        staging.rmdir()
    else:
        staging.replace(home)

    manifest = OUT / MANIFEST
    # ⚠️ **The pending file is named per process.** A fixed name is a collision point between two
    # publishers, and nothing here makes the single-writer assumption true.
    pending = OUT / f"{MANIFEST}.pending-{os.getpid()}"
    superseded = _current_generation(manifest)
    pending.write_text(
        json.dumps(
            {"schema": 1, "generation": generation, "puzzles": sorted(path.stem for path in staged)},
            indent=1,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    # The commit. Everything above this line can fail without changing what is published.
    pending.replace(manifest)

    # ⚠️ **The generation the manifest used to name is kept.** Replacing the manifest atomically stops
    # a reader seeing a torn pointer; it does not make *fetch the manifest* and *fetch a puzzle* one
    # transaction. A reader — or a CDN — holding the previous manifest asks for one of its puzzles
    # after the swap, and deleting that generation at commit time turns a normal release into a 404
    # for everyone mid-solve. A cached manifest stretches that window far past the rename.
    #
    # So the commit path collects nothing. One generation back is retained, and anything older is
    # swept on the *next* publish, by which time no live manifest can name it. Staging directories are
    # skipped entirely: they may belong to another process.
    keep = {generation, superseded}
    for stale in OUT.iterdir():
        if stale.is_dir() and stale.name not in keep and not stale.name.startswith("."):
            for leftover in stale.iterdir():
                leftover.unlink()
            stale.rmdir()
    return generation


def main() -> None:
    fixtures = "--fixtures" in sys.argv
    secret = os.environ.get(SECRET_VARIABLE, "").encode()
    if not secret:
        if not fixtures:
            message = (
                f"{SECRET_VARIABLE} is unset. Publishing needs the real key; there is no fallback. "
                "Pass --fixtures to sign with the repository key instead, which produces packages "
                "nobody may trust and everybody can forge."
            )
            raise SystemExit(message)
        secret = FIXTURE_SECRET
        print("=" * 78)
        print("FIXTURES MODE — signed with the key that lives in this repository.")
        print("These packages prove the format parses. They prove nothing about where they came from.")
        print("=" * 78)
    sample = load(4, gated=True, gate=GATE, max_batters=13, max_pitchers=4)

    with_substitution = [item for item in sample if len(set(item.slots)) < len(item.slots)]
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

    wanted = _choose(sample, with_substitution, with_footnote)

    # ⚠️ The last known-good set is not deleted first. A loader error, an exhausted candidate pool,
    # an interrupted process or a full disk used to leave `serve/data/puzzles` empty or half-written,
    # and the pattern would be unsafe to reuse for a real inventory pipeline. Everything is built and
    # certified in a sibling directory and the published set is replaced only once the batch is whole.
    OUT.mkdir(parents=True, exist_ok=True)
    staging = OUT / ".staging"
    if staging.exists():
        for leftover in staging.iterdir():
            leftover.unlink()
        staging.rmdir()
    staging.mkdir()

    written = 0
    for loaded, target in zip(wanted, TARGETS, strict=True):
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

    # ⚠️ `written` counts successful builds and `_publish` counts files. They used to be the same
    # number by assumption, and the assumption is exactly what a collision breaks: two builds, one
    # file, and a counter that says six.
    generation = _publish(staging, len(TARGETS))
    print(f"{written} puzzles in {OUT / generation}, committed by replacing {MANIFEST}")


if __name__ == "__main__":
    main()
