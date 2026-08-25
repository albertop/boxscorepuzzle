# Code Review v42 - Full Codebase Review

**Date:** 2026-08-24  
**Method:** Static review of the complete active repository and current documentation. No test, lint, type-check, build, database, browser, Docker, or Git command was run.  
**Scope:** Active Python, JavaScript, HTML/CSS, tests, workflows, deployment files, operator scripts, and current Markdown documentation. `_not_in_use`, generated inventory, caches, research questions, and findings already pending in `todo.md` were excluded as sources of new issues.

## Executive summary

Three actionable findings remain, all **P2**. Two are in the newly completed production deployment path: the publisher's post-rotation health check cannot pass inside the image that runs it, and the transfer bundle omits the scheduler configuration required by the fresh-install instructions. The third is in the new share feature: its clipboard fallback begins only after asynchronous image generation, after the user activation it explicitly depends on may have expired.

No finding depends on multiple developers, concurrent publishers, enterprise infrastructure, hostile local files, or independent reconstruction of the reveal-only half of a boxscore. No research question was filed as a defect.

## Disposition of v41

All four v41 findings are closed satisfactorily:

- **v41-P1-01:** `serve.Dockerfile` now copies the nginx template to `/etc/nginx/templates/default.conf.template`, and the image-level test exercises the built image rather than a separately mounted configuration.
- **v41-P2-01:** the `keep` health check now uses Python's standard library, which is present in `python:3.13-slim`, and the image test asks the built image whether the configured executable exists.
- **v41-P2-02:** production nginx now applies `no-store` to `/engine/`, and the cache test requests an engine module.
- **v41-P3-01:** `CLAUDE.md` now records `keep`'s runtime dependency and why it exists.

None is carried forward into v42.

## Findings

### Docker / Containerization Expert

#### v42-P2-01 - The production publisher can never find the deployed client its health check requires

- **Hat:** Docker / Containerization Expert
- **Severity:** P2
- **Confidence:** High
- **Location:** `publish/src/publish/health.py:126`; `publish/src/publish/__main__.py:52`; `deploy/publish.Dockerfile:32`; `deploy/ofelia/rotation.ini:84`; `publish/tests/test_health.py:21`
- **Description:** After every rotation, `main()` calls `inspect(public, when)`. The schema-compatibility part of that check derives the client path as `public.parents[1] / "engine" / "package.js"`. Unit tests make this pass by constructing a synthetic `serve/engine/package.js` beside `serve/data/puzzles`. Production has a different topology: Ofelia mounts the public volume at `/srv/public`, the publisher image contains only `/app`, and neither the `serve` image nor its `/srv/serve/engine` directory is mounted into the job. With `public == /srv/public`, the derived reader is `/engine/package.js`, which cannot exist in this container.
- **Impact:** A successful rotation writes today's files and then exits non-zero with `no client is deployed`. The one exit code meant to distinguish a healthy daily run from a failed one is therefore permanently red. A real rotation failure becomes indistinguishable from the expected false alarm, while a manual first run reports failure after already changing the public state.
- **Reproduction scenario:** Run the command defined by `rotation.ini`: mount only the inventory at `/srv/inventory` and the named volume at `/srv/public`, then start `bxcpze-publish`. The copy and retirement steps complete. `inspect(Path("/srv/public"), ...)` then resolves its reader to `/engine/package.js`; `publish.Dockerfile` creates no such path, so line 128 returns a fault and `__main__.py` exits non-zero at line 55. The passing unit fixture does not reproduce either production mount.
- **Recommended fix:** Make the client contract an explicit input instead of inferring it from a development directory layout. The practical production path is to attach the one-shot job to the existing backend network, fetch the actual deployed `/engine/package.js` (or a small capability document served by the same image), and pass the accepted schema set into `inspect()`. Keep filesystem-set checks local to `/srv/public`. Add one image-level test that runs the real `serve` and `publish` images with the same network and volume paths used by Ofelia; the synthetic unit fixture can remain for the pure parsing cases.
- **Blast radius:** The publisher's exit status, deployment diagnosis, and schema-skew detection. The rotation's copy/delete behavior and the files already written are not prevented by this fault.

