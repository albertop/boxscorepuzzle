# Code Review v08

**Date:** 2026-08-18  
**Method:** static review only; no tests, scripts, database calls, browser checks, or package generation were run  
**Scope:** project documentation plus the post-v07 changes in `forge` and `discovery`; `.venv`, caches, generated artifacts, and `_not_in_use` excluded  
**Backlog policy:** findings marked pending in `docs/reviews/todo.md` are intentionally not repeated

## Executive summary

The delta makes substantial progress: Ed25519 package signing exists, the publication certification boundary is much stronger, schema v2 carries slot references, source evidence is bound to the package id, and the research controls from v07 were corrected.

The release path is not ready to be trusted yet. The writer still commits an unsigned manifest even though a manifest-signing function exists, the solver's new phase split omits the global identity from contradiction checks, and the claim that schema v1 remains readable is false for signed v1 files. An `--ephemeral` invocation can also use the production private key when that environment variable is present.

Seven new, deduplicated findings follow: four P1 and three P2.

## Findings

### v08-P1-01: The writer atomically commits an unsigned manifest

**Personas:** Security Engineer, QA/Reliability Engineer, Backend Architect  
**Confidence:** High

`boxscore_package.signing` now implements `sign_manifest()` and explains why individual package signatures do not authenticate the selected set. The actual writer never calls it. `_publish()` writes a plain dictionary containing `schema`, `generation`, and `puzzles`, then atomically replaces the live manifest with those unsigned bytes.

Evidence:

