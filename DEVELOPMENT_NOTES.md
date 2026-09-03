# MacHuna — Development Notes

This document is for continuity between development sessions. If starting a new Claude session, point Claude at this file and the main machuna.py source and development can resume from where it left off.

---

## Project Summary

MacHuna is a macOS application that converts video and still image files to the Grass Valley Kahuna `.SWS` native format. It was built collaboratively between David Steer (DNS Vision Limited) and Claude (Anthropic) with no prior coding experience on David's part.

**Current version:** v1.6.20
**Status:** Tested on a live Grass Valley Kahuna mainframe. Core conversion confirmed working. v1.6.20: Packaging and workflow, no app-code change. `MacHuna.spec` left `bundle_identifier=None` (PyInstaller then defaults it to the bundle name "MacHuna") and stamped no version, so every copy on the machine claimed one identity and reported 0.0.0 in Finder - which is how David's Dock ended up launching a v1.6.12 build all day while `dist/` moved on. Now `com.dnsvision.machuna` with `CFBundleShortVersionString`/`CFBundleVersion` read from `VERSION` by a `_read_version()` helper in the spec. His own copy now lives at `/Applications/MacHuna.app` (Dock re-pointed there; Dock plist backed up to `~/.machuna_backups/`), refreshed as step 8 of every release, and **publishing to the share folder is now a separate opt-in step 9** - he wants to run a build before the public gets it, so the share copy may sit several versions behind by design. This also clears the long-standing 0.0.0 cosmetic note. Also rewrote USER_MANUAL section 4.4 as one coherent section: it had been written a paragraph per release across v1.6.13-v1.6.19 and read as a changelog in prose, with an apparent self-contradiction on kept-versus-cleared values. Now ordered by task with a kept/cleared table, a worked example, and no inline version tags. v1.6.19: Wording only. The Sony TGA one-clip-at-a-time error now leads with "To batch convert to Sony TGA, tick 'Use bespoke names'" and explains the shared-field limitation afterwards, rather than burying the workaround in its third paragraph (David's observation). The grey note beside the shared Clip name field points at bespoke names too. No behaviour change. v1.6.18: Fixed the stale duplicate mark David spotted - the v1.6.17 trace cleared only the edited row, so fixing one half of a duplicate pair left the other still flagged. Editing now calls `_bespoke_recheck()`, which re-analyses the whole batch and applies the result via `_bespoke_apply_marks(codes, only_marked=True)`; the `only_marked` guard is what stops typing marking fields that were never flagged (blank is the normal starting state), and rows track their own state in `hint.marked`. `_bespoke_mark()` keeps the scroll-and-focus, `_bespoke_recheck()` deliberately does not, so the cursor is never yanked mid-edit. `_bespoke_reset()` now also destroys the row widgets instead of just clearing the list that tracked them. v1.6.17: A blocked bespoke batch now marks every offending field in red with a per-row reason, scrolls to the first and focuses it; typing clears that row's own mark. `validate_bespoke_ids()` and the new `bespoke_row_issues()` are both thin wrappers over a shared `_analyse_bespoke_ids()` returning (per-row codes, grouped messages), so the dialog and the field marks cannot disagree. Also fixed the truncation David spotted: the panel is measured once at rebuild while the hints still read "1-9999", so a longer mark was clipped — the hint column now reserves `_BESPOKE_HINT_WIDTH` (17 chars, >= "duplicate number"), which also stops marking shifting the layout. **Panel height deliberately left fixed** — auto-growing just relocates the problem to the window height (David's point), and the real answer is a resizable/paged layout in the Swift rewrite. 94 unit tests (9 new). v1.6.16: Unticking the bespoke checkbox is now the "start over" gesture — new `_clear_selection()` empties `_selected_items`, `_selected_folders`, the input type and the audio/TGA flags as well as the typed IDs, resets the summary, disables Convert and logs why. With v1.6.15's "Add to List" the selection could otherwise only grow. v1.6.15: Batches can now be built up from more than one folder. The folder browser gained an "Add to List" button (shown only when something is already selected) alongside "Select", which still replaces. `open_files` was restructured so no state is touched until a button is pressed — cancelling the dialog previously left `_input_type[0]` set to the scanned folder's type. New module-level `merge_input_types()` decides whether two selections can share a batch (encode-to-SWS and extract-from-SWS are separate families; from_sws + from_eif merges to mixed_eif_sws) and is unit-tested. Bespoke values are now also cleared on *untick*, and "Select" blanks the panel while "Add to List" preserves it — building a list up keeps your typing, starting a new one does not. 85 unit tests (6 new). v1.6.14: Two bespoke-mode refinements from David's first hands-on test. Bespoke fields now blank on every *return* to the mode — cleared when the checkbox is ticked on and again when a bespoke batch finishes — instead of holding values for the whole session; preservation across a selection change while the mode stays on is kept, as that is the case where retyping is a nuisance. The panel's scrollbar now sits beside the list (canvas sized to `bespoke_inner.winfo_reqwidth()` and packed without `expand`, scrollbar packed `side='left'`) rather than at the far right edge of the window, 597px away from the rows it scrolls. v1.6.13: Bespoke per-item output IDs on batch convert — a checkbox alongside the existing numbering/naming controls swaps the single auto-sequence control for a scrollable panel with one input per selected item: an output number (1-9999) for Kahuna SWS and Kayenne EIF, a 4-character clip name for Sony TGA. Offered for those three outputs only (Kayenne TGA and TGA Sequence self-name from the source). Fields start blank on purpose so unfinished rows are obvious, and values survive a selection change. Three blocking checks run before anything is written — valid/in-range, no in-batch duplicates, no collision with the destination (`N.SWS` as file *or* split-file folder, `NNNN.eif`, or a Sony clip-name folder) — all naming the offending items, with no overwrite path offered. This also lifts the Sony TGA one-clip-per-batch cap when bespoke names are in use: distinct names mean distinct folders, so several Sony clips can convert together; the cap is retained when they are not. Unticked behaviour is byte-for-byte unchanged. New module-level `validate_bespoke_ids()` / `normalise_bespoke_value()` carry the rules so they are unit-testable outside the GUI; 79 unit tests (20 new). Verified by driving the real GUI: 25 scripted checks covering blocked and successful batches for both numbers and Sony names. v1.6.12: Three fixes clearing the last code-only items before hardware testing. Fix 9(b) — cross-rate interlaced→progressive played at the wrong speed; new shared helper `_i_to_p_filter()` appends an fps resample whenever bob-deinterlacing alone would miss the target rate, applied to all four i→p paths (verified: 4s 25fps i-source → 1080p60 gave 200 frames/3.33s before, 240/4.00s after). This also caught an unrecorded instance in `convert_clip`'s own down-rate branch (29.97i → 1080p25 ran 20% slow: 120 frames before, 100 after) — the path the review cited as the good example. Raw TGA sequences unchanged (no declared source rate exists to resample from; assumption now explicit). Fix 10 — the Sony TGA TFF/BFF toggle was displayed but ignored (weave and yadif parity both hardcoded TFF); now honoured in all four sites and named in the log, with `_p_to_i_field_map` gaining a `field_order='TFF'` default so the hardware-confirmed SWS weave is byte-identical. Fix 4 — a still selected with EIF/Sony TGA/TGA Sequence output silently produced nothing (no handler for single-image items, in `_run_to_eif` as well as `_run_to_tga_seq`); now blocked up front with a named-file error. **Stills are SWS-only, permanently — see "Stills are SWS-only (settled)".** 59 unit tests. v1.6.11: Fixed clip→EIF wrong-speed bug (Fix 14) — `convert_clip_to_eif` extracted frames at the source rate but stamped the header at the nearest EIF rate (25/50), so any non-25/50 source (29.97/30/59.94/60fps) played at the wrong speed on a Kayenne. Extraction now resamples to the chosen EIF rate (`vf_extra=f'fps={fps:g}'` on `convert_to_v210`, applied to both fill and key planes) so frame count matches header fps and duration is preserved; verified end-to-end (60fps 2s clip → 100 frames @ 50fps = 2.0s) plus 7 new unit tests. EIF output remains hardware-unconfirmed. v1.6.10: Fixed the progressive→interlaced same-rate speed bug (Fix 9(a)) — the p→i weave halves the frame count, which is only correct for a double-rate (field-rate) source (50p→1080i50 etc.); a same-rate source (25p→1080i50) was being silently halved and played at 2× speed. New shared helper `_p_to_i_field_map()` now weaves only at the field rate and blocks same-rate and cross-rate sources with a clear error (no file written) rather than producing a wrong-speed clip. Applied to the three p→i paths that know their source fps: video-clip→SWS (`convert_clip`), SWS→SWS (uses the source header's fps), and clip→TGA extraction. Raw TGA-sequence p→i is unchanged (no source fps available — still assumes a double-rate field stream; assumption now documented in code). No PsF path shipped, so nothing new is hardware-unconfirmed; the double-rate weave remains confirmed. v1.6.9: SWS→SWS metadata fixes — output header clip name now follows the source SWS name (was the placeholder "0001" from the temp intermediate frames), a keyless source no longer gains a phantom key plane (the extractor always writes RGBA, so has_key must be forced to follow the source), and dropped audio is now flagged in the log instead of silently discarded (validated in-app: 1080i50→1080p50 logged `clip name: 51  key: yes`). Also confirmed empirically that TGA-Sequence/Sony-TGA output does NOT drop alpha through yadif/tinterlace — the reviewed report was a false alarm; RGBA test frames through both filters preserved the alpha channel, so no change was made. v1.6.8: 720p/50 and 720p/59.94 withdrawn from all format tables and the dropdown — the SWS output was never hardware-verified and the v210 plane_size maths is wrong for 1280-wide (non-48-multiple) output, so it produced corrupt files. This is a "broken + unverifiable export" withdrawal, NOT "obsolete format": 720p/59.94 is still actively broadcast (ABC/Fox, 2026) and is a reinstatement candidate once a K-Watch 720p reference and hardware verification are available. v1.6.7: TGA→SWS interlaced source now uses yadif deinterlacing (send_field, TFF) instead of frame duplication — correct motion, no comb artefacts (validated in-app: 30 interlaced frames → 60 progressive, smooth playback); USER_MANUAL.md added to the release checklist so the manual no longer drifts behind the code. v1.6.6: Sony TGA added as output option for TGA sequence input — direct TGA→Sony TGA conversion with i↔p handling (tinterlace/yadif); "TGA source interlaced" checkbox shown; Sony naming convention (CN0000.tga in CN/ subfolder). v1.6.5: SWS→SWS i↔p conversion (two-step TGA intermediate; source interlace auto-detected from header; yadif for i→p, tinterlace for p→i); TGA Sequence output for TGA and clip inputs (same filter logic; subfolder per sequence); Kayenne MOV removed from SWS output (unconfirmed hardware). v1.6.4: TGA→EIF interlaced path now uses yadif deinterlacing (send_field, TFF) instead of frame duplication — correct motion and no comb artefacts. v1.6.3: Field order default changed from BFF to TFF (engineer advice — TFF correct for all known 1080i HD workflows); TFF now appears first in UI radio buttons; BFF retained as fallback. v1.6.2: EIF→EIF routing bug fixed (removed Kayenne EIF output option when input is EIF — was silently no-op); doc corrections. v1.6.1: Code cleanup — dead code removal (5 superseded functions), `_eif_parse_unit` helper extracted, redundant numpy imports removed, player status bar text fixed. v1.6.0: Full EIF feature set — EIF read (Video Player), EIF write (TGA/MOV/SWS → .eif with slot naming 0001.eif+), EIF→SWS lossless YCbCr repack, EIF→Kayenne TGA, EIF→Sony TGA, TGA source interlaced option for EIF output, mixed EIF+SWS folder detection, Player file picker (folder→file), format label in Player info strip. All EIF write/conversion paths UNCONFIRMED pending hardware test on live Kayenne desk. v1.5.43: Kayenne EIF output added — MOV/TGA/SWS → .eif conversion with full header construction (18260-byte header verified byte-for-byte against real Kayenne clips), BT.709 YCbCr encoding, 4:2:2 chroma subsampling, key channel, tail sentinel; UNCONFIRMED pending hardware test. v1.5.42: EIF frame rate auto-detected from header (0x0FC = frame duration in µs; 40000=25fps, 20000=50fps); Video Player no longer prompts for frame rate and correctly reports key present. v1.5.41: EIF key channel decoded — bits[29:20] = key level (64=transparent, 940=opaque); wipes and alpha mattes now visible in Video Player key and composite panels. v1.5.40: EIF colour decode fixed — pixel format fully reverse-engineered from real clip (UCI DOWNHILL footage); each 32-bit word = key[29:20] + Y[19:10] + C[9:0] (even=Cb, odd=Cr); three 360-row units stack vertically to form 1920×1080. v1.5.39: EIF playback in Video Player (experimental) — Kayenne native .eif format reverse-engineered; header fields confirmed (clip name 0x004, frame count 0x06C, video start 0x070, video end 0x080). v1.5.38: Video Player now uses folder-based file picker (matches Convert window — TGA sequences collapsed to one entry per sequence); fixed TGA fps picker dialog unresponsive on macOS (transient/grab_set ordering). v1.5.37: Sony TGA multi-file guard — error dialog blocks conversion if more than one clip is selected (all would write to the same folder, second overwrites first). v1.5.36: Fixed MOV → Sony TGA output folder naming (was using MOV filename stem instead of 4-char clip name). v1.5.35: Docs update — TGA sequence naming convention flexibility explicitly documented in README and USER_MANUAL. v1.5.34: Fixed TGA sequence detection for files without a separator between base name and frame number (e.g. FEDX0000.tga). v1.5.33: Unified format-in / format-out interface — MacHuna and Hula merged into a single Convert section; input autodetection drives the Output dropdown; adaptive controls show only what is relevant to the current conversion; MOV → TGA path surfaced with hardware-unconfirmed warning; Sony TGA output folder now named after clip name; "SWS Player" renamed "Video Player"; HulaWindow no longer launched from GUI. v1.5.32: Watch Folder and Slot Override removed (MacHuna is a field tool, not a server app); smart folder browser replaces file picker (TGA sequences collapsed to one entry per sequence); i→p TGA conversion fixed (frame duplication preserves duration); "Include audio" moved to folder browser dialog, shown only when audio detected; "TGA source already interlaced" label shortened. v1.5.31: Hula bugfixes — interlaced SWS → interlaced TGA routing bug fixed; Hula MOV encoder now uses _run_ffmpeg so Stop/Cancel works. v1.5.30: Fixed i→p double-speed bug (bob deinterlace via yadif) + TGA i→i double-speed bug ("TGA source already interlaced" checkbox skips tinterlace). v1.5.29: Watch Folder TGA batch: single combined log + auto-stop when batch complete. v1.5.28: Fixed SWS Player crash when opening/playing a second file with audio (heap corruption — stop() was closing PortAudio stream from main thread while audio thread was in write(); fix: stop() now only signals + joins, audio thread closes its own stream in finally). v1.5.27: SWS Player now accepts TGA sequences and MOV/MP4/MXF/AVI. v1.5.26: Batch Convert confirmation dialog (custom Toplevel, no app icon). v1.5.25: Slot override field in Settings, two-row Settings layout, Batch Convert button visibility fix, default window size 960×460. v1.5.24: Fixed TGA sequence P→I conversion (missing tinterlace filter + wrong frame count). v1.5.23: Open in Finder buttons on Watch Folder, Destination Folder, and Hula Destination Folder rows. v1.5.22: Hula GUI redesigned — full standard dropdown (all 9 formats), MOV input support, Kayenne/Sony TGA targets consolidated (Kayenne TGA UNCONFIRMED). v1.5.21: Hula Sony MVS 25i source guard (rejects non-1080p50 input). v1.5.20: Hula Sony MVS 25i TGA output (field-woven, BFF/TFF toggle). v1.5.19: Compact broadcast metadata display in SWS Player and Hula (standard/frms/duration). v1.5.18: P→I transcoding via tinterlace (TFF, unconfirmed on 1080i hardware). v1.5.17: Interlaced standard codes corrected (0xc923 for all interlaced, 0x8000 = interlaced flag). v1.5.16: TGA removed from Batch Convert file picker. v1.5.15: SWSPlayer playback jitter fixed via absolute timing. v1.5.14: SWSPlayer interlaced playback speed fixed (field rate vs frame rate). v1.5.13: SWSPlayer and Hula fps lookup fixed for all standards. v1.5.12: All ffmpeg calls now go through _run_ffmpeg - Stop/Cancel works for all conversion paths. v1.5.11: Ignore alpha for TGA sequences fixed. v1.5.10: FORMAT_VARIANTS lookup table applied - format variant (0x18C) now correct for all nine standards. v1.5.9: Unverified standards removed from dropdown. v1.5.8: All nine video standards fully confirmed by K-Watch hex analysis; progressive-to-interlaced mismatch warning added. v1.5.7: Stop button kills ffmpeg immediately; Cancel Batch button added. v1.5.5: Format variant field (0x18C) initial fix. v1.5.4: Window size persistence. v1.5.0: Hula SWS Extractor integrated. v1.4.0: SWS Preview Player integrated. v1.3.0: Large file split (>4GB) confirmed working on live Kahuna.
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

