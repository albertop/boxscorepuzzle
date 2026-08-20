# Code Review v27 - Tenth Pass

## Scope

This pass reviews the revised correction for `v27-P3-16`:

- `discovery/batting-order/arms.py`
- `forge/tests/test_specimen_eligibility.py`
- The specimen mutations added to `discovery/batting-order/mutation_sweep.py`

Cache files and source timestamps produced by the mutation sweep's restore cycle were excluded from the correction scope. The batting-order fallback remains experimental and the verifier's value-producing lineup step remains deliberately deferred. No source code, tests, generated output, configuration, or planning document was changed by this review. Tests and static-analysis tools were not run.

## Tenth-Pass Correction Review

### `v27-P3-16` is resolved

`_classify_specimen()` now establishes eligibility before composition. It requires a retained `(arm, SPECIMEN_TARGET)` specimen for every arm that will be rendered, restricts treatment rows to the exact specimen target and to reached rows, and returns `None` rather than `negative` when that observation does not exist. Only an eligible reached treatment with zero lineup-arithmetic steps enters the contrast pool; a positive count enters the positive pool.

The focused test module covers a missing treatment, a missing baseline, a genuine reached-zero contrast, a reached-positive treatment, missing specimen maps despite optimistic rows, and a row from another target. The mutation sweep separately removes the both-pages check, converts an absent treatment observation into a contrast, and removes the target restriction. Those mutations match the three ways the correction could regress rather than merely restating its final syntax.

The defensive `never reached` branch in `_specimen_pages()` remains appropriate for direct or future callers, but the main selection path can no longer choose such a direction and then claim it as one of the completed specimen comparisons.

## Tenth-Pass Disposition

- `v27-P3-16` is materially resolved in the classifier, its call site, focused tests, and mutation definitions.
- The original quota fix `v27-P3-12` remains intact: pool composition is still enforced only after eligible candidates have been collected.
- The correction does not broaden production behavior or start the deferred verifier implementation.
- No new production, publication, research-validity, security, performance, test, or API-contract finding was identified.

## Tenth-Pass Persona Summary

- **Software architect:** Eligibility is isolated in a small classifier and the rendering/pool responsibilities remain separate.
- **Security engineer:** No practical security issue was introduced.
- **Performance engineer:** Classification is constant-size work and does not change the expensive measurement loop.
- **Test engineer:** Each meaningful branch has a focused case, and the sweep attacks the actual missing-observation regressions.
- **Data scientist:** An absent observation is no longer pooled with a measured zero.
- **Statistician/methodologist:** Both rendered arms must now exist at the same declared target before composition is evaluated.
- **UX/API contract reviewer:** A selected specimen once again guarantees the promised two-page comparison.
- **Solo-maintainer pragmatist:** The fix is local, explicit, and avoids redesigning the specimen pipeline.

## Tenth-Pass Verdict

The revised correction closes the remaining **P3**. No new P0, P1, P2, or P3 finding was identified. All findings active at the start of this pass are now resolved.

## Ninth-Pass Correction Review (superseded)

### `v27-P3-16` remains open

The submitted delta does not change the specimen classifier. At `discovery/batting-order/arms.py:519`, `uses_lineup` is still computed with `any(...)` over reached treatment rows, and line 524 still sends every false result to `negative`. Consequently, a treatment arm that never reached target 5 remains indistinguishable from one that reached it with zero lineup-arithmetic steps. There is still no eligibility check requiring both entries in `SPECIMEN_ARMS` to exist before the direction enters either pool, so `_specimen_pages()` can still emit `never reached` while the summary announces a completed contrast set.

The actual source change is at `discovery/batting-order/mutation_sweep.py:112`: it mutates `division_against_chain()` back to the old total-deduction denominator. That is a sensible additional check for the already-resolved `v27-P2-13`, and its mutation is narrowly stated. It neither modifies the specimen behavior nor adds a mutation/test that would detect an unreached arm entering the contrast pool.

## Ninth-Pass Disposition (superseded)

- No new finding ID is warranted; the behavior is exactly the still-open `v27-P3-16`.
- The correction needed in `arms.py` is still to exclude a direction from both pools unless every `(arm, SPECIMEN_TARGET)` in `SPECIMEN_ARMS` exists, then classify the reached treatment row by whether its lineup count is zero or positive.
- The new denominator mutation appropriately strengthens evidence for resolved finding `v27-P2-13`.
- No new production, publication, security, performance, or statistical defect was found in the submitted delta.

