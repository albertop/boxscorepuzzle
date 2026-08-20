# Code Review v26 - Second Pass

## Scope

This review concentrates on the changes made since v25, with an intentionally close inspection of the new batting-order experiment and its generated result:

- `discovery/batting-order/measure.py`
- `discovery/batting-order/result.log`
- The corresponding conclusions recorded in `docs/reviews/todo.md`
- The updated session-persistence implementation and tests, to confirm the disposition of the v25 findings

No source files, tests, configuration, generated results, or planning documents were changed. Tests and static-analysis tools were not run as part of this review.

## Second-Pass Findings

### v26-P2-04: The exception-distribution report hides every category with zero exceptions

- **Persona:** QA / Reliability Engineer
- **Priority:** P2
- **Location:** `discovery/batting-order/measure.py:221`, `discovery/batting-order/measure.py:225`, `discovery/batting-order/result.log:23`
- **Description:** `_report()` constructs `whole` from all rows but iterates only over `spread.items()`, where `spread` contains values observed among exceptions. Any population category with no exception is therefore omitted instead of being printed as `0 / population`. The production result demonstrates this directly: it contains 6,276 extra-inning directions, all five exceptions are non-extra-inning directions, and the table prints only `False: 5/93,950`; it suppresses `True: 0/6,276`. The same omission affects source types, method codes, home/away, and last-batting categories whenever one side has zero failures.
- **Impact:** This table exists specifically to determine whether failures cluster. Suppressing zero-failure categories removes some of the strongest clustering evidence and can make a one-sided result look like an incomplete neutral split. The five-direction pool exclusion remains correctly counted, but the script cannot support its explanatory conclusions from the table as currently rendered.
- **Reproduction:** Run the current report and inspect the production `extra innings` row. The header reports 6,276 extra-inning directions, but that category is absent from the distribution because its exception count is zero. The same behavior follows directly from iterating `sorted(spread.items())` rather than the complete population keys.
- **Recommended fix and rationale:** Iterate over the keys in `whole` and obtain each numerator with `spread[value]`, which naturally returns zero for a missing `Counter` key. Sorting the complete population rather than the exception subset makes every comparison explicit and prevents absence from being mistaken for missing data.

### v26-P3-05: The projected payoff still includes the five directions the proposed pool rule removes

- **Persona:** Python Principal Engineer
- **Priority:** P3
- **Location:** `discovery/batting-order/measure.py:267`, `discovery/batting-order/measure.py:269`, `discovery/batting-order/measure.py:280`
- **Description:** `_what_it_buys()` labels its output as the payoff “if the pool rule made it exact,” but its `admissible` CTE applies only `candidates(gated=True)`. It does not exclude the five gated directions that fail the batting-order property. Consequently, the reported 826,080 directly determined rows out of 990,253 batting rows describe the current gated cohort of 100,226 directions, not the post-rule cohort of 100,221 directions.
- **Impact:** The numerical difference is very small and is unlikely to change the displayed 83.4%, but the experiment does not measure the population named by its heading. More importantly, future exception growth would silently make the payoff drift farther from the actual post-rule pool.
- **Reproduction:** The production section reports five exceptions. `_what_it_buys()` rebuilds the gated cohort without a predicate or key exclusion for those five directions, then aggregates occupancy over every row in that cohort.
- **Recommended fix and rationale:** Derive the failing `(GAME_ID, TEAM_ID)` keys once from the gated measurement and exclude those same keys from the payoff query, or express the batting-order validity predicate in a shared SQL CTE consumed by both measurements. Avoid hard-coding the present five IDs. Sharing the derived exclusion prevents the decision cohort and payoff cohort from drifting apart.

## Corrections Verified From the First Pass

- **`v26-P2-01` resolved:** The production measurement now passes the 30% zero-density gate, reports the 100,226-direction production cohort separately, and labels the 371,802-direction ungated cohort as structural evidence only. `_what_it_buys()` also uses the gated cohort.
- **`v26-P2-02` resolved:** The query now derives `batted_last` from home/away orientation and the terminal `x` marker in `HomeLineScore`. Home offense and last batting side are reported independently.
- **`v26-P3-03` resolved:** The strong hypothesis now says “at most one” cut point and explicitly documents the equal-slot case when total plate appearances are divisible by nine.

