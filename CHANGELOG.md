# Changelog — MacHuna

All notable changes to MacHuna are documented here.

---

## v1.5.31 — 2026-05-11

### Fixed
- **Hula: interlaced SWS → interlaced TGA target was incorrectly rejected.** When an interlaced SWS (e.g. 1080i/50, 25fps) was loaded into Hula with an interlaced standard selected, the batch runner sent it to `_hula_convert_tga_interlaced`, which immediately rejected it because 25fps < 48fps guard. The correct behaviour for an interlaced source + interlaced target is a straight frame dump (the frames are already woven). Fix: the batch runner now reads the source header fps first; sources below 48fps are passed to `_hula_convert_tga` with a log message advising the user to tick "TGA source already interlaced" when re-importing into Watch Folder.
- **Hula: Kayenne MOV encoder could not be cancelled.** `_hula_convert_mov` was calling `subprocess.run` directly, bypassing the `_run_ffmpeg` wrapper. Stop/Cancel had no way to kill the ffmpeg process mid-encode. Fixed: now calls `_run_ffmpeg(cmd, check=True)`.

---

## v1.5.30 — 2026-05-10

### Fixed
- **Interlaced→progressive conversion played at double speed (or faster).** When converting a 1080i/50 MOV to any progressive standard (1080p/50, 1080p/60, 720p/50 etc.), ffmpeg was passing through the source's 25 interlaced frames without deinterlacing. The SWS format variant tells the Kahuna (and SWSPlayer) to play at 50fps, so 25 frames played in half the expected time — double speed. Fix: MacHuna now detects interlaced→progressive conversions (`is_interlaced` source + progressive target), applies `yadif=mode=send_field` (bob deinterlace) to produce one output frame per input field, then resamples to the exact target fps. Frame count and audio timing are now both correct.
- **TGA sequence → interlaced standard played at double speed when source frames were already interlaced.** When TGA files extracted from an existing 1080i/50 SWS were re-wrapped targeting 1080i/50, MacHuna incorrectly applied `tinterlace`, treating each TGA as a progressive frame and pairing them up — halving the frame count and causing double-speed playback. Fix: a new **"TGA source already interlaced"** checkbox in the options row tells MacHuna to skip `tinterlace` and pass the frames through directly. Leave unticked for progressive animations/graphics that need genuine interlace conversion.

---

## v1.5.29 — 2026-05-10

### Added
- **Single batch log for Watch Folder TGA conversions.** When a set of TGA sequences is processed via the Watch Folder, MacHuna now waits until all sequences in the batch are complete before writing one combined log file (e.g. `MacHuna_Log_10-05-2026.txt`) listing every slot, sequence name, and status. Previously a separate log was written per sequence.
- **Watch Folder auto-stops after TGA batch completes.** Once all detected TGA sequences have been converted and no new TGA files arrive in the next scan cycle, the Watch service stops itself automatically and logs "Batch complete — watch stopped automatically."

---

## v1.5.28 — 2026-05-10

### Fixed
- **SWS Player crash when opening or playing a second audio file (heap corruption).** Closing a PortAudio stream from the main thread while the audio thread was inside `write()` corrupted PortAudio's internal C buffers. The corruption was then detected by `libsystem_malloc` when CoreGraphics tried to allocate memory (typically when the Open file dialog was shown), causing a `SIGTRAP / memory corruption of free block` crash. Fix: `stop()` no longer touches the stream at all — it sets the stop event, joins the audio thread (which exits within one write-chunk, ~100ms), then clears the reference. The audio thread's own `finally` block closes the stream safely from the thread that owns it. `_play()` also now checks the stop event after its 50ms pre-start sleep so it won't open a stream that is already being torn down.

---

## v1.5.27 — 2026-05-10

### Added
- **SWS Player now accepts TGA sequences and video files.** The "Open SWS..." button is now "Open..." and accepts `.SWS`, `.TGA` (picks the whole sequence from whichever frame you select), `.MOV`, `.MP4`, `.MXF`, `.MKV`, and `.AVI`. TGA sequences prompt for frame rate (23.976 / 25 / 29.97 / 30 / 50 / 59.94 / 60) before loading. Fill, Key, and Composite panels work for all formats; audio meters work for video files.
- MOV/video files with an alpha channel (e.g. ProRes 4444) correctly populate the Key and Composite panels. Alpha is detected via the source pixel format (`yuva*`, `rgba`, etc.).
- Audio extracted from video files is converted to the player's 16-channel PCM format (L→ch0, R→ch2) so the audio meters are active.

