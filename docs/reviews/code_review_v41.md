# Code Review v41 - Full Codebase Review

**Date:** 2026-08-24  
**Method:** Static review of the complete active repository, with an explicit closure audit of v40 before the new pass. No test, lint, type-check, build, database, browser, Docker, network, or Git command was run.  
**Scope:** Active Python, JavaScript, HTML/CSS, publication code, tests, workflows, hooks, Docker/nginx configuration, development tooling, and current Markdown documentation. `_not_in_use`, generated inventory, caches, research outputs, and findings already recorded as pending in `docs/reviews/todo.md` were excluded as sources of new issues.

## Disposition of v40 - all three satisfactorily closed

| Finding | Verdict | What was verified statically |
|---|---|---|
| **v40-P1-01** | ✔ Fixed | `inspect()` parses `today.json` once into its date and `puzzle_id`, requires the named package to exist, and applies the same target check to `yesterday.json` when that optional pointer exists. Missing, unreadable, id-less, and dangling pointers produce named faults. |
| **v40-P2-01** | ✔ Fixed | Every package, dated pointer, and public manifest now goes through `_place()`: bytes are written to a sibling `.pending` file and committed with `Path.replace()`. A failed pending write removes only the pending file and preserves the previous served bytes. The sweep for abandoned pending files is separate from the `*.json` sweep, so it can actually fire. |
| **v40-P3-01** | ✔ Fixed | `weekly.yml` installs and checks `publish/`, including coverage. The project-tree guard now checks the scheduled workflow as a third side beside the hook and push workflows, so another project using the same tool names can no longer hide an omitted tree. |

No v40 item is incomplete or still pending.

## Executive summary

Four new actionable findings remain: **one P1, two P2, and one P3**. The P1 prevents the newly completed web image from building at all. One P2 makes the `keep` image report unhealthy independently of the application; the other leaves the engine half of the JavaScript module graph outside the cache policy E3 claims to enforce. The P3 is an authoritative architecture statement made false by the runtime dependency F1 itself introduced.

The deployment findings are against F1, which `docs/beta-0-plan.md` marks built and complete. TLS, DNS, the production Compose file, host-wide IP retention, and the measured rate limit remain assigned to F2 and are not reported as missing code.

## P1 findings

### Docker Expert

#### v41-P1-01 - The completed `serve` image copies a configuration file that does not exist

- **Severity:** P1
- **Confidence:** High
- **Location:** `deploy/serve.Dockerfile:24`; the only source file is `deploy/nginx/boxscorepuzzle.conf.template`
- **Description:** The Dockerfile copies `deploy/nginx/boxscorepuzzle.conf` into `/etc/nginx/conf.d/default.conf`, but no file with that source name exists. The configuration was renamed to `.conf.template` when `${KEEP_SHARED_TOKEN}` substitution was added, and the Dockerfile retained the previous name. This is also the wrong destination for the new artifact: nginx's official entrypoint substitutes files under `/etc/nginx/templates/`, not a file already placed in `conf.d`.
- **Why this matters:** F1.1 and F1.3b are marked done, yet the current production web image cannot be built from the repository. Even if a plain `.conf` were recreated just to satisfy `COPY`, `${KEEP_SHARED_TOKEN}` would bypass the template substitution described by the configuration itself and reach nginx unresolved.
- **Reproduction:** Use the documented repository-root build context with `deploy/serve.Dockerfile`. Docker must resolve the source of every `COPY`; `deploy/nginx/boxscorepuzzle.conf` is absent, while `rg --files deploy` contains only `boxscorepuzzle.conf.template`. The build therefore stops at line 24 before nginx can start.
- **Suggested fix:** Copy `deploy/nginx/boxscorepuzzle.conf.template` to `/etc/nginx/templates/default.conf.template`, which is the path the base image's entrypoint processes before starting nginx. Add one narrow image-smoke test that builds this Dockerfile and requests `/`; the existing nginx tests mount the template independently and therefore cannot detect a broken Dockerfile source or destination.
- **Blast radius:** The entire static site image, including `/today`, `/p/<id>`, cache headers, and the proxy to `keep`. The development server and direct nginx-template tests can remain green while this image is unbuildable.

