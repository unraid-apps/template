#!/usr/bin/env python3
"""Decide which upstream tags the wrapper must (re)build.

Reads the public tag list of the upstream image on GHCR, keeps stable
semver tags (vX.Y.Z, no prerelease suffix) at or above MIN_UPSTREAM_VERSION,
resolves each tag's manifest digest and compares it with versions.json.

A tag is scheduled when
  * it has never been built,
  * upstream re-pushed it (digest changed), or
  * it is the newest tag and the wrapper itself changed (WRAPPER_REVISION).

Outputs (GITHUB_OUTPUT when set, otherwise stdout):
  build=<json list of tags, oldest first>
  latest=<the tag that should carry :latest after this run>
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request

UPSTREAM = os.environ.get("UPSTREAM_IMAGE", "ghcr.io/tashfeenahmed/freellmapi")
MIN_VERSION = os.environ.get("MIN_UPSTREAM_VERSION", "v0.16.0")
VERSIONS_FILE = os.environ.get("VERSIONS_FILE", "versions.json")
WRAPPER_REVISION = os.environ.get("WRAPPER_REVISION", "")
FORCE_TAG = os.environ.get("FORCE_TAG", "").strip()
MAX_BUILDS = int(os.environ.get("MAX_BUILDS_PER_RUN", "10"))

STABLE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
ACCEPT = ", ".join(
    [
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    ]
)


def semver(tag: str) -> tuple[int, int, int]:
    m = STABLE.match(tag)
    if not m:
        raise ValueError(tag)
    return tuple(int(x) for x in m.groups())  # type: ignore[return-value]


def registry_parts(image: str) -> tuple[str, str]:
    host, _, path = image.partition("/")
    return host, path


def anonymous_token(host: str, repo: str) -> str:
    url = f"https://{host}/token?scope=repository:{repo}:pull"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)["token"]


def get(url: str, token: str, accept: str | None = None, method: str = "GET"):
    req = urllib.request.Request(url, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if accept:
        req.add_header("Accept", accept)
    return urllib.request.urlopen(req, timeout=60)


def list_tags(host: str, repo: str, token: str) -> list[str]:
    tags: list[str] = []
    url = f"https://{host}/v2/{repo}/tags/list?n=1000"
    while url:
        with get(url, token) as resp:
            data = json.load(resp)
            tags.extend(data.get("tags") or [])
            link = resp.headers.get("Link", "")
        nxt = re.search(r"<([^>]+)>;\s*rel=\"next\"", link)
        url = urllib.parse.urljoin(f"https://{host}", nxt.group(1)) if nxt else None
    return tags


def digest_of(host: str, repo: str, tag: str, token: str) -> str:
    with get(f"https://{host}/v2/{repo}/manifests/{tag}", token, ACCEPT, method="HEAD") as resp:
        digest = resp.headers.get("Docker-Content-Digest")
    if not digest:
        raise RuntimeError(f"no digest header for {repo}:{tag}")
    return digest


def main() -> int:
    host, repo = registry_parts(UPSTREAM)
    token = anonymous_token(host, repo)

    stable = [t for t in list_tags(host, repo, token) if STABLE.match(t)]
    stable = [t for t in stable if semver(t) >= semver(MIN_VERSION)]
    stable.sort(key=semver)
    if not stable:
        print(f"no stable upstream tags >= {MIN_VERSION}", file=sys.stderr)
        return 1

    try:
        with open(VERSIONS_FILE, encoding="utf-8") as fh:
            known: dict = json.load(fh).get("versions", {})
    except FileNotFoundError:
        known = {}

    newest = stable[-1]
    to_build: list[str] = []
    digests: dict[str, str] = {}
    for tag in stable:
        digest = digest_of(host, repo, tag, token)
        digests[tag] = digest
        entry = known.get(tag)
        reason = None
        if FORCE_TAG and tag == FORCE_TAG:
            reason = "forced"
        elif entry is None:
            reason = "new"
        elif entry.get("upstream_digest") != digest:
            reason = "upstream digest changed"
        elif tag == newest and WRAPPER_REVISION and entry.get("wrapper_revision") != WRAPPER_REVISION:
            reason = "wrapper changed"
        if reason:
            print(f"{tag}: {reason}", file=sys.stderr)
            to_build.append(tag)
        else:
            print(f"{tag}: up to date", file=sys.stderr)

    if len(to_build) > MAX_BUILDS:
        # Newest first so :latest is always right; older tags follow next run.
        to_build = sorted(to_build, key=semver)[-MAX_BUILDS:]

    built_or_known = [t for t in stable if t in known or t in to_build]
    latest = max(built_or_known, key=semver) if built_or_known else newest

    out = {
        "build": json.dumps(to_build),
        "latest": latest,
        "digests": json.dumps({t: digests[t] for t in to_build}),
    }
    dest = os.environ.get("GITHUB_OUTPUT")
    lines = [f"{k}={v}" for k, v in out.items()]
    if dest:
        with open(dest, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
