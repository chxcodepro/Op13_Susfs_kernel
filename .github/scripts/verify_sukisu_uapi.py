import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from sync_sukisu_versions import release_version


def parse_uapi_version(source):
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)
    patterns = [
        r"DECLARE\(\s*__u32\s*,\s*KERNEL_SU_UAPI_VERSION\s*,\s*([0-9]+)\s*\)",
        r"\bKERNEL_SU_UAPI_VERSION\s*=\s*([0-9]+)\s*;",
        r"(?m)^\s*#define\s+KERNEL_SU_UAPI_VERSION\s+([0-9]+)\s*$",
    ]
    versions = [int(match) for pattern in patterns for match in re.findall(pattern, source)]
    if len(versions) != 1 or versions[0] <= 0:
        raise ValueError("Expected exactly one positive KERNEL_SU_UAPI_VERSION declaration")
    return versions[0]


def driver_uapi(kernel_dir, allow_legacy=False):
    candidates = [
        kernel_dir / "include/uapi/supercall.h",
        kernel_dir.parent / "uapi/supercall.h",
    ]
    for header in candidates:
        if header.is_file():
            source = header.read_text(encoding="utf-8-sig")
            if allow_legacy and "KERNEL_SU_UAPI_VERSION" not in source:
                return None
            return parse_uapi_version(source)
    if allow_legacy:
        return None
    raise ValueError(f"No driver UAPI header under {kernel_dir}")


def github_json(path):
    url = "https://api.github.com/repos/SukiSU-Ultra/SukiSU-Ultra/" + path
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "op13-sukisu-uapi-check",
    }
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def manager_tag_for_version(version):
    if not re.fullmatch(r"[0-9]{5,}", version) or int(version) <= 0:
        raise ValueError("Invalid Manager versionCode")
    page = 1
    while True:
        releases = github_json(f"releases?per_page=100&page={page}")
        for release in releases:
            try:
                candidate = release_version(release)
            except ValueError:
                continue
            if candidate == version:
                return release["tag_name"]
        if len(releases) < 100:
            break
        page += 1
    raise ValueError(f"No official stable Manager release matches versionCode {version}")


def manager_uapi(tag):
    payload = github_json("contents/uapi/supercall.h?ref=" + quote(tag, safe=""))
    source = base64.b64decode(payload["content"]).decode("utf-8-sig")
    return parse_uapi_version(source)


def extension_contract(source):
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)
    versions = re.findall(
        r"(?m)^\s*#define\s+KSU_EXTENSION_API_VERSION\s+([0-9]+)[uU]?\s*$", source
    )
    if "KSU_EXTENSION_API_VERSION" in source and (len(versions) != 1 or int(versions[0]) <= 0):
        raise ValueError("Expected one positive KSU_EXTENSION_API_VERSION definition")
    return {
        "api": int(versions[0]) if versions else 0,
        "version_spoof": bool(re.search(r"\bKSU_EXTENSION_VERSION_SPOOF\s*=\s*5\b", source)),
    }


def manager_extensions(tag):
    try:
        payload = github_json("contents/uapi/extension.h?ref=" + quote(tag, safe=""))
    except HTTPError as error:
        if error.code != 404:
            raise
        return extension_contract("")
    return extension_contract(base64.b64decode(payload["content"]).decode("utf-8-sig"))


def driver_extensions(kernel_dir):
    for header in (kernel_dir / "include/uapi/extension.h", kernel_dir.parent / "uapi/extension.h"):
        if header.is_file():
            return extension_contract(header.read_text(encoding="utf-8-sig"))
    return extension_contract("")


def verify(kernel_dir, tag="", manager_version=""):
    if tag and manager_version:
        raise ValueError("Choose either a Manager tag or versionCode")
    if manager_version:
        tag = manager_tag_for_version(manager_version)
    actual = driver_uapi(kernel_dir, allow_legacy=not tag)
    expected = manager_uapi(tag) if tag else None
    if expected is not None and actual != expected:
        raise ValueError(
            f"SukiSU UAPI mismatch: driver={actual}, Manager {tag}={expected}. "
            "Select a compatible driver/SUSFS pair; changing KSU_VERSION is not an interface upgrade."
        )
    extensions = driver_extensions(kernel_dir) if tag else {"api": None, "version_spoof": False}
    required = manager_extensions(tag) if tag else None
    if required and required["version_spoof"] and not extensions["version_spoof"]:
        raise ValueError(
            f"SukiSU extension mismatch: driver={extensions}, Manager {tag}={required}. "
            "Apply the v4.3 extension backport or select a compatible source/Manager pair."
        )
    return {
        "kernel_uapi": actual,
        "manager_uapi": expected,
        "manager_tag": tag,
        "manager_version": manager_version or None,
        "kernel_extension_api": extensions["api"],
        "manager_extension_api": required["api"] if required else None,
        "kernel_version_spoof": extensions["version_spoof"],
        "mode": "manual-checked" if manager_version else "auto" if tag else "manual-unchecked",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-dir", type=Path, required=True)
    manager = parser.add_mutually_exclusive_group()
    manager.add_argument("--manager-tag", default="")
    manager.add_argument("--manager-version", default="")
    args = parser.parse_args()
    try:
        result = verify(args.kernel_dir.resolve(), args.manager_tag, args.manager_version)
    except (OSError, ValueError, KeyError) as error:
        print(f"SukiSU compatibility check failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
