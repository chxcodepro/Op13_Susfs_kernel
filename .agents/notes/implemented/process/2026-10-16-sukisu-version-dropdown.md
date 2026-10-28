# Agent Note: Keep the SukiSU version dropdown current

Status: implemented

## Problem

The dispatch form previously listed only `auto`, `40900`, and `40796` while the
official Manager had reached `40994`. Runtime auto-resolution worked, but users
could not see the latest numeric choice before starting a build.

## Decision

`sync-sukisu-versions.yml` reads the official latest stable release daily at
10:23 Asia/Shanghai and on manual dispatch. A standard-library Python script
updates only the SukiSU version input's description and choices, preserving
`auto`, the current stable versionCode, and compatibility values `40994`,
`40900`, and `40796`. A newer stable replaces the previous automatically tracked choice.
No release change means no commit. API or schema failures leave the file alone.

`40994` remains a permanent compatibility choice for the repaired UAPI 5 pair.
Manager v4.2.1 / 40994 declares UAPI 5; the newer v4.2.1-r2 / 41068 declares 6.
GitHub validates choice inputs and rejects a dispatch with HTTP 422 when 40994
is missing. Keeping it in both the YAML and generator preserves the release
build's supported Manager selection across daily refreshes.

All three build dispatch forms use Chinese descriptions while preserving input
keys, choice values, source pins, and feature defaults. The generated version
description also stays in Chinese, with literal UTF-8 text in YAML, so daily
synchronization does not restore English copy. Their `kernel_suffix` defaults
match the supplied PJZ110_17.0.0.103 screenshot:
`android15-8-g9bc34d5b0c79-abogki537459655-4k`; the unused `SUB_VERSION` metadata
is aligned to `118`. The kernel remains on the Android 15 GKI / 6.6.118 source
baseline; matching the version identifier does not establish firmware support.

The job checks out the default branch and pushes normally, never force-pushing.
Workflow-file writes require `SUKISU_VERSION_SYNC_TOKEN`, a repository-limited
token with Contents and Workflows write access; `GITHUB_TOKEN` is insufficient.
The job fails explicitly if that secret is absent or branch protection denies
the push. Numeric versionCodes are the only upstream data embedded in YAML.

The build publishes the resolved version and source ref in its summary before
compiling, so a cancelled build still exposes the selection. Source refs remain
pinned independently of Manager versions, preserving the contract in the
[KPM note](../bug-fix/2026-09-18-kpm-image-patching.md). That note partially
overlaps version selection and keeps ownership of Image patching and source
pairing. The later [Manager UAPI repair](../bug-fix/2026-10-17-sukisu-uapi-manager-compatibility.md)
adds the auto-mode interface guard and changes the paired source defaults;
this note continues to own dropdown synchronization and Chinese input copy.

## Alternatives considered

- Runtime `auto` plus a summary needs no write credential, but leaves the
  pre-build dropdown stale. The user chose scheduled dropdown synchronization.
- Fetching choices when opening Run workflow would be immediate, but native
  GitHub choice inputs are static YAML and offer no dynamic API data source.
- Adding 40994 only to the current YAML unblocks one dispatch, but the next
  scheduled refresh removes it. The generator retains it as a compatibility value.

## Consequences

The visible choice tracks stable releases without manual number edits. Refresh
depends on GitHub's scheduler, token expiry, and branch permissions. Token-based
commits can trigger the existing push lint workflow; the sync itself has no
push trigger. No kernel build starts automatically.

Remote publishing requires the configured secret and a pushed default-branch
workflow. This change does not validate ColorOS 17 boot or vendor-module
compatibility.

## Verification

The 2026-10-27 compatibility addition receives code and YAML review only;
the tests below describe the initial implementation. Test expectations now cover
40994 retention after a newer release and deduplication of every compatibility value.

The 12 focused unittest cases pass, covering parsing, deduplication,
idempotence, replacement, unrelated content and line-ending preservation, dry
runs, Action outputs, and failure paths. A live `--check` resolves `40994` and
finds the dropdown current. Both affected workflows pass actionlint and YAML
structure checks; changed shell blocks pass `bash -n`, and executing the summary
block includes the resolved version, release, and source ref. Note format and
relative-link checks pass.

Dispatch validation covers all 74 Chinese descriptions across the three build
forms and the screenshot-matching default version string. Structural comparison
allows only description edits, the `kernel_suffix` default, and `SUB_VERSION`
metadata; all source pins, machine-readable options, feature defaults, and build
steps remain unchanged. The localized generator passes its focused tests and a
live no-change check; all three changed workflows pass actionlint.

The initial [remote sync](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/38929281932)
passes all 12 cases and creates automatic commit `d7d25b4`, adding `40994` to the
default-branch workflow. The published choices are `auto`, `40994`, `40900`, and
`40796`. The [generated-commit lint](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/38929304606)
passes. A [second sync](https://github.com/chxcodepro/Op13_Susfs_kernel/actions/runs/38929512183)
reports the dropdown current and creates no commit, verifying the no-change
publication path with the configured credential. No kernel build is dispatched.
