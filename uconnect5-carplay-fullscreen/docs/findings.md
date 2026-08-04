# Findings log

Running log of concrete technical findings, in date order. Keep entries
factual and specific (file paths, offsets, resource names, exact commands
run) rather than general notes — this is the thing future-us will want to
grep.

Do not paste large chunks of decompiled proprietary code/resources here.
Reference where it lives locally (outside this repo) and summarize what it
shows.

## Template for a new entry

```
### YYYY-MM-DD

- Platform / version string:
- What we looked at:
- Command(s) run:
- What we found:
- Next question this raises:
```

## Entries

### 2026-08-04

- Platform / version string: n/a (checking a reference project, not our unit)
- What we looked at: `github.com/jason0x90/uconnect-swdl` — a public repo
  containing what looks like a fully extracted filesystem for the RA3 and
  RA4 Uconnect platforms (single commit, `RA4 14.05.03`).
- Command(s) run: `grep -ril carplay .` across the whole tree; browsed
  `usr/share/scripts/update/` lua installer scripts.
- What we found:
  - **Zero CarPlay references.** RA3/RA4 are QNX-based with a Flash
    (`.swf`) HMI layer — a different OS and UI stack entirely from Uconnect
    5's Android-based system. This repo does not help locate CarPlay
    layout/inset code. Not useful for Phase 2 as-is.
  - Repo has no extraction tooling included — it's the already-unpacked
    result, not a script we can reuse or adapt.
  - The installer code refers to an update subsystem named **"KaliSWDL"**
    (e.g. comment in `newswdl.lua`: "used for moving from KaliSWDL to
    NewSWDL"). That name also appears in the file listing of a *current*
    Uconnect 5 update package (`KaliSWDL.log`, per public how-to-update
    guides) — so the update/installer mechanism's naming has apparently
    persisted across the QNX→Android platform transition, even though the
    OS underneath changed completely. Minor lead, not a shortcut.
- Next question this raises: is there an equivalent public extraction of
  an *R1L or later* (Android-based) unit anywhere? Worth a targeted search
  before assuming we're starting from zero on the container format.
