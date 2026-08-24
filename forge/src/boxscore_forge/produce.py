"""Making one puzzle: erase a board, sign it, and put it through the publication gate.

**The per-board core, and the only definition of it.** `write_reference_puzzles.py` held this as
`build()` and was the only caller; the batch producer that fills the calendar needs exactly the same
thing, and a second copy of *how a package is made* is the defect this project meets most often.

⚠️ **It runs the gate, not a subset of the checks.** `certify_for_publication` is the boundary;
assembling a handful of checks per call site is what that boundary exists to remove.

⚠️⚠️ **It returns why it refused rather than printing it.** The reference writer printed the refusal —
correct for a script, wrong for a library, and it discarded the one number a batch run is sized from:
**which check refuses how often** (`docs/beta-0-plan.md`, A2.2). The gate keeps 11% of the pool before
any of this runs, so a five-month batch has to know its yield per cause before it starts, not after.
"""

from dataclasses import dataclass
from typing import Final

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from boxscore_domain import AUTOMATIC_RUNNER_FROM, MAX_INNINGS, REGULATION_INNINGS
from boxscore_forge.identity import puzzle_id
from boxscore_forge.lineup_fallback import erase_with_lineup_fallback
from boxscore_forge.pool import POSTSEASON_SOURCE, Loaded
from boxscore_forge.publish import slot_references, to_board
from boxscore_package.format import Package, PrintedBoxscore, Reveal
from boxscore_package.signing import sign
from boxscore_verify.certify import Evidence, certify_for_publication

SEED: Final = 6
"""The erasure seed. **Fixed, because §21 requires the same game to yield the same puzzle.** A seed
that varied per run would make regeneration produce different boards for the same date, which is the
double idempotence rule broken at its root."""


@dataclass(frozen=True, slots=True)
class Attempt:
    """One board's outcome: the package, or what stopped it.

    `cause` is `""` when it worked, `"erasure"` when no board could be erased to the target, and
    `"certification"` when the gate refused — and those are **different populations**. A pool that
    cannot be erased is a pool problem; a board the gate refuses is a validation problem. Collapsing
    them into `None` is what the reference writer did, and it is why nobody knows the yield today.
    """

    package: Package | None
    cause: str
    refusals: tuple[str, ...]


def reveal_for(loaded: Loaded) -> Reveal:
    """The answer to the mystery, which section 23 requires to be in the file."""
    # ⚠️ The teams come from the same query as the roster. `game_id[:3]` is the *home* club, and
    # labelling it as the offence is right only when the home side batted — which is how four of the
    # first six files claimed a lineup for a team it never played for. The names and the code have to
    # come from one source or nothing checks that they agree.
    return Reveal(
        # Composed by the loader, not here. ⚠️ This joined a `(first, last)` pair with
        # `.strip() or "Unknown"` while the prototype builder joined the same pair with neither — one
        # rule in two places, disagreeing about the players who have no given name on record.
        batter_names=loaded.names,
        pitcher_names=loaded.pitcher_names,
        offense_team=loaded.offense_team,
        defense_team=loaded.defense_team,
        played_on=f"{loaded.game_id[3:7]}-{loaded.game_id[7:9]}-{loaded.game_id[9:11]}",
        # ⚠️ **From the loader and never assembled here.** The printed sheet restates the board's own
        # numbers for the half they share, and `check_reveal_agrees` refuses a package where the two
        # disagree — so a second assembly here would be a second definition of the boxscore with a
        # guard standing between them, which is the arrangement that guard exists to make unnecessary.
        boxscore=required_boxscore(loaded),
        card="",
    )


def required_boxscore(loaded: Loaded) -> PrintedBoxscore:
    """The printed sheet, or a refusal that names the board.

    ⚠️ **Fails rather than defaults.** `Loaded.printed` is `None` only when the loader could not name
    a club, and it drops those directions — so `None` here means the loader and this writer disagree
    about what a loaded direction contains. An empty boxscore substituted quietly would ship a reveal
    with no sheet in it and no error anywhere, which is the absence of a check reading as a passing one.
    """
    if loaded.printed is None:
        message = f"{loaded.game_id} {loaded.offense_team} came back from the loader with no printed boxscore"
        raise SystemExit(message)
    return loaded.printed


