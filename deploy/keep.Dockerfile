# The data layer's image. **F1.2, and its port is never published.**
#
# ⚠️⚠️ **Two lines of defence and the order matters** (`docs/data-layer.md` §4). The first is that
# nothing outside the Docker network can reach this at all — the port is not published, and the browser
# posts to `serve`, which proxies. The second is the shared token. **The token is not the first line and
# must never be relied on as one.**
#
# ⚠️ **No secret is built in.** `KEEP_SHARED_TOKEN` and `KEEP_DSN` arrive as environment variables at run
# time. `keep` refuses to start without either — a service that accepted everything because no token was
# configured is an open door that looks like a working deployment, which is why the refusal is at start-up
# rather than at the first request.
#
#     docker build -f deploy/keep.Dockerfile -t boxscorepuzzle-keep keep/
#
# ⚠️ Built from `keep/` rather than the repository root, and that is the boundary rather than a
# convenience: this build **cannot** copy `forge/`, `serve/` or anything else, because they are not in
# its context. §33 enforced by the shape of the command.

# ⚠⚠ **`slim` rather than `alpine`, and the reason is the driver.** `psycopg[binary]` ships manylinux
# wheels, which are glibc; on musl there is no wheel and the install falls back to building from source
# against a libpq that is not there. The image would have to grow a compiler to save a few megabytes.
FROM python:3.13-slim

# ⚠️⚠️ **`--frozen`, so the image is the lockfile's answer and not today's index.** The lockfile is the
# reproducibility guarantee this project commits for exactly this reason; resolving at build time would
# make two builds of one commit different images.
#
# ⚠⚠ **`keep` has exactly one runtime dependency and it was in the dev group until F1.** The comment
# justifying that read *"a dev extra because production installs it"*, which is circular: `keep` cannot
# start without a database. `--no-dev` produced a container that would have died on its first request.
# **The image is what surfaced it** — nothing else in the project installs `keep` the way production does.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY migrations/ ./migrations/
RUN uv sync --frozen --no-dev

# ⚠️⚠️ **Unprivileged, and created rather than reused.** The base image has no non-root user, so this
# makes one; running as root inside a container is not a boundary just because the container is one.
# Nothing here needs to write to the filesystem — the state is in Postgres — so the tree stays owned by
# root and readable, which is stricter than handing it over.
RUN adduser --disabled-password --gecos "" --uid 10001 keep
USER keep

ENV PATH="/app/.venv/bin:$PATH"

# ⚠️ **Not published in any compose file.** `EXPOSE` documents the port for whatever is on the same
# network; it does not open anything to the host, and F2's compose must not add `ports:` for it.
EXPOSE 8081

# ⚠️ The health endpoint, asked over HTTP for the same reason the other image's is: a bound port is not
# a working service. `docs/keep-api.md` names what it answers.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1:8081/health || exit 1

CMD ["python", "-m", "keep.main"]