## Second-Pass Persona Summary

| Persona | Result |
|---|---|
| Backend Architect | No additional actionable finding. |
| Python Principal Engineer | Raised `v26-P3-05`. |
| Frontend Engineer | No frontend code is in the re-review scope. |
| QA / Reliability Engineer | Raised `v26-P2-04`. |
| Security Engineer | No security finding. |
| UX / Visual Reviewer | No user-interface or visual artifact is in scope. |
| Baseball / Boxscore Domain Reviewer | The revised home/last-batting distinction is materially correct for the measured game-log representation; no new actionable finding. |
| Kakuro / Logic-Puzzle Reviewer | The revised cyclic-distribution predicate and its prose now agree; no new actionable finding. |

## Second-Pass Verdict

The script's central measurement is now credible: it tests the correct production cohort, finds five explicit production exceptions, and no longer confuses home offense with the last batting side. The remaining P2 affects the interpretation of where exceptions cluster, not the five-direction exclusion itself. The P3 affects only the exactness of the projected payoff. No P0 or P1 finding was identified.

## Resolved First-Pass Findings

### v26-P2-01: The experiment measures a different population from the production puzzle pool

- **Persona:** QA / Reliability Engineer
- **Priority:** P2
- **Location:** `discovery/batting-order/measure.py:97`, `discovery/batting-order/measure.py:228`, `discovery/batting-order/result.log:5`, `discovery/batting-order/result.log:81`, `docs/reviews/todo.md:2274`, `docs/reviews/todo.md:2288`
- **Description:** Both database paths build the canonical eligibility predicate with `eligibility(seasons=...)`, but neither supplies the production zero-density gate. The experiment therefore applies the cap, provenance, log-coverage, and season rules while still admitting directions above the generator's 30% zero-density ceiling. This is visible in the reported population of 371,802 directions, rather than the previously established gated production cohort of 100,226 directions. The same mismatch affects the reported 75.1% occupancy payoff.
- **Impact:** The TODO currently uses the 35 exceptions from the ungated population to justify a production pool rule. Until the exceptions are measured inside the actual production population, the rule may reject unnecessary records, and its stated affected count is not established. The structural hypothesis may still be correct, but this run does not prove its effect on the shipped pool.
- **Reproduction:** Compare the two `eligibility(...)` calls in this script with the production-cohort construction used by the accepted footnote-multiplicity experiment, which passes `zero_density_clause(ZERO_DENSITY_GATE)` as `gate_clause`. A direction satisfying the current predicates but exceeding 30% zero density is included by this script and excluded by the generator.
- **Recommended fix and rationale:** Import `zero_density_clause` and `ZERO_DENSITY_GATE`, create one local production-cohort helper that passes the gate clause, and use it in both `_rows()` and `_what_it_buys()`. Rerun the result and revise the TODO decision from that output. If the ungated population remains diagnostically useful, report it separately and label it explicitly as outside the production pool. This keeps the research population aligned with the decision the research is intended to support.

### v26-P2-02: `offense_is_home` is incorrectly analyzed as “batted last”

