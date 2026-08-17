# Boxscore Puzzle — Design Document

> Status: **Level 100 (what and why).** No implementation decisions.
> Domain: `boxscorepuzzle.com`
> Target launch: Spring Training 2027
> Last updated: August 15, 2026

---

## 1. Concept

### The one-line pitch

> **A daily puzzle where you reconstruct the boxscore of a real Major League game by logic.**

Conversational version, for explaining fast: *"Sudoku with real baseball boxscores."* Technically it's kakuro, not sudoku, but the imprecision earns its keep: it communicates in three words that this is deduction, that it's daily, and that there's no guessing.

The official definition says **"real"** and **"by logic"** — the two differentiators against Immaculate Grid and against cosmetic baseball-sudoku products.

*Neither version mentions the reveal, the archive, or the stats. That's correct: if the pitch needed to explain monetization, something would be wrong with the product.*

### Description

A website that publishes a daily puzzle built on the boxscore of a real Major League game. The boxscore is shown with cells erased, and the player reconstructs them. The solution is unique and reachable by deduction, never by guessing.

**Why it works:** a boxscore is an overdetermined system of integer equations. Baseball's accounting identities force the missing values.

**What it is NOT:** it is not reconstructing play-by-play from the boxscore. That mapping is massively many-to-one and has no unique solution.

### Anti-goals

Approved as explicit product boundaries:

- **Not trivia.** You don't answer with baseball knowledge, you answer with deduction. This is the line separating this from Immaculate Grid.
- **Not a simulator.** The game is not reconstructed play by play.
- **Not a stats tool.** Even though the data comes from Retrosheet, this is not for querying or analysis.
- **Not a baseball social network.** There is comparison among friends, but no profiles, walls, or forums.
- **Not a sudoku app with a baseball skin.** It's the reverse: baseball is the substance, not the veneer.

**The first one matters most**, because that's where real pressure will come: it will be tempting to add "guess the player" or trivia questions to make it more accessible. That would dissolve the product — **a puzzle is either deduction or guessing, not both.**

---

## 2. Target audience

**The baseball fan**, not the puzzle solver.

Consequences:

- Vocabulary (AB, R, H, RBI, BB, K, IP, ER) is assumed known. No need to teach it.
- Keep the **canonical boxscore format**. Visual familiarity *is* part of onboarding. Do not "simplify" the design.
- The risk inverts: the danger isn't that baseball scares people off — it's that the fan **isn't a puzzle person** and lacks patience for constraint propagation. The opening curve must be gentler than a sudoku site's.
- Distribution channel: baseball communities (newsletters, SABR, forums), not puzzle communities.

---

## 3. The logic engine

### Constraint families

**Equalities**

