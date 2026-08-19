"""Is an unassigned footnote resolvable? Three separate questions, per group size and term count.

⚠️ **Stall count says how often a player has to think. It does not say whether the thing to think
about can be resolved.** Different problems, and only the second can leave a board underivable, which
§22 forbids.

⚠️ **This instrument has been wrong three times, in three different ways, and each fault made a number
look like a finding.** They are worth stating because the shape recurs rather than the bug:

  **A metric that could not vary.** Blockage hid the group and left every other cell given, so every
  deduction was a hidden cell and nothing could depend on them. It read `0%` on every board and was
  reported as *the assignment never blocks the rest of the board*.

  **A metric that could not fire where it mattered.** The counterfactual's baseline removed every cell
  in `erased`, and footnote cells **are** erasable — so when the sampled erasure had already hidden the
  group, baseline and treatment were the same board. Blockage was forced false on exactly the published
  states the question is about.

  **Denominators that did not match their questions.** Derivability counted ambiguous groups as
  failures, unmeasured trials counted as negatives, and which population a table used was decided by
  the *title string* of its heading.

What follows from that is the shape of this file: the measurements are pure functions in `metrics.py`
so a test can call the production predicate, and each row of the report carries its own eligibility
rule as a callable rather than inferring one from display copy.

Read-only against DGL. Run from `forge/`.
"""

import contextlib
import hashlib
import io
import json
import os
import secrets
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))

from measure import Loaded, load  # noqa: E402
from metrics import completions, derivable, stops_progress, uses_the_group  # noqa: E402

from boxscore_forge.constraints import cell_values, footnote_cell, shape_of  # noqa: E402
from boxscore_forge.erasure import erase  # noqa: E402
from boxscore_forge.identities import FOOTNOTE_COLUMNS, find_violations  # noqa: E402
from boxscore_forge.publish import to_board  # noqa: E402

SAMPLE_PER_DECADE = 20
GATE = 0.25
SEEDS = (907, 908, 909)
"""⚠️ **One erasure per board is one sample, not a rate.** Whether a group gates progress depends on
which cells are blank, and the erasure decides that. Third instance of that shape, after the stall
ceiling from one greedy path and open-against-given from one ordering — and the first corrected before
the number had been believed rather than after.

**Only blockage needs them.** Completions and derivability are read off the complete board with the
group hidden, so they cannot move with the seed."""

TARGET_STALLS = 8
COLUMNS = (0, 1, 2, 3, "4+")
RESULT_SCHEMA = 5
"""Which contract an artifact was written under. A reader of an old file needs to know.

⚠️ **This has to move when the *identity* contract moves, not only when a metric does.** Schema 4
digested the tracked paths from a second command and wrote eight-hex tree digests; schema 5 takes them
from the diff itself and writes sixteen. Two files claiming schema 4 with different field widths would
be two contracts under one number, which is what the version exists to prevent.
"""


@dataclass(frozen=True)
class Group:
    """One slot group on one board. Every field is a separate question."""

    rows: int
    terms: int
    completions: int
    derivable: bool
    trials: int
    """Erasures that reached the target. Zero means **unmeasured**, which is not the same as negative:
    a board that resists erasure is not a random draw, so counting it as a negative biases the rate
    downward and selectively."""

    stopped: int
    used: int


@dataclass(frozen=True)
class Coverage:
    """Run-level accounting, which is not the same as the group-trial denominator.

    ⚠️ **`erase` is called once per direction and seed, before the direction becomes slot groups.**
    Reporting `len(groups) * len(SEEDS)` as *erasures attempted* counted group-erasure evaluations,
    and summing `group.trials` reported one successful erasure once per group on its board — so a
    direction with nine groups claimed nine successes for one call. The repeated count is the right
    denominator for a per-group per-erasure rate and the wrong measure of how often the eraser worked.
    """

    directions: int = 0
    attempted: int = 0
    reached: int = 0

    def plus(self, attempted: int, reached: int) -> "Coverage":
        return Coverage(self.directions + 1, self.attempted + attempted, self.reached + reached)


