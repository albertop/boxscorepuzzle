# Code Review v24

Date: 2026-08-20

## Result

No new findings. No P0, P1, P2, or P3 finding is reported.

This pass reviewed every file changed after v23: the string catalogue, phone shell, phone-board
renderer, browser tests, and the updated review ledger. Both v23 findings are closed and are not
repeated.

The accessible cell name is now derived from the same rendered value as the visible cell on every
`paint()` call, including the initial blank state, changed values, clearing, and innings display. The
thirds rule now lives in the importable `applyKey()` path, refuses non-innings cells independently of
the UI, and is mirrored by disabled keypad controls that follow selection.

Known work already recorded in `docs/reviews/todo.md` is excluded: persistence, reveal, timer,
Done-time validation, routes, the hand-solve decisions, the remaining six-pitcher measurements, the
unexplained 8-stall coverage difference, the volume generator, and unfinished product surfaces.

No tests, linters, type checks, builds, browser runs, or accessibility-tool runs were performed during
this review.

## Backend Architect

No new practical backend finding was found. The reviewed changes stay in the phone presentation and
input boundary and do not alter the package or verification contracts.

## Python Principal

No Python files changed after v23, and no new Python finding was found in the reviewed integration
surface.

## Frontend Engineer

No new frontend finding was found. `paint()` computes one `shown` value and uses it for both
`textContent` and the accessible name, preventing the two representations from diverging. The base
row/column label is installed before the first paint, so the opening blank state is also complete.

## QA / Reliability

No new reliability finding was found. The tests cover enter, change, clear, initial blank naming,
handler-level refusal of thirds on plain integers, successful thirds input on outs, and the keypad's
enabled and disabled states. The handler guard and disabled controls protect different paths rather
than duplicating one assertion.

## Security

No new practical security finding was found. The reviewed changes do not add an attacker-controlled
network, credential, authorization, storage, or command-execution boundary, so attack-scenario fields
are not applicable.

## UX / Visual

No new interaction or visual finding was found. A thirds control is unavailable until an outs cell is
selected, and the handler still refuses the operation if it arrives through another path. Filled,
selected, and peer cell styling is unchanged from the already recorded cascade correction.

## Baseball / Boxscore

No new baseball-semantic finding was found. Whole-number statistics remain whole-number inputs, while
pitching rows and pitching totals continue to express outs as conventional fractional innings.

## Kakuro / Logic-Puzzle

No new deduction or puzzle-state finding was found. The input changes alter only how a valid integer is
entered and announced; they do not change cell identities, uniqueness, derivability, or completion.

## Residual Risk

The new DOM tests verify attributes and rendered values but do not exercise an actual VoiceOver,
TalkBack, or browser accessibility tree. That is a validation gap rather than a code finding: the
reviewed implementation keeps the accessible and visible value in one computation, and no conflicting
path was found.

## Recommendation

No code change is requested from v24. The next useful validation for this specific change is a short
manual pass with a real phone screen reader when the phone shell is next exercised; it does not block
the reviewed implementation.
