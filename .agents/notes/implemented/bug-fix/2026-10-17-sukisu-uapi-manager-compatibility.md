# Agent Note: Match the SukiSU Manager UAPI with the builtin driver

Status: implemented

## Problem

Run 38934738706 boots successfully on PJZ110_17.0.0.103 and ADB `su -c id`
returns uid 0. Its fixed f2201c4 driver reports UAPI 2, while Manager v4.2.1
reports UAPI 5 and disables full-feature compatibility. Overriding KSU_VERSION
to 40994 does not change that interface. The red kernel-update warning is an
actual protocol mismatch, not evidence that the new boot image failed to load.

## Decision

The workflow pins the official builtin driver to 0af2cf9cef7dc2239fa7ebb3f7898830a1087e26.
It already implements scoped su-session file descriptors (UAPI 3) and the
services-stage start/skip result (UAPI 5), but its header still declares 2 and
omits the UAPI 4 bundled-LKM flag plumbing. The patch backports that upstream
flag/parameter implementation and declares 5. The Android 15 / 6.6.118 kernel
base stays unchanged; the new driver pairs with CCTV18 SUSFS 3f6aae5
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
scan references an out-of-scope pkg variable. The patch adds the release's exact
manager ioctl definition and skips KSU_PACKAGE_NAME in that scan, retaining signature
verification and builtin-manager priority.

CCTV18 SUSFS v2.3.0 declares ksu_su_compat_enabled as static_key_true in
fs/exec.c, fs/open.c, and fs/stat.c, but the unpatched builtin defines a bool.
The patch aligns the driver definition, header, getter, setter, and non-SUSFS read with the static
key contract. A plain bool can link across translation units while leaving
static-branch toggling invalid; compilation alone does not establish this ABI.
The build inspects the linked vmlinux symbol and rejects a missing or one-byte
switch for this pinned driver, retaining the result in the debug artifact.

Run 38943053604 reaches final link but finds an undefined
context_struct_compute_av_fn in the driver's policy-query code. For this exact
driver/SUSFS pair, the workflow adds two thin ss/services.c wrappers around the kernel's own
context/access-vector and masked-permission audit helpers. This binds the
driver to this kernel's real policy implementation without weak-symbol stubs,
duplicating the policy algorithm, or enabling the guarded hooks.c/selinuxfs.c
hiding replacements. The latter guard and its limitation remain unchanged.

Before building in auto mode, the workflow compares the actual driver's UAPI
with the official Manager release source. Mismatches fail instead of disguising
an old interface with a new numeric driver version. Explicit legacy manual
source/version choices remain available, alongside final-Image KPM patching and packaging
checks from the [KPM decision](2026-09-18-kpm-image-patching.md).
That decision remains responsible for Image transformation; the
[dropdown decision](../process/2026-10-16-sukisu-version-dropdown.md)
remains responsible for synchronized numeric choices. Neither decision alone
establishes protocol compatibility.

### Upstream v114 integration

The merged workflow retains the repaired `0af2cf9` / `3f6aae5` default pair,
auto/manual Manager version selection, and the KPM final-Image pipeline. It
adopts upstream's post-fs-data manager scan, posix-cpu-timers security patch,
source-present ADIOS/Re:Kernel configuration, pinned Baseband Guard install,
flasher branding, and v114 artifact names. BakaSU uses upstream's v111 names.

The helper patch matches the literal repaired SUSFS commit independently of
upstream's `VERIFIED_SUSFS=2919a9a`. Only upstream's alternative `2d1de62` /
`2919a9a` pair enables policy-query hooks automatically. This preserves the
default repair's guard while retaining the upstream pair's existing path.

## Alternatives considered

- Changing only the UAPI number removes the banner cheaply but leaves scoped
  descriptor and services semantics unimplemented on f2201c4. Reject it.
- Using the main/LKM release supplies UAPI 5 directly, but discards the current
  builtin/SUSFS integration and requires a larger hook/build-layout migration.
- Downgrading Manager avoids changing the boot image, but forfeits the user's
  chosen v4.2.1 Manager and does not correct future auto-version mismatches.
- Replacing the fork defaults with upstream's `2d1de62` / `2919a9a` and fixed
  40900 version avoids the helper backport, but drops the repaired UAPI 5 and
  automatic Manager selection. The merge keeps that pair as an explicit option.

## Verification

The 2026-10-27 integration receives merge-diff and source-pair review, including
YAML parsing of the changed workflows and composite action. All original build
steps and the eight local patch/script/sync files are retained. The pinned
builtin's post-fs-data function has the observer anchor and already uses
track_throne elsewhere. Tests and a fresh kernel build remain unrun, per the
user's instruction; the evidence below describes the earlier UAPI repair.

The eight focused UAPI tests pass, including rejection of driver UAPI 2 against
Manager UAPI 5 and preservation of explicit legacy manual mode. The 12 version
sync tests remain valid. Changed shell blocks pass bash syntax checks and the
workflow passes actionlint. The linked-symbol guard accepts a static key and
rejects a bool or missing symbol.

[Run 38944690920](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/38944690920)
at 3c97d2e completes successfully with no compiler warnings or errors. It records
driver 40994 / v4.2.1-0af2cf9c and UAPI 5 against Manager v4.2.1 UAPI 5. The
linked su-compat switch is a 16-byte OBJECT. Final configuration enables KSU,
KPM, and all requested core SUSFS features; the existing SELinux query guard
still covers hooks.c and selinuxfs.c.

The official KPM tool transforms the 38,529,536-byte compiler Image into a
38,711,360-byte final Image. CI verifies both public checksums and package
consistency. The downloaded flashable ZIP's Image also compares byte-for-byte
with the standalone final Image. BUILD_INFO records UAPI 5/5 and KPM patched.
The kernel release remains
6.6.118-android15-8-g9bc34d5b0c79-abogki537459655-4k. The package targets the
active boot slot using BLOCK=boot, IS_SLOT_DEVICE=auto, SLOT_SELECT=active.

Artifact 12065117719 is OP13-SUKISU-CCTV18-INLINE-STOCKLIKE-v111-14. Local copy:
artifacts/run-38944690920/OP13-SUKISU-CCTV18-INLINE-STOCKLIKE-v111-14/artifacts/AK3_OP13_SukiSUUltra_CCTV18_inline_stocklike_v111_14_FLASH_THIS.zip.

## Consequences

Auto builds reject incompatible UAPI pairs rather than producing a misleading
numeric version. The compatibility patches apply only to their exact pinned
source pairs, so changing sources requires a deliberate compatibility review.
Numeric manual selections keep their original contract and unchecked status.

The phone remains on its previous image; no flash or reboot is performed.
Build and static checks do not replace the later, separately authorized phone
check of Manager full-feature status, app grants, modules, and KPM.
