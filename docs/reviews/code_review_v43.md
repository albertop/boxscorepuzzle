# Code Review v43

**Date:** 2026-08-26  
**Method:** static review only; no tests, linters, builds, browser runs, Docker commands, or Git commands were executed.  
**Scope:** the active source tree, with extra attention to every surface changed after v42 and to the closure of the three v42 findings. Generated inventories, caches, temporary artifacts, `_not_in_use`, and research questions were excluded under the review contract.

## Findings

### v43-P2-01 - The publish loader and runbook still require an Ofelia `image` line that the current deployment deliberately removed

**Priority:** P2  
**Confidence:** High  
**Locations:** `tools/deploy_bxcpze_publish_image.sh:96`, `tools/deploy_bxcpze_publish_image.sh:109`, `tools/create_docker_image.ps1:175`, `deploy/compose.yaml:195`, `deploy/ofelia/rotation.ini:79`, `docs/runbook-inventory.md:386`, `docs/runbook-inventory.md:400`

**Description**

The deployment design has changed correctly in two authoritative files:

- `compose.yaml` declares a stopped `bxcpze-publish` container and selects its image through `BXCPZE_PUBLISH_VERSION`.
- `rotation.ini` starts that container with `container = bxcpze-publish` and deliberately contains no `image =` line, avoiding Ofelia's unconditional pull of a local-only image.

The operator-facing paths still describe the superseded design:

- `deploy_bxcpze_publish_image.sh` asks the operator to add an `image = bxcpze-publish:<version>` line when the config is new.
- When the current config already exists, the same script searches for that removed line and exits 1 because it cannot find it.
- `create_docker_image.ps1` says Compose has no `BXCPZE_PUBLISH_VERSION` and directs the operator to edit the INI.
- The runbook repeats both obsolete claims and says `publish` is not a service.

This is the unfinished part of **v42-P2-02**. Copying `rotation.ini` into the transfer bundle fixed the missing-file half, but the later container redesign invalidated the version-selection half before the finding was fully closed.

**Impact**

A correct deployment using the current `rotation.ini` is reported as invalid by the official publish loader. Worse, following its remediation adds the exact `image` setting the new design removed: Ofelia then tries to pull a private local image from a registry and the daily rotation fails. The script can therefore either block a valid release or steer the operator back into the scheduler failure the container design was introduced to prevent.

**Reproduction**

1. Install the current `deploy/ofelia/rotation.ini` as `/srv/boxscorepuzzle/ofelia/config.ini`.
2. Load a publish tar and run `deploy_bxcpze_publish_image.sh <version>`.
3. The image itself passes the load/tag checks.
4. The script's anchored search finds no `image = bxcpze-publish:` line, because the current config correctly uses `container = bxcpze-publish`, and exits 1.
5. Its proposed repair adds an image-based Ofelia job that contradicts `rotation.ini:83-91` and bypasses the `BXCPZE_PUBLISH_VERSION` selected by Compose.

**Suggested fix**

Remove the INI image-line inspection and all instructions to edit that line. Make the publish loader finish like the other loaders: tell the operator to set `BXCPZE_PUBLISH_VERSION=<version>` in the stack and redeploy it, then optionally confirm that the resulting `bxcpze-publish` container references the loaded tag. Update the completion message and runbook sections in the same change. Extend the existing deployment consistency test so the publisher loader cannot again claim that a Compose variable is absent or require an Ofelia image line while Compose and `rotation.ini` use the container design.

**Blast radius:** deployment scripts, deployment documentation, and their static consistency tests. The Compose/Ofelia design itself does not need to be replaced.

## v42 closure audit

| Prior item | Status | Evidence |
|---|---|---|
| `v42-P2-01` | **Closed satisfactorily** | `publish` now accepts `--client`, defaults to `http://bxcpze-serve:8080/engine/package.js`, queries it before rotation, and both containers share the backend network. It no longer derives `/engine/package.js` from the public volume. |
| `v42-P2-02` | **Incomplete** | `rotation.ini` now travels in `docker_images/`, but the publish loader, build completion message, and runbook still implement the superseded image-line design. Refiled above as `v43-P2-01`. |
| `v42-P2-03` | **Closed satisfactorily** | `shareResult()` starts image creation without awaiting it; `sendShare()` selects the channel first; and the clipboard branch calls `clipboard.write()` synchronously with a promise-backed `ClipboardItem`. The actual caller now preserves the click activation rather than only the lower-level test doing so. |

## Hat coverage

| Hat | Surfaces reviewed | Result |
|---|---|---|
| Product and requirements | Current beta-1 plan, difficulty constants, active decisions, and user-visible landing/finish/share behavior | No new material issue |
| Python and domain model | Package format, shared pointer/manifest builders, domain constants, publisher preflight, and retention implementation | No new material issue |
| JavaScript and browser | Landing flow, finished-game flow, share pipeline, wide/pointer behavior, line-score renderer, board interaction, and related static guards | No new material issue |
| Data and migrations | Migrations 003/004, application-generated UTC arrival stamps, purge windows, inserts, and retention tests | No new material issue |
| Security and privacy | Signed inventory boundary, public/private paths, client ingestion bounds, credentials, and published-volume behavior | No new material issue |
| Docker and operations | Image creation, transfer bundle, all three loaders, Compose, Ofelia, publisher networking, retention schedule, and runbook | One finding above |
| Tests and CI | New and changed guards were inspected for whether they exercise the production path rather than a synthetic substitute | Missing deployment-design consistency coverage noted in the finding |
| Documentation | Active runbooks, beta notes, inventory instructions, review ledger, and TODO interactions | Deployment drift included in `v43-P2-01`; stale retention wording noted below without inflating it into a runtime bug |

## Deliberate non-findings

- `todo.md:138-168` still says event retention is open and that `events` is absent from `RETENTION_DAYS`. The code and migration now cap events at 730 days. This tracking text should be reconciled, but the implemented retention path is coherent and this review does not mislabel stale issue bookkeeping as a production defect.
- The new pointer and manifest helpers centralize document shape shared by two writers without sharing puzzle-generation reasoning. No verifier-independence issue was opened.
- `followPointer()` watches capability changes while the control set is chosen when the shell is built. A mid-session hardware change could leave the original controls mounted, but that is not a normal-path failure demonstrated by the current evidence and is not filed as a bug.
- Research questions, provisional product thresholds, and unvalidated difficulty labels remain decisions, not code defects.
- No issue was opened for validating the reveal-only half of historical Retrosheet data. Under the project contract, that half is consumed as-is and does not justify hundreds of lines of defensive validation.
- No concurrency, multi-developer, registry, orchestration, or enterprise-environment scenario was used to manufacture a finding for this solo-developer deployment.

## Summary

**New findings:** 1 (`1 P2`).  
**v42 status:** 2 closed satisfactorily; 1 incomplete and refiled.  
**Release position:** fix `v43-P2-01` before using the publish loader's scheduler instructions; following them against the current stack can restore the previously removed Ofelia pull failure.
