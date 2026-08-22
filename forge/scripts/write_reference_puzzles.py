"""Six real puzzles, all the way through the pipeline and onto disk.

**The first publishable artefact this project has produced.** Everything before it measured.

Pool -> erasure -> four validation layers -> signed package -> file, and then read back from the file
and verified again with the real secret. A package that validates in the process that made it and
fails when read from disk is precisely the class of defect this project keeps finding, so the round
trip is the point rather than a formality.

They exist so `serve` has something real to build against from day one instead of invented data.
Spread across the chain 5-11 curve and across decades, and they include the two cases **the client has
to be able to draw**: a suffixed label and a live footnote.

⚠️ **This said "the two cases the tutorial has to teach" and the tutorial reads none of this.**
(v37-P3-04, reissued as v38-P3-02) `tutorial-main.js` fetches nothing — no package, no manifest, no
network — so the requirement was true when the tutorial was going to be built on real data and stopped
being true when it was not. What the two traits are actually for is **rendering coverage**: a reference
set with no suffixed label and no live footnote leaves two of the board's shapes undrawn by anything.

Read-only against DGL. Run from `forge/`.
"""

import hashlib
import json
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
# ⚠️⚠️ **`discovery/` is off this path as of 2026-08-22, and that is the point of the change.** Two
# inserts used to be here: `difficulty-metrics` for the loader, now `boxscore_forge.pool`, and
# `verifier`, which **nothing in this file has ever imported** — a dead insert that made the boundary
# look crossed when it was not, and would have quietly re-enabled the crossing for whoever added the
# next import. The publication path reaches nothing outside `forge/src` now.
sys.path.insert(0, str(_ROOT / "forge" / "src"))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

from boxscore_domain import ZERO_DENSITY_GATE  # noqa: E402

# ⚠️ **The loader lives in `boxscore_forge.pool` since 2026-08-22** (`docs/beta-0-plan.md`, A1). It used
# to be `from measure import Loaded, load`, reaching into `discovery/difficulty-metrics` — so the path
# that writes signed packages ran through a research script, outside `mypy --strict` and inside the
# ratcheted lint tree, where any cleanup could break publishing.
#
# The deferral was recorded here with its reason: moving it is **building the inventory pipeline**, not
# renaming a module. That is what this is. `measure` re-exports every name, so the 33 discovery scripts
# that import them are untouched.
from boxscore_forge.pool import Loaded, load  # noqa: E402

# ⚠️ **`produce` was `build()` in this file and is now the only definition of it** (`docs/beta-0-plan.md`,
# A2). The batch producer that fills the calendar needs the same per-board core, and two copies of *how a
# package is made* is the shape this project meets most often. `reveal_for`, `required_boxscore` and
# `evidence_for` went with it: each is a fact about a loaded direction rather than about this script.
from boxscore_forge.produce import Attempt, evidence_for, produce  # noqa: E402

# ⚠️ **Where the key comes from is stated once, in `boxscore_forge.publication_key`.** These three
# constants and the pinned check were declared here and the batch producer needed all of them; two
# copies of *which file holds the private key* is the one duplication in this repository that fails as
# a five-month outage rather than as a bug.
from boxscore_forge.publication_key import (  # noqa: E402
    KEY_FILE,
    KEY_VARIABLE,
    publication_key,
)
from boxscore_package.format import Package, read, write  # noqa: E402
from boxscore_package.signing import sign_manifest  # noqa: E402
from boxscore_verify.certify import certify_for_publication  # noqa: E402

NOTE = "reference data for serve, not inventory"
"""What these packages say they are. ⚠️ **A parameter of `produce` now**, because the batch producer
writes real inventory and must not inherit a note calling itself reference data."""

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
# ⚠️⚠️ **The decided gate, not a stricter literal.** (v36-P3-36) This read `GATE = 0.25` with no note,
# no measurement and no `PROVISIONAL` marker — everything `docs/python-conventions.md` requires of a
# value that shapes the product, absent from a value that shapes which boards `serve` is built against.
# `ZERO_DENSITY_GATE` is 0.30 and is marked *measured, decided*.
#
# ⚠️ **The literal-copy guard could not see it**, because 0.25 is a *different number for the same
# knob* rather than a copy of the same one. That is the drift the guard is blind to by construction.
#
# ⚠️ **The six packages were drawn under 0.25 and were redrawn under this gate on 2026-08-21**, which
# is what closed the consequence rather than only the cause. (v37-P3-04) The batch is materially
# different: median zero density 21% → 29%, with five of the six above the old set's maximum, and the
# largest roster 10 batters → 12. The client had been developed and its layout judged against boards
# **less zero-heavy than the ones that ship**, which is why regenerating came before building more of
# `serve` on top. Recorded in `docs/reviews/todo.md` and in `docs/serve-brief.md`.
#
# ⚠️⚠️ **The provenance is not in the artefact, and a comment cannot fix that.** Nothing in a published
# package says which gate drew it, so this paragraph is the only record and it goes stale the moment
# the batch is redrawn again — which is exactly how it came to be wrong. **Recording the gate in the
# package metadata is the durable answer** and is recorded as an open decision, not taken here.
#
# ⚠️ `SEED` moved to `boxscore_forge.produce` with the core that uses it, and is imported above rather
# than declared twice. §21 needs it fixed: a seed that varied per run would make the same game yield a
# different puzzle, which is the double idempotence rule broken at its root.
OUT = _ROOT / "serve" / "data" / "puzzles"
EPHEMERAL_OUT = _ROOT / "discovery" / "ephemeral-puzzles"
"""Where a throwaway batch goes. **Outside `serve/`**, so an untrusted writer mode cannot
change the trusted namespace at all — which is stronger than a reader that refuses it."""

