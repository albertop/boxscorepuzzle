/**
 * Who this browser is, as far as the event record is concerned.
 *
 * ⚠️⚠️ **Its cost is asymmetric, which is why it comes before anything larger.** C7 stores events and is
 * irreversible: **every event recorded before this exists is unattributable**, and no later work
 * recovers it. Nothing about the game depends on it, so it would be easy to defer — and deferring it is
 * the one choice that loses something permanently.
 *
 * ⚠️ **Its own key and its own lifetime.** The per-puzzle session lives under
 * `boxscorepuzzle.session.v1.<id>` and is disposable — cleared when a puzzle is finished with, rewritten
 * on every entry. A device identity inside it would be thrown away with the board it happened to sit in.
 *
 * §35: **a random UUID and nothing else.** Not a fingerprint, not an IP, not anything derived from the
 * machine — an opaque value this browser made up about itself, which is what makes GDPR deletion a
 * matter of breaking one link rather than hunting through rows.
 */

export const DEVICE_KEY = "boxscorepuzzle.device.v1";

/**
 * This browser's device id, creating one the first time.
 *
 * ⚠️ **A storage that refuses returns a fresh id every call, and the game still plays** (§23). The
 * fallback in `browserStorage()` accepts everything and remembers nothing, so a private window or a
 * blocked origin plays anonymously rather than not at all. **The events from such a device look like a
 * new device each time**, which is the honest outcome: there is nothing to tie them to.
 *
 * @param {Storage} storage the same object `createStore` is given.
 * @returns {string} a UUID, stable for as long as the storage keeps it.
 */
export function deviceId(storage) {
  const held = storage.getItem(DEVICE_KEY);
  if (held) return held;

  const made = newId();
  storage.setItem(DEVICE_KEY, made);
  // ⚠️ Read back rather than returned directly. A storage that accepts and forgets — the refused-storage
  // fallback, or a quota that silently drops — would otherwise have this function *claim* an id it did
  // not keep, and the next call would return a different one while this one insisted it was stored.
  return storage.getItem(DEVICE_KEY) || made;
}

/**
 * A random UUID, from the platform where there is one.
 *
 * ⚠️ `crypto.randomUUID` is not everywhere: it needs a secure context, so `http://` on a phone over the
 * local network — which is how this board gets looked at during development — does not have it. The
 * fallback is `getRandomValues`, and only if that is missing too does this fall back to `Math.random`.
 *
 * ⚠️⚠️ **The last fallback is not cryptographic and does not need to be.** This id is not a secret and
 * guessing one buys nothing: it names a device to a counter, it authorises nothing, and §35 keeps
 * anything worth stealing out of the row it points at. What it must be is *unlikely to collide*, and
 * 122 bits of `Math.random` is far past that for a beta with tens of devices.
 */
function newId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();

  const bytes = new Uint8Array(16);
  if (globalThis.crypto?.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) bytes[index] = Math.floor(Math.random() * 256);
  }
  // Version 4, variant 1 — the shape a UUID is expected to have, so nothing downstream has to special-case
  // ids this browser made.
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/**
 * `2026-08-22` for a Date, in the **player's** zone.
 *
 * ⚠️⚠️ **Not `toISOString()`, and this is where data is lost rather than merely wrong.** That returns
 * UTC: somebody in California playing at eleven at night is recorded as having played the following
 * day. **Every question about when people play is then unanswerable**, and it is as irrecoverable as
 * the date itself — the information is gone the moment the row is written, not reconstructable from it.
 *
 * ⚠️ The *calendar* date is a different thing and uses a different clock: **the system's**. August 22nd's
 * puzzle is August 22nd's for everyone, everywhere. The two dates on an event answer two questions —
 * *which puzzle* and *when did this person sit down* — and they must not share a clock.
 */
export function localDate(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}
