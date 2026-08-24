# The image that serves the game. **F1.1, and it holds `serve/` and nothing else.**
#
# ⚠️⚠️ **`forge/` must never reach the VPS** (§16, §33). It holds the generator and the
# human-solvability guarantee, which is trade secret, and no build stage here may copy it — not for a
# lockfile, not for a shared module, not for convenience. That is the half of §33 that is permanent.
#
# ⚠️ **This is nginx and nothing else: there is no application to run.** `serve/` is static files, which
# is §23's whole point — the day's puzzle survives every backend being down because serving it needs no
# backend. An image with a Python process in it would be a process whose failure takes the game away.
#
#     docker build -f deploy/serve.Dockerfile -t bxcpze-serve .
#
# ⚠️ Built from the repository root, because it copies two sibling directories: the served tree and the
# server block that describes how to serve it.

# ⚠️ **Pinned to a minor, not to `alpine` or `stable`.** A floating tag means the image the tests built
# and the image production runs can be different builds of different nginx, and the difference shows up
# only as behaviour. Moving it is a deliberate edit and `forge/tests/test_the_images_build.py` starts
# what it produced.
FROM nginx:1.30.4-alpine

# ⚠️⚠️ **Nothing here is a secret and nothing here may become one.** The image holds published puzzles,
# the client, and the **public** half of the signing key — which belongs in the tree, because it records
# which pair the inventory belongs to and protects nothing by being hidden (`docs/signing-keys.md`).
# The private key never leaves the laptop; the shared token arrives as an environment variable at run
# time and is never baked in.
COPY serve/ /srv/serve/
# ⚠️⚠️⚠️ **The TEMPLATE, into `templates/`, and this named the old file and the wrong destination.**
# The config was renamed to `.conf.template` when `${KEEP_SHARED_TOKEN}` arrived and **this line was not
# carried with it** — so the image could not be built at all, and had it built, the placeholder would
# have reached nginx unresolved: `conf.d/` is not the path the entrypoint substitutes.
#
# ⚠️⚠️ **It survived because this image had never been built.** `keep`'s was built and probed; this one
# was covered by tests that **mount the template directly** — the product's config by a path the product
# does not use. v41-P1-01, and one more instance of an instrument answering the near neighbour of its
# question. `forge/tests/test_the_images_build.py` builds it now.
COPY deploy/nginx/boxscorepuzzle.conf.template /etc/nginx/templates/default.conf.template

# ⚠️⚠️ **Unprivileged, and the port above 1024 is what makes that possible.** A container that starts as
# root to bind 80 and drops afterwards still has a root-owned start-up; binding 8080 needs nothing.
# nginx's own image ships an `nginx` user, so this is a switch rather than a new account.
#
# ⚠️ The directories nginx writes to have to be writable by that user, and the base image's `nginx.conf`
# also wants to write a pid file. Both are handed over rather than the process being given root back.
#
# ⚠⚠ **The pid line is rewritten by shape, not by its old value.** The first version replaced
# `/var/run/nginx.pid` and this image says `/run/nginx.pid` — so the `sed` matched nothing, the build
# succeeded, and the container **died on start with `open() "/run/nginx.pid" failed`**. A substitution
# that finds nothing is silent, and a Dockerfile has no way to notice: only running it does.
# ⚠️ The stock `default.conf` is removed: the entrypoint writes ours beside it, and two server blocks
# on one port means whichever nginx reads first wins.
#
# ⚠️⚠️ **The file-descriptor ceiling, and the startup log is what asks for it.** The stock image reports
# `getrlimit(RLIMIT_NOFILE): 1024:524288` — a **soft** limit of 1024 descriptors per worker against a
# hard limit half a million. Every client connection is one descriptor and every proxied request to
# `keep` is a second, so 1024 is the real ceiling on concurrency and the hard limit is not the thing
# doing the limiting.
#
# `worker_rlimit_nofile` is nginx calling `setrlimit` on itself, bounded by the hard limit — so this
# alone raises it, with no privilege and no change on the host. `worker_connections` is raised beside it
# because a descriptor budget nothing is allowed to spend is not a budget.
#
# ⚠️ **8192 and 2048 are the operator's own numbers**, from the VPS's `/etc/nginx/nginx.conf`, which has
# run five sites for months. Matching them is deliberate: a second set of figures here would be a second
# opinion about the same machine, and nobody has measured this container to have a different one.
#
# ⚠️⚠️ **Every `sed` below is verified in the same layer, and this Dockerfile is why.** The pid line was
# rewritten from `/var/run/nginx.pid` when this image says `/run/nginx.pid` — the substitution matched
# nothing, **the build succeeded**, and the container died on start. A `sed` that finds nothing is
# silent and a Dockerfile has no way to notice. The `grep -q` calls turn that into a failed build.
# ⚠️⚠️ **The published path is owned by the uid that WRITES it, which is not this image's.** The
# rotation (`deploy/publish.Dockerfile`, uid 10002) is the only writer; nginx only reads, and 755 is
# enough for that. **Docker takes a new named volume's ownership from the image path it populates it
# from**, and that path is this one -- so if this image leaves it root-owned, the rotation cannot write
# and fails with `PermissionError` the first time it runs.
#
# ⚠️ **Found by running the rotation, not by reading either file.** `publish.Dockerfile` claimed in a
# comment that the public path was "mounted writable and owned by this uid" and nothing made it so.
# `forge/tests/test_the_images_build.py` now asserts the two agree, because a uid spelled in two
# Dockerfiles is two places encoding one fact.
RUN chown -R 10002:10002 /srv/serve/data/puzzles

RUN rm -f /etc/nginx/conf.d/default.conf \
 && chown -R nginx:nginx /var/cache/nginx /var/run /etc/nginx/conf.d /etc/nginx/templates \
 && sed -i 's|^user  nginx;|# user directive removed: this image runs as nginx already|' /etc/nginx/nginx.conf \
 && sed -i 's|pid *[^;]*;|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf \
 && sed -i 's|^worker_processes .*|worker_processes  auto;\nworker_rlimit_nofile  8192;|' /etc/nginx/nginx.conf \
 && sed -i 's|worker_connections  *[0-9]*;|worker_connections  2048;|' /etc/nginx/nginx.conf \
 && grep -q '^pid /tmp/nginx.pid;' /etc/nginx/nginx.conf \
 && grep -q '^worker_rlimit_nofile  8192;' /etc/nginx/nginx.conf \
 && grep -q 'worker_connections  2048;' /etc/nginx/nginx.conf \
 && ! grep -q '^user  nginx;' /etc/nginx/nginx.conf

USER nginx

EXPOSE 8080

# ⚠️ **A healthcheck that asks for a page, not for an open port.** `CLAUDE.md`: a wait loop's success
# condition is a real request. A container whose port is bound and whose server is not answering is
# exactly the state Docker would otherwise report as healthy — and it is the state the nginx probe hit
# in CI.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://127.0.0.1:8080/ || exit 1
