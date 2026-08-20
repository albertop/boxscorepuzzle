/**
 * Where a session is kept between visits.
 *
 * **`localStorage`, not cookies** (`docs/serve-flow.md` §6). Cookies travel to the server on every
 * request, which is waste for data the server does not want, and they are size-limited in a way a board
 * of filled cells will meet. C7 requires events stored locally first, which is also what makes §23 true:
 * with the backend down, login and sync fail and **the game still works**.
 *
 * ⚠️ **The storage object is injected**, so this is testable without a browser and so a later interface
 * can hand it something else. The engine knows nothing about screens; a key-value store is not a screen.
 *
 * ⚠️ **Every read fails soft and every write fails soft.** A quota error, a disabled store, private
 * browsing, a half-written value from a killed tab — none of them may stop a player playing. The rule
 * is not that persistence is unimportant; it is that **the play path may never depend on it**, and the
 * failure a player would forgive is a lost session rather than a board that will not open.
 */

/**
 * ⚠️ **The version is in the key, not in the value.** A saved shape that changes meaning must not be
 * read by code expecting the old one — and a version *inside* the value has to be parsed before it can
 * be checked, which means trusting the very bytes in question. A new prefix simply cannot collide with
 * the old data, and the old data ages out on its own.
 */
export const PREFIX = "boxscorepuzzle.session.v1.";

/** One puzzle, one key. **Tomorrow is a different puzzle** and carries nothing across (§27). */
export const keyFor = (puzzleId) => `${PREFIX}${puzzleId}`;

export function createStore(storage) {
  const read = (key) => {
    try {
      return storage.getItem(key);
    } catch {
      // A store that throws on read is a store that is not there. Same answer either way.
      return null;
    }
  };

  return {
    /**
     * Write the session down. Returns whether it landed, for a caller that wants to know — **and no
     * caller may refuse to continue because it did not.**
     */
    save(puzzleId, session) {
      try {
        storage.setItem(keyFor(puzzleId), JSON.stringify(session));
        return true;
      } catch {
        return false;
      }
    },

    /**
     * The saved session, or `null`.
     *
     * ⚠️ **Malformed storage reads as absent, never as an error and never as a partial session.** The
     * board this restores into is the day's puzzle; half a session applied to it would be worse than
     * none, because the player would meet entries they did not make and no way to tell.
     */
    load(puzzleId) {
      const raw = read(keyFor(puzzleId));
      if (raw === null) return null;
      try {
        const saved = JSON.parse(raw);
        // `typeof null === "object"`, and an array is an object too. Both are malformed here.
        if (saved === null || typeof saved !== "object" || Array.isArray(saved)) return null;
        return saved;
      } catch {
        return null;
      }
    },

    forget(puzzleId) {
      try {
        storage.removeItem(keyFor(puzzleId));
        return true;
      } catch {
        return false;
      }
    },
  };
}

/**
 * The browser's store, or a working stand-in.
 *
 * ⚠️ **Private browsing and disabled storage throw on *access*, not on use**, so the reference itself has
 * to be taken inside a `try`. A shell that reads `localStorage` at module scope crashes before it draws
 * anything — the whole board lost to a setting about saving.
 */
export function browserStorage() {
  try {
    const probe = `${PREFIX}probe`;
    localStorage.setItem(probe, "1");
    localStorage.removeItem(probe);
    return localStorage;
  } catch {
    // Accepts everything and remembers nothing. The game plays; the session does not survive the tab.
    return { getItem: () => null, setItem: () => {}, removeItem: () => {} };
  }
}
