# Agent Note: Backport SukiSU v4.3 extensions onto the guarded builtin lane

Status: implemented

## Problem

The ce75122 builtin pin has UAPI 6 but predates version_spoof and extension
ABI discovery. Stamping the latest Manager version leaves its new settings
without a kernel handler. The latest stable releases are v4.3.0-r1/41140 and
v4.3.0-r2/41150; their source comparisons also contain relevant kernel fixes.

## Decision

The default lane keeps ce75122, CCTV18 3f6aae5, the existing static-key/startup
repair and KPM Image pipeline. A separate pinned-source patch backports upstream
version_spoof, extension ABI 2 enumeration, reference balancing, rate-limited
logging and SELinux parsing/generation fixes. Extension requirements are checked
alongside UAPI; the build reports them and checks the linked version-spoof IO
handler before packaging. The Manager dropdown tracks 41150 and preserves
41140 as the matching v4.3.0-r1 fallback.

The note audit finds partial overlap with the [native-UAPI decision](../bug-fix/2026-10-28-sukisu-native-uapi6.md)
and [startup-safety decision](../bug-fix/2026-10-28-sukisu-startup-safety.md):
they keep ownership of the pin and disabled startup hooks. The
[version-dropdown decision](../process/2026-10-16-sukisu-version-dropdown.md)
keeps ownership of release synchronization. Other active notes are unrelated.

The [adaptation report](../../../../docs/SUKISU_v4.3_ADAPTATION.md) records exact
upstream commit links and the r1/r2 comparison. The extension ioctl remains
32 bytes; API-0 callers retain ABI-1 behavior. The verifier's untagged legacy
entry point performs no new extension parsing or remote lookup. New checked
calls require version_spoof when that Manager declares it. Both extension ABI
versions are reported; the Manager's header declares its supported maximum,
and its ABI-0/1 fallback remains usable when the requested handler exists.

## Alternatives considered

- Advance builtin to its current head: gets the features together, but also
  changes SUSFS priority-UID, KPM bridge and startup behavior. Retain the
  existing pair and backport the required contracts.
- Add version_spoof alone: enables the settings, but leaves the Manager's
  kernel-driven extension enumeration and recent kernel fixes behind.

## Consequences

The default build carries the feature implementation along with its reported
version. Missing extension support stops a checked build even when UAPI matches.
The fixed source pair avoids importing unrelated priority-UID/KPM migrations.
Main/LKM's r1 BTF-offset path stays unchanged in this source-built builtin lane;
r2 has no kernel changes. Existing archives still require replacement builds.

The upstream patch series applies cleanly after the guarded ce75122 patch.
Review covers changed callers, handler registration, unity-build inclusion,
UAPI layouts, reference ownership, policy generation and workflow ordering.
The SELinux-generation adaptation passes the new sequence in both 5.10+ policy
paths and retains zero in the older branches. Added fixtures cover missing
extensions despite UAPI equality, parsing, HTTP failures and legacy entry points.
No tests or kernel compilation are run under the user's review-only rule;
device boot/save/reset/reboot-persistence remain unverified. Source publication
does not run a kernel build or change the phone configuration.
