/**
 * The phone shell: loads a package, wires selection and the keypad, redraws.
 *
 * ⚠️ **The engine does not know what day it is** (C4). This loader decides which puzzle, and for now it
 * reads the manifest and takes an id from the query string so every reference package can be looked at.
 * The real `/today` route is shell work and does not live here.
 */

import { battingCell, footnoteCell, pitchingCell } from "../../engine/columns.js";
import { createGame } from "../../engine/game.js";
import { PackageError, readPackage } from "../../engine/package.js";
import { text } from "../../engine/strings.js";
import {
  columnsFor,
  paint,
  renderFootnotes,
  renderKeypad,
  renderLineScore,
  renderSection,
  totalNameFor,
} from "./board.js";

const DATA = "../../data/puzzles";

async function loadPuzzle() {
  const manifest = await (await fetch(`${DATA}/manifest.json`)).json();
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
  score.append(renderLineScore(puzzle.puzzle.lineScore));
  app.append(score);

  const scroller = document.createElement("div");
  scroller.className = "scroller";
  app.append(scroller);

  const select = (name) => {
    if (!game.isBlank(name)) return;
    selected = name;
    for (const node of scroller.querySelectorAll("td.cell")) {
      node.classList.toggle("selected", node.dataset.cell === name);
      // The row and column a selected cell shares an equation with. Shown because a deduction is
      // always about a line, and finding it by eye on a 44px grid is the tedious part.
      const sameRow = node.dataset.cell.split(".")[0] === name.split(".")[0];
      const sameColumn = node.dataset.cell.split(".")[1] === name.split(".")[1];
      node.classList.toggle("peer", node.dataset.cell !== name && (sameRow || sameColumn));
    }
  };

  const draw = () => {
    scroller.replaceChildren();
    scroller.append(
      renderSection({
        title: text("board.batting"),
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
        title: text("board.pitching"),
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
    for (const node of scroller.querySelectorAll("td.cell")) paint(node, game);
    const footnotes = scroller.querySelector(".footnotes");
    footnotes.replaceWith(renderFootnotes(puzzle, game));
  };

  app.append(
    renderKeypad((key) => {
      if (!selected) return;
      const innings = selected.startsWith("pitching") && selected.endsWith(".outs");
      if (key.clear) game.enter(selected, null);
      else if (key.thirds !== undefined) {
        // ⚠️ Innings are entered as whole innings then a third, the way they are written. The thirds
        // keys adjust the current entry rather than appending a digit, because `6` then `⅓` is `6.1`
        // and not sixty-one.
        const current = game.value(selected) ?? 0;
        game.enter(selected, Math.floor(current / 3) * 3 + key.thirds);
      } else if (innings) {
        const current = game.value(selected) ?? 0;
        const whole = Number(`${Math.floor(current / 3)}${key.digit}`);
        game.enter(selected, whole * 3 + (current % 3));
      } else {
        const current = game.value(selected);
        const grown = current === null ? key.digit : Number(`${current}${key.digit}`);
        game.enter(selected, grown > 99 ? key.digit : grown);
      }
      repaint();
    }),
  );

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
