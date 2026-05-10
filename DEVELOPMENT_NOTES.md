# MacHuna — Development Notes

This document is for continuity between development sessions. If starting a new Claude session, point Claude at this file and the main machuna.py source and development can resume from where it left off.

---

## Project Summary

MacHuna is a macOS watch folder application that converts video and still image files to the Grass Valley Kahuna `.SWS` native format. It was built collaboratively between David Steer (DNS Vision Limited) and Claude (Anthropic) with no prior coding experience on David's part.

**Current version:** v1.5.27
**Status:** Tested on a live Grass Valley Kahuna mainframe. Core conversion confirmed working. v1.5.27: SWS Player now accepts TGA sequences and MOV/MP4/MXF/AVI — known crash on second MOV open (fix pending). v1.5.26: Batch Convert confirmation dialog (custom Toplevel, no app icon). v1.5.25: Slot override field in Settings, two-row Settings layout, Batch Convert button visibility fix, default window size 960×460. v1.5.24: Fixed TGA sequence P→I conversion (missing tinterlace filter + wrong frame count). v1.5.23: Open in Finder buttons on Watch Folder, Destination Folder, and Hula Destination Folder rows. v1.5.22: Hula GUI redesigned — full standard dropdown (all 9 formats), MOV input support, Kayenne/Sony TGA targets consolidated (Kayenne TGA UNCONFIRMED). v1.5.21: Hula Sony MVS 25i source guard (rejects non-1080p50 input). v1.5.20: Hula Sony MVS 25i TGA output (field-woven, BFF/TFF toggle). v1.5.19: Compact broadcast metadata display in SWS Player and Hula (standard/frms/duration). v1.5.18: P→I transcoding via tinterlace (TFF, unconfirmed on 1080i hardware). v1.5.17: Interlaced standard codes corrected (0xc923 for all interlaced, 0x8000 = interlaced flag). v1.5.16: TGA removed from Batch Convert file picker. v1.5.15: SWSPlayer playback jitter fixed via absolute timing. v1.5.14: SWSPlayer interlaced playback speed fixed (field rate vs frame rate). v1.5.13: SWSPlayer and Hula fps lookup fixed for all standards. v1.5.12: All ffmpeg calls now go through _run_ffmpeg - Stop/Cancel works for all conversion paths. v1.5.11: Ignore alpha for TGA sequences fixed. v1.5.10: FORMAT_VARIANTS lookup table applied - format variant (0x18C) now correct for all nine standards. v1.5.9: Unverified standards removed from dropdown. v1.5.8: All nine video standards fully confirmed by K-Watch hex analysis; progressive-to-interlaced mismatch warning added. v1.5.7: Stop button kills ffmpeg immediately; Cancel Batch button added. v1.5.5: Format variant field (0x18C) initial fix. v1.5.4: Window size persistence. v1.5.0: Hula SWS Extractor integrated. v1.4.0: SWS Preview Player integrated. v1.3.0: Large file split (>4GB) confirmed working on live Kahuna.
**Repository:** https://github.com/DNSVision/MacHuna
**Dev machine:** MacBook Air M1 (all dev and building must happen here)

---

## Development Environment

- **Python:** 3.12
- **Key libraries:** Pillow, numpy, sounddevice, tkinter (built-in), subprocess, struct, watchdog, tkinterdnd2-universal (installed but currently disabled)
- **ffmpeg:** Installed via Homebrew at `/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/`
- **PyInstaller:** Installed via pip3.12
- **Working directory:** `~/Developer/MacHuna/`
- **Main script:** `machuna.py`

### Build Command

Always run from the project directory so build artefacts land in `~/Developer/MacHuna/` rather than the home folder.

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

Note: `--add-data` bundles the app icon PNG for the About box. The `~` shorthand does not expand inside `--add-data` so the full path is required. Built .app appears in `~/Developer/MacHuna/dist/MacHuna.app`. Right-click > Open first time to bypass Gatekeeper.

### GitHub Push Workflow

```bash
cd ~/Developer/MacHuna
git add .
git commit -m "Description of changes"
git push
```

---

## Roadmap (Priority Order)

