# Agent Note: Isolate the native UAPI 6 startup regression

Status: implemented

## Problem

After flashing build 40794283862 / v114-17, the user reports repeated launcher
restarts followed by a full system reboot. Its final config matches v114-16,
and the driver/Manager UAPI report is 6/6. Replacing the builtin source also
introduced 63 changed runtime-related files excluding nolibc, beyond the
intended interface upgrade.

The new mount_hide feature defaults on and installs a file_open LSM hook.
For selected app/isolated UIDs it returns ENOENT for any basename mountinfo,
mounts or mountstats without verifying procfs. This is an independent default
filesystem-behavior change with a credible application-startup failure path.
The exact launcher crash and final reboot trigger remain unconfirmed without
the incident's logs.

PREINIT is also advertised when its runner is compiled, although the pinned
builtin's execve entry returns false and its setup helper has no internal
caller. The earlier header-install step enabled this incomplete capability.

## Decision

The pinned-source compatibility patch removes mount_hide's header/source
inclusion, initialization and LSM registration. Its handler is not registered,
so a saved feature value cannot reattach the denied-open path. Existing
SUSFS/namespace unmount handling stays intact.

The same patch removes the unwired runner's build rules and defines
KSU_NO_PREINIT. Existing upstream guards suppress the PREINIT information flag
and runner startup. Native UAPI 6, symbol lookup, the static-key ABI repair,
KPM and checked Manager selection remain intact. Header preparation remains
available for custom source refs rather than the patched pin.

The workflow fails if the pinned source still includes/registers mount_hide
or lacks the explicit PREINIT disable flag, and records the source contract
in sukisu-startup-safety.txt. README identifies the affected archive and the
need for a newly built candidate.

The [native UAPI 6 decision](2026-10-28-sukisu-native-uapi6.md) still owns source
selection and Manager checks. This decision supersedes its initial startup
feature handling while preserving those interface changes.

## Alternatives considered

- Flip only mount_hide's default boolean: smaller patch, but saved feature
  configuration could enable the same global deny path again.
- Add a procfs/path check only: narrows the overbroad filter, but still changes
  legitimate mount-information reads for ordinary apps. Restore the previous
  LSM behavior first.
- Disable every Root module or change thermal settings: could mask a trigger,
  but does not repair the source regression and disrupts unrelated choices.
- Claim PREINIT support without its execution wiring: retains a feature bit,
  but lets userspace choose an unsupported startup path. Report capability
  absence until the integration is complete.
- Downgrade the whole driver to UAPI 5: returns to a known older base but
  reintroduces the installed Manager's interface mismatch. Keep native UAPI 6.

## Consequences

The two new optional hiding/startup behaviors are absent in the patched pin.
SUSFS, KPM, HybridSwap and the firmware I/O default retain their prior
configuration. Old v114-17 archives do not acquire this fix retroactively.

Patch applicability and source inclusion/registration paths receive static review only,
per the current source-push scope. No build, test suite, phone modification or
reboot is performed. Runtime confirmation still needs a new build and the
incident's crash/reboot evidence; this is a targeted source repair candidate.