MANIFEST = "manifest.json"


def _hardest_unused_target(loaded: Loaded, key: Ed25519PrivateKey, taken: set[int]) -> Package | None:
    """Ask the board how hard it can be, and take the first target no other board has claimed.

    ⚠️ **Ask rather than tell.** Counting down from the ceiling takes each board's own maximum, and
    `taken` keeps the six boards at six different rungs — six copies of the easiest one would be a
    reference set that exercises nothing.

    ⚠️ **The refusal is printed here and returned by `produce`.** It used to be printed inside the core,
    which is a script's interface in a library — and it discarded which check refused how often, which
    is the number a batch run is sized from.
    """
    for target in range(CEILING, 0, -1):
        if target in taken:
            continue
        attempt: Attempt = produce(loaded, target, key, note=NOTE)
        if attempt.refusals:
            print(f"  refused {loaded.game_id} at {target} stalls: {'; '.join(attempt.refusals)}")
        if attempt.package is not None:
            taken.add(target)
            return attempt.package
    return None


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


def _traits_survived(published: list[Package]) -> None:
    """⚠️⚠️ **Two rendering cases the shipped batch must contain, asserted over what shipped.** (v36-P2-06)

    `_choose` puts a board with a suffixed label and a board with a live footnote into the *candidate*
    list, and this module's docstring promises the published six carry both. The write loop then
    discards any candidate that reaches no target — with a `print` — and that docstring itself records
    that **two of six candidates produced no puzzle at any target from 12 down**. So the promise held
    over twelve candidates and nothing held it over the six files.

    This project's rule: **anything acting as a launch gate is asserted, not printed** — and `_choose`'s
    selection is exactly a promise printed and believed.

    ⚠️⚠️ **This said "the two cases *the tutorial* has to teach" and the tutorial reads none of this.**
    (v37-P3-01) `tutorial-main.js` fetches nothing at all — no package, no manifest, no network — and
    teaches on a made-up four-batter board, which is deliberate and recorded there: the one screen a
    stranger is most likely to open first is the one with nothing to go wrong. **The justification was
    true when the tutorial was going to be built on real data and stopped being true when it was not**,
    and a stale reason in a gate's own docstring is worse than none: v37's reviewer read it, believed
    the tutorial depended on this, and filed a fragility finding about a dependency that does not exist.

    **Who actually needs these boards is the client and its suite.** `serve/tests/engine.test.js`
    searches the shipped packages for one with a live footnote total in three places, and
    `board.js`'s substitution indentation keys off a slot reference longer than one character — so a
    batch with neither trait leaves both paths unexercised against real data. That is a rendering
    coverage requirement, not an editorial one.

    ⚠️⚠️ **One of each is the floor, and it stays at one — decided by the operator on 2026-08-21.**
    Today the batch carries **three** boards with a shared slot and **five** with a live footnote; a
    previous batch carried exactly one of the first, which is what made this worth asserting at all.

    Raising it to two was proposed by `v37-P3-01` and **rejected**, for the reason the proposal works
    against: a higher floor makes the writer **refuse more often**, and the concern behind the proposal
    was fragility. It would also be a third quota over six boards that already carry
    one-direction-per-game and distinct stall targets — and `CLAUDE.md` records a weighted sample
    producing **zero** boards at a rung under exactly that pressure.

    Raised before `_publish`, so a batch missing either trait leaves the published set untouched —
    **loudly, and with the previous generation still serving.** A collapse here is a refusal to
    publish, never a silent publication.
    """
    # ⚠️⚠️ **A *suffixed* reference, and the first version of this check could not fail.** It asked
    # whether `slot_references` was present and non-empty — but `Package.__post_init__` already refuses
    # a package without one per batting row, so that was true of every board ever written. A gate that
    # fires on nothing is the same defect as one that fires on everything, and it was written into the
    # gate closing a finding about promises nobody verifies.
    #
    # The trait is a lineup slot shared by two rows, which the reference marks by suffixing: `5a`, `5b`
    # against a plain `5`. ⚠️ This said **exactly one of the six** carries it, which was true of the
    # batch drawn under the old gate and is not true of the current one — three of six do. A count in a
    # comment goes stale the first time the batch is redrawn; what is asserted below is the floor.
    with_slot = [one for one in published if any(not ref.isdigit() for ref in one.slot_references or ())]
    with_footnote = [
        one for one in published if any(value for row in one.solution.footnotes for value in row if value is not None)
    ]
    missing = []
    if not with_slot:
        missing.append("no board carries a shared slot reference (the suffixed-label case)")
    if not with_footnote:
        missing.append("no board carries a live footnote term")
    if missing:
        message = (
            f"the written batch of {len(published)} does not cover the client rendering traits the "
            f"reference set exists to exercise: " + "; ".join(missing) + " - published set left as it was"
        )
        raise SystemExit(message)


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