### Known issue
- SWS Player crashes when opening a second MOV/video file in the same session. SWS and TGA are unaffected. Fix scheduled for next session — suspected threading conflict between the audio extraction subprocess and the display reset on second open.

---

## v1.5.26 — 2026-05-10

### Added
- **Batch Convert confirmation dialog.** Clicking Open Files now shows a "Convert N file(s) starting at slot X?" prompt before conversion begins. Uses a custom `_ask_confirm` Toplevel to avoid the macOS app icon that appears in standard `messagebox` dialogs.

---

## v1.5.25 — 2026-05-10

### Added
- **Slot override** field in the Settings row. Set to any number to override the SWS slot derived from the TGA filename; subsequent sequences auto-increment from there. Defaults to 0 (use filename) and resets to 0 on every launch.

### Changed
- Settings row split into two lines — standard/slot override on row 1, conversion options (Split, Delete, Ignore alpha, Include audio, Auto play, Loop play) on row 2.
- Hula and SWS Player buttons in the Batch Convert row now always visible regardless of window width (packing order fixed).
- Default window size updated to 960×460 to better fit the new two-row settings layout.
- Batch Convert hint text shortened to "MOV, MP4, MXF, PNG, BMP, JPG only. TGA → Watch Folder."
- Fixed misleading "plays at double speed" warning in `convert_still` — a single still stored progressive in an interlaced wrapper is normal for graphics.

---

## v1.5.24 — 2026-05-10

### Fixed
- **TGA sequence P→I conversion was broken.** When converting a progressive TGA sequence to an interlaced standard (1080i50/59.94/60), two bugs were present: (1) no `tinterlace` filter was applied, so all 50 progressive frames were stored as-is in an interlaced SWS; (2) the frame count was not halved, so the SWS stored 50 frames at 25fps and played back at half speed. Both paths (fill and alpha/key) now apply `tinterlace=mode=interleave_top`, and the output frame count is derived from the actual file size after ffmpeg runs — matching the fix already in place for the MOV conversion path.

---

## v1.5.23 — 2026-05-10

### Added
- **Open in Finder** button added to the Watch Folder row, Destination Folder row, and Hula Destination Folder row. Opens the folder directly in Finder with one click — makes it practical to store folders anywhere on the machine without needing to remember their location. Warns if the folder is not set or does not exist.

---

## v1.5.22 — 2026-05-10

### Changed
- **Hula GUI redesigned:** Output target consolidated to three options — **Kayenne MOV**, **Kayenne TGA**, **Sony TGA**. When a TGA target is selected, a **Standard** dropdown (matching the main MacHuna standard picker — 1080i50, 1080p50, 720p50, etc.) appears. Interlaced standards trigger field-weaving automatically; progressive standards extract frames directly. Field order (BFF/TFF) shows only when an interlaced standard is selected. This replaces the old fixed "Sony MVS 25i" and "Sony MVS 50p" radio buttons.
- **Hula now accepts MOV input** as well as SWS. The file picker accepts `.sws` and `.mov`. MOV → TGA uses ffmpeg frame extraction (progressive) or PIL field-weaving (interlaced), matching the SWS path. MOV input is not valid for the Kayenne MOV target.
- `_hula_convert_tga_25i` renamed to `_hula_convert_tga_interlaced` and updated to support both Kayenne TGA and Sony TGA naming conventions.
- `_hula_run_batch` renamed `sws_paths` parameter to `input_paths` and added `standard` parameter (replaces `fmt`).
- Window title updated to "Hula — SWS / MOV Extractor".

### Added
- New `_hula_convert_mov_to_tga()` function handles MOV → TGA for all supported standards and both targets.
- `hula_standard` and `hula_field_order` now persisted in saved settings.

### Notes
- **Kayenne TGA output parameters are UNCONFIRMED** pending hardware verification. Contact engineering to confirm before relying on Kayenne TGA output in production.

---

## v1.5.21 — 2026-05-09

### Added
- Hula Sony MVS 25i: source guard rejects non-1080p50 files before converting, with a clear error message naming the file and its actual standard. Prevents silently producing bad output when the wrong SWS is loaded.

---

## v1.5.20 — 2026-05-09

