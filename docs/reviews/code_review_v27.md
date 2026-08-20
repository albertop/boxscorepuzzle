# Code Review v27 - Fourth Pass

## Scope

This review concentrates on the batting-order work added after v26:

- `forge/src/boxscore_forge/constraints.py`
- `forge/tests/test_batting_order.py`
- `discovery/batting-order/arms.py`
- `discovery/batting-order/arms.log`
- The revised `discovery/batting-order/measure.py` and `result.log`
- The corresponding decisions and status in `docs/reviews/todo.md`

The production erasure path still calls `shape_of(direction)` without slots, so the new constraint is currently opt-in and does not change shipped puzzle generation. `arms.log` is empty, so this review covers the new instrument's code but cannot assess experimental results that have not been recorded. No source code, tests, generated output, configuration, or planning document was changed. Tests and static-analysis tools were not run.

## Fourth-Pass Finding

### v27-P2-08 - The regression named for a deduced shared-slot dependency never creates one

- **Persona:** Test engineer / Statistician-methodologist
- **Severity:** P2
- **Location:** `forge/tests/test_batting_order.py:278`
- **Description:** `test_a_deduced_companion_is_an_edge_and_moves_the_depth` gives only the team plate-appearance total, deliberately leaves both rows in shared slot 9 unresolved, and then asserts that neither row was deduced. It never has propagation deduce one companion before lineup arithmetic solves the other, and it never asserts `depends_on`, `depth`, or `chain_length`. The production fix now carries deduced companions into the dependency graph, but this test does not exercise that behavior.
- **Impact:** The companion transport can regress while the newly added suite remains green. Removing the companion from `_lineup_moves` or from `_next_step`'s dependency set would again understate shared-slot chain depth, including the metric consumed by the arm comparison, without this purported regression test detecting it.
- **Reproduction:** In the setup at lines 282-289, neither shared-row PA is ever present in `solution.deductions`; the only assertion is that both remain absent. Revert only the companion contribution to `leaned_on` in `solver.py`: this test's result and assertion are unchanged because no dependency edge is ever produced.
- **Recommended fix and rationale:** Build a fixture where row identity first deduces one shared-slot companion's PA from its batting components, then lineup arithmetic derives the other row from the known slot total. Assert that the lineup step contains that deduced companion in `depends_on` and that its depth is one greater than the deepest deduced input. Keep the current unsplittable-sum scenario as a separate test. This makes the regression guard fail for the exact graph defect it claims to close.

## Fourth-Pass Disposition

- `v27-P2-06` is fixed in production: shared-slot lineup moves now return known companions and `_next_step` includes deduced companions, while consistently excluding givens, from the dependency graph.
- `v27-P2-07` is fixed: `bounding_steps` now counts `Technique.BOUNDING` directly rather than deriving it from `trivial_steps`.
- The new tests cover direct lineup arithmetic, shared-slot non-splitting, given exclusion, and the corrected bounding count. The remaining gap is the ineffective deduced-companion regression in `v27-P2-08`.
- `discovery/batting-order/arms.log` is currently empty, so it provides no completed experimental result to assess in this pass.
- The verifier's inability to replay `LINEUP_ARITHMETIC` is already recorded as pending product work in `todo.md`; it is not duplicated as a review finding.

## Fourth-Pass Persona Summary

- **Software architect:** The lineup dependency transport and direct bounding metric now match the intended model.
- **Security engineer:** No practical security regression found in the changed surface.
- **Performance engineer:** No practical runtime or memory regression found.
- **Test engineer:** One regression test does not execute or assert the behavior named by the test (`v27-P2-08`).
- **Data scientist:** No new arithmetic correctness defect found.
- **Statistician/methodologist:** Production chain-depth provenance is fixed, but its shared-slot deduced-input case remains unprotected.
- **UX/API contract reviewer:** No shipped API or user-facing contract regression found.
- **Solo-maintainer pragmatist:** Fix the single test gap; no broader refactor is warranted.

