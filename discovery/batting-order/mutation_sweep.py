"""Revert each claim of the batting-order work in turn, and require the suite to notice.

⚠⚠ **This exists because five review passes in a row found defects in code written minutes earlier,
and the reviewer was doing the checking I should have done.** Writing a guard is not the same as knowing
it guards anything, and the difference is one command.

It found one immediately: flipping the verifier's spread bound from `<= 1` to `== 1` — which would
reject every board whose plate appearances divide evenly by nine — left the whole suite green. The
agreement test compares which rows each relation is about, and `equality` does not change the rows. **A
structural comparison is blind to semantics by construction.**

Run it after touching the constraint, the solver or their tests. A `MISSED` line is a claim nothing in
the suite would notice being deleted.

⚠⚠ **v27-P2-09: this script had the exact defect it exists to catch.** `caught` was
`returncode != 0`, and it never checked that the *unmutated* suite passes. One unrelated failing test,
a collection error, a bad `-k` — anything making pytest non-zero for its own reasons — and all ten
mutations report `CAUGHT` from that same failure, `failures` stays empty, and the script prints its
strongest possible result while proving nothing about any mutation. A tool built to stop guards that
cannot fail, that could not fail. **The rule about checking your own guard applies to the thing that
checks the guards**, and it did not occur to me to apply it there.

Closed two ways. **A green baseline is run first and the sweep aborts without it** — a red mutant says
nothing unless the tree it mutates is green. And the exit code is *read* rather than tested for
truthiness: pytest returns `1` for "a test failed", which is the only code that kills a mutant. `2`
through `5` are interruption, internal error, usage error and no-tests-collected — those are the sweep
being broken, and they now stop it with the captured output instead of counting as ten successes.

⚠️ Every mutation is the *smallest* change that undoes one claim. A revert removing two things at once
cannot say which of them the guard is watching — that lesson is v18's and it is applied here.
"""

import pathlib
import subprocess
import sys

# Computed from this file, never from the caller's working directory: a result that cannot be re-run
# identically is not evidence.
ROOT = pathlib.Path(__file__).resolve().parents[2]
PYTHON = ROOT / "forge" / ".venv" / "Scripts" / "python.exe"
PYTEST = [str(PYTHON), "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "-x", "forge/tests"]

PASSED = 0
"""pytest: everything green."""
TESTS_FAILED = 1
"""pytest: a test failed. ⚠️ **The only code that kills a mutant.** Every other non-zero code means
pytest never got as far as judging the mutation."""
BROKEN = {2: "interrupted", 3: "internal error", 4: "usage error", 5: "no tests collected"}

MUTATIONS = [
    (
        "the spread bound that makes the chain a cycle",
        "forge/src/boxscore_forge/constraints.py",
        "        Identity.BATTING_ORDER,\n        constant=1,\n    )",
        "        Identity.BATTING_ORDER,\n        constant=0,\n    )",
    ),
    (
        "the verifier's spread bound",
        "forge/src/boxscore_verify/rules.py",
        'origin=f"PA(slot {order[0]}) - PA(slot {order[-1]}) <= 1",\n            equality=False,',
        'origin=f"PA(slot {order[0]}) - PA(slot {order[-1]}) <= 1",\n            equality=True,',
    ),
    (
        "the lineup arithmetic itself",
        "forge/src/boxscore_forge/solver.py",
        "    lineup = _lineup_moves(shape, values)\n    if lineup:",
        "    lineup = _lineup_moves(shape, values)\n    if False and lineup:",
    ),
    (
        "the companion rows in the dependency graph",
        "forge/src/boxscore_forge/solver.py",
        'earlier for earlier in (batting_total_cell("plate_appearances"), *companions) if earlier in depths',
        'earlier for earlier in (batting_total_cell("plate_appearances"),) if earlier in depths',
    ),
    (
        "excluding givens from the graph",
        "forge/src/boxscore_forge/solver.py",
        '(batting_total_cell("plate_appearances"), *companions) if earlier in depths',
        '(batting_total_cell("plate_appearances"), *companions) if True',
    ),
    (
        "bounding counted by technique",
        "forge/src/boxscore_forge/solver.py",
        "if deduction.technique is Technique.BOUNDING)",
        "if not deduction.has_a_comparable_cost)",
    ),
    (
        "refusing a lineup that is not the nine positions",
        "forge/src/boxscore_forge/constraints.py",
        "if self.slots and set(self.slots) != set(range(1, 10)):",
        "if False and set(self.slots) != set(range(1, 10)):",
    ),
    (
        "the verifier refusing the same",
        "forge/src/boxscore_verify/rules.py",
        "    if set(slots) != set(range(1, 10)):",
        "    if False and set(slots) != set(range(1, 10)):",
    ),
    (
        "leaving a shared slot unsplit",
        "forge/src/boxscore_forge/solver.py",
        "        if len(unknown) == 1:",
        "        if len(unknown) >= 1:",
    ),
    (
        "the constraint being off without slots",
        "forge/src/boxscore_forge/solver.py",
        "    if not shape.slots:\n        return []",
        "    if False:\n        return []",
    ),
    (
        "the filler cap's denominator",
        "forge/src/boxscore_forge/lineup_fallback.py",
        "    return division / chain",
        "    return division / len(puzzle.solution.deductions)",
    ),
    (
        "specimen eligibility: both arms must have a rendered page",
        "discovery/batting-order/arms.py",
        "    if any((arm, SPECIMEN_TARGET) not in specimens for arm in SPECIMEN_ARMS):\n        return None",
        "    if False:\n        return None",
    ),
    (
        "specimen eligibility: an unreached treatment is not a contrast",
        "discovery/batting-order/arms.py",
        "    if not reached:\n        return None",
        '    if not reached:\n        return "negative"',
    ),
    (
        "specimen eligibility: rows at another target cannot qualify a direction",
        "discovery/batting-order/arms.py",
        "row.arm in drawn and row.target == SPECIMEN_TARGET and row.reached",
        "row.arm in drawn and row.reached",
    ),
]

WIRING = [
    (
        "a production module calling erase(..., slots=...)",
        "forge/src/boxscore_forge/_sweep_producer.py",
        (
            '"""A production builder that enables the batting order."""\n\n'
            "from boxscore_forge.erasure import erase\n\n\n"
            "def build(direction, lineup):\n"
            "    return erase(direction, target_stalls=5, seed=1, slots=lineup)\n"
        ),
    ),
    (
        "a module bridging the experiment to certification",
        "forge/src/boxscore_forge/_sweep_bridge.py",
        (
            '"""A producer that builds with the experiment and hands the board to certification."""\n\n'
            "from boxscore_forge.lineup_fallback import erase_with_lineup_fallback\n"
            "from boxscore_verify.certify import certify_for_publication\n\n"
            '__all__ = ["certify_for_publication", "erase_with_lineup_fallback"]\n'
        ),
    ),
]
"""⚠️⚠️ **Mutations that ADD a module, because the risk being guarded is wiring that does not exist yet.**

v27-P2-14 and v27-P2-15 were two guards that could not fail, and an edit-based sweep signed off on
both. The production guard was "verified" by changing `shape_of(direction, slots)` to
`slots=slots` — the one change it could see, and **not the change that matters**, which is a
*different module* calling `erase(..., slots=...)`. The publication guard was verified against edits
that never created the forbidden shape at all: a third module importing the fallback *and*
certification.

**A mutation has to be the thing you are afraid of.** These two write that module, run the suite, and
delete it again.
"""


def run_suite() -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603
        PYTEST, capture_output=True, text=True, encoding="utf-8", check=False, cwd=ROOT, timeout=900
    )


