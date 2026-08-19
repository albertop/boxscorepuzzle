"""Fifty boards to solve by hand, as a printable pack — and an experiment inside it.

§22 promotes the hand-solve from sanity check to launch gate, because it is the only real
verification of human derivability that exists and the only check the same-author risk does not
touch. This builds the pack.

**It is also an experiment with a hypothesis.** Layer 3 certifies that a propagator holding every
relation at once needs no guess; layer 3b asks the same of a solver reading one relation at a time,
and **29% of Saturday boards fail it**. A player sits between the two and nothing automated says
where. So a third of these fifty come from the uncertified 29%, interleaved at random and unlabelled:

  * solved with no more difficulty than the rest → 3b is too conservative and stays reported
  * stuck systematically on them → 3b becomes a gate

**Which board is which is in `key.csv`, which must not be opened until the solving is finished.**
Nothing on a puzzle page identifies the game, the date, the teams, the chain target, the difficulty
or the certification status. The board reference is a sequential number and encodes nothing.

Read-only against DGL. Run from `forge/`.
"""

import csv
import random
import sys
from dataclasses import dataclass
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "forge" / "src"))
sys.path.insert(0, str(_ROOT / "discovery" / "difficulty-metrics"))
sys.path.insert(0, str(_ROOT / "discovery" / "verifier"))

from collections.abc import Sequence  # noqa: E402

from measure import Loaded, load, slot_references  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import mm  # noqa: E402
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

from boxscore_forge.erasure import erase  # noqa: E402
from boxscore_forge.publish import to_board  # noqa: E402
from boxscore_package.format import FOOTNOTE_COLUMNS, Board  # noqa: E402
from boxscore_package.format import Package as PuzzlePackage  # noqa: E402
from boxscore_package.innings import to_display  # noqa: E402
from boxscore_verify.verify import UNSIGNED, derivable_in_view, verify  # noqa: E402

TARGETS = (5, 7, 9, 11)
QUOTAS = {5: 8, 7: 11, 9: 14, 11: 17}
"""Every rung present, weighted towards the hard end.

⚠️ **These are chain targets and the target variable is now stalls.** Chain counts how long a solve
is; the operator solved a chain-10 board in under a minute. **This pack must not be printed until
`erase` can take a stall target** — a pack that says stalls and means chain would repeat the mistake
it exists to correct.

Explicit quotas rather than weighted sampling. A first version drew by weight and produced no chain-5
boards at all — with one board per game, the hard targets took every game before the easy ones were
reached, and a pack missing a rung cannot say anything about that rung.
"""

WANTED = 50
UNCERTIFIED_SHARE = 1 / 3
PRE_1950_ALLOWANCE = 2
"""§5's pre-1950 preference, applied so the pack looks like what will actually ship."""

GATE = 0.25
"""§5's zero-density gate at its strict end. The corrected pool is abundant enough to afford it."""

SEED = 50
SAMPLE_PER_DECADE = 8

BATTING_HEADS = ("PA", "AB", "R", "H", "BB", "SO")
PITCHING_HEADS = ("IP", "H", "R", "ER", "BB", "SO")
FOOTNOTE_LABELS = (
    ("hit_by_pitch", "HBP"),
    ("sacrifice_flies", "SF"),
    ("sacrifice_hits", "SH"),
    ("catcher_interference", "CI"),
)


@dataclass(frozen=True)
class Candidate:
    loaded: Loaded
    target: int
    puzzle: Board
    solution: Board
    certified: bool
    has_substitution: bool
    has_live_footnote: bool