- **Persona:** Baseball / Boxscore Domain Reviewer
- **Priority:** P2
- **Location:** `discovery/batting-order/measure.py:111`, `discovery/batting-order/measure.py:127`, `discovery/batting-order/measure.py:134`, `discovery/batting-order/measure.py:150`, `discovery/batting-order/measure.py:179`, `discovery/batting-order/result.log:5`, `discovery/batting-order/result.log:46`, `docs/reviews/todo.md:2294`
- **Description:** The query selects `offense_is_home`, but the reporting code renames that value `walkoff_side` and labels it “batting last.” Home/away orientation does not identify which team made the game's final plate appearance. For example, when the home team leads after the top of the ninth, the visitors bat last and no bottom of the ninth is played, even though the home direction still has `offense_is_home = true`.
- **Impact:** The conclusion that exceptions do not cluster by whether a team batted last is unsupported; the experiment only shows that they do not cluster by home/away side. Consequently, this dimension cannot yet support the TODO's interpretation that the exceptions look like transcription noise rather than terminal-game effects.
- **Reproduction:** Select any regulation home win in which the home team already leads after the visitor's final half-inning. The script counts the home direction under “batting last,” although the visitor made the game's last plate appearance. Its near-half population split is the expected home/away orientation split, not evidence about terminal batting order.
- **Recommended fix and rationale:** Either relabel the dimension consistently as “home offense” and remove conclusions about batting last, or derive the actual final batting side from the terminal line-score/event evidence and document how shortened, walk-off, and extra-inning games are handled. Then rerun the clustering analysis and update the result and TODO. This preserves a valid home/away comparison while preventing it from being interpreted as a different baseball fact.

### v26-P3-03: The stated “strong” hypothesis and its executable check disagree

- **Persona:** Kakuro / Logic-Puzzle Reviewer
- **Priority:** P3
- **Location:** `discovery/batting-order/measure.py:7`, `discovery/batting-order/measure.py:65`, `discovery/batting-order/measure.py:77`, `discovery/batting-order/measure.py:151`, `discovery/batting-order/result.log:6`
- **Description:** The module defines the strong hypothesis as having “exactly one step down,” but `faults()` accepts zero cut points. Zero cuts are also required by `predicted()` whenever total plate appearances are divisible by nine, because every slot then receives the same value. The reported count said to satisfy all three hypotheses therefore includes records that do not satisfy the strong hypothesis as written.
- **Impact:** The primary determined-distribution test and its exception set are not harmed, but the independent strong-hypothesis success count and the prose interpretation of “all three claims” are inaccurate. This makes it harder to tell whether the code or the stated mathematical claim is authoritative.
- **Reproduction:** Pass `[4, 4, 4, 4, 4, 4, 4, 4, 4]` to `faults()`. It returns no fault and equals `predicted(36)`, despite containing no step down and therefore violating the literal “exactly one” definition.
- **Recommended fix and rationale:** If the intended property is the one implemented, define it as “at most one cut point, with a drop of exactly one when the total has a nonzero remainder modulo nine.” If exactly one cut is genuinely required, add a zero-cut fault and report that claim separately from the determined-distribution result. Aligning the prose and predicate makes the experiment reproducible without changing the useful mathematical rule.

## First-Pass Persona Summary (superseded)

| Persona | Result |
|---|---|
| Backend Architect | No additional actionable finding in the reviewed changes. |
| Python Principal Engineer | No additional actionable finding beyond the experiment-construction issues above. |
| Frontend Engineer | The changed phone restore call site is consistent with the updated validation contract; no new finding. |
| QA / Reliability Engineer | Raised `v26-P2-01`. |
| Security Engineer | No security finding in the reviewed changes. |
| UX / Visual Reviewer | No user-interface or visual regression identified in the reviewed changes. |
| Baseball / Boxscore Domain Reviewer | Raised `v26-P2-02`. |
| Kakuro / Logic-Puzzle Reviewer | Raised `v26-P3-03`. |

## Previous Review Disposition

The two v25 findings are recorded as closed in the updated TODO. Session restoration now has malformed-payload coverage and delegates semantic validation to the game layer, while the persistence contract is documented consistently. Neither finding is repeated here.

## First-Pass Recommended Order of Work (superseded)

1. Rerun the experiment against the exact production-gated cohort before adopting the 35-row exclusion rule.
2. Correct or relabel the home-versus-terminal-batting analysis before using it to characterize the exceptions.
3. Make the strong-hypothesis wording match its predicate.

## First-Pass Verdict (superseded)

The new script provides a useful and potentially high-value structural result, but the current output is not yet sufficient to authorize the proposed production-pool rule. The cohort mismatch and the home/last-batting conflation should be resolved first. No P0 or P1 finding was identified.