def groups_in(loaded: Loaded) -> tuple[list[Group], int]:
    direction = loaded.direction
    shape, values = shape_of(direction), cell_values(direction)
    by_slot: dict[int, list[int]] = defaultdict(list)
    for index, slot in enumerate(loaded.slots):
        by_slot[slot].append(index)

    drawn = [erase(direction, target_stalls=TARGET_STALLS, seed=seed) for seed in SEEDS]
    erasures = [puzzle.erased for puzzle in drawn if puzzle is not None]

    found: list[Group] = []
    for indexes in by_slot.values():
        terms = sum(
            getattr(direction.batter_footnotes[index], column) for index in indexes for column in FOOTNOTE_COLUMNS
        )
        hidden = frozenset(footnote_cell(index, column) for index in indexes for column in FOOTNOTE_COLUMNS)
        found.append(
            Group(
                rows=len(indexes),
                terms=terms,
                completions=completions(to_board(direction, hidden)),
                derivable=derivable(shape, values, hidden),
                trials=len(erasures),
                stopped=sum(stops_progress(shape, values, erased, hidden) for erased in erasures),
                used=sum(uses_the_group(shape, values, erased, hidden) for erased in erasures),
            )
        )
    return found, len(erasures)


@dataclass(frozen=True)
class Row:
    """One question: which groups it is about, and what it counts.

    ⚠️ **Eligibility is a callable, not a string test on the heading.** It used to be inferred from
    whether the title began with `DERIVABLE` or `HIDING`, so renaming a heading silently restored the
    unconditional denominator. Display copy deciding statistics is the same defect as formatting
    deciding a domain rule, which this project has already had three times.
    """

    title: str
    note: str
    eligible: Callable[[Group], bool]
    numerator: Callable[[Group], int]
    denominator: Callable[[Group], int]


ROWS = (
    Row(
        "EXACTLY ONE COMPLETION",
        "is the assignment ambiguous at all — a property of the board, not of a technique",
        lambda _: True,
        lambda group: int(group.completions == 1),
        lambda _: 1,
    ),
    Row(
        "DERIVABLE, AMONG THOSE WITH ONE COMPLETION",
        "conditional: ambiguous groups are not failures of the solver and are not counted as such",
        lambda group: group.completions == 1,
        lambda group: int(group.derivable),
        lambda _: 1,
    ),
    Row(
        "TRIALS WHERE HIDING IT STOPPED OUTSIDE PROGRESS",
        "per trial, not per group: exposure varies because not every seed reaches the target",
        lambda group: group.trials > 0,
        lambda group: group.stopped,
        lambda group: group.trials,
    ),
    Row(
        "TRIALS WHERE SOME OUTSIDE DEDUCTION USED IT",
        "a weaker claim than blocking, on the same denominator so the two can be compared",
        lambda group: group.trials > 0,
        lambda group: group.used,
        lambda group: group.trials,
    ),
)


def _cohort(cells: dict, rows: int, terms: object) -> list[Group]:
    if terms == "4+":
        return [g for key, here in cells.items() if key[0] == rows and key[1] >= 4 for g in here]  # noqa: PLR2004
    return cells.get((rows, terms), [])


