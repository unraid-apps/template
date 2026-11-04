#!/usr/bin/env python3
"""Validate Unraid Community Applications XML files.

usage: validate-template.py [--check-urls] [--allow-placeholders] <file.xml> [...]

--allow-placeholders skips the APPNAME/TODO check (for the starter repo only).

Checks well-formedness, the elements Community Applications and dockerMan
expect, Config attribute sanity, and (with --check-urls) that Icon and
TemplateURL answer over HTTP. Works for Docker templates (<Container>) and
repository profiles (<CommunityApplications>). Exit code 1 on any problem.
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

REQUIRED_CONTAINER = ["Name", "Repository", "Registry", "Network", "Support", "Project", "Overview", "Category", "Icon", "TemplateURL"]
RECOMMENDED_CONTAINER = ["WebUI", "Shell", "Privileged"]
CONFIG_ATTRS = ["Name", "Target", "Default", "Mode", "Description", "Type", "Display", "Required", "Mask"]
CONFIG_TYPES = {"Port", "Path", "Variable", "Label", "Device"}
DISPLAY = {"always", "advanced", "always-hide", "advanced-hide"}
BOOL = {"true", "false"}
TS_SERVE = {"", "no", "serve", "funnel"}


def url_ok(url: str) -> str | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "unraid-apps-validator"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status >= 400:
                return f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code in (403, 405):  # some hosts refuse HEAD; try GET
            try:
                with urllib.request.urlopen(url, timeout=20):
                    return None
            except Exception as e2:  # noqa: BLE001
                return str(e2)
        return f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return str(e)
    return None


def text(root: ET.Element, tag: str) -> str:
    el = root.find(tag)
    return (el.text or "").strip() if el is not None else ""


ALLOW_PLACEHOLDERS = False


def has_placeholders(root: ET.Element) -> bool:
    raw = ET.tostring(root, encoding="unicode")
    return "APPNAME" in raw or "TODO" in raw


def validate_container(root: ET.Element, path: str, check_urls: bool) -> list[str]:
    errors: list[str] = []
    for tag in REQUIRED_CONTAINER:
        if not text(root, tag):
            errors.append(f"missing or empty <{tag}>")
    for tag in RECOMMENDED_CONTAINER:
        if root.find(tag) is None:
            print(f"{path}: note: no <{tag}> element")
    if has_placeholders(root) and not ALLOW_PLACEHOLDERS:
        errors.append("placeholder text (APPNAME/TODO) still present")
    if len(text(root, "Overview")) < 80:
        errors.append("<Overview> is very short; CA shows it as the app description")
    if text(root, "Network") not in {"bridge", "host", "none"} and not text(root, "Network").startswith(("br", "eth", "bond", "custom")):
        print(f"{path}: note: unusual <Network> value '{text(root, 'Network')}'")
    if text(root, "Privileged") and text(root, "Privileged") not in BOOL:
        errors.append("<Privileged> must be true or false")

    ts = text(root, "TailscaleServe")
    if ts not in TS_SERVE:
        errors.append(f"<TailscaleServe> must be one of no|serve|funnel, got '{ts}'")
    if text(root, "TailscaleEnabled") and text(root, "TailscaleEnabled") not in BOOL:
        errors.append("<TailscaleEnabled> must be true or false")

    seen_targets: dict[str, str] = {}
    for i, cfg in enumerate(root.findall("Config"), 1):
        where = f"Config #{i} ({cfg.get('Name', '?')})"
        for attr in CONFIG_ATTRS:
            if attr not in cfg.attrib:
                errors.append(f"{where}: missing attribute {attr}")
        ctype = cfg.get("Type", "")
        if ctype not in CONFIG_TYPES:
            errors.append(f"{where}: Type must be one of {sorted(CONFIG_TYPES)}")
        if cfg.get("Display") not in DISPLAY:
            errors.append(f"{where}: Display must be one of {sorted(DISPLAY)}")
        for b in ("Required", "Mask"):
            if cfg.get(b) not in BOOL:
                errors.append(f"{where}: {b} must be true or false")
        if ctype == "Port" and cfg.get("Mode") not in {"tcp", "udp"}:
            errors.append(f"{where}: Port Mode must be tcp or udp")
        if ctype == "Path" and cfg.get("Mode") not in {"rw", "ro", "rw,slave", "ro,slave", "rw,shared", "ro,shared"}:
            errors.append(f"{where}: Path Mode must be rw/ro (optionally ,slave/,shared)")
        if cfg.get("Required") == "true" and not (cfg.text or "").strip() and not cfg.get("Default"):
            print(f"{path}: note: {where} is Required but has no default value (user must fill it)")
        key = f"{ctype}:{cfg.get('Target')}"
        if key in seen_targets:
            errors.append(f"{where}: duplicate Target for {ctype} '{cfg.get('Target')}'")
        seen_targets[key] = where

    if check_urls:
        for tag in ("Icon", "TemplateURL"):
            url = text(root, tag)
            if url:
                problem = url_ok(url)
                if problem:
                    errors.append(f"<{tag}> {url} not reachable: {problem}")
    return errors


def validate_profile(root: ET.Element, path: str, check_urls: bool) -> list[str]:
    errors: list[str] = []
    if has_placeholders(root) and not ALLOW_PLACEHOLDERS:
        errors.append("placeholder text (APPNAME/TODO) still present")
    if len(text(root, "Profile")) < 40:
        errors.append("<Profile> must be a non-empty description of the repository")
    for tag in ("Icon", "WebPage"):
        if not text(root, tag):
            errors.append(f"missing or empty <{tag}>")
    if check_urls:
        for tag in ("Icon", "WebPage", "Forum"):
            url = text(root, tag)
            if url:
                problem = url_ok(url)
                if problem:
                    errors.append(f"<{tag}> {url} not reachable: {problem}")
    return errors


def main(argv: list[str]) -> int:
    global ALLOW_PLACEHOLDERS
    check_urls = "--check-urls" in argv
    ALLOW_PLACEHOLDERS = "--allow-placeholders" in argv
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print(__doc__)
        return 2
    failed = False
    for path in files:
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as e:
            print(f"{path}: XML parse error: {e}")
            failed = True
            continue
        if root.tag == "Container":
            errors = validate_container(root, path, check_urls)
        elif root.tag in {"CommunityApplications", "Maintainer"}:
            errors = validate_profile(root, path, check_urls)
        else:
            errors = [f"unknown root element <{root.tag}>"]
        for e in errors:
            print(f"{path}: ERROR: {e}")
        if errors:
            failed = True
        else:
            print(f"{path}: OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
