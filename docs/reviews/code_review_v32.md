# Code Review v32

**Date:** 2026-08-20  
**Project context:** solo-developer application  
**Review rule:** only reproducible defects with concrete impact and a proportional fix are filed. Research questions, historical limitations, adversarial local edits, and complexity that the product does not need are excluded.

## Findings

### v32-P3-01 - The batting-order discovery script still reports that the verifier cannot check lineup deductions

**Status:** Resolved  
**Location:** `discovery/batting-order/arms.py:567`  
**Contradicting implementation:** `forge/src/boxscore_forge/lineup_fallback.py:25`

**Resolution:** The report now limits its warning to what the run genuinely does not measure: whether
the generated boards pass verifier layer 3. It explicitly retracts the former claim, identifies
`boxscore_verify.reason.lineup_values()` as the independent verifier step, and no longer presents
completed verifier work as a release blocker.

`arms.py` unconditionally ends its current report by saying that the verifier has no twin of the lineup step and therefore would refuse a board whose unique solution depends on that step. That was true during the investigation, but it is no longer true: the verifier now has the independent, value-producing `lineup_values()` implementation that made adoption possible.

**Normal-flow reproduction:** Run the maintained batting-order arm report and read its final `NOT MEASURED HERE` block. The warning describes a verifier limitation that the current source no longer has.

**Impact:** A developer using the script for the decision it was built to support receives a false release constraint. That can send the project back into already-completed verifier work or incorrectly disqualify valid boards.

**Proportional fix:** Replace the stale footer with the verifier's current status. Keep any genuinely unmeasured property separate from the removed limitation.

### v32-P3-02 - The serve-flow document says the packaged reveal is never shown, but the shipping shell shows it

**Status:** Resolved  
**Location:** `docs/serve-flow.md:229` and `docs/serve-flow.md:353`  
**Current implementation:** `serve/ui/phone/shell.js:172` and `serve/ui/phone/finish.js:88`

**Resolution:** Both sections now describe the implemented successful-check and finished-session restore
paths. The obsolete statement is retained only inside an explicit historical note, and the implementation
order section says that persistence and the reveal are complete.

The document twice states that the reveal ships in every package but is "drawn nowhere" and is the one payoff the player never receives. The current finish path calls `renderReveal()` after a successful check and also restores the reveal for an already-finished saved session.

**Normal-flow reproduction:** Follow the documented serve flow, then solve a board in the current phone UI. The UI presents the reveal even though the document describes that step as absent.

**Impact:** This is the main implementation-flow document, so its false current-state claim can cause duplicate work and incorrect review conclusions about the finish experience.

**Proportional fix:** Rewrite the two stale current-state sentences to describe the implemented finish and restore behavior. Preserve historical context only if it is explicitly labelled as history.

## Review result

No P0, P1, or P2 defects were found. Both P3 findings were corrected and no new defect was introduced by
their fixes. No issue was opened for the batting-order causal measurement, the unplayed half of a historical
game, or other investigation questions that do not demonstrate broken product behavior.
