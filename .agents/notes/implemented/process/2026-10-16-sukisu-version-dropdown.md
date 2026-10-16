# Agent Note: Keep the SukiSU version dropdown current

Status: implemented

## Problem

The dispatch form lists only `auto`, `40900`, and `40796` while the official
Manager has reached `40994`. Runtime auto-resolution works, but users cannot
see the latest numeric choice before starting a build.

## Decision

`sync-sukisu-versions.yml` reads the official latest stable release daily at
10:23 Asia/Shanghai and on manual dispatch. A standard-library Python script
updates only the SukiSU version input's description and choices, preserving
`auto`, the current stable versionCode, and compatibility values `40900` and
`40796`. A newer stable replaces the previous automatically tracked choice.
No release change means no commit. API or schema failures leave the file alone.

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
pairing; no existing decision is superseded.

## Alternatives considered

- Runtime `auto` plus a summary needs no write credential, but leaves the
  pre-build dropdown stale. The user chose scheduled dropdown synchronization.
- Fetching choices when opening Run workflow would be immediate, but native
  GitHub choice inputs are static YAML and offer no dynamic API data source.

## Consequences

The visible choice tracks stable releases without manual number edits. Refresh
depends on GitHub's scheduler, token expiry, and branch permissions. Token-based
commits can trigger the existing push lint workflow; the sync itself has no
push trigger. No kernel build starts automatically.

Remote publishing requires the configured secret and a pushed default-branch
workflow. This change does not validate ColorOS 17 boot or vendor-module
compatibility.

## Verification

The 12 focused unittest cases pass, covering parsing, deduplication,
idempotence, replacement, unrelated content and line-ending preservation, dry
runs, Action outputs, and failure paths. A live `--check` resolves `40994` and
finds the dropdown current. Both affected workflows pass actionlint and YAML
structure checks; changed shell blocks pass `bash -n`, and executing the summary
block includes the resolved version, release, and source ref. Note format and
relative-link checks pass. Publishing and the actual GitHub dropdown await the
repository secret and a pushed workflow.
