# Code Review v11

**Date:** 2026-08-19  
**Method:** Static review only. No tests, linters, type checkers, application commands, or Git commands were run.  
**Scope:** Files changed after `code_review_v10.md`, their affected contracts and tests, the previously read project guidance, and the updated `docs/reviews/todo.md`. Generated caches and `_not_in_use` were excluded. The empty `discovery/footnote-groups/results.txt` contains no result to review.

## Executive summary

This review found four new issues: one P1 defect in the revised blockage counterfactual and three P2 reliability defects in its trial accounting, report construction, and provenance. The fixes for all four v10 findings are present: schema construction and parsing now reject non-string slot references consistently, failed erasures are nullable, derivability is filtered to unique groups, and blockage uses paired solver closures. The new P1 is in the last of those repairs: its baseline does not always make the assignment available.

No item already recorded in `docs/reviews/todo.md` is repeated. In particular, `v05-P1-02` remains the sole open backlog item and the invalid pre-v10 group result remains historical rather than becoming a new finding here.

| ID | Priority | Perspective | Finding |
|---|---:|---|---|
| `v11-P1-01` | P1 | QA / puzzle logic | The counterfactual baseline leaves naturally erased group cells hidden |
| `v11-P2-01` | P2 | QA / data analysis | Blockage and usage rates compare groups with unequal or zero trial exposure |
| `v11-P2-02` | P2 | Python / reliability | Presentation titles silently select statistical denominators |
| `v11-P2-03` | P2 | QA / reproducibility | The provenance stamp does not identify the code that actually produced the result |

## Findings

### `v11-P1-01` - The counterfactual baseline leaves naturally erased group cells hidden

**Locations:** `discovery/footnote-groups/measure.py`, `groups_in()` baseline/treatment construction; `forge/tests/test_group_metrics.py`, `TestTheBlockagePredicateItself`

**Problem:** The intended comparison is the same erased puzzle with the footnote-group assignment available versus hidden. The baseline currently builds its givens by removing every cell in `erased`. If the sampled erasure already contains one or more cells from `hidden`, those group values remain absent from the baseline. The treatment removes `hidden` again, so those cells create no treatment difference. When an erasure already hides the whole group, baseline and treatment are identical and blockage is forced to `False` for that trial.

The new behavioral test mirrors this construction and asserts only `outside_before >= outside_after`. Equality satisfies that assertion, so the test still passes when no outside cell is ever stopped. It therefore does not enforce the class promise that the blockage predicate can become true.

**Impact:** The central group experiment systematically undercounts blockage on the exact published-puzzle states where footnote cells were selected for erasure. A zero or low rate cannot distinguish "revealing the assignment did not help" from "the baseline never revealed the assignment." Any generator constraint or attribution design chosen from that result would rest on a contaminated treatment comparison.

**Recommendation:** Build the baseline by restoring the group independently of the sampled erasure, for example by excluding only `erased - hidden` from its givens. Build the treatment by excluding `erased | hidden`. Extract that pair construction and the closure comparison into a pure function. Add a fixture whose erasure contains a group cell and for which revealing the complete group produces a strict outside-closure gain; assert the production predicate is `True`, not merely that one closure is a superset.

### `v11-P2-01` - Blockage and usage rates compare groups with unequal or zero trial exposure

**Locations:** `discovery/footnote-groups/measure.py`, `groups_in()`, `Group.trials`, `Group.stopped`, `_eligible()`, and `report()`

**Problem:** Only successful erasures enter `erasures`, so groups can receive one, two, or three trials. `blocked = stopped > 0` then turns those variable trial counts into one Boolean and gives every group equal weight. With the same per-trial blockage probability, a group exposed three times is more likely to be marked positive than a group exposed once.

The newer `used` metric has the inverse form of the v10 missing-trial defect: it defaults to `False`, and `_eligible()` excludes unmeasured groups only for the heading beginning with `HIDING`. A group with zero successful erasures therefore enters the usage denominator as a measured negative. Finally, the `Group` documentation says `trials` and `stopped` are printed beside the rate, but the tables print only the number of groups in the cohort.

**Impact:** Percentages vary with erasure success and seed count as well as with puzzle behavior. Cohorts that resist the target erasure receive fewer chances to become blockers, while completely unmeasured cohorts lower the usage rate. Readers cannot diagnose the bias because the output omits attempted, successful, and stopped trial totals.

**Recommendation:** Choose and label the estimand explicitly. For a per-trial rate, report `sum(stopped) / sum(trials)` and exclude groups with no successful trial. For an any-hit group rate, require the same number of successful trials per group, using deterministic replacement seeds or marking the group unmeasured. Make `used` nullable or apply the same measured-trial eligibility rule. Print attempted seeds, successful trials, stopped trials, and eligible groups for every cohort.