def evidence_for(loaded: Loaded) -> Evidence:
    """What the producer knows and the package cannot say for itself.

    ⚠️ **`is_deduced` is the provenance row's own value now.** It used to be rebuilt here as
    `source_type.startswith("ED")`, which is a second copy of a rule the database already states — so a
    deduced record filed under an accepted source type would have passed §32's exclusion.

    ⚠️⚠️ **Four of these fields assert `to_board` fidelity and nothing more, and the list does not say
    so.** (v36-P3-14) `official_errors`, `official_defense_runs`, `official_defense_hits` and
    `official_defense_errors` are read from `loaded.direction.line_score` — **the same object the
    package's line score is built from**, one `to_board` copy apart. `check_independent_correspondence`
    compares the package against them, so what they can catch is a field swapped inside an eight-line
    copy; they cannot catch a board that never happened.

    **Only `official_at_bats` and `official_left_on_base` are correspondence in the strict sense**: they
    come from `retroGameLogs`, a table the board is not built from. `Evidence`'s own docstring makes
    that distinction and this call site presented all of them alike, which is the
    anchor-derived-from-what-it-verifies shape in miniature — documented as deliberate only for the
    query-level case.

    They are kept because a `to_board` swap is a real defect and cheap to exclude. They are labelled
    because a list where two entries mean something different from the other four, unmarked, is how a
    reader comes to believe the gate is stronger than it is.
    """
    return Evidence(
        # ⚠️ **The board as the database has it**, which is what layer 4 must solve back to. The
        # package under certification here is the one read back from disk, so the comparison is
        # between the file and the game rather than between the file and itself.
        source=to_board(loaded.direction, None),
        game_id=loaded.game_id,
        offense_team=loaded.offense_team,
        source_type=loaded.source_type,
        is_deduced=loaded.is_deduced,
        official_hits=loaded.official_hits,
        official_runs=loaded.official_runs,
        # ⚠️ These four come from the direction the package is built from. They assert `to_board`
        # fidelity, not correspondence with the game. See the note above.
        official_errors=loaded.direction.line_score.offense_errors,
        official_defense_runs=loaded.direction.line_score.defense_runs,
        official_defense_hits=loaded.direction.line_score.defense_hits,
        official_defense_errors=loaded.direction.line_score.defense_errors,
        # ⚠️ The two real anchors: `retroGameLogs`, a table the board is not built from.
        official_at_bats=loaded.official_at_bats,
        official_left_on_base=loaded.official_left_on_base,
    )


def inadmissible(loaded: Loaded) -> str:
    """Why this game may not become a board, or `""`. **`docs/excluded-games.md` is the register.**

    ⚠⚠ **Every one of these balances.** Forfeits, ties and partial accounts were tested through this
    very function and **published boards the four layers accepted** — §22's layers ask whether the
    numbers agree with each other, and for these games they do. What they describe is a game the board
    cannot honestly show, and **what lies is the reveal** (§29): it prints the finished boxscore beside a
    Baseball Reference link, and a player who follows it finds *forfeited*, or *tie, called*, or a game
    completed three weeks later.

    **So a future reader meeting a refusal on a perfect game is not looking at a broken check.** That is
    why this returns a named cause and why the register exists.
    """
    score = loaded.direction.line_score
    innings = max(len(score.offense_by_inning), len(score.defense_by_inning))
    grounds = (
        # The board draws twelve (§6). A seventeen-inning line score has seventeen columns.
        (innings > MAX_INNINGS, "innings"),
        # ⚠️⚠️ **Three conditions, and the third is the rule rather than a detail.** The operator settled
        # this on 2026-08-24: the automatic runner is a **regular-season** rule from 2020, and it has
        # never applied to the postseason in any season. A 2020+ postseason extra-inning game is
        # ordinary and must be admitted — `test_the_automatic_runner_is_regular_season_only` fails if
        # a season floor is ever applied to both halves, which is the wrong rule with the right number.
        #
        # ⚠️ **The exemption is an acceptance test, not an exclusion.** A game escapes only by being
        # positively known to be postseason; an unrecorded `source_type` is treated as regular season
        # and refused. That is the fail-closed direction — a board lost against an identity broken —
        # and the same shape as `account != "Y"` below.
        (
            innings > REGULATION_INNINGS
            and loaded.season >= AUTOMATIC_RUNNER_FROM
            and loaded.source_type != POSTSEASON_SOURCE,
            "automatic runner",
        ),
        (bool(loaded.forfeit), "forfeit"),
        # ⚠️ All protests, not only the two upheld codes. A disallowed protest leaves the game exactly
        # as played and those 127 are sound — the operator ruled that 132 games out of 203,908 is not
        # worth a rule that has to be right about five letters. Recorded so nobody re-admits them
        # believing they were excluded by mistake.
        (bool(loaded.protest), "protest"),
        (loaded.completed_later, "completed later"),
        # ⚠️ **An acceptance test.** Retrosheet's codes are `Y` complete, `P` partial, `N` nothing, `D`
        # derived — and 297 pool games carry no value at all. `!= "P"` would admit every code nobody
        # thought of, including the empty one, which is the fail-open shape §32 has closed twice.
        (loaded.account != "Y", "partial account"),
        (score.offense_runs == score.defense_runs, "tie"),
    )
    # ⚠️ A tuple rather than a chain of returns, so adding a rule is adding a line and the order the
    # causes are reported in is visible in one place.
    return next((cause for holds, cause in grounds if holds), "")


