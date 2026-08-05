# MacHuna — Claude Code Instructions

MacHuna is a single-file Python app (`machuna.py`) that translates broadcast media assets between formats: video, TGA sequences, and stills to/from Grass Valley Kahuna `.SWS`, Kayenne MOV, Kayenne TGA, and Sony TGA. Built collaboratively by David Steer (DNS Vision) and Claude. David has no coding background — Claude writes all code.

## Dev environment

- Machine: MacBook (Apple Silicon M5)
- Python: `/opt/homebrew/bin/python3.12`
- Build: `python3.12 -m PyInstaller MacHuna.spec -y`
- Run for testing: `/opt/homebrew/bin/python3.12 machuna.py --gui`

## Staying current between sessions (git-anchored)

To stop Claude's understanding of the code drifting from what is actually built, the working state is anchored to a git commit rather than to memory or the prose docs.

- **On resuming** a session that will touch this repo: read the "Session Anchor" block at the top of `HANDOVER_NOTES.md`, then run `git log --oneline <anchor>..HEAD` and `git status -s`. Reconcile anything that changed since the anchor before trusting the docs or prior memory — the code is the source of truth. A full re-read of `machuna.py` is only needed when that diff is large, after a long gap, or before a big undertaking (e.g. the Swift port); otherwise just read the changed areas.
- **On finishing** a session that changed the repo: update the "Session Anchor" block in `HANDOVER_NOTES.md` to the new HEAD (short commit + date) with a one-line note of what moved.
- Always distinguish "we decided this" from "I verified this in the code" — never assert a file/line fact from memory, check it. Same discipline as the UNCONFIRMED hardware flags.

## On every release (version bump)

When the version number in `machuna.py` changes, update ALL of the following — no exceptions:

1. **`machuna.py`** — `VERSION = "x.x.x"` near the top
2. **`CHANGELOG.md`** — add a new `## vX.X.X — YYYY-MM-DD` section describing what changed
3. **`DEVELOPMENT_NOTES.md`** — update `**Current version:**` line and prepend a one-line summary to the version history in that line
4. **`HANDOVER_NOTES.md`** — update the `**MacHuna:**` line under `## Current Versions`
5. **`README.md`** — update if any user-facing features, supported formats, or workflow steps changed
6. **`USER_MANUAL.md`** — update if any user-facing feature, behaviour, format, workflow step, or field-order/interlace handling changed. This is a user-facing document — do not let it drift out of date behind the code.
7. **`MacHuna_User_Manual.pdf`** — if `USER_MANUAL.md` changed (including the version stamp on its title line), regenerate the PDF so it matches. Requires `pandoc` + `weasyprint` (both installed on the M5). Command:

   ```
   pandoc USER_MANUAL.md -f gfm -t html5 -s -c manual_style.css --pdf-engine=weasyprint -o MacHuna_User_Manual.pdf
   ```

   Styling lives in `manual_style.css`. Use `-f gfm` so the Contents links resolve (GitHub-style anchors).

Before building, run the test suite and confirm it passes:

```
/opt/homebrew/bin/python3.12 -m pytest test_machuna.py -v
```

Then build with PyInstaller and push to GitHub unless David says otherwise.

8. **Sync the public share folder** (`~/Desktop/Machuna Share`) — after the build and push, refresh the three published artefacts so people with the link get the latest release. Only these three, nothing else:
   - `dist/MacHuna.app` → `MACHUNA APP/MacHuna.app` — remove the old bundle first (`rm -rf`), then `cp -R` the fresh build.
   - `MacHuna_User_Manual.pdf` → `USER MANUAL/MacHuna_User_Manual_vX.X.X.pdf` (versioned filename matching the release). **Delete the previous `MacHuna_User_Manual_v*.pdf`** first so only the current version remains.
   - `DEVELOPMENT_NOTES.md` → `DEV NOTES/DEVELOPMENT_NOTES.md` (replace).

   The share is an iCloud-shared Desktop folder; verify the exact subfolder names before copying (`ls "$HOME/Desktop/Machuna Share"`) in case they change. This publishes to a public download link, so only run it for a finished, pushed release.

## Architecture notes

- Single file: `machuna.py` (~2,600+ lines). Contains conversion engine, SWS header builder, extraction engine, Video Player, audio handling, GUI, settings, and CLI.
- Version constant: `VERSION` near top of file — title bar reads from it.
- SWS format constants (`VIDEO_STANDARDS`, `FORMAT_VARIANTS`, `FORMAT_VARIANT_FPS`, `FORMAT_VARIANT_DISPLAY`) are all keyed by standard name string (e.g. `'1080i50'`).
- All ffmpeg calls go through `_run_ffmpeg()` so Stop/Cancel can kill them.
- Build output: `dist/MacHuna.app`
- Tests live in `test_machuna.py` and cover the SWS header builder and all four format constant tables. Update them if `build_sws_header`'s signature changes or any header byte offsets/constants change. The format table tests auto-cover new video standards (they iterate the dicts), so adding a standard doesn't require new test cases — just run the suite to confirm consistency.

## Key constraints

- Do not add unverified video standards to the dropdown — they must be confirmed against real K-Watch reference files first.
- Field order for P→I transcoding is TFF (SMPTE standard for 1080i HD) — unconfirmed on 1080i hardware as of v1.5.19.
- PyInstaller builds must happen on the M5 MacBook (Apple Silicon).

## Extraction output hardware unknowns

MacHuna's extraction logic is correct by code analysis, but the following output paths have never been tested on real hardware. Do not remove the UNCONFIRMED notes in the code or README until these are verified:

- **Kayenne MOV output** — never loaded on a live Kayenne ClipStore/Image Store
- **Kayenne TGA output** — frame naming and format unconfirmed
- **Sony MVS clip naming** — 4-char prefix convention unconfirmed on a live Sony MVS
- **Interlaced SWS → MOV: interlace metadata** — ProRes container has no field-order flags; unknown whether a Kayenne desk requires them. Potential fix when confirmed: add `-field_order tb` (TFF) or `bb` (BFF) to `_hula_convert_mov` ffmpeg command
- **Sony MVS 25i field order** — TFF default (on engineer advice); BFF toggle retained in UI if incorrect on hardware
- **MOV → TGA** — full path coded, never hardware-tested

Full detail in `DEVELOPMENT_NOTES.md` under "Extraction output hardware unknowns".
