# JavaScript Conventions

This document is the JavaScript counterpart to `docs/python-conventions.md`.

These rules apply to the hand-written JavaScript under `serve/`. They are written for this repository as it exists today: browser ES modules, a small client engine, a phone UI, static puzzle packages, and a custom browser test harness. Do not import generic Node/Express/npm conventions unless the repository actually adopts that stack.

## 0. Simplicity rule

The goal is good code, not ceremony.

- Prefer the simplest clear implementation that protects the product invariant.
- Do not add layers, abstractions, helper files, classes, build tools, or dependencies just to satisfy a convention.
- A convention is strongest when it prevents a bug this project can realistically ship.
- A convention is weak when it only makes code look more "enterprise" without making the puzzle safer, clearer, faster, or easier to change.
- If following a rule would make a small local change harder to understand, keep the local code clear and leave a short explanation when needed.
- Optimize for code a solo developer can return to in six months and trust quickly.

## 1. The stack that exists today

- Runtime target: modern browser JavaScript.
- Module system: ES modules with explicit `.js` import extensions.
- Main code area: `serve/engine/` and `serve/ui/phone/`.
- Test area: `serve/tests/`.
- Data area: `serve/data/`.
- Package manager: none for the current JavaScript surface.
- Build tool: none for the current JavaScript surface.
- Test runner: the project-owned browser harness in `serve/tests/harness.js`.

Do not write instructions that assume `package.json`, npm scripts, Express, PostgreSQL, Vitest, ESLint, or Prettier until those tools actually exist in this project.

If a future change introduces npm tooling, update this document in the same change. The tooling contract must name the real install, test, lint, and build commands.

## 2. Directory and ownership rules

- `serve/engine/` owns puzzle state, package reading, rules, strings, clocks, and reusable client logic.
- `serve/ui/phone/` owns DOM rendering, event wiring, focus behavior, phone layout behavior, entry points, and browser-facing flows.
- `serve/tests/` owns browser-driven tests and the custom assertions used by those tests.
- `serve/data/` is data consumed by the client, not a place for hand-written control logic.
- New JavaScript files must go into the existing layer that owns their responsibility.
- Do not create a generic `src/`, `controllers/`, `models/`, or `routes/` tree for this client unless the architecture actually changes.
- Engine modules may be imported by UI modules.
- Engine modules must not import UI modules.
- Entry points may have top-level side effects.
- Reusable modules must avoid top-level side effects.

## 3. Module conventions

- Use ES module syntax: `import` and `export`.
- Use explicit relative import extensions: `./game.js`, not `./game`.
- Prefer named exports for reusable functions, constants, and classes.
- Avoid default exports unless there is a strong local precedent in the same layer.
- Keep development-only or test-only code out of normal page loads.
- Use dynamic `import()` for optional test/development branches that must not be loaded by regular users.
- Do not introduce CommonJS `require()` or `module.exports`.

## 4. Variable and function style

- Use `const` by default.
- Use `let` only when reassignment is part of the algorithm.
- Never use `var`.
- Use strict equality: `===` and `!==`.
- Prefer clear function declarations for exported operations that define a module's public vocabulary.
- Local helpers may be arrow functions when that reads better.
- Keep boolean names affirmative where possible: `isFinished`, `hasEntry`, `canReveal`.
- Avoid clever coercion. Convert strings, numbers, and booleans explicitly.
- Avoid mutation across module boundaries. If a caller should not mutate returned data, return fresh arrays, fresh objects, or documented read-only views.
- Do not extract a helper just because a block is a few lines long. Extract when the name explains a domain idea or when duplication has already become risky.
- Do not turn plain data into classes unless identity, invariants, or behavior genuinely benefit from it.

## 5. Formatting conventions

- Match the surrounding JavaScript style.
- Use two-space indentation.
- Use double quotes for strings.
- Use semicolons.
- Use trailing commas in multiline arrays, objects, argument lists, and imports when the surrounding file does.
- Break long expressions where the domain idea changes, not merely to satisfy an arbitrary width.
- Do not reformat an entire file when changing one behavior.

## 6. Boundary validation

- Treat puzzle package JSON as untrusted input.
- Treat local storage as untrusted input.
- Treat URL parameters as untrusted input.
- Validate external shapes at the boundary before downstream code uses them.
- Error messages for malformed data must name the rejected field or invariant.
- A malformed package should be refused deliberately, not allowed to become a later `TypeError`.
- Use `null` deliberately when it is part of the schema.
- Do not confuse missing, `undefined`, and `null`; document the difference when both are meaningful.
- For whole-number puzzle values, use explicit numeric checks such as `Number.isInteger(value)` and `value >= 0`.
- Do not use truthiness checks for numeric cells; `0` is a valid baseball value.

## 7. Async and fetch conventions

- Use `async`/`await` for asynchronous flows.
- Do not blanket-wrap every `await` in `try/catch`.
- Catch errors at the layer that can add meaning, choose user-facing behavior, or preserve a useful diagnostic.
- Lower-level functions should throw precise errors and let the owning boundary decide how to present them.
- Fetch callers that read moving pointers, manifests, or test data should make caching behavior explicit.
- A page entry point may catch package-loading failures and translate them into player-facing copy.
- Reusable engine functions should not fetch unless fetching is their explicit responsibility.
- Do not introduce a generic request wrapper until there are enough call sites to prove the wrapper removes real duplication.

## 8. DOM and UI conventions