def report(groups: list[Group], coverage: "Coverage") -> None:
    cells: dict[tuple[int, int], list[Group]] = defaultdict(list)
    for group in groups:
        cells[(group.rows, group.terms)].append(group)
    seen = sorted({group.rows for group in groups})
    header = f"{'rows':>5}" + "".join(f"{f'{t} terms' if t != 1 else '1 term':>18}" for t in COLUMNS)

    for row in ROWS:
        print("")
        print(f"=== {row.title} ===")
        print(f"  {row.note}")
        print(header)
        for rows in seen:
            line = f"{rows:>5}"
            for terms in COLUMNS:
                here = [g for g in _cohort(cells, rows, terms) if row.eligible(g)]
                over = sum(row.denominator(g) for g in here)
                under = sum(row.numerator(g) for g in here)
                line += f"{f'{under / over:.0%} [{under}/{over}]' if over else '-':>18}"
            print(line)

    print("")
    print("=== COVERAGE, SO THE DENOMINATORS CAN BE READ ===")
    print(
        f"  erasures: {coverage.attempted} attempted over {coverage.directions} directions, "
        f"{coverage.reached} reached {TARGET_STALLS} stalls"
    )
    print(f"  group-erasure trials: {sum(g.trials for g in groups)} — the blockage denominator, which")
    print("    repeats each successful erasure once per group on its board and is not an eraser count")
    print(f"  groups with no successful erasure: {sum(1 for g in groups if g.trials == 0)} — excluded")
    print(f"  ambiguous groups (more than one completion): {sum(1 for g in groups if g.completions > 1)}")
    print(f"  {len(groups)} slot groups from {coverage.directions} directions")

    print("")
    print("=== THE CONTROL, AT A FIXED TERM COUNT ===")
    print("  One row with two terms is not ambiguous at all. Comparing `>= 2` against `>= 2` mixed")
    print("  populations of different composition, so a difference could be volume or assignment.")
    for terms in (2, 3):
        one, two = _cohort(cells, 1, terms), _cohort(cells, 2, terms)
        if one and two:
            print(
                f"  {terms} terms: one row {sum(g.completions == 1 for g in one) / len(one):.0%} unique "
                f"[{len(one)}], two rows {sum(g.completions == 1 for g in two) / len(two):.0%} [{len(two)}]"
            )
        else:
            print(f"  {terms} terms: one row [{len(one)}], two rows [{len(two)}] — too few to compare")


@dataclass(frozen=True)
class RunIdentity:
    """What produced a run, captured **before** it and frozen.

    ⚠️ **The stamp used to be assembled after every board had been measured**, from whatever was on
    disk by then. A long database experiment gives ample time for `measure.py`, the branch or the
    working tree to change, so the artifact recorded the end-of-run state rather than the code that
    had already been loaded and executed — the exact mid-run change this mechanism exists to expose.

    ⚠️ **And it named no input.** A direction count is not the data: the database can change while the
    revision and the source hash stay identical, producing a different sample under the same
    provenance.

    ⚠️ **Then it digested the identifiers instead of the boards.** `game_id:offense_team` is a *label*.
    Every batting, footnote and pitching value, every lineup slot — everything `groups_in` actually
    reads — could change under the same label and the digest would not move. That is the project's own
    failure shape one level in: a check that cannot distinguish, reporting as though it had. The digest
    now covers exactly what the measurement consumes, per direction, and the per-direction digests are
    **rendered in the artifact** so the aggregate can be checked rather than trusted.
    """

    revision: str
    tracked_changes: str
    untracked: str
    instrument: str
    inputs: str = "not yet loaded"
    directions: tuple[tuple[str, str], ...] = ()
    """`(identifier, digest)` per direction, sorted. The aggregate alone says two runs differ; these
    say *which board* differs, which is the difference between a signal and an actionable one."""

    @property
    def publishable(self) -> bool:
        """⚠️ **Either repository question failing is a refusal.** Only `revision unknown` used to
        block, so a failed `git status` published a result that could not say whether an untracked
        file had shadowed an imported dependency."""
        return "unknown" not in (self.revision, self.tracked_changes, self.untracked)

    def with_inputs(self, sample: list[Loaded]) -> "RunIdentity":
        """Digest every board by its **contents**, immediately after `load()` and before measuring."""
        per_direction = tuple(sorted((f"{item.game_id}:{item.offense_team}", _board_digest(item)) for item in sample))
        aggregate = hashlib.sha256("".join(a + b for a, b in per_direction).encode()).hexdigest()[:12]
        return replace(self, inputs=aggregate, directions=per_direction)


