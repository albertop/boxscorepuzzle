/**
 * What *Share* does, for every surface that offers it.
 *
 * ⚠️⚠️ **One function because there is one act, and it lived in a closure until the landing page needed
 * it too.** `shell.js` built the image, sent it and queued the record inside `createShell`, closed over
 * four of its arguments. The moment a second screen offers Share, that shape forces a choice between
 * exporting the shell's insides and writing the sequence twice — and the second one is this project's
 * own failure mode, *two places that should say the same thing*. A share from the landing and a share
 * from the reveal must produce the same image, the same sentence and the same row.
 *
 * ⚠️⚠️ **The record is queued whatever the sheet does, and the order is deliberate.** `navigator.share`
 * rejects when the player cancels, and on some platforms resolves whether or not anything was sent — so
 * waiting for it to resolve before recording would drop shares on the platforms that lie and record
 * fewer than happened on the ones that do not. What is being measured is **intent**: the player pressed
 * Share and the mechanism responded. `docs/keep-api.md` says so beside the column.
 *
 * ⚠️ **The image is built before either path is taken**, because both need it and a failure to build one
 * must not present as a cancelled share.
 *
 * ⚠️ **`game` is separate from `record` and is not derivable from it.** The image is drawn from the
 * board — the real cells, masked — and the record carries a duration and an id. A share needs both.
 */

import { eventId } from "../../engine/outbox.js";
import { shareRecord } from "../../engine/share.js";
import { formatDuration } from "./finish.js";
import { sendShare } from "./share-send.js";
import { shareImage } from "./share-image.js";

export async function shareResult({
  puzzle,
  game,
  record,
  shares = null,
  device = null,
  outbox = null,
  send = sendShare,
  draw = shareImage,
}) {
  const image = await draw(puzzle, game);
  const file = new File([image], "boxscorepuzzle.png", { type: "image/png" });
  // ⚠️ The same `formatDuration` the reveal and the image use. One result must not have three numbers,
  // and the sentence beside the image is where a mismatch would be most visible.
  const channel = await send(file, formatDuration(record.duration_ms));
  // ⚠️ `event_id` is the game's own id when there is a queue and null when there is not — present and
  // null, never absent, which is what `keep` refuses by name.
  shares?.add(
    shareRecord({
      deviceId: device,
      puzzleId: record.puzzle_id,
      eventId: outbox ? eventId(record) : null,
      channel,
      at: record.played_on ?? null,
    }),
  );
  return channel;
}
