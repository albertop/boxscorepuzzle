"""`keep` — the data layer. Devices, events, and later accounts and subscriptions.

`docs/data-layer.md` is the architecture and `docs/keep-api.md` is the surface. **Nothing here imports
`forge` or `serve`**: three tiers with independent lifecycles is what §33 asks for, and a shared import
is how that stops being true without anybody deciding it.
"""
