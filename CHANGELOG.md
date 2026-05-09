# Changelog — MacHuna

All notable changes to MacHuna are documented here.

---

## v1.5.9 — 2026-05-09

### Changed
- Video standards dropdown now shows only confirmed standards. Unverified standards (1080p29.97, 1080p30, 2160p variants) removed pending verification against K-Watch reference files.

---

## v1.5.8 — 2026-05-09

### Fixed
- Video standard codes (0x188) and format variant values (0x18C) fully confirmed by hex analysis of K-Watch reference files for all nine supported standards. Previous values for 1080i59.94, 1080i60, 1080p25, 1080p59.94, 1080p60, 720p50, and 720p59.94 were estimated and have now been replaced with confirmed values.
- 1080i/59.94 correctly uses standard code 0xc923 (not 0x4923) -- the 0x8000 bit appears to flag drop-frame timing.
- Format variant field (0x18C) is now a full confirmed lookup table rather than a simple interlaced/progressive flag.

### Added
- Progressive-to-interlaced mismatch warning. When an interlaced output standard is selected but the source file is detected as progressive, MacHuna logs a clear warning explaining that the video data will remain progressive and will play back at double speed on the Kahuna. Recommends using a native interlaced source or K-Watch for correct interlaced output.
- Interlaced source detection via ffprobe `field_order` field added to `get_video_info()`.

---

## v1.5.7 — 2026-05-08

### Fixed
- Stop button now kills the currently running ffmpeg process immediately, rather than waiting for the current file to complete. Effective for long MOV conversions; for rapid TGA floods the watch folder scan thread may have already queued additional files which will still complete.

### Added
- Cancel Batch button added to the main button row. Disabled by default, enables automatically when a batch conversion starts via Open Files. Kills the current ffmpeg process and stops after the current file. Conversion log is not written if the batch is cancelled.

---

## v1.5.5 — 2026-05-08

### Fixed
- Format variant field at header offset 0x18C now correctly set to 0x08 for interlaced standards (1080i50, 1080i5994, 1080i60) and 0x18 for progressive standards. Previously hardcoded to 0x18 regardless of standard, causing interlaced files to be identified as progressive on the Kahuna desk. Confirmed by hex analysis of K-Watch reference files.

---

## v1.5.4 — 2026-05-07

### Fixed
- Default window size set to 1121x592, matching a well-proportioned layout on a MacBook Air display. Window size is persisted between sessions -- MacHuna remembers the last size you set.

---

## v1.5.3 — 2026-05-07

### Fixed
- Interim window size adjustment (superseded by v1.5.4).

---

## v1.5.2 — 2026-05-07

### Fixed
- Window no longer opens too narrow on first launch, hiding the Settings checkboxes. Minimum window width set to 960px. Window size persisted to settings on quit and restored on next launch.

---

## v1.5.1 — 2026-05-07

### Fixed
- Sony MVS TGA naming convention corrected: clip name now prefixes the frame number (e.g. `WIPE0000.tga`) rather than following it. This matches the actual Sony MVS import behaviour confirmed from real-world TGA sequences.

---

## v1.5.0 — 2026-05-07

### Added
- **Hula SWS Extractor** integrated as a built-in tool. A Hula button in the Batch Convert row opens a non-modal window for converting .SWS files back to Kayenne MOV, Kayenne TGA, or Sony MVS TGA format. Settings persisted under `hula_` prefixed keys in `~/.kwatch_settings.json`.

---

## v1.4.1 — 2026-05-07

### Fixed
- SWS Player audio detection now uses `aud_offset` (0x1E8) and `aud_fmt` (0x1EC) fields rather than `aud_frame_size` (0x1C2). Fixes audio not being detected in third-party SWS files where the frame size field carries a non-standard value (e.g. 0x3EC0 rather than 0x1680).

---

## v1.4.0 — 2026-05-07

### Added
- **SWS Preview Player** integrated as a built-in tool. An SWS Player button in the Batch Convert row opens a non-modal quad-display player (fill, key, composite, audio meters) with transport controls. Multiple player windows can be open simultaneously.

---

## v1.3.0

### Added
- **Large file support.** Files larger than 4GB are automatically split into 2GB FAT32-safe chunks matching the K-Watch split file format exactly. Confirmed working on a live Grass Valley Kahuna mainframe.

### Fixed
- `build_sws_header()` uint32 overflow for files >4GB — 0x1CC field now capped at 0xFFFFFFFF and patched correctly by `_write_sws_split()`.

---

## v1.2.1

### Added
- A conversion log (.txt) is written to the destination folder after each batch convert operation.

---

## v1.2.0

### Added
- **Batch Convert** section with file picker (Open Files button), start number field, and alphabetical ordering. Converts MOV, MP4, and still image files without requiring the Watch Folder service.

---

## v1.1.0

### Added
- **Audio support.** 16-bit LE PCM, 16 channels, 48kHz. Correct K-Watch channel mapping (L=Ch1, R=Ch3) confirmed by hex analysis of K-Watch reference files. Include audio checkbox added to GUI (default: on). Confirmed working on live Kahuna.
- **Auto play / Loop play flags.** Bits 2 (0x04) and 3 (0x08) of the video standard code at 0x188, confirmed by hex analysis across all four flag combinations. Both checkboxes added to GUI (default: off).
- **Ignore alpha/key option.** When ticked, no key plane is written and header fields 0x1A8 and 0x1B4 are zeroed, matching K-Watch no-alpha behaviour. Confirmed by live Kahuna test.

---

## v1.0.0

### Initial release
- Watch folder service monitoring for incoming media files
- Converts MOV, MP4, MXF, MKV, AVI, TGA sequences, and still images to .SWS
- Fill and key planes encoded as v210 big-endian
- BT.709 colour space with limited range (confirmed correct luminance on live Kahuna)
- Supports 1080i50, 1080i29.97, 1080p25, 1080p50, 720p50, 720p59.94
- Settings persisted to `~/.kwatch_settings.json`
- SWS format reverse-engineered from K-Watch reference files and verified on a live Grass Valley Kahuna mainframe
