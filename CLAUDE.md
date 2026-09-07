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
- The **canonical roadmap / open-work list** is in `DEVELOPMENT_NOTES.md` under "Roadmap (canonical)". Treat it as the single authoritative list of what is left to do; `README.md` and `HANDOVER_NOTES.md` point to it. Reconcile it against git and the code, and do not start a second roadmap anywhere else.

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

8. **Refresh David's own copy** — `rm -rf /Applications/MacHuna.app && cp -R dist/MacHuna.app /Applications/MacHuna.app`. His Dock points at `/Applications/MacHuna.app`, so without this step he keeps launching the previous release while `dist/` quietly moves ahead. This is his private copy and is **not** published; do it on every release.

9. **Publish to dnsvision.tv** — **only when David explicitly asks.** Deliberately decoupled from step 8: he wants to run a build himself before the public gets it, so a release never implies a publish.

   ```
   ./publish.sh --upload
   ```

   That builds `publish/` and uploads it: the versioned zip to the Cloudflare R2 bucket `machuna`, then the site to the Worker `soft-glade-217b`, then verifies the live URLs. **The zip always goes first** — the page and `version.json` both announce a version, so if they led, MacHuna would tell people about a release the download link could not serve. The script enforces the order and refuses to run if `machuna.py`, the built `.app`, `website/machuna/version.json` and the page disagree about the version.

   **Before publishing, update `website/machuna/version.json`** (version, released, summary, download URL) **and the page at `website/machuna/index.html`** (current-release panel, download link, mailto subject, and a new entry at the top of the release list). The script will refuse if you forget the page — that check exists because it was forgotten once.

   Uses `~/.machuna_publish_token`, a Cloudflare API token scoped to Workers R2 Storage:Edit and Workers Scripts:Edit only. It cannot touch DNS, the domain or email. **Expires 2027-09-07** — if Cloudflare rejects it, the script says so and where to make a new one.

   `./publish.sh` with no arguments builds `publish/` and opens it for a manual drag, if the automation is ever unavailable.

   **Deleting the superseded zip from the bucket is not automated** and stays a human decision; it is the only irreversible step.

   *(The old `~/Desktop/Machuna Share` iCloud folder is retired as of 2026-09-07. It is stale at v1.6.20 and nothing publishes to it. Do not sync it; do not treat its contents as current.)*

## Architecture notes

- Single file: `machuna.py` (~2,600+ lines). Contains conversion engine, SWS header builder, extraction engine, Video Player, audio handling, GUI, settings, and CLI.
- Version constant: `VERSION` near top of file — title bar reads from it.
- SWS format constants (`VIDEO_STANDARDS`, `FORMAT_VARIANTS`, `FORMAT_VARIANT_FPS`, `FORMAT_VARIANT_DISPLAY`) are all keyed by standard name string (e.g. `'1080i50'`).
- All ffmpeg calls go through `_run_ffmpeg()` so Stop/Cancel can kill them.
- **The update check fetches via `/usr/bin/curl`, never Python's `urllib`/`ssl`, and this must not be "tidied up".** The bundled app ships Homebrew's libssl whose compiled-in `OPENSSLDIR` is `/opt/homebrew/etc/openssl@3` — a path that exists on the M5 and on no recipient's Mac, so Python HTTPS would fail on every machine but this one, *silently*. curl uses the macOS system trust store. Never disable certificate verification: the manifest tells people where to download software from.
- `UPDATE_MANIFEST_URL` is `https://dnsvision.tv/machuna/version.json`. **It is baked into every shipped copy — never move it.**
- Build output: `dist/MacHuna.app`. `/Applications/MacHuna.app` is David's own copy (what his Dock launches — refresh it every release, step 8). The published copy is now the zip in the Cloudflare R2 bucket, not a folder on disk. The spec sets `bundle_identifier='com.dnsvision.machuna'` and stamps `CFBundleShortVersionString` from `VERSION`, so ⌘I in Finder tells copies apart; anything reporting 0.0.0 predates v1.6.20. The stale `~/Desktop/Machuna Share` copy is retired and should be ignored.
- `website/` is the source of the public download page; `publish.sh` builds `publish/` from it and uploads. Neither is part of the shipping app. **`website/` and `publish/site/` are easy to confuse** — `website/` is tracked and has no manual PDF in it; `publish/site/` is the built upload. The manual is copied in from the repo root at publish time so there is only ever one to keep current.
- The manual PDF is a **build input** as of v1.7.0 (`MacHuna.spec` `datas`), because Help ▸ MacHuna User Manual opens the bundled copy. Regenerate it before building, not after.
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
