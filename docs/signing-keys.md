# The signing key

⚠⚠ **`publish/` holds no key and signs nothing.** Every per-date pointer is signed at generation, so the daily rotation is a copy — which is what lets it run on the VPS without a private key ever being there. `docs/calendar.md` records the decision; this is the sentence that keeps it from being eroded by a future step that finds signing convenient.

The forge signs every package and every manifest with an Ed25519 private key. `serve` verifies with the
public half and **cannot sign** — that asymmetry is the point, and it is what an HMAC could not express:
every verifier of a MAC is also a signer, so a shared secret on the VPS *was* the forge's signing
authority (§33).

**This key is generated on the operator's machine and nowhere else.** Not in a session, not in CI, not
on the VPS. A private key that has existed somewhere other than the forge is not a forge key any more,
whatever is done with it afterwards.

---

## Generating it

Run this on the laptop, from `forge/`. It writes the private half to a file outside the repository and
prints the public half.

```bash
uv run python -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; import pathlib; k = Ed25519PrivateKey.generate(); p = pathlib.Path.home() / '.boxscorepuzzle-signing-key'; p.write_text(k.private_bytes_raw().hex(), encoding='utf-8'); print('private key written to', p); print('public key:', k.public_key().public_bytes_raw().hex())"
```

⚠️ **`uv run python`, not `.venv/Scripts/python.exe`.** The venv's executable is a launcher pointing at a uv-managed interpreter, and it resolves in some shells and not others — it works from bash and fails from PowerShell with *did not find executable*. `uv run` asks uv to resolve the interpreter, which is the thing that knows where it is. If `uv` is not on the PATH it is under `%LOCALAPPDATA%\Microsoft\WinGet\Packages\astral-sh.uv_*\uv.exe`.

**64 hexadecimal characters each.** The private half is the file's whole contents; the public half is
what the command prints.

### Setting it for a publishing run

**Nothing.** The writer reads `~/.boxscorepuzzle-signing-key` at publish time, so the key is in one
process for the length of one publish and in no environment at all.

`BOXSCORE_SIGNING_KEY` still wins if it is set, because an export is a deliberate instruction — for a
key kept somewhere else, or a one-off run with a different pair. For the current PowerShell session:

```bash
$env:BOXSCORE_SIGNING_KEY = (Get-Content "$HOME\.boxscorepuzzle-signing-key" -Raw).Trim()
```

### ⚠️⚠️ Never make it permanent, and remove it if it already is

This document used to recommend `[Environment]::SetEnvironmentVariable(..., "User")`, *so a publish
never fails for a forgotten shell*. **Do not.** A User-scope variable is inherited by **every process
the account runs** — every `npm install` postinstall, every pip build hook, every script from every
sibling project on a machine that holds several. One compromised dependency, anywhere, reads
`os.environ` and takes it; whoever holds it can then sign inventory `serve` accepts.

**And this is the one secret here that cannot be rotated cheaply.** Rotating invalidates every
signature ever issued, so every package and every manifest has to be reissued (below). What the
permanent variable bought was avoiding a loud, fail-closed error that the writer raises by design —
**a permanent exposure to buy nothing**, and now it does not even buy that.

Check whether the variable is persisted, and clear it if so. PowerShell:

```bash
if ([Environment]::GetEnvironmentVariable("BOXSCORE_SIGNING_KEY","User")) { "User scope: SET" } else { "User scope: not set" }
```

```bash
[Environment]::SetEnvironmentVariable("BOXSCORE_SIGNING_KEY", $null, "User")
```

⚠️ **Clearing the variable does not un-expose a key that was already exposed.** If it sat in User scope
on a machine that has run untrusted install hooks, the conservative reading is that it may have been
read — and the answer to that is rotation, not deletion. That is a judgement about this machine's
history, not something a document can settle.

### Deriving the public half again

The public key is a function of the private one, so it never needs storing separately — but it does
need to be *read* to put it in the repository:

```bash
uv run python -c "from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; import os; print(Ed25519PrivateKey.from_private_bytes(bytes.fromhex(os.environ['BOXSCORE_SIGNING_KEY'])).public_key().public_bytes_raw().hex())"
```

---

## The rules, which are permanent

**The private key never enters Git.** Not the repository, not a versioned `.env`, not a fixture, not a
test. If it leaks, anyone can sign inventory that `serve` accepts, and §33's guarantee — that only the
forge produces puzzles — is gone. This is the reason `--fixtures` and the repository fallback were
**deleted** rather than made safe: a convenient key in the repository is the leak, already happened.

**It must be backed up somewhere other than the laptop.** It is the only secret in this project that
cannot be rotated cheaply: rotating it invalidates every signature ever issued, so every package and
every manifest has to be reissued. §33 already names the laptop as a single point of failure and Git as
the backup for everything else — this is the one thing Git cannot back up, so it needs its own copy
somewhere durable.

⚠️ **The public key does go in the repository.** `serve` needs it, and committing it is what records
which key pair the inventory belongs to. *Keys never go in Git* is the kind of rule that gets
over-applied to the half that should be there — the public half protects nothing by being secret and
protects the pairing by being written down.

**A key file is where the key is; an exported variable is an instruction.** `--ephemeral` refuses to
run when `BOXSCORE_SIGNING_KEY` is set — the two together do not say which trust domain was meant — and
**ignores the key file entirely**, because the file exists on every machine that has a key and weighing
it the same way would make `--ephemeral` impossible exactly where it is used.

**A missing key is an error, never a quieter mode.** The writer refuses to publish without
`BOXSCORE_SIGNING_KEY`. `--ephemeral` generates a throwaway pair for testing the pipeline; what it
produces is signed by a key that exists only for that run, so **`serve` refuses those packages by
itself** rather than on the strength of a comment. That is the difference between a mode that is safe
and one that cannot be mistaken for the real thing.

---

## Where it is used

| | |
|---|---|
| **Packages** | `sign()` over the published shape — keys sorted, separators compact, `signature` excluded. 128 hex characters |
| **The manifest** | signed the same way. A signature per puzzle says each puzzle is genuine; **only this says the *set* is**, and altering the manifest — omitting ids, pointing at a retained generation, pointing at nothing — breaks no package signature at all |
| **Verification** | `certify_for_publication()` takes the public key. `UNSIGNED` is the only explicit bypass and exists for tests and discovery, never for a publish path |