def footnote_line(board: Board, slots: "Sequence[int]") -> str:
    """`SF: 3   SH: 2, 9b   LOB: 9` — read from the **puzzle**, never from the source direction.

    ⚠️ **This took its values from `Loaded.direction` and the grid beside it drew the erased board.**
    The per-batter footnote cells are erasable, so a value removed for grading was handed straight back
    on the page: the printed board was easier than the puzzle whose stalls and layer-3b status its key
    recorded. That is not the `Direction → Board` defect fixed earlier — it is `Board → the artifact a
    human reads`, one boundary further out, and the same shape.

    ⚠️ **The placeholder is provisional.** An erased attribution has to be *resolvable* rather than
    merely absent — a blank in a sparse prose line does not read like an empty cell in a grid — and how
    many candidates it must separate depends on the group measurement. `?` holds the position until
    that lands; it is not the design.
    """
    parts = []
    for field, short in FOOTNOTE_LABELS:
        column = FOOTNOTE_COLUMNS.index(field)
        references = slot_references(slots)
        carriers = [
            references[index] if row[column] else "?"
            for index, row in enumerate(board.footnotes)
            if row[column] is None or row[column]
        ]
        if carriers:
            parts.append(f"{short}: {', '.join(carriers)}")
    parts.append(f"LOB: {board.left_on_base}")
    return "   ".join(parts)


def candidates(sample: list[Loaded]) -> list[Candidate]:
    found: list[Candidate] = []
    for loaded in sample:
        source = to_board(loaded.direction, None)
        for target in TARGETS:
            produced = erase(loaded.direction, target_chain=target, seed=SEED)
            if produced is None:
                continue
            board = to_board(loaded.direction, produced.erased)
            package = PuzzlePackage(
                labels=("C",) * len(board.batting),
                pitcher_labels=("C",) * len(board.pitching),
                offense_is_home=True,
                puzzle_id="pack",
                puzzle=board,
                solution=source,
            )
            if not verify(package, secret=UNSIGNED).accepted:
                continue
            found.append(
                Candidate(
                    loaded=loaded,
                    target=target,
                    puzzle=board,
                    solution=source,
                    certified=derivable_in_view(package),
                    # ⚠️ A substitution is two rows sharing a lineup slot, not a hyphen in a label. This
                    # read `"-" in label` and broke silently the moment the suffix was removed — the pool
                    # reported that no board carries a substitution, which is false of 12% of them. Third
                    # instance today of something derived from the label's formatting instead of the slot.
                    has_substitution=len(set(loaded.slots)) < len(loaded.slots),
                    has_live_footnote=any(
                        note.hit_by_pitch or note.sacrifice_flies or note.sacrifice_hits or note.catcher_interference
                        for note in loaded.direction.batter_footnotes
                    ),
                )
            )
    return found