**Blocked on hardware (the gate before "feature-complete"):**
- **EIF hardware-test session** - the single most important item. Full checklist under "EIF Roadmap - hardware verification first" below. Unblocks: EIF write confirmation, 25fps movi tag, `.eaf` audio, tail length, clip-name/slot rules, interlaced-EIF storage.
- **Extraction outputs on real desks** - Kayenne TGA/MOV, Sony TGA clip naming, Sony MVS 25i field order, interlaced-SWS to MOV field metadata, MOV to TGA. See "Extraction output hardware unknowns" below.
- **P->I field order on a genuine 1080i Kahuna** - TFF assumed correct; confirm on hardware (one-word flip to `interleave_bottom` if wrong).

**Open code work (no hardware needed):**
- ~~**Bespoke per-item output IDs on batch convert**~~ - DONE in v1.6.13. Per-item numbers for Kahuna SWS and Kayenne EIF, per-item 4-character names for Sony TGA, validated for blanks, in-batch duplicates and destination collisions before anything is written. Also lifted the Sony TGA one-clip-per-batch cap when bespoke names are in use.
- **White key (INVESTIGATE ONLY)** - possible Y-value inversion in `_generate_white_key`; do not change without a hex-compare against a real K-Watch reference. Detail in "Outstanding review items" + "White Key Plane". *(This is the only open code item. Fix 9(b) and Fix 10 were resolved in v1.6.12, bespoke IDs in v1.6.13.)*

