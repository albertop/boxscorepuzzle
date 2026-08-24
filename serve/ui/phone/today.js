/**
 * `/today` resolves to `/p/<id>` and replaces itself in history.
 *
 * ⚠️⚠️ **It reads the pointer and nothing else.** No date arithmetic, no clock: which puzzle is today's
 * was decided when `publish.rotate` copied `days/<date>.json` into the served root as `today.json`.
 * This is the second half of C6 — `/p/<id>` canonical, `/today` redirecting — and the redirect target
 * comes out of a file rather than out of a calculation.
 *
 * ⚠️ **`replace`, not `assign`.** A player who arrives at `/today` and presses back should leave, not
 * bounce off the redirect into the board again.
 */

import { PackageError } from "../../engine/package.js";
import { text } from "../../engine/strings.js";
import { applyHead } from "./head.js";
import { NoPuzzle, TODAY, todayPointer, withSearch } from "./daily.js";

applyHead("landing");

const root = document.getElementById("today");

try {
  const pointer = await todayPointer();
  if (pointer === null) throw new NoPuzzle(`no ${TODAY}: there is nothing to serve`);
  // ⚠️ `?test=` survives the hop. `/t/<mode>` on the development server lands here, and the mode has to
  // reach the board — otherwise checking a change on a handset costs a manual URL edit, which is the
  // cost the short addresses exist to remove.
  location.replace(withSearch(`/p/${pointer.puzzle_id}`));
} catch (error) {
  // ⚠️ **No fallback to any other board.** The whole point of `/today` is that it names one thing; an
  // address that quietly serves something else when it cannot is the soft-404 this release closed.
  root.replaceChildren();
  const message = document.createElement("p");
  message.className = "landing-tagline";
  message.textContent = text(error instanceof NoPuzzle ? "day.none" : "package.unreadable");
  root.append(message);
  if (error instanceof PackageError || error instanceof NoPuzzle) console.error("no board:", error.message);
  else throw error;
}
