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

`puzzles/` — **the served root, produced by `publish.rotate` and not by hand.** Since E1 it holds
exactly what the VPS will hold:

```
today.json       {"date", "puzzle_id", "generation", "schema", "signature"}   signed at generation
yesterday.json   the same, for the rollover window; legitimately absent on the calendar's first day
<puzzle_id>.json the two public packages, flat -- never <generation>/<id>.json
manifest.json    {"schema", "puzzles"} -- the two ids that are public, written from the files placed
```

⚠️⚠️ **It held six packages until 2026-08-23 and `docs/calendar.md` allows two.** Nothing had escaped —
there is no VPS yet — but the tree the browser reads is the one the access model is about, and it was the
model inverted. The six are a *private* reference inventory now, under `forge/reference-inventory/`,
which is gitignored the way `forge/inventory/` is; the rotation publishes two of them here.

⚠️ **So development and production draw from the same population by construction rather than by
resemblance.** What the browser loads on the laptop is byte-for-byte what it loads on the VPS, placed by
the same executable. Rebuild it with:

```
uv run python scripts/write_reference_puzzles.py          # in forge/, writes the private inventory
uv run python -m publish --inventory ../forge/reference-inventory \
                        --public ../serve/data/puzzles --date 2026-09-02
```

⚠️ **`--date` is fixed on purpose.** A committed development tree dated by the clock goes stale the next
morning, and client-side staleness is undetectable by design (`serve/ui/phone/daily.js`) — so it would
read as a defect nobody can locate.

**The manifest is signed the same way as the packages.** A signature per puzzle says each puzzle is
genuine; only the manifest signature says the *set* is. ⚠️ The **public** manifest the rotation writes is
not signed and does not need to be: it is derived from the files actually placed, and each of those
carries its own signature and its own dated pointer.