def _board_digest(item: Loaded) -> str:
    """Exactly what `groups_in` reads off a board, canonically serialised.

    ⚠️ **Scoped to what the measurement consumes, not to everything the loader carries.** `groups_in`
    reads `cell_values(direction)` and `loaded.slots` and nothing else, so those are what determine the
    result and those are what the digest covers. Widening it to names, teams or source flags would make
    the digest move for reasons that cannot change a number, which is how a check becomes noise.
    """
    canonical = json.dumps(
        {"cells": cell_values(item.direction), "slots": list(item.slots)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def identify() -> RunIdentity:
    """Read the world once, at the top of the run, before anything is measured."""
    # ⚠️ **A status line is not a file's contents.** `_describe` hashed the porcelain output, so two
    # different edits to the same path produced the same digest — the same defect as digesting an
    # identifier instead of a board, in the field next to it. Tracked edits are digested from the diff
    # and untracked files from their bytes.
    # ⚠️ **The tracked paths come out of the diff itself, not out of a second command.** Status and
    # diff are two observations of a mutable tree: v15 refused the one contradiction it could see
    # (no paths, non-empty diff) and accepted every other mixed pair without proving the two came from
    # one state. One snapshot cannot contradict itself, so the contradiction stops being detectable
    # and starts being impossible.
    diff = _git_bytes("diff", "--binary", "HEAD")
    # Untracked files are invisible to `diff` by definition, so this question keeps its own command.
    # It is still two observations — the listing and the bytes — and that residue is recorded rather
    # than solved, because solving it means running the worker from an immutable snapshot.
    listed = _porcelain_paths(_git_bytes("status", "--porcelain", "-z", "--untracked-files=all"))
    if diff is None or listed is None:
        tracked = untracked = "unknown"
    else:
        # ⚠️ Untracked and modified were counted together and both labelled `+untracked`, so an
        # ordinary edit read as an unknown file. Two questions, two answers.
        untracked_paths = listed
        tracked = _describe(_diff_paths(diff), diff)
        untracked = _describe(untracked_paths, _bytes_of(untracked_paths))
    return RunIdentity(
        revision=_git("rev-parse", "--short", "HEAD"),
        tracked_changes=tracked,
        untracked=untracked,
        instrument=source_hashes(),
    )


def _describe(paths: list[str], contents: bytes | None) -> str:
    """`clean`, or a count with a digest over the paths **and the bytes that changed**.

    ⚠️ **`clean` was returned whenever the path list was empty, whatever the contents said.** The paths
    and the bytes come from two commands against a mutable tree, so `git status` can report nothing
    tracked while `git diff` carries a change made between the two calls — and the artifact then said
    *clean* over a run that used an edited solver. **A contradiction between the two is not a clean
    tree; it is an unreadable one**, and the whole point of this field is that it fails closed.

    The two directions are not symmetric, and only one is dangerous. Contents without paths
    under-reports and is refused. Paths without contents over-reports and is kept, because a dirty
    digest over a tree that has since been restored costs nothing but an unnecessary rerun.
    """
    if contents is None:
        return "unknown"
    if contents and not paths:
        return "unknown"
    if not paths:
        return "clean"
    # ⚠️ Length-prefixed, and **sixteen** hex characters. Eight is 32 bits, which is small enough to
    # search by varying a disposable file until the displayed identity matches an approved one.
    preimage = b"".join(_record(path.encode("utf-8", "surrogateescape")) for path in sorted(paths))
    digest = hashlib.sha256(preimage + contents).hexdigest()[:16]
    return f"{len(paths)} files, {digest}"


def _bytes_of(paths: list[str]) -> bytes | None:
    """One canonical record per untracked file, or `None` if one could not be read.

    ⚠️ **An unreadable file used to become the literal marker `<unreadable>` and publish anyway**, so
    two different files nobody could read were one identity — a digest that cannot see the thing it
    names, reporting as though it had. Same rule as the diff: a failure to read is not a reading.

    ⚠️ **And the encoding was not injective.** Path bytes and file bytes were concatenated with no
    lengths and no separators, so `{a: b"b", bc: b""}` and `{ab: b"b", c: b""}` produced the same
    preimage, the same digest and the same `2 files` label — two different trees with one identity, no
    adversary required. Every field is now length-prefixed, which is what makes the encoding reversible
    in principle and therefore collision-free in practice.
    """
    blob = b""
    for path in sorted(paths):
        try:
            content = (_ROOT / path).read_bytes()
        except OSError:
            return None
        blob += _record(path.encode("utf-8", "surrogateescape")) + _record(content)
    return blob


def _record(field: bytes) -> bytes:
    """`<length>:<bytes>`. A length prefix is the whole difference between a digest and a guess."""
    return f"{len(field)}:".encode() + field


def _diff_paths(diff: bytes) -> list[str]:
    """The paths named by a `--binary` diff, taken from the snapshot the bytes came from.

    `diff --git a/<path> b/<path>` is the header of every file section. Reading the paths here rather
    than from a second `git status` is what makes the two halves of the tracked digest one observation.
    """
    prefix = b"diff --git a/"
    paths = []
    for line in diff.splitlines():
        if line.startswith(prefix):
            body = line[len(prefix) :]
            half = body.find(b" b/")
            paths.append(body[:half].decode("utf-8", "surrogateescape") if half > 0 else body.decode())
    return paths


def _porcelain_paths(raw: bytes | None) -> list[str] | None:
    """The untracked paths from `--porcelain -z`, or `None` when the command failed.

    ⚠️ **`-z` because porcelain quotes and escapes any path that needs it.** Sliced from the text form,
    `"src/a\tb.py"` arrives with its quotes attached, opens nothing, and used to become the
    `<unreadable>` marker. NUL-separated records are the only form that round-trips a filename, and
    `surrogateescape` keeps bytes git will not promise are UTF-8.
    """
    if raw is None:
        return None
    fields = raw.decode("utf-8", "surrogateescape").split("\0")
    untracked: list[str] = []
    index = 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        if status == "??":
            untracked.append(entry[3:])
            continue
        # A rename or a copy carries its source path as its own record. Nothing here needs the tracked
        # paths any more — they come from the diff — but the extra record still has to be consumed, or
        # a source path is read as the next status line.
        if ("R" in status or "C" in status) and index < len(fields):
            index += 1
    return untracked


def _git(*arguments: str) -> str:
    """Git output, or `unknown`. `unknown` is not publishable — see `main`."""
    try:
        return subprocess.run(  # noqa: S603
            ["git", "-C", str(_ROOT), *arguments],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return "unknown"


def _git_bytes(*arguments: str) -> bytes | None:
    """Git output undecoded, or `None` when the command failed.

    ⚠️ **`None` rather than `b""`, because empty output is a legitimate answer.** The first version of
    this asked `_git` for `diff --binary`, which returns bytes a text pipe cannot decode: the reader
    thread died, `stdout` came back `None` and the caller raised. Had it degraded one step more
    gracefully it would have returned an empty string — and an empty diff reads as *nothing changed*,
    so a failure to read the tree would have published a dirty tree as clean. That is this project's
    named failure shape: the absence of a check reading as the presence of a passing one.
    """
    try:
        return subprocess.run(  # noqa: S603
            ["git", "-C", str(_ROOT), *arguments],  # noqa: S607
            capture_output=True,
            check=True,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def source_hashes() -> str:
    """A digest of the code that actually decides, so a revision is not the only identity.

    A commit says what was committed. These say what ran — including files git has never heard of,
    which is the gap `--dirty` leaves open.
    """
    digest = hashlib.sha256()
    # ⚠️ **The loader belongs here.** It chooses the sample and builds every board, and it lives in a
    # sibling discovery directory rather than in `boxscore_forge` — so neither this hash nor the
    # revision's dependency graph reached it. Everything else the run touches is tracked, and the
    # tracked-changes digest is what covers those.
    sources = (_HERE / "measure.py", _HERE / "metrics.py", _ROOT / "discovery" / "difficulty-metrics" / "measure.py")
    for path in sorted(sources):
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def provenance(identity: "RunIdentity", coverage: "Coverage", groups: int, trials: int) -> str:
    """Render a `RunIdentity` and the run's coverage.

    ⚠️ **This function reads an identity; it no longer takes one.** It used to call `git` itself, at
    the end of a run that had already been going for hours — so the stamp described the tree as it
    stood when the last board finished, not the code that had been loaded and executed. Capturing is
    `identify()`, called first thing in `main`; this only formats what was captured.
    """
    return "\n".join(
        [
            "=== WHAT PRODUCED THIS ===",
            (
                f"  result schema      {RESULT_SCHEMA}   (1 could not vary; 2 could not fire; "
                f"3 digested labels; 4 mixed two git snapshots)"
            ),
            f"  revision           {identity.revision}",
            f"  tracked changes    {identity.tracked_changes}",
            f"  untracked files    {identity.untracked}",
            f"  instrument         sha256 {identity.instrument}   (hashed before the run)",
            f"  inputs             sha256 {identity.inputs} over {len(identity.directions)} directions, listed below",
            f"  sample             {coverage.directions} directions, {SAMPLE_PER_DECADE} per decade, gate {GATE:.0%}",
            (
                f"  erasures           {SEEDS} per direction; {coverage.reached} of "
                f"{coverage.attempted} reached {TARGET_STALLS} stalls"
            ),
            f"  group trials       {trials}   (each successful erasure once per group on its board)",
            f"  groups             {groups}",
            "  blockage           counterfactual, per trial; the baseline restores the group whatever",
            "                     the erasure did to it, so the only difference is the assignment",
            "  derivability       conditional on exactly one completion",
            "",
            "=== THE BOARDS THIS DIGEST COVERS ===",
            # ⚠️ The aggregate says two runs differ. Without the list it cannot say which board, and a
            # digest nobody can check is a claim rather than evidence.
            *(f"  {identifier:<20} {digest}" for identifier, digest in identity.directions),
            "COMPLETE",
        ]
    )


def _destination(argv: list[str]) -> Path:
    """`--output <path>`, or the canonical name. A missing value says so rather than raising."""
    if "--output" not in argv:
        return _HERE / "results.txt"
    index = argv.index("--output")
    if index + 1 >= len(argv):
        message = "--output needs a path"
        raise SystemExit(message)
    return Path(argv[index + 1])


def _refuse_unwritable(out: Path) -> None:
    """Prove the artifact can be written **before** the run, by writing.

    ⚠️ **`out.parent.is_dir()` is not writability.** A directory sitting at `out`, a read-only parent,
    a full disk — every one of them passes an existence test and fails five hours later inside
    `publish()`, which is exactly the operational cost `v14-P2-01` moved the provenance gate to avoid,
    one field over. The only check that answers the question is the operation itself.
    """
    if out.is_dir():
        message = f"{out} is a directory; the artifact cannot replace it"
        raise SystemExit(message)
    if not out.parent.is_dir():
        message = f"{out.parent} is not a directory; nothing this run produces could be published"
        raise SystemExit(message)
    probe = out.with_name(f"{out.name}.probe-{os.getpid()}-{secrets.token_hex(4)}")
    moved = probe.with_name(f"{probe.name}.moved")
    try:
        probe.write_bytes(b"")
        probe.replace(moved)
    except OSError as error:
        message = f"{out.parent} cannot be written to ({error}); this run could publish nothing"
        raise SystemExit(message) from error
    finally:
        probe.unlink(missing_ok=True)
        moved.unlink(missing_ok=True)
    if out.exists():
        _prove_replaceable(out)


def _prove_replaceable(out: Path) -> None:
    """Rename an existing destination away and back, which is the right `publish` actually needs.

    ⚠️ **Creating a sibling proves the directory, not the target.** `publish` ends in
    `pending.replace(out)`, and on Windows an existing `out` can be read-only, held open by another
    process without delete sharing, or carry an ACL of its own while a fresh sibling is created
    happily. That is the realistic case — a results file left open in an editor — and it failed only
    inside `publish`, hours later, which is the whole cost this preflight exists to avoid.

    Renaming the file away and back is the same right `replace` needs, and it is restored in `finally`
    so an interruption between the two leaves the file where it was.
    """
    aside = out.with_name(f"{out.name}.replaceable-{os.getpid()}-{secrets.token_hex(4)}")
    try:
        out.replace(aside)
    except OSError as error:
        message = f"{out} exists and cannot be replaced ({error}); this run could publish nothing"
        raise SystemExit(message) from error
    finally:
        if aside.exists():
            aside.replace(out)


def _refuse_unless_identified(identity: RunIdentity, *, expect_inputs: bool = False) -> None:
    """A result that cannot say what produced it is worse than no result: it occupies the name a
    decision gets read from. *Either* repository question failing is enough, since an untracked file
    can shadow an imported dependency without touching a commit."""
    if not identity.publishable:
        message = f"provenance is incomplete ({identity}); refusing to run"
        raise SystemExit(message)
    # The preflight cannot ask this — nothing is loaded yet — but the publication gate must, or a
    # stamp reading `inputs not yet loaded` would certify an artifact that names no data at all.
    if expect_inputs and not identity.directions:
        message = f"the identity names no inputs ({identity.inputs}); refusing to publish"
        raise SystemExit(message)


def publish(
    out: Path,
    text: str,
    pid: int | None = None,
    nonce: Callable[[], str] = lambda: secrets.token_hex(4),
) -> Path:
    """Write `text` to `out` through a staging file of its own, and return the path that was staged.

    ⚠️ **A fixed staging name is not a single-writer contract.** An atomic final rename protects the
    destination and not the preparation: two overlapping runs sharing `results.txt.pending` can
    truncate each other, or one can move the other's bytes into the canonical path. This is the same
    class already removed from the reference publisher, and a long run makes a duplicate launch
    operationally plausible rather than a timing curiosity.

    ⚠️ **Extracted so the claim can be tested rather than read.** Inline in `main`, behind a database
    sample and an hour of solving, neither the uniqueness of the staging name nor the cleanup on
    failure was reachable from a test — the only guard available was a grep for `getpid`, which is the
    shape of check this project has recorded failing five times. `pid` and `nonce` are parameters for
    the same reason: a test that cannot force a collision cannot show the name is what prevents one.

    Staged in `out`'s own directory, because `replace` is atomic only within a filesystem, and removed
    on either failure so an aborted publish leaves nothing partial beside the real file.
    """
    pending = out.with_name(f"{out.name}.pending-{os.getpid() if pid is None else pid}-{nonce()}")
    try:
        pending.write_text(text, encoding="utf-8")
        pending.replace(out)
    finally:
        pending.unlink(missing_ok=True)
    return pending


def main() -> None:
    out = _destination(sys.argv)
    identity = identify()
    # ⚠️ **Fail closed *before* the work, not after.** This check sat after the sample, three seeds of
    # erasure and every solve — hours of compute whose outcome was already decided, since nothing later
    # can repair an `unknown` repository field. A guaranteed-discarded run that looks like a
    # progressing experiment is worse than an immediate refusal.
    _refuse_unless_identified(identity)
    _refuse_unwritable(out)
    sample = [
        item
        for item in load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
        if not find_violations(item.direction)
    ]
    if not sample:
        message = f"no directions survived the {GATE:.0%} gate"
        raise SystemExit(message)
    identity = identity.with_inputs(sample)
    print(f"{len(sample)} gated directions", flush=True)

    groups: list[Group] = []
    coverage = Coverage()
    for number, item in enumerate(sample, start=1):
        found, reached = groups_in(item)
        groups.extend(found)
        coverage = coverage.plus(len(SEEDS), reached)
        if number % 20 == 0:
            print(f"  {number}/{len(sample)} boards, {len(groups)} groups", flush=True)
    if not groups:
        message = "no slot groups were produced; the sample carried no lineups"
        raise SystemExit(message)

    # ⚠️ The instrument owns its artifact. Shell redirection leaves a partial file at the canonical
    # path when a run is interrupted, and a partial file with no completion marker still occupies the
    # name a decision gets read from. Written aside and replaced, with `COMPLETE` as the last line.
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        report(groups, coverage)
        print("")
        print(provenance(identity, coverage, len(groups), sum(group.trials for group in groups)))
    text = captured.getvalue()
    # The second gate. `identify()` is frozen, so this cannot disagree with the first — it is here
    # because a publication path that trusts an earlier check is one refactor from having no check.
    _refuse_unless_identified(identity, expect_inputs=True)
    print(text)
    publish(out, text)
    print(f"written to {out}")


if __name__ == "__main__":
    main()