1. ~~**Tidy dev environment / GitHub**~~ -- DONE
2. ~~**Ignore alpha/key option**~~ -- DONE. Checkbox in GUI. When ticked, no key plane is written at all and header fields 0x1A8 and 0x1B4 are zeroed -- matches K-Watch behaviour exactly (confirmed by live Kahuna test and hex analysis of K-Watch reference file). Note: earlier implementation wrote a solid white key plane which was incorrect -- the Kahuna was showing a black key panel rather than no key at all.
3. ~~**Batch convert with file picker**~~ -- DONE. Batch Convert section in GUI with start number field, Open Files button, alphabetical ordering, auto-incrementing numbers, and conversion log text file written to destination folder after each batch.
4. ~~**TGA sequence hint in Batch Convert**~~ -- DONE. Grey label added to Batch Convert section: "For TGA sequences, use the Watch Folder service above." Batch convert (Open Files) is for MOVs and single-frame stills only.
5. ~~**Audio support**~~ -- DONE. extract_audio() extracts 16-bit LE PCM, upmixes to 16 channels at 48kHz, pads to exact frame alignment. Header fields 0x1C2, 0x1E8, 0x1EC, 0x1CC updated correctly. "Include audio" checkbox added to GUI (default: on). Confirmed working on live Kahuna.
6. ~~**Auto play / Loop play**~~ -- DONE. Bits 2 and 3 of the low byte at 0x188 confirmed by hex analysis of K-Watch reference files across all four flag combinations (neither, auto only, loop only, both). Auto play = bit 2 (0x04), Loop play = bit 3 (0x08), OR'd into the video standard code. Both checkboxes added to GUI (default: off), saved to settings, passed through all converters and WatchService. Awaiting live Kahuna test.
7. ~~**Split large files (>4GB)**~~ -- DONE. Format fully reverse-engineered from real K-Watch split files. _write_sws_split() rewritten: correct 2GB chunk size, correct data layout (all fill then all key, not interleaved), correct header patching (0x1A8 and 0x1B4 zeroed, 0x1CC set to final chunk size), correct filename format (01_OF_03._XX), streams directly to disk with no in-memory buffering. Also fixed uint32 overflow in build_sws_header() for files >4GB (0x1CC now capped at 0xFFFFFFFF -- patched correctly by _write_sws_split() anyway). Confirmed working on live Kahuna.
8. ~~**SWS to MOV / TGA conversion (Hula)**~~ -- DONE. Hula SWS Extractor built first as standalone app (DNSVision/Hula v0.1.0), then integrated into MacHuna v1.5.0. See Hula Integration section below.
9. ~~**Manual reorder in batch convert**~~ -- Dropped. Alphabetical ordering is sufficient.
10. ~~**Standalone preview viewer**~~ -- DONE. SWS Player built as companion app (DNSVision/SWSPlayer) and integrated into MacHuna in v1.4.0. All player code folded into machuna.py -- SWSHeader, PlayerFrameCache, PlayerAudio, numpy v210 decoder, composite and meter functions. tkinter and Pillow imports moved to top level to support the player classes.
11. ~~**Integrate preview into main app**~~ -- DONE. SWS Player button added to top-right of Batch Convert row. Opens SWSPlayer as a non-modal tk.Toplevel child window. File picker opens at the configured Destination Folder. Multiple player windows can be open simultaneously. Closing the player does not affect MacHuna.

### Future Considerations
- HLG Rec.2020 colour space option (header field 0x188 needs a different value -- requires a real HLG SWS to hex dump and verify)
- Split file support in SWS Player (requires virtual multi-file stream abstraction and frame cap)
- Sony MVS 25i field order confirmation -- BFF assumed for PAL/50Hz; needs live hardware test on a Sony MVS desk
- ~~Sony MVS 50i TGA output in Hula~~ -- DONE (v1.5.20/v1.5.21 as Sony MVS TGA 25i with BFF/TFF toggle and source guard)
- ~~True drag and drop~~ -- Dropped. Current file picker workflow is sufficient.

---

## Hula Integration (v1.5.0)

Hula is an SWS extractor -- the reverse of MacHuna. It converts `.SWS` files back to standard media formats for use on Kayenne and Sony MVS desks. It was developed first as a standalone app (`DNSVision/Hula`, last version v0.1.1) then folded into MacHuna following the same pattern as SWS Player. **The standalone repo is archived and no longer maintained** — MacHuna's integrated Hula has far outstripped it in features.

### How it works in MacHuna

- A "Hula" button sits in the Batch Convert row, to the left of the "SWS Player" button
- Clicking it opens a `HulaWindow` -- a non-modal `tk.Toplevel` child window
- The window is self-contained: destination folder, output target, clip name, file picker, convert button, log
- Settings (`hula_dest`, `hula_target`, `hula_clip`) are persisted in the existing `~/.kwatch_settings.json` under `hula_` prefixed keys
- The shared settings dict `s` is passed by reference to `HulaWindow` so it can update settings in place; `save_settings` is passed as a callback

### Code structure in machuna.py

All Hula code lives in a clearly marked section just above `launch_gui()`:

