import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


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


def manager_uapi(tag):
    url = (
        "https://api.github.com/repos/SukiSU-Ultra/SukiSU-Ultra/contents/"
        "uapi/supercall.h?ref=" + quote(tag, safe="")
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "op13-sukisu-uapi-check",
    }
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        payload = json.load(response)
    source = base64.b64decode(payload["content"]).decode("utf-8-sig")
    return parse_uapi_version(source)


def verify(kernel_dir, tag=""):
    actual = driver_uapi(kernel_dir, allow_legacy=not tag)
    expected = manager_uapi(tag) if tag else None
    if expected is not None and actual != expected:
        raise ValueError(
            f"SukiSU UAPI mismatch: driver={actual}, Manager {tag}={expected}. "
            "Select a compatible driver/SUSFS pair; changing KSU_VERSION is not an interface upgrade."
        )
    return {
        "kernel_uapi": actual,
        "manager_uapi": expected,
        "manager_tag": tag,
        "mode": "auto" if tag else "manual-unchecked",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kernel-dir", type=Path, required=True)
    parser.add_argument("--manager-tag", default="")
    args = parser.parse_args()
    try:
        result = verify(args.kernel_dir.resolve(), args.manager_tag)
    except (OSError, ValueError, KeyError) as error:
        print(f"UAPI compatibility check failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
