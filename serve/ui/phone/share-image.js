/**
 * The share image: the real board, with the player's answers replaced, drawn to a PNG.
 *
 * **`docs/serve-flow.md` §7b decides what it contains and `share.js` decides what it hides.** This file
 * is only the part that turns a laid-out board into a file a messaging app will accept.
 *
 * ⚠️⚠️ **Drawn with the board's own renderers, never a second one.** `renderLineScore`,
 * `renderSection` and `renderFootnotes` build the node; the only difference from the live board is the
 * game they are given, which is `maskAnswers()`'s facade. This project's standing rule is that a
 * variant is a **parameter of the real renderer** — a comparison page that drew its own grid twice
 * showed something other than what it was evaluating, and the judgement would have been made on a
 * board that does not exist. `landing.js` draws its example the same way.
 *
 * ⚠️⚠️ **Everything the picture depends on is inlined, and that is the whole difficulty.** An `<img>`
 * pointed at an SVG is a **separate document**: it cannot reach the page's stylesheets, cannot reach
 * `/ui/fonts/`, and does not inherit a single computed value. So the three sheets are fetched and
 * embedded, and the three woff2 faces are embedded as data URIs inside them.
 *
 * **If the fonts were left out the image would still be produced** — in whatever face the renderer
 * falls back to, with different metrics, different column widths and a board that no longer reads as a
 * boxscore. It would look like a working share until somebody opened one on a phone. That is this
 * project's recorded shape of an instrument supplying the property under test, so `embedFonts` refuses
 * rather than degrading.
 */

import { maskAnswers } from "../../engine/share.js";
import { text } from "../../engine/strings.js";
import { battingCell, pitchingCell } from "../../engine/columns.js";
import { columnsFor, renderFootnotes, renderLineScore, renderSection, totalNameFor } from "./board.js";
import { formatDuration } from "./finish.js";

const SHEETS = ["/ui/phone/fonts.css", "/ui/phone/tokens.css", "/ui/phone/board.css"];

const FONTS = [
  "/ui/fonts/plex-condensed-400.woff2",
  "/ui/fonts/plex-condensed-600.woff2",
  "/ui/fonts/plex-condensed-700.woff2",
];

/**
 * How wide the drawn board is, in CSS pixels, before the scale below.
 *
 * ⚠️ **375, which is §6's phone.** The board's column budget was measured against it and every width
 * in `board.css` is written for it; rendering the share at some other width would be rendering a
 * layout nobody has looked at. The image is not a screenshot of the player's phone — it is the board
 * at the width the board was designed for.
 */
const WIDTH = 375;

/**
 * ⚠️ **Two device pixels per CSS pixel.** A share arrives on a phone at whatever size the messaging app
 * chooses, and every one of them re-encodes it: a 1× image is resampled to something soft, and digits
 * at this size are exactly what softness destroys. Above 2× the file grows faster than the legibility
 * does, and WhatsApp re-compresses past the difference anyway (G3.1).
 */
const SCALE = 2;

/**
 * The blur, in CSS pixels at 1×.
 *
 * ⚠️⚠️ **This is typography, not security** (`serve-flow.md` §7b). The values under it are already
 * random, so the blur is not hiding anything — it makes the image read as a finished boxscore at a
 * glance rather than as a wall of arbitrary numbers, and it says *these were mine* against *these were
 * given*. **If it were removed the design would still be safe and would simply look wrong.**
 */
const BLUR = 2.2;

/**
 * Build the board node for the image, from the real renderers and a masked game.
 *
 * Visitor first, batting then footnotes then pitching — the same order and the same two heading keys
 * `shell.js` uses, so one name cannot be spelled two ways across the product.
 */
function boardNode(puzzle, game) {
  const board = document.createElement("div");
  board.className = "share-board";
  board.append(renderLineScore(puzzle.puzzle.lineScore, puzzle.offenseIsHome));
  board.append(
    renderSection({
      title: `${text(puzzle.offenseIsHome ? "side.home" : "side.away")} ${text("board.batting")}`,
      columns: columnsFor.batting,
      rows: puzzle.puzzle.batting,
      labels: puzzle.labels,
      slots: puzzle.slotReferences,
      // ⚠️⚠️ **The real name builders, imported rather than spelled.** A second definition of a
      // cell's name would produce a board whose cells the game does not recognise, and it would render
      // -- blank, in the right shape, with no error anywhere.
      cellName: battingCell,
      totalName: totalNameFor.batting,
      game,
      // ⚠️ Null, so `renderSection` draws cells that are not controls at all — no listener, no tab
      // stop, no `role="button"`. A picture has no interaction to offer and an image carrying the
      // markup of one would be a lie about the artefact.
      onSelect: null,
    }),
  );
  board.append(renderFootnotes(puzzle, game));
  board.append(
    renderSection({
      title: `${text(puzzle.offenseIsHome ? "side.away" : "side.home")} ${text("board.pitching")}`,
      columns: columnsFor.pitching,
      rows: puzzle.puzzle.pitching,
      labels: puzzle.pitcherLabels,
      slots: null,
      cellName: pitchingCell,
      totalName: totalNameFor.pitching,
      game,
      onSelect: null,
    }),
  );
  board.append(resultLine(game));
  return board;
}