- `HULA_TARGET_*` constants
- `_HULA_OFF_*` header offset constants (read side only -- no write side needed)
- `_HULA_STD_CODE_FPS` dict
- `HulaSWSHeader` class -- parses the 512-byte SWS header for reading
- `_hula_decode_frame()` -- decodes one frame pair using the existing `_v210_plane_to_yuv`, `_yuv_to_rgb8`, `_yuv_to_gray8` functions (no duplication)
- `_hula_extract_audio_stereo()` -- extracts Ch0+Ch2 from SWS 16ch PCM as stereo temp file
- `_hula_convert_tga()` -- converts one SWS to a TGA sequence subfolder
- `_hula_convert_mov()` -- converts one SWS to a ProRes 4444 MOV
- `_hula_run_batch()` -- batch dispatcher, called from worker thread
- `HulaWindow` class -- the tkinter GUI

### Output formats

| Target | Format | Naming |
|--------|--------|--------|
| Kayenne MOV | ProRes 4444, embedded alpha, BT.709, audio if present | `0001.mov`, `0002.mov` ... flat in dest |
| Kayenne TGA | 32-bit RGBA TGA | `0001.tga` onwards, subfolder per SWS |
| Sony MVS TGA | 32-bit RGBA TGA | `XXXX0000.tga` onwards (clip name prefix, then frame number), subfolder per SWS |

### Sony MVS interlaced TGA -- implemented in v1.5.20+

Interlaced TGA output was implemented in v1.5.20 via field-weaving (pairs of progressive frames interleaved by line). Available for all interlaced standards via the Standard dropdown. Field order toggle (BFF/TFF) present; BFF assumed for PAL/50Hz, unconfirmed on hardware.

### Standalone Hula repo

`DNSVision/Hula` is **archived and no longer maintained**. MacHuna's integrated Hula is the only active version. There is no sync obligation between the two — all future Hula development happens in `machuna.py` only.

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
| 720p/50 | `0x4923` | `0x10` | confirmed |
| 720p/59.94 | `0x4923` | `0x0f` | confirmed |

> **NOTE:** 0x18C values are not a flags field -- they are an index into the Kahuna's internal standard table. The simple 0x08=interlaced / 0x18=progressive theory was incorrect. Each standard has its own specific value which must be confirmed against K-Watch output.

> **UNVERIFIED STANDARDS:** 1080p/29.97, 1080p/30, and 2160p variants have been removed from the MacHuna dropdown pending verification. Do not add them back without confirmed K-Watch reference files. SD standards (625/50, 525/59.94) and sF (segmented frame) variants are supported by K-Watch but not implemented in MacHuna.

> **HOW TO VERIFY A NEW STANDARD:** Convert any file in K-Watch with the target standard selected. Run `xxd -l 512 output.SWS` and read offset 0x188 (4 bytes) and 0x18C (4 bytes). Both values are needed.

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

Both Stop (watch folder) and Cancel Batch call `_kill_current_ffmpeg()`. As of v1.5.12, all ffmpeg calls go through `_run_ffmpeg()` -- this includes audio extraction, TGA sequence conversion, and alpha extraction fallback paths which previously used `subprocess.run` directly. Stop/Cancel now works for all conversion paths. For rapid TGA floods, the watch folder scan thread may have already queued additional files before Stop is pressed -- those will still convert. This is an acceptable limitation for the current use case.

Note: killing ffmpeg mid-conversion raises `subprocess.CalledProcessError` with SIGKILL (returncode -9). The WatchService `_scan()` catches this as a general exception and logs it -- this is correct behaviour, not a bug.


ffmpeg outputs v210 as little-endian 32-bit words. The Kahuna expects big-endian. Every 4-byte word must be byte-swapped after conversion via _byteswap_v210().

### Colour Space
Fill plane must use -colorspace bt709 -color_range tv flags. Without these, luminance is ~80mV too high (confirmed on live Kahuna test).

### White Key Plane
When no alpha is present (or ignore alpha ticked), _generate_white_key() writes a solid white key plane. The repeating 8-byte pattern is: 20 01 02 00 04 08 00 40 -- confirmed by hex analysis of a real K-Watch file.

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
Implemented in v1.5.18. Field order TFF — consistent with SMPTE spec for 1080i HD, unconfirmed on a 1080i Kahuna setup. Tested on 1080P Kahuna only (see Hardware Test below).

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
- **Field order TFF unconfirmed** — cannot assess TFF vs BFF on a 1080P Kahuna. Needs test on a 1080i setup: wrong field order shows as motion going the wrong direction on moving content.

