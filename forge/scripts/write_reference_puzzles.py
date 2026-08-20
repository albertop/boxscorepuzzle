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

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from measure import Loaded, load, slot_references  # noqa: E402

from boxscore_forge.identity import puzzle_id  # noqa: E402
from boxscore_forge.lineup_fallback import erase_with_lineup_fallback  # noqa: E402
from boxscore_forge.publish import to_board  # noqa: E402
from boxscore_package.format import Package, Reveal, read, write  # noqa: E402
from boxscore_package.signing import sign, sign_manifest, signing_key  # noqa: E402
from boxscore_verify.certify import Evidence, certify_for_publication  # noqa: E402

REFERENCE_BOARDS = 6
CANDIDATES = 12
CEILING = 12
"""How many boards to publish, and the highest stall count worth attempting.

⚠️ **This used to be a fixed list — `(5, 6, 7, 8, 9, 10)` — with the *n*th game required to hit the
*n*th number, one attempt each.** Every one of the six was discarded the day the footnote cells went
back to given, because those numbers were chosen on a scale that counted the solver deducing zeros. On
the corrected scale only 54% of boards reach five stalls and 21% reach eight, so demanding a particular
board hit a particular number in one attempt fails almost always.

**So the writer no longer asserts a scale it cannot know.** It asks each board what it reaches, takes the
highest, and publishes boards with distinct counts. A stall is the moment propagation runs dry and
something beyond direct substitution is needed; **no band is implied** — these are six different boards
for the client to be built against, not a difficulty scale. The ladder is a separate thing and it waits
on the new scale, because its rungs were picked on the old one.
"""
GATE = 0.25
SEED = 6
OUT = _ROOT / "serve" / "data" / "puzzles"
EPHEMERAL_OUT = _ROOT / "discovery" / "ephemeral-puzzles"
"""Where a throwaway batch goes. **Outside `serve/`**, so an untrusted writer mode cannot
change the trusted namespace at all — which is stronger than a reader that refuses it."""

PINNED_PUBLIC_KEY = _ROOT / "serve" / "data" / "signing-public-key.hex"
MANIFEST = "manifest.json"

KEY_VARIABLE = "BOXSCORE_SIGNING_KEY"
"""The forge's Ed25519 private key, 64 hex characters, from the environment and never from here.

⚠️ **The fallback and the fixtures mode are gone rather than migrated.** Both existed because an
HMAC key is symmetric: a convenient one in the repository let the script run, and anything it
signed was forgeable by anyone holding the repository — so the mode had to be made loud and
guarded instead of removed.

With a key pair the problem dissolves. A **generated** key signs a throwaway batch perfectly well
and is worth nothing to an attacker, because the public half that would verify it goes nowhere.
`--ephemeral` does that and prints the public half; `serve` holds a different public key and
**refuses the batch itself**, instead of a comment asking to be believed.
"""


def reveal_for(loaded: Loaded) -> Reveal:
    """The answer to the mystery, which section 23 requires to be in the file."""
    # ⚠️ The teams come from the same query as the roster. `game_id[:3]` is the *home* club, and
    # labelling it as the offence is right only when the home side batted — which is how four of the
    # first six files claimed a lineup for a team it never played for. The names and the code have to
    # come from one source or nothing checks that they agree.
    return Reveal(
        # Composed by the loader, not here. ⚠️ This joined a `(first, last)` pair with
        # `.strip() or "Unknown"` while the prototype builder joined the same pair with neither — one
        # rule in two places, disagreeing about the players who have no given name on record.
        batter_names=loaded.names,
        pitcher_names=loaded.pitcher_names,
        offense_team=loaded.offense_team,
        defense_team=loaded.defense_team,
        played_on=f"{loaded.game_id[3:7]}-{loaded.game_id[7:9]}-{loaded.game_id[9:11]}",
        card="",
    )