**Future / low priority (no demand yet):**
- Additional output standards (1080p/29.97, 1080p/30, SD 625/50 & 525/59.94, sF variants, 2160p) - need confirmed K-Watch reference files before re-adding to the dropdown.
- 720p/59.94 reinstatement (genuine US demand, ABC/Fox) - needs a K-Watch 720p reference, hardware, and the plane_size fix. See "Format Support Rationale".
- EIF -> Kayenne MOV (pure code, no user demand).
- HLG Rec.2020 colour space (needs a real HLG SWS to reverse-engineer).
- Split-file support in the Video Player.
- Windows port (community contribution; note in README when repos go public).
- Going public - make the repo public once the Kayenne/Sony hardware tests pass.

**Settled - do not reopen:** stills are SWS-only (see "Stills are SWS-only (settled)"); true drag-and-drop dropped; manual batch reorder dropped.

**After the gate:** the native Swift port (see HANDOVER_NOTES "Swift Rewrite" and `design/`).

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
4. **White key — INVESTIGATE ONLY, do not change without evidence.** `_generate_white_key` (~404–418) decodes as Y=64 (black in the 64–940 convention), while the alphaextract and EIF→SWS key paths write 940 as opaque — a contradiction. *But* the white-key behaviour was confirmed on hardware, so the generated key is presumably correct as-is. Before any change: hex-compare `_generate_white_key`'s output against a real K-Watch reference file that has a generated key, and check what value the alphaextract path actually produces for a fully-opaque alpha. Document the finding here; change code only if the comparison proves an inversion. See also "### White Key Plane" below.

