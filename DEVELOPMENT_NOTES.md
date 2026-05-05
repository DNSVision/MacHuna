# MacHuna — Development Notes

This document is for continuity between development sessions. If starting a new Claude session, point Claude at this file and the main machuna.py source and development can resume from where it left off.

---

## Project Summary

MacHuna is a macOS watch folder application that converts video and still image files to the Grass Valley Kahuna `.SWS` native format. It was built collaboratively between David Steer (DNS Vision Limited) and Claude (Anthropic) with no prior coding experience on David's part.

**Current version:** v1.1.1
**Status:** Alpha tested on a live Grass Valley Kahuna mainframe. Core conversion working correctly. Batch convert added and tested. Audio support implemented and verified by hex comparison against MacHuna output -- awaiting live Kahuna test. v1.1.1 fixes: Clear Log button added, settings now save correctly on Cmd+Q, start_num_var UnboundLocalError on launch fixed. VERSION constant added, title bar and About box now read from it automatically.
**Repository:** https://github.com/DNSVision/MacHuna
**Dev machine:** MacBook Air M1 (all dev and building must happen here)

---

## Development Environment

- **Python:** 3.12
- **Key libraries:** Pillow, numpy, tkinter (built-in), subprocess, struct, watchdog, tkinterdnd2-universal (installed but currently disabled)
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
2. ~~**Ignore alpha/key option**~~ -- DONE. Checkbox in GUI. When ticked, alpha is ignored and a solid white key plane is written matching K-Watch behaviour exactly (confirmed by hex analysis).
3. ~~**Batch convert with file picker**~~ -- DONE. Batch Convert section in GUI with start number field, Open Files button, alphabetical ordering, auto-incrementing numbers, and conversion log text file written to destination folder after each batch.
4. ~~**TGA sequence hint in Batch Convert**~~ -- DONE. Grey label added to Batch Convert section: "For TGA sequences, use the Watch Folder service above." Batch convert (Open Files) is for MOVs and single-frame stills only.
5. ~~**Audio support**~~ -- DONE. extract_audio() extracts 16-bit LE PCM, upmixes to 16 channels at 48kHz, pads to exact frame alignment. Header fields 0x1C2, 0x1E8, 0x1EC, 0x1CC updated correctly. "Include audio" checkbox added to GUI (default: on). Verified by hex comparison against MacHuna-generated SWS -- file size and audio section exact match. Awaiting live Kahuna test.
6. **Split large files (>4GB)** -- Format now fully reverse-engineered from real K-Watch split files (see Split File Format section below). Ready to implement. Needs Kahuna and a large file to verify output. Do not implement until audio Kahuna test is complete.
7. **SWS to MOV conversion** -- Reverse conversion. All format knowledge in place. No Kahuna needed to verify.
8. **Manual reorder in batch convert** -- Parked. Currently files are sorted alphabetically. Drag-to-reorder list is a future feature.
9. **Standalone preview viewer** -- Fill, key and audio preview with audio meters. Most complex item.
10. **Integrate preview into main app** -- Follows naturally from item 9.

### Future Considerations
- HLG Rec.2020 colour space option (header field 0x188 needs a different value -- requires a real HLG SWS to hex dump and verify)
- True drag and drop (currently disabled -- see drag and drop note below)
- Cloud/networked version

---

## Drag and Drop Status

`tkinterdnd2-universal` is installed but HAS_DND is hardcoded to False in the script. The native tkdnd library is incompatible with Homebrew Python 3.12 on Apple Silicon -- crashes with "cannot find symbol tkdnd_Init".

The drag and drop code is fully written in on_drop() and will work once the library issue is resolved. Options to fix:
- Install Python from python.org (official installer) instead of Homebrew
- Build tkdnd from source against Homebrew's Tk

For now, the Open Files button in the Batch Convert section provides equivalent functionality for MOVs and single-frame stills. TGA sequences must use the Watch Folder service.

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
| 0x188 | uint32 | Video standard code |
| 0x18C | uint32 | FPS numerator |
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

### Video Standard Codes (offset 0x188)

| Code | Standard |
|------|----------|
| 0x00004923 | 1080i25, 1080p50 |
| 0x00004921 | 1080i29.97 |
| 0x00004925 | 1080p25 |
| 0x00004817 | 720p50 |
| 0x00004816 | 720p59.94 |