## Fourth-Pass Verdict

One new practical finding remains: **one P2** (`v27-P2-08`). No new P0, P1, or P3 finding was identified. The two third-pass production defects are resolved; the open item is a narrowly scoped regression-coverage hole in the exact shared-slot provenance case.

## Resolved Third-Pass Findings

### v27-P2-06: Shared-slot lineup deductions omit the row they subtract from their dependency graph

- **Persona:** QA / Reliability Engineer
- **Priority:** P2
- **Location:** `forge/src/boxscore_forge/solver.py:489`, `discovery/batting-order/arms.py:199`
- **Description:** `_lineup_moves()` correctly waits until a slot has only one unknown row and computes that row as the predicted slot total minus the known rows sharing the slot. `_next_step()`, however, records every resulting deduction as depending only on `batting_totals.plate_appearances`, and computes its depth only from that total. A shared-slot deduction also depends on every known PA value subtracted inside `_lineup_moves()`. If one of those companion rows was itself deduced earlier, that edge and its depth are lost. The method also inserts the total into `depends_on` even when the total was a given, unlike ordinary propagation, which records only previously deduced cells.
- **Impact:** `Solution.chain_length` can understate the path on substitution-heavy boards, and `arms.py` persists that understated chain for the experiment currently running. The numerical PA result remains correct, but the reported solution graph is not the path that produced it. This matters directly to an instrument comparing whether the batting-order constraint adds a chain.
- **Reproduction:** Use a shared slot whose target sum is four, with one row already deduced as one at depth greater than one and the other row unknown. The lineup move computes the unknown as three by subtracting the first row. The emitted `Deduction` has depth `1 + depth(total)` and `depends_on={total}`; changing or removing the known companion would change the result even though it is absent from the recorded provenance.
- **Recommended fix and rationale:** Have `_lineup_moves()` return the known companion cells used with each move. In `_next_step()`, include deduced companions in `depends_on` and calculate depth from the maximum depth of the total and those companions; do not add a given total to the dependency set if the graph's established convention excludes givens. Add a shared-slot test in which the known companion is a prior deduction and assert both dependency membership and chain depth. The solution graph should describe the arithmetic actually performed, not only the rule that authorized it.

### v27-P2-07: `bounding_steps` counts every lineup-arithmetic move as bounding

- **Persona:** Python Principal Engineer
- **Priority:** P2
- **Location:** `forge/src/boxscore_forge/solver.py:298`, `forge/src/boxscore_forge/solver.py:389`, `discovery/difficulty-weights/measure.py:125`
- **Description:** Before `LINEUP_ARITHMETIC` existed, `Solution.bounding_steps` counted deductions with `not deduction.has_a_comparable_cost`, which was equivalent to counting `Technique.BOUNDING`. The new lineup deductions also set `known_terms_combined=None`, so they have no comparable cost and now satisfy that old proxy. A total-visible nine-slot board therefore reports nine bounding steps despite using zero `Technique.BOUNDING` deductions. `stalls` and `arms.py` correctly check the explicit technique, making the two public metrics disagree about the same solution.
- **Impact:** Any measurement consuming `Solution.bounding_steps`, including `discovery/difficulty-weights/measure.py`, will treat the cheapest filler operation as the hardest class of move once slots are enabled. This recreates the exact classification inversion that introducing `LINEUP_ARITHMETIC` was meant to remove. Production is still contained because it passes no slots, but the API is incorrect for the feature under evaluation.
- **Reproduction:** Solve a one-row-per-slot shape with slots 1 through 9 and a given PA total of 39. The nine PA deductions all have `Technique.LINEUP_ARITHMETIC` and the solution has zero bounding stalls, but `bounding_steps` returns nine because all nine deductions have `known_terms_combined is None`.
- **Recommended fix and rationale:** Implement `bounding_steps` as an explicit count of `deduction.technique is Technique.BOUNDING`. Audit other properties that use `has_a_comparable_cost` as a technique proxy now that “not comparable” has two meanings, and add a regression asserting that the total-visible lineup solve has nine lineup steps, zero bounding steps, and zero stalls. Technique identity is the stable contract; cost availability is no longer an equivalent classification.