### Stills are SWS-only (settled — do not reopen)

**Decision (David, 2026-08-05): single-frame clips are not a thing. This is out of the spec permanently and is not to be proposed again.**

A still image converts to a Kahuna `.SWS` still, and to nothing else. MacHuna does not produce single-frame Kayenne EIF, Sony TGA or TGA Sequence output. Those outputs require a clip or a TGA sequence.

**Why this kept coming back:** the docs contradicted themselves. `DEVELOPMENT_NOTES.md` had exactly one supporting line (the batch-convert scope note: "single-frame TGA stills are an edge case not worth the ambiguity"), while `README.md`, `USER_MANUAL.md` and the Fix 4 review entry all implied stills were valid input for the clip-style outputs. The Fix 4 entry went further and proposed building it. Anyone reading the docs fresh would reasonably have concluded it was wanted. That is now fixed in all four places, which is the point of this section.

**Enforced in code** by a guard in the Convert handler (search `Stills are valid for Kahuna SWS output only`), which blocks the combination with a named-file error before any conversion starts. Before v1.6.12 a still selected with a clip-style output silently vanished: no file, no error, no log entry, because neither `_run_to_tga_seq` nor `_run_to_eif` has a `'still'` branch.

**Not affected:** stills → Kahuna SWS remains a headline, hardware-confirmed feature. This decision narrows the *outputs* stills are offered to; it does not remove stills as an input.

