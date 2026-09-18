# Agent Note: Patch the published SukiSU Image with the KPM payload

Status: implemented

## Problem

The SukiSU workflow enabled `CONFIG_KPM=y` and published the compiler's raw
`Image` directly. SukiSU's source-level KPM entry points are intentional stubs;
the KernelPatch payload must hook them in the final image. A phone booted from
the old artifact therefore reported `Stub function called (sukisu_kpm_version)`
even though `/proc/config.gz` contained `CONFIG_KPM=y`.

The workflow also created the standalone Image checksum before any possible
post-build transformation. That makes it too easy for the published Image, its
checksum, and the Image embedded in AnyKernel3 to diverge.

## Decision

The SukiSU lane patches the compiled `Image` after the driver-version check and
before any public artifact is copied or hashed. It downloads `patch_linux` from
the official `SukiSU-Ultra/SukiSU_patch` repository at a pinned commit and
verifies the tool against a pinned SHA256 before execution. A KPM-enabled build
must produce a non-empty `oImage` whose hash differs from the raw compiler
output; otherwise the workflow fails instead of shipping a stub-only kernel.

The final standalone Image is copied and hashed only after that stage. The
AnyKernel3 package must contain an `Image` with the same SHA256, and both public
checksum files are verified before the job is considered successful.

The `sukisu_driver_version` dispatch input is a choice. `auto` queries the
latest official SukiSU release at run time and extracts the Manager APK
versionCode; known compatibility values remain selectable fallbacks. The kernel
source ref stays on the compile-tested default because automatically advancing
it can cross the SukiSU/SUSFS generation boundary.

## Alternatives considered

Running the unpinned `patch_linux` from the upstream default branch is the
shortest implementation and is used by some public workflows. It was rejected
because the executable could change between identical builds and because a
network response would become executable without an integrity check.

Automatically switching the SukiSU kernel source to the newest release tag was
also considered. It was rejected for this stable lane because the source and
SUSFS refs have an explicit compatibility contract; selecting the newest
Manager version number does not prove that a new kernel source generation still
links with the pinned SUSFS tree.

## Verification

The workflow parses as YAML with all 25 dispatch inputs and all build steps
present, and `git diff --check` reports no whitespace errors. The pinned
`SukiSU_patch` commit resolves to `547ae94bcaec53d030398f857950c64662043a5d`;
its `kpm/patch_linux` SHA256 is
`1bd00563e9d8fbbd11a16c0c1c59c5add406e6c5c92557def50f93d6f0aebe2d`.

A full kernel compile cannot be reproduced locally on the Windows host. The
next Actions run must still prove that the pinned patcher accepts this exact
6.6.118 Image, emits a different non-empty `oImage`, and passes the embedded
Image checksum comparison. A fresh phone boot is the final runtime check: the
manager must show a KPM version and `dmesg` must not report
`Stub function called (sukisu_kpm_version)`.

## Consequences

KPM-enabled artifacts are larger post-build images and require the pinned
KernelPatch download to remain available with the recorded hash. A deliberate
upstream patcher update now requires updating both its commit and SHA256.

In exchange, `CONFIG_KPM=y` can no longer be mistaken for a working KPM payload,
the published checksums describe the bytes users actually flash, and selecting
`auto` in the Actions form keeps the reported driver version aligned with the
latest official Manager release without manual number entry.
