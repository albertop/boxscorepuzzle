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

import { text } from "../../engine/strings.js";

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
 * @returns {Promise<"native" | "clipboard">}
 */
export async function sendShare(file, { navigatorRef = navigator, clipboardRef = navigator.clipboard } = {}) {
  const payload = { files: [file], text: text("share.text"), url: DESTINATION() };
  if (navigatorRef?.canShare?.({ files: [file] }) && navigatorRef.share) {
    try {
      await navigatorRef.share(payload);
    } catch (refused) {
      // ⚠️ Swallowed **by name**, not by a bare catch. Anything that is not the player dismissing the
      // sheet is a real fault and belongs in the error queue like every other one.
      if (refused?.name !== "AbortError") throw refused;
    }
    return "native";
  }
  await copyToClipboard(file, clipboardRef);
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
async function copyToClipboard(file, clipboardRef) {
  if (!clipboardRef?.write || typeof ClipboardItem === "undefined") {
    throw new Error("share: neither a share sheet nor an image clipboard is available");
  }
  await clipboardRef.write([new ClipboardItem({ "image/png": file })]);
}