### EIF Roadmap — hardware verification first

Fix 14 (clip→EIF speed, v1.6.11) cleared the last item that could be done without hardware. **Everything remaining is gated on either a live Kayenne desk or reference files from a Kayenne operator.** So the roadmap is no longer a list of things to code speculatively — it is one hardware-test session, plus the code follow-ups that the results unlock. Do not build the follow-ups ahead of the test; the whole point is to stop guessing.

#### Priority 1 — the EIF hardware test session (unblocks almost everything below)

The single most important outstanding work in the project. When a live Kayenne ClipStore / Image Store is available, run the "Priority hardware test steps" above and, in the same visit, capture what's needed to close the other unknowns. Get through as much of this checklist as the desk time allows:

- [ ] **EIF write, 50fps (core go/no-go)** — Convert a known short 50fps TGA sequence to `0001.eif`, import, verify: file appears, frame count correct, plays at correct speed, colours correct, key correct.
- [ ] **EIF write, 25fps** — Same with a 25fps source. Confirms the 25fps write path.
- [ ] **Capture a real 25fps `.eif`** produced by the Kayenne itself → hex-compare offset 0x8DC to verify or correct the assumed `b'RIFFRIFF'` movi chunk tag (the 50fps value is already confirmed).
- [ ] **Capture a real interlaced `.eif`**, or otherwise establish how the desk stores originally-interlaced content (50p progressive, 25p field-pairs, or other). Settles the "1080i in EIF" unknown and tells us which write path's interlaced handling is correct.
- [ ] **Capture a real `.eaf`** companion file from a clip that has audio → the audio format is entirely unknown; this file is the prerequisite before any EIF-audio code can be written.
- [ ] **Tail length** — obtain one reference file with frame_count < 36 and one with ≥ 36 → confirm whether the desk cares about the 128 vs 140-byte tail.
- [ ] **Clip name / slot rules** — try importing with a clip name (0x004) that does not match the filename stem, and with non-contiguous / non-`0001` start slots → learn whether the desk enforces either.
- [ ] **While a desk is available, verify the other unconfirmed extraction outputs too:** EIF→SWS (lossless), EIF→Kayenne TGA, EIF→Sony TGA, Kayenne MOV/TGA output, interlaced-SWS→MOV field-order metadata, and Sony MVS 25i field order. See the two hardware-unknowns tables above.