- Prefer `document.createElement`, `textContent`, `classList`, `dataset`, and attributes over string-built HTML.
- Do not put package data, player data, URL data, or translated text into `innerHTML`.
- `innerHTML` is only acceptable for tiny static skeletons controlled entirely by the source file.
- Interactive elements should be real controls when possible.
- If a non-button element acts like a button, it must get the keyboard, focus, role, and ARIA treatment that makes it a real control for users.
- Keep focus behavior explicit when opening or closing panels.
- User-visible text that matters must exist as text nodes or attributes, not only as CSS decoration.
- UI code may know about DOM and device behavior.
- Engine code should not need the screen to answer a rules question.
- Do not build a component framework by hand. Small DOM helpers are fine; architectural scaffolding should earn its place.

## 9. State and persistence conventions

- Store events and facts that cannot be reconstructed, not just aggregate state.
- A saved session is optional recovery data, not a boot dependency.
- If a saved session is malformed, refuse it and let the player receive a playable board.
- Game-ending state belongs in the engine, not only in the UI.
- A finished board must remain immutable through the public game API.
- Presentation layers should not have to remember core game rules independently.
- When adding a new persisted field, update restore validation and tests in the same change.

## 10. Error and logging conventions

- Throw `Error` or a domain-specific error class when the caller is expected to handle a failure.
- Error text should say what was rejected, not merely that something failed.
- User-facing copy should come from the same string/catalog path as the rest of the UI.
- Console logging belongs at diagnostics and boundary points, not in core rule functions.
- Never log secrets, tokens, signing material, or private operator data.
- Do not hide a malformed package behind a generic fallback if that would make a broken published board look valid.

## 11. Security conventions

- Client-side code cannot protect secrets. Do not put secrets in `serve/`.
- Browser signature verification is not a publication guarantee when the verifier and data come from the same origin. Verification belongs before publication.
- Never build SQL, shell commands, file paths, or HTML strings from untrusted JavaScript input. Most of this client should not be doing any of those things at all.
- Keep test mode and development affordances isolated behind explicit branches.
- Do not load test helpers on normal player pages.
- Do not make URL parameters silently unlock production-only behavior.

## 12. Testing conventions

- New engine behavior that changes puzzle rules, player state, package reading, persistence, timing, or scoring needs a test in `serve/tests/`.
- New package-shape validation needs a malformed-package test when the rejected shape could otherwise ship as a broken board.
- New UI behavior needs a browser harness test when it affects reachability, focus, finishing, persistence, test mode isolation, or a player-visible invariant.
- Tiny copy, spacing, class-name, or markup-only changes do not need a new test unless they protect a previously broken behavior.
- Prefer real puzzle packages for invariants that depend on baseball or generated package shape.
- Use tiny synthetic objects only for malformed inputs or focused state transitions.
- Test names should state the product invariant, not the implementation detail.
- Assertions must include messages that identify the broken property.
- Do not write tests that only validate the last value produced by a loop.
- Do not compare DOM nodes through JSON/string equality; compare identity directly with `assert(a === b)`.
- If a helper cannot assert a class of values safely, make it refuse that class loudly.

## 13. Comments and documentation conventions

- Comments should explain why the rule exists, especially when the rule prevents a previously seen defect.
- Do not keep stale comments after a product decision changes.
- A warning-style comment must name the invariant it protects, not merely express anxiety.
- Do not repeat the same domain rule in many comments. Prefer one named function, one constant, or one shared helper.
- If a number is measured, cite the measurement source.
- If a number is chosen but not measured, mark it as provisional and explain what will validate it.
- Do not bury product requirements in comments when they belong in docs or tests.

## 14. Constants and magic numbers

- Name domain numbers.
- Keep schema versions, game limits, column definitions, cache rules, and puzzle limits near the layer that owns them.
- Do not duplicate roster caps, column names, or schema meanings across files.
- A duplicated number is acceptable only when the test is explicitly proving two independent surfaces agree.
- If a constant changes package meaning, treat it as a schema or compatibility decision, not a local refactor.
- Do not create a constants file for one local number that is obvious at the use site. Move it only when reuse, measurement, or domain meaning makes the name valuable.

## 15. Dependencies

- Prefer modern browser APIs and small project-owned helpers.
- Do not add a JavaScript dependency casually.
- Do not add Lodash, Ramda, date libraries, DOM helper libraries, or bundlers unless the project has a measured need.
- If a dependency is introduced, add the real package-management files and update this document with the install/test/build contract.
- Do not hand-edit a lockfile if npm tooling is later introduced; change dependencies through the package manager.

## 16. What not to copy from generic web templates

- Do not claim the project uses Express unless an Express server exists.
- Do not claim the project uses PostgreSQL unless JavaScript code actually connects to it.
- Do not claim the project uses npm commands unless `package.json` defines them.
- Do not require Vitest tests unless the project adopts Vitest.
- Do not require every `await` to have a local `try/catch`; that produces noisy handlers and weaker error boundaries.
- Do not force arrow functions everywhere; this codebase uses function declarations well for public module vocabulary.
- Do not impose an API response envelope on static client modules.

## 17. Review checklist for JavaScript changes

- Did the convention make this simpler and safer, or just heavier?
- Does this belong in `engine`, `ui/phone`, `tests`, or `data`?
- Can the engine still be tested without mounting a screen?
- Is every external shape validated before use?
- Can `0` pass wherever baseball allows zero?
- Did this add a top-level side effect to a reusable module?
- Did this load test/development code on a normal player path?
- Does the UI remain keyboard and screen-reader reachable?
- Is user-visible text created safely?
- Is the persisted session still optional and validated?
- Does the test prove the invariant, or only the current implementation?
- Did any comment become stale because the behavior changed?
- Did a chosen number need a named constant or a measurement note?
- Would a solo maintainer understand this faster than the previous version?