/**
 * The line under the board: the time, the tries and the hints.
 *
 * ⚠️⚠️ **The same catalogue keys as the reveal** (G1.3). One number must not have two names in the
 * artefact whose entire purpose is comparison — a player whose reveal says *Checks failed* and whose
 * share says something else has two numbers where they have one.
 *
 * ⚠️ All three travel or none of them means anything. §26's comparison rests on the trio: *a time
 * reached on the first attempt and the same time reached after fifteen is two different results*, and
 * a hint does not corrupt a shared result **if it is shared alongside the time**.
 */
function resultLine(game) {
  const line = document.createElement("p");
  line.className = "share-result";
  const record = game.record();
  const parts = [
    [text("reveal.time"), formatDuration(record.duration_ms)],
    [text("reveal.tries"), String(record.failed_checks)],
    [text("reveal.hints"), record.hints === 0 ? text("reveal.no_hints") : String(record.hints)],
  ];
  for (const [label, value] of parts) {
    const item = document.createElement("span");
    item.className = "share-result-item";
    const name = document.createElement("span");
    name.className = "share-result-label";
    name.textContent = label;
    const figure = document.createElement("span");
    figure.className = "share-result-value";
    figure.textContent = value;
    item.append(name, figure);
    line.append(item);
  }
  return line;
}

/** The three sheets, concatenated, with the faces embedded. */
async function inlinedCss() {
  const sheets = await Promise.all(SHEETS.map(async (href) => (await fetchOrRaise(href)).text()));
  return embedFonts(sheets.join("\n")) ;
}

async function fetchOrRaise(url) {
  const response = await fetch(url);
  if (!response.ok) {
    // ⚠️ Named rather than swallowed. A share that silently produced an unstyled image would look like
    // a working feature to everything except a person holding a phone.
    throw new Error(`share image: ${url} answered ${response.status}`);
  }
  return response;
}

/**
 * Replace every `url(...)` pointing at a face with the face itself, base64.
 *
 * ⚠️⚠️ **Refuses when a face is missing rather than producing an image in a fallback typeface.** The
 * board's column widths are metric-dependent; the wrong face is a board that no longer lines up, and
 * it is *invisible* to every check short of looking at the result. An error here is a share that did
 * not happen, which the player sees at once.
 */
async function embedFonts(css) {
  let embedded = css;
  for (const path of FONTS) {
    const bytes = new Uint8Array(await (await fetchOrRaise(path)).arrayBuffer());
    let binary = "";
    for (const byte of bytes) binary += String.fromCharCode(byte);
    const uri = `data:font/woff2;base64,${btoa(binary)}`;
    // The sheets name the faces relatively (`../fonts/x.woff2`); match on the file name so the same
    // replacement works whatever the sheet writes in front of it.
    const file = path.slice(path.lastIndexOf("/") + 1);
    const pattern = new RegExp(`url\\((['"]?)[^'")]*${file.replace(/\./g, "\\.")}\\1\\)`, "g");
    if (!pattern.test(embedded)) {
      throw new Error(`share image: ${file} is not referenced by any sheet, so nothing would embed it`);
    }
    embedded = embedded.replace(pattern, `url(${uri})`);
  }
  return embedded;
}

/**
 * Stylesheet text, wrapped so the SVG parser cannot read it as markup.
 *
 * ⚠️⚠️ **Without this, one `<` in a CSS COMMENT kills the share.** The sheets are concatenated into a
 * `<style>` inside a `foreignObject`, and that document is parsed as XML: a bare `<` ends the element
 * early and the whole SVG is refused. `rasterise` then reports *the SVG did not load* with no idea why.
 *
 * **It happened.** Comments reading ``a `<button>` centres its label`` and ``an `<a>` and a `<button>`
 * in one rule`` were written into `board.css` and `landing.css`, and **both share buttons stopped
 * working in production** -- the only growth mechanism the product has, broken by prose. It is the
 * favicon defect exactly: a comment invalidating the document it explains.
 *
 * ⚠️ **CDATA rather than escaping or stripping comments.** Escaping means knowing every character that
 * matters; stripping comments means a parser for CSS and would still miss `<` in a `content:` value.
 * CDATA says *none of this is markup*, which is the actual claim.
 *
 * ⚠️ `]]>` is the one sequence CDATA cannot hold, so it is split across two sections -- the standard
 * form, and it always works. **Not a refusal**: a share that fails is worse than one that costs six
 * characters, and this cannot produce a wrong image, only a valid one.
 */
const cdata = (text) => `<![CDATA[${text.replaceAll("]]>", "]]]]><![CDATA[>")}]]>`;