#### Priority 2 — code follow-ups, unlocked by the test results (do NOT build speculatively)

- **EIF audio (.eaf)** — once a real `.eaf` is hex-analysed, implement read and write.
- **Interlaced EIF reconciliation** — once the desk's interlaced storage is known, fix whichever of `convert_clip_to_eif` (currently passes interlaced through untouched) or `convert_tga_seq_to_eif` (deinterlaces to 50p via yadif) is wrong, so the two paths agree.
- **25fps movi tag** — correct the 8 bytes at 0x8DC if the hex compare shows the `b'RIFFRIFF'` assumption is wrong.
- **Tail length** — extend the tail to 140 bytes for all files if the desk turns out to be strict about it.

#### Priority 3 — pure code, no hardware needed (lowest priority — no demand yet)

- **EIF→Kayenne MOV** — decode EIF frames → ffmpeg ProRes 4444 encode. Not yet coded. The only remaining item that needs neither hardware nor reference files, but there is no user demand for it, so it sits below the hardware work.

### Future Considerations
- HLG Rec.2020 colour space option (header field 0x188 needs a different value -- requires a real HLG SWS to hex dump and verify)
- Split file support in Video Player (requires virtual multi-file stream abstraction and frame cap)
- Sony MVS 25i field order confirmation -- BFF assumed for PAL/50Hz; needs live hardware test on a Sony MVS desk
- ~~Sony MVS 50i TGA output in Hula~~ -- DONE (v1.5.20/v1.5.21 as Sony MVS TGA 25i with BFF/TFF toggle and source guard)
- ~~True drag and drop~~ -- Dropped. Current file picker workflow is sufficient.

### Unified App (implemented in v1.5.33)

MacHuna v1.5.33 unified the full conversion engine into a single format-in / format-out UI. The user opens a folder; MacHuna autodetects the input type (SWS, video, TGA/stills) and adapts the Output dropdown and controls accordingly. The "which tool do I use?" question is gone.

**Remaining work:** The extraction output paths (SWS → Kayenne MOV, SWS → Kayenne TGA, SWS → Sony TGA, MOV → TGA) are coded and working by analysis but unconfirmed on real hardware. These need live desk tests on Kayenne and Sony MVS before being marked confirmed. See "Extraction output hardware unknowns" below.

