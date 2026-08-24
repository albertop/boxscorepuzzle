"""Every hand-solve answer key is ignored by Git, and the pack's results are not.

⚠️⚠️ **Written because `fifty-key.csv` was neither.** `.gitignore` named `key.csv` and
`ceiling-key.csv` by hand; the key built for the fifty-board pack was never added, so it sat
untracked and unignored — one `git add -A` from being committed, which `.gitignore`'s own comment
calls *fatal to the experiment*. It was found by comparing two `git status` outputs by eye, which is
not a mechanism.

**Two hand-maintained lines and a third artefact of the same kind is this project's signature defect:**
two places that should say the same thing saying different things, with nothing checking they agree.
The repair is a glob, and this file is what makes the glob a rule rather than a wider guess.

⚠️ **The negative case is half the test and the more fragile half.** `pack-a-difficulty.csv` holds
sixteen boards solved by hand and cannot be regenerated — the obvious "tidy-up" is to ignore the whole
directory, which would protect the keys and silently stop backing up the results. So this asserts what
must be ignored *and* what must not be, because only the pair pins the boundary.

⚠️ **Ignored is not enough on its own.** A file already tracked stays tracked whatever `.gitignore`
says, so the tracked-ness of each key is asserted separately rather than inferred from the ignore.

⚠️⚠️ **Seen red three ways before being believed**, because a guard nobody has watched fail is
indistinguishable from a broken one:

| what was broken | what went red |
|---|---|
| the `*key.csv` glob commented out of `.gitignore` | all three keys, on the ignore |
| `discovery/hand-solve/*.csv` appended — the plausible "tidy-up" | the results file, on being ignored |
| `git add -f discovery/hand-solve/key.csv` | that key, on **both** the ignore and the tracking |

⚠️ The third is why both halves exist and why they are not redundant: `git check-ignore` reports a
tracked file as *not ignored*, so the ignore assertion happens to catch tracking with a message about
the wrong thing. The tracked assertion says what actually has to be done — `git rm --cached`, and treat
the answers as disclosed.
"""

import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PACK = _ROOT / "discovery" / "hand-solve"

_RESULTS = "pack-a-difficulty.csv"
"""The operator's ratings and derivability verdicts. **Tracked on purpose.**

It is `board,how_hard,solved,had_to_guess` and names no game without the key, which is ignored — so it
carries the finding and none of the answers. It is irreplaceable in the way `docs/calendar.md` is: it
records sixteen boards solved by a person, and nothing can recompute it.
"""


def _keys() -> list[Path]:
    """Every answer key on disk, found by shape rather than by a list."""
    return sorted(_PACK.glob("*key.csv"))


def _git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(("git", *arguments), cwd=_ROOT, capture_output=True, text=True, check=False)


def test_the_sweep_finds_keys_to_check() -> None:
    """⚠️ A check over an empty set passes forever. Assert the subject was there.

    This project records three cases of a validator reporting success about nothing. If the pack is
    ever rebuilt under different filenames, this fails loudly instead of going quietly green.
    """
    assert _keys(), f"no *key.csv under {_PACK}; this test would pass over an empty set"


@pytest.mark.parametrize("key", _keys(), ids=lambda path: path.name)
def test_every_answer_key_is_ignored(key: Path) -> None:
    """`git check-ignore` exits 0 only when something actually ignores the path."""
    result = _git("check-ignore", "-v", str(key.relative_to(_ROOT)))
    assert result.returncode == 0, (
        f"{key.name} is not ignored. Committing it is fatal to the hand-solve experiment: "
        f"the boards only measure anything if they are met blind. Add it to .gitignore's "
        f"discovery/hand-solve/*key.csv rule, or give it a name that rule covers."
    )


@pytest.mark.parametrize("key", _keys(), ids=lambda path: path.name)
def test_no_answer_key_is_tracked(key: Path) -> None:
    """⚠️ Ignoring does nothing to a file Git already tracks, so ask Git directly."""
    result = _git("ls-files", "--error-unmatch", str(key.relative_to(_ROOT)))
    assert result.returncode != 0, (
        f"{key.name} is tracked. .gitignore does not untrack anything: "
        f"run `git rm --cached` on it, and treat the answers as disclosed."
    )


def test_the_hand_solve_results_are_not_ignored() -> None:
    """⚠️⚠️ The other half: ignoring the directory would protect the keys and lose the findings.

    `pack-a-difficulty.csv` went unbacked-up once already. §33 names the laptop as the single point of
    failure and the repository as the backup, and this file is one of the few artefacts here that no
    process can regenerate.
    """
    results = _PACK / _RESULTS
    assert results.exists(), f"{_RESULTS} is missing; it holds Pack A's hand-solve results"
    result = _git("check-ignore", "-v", str(results.relative_to(_ROOT)))
    assert result.returncode != 0, (
        f"{_RESULTS} is ignored by `{result.stdout.strip()}`. It is board, rating and derivability "
        f"verdict — it names no game without the key and cannot be regenerated. A rule broad enough "
        f"to catch it is too broad: narrow it to the keys."
    )
