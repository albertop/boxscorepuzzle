# Code Review v27

## Scope

This review concentrates on the batting-order work added after v26:

- `forge/src/boxscore_forge/constraints.py`
- `forge/tests/test_batting_order.py`
- `discovery/batting-order/arms.py`
- `discovery/batting-order/arms.log`
- The revised `discovery/batting-order/measure.py` and `result.log`
- The corresponding decisions and status in `docs/reviews/todo.md`

The production erasure path still calls `shape_of(direction)` without slots, so the new constraint is currently opt-in and does not change shipped puzzle generation. `arms.log` is empty, so this review covers the new instrument's code but cannot assess experimental results that have not been recorded. No source code, tests, generated output, configuration, or planning document was changed. Tests and static-analysis tools were not run.

## Findings

### v27-P1-01: The implementation encodes only monotonicity, not the cyclic batting-order rule it claims to measure

- **Persona:** Kakuro / Logic-Puzzle Reviewer
- **Priority:** P1
- **Location:** `forge/src/boxscore_forge/constraints.py:372`, `forge/src/boxscore_forge/constraints.py:393`, `forge/src/boxscore_verify/rules.py:229`, `forge/src/boxscore_verify/rules.py:255`, `discovery/batting-order/arms.py:146`
- **Description:** Both implementations emit only the eight adjacent inequalities `PA(slot n) >= PA(slot n+1)`. Those inequalities establish the weak hypothesis but do not establish that adjacent values differ by at most one, that the total spread is at most one, or that the team total determines the nine slot values. Nevertheless, the constraint docstring and `arms.py` treat the implementation as the full cyclic rule and build the `on_total_given` arm around the premise that a known total determines every slot. The tests exercise a real cyclic distribution, a flat distribution, and a rise, but do not exercise a monotone distribution that is impossible under a cyclic lineup.
- **Impact:** The new experiment does not measure the feature described by its arms. It measures the effect of a weaker monotonic bound. In particular, `on_total_given` does not represent “nine values follow from one number,” so its comparison cannot distinguish the claimed filler case from the total-erased case. If this implementation were later enabled in production, it would be safe but materially underpowered: valid deductions promised by the documented rule would remain unavailable. The independent verifier repeats the same weaker mathematical statement, so cross-implementation agreement does not expose the mismatch.
- **Reproduction:** With one row in each slot, use slot totals `(6, 5, 4, 4, 4, 4, 4, 4, 4)`. Every emitted relation is satisfied because the sequence never rises, and the batting-column equation can balance against the total `39`. The actual cyclic prediction for 39 plate appearances is `(5, 5, 5, 4, 4, 4, 4, 4, 4)`, so the accepted vector is impossible under the rule the experiment says it enabled.
- **Recommended fix and rationale:** Encode the missing total-spread bound independently on both sides: the monotonic chain plus `PA(slot 1) - PA(slot 9) <= 1` is sufficient to force every slot to one of two adjacent values and permit only one cut. The generator's `Inequality` currently has no constant, so extend it and the bound propagation code to represent a non-zero limit; the verifier already has a relation constant. Add tests that reject a monotone multi-drop vector and demonstrate that a known total narrows all nine slot sums to the predicted distribution. Alternatively, explicitly rename the feature as weak monotonicity and rewrite the experiment's hypotheses, but do not draw full-cycle conclusions from it.

### v27-P2-02: The persisted arm rows discard both identifiers needed to reproduce and pair a trial

- **Persona:** Backend Architect
- **Priority:** P2
- **Location:** `discovery/batting-order/arms.py:64`, `discovery/batting-order/arms.py:141`, `discovery/batting-order/arms.py:172`
- **Description:** `Row` says it represents one direction, one seed, one arm, and one target, but it stores neither the seed nor the offensive team that identifies the direction. `_measure()` receives `seed`, and `Loaded` carries the offense identifier, yet both are omitted when the row is created. Every direction is deliberately run with seeds 1, 2, and 3, so ambiguity is guaranteed in the generated JSON rather than being a rare collision. If both directions of one game enter the sample, their records are also indistinguishable, and the “per board” ceiling groups them by `game` alone.
- **Impact:** The expensive `arms.json` artifact cannot pair the three arms for a specific canonical walk, reproduce an anomalous row, or reliably distinguish the two boards represented by one baseball game. Aggregate coverage still counts rows, but any paired analysis or investigation of a surprising result can silently compare different seeds or merge home and away directions.
- **Reproduction:** Call `_measure()` for one `Loaded` direction with seeds 1 and 2. Rows for the same arm and target have identical stored identity fields (`game`, `season`, `arm`, `target`); only outcome values may reveal that they came from different walks. The JSON contains no field from which the missing seed can be recovered.
- **Recommended fix and rationale:** Add `seed` and the offensive team/direction identifier to `Row`, populate them at creation, and use `(game, offense)` wherever the report groups by board. Preserve those fields in `arms.json`. This makes the canonical-walk control auditable and keeps direction-level results from being merged accidentally.