### `v11-P2-02` - Presentation titles silently select statistical denominators

**Locations:** `discovery/footnote-groups/measure.py`, `_eligible()` and `report()`; `forge/tests/test_group_metrics.py`, source-text denominator tests

**Problem:** `_eligible()` decides whether a group belongs in a calculation by checking whether the human-facing title starts with `DERIVABLE` or `HIDING`. Renaming, reordering, or localizing a heading can silently restore the unconditional derivability denominator or count unmeasured blockage trials as negatives. Statistical semantics therefore depend on display copy.

The tests search the source for fragments such as `group.completions == 1`; they do not call `report()` with mixed groups and verify the resulting denominator. The condition can remain somewhere in the file while no longer governing the relevant table.

**Impact:** A copy-only report edit can alter experimental results without touching an obvious calculation and without failing the current tests. This recreates the same class of defect the project has already encountered when formatting conventions were allowed to make domain decisions.

**Recommendation:** Define each report row with structured data: a stable metric identifier, an eligibility callable, a value callable, and presentation text. Pass eligibility directly rather than deriving it from the title. Add behavioral tests over a small mixed `Group` collection and assert both numerator and denominator for uniqueness, conditional derivability, blockage, and usage.

### `v11-P2-03` - The provenance stamp does not identify the code that actually produced the result

**Locations:** `discovery/footnote-groups/measure.py`, `stamp()` and `main()`; `discovery/footnote-groups/results.txt`

**Problem:** The `WHAT PRODUCED THIS` block reads `.git/HEAD` and, for a symbolic ref, reads only the corresponding loose ref file. It does not record whether the working tree differs from that commit, so an edited instrument can be labelled with the previous commit. It also produces a malformed revision when the ref is packed and does not support a worktree where `.git` is a file. More fundamentally, a commit alone does not identify the imported solver, erasure code, query/data snapshot, or the instrument contents when any are uncommitted.

The stamp is emitted only at the end to standard output. The script does not own result publication, so shell redirection can leave an empty or partial file after interruption. The current `results.txt` is zero bytes and consequently provides neither provenance nor a success marker; this review does not infer whether that run is active, failed, or not yet started.

**Impact:** Two outputs can claim the same revision while being produced by different code, and a partial artifact can occupy the canonical result path without declaring failure. That defeats the stated purpose of distinguishing current evidence from stale or invalid evidence.

**Recommendation:** Give the instrument an `--output` path and write a temporary artifact that is atomically replaced only after a successful run. Record a result-schema version, hashes of the instrument and relevant imported source, data/query snapshot identity, all sampling parameters, attempted and successful trials, and a completion marker. If Git metadata is retained, obtain it through a worktree-aware mechanism and include dirty state; never substitute the symbolic ref text for a revision hash.

## Security review

No new OWASP-class issue was identified in the changed surface. The reviewed changes affect local package validation and an offline discovery instrument, not a new trust boundary or network input. Because there is no new security finding, attack scenario, exploitation method, business impact, and security fix fields are not applicable.

## Perspective coverage

| Perspective | Result |
|---|---|
| Python principal engineer | Found string-driven control flow and incomplete repository-state handling; the v10 constructor boundary is fixed |
| QA and reliability | Found the invalid baseline, unequal exposure, non-behavioral tests, and non-transactional result artifact |
| Frontend engineer | No changed frontend surface and no new finding |
| Security / OWASP | No new security issue in the changed offline surface |
| Backend architect | Package validation now has one error contract; result publication still lacks an owned atomic boundary |
| Baseball / boxscore domain | Group membership remains tied to lineup slots and the four canonical footnote columns; no new domain-mapping issue found |
| Kakuro / logic-puzzle design | The counterfactual does not yet isolate assignment availability, so the blockage conclusion is not valid |
| UX / graphic design | No changed player-facing surface; report copy currently controls calculation semantics, covered by `v11-P2-02` |

## Further improvements

1. Move group measurement into pure functions accepting shape, values, hidden cells, and erased cells so tests can exercise the exact production predicate without a database or source inspection.
2. Separate exploratory summaries from decision gates. A sampled positive can demonstrate existence, but sampled negatives cannot prove that no deal can block without exhaustive coverage.
3. Preserve the previous valid result until a complete replacement is ready; an in-flight or failed run should use a distinct temporary path.

## Residual risk

This was a static review. The empty result artifact was not executed or diagnosed, and no numerical conclusion from the revised instrument was evaluated. Runtime behavior, erasure success coverage, database state, statistical outputs, and full-suite compatibility remain unverified by design.
