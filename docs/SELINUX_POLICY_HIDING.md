# SELinux policy hiding — how it works and how to turn it on

> **This supersedes the earlier `KNOWN_SUSFS_SELINUX_LIMITATION.md`, which was
> wrong.** That document concluded the required symbols existed nowhere. They do
> exist — in the root driver, not in the SUSFS patch. Corrected below.

## Symptom

Root-detection scanners report things like:

- *"Dirty SELinux policy exposes LSPosed rule"*
- *"Enforcing with KSU context materialized"* — KSU SELinux contexts visible in
  the live policy

## How the feature actually works

CCTV18's SUSFS patch adds calls into `security/selinux/hooks.c` and
`security/selinux/selinuxfs.c` that answer policy queries from a *pristine
backup* of the policy instead of the live (KSU-modified) one. It declares three
symbols `extern` but does **not** define them:

- `backup_sepolicy`
- `security_context_to_sid_with_policy`
- `security_sid_to_context_with_policy`

The definitions come from the **root driver**, not from SUSFS:

| Symbol | Defined in |
|---|---|
| `backup_sepolicy` | `drivers/kernelsu/selinux/rules.c` (line 3, global) |
| `security_context_to_sid_with_policy` | `drivers/kernelsu/feature/selinux_hide.c` |
| `security_sid_to_context_with_policy` | `drivers/kernelsu/feature/selinux_hide.c` |
| `security_compute_av_user_with_policy` | `drivers/kernelsu/feature/selinux_hide.c` |

Both files are compiled unconditionally — they appear in the build log as
`CC drivers/kernelsu/feature/selinux_hide.o` and
`CC drivers/kernelsu/selinux/rules.o`.

## What went wrong here (build side)

At the **v77-era** root revision the driver did **not** yet define those symbols,
so the link failed:

```
ld.lld: error: undefined symbol: security_context_to_sid_with_policy
ld.lld: error: undefined symbol: backup_sepolicy
```

A guard was added to the **SukiSU lane** that rewrote

```c
#ifdef CONFIG_KSU_SUSFS
```

to

```c
#if defined(CONFIG_KSU_SUSFS) && defined(CONFIG_KSU_SUSFS_SELINUX_POLICY_HIDE)
```

in those two files, compiling the blocks out. Since no root project defines
`CONFIG_KSU_SUSFS_SELINUX_POLICY_HIDE`, that permanently disabled the feature.

### Current pair-specific behavior

The SukiSU guard uses exact source pairs, with `OX_SELINUX_HIDE_HOOKS=auto`:

- **Fork default `0af2cf9` / `3f6aae5`:** apply the two kernel SELinux helper
  wrappers needed by the driver, and keep the `hooks.c` / `selinuxfs.c`
  policy-query replacement blocks gated off. This is the retained UAPI 5 repair.
- **Upstream alternative `2d1de62` / `2919a9a`:** keep the replacement hooks
  enabled, following upstream's linked-pair configuration.
- **Other pairs:** apply the guard. Explicit `on` / `off` overrides remain
  available for deliberate source-pair validation.

SukiSU records its decision in `_ox_debug/selinux-policy-query-guard.log` and
`selinux-policy-query-guard-files.txt`. Helper-patch output is in
`selinux-query-helpers.log` for the default pair.

The **BakaSU lane** defaults to `OX_BAKASU_SELINUX_HIDE_OWNER=bakasu`, retaining
the driver's own SELinux hiding and excluding the SUSFS SELinux replacement
sections. See `_ox_debug/selinux-hide-status.txt` for its result.

## What you must still do (runtime side)

Compiling the code in is only half of it. In `selinux_hide.c`:

```c
bool ksu_selinux_hide_running __read_mostly = false;
```

The feature is **off by default** and is toggled at runtime through the
manager's feature system (`selinux_hide_feature_set`). For a build with the
replacement hooks enabled, **enable the SELinux hide feature in the SukiSU manager**.
If it stays off, scanners will keep seeing KSU contexts even though the kernel
supports hiding them.

## What this cannot fix

The *"Dirty SELinux policy exposes LSPosed rule"* finding is largely about
**LSPosed itself** — loaded Xposed classes, `XposedBridge` fields, binder bridge
replies, stack-trace signatures in your app's runtime. Those are userspace
artefacts of an active hook framework. No kernel feature can mask them; that is
LSPosed/module-level hiding territory.

SELinux policy hiding addresses the *policy-surface* half (KSU contexts, dirty
policy rules), not the presence of a hook framework inside a process.