## Ninth-Pass Persona Summary (superseded)

- **Software architect:** No production boundary changed; the research selector remains the only open surface.
- **Security engineer:** No practical security issue was introduced.
- **Performance engineer:** The new mutation adds test-suite runtime only when the sweep is deliberately run; no product runtime changes.
- **Test engineer:** The denominator now has a useful mutant, but no guard was added for paired specimen eligibility.
- **Data scientist:** Missing treatment results are still classified as zero-treatment results in the specimen sample.
- **Statistician/methodologist:** The contrast pool still mixes a measured zero with an absent observation.
- **UX/API contract reviewer:** The artifact can still promise a rendered comparison and substitute a `never reached` message.
- **Solo-maintainer pragmatist:** One local eligibility condition in `arms.py` remains sufficient; broader work is unnecessary.

## Ninth-Pass Verdict (superseded)

The submitted change does **not** correct `v27-P3-16`. No new P0, P1, P2, or P3 finding was identified, but the existing **P3 remains open**. The only new source change is useful reinforcement for the already-closed denominator defect.

## Resolved Eighth-Pass Finding

### v27-P3-16 - An unreached arm can satisfy the promised no-arithmetic contrast quota

- **Persona:** Test engineer / UX evidence reviewer
- **Severity:** P3
- **Location:** `discovery/batting-order/arms.py:518`
- **Description:** The new two-pool selector correctly enforces the sizes of its positive and negative pools, but the classification still defines `uses_lineup` with `any(...)` over *reached* treatment rows. `False` therefore has two meanings: the treatment reached target 5 and used zero lineup-arithmetic steps, or the treatment never reached target 5 and produced no qualifying row. Both are appended to `negative`. The selector also does not require the baseline arm to have reached the specimen target. `_specimen_pages()` handles either missing arm by writing a `never reached` message instead of rendering that half of the comparison, while the summary still says that three boards with the declared two-positive/one-contrast composition were written.
- **Impact:** A normal rerun can pass the new quota, announce a complete contrast set, and replace one or more promised board pages with absence messages. That defeats the purpose of reading the same board under both arms and can leave the adoption decision resting on less visual evidence than the instrument claims to provide. This is limited to the research artifact and does not affect published puzzles.
- **Reproduction:** Use a seed-one direction whose `on_total_erasable` arm does not reach `SPECIMEN_TARGET`. The generator creates no `(on_total_erasable, 5)` specimen, the filtered `any(...)` returns `False`, and the direction enters `negative`. If selected as its first candidate, `_choose_specimens()` accepts it as the required contrast and `_specimen_pages()` emits `arm on_total_erasable never reached 5 stalls`. Similarly, a direction whose treatment reaches 5 but whose baseline does not can enter either pool and produce a missing baseline page.
- **Recommended fix and rationale:** Before classifying a direction, require `all((arm, SPECIMEN_TARGET) in specimens for arm in SPECIMEN_ARMS)`. Among those eligible paired specimens, classify the treatment row as positive when `pa_by_lineup > 0` and as contrast only when it reached the target with exactly zero lineup steps. Keep `_choose_specimens()` as the quota postcondition and add a focused case proving an unreached arm belongs to neither pool. Eligibility must establish that the promised comparison exists before composition can establish what kind of comparison it is.

## Eighth-Pass Disposition

- `v27-P2-13` is resolved. `division_against_chain()` now uses `solution.chain_length`, handles a zero-length chain explicitly, and the real fallback test makes chain length differ from deduction count so the denominator affects the verdict.
- `v27-P2-14` is resolved. The production-off guard now scans first-party calls to `erase()` rather than the internal `shape_of()` forwarding call, and its positive control establishes that the allowed experimental call is visible to the scanner.
- `v27-P2-15` is resolved for the current import architecture. The guard now starts from every first-party module and rejects any dependency closure reaching both fallback and certification; the stronger temporary rule also rejects every import of the experimental module outside its own tests.
- `v27-P2-11` is resolved. Every row now persists the completed walk's `walk_max_stalls`, and `_ceiling()` pairs those terminal values by direction and seed without conditioning on target success. Legacy artifacts produce an explicit `NOT ANSWERABLE` result instead of the old censored table.
- `v27-P3-12` is resolved as originally stated: separate pools and `_choose_specimens()` now enforce the requested numeric quota. `v27-P3-16` is the narrower remaining eligibility defect inside those pools.
- The expensive verifier lineup step remains deferred, consistently with the current plan. No new production solver, publication, security, or performance defect was found.

