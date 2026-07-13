# design/ — reference material only

These files are **reference material for the eventual native Swift port** of
MacHuna (the "mac-arsed" rewrite). They are **not part of the shipping Python
app**:

- nothing here is imported by `machuna.py`, bundled by `MacHuna.spec`, or covered by `test_machuna.py`
- nothing here is on the release checklist in `CLAUDE.md`
- nothing here is published to the `Machuna Share` folder

They exist purely to capture design intent so it isn't lost. Treat them as a
sketch, not a spec.

When the Swift port actually begins (Phase 1, FormatKit), it should live in its
own repository (e.g. `DNSVision/MacHuna-Swift`), not here. This folder is a
temporary home until that point.

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
