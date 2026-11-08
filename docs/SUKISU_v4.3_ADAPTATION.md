# SukiSU v4.3: release changes and OP13 builtin adaptation

Checked on 2026-11-08 against official release tags and commit comparisons.

## Latest two stable releases

| Release | Manager versionCode | Changes relative to its predecessor |
|---|---|---|
| [v4.3.0-r1](https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases/tag/v4.3.0-r1), November 3 | 41140 | Theme store, multiple sources, accounts, uploads, author pages, tag filters, trials and adaptive light/dark theme packages. Encrypted `.sukisu` packages, selective import/export, home-card backgrounds/stickers, text customization and saved appearance sections. WebUI File API and package-manager interface updates. Fixes duplicate dynamic-manager entries for multiple Android users and first-launch task closure. APK/icon trimming and an optional AI-assistant host bridge. Kernel changes include wrapped-file reference balancing, quieter/rate-limited logging, LKM SELinux inode/BTF compatibility and policy generation tracking. |
| [v4.3.0-r2](https://github.com/SukiSU-Ultra/SukiSU-Ultra/releases/tag/v4.3.0-r2), November 5 | 41150 | Theme comments/messages, author follows, content gating and one-time-key sign-in; parallel/distributed uploads, live transfer speed/ETA, faster transfers/import, broader import/export destinations and clear-before-overwrite restoration. Adaptive grid/film-strip browsing, retained browse position, theme links and an appearance-overlay configuration page. Rotating device credentials. All ten commits in this interval concern Manager; the comparison contains no kernel changes. |

Full source comparisons:

- [v4.3.0 → v4.3.0-r1: 40 commits](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/v4.3.0...v4.3.0-r1)
- [v4.3.0-r1 → v4.3.0-r2: 10 commits](https://github.com/SukiSU-Ultra/SukiSU-Ultra/compare/v4.3.0-r1...v4.3.0-r2)

The r1 release note highlights only the theme store, workflow repair and
first-launch fix; the table also covers its actual source comparison. The AI
commit provides a host bridge; visible assistant features depend on a provider
module/AAR being included in the Manager build.

## Why a freshly built kernel still lacked version customization

[Version customization (#1023)](https://github.com/SukiSU-Ultra/SukiSU-Ultra/pull/1023)
first shipped in the v4.3.0 base release. This build lane pins builtin
`ce75122bec7423e0f1fa06e3e9a174085c5231ab`, which precedes its implementation.
Automatic Manager selection overwrites `KSU_VERSION`, while the pinned source
continues to lack extension ID 5 and its IO handler. UAPI 6 equality alone
therefore passed the old compatibility check with this feature missing.

The existing source pin remains paired with CCTV18 SUSFS `3f6aae5`. The new
`sukisu-builtin-v4.3-extensions.patch` applies after the static-key/startup patch
only for that exact default SukiSU commit.

The verifier requires version-spoof support for a Manager that declares it.
Extension ABI values are reported separately: Manager can negotiate its older
ABI-0/1 fallback, so its header's maximum ABI is preserved as informational.

## What the builtin patch carries

| Change | Upstream basis | Integration |
|---|---|---|
| Version customization | [a0fd2beb](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/a0fd2beb78e3c3969137742fbabc7088398451f8), corrected by [fbc67d00](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/fbc67d004b3b68723e91dd86d50dead1120b4a9a) | Kernel GET/SET/RESET/WIPE, build defaults, mutex-protected overrides and length/mask validation; unity-build inclusion, handler registration and current/legacy/full-version response hooks. Official Manager/ksud already supplies persistence and boot restoration. |
| Capability bits and extension ABI 2 | [b5917072](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/b59170724cdc05bf5dee8d8a8b182c5f1ddd60e3), [0289fe99](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/0289fe99ab593c92f349360176ab5301d2986542) | ABI probe, handler enumeration, caller-version checks and validated capabilities. The ioctl envelope remains 32 bytes; legacy callers with API 0 retain ABI-1 behavior. |
| SELinux hide parsing | [85d3b048](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/85d3b0483df224f1dcf6f2880b3181d3f2ca4e0f) | Backup/live policy fields are parsed together, with policy-local validation and retry after `-ESTALE`. The existing kernel policy-query guard remains unchanged. |
| Wrapped-file reference leak | [cbfdd5e4](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/cbfdd5e4a359e2ff43eee8136eff1d5cbc78863d) | Drop the extra successful-open reference after the wrapper takes its own reference; the failure path retains its close. |
| Atomic/frequent-path logging | [f06b756d](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/f06b756d3106a47d405d665e55d9750c85d03a06) | Remove allow-list console dumps and rate-limit ioctl messages. Include `linux/ratelimit.h` explicitly. Main/LKM-only hook files have no counterparts in this builtin pin. |
| SELinux policy generation | [85d05cf2](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/85d05cf22bb0bcc7d41d555221d7eedc850b709f) | Both policy-publication paths advance `latest_granting` and pass the new generation to AVC/status notifications. Pre-5.10 branches retain their prior zero-sequence behavior. |

The r1 BTF inode-offset workaround targets separately built LKM code across
kernel ABI changes. This lane compiles builtin code against its own 6.6.118
kernel headers and keeps that path unchanged. r2 adds no further kernel patch.
The newer SUSFS priority-UID/KPM bridge migrations and mount-hide/PREINIT
startup paths stay outside this backport; their existing pairing and safety
decisions remain in force.

## Build and use

1. Build **OP13 SukiSU Ultra** from the updated source with the default
   `ce75122` / `3f6aae5` pair and `sukisu_driver_version=auto` or `41150`.
2. Inspect `_ox_debug/sukisu-uapi-compat.json`: UAPI should be 6/6, extension
   ABI 2/2 and `kernel_version_spoof` true. The build also requires the
   version-spoof IO handler in the linked `vmlinux` before packaging.
3. Install the matching official Manager and follow the existing backup/flash
   procedure. Open **Extensions → SukiSU version customization**.
4. For a display-only change, edit the full version string, retaining versionCode
   **41150** and UAPI **6** with Manager v4.3.0-r2. Manager/ksud compatibility
   checks use the effective numeric version and UAPI.

For v4.3.0-r1, the matching numeric value is 41140 with UAPI 6. The verifier
resolves that official release when explicitly selected through workflow dispatch.

The read-only CLI entry points, using the installed matching ksud, are:

```sh
su -c '/data/adb/ksud extension list'
su -c '/data/adb/ksud extension version-spoof get'
```

After a customization, reopen Manager and verify the new value; after reboot,
verify restoration and **Restore defaults** from the same page. Kernel source
changes alone leave existing flashable archives untouched.

### Recovery from incompatible custom numeric values

Use an available root/recovery environment to delete
`/data/adb/ksu/.version_spoof_config`, then reboot to restore kernel build values.
The separate `/data/adb/ksu/.version_spoof_warning_hidden` file controls warning
visibility; deleting it restores warnings when Manager restarts.

## Verification status

The first two builds, [42471010836](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/42471010836)
and [42471521043](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/42471521043),
stop before compilation because the public Clang asset URL returns HTTP 504.
The toolchain-download repair resolves both archive IDs from the same release
tag and uses the official asset API with bounded curl retries. Its
[decision record](../.agents/notes/implemented/bug-fix/2026-11-08-sukisu-toolchain-asset-api.md)
preserves the evidence and download contract. The user-started
[run 42472248698](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/42472248698)
passes full toolchain transfer/extraction, kernel compilation, packaging and
artifact upload. Its compatibility report records UAPI 6/6, extension ABI 2/2
and `kernel_version_spoof=true` for Manager v4.3.0-r2 (41150). The artifact
**OP13-SUKISU-CCTV18-INLINE-STOCKLIKE-v114-22** is available from that run.
The separate actionlint download failure uses the same asset-API repair.

The backport is assembled from the upstream builtin patches against the exact
repaired pin, with a small adaptation of the r1 SELinux-generation fix to retain
the builtin's older-kernel branches. Review covers the changed handlers,
dispatch callers, payload layouts, source inclusion, failure paths and workflow
ordering. Added regression fixtures cover equal-UAPI/missing-extension rejection,
ABI parsing, release-layout headers, legacy calls and HTTP failures.

Local verification follows the requested static-review-only scope; no local
test suite or kernel build is started. The user-started GitHub build above
passes compilation and packaging. Device boot stability, save/reset and reboot
persistence still need confirmation with v114-22. Keep a usable boot-image
backup before that device stage.