def choose(pool: list[Candidate], rng: random.Random) -> list[Candidate]:
    """Fifty boards: a third uncertified, every chain target present, era quota respected.

    One board per game, so no solver sees the same lineup twice and recognises it.
    """
    wanted_uncertified = round(WANTED * UNCERTIFIED_SHARE)
    chosen: list[Candidate] = []
    used_games: set[str] = set()
    pre_1950 = [0]

    def take(candidate: Candidate) -> bool:
        if candidate.loaded.game_id in used_games:
            return False
        if candidate.loaded.season < 1950 and pre_1950[0] >= PRE_1950_ALLOWANCE:
            return False
        used_games.add(candidate.loaded.game_id)
        pre_1950[0] += candidate.loaded.season < 1950
        chosen.append(candidate)
        return True

    def shuffled(items: list[Candidate]) -> list[Candidate]:
        ordered = sorted(items, key=lambda item: item.loaded.game_id)
        rng.shuffle(ordered)
        return ordered

    # ⚠️ Uncertified boards are capped **per rung**, not only overall. Layer 3b certifies 100% of
    # chain-5 boards and 91% of chain-11 ones, so the uncertified candidates all live at the hard
    # end — and filling the hardest rung with them made every chain-11 board uncertified and every
    # other board certified. That is a perfectly confounded experiment: uncertified and hard would
    # be the same variable, and any difference the solver felt would be difficulty.
    #
    # Each rung therefore gets at most half its quota uncertified, which keeps the comparison inside
    # a rung where the boards are the same difficulty by construction.
    for target in sorted(TARGETS, reverse=True):
        wanted = QUOTAS[target]
        ceiling_here = wanted // 2
        at_target = len([item for item in chosen if item.target == target])
        for prefer_uncertified in (True, False):
            for candidate in shuffled([item for item in pool if item.target == target]):
                if at_target >= wanted:
                    break
                if candidate.certified == prefer_uncertified:
                    continue
                if prefer_uncertified:
                    if len([c for c in chosen if not c.certified]) >= wanted_uncertified:
                        break
                    here = len([c for c in chosen if c.target == target and not c.certified])
                    if here >= ceiling_here:
                        break
                if take(candidate):
                    at_target += 1

    # The two cases the tutorial has to teach must appear somewhere in the pack. If one is missing a
    # board is *swapped* rather than appended: the replacement takes the place of one at the same
    # chain target, the same certification and the same side of 1950, so every quota survives the
    # substitution. An earlier version appended and then dropped `chosen[-2]`, which removed an
    # arbitrary board and could silently empty a rung.
    for trait_name, trait in (
        ("substitution", lambda c: c.has_substitution),
        ("live footnote", lambda c: c.has_live_footnote),
    ):
        if any(trait(item) for item in chosen):
            continue
        for candidate in shuffled([item for item in pool if trait(item)]):  # pragma: no cover - rare
            if candidate.loaded.game_id in used_games:
                continue
            victims = [
                item
                for item in chosen
                if item.target == candidate.target
                and item.certified == candidate.certified
                and not trait(item)
                and (item.loaded.season < 1950) == (candidate.loaded.season < 1950)
            ]
            if not victims:
                continue
            chosen.remove(victims[0])
            used_games.discard(victims[0].loaded.game_id)
            pre_1950[0] -= victims[0].loaded.season < 1950
            take(candidate)
            break
        else:  # pragma: no cover - only if the pool cannot supply the trait at all
            message = f"no board in the pool carries a {trait_name} at a target the pack can spare"
            raise SystemExit(message)

    rng.shuffle(chosen)
    audit(chosen)
    return chosen


FORMULAS = (
    "PA = AB + BB + HBP + SF + SH + CI &nbsp;&nbsp;|&nbsp;&nbsp; "
    "Column totals = sum of the rows &nbsp;&nbsp;|&nbsp;&nbsp; "
    "PA = Outs + Runs + LOB<br/>"
    "Team H = hits allowed by the opposing pitchers (same for BB, SO, R) &nbsp;&nbsp;|&nbsp;&nbsp; "
    "Outs = 3 x innings pitched &nbsp;&nbsp;|&nbsp;&nbsp; "
    "AB &ge; H &nbsp;&nbsp;|&nbsp;&nbsp; ER &le; R &nbsp;&nbsp;|&nbsp;&nbsp; nothing below zero"
)
"""On every page, not only on a cover sheet — somebody solving across several days should not have
to go and find it.

It doubles as the first real test of §8's permanent reference sheet. If this works on paper across
fifty boards the reference sheet is about right, and if it does not, that is worth knowing now.
"""