### v210 Encoding
ffmpeg outputs v210 as little-endian 32-bit words. The Kahuna expects big-endian. Every 4-byte word must be byte-swapped after conversion via _byteswap_v210().

### Colour Space
Fill plane must use -colorspace bt709 -color_range tv flags. Without these, luminance is ~80mV too high (confirmed on live Kahuna test).

### White Key Plane
When no alpha is present (or ignore alpha ticked), _generate_white_key() writes a solid white key plane. The repeating 8-byte pattern is: 20 01 02 00 04 08 00 40 -- confirmed by hex analysis of a real K-Watch file.

---

## Split File Format (>4GB)

Fully reverse-engineered from a real K-Watch split file (3-chunk example, 1080i25, 1000 frames).

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
Not observed in the reference file and almost certainly not supported given the file sizes involved. Do not implement audio for split files.

### Implementation notes
- The existing _write_sws_split() function has a skeleton but the header logic is wrong -- it needs updating to match the above
- The 0x1CC field containing the final chunk size rather than total size is confirmed by hex analysis
- Play count (0x1A8) and 0x1B4 are both zeroed in split files -- confirmed
- Test by generating a >4GB file on the M1 and loading onto a Kahuna

---

## Audio Format (confirmed by hex analysis of K-Watch and MacHuna output)

- Audio appended after key plane
- **16-bit signed little-endian PCM** (not 24-bit -- matches common MOV source format)
- **16 channels interleaved** -- source channels padded to 16 with silence
- **48,000 Hz sample rate**
- Samples per frame = 48000 / fps (e.g. 960 at 50fps, 1920 at 25fps)
- Bytes per frame = samples_per_frame x 2 x 16
- Audio frame size header field (0x1C2) is always 0x1680 (5760) regardless of fps -- fixed value
- Audio data offset = 512 + plane_size x frame_count x 2
- ffmpeg extraction: -acodec pcm_s16le -ar 48000 -ac 16 -f s16le
- TGA sequence audio is out of scope

Note: The Audio Spec.pdf was written before full hex analysis and incorrectly states 24-bit PCM. The actual format is 16-bit. The spec PDF can be disregarded -- the implementation in extract_audio() is correct.

---

## Known Issues

### Large File Split (>4GB)
Format fully reverse-engineered (see Split File Format section). Implementation straightforward but not yet done. Do not implement until audio Kahuna test is confirmed working.

### Video plane differences between machines
MacHuna-generated v210 video data differs byte-for-byte from K-Watch output and between different machines running MacHuna. This is normal -- ffmpeg produces slightly different v210 encoding on different hardware/versions. The Kahuna accepted MacHuna output correctly on live test. This is not a bug.

---

## Technical Decisions

- onedir vs onefile: Must use --onedir. The --onefile + --windowed combination causes ffmpeg binaries to not bundle correctly on macOS.
- ffmpeg path: Must point to real binary not Homebrew symlink (/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffmpeg). Symlinks confuse PyInstaller.
- sys.frozen check: _get_ffmpeg_path() checks sys.frozen to find bundled ffmpeg when running as .app.
- TGA sequences: Handled via ffmpeg concat demuxer with a temporary concat file. Must use Watch Folder service -- not supported in Batch Convert file picker.
- Settings persistence: Stored as JSON in ~/.kwatch_settings.json.
- VERSION constant: Single `VERSION = "1.1.1"` constant near the top of machuna.py. Title bar and About box both read from it. Update this one line for each release.
- About box: Custom `tk.Toplevel` dialog. `tk::mac::ShowAbout` is silently overridden by PyInstaller's default panel, so an explicit menubar with `name='apple'` is created and the About item wired to our command instead. App icon loaded from `sys._MEIPASS` (bundled via `--add-data`) using Pillow; falls back to rocket emoji if image not found.
- White key plane: Written by _generate_white_key() whenever no alpha present, matching K-Watch exactly.
- Batch convert ordering: Files sorted alphabetically. Manual reorder is a future feature.
- Batch convert scope: MOVs and single-frame stills only. TGA sequences require the Watch Folder service.
- Audio bit depth: 16-bit LE (not 24-bit). Confirmed by hex analysis of K-Watch reference files. Source MOV audio is passed through at native bit depth via ffmpeg -ac 16 upmix.
- Audio frame size header field (0x1C2): Fixed value 0x1680 (5760) regardless of fps. Actual bytes per frame varies with fps but this header field does not.

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