## Third-Pass Disposition (superseded)

- **`v27-P1-05` resolved in the generator solver:** `_lineup_moves()` now performs the quotient/remainder step directly, leaves a shared slot unsplit when two rows remain unknown, assigns the cheapest dedicated technique, and has end-to-end `solve()` tests. Production still passes no slots and is explicitly covered as unchanged.
- **Verifier limitation not duplicated:** the independent verifier has no corresponding value-aware step and would reject a board that relies on this constraint as underivable. This is explicitly recorded in the TODO and in the instrument output as pending only if the operator decides to ship the feature.
- **Experiment incomplete:** `arms.log` currently contains progress only through 10 of 48 directions. No coverage, technique, or payoff conclusion is available yet.

## Third-Pass Persona Summary (superseded)

| Persona | Result |
|---|---|
| Backend Architect | The new technique is correctly contained behind explicit slot metadata; no additional finding. |
| Python Principal Engineer | Raised `v27-P2-07`. |
| Frontend Engineer | No frontend changes are in scope. |
| QA / Reliability Engineer | Raised `v27-P2-06`. |
| Security Engineer | No security finding. |
| UX / Visual Reviewer | No user-interface or visual changes are in scope. |
| Baseball / Boxscore Domain Reviewer | The direct total-to-slot arithmetic and refusal to split two unknown substitute rows are correct. |
| Kakuro / Logic-Puzzle Reviewer | The generator now reaches the exact cyclic consequence; no new mathematical finding. |

## Third-Pass Verdict (superseded)

The central second-pass P1 is closed in the generator, and no numerical claim from the still-running experiment has been accepted. Two P2 integration findings remain: dependency provenance is incomplete for shared slots, and one legacy metric misclassifies the new cheapest technique as bounding. No P0, P1, or P3 finding is open from this third pass.

## Resolved Second-Pass Finding

### v27-P1-05: The interval solver cannot realize the exact deduction the corrected cyclic model promises

- **Persona:** Kakuro / Logic-Puzzle Reviewer
- **Priority:** P1
- **Location:** `forge/src/boxscore_forge/constraints.py:390`, `forge/src/boxscore_forge/constraints.py:421`, `forge/src/boxscore_forge/bounds.py:67`, `forge/src/boxscore_forge/bounds.py:103`, `discovery/batting-order/arms.py:154`
- **Description:** The first-pass repair now describes the correct feasible set: adjacent slot sums are monotone and slot 1 can exceed slot 9 by at most one. However, the solver propagates independent intervals rather than correlated integer solutions. Given only a known PA total, the column-sum equation, monotonic chain, and spread bound do not narrow any individual slot to the quotient/remainder prediction. The tests prove that valid vectors satisfy the relations and impossible vectors do not; they never call `narrow()` or `solve()` to prove the documented operational consequence that a known total determines all nine slot sums. There is a second measurement mismatch at the same boundary: all deductions obtained through inequalities are classified as `Technique.BOUNDING`, while `arms.py` interprets bounding PA deductions as reasoning and non-bounding deductions as filler. Even if the intervals happened to corner a PA cell, the total-visible arm would count the cyclic arithmetic as a stall rather than as the trivial quotient/remainder step that arm is intended to isolate.
- **Impact:** The corrected relations prevent impossible solutions, but `on_total_given` still does not represent “the player types nine values from one number.” Therefore the three-arm experiment cannot yet answer whether keeping the total visible creates filler or whether erasing it creates useful reasoning. It will either fail to expose deductions a human has immediately or attribute them to the difficult technique being measured. Production remains unaffected because the production erasure path still supplies no slots.
- **Reproduction:** Create a shape with one batting row in each slot 1 through 9 and give only `batting_totals.plate_appearances = 39` among the PA column. The column equation initially caps every slot at 39. Because all nine domains overlap at `0..39`, each adjacent inequality and the first/last spread inequality leaves those intervals unchanged; fixed-point propagation cannot reach the actual `(5, 5, 5, 4, 4, 4, 4, 4, 4)` distribution. Direct predicate tests pass because the relations are mathematically correct, but no cell is operationally deduced.
- **Recommended fix and rationale:** Add a value-aware cyclic propagator for the slot sums. When the team total is known, compute `divmod(total, 9)` and constrain each slot sum directly; when a slot has substitutions, constrain the sum of its rows rather than assigning one player. Mark this deterministic total-to-slot step separately from exploratory bounding so the total-visible arm can classify it as filler. A linear alternative is to add the position-specific bounds `9*S_i - T + i - 1 >= 0` and `T - 9*S_i - i + 9 >= 0`, but that requires teaching `_reach()` and `_divide()` about coefficient magnitudes and integer rounding; they currently assume coefficients of `1` or `-1`. Add end-to-end `narrow()` or `solve()` tests for totals with remainder zero and nonzero, including a shared slot. Satisfaction tests alone cannot establish solver behavior.