def survey_box() -> Table:
    """The three categories stay separate, and the 1-6 scale is what validates the chain.

    ⚠️ **The scale is the only thing that can test whether chain length measures difficulty at all.**
    Chain length is a solver measurement; that it corresponds to what a person experiences is an
    assumption nobody has checked. If the marked 1-6 tracks chain, the scale is validated. If it does
    not, chain is measuring something else and the generator's control variable is wrong — which is
    worth knowing before a calendar is built on it.

    It is deliberately not tied to the day of the week. A 5 marked on a board the system calls Monday
    says that board is misclassified, and that is exactly the signal wanted.

    Two conditions or it measures nothing, both enforced elsewhere: **the chain target never appears
    on the page**, since seeing "chain 8" anchors the rating to the number, and **the pages are not
    ordered by chain**, since the early boards become the reference for everything after them.

    Only **had to guess** bears on layer 3b. **Tedious** and **boring** bear on the difficulty curve
    and the quality filter, and merging them loses both answers.

    The free-text line matters more than it looks: every serious defect in this project came from
    somebody noticing that something looked wrong, never from a statistic.
    """
    lines = [
        ["Time taken: ________ min", "Finished?    Y  /  N"],
        ["How many times did you have to stop and think?  ______", ""],
        ["How hard was it?     1     2     3     4     5     6", "(1 = very easy, 6 = very hard)"],
        ["If not finished, where did you get stuck?  _________________________________________", ""],
        ["How did it feel?   (tick any)", ""],
        ["   [   ] Had to guess — no next step by reasoning", "   [   ] Tedious — too much adding, or hunting"],
        ["   [   ] Boring — easy, nothing to think about", "   [   ] Good"],
        ["Anything odd?  ____________________________________________________________________", ""],
    ]
    table = Table(lines, colWidths=[80 * mm, 72 * mm], rowHeights=4.9 * mm)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#666666")),
                # The four feelings sit two by two rather than one per line: it is a shorter box and
                # a tick grid reads faster than a list when the same four choices repeat fifty times.
                ("SPAN", (0, 1), (1, 1)),
                ("SPAN", (0, 3), (1, 3)),
                ("SPAN", (0, 4), (1, 4)),
                ("SPAN", (0, 7), (1, 7)),
                ("LINEBELOW", (0, 0), (-1, 0), 0.3, colors.HexColor("#bbbbbb")),
                ("LINEBELOW", (0, 2), (-1, 2), 0.3, colors.HexColor("#bbbbbb")),
                ("LINEBELOW", (0, 6), (-1, 6), 0.3, colors.HexColor("#bbbbbb")),
            ]
        )
    )
    return table


def audit(chosen: list[Candidate]) -> None:
    """Assert the pack is what it claims. A launch gate is checked by code, never believed from print.

    The pack decides whether layer 3b becomes a gate, so a pack that reports quotas it does not meet
    invalidates that experiment silently. It has happened once already: weighted sampling produced
    zero boards at the easiest rung and only the printed summary showed it.
    """
    wanted_uncertified = round(WANTED * UNCERTIFIED_SHARE)
    problems: list[str] = []
    if len(chosen) != WANTED:
        problems.append(f"{len(chosen)} boards, wanted {WANTED}")
    for target, quota in QUOTAS.items():
        at_target = sum(1 for item in chosen if item.target == target)
        if at_target != quota:
            problems.append(f"chain {target} has {at_target} boards against a quota of {quota}")
    uncertified = sum(1 for item in chosen if not item.certified)
    if abs(uncertified - wanted_uncertified) > 2:
        problems.append(f"{uncertified} uncertified boards, wanted about {wanted_uncertified}")
    pre_1950 = sum(1 for item in chosen if item.loaded.season < 1950)
    if pre_1950 > PRE_1950_ALLOWANCE:
        problems.append(f"{pre_1950} pre-1950 boards against an allowance of {PRE_1950_ALLOWANCE}")
    games = [item.loaded.game_id for item in chosen]
    if len(set(games)) != len(games):
        problems.append("the same game appears twice")
    if not any(item.has_substitution for item in chosen):
        problems.append("no board carries a suffixed label, and the tutorial has to teach one")
    if not any(item.has_live_footnote for item in chosen):
        problems.append("no board carries a live footnote, and the tutorial has to teach one")
    # ⚠️ Also folded in: layer 3b certifies every easy board and 91% of the hard ones, so the
    # uncertified candidates all live at the hard end. A rung entirely uncertified makes
    # "uncertified" and "hard" the same variable, and any difference the solver feels is difficulty.
    by_rung = {target: sum(1 for c in chosen if c.target == target and not c.certified) for target in TARGETS}
    for target, count in by_rung.items():
        if count and count == QUOTAS[target]:
            problems.append(f"chain {target} is entirely uncertified, so nothing at that rung compares")

    # ⚠️ Folded in from a second `audit()` that had been defined below this one. Python kept the
    # later definition, so the strict uncertified share this function enforces was not running and a
    # pack could pass with anywhere from 10% to 50% uncertified boards. One audit, not two.
    order = [candidate.target for candidate in chosen]
    rising = sum(1 for a, b in zip(order, order[1:], strict=False) if b > a)
    falling = sum(1 for a, b in zip(order, order[1:], strict=False) if b < a)
    if rising == 0 or falling == 0 or min(rising, falling) < len(order) // 5:
        problems.append(f"the page order is monotonic in difficulty: {rising} rises, {falling} falls")

    if problems:
        raise SystemExit("the pack does not satisfy its own constraints: " + "; ".join(problems))


