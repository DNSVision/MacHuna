# MacHuna & Hula - Session Handover Notes

Paste this document into a new Claude session to resume development. Read carefully before asking for any files or writing any code.

---

## Recent Session Notes (May 2026)

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

7. **Batch Convert TGA ambiguity - fixed in v1.5.16.** TGA files removed from the Batch Convert file picker entirely. Batch Convert now accepts MOV, MP4, MXF, MKV, AVI, PNG, BMP, and JPG only. A hint label in the Batch Convert row directs TGA sequence users to the Watch Folder.

**Remaining items from the review (no action needed):**
- SWS Player memory usage - frames cached in memory, fine for short clips but a known limitation for longer material. Document rather than fix.
- Single-file architecture - machuna.py contains conversion engine, header builder, GUI, watch service, audio, SWS Player, Hula, settings, CLI. Suggested future modularisation: sws.py, player.py, hula.py, audio.py, gui.py. Not urgent.

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
- **Stop button** now calls `_kill_current_ffmpeg()` in addition to setting the WatchService stop event
- Kill is immediate for long MOV conversions; for rapid TGA floods the scan thread may have already queued files which will still convert - this is an acceptable limitation
- A global `_current_ffmpeg_proc` and `_ffmpeg_proc_lock` track the active subprocess via `_run_ffmpeg()` wrapper
- Killing ffmpeg raises `subprocess.CalledProcessError` with SIGKILL (-9) - this is caught by WatchService `_scan()` exception handler and logged. This is correct behaviour, not a bug.
- Conversion log is not written if batch is cancelled

### File Delivery Method
Claude Code CLI has direct file system access and edits machuna.py directly using the Edit tool. No patch scripts needed. Always test with `python3.12 ~/Developer/MacHuna/machuna.py --gui` before building.

---

## What These Projects Are

**MacHuna** (`DNSVision/MacHuna`) is a macOS application that converts video and still image files to the Grass Valley Kahuna `.SWS` native format. It is a Mac-native alternative to the Windows-only K-Watch application. Built by David Steer (DNS Vision Limited) and Claude (Anthropic) using AI-assisted development with no prior coding background on David's part.

**Hula** is MacHuna's built-in SWS extractor — converts `.SWS` files back to standard media formats for Kayenne and Sony MVS desks. Originally built as a standalone app (`DNSVision/Hula`), now fully integrated into MacHuna. The standalone repo is **archived and no longer maintained** — MacHuna's integrated Hula has far outstripped it in features.

MacHuna repo is currently **private**.

---

## Current Versions

- **MacHuna:** v1.5.30
- **Hula (standalone, archived):** v0.1.1 — no longer maintained, use MacHuna's built-in Hula

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
- **Key libraries:** Pillow, numpy, tkinter, sounddevice, watchdog, tkinterdnd2-universal

---

## Build Commands

### MacHuna

```bash
cd ~/Developer/MacHuna && python3.12 -m PyInstaller \
  --onedir \
  --windowed \
  --name "MacHuna" \
  --icon ~/Developer/MacHuna/machuna.icns \
  --add-binary "/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffmpeg:." \
  --add-binary "/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffprobe:." \
  --add-data "/Users/davidsteer/Developer/MacHuna/machuna_final_1024.png:." \
  --noconfirm \
  ~/Developer/MacHuna/machuna.py
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

- Watch Folder service - converts incoming media files to .SWS automatically
- Batch Convert - file picker for MOVs and stills
- Cancel Batch button - kills current ffmpeg and stops batch after current file
- Stop button - stops watch folder service AND kills current ffmpeg immediately
- Video standards: all nine confirmed by K-Watch hex analysis -- 1080i/50, 1080i/59.94, 1080i/60, 1080p/25, 1080p/50, 1080p/59.94, 1080p/60, 720p/50, 720p/59.94
- Progressive-to-interlaced mismatch warning logged automatically
- Input formats: MOV, MP4, MXF, MKV, AVI, TGA sequences, PNG, BMP, JPG
- Fill and key planes encoded as v210 big-endian
- Ignore alpha/key option
- Audio: 16-bit LE PCM, 16ch, 48kHz, L=Ch1 R=Ch3 (K-Watch mapping)
- Auto play / Loop play flags
- Large file support: >4GB split into 2GB FAT32-safe chunks
- Built-in SWS Preview Player (fill, key, composite, audio meters)
- Built-in Hula SWS Extractor
- Window size persisted between sessions
- Settings saved to `~/.kwatch_settings.json`

---

## Hula Feature Summary

- Converts .SWS to four output targets:
  - Kayenne MOV: ProRes 4444 with embedded alpha, BT.709, audio muxed if present
  - Kayenne TGA: 32-bit RGBA, frames 0001.tga onwards, subfolder per SWS
  - Sony MVS TGA (50p): 32-bit RGBA progressive, frames XXXX0000.tga (4-char clip name prefix)
  - Sony MVS TGA (25i): field-woven interlaced from 1080p50 source, BFF/TFF toggle, frame count halved
- Batch conversion supported
- Source guard: Sony MVS 25i rejects non-1080p50 input with a clear error message
- Per-file metadata shown at load time: standard, frame count, duration

---

## Code Structure in machuna.py

The file is a single script. Key sections in order:

1. Imports and constants (including `_current_ffmpeg_proc` and `_ffmpeg_proc_lock`)
2. `_run_ffmpeg()` - tracked ffmpeg subprocess wrapper
3. `_kill_current_ffmpeg()` - kills active ffmpeg process
4. SWS header builder and conversion functions (Watch Folder path)
5. WatchService class
6. SWSPlayer classes (PlayerFrameCache, PlayerAudio, SWSPlayer)
7. **Hula section** - HulaSWSHeader, _hula_* converter functions, HulaWindow class
8. launch_gui() - main GUI

The v210 decoder functions (`_v210_plane_to_yuv`, `_yuv_to_rgb8`, `_yuv_to_gray8`) are shared between SWSPlayer and Hula - do not duplicate.

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

### Hula (integrated in MacHuna only — standalone DNSVision/Hula archived)
- Live hardware test on Kayenne and Sony MVS — Sony MVS clip naming unverified on hardware
- Sony MVS 25i field order confirmation — BFF assumed for PAL/50Hz; flip toggle in Hula if motion artefacts appear on a real desk

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
- Both Stop (watch folder) and Cancel Batch call `_kill_current_ffmpeg()`
- Killing ffmpeg mid-conversion raises CalledProcessError with SIGKILL (-9) - caught by WatchService exception handler

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