## Eighth-Pass Persona Summary

- **Software architect:** The experimental-to-publication import bridge is now guarded in the direction real wiring would take.
- **Security engineer:** No practical security issue was found in this delta.
- **Performance engineer:** The conditional retry still limits extra erasure work to ordinary misses; no new runtime concern was found.
- **Test engineer:** The five earlier guards/measurements are materially corrected; specimen eligibility still conflates a zero result with no result.
- **Data scientist:** Terminal walk ceilings are now retained independently of configured target crossings.
- **Statistician/methodologist:** The cap denominator now matches its recorded provisional unit, and the ceiling comparison no longer censors treatment-only reaches.
- **UX/API contract reviewer:** The specimen summary can still promise a rendered two-arm contrast when one arm has no board at that target.
- **Solo-maintainer pragmatist:** The only remaining change is local to the specimen classification in `arms.py`; no redesign is warranted.

## Eighth-Pass Verdict

One new practical finding remains: **one P3** (`v27-P3-16`). No P0, P1, or P2 finding was identified. All three seventh-pass P2 findings and both unresolved sixth-pass findings are materially corrected; the remaining issue affects the honesty/completeness of the research specimen pages, not production behavior.

## Resolved Seventh-Pass Findings

### v27-P2-13 - The provisional chain-share cap is implemented with a different denominator

- **Persona:** Statistician-methodologist / Test engineer
- **Severity:** P2
- **Location:** `forge/src/boxscore_forge/lineup_fallback.py:39`
- **Description:** The 20% threshold was derived from the two ATL cases as nine division steps over chain lengths 24 and 26, reported as 38% and 35%. `division_share()` instead divides lineup steps by `len(solution.deductions)`, the total number of solved blanks. The constant and review documents continue to call this a share of the chain, so the implementation applies the provisional number to a different metric from the one that produced it.
- **Impact:** A board the policy was introduced specifically to discard can pass when it has many deductions outside the critical chain. For example, nine lineup steps on a chain of 24 are 37.5% under the recorded rule, but nine among 50 total deductions are 18% under the code and are retained. That silently removes the only protection against the two known filler-heavy shapes.
- **Reproduction:** Construct a `Puzzle` whose solution has `chain_length == 24`, nine `LINEUP_ARITHMETIC` deductions, and at least 45 deductions overall. The documented chain share exceeds the 0.20 cap, while `division_share()` returns at most 0.20 and `erase_with_lineup_fallback()` does not discard it. The boundary table in `test_lineup_fallback.py:127` only evaluates `division / total` directly and never exercises which solution property supplies that denominator.
- **Recommended fix and rationale:** Either compute the recorded metric as lineup-step count divided by `solution.chain_length` (with an explicit zero-chain rule), or rename the metric and re-measure the threshold against total deductions before using 0.20. Add a test with different `chain_length` and deduction counts so changing the denominator changes the verdict. A provisional threshold may be soft; its unit cannot be.

### v27-P2-14 - The production-off test inspects an internal call that already carries slots positionally

- **Persona:** Test engineer / Solo-maintainer pragmatist
- **Severity:** P2
- **Location:** `forge/tests/test_lineup_fallback_cannot_publish.py:81`
- **Description:** `test_production_erasure_still_passes_no_batting_order` claims to inspect production callers of `erase()`, but it parses only `erasure.py`, finds calls to `shape_of()`, and checks whether they contain a keyword named `slots`. The one real call is `shape_of(direction, slots)` at `erasure.py:241`: it already passes slots positionally, so the guard succeeds because it checks syntax rather than activation. No caller of `erase()` is inspected.
- **Impact:** A production builder can start calling `erase(..., slots=lineup)` and this safety test remains green because `erasure.py` itself did not change. The test therefore cannot enforce the plan's load-bearing claim that production keeps omitting batting-order metadata.
- **Reproduction:** Add `slots=some_lineup` to any production `erase()` call outside `erasure.py`. The AST scanned by this test is unchanged, its `shape_calls` still contain no keyword named `slots`, and all assertions at lines 95-98 still pass.
- **Recommended fix and rationale:** Walk first-party call sites of `erase()` and refuse any `slots` argument outside the explicitly experimental module, or expose separate production and experimental entry points so production cannot name the option at all. Mutation-check the actual forbidden wiring by changing a real producer call, not the internal positional forwarding that both modes require.

