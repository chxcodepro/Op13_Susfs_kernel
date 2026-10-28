# Agent Note: Preserve ColorOS HybridSwap module ownership

Status: implemented

## Problem

PJZ110_17.0.0.103 records NAND swap error 1004 and lacks
`/sys/block/zram0/hybridswap_core_enable`. Its active kernel and the saved
run-40630502965 configuration have `CONFIG_ZRAM=y` and `CONFIG_ZSMALLOC=y`.
Both active workflows force those generic implementations into the Image,
while the pinned GKI defconfig supplies `CONFIG_ZRAM=m`. ColorOS ships
`oplus_bsp_hybridswap_zram.ko` and its vendor allocator dependencies.

The generic and vendor ZRAM implementations register the same CPU hotplug
state and control class. Only the vendor implementation provides HybridSwap.
The old bundled RAM fix forces the condition property true after boot and
writes the vendor device-life control, concealing failures without restoring
the missing interfaces.

## Decision

Both SukiSU and BakaSU workflows set ZRAM and ZSMALLOC to modules before
`olddefconfig`, independently of the extra-codec toggle. They reject a final
configuration that changes either option away from `m`. Codec support,
generic-module writeback and recompression options remain available; the
installed ColorOS vendor modules determine their own runtime capabilities.

The packages omit the old RAM fix. During a separately authorized flash,
the flasher disables only the existing `op13_ram_expansion_fix` module when
its directory is accessible. It retains that directory for recovery and
reports a failed disable operation. With inaccessible `/data`, the user
disables the historical module through the root manager.

## Alternatives considered

- Keep generic ZRAM builtin and force the UI condition true: preserves a
  standalone generic driver, but leaves the required HybridSwap interfaces
  absent and masks initialization failure.
- Import the complete vendor memory stack into the common kernel: offers
  direct integration, but duplicates the firmware's module ownership and
  introduces a larger ABI and maintenance change than this repair needs.
- Disable all compression support: removes the conflict, but discards codec
  capabilities unnecessarily. Preserve codec settings and modular drivers.

## Consequences

The existing ZRAM input names and defaults remain usable. Root, SUSFS, KPM,
network and compiler settings retain their prior values. The I/O default is
covered by the [firmware I/O decision](../process/2026-10-28-preserve-firmware-io-default.md). Firmware
modules remain responsible for runtime compressor selection and memory
expansion. Existing release archives remain unchanged.

Changed workflows receive static configuration, packaging and diff review.
A new kernel build and phone boot remain required to establish module ABI
compatibility, successful HybridSwap initialization and the selected expansion
size. Runtime recovery remains pending until a new kernel is built and
installed. Existing release archives and the running phone remain unchanged.