# ⚠️ The baseline, and the sweep does not start without it. Ten red mutants mean nothing if the tree
# was already red -- they would all be reporting the same unrelated failure as ten separate successes.
print("baseline: the unmutated suite must be green before any mutation can mean anything")
baseline = run_suite()
if baseline.returncode != PASSED:
    print(f"  ABORT - the untouched tree exits {baseline.returncode}, so nothing below would be evidence")
    print((baseline.stdout or "")[-3000:])
    print((baseline.stderr or "")[-2000:])
    sys.exit(1)
print("  green")
print("")

originals = {path: (ROOT / path).read_text(encoding="utf-8") for _, path, _, _ in MUTATIONS}
failures = []
broken = []
try:
    for name, path, old, new in MUTATIONS:
        target = ROOT / path
        text = originals[path]
        if text.count(old) != 1:
            failures.append(f"{name}: the anchor is not unique ({text.count(old)}); mutation not applied")
            continue
        target.write_text(text.replace(old, new), encoding="utf-8", newline=chr(10))
        result = run_suite()
        target.write_text(text, encoding="utf-8", newline=chr(10))
        # ⚠️ Read, not tested for truthiness. Only TESTS_FAILED means the suite judged the mutation.
        if result.returncode == TESTS_FAILED:
            print(f"  CAUGHT  {name}")
        elif result.returncode == PASSED:
            print(f"  MISSED  {name}")
            failures.append(name)
        else:
            why = BROKEN.get(result.returncode, f"exit {result.returncode}")
            print(f"  BROKEN  {name} - pytest {why}, so this mutation was never judged")
            print((result.stdout or "")[-1500:])
            broken.append(f"{name}: pytest {why}")
finally:
    for path, text in originals.items():
        (ROOT / path).write_text(text, encoding="utf-8", newline=chr(10))

for name, path, body in WIRING:
    target = ROOT / path
    if target.exists():
        # Refusing rather than overwriting: the file is a fixture this script owns, and finding one
        # already there means a previous run died mid-mutation and the tree is not clean.
        failures.append(f"{name}: {path} already exists, so a previous run left the tree dirty")
        continue
    target.write_text(body, encoding="utf-8", newline=chr(10))
    try:
        result = run_suite()
    finally:
        target.unlink()
    if result.returncode == TESTS_FAILED:
        print(f"  CAUGHT  {name}")
    elif result.returncode == PASSED:
        print(f"  MISSED  {name}")
        failures.append(name)
    else:
        why = BROKEN.get(result.returncode, f"exit {result.returncode}")
        print(f"  BROKEN  {name} - pytest {why}, so this wiring was never judged")
        print((result.stdout or "")[-1500:])
        broken.append(f"{name}: pytest {why}")

print("")
if broken:
    print(f"{len(broken)} mutation(s) the sweep could not judge - fix these before reading anything else:")
    for name in broken:
        print(f"   {name}")
if failures:
    print(f"{len(failures)} claim(s) nothing would have caught:")
    for name in failures:
        print(f"   {name}")
if broken or failures:
    sys.exit(1)
print(f"all {len(MUTATIONS) + len(WIRING)} claims are guarded, against a baseline that was green")
