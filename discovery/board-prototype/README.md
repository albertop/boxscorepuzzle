# The board prototype — and which instrument answers which question

There are **two** board renderers in `discovery/`, and they are not duplicates. Deleting either one
loses a question.

| | `board-prototype/template.html` | `pitcher-cap/render_boards.py` |
|---|---|---|
| Question | **What can the player see at once?** | **What does a board look like?** |
| Layout | full-viewport flex column, scroll container, sticky header, pinned totals anchor | blocks in normal document flow |
| Interactive | yes — keypad, cell selection, progressive reveal, contextual anchoring | no JavaScript at all |
| Good for | working set, rows visible at 375px and 320px, whether a step's numbers stay together while scrolling | judging a whole board — density, clutter, whether a section reads as noise |
| Bad for | judging a board, because it deliberately shows only part of one | anything about scrolling or what is on screen at once |

**Why the flat one exists.** The prototype's page renders twice in at least one real browser — a
narrow clipped copy of the whole page beside the full one — which makes it useless for a visual
judgement even though it is still correct for the measurement it was built for. Rather than debug
someone's browser, the judging renderer avoids everything that could be involved: no viewport-height
flex, no `overflow: hidden`, no `position: sticky`, no absolutely positioned anchor row, no script.

**Neither is the product.** Nothing here goes to `serve/`.

## What the prototype settled

- **Rows on screen do not bind.** With the active section's totals pinned they never scroll away, and
  70% of steps at a chain target of ten touch rows within a five-row window. That is what let the
  batter cap go from 10 to 13 — and, once someone noticed it had never been applied to pitchers, the
  pitcher cap from 2 to 4 (§5, §6).
- **The label column is 66px, seven characters, fixed**, with disambiguation by first initial:
  6.64% of boards carry two identical surnames, so it is not a truncation artefact (§7).
- **Contextual anchoring** rather than two panes: one continuous board, the totals of whichever
  section is in view pinned to the bottom.

## Running them

Both read real directions from DGL and are run from `forge/`:

```
uv run python ../discovery/board-prototype/build.py ../discovery/board-prototype
uv run python ../discovery/pitcher-cap/render_boards.py
```