### v27-P2-15 - Walking imports outward from certification cannot detect a producer that bridges the experiment to it

- **Persona:** Software architect / Test engineer
- **Severity:** P2
- **Location:** `forge/tests/test_lineup_fallback_cannot_publish.py:40`
- **Description:** The publication guard computes modules imported by `boxscore_verify.certify` and asserts that the fallback is not among its dependencies. Real publication wiring points in the opposite direction: a producer imports `erase_with_lineup_fallback()` and also imports `certify_for_publication()`. Adding that bridge does not make certification import the producer, so `_reachable(PUBLICATION_ENTRY)` is unchanged. The same directional blind spot applies to the four other verifier/package entry modules.
- **Impact:** The test can remain green after the exact wiring mistake it says it prevents. The fallback also returns the ordinary `Puzzle` type with no experimental provenance enforced at the certification boundary, so the import check is currently the claimed structural fence rather than a redundant defense.
- **Reproduction:** Create a producer module that imports both `boxscore_forge.lineup_fallback` and `boxscore_verify.certify`, then sends the produced board through the normal packaging/certification flow. None of the reachability searches starting from certification or package modules can traverse backward into that caller, so lines 66-79 still pass.
- **Recommended fix and rationale:** Scan producer/publication modules for any node whose dependency closure reaches both the fallback and certification, and independently make experimental provenance unrepresentable as an ordinary publishable result (for example, a distinct fallback result type accepted only by research code). A graph guard must follow the direction the forbidden call path actually takes; a type/data boundary makes the safety property survive refactors that change imports.

## Seventh-Pass Disposition (superseded)

- The conditional retry correctly attempts ordinary erasure first and uses the same candidate ordering and seed for the fallback attempt.
- `LINEUP_DIVISION_SHARE_CAP` is visibly marked provisional and its two-board origin is documented, but `v27-P2-13` applies it in the wrong unit.
- No value-producing lineup step was added to `boxscore_verify`; the expensive verifier work remains deferred as planned.
- The new publication tests demonstrate that the experimental module is not imported by today's verifier/package dependencies, but `v27-P2-14` and `v27-P2-15` show that they do not enforce the stronger no-wiring claim recorded in the plan.
- `v27-P2-11` and `v27-P3-12` were not touched by this delta and remain open in the sixth-pass section below.
- No new production solver arithmetic defect was found.

## Seventh-Pass Persona Summary (superseded)

- **Software architect:** The experimental module is isolated today, but dependency direction makes the claimed publication fence incomplete.
- **Security engineer:** No adversarial security issue found; the boundary problem is publication correctness.
- **Performance engineer:** The wrapper repeats erasure only after a miss, matching the intended cost profile.
- **Test engineer:** Two safety guards cannot fail under the activation paths they claim to prohibit.
- **Data scientist:** Conditional treatment is represented explicitly by the returned reason.
- **Statistician/methodologist:** The provisional threshold is applied to total deductions rather than the measured chain-share unit.
- **UX/API contract reviewer:** No shipped player-facing change is active.
- **Solo-maintainer pragmatist:** Fix the denominator and replace the two blind guards before relying on the freeze; all changes remain local.

## Seventh-Pass Verdict (superseded)

Three new practical findings remain: **three P2s** (`v27-P2-13`, `v27-P2-14`, and `v27-P2-15`). No new P0, P1, or P3 finding was identified. The fallback behavior itself follows the agreed conditional design, but its filler filter and two publication safeguards currently establish less than their documentation claims.

## Resolved Sixth-Pass Findings

### v27-P2-11 - The paired ceiling table discards the one-arm reaches that define a ceiling difference