---

## Extraction Engine (integrated from v1.5.0, unified in v1.5.33)

MacHuna's extraction engine converts `.SWS` files back to standard media formats for use on Kayenne and Sony MVS desks. It was developed first as a standalone app (`DNSVision/Hula`, last version v0.1.1) then folded into MacHuna v1.5.0, and fully unified into the main Convert interface in v1.5.33. **The standalone repo is archived and no longer maintained.**

### How it works in MacHuna (v1.5.33+)

- Open a folder of `.SWS` files; MacHuna autodetects the input type and populates the Output dropdown with extraction targets (Kayenne MOV, Kayenne TGA, Sony TGA)
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
| Kayenne MOV | ProRes 4444, embedded alpha, BT.709, audio if present | `0001.mov`, `0002.mov` ... flat in dest | SWS input only |
| Kayenne TGA | 32-bit RGBA TGA | `0001.tga` onwards, subfolder per SWS | Progressive or interlaced via standard dropdown |
| Sony TGA | 32-bit RGBA TGA | `XXXX0000.tga` onwards (4-char clip name prefix + frame number), subfolder per SWS | Progressive or interlaced via standard dropdown; BFF/TFF toggle for interlaced |

### Sony MVS interlaced TGA -- implemented in v1.5.20+

Interlaced TGA output was implemented in v1.5.20 via field-weaving (pairs of progressive frames interleaved by line). Available for all interlaced standards via the Standard dropdown. Field order toggle (BFF/TFF) present; BFF assumed for PAL/50Hz, unconfirmed on hardware.

### Extraction output hardware unknowns (as of v1.5.33)

A thorough code review (May 2026) identified the following items that are coded but unconfirmed on real hardware. Each needs a live desk test before being marked confirmed.

