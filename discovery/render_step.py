"""Six rendered boards, written beside every measurement in this round.

Not decoration and not a test. Four serious defects in this project were found by looking at a
board — the zero-heavy board, the totals row showing pitching, the zero-filled error columns, and
both of the loader defects. A measurement that produces a distribution should also produce a handful
of examples, checked by eye, before the numbers are trusted.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2] if "discovery" in str(Path(__file__).resolve()) else None


def write_examples(sample, out_path, *, target_chain=9, seed=3, note=""):
    """Render up to six boards from `sample` to `out_path`. Failures here must not kill a run."""
    root = Path(out_path).resolve().parents[2]
    sys.path.insert(0, str(root / "discovery" / "pitcher-cap"))
    sys.path.insert(0, str(root / "discovery" / "verifier"))
    from render_boards import page, render as render_board

    from boxscore_forge.erasure import erase

    boards = []
    for item in sample[:: max(len(sample) // 6, 1)][:6]:
        puzzle = erase(item.direction, target_chain=target_chain, seed=seed)
        if puzzle is None:
            continue
        label = f"{len(item.direction.batting)} batters, {len(item.direction.pitching)} pitchers, chain {target_chain}"
        boards.append(render_board(item, puzzle, f"{label}{note}"))
    Path(out_path).write_text(page(boards), encoding="utf-8")
    return len(boards)
