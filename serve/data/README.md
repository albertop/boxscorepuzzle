# What `serve` receives

`signing-public-key.hex` — the Ed25519 public key the forge signs with, 64 hex characters.

**It belongs in Git and the private half never does.** This one verifies and cannot sign, so it protects
nothing by being secret and protects the pairing by being written down: it records which key pair the
inventory in `puzzles/` belongs to. See `docs/signing-keys.md`.

⚠️⚠️ **This said `serve` verifies before rendering. It does not, and never has.** (v36-P3-35)
`docs/serve-brief.md` §5 records the decision — *the client does not verify signatures*, because a
browser checking a signature it received from the same origin as the verifier is theatre — and
`package.js` says the same in its header. **No code under `serve/` reads this key or the manifest's
`signature` field.** A rule stated falsely in the place people go to learn the rules is the shape
`CLAUDE.md`'s CI section was rewritten to close, and this was the same thing one directory over.

**What the key is actually for:** it records which pair the inventory in `puzzles/` belongs to, so a
VPS ingest step — which does not exist yet — can refuse a batch signed by a different one. That is what
would make `--ephemeral` batches safe to produce: signed by a pair that existed for one run, refused
without anyone having to remember they were only a test. ⚠️ **In the future tense, because the step is
not built.**

`puzzles/` — `manifest.json` names the current generation and the puzzles in it, and is signed the same
way. A signature per puzzle says each puzzle is genuine; only the manifest signature says the *set* is.
