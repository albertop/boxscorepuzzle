# Code review v01 — findings not accepted as stated

**Nothing was rejected.** All eight findings were verified in the code and all eight are fixed; the
record is in `todo.md`.

This file exists because one finding was accepted with its **scope corrected**, and a correction that
is not written down reads later as agreement.

---

## v01-P2-4 — accepted, but it was not a data bug

**The review's finding stands and the fix is done.** The model called the fourth footnote term
`reached_on_interference` and the package schema called it `catcher_interference`; it is now
`catcher_interference` everywhere, with a test asserting the model's dataclass fields equal the
package's column tuples.

**The scope correction:** the review's own text is careful about this — "the adapter in discovery
writes the internal field positionally, so the values move" — and that is right. **No board ever
carried a wrong number.** The two vocabularies never met at runtime, because the format stores arrays
and the adapter translates by position.

Worth stating plainly, because "CI abbreviation wrong at the boundary" invites the reading that
puzzles shipped with bad data. They did not. What was real is the fragility: a future reader taking
the column **by name** would have displayed or validated the wrong concept, and the tuple order would
have kept agreeing with itself the whole time. That is why it was worth fixing and why the fix is a
test rather than a data migration.

---

## Two things the review could not have known

Neither is a criticism of it; both are context that arrived after it was written.

**v01-P1-1 was live.** The predicate mismatch was contaminating a measurement running while the review
was being read, and a partially-applied fix of my own from that morning was the cause — the
replacement pattern had missed the `d.` prefix, so the shape query was fixed and the row query was
not. A half-applied fix reads exactly like a whole one.

**It also closed an open number.** The loader sweep had eight unexplained disagreements with the game
log, left open that morning rather than explained away. They were this bug, and they went to zero
with the fix.