- **Persona:** Statistician-methodologist / Data scientist
- **Severity:** P2
- **Location:** `discovery/batting-order/arms.py:367`
- **Description:** `_ceiling()` is built only from `_pairs()` at each target. `_pairs()` retains a row only when both arms reached that same target, so a walk that reaches 8 stalls under the treatment but only 6 under the baseline contributes neither its treated 8 nor its failed baseline 8. The loop then takes maxima over the surviving common-target snapshots and labels them the stall ceiling. Those snapshots are first crossings of the configured targets, not the maximum stalls observed over the completed erasure walk.
- **Impact:** The table can report equal ceilings after censoring the exact treatment gains or losses it is meant to summarize. The persisted run already shows 73 `on_total_erasable` target-8 reaches against 53 for `off`; at least 20 treated target-8 rows have no possible baseline target-8 counterpart and therefore cannot affect this ceiling table. Coverage reports that difference correctly, but the later paired ceiling summary can contradict or conceal it.
- **Reproduction:** Take any key that reached target 8 only under `on_total_erasable`. `_pairs(rows, "on_total_erasable", 8)` drops it. If both arms reached target 6, `_ceiling()` retains only their target-6 snapshots and may assign both a maximum near 6, even though one arm demonstrably continued to 8. A walk that continued beyond the largest configured target is also capped at its first target-8 snapshot rather than its actual terminal maximum.
- **Recommended fix and rationale:** Track the maximum stall count reached during the full accepted erasure walk for every `(game, offense, seed, arm)`, persist it independently of target reach, and pair those values by walk without requiring equal target success. Aggregate to direction only after computing the paired walk-level deltas. Alternatively, rename the current output to describe its actual value, but it cannot answer the ceiling question without retaining the terminal maximum.

### v27-P3-12 - The specimen selector does not enforce the contrast promised by its own rule

- **Persona:** Test engineer / UX evidence reviewer
- **Severity:** P3
- **Location:** `discovery/batting-order/arms.py:435`
- **Description:** The intended specimen set is cases using lineup arithmetic plus one deliberate contrast, but `if uses_lineup or not contrast` accepts every lineup-positive board even before a contrast has been found. If the first three eligible seed-one boards use lineup arithmetic, `chosen` fills to `SPECIMEN_BOARDS` and the later contrast can never enter. There is no final assertion that the declared composition or even the requested count was achieved.
- **Impact:** A normal rerun with a different sample order can silently produce an eye-check containing only treatment-positive examples while the output still cites `SPECIMEN_RULE` as the selection rule. The current artifact happens to contain a contrast, but the safeguard depends on data order rather than enforcing the evidence mix it claims.
- **Reproduction:** Let the first three seed-one boards have `uses_lineup=True`. Each satisfies the condition at lines 435-448, `len(chosen)` reaches three, and all later boards are skipped. The summary then prints `3 of 3 ... use lineup arithmetic` beside a rule that says there should be one contrast.
- **Recommended fix and rationale:** Collect lineup-positive and lineup-negative candidates separately, then deterministically choose the required quota only after measurement; fail clearly unless both pools can satisfy it. This turns the specimen rule from a comment about the current artifact into a postcondition of every rerun.

## Sixth-Pass Disposition (superseded)

- `v27-P2-09` is resolved. The mutation sweep runs an untouched baseline first, treats only pytest exit 1 as a killed mutant, and reports infrastructure statuses as broken rather than caught.
- `v27-P2-10` is resolved for blanks, PA techniques, and families: those tables now join by direction and seed within each target, while coverage deliberately remains unpaired.
- The persisted artifact contains 2,160 uniquely keyed rows: 48 directions, three seeds, three arms, and five targets, with no duplicate trial key found in the reviewed summary.
- The current specimen file uses explicit page separators and includes treatment-visible pages plus a contrast, but the selector does not guarantee that composition on the next run (`v27-P3-12`).
- The remaining analytical defect is isolated to the ceiling summary (`v27-P2-11`); it does not invalidate the unpaired coverage table or the correctly paired per-target tables.
- The verifier's value-aware lineup step remains pending in `todo.md` and is not duplicated here.

## Sixth-Pass Persona Summary (superseded)

- **Software architect:** No new production solver or verifier-rule defect found.
- **Security engineer:** No practical security regression found.
- **Performance engineer:** No practical runtime or memory regression found.
- **Test engineer:** The mutation harness is now fail-closed; the specimen quota still lacks a postcondition.
- **Data scientist:** The persisted rows are complete and pairable, but no terminal per-walk ceiling is retained.
- **Statistician/methodologist:** Per-target pairing is fixed; censoring one-arm reaches makes the ceiling comparison invalid.
- **UX/API contract reviewer:** The rendered evidence is readable, but future selection is not guaranteed to include its promised contrast.
- **Solo-maintainer pragmatist:** Both remaining fixes are local to `arms.py`; no broader redesign is needed.