def indented(label: str, *, substitute: bool) -> str:
    """A row that shares its slot with an earlier one is indented, the way a printed boxscore sets it.

    ⚠️ **This used to decide by `"-" in label`, and that was the same defect this project spent a day
    closing, asleep.** Indentation is a property of the *lineup slot* — this man came into somebody
    else's place — and it was being derived from a formatting detail of the label. The two agreed by
    coincidence, and the moment the suffix was removed the cue vanished and every substitute drew as a
    starter. Deriving it from the slot removes the coincidence.
    """
    return f"  {label}" if substitute else label


def substitutes(slots: "Sequence[int]") -> list[bool]:
    """Which rows share a slot with a row above them. One source for the indent and the rule."""
    seen: set[int] = set()
    flags: list[bool] = []
    for slot in slots:
        flags.append(slot in seen)
        seen.add(slot)
    return flags


def board_table(board: Board, loaded: Loaded, *, solved: bool) -> Table:
    # ⚠️ Eight columns, not seven. The first carries the lineup slot, and it is the cell a footnote
    # reference points at: `SH: 9b` is useless if nothing on the board says `9b`. Its header is left
    # blank on purpose — no boxscore has a slot column, so any symbol there is our invention asking to
    # be interpreted, while `1, 2, 3...` in order explains itself.
    rows: list[list[str]] = [["", "", *BATTING_HEADS]]
    spans: list[tuple[str, tuple[int, int], tuple[int, int], object]] = []
    batting_team = "HOME" if loaded.offense_is_home else "AWAY"
    pitching_team = "AWAY" if loaded.offense_is_home else "HOME"

    rows.append([f"{batting_team} BATTING", *([""] * 7)])
    section_rows = [len(rows) - 1]
    sub = substitutes(loaded.slots)
    references = slot_references(loaded.slots)
    first_batting_row = len(rows)
    for index, line in enumerate(board.batting):
        rows.append(
            [
                references[index],
                indented(loaded.labels[index], substitute=sub[index]),
                *("" if value is None else str(value) for value in line),
            ]
        )
    # The rule between slots goes above the first row of each new slot, which is where a block starts.
    slot_rules = [first_batting_row + index for index, shared in enumerate(sub) if not shared and index]
    rows.append(["", "TOTALS", *("" if value is None else str(value) for value in board.batting_totals)])
    totals_rows = [len(rows) - 1]

    rows.append([f"{pitching_team} PITCHING", *([""] * 7)])
    section_rows.append(len(rows) - 1)
    rows.append(["", "", *PITCHING_HEADS])
    head_rows = [0, len(rows) - 1]
    for index, line in enumerate(board.pitching):
        label = loaded.pitcher_labels[index] if index < len(loaded.pitcher_labels) else f"P{index + 1}"
        cells = ["" if value is None else str(value) for value in line]
        if line[0] is not None:
            cells[0] = to_display(line[0])
        # The slot column is empty in the pitching section: those are the *opposing* team's pitchers
        # and they have no place in this batting order. Left blank deliberately rather than by
        # omission, since a stray number here would name a row that does not exist.
        rows.append(["", label, *cells])
    totals = ["" if value is None else str(value) for value in board.pitching_totals]
    if board.pitching_totals[0] is not None:
        totals[0] = to_display(board.pitching_totals[0])
    rows.append(["", "TOTALS", *totals])
    totals_rows.append(len(rows) - 1)

    del solved
    # Shorter rows on a tall board. Eight millimetres is still far more than a digit needs, and
    # the page has to carry the formula strip and the survey box as well as the grid.
    height = 7.4 * mm if len(rows) > 20 else 8.6 * mm
    # The slot column is taken out of the label column rather than added to the board: the label no
    # longer carries a suffix, so it needs less than it did, and the six data columns keep their width.
    table = Table(rows, colWidths=[8 * mm, 18 * mm, *([21 * mm] * 6)], rowHeights=height)
    style: list[tuple[object, ...]] = [
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("LEFTPADDING", (0, 0), (1, -1), 3),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        (
            "BACKGROUND",
            (0, first_batting_row),
            (0, first_batting_row + len(board.batting) - 1),
            colors.HexColor("#eeeeee"),
        ),
    ]
    for row in head_rows:
        style += [
            ("BACKGROUND", (0, row), (-1, row), colors.HexColor("#dddddd")),
            ("FONTNAME", (0, row), (-1, row), "Helvetica-Bold"),
        ]
    for row in section_rows:
        style += [
            ("BACKGROUND", (0, row), (-1, row), colors.HexColor("#333333")),
            ("TEXTCOLOR", (0, row), (-1, row), colors.white),
            ("FONTNAME", (0, row), (-1, row), "Helvetica-Bold"),
            ("FONTSIZE", (0, row), (-1, row), 8),
            ("ALIGN", (0, row), (-1, row), "LEFT"),
            ("SPAN", (0, row), (-1, row)),
        ]
    for row in totals_rows:
        style += [
            ("BACKGROUND", (0, row), (-1, row), colors.HexColor("#eeeeee")),
            ("FONTNAME", (0, row), (-1, row), "Helvetica-Bold"),
        ]
    style += [("LINEABOVE", (0, row), (-1, row), 1.1, colors.HexColor("#666666")) for row in slot_rules]
    table.setStyle(TableStyle(style + [tuple(span) for span in spans]))  # type: ignore[arg-type]
    return table


