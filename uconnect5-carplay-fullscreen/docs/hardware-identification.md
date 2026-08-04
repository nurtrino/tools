# Step 0: Identify exactly what you have

Everything downstream (which exploit threads are relevant, which firmware
package to pull, which APK to decompile) depends on this. Fill this in
before anything else.

## From the Uconnect screen (no tools needed)

1. Go to **Settings → System Information** (exact path varies slightly by
   model year) and record:
   - **Software/system version string** — looks like
     `FCA_R1L_ARM64_00.145.00.15.00`. The middle token (`R1L` here) is the
     platform code and is the single most useful piece of information —
     it's what determines whether the XDA "FCA R1L" thread applies to you
     at all, or whether you're on a different Harman platform (e.g. the RAM
     12"/14.5" units use different codes).
   - Build date, if shown.
2. **Screen orientation and layout**, described precisely:
   - Is the display portrait or landscape?
   - Height (in rough %, or better, pixels if you can get a screenshot) of
     the top bar and bottom bar that box in CarPlay.
   - What's actually *in* each bar (status icons, climate controls,
     shortcuts) — this hints at which system component owns that region.

## From the vehicle itself

- Year/make/model/trim.
- If you're willing to remove the head unit (not required yet): the
  physical part number / serial label often has a prefix like `T0071` or
  `T00AD` for Harman-made units — record it but don't post it publicly
  paired with your VIN.

## Why this matters before downloading firmware

The Stellantis update center matches update packages to a VIN, and
different platforms package their update payload differently. Knowing the
platform code up front avoids pulling the wrong package or wasting time
interpreting a `.upd` layout that doesn't match what others have documented.

## Log your answers here

```
Platform code (e.g. R1L):
Full version string:
Screen orientation:
Top bar content / approx height:
Bottom bar content / approx height:
Vehicle year/make/model/trim:
```
