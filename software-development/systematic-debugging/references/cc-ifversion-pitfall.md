# cc-ifversion Pitfall

## The Problem

The kernel Makefile function `$(call cc-ifversion, -ge, VERSION, ...)` does NOT check the CURRENT compiler version. It checks `CONFIG_GCC_VERSION` — the version of GCC that was used to BUILD the kernel.

```makefile
# cc-ifversion definition (scripts/Makefile.compiler):
cc-ifversion = $(shell [ $(CONFIG_GCC_VERSION)0 -ge $(2)000 ] && echo $(3) || echo $(4))
```

## Impact

When building a kernel module with a different GCC than the one that built the kernel:

- `$(call cc-ifversion, -ge, 1201, KBUILD_CFLAGS += -fzero-call-used-regs=used-gpr)` → evaluates TRUE even if current GCC is 9.4, as long as the kernel was built with GCC >= 12.01
- This causes `unrecognized command line option` errors with older GCC

## Affected Flags (seen on kernel 5.19 built with GCC 12)

| Flag | Added by | Kernel Config |
|------|----------|--------------|
| `-mharden-sls=all` | `arch/x86/Makefile` | `CONFIG_SLS` |
| `-ftrivial-auto-var-init=zero` | `Makefile` | `CONFIG_INIT_STACK_ALL_ZERO` |
| `-fzero-call-used-regs=used-gpr` | `Makefile` | `CONFIG_ZERO_CALL_USED_REGS` |

## Workarounds

1. **Comment out the flags** in extracted kernel headers Makefile (safe — these are optional security hardening)
2. **Replace precompiled binaries** (`objtool`, `fixdep`) with stub scripts if GLIBC mismatch also exists
3. **Install matching GCC version** (best but may require sudo + proxy)
4. **Upgrade kernel** to one with the driver built-in (skips compilation entirely)

**Do NOT** try to fix with more `$(call cc-ifversion, ...)` wrappers — they won't help because they check the wrong GCC version.
