"""The reference writer's own gate call, exercised without the database. (v36 regression)

⚠️⚠️ **A check added to the publication gate stopped the writer publishing anything, and the whole
suite stayed green.** `check_no_leaking_metadata` was registered so the gate verifies that
`published()` stripped `game_id`, `season` and the rest — a correct check, and the registry's own
tests cover both of its directions. What no test covered was **the call site**: `build()` handed the
gate the *working* package, the one that deliberately still carries `game_id` because the producer
needs it, and which never ships. Every candidate was refused, the run wrote 0 of 6, and only the
fail-closed staging kept the published set alive.

**This is the project's named failure shape in its purest form: two places that should say the same
thing.** The gate's notion of *the package for publication* and the writer's notion of it were
different objects, and nothing compared them. `canonical_bytes` had already decided the question —
the signature is computed over `package.published().as_json()` — so the writer was disagreeing with
its own signer about what the package is.

⚠️ **The existing fixture could not have caught it, and its comment says the opposite.**
`test_lineup_fallback_is_adopted.py` builds a package it describes as *"built the way production
builds it"* and gives it **no metadata at all**, so `LEAKING_METADATA & {}` is empty and the check
passes on a package differing from the writer's in exactly the field that mattered. A claim like that
in a test is worse than its absence, because it is the reason nobody looks.

So this file calls **the writer's own `build()`**, with the writer's own metadata, and no database:
`Loaded` is a plain dataclass and the fixture direction is a real 1968 game.
"""

import ast
import pathlib
import sys
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from boxscore_forge.boxscore import Direction
from boxscore_forge.publish import to_board
from boxscore_package.format import BATTING_COLUMNS, LEAKING_METADATA, Package
from boxscore_verify.certify import certify_for_publication
from tests.reveals import reveal_for as fixture_reveal

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "forge" / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import write_reference_puzzles as writer  # noqa: E402

from boxscore_forge.pool import Loaded  # noqa: E402
from boxscore_forge.produce import produce  # noqa: E402

GAME, OFFENSE, DEFENSE = "SLN19680808", "CHN", "SLN"
"""The game the shared fixture is. The gate checks the identifier against the evidence, so both have
to name the same one."""

SLOTS = tuple(range(1, 10))

TARGET = 4
"""⚠️ Any target the fixture reaches would do — this file is about the gate, not about difficulty — so
the fixture below states that it was reached rather than assuming it. A `build()` returning `None`
because the erasure missed looks identical to one refused by the gate, and that confusion is the whole
reason this file exists.
"""


def _loaded(direction: Direction) -> Loaded:
    """A `Loaded` the way the loader would hand one over, built from the fixture instead of SQL."""
    labels = ("C",) * len(direction.batting)
    pitcher_labels = ("SP",) * len(direction.pitching)
    board = to_board(direction, None)
    # The reveal helper composes a sheet agreeing with the board by construction, and the names it
    # invents are the ones `check_reveal_agrees` compares against — so they come from here rather than
    # being made up a second time.
    fixture = fixture_reveal(board, labels=labels, pitcher_labels=pitcher_labels, offense=OFFENSE, defense=DEFENSE)
    return writer.Loaded(
        game_id=GAME,
        season=1968,
        direction=direction,
        labels=labels,
        offense_is_home=False,
        names=fixture.batter_names,
        pitcher_labels=pitcher_labels,
        offense_team=OFFENSE,
        defense_team=DEFENSE,
        pitcher_names=fixture.pitcher_names,
        source_type="EVN",
        official_hits=board.line_score.offense_hits,
        official_runs=board.line_score.offense_runs,
        is_deduced=False,
        official_at_bats=board.batting_totals[BATTING_COLUMNS.index("at_bats")],
        # ⚠⚠ **Admissible, and spelled out rather than defaulted.** `Loaded`'s four disposition fields
        # default to the *refusing* values (`docs/excluded-games.md`), so a fixture that omits them is
        # refused as a partial account -- which is the fail-closed direction and the reason the default
        # is what it is. A fixture standing in for a publishable game has to say so.
        account="Y",
        official_left_on_base=board.left_on_base,
        slots=SLOTS,
        printed=fixture.boxscore,
    )


