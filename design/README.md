# design/ — reference material only

These files are **reference material for the eventual native Swift port** of
MacHuna (the "mac-arsed" rewrite). They are **not part of the shipping Python
app**:

- nothing here is imported by `machuna.py`, bundled by `MacHuna.spec`, or covered by `test_machuna.py`
- nothing here is on the release checklist in `CLAUDE.md`
- nothing here is published to the `Machuna Share` folder

They exist purely to capture design intent so it isn't lost. Treat them as a
sketch, not a spec.

**SUPERSEDED 2026-09-24.** The Swift work has begun and lives in
`DNSVision/MacHuna-Swift`. Its decision record, `DESIGN_DECISIONS.md`, is the
authority, and the current mockups are a canvas linked from it.

Two things here are now actively wrong and are kept only as a record of how the
thinking started:

- There is **no FormatKit and no Phase 1**. The format code is not ported to
  Swift at all; `machuna.py` is frozen and does the conversion.
- `native-gui-mockup.png` predates the decision to make the source list a
  **table** with per-item output naming, status and a live output cell.

`menu-model.md` is closer to current, but see the correction noted in it.

## Contents

- `native-gui-mockup.png` — rendered mockup of a native MacHuna window (menu bar, unified toolbar, source-list sidebar, adaptive conversion settings).
- `native-gui-mockup.html` — self-contained source for the mockup (theme variables and icon font inlined). Edit and re-render to a PNG with any Chromium browser:

  ```
  "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" \
    --headless=new --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=752,540 --virtual-time-budget=3500 \
    --default-background-color=FFFFFFFF \
    --screenshot="$PWD/native-gui-mockup.png" \
    "file://$PWD/native-gui-mockup.html"
  ```
