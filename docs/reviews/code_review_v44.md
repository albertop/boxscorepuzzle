# Code Review v44

**Date:** 2026-08-26  
**Method:** static review only; no tests, linters, builds, browser runs, Docker commands, or Git commands were executed.  
**Scope:** every active file changed after v43, the production paths those files invoke, the closure of v43's sole finding, and the current TODO state. Generated inventories, caches, temporary artifacts, `_not_in_use`, and research questions were excluded under the review contract.

## Findings

### v44-P2-01 - The runbook still invokes both pre-container publisher paths, and the v43 guard inspects only the loader

**Priority:** P2  
**Confidence:** High  
**Locations:** `docs/runbook-inventory.md:464`, `docs/runbook-inventory.md:476`, `publish/src/publish/__main__.py:25`, `publish/src/publish/health.py:141`, `tools/deploy_bxcpze_publish_image.sh:139`, `forge/tests/test_the_transfer_bundle_is_complete.py:229`

**Description**

The executable deployment path was corrected after v43: Compose owns a stopped `bxcpze-publish` container with its volumes, command and backend network; Ofelia starts that container; and the publish loader now tells the operator to run `docker start -a bxcpze-publish`.

The runbook still provides two commands from the superseded image-based design:

```text
docker exec bxcpze_publish python -m publish --inventory /inventory --public /public --health
```

and:

```text
docker run --rm \
  -v /srv/boxscorepuzzle/inventory:/srv/inventory:ro \
  -v boxscorepuzzle_puzzles:/srv/public \
  bxcpze-publish:x.y.z
```

The first command cannot perform its advertised health check: the declared container is named `bxcpze-publish`, not `bxcpze_publish`; its healthy state is stopped, so `docker exec` cannot enter it; `publish.__main__` has no `--health` option; and the service paths are `/srv/inventory` and `/srv/public`, not `/inventory` and `/public`.

The second command does run the image, but creates a different container without Compose's backend network. The production client default is `http://bxcpze-serve:8080/engine/package.js`; that name cannot resolve from the ad-hoc container. `_read_client()` therefore returns `None`, the preflight deliberately treats the unanswered question as non-blocking, and rotation writes the packages. The post-rotation verdict then reports the missing client only after the public path has changed.

This is the unfinished part of **v43-P2-01**. The new `test_the_hand_run_starts_the_declared_container` guard reads only `_LOADER`, so it is green while the operator's runbook continues to print the exact `docker run` the test forbids in the loader.

**Impact**

Following section 5b produces no health verdict at all. Following section 5c defeats the preflight comparison between the deployed client's `READABLE` list and the packages about to be served. On an ordinary compatible release it rotates successfully and then produces a false-red health result; on an incompatible release it can publish unreadable boards before producing that red result. The runbook therefore fails at the deployment boundary it explicitly says it is verifying.

**Reproduction**

1. Deploy the current stack, whose healthy publisher container is named `bxcpze-publish` and is stopped after its one-shot run.
2. Execute the section 5b command. Docker cannot exec into `bxcpze_publish`; correcting only the punctuation still targets a stopped container, and starting it would expose that `--health` is not a parser option.
3. Execute the section 5c command instead.
4. The ad-hoc container has no backend-network DNS entry for `bxcpze-serve`, so `readable_versions()` receives no client and rotation proceeds without the schema refusal.
5. The final inspection treats the same missing client as a fault, but the public files have already been written.

**Suggested fix**

Replace both publisher commands in the runbook with the declared-container path already printed by the loader:

```text
docker start -a bxcpze-publish
```

Make clear that redeploying the stack already runs that one-shot container once, and that `docker start -a` is the repeatable manual verification. Extend `test_the_hand_run_starts_the_declared_container` to inspect the operator-facing command blocks in both the loader and the relevant runbook sections. It should reject an ad-hoc `docker run` for the publisher and require the declared container in every place that instructs the operator to run or verify a rotation.

**Blast radius:** one runbook and one static deployment-consistency test. The current Compose, Ofelia, loader and publisher implementations already use the correct model.

## v43 closure audit

| Prior item | Status | Evidence |
|---|---|---|
| `v43-P2-01` | **Incomplete** | The version now lives only in `BXCPZE_PUBLISH_VERSION`; `rotation.ini` names the declared container; the loader no longer requires an Ofelia image line; the transfer bundle carries the INI; and the stack-variable list is current. However, the same runbook still contains two obsolete publisher commands that bypass or cannot reach the declared container. Refiled above as `v44-P2-01`. |

## Hat coverage

| Hat | Surfaces reviewed | Result |
|---|---|---|
| Product and requirements | Current beta-0 decisions, Pack A retirement, retained difficulty history, and active TODO items | No new material issue |
| Python and domain model | Inventory writer, manifest/pointer use, retired hand-solve entry point, publisher preflight, and retention bounds | No new material issue |
| JavaScript and browser | Explicit phone/desktop test devices, pointer behavior, share activation coverage, and unchanged production interaction paths | No new material issue |
| Data and migrations | Event-duration boundary tests, the 730/365/180-day retention contract, UTC arrival stamps, and active data documentation | No new material issue |
| Security and privacy | Signing-key boundary, ignored/generated hand-solve artifacts, private inventory placement, and public rotation limit | No new material issue |
| Docker and operations | Compose publisher service, Ofelia jobs, all publisher instructions, transfer bundle, runbook commands, and health networking | One finding above |
| Tests and CI | New deployment guards, explicit device fixtures, discovery lint baseline, and whether guards inspect every operator-facing subject | The runbook omission is part of `v44-P2-01` |
| Documentation | Runbook, beta plan, keep API, data-layer contract, review ledger, and TODO closure text | The executable runbook contradiction is part of `v44-P2-01` |

## Deliberate non-findings

- The local build output and the VPS `images/` layout are intentionally different. Archives originate under `docker_images/` and are placed under `images/` on the VPS; this is deployment topology, not a loader defect, and v43's withdrawn P1 is not reopened.
- Pack A is retired by a refusal in `build_pack.main()` while the module remains because independent renderer tests import its components. `_unreachable_main()` is not connected to the CLI. This matches the documented retirement contract and is not treated as dead-code or secret-generation bug.
- `todo.md` now marks event retention closed at 730 days but preserves the former open analysis below that closure, including an old unchecked subheading. The active implementation and authoritative data documents all state the decided limit. The historical ledger could be labelled more clearly, but this review does not turn issue-history presentation into a production bug.
- The device-capability watcher keeps CSS classes current while the mounted control set is selected when the shell starts. No normal-path failure was demonstrated by the changed production code, so no hardware-transition edge case is filed.
- Research questions, provisional difficulty thresholds, and withdrawn human-measurement work are not code defects.
- No issue was opened for validating the reveal-only half of historical Retrosheet data; that half remains consumed as-is under the project contract.
- No concurrency, multi-developer, registry, orchestration, or enterprise-environment scenario was used to manufacture a finding for this solo-developer deployment.

## Summary

**New findings:** 1 (`1 P2`).  
**v43 status:** its sole finding is only partially closed and is refiled as `v44-P2-01`.  
**Release position:** do not use the two publisher commands currently printed in `docs/runbook-inventory.md`. The loader's `docker start -a bxcpze-publish` path is consistent with the deployed container and preserves the backend-network preflight.