def build(loaded: Loaded, target: int, key: Ed25519PrivateKey) -> Package | None:
    """Generate one puzzle and put it through the publication gate, not a subset of the checks.

    ⚠⚠ **The batting order is a fallback, not a switch.** Boards that reach their target without it
    never see it, so they never pay its cost: with the constraint on everywhere, a median of eight
    steps per board became *read the total, divide by nine, write it down* — 244 such cells across the
    walks measured. On the eleven directions that reach eight stalls only with it, nine carry no such
    filler at all. It is worth something exactly where the board cannot get there without it.
    """
    produced, why = erase_with_lineup_fallback(loaded.direction, tuple(loaded.slots), target_stalls=target, seed=SEED)
    del why  # The reason is for the measurement instruments; this script only needs the board.
    if produced is None:
        return None
    package = sign(
        Package(
            puzzle_id=puzzle_id(loaded.game_id, loaded.offense_team),
            puzzle=to_board(loaded.direction, produced.erased),
            solution=to_board(loaded.direction, None),
            labels=loaded.labels,
            slot_references=slot_references(loaded.slots),
            # From the loader, which reads it from the game rather than inferring it. A client cannot
            # know which club batted last, and one that guessed would be right only when the line
            # score happens to be ragged.
            offense_is_home=loaded.offense_is_home,
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
        key,
    )
    # ⚠️ The gate, not `verify()`. Assembling a subset of the checks at each call site is the defect
    # this boundary exists to remove, and this writer was one of the sites doing it.
    certified = certify_for_publication(package, evidence=evidence_for(loaded), secret=key.public_key())
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
        # ⚠️ **More candidates than boards, because some reach nothing at all.** With the footnote line
        # given, two of six candidates produced no puzzle at any target from 12 down — the writer used
        # to take exactly six and then be short. Taking a margin costs nothing: the surplus is simply
        # never built.
        if len(wanted) == CANDIDATES:
            break
        claim(wanted, seen, item)
    if len(wanted) < REFERENCE_BOARDS:
        message = f"only {len(wanted)} distinct games in the sample, wanted {REFERENCE_BOARDS}"
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


def _publish(staging: Path, expected: int, key: Ed25519PrivateKey, out: Path) -> str:
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
    home = out / generation
    if home.exists():
        # Same contents as a generation already on disk. §21's idempotence, arriving as a no-op.
        for path in staged:
            path.unlink()
        staging.rmdir()
    else:
        staging.replace(home)

    manifest = out / MANIFEST
    # ⚠️ **The pending file is named per process.** A fixed name is a collision point between two
    # publishers, and nothing here makes the single-writer assumption true.
    pending = out / f"{MANIFEST}.pending-{os.getpid()}"
    superseded = _current_generation(manifest)
    # ⚠️ **Signed.** `sign_manifest` existed and this wrote a plain dictionary — a check that exists
    # and is never invoked, one level above the code it protects. A signature per puzzle says each
    # puzzle is genuine; only this says the *set* is, and swapping the manifest for one that points at
    # a retained generation, omits ids or names nothing at all breaks no package signature.
    document = sign_manifest(
        {"schema": 1, "generation": generation, "puzzles": sorted(path.stem for path in staged)}, key
    )
    pending.write_text(json.dumps(document, indent=1, sort_keys=True), encoding="utf-8")
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
    for stale in out.iterdir():
        if stale.is_dir() and stale.name not in keep and not stale.name.startswith("."):
            for leftover in stale.iterdir():
                leftover.unlink()
            stale.rmdir()
    return generation


def key_and_destination() -> tuple[Ed25519PrivateKey, Path]:
    """The key this batch is signed with, and the only directory it is allowed to write.

    ⚠️ **The trust domain decides the destination, not a comment.** Both modes used to publish
    through the production `OUT`, so an `--ephemeral` run — which anyone able to execute the
    writer can start, no key theft required — replaced the live manifest with one signed by a key
    `serve` does not hold. `serve` refusing it preserves integrity and **not availability**: the
    inventory goes dark and the publisher reports a certified commit.

    ⚠️ **And a production key is checked against the one `serve` pins, before anything is written.**
    Self-verification used the public half of the key that had just signed, which proves the batch
    is internally consistent and nothing about whether the deployed reader will accept it. A valid
    Ed25519 key that is not *the* key produced exactly the same outage, by accident.
    """
    ephemeral = "--ephemeral" in sys.argv
    material = os.environ.get(KEY_VARIABLE, "")
    if ephemeral and material:
        message = (
            f"--ephemeral was given and {KEY_VARIABLE} is set. Refusing to guess which trust "
            "domain was meant: unset the variable for a throwaway batch, or drop the flag to publish."
        )
        raise SystemExit(message)
    if not material and not ephemeral:
        message = (
            f"{KEY_VARIABLE} is unset. Publishing needs the forge's private key, 64 hex characters. "
            "Pass --ephemeral to write a throwaway batch outside the served directory."
        )
        raise SystemExit(message)

    if ephemeral:
        key = Ed25519PrivateKey.generate()
        print("=" * 78)
        print("EPHEMERAL — a pair generated for this run, into a directory serve does not read.")
        print(f"public half: {key.public_key().public_bytes_raw().hex()}")
        print("=" * 78)
        return key, EPHEMERAL_OUT

    key = signing_key(material)
    pinned = PINNED_PUBLIC_KEY.read_text(encoding="utf-8").strip()
    offered = key.public_key().public_bytes_raw().hex()
    if offered != pinned:
        message = (
            f"{KEY_VARIABLE} does not match the key serve pins in {PINNED_PUBLIC_KEY.name}. "
            f"Publishing with it would replace the live manifest with one serve refuses, which is "
            f"an outage rather than a rejected file. Offered {offered[:16]}..., pinned {pinned[:16]}..."
        )
        raise SystemExit(message)
    return key, OUT


def main() -> None:
    key, out = key_and_destination()
    sample = load(4, gated=True, gate=GATE)

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
    out.mkdir(parents=True, exist_ok=True)
    staging = out / ".staging"
    if staging.exists():
        for leftover in staging.iterdir():
            leftover.unlink()
        staging.rmdir()
    staging.mkdir()

    # ⚠️ Ask the board rather than tell it. The highest target it reaches, and one board per count so
    # the six are actually different rather than six copies of the easiest rung.
    written = 0
    taken: set[int] = set()
    for loaded in wanted:
        if written == REFERENCE_BOARDS:
            break
        package = None
        for target in range(CEILING, 0, -1):
            if target in taken:
                continue
            package = build(loaded, target, key)
            if package is not None:
                taken.add(target)
                break
        if package is None:
            print(f"  discarded {loaded.game_id}: reached no target from {CEILING} down")
            continue
        path = staging / f"{package.puzzle_id}.json"
        write(path, package.published())

        # The round trip. Read back from the file, not from the object that wrote it.
        restored = read(path)
        # The reveal is the payoff and no verifier layer can see it — a wrong team breaks no
        # equation. Checked here, on the file, for the same reason the round trip is.
        # The same gate on the way back in. A package that certifies in the process that made it and
        # fails when read from disk is the class of defect this project keeps finding.
        again = certify_for_publication(restored, evidence=evidence_for(loaded), secret=key.public_key())
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

    if written != REFERENCE_BOARDS:
        # The staging directory is left behind deliberately: it is evidence of what the failed run
        # produced, and the published set is untouched.
        message = f"wrote {written} puzzles, wanted {REFERENCE_BOARDS} — published set left as it was"
        raise SystemExit(message)

    # ⚠️ `written` counts successful builds and `_publish` counts files. They used to be the same
    # number by assumption, and the assumption is exactly what a collision breaks: two builds, one
    # file, and a counter that says six.
    generation = _publish(staging, REFERENCE_BOARDS, key, out)
    print(f"{written} puzzles in {out / generation}, committed by replacing {MANIFEST}")


if __name__ == "__main__":
    main()