| Item | Status | Notes |
|------|--------|-------|
| **Kayenne MOV output** | UNCONFIRMED on Kayenne hardware | ProRes 4444, correct fps, BT.709. Logic correct by analysis but never loaded onto a live Kayenne ClipStore/Image Store. |
| **Kayenne TGA output** | UNCONFIRMED | 32-bit RGBA, correct naming (0001.tga onwards). Marked UNCONFIRMED in code since v1.5.22. |
| **Sony MVS TGA clip naming** | UNCONFIRMED | 4-char clip prefix + 4-digit frame number (e.g. `WIPE0000.tga`). Naming convention assumed from desk documentation; not verified by importing onto a live Sony MVS. |
| **Interlaced SWS → MOV: interlace metadata** | KNOWN GAP | A 1080i/50 SWS converted to Kayenne MOV produces a 25fps ProRes file with correctly decoded interlaced frames, but ffmpeg does not write field-order flags into the container. A downstream NLE or desk may not identify the frames as interlaced. Whether a Kayenne desk cares is unknown — needs hardware test. Potential fix: add `-field_order tb` (TFF) or `bb` (BFF) to the ffmpeg encode command. |
| **Interlaced SWS → TGA (progressive target)** | POTENTIAL CONFUSION | If an interlaced SWS is converted to TGA with a progressive standard selected, MacHuna does a straight frame dump (correct — it doesn't try to deinterlace). The resulting TGAs contain interlaced frames, which will show comb artefacts if treated as progressive. This is an edge case but worth documenting. |
| **Sony MVS 25i field order** | UNCONFIRMED | TFF is now the default (changed from BFF in v1.6.3 on engineer advice). A TFF/BFF toggle is present in the UI. Needs live desk test — if motion artefacts appear, flip the toggle. |
| **MOV → TGA** | UNCONFIRMED | Full path (MOV input + TGA target) is coded and routes correctly, but has never been tested on hardware. |

**How to hardware-test:** Convert a known clip in MacHuna to SWS, then round-trip it back through MacHuna's extraction outputs. Load the result onto the target desk and verify correct playback, frame count, and field order. The Kayenne and Sony tests are independent — access to each desk is needed separately.

---

## EIF Format (Grass Valley Kayenne Native)

Added in v1.5.39–v1.6.0. MacHuna can read and write Grass Valley Kayenne `.eif` clips. The format was fully reverse-engineered from real Kayenne-produced files (UCI Downhill World Cup title card, 50fps, file `0003.eif`).

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
| 0x060 | 4 bytes | Flags | 0x03=50fps, 0x07=25fps |
| 0x064 | 4 bytes | Rate code | 0x000104A4=50fps, 0x00010484=25fps |
| 0x06C | 4 bytes | Frame count | Logical frames (units = frame_count × 3) |
| 0x070 | 4 bytes | video_start | Byte offset to first unit |
| 0x080 | 4 bytes | video_end | Byte offset after last unit |
| 0x0A8 | 16 bytes | Thumbnail meta | Constant: 80×45 RGB24, AVI start at 220 |
| 0x0DC | — | AVI RIFF | Size field = 0; Kayenne ignores it |
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
| `_hula_convert_eif_to_tga(...)` | EIF → Kayenne TGA or Sony TGA (progressive) |
| `_hula_convert_eif_to_tga_interlaced(...)` | EIF → interlaced TGA (field-woven pairs) |

### EIF Hardware Unknowns and Roadmap

All EIF write paths are coded and verified against real Kayenne reference files by hex analysis. None have been tested on live Kayenne hardware. The following items need hardware or reference-file access to resolve:

| Item | Status | Detail |
|------|--------|--------|
| **EIF write — Kayenne hardware test** | UNCONFIRMED | Generated `.eif` files have never been loaded on a live Kayenne ClipStore or Image Store. Header matches real clips byte-for-byte (excluding timestamp and clip name). Priority: HIGH — the most important test to run. |
| **25fps EIF movi chunk tag** | UNCONFIRMED | The 8-byte movi chunk tag at 0x8DC for 25fps EIF is assumed to be `b'RIFFRIFF'` (i.e. the ASCII bytes `RIFF` repeated). No 25fps reference files were available. The 50fps value `\x00\x02\x01\x04\x00\x02\x01\x04` is confirmed. Fix requires a real 25fps Kayenne-produced `.eif` file for hex comparison. |
| **Tail length: 128 vs 140 bytes** | KNOWN GAP | MacHuna-generated files have a 128-byte tail sentinel. Real Kayenne files with frame_count ≥ 36 have 140-byte tails (difference is 12 bytes of unknown content). Unknown if Kayenne validates tail length. Low risk — the extra bytes may be padding. |
| **EIF→Kayenne TGA** | UNCONFIRMED | Coded and working by analysis; never loaded on a Kayenne Image Store. |
| **EIF→Sony TGA** | UNCONFIRMED | Coded and working by analysis; never imported on a Sony MVS. |
| **EIF→Kahuna SWS (lossless)** | UNCONFIRMED | Round-trip verified in software (Video Player confirms correct output). Unconfirmed on Kahuna hardware. |
| **EIF→Kayenne MOV** | NOT IMPLEMENTED | No EIF→MOV path exists. Would require decoding EIF frames and encoding to ProRes 4444 via ffmpeg. |
| **EIF audio (.eaf companion files)** | NOT IMPLEMENTED | Kayenne companion `.eaf` files are suspected to carry audio. `has_audio` is always False. Audio format entirely unknown. Needs hex analysis of a real `.eaf` file. |
| **1080i content in EIF** | UNKNOWN | EIF is always stored progressively. How a Kayenne desk handles originally-interlaced content (whether it stores as 50fps progressive, 25fps field-pairs, or some other format) is unknown. This affects the interlaced TGA→EIF path (currently uses frame duplication). |
| **Embedded clip name on Kayenne import** | UNKNOWN | Whether the Kayenne reads or validates the clip name at header offset 0x004 is unconfirmed. MacHuna writes the source filename stem. If Kayenne enforces specific naming, the clip name field may need to match the slot filename stem. |
| **Slot number range and contiguity** | UNKNOWN | Whether the Kayenne requires EIF clips to be numbered from a specific starting slot (e.g. 0001) or requires contiguous numbers is unconfirmed. MacHuna uses the slot spinbox value as the starting number. |

**Priority hardware test steps:**
1. Use MacHuna to convert a known short TGA sequence (e.g. 10 frames, 50fps) to EIF → name it `0001.eif`
2. Copy to a USB drive formatted correctly for Kayenne
3. Import on a live Kayenne ClipStore / Image Store
4. Verify: file appears, frame count correct, playback correct speed, colours correct, key correct
5. If clips with audio need testing: source a real `.eaf` file from a Kayenne operator for hex analysis before implementing

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

**Key finding:** 201.SWS source TGAs were already interlaced frames (Kayenne output), so frame_count matching the TGA count is expected. The P→I transcoding confirmation came from the second 50.SWS analysis (see above).

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