def refuse_second_direction(games: dict[str, str], game_id: str, name: str) -> None:
    """One game, one puzzle — stated about the batch that was actually written.

    ⚠⚠ **From schema 5 the reveal prints both clubs**, and the other club's half is the other
    direction of that game, which §5 makes a second board. Publishing both hands the second one away
    inside the first one's reveal. The pool is 400,000+ directions, so spending a whole game on each
    board costs nothing measurable.

    ⚠️ **`claim` already refuses a repeated game, and that is not this check.** `claim` decides what
    goes into the candidate list; this decides what may be published. A rule applied during selection
    is not a check performed at the boundary — a caller assembling a batch another way bypasses the
    first and never learns it did. Same rule, two places, on purpose: one filters and one refuses.

    ⚠️ **And it has nowhere better to live yet.** The calendar is what will really own this, because
    the rule is about everything ever published rather than about one batch, and there is no calendar.
    Recorded in CLAUDE.md so the obligation is waiting when it is built.
    """
    if game_id in games:
        message = (
            f"{name} and {games[game_id]} are both directions of {game_id}. From schema 5 each "
            "reveal prints both clubs, so publishing both gives one of the two puzzles away."
        )
        raise SystemExit(message)
    games[game_id] = name


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
    exported = os.environ.get(KEY_VARIABLE, "")

    # ⚠️ **The variable, then the file** (v36-P3-29). An export is a deliberate act and keeps winning;
    # the file is where the key lives, so a publish needs no export at all and the key can stop being
    # inherited by every process on the machine. See `KEY_FILE`.
    #
    # ⚠️ **`--ephemeral` weighs only the variable, and the asymmetry is the point.** The refusal below
    # exists so the script never guesses which trust domain was meant — and an export says *publish for
    # real* where a file in the home directory says only *this is where the key is kept*. Weighing the
    # file too would make `--ephemeral` impossible on the one machine that has a key.
    material = exported
    if not material and not ephemeral and KEY_FILE.exists():
        try:
            material = KEY_FILE.read_text(encoding="utf-8").strip()
        except OSError as error:
            # Fail closed and say which file. An unreadable key file falling through to "unset" would
            # report the wrong problem and invite exporting the secret to work around it.
            message = f"{KEY_FILE} exists and could not be read: {error}"
            raise SystemExit(message) from error

    if ephemeral and exported:
        message = (
            f"--ephemeral was given and {KEY_VARIABLE} is set. Refusing to guess which trust "
            "domain was meant: unset the variable for a throwaway batch, or drop the flag to publish."
        )
        raise SystemExit(message)
    if not material and not ephemeral:
        message = (
            f"no signing key: {KEY_VARIABLE} is unset and {KEY_FILE} does not exist. Publishing needs "
            "the forge's private key, 64 hex characters. Pass --ephemeral to write a throwaway batch "
            "outside the served directory."
        )
        raise SystemExit(message)

    if ephemeral:
        key = Ed25519PrivateKey.generate()
        print("=" * 78)
        print("EPHEMERAL — a pair generated for this run, into a directory serve does not read.")
        print(f"public half: {key.public_key().public_bytes_raw().hex()}")
        print("=" * 78)
        return key, EPHEMERAL_OUT

    # ⚠️ **The pinned check lives in `boxscore_forge.publication_key` now**, because the batch producer
    # needs the same rule and *where the key comes from* is the one duplication here that fails as a
    # five-month outage rather than as a bug. This function keeps what is genuinely its own: choosing
    # the destination, and the `--ephemeral` trust domain.
    return publication_key(), OUT


def main() -> None:
    key, out = key_and_destination()
    sample = load(4, gated=True, gate=ZERO_DENSITY_GATE)

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
    games: dict[str, str] = {}
    # ⚠️ The packages that reached disk, kept so the batch can be checked rather than assumed. See the
    # assertion after this loop: `wanted` is the candidate list and is not what ships.
    published: list[Package] = []
    for loaded in wanted:
        if written == REFERENCE_BOARDS:
            break
        package = _hardest_unused_target(loaded, key, taken)
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

        refuse_second_direction(games, loaded.game_id, path.name)

        published.append(restored)
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

    _traits_survived(published)

    # ⚠️ `written` counts successful builds and `_publish` counts files. They used to be the same
    # number by assumption, and the assumption is exactly what a collision breaks: two builds, one
    # file, and a counter that says six.
    generation = _publish(staging, REFERENCE_BOARDS, key, out)
    print(f"{written} puzzles in {out / generation}, committed by replacing {MANIFEST}")


if __name__ == "__main__":
    main()
