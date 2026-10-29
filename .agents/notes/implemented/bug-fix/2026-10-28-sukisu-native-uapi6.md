# Agent Note: Use native UAPI 6 and check numeric Manager selections

Status: implemented

## Problem

Build 40738553505 stamps driver version 41068 onto the repaired UAPI 5 source
0af2cf9. Its compatibility report is manual-unchecked. The running driver
reports version 41068/UAPI 5, while the installed v4.2.1-r2 Manager uses UAPI 6.
Numeric equality conceals the incompatible interface generation.

## Decision

The default builtin driver is pinned to upstream
[ce75122](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/ce75122bec7423e0f1fa06e3e9a174085c5231ab).
It includes the real symbol-lookup
ioctl, preinit sources and UAPI 6 information flags. This pin precedes
the later priority-UID SUSFS and KPM bridge migrations, keeping this change
focused on the Manager interface. CCTV18 SUSFS remains pinned to 3f6aae5.

A narrow driver patch preserves the static_key_true ABI expected by that
CCTV18 tree. Both the getter/setter and the non-SUSFS read use the static key.
The final linked-symbol audit also covers the new pin. The initial revision
exported UAPI headers for the embedded runner. The reported boot failure and
incomplete PREINIT wiring are addressed by the later
[startup-safety decision](2026-10-28-sukisu-startup-safety.md), which owns that
optional capability and the new mount-hiding path.

Numeric Manager selections resolve an official stable release by its APK
versionCode and compare the actual Manager header with the driver. Unknown
numbers fail. The verifier's existing no-tag/no-version interface remains
available for legacy callers; the workflow uses it only for the documented
pre-UAPI 6c13a06/40796 pair. Auto selection and the numeric 40994/UAPI 5 legacy
pair remain supported with a matching source.

The [UAPI 5 repair](2026-10-17-sukisu-uapi-manager-compatibility.md) remains
responsible for the legacy 0af2cf9 selection and its SELinux helpers. This
decision owns the new default and the workflow's checked numeric selections.

## Alternatives considered

- Change the old header number to 6: small diff, but omits symbol lookup and
  preinit implementation. Use the native upstream implementation.
- Use the newest builtin head: includes unrelated SUSFS priority-UID and KPM
  bridge changes. Pin the native UAPI 6 revision before those migrations.
- Backport the entire preinit runner into 0af2cf9: retains the old pin, but
  duplicates a substantial upstream implementation and its dependency order.
- Keep numeric selections unchecked: preserves arbitrary version stamping,
  but reproduces the mismatched 41068/UAPI 5 artifact. Check known releases
  while retaining the explicit pre-UAPI lane and existing verifier API.

## Consequences

The default source targets the installed Manager's real interface. Existing
HybridSwap, firmware I/O defaults, KPM Image transformation and SUSFS guards
remain in place. Numeric mismatches stop before kernel compilation.

Patch applicability, source contracts, Python/YAML syntax and changed shell
blocks receive static review. The initial task requested source push only.
The user later built run 40794283862 and reported launcher loops followed by
a full reboot; runtime acceptance failed, leading to the startup-safety repair.
The added regression fixtures document UAPI 5/6 mismatches, numeric matching,
release filtering/pagination and preserved legacy calls; no test suite is run.
