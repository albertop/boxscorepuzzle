/**
 * The phone shell: loads a package, wires selection and the keypad, redraws.
 *
 * ⚠️ **The engine does not know what day it is** (C4). This loader decides which puzzle, and for now it
 * reads the manifest and takes an id from the query string so every reference package can be looked at.
 * The real `/today` route is shell work and does not live here.
 */

import { battingCell, footnoteCell, pitchingCell, sectionOf } from "../../engine/columns.js";
import { createGame } from "../../engine/game.js";
import { PackageError, readPackage } from "../../engine/package.js";
import { text } from "../../engine/strings.js";
import {
  applyKey,
  columnsFor,
  isInningsCell,
  paint,
  renderFootnotes,
  renderKeypad,
  renderLineScore,
  renderSection,
  totalNameFor,
} from "./board.js";

const DATA = "../../data/puzzles";

/**
 * The manifest is a **pointer** and the packages are **immutable**, so they cache differently.
 *
 * ⚠️ **Found the moment the six were regenerated.** The generation directory changed, the manifest was
 * rewritten to name it — and the browser kept serving the old manifest, so the client loaded packages
 * from a retired generation and refused them as the wrong schema. The code was correct and the page was
 * wrong, which is the shape `docs/serve-brief.md` §6 already records once: a prototype reported as *not
 * rendering* that was the cache.
 *
 * A package at `<generation>/<id>.json` can never change — a new one gets a new generation — so it is
 * safe to cache hard. The manifest is the only thing that says which generation is current, and a stale
 * pointer is indistinguishable from a stale build. `no-store`, always.
 *
 * This is the read side of §33's rule that the calendar extends rather than rewrites, and of the
 * caching rule in CLAUDE.md: cache the day's puzzle, never the pointer to it.
 */
async function loadPuzzle() {
  const manifest = await (await fetch(`${DATA}/manifest.json`, { cache: "no-store" })).json();
  const wanted = new URLSearchParams(location.search).get("p");
  const id = manifest.puzzles.includes(wanted) ? wanted : manifest.puzzles[0];
  const raw = await (await fetch(`${DATA}/${manifest.generation}/${id}.json`)).json();
  return { puzzle: readPackage(raw), manifest, id };
}

function boot({ puzzle }) {
  const app = document.getElementById("app");
  app.replaceChildren();
  const game = createGame(puzzle);
  let selected = null;

  const score = document.createElement("div");
  score.className = "linescore";
  score.append(renderLineScore(puzzle.puzzle.lineScore, puzzle.offenseIsHome));
  app.append(score);

  const scroller = document.createElement("div");
  scroller.className = "scroller";
  app.append(scroller);

  let keypad = null;
  const select = (name) => {
    if (!game.isBlank(name)) return;
    selected = name;
    // The visible half of the same rule the handler enforces: the thirds keys apply to one kind of
    // cell, so they are only offered on that kind.
    keypad?.allowThirds(isInningsCell(name));
    for (const node of scroller.querySelectorAll(".cell")) {
      const isSelected = node.dataset.cell === name;
      node.classList.toggle("selected", isSelected);
      // The amber says *this one* to the eye; `aria-pressed` says it to everything else. A state that
      // only one of them can read is a state half the players cannot see.
      if (node.hasAttribute("aria-pressed")) node.setAttribute("aria-pressed", isSelected ? "true" : "false");
      // The row and column a selected cell shares an equation with. Shown because a deduction is
      // always about a line, and finding it by eye on a 44px grid is the tedious part.
      const other = node.dataset.cell !== name;
      const sameRow = node.dataset.cell.split(".")[0] === name.split(".")[0];
      // ⚠️ **Same column *within the same block*.** `hits` names a batting column and a pitching column,
      // so comparing the column alone lit the pitching grid from a batting selection — two grids that
      // share a word and no equation. The offence's hits and what the opposing staff allowed are
      // related, but by the cross-team identity, not by being one column.
      const sameColumn =
        node.dataset.cell.split(".")[1] === name.split(".")[1] &&
        sectionOf(node.dataset.cell) === sectionOf(name);
      // ⚠️ **The footnote line takes the amber and nothing else.** The highlight answers *which cells
      // does this one share an equation with*, and it answers it by lying along a row or a column — a
      // shape the grid has and the line does not. Tinting `#5a` and `#5b` because they share a column
      // showed a relation the line's own layout does not express, so the cue said something the eye
      // could not follow. Selected, yes; related, not here.
      const inLine = node.closest(".footnotes") !== null;
      node.classList.toggle("peer", !inLine && other && (sameRow || sameColumn));
    }
  };

  const draw = () => {
    scroller.replaceChildren();
    scroller.append(
      renderSection({
        // The same two keys the scoreboard uses, so one name cannot be spelled two ways on one screen.
        title: `${text(puzzle.offenseIsHome ? "side.home" : "side.away")} ${text("board.batting")}`,
        columns: columnsFor.batting,
        rows: puzzle.puzzle.batting,
        labels: puzzle.labels,
        slots: puzzle.slotReferences,
        cellName: battingCell,
        totalName: totalNameFor.batting,
        game,
        onSelect: select,
      }),
    );
    scroller.append(renderFootnotes(puzzle, game));
    scroller.append(
      renderSection({
        // The other side, always: the board is one team batting against the other's staff.
        title: `${text(puzzle.offenseIsHome ? "side.away" : "side.home")} ${text("board.pitching")}`,
        columns: columnsFor.pitching,
        rows: puzzle.puzzle.pitching,
        labels: puzzle.pitcherLabels,
        slots: null,
        cellName: pitchingCell,
        totalName: totalNameFor.pitching,
        game,
        onSelect: select,
      }),
    );
    if (selected) select(selected);
  };

  const repaint = () => {
    for (const node of scroller.querySelectorAll(".cell")) paint(node, game);
    const footnotes = scroller.querySelector(".footnotes");
    footnotes.replaceWith(renderFootnotes(puzzle, game));
  };

  keypad = renderKeypad((key) => {
    if (!selected) return;
    applyKey(game, selected, key);
    repaint();
  });
  app.append(keypad);

  draw();
  globalThis.__game = game;
  globalThis.__puzzle = puzzle;
}

try {
  boot(await loadPuzzle());
} catch (error) {
  const app = document.getElementById("app");
  app.replaceChildren();
  const message = document.createElement("p");
  message.style.padding = "1rem";
  // The player sees the catalogued sentence; the console keeps what actually went wrong.
  message.textContent = text("package.unreadable");
  app.append(message);
  if (error instanceof PackageError) console.error("package refused:", error.message);
  else throw error;
}
