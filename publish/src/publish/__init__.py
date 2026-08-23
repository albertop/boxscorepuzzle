"""The serving side's executables. **`docs/calendar.md` owns the access model they enforce.**

⚠️ **A fourth tree beside `forge`, `serve` and `keep`, and the reason is that `serve/` is static.** It is
23 JavaScript modules, HTML, CSS and fonts, governed by `docs/javascript-conventions.md`, which says in
its own second paragraph that its rules apply to *the hand-written JavaScript under `serve/`*. A Python
project inside that tree would make the sentence describe half of it.

⚠️⚠️ **And the relationship this needs is the one `forge` already has.** `write_reference_puzzles.py`
writes packages into `serve/data/puzzles/` from outside `serve/` and has never needed to live inside it.
§33 forbids cross-*imports*; the only thing that crosses here is a signed package, which is exactly what
§33 permits. **Nothing in here imports `serve`, and nothing in `serve` imports this.**
"""