## Sixth-Pass Verdict (superseded)

Two new practical findings remain: **one P2** (`v27-P2-11`) and **one P3** (`v27-P3-12`). No new P0 or P1 finding was identified. Both fifth-pass findings are resolved, and no new production defect was found; the open work is confined to accurately reporting the experiment's ceiling and enforcing the declared specimen mix.

## Resolved Fifth-Pass Findings

### v27-P2-09 - The mutation sweep treats an already-failing suite as ten successful guards

- **Persona:** Test engineer / Solo-maintainer pragmatist
- **Severity:** P2
- **Location:** `discovery/batting-order/mutation_sweep.py:99`
- **Description:** The sweep never establishes that the unmodified suite passes. For each mutation it defines `caught` as any non-zero pytest return code and reports that as success. An unrelated failing test, a collection failure, or another persistent pytest error therefore makes every mutation print `CAUGHT`; `failures` remains empty and the script exits successfully with the claim that all ten behaviors are guarded.
- **Impact:** The new tool can produce its strongest possible green result while proving nothing about any mutation. This is a direct false-positive in the safeguard introduced to stop plausible-looking but blind tests, and it can happen in this single-developer workflow whenever the sweep is launched before the ordinary suite has been brought back to green.
- **Reproduction:** Add or retain one unrelated always-failing forge test, then run `mutation_sweep.py`. Every mutated subprocess returns non-zero because of that same baseline failure, so lines 108-111 classify all ten mutations as caught and the final process exits zero.
- **Recommended fix and rationale:** Run the identical pytest command once against the untouched tree and abort unless it returns zero. For mutant runs, count pytest's ordinary test-failure result as a killed mutation, but treat interruption, internal error, usage error, and no-tests-collected statuses as sweep failures and print their captured output. A green baseline is the minimum evidence required before a red mutant says anything about the mutation.

### v27-P2-10 - The arm report records pairing keys but still compares different survivor populations

- **Persona:** Statistician-methodologist / Data scientist
- **Severity:** P2
- **Location:** `discovery/batting-order/arms.py:273`, `discovery/batting-order/arms.py:282`
- **Description:** `Row` now records `(game, offense, seed, target)`, which makes trials pairable, but `_report()` does not use that key. The blanks table independently selects reached rows for each arm, and the PA-technique table independently selects every reached row while also pooling all targets. Reachability is itself changed by the treatment, so the arms can contribute different directions, seeds, and target mixtures to the figures being compared.
- **Impact:** A difference in median blanks or bounding share can be caused by which trials survived in an arm rather than by the batting-order treatment on the same walk. The report can therefore attribute a cohort-composition effect to the constraint, even though the expensive artifact now contains exactly the fields needed to remove that confound.
- **Reproduction:** Consider a `(game, offense, seed)` that reaches target 8 only under `on_total_erasable`. Its target-8 row contributes to that arm's blanks median and technique totals, while no counterpart contributes to `off`. Whenever the coverage table differs between arms, the later tables are mechanically summarizing different populations; pooling targets adds a second unequal weighting.
- **Recommended fix and rationale:** Keep the coverage table unpaired, because failure to reach is its outcome. For treatment-effect tables, join rows by `(game, offense, seed, target)`, retain keys reached by both compared arms, and report paired deltas separately per target. If an overall technique summary is still useful, aggregate equal-weight paired results rather than raw cells from differently composed reached sets. This uses the pairing fields added for the experiment's stated comparison and isolates treatment from survivorship.

## Fifth-Pass Disposition (superseded)

- `v27-P2-08` is resolved. The test now has propagation deduce the companion PA, then asserts that lineup arithmetic depends on it and advances depth by one.
- The verifier regression now also asserts the semantic fields its structural comparison could not see: the spread constant and `equality=False`.
- The generator and verifier batting-order implementations reviewed here express the same cyclic bound in their respective inequality conventions; no new production-solver defect was found.
- The retained mutation sweep is directionally valuable, but `v27-P2-09` must be closed before its all-green summary is trustworthy.
- The persisted arm rows are now pairable, but `v27-P2-10` remains in the built-in analysis that consumes them.
- The verifier's lack of a value-aware lineup step remains explicitly pending in `todo.md` and is not duplicated as a finding.

