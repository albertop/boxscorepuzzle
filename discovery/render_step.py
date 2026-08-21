"""Six rendered boards, written beside every measurement in this round.

Not decoration and not a test. Four serious defects in this project were found by looking at a
board — the zero-heavy board, the totals row showing pitching, the zero-filled error columns, and
both of the loader defects. A measurement that produces a distribution should also produce a handful
of examples, checked by eye, before the numbers are trusted.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ⚠️ `_ROOT` was computed here and never read; the real root was re-derived from the output path,
# which silently assumed every artefact lives exactly two levels under the repository. Anchored on this
# file, like every other script. v36-P3-04.
_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class Options:
    """How the six boards are drawn and what the page says about them.

    ⚠️ **One record rather than seven parameters**, so the private half is not a seven-argument
    function that has to be read against its caller. The public signature is unchanged: callers still
    pass keywords.
    """

    target_chain: int = 9
    seed: int = 3
    note: str = ""
    title: str = ""
    intro: str = ""


def write_examples(
    sample: list[Any],
    out_path: Path | str,
    *,
    target_chain: int = 9,
    seed: int = 3,
    note: str = "",
    title: str = "",
    intro: str = "",
) -> int:
    """Render up to six boards from `sample` to `out_path`.

    ⚠️⚠️ **"Failures here must not kill a run" was a promise nothing kept.** (v36-P3-04) Nothing caught
    anything, so a render failure in `pool-at-4-pitchers/remeasure.py` — after the trajectories were
    already computed in memory — **discarded the compute**. That is the three-hours-lost shape this
    project records, waiting behind a sentence that said it could not happen.

    It is implemented now: a failure prints what went wrong and returns 0 boards, so the run that paid
    for the measurement keeps it.
    """
    root = _ROOT
    sys.path.insert(0, str(root / "discovery" / "pitcher-cap"))
    sys.path.insert(0, str(root / "discovery" / "verifier"))
    # ⚠️ The whole body, in one `try`. A helper taking the seven arguments separately would satisfy
    # the contract and hand the file a seven-parameter function to explain; the guarantee is about
    # *this* function not killing a run, so it is written where that is visible.
    try:
        return _draw(sample, out_path, Options(target_chain, seed, note, title, intro))
    # ⚠️ A bare Exception on purpose: the contract is that NOTHING here kills a run, so narrowing it
    # to the failures somebody thought of would leave the ones nobody did.
    except Exception as error:
        print(f"render_step: {out_path} not written ({type(error).__name__}: {error})")
        return 0


def _draw(sample: list[Any], out_path: Path | str, options: Options) -> int:
    from render_boards import page, render as render_board  # noqa: PLC0415

    from boxscore_forge.erasure import erase  # noqa: PLC0415

    boards = []
    for item in sample[:: max(len(sample) // 6, 1)][:6]:
        puzzle = erase(item.direction, target_chain=options.target_chain, seed=options.seed)
        if puzzle is None:
            continue
        label = (
            f"{len(item.direction.batting)} batters, {len(item.direction.pitching)} pitchers, "
            f"chain {options.target_chain}"
        )
        boards.append(render_board(item, puzzle, f"{label}{options.note}"))
    Path(out_path).write_text(page(boards, title=options.title, intro=options.intro), encoding="utf-8")
    return len(boards)