### Added
- Hula: Sony MVS TGA target split into two options — **Sony MVS TGA (50p)** (straight progressive, existing behaviour) and **Sony MVS TGA (25i)** (new field-woven interlaced output for older MVS desks that don't support 50P).
- Sony MVS TGA (25i) weaves pairs of consecutive 50P frames into interlaced frames via numpy line-interleaving, halving the frame count. Includes a **BFF/TFF field order toggle** (defaults to BFF, typical for PAL/50Hz Sony MVS desks). Field order can be flipped on-site if motion artefacts appear.

---

## v1.5.19 — 2026-05-09

### Changed
- SWS Player and Hula file list now display compact broadcast-style metadata: standard (e.g. `1080i50`), frame count (e.g. `30frms`), and wall-clock duration (e.g. `1.20s`). Replaces the previous `width×height  fps  frames` format.
- Duration display omits leading zero sections — clips under a minute show seconds only (`1.20s`), longer clips show `MM:SS.xxs` or `HH:MM:SS.xxs`.
- SWS Player standard name now derived from the format variant byte (same as Hula), ensuring consistent labelling across both tools.

---

## v1.5.18 — 2026-05-09

### Added
- Progressive-to-interlaced transcoding. When a progressive source is converted to an interlaced standard (1080i/50, 1080i/59.94, 1080i/60), MacHuna now weaves pairs of progressive frames into genuine interlaced frames using the ffmpeg `tinterlace=mode=interleave_top` filter. Frame count halves (e.g. 60 frames at 50fps → 30 frames at 25fps for 1080i/50). Field order is Top Field First (TFF) — SMPTE standard for 1080i HD — pending hardware confirmation on a live Kahuna. The previous "source is progressive" warning is replaced with a log message describing the transcode.

---

## v1.5.17 — 2026-05-09

### Fixed
- Standard code (0x188) for all interlaced standards corrected to `0xc923`. The 0x8000 bit flags interlaced scanning, not drop-frame timing as previously assumed. Previously, 1080i/50 and 1080i/60 were written with `0x4923` (progressive code); K-Watch reference files confirm all three interlaced standards use `0xc923`. The Kahuna was tolerating the wrong value because it uses the format variant field (0x18C) as the primary standard discriminator, but MacHuna output now matches K-Watch exactly. Confirmed by hex analysis of a K-Watch P→I transcode (1080p/50 MOV → 1080i/50 SWS).

---

## v1.5.16 — 2026-05-09

### Changed
- TGA files removed from the Batch Convert file picker. Batch Convert handles MOV, MP4, MXF, MKV, AVI, PNG, BMP, and JPG only. TGA sequences must use the Watch Folder service. A hint label in the Batch Convert row makes this explicit.

---

## v1.5.15 — 2026-05-09

### Fixed
- SWS Player playback loop now uses absolute timing to prevent frame jitter. Previously, any sleep overshoot in one frame carried into the next and accumulated. The loop now calculates sleep relative to an absolute start time so drift self-corrects each frame.

---

## v1.5.14 — 2026-05-09

### Fixed
- SWS Player now plays interlaced files at the correct speed. 1080i/50, 1080i/59.94, and 1080i/60 were playing at double speed because the fps lookup was returning the field rate (50/59.94/60) rather than the frame rate (25/29.97/30). Each stored SWS frame is a full frame, not a field.

---

## v1.5.13 — 2026-05-09

### Fixed
- SWS Player and Hula now determine fps by reading the format variant field (0x18C) rather than the standard code (0x188). Since eight standards share the same standard code (0x4923), the old lookup returned 50fps for everything including 1080p/25 (should be 25fps) and 60fps standards (should be 60fps). The format variant values are all unique so the new lookup is unambiguous. The standard code lookup is retained as a fallback for third-party files.

---

## v1.5.12 — 2026-05-09

### Fixed
- Stop and Cancel Batch now correctly kill ffmpeg during audio extraction, TGA sequence conversion, and alpha extraction fallback. These paths were using `subprocess.run` directly instead of the `_run_ffmpeg` wrapper, making them invisible to the kill mechanism introduced in v1.5.7.

---

## v1.5.11 — 2026-05-09

### Fixed
- `convert_tga_sequence`: Ignore alpha/key option now correctly omits the key plane entirely when ticked, matching the behaviour of `convert_still` and `convert_clip`. Previously, ticking Ignore alpha on a TGA sequence would still generate a white key plane. Header fields 0x1A8 and 0x1B4 are now correctly zeroed when no key plane is written.

---

## v1.5.10 — 2026-05-09

### Fixed
- Format variant field (0x18C) now uses a confirmed per-standard lookup table (`FORMAT_VARIANTS`) instead of the simple interlaced/progressive logic from v1.5.5. The v1.5.8 analysis had confirmed the correct values for all nine standards but the code was not updated at that time. Standards affected: 1080i/59.94 (0x05), 1080i/60 (0x04), 1080p/25 (0x13), 1080p/59.94 (0x17), 1080p/60 (0x16), 720p/50 (0x10), 720p/59.94 (0x0f). Values for 1080i/50 (0x08) and 1080p/50 (0x18) were already correct.

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