def line_score_table(loaded: Loaded) -> Table:
    score = loaded.direction.line_score
    innings = max(len(score.offense_by_inning), len(score.defense_by_inning))
    away, home = (
        (score.defense_by_inning, score.offense_by_inning)
        if loaded.offense_is_home
        else (score.offense_by_inning, score.defense_by_inning)
    )
    away_rhe, home_rhe = (
        (
            (score.defense_runs, score.defense_hits, score.defense_errors),
            (score.offense_runs, score.offense_hits, score.offense_errors),
        )
        if loaded.offense_is_home
        else (
            (score.offense_runs, score.offense_hits, score.offense_errors),
            (score.defense_runs, score.defense_hits, score.defense_errors),
        )
    )
    header = ["", *(str(index + 1) for index in range(innings)), "R", "H", "E"]
    rows = [header]
    for side, by_inning, rhe in (("AWAY", away, away_rhe), ("HOME", home, home_rhe)):
        cells = [str(by_inning[index]) if index < len(by_inning) else "x" for index in range(innings)]
        rows.append([side, *cells, *(str(value) for value in rhe)])
    table = Table(rows, colWidths=[14 * mm, *([9 * mm] * innings), 10 * mm, 10 * mm, 10 * mm], rowHeights=6 * mm)
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bbbbbb")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("LINEBEFORE", (innings + 1, 0), (innings + 1, -1), 1.0, colors.HexColor("#666666")),
            ]
        )
    )
    return table


