import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.request import Request, urlopen


RELEASE_API = "https://api.github.com/repos/SukiSU-Ultra/SukiSU-Ultra/releases/latest"
WORKFLOW = Path(__file__).resolve().parents[1] / "workflows" / "Build SukiSU_Ultra.yml"
COMPATIBILITY_VERSIONS = ("40900", "40796")


def release_version(release):
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("Expected an official stable release")
    if not release.get("tag_name"):
        raise ValueError("Release has no tag_name")
    names = [asset.get("name", "") for asset in release.get("assets", [])]
    apks = [name for name in names if re.search(r"\.apk$", name, re.I)]
    preferred = [name for name in apks if re.match(r"^SukiSU_", name, re.I)]
    apks = preferred or apks
    for name in apks:
        match = re.search(r"[_-]([0-9]{5,})-release\.apk$", name)
        if match and int(match[1]) > 0:
            return match[1]
    for name in apks:
        matches = re.findall(r"[0-9]{5,}", name)
        if matches and int(matches[-1]) > 0:
            return matches[-1]
    raise ValueError("No Manager APK versionCode found in official release assets")


def latest_release():
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "op13-sukisu-version-sync",
    }
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(RELEASE_API, headers=headers), timeout=30) as response:
        return json.load(response)


def update_choices(source, version):
    if not re.fullmatch(r"[0-9]{5,}", version) or int(version) <= 0:
        raise ValueError("Invalid versionCode")
    newline = "\r\n" if "\r\n" in source else "\n"
    normalized = source.replace("\r\n", "\n")
    blocks = list(re.finditer(
        r"(?ms)^      sukisu_driver_version:\n.*?(?=^      [A-Za-z_]\w*:\n|\Z)",
        normalized,
    ))
    if len(blocks) != 1:
        raise ValueError("Expected exactly one sukisu_driver_version input")
    match = blocks[0]
    block = match[0]
    if not re.search(r"(?m)^        type: choice$", block):
        raise ValueError("sukisu_driver_version is not a choice input")
    description = (
        "auto：构建时获取官方最新稳定版；"
        f"当前已同步：{version}。源码提交单独选择。"
    )
    block, descriptions = re.subn(
        r"(?m)^        description: [^\n]*$",
        lambda _: "        description: " + json.dumps(description, ensure_ascii=False),
        block,
    )
    versions = dict.fromkeys((version, *COMPATIBILITY_VERSIONS))
    options = "        options:\n          - auto\n" + "".join(
        f'          - "{item}"\n' for item in versions
    )
    block, choices = re.subn(
        r"(?m)^        options:\n(?:          - [^\n]*\n)+",
        lambda _: options,
        block,
    )
    if descriptions != 1 or choices != 1:
        raise ValueError("Unrecognized version input layout; workflow left unchanged")
    updated = normalized[:match.start()] + block + normalized[match.end():]
    return updated.replace("\n", newline)


def sync_workflow(path, release, check=False):
    version = release_version(release)
    original = path.read_bytes().decode("utf-8")
    updated = update_choices(original, version)
    changed = original != updated
    if changed and not check:
        path.write_bytes(updated.encode("utf-8"))
    return version, changed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        version, changed = sync_workflow(WORKFLOW, latest_release(), args.check)
    except (OSError, ValueError) as error:
        print(f"Version sync failed: {error}", file=sys.stderr)
        return 1
    print(f"Latest official stable versionCode: {version}")
    print("Dropdown needs an update" if args.check and changed else
          "Dropdown updated" if changed else "Dropdown already current")
    if not args.check and (output := os.environ.get("GITHUB_OUTPUT")):
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"version={version}\nchanged={str(changed).lower()}\n")
    return int(args.check and changed)


if __name__ == "__main__":
    sys.exit(main())
