# Agent Note: Download SukiSU CI binaries through the asset API

Status: implemented

## Problem

Builds [42471010836](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/42471010836)
and [42471521043](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/42471521043)
stop in Sync kernel sources: the public clang-r510928.zip URL returns HTTP 504
and aria2 exits with code 29. The tag/name match official Release metadata and
the earlier successful build's configuration. The user can download locally.
A GET through the public URL also returns 504 on the inspection path, while
the official asset API follows a 302 and returns a one-byte range with HTTP 206.

The same commit's [Lint Workflows run 42472215248](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/42472215248)
also fails during binary download. The upstream actionlint bootstrap script
requests actionlint_1.7.12_linux_amd64.tar.gz from the public release URL, receives
107 bytes and passes that non-gzip content to tar, which exits with code 2.

## Decision

The SukiSU workflow resolves both expected asset IDs from the existing
LLVM-Clang18-r510928 release tag, then downloads through the official asset
API with Accept: application/octet-stream. Clang and build-tools use the same
route, authentication and retry policy. Existing archive names, extraction
paths and the toolchain release input keep their meanings.

curl follows redirects and retries transient failures, including HTTP 504,
up to five times with a five-second delay and a 300-second retry-start window.
The workflow's scoped GitHub token authenticates API requests; curl's ordinary
cross-host redirect behavior strips Authorization on the asset-storage host.
jq -e requires exactly one positive numeric ID for each expected asset; missing,
ambiguous or malformed IDs stop before downloading. curl -f and the existing
unzip commands preserve HTTP/archive failure handling. Release metadata is
retained in the debug artifact. Other kernel build lanes retain their current
download paths.

The actionlint step uses the same API/retry policy. It keeps the bootstrap's
latest-stable selection, resolves the unique Linux amd64 tarball ID, downloads
with HTTP failure handling and extracts only actionlint. The existing linter
arguments and yamllint step stay unchanged.

The active-note audit finds no earlier toolchain-download decision. The
[v4.3 backport](../feature/2026-11-08-sukisu-v430-extensions.md) owns the kernel
adaptation; this decision owns the preceding download-stage blocker.

## Alternatives considered

- Retry the unchanged public URL: preserves aria2 throughput, but two builds
  and a direct GET fail at that entry point while the official API responds.
- Hardcode the observed asset IDs: shortest URL edit, but breaks the existing
  release-tag selection when a toolchain release changes or an asset is replaced.

## Consequences

The workflow keeps its selected compiler and switches the failing entry point.
It uses the already-installed curl and jq, with no downloader script or new
dependency. Official API availability and permissions remain prerequisites.

The user-started [kernel run 42472248698](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/42472248698)
passes full toolchain transfer/extraction, kernel compilation, packaging and
artifact upload. Its compatibility report records UAPI 6/6, extension ABI 2/2
and kernel_version_spoof=true for Manager v4.3.0-r2 (41150). The resulting
artifact is OP13-SUKISU-CCTV18-INLINE-STOCKLIKE-v114-22. Modified YAML/shell
receive static review under the user's review-only rule. Source publication
triggers the existing lint workflow; no extra test suite or kernel build is
started locally. Device boot and version-customization persistence remain
unverified.

References: [GitHub asset download](https://docs.github.com/en/rest/releases/assets#get-a-release-asset),
[curl retry behavior](https://curl.se/docs/manpage.html#--retry).
