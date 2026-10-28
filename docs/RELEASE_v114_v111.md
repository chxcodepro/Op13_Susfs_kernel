# OP13 GKI Kernel — SukiSU Ultra v114 · BakaSU v111

Daily‑driver **Linux 6.6.118 GKI 2.0** kernel for the **OnePlus 13 CN**
(`PJZ110` / `sun` / `SM8750`), built for **ColorOS 17 CN (Android 17)**
(tested base: `PJZ110_17.0.0.103`).

> ⚠️ Flashing kernels can bootloop or soft‑brick a device. Back up `boot` /
> `init_boot` first. See the README "Safety first" section before flashing.

## Pick your build

| Lane | Workflow | Driver | SUSFS | Manager APK |
|---|---|---|---|---|
| **BakaSU v111** (recommended) | `Build_ReSukiSU.yml` | BakaSU `main` @ `d7260ca` | `3f6aae5` (v2.3.0) | latest BakaSU manager |
| **SukiSU Ultra v114** | `Build SukiSU_Ultra.yml` | SukiSU `builtin` @ `0af2cf9` + UAPI 5 repairs | `3f6aae5` (v2.3.0) + SELinux helpers | UAPI-compatible stable release selected by `auto` |

Shared pins: kernel `2a4726b` (6.6.118), assets `21db9e7`, AnyKernel3 `020dfec`,
toolchain CCTV18 Clang 18 `r510928`.

## What's new since v112 / v109

### ColorOS 17 CN
- **Kernel base unchanged and correct.** ColorOS 17 CN ships 6.6.118 on the same
  `android15-6.6` GKI branch. No KMI change from ColorOS 16.
- **Stock `uname -r` updated** to the ColorOS 17 value:
  `6.6.118-android15-8-g9bc34d5b0c79-abogki537459655-4k`.
- **Trailing `+` removed.** `setlocalversion` used to append `+` to the release
  string (`…-4k+`), which no stock kernel has. Fixed.
- **`/proc/version` mimics stock GKI** — `kleaf@build-host`.

### Features that were silently off — now on
ADIOS, Re:Kernel and Baseband‑Guard defaulted to **On** but never took effect
(the workflow looked for patch files that don't exist). The merged workflows
enable available sources directly; inspect the final config for:
- **ADIOS** I/O scheduler (`CONFIG_MQ_IOSCHED_ADIOS=y`, default scheduler)
- **Re:Kernel** (`CONFIG_REKERNEL=y`)
- **Baseband‑Guard** (`CONFIG_BBG=y`, added to `CONFIG_LSM`) — pinned `a5b57f1`

All three are KMI‑safe (no kernel header changes).

### Security
- **posix‑cpu‑timers use‑after‑free fix** (6.6‑stable `12a891c773ae`, mainline
  `920f893f735e`) — closes a local privilege‑escalation path. Best‑effort, logged
  to `_ox_debug/sec-posix-timers.txt`; skip with `OX_SKIP_UAF_FIX=1`.
- **CVE‑2026‑43499** (rtmutex) — still applied in both lanes.

### Build fixes
- **SukiSU:** this fork retains the repaired `0af2cf9` / `3f6aae5` pair and adds
  the two kernel SELinux helper wrappers required for linking. Its policy-query
  guard remains active by default. Upstream's alternative `2d1de62` / `2919a9a`
  hook-enabled path remains available with explicit source and Manager choices.
- **KPM:** retain pinned final-Image payload injection before artifact creation,
  with matching standalone and AnyKernel3 Images and final checksum checks.
- **BakaSU:** post‑package banner check updated for the BakaSU name.

### SukiSU v114 — "Failed to grant Root!" until the manager restarts
If ColorOS starts the manager process early in boot, it could cache a non‑root
shell before the kernel recognised it as the manager. v114 adds an early manager
scan at post‑fs‑data (as BakaSU already does). Check after flashing:

```sh
su -c 'dmesg | grep -E "scanning manager|Crowning manager"'
```

### Flasher text
The AnyKernel3 flasher text now matches the release template. The root name and
credit are one `env:` line each per workflow: `OX_ROOT_DISPLAY_NAME`,
`OX_ROOT_CREDIT`.

### CI maintenance (2026‑10‑18)
The upstream workflow and composite-action updates adopt `actions/cache@v5`,
`actions/github-script@v8`, `actions/checkout@v5`, and
`actions/upload-artifact@v6`. The local version-sync workflow stays unchanged.

## Match the SukiSU Manager to the build summary
The default builtin receives this fork's UAPI 5 repair, previously built with
Manager v4.2.1 / 40994. `auto` selects the latest official stable release and
checks its UAPI against the patched driver before compilation. Install that
recorded release. Explicit numeric choices retain their `manual-unchecked`
status; source refs are selected separately.

## After flashing — check
- `uname -r` ends in `-4k` (no `+`)
- `su` works from Termux/adb and App Profile saves
- In the build artifact: `_ox_debug/pairing.txt` = `pairing: OK`,
  `sec-posix-timers.txt` = applied