@pytest.fixture
def built(cubs_at_braves_1968: Direction) -> Package:
    """What `produce()` returns, or a failure naming which half went wrong.

    ⚠️ **A throwaway key.** The real signing key never enters a test (§33), and nothing here needs it:
    `produce()` verifies against `key.public_key()`, which any Ed25519 pair satisfies.

    ⚠️ **`build()` moved to `boxscore_forge.produce` as `produce()`** (`docs/beta-0-plan.md`, A2), so the
    batch producer and this writer share one definition. The assertion below is better for it: the
    attempt now says *which* half went wrong instead of leaving a silent `None` to be guessed at, which
    is the regression this whole file is about.
    """
    attempt = produce(_loaded(cubs_at_braves_1968), TARGET, Ed25519PrivateKey.generate(), note=writer.NOTE)

    assert attempt.package is not None, (
        f"the writer built nothing at {TARGET} stalls: {attempt.cause or 'no cause given'}"
        f"{' — ' + '; '.join(attempt.refusals) if attempt.refusals else ''}"
    )
    return attempt.package


class TestTheWriterPublishesWhatItsOwnGateAccepts:
    def test_a_board_the_writer_builds_reaches_the_gate(self, built: Package) -> None:
        """The regression itself. With the call site handing over the working package, this is `None`."""
        assert built.puzzle_id

    def test_what_the_writer_returns_names_no_game(self, built: Package) -> None:
        """§7: the shape that travels carries nothing giving the answer away."""
        leaking = sorted(LEAKING_METADATA & built.metadata.keys())

        assert leaking == [], f"the writer returns a package still naming the game: {leaking}"

    def test_the_writer_still_records_what_the_board_is(self, built: Package) -> None:
        """⚠️ The strip must not be achieved by the producer recording less.

        Seam C3 wants rich metadata on every puzzle. A writer that stopped attaching `stalls` and
        `families` would pass the test above for the wrong reason, and this is the difference.
        """
        assert {"stalls", "target_stalls", "families", "blanks", "lineup"} <= built.metadata.keys()


class TestTheGateHasTeethOnThisExactPackage:
    """⚠️⚠️ Without these two, the green above is worth nothing.

    A leak check that never fires and one that always passes look identical from a passing test. These
    say: the producer really does attach the keys, and the gate really does refuse them — so the
    package publishing is the **strip** working rather than the check being vacuous.
    """

    def test_the_producer_attaches_the_keys_the_strip_is_for(self) -> None:
        """Read off `produce()` itself, because the package it returns no longer carries them.

        ⚠️ If this fails, the control below is guarding a field nobody writes and the file has quietly
        stopped testing anything.

        ⚠️ **The scan follows the function.** It parsed `write_reference_puzzles.py` for `def build`;
        that function is `produce` in `boxscore_forge/produce.py` now, and a scan left pointing at the
        old file finds nothing — `next()` over an empty generator, which raises rather than passing, and
        that is the only reason this was caught rather than silently guarding nothing.
        """
        source = _ROOT / "forge" / "src" / "boxscore_forge" / "produce.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        core = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "produce")
        written = {
            key.value
            for node in ast.walk(core)
            if isinstance(node, ast.Dict)
            for key in node.keys
            if isinstance(key, ast.Constant) and isinstance(key.value, str)
        }

        assert LEAKING_METADATA & written, "produce() no longer attaches any key the strip is for"

    def test_the_same_package_is_refused_with_the_producers_metadata_back(
        self, built: Package, cubs_at_braves_1968: Direction
    ) -> None:
        """The exact object that publishes, refused the moment the game is named on it."""
        named = replace(built, metadata={**built.metadata, "game_id": GAME, "season": 1968})

        result = certify_for_publication(
            named,
            evidence=writer.evidence_for(_loaded(cubs_at_braves_1968)),
            secret=Ed25519PrivateKey.generate().public_key(),
        )

        assert not result.publishable
        assert any("no_leaking_metadata" in refusal for refusal in result.refusals), result.refusals
