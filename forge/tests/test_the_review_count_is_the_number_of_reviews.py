"""`docs/reviews/todo.md` says how many reviews there have been, and the directory decides.

⚠️⚠️ **Written because that number was wrong for ten reviews.** The backlog opened with *"twenty-nine
reviews, 135 findings"* while `docs/reviews/` held thirty-nine, and the same file already records that
**the count in it had been wrong three times.** A number restated by hand, that nothing checks, in the
document whose subject is checking things.

⚠️ **The finding total was dropped rather than corrected**, and that is the other half of the repair:
re-deriving it by hand produces a fourth number nobody can verify either, and a wrong count reads as a
measurement. What can be counted from the tree is asserted here; what cannot is not claimed.

⚠️⚠️ **Only the hook runs this.** `ci-forge.yml` skips a push touching only documents, which adding a
review is. Named rather than assumed.
"""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_REVIEWS = _ROOT / "docs" / "reviews"
_TODO = _REVIEWS / "todo.md"

_CLAIM = re.compile(r"\*\*(\d+) reviews\*\*")
"""How the backlog states it: `**39 reviews**`.

⚠️ Bold-delimited so a number in ordinary prose — *v28 was a full-tree review* — cannot match. The
pattern this project keeps being caught by is one that matches the tail of something else."""


def _review_files() -> list[Path]:
    return sorted(_REVIEWS.glob("code_review_v*.md"))


def test_the_backlog_counts_the_reviews_that_exist() -> None:
    reviews = _review_files()
    assert reviews, "no review documents found; this test would otherwise assert nothing"

    claimed = _CLAIM.search(_TODO.read_text(encoding="utf-8"))
    assert claimed, "docs/reviews/todo.md no longer states a review count in the form **N reviews**"

    assert int(claimed[1]) == len(reviews), (
        f"todo.md says {claimed[1]} reviews and docs/reviews/ holds {len(reviews)} "
        f"(latest: {reviews[-1].name}). The directory is the authority."
    )


def test_the_reviews_are_numbered_without_a_gap() -> None:
    """⚠️ Otherwise the count above can be right while a review is missing.

    Counting files and reading the highest number are two different questions, and they agree only when
    the sequence is complete — which is the assumption the count silently rests on.
    """
    numbers = sorted(int(path.stem.removeprefix("code_review_v")) for path in _review_files())

    assert numbers == list(range(1, len(numbers) + 1)), f"the review numbering has a gap: {numbers}"
