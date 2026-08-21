# Code Review v33

**Date:** 2026-08-20  
**Project context:** solo-developer application  
**Method:** static review of the v33 source, tests, operational script, and current Markdown contracts. No tests or validation commands were run.  
**Filing rule:** only a reproducible failure in an intended flow, with concrete impact and a proportional fix, is an issue. Research questions and dormant product choices are not defects.

## Findings

### v33-P3-01 - The postseason source gate fails for an unexpected file that the season floor already excludes

**Status:** ✅ **Closed 2026-08-20.** Accepted as filed and fixed as proposed: an unexpected kind is fatal
only when it carries a season at or above the floor. A file proved entirely below it is reported under a
`NOTE` block and the run passes, because the pool already excludes every game in it — a check that fires
when nothing is wrong is one that gets loosened until it says nothing.

⚠️ **And the review's own proviso was a second defect, not a detail of the fix.** *"Keep an unexpected file
with no readable `id,` season as fatal"* was describing behaviour the script did not have: empty `$seasons`
made `$above` empty too, and the message was chosen from `$above` alone — so a file whose contents could
not be classified announced itself as **"all below the floor"**. Unreadable was indistinguishable from
safely old, three lines under a comment about that exact shape. It is now fatal and says why.

Verified against four synthetic downloads rather than by reading the change: only-`.EVE` passes, a `.EDN`
of 1950 games passes with the note, a `.EDN` of 1975 games fails, and an entry with no parseable `id,` line
fails. The real `events-post` directory still passes.


**Location:** `discovery/retrosheet-coverage/check_postseason_sources.ps1:59`

The script correctly computes `$above`, the seasons in an unexpected event-file kind that are at or above
`$SeasonFloor`. It also prints `all below the floor` when that set is empty. But line 61 adds the file to
`$offenders` in both cases, and every offender causes the script to throw at line 86.

**Reproduction:** Put an unexpected `.E??` entry in the postseason download whose `id,` records are all
before 1969, then run the documented reload check with the default floor. The script reports that the file
is entirely below the floor and still exits as failed, claiming that the floor no longer protects the pool.

**Impact:** This is a false operational gate. A Retrosheet reload that adds only source material outside the
admitted postseason range blocks the documented procedure and tells the operator to move the floor or add a
provenance table even though the SQL already excludes every affected game.

**Proportional fix:** Add an unexpected file to the fatal list only when it contains a season at or above the
floor. Keep an unexpected file with no readable `id,` season as fatal so the script continues to fail closed;
an unexpected file proved to be entirely below the floor may be reported separately without failing.

## Decisions deliberately not filed as bugs

The new aggregate checks over the printed boxscore do not reopen the retracted row-level requirement in
`v30-P1-02`. The corrected v30 contract explicitly permits aggregate corroboration and rejects only turning
the verifier into a second row-by-row Retrosheet validator; `check_printed_boxscore_corresponds()` stops at
that boundary.

Postseason publication remains opt-in in the loader and is still recorded as a product decision rather than
an active production path. Its lack of a caller is therefore not filed as an implementation defect.

## Review result

No P0, P1, or P2 defects were found. One P3 operational defect was open; **it is closed.**

⚠️ **One thing found while acting on this review, in the ledger rather than the code.** v33 refers to
*"the corrected v30 contract"* for `v30-P1-02`, and `code_review_v30.md` was **saying two opposite things
about that id**: retracted at the top and in its closed-findings list, and restated below under
`## Findings` as a live P1 whose *"Recommended fix"* is the row-level certification the operator refused —
with two summary lines still calling it a defect. Anyone going to the detail to act met an open mandate.
Two places that should agree, disagreeing, with nothing checking that they do: this project's most common
defect, found in the file that records them. The finding is now marked retracted where it is stated,
folded away, and kept rather than deleted, because the reasoning explains where the boundary sits.
**The retraction stands, confirmed by the operator.** The regular-season provenance path
continues to fail closed, postseason table selection travels as one `Season` record, publication evidence is
bound to the package identifier, and the v33 certification changes introduce no additional demonstrated
failure in the current publication path.

