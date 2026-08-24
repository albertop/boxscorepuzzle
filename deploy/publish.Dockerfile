# The rotation's image. **F3, and it runs once a day and exits.**
#
# ⚠️⚠️ **A third image because `serve` cannot do this.** `serve` is nginx over a static tree; it has no
# Python and must not gain one. The rotation is the serving side's *executable* (`publish/`), and giving
# nginx a runtime so it could run a daily job would make the web server the thing that decides what is
# published.
#
# ⚠️⚠️ **It is not a service and has no health check.** It runs, prints what it did, and exits — the
# scheduler is what makes it daily, and its **exit code is the verdict**. A container that stayed up to
# "manage" a once-a-day task would be a supervisor nobody wrote, hiding a failure behind a green dot.
#
#     docker build -f deploy/publish.Dockerfile -t bxcpze-publish publish/
#
# ⚠️ Built from `publish/` rather than the repository root, and that is the boundary rather than a
# convenience: this build **cannot** copy `forge/`, because it is not in its context. §33 enforced by
# the shape of the command, the same way `keep`'s is.
#
# ⚠️⚠️ **The inventory is NOT in this image and must never be.** It is five months of signed packages,
# it grows every batch, and it is the thing §16 protects. It arrives as a read-only mount, so adding a
# month is a file transfer rather than a rebuild — and an image that carried it would ship the whole
# inventory on every deploy of a fifty-line program.

# ⚠️ `slim` rather than `alpine`: `publish` has no compiled dependency today, but `keep` is on this base
# for a reason that could arrive here too, and two Python bases in one deployment is two sets of security
# updates to track for no benefit.
FROM python:3.13-slim

# ⚠️ **`--frozen`, so the image is the lockfile's answer and not today's index.** Two builds of one
# commit must be one image; the lockfile is the reproducibility guarantee this project commits.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# ⚠️⚠️ **Unprivileged, and it writes.** Unlike `keep`, this container's whole job is to put files in the
# served root, so the public path is mounted writable and owned by this uid. The inventory is mounted
# **read-only**: the rotation reads generations and never alters them, and a mount that cannot be written
# is a stronger statement of that than a code review.
# ⚠️⚠️ **10002 is agreed with `deploy/serve.Dockerfile`, which chowns the published path to it.** A
# new named volume takes its ownership from the image that first populates it -- `serve` -- so the two
# have to name the same number or the rotation cannot write. Asserted by
# `forge/tests/test_the_images_build.py`; the first version had no agreement and failed with
# `PermissionError` the first time it ran.
RUN adduser --disabled-password --gecos "" --uid 10002 publish
USER publish

ENV PATH="/app/.venv/bin:$PATH"

# ⚠️ **The default command is the real one**, so `docker run bxcpze-publish` with nothing else rotates.
# The scheduler names it explicitly anyway -- a job whose command lives only in a label is a job nobody
# can reproduce by hand when it fails at four in the morning.
#
# ⚠️ **No `--date`.** `serving_date()` decides, server-side, once. `--date` exists to reproduce a day,
# never to choose one, and a scheduled job that named a date would publish the same day for ever.
ENTRYPOINT ["python", "-m", "publish"]
CMD ["--inventory", "/srv/inventory", "--public", "/srv/public"]
