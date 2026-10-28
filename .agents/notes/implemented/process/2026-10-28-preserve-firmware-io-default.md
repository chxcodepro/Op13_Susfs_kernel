# Agent Note: Retain the firmware I/O default for daily builds

Status: implemented

## Problem

The running PJZ110 uses mq-deadline. The workflow defaults enable ADIOS and
make it the default without a device comparison establishing a benefit for
the user's workload. The user approves the recommended conservative changes
after reviewing the performance audit.

## Decision

Both active lanes default `adios` to `Off` and explicitly clear
`CONFIG_MQ_IOSCHED_DEFAULT_ADIOS` when ADIOS is not selected. The source's
existing modular scheduler support remains intact. Explicit `adios=On`
continues to compile ADIOS into the Image and select it as default.

## Alternatives considered

- Keep ADIOS enabled by default: exposes the new scheduler immediately, but
  changes the running device's established I/O behavior without measured
  benefit.
- Remove ADIOS completely: narrows future options unnecessarily. Retain the
  source and explicit opt-in setting.

## Consequences

Daily builds preserve the firmware's I/O selection. This decision avoids an
additional unmeasured policy change while repairing HybridSwap. Existing
Root, KPM, SUSFS, compiler and network selections remain intact. Static
workflow and shell review cover the change. Runtime deployment remains a
separate step after building the updated kernel.