## Fifth-Pass Persona Summary (superseded)

- **Software architect:** No new defect found in the generator/verifier rule boundary or dependency graph.
- **Security engineer:** No practical security regression found in the changed surface.
- **Performance engineer:** No practical runtime or memory regression found; the concerns are validity guards, not speed.
- **Test engineer:** The new mutation harness can false-pass without a green baseline (`v27-P2-09`).
- **Data scientist:** The raw rows preserve the identifiers needed for valid paired analysis.
- **Statistician/methodologist:** The current report ignores those identifiers and compares unequal survivor sets (`v27-P2-10`).
- **UX/API contract reviewer:** No shipped API or user-facing contract regression found.
- **Solo-maintainer pragmatist:** Both fixes are local to the two new research scripts and require no broader refactor.

## Fifth-Pass Verdict (superseded)

Two new practical findings remain: **two P2s** (`v27-P2-09` and `v27-P2-10`). No new P0, P1, or P3 finding was identified. The fourth-pass regression gap is closed, and no new production solver defect was found; the remaining risk is that the new validation and analysis scripts can report stronger evidence than they have established.

## Resolved Fourth-Pass Finding

### v27-P2-08 - The regression named for a deduced shared-slot dependency never creates one

- **Persona:** Test engineer / Statistician-methodologist
- **Severity:** P2
- **Location:** `forge/tests/test_batting_order.py:278`
- **Description:** `test_a_deduced_companion_is_an_edge_and_moves_the_depth` gives only the team plate-appearance total, deliberately leaves both rows in shared slot 9 unresolved, and then asserts that neither row was deduced. It never has propagation deduce one companion before lineup arithmetic solves the other, and it never asserts `depends_on`, `depth`, or `chain_length`. The production fix now carries deduced companions into the dependency graph, but this test does not exercise that behavior.
- **Impact:** The companion transport can regress while the newly added suite remains green. Removing the companion from `_lineup_moves` or from `_next_step`'s dependency set would again understate shared-slot chain depth, including the metric consumed by the arm comparison, without this purported regression test detecting it.
- **Reproduction:** In the setup at lines 282-289, neither shared-row PA is ever present in `solution.deductions`; the only assertion is that both remain absent. Revert only the companion contribution to `leaned_on` in `solver.py`: this test's result and assertion are unchanged because no dependency edge is ever produced.
- **Recommended fix and rationale:** Build a fixture where row identity first deduces one shared-slot companion's PA from its batting components, then lineup arithmetic derives the other row from the known slot total. Assert that the lineup step contains that deduced companion in `depends_on` and that its depth is one greater than the deepest deduced input. Keep the current unsplittable-sum scenario as a separate test. This makes the regression guard fail for the exact graph defect it claims to close.

## Fourth-Pass Disposition (superseded)

- `v27-P2-06` is fixed in production: shared-slot lineup moves now return known companions and `_next_step` includes deduced companions, while consistently excluding givens, from the dependency graph.
- `v27-P2-07` is fixed: `bounding_steps` now counts `Technique.BOUNDING` directly rather than deriving it from `trivial_steps`.
- The new tests cover direct lineup arithmetic, shared-slot non-splitting, given exclusion, and the corrected bounding count. The remaining gap is the ineffective deduced-companion regression in `v27-P2-08`.
- `discovery/batting-order/arms.log` is currently empty, so it provides no completed experimental result to assess in this pass.
- The verifier's inability to replay `LINEUP_ARITHMETIC` is already recorded as pending product work in `todo.md`; it is not duplicated as a review finding.

## Fourth-Pass Persona Summary (superseded)

- **Software architect:** The lineup dependency transport and direct bounding metric now match the intended model.
- **Security engineer:** No practical security regression found in the changed surface.
- **Performance engineer:** No practical runtime or memory regression found.
- **Test engineer:** One regression test does not execute or assert the behavior named by the test (`v27-P2-08`).
- **Data scientist:** No new arithmetic correctness defect found.
- **Statistician/methodologist:** Production chain-depth provenance is fixed, but its shared-slot deduced-input case remains unprotected.
- **UX/API contract reviewer:** No shipped API or user-facing contract regression found.
- **Solo-maintainer pragmatist:** Fix the single test gap; no broader refactor is warranted.

## Fourth-Pass Verdict (superseded)

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
