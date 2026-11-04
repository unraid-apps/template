#!/usr/bin/env python3
"""Record a successful build in versions.json and regenerate VERSIONS.md.

usage: record-version.py <tag> <upstream_digest> <wrapper_revision> <our_digest>
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys

VERSIONS_FILE = os.environ.get("VERSIONS_FILE", "versions.json")
VERSIONS_MD = os.environ.get("VERSIONS_MD", "VERSIONS.md")
UPSTREAM_REPO = os.environ.get("UPSTREAM_REPO", "tashfeenahmed/freellmapi")
OUR_IMAGE = os.environ.get("OUR_IMAGE", "ghcr.io/unraid-apps/freellmapi")
STABLE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def semver(tag: str):
    return tuple(int(x) for x in STABLE.match(tag).groups())


def main() -> int:
    tag, upstream_digest, wrapper_revision, our_digest = sys.argv[1:5]
    try:
        with open(VERSIONS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        data = {"versions": {}}
    data.setdefault("versions", {})[tag] = {
        "upstream_digest": upstream_digest,
        "wrapper_revision": wrapper_revision,
        "image_digest": our_digest,
        "built_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
    }
    data["versions"] = dict(sorted(data["versions"].items(), key=lambda kv: semver(kv[0]), reverse=True))
    with open(VERSIONS_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")

    rows = [
        "# Mirrored versions",
        "",
        f"Wrapper builds of [{UPSTREAM_REPO}](https://github.com/{UPSTREAM_REPO}) published as `{OUR_IMAGE}`.",
        "Maintained automatically by the sync workflow; the newest entry also carries the `latest` tag.",
        "",
        "| Tag | Built (UTC) | Upstream release | Wrapper rev | Upstream digest |",
        "| --- | --- | --- | --- | --- |",
    ]
    for t, e in data["versions"].items():
        rows.append(
            f"| `{t}` | {e['built_at']} | [notes](https://github.com/{UPSTREAM_REPO}/releases/tag/{t}) "
            f"| `{e['wrapper_revision']}` | `{e['upstream_digest'][:19]}…` |"
        )
    with open(VERSIONS_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(rows) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
