"""Report every ruff finding in `discovery/` and `tools/`, and fail if the count for any rule grows.

⚠️⚠️ **These findings have never been reported, and the reason is a gap between two configurations.**
`forge/pyproject.toml` sets `extend-include = ["../discovery/**/*.py"]` — deliberately, because the
duplicate `audit()` that disabled a launch-gate check lived in `discovery/` and was outside the lint
scope that ran. But `extend-include` only decides which files ruff considers *while walking a path it
was given*, and every invocation gave it `src/ tests/ scripts/`. The config said discovery was in
scope; nothing ever pointed at it. **Two places disagreeing with nothing checking they agree**, in the
lint configuration, which is the thing that catches that shape elsewhere.

⚠️ **A ratchet, not a gate, and that is a decision rather than a compromise.** There are 199 findings
today. Making them blocking would leave `main` unmergeable from the first commit that protects it, and
scheduling a cleanup of throwaway decision tools ahead of the hand-solve pack is not a trade worth
making. Making them advisory would be worse: an advisory count is one nobody reads, and it would rot
back to the state this file exists to end.

So: **the whole report is printed every run, and the build fails if any rule's count rises or a new
rule appears.** The findings are visible, they cannot grow, and lowering the baseline is a one-line
commit that a cleanup naturally produces.

⚠️ **Per rule, not a total.** A single number is a weak ratchet — fix one finding, add another, and it
never moves. Per rule, a new `S608` cannot hide behind a fixed `E501`.

⚠️ **`forge/` is not in here and must never be.** It is clean and it is blocking, checked directly in
the workflow. A ratchet over code that is already at zero is a way of allowing it to stop being zero.

    python tools/lint_discovery.py [--update]
"""

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

# ⚠⚠ **The stream is forced to UTF-8 before anything is printed.** This report quotes the source it
# is reporting on, that source contains `≤` and `→` in docstrings, and Windows gives a redirected
# stream cp1252 — so the first run died on a `UnicodeEncodeError` at character 42,033 and reported
# nothing at all. The project already records a run lost this way, and the rule was written as "do not
# put a warning sign in a report". That was too narrow: **a tool that prints code it did not write
# cannot control the characters in it**, so the stream has to be able to carry them rather than the
# content having to avoid them.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tools" / "discovery-lint-baseline.json"
TARGETS = ("discovery", "tools")


def measure() -> tuple[Counter[str], str]:
    """Ruff's findings for the targets, as counts per rule and as the report a person reads."""
    # ⚠️ Run from `forge/`, because that is where the ruff configuration lives and ruff resolves
    # `line-length`, the rule selection and the per-file ignores from the nearest config to the
    # *invocation*. Pointed at these paths from anywhere else it applies defaults, and the numbers
    # would be about a rule set nobody chose.
    common = [sys.executable, "-m", "ruff", "check", *[str(ROOT / target) for target in TARGETS]]
    findings = subprocess.run(  # noqa: S603
        [*common, "--output-format", "json"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT / "forge",
        check=False,
    )
    if findings.returncode not in (0, 1):
        print(findings.stderr)
        message = f"ruff exited {findings.returncode}"
        raise SystemExit(message)
    readable = subprocess.run(  # noqa: S603
        common,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=ROOT / "forge",
        check=False,
    )
    return Counter(row["code"] for row in json.loads(findings.stdout or "[]")), readable.stdout


def main() -> int:
    counts, report = measure()
    print(report)
    print(f"{sum(counts.values())} findings across {', '.join(TARGETS)}/\n")

    if "--update" in sys.argv:
        BASELINE.write_text(json.dumps(dict(sorted(counts.items())), indent=2) + "\n", encoding="utf-8")
        print(f"baseline written: {sum(counts.values())} findings")
        return 0

    if not BASELINE.exists():
        # ⚠️ Fails rather than writing itself a baseline on first run. A ratchet that creates its own
        # reference point silently accepts whatever it finds, which is the absence of a check reading
        # as a passing one.
        print(f"no baseline at {BASELINE.relative_to(ROOT)}. Run with --update to record one.")
        return 1

    baseline = Counter(json.loads(BASELINE.read_text(encoding="utf-8")))
    worse = {code: (baseline.get(code, 0), found) for code, found in counts.items() if found > baseline.get(code, 0)}
    if worse:
        print("These rules got worse:")
        for code, (was, now) in sorted(worse.items()):
            print(f"  {code}: {was} -> {now}")
        print("\nFix them, or run `python tools/lint_discovery.py --update` if the rise is intended.")
        return 1

    better = {code: (baseline[code], counts.get(code, 0)) for code in baseline if counts.get(code, 0) < baseline[code]}
    if better:
        # Not a failure. Said out loud because a baseline nobody lowers is a baseline that stops
        # meaning anything, and this is the moment to lower it.
        print("These rules improved. Run with --update to lock the gain in:")
        for code, (was, now) in sorted(better.items()):
            print(f"  {code}: {was} -> {now}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