def build_pdf(path: Path, chosen: list[Candidate], *, answers: bool) -> None:
    document = SimpleDocTemplate(
        str(path), pagesize=A4, topMargin=14 * mm, bottomMargin=12 * mm, leftMargin=16 * mm, rightMargin=16 * mm
    )
    reference = ParagraphStyle("reference", fontName="Helvetica-Bold", fontSize=11)
    footnotes = ParagraphStyle("footnotes", fontName="Helvetica", fontSize=8.5, spaceBefore=3)
    formulas = ParagraphStyle(
        "formulas",
        fontName="Helvetica",
        fontSize=7.0,
        leading=9,
        spaceBefore=2,
        textColor=colors.HexColor("#333333"),
    )
    story: list[object] = []
    for index, candidate in enumerate(chosen, start=1):
        # Nothing here names the game, the date, the teams, the target or the certification. All of
        # that is the key file, and a spoiler on the page would void the experiment.
        story.append(Paragraph(f"Board {index:02d}{' — solution' if answers else ''}", reference))
        story.append(Paragraph(FORMULAS, formulas))
        story.append(Spacer(1, 2 * mm))
        story.append(line_score_table(candidate.loaded))
        story.append(
            Paragraph(
                footnote_line(candidate.solution if answers else candidate.puzzle, candidate.loaded.slots),
                footnotes,
            )
        )
        story.append(Spacer(1, 2 * mm))
        story.append(board_table(candidate.solution if answers else candidate.puzzle, candidate.loaded, solved=answers))
        if not answers:
            story.append(Spacer(1, 3 * mm))
            story.append(survey_box())
        if index < len(chosen):
            story.append(PageBreak())
    document.build(story)


def write_key(path: Path, chosen: list[Candidate]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["board", "game_id", "season", "chain_target", "certified_by_3b", "substitution", "live_footnote"]
        )
        for index, candidate in enumerate(chosen, start=1):
            writer.writerow(
                [
                    f"{index:02d}",
                    candidate.loaded.game_id,
                    candidate.loaded.season,
                    candidate.target,
                    "yes" if candidate.certified else "NO",
                    "yes" if candidate.has_substitution else "",
                    "yes" if candidate.has_live_footnote else "",
                ]
            )


def write_sheet(path: Path, count: int) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["board", "solved", "minutes", "got_stuck_where", "underivable", "tedious", "boring", "notes"])
        for index in range(1, count + 1):
            writer.writerow([f"{index:02d}", "", "", "", "", "", "", ""])


def main() -> None:
    rng = random.Random(SEED)
    sample = load(SAMPLE_PER_DECADE, gated=True, gate=GATE, max_batters=13, max_pitchers=4)
    pool = candidates(sample)
    chosen = choose(pool, rng)
    audit(chosen)

    out = Path(__file__).resolve().parent
    build_pdf(out / "boards.pdf", chosen, answers=False)
    build_pdf(out / "solutions.pdf", chosen, answers=True)
    write_key(out / "key.csv", chosen)
    write_sheet(out / "recording-sheet.csv", len(chosen))

    uncertified = sum(1 for candidate in chosen if not candidate.certified)
    by_target: dict[int, int] = {}
    for candidate in chosen:
        by_target[candidate.target] = by_target.get(candidate.target, 0) + 1
    print(f"pool: {len(pool)} verified puzzles from {len(sample)} directions")
    print(f"chosen: {len(chosen)} boards, {uncertified} of them uncertified by layer 3b")
    print(f"by chain target: {dict(sorted(by_target.items()))}")
    print(f"pre-1950: {sum(1 for c in chosen if c.loaded.season < 1950)} (allowance {PRE_1950_ALLOWANCE})")
    print(f"with a substitution: {sum(1 for c in chosen if c.has_substitution)}")
    print(f"with a live footnote: {sum(1 for c in chosen if c.has_live_footnote)}")
    print(f"wrote {out / 'boards.pdf'}, solutions.pdf, key.csv, recording-sheet.csv")


if __name__ == "__main__":
    main()