#### v42-P2-02 - The transfer bundle omits the scheduler file that the fresh-install procedure tries to install

- **Hat:** Docker / Containerization Expert
- **Severity:** P2
- **Confidence:** High
- **Location:** `tools/create_docker_image.ps1:156`; `tools/create_docker_image.ps1:165`; `tools/create_docker_image.ps1:167`; `tools/deploy_bxcpze_publish_image.sh:96`; `docs/runbook-inventory.md:306`; `docs/runbook-inventory.md:344`; `deploy/compose.yaml:200`
- **Description:** The build script says one transfer of `docker_images/` brings everything the server needs and copies the three load scripts into that directory, but it does not copy `deploy/ofelia/rotation.ini`. On a fresh VPS, the publish load script detects that `/srv/boxscorepuzzle/ofelia/config.ini` is absent and instructs the operator to install it from `deploy/ofelia/rotation.ini`, a path that was not included in the documented transfer. It then exits successfully. The generic final instruction also tells a publish build to set `BXCPZE_PUBLISH_VERSION` in Portainer, but Compose has no such variable; the version lives in the omitted INI file.
- **Impact:** Following the documented clean-install path leaves the scheduler without its bind-mounted configuration, so the daily rotation cannot start. A manual rotation can make launch day look correct, but the puzzle stops changing after that. On upgrades, the nonexistent Compose variable gives the operator a successful-looking action that does not change the image Ofelia runs.
- **Reproduction scenario:** Start with a server containing only the `docker_images/` directory produced by `create_docker_image.ps1`, as step 3 of the runbook directs. Run `deploy_bxcpze_publish_image.sh` before any scheduler config exists. Its proposed `sudo install ... deploy/ofelia/rotation.ini` source is absent, and the script still exits zero. Following the PowerShell script's `BXCPZE_PUBLISH_VERSION` instruction changes no field consumed by `compose.yaml` or `rotation.ini`.
- **Recommended fix:** Copy `rotation.ini` into `docker_images/` beside the load scripts, install it from `$SCRIPT_DIR` on first setup, and fail until the destination exists and names the loaded image. Branch the PowerShell completion message for `publish`: instruct the operator to update and verify the INI image line and restart `bxcpze-scheduler`, not to set an unused Portainer variable. Update the runbook to name that same transferred source path.
- **Blast radius:** Fresh production installation and future publisher-image upgrades. The `serve` and `keep` transfer paths are unaffected.

### Frontend Engineer

#### v42-P2-03 - The clipboard fallback starts after asynchronous image generation has consumed the user gesture

- **Hat:** Frontend Engineer
- **Severity:** P2
- **Confidence:** High
- **Location:** `serve/ui/phone/share-result.js:40`; `serve/ui/phone/share-send.js:71`; `serve/ui/phone/share-send.js:75`; `serve/ui/phone/finish.js:230`; `serve/ui/phone/landing.js:166`
- **Description:** Both share buttons call `shareResult()`, which awaits the full image build before calling `sendShare()`. That build fetches three stylesheets and three fonts, lays out the board, serializes SVG, loads an image, and rasterizes a canvas. Only after all of those awaits does the clipboard branch call `navigator.clipboard.write()`. The comment above `copyToClipboard()` correctly states that activation-gated browsers require the write to begin in the same user-gesture turn and that a promised image should be handed to `ClipboardItem`; the implementation does the opposite by passing an already resolved `File`. Existing tests call `sendShare()` directly with a prebuilt file, so they cannot observe the lost click boundary.
- **Impact:** On a browser that cannot natively share files and requires transient activation for image clipboard writes, pressing Share waits while the image is generated and then rejects with `NotAllowedError`. The async click handler provides no player-facing failure state; the button simply becomes available again. This breaks the exact desktop/fallback path `copyToClipboard()` exists to provide.
- **Reproduction scenario:** Use a browser where `navigator.canShare({files})` is false and image clipboard writes require active user activation. Press Share on the reveal or finished landing page. By the time `clipboardRef.write()` runs, image generation has crossed multiple asynchronous tasks and activation is no longer active, so the write is refused. The unit test still passes because it begins at `sendShare()` with the file already available and a mock clipboard that has no activation rule.
- **Recommended fix:** Choose the fallback before awaiting image generation and begin `clipboard.write()` synchronously from the click task, using `new ClipboardItem({"image/png": imagePromise})`. Alternatively pre-render and cache the file when the solved view appears so both native share and clipboard invocation begin with a ready file. Add an ordering test that requires `clipboard.write()` to be called before the injected image promise resolves, then perform one real-browser fallback check; a mock that accepts every write cannot validate activation.
- **Blast radius:** Sharing from the solved reveal and from the finished landing page on browsers using the clipboard fallback. The native file-share path and the privacy masking of the generated image are unchanged.

