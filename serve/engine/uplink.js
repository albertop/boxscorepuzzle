/**
 * Everything the client sends anywhere, wired up once.
 *
 * ⚠️⚠️ **In the engine rather than in `ui/phone/`, because there are three interfaces coming.** Tablet
 * and desktop would each have had to remember to build a device id, two queues and an error watcher over
 * *one* storage object — and a rule every interface has to remember is one the third will forget. §33:
 * one core, three screens.
 *
 * ⚠️ **One storage object, passed everywhere.** Two calls to `browserStorage()` probe `localStorage`
 * twice and, when it refuses, hand back **two different** do-nothing objects — so the session, the
 * device identity and the queues would be looking at unrelated places that all forget. The shell already
 * carries this note for its own two consumers; this is the same defect at a larger radius.
 *
 * ⚠️ **Nothing here is on the play path** (§23). It is called before the puzzle is fetched so that a
 * failure *during* the fetch is reported, and everything it starts is fire-and-forget.
 */

import { browserStorage } from "./store.js";
import { deviceId } from "./device.js";
import { errorOutbox, eventOutbox, shareOutbox } from "./outbox.js";
import { watchForErrors } from "./report.js";

/**
 * Start the queues and the error watcher.
 *
 * @param {object} [options]
 * @param {Storage} [options.storage] where queues and the device id live.
 * @param {EventTarget} [options.target] the window, for `online`, `visibilitychange` and uncaught errors.
 * @param {Function} [options.send] the transport, injected by tests.
 * @returns {{storage: Storage, device: string, events: object, errors: object, shares: object, stop: Function}}
 */
export function startUplink({ storage = browserStorage(), target = globalThis, send } = {}) {
  const device = deviceId(storage);
  const events = eventOutbox(storage, send);
  const errors = errorOutbox(storage, send);
  // ⚠️ The share's queue. Separate from the event's because a share is a separate event: it
  // happens after the game is uploaded, and `keep`'s insert ignores a second arrival of an id it
  // already holds -- so a field on the event could never be filled in afterwards.
  const shares = shareOutbox(storage, send);

  // ⚠️ **The watcher is installed before either queue is followed**, so an exception thrown by the
  // first drain is reported rather than lost. It is the one ordering here that is not arbitrary.
  const stopWatching = watchForErrors({ outbox: errors, deviceId: device, target });
  const stopEvents = events.follow(target);
  const stopErrors = errors.follow(target);
  const stopShares = shares.follow(target);

  return {
    storage,
    device,
    events,
    errors,
    shares,
    /** For a test, and for an interface that unmounts. Nothing in the browser calls it. */
    stop() {
      stopWatching();
      stopEvents();
      stopErrors();
      stopShares();
    },
  };
}