def produce(loaded: Loaded, target: int, key: Ed25519PrivateKey, *, note: str, seed: int = SEED) -> Attempt:
    """Generate one puzzle and put it through the publication gate, not a subset of the checks.

    ⚠⚠ **The batting order is a fallback, not a switch.** Boards that reach their target without it
    never see it, so they never pay its cost: with the constraint on everywhere, a median of eight
    steps per board became *read the total, divide by nine, write it down* — 244 such cells across the
    walks measured. On the eleven directions that reach eight stalls only with it, nine carry no such
    filler at all. It is worth something exactly where the board cannot get there without it.
    """
    # ⚠⚠ **Before any work, and this is the guarantee rather than the query.** The pool excludes these
    # too, but only to avoid building what it would discard — a `Loaded` assembled by hand never passed
    # through a `WHERE`, and one query's rule is not the next query's. **Every published board comes
    # through here**, so this is the narrowest place that cannot be walked around.
    if refusal := inadmissible(loaded):
        return Attempt(package=None, cause=refusal, refusals=())
    produced, why = erase_with_lineup_fallback(loaded.direction, tuple(loaded.slots), target_stalls=target, seed=seed)
    # ⚠️⚠️ **Kept, and written into the package.** (v36-P2-12) This read `del why` — *the reason is for
    # the measurement instruments; this script only needs the board* — and `lineup_fallback.py` returns
    # it precisely because **every measurement comparing these boards needs to know which population
    # each one is in**. The one production caller was throwing that away.
    #
    # Without it, a board that is unique and derivable **only because of the batting-order clue** is
    # indistinguishable in its own metadata from a plain one. Seam C3 asks for *techniques required*;
    # a calendar shaping the week by technique, or a client deciding what to surface, cannot see the
    # one family that cannot be read off a boxscore — the family §8 has to teach for that very reason.
    #
    # ⚠️⚠️ **`families` carries it now, and this comment said the opposite for a commit.** (v37-P3-04)
    # It read *"`FAMILY_OF` maps no `Identity` to the batting order… that is an operator decision and
    # it is recorded in `todo.md`, not taken here"*. **The decision was taken on 2026-08-21**:
    # `Family.BATTING_ORDER` exists, `FAMILY_OF` maps the identity to it, and one of the six published
    # boards lists `batting_order` among its families.
    #
    # ⚠️ A settled decision described as open, in the production path, is an invitation to reopen it —
    # which is worse than a stale figure, because a reader has no number to check it against. `lineup`
    # below is still worth recording separately: it says whether the board *needed* the clue, which is
    # not the same question as which families its solution used.
    if produced is None:
        # ⚠️ **The erasure failing is a different outcome from the gate refusing**, and a producer that
        # collapsed them could not tell a pool that yields nothing from one whose boards keep failing a
        # check. The batch run's survival rate is read per cause.
        return Attempt(package=None, cause="erasure", refusals=())
    package = sign(
        Package(
            puzzle_id=puzzle_id(loaded.game_id, loaded.offense_team),
            puzzle=to_board(loaded.direction, produced.erased),
            solution=to_board(loaded.direction, None),
            labels=loaded.labels,
            slot_references=slot_references(loaded.slots),
            # From the loader, which reads it from the game rather than inferring it. A client cannot
            # know which club batted last, and one that guessed would be right only when the line
            # score happens to be ragged.
            offense_is_home=loaded.offense_is_home,
            pitcher_labels=loaded.pitcher_labels,
            reveal=reveal_for(loaded),
            metadata={
                "note": note,
                "difficulty_model": "stalls",
                # ⚠⚠ **Recorded so `audit()` can ask the shipped population whether it is clean, from
                # disk and without a database.** A rule that lives only in a `WHERE` has nothing
                # checking it afterwards — which is how the seventeen-inning board reached a date. These
                # four are what the packages carry forward about their own admissibility.
                "innings": max(
                    len(loaded.direction.line_score.offense_by_inning),
                    len(loaded.direction.line_score.defense_by_inning),
                ),
                # ⚠️ No `season` here: §7 strips it from the published package, so it would not
                # survive to be audited. `audit()` reads the era from the calendar's `game_id`.
                "account": loaded.account,
                "disposition": "".join((loaded.forfeit, loaded.protest, "C" if loaded.completed_later else "")),
                "target_stalls": target,
                "stalls": produced.solution.stalls,
                # Descriptive telemetry. Chain is recorded because every earlier measurement used it
                # and they have to stay comparable — it is not what the board was selected on.
                "chain_length": produced.solution.chain_length,
                "blanks": len(produced.erased),
                "families": sorted(family.value for family in produced.solution.families_used),
                # `"plain"` or `"fallback"`: whether this board reached its target without the
                # batting-order clue or only with it. The distinction the erasure already knows and
                # the package could not previously state.
                "lineup": why,
                "batters": len(loaded.direction.batting),
                "pitchers": len(loaded.direction.pitching),
                "seed": seed,
                "game_id": loaded.game_id,
                "season": loaded.season,
            },
        ),
        key,
    )
    # ⚠️ The gate, not `verify()`. Assembling a subset of the checks at each call site is the defect
    # this boundary exists to remove, and this writer was one of the sites doing it.
    #
    # ⚠️⚠️ **`published()`, because that is the object the gate is named for — and this call site said
    # otherwise for one commit, which stopped the writer publishing anything at all.**
    #
    # The metadata above deliberately carries `game_id` and `season`: the producer needs them, and
    # `published()` strips them on the way out. `check_no_leaking_metadata` (v36-P2-10) was added to
    # the registry so the strip is verified at the boundary rather than trusted — and it is right.
    # What was wrong is what this line handed it: **the working object, which never ships.** Every
    # candidate was refused, the run wrote 0 of 6, and the fail-closed staging left the published set
    # untouched, which is the only reason this cost nothing.
    #
    # **`canonical_bytes` had already decided the question.** The signature is computed over
    # `package.published().as_json()` — the signer's object of record is the shape that travels, so a
    # gate certifying a different shape was disagreeing with the signature about what the package *is*.
    #
    # ⚠️ The leak check cannot fire here, by construction, and that is not a check switched off: the
    # one that can fire is in `main`, over the package **read back from the file**. This call is a
    # pre-screen that discards a candidate cheaply; the boundary is disk.
    for_publication = package.published()
    certified = certify_for_publication(for_publication, evidence=evidence_for(loaded), secret=key.public_key())
    if not certified.publishable:
        # ⚠️ **Returned, not printed.** This printed the refusal, which is a script's interface and not
        # a library's — and it threw away the one thing a batch run needs, which is *which check*
        # refused how often. `docs/beta-0-plan.md` A2.2 sizes a five-month batch off that number.
        return Attempt(package=None, cause="certification", refusals=tuple(certified.refusals))
    return Attempt(package=for_publication, cause="", refusals=())