- Σ individuals = team totals (AB, H, R, RBI, BB, K)
- PA = AB + BB + HBP + SF + SH
- **PA = Outs + R + LOB** — every batter either makes an out, scores, or is left on base
- Outs = 3 × IP by opposing pitchers (adjusted if the home team doesn't bat in the 9th)
- Σ runs per inning = total R in the line score
- **Cross-team constraint:** team A's H = Σ hits allowed by team B's pitchers (same for BB, K, R)

**Inequalities**

- H ≥ 2B + 3B + HR
- AB ≥ H
- ER ≤ R
- RBI ≥ HR (per player)
- Team RBI ≤ team R
- Non-negativity in all cells

### The cross-constraint is the essential part

Without the constraint linking one team's offense to the opposing pitching line, the puzzle degenerates into row arithmetic. That cross-link is what makes it a real puzzle.

---

## 4. Deduction, not guessing

**The real risk isn't ambiguity — it's derivability.**

A uniqueness proof guarantees one answer exists, but does **not** guarantee a human can reach it by reasoning. You can generate unique-solution puzzles whose uniqueness depends on a system of four simultaneous unknowns. Mathematically perfect, and the player experiences them as trial and error.

### The technique ladder

| Level | Technique |
|-------|-----------|
| T1 | Equation with a single unknown → direct solve |
| T2 | T1 propagated to fixed point |
| T3 | Two equations sharing unknowns → 2×2 system |
| T4 | Bounding by inequality (AB ≥ H, ER ≤ R, non-negativity) |
| T5 | Global team identity: PA = Outs + R + LOB |

**Publication rule:** a puzzle ships only if a solver implementing exclusively T1–T5 solves it **without backtracking**. If it needs to guess a single cell, it's discarded or given one cell back as a hint.

Secondary benefit: difficulty derives itself — the highest technique required and how many times.

### Two properties that bring it close to sudoku

- **Bounded domains.** If the team has 8 hits, no individual H cell can exceed 8. Enables a **candidates mode** (pencil marks) that makes the deduction visible.
- **Self-verifying.** If all equations balance, the player knows they're done without the site confirming it.

### What must be accepted

In sudoku all 81 cells mean the same thing. Here each column has its own semantics and the player must learn boxscore accounting. That forces an onboarding curve.

---

## 5. Daily game selection

**Criterion: random among games with good puzzle shape.** Not anniversaries, not historical significance.

This makes the **quality metric** a central design piece:

- **Compressibility** — max % of cells removable while preserving uniqueness. The primary metric, expensive to compute; only run on candidates that pass the prefilter.
- **Zero density** — a 3-hit game leaves almost everything at 0 and cells force themselves. Penalize.
- **Roster compactness** — hard filter. **⚠️ Thresholds provisional** (≤10 batters in the offensive
  team, ≤3 pitchers in the defensive team). These are unvalidated estimates pending the measurements
  in §6. Note the filter is **asymmetric**: only the offensive team's batters and the defensive
  team's pitchers appear on the board.
- **Line score variety** — discard 0-0-0-0-0-0-1-0-0.
- **Digit range** — numbers > 3 should appear in several columns.

**Measured funnel (August 2026), counted by direction:**

| Step | Directions | Survives |
|---|---|---|
| Games with event files (203,908) | 407,816 | — |
| Minus deduced (3,465 games) | 400,886 | 98.3% |
| Roster fits the board (provisional caps) | 65,522 | 16.3% |
| Minus discrepancies against official data in board columns | 55,024 | 84.0% |

**The pool holds.** Even if the remaining quality filters cut 80%, that leaves ~11,000 puzzles —
thirty years of daily play, plus a substantial archive at launch (§10).

**55,024 is an upper bound, not the pool.** Compressibility, zero density, line score variety, and
digit range are still to be applied, and compressibility is the expensive one that actually decides
whether a boxscore is a puzzle. Expect a significant further cut.

**Caveat:** the discrepancy filter only covers 1898–1986. From 1987 on, "no reduction" means "not
measured," not "clean" — though modern rosters barely pass the roster filter anyway, so those years
contribute little.

**Era skew, measured:** the pool sits **62% in 1910–1949** and only 30% in 1950–1985 — older than
originally assumed. The 2020s contribute 66 directions against 13,782 from the 1910s. The batter cap
is the cause, not a historical preference.

This is acceptable: the target market is the United States (§20), and 1910–1949 is the most
mythologized era of American baseball. **Do not weight the calendar by era yet** — the measurement
is pre-quality-filter, and both zero density and digit range select *against* low-scoring games,
which are concentrated in the dead-ball era. The distribution may shift forward on its own. Re-measure
after compressibility.

---

## 6. The board — mobile decides the UX

**Decision: the phone screen defines the design.**

### Why the general rule doesn't apply

**The board cannot change by screen size.** This is a shared daily puzzle: everyone solves the same one. There can't be a reduced phone version and a full desktop version, because it would stop being the same game and the same share grid.

And something harder: **in a deduction puzzle you cannot hide columns.** Every visible number is part of an equation. Hiding a column on mobile doesn't simplify the view — it erases a constraint.

**Resulting rule: whatever fits on a phone IS the puzzle.** Desktop only gets more air, larger type, and side space for the reference sheet. Never the reverse.

### Width budget

Reasonable worst case: 375px minus margins ≈ **343px usable**.

The hard floor isn't typography — it's the **44px minimum touch target**. With a ~70px label column, 273px remain → **six data columns maximum**.

- Batting line (AB, R, H, RBI, BB, K) = 6 columns. **Fits, with zero margin.**
- Pitching line (IP, H, R, ER, BB, K) = 6 columns. **Fits, with zero margin.**
- **Consequence: a seventh column cannot be added.** No HBP, no 2B/3B/HR as their own columns.

### The line score doesn't fit — and that resolves an open question

Nine innings + R/H/E = 12 columns. At 44px that's 528px. Impossible.

**Solution: the line score is given complete and never erased. It is the puzzle's anchor.** Being non-editable, it needs no touch target, so it renders small and read-only — and then it fits.

The screen constraint answered the design question of which cells are never erased.

### Height budget — worse than width

iPhone SE: ~667px, minus browser chrome, minus the custom numeric keypad (250–300px). That leaves **~300–350px of visible board** against roughly 16 required rows. **Scrolling is unavoidable.**

**Critical derived rule: header and totals row stay pinned during scroll.** In a deduction puzzle the totals are consulted constantly; if they leave the screen, the player loses the ability to reason. Non-negotiable.

### Other consequences

- **No hover.** Candidates mode needs a different interaction.
- **Row and column highlighting on cell selection goes from decoration to necessity** — it's the only thing showing the player which equations that cell touches.
- "Luis Aparicio" doesn't fit in 70px. **The progressive name reveal must appear outside the label column** (below the row, or as a transient notice).

### v1 board composition — ⚠️ PROVISIONAL, pending measurement

**These numbers are unvalidated estimates and must not be treated as decided.**

- Line score for both teams + R/H/E — **complete, read-only, never erased** *(this part is decided)*
- Offense for **one team only**: rows × AB, R, H, RBI, BB, K + totals
- Pitching for the **opposing team**: rows × IP, H, R, ER, BB, K + totals
- **Footnote line: LOB, HBP, SF, SH** — given, read-only, never erased *(decided; see below)*

**What is actually decided:** six data columns maximum (derived from the width budget above), the
column sets, one team's offense against the other team's pitching, the line score as anchor, and
the footnote line.

### The footnote line — why the board needs one

**Found while starting the solver (August 2026): the column sets alone cannot express two of the
five identity families.**

- **T5 is `PA = Outs + R + LOB`.** `Outs` derives from the opposing `IP` and `R` is in the line
  score, but **LOB appears nowhere.** Without it, the most powerful rung of the ladder is not
  applicable at all.
- **The batter line is `PA = AB + BB + HBP + SF + SH`** (§8, tutorial step P2). The last three
  cannot be columns — the width budget closed that above.

**This is not a defect in the column choice.** A printed boxscore publishes exactly these values as
footnotes rather than columns: LOB, 2B, 3B, HR, SF, SH, HBP, DP. The width budget forbids a seventh
**column** because of the 44px touch target; a footnote line consumes no column width and needs no
touch target, because like the line score it is given and never erased.

It also plays in favour of §2, which says keeping the canonical boxscore format *is* part of
onboarding. A board with footnotes looks more like a real boxscore, not less.

**The alternative was measured and rejected:** restricting the pool to games where HBP, SF and SH
are all zero would cost 57% of surviving directions (85,497 instead of 195,359 at a 15-row budget).
It would have improved the era balance as a side effect — the sacrifice bunt was constant in the
dead-ball era, so requiring zero pushes the pool forward in time — but paying 57% of the pool to
avoid a line of footnotes that real boxscores print anyway is the wrong trade.

### Two corrections found by reading cwbox and checking against the database

**1. A fifth footnote quantity was missing: reaching base on defensive interference.** It is a plate
appearance that is not an at-bat and not any of the other four categories, and a boxscore missing it
still looks right — which is why it went unnoticed. Measured across every batter row Retrosheet has:

| Forward count of plate appearances | Rows that fail |
|---|---:|
| `AB + BB + HBP + SF + SH + XI` | **0** of 5,325,173 |
| `AB + BB + HBP + SF + SH` | 1,956 |

It affects 1,933 team-games, roughly one in every 200. **Decision needed:** either the footnote line
carries a fifth value that is zero in 99.5% of games, or the pool excludes those games. Excluding
costs almost nothing and keeps the footnote line shorter on a 375px board, which argues for it —
but the identity itself must know about interference either way, so that a rejection happens for
the stated reason rather than by accident.

**2. The backward count stops holding in 2020.** `PA = Outs + R + LOB` assumes every runner arrived
by way of a plate appearance. Extra innings now begin with a runner already on second who never
batted, so the identity breaks by exactly the number of extra half-innings:

| Era | Team-games that fail | Of those, in extra innings |
|---|---:|---:|
| 2020 onward | 2,304 | 2,252 |
| Before 2020 | **11** | 1 |

Eleven failures in more than 400,000 team-games before 2020 — those are source errors, and catching
them is what layer 1 is for. **Rejecting the modern extra-inning games is correct, not a false
negative:** the board genuinely cannot express that identity for them, so they are not solvable
puzzles regardless.

**⚠️ Still open: attribution granularity.** Whether HBP, SF and SH are given per team or per player.
A printed boxscore attributes them by name ("SF: Aparicio"). Per player makes the batter identity a
per-row equation, which is a T1/T2 workhorse; per team collapses it to a single team-level equation
and removes one constraint per row. **This materially changes puzzle difficulty and must be decided
before the erasure algorithm.**

**What is NOT decided:**

| Parameter | Provisional value | Status |
|---|---|---|
| Max batters in the offensive team | ≤10 | **Estimate.** Comes from "roughly 16 rows fit" — never measured against a real board |
| Max pitchers in the defensive team | ≤3 | **Estimate.** Same origin |
| % of cells erased | 25–35% | **Invented.** No basis yet |

### How these get resolved

**Two independent measurements, both required before fixing these numbers:**

1. **Height budget, measured not estimated.** Prototype the board in a browser with real data at
   375px and count how many rows actually fit above the keypad. That gives the true row ceiling,
   which sets the roster caps.

2. **Compressibility and technique distribution across the pool.** For a sample of surviving
   directions: how many cells can be erased while preserving uniqueness *and* T1–T5 derivability,
   and which techniques the result demands. **This is the measurement that decides whether a board
   this size produces hard puzzles at all.**

If most of the sample resolves with T1 and T2 only, the board is too small and the caps must be
loosened — accepting fewer rows on screen is not an option, so that would mean revisiting the
column set or the board's shape.

**If pool size ever needs loosening, the lever is the batter cap, not the pitcher cap.** Measured:
only 18.5% of directions pass ≤10 batters, while 66.9% pass ≤3 pitchers. The batter cap is what
constrains the pool, and it is also what produces the 1910–1949 era skew.

### On the relationship between board size and difficulty

Fewer rows does **not** mean an easier puzzle. Difficulty in a deduction puzzle comes from how many
equations intersect and which techniques must be chained, not from row count. A 26-row board solvable
entirely by column sums is trivial and long; a 12-row board requiring T5 and the pitching cross is
hard and short.

The effect actually runs the other way: **more rows means more equations, and more equations makes
uniqueness easier to reach** — more redundant paths to deduce each cell. That is what produces easy
puzzles.

This is an argument for measuring rather than assuming, in either direction.

### Why the board is a subset at all

A full MLB boxscore is ~26 rows, unplayable on a phone. This is the minimum shape preserving all
three constraint families, including the cross-team constraint that §3 identifies as essential.

### Design process

- **Prototype in the browser with real data, not in Figma.** Tables lie in mockups: real numbers have different widths.
- Test on small physical devices. iPhone SE is the worst case.
- **Accessibility from the start:** correct table semantics so a screen reader announces "row Aparicio, column hits". Retrofitting this means rebuilding the board.
- Consider outside design help at this point. It's where a purchased hour returns the most.

---

## 7. Game identity — progressive reveal

**Decision: progressive reveal.**

- Rows start labeled with **positions** (C, 1B, 2B, SS, LF...), not names. It's authentic baseball grammar and identifies nothing.
- **On completing and validating a row, that player's name appears.**
- Teams, date, and context are revealed at the end.

**Rationale:** with a baseball-fan audience, names are not decoration — they're the emotional payload of a boxscore. A boxscore without names is a spreadsheet. Progressive reveal turns the tension into mechanics: the mystery holds at the start, which is when a Google search would still help, and names arrive as reward. A name you earned weighs more than one handed to you.

**Note on cheating:** the risk of players looking up the game is overrated. The solution already lives in the client JSON and that's accepted. A daily puzzle is only cheated against oneself. Wordle had the answer one click away and nothing happened.

### Consequences

- **Forces row-level validation.** Constrains the open error-handling question.
- **The name appearing _is_ feedback.** The game stops being silent. This is welcome: it softens the experience exactly where the "fan without puzzle patience" risk lives.
- **Free visual progress.** Nine names appearing one by one is a progress bar nobody had to design.
- **⚠️ The final reveal loses its surprise.** With nine names visible the player already knows the game. The closing must deliver something else: date, teams, ballpark, and **why that game mattered**.
- Position labels depend on era. The pool skews to 1950–1985, much of it pre-DH. The pitcher batting ninth is a strong era tell.
- The share grid cannot contain names.
- Reserve width in the label column: "SS" and "Luis Aparicio" don't occupy the same space.

---

## 8. Tutorial

**Not a modal.** The first games *are* the tutorial. Each introduces a single identity:

1. **P1** — Column sum. One missing cell with the total given. Impossible to fail.
2. **P2** — The batter line: PA = AB + BB + HBP + SF + SH
3. **P3** — The batting↔pitching cross. **The game's "aha" moment.** Stage it deliberately.
4. **P4** — Inequalities and non-negativity to eliminate candidates.
5. **P5** — The global identity PA = Outs + R + LOB. The most powerful and least intuitive.

### Scope: the mechanics, not baseball

- **Does explain:** that totals rule, that the batter line balances, that opposing pitching crosses with the offense, that PA = Outs + R + LOB
- **Does not explain:** what AB means, what an RBI is, why there are nine innings

**The tutorial teaches identities, not statistics.** A hardcore fan knows what LOB is and has never once thought that PA = Outs + R + LOB.

### Mandatory on first play

**The tutorial is not skippable on the first game.** It's short, and it's the only guarantee that nobody reaches the real puzzle without understanding the mechanics. Permanent access to replay it, alongside the reference sheet.

### Policy for players who don't know baseball

**Not served, but not shut out either.**

No baseball tutorial, no stats glossary, no simplified mode — all of that would dilute the canonical board that §2 decided to preserve.

But the reference sheet serves them anyway and position labels are learnable. Someone curious can come in and stay. **They're simply not designed for, and failing to capture them isn't measured as failure.**

**Permanent collapsible reference sheet** with the five identity families. Sudoku doesn't need one because there's a single rule; here there are five and the casual player forgets them between sessions. Not optional.

---

## 9. Platform

**Website (PWA), not a native app.**

- The growth mechanism of a daily puzzle is the **shared link**. An app inserts an app-store page into that flow and loses half the people.
- Maintenance cost: two stores and two review cycles are a new front for a solo operator.
- The content demands nothing native: it's a grid of numbers.
- Iterating the generator on the web means deploying; in a store it means waiting for review.
- **PWA** recovers what matters: installable, offline, daily notification.

**Critical mobile care:** custom on-screen numeric keypad, never the system keyboard.

**Accepted consequences:**

- Cache only the day's puzzle, not the week, to avoid leaking future puzzles.
- The solution lives in the client and will be visible in devtools. Accepted — the streak is against yourself.

### Native app for the paid tier — rejected

**Question evaluated:** a mobile app for paying users and web only for free users?

**No.** Four reasons:

1. **It puts an app store at the only point where money enters.** Apple takes a cut of in-app subscriptions; added to the merchant of record, a considerable slice is lost. Rules about linking to external payment change every year.
2. **It inverts the commitment ladder.** The path would become: free game on web → pay → *now install an app and start over*. That's asking for friction right after someone paid — the worst possible moment.
3. **It doubles the product surface.** Two codebases, two deployment cycles. For a solo operator, the worst return on the list.
4. **It breaks seams C4, C5, and C6**, which exist so the same engine serves every context.

**The underlying intuition was right** — paying users should feel they get something better. But that's delivered through the product (no ads, archive, stats, streak insurance), not a different platform. The PWA already provides install, offline, and daily notification.

The only thing a native app would add is store visibility as a discovery channel — and that would serve to acquire **free** users, the opposite of what was proposed.

If there's ever an app, it should be for everyone and only after the site works.

---

## 10. Monetization

### Principle

The base design must support **all** paths without rebuilding the site. Not implementing them all in v1, but closing off none.

### Data license

Retrosheet explicitly permits commercial use, with one requirement: the copyright notice must appear prominently. It goes in the footer.

### Reference model: crossword and sudoku sites

**Decision: copy the NYT Games playbook and equivalents.** Three pillars:

1. **One free daily game, forever.** Habit and acquisition engine. Never touched.
2. **The archive behind the wall.** The number-one conversion driver — at the NYT what you buy is the full crossword and the 10,000+ puzzle archive, not "more puzzles per day."
3. **No ads for paying users.** The free tier is monetized with advertising; removing it is part of what the subscription sells.

**Consequence:** ads return to the plan, and logically so — they're the complement to the wall, not the primary model. This reactivates seam C9.

### Chosen model: recurring subscription

**Recurring subscription**, not one-time purchase.

Rationale (from the operator): a one-time purchase is a perpetual obligation to maintain the site. A subscription bounds the commitment — on shutdown, renewals stop, the unused portion is refunded, and nothing is owed to anyone.

**Consequence:** what's sold isn't "the archive" (a static asset that gets exhausted), it's a **membership** — unlimited play, catalog, stats, packs. The product does deliver continuously: a new puzzle every day.

Structure:

- Monthly and annual, annual discounted
- **No lifetime tier** — it reintroduces the problem being avoided
- Cancel anytime; on cancellation the free daily puzzle continues
- Terms: access while the service operates

### Two tiers from day 0

**Firm operator decision.** The site launches with both levels:

- **Free:** one daily puzzle
- **Paid:** archive, stats, packs, no ads, unlimited play

**Rationale:** converting a free site into a paid one burns trust, and the base attracted while free self-selected for free. Launching with the price in place means everyone who arrives knows the rules from day one.

**Warning on "all you can eat" as the sole argument:** the value of a daily game is in the ritual and in everyone solving the same puzzle today, not in quantity. People don't want more puzzles, they want *the* puzzle. The paid tier needs: archive, personal stats, **streak insurance** (one grace day a month — the strongest hook that exists in daily games), themed packs. Unlimited works well as part of the bundle, poorly as the sole argument.

**Rare advantage to exploit:** the NYT archive took thirty years to exist. Here it's possible to **launch with an archive** — hundreds or thousands of verified puzzles from day one, because Retrosheet already has them and the generator produces them in batch. The asset that in this category is a longevity prize is available before opening.

### Merchant of record

**Paddle or Lemon Squeezy** rather than raw Stripe. What it covers beyond payment — they become the **legal seller of record**, the customer buys from them:

- **Global tax:** they collect and remit sales tax and VAT across 200+ jurisdictions. Avoids VAT registration in Europe and tracking state thresholds in the US.
- Payment processing (cards, PayPal, Apple/Google Pay, local methods)
- Subscription management: recurrence, plan changes, proration, cancellation
- **Failed payment recovery** — retries and expired-card updates. Involuntary churn is a large share of total churn
- **Fraud and chargebacks** — they assume legal liability for transactions
- Hosted checkout with per-country currency and translation
- Automatic invoices and receipts
- **Customer billing support** — they handle payment inquiries directly
- PCI compliance and 3D Secure

**That second-to-last point is decisive:** most tickets in a subscription business are billing, not product. Delegating them is what makes solo support manageable.

**Cost:** Paddle and Lemon Squeezy both charge 5% + $0.50 per transaction, against ~2.9% + 30¢ for raw Stripe. Two points more for everything above.

**Tentative preference: Paddle.** Lemon Squeezy adds 1.5% on international payments while Paddle includes everything in its rate — relevant when selling to the Dominican Republic, Venezuela, and Spain. Also, Lemon Squeezy was acquired by Stripe in 2024 and its direction now depends on that strategy. *Verify pricing and features when deciding.*

### Operational consequences of charging from day 0

- There are paying customers on day 1 with an untested generator. An unsolvable puzzle in week 2 is no longer a bug — it's a refund.
- **Pre-validation of arithmetic and the pre-generated puzzle bank stop being maintenance and become launch requirements.**
- Pre-launch checklist: merchant of record configured, terms, privacy policy, refund policy.
- Consider a **founder price** locked for the first subscribers: it compensates the risk they take and builds a committed core.

### Other paths (priority order)

1. **Sponsorship / B2B** — embeddable widget for newsletters and media. Doesn't depend on volume.
2. **Themed packs** — the database is a real competitive advantage
3. **PDF / print books** — set aside for now at the operator's request

---

## 11. Accounts and abuse

- **Social login only:** Google + Apple + email magic link. **No Facebook** (declining usage, more review process, marginal coverage).
- No own passwords: zero storage, zero recovery flows, zero breach liability.

### Sharing policy

**Personal and household use**, stated explicitly in the terms.

Rationale: it's what will happen anyway; writing it down aligns the rule with reality, removes guilt from paying customers, and leaves room to treat extreme cases as abuse without having criminalized a family.

**Also, sharing with a family member produces customers.** Stats and streaks are personal; shared, they mean nothing. Whoever gets hooked ends up wanting their own account.

### Mechanism

- 8–10 devices per account, **silent eviction of the oldest**
- No accusations, no blocks, no manual review, no fraud detection, no geographic analysis
- Self-enforcing: a family never notices; an account shared among thirty people becomes useless on its own
- Identifier: random UUID at first login, **not browser fingerprinting**
- **In v1:** only record the device. The limit stays off by configuration.

**Guiding principle:** wrongly blocking someone who pays costs more than the fraud avoided.

---

## 12. Architectural seams

These must exist in v1 even if no paid feature is used.

| # | Seam | Enables |
|---|------|---------|
| C1 | Three sealed layers: generator → data → client. Zero puzzle logic in the client | Books, embed |
| C2 | Puzzle = pure data with immutable ID and versioned schema | Everything else |
| C3 | Rich metadata on every puzzle even if unused (year, teams, flags, difficulty, techniques) | Themed packs |
| C4 | The engine doesn't know what day it is; a *loader* decides | Unlimited mode, archive |
| C5 | Engine with no chrome or branding, themeable via CSS variables | B2B licensing |
| C6 | Per-puzzle routes from day one: `/p/<id>` canonical, `/today` redirect | Archive, sharing |
| C7 | **Store events, not state** (puzzle_id, duration, hints, techniques, errors) | Stats, calibration, migration to accounts |
| C8 | `canAccess(puzzle, user)` — in v1 always returns true | Any gating |
| C9 | Reserved, empty layout slots | Ads without wrecking mobile |
| C10 | Two-phase boot that can wait for consent | Privacy |
| C11 | Zero strings in code, including generated text and metadata | Optional Spanish (§13) |

**C7 is the irreversible one.** If v1 only stores "streak: 7", that history is never recoverable.

**Note on C8 and subscription:** a signed token with expiry validates offline, which makes it copyable. Device control requires a short token (24h) refreshed against an endpoint. That refresh call is where devices are counted. Still nearly static — a single endpoint.

---

## 13. Language

**Interface: English. Spanish is a nice-to-have, not a must-have.**

The target market is the United States. Spanish adds convenience for Latin American baseball fans —
who can play because they read a boxscore the same way — but it is not required for launch and can
slip without affecting the product.

**What stays mandatory regardless: seam C11 — zero user-facing strings in code.** All copy goes
through the string catalog from day one, including generated reveal text and metadata. That costs
almost nothing to do now and is expensive to retrofit, so the option stays open even if Spanish never
ships.

**Project convention:** all documents, code, and source comments in **English**. Discussion happens
in Spanish; artifacts are in English.

---

## 14. Competitive landscape

**Nobody is doing exactly this.** The adjacent space is populated:

| Product | What it is | Relationship |
|---------|-----------|--------------|
| **Immaculate Grid** (Sports Reference) | Daily baseball trivia | **The real incumbent.** Owns the fan's daily habit. Knowledge, not deduction. |
| **Daily Walkoff** | Daily MLB trivia, 30 puzzles | Same genre as Immaculate Grid |
| **Baseball Sudoku** (ESPN, books, baseballsudoku.com) | Sudoku with positions instead of numbers | Cosmetic skin, zero baseball logic. **Name collision risk.** |
| **TripleLog Baseball Sudoku** | Sudoku where cells are at-bat outcomes and you must score the correct runs per inning | Closest conceptually. Integrates real baseball logic, but over constructed puzzles, not real games. |

**The gap:** none uses a **real historical boxscore** as substrate, nor arithmetic deduction as the mechanic. That space is open.

**The threat:** not that someone copies the idea, but that Immaculate Grid already owns the mental space of "the daily baseball game."

---

## 15. Risks of success

Scenario: 9,000 paying users within 3 months.

1. **Support volume.** The most underestimated cost. Thousands of paying customers generate hundreds of tickets a month for one person. Mitigation: self-serve cancellation, aggressive FAQ, zero manual account fixes.
2. **Daily delivery stops being a promise and becomes a contract.** A day without a puzzle is an incident. Mitigation: pre-generated batch months ahead, automated publishing.
3. **A defective puzzle hits everyone the same day.** Requires an emergency switch and rollback.
4. **Obligation and burnout.** With people paying, walking away isn't an option. Hence the subscription and the orderly-shutdown clause.
5. **Tax and administration.** Delegated to the merchant of record.

### Price — pending

The figures used in conversation ($1.99/month, $9.99/year) **were examples, not proposals.** Real pricing is a later discussion.

It depends on three still-open items: how many puzzles the archive has at launch, whether the free tier carries ads, and exactly what's in the membership.

**The only thing fixed now, because it's structural and doesn't change with the number:** annual should equal **~10 months** of monthly. Enough to push annual without giving away half the revenue.

**Category reference:** NYT Games costs $39.99/year.

---

## 16. Protecting the idea

**Game mechanics are not protectable.** Rules and ideas are explicitly outside copyright. Only concrete expression is protected: code, visual design, name.

**Worth doing:**

- Register the name as a trademark
- **Don't publish the generator algorithm.** It's a trade secret and the genuinely hard piece to replicate — above all the T1–T5 human-solvability guarantee.

**The real defenses:**

1. **Habit and streak.** Enormously sticky. Nobody abandons a 200-day streak to move to a clone.
2. **The generator with its derivability guarantee.** Hard to replicate.
3. **The Retrosheet pipeline and database.** Years of accumulated work.
4. **Being first with that audience.**

**Precedent:** Wordle was cloned within days and still won. First-mover plus habit beat the copies.

**Registered caveat:** with AI, the implementation barrier is low — which also means secrecy protects less than it seems, since whoever sees the site in February can also copy it quickly. What AI does not shorten: historical data quality and validation, design judgment, and above all the audience.

---

## 17. Legal structure

**LLC formed before public launch**, not before design.

Since the site launches charging from day 0, the trigger coincides with launch. The moments that require it:

- Before charging the first person
- Before registering the trademark (registering personally means an assignment later)
- Before opening the separate bank account

**An LLC only protects if real separation is maintained.** Collecting into a personal account and paying expenses with a personal card makes the shield decorative — that's what allows piercing the veil of a single-member LLC.

**Notes:**

- BOI reporting: LLCs formed in any US state are exempt from the federal requirement. The law wasn't repealed, only suspended by rule — verify current status when forming.
- A single-member LLC is a pass-through by default; it changes nothing tax-wise at the start. S-corp election only enters the conversation with substantial net profit, and with an accountant.
- *None of this is legal or tax advice. Confirm with a professional.*

---

## 18. Daily operational load

**The game is almost no work. The subscribers are.**

**What is NOT a load:** publishing the puzzle. With months pre-generated and verified, it's an automated process. Zero minutes a day. A huge advantage over a crossword site, which depends on human constructors and editors — here the content comes from a database.

**What IS a load: support**, and nothing is close to second. With thousands of subscribers, daily emails arrive: login won't work, I was charged twice, I want a refund, I lost my streak, I changed phones, this puzzle is broken. Mostly account and billing problems, not the game. **Realistic range: 30 minutes to 2 hours daily, with spikes when something breaks.**

**By frequency:**

- **Daily:** verify the puzzle shipped and nothing is down
- **Weekly:** metrics, community responses
- **Monthly:** reconcile payments, review the pool, bookkeeping
- **Annual:** LLC report, taxes, renewals

**The psychological load nobody mentions:** it's a *daily* game. There is no weekend or vacation without a puzzle. Even automated, the operator is the only one who can fix it. People who run daily games solo describe that as the most exhausting part — not the hours, but never being able to disconnect.

**How it's reduced — designed now, not later:**

- **Self-serve** cancellation and account management. Every action requiring manual intervention multiplies by thousands
- Merchant of record, absorbing most billing tickets
- Aggressive FAQ and **a single contact channel**, not five
- **Automatic, no-questions refunds** below a certain amount: arguing costs more than refunding
- Publishing months ahead, so a failure gives days of margin rather than hours
- Automated alerts instead of manual checking

With that discipline: **1–2 hours daily in steady state.** Without it, it becomes a full-time job.

---

## 19. Timeline and launch

**Chosen window: Spring Training 2027.**

Advantage: 4–6 weeks of shakedown **before** Opening Day, which is the real attention peak. Launch in February with few people watching, fix what breaks, and arrive at late March working. Launching directly on Opening Day would mean maximum traffic against an untested product.

**Working backward:**

| Period | Focus |
|--------|-------|
| Aug–Sep 2026 | Close design; start building audience |
| Oct 2026 | Playoffs — second attention peak of the year |
| Oct–Dec 2026 | Construction |
| Jan 2027 | Closed beta (friends and family, controlled environment) |
| Feb 2027 | Spring Training launch |
| Late March 2027 | Opening Day — the moment of truth |

**If something falls out of scope, let it be the billing infrastructure before the game.**

---

## 20. Audience strategy

**Decision: no free puzzles posted on social media before launch.** The project ships complete or not at all.

Operator's rationale: fear that someone takes the idea and implements it faster, and not wanting to burn the single first impression available in a small niche.

**What is done starting now:** build audience **without showing the game.** The baseball history content the operator already writes leaks nothing about the product and attracts baseball fans. Mailing list and consistent presence through February.

**Launch channels (by weight):**

1. **The product is the main channel** — the share grid. Every solved game is a potential post aimed at people who already read boxscores. **This makes grid design a growth decision, not an aesthetic one.**
2. **Baseball newsletters** — probably the best external channel, and it overlaps with the B2B embeddable-widget path
3. **Communities:** r/baseball, r/Sabermetrics, SABR, Discord. SABR fits the operator's profile particularly well
4. **The archive is SEO** — every archived puzzle is an indexable page about a real game. Thousands of long-tail pages no other puzzle game has
5. **The baseball calendar** — Opening Day, playoffs, World Series

**Market note:** the target market is the United States. Latin American baseball fans can use the
product because they read a boxscore the same way — hence optional Spanish — but Latin America
is **not a target market**. Treating it as one would require detailed design review, not an
extension.

**Warnings:**

- A thousand users who try is easy. **A thousand who return on day 30 is the real problem**, and that's solved by the game, not by distribution.
- Charging from day 0 dampens sharing. **The free tier must be a complete, satisfying game on its own**, or the growth channel is choked off.
- For the closed beta to be useful: don't ask whether they like it. **Measure whether they return on day seven without a reminder.** Recruit baseball people with no personal attachment (SABR) before family.

---

## 21. Batch generation and calendar

### Generation

**A single offline run producing thousands of puzzles.** The generator runs offline against Retrosheet and publishes the batch as static files.

**Double idempotence — two distinct things that must not be conflated:**

1. **Puzzle idempotence** — the same Retrosheet game always produces the same puzzle with the same ID. Regenerating the batch creates no duplicates.
2. **Calendar idempotence** — the date → puzzle assignment is fixed and never recomputed. Running the process again reassigns nothing.

**The puzzle ID derives from the game, never from the date.** If it derived from the date, the same puzzle in the archive and in the daily calendar would be two distinct entities, breaking the no-repetition promise.

The process that extends the calendar must be able to run twice with no effect, because sooner or later it will be run twice by mistake.

**Interaction with the difficulty curve (§31):** calendar assignment isn't only "don't repeat." The generator must **classify each puzzle by level and shape the week** — easy Monday, hard Saturday. The calendar is built once respecting that pattern, then it's immutable.

### The calendar, not local consumption

**Rejected:** each device "burning" games from a local list.

Rationale: it breaks the daily game. Each user would end up on a different puzzle, losing what sustains the model — that **everyone solves the same puzzle today**. Without that there's no conversation, no result comparison, and the share grid means nothing. Also, someone playing on phone and laptop would be on different puzzles.

**Solution, still requiring no backend:** which puzzle corresponds to each date is fixed in advance. The client computes today's date and requests that static file from the CDN. Zero front-back interaction to play, same puzzle for everyone.

No-repetition is resolved at batch generation, not at runtime.

**Purely local consumption does apply to the archive** — there's no reason for a shared puzzle, each person plays what they want, and no backend is involved at all.

### Calendar rule: extend, never rewrite

Once someone has played a date's puzzle, that date cannot change — streaks, shared results, and stats hang from it. **The past calendar is history, not configuration.**

Case of a defective puzzle detected late:

- **If the date hasn't arrived:** it can be replaced. That stretch is future and nothing hangs from it.
- **If the date has passed:** don't touch it. Mark it void and exclude it from streaks and stats, but leave the assignment.

The calendar "freeze" date is a real parameter: what's published through today is immutable; what comes after is editable.

---

## 22. Correctness guarantee — design principle

**An incorrect puzzle must be virtually impossible. This is where all the effort goes.**

With customers paying from day 0, a broken puzzle isn't a bug: it's a refund and a lost streak that can't be given back.

### "Incorrect" is not one thing

| Failure type | Description |
|---|---|
| **Bad data** | The historical boxscore doesn't balance at source |
| **No solution** | Constraints contradict each other |
| **Multiple solutions** | Cells were erased that weren't forced |
| **Unique but not derivable** | **The worst.** Looks correct and the player is trapped guessing |

The last one demands the real work, and is covered by the T1–T5 no-backtracking rule (§4).

### Independent layers, each able to reject on its own

1. Validate the boxscore against all identities before admitting it to the pool
2. Prove solution uniqueness
3. Require the human-technique solver to finish without guessing
4. **End-to-end verification:** take the published puzzle, solve it from scratch, and compare against the original boxscore. If it doesn't match exactly, discard.

**Critical requirement: each layer is implemented separately and shares no code with the generator.** If the verifier reuses the generator's functions, it inherits its bugs and the validation is theater.

### Operating rules

- **Nothing publishes without passing all layers.**
- **A puzzle that fails is discarded silently — never "fixed."** With thousands of candidates, throwing away 30% costs nothing.
- **Sign every published puzzle** and verify the signature before serving, to catch post-generation corruption.
- **Have an escape hatch:** a pre-verified backup puzzle and a switch to substitute the day's. "Virtually impossible" is not "impossible," and with 30,000 people playing you find out fast.

### The layer no automated test replaces

**Solve a sample by hand.** Fifty puzzles before launch. That's where what no test detects shows up: correct but boring, or brutally hard.

---

## 23. Infrastructure

Scenario: 9,000 registered accounts, 30,000 daily unique players, 99.9% availability target.

### The load is smaller than the numbers suggest

Daily-game traffic concentrates at the puzzle rollover and in the morning. Even assuming a third within the same hour, that's a few requests per second with peaks of dozens in the peak minute.

**And above all it's static traffic.** The day's puzzle is the same file for everyone: kilobytes from a CDN edge with near-total cache hit rate.

The dynamic part is small — token refresh, device registration, event sync. With 9,000 accounts that's tens of thousands of operations a day.

### Three nines: 43 minutes of downtime a month

**Availability isn't bought with bigger servers — it's achieved by having fewer pieces.** Chaining CDN + backend + database as mandatory dependencies multiplies their availabilities and lands *below* the target even if each is good.

**Way out: define "up" as the puzzle being playable.**

And it's possible because it's already designed that way: the puzzle is static, validation is client-side, and C7 stores events locally. **If the backend goes down, you can't log in or sync stats, but the day's game still works.** It's the only realistic way to sustain three nines solo.

### From where the real outages come

- **Your own deployments.** Most outages are self-inflicted. Don't deploy near the puzzle rollover; have instant rollback.
- **The daily rollover** — the only moment something must fire on time. Publish ahead; don't generate at midnight.
- **Third parties** — a Google OAuth or Paddle outage is inherited.
- **Expired certificates and domains.** Silly, and among the most common causes of total outage.

**The system must degrade on its own, not wait for human reaction.** If something breaks at 3am, the month's budget is spent.

*Note: §33 chose Docker + nginx on a VPS rather than serverless. That satisfies the underlying argument — fewer chained pieces — but it does mean there is a server to patch. Revisit this section at level 200.*

---

## 24. Brand and domain

**Primary domain: `boxscorepuzzle.com`**

**Name language: English, no concessions.** The audience will come overwhelmingly from the US, and baseball vocabulary is already English throughout the Caribbean. Any Spanish applies to the **interface**, not the name.

### Advantages and limitation of the chosen name

**In favor:** describes the product unambiguously, helps in search, no legal risk, works equally for the Caribbean audience.

**⚠️ Limitation:** it's descriptive, which makes it **hard to register as a trademark on its own** — purely descriptive marks aren't protected because nobody can appropriate the words naming a category.

Not a problem today, but for §34: trademark protection will likely come from a **distinctive logo or a secondary name**, not the two words alone. And for that same reason it doesn't block the umbrella of §30 — you can have the descriptive domain and a separate mark when needed.

### Registered domains ✅

- **`boxscorepuzzle.com`** — canonical
- `boxscorepuzzles.com` — defensive, redirects
- `boxscorepuzzle.app` — for an eventual wrapped PWA, redirects

**Canonical policy:** one indexable version, `boxscorepuzzle.com`. The other two redirect. If search engines see the same content at three addresses, ranking is diluted — which is precisely the advantage of having chosen a descriptive name.

**Operations:** auto-renewal and privacy protection enabled on all three ✅. An expired domain is among the most common causes of total outage (§23).

### Rejected for unavailability

Scorekeeper · Left on Base · Ghost Game · The Daily Box · Crack the Box · Boxly · Scorely

**Lesson:** short combinations of common English words have been taken for years, mostly by resellers. The `-ly` suffix is swept clean from the startup era. That path is exhausted.

### Criteria used

1. Don't say "sudoku" — there are registered marks associated with the term, baseballsudoku.com exists, and the game is kakuro anyway. The analogy belongs in the **copy**, not the name.
2. Don't box into a single game (§30)
3. Pronounceable and spellable on hearing
4. One or two words

### Pending, not urgent

- [ ] Consider a **short separate brand name**, registrable, providing the asset the descriptive name cannot. `boxscorepuzzle.com` would keep working for search.

---

## 25. Seasonality

**The puzzle ships all 365 days, without exception.** Interrupting the daily would be suicidal: the streak sustains the habit, and a pause breaks it for everyone at once.

**But the puzzle doesn't stop and attention does.** Baseball has a winter; from November to February attention to the sport collapses regardless. The question isn't whether to publish, but what to expect of those months.

**Annual is the defense.** Someone who subscribed in April keeps paying in December whether they play or not. A strong argument for pushing annual beyond the discount: **winter is exactly when monthly subscriptions get cancelled.**

**Winter is the construction window.** November to February: nobody's watching, traffic is at the floor, and things can be changed without exposure. It matches the project's real cycle.

**Two zero-cost uses:**

- **Baseball winter moments** — Hall of Fame, awards, free-agent signings. And for the Caribbean audience, **winter leagues are in full season while MLB sleeps.** Hooks for content, not for the product.
- **Seasonality as a metric** — the retention curve will drop in winter for reasons unrelated to the game. Know it in advance so the calendar isn't mistaken for a product problem.

---

## 26. Time, competition, and the social layer

**Principle: don't split the experience by tier, split the analysis.** Everyone plays the same; paying users see more about how they played.

### Rejected: competitive mode only for subscribers

- **A leaderboard needs population.** With typical 2–5% conversion, a subscriber-only board is thin precisely where it needs density. It would mean charging for the worse version of the feature.
- It's backwards: the daily puzzle is the same for everyone, so that's exactly where comparison makes sense with everybody in.
- **Timing changes how you play, not only what you see at the end.** If the clock runs, you rush; if not, you savor. It can't be one contemplative experience for some and competitive for others.

### Decision: measure for everyone, compare as a paid feature

- **Timer for everyone, silently.** C7 already stores duration, so it's free. Your own time is shown discreetly, not as the headline.
- **The paid feature isn't "a subscriber leaderboard," it's personal stats with a percentile against the whole user base:** times over time, highest technique level, relative position among everyone who played today.

**The key property: that feature improves as the free tier grows**, rather than degrading. That's the correct incentive.

### On a public global leaderboard — two warnings

- **The solution lives in the client and so does the timer.** A public ranking is trivially manipulable, and verifying server-side fights the static architecture (§23) and the three nines. High cost for the most fragile feature.
- In daily games these rankings are always won by the same few speedrunners, which demotivates everyone else. **Wordle has none and grew more than anyone.**

### Social competition: among friends, not global

Small private groups. No incentive to cheat because it's social, it fits the share grid, and it works as a paid feature without needing mass population.

*Note: private friend groups are the one feature that genuinely requires a real backend — comparing between people can't be done with static files.*

---

## 27. Failure and retention

**Decision: you can never lose.**

### Why

In a unique-solution, pure-deduction puzzle, losing is artificial — it would have to be invented with an error limit or a clock. And that punishes exactly the profile identified as fragile in §2: the baseball fan who isn't a puzzle person. It would put a barrier in front of the very user who needs protecting.

### Design

- The puzzle stays **open all day**
- It saves itself
- At midnight it **closes for streak purposes, but doesn't disappear** — it can be finished later from the archive
- Failure isn't "you lost," it's "you missed the day"

Generates urgency without punishment.

### The return hook

The usual mechanisms — streak, notification, rising difficulty — work and must exist. But they're the same ones everyone has, and none is a reason to choose this game.

**Note:** the reveal was originally framed as the differentiating hook ("no sudoku can tell you that you just reconstructed a game from August 1974"). With §29 deciding it will be an automatic template card with no manual writing, **the weight of retention returns to habit and puzzle quality.** The disproportionate effort goes to the generator and the difficulty curve.

### Warning about streaks

They're effective, but they have a known effect: **when someone breaks a long streak, many never play again.** Guilt expels.

That's why streak insurance isn't only a paid feature — it's **protection against your own mechanism**. There must also be **a free grace day**, even if only one per month.

**Principle:** a game people return to out of enjoyment retains better than one they return to out of fear of losing something.

---

## 28. Community

**Decision: no comments or forums on the site. Not in v1.**

### Reasons

- **The cost isn't building it, it's moderating it.** An unwatched comment space degrades, and with thousands of users it adds directly to the daily support hours §18 identifies as the biggest load.
- **It conflicts with the anti-goals** (§1): this is not a baseball social network.
- **Comments on a daily puzzle are a spoiler machine.** Someone posts an answer and ruins the day for latecomers.

### The alternative, at no cost

**Community lives outside.** The share grid pushes conversation to social media, Reddit, and WhatsApp groups, which is where the audience already is. Traffic is retained without taking on moderation.

### If community is wanted later

A dedicated Discord channel, **separate from the site**, with volunteer moderators drawn from the player base.

---

## 29. Site content

**Decision: system-generated content yes. Blog with a publishing commitment, no.**

Rationale: a blog with a calendar is a recurring obligation on top of the daily one, competing with the time the product needs.

### What the system generates on its own

**Every archived puzzle is a page about a real game.** Thousands of indexable pages no other puzzle game can have. The system generates the content, not the operator.

### The reveal card

**Decision: template-generated card, no manual improvement.**

Content, all by database query:

- How the game unfolded per the line score
- Who had the best batting line
- Winner and loser
- Statistical oddities: many strikeouts, late comeback, complete game

**Two things that make it pay off far more than it sounds:**

- **Comparative data** — that it was the only time that pitcher struck out thirteen, that the team was on a nine-game losing streak. It's a query, not writing, and it gives a flavor a generic summary can't. **Almost nobody else has that database.**
- **Link to Baseball Reference** for the game. One line of code: the fan who wants depth goes there on their own. Delegates narrative to whoever already has it.

### Consequence for retention — important

**If the reveal is a card, it stops being the retention hook** §27 assigned it. A card is a pleasant closing, not a reason to return.

**The weight of retention returns to habit, streak, and above all puzzle quality.** The disproportionate effort goes to the **generator and the difficulty curve**, not the text.

*Reason for the decision: with a perpetual daily puzzle, committing to write by hand every day is exactly the kind of recurring obligation the project decided to avoid. Consistency with that principle is worth more than better text.*

### Existing owned content

The operator already writes about baseball history on another site. **That content stays where it is and links to the game.** No duplicated effort, nothing to migrate.

### Recorded, not adopted

It was assessed that the real narrative interest isn't in the game but in **the players** — every boxscore has nine names and almost always one with a story. It would fit progressive reveal and the audience well. Set aside because it would require manual writing.

---

## 30. Game or platform — the growth axis

**Decision: the umbrella is "deduction on real baseball data," not "baseball puzzles."**

It isn't decided now that there will be a platform, but **the name is chosen and the seams left as if there could be.** It's a free option: an umbrella name obligates nothing, while an overly literal name closes the door.

### What's in and what's out

**In — natural growth that reuses the machinery:** deduction on season lines, on standings, on player careers. Same generator, same pipeline, same promise.

**Out — trivia and crosswords.**

- **Trivia uses a different faculty.** One recalls, the other reasons. It's the anti-goal approved in §1, and Immaculate Grid already owns that space and does it well.
- **None of what's built transfers.** The generator, the uniqueness proof, the T1–T5 solver, and layered validation serve deduction games and are worthless for trivia. It would be starting from zero.
- **Crosswords are built by humans** and don't come from the data.

**The real risk isn't failing at trivia, it's the umbrella ceasing to mean anything.** With "baseball puzzles" you compete head-on with the incumbent. With "deduction on real baseball data" there's nobody.

### Consequences

- **On seams:** C4 and C5 already separate engine from site. A platform would additionally need the shell to host several games and accounts/subscription not tied to one.
- **Note:** if this works, the second game is the cheapest growth available — audience, billing, and data will already exist; only the mechanic is missing.

---

## 31. Novelty and the difficulty curve

### The genre doesn't depend on novelty, it depends on ritual

Crosswords and sudokus have gone decades without exhausting themselves. Nobody does today's sudoku expecting something new — they do it because it's what they do with coffee. **Repetition isn't a defect of the product, it is the product.**

What they provide is **variation within a constant form**: difficulty changes, the solution path changes, the player changes.

### Decision: difficulty tied to the day of the week

**Easy Monday, hard Saturday**, crossword-style. The T1–T5 ladder (§4) already classifies each puzzle, so the calendar can be built to give the week a shape. **It's free and worth more than any feature that could be added.**

### Rejected: random daily difficulty

- **It removes the player's ability to plan.** Someone who knows Monday is five minutes and Saturday is forty can do it at breakfast on weekdays and save the weekend. Without anticipation, the day a hard one lands with ten free minutes, it gets abandoned — **and that abandonment breaks the streak**, which is the retention mechanism.
- **The weekly pattern *is* part of the ritual.** Saturday being hard gives Saturday character. Random is noise, and noise doesn't become habit.
- **It makes progression invisible.** A player can't feel improvement without a stable reference.
- **First-week risk.** With baseball fans who aren't necessarily puzzle people, the first week decides whether they stay. The calendar guarantees their first Monday is gentle; random could hand them a brutal Saturday on day one.

### Yes: randomness *within* the level

Every Tuesday at medium difficulty, but **each Tuesday demanding different techniques** — one opens via the pitching cross, another via the global identity. Predictable in effort, unpredictable in path.

It's what crosswords do: Saturday is always hard, but never the same kind of hard.

### Format's own advantage

**The data does vary.** A sudoku is always the same nine digits. Here there are different eras, one-run games and twenty-run games, shutouts and blowouts, names appearing. Every board has its own texture even though the rules don't change — more variety than the genre has.

### Warning about what does NOT help

**Adding features.** Daily games that age badly are the ones that answer boredom with achievements, coins, and events. That doesn't fix a weak puzzle, it only disguises it.

**What decides whether it lasts five years:** that the puzzle is well made, that difficulty is honest, that there's never guessing, and that it ships every day without failing.

**The defense against novelty decay isn't a feature. It's the generator.**

---

## 32. Data sources

### Primary source: Retrosheet

Confirmed. Event files in SQL Server, already in the operator's possession. Commercial use permitted with the prominent copyright notice (see §10 and the notice at the end of this document).

### Generation tool: cwbox (Chadwick tools)

`https://github.com/chadwickbureau/chadwick`

**This is the pipeline's input engine.** `cwbox` is a boxscore generator, part of the command-line tools for extracting information from Retrosheet event files, alongside `cwevent`, `cwgame`, `cwsub`, and `cwdaily`.

**Why it fits:**

- **It derives the boxscore from the events**, so totals balance by construction — it inherits no transcription errors.
- Starting from play-by-play, it carries what a newspaper boxscore lacks: **RBI, BB, and K per batter, LOB, and complete pitching lines**. Resolves the board's column problem (§6).
- The operator already has experience with these tools.

**License:** Chadwick is GPL. No impact on the project — running a command-line tool doesn't contaminate the output. It would only matter if its source were incorporated.

### ⚠️ Pool criterion: the three source file types are not equivalent

Retrosheet publishes the material in three forms, and **they must be distinguished when building the pool**:

| Type | Reliability |
|---|---|
| **Boxscore files** | Reflect **official totals**. Most reliable. |
| **Event files** | Reflect the limitations of known play-by-play sources for that game. |
| **Deduced event files** | **Reconstructions** from partial information and context, not complete accounts. |

**Games from deduced event files must be excluded from the pool.** They are reconstructions, and that's where boxscores that don't balance will show up.

**⚠️ Loader defect found (August 2026):** the download script concatenates `<season>*.E??`, and that
wildcard swallows `.EDA/.EDN/.EDF` — the deduced files. 105 files, 3,465 games, 1910–1968, already
loaded with nothing distinguishing them. The zips are the only place the distinction survives.

**Fix: record provenance as a column** on the game table (source file extension), rather than
maintaining a separate exclusion list. A regenerated exclusion list is a second source of truth that
can drift; a provenance column is permanent, queryable data — and §22's layer 1 needs it anyway.

### Good news about the chosen columns

Retrosheet proofs **offensive and pitching** statistics closely. **Defensive** ones — putouts and assists — are proofed less, because they were known to be kept far less reliably.

The §6 board uses AB, R, H, RBI, BB, K and IP, H, R, ER, BB, K: **all from the well-proofed side.** The problematic columns are exactly the ones dropped for lack of screen space. **The mobile constraint prevented a data problem.**

### Evaluated and rejected: chadwickbureau/data-boxscores

`https://github.com/chadwickbureau/data-boxscores`

*(A different repository from the Chadwick tools; reviewed due to a URL mix-up.)* **Unusable as a source.** Four reasons:

1. **It's minor league, not Major League.** The one-line pitch (§1) says "a real Major League game," and the reveal card with its Baseball Reference link loses its value with a forgotten minor-league game.
2. **It is deliberately an uncorrected archive.** The README warns that sources contain errors and that the collection doesn't attempt to correct them. The governing principle is *"type what's in the source,"* and it warns that **totals will not balance.** Conflicts with §22.
3. **It deliberately omits derivable values.** Its own example: if a boxscore lists Smith with 8 innings and doesn't mention Jones, they instruct *not* to transcribe Jones's inning even though it follows logically. **That deduction is exactly the game's mechanic.**
4. **Missing columns.** The most common header set is `ab r h po a e` — no RBI, BB, or K per batter.

**License:** data CC BY 4.0 (commercial use permitted with attribution); parser GPL 2.0.

### Separately useful: the Chadwick Bureau person register

`chadwickbureau/register` — for resolving player identities and names, exactly what §7's progressive reveal needs.

---

## 33. Environment separation: forge and serve

**These are not two environments of the same system. They are two separate systems communicating by artifact transfer, not over the network.**

> *Naming note: "forge" and "serve" replace the earlier informal terms. Pending final confirmation.*

### The boundary

**Operator's laptop — "forge", intermittent availability:**

- SQL Server with Retrosheet
- cwbox and the rest of the Chadwick tools
- Pool quality filter (§5)
- Generator and erasure algorithm
- T1–T5 validation solver (§4)
- End-to-end verification (§22)
- Calendar construction (§21)

Everything heavy and everything that can take hours.

**VPS — "serve", permanent availability:**

- Serving already-cooked puzzles
- The few endpoints: token, device registration, event sync

**The artifact that crosses is an immutable package of already-validated puzzles. The VPS never generates or validates anything — it only serves what it received.**

### The complete rule

**The forge knows nothing about users. The service knows nothing about generating.**

Neither machine needs to know the other's world. **The backend laptop knows nothing about rankings, accounts, or streaks.**

### Three independent domains with distinct lifecycles

| Domain | Who writes | Lifecycle |
|---|---|---|
| **Puzzles and calendar** | Forge only | Immutable, versioned. The VPS receives and never touches them |
| **The application** (engine, interface, copy) | Deployment | Deployed and rolled back at will, **without touching inventory** |
| **User data** (accounts, streaks, events, devices) | VPS only | The laptop never sees it |

**The use case this solves:** changing the application for a UX reason must not require touching the puzzle inventory or the calendar. And vice versa: loading new inventory must not require touching the application.

**Free privacy benefit:** personal data never leaves the server. The laptop is not an exposure surface for customer information, which simplifies the privacy policy.

### Service stack: Docker and nginx

**Decided.** With one care that follows from the above:

**The container and the puzzle inventory must be separate things.** If puzzles travel inside the image, every application deployment rebuilds the image and drags the inventory along — exactly what must be avoided.

- **The application goes in the container**
- **The puzzles are mounted as a volume**
- **Inventory updates and application deployments are independent operations**

**Domain configuration in nginx** (decided in advance, applied when the server is set up):

- Permanent (301) redirect from `boxscorepuzzles.com` and `boxscorepuzzle.app` to `boxscorepuzzle.com`
- Choose with or without `www` and redirect the other variant
- One indexable address only, to avoid diluting ranking across duplicates

### Forward inventory: 5 months

**Decision: the VPS always holds five months of puzzles served ahead.**

Covers an entire winter, which is exactly when the project might go unattended (§25).

**Alert when inventory drops below three months**, to find out with margin rather than all at once.

### The data container and its API

**The inventory lives in its own container with its own read layer.** The application requests puzzles and doesn't know how they're stored; updating inventory still doesn't touch the app.

**The key distinction is public read versus private write:**

| Operation | Protection |
|---|---|
| **Daily puzzle** | **None.** Static file served by nginx, no API, no key |
| **Inventory upload from the laptop** | **Header key.** It's a write, happens rarely, isn't in anyone's play path |
| **Paid historical archive** | **`canAccess()` from C8** validating the user token |

**Why the daily puzzle carries no key:**

- A header key **travels to the browser** and anyone can see it in the network tab. It protects nothing.
- It turns game delivery into an authenticated call, exactly what §23 avoids. If that layer falls or the key expires, **the game doesn't load** — introducing a fragile dependency in the one path that must survive everything.
- The daily puzzle is **public by nature**: everyone will see it today.

**And a static key is useless for the paid archive:** it's the same for everyone and doesn't distinguish who paid, which is the only thing that actually needs controlling.

### Abuse of the open daily puzzle — what's defended and what isn't

Three distinct scenarios, and only one deserves a defense:

| Scenario | Response |
|---|---|
| **Copying the daily puzzle to republish** | Unlikely — would require building an interface and attracting users. The defense is brand, not technical: streaks and stats live on the original site |
| **Downloading the full inventory** | Real, but **a key doesn't solve it.** Publishing only the day's file does; the archive sits behind C8 |
| **Automated traffic that takes down the server** | **The only one that truly matters** |

**For the third, the tool isn't authentication:**

- Per-IP rate limiting in nginx
- Only the current date's puzzle published, nothing future
- Caching with correct headers, absorbing almost all traffic before it reaches the container

**A cached static file withstands far more than an authenticated endpoint**, so leaving it open makes it *more* abuse-resistant, not less.

**And the underlying point:** the daily puzzle is public by design. Everyone will see it today and sharing is desired — it's the main growth channel (§20). Putting a barrier on it fights the model itself.

**What protects the business is what's already decided:** archive, stats, and streaks behind an account.

### Consequences

**1. Publishing well ahead stops being good practice and becomes mandatory.** If the laptop is the only machine that can produce puzzles, the VPS needs **months of inventory served ahead**. The laptop can be off, on a plane, or broken.

**2. The transfer must be verifiable.** Sign the package and verify the signature on receipt — already planned in §22 against corruption — now also covering an incomplete or interrupted upload.

**3. ⚠️ The laptop is a single point of failure.** If it dies, the pipeline and the ability to produce are lost. The site stays alive as long as inventory lasts, but can't be replenished.

Requires:

- Backup of the generator code
- Backup of the processed Retrosheet database
- Knowing how long rebuilding the environment on a new machine would take

### Folder and repository structure

```
boxscorepuzzle/
├── CLAUDE.md
├── docs/
│   ├── design-boxscore-puzzle.md
│   └── python-conventions.md
├── forge/           ← generator, cwbox, SQL, validation, calendar
└── serve/           ← app, nginx, docker, endpoints
```

A single root containing everything, with this section's separation visible in the structure itself. Name without spaces or hyphens, matching the domain.

**A single private Git repository on GitHub: `boxscorepuzzle`.** Rationale: one push backs up everything, which matters because the repository's primary job is being the backup. The forge/serve separation is enforced where it actually matters — in deployment configuration and in the no-cross-imports rule — not by repository boundaries. **Deployment ships `serve/` only; generator code must never reach the VPS.**

**The repository stays private permanently.** `forge/` holds the generator algorithm and the T1–T5 solvability guarantee — the trade secret identified in §16.

**GitHub is also the backup that consequence 3 requires.** Pushing is not optional hygiene, it's the disaster recovery plan: push at the end of every working session.

**What GitHub does not cover, and how each is handled:**

| Asset | Coverage |
|---|---|
| Generated puzzle inventory | The VPS is already a second copy — five months stay served even if the laptop dies |
| Processed Retrosheet database | Not backed up; **the loader script is.** Keep the load process reproducible from Retrosheet's original files |

That second row is the design rule: **make the pipeline reproducible rather than backing up its output.** The backup is the code.

*If `serve` ever needs its own CI, collaborators, or release cadence, splitting it out later is minor work.*

**⚠️ Generated puzzle inventory does not go in Git.** Thousands of files growing indefinitely, and not code. They go to an ignored folder inside `forge` and from there transfer to the VPS. If they enter the repository, within a year it's unusable.

**`CLAUDE.md` at the root** with the non-negotiable constraints, so they're read every working session:

- The T1–T5 no-backtracking guarantee (§4)
- Layered validation with code independent of the generator (§22)
- Double idempotence (§21)
- The calendar extends, never rewrites (§21)
- The forge knows nothing about users; the service knows nothing about generating (§33)

---

## 34. Legal matters — revisit before launch

> *None of this is legal advice. Confirm with a lawyer before launch.*

### Required on day 1

Since the site launches charging from day 0 (§10), these are not optional:

- **Terms of service.** The essential content is already decided and scattered through this document: access while the service operates (§10), personal and household use (§11), free cancellation. Drafting remains.
- **Privacy policy.** Mandatory as soon as there are accounts. **With users in Spain and the EU, GDPR applies**, even with operations in Miami.
- **Refund policy.** Paddle requires it, and §18 already decided on no-questions refunds below a threshold.
- **Retrosheet notice**, visible and prominent.
- **LLC formed** (§17).

### Not yet discussed

- **⚠️ Right to data deletion.** GDPR and California law require it. **It conflicts with the design and must be resolved:** if someone asks to delete their account, what happens to their C7 events that feed §26's percentiles? The likely answer is **anonymize rather than delete** — see §35, which resolves this at the schema level.
- **Cookies and consent.** Needed the day there are ads or analytics. C10 already anticipated this architecturally.
- **Taxes.** Collection delegated to the merchant of record. Declaring the income remains the operator's responsibility.
- **Minors.** A puzzle game will attract teenagers. In the US, COPPA applies under 13; the standard approach is to **prohibit registration under 13 in the terms**.
- **Real player names and data.** Statistical data are facts and nobody owns them. **But team photos and logos are owned.** With the text card and the Baseball Reference link (§29), there's no issue — best not to stray from that.
- **Accessibility.** Lawsuits over inaccessible commercial sites have proliferated in the US. Reinforces that accessibility is designed, not retrofitted (§6).

### Priority

**Trademark goes first.** It isn't a document drafted in an afternoon — clearance and registration take months.

---

## 35. User data

**Principle: the minimum required to operate.** Store what the already-decided features need, nothing more. Every extra field is leak surface and compliance work.

### What is stored

**Identity**

- Own internal identifier
- Email
- Link to the OAuth provider
- Creation and last-access dates

**No real name, photo, or date of birth**, even if Google offers them. They aren't needed, and requesting fewer permissions improves conversion on the login screen.

**Subscription**

- Paddle customer identifier
- Status
- Expiry date

**No card or billing data** — that lives at Paddle, which is the entire point of a merchant of record (§10).

**Devices** (§11)

- Random UUID
- Last seen
- Human-readable label so the user can recognize which one it is

No browser fingerprinting.

**Games — the heart of C7**

Per game: puzzle identifier, date, duration, whether completed, hints used, errors, and the highest technique required.

**The filled cells are not stored.** They aren't needed: percentiles, streaks, and difficulty calibration all come from aggregates.

**Preferences**

- Language
- Accessibility settings, if any

### What is NOT stored

- **IP address.** Personal data under GDPR and it adds nothing. For rate limiting, nginx uses it in memory without persistence
- Geolocation
- In-site browsing history
- Anything kept "just in case"

### Two schema requirements

**1. Separate events from identity at schema design time.** If a game references an unlinkable user identifier, **GDPR deletion is resolved by breaking that link** — and percentiles survive because the aggregate data becomes anonymous. **This resolves the conflict noted in §34.**

**2. Define a retention policy.** An account inactive for three years probably doesn't need to stay. Less old data is less risk.

---

## 36. Open items

**Blocking**

- [x] ~~Player names~~ — **resolved:** progressive reveal (§7)
- [~] **v1 board — partially resolved.** Column sets, six-column ceiling, and line-score-as-anchor are decided (§6). **Row counts, roster caps, and erasure percentage are provisional** and blocked on two measurements: the real height budget from a browser prototype, and compressibility + technique distribution across the pool. **Puzzle quality outranks board size — if the measurements say the board is too small to produce hard puzzles, the board changes.**

**Game core**

- [ ] Erasure algorithm: how many cells, in what order, whether the pattern is symmetric
- [x] ~~Which cells are never erased~~ — **resolved:** the line score, by width constraint (§6)
- [ ] Error handling: progressive reveal already forces row validation; still to define whether there's an error limit and what happens on failure
- [ ] What exactly a hint is: reveal a cell, flag a contradiction, or suggest a technique?
- [x] ~~Saving, pausing, resuming~~ — **resolved:** the puzzle stays open all day and saves itself (§27)
- [ ] What time the puzzle rolls over: local midnight or UTC
- [x] ~~What breaks the streak and whether there's grace~~ — **resolved:** midnight close for streak purposes, free monthly grace day, streak insurance in the paid tier (§27)
- [x] ~~Weekly difficulty curve~~ — **resolved:** easy Monday, hard Saturday, with technique randomness within each level (§31)

**Presentation**

- [x] ~~What the final reveal shows~~ — **resolved:** template-generated card with comparative data and a Baseball Reference link (§29)
- [ ] What the share grid encodes without spoilers (no names)
- [ ] Where the revealed name appears on mobile, since it doesn't fit in the label column (§6)
- [ ] How candidates mode works without hover (§6)

**Level 100**

- [x] ~~Can you lose?~~ — **resolved:** §27
- [x] ~~Does time matter?~~ — **resolved:** §26
- [x] ~~Is there a social layer?~~ — **resolved:** §26
- [x] ~~Does novelty run out?~~ — **resolved:** §31
- [x] ~~Seasonality~~ — **resolved:** §25
- [x] ~~Puzzle only, or content too?~~ — **resolved:** §29
- [x] ~~Is there community?~~ — **resolved:** §28
- [x] ~~What about players who don't know baseball?~~ — **resolved:** §8
- [x] ~~The one-line pitch~~ — **resolved:** §1
- [x] ~~The anti-goals~~ — **resolved:** §1
- [x] ~~What the product is in a year~~ — **resolved:** §30
- [x] ~~Brand and domain~~ — **resolved:** §24
- [ ] What gets measured to know it's working *(better resolved near launch)*
- [ ] **Accessibility as a product decision.** A grid of numbers with correct semantics is surprisingly playable with a screen reader — one of the few games a blind person could play in full. Could be a differentiator, not just compliance

**Data**

- [x] ~~Retrosheet coverage~~ — **measured (August 2026):** funnel in §5. 55,024 surviving directions before quality filters
- [ ] **⚠️ Next measurement, and the one that matters most: compressibility and technique distribution.** For a sample of surviving directions — how many cells can be erased preserving uniqueness *and* T1–T5 derivability, and which techniques the result demands. **This decides whether the board size produces hard puzzles.** Everything about board dimensions is blocked on it (§6)
- [ ] Re-measure era distribution after quality filters, before deciding whether the calendar needs era weighting (§5)
- [ ] **Loader fix:** add a provenance column so deduced event files are distinguishable (§32)
- [x] ~~Prior arithmetic validation~~ — **resolved:** layer 1 of §22
- [x] ~~No-repetition policy~~ — **resolved:** at batch generation (§21)

**Business and operations**

- [ ] Final pricing and the free/paid line
- [ ] Retention metrics
- [ ] Privacy, terms, refunds, and data deletion — full inventory in §34
- [ ] Retention policy: how long an inactive account is kept (§35)
- [ ] Accessibility: screen readers, color blindness, touch targets
- [ ] Forge rebuild plan if the laptop is lost (§33)
- [x] ~~Months of forward inventory~~ — **resolved:** 5 months, alert below 3 (§33)
- [x] ~~Daily publishing: batch or scheduled process~~ — **resolved:** pre-generated batch with fixed calendar (§21)
- [x] ~~What to do if a puzzle ships defective~~ — **resolved:** verified backup + substitution switch; if the date has passed, void it but don't reassign (§21, §22)

---

## Required notice

> The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at "www.retrosheet.org".
