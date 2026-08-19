# What `serve` receives

`signing-public-key.hex` — the Ed25519 public key the forge signs with, 64 hex characters.

**It belongs in Git and the private half never does.** This one verifies and cannot sign, so it protects
nothing by being secret and protects the pairing by being written down: it records which key pair the
inventory in `puzzles/` belongs to. See `docs/signing-keys.md`.

⚠️ **`serve` verifies before rendering, and a package it cannot verify is not served.** That is what
makes `--ephemeral` batches safe to produce — they are signed by a pair that existed for one run, so
this key refuses them without anyone having to remember that they were only a test.

`puzzles/` — `manifest.json` names the current generation and the puzzles in it, and is signed the same
way. A signature per puzzle says each puzzle is genuine; only the manifest signature says the *set* is.
