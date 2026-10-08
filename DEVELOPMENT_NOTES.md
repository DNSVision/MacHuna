# MacHuna — Development Notes

This document is for continuity between development sessions. If starting a new Claude session, point Claude at this file and the main machuna.py source and development can resume from where it left off.

---

## Project Summary

MacHuna is a macOS application that converts video and still image files to the Grass Valley Kahuna `.SWS` native format. It was built collaboratively between David Steer (DNS Vision Limited) and Claude (Anthropic) with no prior coding experience on David's part.

**Current version:** v1.12.3
**Status:** Tested on a live Grass Valley Kahuna mainframe and a live K-Frame. v1.12.3 (2026-10-08): soft keys on unlabelled clips keep 16-bit precision to EIF (8-bit grey since v1.12.1 put them up to 5 levels off the source alpha) - found by the regression run on David's real material, judged against the source. v1.12.2 (2026-10-08): 59.94 and 60 are one family everywhere - interlaced 59.94 <-> 60 passes through untouched, logged as 0.1% fast/slow (David). v1.12.1 (2026-10-08): the engine-soundness release - 324-case conversion matrix through MacHuna 2.0's bridge, three independent reviews and a black-box pass; decisions A-M: rate conversion keeps duration (one frame rule, exact 59.94), every SWS 1920x1080, SWS to SWS 10-bit and lossless, atomic EIF writes, EIF to SWS honours the standard and keeps the key, dual mono, untagged HD as BT.709, MOV to TGA 1920x1080 RGBA, Sony names exactly 4 characters. v1.12.0 (2026-10-08): the K-Frame desk-session release - 25fps EIF rate code fixed (50i clips played too fast); `.eaf` read correctly (4ch 24-bit-in-32-bit LE, not 8ch 16-bit BE) and written for EIF output; EIF to SWS and SWS to SWS carry audio; mono to both channels; K-Frame and Sony TGA weave only fast progressive sources; interlaced TGA to EIF as woven 25fps; RGB-to-EIF encoder rounds and filters colour co-sited; Video Player plays EIF audio; all hardware warnings lifted (K-Frame confirmed on the desk, Sony on David's judgement). v1.11.0: a keyless source no longer gets a flat key plane - confirmed on a live Kahuna 2026-09-18 that the plane loads as a black key and keys out to nothing, so it only doubled the file. Halves every keyless file. First deliberate divergence from K-Watch, made on evidence. _generate_white_key removed. v1.10.3: interlaced TGA → progressive MOV restored - v1.10.2 removed it on the reasoning that ProRes has no field-order flag, which is true for WEAVING and irrelevant to DEINTERLACING. Bob gives one frame per field, so 25fps interlaced becomes 50fps progressive of the same length. v1.10.2: QuickTime MOV from a TGA sequence gets its own frame-rate control instead of borrowing the SWS Standard dropdown - that list has no progressive 30fps (only interlaced), so 30fps material played at double speed. The interlaced tickbox is hidden for MOV and would not have helped (tested). v1.10.1: QuickTime MOV output can be named per item (new BESPOKE_MODE_MOV; blank = source name, so v1.10.0 behaviour is the default). David spotted the gap on first use. v1.10.0: QuickTime MOV output (SWS/EIF/TGA sequence → ProRes 4444 with alpha and audio), plus .eaf audio reading - programme channels picked by sample-to-sample correlation, not loudness, because channels 0 and 2 carry loud non-audio spikes. MOV is no longer a desk format, so it leaves the hardware-unknowns tables and the desk checklist. Also: the MOV "Include audio" checkbox was ignored, output_format was saved but never restored, and a structural guard now ties dropdown labels to their warning keys. v1.9.3: The manual, README and About box no longer position MacHuna against K-Watch - positive Mac-native framing instead; neutral technical K-Watch references (split format, 0x1680, TGA naming) kept on purpose as interoperability facts. v1.9.2: Terminology - the Kayenne output formats are renamed K-Frame, because Kayenne is a control panel and the Image Store that holds .eif/.eaf lives in the frame, which Karrera and GV Korona also drive; provenance statements ("real Kayenne files") and the historical record are deliberately left as written. Also corrected the in-app and manual claim that the .eaf format was unknown - it was decoded on 2026-09-09. v1.6.20: Packaging and workflow, no app-code change. `MacHuna.spec` left `bundle_identifier=None` (PyInstaller then defaults it to the bundle name "MacHuna") and stamped no version, so every copy on the machine claimed one identity and reported 0.0.0 in Finder - which is how David's Dock ended up launching a v1.6.12 build all day while `dist/` moved on. Now `com.dnsvision.machuna` with `CFBundleShortVersionString`/`CFBundleVersion` read from `VERSION` by a `_read_version()` helper in the spec. His own copy now lives at `/Applications/MacHuna.app` (Dock re-pointed there; Dock plist backed up to `~/.machuna_backups/`), refreshed as step 8 of every release, and **publishing to the share folder is now a separate opt-in step 9** - he wants to run a build before the public gets it, so the share copy may sit several versions behind by design. This also clears the long-standing 0.0.0 cosmetic note. Also rewrote USER_MANUAL section 4.4 as one coherent section: it had been written a paragraph per release across v1.6.13-v1.6.19 and read as a changelog in prose, with an apparent self-contradiction on kept-versus-cleared values. Now ordered by task with a kept/cleared table, a worked example, and no inline version tags. v1.6.19: Wording only. The Sony TGA one-clip-at-a-time error now leads with "To batch convert to Sony TGA, tick 'Use bespoke names'" and explains the shared-field limitation afterwards, rather than burying the workaround in its third paragraph (David's observation). The grey note beside the shared Clip name field points at bespoke names too. No behaviour change. v1.6.18: Fixed the stale duplicate mark David spotted - the v1.6.17 trace cleared only the edited row, so fixing one half of a duplicate pair left the other still flagged. Editing now calls `_bespoke_recheck()`, which re-analyses the whole batch and applies the result via `_bespoke_apply_marks(codes, only_marked=True)`; the `only_marked` guard is what stops typing marking fields that were never flagged (blank is the normal starting state), and rows track their own state in `hint.marked`. `_bespoke_mark()` keeps the scroll-and-focus, `_bespoke_recheck()` deliberately does not, so the cursor is never yanked mid-edit. `_bespoke_reset()` now also destroys the row widgets instead of just clearing the list that tracked them. v1.6.17: A blocked bespoke batch now marks every offending field in red with a per-row reason, scrolls to the first and focuses it; typing clears that row's own mark. `validate_bespoke_ids()` and the new `bespoke_row_issues()` are both thin wrappers over a shared `_analyse_bespoke_ids()` returning (per-row codes, grouped messages), so the dialog and the field marks cannot disagree. Also fixed the truncation David spotted: the panel is measured once at rebuild while the hints still read "1-9999", so a longer mark was clipped — the hint column now reserves `_BESPOKE_HINT_WIDTH` (17 chars, >= "duplicate number"), which also stops marking shifting the layout. **Panel height deliberately left fixed** — auto-growing just relocates the problem to the window height (David's point), and the real answer is a resizable/paged layout in the Swift rewrite. 94 unit tests (9 new). v1.6.16: Unticking the bespoke checkbox is now the "start over" gesture — new `_clear_selection()` empties `_selected_items`, `_selected_folders`, the input type and the audio/TGA flags as well as the typed IDs, resets the summary, disables Convert and logs why. With v1.6.15's "Add to List" the selection could otherwise only grow. v1.6.15: Batches can now be built up from more than one folder. The folder browser gained an "Add to List" button (shown only when something is already selected) alongside "Select", which still replaces. `open_files` was restructured so no state is touched until a button is pressed — cancelling the dialog previously left `_input_type[0]` set to the scanned folder's type. New module-level `merge_input_types()` decides whether two selections can share a batch (encode-to-SWS and extract-from-SWS are separate families; from_sws + from_eif merges to mixed_eif_sws) and is unit-tested. Bespoke values are now also cleared on *untick*, and "Select" blanks the panel while "Add to List" preserves it — building a list up keeps your typing, starting a new one does not. 85 unit tests (6 new). v1.6.14: Two bespoke-mode refinements from David's first hands-on test. Bespoke fields now blank on every *return* to the mode — cleared when the checkbox is ticked on and again when a bespoke batch finishes — instead of holding values for the whole session; preservation across a selection change while the mode stays on is kept, as that is the case where retyping is a nuisance. The panel's scrollbar now sits beside the list (canvas sized to `bespoke_inner.winfo_reqwidth()` and packed without `expand`, scrollbar packed `side='left'`) rather than at the far right edge of the window, 597px away from the rows it scrolls. v1.6.13: Bespoke per-item output IDs on batch convert — a checkbox alongside the existing numbering/naming controls swaps the single auto-sequence control for a scrollable panel with one input per selected item: an output number (1-9999) for Kahuna SWS and Kayenne EIF, a 4-character clip name for Sony TGA. Offered for those three outputs only (Kayenne TGA and TGA Sequence self-name from the source). Fields start blank on purpose so unfinished rows are obvious, and values survive a selection change. Three blocking checks run before anything is written — valid/in-range, no in-batch duplicates, no collision with the destination (`N.SWS` as file *or* split-file folder, `NNNN.eif`, or a Sony clip-name folder) — all naming the offending items, with no overwrite path offered. This also lifts the Sony TGA one-clip-per-batch cap when bespoke names are in use: distinct names mean distinct folders, so several Sony clips can convert together; the cap is retained when they are not. Unticked behaviour is byte-for-byte unchanged. New module-level `validate_bespoke_ids()` / `normalise_bespoke_value()` carry the rules so they are unit-testable outside the GUI; 79 unit tests (20 new). Verified by driving the real GUI: 25 scripted checks covering blocked and successful batches for both numbers and Sony names. v1.6.12: Three fixes clearing the last code-only items before hardware testing. Fix 9(b) — cross-rate interlaced→progressive played at the wrong speed; new shared helper `_i_to_p_filter()` appends an fps resample whenever bob-deinterlacing alone would miss the target rate, applied to all four i→p paths (verified: 4s 25fps i-source → 1080p60 gave 200 frames/3.33s before, 240/4.00s after). This also caught an unrecorded instance in `convert_clip`'s own down-rate branch (29.97i → 1080p25 ran 20% slow: 120 frames before, 100 after) — the path the review cited as the good example. Raw TGA sequences unchanged (no declared source rate exists to resample from; assumption now explicit). Fix 10 — the Sony TGA TFF/BFF toggle was displayed but ignored (weave and yadif parity both hardcoded TFF); now honoured in all four sites and named in the log, with `_p_to_i_field_map` gaining a `field_order='TFF'` default so the hardware-confirmed SWS weave is byte-identical. Fix 4 — a still selected with EIF/Sony TGA/TGA Sequence output silently produced nothing (no handler for single-image items, in `_run_to_eif` as well as `_run_to_tga_seq`); now blocked up front with a named-file error. **Stills are SWS-only, permanently — see "Stills are SWS-only (settled)".** 59 unit tests. v1.6.11: Fixed clip→EIF wrong-speed bug (Fix 14) — `convert_clip_to_eif` extracted frames at the source rate but stamped the header at the nearest EIF rate (25/50), so any non-25/50 source (29.97/30/59.94/60fps) played at the wrong speed on a Kayenne. Extraction now resamples to the chosen EIF rate (`vf_extra=f'fps={fps:g}'` on `convert_to_v210`, applied to both fill and key planes) so frame count matches header fps and duration is preserved; verified end-to-end (60fps 2s clip → 100 frames @ 50fps = 2.0s) plus 7 new unit tests. EIF output remains hardware-unconfirmed. v1.6.10: Fixed the progressive→interlaced same-rate speed bug (Fix 9(a)) — the p→i weave halves the frame count, which is only correct for a double-rate (field-rate) source (50p→1080i50 etc.); a same-rate source (25p→1080i50) was being silently halved and played at 2× speed. New shared helper `_p_to_i_field_map()` now weaves only at the field rate and blocks same-rate and cross-rate sources with a clear error (no file written) rather than producing a wrong-speed clip. Applied to the three p→i paths that know their source fps: video-clip→SWS (`convert_clip`), SWS→SWS (uses the source header's fps), and clip→TGA extraction. Raw TGA-sequence p→i is unchanged (no source fps available — still assumes a double-rate field stream; assumption now documented in code). No PsF path shipped, so nothing new is hardware-unconfirmed; the double-rate weave remains confirmed. v1.6.9: SWS→SWS metadata fixes — output header clip name now follows the source SWS name (was the placeholder "0001" from the temp intermediate frames), a keyless source no longer gains a phantom key plane (the extractor always writes RGBA, so has_key must be forced to follow the source), and dropped audio is now flagged in the log instead of silently discarded (validated in-app: 1080i50→1080p50 logged `clip name: 51  key: yes`). Also confirmed empirically that TGA-Sequence/Sony-TGA output does NOT drop alpha through yadif/tinterlace — the reviewed report was a false alarm; RGBA test frames through both filters preserved the alpha channel, so no change was made. v1.6.8: 720p/50 and 720p/59.94 withdrawn from all format tables and the dropdown — the SWS output was never hardware-verified and the v210 plane_size maths is wrong for 1280-wide (non-48-multiple) output, so it produced corrupt files. This is a "broken + unverifiable export" withdrawal, NOT "obsolete format": 720p/59.94 is still actively broadcast (ABC/Fox, 2026) and is a reinstatement candidate once a K-Watch 720p reference and hardware verification are available. v1.6.7: TGA→SWS interlaced source now uses yadif deinterlacing (send_field, TFF) instead of frame duplication — correct motion, no comb artefacts (validated in-app: 30 interlaced frames → 60 progressive, smooth playback); USER_MANUAL.md added to the release checklist so the manual no longer drifts behind the code. v1.6.6: Sony TGA added as output option for TGA sequence input — direct TGA→Sony TGA conversion with i↔p handling (tinterlace/yadif); "TGA source interlaced" checkbox shown; Sony naming convention (CN0000.tga in CN/ subfolder). v1.6.5: SWS→SWS i↔p conversion (two-step TGA intermediate; source interlace auto-detected from header; yadif for i→p, tinterlace for p→i); TGA Sequence output for TGA and clip inputs (same filter logic; subfolder per sequence); Kayenne MOV removed from SWS output (unconfirmed hardware). v1.6.4: TGA→EIF interlaced path now uses yadif deinterlacing (send_field, TFF) instead of frame duplication — correct motion and no comb artefacts. v1.6.3: Field order default changed from BFF to TFF (engineer advice — TFF correct for all known 1080i HD workflows); TFF now appears first in UI radio buttons; BFF retained as fallback. v1.6.2: EIF→EIF routing bug fixed (removed Kayenne EIF output option when input is EIF — was silently no-op); doc corrections. v1.6.1: Code cleanup — dead code removal (5 superseded functions), `_eif_parse_unit` helper extracted, redundant numpy imports removed, player status bar text fixed. v1.6.0: Full EIF feature set — EIF read (Video Player), EIF write (TGA/MOV/SWS → .eif with slot naming 0001.eif+), EIF→SWS lossless YCbCr repack, EIF→Kayenne TGA, EIF→Sony TGA, TGA source interlaced option for EIF output, mixed EIF+SWS folder detection, Player file picker (folder→file), format label in Player info strip. All EIF write/conversion paths UNCONFIRMED pending hardware test on live Kayenne desk. v1.5.43: Kayenne EIF output added — MOV/TGA/SWS → .eif conversion with full header construction (18260-byte header verified byte-for-byte against real Kayenne clips), BT.709 YCbCr encoding, 4:2:2 chroma subsampling, key channel, tail sentinel; UNCONFIRMED pending hardware test. v1.5.42: EIF frame rate auto-detected from header (0x0FC = frame duration in µs; 40000=25fps, 20000=50fps); Video Player no longer prompts for frame rate and correctly reports key present. v1.5.41: EIF key channel decoded — bits[29:20] = key level (64=transparent, 940=opaque); wipes and alpha mattes now visible in Video Player key and composite panels. v1.5.40: EIF colour decode fixed — pixel format fully reverse-engineered from real clip (UCI DOWNHILL footage); each 32-bit word = key[29:20] + Y[19:10] + C[9:0] (even=Cb, odd=Cr); three 360-row units stack vertically to form 1920×1080. v1.5.39: EIF playback in Video Player (experimental) — Kayenne native .eif format reverse-engineered; header fields confirmed (clip name 0x004, frame count 0x06C, video start 0x070, video end 0x080). v1.5.38: Video Player now uses folder-based file picker (matches Convert window — TGA sequences collapsed to one entry per sequence); fixed TGA fps picker dialog unresponsive on macOS (transient/grab_set ordering). v1.5.37: Sony TGA multi-file guard — error dialog blocks conversion if more than one clip is selected (all would write to the same folder, second overwrites first). v1.5.36: Fixed MOV → Sony TGA output folder naming (was using MOV filename stem instead of 4-char clip name). v1.5.35: Docs update — TGA sequence naming convention flexibility explicitly documented in README and USER_MANUAL. v1.5.34: Fixed TGA sequence detection for files without a separator between base name and frame number (e.g. FEDX0000.tga). v1.5.33: Unified format-in / format-out interface — MacHuna and Hula merged into a single Convert section; input autodetection drives the Output dropdown; adaptive controls show only what is relevant to the current conversion; MOV → TGA path surfaced with hardware-unconfirmed warning; Sony TGA output folder now named after clip name; "SWS Player" renamed "Video Player"; HulaWindow no longer launched from GUI. v1.5.32: Watch Folder and Slot Override removed (MacHuna is a field tool, not a server app); smart folder browser replaces file picker (TGA sequences collapsed to one entry per sequence); i→p TGA conversion fixed (frame duplication preserves duration); "Include audio" moved to folder browser dialog, shown only when audio detected; "TGA source already interlaced" label shortened. v1.5.31: Hula bugfixes — interlaced SWS → interlaced TGA routing bug fixed; Hula MOV encoder now uses _run_ffmpeg so Stop/Cancel works. v1.5.30: Fixed i→p double-speed bug (bob deinterlace via yadif) + TGA i→i double-speed bug ("TGA source already interlaced" checkbox skips tinterlace). v1.5.29: Watch Folder TGA batch: single combined log + auto-stop when batch complete. v1.5.28: Fixed SWS Player crash when opening/playing a second file with audio (heap corruption — stop() was closing PortAudio stream from main thread while audio thread was in write(); fix: stop() now only signals + joins, audio thread closes its own stream in finally). v1.5.27: SWS Player now accepts TGA sequences and MOV/MP4/MXF/AVI. v1.5.26: Batch Convert confirmation dialog (custom Toplevel, no app icon). v1.5.25: Slot override field in Settings, two-row Settings layout, Batch Convert button visibility fix, default window size 960×460. v1.5.24: Fixed TGA sequence P→I conversion (missing tinterlace filter + wrong frame count). v1.5.23: Open in Finder buttons on Watch Folder, Destination Folder, and Hula Destination Folder rows. v1.5.22: Hula GUI redesigned — full standard dropdown (all 9 formats), MOV input support, Kayenne/Sony TGA targets consolidated (Kayenne TGA UNCONFIRMED). v1.5.21: Hula Sony MVS 25i source guard (rejects non-1080p50 input). v1.5.20: Hula Sony MVS 25i TGA output (field-woven, BFF/TFF toggle). v1.5.19: Compact broadcast metadata display in SWS Player and Hula (standard/frms/duration). v1.5.18: P→I transcoding via tinterlace (TFF, unconfirmed on 1080i hardware). v1.5.17: Interlaced standard codes corrected (0xc923 for all interlaced, 0x8000 = interlaced flag). v1.5.16: TGA removed from Batch Convert file picker. v1.5.15: SWSPlayer playback jitter fixed via absolute timing. v1.5.14: SWSPlayer interlaced playback speed fixed (field rate vs frame rate). v1.5.13: SWSPlayer and Hula fps lookup fixed for all standards. v1.5.12: All ffmpeg calls now go through _run_ffmpeg - Stop/Cancel works for all conversion paths. v1.5.11: Ignore alpha for TGA sequences fixed. v1.5.10: FORMAT_VARIANTS lookup table applied - format variant (0x18C) now correct for all nine standards. v1.5.9: Unverified standards removed from dropdown. v1.5.8: All nine video standards fully confirmed by K-Watch hex analysis; progressive-to-interlaced mismatch warning added. v1.5.7: Stop button kills ffmpeg immediately; Cancel Batch button added. v1.5.5: Format variant field (0x18C) initial fix. v1.5.4: Window size persistence. v1.5.0: Hula SWS Extractor integrated. v1.4.0: SWS Preview Player integrated. v1.3.0: Large file split (>4GB) confirmed working on live Kahuna.
**Repository:** https://github.com/DNSVision/MacHuna
**Dev machine:** MacBook Air M5 (Apple Silicon; all dev and building happens here)

---

## Development Environment

- **Python:** 3.12
- **Key libraries:** Pillow, numpy, sounddevice, tkinter (built-in), subprocess, struct, tkinterdnd2-universal (installed but currently disabled)
- **ffmpeg:** Installed via Homebrew (`brew install ffmpeg`). The build resolves it from PATH via `shutil.which`, so the version is not pinned.
- **PyInstaller:** Installed via pip3.12
- **Working directory:** `~/Developer/MacHuna/`
- **Main script:** `machuna.py`

### Setting up on a new Mac (Apple Silicon)

The M5 (and any future Apple Silicon Mac) needs the toolchain installed once, then a clone. `MacHuna.spec` is portable and tracked in the repo, so no files need copying by hand.

```bash
# 1. Homebrew first if not present:
#    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. System tools + libraries (python-tk is what gives Python its GUI/tkinter)
brew install python@3.12 python-tk@3.12 ffmpeg pandoc weasyprint git gh

# 3. Python packages
#    Homebrew's python@3.12 is an "externally-managed" environment (PEP 668), so a
#    bare `pip install` is blocked. Use --user --break-system-packages: it installs
#    into ~/Library/Python/3.12 for this interpreter (leaving Homebrew's own
#    site-packages untouched) so the bare `/opt/homebrew/bin/python3.12` commands
#    below (run, test, build) all find the packages without a venv.
#    pytest is needed for the test suite in step 5.
/opt/homebrew/bin/python3.12 -m pip install --user --break-system-packages \
    pillow numpy sounddevice tkinterdnd2 pyinstaller pytest

# 4. GitHub auth, then clone (use the same path so any per-project tooling matches)
gh auth login
mkdir -p ~/Developer && cd ~/Developer
git clone https://github.com/DNSVision/MacHuna.git

# 5. Verify
cd ~/Developer/MacHuna
/opt/homebrew/bin/python3.12 -m pytest test_machuna.py -v      # expect 59 passed
/opt/homebrew/bin/python3.12 machuna.py --gui                  # app launches
python3.12 -m PyInstaller MacHuna.spec -y                      # build works
```

Also install Claude Code itself. `pandoc` + `weasyprint` are only needed for regenerating the user-manual PDF (release step 7).

**Claude Code memory (optional, private — not in this repo):** the project's saved memory lives at `~/.claude/projects/-Users-davidsteer-Developer-MacHuna/memory/`. It does not travel with the repo (it contains personal working notes). To carry it over, either use Apple Migration Assistant (brings all of `~/.claude/`), or restore it from a personal backup zip into that same path. The folder name is derived from the clone path, so keeping the repo at `~/Developer/MacHuna` under the same username makes it a drop-in restore.

### Build Command

Build from the project directory using the tracked spec (`MacHuna.spec`):

```bash
cd ~/Developer/MacHuna && python3.12 -m PyInstaller MacHuna.spec -y
```

The spec is portable: it finds ffmpeg/ffprobe on PATH via `shutil.which` (not a pinned Homebrew Cellar version) and locates `machuna.py`, `machuna.icns` and `machuna_final_1024.png` relative to itself (`SPECPATH`), so it builds on any Apple Silicon Mac regardless of ffmpeg version or username. It fails with a clear "brew install ffmpeg" message if ffmpeg is missing. Built .app appears in `~/Developer/MacHuna/dist/MacHuna.app`. Right-click > Open first time to bypass Gatekeeper.

### GitHub Push Workflow

```bash
cd ~/Developer/MacHuna
git add .
git commit -m "Description of changes"
git push
```

---

## Roadmap (canonical - the one list to work from)

> **This is the single authoritative list of open work.** `README.md` and `HANDOVER_NOTES.md` point here rather than keeping their own copies. The detailed sections lower down (EIF Roadmap, Outstanding review items, Extraction output hardware unknowns, Future Considerations) hold the specifics; this is the index. Reconcile it against git and the code when resuming - see the Session Anchor in `HANDOVER_NOTES.md`.

**Blocked on hardware:**
- ~~**EIF hardware-test session**~~ - **DONE 2026-10-07** on a live K-Frame. EIF write confirmed at 50fps and 25fps/50i, K-Frame TGA from MOV/EIF/SWS, `.eaf` writing, the `0x60` flag (harmless), the KNOCKOUT_WIPE round trip. Results under "KNOCKOUT_WIPE round-trip RESULTS"; fixes in `CHANGELOG.md` "Unreleased".
- ~~**Extraction outputs on real desks**~~ - K-Frame TGA and MOV to TGA **confirmed 2026-10-07**. **Sony TGA warning lifted by David on 2026-10-08 on his own judgement**; its naming and 25i field order have still never been loaded on a Sony desk in testing (engineering note only, not shown to users).
- **STILL UNTESTED ON HARDWARE (as of engine v1.12.3 / MacHuna 2.1.0, live 2026-10-08).** Everything below is proven in software (tests, the 324-case matrix, three reviews, the Fable black-box pass, the real-material regression run) but has never been loaded on the desk it is for. **This is the agenda for the next Kahuna session**; make the test files from source with the current engine, and check the desk is set to the standard you need first (a 1080i desk for the interlaced items).
  - **Kahuna, field order:** P->I weave is TFF (assumed, SMPTE). Confirm on a genuine 1080i Kahuna; a one-word flip to `interleave_bottom` if wrong. Older test files in `~/Documents/DNS Vision/Wipes/MacHuna/DESK TESTS/` predate v1.12.
  - **Kahuna, changed in v1.12.x:** frame-rate conversion (25p to 1080p50, 50p to 1080p25, decision A/H frame picking); SWS to SWS, now 10-bit byte copies (i50 passthrough, p50 to i50 lossless weave, i50 to p50 deinterlace); EIF to SWS at 1080i50 (25fps EIF frames as they are; 50fps EIF woven); dual-mono MOV (track 1 left, track 2 right) and mono on both sides; a split (>4GB) SWS now written with NO audio claimed in its header (decision F).
  - **Kahuna, 59.94/60:** nothing at 59.94 or 60 has ever been played on a Kahuna. Audio at 1602/801 samples a frame has no K-Watch 59.94 reference. 59.94 <-> 60 passthrough plays 0.1% off by design (v1.12.2).
  - **Sony MVS:** never loaded on a Sony desk - 4-character naming, 25i field order (TFF default, BFF toggle), and since v1.12.1 1920x1080 RGBA from clips. In-app warning lifted on David's judgement; the public page still says "Untested on a desk".
  - **K-Frame, after the desk session:** 59.94p and 29.97 sources converted to EIF (frame-picked to 50/25) and the v1.12.3 key precision change - formats already proven, so low risk.

**Open code work (no hardware needed):**
- ~~**White key (INVESTIGATE ONLY)**~~ - **CLOSED 2026-09-17.** The hex comparison was done against K-Watch files predating MacHuna: the generated key matches the reference exactly and must not be changed. **There are now no open code items at all** - everything left is gated on the desk. What came out of it is a new *hardware* question (should a keyless source get a key plane at all?), on the checklist below. Detail in "Outstanding review items" 4. Everything else on this list has been done: Fix 9(b) and Fix 10 in v1.6.12, bespoke IDs in v1.6.13, the post-conversion selection clear in v1.6.21, the Help menu / update check / contact in v1.7.0, and QuickTime MOV output with `.eaf` audio reading in v1.10.0.

**Distribution - DONE 2026-09-07, and MOVED to the Swift repo 2026-09-25:**
- **THE DOWNLOAD IS NO LONGER THIS APP.** `dnsvision.tv/machuna` has served **MacHuna 2.0.0, the Swift app**, since 2026-09-25. It took over this repo's update channel and bundle identifier, so a v1.11.0 copy checking for updates is offered it. **`publish.sh` and `website/` in THIS repo are retired - do not run them.** Publishing now happens from `MacHuna-Swift/publish.sh`, which is a port of this one plus a refusal to publish an app that is not self-contained.
- The 1.11.0 zip was **deleted from the bucket** on David's instruction 2026-09-25. A verified copy is kept at `dist/released/MacHuna-1.11.0.zip` (gitignored) so it can be put back if anyone ever needs it.
- Public download page live at `https://dnsvision.tv/machuna` (Cloudflare Pages/Worker `soft-glade-217b`), app served from R2 bucket `machuna` via `downloads.dnsvision.tv` because Pages caps files at 25 MB.
- **The procedure is documented in `MacHuna-Swift/PUBLISHING.md` and nowhere else.** Page source tracked in `website/` **(in the Swift repo)**; `./publish.sh --upload` builds and uploads, enforcing zip-before-site and refusing to run if the version constant, the built `.app`, `version.json` and the page disagree. **For a site-only change, such as the favicon, build with `./publish.sh` and then `wrangler deploy` alone** - the release script always re-uploads the 35 MB app, which is pointless when only a page changed.
- The site carries a favicon built from the app icon (`MacHuna-Swift/Scripts/make-favicons.py`), added 2026-09-26.
- In-app update notifications and Report a Problem / Suggest a Feature shipped in v1.7.0.
- The `~/Desktop/Machuna Share` iCloud folder is **retired**, stale at v1.6.20. Nothing publishes to it. David may delete it once everyone has the new link.

**macOS floor is 26 - LEFT DELIBERATELY, do not "fix" it (decided 2026-09-17):**
- The shipped `.app` requires **macOS 26 or later**, and the page, `version.json` and README now say so. Before this they claimed macOS 12, which was simply false.
- **The floor is not Apple's doing and not a code problem.** It comes from the machine the build runs on: Homebrew bottles and pip wheels are both built for the current OS and stamp it as their minimum. Measured in the v1.10.1 bundle: **74 binaries at 26.0** (Homebrew - Python, Tcl/Tk, ffmpeg), **13 at 14.0** (numpy's pip wheels), **1 at 15.0** (libmp3lame). PyInstaller's own launcher is 11.0, so it is purely the bundled parts. `Python` itself is 26.0, and PyInstaller loads it before anything else, so on an older Mac the app dies at launch showing nothing.
- **macOS 11 (the first Apple Silicon release) is not reachable** by swapping Homebrew for python.org alone - numpy's wheels would hold the floor at 14. That correction matters: an earlier suggestion in this session that a Python swap would reach macOS 11 was wrong.
- **The real fix, if it is ever wanted, is to build on the oldest macOS to be supported** (an older machine or a cloud runner), because Homebrew and pip both follow the build machine. One change, all three sources drop together.
- **David's decision: leave the floor alone and correct the claim instead.** No user has reported a failure, nobody knows what recipients run, and a CI pipeline is disproportionate to an unobserved problem. **There is no performance argument either way** - the minimum-OS stamp is a compatibility label, not a speed setting.

**MacHuna 2.0 (Swift) - open items.** The interface shipped 2026-09-25; these
are what is left in `DNSVision/MacHuna-Swift`. None blocks anything.
- **`--selftest` resolves `testmedia/` against the working directory**, so from
  anywhere but the repo it reports `0 of 4 opened` and still exits 0. A zero that
  reads as failure should say the media is missing instead. Found 2026-09-26
  while verifying the published build.
- **No Settings window**, and possibly none needed - everything lives in the
  inspector and the menus. Recorded so the absence is a decision, not an oversight.
- **`DNSVision/MacHuna-Swift` is private**, by David's decision 2026-09-24. It can
  be opened whenever there is something worth showing.
- The **full Swift rewrite of the conversion pipeline** is a later phase - see the
  last paragraph of this roadmap.
- **GUI questions raised by the K-Frame desk session (2026-10-07), to resolve
  with David before building:**
  - ~~**EIF audio controls**~~ - **DECIDED 2026-10-08**: one Include audio
    tickbox exactly as for SWS - shown only when the source has audio, on by
    default, binary, first two source channels become L/R. Mono to match SWS
    (to be checked). Spec in `MacHuna-Swift/DESIGN_DECISIONS.md` section 43.
  - ~~**The Standard control for K-Frame TGA output**~~ - **DECIDED 2026-10-08**:
    no Standard control; worked out from the source, asking only when there is a
    real choice (a progressive 50fps source: "Is the desk 50p or 50i?"). An
    interlaced source is never woven again. K-Frame TGA only for now. Spec in
    `MacHuna-Swift/DESIGN_DECISIONS.md` section 44. **Engine half DONE
    2026-10-08** (source-aware weaving, `kframe_tga_asks_desk_format`); the
    Swift control is still to build.
  - ~~**Dragging an EIF that has an `.eaf`**~~ - **DECIDED 2026-10-08**: the drag
    carries both files, the row shows audio is present, clashes are left to the
    Finder, and a missing `.eaf` counts as a vanished output. Spec in
    `MacHuna-Swift/DESIGN_DECISIONS.md` section 42; built once `.eaf` writing
    exists.

- **AUDIO MUST MATCH THE TARGET, WHATEVER THE SOURCE (David, 2026-10-08).**
  Every route that carries audio must write exactly what the target desk expects:
  - Kahuna SWS: in-file, 16ch 16-bit LE 48kHz, L on 1, R on 3.
  - K-Frame EIF: companion `.eaf`, 4ch 24-bit-in-32-bit LE 48kHz, L on 1, R on 2,
    zero-padded to frame_count x samples-per-frame (spec under the 2026-10-07
    desk results).
  - QuickTime MOV: stereo PCM 48kHz.
  Sources vary: MOV at 16 or 24-bit, mono to multichannel, sometimes 44.1kHz;
  SWS's 16-channel layout; EIF's `.eaf`. **Proof required: an outcome test for
  every source x target pair carrying audio** - convert a file with KNOWN audio,
  read the written output back from disk, and check sample rate, channel slots,
  bit depth, length against frame count, and content against the source.
  Bit-exact where nothing is lost (e.g. 16-bit into `.eaf` is the sample `<< 8`);
  where something must be lost (24-bit into 16-bit SWS) the test pins down the
  exact rule. **State on 2026-10-08:** EIF to MOV was reduced to 8-bit by
  `read_eaf_stereo` - FIXED (now 24-bit, bit-exact, proven end to end from the
  desk's own KNOCKOUT_WIPE clip). **EIF to SWS carries no audio at all** (an
  earlier note here wrongly said it came through at 8-bit; it never reads the
  `.eaf`). SWS to EIF and MOV to EIF carry no audio until `.eaf` writing exists.

- **Audio decisions for fix 3 (David, 2026-10-08):**
  - **Mono goes to BOTH left and right, for SWS and EIF.** Measured on v1.11.0:
    SWS put a mono source on the left only (`pan=16c|c0=c0|c2=c1` has no second
    input channel for right) - an accident of the routing, never
    hardware-confirmed. Stereo and multichannel SWS output must stay
    byte-identical; only mono changes.
  - **`NNNN.eif` and `NNNN.eaf` are one output.** Writing an EIF either writes
    fresh audio or removes a stale `.eaf` of the same name, and logs it. A
    leftover `.eaf` would otherwise put an old clip's sound on air with a new
    picture, because the desk pairs them by name alone.

- ~~**Interlaced TGA sequence to EIF disagrees with the desk**~~ - **FIXED
  2026-10-08**: `convert_tga_seq_to_eif(source_interlaced=True)` now writes the
  woven frames as they are at 25fps (yadif branch removed), scaling non-1080
  frames one field at a time. Progressive output byte-identical. Settles the
  old "Interlaced EIF reconciliation" item: the routes now agree with the desk.
- **Split SWS files drop their audio but the header still declares it
  (pre-existing, found 2026-10-08 during fix 3).** `write_sws` sends anything
  over the FAT32 limit to `_write_sws_split`, which never writes audio
  ("audio is not supported in split files"), but the header was already built
  with `has_audio=True`. Affects MOV to SWS since long before the desk fixes, and
  now EIF to SWS for long clips too. Not changed by fix 3. Fix: build the header
  after deciding whether the file splits, or support audio in split files once a
  reference exists.

- ~~**Sony TGA weaves an already-interlaced MOV a second time**~~ - **FIXED
  2026-10-08 at David's instruction**, same rule as K-Frame TGA: only a
  progressive source at 50fps or more is woven. TNTS 50i to Sony at 1080i50 now
  30 frames (was 15). Sony output itself is still unconfirmed on a Sony desk.
- **The full conversion matrix lives in `MacHuna-Swift/testmedia/matrix/`**
  (`matrix.py`, `analyse.py`). It drives MacHuna 2.0's bridge with the engine and
  checks every result from disk (duration, rate, standard, key, audio presence,
  channels, length and content against an independent decode). Re-run it after
  any engine change: `python3.12 matrix.py && python3.12 analyse.py` (about 30s).
  On 2026-10-08 after the v1.12.1 fixes: 254 cases, 215 pass every rule, 0 break
  a rule, 39 deliberate refusals. `bridge_planned.py` there is the bridge WITH the
  engine-move changes below already applied and matrix-tested - start the Swift
  stage from it.
- **Swift bridge changes that MUST land with the engine pin move (2026-10-08),
  not before** - the pinned v1.11.0 engine does not have these arguments or
  functions, so adding them early would break every conversion they touch:
  - Pass `include_audio=job.get("includeAudio", True)` to `convert_eif_to_sws`,
    `convert_clip_to_eif` and `convert_sws_to_eif` (bridge ~lines 391, 506,
    509). Without it the Include audio tickbox is ignored for those routes.
  - Replace the bridge's own SWS-to-SWS routing (~lines 412-440, which still
    drops audio) with one call to `m.convert_sws_to_sws(...,
    include_audio=...)`.
  - Run `--selftest` after the move: it pins some behaviour against the engine.
  - `_to_eif` and `_to_sws` (EIF source): a cancelled conversion now returns None
    (nothing is written and any previous `.eif`/`.eaf` pair is kept, decision L;
    an EIF-to-SWS writes nothing). The bridge
    ignores return values today, so cancelled rows show "done" with an empty
    path. Report them as cancelled (second review, 2026-10-08).
  - The bridge's own MOV/TGA-sequence to TGA routes (`_to_tga_seq`, ~lines
    516-610) duplicate engine work and miss three Fable-pass fixes. Either call
    the engine (`_hula_convert_mov_to_tga`) or apply each: read TGA input through
    `m._tga_input_args` (TGAs are never guessed - a byte-9 frame was misread as
    CD+G); Sony names through `m.sony_clip_name` (decision M - it builds
    `f"{clip_name}%04d.tga"` itself); untagged HD as BT.709 and 1920x1080 32-bit
    RGBA output (decision I).
  - A still sent to K-Frame TGA should be refused cleanly ("stills convert to
    Kahuna SWS only"); today it is routed as an extraction, fails, and leaves an
    empty folder.
  - **Update MacHuna 2.0's own manual** (`MacHuna-Swift/USER_MANUAL.md`) to tell the same story as the engine manual's v1.12.0 changes: EIF audio, no hardware warnings, interlaced TGA to EIF, mono, SWS-to-SWS audio, ProRes colour advice, K-Frame Sequence import.
- **Swift side of fix 5 (do with the engine pin move):** `Sources/MacHuna/Item.swift`
  `unverifiedNote` has its own copy of the hardware warnings (K-Frame EIF,
  K-Frame TGA, Sony TGA). All three must go, to match the engine (lifted
  2026-10-08). The Swift app never used the engine's notes.

- **Matrix + independent review decisions (David, 2026-10-08, "go with all your
  recommendations"):** found by the full conversion matrix (254 cases through
  MacHuna 2.0's bridge) and an independent review of v1.11.0..v1.12.0.
  - **A. Progressive at a different rate is rate-converted** (frames dropped or
    repeated so duration and audio stay right) on SWS, SWS to SWS and SWS to EIF,
    as EIF output already did. Interlaced to interlaced at a different rate
    (i50 to i59.94) is refused, as progressive to interlaced already was.
  - **B. Interlaced TGA sequence to a 25/30p SWS** gives one deinterlaced frame per
    interlaced frame (it doubled the frames and played at half speed).
  - **C. A keyless EIF to SWS writes no key plane** ("no key in, no key out"): an
    EIF whose key is fully opaque throughout counts as keyless.
  - **D. EIF to SWS honours the chosen standard** where it can: 25fps EIF to
    1080p25 or 1080i50 (woven frames as they are); 50fps EIF to 1080p50, or
    1080i50 by weaving pairs; other progressive rates rate-converted per A;
    other interlaced rates refused.
  - **E. Dual-mono MOVs** (two mono audio tracks): track 1 is left, track 2 right.
  - **F. A split SWS (over 4GB) is written without audio**, says so in the log,
    and its header tells the truth (no audio claimed).
  - **G. Every SWS output is scaled to 1920x1080** (second review, 2026-10-08):
    every standard MacHuna offers is 1080, as EIF output already assumed. Before,
    MOV-to-SWS kept the source size, and widths that were not a multiple of 48
    (1280-wide 720p) produced a broken SWS (wrong line size, so frame count and
    audio position wrong). Full-HD sources must stay byte-identical.
  - **Fable black-box pass decisions (David, 2026-10-08):**
    - **C REVERTED: always retain an alpha if there is one.** An EIF always stores
      a key, so an opaque-throughout EIF key may be an intended full-frame key;
      dropping it turned a CK clip into a C clip. David: "some clips might need a
      solid key throughout... that would seem intentional." Same for a source
      whose alpha channel is fully opaque (J withdrawn). "No key in, no key out"
      applies only where there is NO alpha channel at all (the 18 September
      Kahuna finding).
    - **H. One frame-selection rule everywhere**: output frame k shows source
      frame floor(k x source_rate / output_rate), so the first frame is always
      shown (ffmpeg's fps filter on the video routes picked differently).
      DONE: `_pick_frames()` with exact NTSC fractions (rounded 59.94 picks a
      different frame from about frame 5994); count rounds halves up so the last
      source frame stays (5 frames at 50 -> 0, 2, 4 at 25). Every SWS and EIF
      route picks in Python. Tested: no ffmpeg fps setting gives the rule -
      the default (nearest) picks wrongly at 59.94<->50 and 29.97<->25, and
      `round=up` picks rightly but can add a frame at the end. `round=up` is
      used only where ffmpeg writes a TGA sequence directly (Tk and bridge TGA
      routes, via `_i_to_p_filter`). Also: an interlaced clip at another rate is
      refused for EIF, as SWS to EIF already was (decision A).
    - **I. K-Frame and Sony TGA from a MOV are 1920x1080 32-bit RGBA**, as from
      SWS/EIF (they kept the source size, and were 24-bit without alpha).
    - **K. SWS to SWS stays 10-bit throughout**, lossless where no processing is
      needed (it went through an 8-bit TGA intermediate).
      DONE: the planes are copied from the source. Passthrough, frame picks and
      the TFF weave copy the source's own bytes (the weave copies v210 lines -
      even from frame 2k, odd from 2k+1, matching ffmpeg's interleave_top,
      checked); deinterlacing and scaling a non-1080 source run ffmpeg on the
      v210 itself (`-f v210`). The 8-bit route moved a test pattern by up to 416
      10-bit steps (RGB clipped colours it cannot hold); a still now comes back
      from yadif within 1. Needs the Kahuna session: i50 SWS to SWS outputs.
    - **L. EIF writes are atomic**: written to a temporary file and renamed into
      place on success, so a cancel or failure leaves the previous pair intact
      and never a half-written file.
    - **M. Sony TGA clip names must be exactly 4 characters** (shorter names were
      padded with spaces in the filenames).
    - Fixes, no decision: untagged HD treated as BT.709 (MacHuna made the same
      SD-colour shift as the K-Frame on untagged ProRes; the claim that MacHuna
      was right "in every case" was never measured for untagged files and was
      false); 24-bit TGA to SWS; zero-frame SWS outputs; engine refuses stills
      to EIF; key range clamped after scaling.
    - **59.94 and 60 stay one family (decision a, David 2026-10-08): "go with a
      but focus on making 59.94 correct as that's the format Americans tend to
      use."** The 0.5fps tolerance in `_p_to_i_field_map` / `_i_to_p_filter` is
      kept, so 59.94p can weave to 1080i60 as before. 59.94 itself must be exact:
      every rate written into a file or handed to ffmpeg goes through `_fps_expr`
      (60000/1001, 30000/1001). Four places did not - the deinterlace resample and
      three MOV encodes, which stamped 59.94 MOVs as 2997/50. Fixed.
    - **59.94 audio is 1602 / 801 samples a frame, and that does not drift.**
      48000 / 29.97 is 1601.6, so a whole number per frame over-counts by 0.4.
      MacHuna decodes audio at a true 48 kHz from sample 0 and only pads or trims
      the end, so sync holds for the whole clip; the rounding is about 15 ms of
      extra silence per minute, at the end. UNCONFIRMED against K-Watch: there is
      no 59.94 K-Watch reference SWS, and the Kahuna has never played one.
    - **ANSWERED - David, 2026-10-08: "yes, allow both please".** Interlaced 59.94 <-> 60 now passes through untouched (`_family_note`), logged as 0.1% fast/slow; the weave logs it too. Was: decision (a)
      makes 59.94p WEAVE into 1080i60 (one family), but an existing 1080i59.94
      SWS is REFUSED for 1080i60, and so is a 29.97i clip (interlaced to another
      interlaced rate uses a strict 0.01fps test). Both give the same 0.1% speed
      error, so the rules disagree. Left as they are until David decides.
    - Matrix now has 59.94p and 29.97i sources (MOV and SWS): 324 cases, 273
      pass every rule, 0 break one, 51 refused on purpose (2026-10-08).
  - Plus, no decision needed: the SWS-to-SWS i-to-i double weave, the EIF+SWS
    folder scan crash on unreadable `.sws` (my v1.12.0 fault), the SWS header
    total size with audio (my v1.12.0 fault), the Tk app marking a cancelled EIF
    row done, and deleting a partial `.eif` after a failure as well as a cancel.

- **Release shape for the desk fixes (2026-10-08):** each engine fix is its own
  commit; one engine release (v1.12.0) at the end with the full checklist, then
  the Swift `engine/` pin moves once. **USER_MANUAL must gain the ProRes colour
  advice:** a K-Frame's own MOV import treats all ProRes as BT.601, so loading
  ProRes straight in shifts saturated colours; converting through MacHuna does
  not (desk results 2026-10-07). **USER_MANUAL section 6 must also be rewritten**:
  it still gives the old `.eaf` format (8-channel 16-bit big-endian) and says EIF
  has no audio, which will stop being true once writing lands. **README line
  ~153 and USER_MANUAL ~321 ("TGA source interlaced")** still say interlaced TGA
  to EIF deinterlaces to 50fps progressive; it now keeps woven 25fps.

**Known limitations (recorded, not scheduled):**
- **"TGA source interlaced" is per batch, not per item.** A batch mixing an interlaced TGA sequence with a progressive one applies the tick to both, so one comes out wrong. David's view (2026-09-09): not a real use case. The v1.8.0 item list makes mixed batches easier to build than the old UI did, which is why it is worth recording. The fix, if ever needed, is a per-row option rather than a batch-wide checkbox.

**Small things left over from the distribution work (low priority):**
- Take a Video Player screenshot for the download page, using `~/Desktop/MacHuna Demo Asset/MacHuna_Wipe.mov` - a synthetic 50fps ProRes 4444 wipe with a real key and audio, generated for exactly this so no client material is involved. **Partly overtaken:** the 2.0.0 page carries one screenshot of the conversion window, and the one-page flier carries two, so the page is promotional again - a player shot would now have somewhere to go. Still nobody has asked for it.
- ~~Apple Developer certificate so downloads open without the Gatekeeper warning.~~ **DONE 2026-09-25.** Enrolled as an individual on David's existing Apple ID, exactly as decided on 2026-09-24 (never as DNS Vision Limited, to avoid two Apple IDs on one Mac). **MacHuna 2.0.0 is Developer ID signed, notarised by Apple and stapled**, verified by downloading it from the live URL, setting the Safari quarantine attribute and getting `accepted, source=Notarized Developer ID`. Team `76DH86HPU3`; `notarytool` credentials are in keychain profile `machuna`. Operational detail in `MacHuna-Swift/DESIGN_DECISIONS.md` section 41.
- Cloudflare publish token expires **2027-09-07**.

**Future / low priority (no demand yet):**
- Additional output standards (1080p/29.97, 1080p/30, SD 625/50 & 525/59.94, sF variants, 2160p) - need confirmed K-Watch reference files before re-adding to the dropdown.
- 720p/59.94 reinstatement (genuine US demand, ABC/Fox) - needs a K-Watch 720p reference, hardware, and the plane_size fix. See "Format Support Rationale".
- HLG Rec.2020 colour space (needs a real HLG SWS to reverse-engineer).
- Windows port (community contribution; note in README when repos go public).
- ~~Going public~~ - **DONE, and this note was stale.** `DNSVision/MacHuna` has
  been public since before 2026-09-24, which is ahead of the condition written
  here (once the K-Frame/Sony hardware tests pass). Found while auditing for
  loose ends. Nothing to do; the condition is simply no longer the policy.
  `DNSVision/MacHuna-Swift` is **private** for now, by David's decision
  2026-09-24, and can be opened whenever there is something worth showing.

**Settled - do not reopen:** stills are SWS-only (see "Stills are SWS-only (settled)").

**Dropped from THIS version, but being built in Swift:** true drag-and-drop, and
manual batch reorder. Both were dropped because Tkinter could not do them well,
not because they were bad ideas; both are near-free in AppKit and are specified
in `MacHuna-Swift/DESIGN_DECISIONS.md` (4.5 and 3.3). Do not reopen them *here*.

**The Swift work has started and does NOT wait for the gate - and it has now
SHIPPED.** `DNSVision/MacHuna-Swift` v2.0.0 was published on 2026-09-25 as a new
interface driving this frozen engine, so it needed nothing from the desk session.
A desk fix made in `machuna.py` now reaches users through a Swift release, not
through a Python build. See HANDOVER_NOTES "Swift
Rewrite" and `MacHuna-Swift/DESIGN_DECISIONS.md`. What *does* still wait for the
gate is the full Swift rewrite of the conversion pipeline, which is a later
phase.

---

## Completed milestones (history)

*(Done items, kept for the record. Live open work is in the canonical roadmap above.)*

1. ~~**Tidy dev environment / GitHub**~~ -- DONE
2. ~~**Ignore alpha/key option**~~ -- DONE. Checkbox in GUI. When ticked, no key plane is written at all and header fields 0x1A8 and 0x1B4 are zeroed -- matches K-Watch behaviour exactly (confirmed by live Kahuna test and hex analysis of K-Watch reference file). Note: earlier implementation wrote a solid white key plane which was incorrect -- the Kahuna was showing a black key panel rather than no key at all.
3. ~~**Batch convert with file picker**~~ -- DONE. Batch Convert section in GUI with start number field, Open Files button, alphabetical ordering, auto-incrementing numbers, and conversion log text file written to destination folder after each batch.
4. ~~**TGA sequence hint in Batch Convert**~~ -- DONE. ~~Grey label added to Batch Convert section: "For TGA sequences, use the Watch Folder service above." Batch convert (Open Files) is for MOVs and single-frame stills only.~~ Superseded by v1.5.32: Watch Folder removed; TGA sequences are now handled by the smart folder browser in Batch Convert.
5. ~~**Audio support**~~ -- DONE. extract_audio() extracts 16-bit LE PCM, upmixes to 16 channels at 48kHz, pads to exact frame alignment. Header fields 0x1C2, 0x1E8, 0x1EC, 0x1CC updated correctly. "Include audio" checkbox added to GUI (default: on). Confirmed working on live Kahuna.
6. ~~**Auto play / Loop play**~~ -- DONE. Bits 2 and 3 of the low byte at 0x188 confirmed by hex analysis of K-Watch reference files across all four flag combinations (neither, auto only, loop only, both). Auto play = bit 2 (0x04), Loop play = bit 3 (0x08), OR'd into the video standard code. Both checkboxes added to GUI (default: off), saved to settings, passed through all converters. Awaiting live Kahuna test.
7. ~~**Split large files (>4GB)**~~ -- DONE. Format fully reverse-engineered from real K-Watch split files. _write_sws_split() rewritten: correct 2GB chunk size, correct data layout (all fill then all key, not interleaved), correct header patching (0x1A8 and 0x1B4 zeroed, 0x1CC set to final chunk size), correct filename format (01_OF_03._XX), streams directly to disk with no in-memory buffering. Also fixed uint32 overflow in build_sws_header() for files >4GB (0x1CC now capped at 0xFFFFFFFF -- patched correctly by _write_sws_split() anyway). Confirmed working on live Kahuna.
8. ~~**SWS to MOV / TGA conversion (Hula)**~~ -- DONE. Hula SWS Extractor built first as standalone app (DNSVision/Hula v0.1.0), then integrated into MacHuna v1.5.0. See Hula Integration section below.
9. ~~**Manual reorder in batch convert**~~ -- Dropped. Alphabetical ordering is sufficient.
10. ~~**Standalone preview viewer**~~ -- DONE. SWS Player built as companion app (DNSVision/SWSPlayer) and integrated into MacHuna in v1.4.0. All player code folded into machuna.py -- SWSHeader, PlayerFrameCache, PlayerAudio, numpy v210 decoder, composite and meter functions. tkinter and Pillow imports moved to top level to support the player classes.
11. ~~**Integrate preview into main app**~~ -- DONE. SWS Player button added to top-right of Batch Convert row. Opens SWSPlayer as a non-modal tk.Toplevel child window. File picker opens at the configured Destination Folder. Multiple player windows can be open simultaneously. Closing the player does not affect MacHuna.

### Outstanding review items (from the 2026-07-08 adversarial code review)

A full adversarial code review (Fable 5) produced a working file `REVIEW_FIXES_v167.md` (since deleted). **Resolved in v1.6.7–v1.6.10:** Fix 6 (TGA→SWS interlaced now uses yadif, not frame duplication), Fix 1 (720p output withdrawn — removed the corrupt 1280-wide `plane_size` path entirely), Fix 5 (investigated — alpha is *not* dropped on TGA-Sequence/Sony-TGA output; confirmed empirically, no change), Fix 11 (SWS→SWS clip name / key-follows-source / audio-drop warning), Fix 9(a) **p→i same-rate speed bug** (v1.6.10 — new shared `_p_to_i_field_map()` helper weaves only at the field/double rate and blocks same-rate + cross-rate progressive sources with a clear error instead of silently producing a 2×-speed clip; applied to `convert_clip`, SWS→SWS and clip→TGA. Raw TGA-sequence p→i left unchanged — no source fps to check — with the double-rate assumption now documented in code), Fix 14 **clip→EIF wrong-speed bug** (v1.6.11 — `convert_clip_to_eif` now resamples the source to the chosen EIF rate via `vf_extra=f'fps={fps:g}'` on `convert_to_v210`, so the written frame count matches the header fps for any source rate; applied to both fill and key planes; verified end-to-end + 7 unit tests). **Dismissed as non-issues for DNS Vision's workflow:** Fix 2 (i→i same-format conversion never done), Fix 3 (splits can't hold audio), Fix 7 (cancelled-job logs OK), Fix 8 (frames are always zero-padded), Fix 12 / 13 / 15 (stale-frame clear, apostrophe-in-path escaping, lone-TGA detection).

**Still genuinely open** (re-verify against the code before acting — line refs are approximate):

1. ~~**Fix 4 (HIGH) — a still produces no output on TGA-Sequence / Sony-TGA outputs.**~~ — RESOLVED in v1.6.12 by **blocking the combination**, not by converting it. The review suggested "handle a still as single-frame TGA output, or log an error"; the first half of that is explicitly out of scope. See "Stills are SWS-only (settled)" below. The same silent-vanish gap was found in `_run_to_eif` (it handles `'tga_seq'`/`'clip'`/`'sws'` only) and is covered by the same guard.
2. ~~**Fix 9(b) (MEDIUM) — cross-rate i→p on SWS→SWS / TGA-Sequence / Sony-TGA plays at the wrong speed.**~~ — RESOLVED in v1.6.12. A new shared `_i_to_p_filter()` appends an explicit fps resample on all four i→p paths so the output frame count matches the stamped target rate; it also fixed a previously-unrecorded instance in `convert_clip` itself (a down-rate SWS output, e.g. i5994→p25, ran ~20% slow). Raw TGA sequences are left unchanged (a TGA pile carries no declared frame rate to resample from). See CHANGELOG v1.6.12. *(Fix 9(a), the p→i cousin, was resolved earlier in v1.6.10.)*
3. ~~**Fix 10 (MEDIUM) — Sony TGA field-order toggle ignored.**~~ — RESOLVED in v1.6.12. `_run_to_tga_seq` now honours the UI's `field_order_var` (BFF → parity `bff` / `interleave_bottom`) in both directions, for TGA-sequence and video-clip inputs; `_p_to_i_field_map` gained a `field_order` parameter so the hardware-confirmed SWS weave stays byte-for-byte unchanged. *Which* field order a Sony MVS actually wants is still hardware-unconfirmed — this just makes the toggle functional. See CHANGELOG v1.6.12.
4. ~~**White key — INVESTIGATE ONLY.**~~ — **INVESTIGATION CLOSED 2026-09-17. Do not change `_generate_white_key`.** The suspicion was correct as arithmetic and wrong as a conclusion.

   **What the decode shows.** `_generate_white_key` writes the repeating pattern `20 01 02 00 04 08 00 40`, which through MacHuna's own v210 decoder is **Y=64, Cb=512, Cr=512** — black with neutral chroma, not white. MacHuna's own reader (`_hula_decode_frame` → `_yuv_to_gray8`) maps a key of 64 to **alpha 0**, fully transparent. So the function's name and its data disagree. That much is real.

   **What the comparison shows.** MacHuna's first commit is 2026-05-04, so any `.SWS` older than that cannot be its work. A survey of 23 keyed files in `~/Documents/DNS Vision/` found:

   - A Kahuna project still from **2023-05-12** — three years before MacHuna existed — with a key plane of **constant 64**.
   - The same constant 64 in K-Watch-era TNT (2024-12, 2025-06, 2026-02), UEFA (2025-08) and DAZN (2025-10) wipes.
   - Files with a *genuine* key from the same tool and era varying across **64–940**.

   **Conclusion: K-Watch writes 64–940 for a real key and a flat 64 when the source has none. MacHuna reproduces that exactly.** The generated key is correct as-is, which is consistent with the behaviour having been confirmed on hardware. The hex comparison this item asked for is done; nothing in the write path needs changing.

   **Two things the survey turned up that are worth a look on the desk:**
   - `Wipes/UEFA/SUPER CUP 2025/WIPES/8.SWS` is **constant 940** while 1, 2, 3 and 6 from the same session are constant 64. A natural experiment already in the library — does 8 behave differently?
   - `Kahuna Projects/PROJECTS/PRJ00014/STILLS/1.SWS` is a desk-written file whose key uses the **full 0–1023 range**, not 64–940. Desk-written keys are not always in video range. (It also has the 3072-byte header that caused the v1.9.1 shear.)

   **What remains is a different question, and it is a desk question, not a code one** — see "Should a keyless source get a key plane at all?" in the hardware checklist.

### Stills are SWS-only (settled — do not reopen)

**Decision (David, 2026-08-05): single-frame clips are not a thing. This is out of the spec permanently and is not to be proposed again.**

A still image converts to a Kahuna `.SWS` still, and to nothing else. MacHuna does not produce single-frame K-Frame EIF, Sony TGA or TGA Sequence output. Those outputs require a clip or a TGA sequence.

**Why this kept coming back:** the docs contradicted themselves. `DEVELOPMENT_NOTES.md` had exactly one supporting line (the batch-convert scope note: "single-frame TGA stills are an edge case not worth the ambiguity"), while `README.md`, `USER_MANUAL.md` and the Fix 4 review entry all implied stills were valid input for the clip-style outputs. The Fix 4 entry went further and proposed building it. Anyone reading the docs fresh would reasonably have concluded it was wanted. That is now fixed in all four places, which is the point of this section.

**Enforced in code** by a guard in the Convert handler (search `Stills are valid for Kahuna SWS output only`), which blocks the combination with a named-file error before any conversion starts. Before v1.6.12 a still selected with a clip-style output silently vanished: no file, no error, no log entry, because neither `_run_to_tga_seq` nor `_run_to_eif` has a `'still'` branch.

**Not affected:** stills → Kahuna SWS remains a headline, hardware-confirmed feature. This decision narrows the *outputs* stills are offered to; it does not remove stills as an input.

### EIF Roadmap — hardware verification first

Fix 14 (clip→EIF speed, v1.6.11) cleared the last item that could be done without hardware. **Everything remaining is gated on either a live K-Frame desk or reference files from a K-Frame operator.** So the roadmap is no longer a list of things to code speculatively — it is one hardware-test session, plus the code follow-ups that the results unlock. Do not build the follow-ups ahead of the test; the whole point is to stop guessing.

#### Priority 1 — the EIF hardware test session (unblocks almost everything below)

The single most important outstanding work in the project. When a live K-Frame ClipStore / Image Store is available, run the "Priority hardware test steps" above and, in the same visit, capture what's needed to close the other unknowns. Get through as much of this checklist as the desk time allows:

- [x] **THE `0x60` AUDIO-FLAG TEST — the highest-value question on the list.** *(Kept out of these docs until 2026-09-17 so an unproven finding was not recorded as fact. David asked for it written down; it is a question to answer, not an established conclusion.)*
  **RESULT 2026-10-07:** the desk does not care. 0912 carries `0x07` with no `.eaf` and played correctly on a 1080i desk. Bit 2 does mean audio (confirmed by desk-made 50fps files). Since 2026-10-08 MacHuna writes it truthfully.

  **The finding, unproven.** Across all 28 real K-Frame files, `.eif` header byte `0x60` bit 2 (`0x04`) predicts the presence of a companion `.eaf` with no exceptions: `0x07` on every clip that has one, `0x03` on every clip and still that does not. Of 18,260 header bytes, exactly one was constant across the six audio clips and different in the audio-less one, against 10,818 bytes that differ between two clips that *both* have audio. That is not noise.

  **The problem.** `_build_eif_header` writes `0x07` unconditionally, so **every `.eif` MacHuna has ever produced announces an audio companion that does not exist.** Colleagues report the files load fine, so the desk is probably tolerant — but "probably" is what the visit is for.

  **CORRECTION, 2026-10-07 (desk day, checked in the code and the reference files).** "Unconditionally" above is wrong. `_build_eif_header` writes `0x07` at **25fps only** and `0x03` at 50fps (`flags = 0x07 if is_25 else 0x03`). That rule came from the ten 50P reference files (`~/Desktop/TEST WIPES/50P/EIF/`), which all read `0x03` - and **all ten have no audio**, so frame rate and audio were confounded. The 25fps set separates them: `0023` is 25fps, audio-less, and reads `0x03`. So the bit tracks audio, not fps, and **MacHuna's 50fps output already has the correct flag; only 25fps output claims a companion it lacks.** The header table under "Key Header Fields" (`0x03=50fps, 0x07=25fps`) carries the same confusion.

  **The test, revised for a 1080p50 desk.** (a) MacHuna 50fps `.eif` as-is (`0x03`) and a copy patched to `0x07` - does the desk behave differently? (b) A MacHuna 25fps `.eif` as-is (`0x07`), if a 50p desk will load 25fps material at all. The KNOCKOUT_WIPE round trip independently settles the meaning: if the desk's own 50fps conversion with audio reads `0x07`, bit 2 is audio.

  *(Original plan, written when the code was believed to write `0x07` always:)* Import one MacHuna `.eif` as-is (`0x07`, no companion) and one with that byte patched to `0x03`. Does the desk behave differently: refuse it, hang, mute, log anything?

  | Outcome | What to do |
  |---|---|
  | No difference | Leave it alone. It is a cosmetic lie and not worth the risk of changing |
  | Desk objects to `0x07` without a companion | Set the bit from whether audio is actually being written. **Only then** |

  **Do not "fix" this byte beforehand** (David, 2026-09-09, restated 2026-09-17): people are happy with what they have and it is not worth risking on a hypothesis.

- [x] **THE KNOCKOUT_WIPE ROUND TRIP — do this first.** David's plan, and the highest-value test on the list: load one known MOV into the K-Frame, let the desk convert it natively, then analyse what the desk produced against the source. It answers several questions at once and needs no MacHuna output to be correct first. Full baseline below.
  **RESULT 2026-10-07:** done (slot 0900). Settled the `.eaf` layout and channel mapping and the colour finding; see "KNOCKOUT_WIPE round-trip RESULTS".

- [x] ~~**Should a keyless source get a key plane at all?**~~ **ANSWERED 2026-09-18 on a live Kahuna: no.** The flat plane loads as a black key and keys out to nothing; the file without one loads Fill-only and is labelled `C` not `CK` in the desk's file list. Changed in v1.11.0 — every keyless file halves. Original question below for the record.

- [x] ~~Should a keyless source get a key plane at all?~~ *(superseded — see above)* (David's question, 2026-09-17.) Today, converting a source with no alpha while **Ignore alpha is unticked** writes a *full, flat* key plane (constant Y=64) and declares it in the header (`has_key=True`, `0x1A8` = frame count). Only ticking **Ignore alpha** produces a file with no key plane. David's stated requirement is the simpler contract: **no key in, no key out**, whatever the tickbox says.

  **The test, about two minutes:** convert one keyless source twice — once as now (flat key plane) and once with Ignore alpha ticked (no key plane) — load both, and see whether the desk behaves any differently.

  | Outcome | What to do |
  |---|---|
  | Desk behaves identically | Adopt "no key plane when the source has no alpha". **This halves every keyless file**, because a key plane is exactly the size of the fill plane — it also halves conversion time and doubles the clip length that fits under the 4GB split threshold |
  | Desk behaves differently | Keep today's behaviour and record exactly how they differ |

  **Why it has not simply been changed:** K-Watch writes the flat key in this case (evidence in "Outstanding review items" 4), so changing it would be MacHuna's first deliberate divergence from the reference. Same shape as the `0x60` EIF flag: cheap to settle at a desk, not worth guessing at.

- [x] **EIF write, 50fps (core go/no-go)** — Convert a known short 50fps TGA sequence to `0001.eif`, import, verify: file appears, frame count correct, plays at correct speed, colours correct, key correct.
  **RESULT 2026-10-07:** 0901 (from KNOCKOUT_WIPE.mov) looked identical to the desk's own import at 1080p50: loads, frame count, speed, colour and key correct.
- [x] **EIF write, 25fps** — Same with a 25fps source. Confirms the 25fps write path.
  **RESULT 2026-10-07:** 0912 (TNTS 50i, woven 25fps) played correctly at 1080i 25Hz once the `0x064` rate code was fixed; 0911 with the old code played too fast.
- [x] **Capture a real 25fps `.eif`** produced by the K-Frame itself → hex-compare offset 0x8DC to verify or correct the assumed `b'RIFFRIFF'` movi chunk tag (the 50fps value is already confirmed).
  **RESULT 2026-10-07:** the desk wrote `0x8DC` as `RIFF` + zeros, and MacHuna's `RIFFRIFF` is accepted (0912 played correctly). No change needed.
- [x] **Capture a real interlaced `.eif`**, or otherwise establish how the desk stores originally-interlaced content (50p progressive, 25p field-pairs, or other). Settles the "1080i in EIF" unknown and tells us which write path's interlaced handling is correct.
  **RESULT 2026-10-07:** the desk stores 50i as woven 25fps frames (0908, and 0912 accepted). MacHuna's MOV route already did; the TGA route was changed to match on 2026-10-08.
- [x] ~~**Capture a real `.eaf`**~~ - **DONE, and it never needed the desk.** Six real `.eaf` files were already on David's Mac in `~/Desktop/TEST WIPES/50i/EIF/` (`0003`-`0007`, `0022`). Found 2026-09-09 by searching the machine rather than re-reading the note that said they were unobtainable.
- [x] **Confirm the `.eaf` channel mapping** - the one part still needing a desk. Programme audio sits on channels **1 and 3 (zero-indexed)** in all six reference files; channels 0 and 2 carry loud non-audio spikes and 4-7 are silent. Reading is solved and confirmed by ear (2026-09-17). What is still unknown is which channels a K-Frame *expects* when reading, which is needed before MacHuna can *write* an `.eaf`. **The KNOCKOUT_WIPE round trip below should answer this outright.**
  **RESULT 2026-10-07:** the reading was wrong: the body is 4 x 32-bit LE words (24-bit sample + channel tag), programme L/R on channels 1 and 2. Proven bit-exact; reader fixed and writer built 2026-10-08.
- [x] **Tail length** — obtain one reference file with frame_count < 36 and one with ≥ 36 → confirm whether the desk cares about the 128 vs 140-byte tail.
  **RESULT 2026-10-07:** the desk accepted MacHuna's 128-byte tail on clips of 30 and 85 frames, with and without an `.eaf`. No change needed.
- [x] **Clip name / slot rules** — try importing with a clip name (0x004) that does not match the filename stem, and with non-contiguous / non-`0001` start slots → learn whether the desk enforces either.
  **RESULT 2026-10-07:** 0901 carried the clip name KNOCKOUT_WIPE in file `0901.eif` and loaded; the desk shows the header clip name and takes the slot from the file name. Slots 0900-0922, non-contiguous, all worked.
- [x] **While a desk is available, verify the other unconfirmed extraction outputs too:** EIF→SWS (lossless), EIF→K-Frame TGA, EIF→Sony TGA, K-Frame TGA output, and Sony MVS 25i field order. **QuickTime MOV is deliberately not on this list** - it is an ordinary ProRes file, verified by opening it, with no desk behaviour to confirm. See the two hardware-unknowns tables above.
  **RESULT 2026-10-07:** K-Frame TGA from MOV, EIF and SWS confirmed. EIF to SWS and EIF to Sony TGA were not loaded on their desks (no Kahuna or Sony present); all user-facing warnings were lifted on 2026-10-08, Sony on David's judgement.

#### Priority 2 — code follow-ups - ALL DONE 2026-10-08

- ~~**EIF audio (.eaf)**~~ - reading corrected and writing built; see `CHANGELOG.md` "Unreleased".
- ~~**Interlaced EIF reconciliation**~~ - the desk stores woven 25fps; the TGA route now matches the MOV route.
- ~~**25fps movi tag**~~ - accepted as written; no change.
- ~~**Tail length**~~ - 128 bytes accepted; no change.

#### Priority 3 — pure code, no hardware needed (lowest priority — no demand yet)

- ~~**EIF→MOV**~~ — DONE in v1.10.0 as part of QuickTime MOV output, with `.eaf` audio.

### KNOCKOUT_WIPE round-trip baseline (measured 2026-09-17, before the desk visit)

**The plan.** Load one real broadcaster MOV into the K-Frame, let the desk convert it to its own `.eif` + `.eaf`, and bring those files back for analysis against the source. Because we know exactly what went in, whatever comes out is self-decoding. **This is a better test than checking MacHuna's output, because it needs nothing of ours to be right first.**

**Source:** `~/Desktop/TEST WIPES/50P/MOVS/With Sound/KNOCKOUT_WIPE.mov` (80,201,668 bytes, created 2026-03-31). Do not re-encode or rename it; the whole value is in knowing precisely what went in.

| Property | Measured value |
|---|---|
| Video | ProRes 4444, `yuva444p12le`, 1920x1080 |
| Frame rate / count | 50fps, **85 frames**, 1.700s |
| Key | Real and moving: transparent at frame 0, wipes in over 10-30, fully opaque 50-60, wipes out at 70, transparent at 84 |
| Audio | PCM `s16le`, 48kHz, **stereo (2ch)**, 81,600 samples, 1.700s |
| Samples per video frame | **960** (48000 / 50) |
| Left channel | peak 9650, rms 1802.7, 1442 zero-crossings, md5 `975a2d1cdc5f0461` |
| Right channel | peak 10381, rms 1809.7, 1703 zero-crossings, md5 `05c89ba59573bbe9` |
| L vs R | **Genuinely different** — correlation 0.40, different checksums |

**Why L and R differing matters.** It means the desk's output tells us not just *which* channels carry audio but *which is which*. Had the source been mono-as-stereo we could never have separated left from right.

**Falsifiable predictions for the desk's `.eaf`.** Each one either confirms the format or tells us something specific:

| Offset | Prediction | What it settles if wrong |
|---|---|---|
| file size | **1,305,728** bytes (81,600 x 8ch x 2 bytes + 128) | The channel count or header size is not fixed |
| `0x64` | **81600** (sample count) | The field is not a sample count |
| `0x6A` | **85** (frame count) | The field is not a frame count |
| `0x62` | **960** | We read this as samples-per-frame from 25fps files where it is 1920. If a 50fps file also says 1920, it means something else entirely |
| `0x00` | **285365** | Not the constant we assumed |
| channels | L on **1**, R on **3** (zero-indexed) | **The channel mapping question, answered outright** |
| channels 0, 2 | Whatever they are, they are not this audio | Identifies what those spikes actually carry |

**Predictions for the desk's `.eif`:** frame count at `0x06C` = **85**; frame duration at `0x0FC` = **20000** us (50fps); audio flag at `0x60` = **`0x07`**, since this clip genuinely has a companion. A key that varies frame to frame, matching the alpha profile above.

**What this does NOT settle:** whether a desk *accepts* a MacHuna-written `.eif`/`.eaf`. That still needs our output loaded. But it gives us a correct reference to build against first, which is the right order.

**On the day, capture:** both output files, the slot number used, and anything the desk says about the import. Note whether the desk re-levelled the audio — if the `.eaf` samples match the source md5s exactly it did not, and we can write bit-exact audio.

### KNOCKOUT_WIPE round-trip RESULTS (K-Frame, 2026-10-07, desk at 1080p50)

David renamed the source `0900.mov` (byte-identical to KNOCKOUT_WIPE.mov, checked with cmp), the desk imported it to slot 0900 and exported `0900.eif` + `0900.eaf`. Copies and checksums: `MacHuna-Swift/testmedia/desk/2026-10-07-kframe/`. Analysis script `analyse_roundtrip.py` alongside them. The desk's clock reads 2025-05-17.

**Predictions that held:** `.eif` `0x60` = `0x07` (clip has audio), `0x64` = `0x000104A4`, frame count 85, frame duration 20000us, video_start 18260, video_end exactly as MacHuna computes. `.eaf` size 1,305,728, `0x00` = 285365, `0x62` = **960** (so it IS samples per frame), `0x64` = 81600, `0x6A` = 85. **Bit 2 of `0x60` is the audio flag - now confirmed by a desk-made 50fps file**, not just inferred.

**THE BIG ONE - the `.eaf` body was misread.** It is **not** 8 channels of 16-bit big-endian. It is **4 channels of 32-bit little-endian words: bits[23:0] = signed 24-bit sample, bits[31:24] = a tag byte** whose top nibble is the channel number (`0x00`, `0x10`, `0x20`, `0x30`). Older reference files carry extra status bits in the low nibble and `0x40` (AES3-style V/U/C/P bits, probably from embedded SDI audio). Proven bit-exact: desk channel 1 == source L << 8, channel 2 == source R << 8, for all 81,600 samples. **The desk does not re-level audio.** Channels 3-4 are silent. The "loud non-audio spikes on channels 0 and 2" were the low bytes of real 24-bit samples. Confirmed on all six older `.eaf` references too.

**Consequence for the shipping engine (v1.11.0, so MacHuna 2.0 too):** `read_eaf_stereo` takes old "channels" 1 and 3 = the top 8 bits of each sample plus the tag byte. **EIF to MOV audio is effectively 8-bit**, with a +16 DC offset on the right channel from the tag. Residual against the source is rms 75 (8-bit quantisation noise, -28dB below this clip's level). Loud content sounds fine, which is why it passed the listening test; quiet passages and fades would not. Fix in the engine after the desk session. **Writing an `.eaf` is now fully specified.**

**Picture: the desk's import is NOT a lossless reference.** Every Y, C and key value it wrote is a multiple of 4 (8-bit precision), and luma is a few levels to ~20 low, non-uniformly. MacHuna's 0901 matches the source's own YCbCr to within 0.5 of a 10-bit level. So pixel differences between 0900 and 0901 say nothing against MacHuna. Key profile matches the source frame by frame (within 4 levels, the 8-bit step). The source is tagged `color_space=gbr`, which may be how the desk got there. Not chased further.

**Header differences from MacHuna's 0901 (15,925 bytes, 18 runs), none yet known to matter:**
- `0x058` 8 bytes = **Windows FILETIME** creation time (desk wrote 2025-05-17 06:18:32). Same value at `0x58` in the `.eaf`. MacHuna writes zero.
- `0x8E4`-`0x3313` = **the 80x45 thumbnail** (10,800 bytes) that `0x0A8` declares. MacHuna writes zeros, so a MacHuna clip may show a blank thumbnail on the desk. Watch for that when 0901 loads.
- `0x8DC` is **zero** in 0900, but `00020104 00020104` in all ten 50P references. So it is not a fixed "movi tag" the desk requires, and the 25fps `RIFFRIFF` assumption is weaker than thought.
- `0x3318`-`0x4753`: an `00db` chunk, the string `10.42.129.1` (an IP address, presumably the desk's), and `0xEE` fill. Not in the references; probably import metadata.
- **Tail:** 1,305,708 bytes of `0x040101xx` words after video_end, about the size of the `.eaf` body. The audio-bearing 25fps references show the same pattern (tail = audio bytes + 108 to 140). MacHuna writes 128 bytes, which matches audio-less clips.

### EIF write CONFIRMED on a live K-Frame, 50fps (2026-10-07)

MacHuna's `0901.eif` (untouched engine v1.11.0 output of KNOCKOUT_WIPE, flag `0x03`, no `.eaf`, blank thumbnail, no timestamp, 128-byte tail) loaded on the K-Frame at 1080p50 and, in David's words, **"looks identical to 900"**, the desk's own import of the same MOV. So none of the header items MacHuna leaves blank (FILETIME, thumbnail, `0x8DC`, the `0x3318` metadata block, the long tail) is required by the desk. **The 50fps EIF write path is hardware-confirmed**; the warning can come off for 50fps (engine change, after the session).

**Colour: the desk's own import of KNOCKOUT_WIPE is wrong, MacHuna's is right.** David saw it on a half wipe between 0900 and 0901: a visible step in the red. Measured in the red area: source RGB(709) 225,29,50; MacHuna 225,29,49; desk 202,7,47. A least-squares fit of desk YCbCr against source YCbCr gives the **BT.601 to BT.709 matrix** (Cb row 1.0179 vs textbook 1.0186): the desk treated the ProRes as SD colour and converted it. The source is labelled `color_space=gbr` (matrix = RGB, which ProRes YCbCr is not), the likely trigger.

**Control, same day: EPL-ARS-50HD.mov** (another broadcaster; QuickTime Animation, RGB+alpha, no colour label, 60 frames) imported by the desk to slot 0904. The desk used **BT.709** for the RGB to YCbCr conversion and agrees with MacHuna: Arsenal red Y 316 desk / 316 MacHuna (601 would be 380), deep red 300/300 (601: 357), gold 504/504. Chroma within one 8-bit step. Key identical within 4. Desk wrote `0x60` = `0x03` for this audio-less 50fps clip, same as MacHuna. So the desk is right for RGB sources; the KNOCKOUT_WIPE fault is specific to ProRes, probably to its `gbr` label. **Separated, same day: MacHuna_Wipe.mov** (ProRes 4444, **no colour label**, 85 frames, stereo) imported to slot 0905. The desk applied the **601 to 709 conversion again**: strong blue source Cb/Cr 801/317, desk 784/336, predicted-if-SD 785/335. Whole-frame fit, chroma rows Cb = 1.0089Cb + 0.1065Cr, Cr = 0.0721Cb + 1.0218Cr against textbook 1.0186/0.1146 and 0.0750/1.0253. **So the desk's MOV import treats ProRes YCbCr as SD colour whether it is labelled `gbr` or unlabelled**; RGB sources (QuickTime Animation) are converted correctly. **Label test, same day: 0906** = MacHuna_Wipe remuxed with no re-encode (decoded picture and audio md5 identical to the source), labelled BT.709 in both the `colr` atom and every ProRes frame header (`prores_metadata` bsf). The desk's picture data is **byte-identical to 0905's**: zero differing bytes in the picture, only header bytes (name, timestamp, thumbnail) differ. **The desk ignores the colour label entirely and always treats ProRes as BT.601.** No export setting on the broadcaster's side fixes it; only converting outside the desk does. MacHuna produces correct colour in every case, so **converting ProRes through MacHuna gives more accurate colour than loading it straight into a K-Frame.** Audio again bit-exact (24-bit in 32-bit words, tags 0x00-0x30, L on 1, R on 2), `0x60` = `0x07`. Files: `0905_desk_MacHuna_Wipe.eif/.eaf`. Files: `0904_desk_EPL-ARS.eif`, `EPL-ARS_machuna.eif`.

**25fps rate-code BUG found by inspection, same day.** `_build_eif_header` writes `0x064` as `0x000104A4 | (unk064 & 0xFF)`. Since `0xA4 | 0x84 == 0xA4`, **every 25fps EIF MacHuna writes carries the 50fps rate code** (`0x104A4`), while all 18 desk-made 25fps files read `0x10484`. Frame duration (`0x0FC` = 40000) is correct. Fix would be `0x00010400 | unk064`. Test files `0911.eif` (0903 untouched) and `0912.eif` (0903 with only `0x64` corrected to `0x10484`).

**50i: the desk's own MOV import is broken (2026-10-07, desk confirmed at 1080i 25Hz by David).** TNTS 50i.mov (ProRes 4444, interlaced TFF, 30 frames, labelled BT.709) imported to slot 0907. On the desk it **plays at double speed with a green line across the top**. The exported `0907.eif`: the embedded AVI block at `0x0DC` (normally `RIFF....AVI LIST hdrl avih`) is **missing, replaced by what look like memory pointers**, so `0x0FC` frame duration reads **0**. Rest of the header is sane: 30 frames, `0x64` = `0x10484`, `0x60` = `0x03`, tail 124 bytes. **Picture data is fine**: desk frame n = source frame n with both fields woven, i.e. the same storage MacHuna uses for interlaced material. The green line is not in the file (top rows are normal picture), so it comes from playing the damaged clip. Not usable as a reference; the older 25fps desk files (`TEST WIPES/50i/EIF/0003`-`0023`) are. Saved as `0907_desk_TNTS50i.eif`.

**0911 vs 0912 on the 1080i 25Hz desk, same day.** Both show the same green bar at the top as 0907. **0911 (wrong rate code `0x104A4`) plays even faster than 0907; 0912 (corrected `0x10484`) plays at the same speed as 0907**, which is itself about double speed. Since the files differ only at `0x64`, **the desk does read the rate code**: the bug is real and visible, and the fix changes behaviour. But the fixed file still misbehaves exactly like the desk's own import, so something common remains: the TNTS source, or how this desk plays 25fps clips. Next: load a known-good 50i EIF from a real job as a control.

**Control: `0003.eif` (DOWNHILL, desk-made at a real 50i job, 27 frames, with `.eaf`) ALSO plays at double speed with the green bar.** So the desk is mis-playing every 25fps clip regardless of who made it: **a desk state problem, not a file problem.** Best guess (unverified): the clip/image store has not taken on the 1080i 25Hz frame mode (one stored frame per field = double speed; output timing still for the old format = unfilled lines at the top showing as green, YCbCr zero). Candidates: ClipStore Config, or a frame restart after the mode change. Header check before the load: 0003 and 0912 have a **byte-identical AVI block (`0x0DC`-`0x8DB`)**; the only differences are `0x60` (both `0x07`, but 0912 has no `.eaf`), `0x8DC` (`RIFF\0\0\0\0` vs MacHuna's `RIFFRIFF`) and tail length. Follow-up variants built, not loaded: `0913` (0912 with `0x60` = `0x03`) and `0914` (0913 with `0x8E0`-`0x8E3` zeroed). **Net 50i result:** the rate-code bug is confirmed visible; with it fixed, MacHuna's 25fps EIF behaves identically to a genuine desk-made one on this desk. Clean 50i playback is still unconfirmed.

**FIXED THE DESK, THEN RE-TESTED (same day).** David switched the frame mode back and forth a couple of times; after that **0003 plays at the correct speed with no green bar**. So the earlier failures were the desk's state after one mode change, and do not count against any file. Re-run:
- **0911** (as shipped, `0x64` = `0x104A4`): **plays too fast.**
- **0912** (only `0x64` corrected to `0x10484`): **plays correctly.**

**Conclusions:**
1. **The 25fps rate-code bug is real and is the one fix 50i needs.** Every 25fps EIF MacHuna v1.11.0 (and so MacHuna 2.0) writes plays too fast on a 1080i 25Hz K-Frame. Fix: `0x064` = `0x00010400 | unk064`, i.e. `0x10484` at 25fps.
2. **25fps/interlaced EIF write is confirmed with that fix:** woven interlaced frames at 25fps (the `convert_clip_to_eif` pass-through), `RIFFRIFF` at `0x8DC` and a 128-byte tail are all accepted.
3. **The desk's own 50i import works once the desk is settled.** TNTS 50i.mov re-imported after the mode fix plays correctly on the desk (David: "worked fine"). So 0907's corrupt AVI block was caused by the desk's unsettled state, **not** a genuine inability to import interlaced ProRes. Do not cite 0907 as a reason to prefer MacHuna.
4. **The `0x60` audio flag question is ANSWERED: the desk does not care.** 0912 carries `0x07` (claims an `.eaf`) with no `.eaf` present and plays correctly. Still worth writing the flag truthfully when the rate code is fixed, as it is free, but it is not a fault.

**K-Frame TGA output, prepared for the desk (same day).** Ran `_hula_convert_mov_to_tga` on TNTS 50i.mov both ways:
- **BUG (offline, no desk needed): standard 1080i50 on an already-interlaced 25fps MOV** weaves pairs of source frames, giving **15 frames instead of 30**, each mixing fields from two different interlaced frames. The function weaves unconditionally and has no source-rate check, unlike the paths covered by `_p_to_i_field_map` (v1.6.10). A user with a 1080i desk will naturally pick 1080i50. Fix: decide from the source's own rate/scan, as the other paths do.
- Standard 1080p50 gives the correct 30 frames (the original woven frames, untouched), named `0001.tga`-`0030.tga` in a folder named after the source stem (`TNTS 50i`, with a space).
- **MacHuna's progressive path writes RLE-compressed TGA** (image type 10, ffmpeg's targa default), 32-bit BGRA, top-left origin. **Every broadcaster TGA in `TEST WIPES/50P/TGA*` is uncompressed (type 2).** Whether a K-Frame imports RLE TGA is the open question. Test pair in `tga/`: `as_1080p50/TNTS 50i` (MacHuna's real output, 19MB) and `uncompressed/TNTS 50i U` (same frames, `-rle 0`, 237MB; decoded pixel md5 identical).

**K-Frame TGA output CONFIRMED on a live K-Frame (1080i 25Hz), same day.** MacHuna's own output, the RLE-compressed `TNTS 50i` folder (`0001.tga`-`0030.tga`, made by `_hula_convert_mov_to_tga` with standard 1080p50), imported through **Image Store > Library > From Disk/Folders with "Sequence" selected** and "looks good on the desk". Without selecting Sequence the desk lists each TGA as a separate one-frame still (the file name is read as the image ID, "a number between 0001 and 8999" per the manual), which is how it first looked like failure. **RLE compression is accepted**, so the uncompressed copy was not needed. Duration shows `00:01:04`; 0912.eif (also exactly 30 frames) shows the same, so that is the desk's display convention (last-frame timecode from zero), not a dropped frame. Imported TGA sequences go to the Image Store as a movie, which per the manual carries no audio.

**Scope of the confirmation:** the MOV-to-K-Frame-TGA path at a progressive standard, frame naming `0001.tga` up, RLE 32-bit BGRA. Not separately tested: SWS-to-K-Frame-TGA and EIF-to-K-Frame-TGA (different functions, same naming), and the 1080i50 standard on this path, which has the pair-weaving bug noted above.

**Audio at 25fps, 24-bit, short and 4-channel (same day, desk at 1080i 25Hz).** Test MOVs built on the TNTS 50i picture (stream copy, picture md5 identical) with generated 24-bit tones whose low byte is random, so 24-bit survival is provable. Script and samples: `testmedia/desk/2026-10-07-kframe/audio/make_audio_tests.py`.
- **0920.mov** (2ch 24-bit, audio 55,000 samples, picture needs 57,600): desk `.eaf` header `0x60` = `0x0484`, `0x62` = **1920**, `0x64` = **57600**, `0x6A` = 30. **Short audio is zero-padded to frames x 1920**, and the sample count declares the padded length. L on ch1, R on ch2, ch3-4 silent.
- **0921.mov** (4ch 24-bit, full length): **channels map 1:1**, source 1-4 to `.eaf` 1-4, same tags `0x00`-`0x30`.
- **The desk's MOV import TRUNCATES 24-bit audio to 16-bit**: every desk sample equals the source with its low byte zeroed (floor, not rounded), exact at lag 0 on all six channels. The `.eaf` container itself holds 24 bits (the older SDI-recorded references have non-zero low bytes), so this is the importer, not the format.
- Both `.eif`: `0x60` = `0x07`, `0x64` = `0x10484`, frame duration 40000, proper `RIFF` at `0x0DC`, tail about the size of the `.eaf` body.
- **So a MacHuna `.eaf` writer should:** write 4 channels of 32-bit LE words (24-bit sample in bits 23:0, `channel << 4` in bits 31:24); keep the full 24 bits (better than the desk's own import); zero-pad to frame_count x samples-per-frame (1920 at 25fps, 960 at 50fps) and declare that padded count at `0x64`; header `0x00` = 285365, `0x60` = `0x0484`/`0x04A4`, `0x62` = samples per frame, `0x6A` = frame count; set `.eif` `0x60` = `0x07`.
- **WRITER PROVEN END TO END: 0922.** MacHuna's 0912 picture plus an `.eaf` **written by us** in exactly that layout (2ch 24-bit tones with random low bytes, ch3-4 silent, 128-byte `.eif` tail, no FILETIME). Loaded on the desk: **the clip shows the audio icon.** Exported straight back: **the `.eaf` is byte-for-byte identical to what we wrote** (0 differing bytes, header included), so **full 24-bit audio is kept** when the `.eaf` is supplied directly, unlike a MOV import. The exported `.eif` has an identical picture region; the desk only rewrites the header (name, timestamp, thumbnail) and extends the tail to audio size. Not heard (no monitoring), but the desk read, stored and re-exported it without change. Files: `audio/0922.*` (ours), `audio/desk_0922.*` (desk's export).

**Thumbnails and clip names (same day).** Thumbnails are fine: the desk shows the first frame (blank for a wipe that starts transparent), and a new one can be grabbed in the desk GUI. So MacHuna leaving the header thumbnail blank costs nothing. **The desk names a clip from the header clip name at `0x004`, not from the file name:** 0922 (file `0922.eif`) appeared as `TNTS 50I`. The slot number comes from the file name.

**K-Frame TGA via the EIF and SWS routes: CONFIRMED (David: "both came in the right way up, all good").** On the stick: folder `0912` (`_hula_convert_eif_to_tga` from 0912.eif) and folder `930` (`_hula_convert_tga` from `930.SWS`, made with `--convert ... --standard 1080i50` from TNTS). 30 frames each, `0001.tga`-`0030.tga`, verified on the Mac against the source (mean RGB diff 0.11, key identical). **Unlike the MOV route these are uncompressed (type 2) and stored BOTTOM-UP** (TGA descriptor `0x08`, origin bit clear; the MOV route writes `0x28`, top-down, via ffmpeg). **The desk honours the TGA origin flag**: bottom-up and top-down both import correctly, and uncompressed and RLE are both accepted. All three K-Frame TGA routes (MOV, EIF, SWS) are now hardware-confirmed, imported via Image Store > Library with Sequence selected. Files in `testmedia/desk/2026-10-07-kframe/tga2/`.

**Parked by David, same day:** all 25fps EIF work (0903, the 25fps write path, the 25fps `0x8DC` tag), because testing it means changing the desk's format, which may not be allowed. And 0902 (false audio flag) as moot: MacHuna already writes the correct flag at 50fps.

### Future Considerations
- HLG Rec.2020 colour space option (header field 0x188 needs a different value -- requires a real HLG SWS to hex dump and verify)
- Split file support in Video Player (requires virtual multi-file stream abstraction and frame cap)
- Sony MVS 25i field order confirmation -- BFF assumed for PAL/50Hz; needs live hardware test on a Sony MVS desk
- ~~Sony MVS 50i TGA output in Hula~~ -- DONE (v1.5.20/v1.5.21 as Sony MVS TGA 25i with BFF/TFF toggle and source guard)
- ~~True drag and drop~~ -- Dropped. Current file picker workflow is sufficient.

### Unified App (implemented in v1.5.33)

MacHuna v1.5.33 unified the full conversion engine into a single format-in / format-out UI. The user opens a folder; MacHuna autodetects the input type (SWS, video, TGA/stills) and adapts the Output dropdown and controls accordingly. The "which tool do I use?" question is gone.

**Remaining work:** The desk-bound extraction paths (SWS → K-Frame TGA, SWS → Sony TGA, MOV → TGA) are coded and working by analysis but unconfirmed on real hardware. QuickTime MOV output is not among them: it is an ordinary video file. These need live desk tests on K-Frame and Sony MVS before being marked confirmed. See "Extraction output hardware unknowns" below.

---

## Extraction Engine (integrated from v1.5.0, unified in v1.5.33)

MacHuna's extraction engine converts `.SWS` files back to standard media formats for use on K-Frame and Sony MVS desks. It was developed first as a standalone app (`DNSVision/Hula`, last version v0.1.1) then folded into MacHuna v1.5.0, and fully unified into the main Convert interface in v1.5.33. **The standalone repo is archived and no longer maintained.**

### How it works in MacHuna (v1.5.33+)

- Open a folder of `.SWS` files; MacHuna autodetects the input type and populates the Output dropdown with extraction targets (K-Frame TGA, Sony TGA, QuickTime MOV, Kahuna SWS, K-Frame EIF)
- Adaptive controls appear based on the selected output (standard dropdown, clip name, field order, include audio)
- Settings (`clip_name`, `field_order`) are persisted in `~/.kwatch_settings.json`

### Code structure in machuna.py

The extraction code lives in a clearly marked section just above `launch_gui()`:

- `HULA_TARGET_*` constants
- `_HULA_OFF_*` header offset constants (read side only -- no write side needed)
- `HulaSWSHeader` class -- parses the 512-byte SWS header for reading
- `_hula_decode_frame()` -- decodes one frame pair using the existing `_v210_plane_to_yuv`, `_yuv_to_rgb8`, `_yuv_to_gray8` functions (no duplication)
- `_hula_extract_audio_stereo()` -- extracts Ch0+Ch2 from SWS 16ch PCM as stereo temp file
- `_hula_convert_tga()` -- converts one SWS to a TGA sequence subfolder
- `_hula_convert_mov()` -- converts one SWS to a ProRes 4444 MOV
- `_hula_run_batch()` -- batch dispatcher, called from worker thread

### Output formats

| Target | Format | Naming | Notes |
|--------|--------|--------|-------|
| QuickTime MOV | ProRes 4444, embedded alpha, BT.709, audio if present | named after the source, e.g. `51.mov`, `0003.mov`, flat in dest | SWS, EIF or TGA sequence |
| K-Frame TGA | 32-bit RGBA TGA | `0001.tga` onwards, subfolder per SWS | Progressive or interlaced via standard dropdown |
| Sony TGA | 32-bit RGBA TGA | `XXXX0000.tga` onwards (4-char clip name prefix + frame number), subfolder per SWS | Progressive or interlaced via standard dropdown; BFF/TFF toggle for interlaced |

### Sony MVS interlaced TGA -- implemented in v1.5.20+

Interlaced TGA output was implemented in v1.5.20 via field-weaving (pairs of progressive frames interleaved by line). Available for all interlaced standards via the Standard dropdown. Field order toggle (BFF/TFF) present; BFF assumed for PAL/50Hz, unconfirmed on hardware.

### Extraction output hardware unknowns (updated 2026-10-08)

**All user-facing hardware warnings were lifted on 2026-10-08.** The table keeps the engineering record.

| Item | Status | Notes |
|------|--------|-------|
| **K-Frame TGA output** | **CONFIRMED 2026-10-07** | From MOV, EIF and SWS on a live K-Frame at 1080i 25Hz: imported via Image Store > Library with "Sequence" selected, all frames, right way up (bottom-up and top-down both honoured), RLE and uncompressed both accepted. Naming `0001.tga` onwards. |
| **MOV → TGA** | **CONFIRMED 2026-10-07** (K-Frame) | The TNTS 50i MOV route. Its 1080i50 double-weave bug was fixed 2026-10-08 (source-aware weaving). |
| **Sony MVS TGA clip naming** | **Warning lifted by David, 2026-10-08** | 4-char clip prefix + 4-digit frame number (e.g. `WIPE0000.tga`). Never imported onto a Sony MVS in testing; David is confident it works. |
| **Sony MVS 25i field order** | **Warning lifted by David, 2026-10-08** | TFF default (v1.6.3, engineer advice), BFF toggle in the UI. An interlaced source is no longer woven again (2026-10-08). Never loaded on a Sony desk in testing. |
| **Interlaced source → MOV: interlace metadata** | KNOWN LIMITATION | A 1080i/50 source converted to QuickTime MOV produces a 25fps ProRes file with correctly decoded interlaced frames, but ffmpeg writes no field-order flag into the container, so a downstream NLE may not identify the frames as interlaced. Fix if it ever matters: add `-field_order tb` (TFF) or `bb` (BFF) to `_prores_cmd`. Not a hardware question. |
| **Interlaced SWS → TGA (progressive target)** | POTENTIAL CONFUSION | A straight frame dump (correct); the TGAs contain interlaced frames, which show comb artefacts if treated as progressive. |

**How to hardware-test:** Convert a known clip in MacHuna to SWS, then round-trip it back through MacHuna's extraction outputs. Load the result onto the target desk and verify correct playback, frame count, and field order. The K-Frame and Sony tests are independent — access to each desk is needed separately.

---

## MOV audio into SWS is bit-identical - verified 2026-09-25

`KNOCKOUT_WIPE.mov` (1080p50, 85 frames, stereo) converted to `1.SWS` with
"include audio" on, then both read back and compared sample for sample:

| | source MOV | written SWS |
|---|---|---|
| frames | 85 @ 50fps | 85 @ 50fps |
| audio length | 1.700s | 1.700s |
| peak | -10.0 dBFS | -10.0 dBFS |
| RMS | -25.2 dBFS | -25.2 dBFS |

81,600 samples compared, **zero** length difference, largest sample
difference -180 dBFS. The audio is carried through the conversion
unaltered - no resample, no gain change, no truncation.

This also confirms the 16-channel layout the player reads back: programme
audio on channels 0 and 2, as `_player_compute_rms` has always assumed.

Found while testing: the engine has TWO SWS header classes and they are not
interchangeable. `SWSHeader` (machuna.py:1743) is the player's and carries
`total_size` and `parts`; `HulaSWSHeader` (machuna.py:3073) is for conversion
and carries neither. Anything reading audio, or reading a SPLIT clip, needs
the first.

## EIF scan type is NOT recorded, and the one sample measures progressive - 2026-09-25

`EIFHeader` decodes a frame duration at `0x0FC` and nothing else about the
picture. **There is no scan-type field.** A 25fps EIF is therefore ambiguous
from the header alone: it could be 1080p25, or it could be 1080i50 stored as
25 woven frames of 1080 lines.

This matters because `_hula_convert_eif_to_tga` writes EIF frames to TGA
**1:1 with no deinterlacing**. If the frames were woven, every output TGA
would carry comb teeth and nothing in MacHuna would say so.

**Measured, 2026-09-25.** `~/Desktop/TEST WIPES/50i/EIF/0003.eif` (DOWNHILL)
and `0005.eif` (CROSSCOUNTRY), both 27 frames @ 25fps. For every frame of
both files, neighbouring lines differ about **half** as much as lines two
apart (ratio 0.50 to 0.67). Woven fields would invert that, because
neighbouring lines would come from different moments; the ratio would exceed
1. There is ample motion to test against (15 to 67 mean luma change between
frames), so the result is not an artefact of a static picture.

**Conclusion: these files hold progressive frames at 25fps**, despite living
in a folder named `50i`, and the existing 1:1 conversion is correct for them.

**What is still unknown.** Both samples are synthetic wipes. Whether a K-Frame
ever writes woven frames - for camera material, or in another standard - is
not answered by two files, and cannot be answered from the header. Add it to
the desk session: write a clip the desk considers interlaced and measure it.

`tools_eif_comb_test.py` in this repo performs the measurement. It reads
`machuna.py` as a library and does not modify it.

## EIF Format (Grass Valley K-Frame Native)

Added in v1.5.39–v1.6.0. MacHuna can read and write Grass Valley K-Frame `.eif` clips. The format was fully reverse-engineered from real Kayenne-produced files (UCI Downhill World Cup title card, 50fps, file `0003.eif`).

### File Layout
```
[0x000 - 0x4753]  18260-byte header (GV magic + clip name + RIFF/AVI thumbnail + metadata)
[0x4754 - N]      Video data: frame_count × 3 units × 2,764,800 bytes/unit
[N - EOF]         128-byte tail sentinel (fps-dependent repeating pattern)
```

Total video data size: `frame_count × 3 × (360 × 1920 × 4)` bytes.

### Pixel Encoding (32-bit LE word per pixel)

| Bits | Field | Description |
|------|-------|-------------|
| [29:20] | key | 10-bit limited range: 64 = transparent, 940 = opaque |
| [19:10] | Y | Luma (BT.709 limited range 64–940) |
| [9:0] | C | Chroma: even columns = Cb, odd columns = Cr (4:2:2 horizontal) |

Each frame is stored as three contiguous 360-row units stacked vertically:
- Unit 0: rows 0–359
- Unit 1: rows 360–719
- Unit 2: rows 720–1079

One unit = 360 × 1920 × 4 = 2,764,800 bytes. One complete frame = 8,294,400 bytes.

### Key Header Fields (all little-endian)

| Offset | Size | Field | Notes |
|--------|------|-------|-------|
| 0x000 | 4 bytes | Magic | `EB A5 04 00` (constant) |
| 0x004 | 32 bytes | Clip name | Null-terminated ASCII |
| 0x058 | 8 bytes | Timestamp | Windows FILETIME (varies per file) |
| 0x060 | 4 bytes | Flags | `0x03` no `.eaf`, `0x07` with `.eaf` (bit 2 = audio; NOT fps - see the 0x60 correction under the EIF Roadmap). `0x01` on two 25fps stills. MacHuna writes it by fps, which is right at 50fps and wrong at 25fps |
| 0x064 | 4 bytes | Rate code | 0x000104A4=50fps, 0x00010484=25fps |
| 0x06C | 4 bytes | Frame count | Logical frames (units = frame_count × 3) |
| 0x070 | 4 bytes | video_start | Byte offset to first unit |
| 0x080 | 4 bytes | video_end | Byte offset after last unit |
| 0x0A8 | 16 bytes | Thumbnail meta | Constant: 80×45 RGB24, AVI start at 220 |
| 0x0DC | — | AVI RIFF | Size field = 0; K-Frame ignores it |
| 0x0E8 | — | hdrl LIST | Size 312 |
| 0x0F4 | — | avih | Size 56; 0x0FC = frame duration in µs |
| 0x0FC | 4 bytes | dur_us | Frame duration: 40000 = 25fps, 20000 = 50fps |
| 0x134 | — | Video strl | 80×45 RGB24 thumbnail stream |
| 0x1B0 | — | Audio strl | Size 112, dwRate=48000, empty strf |
| 0x204 | 40 bytes | Fixed block | Constant in all real files |
| 0x22C | — | JUNK | Size 1696; zeros |
| 0x8D0 | — | movi LIST | Size 10812 |
| 0x8DC | 8 bytes | movi chunk tag | 50fps: `\x00\x02\x01\x04\x00\x02\x01\x04`; 25fps: assumed `b'RIFFRIFF'` (UNCONFIRMED) |
| 0x8E4 | 10800 bytes | Thumbnail | 80×45 RGB24 (zeros = black in generated files) |
| 0x3324 | — | Zeros | Padding to video_start |

### Tail Sentinel (after video_end)
- Pattern: 4-byte fps-dependent value repeated.
- 50fps: `\x00\x02\x01\x04` × 32 = 128 bytes
- 25fps: `\x52\x49\x46\x46` × 32 = 128 bytes (assumed)
- Real files with frame_count ≥ 36 have 140-byte tails. Generated files use 128 bytes. See EIF hardware unknowns.

### Lossless EIF ↔ SWS Round-Trip

EIF and SWS both store 10-bit BT.709 limited-range YCbCr. MacHuna maps EIF bit-fields directly to v210 BE words without any RGB conversion:
- EIF word → Y[19:10], Cb[9:0] (even cols), Cr[9:0] (odd cols), key[29:20]
- v210 BE group (6 pixels): word0 = Cb0|(Y0<<10)|(Cr0<<20), word1 = Y1|(Cb2<<10)|(Y2<<20), word2 = Cr2|(Y3<<10)|(Cb4<<20), word3 = Y4|(Cr4<<10)|(Y5<<20), then byteswapped LE→BE
- Key: same layout with KC=512 neutral chroma substituted for actual chroma

This is implemented in `_eif_frame_to_v210be(u0, u1, u2)`. The round-trip is lossless — no quantisation noise, no colour shift. Verified in software (SWS output replays correctly in Video Player); UNCONFIRMED on Kahuna hardware.

### Code Structure in machuna.py

| Function | Purpose |
|----------|---------|
| `_build_eif_header(clip_name, frame_count, fps)` | Builds the 18260-byte EIF header |
| `_encode_eif_frame_from_yuv(y_plane, cb_plane, cr_plane, k_plane)` | Encodes one EIF frame (3 units) from v210 YCbCr planes |
| `_encode_eif_frame_from_rgba(img_rgba)` | Encodes one EIF frame from a PIL RGBA image |
| `_decode_eif_frame(u0, u1, u2)` | Decodes 3 EIF units to PIL Image (downscaled, Video Player) |
| `_decode_eif_frame_rgba(u0, u1, u2)` | Decodes 3 EIF units to full-res 1920×1080 PIL RGBA (conversions) |
| `_load_eif_frames(path, log)` | Loads all frames from an EIF file into memory |
| `_eif_frame_to_v210be(u0, u1, u2)` | Converts 3 EIF units directly to v210 BE fill+key (lossless) |
| `convert_clip_to_eif(...)` | MOV/video → EIF |
| `convert_tga_seq_to_eif(...)` | TGA sequence → EIF (with optional source_interlaced path) |
| `convert_sws_to_eif(...)` | SWS → EIF |
| `convert_eif_to_sws(...)` | EIF → SWS (lossless repack) |
| `_hula_convert_eif_to_tga(...)` | EIF → K-Frame TGA or Sony TGA (progressive) |
| `_hula_convert_eif_to_tga_interlaced(...)` | EIF → interlaced TGA (field-woven pairs) |

### EAF format (K-Frame clip audio) — decoded 2026-09-09

> **SUPERSEDED 2026-10-07 - the body layout below is WRONG.** Proven on a live
> K-Frame, bit-exact against sources with known audio: the body is **4 channels
> of 32-bit little-endian words**, each a signed 24-bit sample in bits 23:0 with
> a tag in bits 31:24 (channel number in the high nibble, plus status bits on
> SDI-recorded clips). Programme L/R are channels **1 and 2** (zero-indexed 0
> and 1). `0x60` is the rate code (`0x0484` at 25fps, `0x04A4` at 50fps) and
> `0x62` is samples per frame (1920 / 960). Reading the body as 8 x 16-bit
> big-endian took the top 8 bits of each sample plus the tag byte: "channels 1
> and 3" were those, "channels 0 and 2" were the low bytes of real samples, and
> the "peak 16" of silent 0022 was the tag. Reader corrected in the v1.12.0 desk
> fixes. Full detail under "KNOCKOUT_WIPE round-trip RESULTS". The 2026-09-09
> analysis is kept below as a record.

Worked out from six real files in `~/Desktop/TEST WIPES/50i/EIF/` (`0003`–`0007`, `0022`), verified with exact byte accounting on every one. **The long-standing note that no `.eaf` had ever been obtained was simply wrong** — they had been on the machine all along, and nobody looked.

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | uint32 | Always `285,365` across all six files. Purpose unknown |
| `0x58` | 8 bytes | Looks like a Windows FILETIME |
| `0x60` | uint16 | Always `1156`. Unknown |
| `0x62` | uint16 | Always `1920`. Unknown |
| `0x64` | uint32 | **Sample count** |
| `0x6A` | uint32 | **Frame count** — matches the paired `.eif` header exactly |
| `0x80` | — | Audio begins: `sample_count × 8 channels × 16-bit **big**-endian`, 48 kHz |

`samples × 8 × 2 + 128 == file size` holds for all six, and the audio duration equals the video duration exactly in each case (27, 34 and 37 frame clips). Content confirmed as real audio: peak 32749, RMS ~10895, ~98k zero crossings. `~/Desktop/eaf_0003_ch1-2.wav` was extracted as audible proof.

**Corrected 2026-09-09:** the body is **big-endian**, not little-endian. The first analysis said little-endian; David listened to the extracted audio and said it was wrong. Found by measuring sample-to-sample correlation across every plausible layout — real audio correlates at ~0.99, any wrong endianness, offset or channel count collapses to ~0, and only big-endian scores. Consistent with the rest of the format: the `.eif` video planes are big-endian v210 too. Read correctly, David confirms the audio "sounds very much like the sound effect that went with that wipe".

**Channel layout:** programme audio is on **channels 1 and 3** (zero-indexed), correlating at 0.99 and 1.00. Channels 0 and 2 carry near-full-scale spikes with no correlation — not audio, contents unknown. Channels 4-7 are silent. A 32-bit reading was ruled out: the supposed low words are not uniformly distributed, and a 32-bit reconstruction is spectrally identical to the 16-bit read.

**CONFIRMED BY EAR, 2026-09-17.** David converted `0003.eif` to QuickTime MOV in v1.10.1 and listened: correct audio, correct pitch, correct speed. That single check confirms three things at once - 48kHz is right (a wrong rate shifts pitch and speed together), big-endian is right (wrong gives noise), and channels 1/3 are the programme pair (wrong gives silence or the spike channels). The MOV's audio was also compared sample-for-sample against the `.eaf` and is bit-identical: 103,680 samples, nothing resampled or re-levelled.

**What that does NOT settle.** All six reference files are 50i/25fps and short (27-37 frames); there is no 50P `.eaf` at all, so the format is confirmed for one case, not all. And reading is not writing.

**Still unknown, and needing a desk:** which channels a K-Frame *expects* when it reads an `.eaf`, and what channels 0 and 2 are for. Reading is solved and now verified.

**Lesson:** a documented blocker is not evidence. Check before repeating one.

### EIF Hardware Unknowns and Roadmap - settled on a live K-Frame, 2026-10-07

| Item | Status | Detail |
|------|--------|--------|
| **EIF write** | **CONFIRMED** | 50fps (0901) and 25fps/50i (0912, after the `0x064` rate-code fix), with and without an `.eaf` (0922). |
| **25fps `0x8DC` tag** | **ACCEPTED** | Desk writes `RIFF` + zeros; MacHuna's `RIFFRIFF` plays correctly. |
| **Tail length** | **ACCEPTED** | 128 bytes accepted at 30 and 85 frames, with and without audio. The desk itself writes an audio-sized tail on clips with sound; not required. |
| **EIF to K-Frame TGA** | **CONFIRMED** | Folder `0912` loaded via Image Store > Library, "Sequence". |
| **EIF to Sony TGA** | Warning lifted by David | Never imported on a Sony MVS in testing. |
| **EIF to Kahuna SWS** | SWS output confirmed on Kahuna; this route not loaded | Lossless picture repack; now carries `.eaf` audio (2026-10-08). |
| **EIF audio (`.eaf`)** | **CONFIRMED, read and write** | 4 x 32-bit LE words, 24-bit sample + tag, L/R on 1/2; a MacHuna-written `.eaf` was accepted and exported back byte-identical. |
| **1080i content in EIF** | **SETTLED** | Stored as woven 25fps frames. |
| **Clip name at `0x004`** | **SETTLED** | Need not match the file name; the desk displays it. |
| **Slot numbers** | **SETTLED** | Taken from the file name; non-contiguous slots fine. |

### Standalone repo (archived)

`DNSVision/Hula` is **archived and no longer maintained**. All extraction development happens in `machuna.py` only.

---

## SWS Format Technical Reference

### File Layout (single file, no split)
```
[0x000 - 0x1FF]  512-byte header
[0x200 - N]      Fill plane  (plane_size x frame_count bytes, v210 big-endian)
[N - M]          Key plane   (plane_size x frame_count bytes, v210 big-endian)
[M - EOF]        Audio data  (if present)
```

### Key Header Fields (all big-endian)

| Offset | Size | Description |
|--------|------|-------------|
| 0x000 | 16 bytes | Magic: S&W Kahuna Still |
| 0x020 | string | Source filename |
| 0x100 | string | Clip name |
| 0x148 | string | Creation timestamp |
| 0x168 | string | Modified timestamp |
| 0x188 | uint32 | Video standard code (includes playback flags -- see below) |
| 0x18C | uint32 | Format variant field. This is an index into the Kahuna's internal standard table, not a flags field. All values confirmed by hex analysis of K-Watch reference files (2026-05-09). See Format Variant Field section below. |
| 0x190 | uint32 | Width in pixels |
| 0x194 | uint32 | Height in pixels |
| 0x198 | uint32 | Height again |
| 0x19C | uint32 | Header size = 512 |
| 0x1A0 | uint32 | Plane size (bytes per frame) |
| 0x1A4 | uint32 | Frame count |
| 0x1A8 | uint32 | Play count (= frame count) |
| 0x1B0 | float32 | Play rate (1.0) |
| 0x1B4 | uint32 | (plane_size x frame_count + header_size) / 32 |
| 0x1C2 | uint16 | Audio frame size: 0x1680 (5760) if audio, 0 if not |
| 0x1CC | uint32 | Total file size (includes audio if present) |
| 0x1E8 | uint32 | Audio data offset / 32 (0 if no audio) |
| 0x1EC | uint32 | Audio format flag: 0x03000000 (0 if no audio) |

### Video Standard Codes (offset 0x188) and Format Variant (offset 0x18C)

All values confirmed by hex analysis of K-Watch reference files (2026-05-09). Nine standards verified.

| Standard | 0x188 | 0x18C | Notes |
|---|---|---|---|
| 1080i/50 | `0xc923` | `0x08` | confirmed -- 0x8000 = interlaced flag |
| 1080i/59.94 | `0xc923` | `0x05` | confirmed -- 0x8000 = interlaced flag |
| 1080i/60 | `0xc923` | `0x04` | confirmed by pattern -- 0x8000 = interlaced flag |
| 1080p/25 | `0x4923` | `0x13` | confirmed |
| 1080p/50 | `0x4923` | `0x18` | confirmed |
| 1080p/59.94 | `0x4923` | `0x17` | confirmed |
| 1080p/60 | `0x4923` | `0x16` | confirmed |
| 720p/50 | `0x4923` | `0x10` | header confirmed; **output withdrawn v1.6.8** (never hardware-verified, plane_size wrong for 1280-wide). Header bytes retained here for future reinstatement. |
| 720p/59.94 | `0x4923` | `0x0f` | header confirmed; **output withdrawn v1.6.8** (never hardware-verified, plane_size wrong for 1280-wide). Header bytes retained here for future reinstatement. |

> **NOTE:** 0x18C values are not a flags field -- they are an index into the Kahuna's internal standard table. The simple 0x08=interlaced / 0x18=progressive theory was incorrect. Each standard has its own specific value which must be confirmed against K-Watch output.

> **UNVERIFIED STANDARDS:** 1080p/29.97, 1080p/30, and 2160p variants have been removed from the MacHuna dropdown pending verification. Do not add them back without confirmed K-Watch reference files. SD standards (625/50, 525/59.94) and sF (segmented frame) variants are supported by K-Watch but not implemented in MacHuna.

> **HOW TO VERIFY A NEW STANDARD:** Convert any file in K-Watch with the target standard selected. Run `xxd -l 512 output.SWS` and read offset 0x188 (4 bytes) and 0x18C (4 bytes). Both values are needed.

### Format Support Rationale

Decisions about which standards to implement or defer, based on broadcast research (2026-05).

**720p/59.94** — **Output withdrawn in v1.6.8** (see below). ABC and Fox broadcast networks in the US, plus all their affiliates, still transmit in 720p/59.94 in 2026 — this is *not* a legacy format and there is genuine demand. It was withdrawn only because MacHuna's SWS export for it was never hardware-verified and the v210 plane_size maths is wrong for 1280-wide output (it wrote corrupt files). Reinstate once a K-Watch 720p reference file is available (to confirm the fill-plane layout) and hardware is on hand to verify — at that point also correct the plane_size formula to the 128-byte line-alignment rule the decoder already uses.

**720p/50** — **Output withdrawn in v1.6.8** along with 720p/59.94. Low real-world demand anyway: PAL regions skipped 720p almost entirely, rarely encountered in professional production outside North America.

**1080p/29.97 and 1080p/30** — Not yet implemented, pending verification. In active use in NTSC file delivery workflows and increasingly in ATSC 3.0 deployments. Add to the dropdown once K-Watch reference files are available for hex analysis. Do not add without confirmed 0x188 and 0x18C values. To generate reference files: originate a short clip (even colour bars) in the target standard using Final Cut Pro or DaVinci Resolve, convert in K-Watch, then run `xxd -l 512 output.SWS` and read offsets 0x188 and 0x18C.

**HLG Rec.2020** — Parked pending engineering input. 1080p/50 HLG is now the preferred format for major live European sports production (UEFA Euro 2024 was produced in 1080p/50 HLG). This is the priority HDR addition. Implementation requires a real HLG SWS file from a Kahuna workflow for hex analysis — being pursued via broadcast engineering contacts.

**4K (2160p)** — Not planned until HLG is confirmed. 4K is operational in Japan (NHK BS4K), South Korea (ATSC 3.0), and premium streaming, but not mainstream in live terrestrial broadcast. No K-Watch reference files available. Defer until HLG work is complete and hardware access allows.

### K-Watch Reference File Analysis (2026-05-09)

Two K-Watch reference files were hex-analysed to investigate a potential std_code discrepancy and to understand interlaced frame storage.

**50.SWS (first) — 1080p/50 fresh K-Watch session:**
- std_code: `0x4923` ✓ matches table
- fmt_variant: `0x18` ✓ matches table

**50.SWS (second) — 1080p/50 MOV transcoded to 1080i/50 via K-Watch (P→I transcode):**
- std_code: `0xc923` -- interlaced flag confirmed (matches 201.SWS, two independent sessions)
- fmt_variant: `0x08` ✓ matches table
- frame_count: 30 (source was 60 frames at 50p → halved to 30 frames at 25fps)
- **Confirms tinterlace approach: K-Watch weaves pairs of progressive frames, halving frame count**
- **Confirms 0x8000 = interlaced flag, not drop-frame flag. All interlaced standards use `0xc923`.**

**201.SWS — 1080i/50 fresh K-Watch session (TNTS201_30_0030.tga, 30-frame TGA sequence):**
- std_code: `0xc923` (unexpected — our table says `0x4923` for 1080i/50)
- fmt_variant: `0x08` ✓ matches table
- frame_count: 30 (matches source TGA count — confirms K-Watch stores full frames, NOT separate fields)
- File size verified: 512 + 5,529,600 × 30 × 2 = 331,776,512 bytes ✓
- Anomaly: user confirmed fresh K-Watch session, cause unknown — likely a K-Watch glitch on that conversion. The std_code mismatch is not consistent with 50.SWS and is considered an isolated outlier.

**Key finding:** 201.SWS source TGAs were already interlaced frames (K-Frame output), so frame_count matching the TGA count is expected. The P→I transcoding confirmation came from the second 50.SWS analysis (see above).

### Playback Flags (offset 0x188, low byte)

| Bit | Mask | Flag |
|-----|------|------|
| 2 | 0x04 | Auto Play |
| 3 | 0x08 | Loop Play |

### ffmpeg Process Tracking and Kill

Added in v1.5.7. A global `_current_ffmpeg_proc` reference and `_ffmpeg_proc_lock` thread lock track the active ffmpeg subprocess. `_run_ffmpeg()` wraps `subprocess.Popen`, registers the process, and clears it on completion. `_kill_current_ffmpeg()` kills the process if one is running.

Both Stop and Cancel Batch call `_kill_current_ffmpeg()`. As of v1.5.12, all ffmpeg calls go through `_run_ffmpeg()` -- this includes audio extraction, TGA sequence conversion, and alpha extraction fallback paths which previously used `subprocess.run` directly. Stop/Cancel now works for all conversion paths. For rapid TGA floods, already-queued files may still convert after Stop is pressed -- this is an acceptable limitation.

Note: killing ffmpeg mid-conversion raises `subprocess.CalledProcessError` with SIGKILL (returncode -9). This is caught and logged -- correct behaviour, not a bug.


ffmpeg outputs v210 as little-endian 32-bit words. The Kahuna expects big-endian. Every 4-byte word must be byte-swapped after conversion via _byteswap_v210().

### Colour Space
Fill plane must use -colorspace bt709 -color_range tv flags. Without these, luminance is ~80mV too high (confirmed on live Kahuna test).

### White Key Plane
Written by _generate_white_key() when source has no alpha and ignore alpha is NOT ticked. When ignore alpha IS ticked, no key plane is written at all -- header fields 0x1A8 and 0x1B4 are zeroed and the file contains fill only. The repeating 8-byte pattern for the white key plane is: 20 01 02 00 04 08 00 40 -- confirmed by hex analysis of a real K-Watch file.

**Decoded (2026-09-17): that pattern is Y=64, Cb=512, Cr=512** -- black with neutral chroma, despite the name, and MacHuna's own reader maps it to alpha 0. **This is correct and must not be 'fixed':** K-Watch files predating MacHuna carry exactly the same constant-64 key plane, while their genuine keys vary across 64-940. See "Outstanding review items" 4 for the survey. Whether a keyless source should get this plane at all is a separate question, on the hardware checklist.

---

## Split File Format (>4GB)

Fully reverse-engineered from a real K-Watch split file (3-chunk example, 1080i25, 1000 frames). Implemented and confirmed working on live Kahuna in v1.3.0.

### Folder and file structure
```
1.SWS/                  (folder named as the clip number)
  01_OF_03._XX          (first chunk -- header + video data, exactly 2GB)
  02_OF_03._XX          (subsequent chunks -- raw video data only, exactly 2GB)
  03_OF_03._XX          (final chunk -- raw video data only, remainder)
```

### Chunk sizes
- Chunks 1 through N-1: exactly 2,147,483,648 bytes (2GB)
- Final chunk: remainder (whatever is left)
- Chunk 1 includes the 512-byte header; all others are raw video data with no header

### Header differences vs non-split files (chunk 1 header only)

| Offset | Non-split value | Split value |
|--------|----------------|-------------|
| 0x1A8 | frame_count (play count) | 0 |
| 0x1B4 | (plane x frames + 512) / 32 | 0 |
| 0x1CC | total file size | size of final chunk only |

- 0x1A4 frame_count: total frames across ALL chunks (unchanged)
- All other header fields: identical to non-split

### Audio in split files
Not observed in the reference file and almost certainly not supported given the file sizes involved. Not implemented.

### Implementation notes
- _write_sws_split() streams directly to disk in 1MB blocks -- no in-memory buffering
- Data layout: all fill frames contiguously, then all key frames (not interleaved per frame)
- Header patched inside _write_sws_split() before writing chunk 1 -- build_sws_header() is called normally and the three split-specific fields are overwritten
- build_sws_header() caps 0x1CC at 0xFFFFFFFF to prevent uint32 overflow for files >4GB -- the correct final chunk size is patched in by _write_sws_split() anyway
- Filename format confirmed from real K-Watch reference files: 01_OF_03._XX (single underscore before _XX)

---

## Audio Format (confirmed by hex analysis of K-Watch and MacHuna output)

- Audio appended after key plane
- **16-bit signed little-endian PCM** (not 24-bit -- matches common MOV source format)
- **16 channels interleaved** -- K-Watch channel mapping: Ch1=Left, Ch2=silence, Ch3=Right, Ch4=silence, Ch5-16=silence. Confirmed by hex analysis of K-Watch reference SWS. A straight ffmpeg -ac 16 upmix is wrong (puts R on Ch2). Use pan filter: `pan=16c|c0=c0|c2=c1`
- **48,000 Hz sample rate**
- Samples per frame = 48000 / fps (e.g. 960 at 50fps, 1920 at 25fps)
- Bytes per frame = samples_per_frame x 2 x 16
- Audio frame size header field (0x1C2) is always 0x1680 (5760) regardless of fps -- fixed value
- Audio data offset = 512 + plane_size x frame_count x 2
- ffmpeg extraction: -af 'pan=16c|c0=c0|c2=c1' -acodec pcm_s16le -ar 48000 -f s16le
- TGA sequence audio is out of scope

Note: The Audio Spec.pdf was written before full hex analysis and incorrectly states 24-bit PCM. The actual format is 16-bit. The spec PDF can be disregarded -- the implementation in extract_audio() is correct.

---

## Format Transcoding (Progressive → Interlaced)

### Status
Implemented in v1.5.18. Field order TFF — consistent with SMPTE spec for 1080i HD. Confirmed on Kahuna hardware (2026-05-15, see Hardware Tests below). Field order TFF vs BFF remains unconfirmed on a 1080i Kahuna setup — tested on 1080P Kahuna only.

### What it does
When a progressive source is converted to an interlaced standard, MacHuna uses the ffmpeg `tinterlace` filter to weave pairs of progressive frames into genuine interlaced frames rather than storing progressive data in an interlaced wrapper (which played at double speed on the Kahuna).

### How it works
- `tinterlace=mode=interleave_top` (TFF): odd lines from frame N, even lines from frame N+1
- Frame count halves: 60 frames at 50fps → 30 frames at 25fps for 1080i/50
- plane_size derived from width/height formula `((w+5)//6)*16*h` — more reliable than ffprobe frame count estimate
- Actual output_frame_count derived from fill file size after conversion — accounts for any ffprobe inaccuracy
- Key extraction (alpha channel) also applies tinterlace — both fill and key must match frame count

### Hardware test (2026-05-09, 1080P Kahuna)
- File loaded in normal time (~30 seconds, vs 8+ minutes with the mismatched key bug)
- Playback showed tell-tale interlacing on a 1080P output — expected, not an error
- Pausing mid-clip showed dithering between fields — confirms the two fields are genuinely temporally distinct (correct tinterlace behaviour, not a progressive wrapper)
- **Field order TFF unconfirmed on 1080i** — cannot assess TFF vs BFF on a 1080P Kahuna.

### Hardware test (2026-05-15, Kahuna — all three paths confirmed)
- **1080i/50 MOV → 1080p/50 SWS** — loaded and played at correct speed. Format reported correctly on desk. CONFIRMED.
- **1080p/50 → 1080i/50 SWS** — regression check passed. Loaded and played correctly. CONFIRMED.
- **TGA i→i with "TGA source interlaced" checkbox** — correct speed on hardware. CONFIRMED.

**Kahuna duration display format (confirmed 2026-05-15):** The Kahuna displays clip duration as SS:FF (seconds:frames at the clip's native frame rate), not as timecode. A 1.20s clip at 1080p/50 (60 frames) shows as "01:10" (1 second + 10 frames at 50fps). The same 1.20s clip at 1080i/50 (30 frames) shows as "01:05°" (1 second + 5 frames at 25fps — the ° symbol indicates interlaced). Both are exactly correct. Verified by playing through the mixer, recording into EVS, and frame-counting — both clips confirmed identical length. MacHuna's frame counts are correct.

### To confirm field order (still outstanding)
Load the MacHuna P→I output on a Kahuna running in 1080i/50. Play content with clear horizontal motion. Clean motion = TFF correct. Motion artefacts/reversed = switch to `interleave_bottom` (one-character change in `convert_clip`).

### Key implementation bug fixed in v1.5.18
When source has an alpha channel (`has_alpha=True`), the key extraction command in `convert_to_v210` has its own `-vf alphaextract,...` chain. The tinterlace filter must be appended to this chain too — otherwise fill=30 frames but key=60 frames, producing a 497MB file instead of 332MB and causing the Kahuna to load slowly or fail. Both the primary and fallback key extraction paths now include `vf_extra`.

---

## Known Issues

### PortAudio AUHAL errors on macOS 26 beta
When running as a script (`python3.12 machuna.py --gui`), sounddevice/PortAudio prints `||PaMacCore (AUHAL)|| Error on line 2796: err='-50', msg=Unknown Error` to the terminal during audio playback. Audio plays correctly despite these messages. They are terminal-only and invisible to users running the built `.app`. This is a known macOS 26 beta / Homebrew PortAudio instability, in the same category as the rapid button click crash. Not worth investigating until macOS 26 goes final.

### Video plane differences between machines
MacHuna-generated v210 video data differs byte-for-byte from K-Watch output and between different machines running MacHuna. This is normal -- ffmpeg produces slightly different v210 encoding on different hardware/versions. The Kahuna accepted MacHuna output correctly on live test. This is not a bug.

---

## Technical Decisions

- onedir vs onefile: Must use --onedir. The --onefile + --windowed combination causes ffmpeg binaries to not bundle correctly on macOS.
- ffmpeg path: Must point to real binary not Homebrew symlink (/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffmpeg). Symlinks confuse PyInstaller.
- sys.frozen check: _get_ffmpeg_path() checks sys.frozen to find bundled ffmpeg when running as .app.
- TGA sequences: Handled via ffmpeg concat demuxer with a temporary concat file. Selected via the smart folder browser in Batch Convert -- the browser collapses each sequence to a single entry. Not supported in the file picker (TGA is excluded from Open Files).
- Settings persistence: Stored as JSON in ~/.kwatch_settings.json. Keys include `clip_name`, `field_order`, `output_format` for extraction settings. Old `hula_clip`/`hula_field_order` keys are migrated on load for backwards compat with pre-v1.5.33 settings.
- VERSION constant: Single `VERSION = "x.x.x"` constant near the top of machuna.py. Title bar and About box both read from it. Update this one line for each release.
- Format variant (0x18C): Stored in `FORMAT_VARIANTS` dict keyed by standard name, applied in `build_sws_header`. A companion `FORMAT_VARIANT_FPS` dict maps variant values back to fps -- used by `SWSHeader` and `HulaSWSHeader` for unambiguous fps lookup (all nine variant values are unique). The old simple interlaced/progressive logic (0x08/0x18) was replaced in v1.5.10 after v1.5.8 analysis confirmed each standard has its own specific value.
- Interlaced fps in SWSPlayer: `FORMAT_VARIANT_FPS` uses frame rates for interlaced standards (25/29.97/30fps), not field rates (50/59.94/60fps). Each SWS frame is a full 1920x1080 frame -- MacHuna does not separate fields. Confirmed on hardware (v1.5.14).
- SWSPlayer playback timing: `_playback_loop` sleeps to an absolute target time derived from a fixed origin (`t_origin + frame_num * frame_dur`). This prevents sleep overshoot in one frame from accumulating as drift across subsequent frames (v1.5.15).
- About box: Custom `tk.Toplevel` dialog. `tk::mac::ShowAbout` is silently overridden by PyInstaller's default panel, so an explicit menubar with `name='apple'` is created and the About item wired to our command instead. App icon loaded from `sys._MEIPASS` (bundled via `--add-data`) using Pillow; falls back to rocket emoji if image not found.
- White key plane: Written by _generate_white_key() when source has no alpha and ignore alpha is NOT ticked (i.e. a real fill+key file is expected). When ignore alpha IS ticked, no key plane is written at all -- header fields 0x1A8 and 0x1B4 are zeroed and the file contains fill only. Confirmed by live Kahuna test and hex analysis of K-Watch reference file.
- Batch convert ordering: Files sorted alphabetically. Manual reorder is a future feature.
- Batch convert scope: MOV, MP4, MXF, MKV, AVI, PNG, BMP, JPG only. TGA is excluded from the file picker -- TGA sequences are handled via the smart folder browser (v1.5.32), and single-frame TGA stills are an edge case not worth the ambiguity.
- Audio bit depth: 16-bit LE (not 24-bit). Confirmed by hex analysis of K-Watch reference files. Source MOV audio is passed through at native bit depth via ffmpeg -ac 16 upmix.
- Audio frame size header field (0x1C2) is always 0x1680 (5760) in MacHuna-generated files regardless of fps. Actual bytes per frame varies with fps but this header field does not. Note: third-party workflows may write a different value here -- K-Watch writes 0x3EC0 (16064) for 24fps content (confirmed by hex comparison of K-Watch and third-party SWS files generated from the same source MOV). The field appears to be an arbitrary constant rather than a meaningful bytes-per-frame value in either case. Do not rely on this field for audio detection -- use 0x1E8 and 0x1EC instead.
- Auto play / Loop play flags: Bits 2 (0x04) and 3 (0x08) of the low byte at 0x188, OR'd into the video standard code. Confirmed by hex analysis of K-Watch reference files across all four flag combinations. Both flags default to off.
- SWS Player audio detection: uses `aud_offset > 0 AND aud_fmt == 0x03000000` (fields 0x1E8 and 0x1EC) rather than checking `aud_frame_size == 0x1680` (0x1C2). Confirmed by analysis of a third-party SWS file where 0x1C2 was 0x3EC0 -- audio was present and correctly located but the player was reporting no audio. The 0x1C2 field varies between workflows and is not a reliable audio detection indicator.
- SWS Player integration: All player code lives in machuna.py above launch_gui(). Classes renamed to avoid any future collision: PlayerFrameCache, PlayerAudio. Decode functions prefixed _player_. The standalone sws_player.py repo (DNSVision/SWSPlayer) is now superseded for production use but retained as a reference. sounddevice is a gracefully-degraded dependency -- if not installed, HAS_AUDIO is False and the player opens without audio playback (meters still drawn, no sound).
- Extraction engine: All extraction code lives in machuna.py in a clearly marked section just above launch_gui(). Classes and functions use the `_hula_*` prefix (internal naming only — not user-facing). The v210 decoder functions (_v210_plane_to_yuv, _yuv_to_rgb8, _yuv_to_gray8) are shared with SWSPlayer and not duplicated.
- tkinter top-level import: tk, ttk, filedialog, messagebox, scrolledtext are now imported at module level (guarded with try/except) so the SWSPlayer class can reference tk.Toplevel at definition time. launch_gui() still has its own internal imports which are harmless re-imports.

---

## Development Process Notes

### Reverting to a known good version

Git makes this straightforward. If a change badly breaks the app, we can roll back to any previous commit and the file returns to exactly that state — as if the bad change never happened. To make this reliable, commit after each version bump once it has been tested and confirmed working. Do not batch multiple version bumps into a single commit at the end of a session — if something in the middle broke, we want to be able to land on the last clean version without losing the good changes that came after it.

### The unified app architecture — implemented in v1.5.33

The unified format-in / format-out interface was implemented in v1.5.33. The remaining work is hardware confirmation of the extraction output paths — see "Extraction output hardware unknowns" in the Extraction Engine section. Unconfirmed paths are flagged in the UI with a warning dialogue before converting.

---

## File Structure

```
~/Developer/MacHuna/
├── machuna.py              # Main application source
├── machuna.icns            # App icon (Apple icon format)
├── machuna_final_1024.png  # Source icon image (1024x1024px)
├── Audio Spec.pdf          # Early audio format notes -- superseded, see notes above
├── README.md               # Public-facing repository readme
├── CHANGELOG.md            # Version history and release notes
├── HANDOVER_NOTES.md       # Session handover notes for continuity between development sessions
├── DEVELOPMENT_NOTES.md    # This file
├── CLAUDE.md               # Claude Code instructions and project conventions
└── .gitignore              # Excludes build/, dist/, *.spec etc.
```
