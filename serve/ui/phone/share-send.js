/**
 * Getting the image off the device. **`navigator.share` where it exists, the clipboard where it does
 * not** (`docs/beta-0-plan.md` G2).
 *
 * ⚠️⚠️ **Any friction here is friction on the only growth mechanism the product has.** So there is one
 * press and no dialogue of the product's own: the platform's own sheet is what the player already knows
 * how to dismiss, and a custom "how would you like to share?" step in front of it would be a second
 * decision imposed before the first one.
 *
 * ⚠️⚠️ **Neither path can tell you the share was delivered, and that is why this returns a channel
 * rather than a verdict.** `navigator.share` resolves when the sheet closes — on some platforms
 * whether or not anything was sent — and a clipboard write says nothing about whether it was ever
 * pasted. What the caller records is *the player pressed Share and this mechanism responded*, which
 * `keep-api.md` states beside the column so nobody reads the figure as reach.
 */

import { fill, text } from "../../engine/strings.js";

/**
 * Where the share points. **The image says what was done; this says where to go and do it.**
 *
 * ⚠️ **The site, never `/p/<id>`.** A recipient handed today's board goes straight to a puzzle they
 * have not been introduced to — §7's landing page and the tutorial exist for exactly that visitor, and
 * `serve-flow.md` records that every visit lands there. A share that skips it markets the game to
 * somebody who bounces off it.
 */
const DESTINATION = () => new URL("/", location.href).href;

/**
 * Send it, and say which way it went.
 *
 * ⚠️⚠️ **`canShare` with the file, not `share` alone.** Every mobile browser has `navigator.share`;
 * far fewer accept a `files` payload, and the ones that do not **reject after the sheet has already
 * opened** — the player sees the platform sheet, picks an app, and nothing arrives. Asking first is the
 * difference between a fallback and a failure the player watches happen.
 *
 * ⚠️ **A cancelled sheet is not an error.** `AbortError` is the player changing their mind, and it must
 * not reach the error queue or surface as a failure: the mechanism worked, and this returns `native`
 * because that is what it is measuring.
 *
 * ⚠️ **`elapsed` is required and has no default.** A default would be a share going out with somebody
 * else's time in it, or with an empty one — and the caller always has the record, so there is no case
 * where a sensible default exists.
 *
 * @returns {Promise<"native" | "clipboard">}
 */
/**
 * A 1x1 transparent PNG, as bytes. **Only ever used to ask `canShare` a question.**
 *
 * ⚠️ It never reaches a share sheet or a clipboard: the branch that shares awaits the real image and
 * hands that over. This exists because the question has to be asked before the answer can be built.
 */
const PROBE_PNG = Uint8Array.from(
  atob(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk" +
      "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
  ),
  (character) => character.charCodeAt(0),
);

export async function sendShare(image, elapsed, { navigatorRef = navigator, clipboardRef = navigator.clipboard } = {}) {
  // ⚠️⚠️ **`image` is a PROMISE and that is the whole of v42-P2-03.** It used to be a resolved `File`,
  // and `shareResult` awaited the rasteriser before calling this -- three stylesheets, three fonts, an
  // SVG serialise and a canvas. **The clipboard write then began several tasks after the click**, and a
  // browser that gates image writes on transient activation refuses it. The player pressed Share, waited
  // for the image, and got nothing: the handler is `async` so there is no failure state on screen, the
  // button simply came back.
  //
  // ⚠️ **The comment below already said to hand `ClipboardItem` a promise, and the code handed it a
  // blob.** A comment asserting a property nothing establishes, in the file whose whole job is that
  // property. It is the shape `CLAUDE.md` records for the Dockerfile that claimed a uid owned a volume.
  //
  // ⚠️ **The native branch still awaits, and that is correct rather than an oversight.** `canShare({files})`
  // has to be given a file to answer at all, and the share sheet is opened by the browser rather than
  // written to a gated surface -- it survives the await on every platform this ships to. **Only the
  // clipboard is activation-gated**, so only the clipboard needs the promise form.
  // ⚠️⚠️ **A real one-pixel PNG, and an EMPTY file here was a regression.** `canShare({files})` is asked
  // before the image exists, so it has to be asked about *something* -- and the first version handed it
  // a zero-byte `File`. Implementations differ on that: some answer about the type alone, others refuse
  // an empty payload, and a browser that refuses would send a phone that CAN open a share sheet down the
  // clipboard path instead. **The share is the only growth mechanism the product has**, so the probe is
  // now a valid PNG: 67 bytes, correct magic number, nothing to disagree about.
  const probe = new File([PROBE_PNG], "boxscorepuzzle.png", { type: "image/png" });
  if (navigatorRef?.canShare?.({ files: [probe] }) && navigatorRef.share) {
    const file = await image;
    const payload = { files: [file], text: fill("share.text", { time: elapsed }), url: DESTINATION() };
    try {
      await navigatorRef.share(payload);
    } catch (refused) {
      // ⚠️ Swallowed **by name**, not by a bare catch. Anything that is not the player dismissing the
      // sheet is a real fault and belongs in the error queue like every other one.
      if (refused?.name !== "AbortError") throw refused;
    }
    return "native";
  }
  // ⚠️ Not awaited before this call. `copyToClipboard` starts the write in this turn and awaits inside.
  await copyToClipboard(image, clipboardRef);
  return "clipboard";
}

/**
 * The fallback: the image on the clipboard.
 *
 * ⚠️⚠️ **The image, not a link.** A text-only fallback is a different artefact — `serve-flow.md` §7b
 * rejects the text line outright: *it carries a time and a verdict and no evidence of a board, so it
 * markets nothing.* Falling back to one would mean the desktop share and the phone share are two
 * different products, and only one of them is the one that was designed.
 *
 * ⚠️ **`ClipboardItem` takes the blob directly and the promise form is deliberate.** Safari discards a
 * clipboard write that is not begun in the same turn as the user gesture; handing it the promise rather
 * than the resolved blob is what keeps the write inside that turn.
 */
async function copyToClipboard(image, clipboardRef) {
  if (!clipboardRef?.write || typeof ClipboardItem === "undefined") {
    throw new Error("share: neither a share sheet nor an image clipboard is available");
  }
  // ⚠️⚠️ **`write` is CALLED here, synchronously, and awaited afterwards.** That ordering is the fix:
  // the browser sees the write begin in the same task as the click, and resolves the promise inside
  // `ClipboardItem` afterwards. Awaiting the image first and then calling `write` is the defect, and the
  // two read almost identically.
  const written = clipboardRef.write([new ClipboardItem({ "image/png": image })]);
  await written;
}