## Reviewer-hat coverage

- **Python Principal Developer:** Reviewed forge, publish, and keep boundaries, error handling, determinism, typing conventions, publication health, and current Python conventions. `v42-P2-01` is filed under Docker because the defect is created by the production container topology, not by the pure health rules in isolation.
- **Backend Architect:** Reviewed package v6 production/consumption, pointer generation, rotation, share ingestion, outbox semantics, and keep storage. No additional actionable issue was found.
- **Security Engineer:** Reviewed signing boundaries, secret injection, proxy authorization, private inventory mounts, share masking, URL construction, and database exposure. No secret or answer leakage was found.
- **Database Expert:** Reviewed the new `shares` table, request validation, idempotent inserts, nullable event reference, transaction recovery, and PostgreSQL/SQLite contract tests. No additional actionable issue was found.
- **Research Scientist / Reproducibility Expert:** Reviewed the current hand-solve record, difficulty calibration status, inventory assignment, and measurement notes. Open calibration and ghost-runner questions remain research, not defects.
- **Frontend Engineer:** Reviewed package parsing, landing/board/reveal flow, image construction, native share, clipboard fallback, persistence, queues, accessibility, caching, and current JavaScript conventions. `v42-P2-03` is the actionable result.
- **Baseball / Boxscore Domain Expert:** Reviewed schema v6's Retrosheet game id, home-club reference URL, reveal mapping, line score, innings-as-outs, substitutions, and the deliberate reveal-only boundary. No domain correctness issue was found.
- **Kakuro / Logic Puzzle Expert:** Reviewed erasure, givens, solver/verifier boundaries, lineup relation, hints, solve finalization, and the current calibration record. No new puzzle-correctness issue was found.
- **Docker / Containerization Expert:** Reviewed all three images, nginx templating, health checks, users and volume ownership, Compose networking and exposure, Ofelia, image transfer scripts, and the production runbook. `v42-P2-01` and `v42-P2-02` are the actionable results.

## Deliberate non-findings

- The four v41 findings were checked against their implementations and are not reopened.
- The pre-push hook's moving-working-tree decision, the `MANIFEST_SCHEMA` cleanup, duration ceiling, and remaining hand-solve calibration work are already recorded in `docs/reviews/todo.md` and are not duplicated.
- The reveal-only half of the boxscore remains deliberately taken as-is. No finding asks the application to reconstruct or independently validate Retrosheet content that was not part of the puzzle.
- The future-dated files baked into the `serve` image are not filed separately: the deployment explicitly mounts the production volume over them and instructs the operator to perform an initial rotation. The findings above concern steps that remain broken even when that documented sequence is followed.
- Ofelia's Docker-socket access, its hardcoded publisher tag, and the independent image versions are documented tradeoffs in this single-host deployment. They were not inflated into enterprise-orchestration findings.
- The share image's answer masking is not treated as a blur-security issue: player entries are replaced before rendering, givens are intentionally public, and the blur is only presentation.
- No concurrency, multi-developer workflow, Kubernetes, multi-host orchestration, hostile local inventory, or speculative future payment behavior was treated as an actionable defect.

## Residual risk and validation gap

This was a static review by instruction. The narrow post-fix checks with useful evidentiary value are: run the built `publish` image with the exact Ofelia mounts and actual `serve` image available through the chosen explicit contract path; stage a fresh-server transfer containing only the produced `docker_images/` bundle and complete the scheduler installation from it; and exercise the clipboard fallback in a real activation-gated browser. No command was run during this review to supply those outcomes.
