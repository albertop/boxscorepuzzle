# Findings not fixed as stated

**Nothing has been rejected as wrong.** Every finding in every review was verified in the code. This
file holds the ones that were **not fixed as written** — a scope correction, or a decision that the
failure mode cannot arise in this environment — because a decision that is not written down reads later
as agreement, and a silently skipped finding is a hole nobody knows about.

`todo.md` holds what was fixed. This holds what was not, and why.

---

## ⚖️ The environment the reviewer cannot see

**One laptop, the operator and Claude. No CI yet, no second developer, no concurrent editors, no
adversary inside the repository.** The reviewer reasons from a generic professional setup, so it
produces findings that are correct in the abstract and unreachable here.

⚠️ **The test is *does this need a second actor or a second process I do not control?*** — not *is this
unlikely*. The distinction is easy to get backwards:

| | |
|---|---|
| **Declined** | needs a second developer, a shared build agent, a hostile contributor, a race between two humans |
| **Fixed** | reachable by one person on one machine, however exotic it sounds |

`v16-P2-01` is the worked example of the second row. It arrived with an attack scenario about a
compromised build step, which is not reachable here — but the defect underneath was **two innocent
untracked trees producing one identity**, which needs no second actor at all. Reading only the framing
would have declined a real correctness bug.

Every entry below names what would have to change about the environment for the finding to become real.

---

## v16-P1-01 (the launcher half) — declined: needs a second editor or an unattended scheduler

**Fixed:** the tracked half. Paths now come from the binary diff itself, so that digest is one snapshot
and cannot contradict itself.

**Declined:** closing the remaining windows — Python imports the instrument before `identify()` runs,
and untracked files need a listing and a read. Both are millisecond gaps between operations in one
process on one machine.

The repair is a launcher that captures a manifest, starts the worker from a clean git worktree matching
it, and publishes only from there. That is a larger mechanism than the instrument it would protect.

**Would become real with:** CI, a second developer, or any scheduler running the instrument unattended
while the tree can change.

---

## v17-P2-01 (digest widths) — declined: needs an adversary generating candidates

The tracked and untracked digests show 64 bits; the instrument, board and aggregate digests show 48. A
birthday collision needs about 2³² and 2²⁴ **deliberately generated** candidates respectively.

**Nothing generates candidates here.** With four hundred real boards the accidental collision
probability at 48 bits is around 3 × 10⁻¹³, and the tree digests cover files nobody is manufacturing.
The exploitation path the finding describes — preparing two families of trees and searching offline for
a cross-family collision — requires a contributor or a compromised build step, neither of which exists.

⚠️ **This is declined on the threat, not on the cost.** Widening the slices is a one-character change,
and it is not being made because bumping the result schema a third time to defend against an absent
adversary is churn that makes artifacts harder to compare, not easier.

**Would become real with:** any actor who can put files in the tree and wants an approved provenance
label. If that ever happens the fix is to take full SHA-256 everywhere and move the schema once.

---

## v01-P2-4 — accepted, but it was not a data bug. **A scope correction, not a decline**

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