- [signing.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/signing.py#L105) implements manifest signing.
- [write_reference_puzzles.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/scripts/write_reference_puzzles.py#L238) writes the pending manifest without a signature.
- [write_reference_puzzles.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/scripts/write_reference_puzzles.py#L250) commits that unsigned file.

**Attack scenario:** An attacker can modify files during transfer, in object storage, through a compromised deployment account, or at a cache/origin layer, but does not possess the forge private key.

**Exploitation method:** Replace `manifest.json` with a document that points to a retained older generation, omits selected puzzle ids, or names a nonexistent generation. Every package reached through the altered manifest can still have a valid Ed25519 signature, so package verification alone does not reveal that the selected set was changed.

**Business impact:** Users can receive a replayed or incomplete inventory, get 404s during play, or receive the wrong daily content while every package-level integrity check appears healthy. This damages streaks, daily-puzzle consistency, and trust in publication provenance.

**Recommended fix:** Pass the private key into `_publish()`, sign the complete manifest body before writing the pending file, and atomically commit the signed document. `serve` must verify the manifest before following `generation` or `puzzles`, and reject missing or invalid signatures. Add an end-to-end test that tampers separately with `generation` and the puzzle-id list and proves both are rejected.

### v08-P1-02: Global-identity contradictions are no longer rejected by the solver

**Personas:** Python Principal Developer, QA/Reliability Engineer, Kakuro/logic-puzzle specialist  
**Confidence:** High

The phase split correctly delays `PA = Outs + R + LOB` when selecting deductions, but the same split is incorrectly applied to validation. `solve()` builds `system` from non-global equations and passes only that tuple to `_reject_contradictions()` before and after solving. `global_equations` are used to find moves but never to reject a fully known, inconsistent relation.

Evidence:

- [solver.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_forge/solver.py#L287) separates non-global and global equations.
- [solver.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_forge/solver.py#L294) validates only `system`.
- [solver.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_forge/solver.py#L305) repeats the same incomplete validation at exit.

If every cell is given and only LOB is wrong, the global equation has no unknowns. It therefore produces no propagation move, and the solver can return a complete `Solution` without raising `ContradictionError`.

**Impact:** A central engine API can certify completion for givens that violate one of the four equation families. Current pool and independent-verifier layers may catch this on their normal paths, but any discovery instrument, future generator call site, or direct solver consumer that relies on the solver's own contradiction contract can accept invalid data and record misleading difficulty telemetry.

**Recommended fix:** Keep phase ordering only in move selection. Run contradiction checks against `system + global_equations` at entry and exit, and after deductions if immediate detection is required. Add a focused test that changes only `team_footnotes.left_on_base` on a complete board and requires `ContradictionError`; retain the existing test that proves the global identity still waits its turn when selecting a move.

### v08-P1-03: Signed schema-v1 packages are not readable despite the compatibility promise

**Personas:** Python Principal Developer, QA/Reliability Engineer, Backend Architect  
**Confidence:** High

`READABLE = (1, 2)` and both format documents say version 1 remains parseable. Version 1 signatures are 64 hexadecimal characters from HMAC-SHA256, while version 2 uses 128 hexadecimal characters from Ed25519. The parser applies the single 128-character `SIGNATURE` pattern to both schemas, and signature verification accepts only an Ed25519 public key.

Evidence:

- [format.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/format.py#L31) declares both versions readable.
- [format.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/format.py#L65) defines only the 128-character signature shape.
- [format.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/format.py#L386) applies that pattern without considering schema.
- [signing.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/signing.py#L84) has no schema-dispatched v1 verifier.

The schema-document tests construct objects and inspect `as_json()` directly. Their deliberately invalid `"deadbeef"` signature never passes through `Package.from_json()`, so they do not test the compatibility claim.

**Impact:** Existing signed v1 references and any future legacy file fail at the parsing boundary before compatibility logic can run. A client built to the stated two-version contract cannot actually consume both versions, making deployment or rollback behavior depend on undocumented exceptions.

**Recommended fix:** Make an explicit product choice. If v1 truly remains readable, validate signature shape by schema and dispatch verification to the v1 HMAC verifier or a clearly isolated legacy adapter. If no consumer has shipped and a clean break is preferred, remove v1 from `READABLE` and update both documentation and tests to state that only v2 is accepted. In either case, add disk-level fixtures containing authentic signed v1 and v2 documents rather than testing only constructed dictionaries.

### v08-P1-04: `--ephemeral` can silently sign with the production private key

**Personas:** Security Engineer, Python Principal Developer, QA/Reliability Engineer  
**Confidence:** High

`main()` treats `--ephemeral` only as permission to proceed without `BOXSCORE_SIGNING_KEY`. When both the flag and the environment variable are present, the environment key wins and no warning is printed. The invocation requested a throwaway trust domain but produces packages signed by the production authority.

Evidence:

- [write_reference_puzzles.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/scripts/write_reference_puzzles.py#L273) reads the flag and environment independently.
- [write_reference_puzzles.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/scripts/write_reference_puzzles.py#L282) chooses the environment key whenever it exists.

**Attack scenario:** A developer or automation job runs a fixture/reference generation command with `--ephemeral` on a machine or CI context where the production signing variable is already configured. A party able to trigger that command but not read the key can also turn the process into a limited production-signing oracle.

**Exploitation method:** Supply `--ephemeral` while leaving `BOXSCORE_SIGNING_KEY` present. The code signs the generated reference batch with the production key, and those packages are indistinguishable cryptographically from approved inventory.

**Business impact:** Experimental or fixture content can cross the trust boundary and be accepted by `serve` as production-authentic. This defeats the purpose of the explicit ephemeral mode and increases the blast radius of routine development commands.

**Recommended fix:** Make the modes mutually exclusive and fail if `--ephemeral` is combined with a configured production key, or make the flag unconditionally ignore the environment and generate a new key. Prefer separate output roots for ephemeral and production batches. Add a test for all four flag/environment combinations and assert which key signs each result.

### v08-P2-01: The schema-v2 contract documents semantics the producer no longer emits

**Personas:** Frontend Engineer, Backend Architect, baseball/boxscore specialist, UX/graphic-design specialist  
**Confidence:** High

The format document is the only contract `serve` is supposed to use, but its v2 table still says batting labels are suffixed (`LF-1`, `LF-2`) even though the producer deliberately emits bare positions and uses `slot_references` for row identity. It also marks `left_on_base` nullable even though certification rejects an erased LOB as malformed. Related source docstrings still describe per-batter footnotes as always given, while those cells are now erasable.

Evidence:

- [package-format-v2.md](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/docs/package-format-v2.md#L39) describes obsolete suffixed batting labels.
- [package-format-v2.md](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/docs/package-format-v2.md#L61) marks `left_on_base` nullable.
- [measure.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/difficulty-metrics/measure.py#L210) returns bare batting positions.
- [verify.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_verify/verify.py#L258) rejects a missing LOB.
- [test_schema_document.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/tests/verify/test_schema_document.py#L52) checks field presence but not meaning, nullability, or examples.

**Impact:** The frontend can be implemented correctly against the written contract and still render the wrong visual language or design a nullable state that no certified package may contain. Because `serve` is about to start and must not import forge code, this drift is a direct integration defect rather than documentation polish.

**Recommended fix:** Correct v2 to state bare position labels, non-null LOB in published/certified packages, and nullable per-batter footnotes. Remove copied v1 amendment language that says version 1 is being finished inside the v2 document. Extend contract tests beyond field names: assert nullability rules, representative label examples, signature shapes by schema, and concrete v1/v2 documents parsed through the public reader.

### v08-P2-02: Callers can stamp a schema that disagrees with the payload

**Personas:** Python Principal Developer, QA/Reliability Engineer, Backend Architect  
**Confidence:** High

The comments state that a version follows the payload and cannot disagree with it, but `Package.schema` remains publicly settable. `written_as` returns that explicit value without checking `slot_references`. A caller can therefore serialize schema 2 without references or schema 1 with references. In the inferred path, an empty v2 reference tuple is also falsey and downgrades to schema 1.

Evidence:

- [format.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/format.py#L335) exposes the schema override.
- [format.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/forge/src/boxscore_package/format.py#L346) trusts the override and uses truthiness rather than `is not None`.

The parser rejects mismatched documents, but the writer API can create them. The current reference writer's disk round trip catches its own output; that is not a guarantee for future producers using the shared package module.

**Impact:** A producer can write an internally contradictory package that another process refuses. This breaks the shared format boundary and turns an intended construction invariant into a convention each caller must remember.

**Recommended fix:** Remove the externally settable schema override and derive the version exclusively from `slot_references is not None`, or enforce the invariant in `__post_init__`. If parsed schema must be preserved, store it privately and validate it against the payload immediately. Add construction and round-trip tests for both mismatch directions and for an empty reference tuple.

### v08-P2-03: Empty or disjoint comparison cohorts fail with generic runtime errors

**Personas:** Python Principal Developer, QA/Reliability Engineer, Kakuro/logic-puzzle specialist  
**Confidence:** High

The global-phase comparator now correctly rejects unequal cohorts unless `--allow-partial` is explicit. It does not require the shared intersection to be non-empty. Two disjoint files in diagnostic mode proceed to `summarise([])`, where `statistics.median()` raises, and later code also indexes `shared[0]`. The measurement path has the same problem if a non-empty sample produces zero solved rows. Supplying too few arguments after `--against` also indexes `sys.argv` without validation.

Evidence:

- [compare.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/global-identity-phase/compare.py#L111) computes the intersection without asserting it is non-empty.
- [compare.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/global-identity-phase/compare.py#L134) summarizes that potentially empty cohort.
- [compare.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/global-identity-phase/compare.py#L157) indexes `shared[0]`.
- [compare.py](C:/Users/aperd/Documents/DGLv2/apps/boxscorepuzzle/discovery/global-identity-phase/compare.py#L180) reads two path arguments without checking their count.

**Impact:** A decision instrument fails with `StatisticsError` or `IndexError` instead of explaining that no comparison is possible. This violates the project's explicit discovery rule and makes partial-run diagnosis harder at exactly the point the comparator is meant to protect against false nulls.

**Recommended fix:** Validate CLI arity before indexing, require at least one shared key even in diagnostic mode, and fail with counts and filenames. After measurement, refuse an empty result with a message distinguishing an empty eligible sample from all erasures failing. Add direct tests for empty files, disjoint files with `--allow-partial`, and missing `--against` arguments.

## Persona coverage

| Persona | Result |
|---|---|
| Python Principal Developer | Findings v08-P1-02, v08-P1-03, v08-P1-04, v08-P2-02, and v08-P2-03. |
| QA / Reliability Engineer | Findings v08-P1-01 through v08-P1-04, v08-P2-02, and v08-P2-03. Tests were not executed by request. |
| Frontend Engineer | Finding v08-P2-01. `serve` is still empty, so application component/state/accessibility review does not yet apply. |
| Security Engineer | Findings v08-P1-01 and v08-P1-04. Previously tracked key-rotation and signing work is not duplicated. |
| Backend Architect | Findings v08-P1-01, v08-P1-03, v08-P2-01, and v08-P2-02. |
| Baseball / boxscore specialist | Finding v08-P2-01. Bare positions plus slot references match the decided baseball representation; the v2 document does not. |
| Kakuro / logic-puzzle specialist | Findings v08-P1-02 and v08-P2-03. The phase boundary must change deduction order without removing an invariant. |
| UX / graphic-design specialist | Finding v08-P2-01. A frontend following the document would revive the obsolete suffixed-label visual language. |

## Positive changes observed

- Ed25519 separates signing authority on the forge from verification authority on `serve`.
- `certify_for_publication()` composes mathematical, plausibility, reveal, provenance, and independent-correspondence checks and fails closed when evidence is absent.
- Schema v2 carries one validated slot reference per batting row.
- The loader projects provenance from the qualifying row and carries independent game-log evidence.
- The v07 footnote control now holds term count fixed, and the prototype suffix guard covers multi-digit values.
- The open-versus-given rerun retains all 48 paired boards and reproduces the large treatment difference on a shared order.

## Recommended order of work

1. Sign and verify the manifest before treating the Ed25519 migration as complete.
2. Restore global-equation contradiction checks without changing deduction phase order.
3. Decide whether v1 is truly supported, then make parser, verifier, fixtures, and docs agree.
4. Make ephemeral and production signing modes mutually exclusive.
5. Repair the v2 semantic contract and make schema/payload coherence an enforced invariant.
6. Add explicit empty-cohort handling to the discovery comparator.

## Review boundary

This review does not repeat the open footnote-drawing decision or other work already marked pending in `docs/reviews/todo.md`. The reference-package regeneration already listed there is not itself a finding here. No source code was changed; this Markdown review is the only created file.