## P2 findings

### Docker Expert

#### v41-P2-01 - The `keep` healthcheck invokes an executable the image never installs

- **Severity:** P2
- **Confidence:** High
- **Location:** `deploy/keep.Dockerfile:55`; `keep/src/keep/app.py:60`
- **Description:** The image is based on `python:3.13-slim`, installs the Python project with uv, and never installs `wget`. Its Docker `HEALTHCHECK` nevertheless executes `wget --spider`. The application already has a GET-only `/health` endpoint, but the probe does not use the Python runtime that the image actually guarantees.
- **Why this matters:** A correctly running `keep` process and healthy PostgreSQL connection can still be marked unhealthy because the probe command itself is unavailable. That makes container health, dependency ordering, and the future F3 monitor report an infrastructure failure unrelated to the service they are meant to judge.
- **Reproduction:** Follow the Dockerfile's declared contents: the only copied executable is `uv`, and the only installed project runtime dependency is psycopg. No layer installs `wget`, yet the health command requires it. Docker runs healthchecks inside that final image as the `keep` user, so a host-installed `wget` cannot satisfy the command.
- **Suggested fix:** Use the guaranteed Python standard library to make a short-timeout GET request to `http://127.0.0.1:8081/health`, and let a non-2xx response or exception exit non-zero. This avoids adding a package solely for one probe and matches the application's explicit `method == "GET"` route.
- **Blast radius:** Docker health reporting for the data layer. The WSGI service can still accept proxied requests, but orchestration and monitoring cannot distinguish that from a dead container.

### Frontend Engineer

#### v41-P2-02 - Imported engine modules are outside the production `no-store` rule

- **Severity:** P2
- **Confidence:** High
- **Location:** `deploy/nginx/boxscorepuzzle.conf.template:109`; `serve/ui/phone/daily.js:22`; `docs/calendar.md:531`
- **Description:** nginx applies `Cache-Control: no-store` only under `/ui/`. The page modules import the engine through paths such as `../../engine/package.js`, which resolve to `/engine/package.js`; those requests match no cache location and receive nginx's default static-file behavior. The cache specification describes `/ui/phone/main.js` as representing "the modules and the CSS", but the test requests only the URLs explicitly listed in that table, so the separately rooted engine graph is never exercised.
- **Why this matters:** A deployment can deliver a new `main.js` and an older cached `package.js`, `game.js`, or `store.js`. This project adopted `no-store` for application code because stale JavaScript has already made a correct schema change look broken twice. Covering only the presentation half recreates that exact mixed-version failure on an ordinary production update.
- **Reproduction:** Resolve the import on line 22 of `daily.js`: from `/ui/phone/daily.js`, `../../engine/package.js` becomes `/engine/package.js`. The nginx configuration has a `/ui/` block and package-data blocks but no `/engine/` block, so that response does not receive the documented `no-store` header. The cache-table test cannot fail because `/engine/package.js` is not one of its rows.
- **Suggested fix:** Apply the same `no-store` header to `/engine/` as to `/ui/`, and add one engine-module URL to the authoritative cache table so the existing nginx test requests it. No bundler, asset hashing, or cache-version system is needed.
- **Blast radius:** Every shared engine module used by the landing page and board, including package validation, game state, persistence, reporting, and upload queues. HTML, `/ui/` modules, dated pointers, and immutable puzzle packages already have explicit policies.

## P3 findings

### Python Principal Developer

#### v41-P3-01 - The primary architecture guide still says `keep` has no runtime dependencies

