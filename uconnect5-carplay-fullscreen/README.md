# Uconnect 5 — Fullscreen CarPlay Research

Goal: get Apple CarPlay to render truly fullscreen on a Uconnect 5 head unit
that currently letterboxes it — in this case, a unit with **both a top bar
and a bottom bar** boxing CarPlay into a middle region.

This is personal-vehicle reverse engineering: modifying software on hardware
you own, for interoperability/accessibility purposes. Nothing here is about
attacking other people's vehicles, mass exploitation, or redistributing
Stellantis/Harman firmware. Don't commit OEM firmware binaries, extracted
filesystem images, or proprietary APKs to this repo — analyze them locally
and only check in your own notes/scripts/findings. `.gitignore` in this
folder already excludes common binary/extraction artifacts.

## Status: Phase 0 — no root/shell access yet

This is genuinely uncharted territory. Unlike older QNX-based Uconnect
3/4, Uconnect 5 (Android-based, Harman/Qualcomm Snapdragon automotive SoC)
has hardened USB/ADB access, and there is no publicly documented,
reliable root method for current-generation units. A vulnerability nicknamed
"FCA R1L" is discussed on XDA for Jeep/Fiat/Chrysler R1L units, but the
researchers there are deliberately withholding exploit details to avoid it
being patched via OTA — so there's nothing to reproduce from public sources
today. Treat that as a possible future lead, not a plan.

Because of that, the plan below is ordered so that the most useful work
happens **before** any root/exploit is needed at all.

## Phase plan

1. **Identify exact hardware/software** (no access needed) — see
   `docs/hardware-identification.md`. This determines which platform
   (R1L vs. others) and which community threads/findings are even relevant.
2. **Static firmware analysis** (no vehicle access needed) — Stellantis
   publishes official update packages for download, matched to your VIN, via
   the [Uconnect Software Update Center](https://www.driveuconnect.com/support/software-update.html).
   The extracted package contains a `swdl.upd` file — that's the actual
   firmware payload, and it's inspectable offline. See
   `tools/inspect_upd.py` and `docs/findings.md`.
   - Goal: locate the HMI/launcher/projection component responsible for
     drawing the CarPlay surface, and find whatever config/resource/code
     defines the top-bar and bottom-bar heights (insets) that box it in.
3. **Deploy a change** (blocked on root/shell) — this is the actual hard,
   unsolved part. There is no known way to write a modified value back to a
   live unit without either a working root/shell method or a way to get a
   modified image accepted by the update/signature-verification process.
   Do not attempt to skip to this step by trying to defeat signature checks
   blindly — that risks bricking the head unit. This phase starts once
   Phase 2 tells us *what* to change and Phase 1's research turns up a real
   entry point.

## Why this isn't a quick settings fix

On landscape 12"/14.5" Uconnect 5 displays (RAM 1500/2500/3500), CarPlay
already renders fullscreen as of certain software versions — that case is
just a software-update/settings issue, not a system edit. A unit with a
persistent top bar *and* bottom bar sandwiching CarPlay is different: that's
deliberate HMI layout (status bar + climate/shortcut bar kept reachable),
which means removing it requires changing how the window manager allocates
screen space to the CarPlay projection surface — a real code/config change,
not a toggle.

## Working with me on this

I can't reach your vehicle or your Stellantis account from this sandbox.
The collaboration model is: you do the hands-on steps (checking the version
string, downloading the update package, running the inspection scripts
locally), and paste back what you find — file listings, `file`/`binwalk`
output, decompiled resource values, photos of any physical board access
points if we get to that stage — and I'll help interpret it and plan the
next step.
