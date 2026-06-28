# MacHuna - Session Handover Notes

Paste this document into a new Claude session to resume development. Read carefully before asking for any files or writing any code.

---

## Recent Session Notes (June 2026 — v1.6.6)

### v1.6.6 — Sony TGA output for TGA sequence input

- `OUTPUT_SONY_TGA` added to `to_sws_only` output options in `_update_output_options()`.
- `_update_adaptive_controls()` Sony TGA branch now also shows `chk_tga_int` ("TGA source interlaced") when `_has_tga_seq[0]` is set.
- `worker()` routing: `elif out == OUTPUT_TGA_SEQ or (out == OUTPUT_SONY_TGA and itype == 'to_sws_only')` routes to `_run_to_tga_seq()` instead of falling through to `_run_from_sws()`.
- `_run_to_tga_seq()` extended: detects `is_sony = (out == OUTPUT_SONY_TGA)` at the top. When Sony: output folder is the 4-char clip name (`cn`), output pattern is `CN%04d.tga`, start number is `0` (Sony 0-based). Otherwise unchanged.
- Existing guards (4-char clip name validation, single-clip guard) already applied to all `OUTPUT_SONY_TGA` cases — no changes needed there.

---

## Recent Session Notes (June 2026 — v1.6.5)

### v1.6.5 — SWS→SWS conversion + TGA Sequence output + Kayenne MOV removed

**SWS→SWS standards conversion (i↔p):**
- "Kahuna SWS" added to the Output dropdown when input type is `from_sws`.
- Routed through `_run_to_sws()` → new `sws` branch: extracts SWS frames to a temp TGA dir via `_hula_convert_tga`, then calls `convert_tga_sequence` to re-encode.
- Source interlace auto-detected from SWS header (`'i' in HulaSWSHeader.standard`) — no user checkbox.
- I→P uses `yadif=mode=send_field:parity=tff` (target fps > source fps) or `yadif=mode=send_frame:parity=tff` (same/lower). P→I uses `tinterlace=mode=interleave_top`. Passed via new `_vf_override` parameter on `convert_tga_sequence` to bypass the existing frame-duplication path for i→p.

**TGA Sequence output:**
- New constant `OUTPUT_TGA_SEQ = "TGA Sequence"` added to output constants.
- Appears in `to_sws_only` (TGA/stills input) and `mov_only` (video clip input) dropdown options.
- New function `_run_to_tga_seq()` handles conversion via ffmpeg concat demuxer (TGA input) or direct `-i` (clip input). P→I: tinterlace. I→P: yadif. Passthrough: no filter.
- Routed in `worker()` via `elif out == OUTPUT_TGA_SEQ`.
- "TGA source interlaced" checkbox is shown when input has TGA sequences.
- Output: `0001.tga, 0002.tga…` in `{dest}/{sequence_base}/` subfolder.

**Kayenne MOV removed from SWS output options:**
- Removed from `_update_output_options()` `from_sws` branch.
- Removed from `_run_from_sws()` `target_map`.
- Withdrawn because it was unconfirmed on hardware and not consistently available across all input types.

**`convert_tga_sequence` change:**
- Added `_vf_override: str = None` parameter (internal). When set, bypasses automatic filter detection and uses the supplied ffmpeg filter string directly. Also suppresses frame duplication in the concat file (`do_i_to_p = False`). Used by the SWS→SWS i→p path to apply yadif. Default is None — no change to existing callers.

---

## Recent Session Notes (May 2026 — v1.6.2)

### v1.6.2 — EIF→EIF routing bug fixed; doc corrections

- Removed "Kayenne EIF" from the Output dropdown when the input is EIF files (or a mixed EIF+SWS folder). EIF→EIF conversion was never implemented — `_run_to_eif()` has no handler for `item['type'] == 'eif'`, so EIF files were silently skipped. The option is now absent rather than offering a no-op. Sourcing SWS→EIF from a mixed folder still works via the SWS path.
- Corrected README input detection table (removed Kayenne EIF from EIF source output options).
- Updated HANDOVER_NOTES v1.5.41 historical notes (internal contradiction: bits[29:20] was described as a "constant framing marker" in the confirmed encoding section, then correctly as the key channel two paragraphs later).
- Updated Feature Summary to include EIF features.
- Updated project memory file version.

---

## Recent Session Notes (May 2026 — v1.6.1)

### v1.6.1 — Code cleanup

Post-EIF deep review. No functional changes.

