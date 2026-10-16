# Agent Note: Match the SukiSU Manager UAPI with the builtin driver

Status: proposed

## Problem

Run 38934738706 boots successfully on PJZ110_17.0.0.103 and ADB `su -c id`
returns uid 0. Its fixed f2201c4 driver reports UAPI 2, while Manager v4.2.1
reports UAPI 5 and disables full-feature compatibility. Overriding KSU_VERSION
to 40994 does not change that interface. The red kernel-update warning is an
actual protocol mismatch, not evidence that the new boot image failed to load.

## Proposal

Pin the official builtin driver to 0af2cf9cef7dc2239fa7ebb3f7898830a1087e26.
It already implements scoped su-session file descriptors (UAPI 3) and the
services-stage start/skip result (UAPI 5), but its header still declares 2 and
omits the UAPI 4 bundled-LKM flag plumbing. Backport that complete upstream
flag/parameter implementation, then declare 5. Keep the Android 15 / 6.6.118
kernel base unchanged and pair the new driver with CCTV18 SUSFS 3f6aae5
(v2.3.0), which calls the now-available ksu_install_su_fd().

The UAPI 3 audit follows upstream [86e9b3b](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/86e9b3bf00724b0f649709b8317f0475caf9e8ae): scoped descriptor context,
restricted ioctl permissions, profile-aware wrapper credential override, and
post-exec descriptor installation are present. The wrapper does not need to
call ksu_is_su_session_fd(); that permission check belongs to the dispatcher.
The LSM header change in that commit is formatting only. CCTV18's exec hook
installs the descriptor only for a successful su session after profile setup.
UAPI 4 follows [dda78702](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/dda78702bef1841e70d5b26150b12c03b782e175)
and UAPI 5 follows [7ef2dbb7](https://github.com/SukiSU-Ultra/SukiSU-Ultra/commit/7ef2dbb7fa68722c142f5266f0a7b95c8fb6e7e9).

The first repair build, 38942212803, exposes two additional builtin compile
defects: the manager ioctl is used but not declared, and the dynamic-manager
scan references an out-of-scope pkg variable. Add the release's exact manager
ioctl definition and skip KSU_PACKAGE_NAME in that scan, retaining signature
verification and builtin-manager priority.

CCTV18 SUSFS v2.3.0 declares ksu_su_compat_enabled as static_key_true in
fs/exec.c, fs/open.c, and fs/stat.c, but this builtin defines a bool. Align the
driver definition, header, getter, setter, and non-SUSFS read with the static
key contract. A plain bool can link across translation units while leaving
static-branch toggling invalid; compilation alone does not establish this ABI.
The build inspects the linked vmlinux symbol and rejects a missing or one-byte
switch for this pinned driver, retaining the result in the debug artifact.

Before building in auto mode, compare the actual driver's UAPI with the
official Manager release source. Fail on mismatches instead of disguising an
old interface with a new numeric driver version. Preserve explicit legacy
manual source/version choices. Keep final-Image KPM patching and packaging
checks from the [KPM decision](../../implemented/bug-fix/2026-09-18-kpm-image-patching.md).
That decision remains responsible for Image transformation; the
[dropdown decision](../../implemented/process/2026-10-16-sukisu-version-dropdown.md)
remains responsible for synchronized numeric choices. Neither decision alone
establishes protocol compatibility.

## Alternatives considered

- Changing only the UAPI number removes the banner cheaply but leaves scoped
  descriptor and services semantics unimplemented on f2201c4. Reject it.
- Using the main/LKM release supplies UAPI 5 directly, but discards the current
  builtin/SUSFS integration and requires a larger hook/build-layout migration.
- Downgrading Manager avoids changing the boot image, but forfeits the user's
  chosen v4.2.1 Manager and does not correct future auto-version mismatches.

## Acceptance criteria

- The selected driver implements UAPI 3, 4, and 5, not just the numeric label.
- Focused compatibility tests reject a UAPI 2 driver against Manager UAPI 5.
- One SukiSU Actions build compiles, verifies matching UAPI values, patches
  KPM, and packages the final Image consistently.
- Deliver the repair artifact without flashing the phone automatically.

## Risks

The newer builtin/SUSFS pair may expose compile failures that the old pin
avoids. Validate on a dedicated branch and retain the currently booted image.
Build and static checks do not replace the later, separately authorized phone
check of Manager full-feature status, app grants, modules, and KPM.