## Second-Pass Disposition of the Original Findings (superseded)

- **`v27-P1-01` resolved at the model layer:** both implementations now add the first/last spread bound and reject monotone-but-impossible distributions. Its promised solver behavior remains open as `v27-P1-05`.
- **`v27-P2-02` resolved:** persisted rows now include `offense` and `seed`, and per-board reporting groups by `(game, offense)`.
- **`v27-P2-03` resolved:** both trust boundaries require exactly the slot domain `1..9` while allowing duplicates for substitutions.
- **`v27-P3-04` resolved:** the TODO decision summary now reports 826,039 of 990,202 rows, or 83.4%.

`arms.log` remains empty, so no numerical conclusion from the three-arm experiment is available or reviewed.

## Second-Pass Persona Summary (superseded)

| Persona | Result |
|---|---|
| Backend Architect | The persisted trial identity repair is correct; no new finding. |
| Python Principal Engineer | The non-zero inequality constant is propagated with the correct sign; operational incompleteness is covered by `v27-P1-05`. |
| Frontend Engineer | No frontend changes are in scope. |
| QA / Reliability Engineer | The original regression cases are now represented, but an end-to-end solver case is still missing under `v27-P1-05`. |
| Security Engineer | No security finding. |
| UX / Visual Reviewer | No user-interface or visual changes are in scope. |
| Baseball / Boxscore Domain Reviewer | The corrected per-slot cyclic relation is faithful to the baseball rule for admitted directions. |
| Kakuro / Logic-Puzzle Reviewer | Raised `v27-P1-05`. |

## Second-Pass Verdict (superseded)

The four original v27 findings are corrected, and the run was stopped before an ambiguous artifact was spent. One P1 remains: the mathematical model is now exact, but the solver and experiment cannot yet realize or classify its central total-to-slot deduction. No P0, P2, or P3 finding remains open from this second pass.

## Resolved First-Pass Findings

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

## First-Pass Persona Review Summary (superseded)

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

## First-Pass Recommended Order of Work (completed)

1. Decide whether the feature is the full cyclic rule or only weak monotonicity, then make implementation, tests, and experiment describe the same mathematics before running `arms.py`.
2. Preserve seed and direction identity in the arm artifact before spending time generating it.
3. Reject incomplete slot domains at both trust boundaries.
4. Correct the stale payoff in the TODO summary.

## First-Pass Verdict (superseded)

Production behavior is unchanged because slots are not yet supplied by the production erasure path. That containment is valuable, but the new arm experiment should not be run for a decision in its current form: its central “constraint on” treatment is weaker than the cyclic rule it claims to evaluate. One P1, two P2, and one P3 finding were identified; no P0 finding was identified.