- Removed five dead functions that were superseded by earlier refactors: `_pick_from_folder`, `_load_from_item` (replaced by `askopenfilename` direct picker), `_scan_folder_for_items`, `_scan_folder_for_player` (replaced by `_scan_folder_unified`), `_group_files_for_batch` (replaced by unified batch path).
- Extracted shared EIF bit-decode logic into module-level `_eif_parse_unit(raw) -> (yuv, key)` helper; removed duplicated inner `_unit_arrays` from both `_decode_eif_frame` and `_decode_eif_frame_rgba`.
- Moved `_EIF_UNIT_BYTES` constant from mid-file to the EIF constants block; removed three redundant `import numpy as np` from function bodies.
- Fixed Video Player status bar: still read "select a folder" after the switch to file picker.

---

## Recent Session Notes (May 2026 — v1.6.0)

### v1.6.0 — Full EIF feature set

This release completed the EIF (Grass Valley Kayenne native format) feature set. EIF was reverse-engineered from real Kayenne-produced files across v1.5.39–v1.5.43, with all conversion paths added in v1.6.0.

**What was added:**
- EIF as a conversion output: TGA sequences, MOV, and SWS files can all be converted to `.eif`. Slot naming uses 4-digit zero-padded filenames (0001.eif, 0002.eif…) matching Kayenne's naming convention. A slot spinbox lets the user set the starting slot number.
- TGA source interlaced option for EIF output: uses ffmpeg frame duplication (same concat-repeat approach as TGA→SWS interlaced path) to produce 50fps progressive EIF from 25fps interlaced TGA.
- Batch log written to destination folder after EIF batches.
- EIF as a conversion input: EIF files now appear in the main conversion picker. Folders with EIF only (`from_eif`) and mixed EIF+SWS (`mixed_eif_sws`) both route to EIF-aware outputs.
- EIF → Kahuna SWS: lossless direct YCbCr repack using `_eif_frame_to_v210be`. No RGB round-trip. Output standard auto-derived from EIF fps (ignores user's Standard dropdown).
- EIF → Kayenne TGA: full-res 1920×1080 RGBA TGA sequence, progressive or field-woven interlaced.
- EIF → Sony TGA: 32-bit RGBA with 4-char clip name prefix, progressive or field-woven interlaced.
- Video Player file picker changed from folder picker to standard file picker (files can be clicked directly).
- Format label added to Player info strip for all formats (SWS, TGA, MOV, EIF).

**What is NOT yet confirmed on hardware:**
All EIF write paths are UNCONFIRMED pending a live Kayenne desk test. See DEVELOPMENT_NOTES.md "EIF Hardware Unknowns and Roadmap" for the full table and priority test steps. Key outstanding items:
- EIF write output — never loaded on a live Kayenne desk
- 25fps EIF movi chunk tag at 0x8DC — assumed, no 25fps reference file available
- EIF→Kayenne TGA / EIF→Sony TGA — coded, never hardware-tested
- EIF audio (.eaf companion files) — not implemented; format unknown
- Tail length discrepancy (128 vs 140 bytes for fc≥36)

**EIF pixel format (confirmed from real hardware):**
- 32-bit LE word per pixel: bits[29:20]=key, bits[19:10]=Y, bits[9:0]=C (even=Cb, odd=Cr)
- Three 360-row units stacked vertically = 1920×1080 per frame
- Frame duration at header 0x0FC: 40000µs = 25fps, 20000µs = 50fps

---

## Recent Session Notes (May 2026 — v1.5.41)

### v1.5.41 — EIF key channel decoded; v1.5.40 — EIF colour decode fixed

EIF pixel format fully reverse-engineered from a real mountain bike clip (UCI DOWNHILL WORLD CUP title card, file `0003.eif`).

**Confirmed EIF pixel encoding (final — as implemented):**
- Each 32-bit LE word = one pixel: `bits[29:20]` = key (10-bit limited: 64=transparent, 940=opaque), `bits[19:10]` = Y luma, `bits[9:0]` = chroma C
- Chroma assignment: **even columns = Cb, odd columns = Cr** (standard 4:2:2 horizontal subsampling)
- Each unit is **360 rows × 1920 columns** (not 540×1920 as originally assumed)
- Three units stacked vertically = **1920×1080** complete frame

Note: v1.5.40 initially interpreted `bits[29:20]` as a "constant framing marker" (because wipe key clips have key=940=fully opaque throughout, which looks like a constant). v1.5.41 confirmed it is the key channel — wipe-pattern clips have key values that vary spatially and temporally. v210-based decode was entirely wrong; the current custom bit-field decode is correct.

**Key channel behaviour (confirmed v1.5.41):**
- For fill clips (e.g. DOWNHILL title card): key is always 940 = fully opaque
- For wipe/key clips (e.g. 0301.eif): key ramps from 64 to 940 and back, producing the correct wipe matte
- `EIFHeader.has_key = True` always; fill, key, and composite panels all populated

**Still unknown:**
- Tail section after `video_end` — suspected audio or some index; not yet decoded
- Audio: companion `.eaf` files believed to carry audio; `has_audio` remains False for now

---

## Recent Session Notes (May 2026 — v1.5.39)

### v1.5.39 — EIF playback (experimental)

Grass Valley Kayenne `.eif` format reverse-engineered via hex analysis of a live Kayenne-produced file. Confirmed findings:

- **Container**: GV proprietary header (220 bytes) + RIFF/AVI thumbnail + EIF metadata + pre-video fill + video data
- **Header fields** (all little-endian): clip name at `0x004` (null-terminated ASCII), flags at `0x060`, logical frame count at `0x06C`, video start at `0x070`, video end at `0x080`
- **Video data**: 360 rows × 1920 cols × 4 bytes/pixel, 2,764,800 bytes/unit, 3 units per frame stacked vertically = 1920×1080

---

## Recent Session Notes (May 2026 — v1.5.38)

### v1.5.38 — Video Player folder picker + fps dialog fix

- **Video Player folder picker**: Open… in the player now prompts for a folder (not a file). Scans for SWS, TGA sequences, and video files; TGA sequences collapsed to one entry per sequence. Shows a single-select list; double-click or Open loads the item. Mirrors the Convert window's existing folder browser behaviour. If only one item is in the folder, it loads directly.
- **TGA fps picker fix**: The frame-rate dialog after selecting a TGA sequence could appear behind the window or be unresponsive. Fixed by correctly sequencing `transient()`, `update_idletasks()`, `grab_set()`, and `focus_force()`.

---

## Recent Session Notes (May 2026 — v1.5.33)

### v1.5.33 — Unified format-in / format-out interface

MacHuna and Hula are now one tool. The separate Hula button and HulaWindow are gone. A single Convert section with input autodetection and an adaptive Output dropdown handles all conversion directions:

- **Folder scan → autodetect**: SWS files → FROM-SWS outputs (Kayenne MOV / Kayenne TGA / Sony TGA). MOV/video files → Kahuna SWS or TGA (with hardware-unconfirmed warning for MOV→TGA). Mixed video/TGA/stills → Kahuna SWS only.
- **Adaptive controls**: Standard, Split >4GB, Ignore alpha, Auto play, Loop play, TGA source interlaced, Include audio, Clip name (Sony TGA), BFF/TFF field order — shown only when relevant.
- **Sony TGA folder naming**: output subfolder now named after the 4-character clip name rather than the SWS stem.
- **"Video Player" button**: replaces "SWS Player" label; more accurate since it accepts SWS, TGA sequences, and video files.
- **`HulaWindow` class**: removed in post-v1.5.33 cleanup. All extraction engine functions (`_hula_run_batch`, `_hula_convert_tga`, `_hula_convert_mov`, etc.) remain unchanged.

The unified UI was the long-term direction discussed in v1.5.31 session notes. The hardware unknowns (Kayenne MOV, Kayenne TGA, Sony MVS clip naming, MOV→TGA) remain unconfirmed — the unconfirmed warning dialogue handles this at runtime.

---

## Recent Session Notes (May 2026 — v1.5.32)

### v1.5.32 — TGA Workflow Overhaul

Watch Folder and Slot Override were removed. MacHuna is positioned as a field tool for freelancers, not a networked server app. Watch Folder was a legacy of the K-Watch workflow that David confirmed would never be used in practice.

Key changes:
- **Smart folder browser**: "Open Files…" opens a folder picker; TGA sequences are collapsed to one entry (e.g. `TNTS201  (30 frames)`), video files and stills listed individually. User selects items and clicks Convert.
- **"Use source file number" checkbox**: replaces Slot Override. K-Watch files have slot number embedded in filename; ticking this uses it. Unticked = sequential from Start Number.
- **i→p TGA fix**: ticking "TGA source interlaced" when converting to a progressive standard now duplicates each frame to preserve duration (was playing at double speed before).
- **"Include audio" contextual**: moved into the folder browser dialog, only appears when audio is detected in a video file. Hidden for TGA-only folders.

---

## Recent Session Notes (May 2026 — v1.5.31)

### Unified App — Strategic Discussion (May 2026)

A strategic discussion was held about MacHuna's long-term direction. The core insight: MacHuna started as an SWS converter with Hula added as an optional extra. But the conversion engine now handles MOV, TGA, and SWS in both directions — making it more accurately described as a fully featured format conversion engine for broadcast media. Hula is no longer a bolt-on; it is the other half of the engine.

**The proposal:** Retire the separate Hula window and unify everything into a single format-in / format-out UI. The user picks an input format and an output format; the UI adapts to expose only the controls relevant to that combination (video standard, P/I options, field order, clip name, etc.). No more "is this a MacHuna job or a Hula job?" question.

**Why not do it now:** Six Hula output paths remain UNCONFIRMED on hardware (see Hula Hardware Unknowns table). A unified UI implies that all format combinations are equally reliable. Merging before those paths are confirmed would embed untested code deeper into the main product. The three pending Kahuna tests (below) validate the TO-SWS direction but do not touch the FROM-SWS (Hula) paths at all.

**What is needed before merging:**

1. Kahuna hardware test (imminent — highest priority):
   - 1080i/50 MOV → 1080p/50 SWS plays at correct speed (main v1.5.31 fix)
   - 1080p/50 → 1080i/50 SWS regression check
   - TGA i→i with "TGA source already interlaced" checkbox — correct speed on hardware
   - These confirm the MacHuna conversion engine (TO SWS direction) but do NOT clear the Hula (FROM SWS) unknowns.

2. Kayenne hardware tests (no timeline):
   - SWS → Kayenne MOV — load on a live Kayenne ClipStore / Image Store
   - SWS → Kayenne TGA — verify frame naming and format on hardware

3. Sony MVS hardware tests (no timeline):
   - SWS → Sony TGA — verify 4-char clip naming convention on a live desk
   - Sony MVS 25i field order — BFF assumed; confirm or flip on hardware

4. MOV → TGA via Hula — full path coded, never hardware-tested (not desk-specific; can be tested independently)

Once all FROM-SWS paths are confirmed, the unification can proceed cleanly.

**Near-term stepping stone (optional):** If the Hula/MacHuna split feels awkward before the full rearchitect is ready, a lower-risk improvement would be replacing the separate Hula Toplevel window with two tabs in the main window — "To SWS" and "From SWS" — without touching the underlying conversion logic.

---

### Hula Code Review and Bugfixes (v1.5.31)

A full analysis of Hula's conversion paths for interlaced and progressive sources was conducted. Two bugs were found and fixed:

1. **Interlaced SWS → interlaced TGA target was incorrectly rejected.** The batch runner sent all interlaced-standard selections to `_hula_convert_tga_interlaced`, which guards `fps < 48.0`. An interlaced SWS (25fps) was rejected. Fix: batch runner reads source header fps first. Progressive sources (fps ≥ 48) go to `_hula_convert_tga_interlaced` for field-weaving as before. Interlaced sources go to `_hula_convert_tga` (straight frame dump — frames already woven) with a log message advising the "TGA source already interlaced" checkbox for round-trips.

2. **Hula MOV encoder could not be cancelled.** `_hula_convert_mov` used `subprocess.run` directly, bypassing `_run_ffmpeg`. Stop/Cancel had no effect during long encodes. Fixed to use `_run_ffmpeg(cmd, check=True)`.

### Hula Hardware Unknowns (as of v1.5.31)

A full audit of the extraction output paths identified several items that are coded but unconfirmed on real hardware. These are all documented in full in DEVELOPMENT_NOTES.md under "Extraction output hardware unknowns". Summary:

- **Kayenne MOV and TGA outputs** — logic is correct by analysis, never loaded on a live Kayenne ClipStore/Image Store
- **Sony MVS clip naming** — naming convention assumed, not verified by live desk import
- **Interlaced SWS → MOV: interlace metadata** — ProRes container has no field-order flags; unknown whether a Kayenne desk cares. Potential fix: add `-field_order tb/bb` to ffmpeg encode.
- **Sony MVS 25i field order** — BFF assumed; toggle present if wrong
- **MOV → TGA** — full path coded and routes correctly, never hardware-tested

These are the main items to address in the next hardware test session. No code changes needed until hardware feedback is available.

---



### Development Workflow (updated)
David now uses Claude Code CLI directly. Claude has full file system access and can read, edit, and commit files without patch scripts. The old patch script workaround is no longer needed. Test command remains `python3.12 ~/Developer/MacHuna/machuna.py --gui`.

### Code Review Fixes (v1.5.10-v1.5.15, May 2026)
A comprehensive code review was conducted at the start of this session. Six bugs were found and fixed:

1. **Format variant (0x18C) wrong for 7 of 9 standards - fixed in v1.5.10.** The v1.5.8 reverse engineering confirmed the correct per-standard values but the code was never updated - it still used the v1.5.5 simple interlaced/progressive logic. A `FORMAT_VARIANTS` dict now maps each standard to its confirmed value. A `FORMAT_VARIANT_FPS` reverse lookup was also added (used by fixes 3 and 4 below).

2. **Ignore alpha not respected for TGA sequences - fixed in v1.5.11.** `convert_tga_sequence` was always generating a white key plane when `ignore_alpha=True` instead of omitting the key plane entirely. Also fixed the missing `has_key` argument in its `build_sws_header` call.

3. **Stop/Cancel could not kill ffmpeg during audio extraction or TGA sequence conversion - fixed in v1.5.12.** Several ffmpeg calls were using `subprocess.run` directly instead of the `_run_ffmpeg` wrapper, making them invisible to `_kill_current_ffmpeg()`. All ffmpeg calls now go through the wrapper.

4. **SWSPlayer and Hula reported wrong fps for most standards - fixed in v1.5.13.** Both header parsers were looking up fps from the standard code (0x188), but eight standards share code 0x4923 so the lookup was ambiguous. Both now read the format variant (0x18C) first and use `FORMAT_VARIANT_FPS` for an unambiguous lookup, with the old standard code lookup retained as fallback for third-party files.

5. **SWSPlayer played interlaced files at double speed - fixed in v1.5.14.** `FORMAT_VARIANT_FPS` was returning the field rate (50/59.94/60) for interlaced standards instead of the frame rate (25/29.97/30). Each SWS frame is a full frame, not a field. Confirmed on hardware with a 1080i/50 wipe.

6. **SWSPlayer playback jitter - fixed in v1.5.15.** The playback loop was sleeping relative to each frame's start time, so sleep overshoot accumulated as drift. The loop now sleeps to an absolute target time derived from a fixed origin, so any overshoot self-corrects on the next frame.

7. **Batch Convert TGA ambiguity - fixed in v1.5.16.** TGA files removed from the Batch Convert file picker entirely. Batch Convert now accepts MOV, MP4, MXF, MKV, AVI, PNG, BMP, and JPG only. TGA sequences are handled via the smart folder browser.

**Remaining items from the review (no action needed):**
- Video Player memory usage - frames cached in memory, fine for short clips but a known limitation for longer material. Document rather than fix.
- Single-file architecture - machuna.py contains conversion engine, header builder, GUI, Video Player, extraction engine, audio, settings, CLI. Suggested future modularisation: sws.py, player.py, extraction.py, audio.py, gui.py. Not urgent.

**Positive findings:** Header builder, split-file streaming, audio channel mapping and pan filter all specifically praised.

### Auto Play / Loop Flags
Tested on real Kahuna hardware - Auto Play and Auto Play & Loop flags do not trigger expected behaviour. Crucially, the same files converted by K-Watch also fail to trigger the behaviour. Conclusion: MacHuna is correctly matching K-Watch output. The operational purpose of these flags is unclear - may require GPI trigger, specific store configuration, or particular firmware. Parked pending further investigation.

### Video Standard Codes - Full Verification (v1.5.8/v1.5.9, May 2026)
This was a major reverse engineering session. All nine supported video standards were verified by running K-Watch on Parallels and hex-dumping the output headers. Key findings:

- Both 0x188 (standard code) AND 0x18C (format variant) must be set correctly - we previously only knew 0x188
- 0x18C is NOT a simple interlaced/progressive flag - it is an index into the Kahuna's internal standard table
- All interlaced standards use standard code 0xc923 -- the 0x8000 bit flags interlaced scanning (not drop-frame). Confirmed by P→I transcode analysis (2026-05-09)
- Full confirmed table in DEVELOPMENT_NOTES.md

**How to verify a new standard:** Convert any file in K-Watch with the target standard. Run `xxd -l 512 output.SWS` and read 0x188 (4 bytes) and 0x18C (4 bytes).

**K-Watch behaviour notes:**
- K-Watch can transcode from any source standard to any output standard
- K-Watch requires a full restart when changing output standards - otherwise conversions fail or error
- K-Watch is unreliable with still images (TGA stills often fail to convert)
- K-Watch on Parallels on M1 takes several minutes per 60-frame clip

**Unverified standards removed from dropdown (v1.5.9):** 1080p/29.97, 1080p/30, 2160p variants. These need K-Watch reference files before being added back.

**Progressive-to-interlaced warning (v1.5.8):** MacHuna detects source scan type via ffprobe `field_order` and logs a warning if a progressive source is converted to an interlaced standard. The file loads on the Kahuna but plays at double speed. Genuine interlaced output is the next major feature - see Roadmap.
**Critical discovery confirmed by hex analysis of K-Watch reference files:**

- Offset 0x18C (format variant field) was previously hardcoded to 0x18 in MacHuna
- K-Watch writes 0x08 for 1080i50 and 0x18 for 1080p50
- 0x08 = interlaced, 0x18 = progressive
- MacHuna was writing 0x18 for all standards, causing the Kahuna to display interlaced files as "1080p/50 A" rather than "1080i/50"
- Fixed in v1.5.5: `_interlaced_standards = {'1080i50', '1080i5994', '1080i60'}`, fmt_variant = 0x08 if interlaced else 0x18
- **Only 1080i50 and 1080p50 have been confirmed against K-Watch reference files. All other standards are assumed to follow the same pattern but are unverified on hardware.**

### Format Standards - General
- Only 1080p50 has been properly tested in production
- Other standards (1080i50, 1080p25, 720p50, 720p59.94) are untested on hardware
- Format fusion on the Kahuna means a mismatched file will often still work
- Full hardware test of all standards would require cooperation from truck owners - significant effort for little operational benefit given David's workflow is almost entirely 1080p50
- Recommendation: mark untested standards clearly in DEVELOPMENT_NOTES (done) rather than removing them

### Stop Button / Cancel Batch (v1.5.7)
- **Cancel Batch button** added to main button row - enables when Open Files batch starts, kills current ffmpeg and stops after current file
- **Stop button** calls `_kill_current_ffmpeg()` to kill the active ffmpeg process immediately
- Kill is immediate for long MOV conversions; for rapid TGA floods already-queued files may still convert - acceptable limitation
- A global `_current_ffmpeg_proc` and `_ffmpeg_proc_lock` track the active subprocess via `_run_ffmpeg()` wrapper
- Killing ffmpeg raises `subprocess.CalledProcessError` with SIGKILL (-9) - caught and logged. Correct behaviour, not a bug.
- Conversion log is not written if batch is cancelled

### File Delivery Method
Claude Code CLI has direct file system access and edits machuna.py directly using the Edit tool. No patch scripts needed. Always test with `python3.12 ~/Developer/MacHuna/machuna.py --gui` before building.

---

## What These Projects Are

**MacHuna** (`DNSVision/MacHuna`) is a macOS application that converts video and still image files to the Grass Valley Kahuna `.SWS` native format. It is a Mac-native alternative to the Windows-only K-Watch application. Built by David Steer (DNS Vision Limited) and Claude (Anthropic) using AI-assisted development with no prior coding background on David's part.

MacHuna also extracts `.SWS` files back to standard media formats for Kayenne and Sony MVS desks (SWS → Kayenne MOV, Kayenne TGA, Sony TGA). This extraction engine was originally built as a standalone app (`DNSVision/Hula`), integrated into MacHuna v1.5.0, and unified into the main Convert interface in v1.5.33. The standalone repo is **archived and no longer maintained**.

MacHuna repo is currently **private**.

---

## Current Versions

- **MacHuna:** v1.6.6
- **Hula (standalone, archived):** v0.1.1 — no longer maintained, use MacHuna's extraction outputs

---

## Local File Locations

| File/Folder | Location |
|---|---|
| MacHuna source | `~/Developer/MacHuna/machuna.py` |
| MacHuna built app | `~/Developer/MacHuna/dist/MacHuna.app` |
| MacHuna repo | `https://github.com/DNSVision/MacHuna` |
| Settings | `~/.kwatch_settings.json` |
| PDF generation template | `~/Developer/MacHuna/manual_template.html` |

---

## Development Environment

- **Machine:** MacBook Air M1 - all development and building must happen here
- **Python:** 3.12 (`python3.12`)
- **ffmpeg:** Homebrew at `/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/`
- **PyInstaller:** pip3.12
- **Key libraries:** Pillow, numpy, tkinter, sounddevice, tkinterdnd2-universal

---

## Build Commands

### MacHuna

```bash
python3.12 -m PyInstaller MacHuna.spec -y
```

### User Manual PDF

```bash
pandoc ~/Developer/MacHuna/USER_MANUAL.md \
  -o ~/Desktop/MacHuna_User_Manual.html \
  --template=/Users/davidsteer/Developer/MacHuna/manual_template.html
```

Then open in Safari and File > Print > Save as PDF.

---

## GitHub Push Workflow

```bash
cd ~/Developer/MacHuna
git add .
git commit -m "Description"
git push
```

---

## MacHuna Repo Contents

```
~/Developer/MacHuna/
├── machuna.py              # Main source (~2,700 lines)
├── machuna.icns            # App icon
├── machuna_final_1024.png  # Icon source image
├── Audio Spec.pdf          # Historical reference - superseded, see DEVELOPMENT_NOTES
├── README.md               # Public overview
├── USER_MANUAL.md          # User manual (renders in GitHub)
├── manual_template.html    # Pandoc template for PDF generation
├── DEVELOPMENT_NOTES.md    # Engineering continuity document
├── CHANGELOG.md            # Version history
└── .gitignore
```

---

## MacHuna Feature Summary

- Batch Convert - smart folder browser for MOVs, TGA sequences, and stills
- Cancel Batch button - kills current ffmpeg and stops batch after current file
- Stop button - kills current ffmpeg immediately
- Video standards: all nine confirmed by K-Watch hex analysis -- 1080i/50, 1080i/59.94, 1080i/60, 1080p/25, 1080p/50, 1080p/59.94, 1080p/60, 720p/50, 720p/59.94
- Progressive-to-interlaced mismatch warning logged automatically
- Input formats: MOV, MP4, MXF, MKV, AVI, TGA sequences, PNG, BMP, JPG
- Fill and key planes encoded as v210 big-endian
- Ignore alpha/key option
- Audio: 16-bit LE PCM, 16ch, 48kHz, L=Ch1 R=Ch3 (K-Watch mapping)
- Auto play / Loop play flags
- Large file support: >4GB split into 2GB FAT32-safe chunks
- Built-in Video Player (fill, key, composite, audio meters) -- supports SWS, TGA sequences, MOV/MP4/MXF/AVI, and Kayenne EIF
- Built-in extraction engine (SWS → Kayenne MOV, Kayenne TGA, Sony TGA)
- **Kayenne EIF read** -- Video Player opens .eif files with fill, key, and composite panels; frame rate auto-detected from header
- **Kayenne EIF write** (UNCONFIRMED on hardware) -- converts MOV, TGA sequences, and SWS to .eif with slot-numbered output (0001.eif, 0002.eif...)
- **Kayenne EIF conversion** (UNCONFIRMED on hardware) -- EIF → Kahuna SWS (lossless YCbCr repack), EIF → Kayenne TGA, EIF → Sony TGA
- Window size persisted between sessions
- Settings saved to `~/.kwatch_settings.json`

---

## Extraction Output Summary

- Converts .SWS to three output targets:
  - Kayenne MOV: ProRes 4444 with embedded alpha, BT.709, audio muxed if present
  - Kayenne TGA: 32-bit RGBA, frames 0001.tga onwards, subfolder per SWS
  - Sony TGA: 32-bit RGBA, frames XXXX0000.tga (4-char clip name prefix), subfolder named after clip
- Progressive or interlaced output via Standard dropdown (TGA targets)
- Field order toggle (BFF/TFF) for interlaced standards; always shown for Sony TGA
- Batch conversion supported
- Per-file metadata shown at load time: standard, frame count, duration

---

## Code Structure in machuna.py

The file is a single script. Key sections in order:

1. Imports and constants (including `_current_ffmpeg_proc` and `_ffmpeg_proc_lock`)
2. `_run_ffmpeg()` - tracked ffmpeg subprocess wrapper
3. `_kill_current_ffmpeg()` - kills active ffmpeg process
4. SWS header builder and conversion functions
5. SWSPlayer classes (PlayerFrameCache, PlayerAudio, SWSPlayer)
6. Extraction engine — HulaSWSHeader, _hula_* converter functions
7. launch_gui() - main GUI

The v210 decoder functions (`_v210_plane_to_yuv`, `_yuv_to_rgb8`, `_yuv_to_gray8`) are shared between SWSPlayer and the extraction engine — do not duplicate.

---

## Known Issues

- PortAudio AUHAL errors in terminal when running as script on macOS 26 beta - harmless, invisible in built .app
- macOS 26 beta / Homebrew PortAudio instability - not worth investigating until macOS 26 goes final
- Auto Play / Loop flags - do not trigger on hardware, but K-Watch files also fail - not a MacHuna bug
- Ignore Alpha / TGA sequences - fixed in v1.5.11. Now correctly omits key plane when Ignore Alpha is ticked.
- Stop during rapid TGA flood - kills current ffmpeg but already-queued files may still convert. Acceptable limitation.

---

## Roadmap

### MacHuna
- **Format transcoding (P→I) field order confirmation:** Implemented in v1.5.18 using TFF (SMPTE standard for 1080i HD). Tested on a 1080P Kahuna — file loaded correctly, genuine interlaced fields confirmed. Field order TFF vs BFF cannot be assessed on a 1080P desk. Next test: load MacHuna P→I output on a 1080i/50 Kahuna and check for clean motion. If motion artefacts, change `interleave_top` → `interleave_bottom` in `convert_clip` (one word). See DEVELOPMENT_NOTES.md "Format Transcoding" section.
- Verify additional standards against K-Watch reference files before adding back to dropdown: 1080p/29.97, 1080p/30, SD standards (625/50, 525/59.94), sF variants, 2160p
- Ignore Alpha behaviour for TGA sequences - fixed in v1.5.11
- TGA in Batch Convert - clarify single-frame only, or detect sequences and warn
- HLG Rec.2020 colour space option (requires a real HLG .SWS file to verify)
- Split file support in SWS Preview Player

### Extraction outputs (standalone DNSVision/Hula archived)
- Live hardware test on Kayenne and Sony MVS — Sony MVS clip naming unverified on hardware
- Sony MVS 25i field order confirmation — BFF assumed for PAL/50Hz; flip the toggle in MacHuna if motion artefacts appear on a real desk

### Future consideration
- Windows port - the core Python code has no Mac-specific dependencies. Main changes needed: ffmpeg path handling, macOS menu bar code conditionally skipped, PyInstaller build on Windows machine. Someone with a Windows machine could fork and port without needing to redo any of the reverse engineering. Worth adding "Windows port contributions welcome" to README when repos go public.

### Going public
- Recommendation: do live hardware test on Kayenne and Sony MVS first, then make MacHuna repo public.

---

## Swift Rewrite Discussion

David has discussed potentially rewriting MacHuna as a native Swift/SwiftUI app as a hobby project (not a production necessity - the Python version is complete and working). Key points:

- Would be a staged rewrite: core SWS engine first, then SwiftUI interface
- Python version remains the reference implementation throughout
- ffmpeg would still be required even in Swift - bundle binaries approach
- Suggested repo name: `MacHuna-Swift` running alongside the Python version
- Development machine split: M1 MacBook Air = Python development, M5 MacBook Air = Swift/Xcode
- Swift is less forgiving than Python - harder days expected - but the fully documented SWS format and working reference implementation make it more tractable than a typical rewrite
- Decision deferred - no action needed until David decides to pursue it

---

## Important Technical Notes

### SWS Format
- 512-byte big-endian header
- Fill plane: v210 big-endian
- Key plane: v210 big-endian (absent if play_count at 0x1A8 == 0)
- Audio: 16-bit LE PCM, 16ch, 48kHz (absent if aud_offset at 0x1E8 == 0)
- Audio detection: use aud_offset > 0 AND aud_fmt == 0x03000000. Do NOT use 0x1C2 - unreliable.
- Full header reference in DEVELOPMENT_NOTES.md

### Video Standard Codes - All Confirmed
Full table confirmed by K-Watch hex analysis (2026-05-09). Both fields required:

| Standard | 0x188 | 0x18C |
|---|---|---|
| 1080i/50 | `0xc923` | `0x08` |
| 1080i/59.94 | `0xc923` | `0x05` |
| 1080i/60 | `0xc923` | `0x04` |
| 1080p/25 | `0x4923` | `0x13` |
| 1080p/50 | `0x4923` | `0x18` |
| 1080p/59.94 | `0x4923` | `0x17` |
| 1080p/60 | `0x4923` | `0x16` |
| 720p/50 | `0x4923` | `0x10` |
| 720p/59.94 | `0x4923` | `0x0f` |

0x18C is a Kahuna internal standard index, not a flags field. Do not assume values for unverified standards.

### v210 Decode
- ffmpeg 7.x has a confirmed bug decoding v210 from raw files (returncode 69). Never use ffmpeg for v210 decode.
- Use the pure numpy decoder. The `.copy()` before `byteswap()` is critical - do not remove it.

### Audio
- Channel mapping confirmed by hex analysis of K-Watch reference files: L=Ch1, R=Ch3
- Standard ffmpeg -ac 16 upmix is wrong - MacHuna uses an explicit pan filter

### PyInstaller
- Must use --onedir. --onefile + --windowed does not bundle ffmpeg correctly on macOS.
- ffmpeg path must point to real binary, not Homebrew symlink.

### ffmpeg Process Tracking
- `_run_ffmpeg()` wraps subprocess.Popen and registers the process in `_current_ffmpeg_proc`
- `_kill_current_ffmpeg()` kills the registered process if one exists
- Both Stop and Cancel Batch call `_kill_current_ffmpeg()`
- Killing ffmpeg mid-conversion raises CalledProcessError with SIGKILL (-9) - caught and logged

---

## Coding Preferences (David)

- British English spelling and grammar throughout
- No em dashes - use hyphens instead
- Plain-spoken tone when writing in David's voice
- Metric measurements unless otherwise requested
- No Chrome, no Google products
- Version bumps: patch version (x.x.X) for bugfixes, minor version (x.X.0) for new features
- Deliver code changes via Claude Code CLI (direct file edit), not patch scripts or file downloads

---

## Files to Request Before Writing Code

Before making any changes to machuna.py, ask for the current version to be uploaded - the file is large (~110KB) and changes frequently. Do not work from a cached version.

There is no standalone Hula repo to maintain — `DNSVision/Hula` is archived. All Hula development happens in `machuna.py`.