- **Severity:** P3
- **Confidence:** High
- **Location:** `CLAUDE.md:218`; `keep/pyproject.toml:17`
- **Description:** `CLAUDE.md` states that `keep` has "no runtime dependencies at all." F1 correctly moved `psycopg[binary]` from the development group into the project's runtime dependencies because production cannot start without it. The authoritative guide now gives the opposite answer from the package metadata and from the new Dockerfile's own explanation.
- **Why this matters:** This is the exact dependency classification that produced a container unable to import its database driver earlier in F1. Leaving the old architectural claim in the primary guide invites the same cleanup in reverse: psycopg can be moved back to development because the guide says no runtime package belongs there.
- **Reproduction:** Compare `CLAUDE.md:218` with the `[project].dependencies` declaration in `keep/pyproject.toml`; the latter contains `psycopg[binary]>=3.2` and records why it must be present in production.
- **Suggested fix:** Replace "no runtime dependencies" with the property that remains true: `keep` has one runtime dependency, the PostgreSQL driver, and no framework, ORM, templating layer, or cross-import from the other code trees. Keep the existing explanation that the four trees share no code or deployment cycle.
- **Blast radius:** Developer guidance and future dependency maintenance. Current packaging is correct; the documentation is the stale side.

## Hat coverage with no additional unique finding

- **Backend Architect:** Publication command wiring, public/private inventory separation, route ownership, the static play path, proxy boundary, database startup, and F1/F2 separation were reviewed. No additional issue was created from deployment work explicitly assigned to F2.
- **QA / Reliability:** Publication fault injection, health cases, browser harness, nginx route/cache tests, proxy integration tests, CI workflows, and tree guards were reviewed. The missing image-level smoke coverage is attached to v41-P1-01 rather than duplicated.
- **Security Reviewer:** Token insertion, removal of browser-provided authorization, internal-only keep port, public/private signing keys, path matching, static archive boundary, and non-root users were reviewed. Host logging and rate limiting remain named F2 work; no speculative host finding was opened.
- **UX / Visual Design:** Landing, `/today`, canonical board, tutorial, error states, focus, mobile layout, and reveal flow were reviewed. The page-title date mismatch is already pending in `docs/reviews/todo.md` and is not duplicated.
- **Baseball / Boxscore Domain:** Published board identity, line scores, innings-as-outs, substitutions, footnotes, and full reveal mapping were reviewed. No validation was demanded for the reveal-only half that is intentionally taken as-is.
- **Kakuro / Logic Puzzle Expert:** Erasure, solver families, certification, difficulty evidence, and the hand-solve gate were reviewed. The remaining hand solve is operator validation, not a code defect.

## Deliberate non-findings

- `--date` is an explicit operator-only override used to build the fixed committed development tree. It can select a future pointer by design; no extra production lock was proposed for a solo operator who can already copy the same file manually. The production scheduler must simply omit it.
- TLS, DNS, certbot, the production Compose file, `access_log off`, host-wide IP retention, the internal Docker network, and the measured rate-limit value remain explicitly assigned to F2. They are not defects in F1 artifacts that claim not to implement them.
- The landing-page title using the visitor's clock is already pending in `docs/reviews/todo.md` and is not duplicated.
- The pre-push moving-tree decision and the two `MANIFEST_SCHEMA` items remain recorded in `docs/reviews/todo.md` and are not duplicated.
- Shipping browser test files inside `serve/` was not elevated into a security issue: they contain no private generator, signing secret, archive inventory, or server credential. Image exclusion or an nginx deny may reduce surface and size, but no present business or trust boundary depends on it.
- No concurrent publisher, multi-developer workflow, remote Docker builder, enterprise orchestration, or adversarial local-inventory scenario was treated as an actionable defect.
- The retired v30-P1-02 claim about independently validating the reveal-only half remains retracted.

## Residual risk and validation gap

This was a static review by instruction. The useful post-fix checks are narrow: build and start the `serve` image through its Dockerfile, observe the `keep` image reach healthy through a real GET, and request `/engine/package.js` from nginx to assert `Cache-Control: no-store`. No command was run during this review to supply those outcomes.
