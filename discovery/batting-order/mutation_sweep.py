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

⚠️ Every mutation is the *smallest* change that undoes one claim. A revert removing two things at once
cannot say which of them the guard is watching — that lesson is v18's and it is applied here.
"""

import pathlib
import subprocess
import sys

ROOT = pathlib.Path.cwd()
PYTHON = ROOT / "forge" / ".venv" / "Scripts" / "python.exe"

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
]

originals = {path: (ROOT / path).read_text(encoding="utf-8") for _, path, _, _ in MUTATIONS}
failures = []
try:
    for name, path, old, new in MUTATIONS:
        target = ROOT / path
        text = originals[path]
        if text.count(old) != 1:
            failures.append(f"{name}: the anchor is not unique ({text.count(old)}); mutation not applied")
            continue
        target.write_text(text.replace(old, new), encoding="utf-8", newline=chr(10))
        result = subprocess.run(  # noqa: S603
            [str(PYTHON), "-m", "pytest", "-q", "--no-header", "-p", "no:cacheprovider", "-x", "forge/tests"],
            capture_output=True,
            text=True,
            check=False,
            cwd=ROOT,
            timeout=900,
        )
        target.write_text(text, encoding="utf-8", newline=chr(10))
        caught = result.returncode != 0
        print(f"  {'CAUGHT ' if caught else 'MISSED '} {name}")
        if not caught:
            failures.append(name)
finally:
    for path, text in originals.items():
        (ROOT / path).write_text(text, encoding="utf-8", newline=chr(10))

print("")
if failures:
    print(f"{len(failures)} claim(s) nothing would have caught:")
    for name in failures:
        print(f"   {name}")
    sys.exit(1)
print(f"all {len(MUTATIONS)} claims are guarded")