### To confirm field order
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
- TGA sequences: Handled via ffmpeg concat demuxer with a temporary concat file. Must use Watch Folder service -- not supported in Batch Convert file picker.
- Settings persistence: Stored as JSON in ~/.kwatch_settings.json. Hula settings stored in same file under hula_ prefixed keys.
- VERSION constant: Single `VERSION = "x.x.x"` constant near the top of machuna.py. Title bar and About box both read from it. Update this one line for each release.
- Format variant (0x18C): Stored in `FORMAT_VARIANTS` dict keyed by standard name, applied in `build_sws_header`. A companion `FORMAT_VARIANT_FPS` dict maps variant values back to fps -- used by `SWSHeader` and `HulaSWSHeader` for unambiguous fps lookup (all nine variant values are unique). The old simple interlaced/progressive logic (0x08/0x18) was replaced in v1.5.10 after v1.5.8 analysis confirmed each standard has its own specific value.
- Interlaced fps in SWSPlayer: `FORMAT_VARIANT_FPS` uses frame rates for interlaced standards (25/29.97/30fps), not field rates (50/59.94/60fps). Each SWS frame is a full 1920x1080 frame -- MacHuna does not separate fields. Confirmed on hardware (v1.5.14).
- SWSPlayer playback timing: `_playback_loop` sleeps to an absolute target time derived from a fixed origin (`t_origin + frame_num * frame_dur`). This prevents sleep overshoot in one frame from accumulating as drift across subsequent frames (v1.5.15).
- About box: Custom `tk.Toplevel` dialog. `tk::mac::ShowAbout` is silently overridden by PyInstaller's default panel, so an explicit menubar with `name='apple'` is created and the About item wired to our command instead. App icon loaded from `sys._MEIPASS` (bundled via `--add-data`) using Pillow; falls back to rocket emoji if image not found.
- White key plane: Written by _generate_white_key() when source has no alpha and ignore alpha is NOT ticked (i.e. a real fill+key file is expected). When ignore alpha IS ticked, no key plane is written at all -- header fields 0x1A8 and 0x1B4 are zeroed and the file contains fill only. Confirmed by live Kahuna test and hex analysis of K-Watch reference file.
- Batch convert ordering: Files sorted alphabetically. Manual reorder is a future feature.
- Batch convert scope: MOV, MP4, MXF, MKV, AVI, PNG, BMP, JPG only. TGA is excluded from the file picker (v1.5.16) -- TGA sequences must use the Watch Folder service, and single-frame TGA stills are an edge case not worth the ambiguity.
- Audio bit depth: 16-bit LE (not 24-bit). Confirmed by hex analysis of K-Watch reference files. Source MOV audio is passed through at native bit depth via ffmpeg -ac 16 upmix.
- Audio frame size header field (0x1C2) is always 0x1680 (5760) in MacHuna-generated files regardless of fps. Actual bytes per frame varies with fps but this header field does not. Note: third-party workflows may write a different value here -- K-Watch writes 0x3EC0 (16064) for 24fps content (confirmed by hex comparison of K-Watch and third-party SWS files generated from the same source MOV). The field appears to be an arbitrary constant rather than a meaningful bytes-per-frame value in either case. Do not rely on this field for audio detection -- use 0x1E8 and 0x1EC instead.
- Auto play / Loop play flags: Bits 2 (0x04) and 3 (0x08) of the low byte at 0x188, OR'd into the video standard code. Confirmed by hex analysis of K-Watch reference files across all four flag combinations. Both flags default to off.
- SWS Player audio detection: uses `aud_offset > 0 AND aud_fmt == 0x03000000` (fields 0x1E8 and 0x1EC) rather than checking `aud_frame_size == 0x1680` (0x1C2). Confirmed by analysis of a third-party SWS file where 0x1C2 was 0x3EC0 -- audio was present and correctly located but the player was reporting no audio. The 0x1C2 field varies between workflows and is not a reliable audio detection indicator.
- SWS Player integration: All player code lives in machuna.py above launch_gui(). Classes renamed to avoid any future collision: PlayerFrameCache, PlayerAudio. Decode functions prefixed _player_. The standalone sws_player.py repo (DNSVision/SWSPlayer) is now superseded for production use but retained as a reference. sounddevice is a gracefully-degraded dependency -- if not installed, HAS_AUDIO is False and the player opens without audio playback (meters still drawn, no sound).
- Hula integration: All Hula code lives in machuna.py in a clearly marked section just above launch_gui(). Classes and functions prefixed Hula/hula_ to avoid collision. The v210 decoder functions (_v210_plane_to_yuv, _yuv_to_rgb8, _yuv_to_gray8) are shared -- Hula reuses them directly without duplication.
- tkinter top-level import: tk, ttk, filedialog, messagebox, scrolledtext are now imported at module level (guarded with try/except) so the SWSPlayer and HulaWindow classes can reference tk.Toplevel at definition time. launch_gui() still has its own internal imports which are harmless re-imports.

---

## File Structure

```
~/Developer/MacHuna/
├── machuna.py              # Main application source
├── machuna.icns            # App icon (Apple icon format)
├── machuna_final_1024.png  # Source icon image (1024x1024px)
├── Audio Spec.pdf          # Early audio format notes -- superseded, see notes above
├── README.md               # Public-facing repository readme
├── DEVELOPMENT_NOTES.md    # This file
└── .gitignore              # Excludes build/, dist/, *.spec etc.
```