/**
 * What the image adds on top of the board's own styles.
 *
 * ⚠️ `.cell.filled` is the blur's target and `.given` is deliberately untouched: `paint()` sets exactly
 * those two classes, so the distinction the image draws is the distinction the board already made
 * rather than a second definition of *the player put this here*.
 */
const SHARE_CSS = `
  .share-sheet { width: ${WIDTH}px; background: var(--surface); color: var(--ink);
                 padding: 12px 10px 14px; box-sizing: border-box; }
  .share-board .cell.filled { filter: blur(${BLUR}px); }
  .share-result { display: flex; gap: 14px; justify-content: center; align-items: baseline;
                  margin: 12px 0 0; padding: 10px 0 0; border-top: 1px solid var(--rule); }
  .share-result-item { display: flex; gap: 5px; align-items: baseline; }
  .share-result-label { font-size: 12px; opacity: 0.72; }
  .share-result-value { font-size: 15px; font-weight: 700; font-variant-numeric: tabular-nums; }
`;

/**
 * The board, as a PNG blob.
 *
 * ⚠️⚠️ **Laid out in the real document before it is serialised.** An SVG `foreignObject` does not lay
 * anything out on its own — the height has to be measured, and measuring means the node has to be in a
 * document with the stylesheets applied. It is placed off-screen rather than hidden: `display: none`
 * has no box and would measure zero, which is the kind of failure that produces a valid, empty image.
 */
export async function shareImage(puzzle, game, { random } = {}) {
  const sheet = document.createElement("div");
  sheet.className = "share-sheet";
  sheet.append(boardNode(puzzle, maskAnswers(game, random)));

  const stage = document.createElement("div");
  // Off the screen and still laid out. `left: -10000px` rather than `visibility: hidden` for the same
  // reason as above: everything that has no box measures nothing.
  stage.style.cssText = "position:absolute; left:-10000px; top:0; width:" + WIDTH + "px;";
  // ⚠️ The image's own rules go into the page too, so the measurement below happens under the same
  // stylesheet the SVG renders under. One constant, applied in both places.
  const rules = document.createElement("style");
  rules.textContent = SHARE_CSS;
  stage.append(rules, sheet);
  document.body.append(stage);

  try {
    const height = Math.ceil(sheet.getBoundingClientRect().height);
    if (height < 1) {
      throw new Error("share image: the board measured zero high, so nothing was laid out");
    }
    const css = await inlinedCss();
    const markup = new XMLSerializer().serializeToString(sheet);
    const svg =
      `<svg xmlns="http://www.w3.org/2000/svg" width="${WIDTH}" height="${height}" ` +
      `viewBox="0 0 ${WIDTH} ${height}">` +
      `<foreignObject width="100%" height="100%">` +
      `<div xmlns="http://www.w3.org/1999/xhtml"><style>${cdata(css + SHARE_CSS)}</style>${markup}</div>` +
      `</foreignObject></svg>`;
    return await rasterise(svg, WIDTH, height);
  } finally {
    stage.remove();
  }
}

/**
 * SVG text to a PNG blob.
 *
 * ⚠️⚠️ **A data URI, and a blob URL is not an option here — this is a browser rule, not a preference.**
 * Chromium **taints the canvas** when it draws an SVG that contains a `foreignObject` and was loaded
 * from a `blob:` URL, so `toBlob` then throws `SecurityError` and no image exists. The same SVG loaded
 * from a `data:` URI is clean. Measured on this project's own runner:
 *
 *     plain svg  + blob  CLEAN     foreignObject + blob  TAINTED: SecurityError
 *     plain svg  + data  CLEAN     foreignObject + data  CLEAN
 *
 * **The first version of this used a blob URL** for the honest reason that the markup is a hundred
 * kilobytes and `encodeURIComponent` over it is neither small nor fast. That reasoning was right about
 * the cost and irrelevant: the cheaper form produces nothing at all.
 *
 * ⚠️ **So do not "optimise" this back to a blob.** It will look like a size win, it will pass a review,
 * and it will fail at the moment a player presses Share.
 */
async function rasterise(svg, width, height) {
  const url = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
  const image = new Image();
  image.decoding = "sync";
  await new Promise((resolve, reject) => {
    image.addEventListener("load", resolve, { once: true });
    // ⚠️ The event carries no reason, so the message says what failed rather than pretending to know
    // why. The usual cause is markup the serialiser produced that the SVG parser refuses.
    image.addEventListener("error", () => reject(new Error("share image: the SVG did not load")), { once: true });
    image.src = url;
  });
  const canvas = document.createElement("canvas");
  canvas.width = width * SCALE;
  canvas.height = height * SCALE;
  const context = canvas.getContext("2d");
  context.scale(SCALE, SCALE);
  context.drawImage(image, 0, 0);
  return await new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("share image: the canvas produced nothing"))),
      "image/png",
    );
  });
}