### v27-P2-03: Slot validation accepts incomplete or invalid lineups and silently emits a partial constraint

- **Persona:** Python Principal Engineer
- **Priority:** P2
- **Location:** `forge/src/boxscore_forge/constraints.py:97`, `forge/src/boxscore_forge/constraints.py:102`, `forge/src/boxscore_forge/constraints.py:389`, `forge/src/boxscore_verify/rules.py:243`, `forge/src/boxscore_verify/rules.py:249`
- **Description:** `BoardShape.__post_init__()` and the independent verifier reject only a mismatch between the number of slot labels and batting rows. Neither verifies that the non-empty labels contain every lineup slot from 1 through 9. `_batting_order()` then sorts whichever distinct values were supplied and emits one relation per adjacent value present, silently converting malformed metadata into a smaller relation set.
- **Impact:** A nine-row board labelled `(1, 2, 3, 4, 5, 6, 7, 8, 8)` is accepted and receives only seven order relations; a board with every row labelled as one slot receives none. This is precisely the silent-underconstraint failure the new validation comments say they intend to prevent. `arms.py` currently filters for nine distinct values, but the core API and verifier remain unsafe for the future production caller, and neither guarantees that the values are actually `1..9`.
- **Reproduction:** Construct `BoardShape(batter_count=9, ..., slots=(1, 2, 3, 4, 5, 6, 7, 8, 8))`. Length validation passes. Grouping produces eight distinct keys, so only seven inequalities are emitted instead of the expected eight, with no error explaining that slot 9 is absent.
- **Recommended fix and rationale:** When slots are present, require `set(slots) == set(range(1, 10))` in both independent implementations in addition to the row-count check. Duplicates remain valid for substitutions, but all nine canonical slots must occur. Add cases for a missing slot, slot zero, and a slot above nine. Refusing malformed lineup metadata is safer than silently weakening the model.

### v27-P3-04: The final TODO summary still publishes the superseded 75.1% payoff

- **Persona:** QA / Reliability Engineer
- **Priority:** P3
- **Location:** `docs/reviews/todo.md:2387`, `docs/reviews/todo.md:2884`
- **Description:** The corrected batting-order section records 826,039 of 990,202 post-rule batting rows, or 83.4%, matching the regenerated result. The later “What is actually left” summary still says 75.1%, which the same document already identifies as the old ungated measurement.
- **Impact:** The decision summary presents the wrong expected benefit at the exact point an operator would consult when deciding whether to adopt the pool rule. It also contradicts the authoritative section in the same file.
- **Reproduction:** Compare the payoff at line 2387 with the batting-order decision summary beginning at line 2884. They refer to the same proposed constraint but report 83.4% and 75.1%, respectively.
- **Recommended fix and rationale:** Replace the stale 75.1% summary with 83.4% and, preferably, retain the corrected numerator and denominator. Keeping the decision summary derived from the authoritative measurement prevents a superseded denominator from surviving after the detailed section is repaired.

## Persona Review Summary

| Persona | Result |
|---|---|
| Backend Architect | Raised `v27-P2-02`. |
| Python Principal Engineer | Raised `v27-P2-03`. |
| Frontend Engineer | No frontend changes were part of v27. |
| QA / Reliability Engineer | Raised `v27-P3-04`. |
| Security Engineer | No security finding in the reviewed changes. |
| UX / Visual Reviewer | No user-interface or visual changes were part of v27. |
| Baseball / Boxscore Domain Reviewer | The per-slot grouping and use of substitutions are directionally correct; the mathematical encoding remains incomplete as described in `v27-P1-01`. |
| Kakuro / Logic-Puzzle Reviewer | Raised `v27-P1-01`. |

## Previous Review Disposition

Both second-pass v26 findings are corrected in the revised measurement script. The exception-distribution table now iterates over the complete population and prints zero-exception categories. The payoff query receives the five derived failing direction keys and reports the post-rule population. Neither v26 finding is repeated.

## Recommended Order of Work

1. Decide whether the feature is the full cyclic rule or only weak monotonicity, then make implementation, tests, and experiment describe the same mathematics before running `arms.py`.
2. Preserve seed and direction identity in the arm artifact before spending time generating it.
3. Reject incomplete slot domains at both trust boundaries.
4. Correct the stale payoff in the TODO summary.

## Verdict

Production behavior is unchanged because slots are not yet supplied by the production erasure path. That containment is valuable, but the new arm experiment should not be run for a decision in its current form: its central “constraint on” treatment is weaker than the cyclic rule it claims to evaluate. One P1, two P2, and one P3 finding were identified; no P0 finding was identified.
