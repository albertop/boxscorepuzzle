/**
 * What happens when the player says they are done, and what they get for being right.
 *
 * ⚠️⚠️ **The board never says which cells are wrong, or how many.** Both were considered and both were
 * rejected in `serve-flow.md`, for reasons that are about the game rather than about taste:
 *
 *   - **Marking the wrong cells** makes probing beat deducing. A player who enters a guess and reads
 *     the marks is playing a better strategy than one who works it out, and the puzzle stops being a
 *     deduction puzzle the moment that is true.
 *   - **Counting them** is a binary search over the board. Fill half, check, halve again — the count
 *     hands the player an oracle that answers questions the boxscore never would.
 *
 * So there is one sentence for every wrong board, whatever is wrong with it, and it is a fact about
 * the whole: it does not balance. Nothing here may ever take a cell name.
 *
 * ⚠️ **The clock does not stop for a wrong answer, and attempts are unlimited.** §27 says there is no
 * fail state; what an error costs is time, and time is what gets measured and shared. A limit would
 * add a fail state through the back door, and stopping the clock would make errors free.
 */

import { text } from "../../engine/strings.js";
import { renderLineScore } from "./board.js";

/** `mm:ss`, or `h:mm:ss` past an hour. The first thing the player sees of a clock they never saw run. */
export function formatDuration(milliseconds) {
  const total = Math.max(0, Math.round(milliseconds / 1000));
  const seconds = String(total % 60).padStart(2, "0");
  const minutes = Math.floor(total / 60) % 60;
  const hours = Math.floor(total / 3600);
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${seconds}` : `${minutes}:${seconds}`;
}

/**
 * What a press of *Check* means, as a value rather than as a side effect.
 *
 * ⚠️ Separated from the drawing so the rule can be tested without a DOM, and so the one place that
 * decides *what the player is told* is one place. `state` is `incomplete`, `wrong` or `solved` — and
 * there is deliberately no fourth carrying detail.
 */
export function checkBoard(game) {
  const blanks = game.blanks();
  const empty = blanks.filter((name) => game.value(name) === null);
  if (empty.length > 0) return { state: "incomplete", message: text("done.incomplete") };
  if (!game.isSolved()) return { state: "wrong", message: text("done.not_yet") };
  return { state: "solved", message: "" };
}

/**
 * The official boxscore, drawn complete, with the names the player never saw during play.
 *
 * ⚠️ **This is the payoff, and it is the one thing the player has never received.** The `reveal` block
 * has shipped in every package since schema 2 and was drawn nowhere. §7 keeps names off the board
 * during play so nothing is handed over before it is earned; this is where it is earned.
 */
export function renderReveal(puzzle, record) {
  // ⚠️ **`snake_case`, because the reveal passes through the reader untouched.** `readPackage` maps
  // every other field into the client's own shape and deliberately does not map this one, so writing
  // `reveal.offenseTeam` here reads `undefined` and renders an empty heading -- with no error, on the
  // one screen nobody had ever seen. Checked against a real package rather than assumed.
  const reveal = puzzle.reveal;
  const panel = document.createElement("div");
  panel.className = "reveal";
  panel.setAttribute("role", "dialog");
  panel.setAttribute("aria-modal", "true");
  panel.setAttribute("aria-label", text("reveal.title"));

  const sheet = document.createElement("div");
  sheet.className = "reveal-sheet";
  panel.append(sheet);

  const title = document.createElement("h2");
  title.className = "reveal-title";
  title.textContent = text("reveal.title");
  sheet.append(title);

  // ⚠️ The clock, appearing for the first time. Invisible during play (§26) because a visible timer
  // changes how people play; shown here because it is what the comparison feature will compare.
  const time = document.createElement("p");
  time.className = "reveal-time";
  const label = document.createElement("span");
  label.className = "reveal-time-label";
  label.textContent = text("reveal.time");
  const figure = document.createElement("span");
  figure.className = "reveal-time-figure";
  figure.textContent = formatDuration(record.duration_ms);
  time.append(label, figure);
  sheet.append(time);

  if (record.errors > 0) {
    // ⚠️ Shown **after** the board is solved and never before. During play a count is a binary search;
    // afterwards there is nothing left to search, so it is a result rather than a clue.
    const errors = document.createElement("p");
    errors.className = "reveal-errors";
    const errorLabel = document.createElement("span");
    errorLabel.textContent = text("reveal.errors");
    const errorFigure = document.createElement("span");
    errorFigure.textContent = String(record.errors);
    errors.append(errorLabel, errorFigure);
    sheet.append(errors);
  }

  if (reveal) {
    const heading = document.createElement("p");
    heading.className = "reveal-game";
    // `AWAY vs HOME at DATE`, composed from the catalogue rather than written as a sentence, so a
    // language that orders it differently changes the strings and not this file.
    heading.textContent =
      `${reveal.offense_team} ${text("reveal.versus")} ${reveal.defense_team} ` +
      `${text("reveal.at")} ${reveal.played_on}`;
    sheet.append(heading);

    const score = document.createElement("div");
    score.className = "linescore";
    score.append(renderLineScore(puzzle.puzzle.lineScore, puzzle.offenseIsHome));
    sheet.append(score);

    sheet.append(nameList(reveal.batter_names, puzzle.labels, "reveal-batters"));
    sheet.append(nameList(reveal.pitcher_names, puzzle.pitcherLabels, "reveal-pitchers"));
  }

  const close = document.createElement("button");
  close.type = "button";
  close.className = "reveal-close";
  close.textContent = text("reveal.close");
  sheet.append(close);
  panel.dataset.close = "";
  close.addEventListener("click", () => panel.remove());

  return panel;
}

/**
 * The rows, with the position label the player solved against beside the name they have just earned.
 *
 * ⚠️ Both, not the name alone: the player spent the game thinking of that row as `CF`, and a list of
 * names with no labels is a list they cannot map onto the board they just filled.
 */
function nameList(names, labels, className) {
  const list = document.createElement("ul");
  list.className = className;
  names.forEach((name, index) => {
    const item = document.createElement("li");
    const slot = document.createElement("span");
    slot.className = "reveal-label";
    slot.textContent = labels[index] ?? "";
    const person = document.createElement("span");
    person.className = "reveal-name";
    person.textContent = name;
    item.append(slot, person);
    list.append(item);
  });
  return list;
}
