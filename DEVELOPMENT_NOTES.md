# MacHuna — Development Notes

This document is for continuity between development sessions. If starting a new Claude session, point Claude at this file and the main machuna.py source and development can resume from where it left off.

---

## Project Summary

MacHuna is a macOS watch folder application that converts video and still image files to the Grass Valley Kahuna `.SWS` native format. It was built collaboratively between David Steer (DNS Vision Limited) and Claude (Anthropic) with no prior coding experience on David's part.

The project started as a Python script and has been packaged as a standalone macOS .app bundle using PyInstaller.

**Current version:** v1.0  
**Status:** Alpha tested on a live Grass Valley Kahuna mainframe. Core conversion working correctly.  
**Repository:** https://github.com/DNSVision/MacHuna  
**Dev machine:** MacBook Air M1 (this is important -- all dev and building must happen here as dependencies are installed here)

---

## Development Environment

- **Python:** 3.12
- **Key libraries:** Pillow, numpy, tkinter (built-in), subprocess, struct, watchdog
- **ffmpeg:** Installed via Homebrew at `/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/`
- **PyInstaller:** Installed via pip3.12
- **Working directory:** `~/Developer/MacHuna/`
- **Main script:** `machuna.py`

### Build Command

```bash
python3.12 -m PyInstaller \
  --onedir \
  --windowed \
  --name "MacHuna" \
  --icon ~/Developer/MacHuna/machuna.icns \
  --add-binary "/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffmpeg:." \
  --add-binary "/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffprobe:." \
  --noconfirm \
  ~/Developer/MacHuna/machuna.py
```

Built .app appears in `~/dist/MacHuna/MacHuna.app`. Right-click > Open first time to bypass Gatekeeper.

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
2. **Ignore alpha/key option** -- Quick win. Add checkbox to GUI to ignore embedded alpha channel. No Kahuna needed to test.
3. **Drag and drop into watch window** -- Quick win. Allow files to be dragged directly into the app rather than using watch folder only.
4. **Audio support** -- Format fully reverse-engineered and documented in `Audio Spec.pdf`. Needs Kahuna to verify. See audio section below.
5. **Split large files (>4GB)** -- Code crashes currently with overflow error on files that would produce >4GB output. Needs Kahuna and a large file to test properly. See known issues below.
6. **SWS to MOV conversion** -- Reverse conversion. All format knowledge already in place. No Kahuna needed to verify (output can be checked in any video player).
7. **Standalone preview viewer** -- Fill, key and audio preview with audio meters. Most complex item.
8. **Integrate preview into main app** -- Follows naturally from item 7.

### Future Considerations
- HLG Rec.2020 colour space option (header field 0x188 would need a different value -- requires a real HLG SWS to hex dump and verify)
- Cloud/networked version

---

## SWS Format — Technical Reference

### File Layout
```
[0x000 - 0x1FF]  512-byte header
[0x200 - N]      Fill plane  (plane_size × frame_count bytes, v210 big-endian)
[N - M]          Key plane   (plane_size × frame_count bytes, v210 big-endian)
[M - EOF]        Audio data  (if present -- see Audio Spec.pdf)
```

### Key Header Fields (all big-endian)

| Offset | Size | Description |
|--------|------|-------------|
| `0x000` | 16 bytes | Magic: `S&W Kahuna Still` |
| `0x020` | string | Source filename |
| `0x100` | string | Clip name |
| `0x148` | string | Creation timestamp |
| `0x168` | string | Modified timestamp |
| `0x188` | uint32 | Video standard code (see below) |
| `0x18C` | uint32 | FPS numerator |
| `0x190` | uint32 | Width in pixels |
| `0x194` | uint32 | Height in pixels |
| `0x198` | uint32 | Height again (confirmed) |
| `0x19C` | uint32 | Header size = 512 (0x200) |
| `0x1A0` | uint32 | Plane size (bytes per frame) |
| `0x1A4` | uint32 | Frame count |
| `0x1A8` | uint32 | Play count (= frame count) |
| `0x1B0` | float32 | Play rate (1.0) |
| `0x1B4` | uint32 | (plane_size × frame_count + header_size) ÷ 32 |
| `0x1C2` | uint16 | Audio frame size (0 if no audio) |
| `0x1CC` | uint32 | Total file size |
| `0x1E8` | uint32 | Audio data offset ÷ 32 (0 if no audio) |
| `0x1EC` | uint32 | Audio format flag: `0x03000000` (0 if no audio) |

### Video Standard Codes (offset 0x188)

| Code | Standard |
|------|----------|
| `0x00004923` | 1080i25 |
| `0x00004921` | 1080i29.97 |
| `0x00004925` | 1080p25 |
| `0x00004918` | 1080p50 |
| `0x00004817` | 720p50 |
| `0x00004816` | 720p59.94 |

### v210 Encoding
ffmpeg outputs v210 as little-endian 32-bit words. The Kahuna expects big-endian 32-bit words. Every 4-byte word must be byte-swapped after conversion. This is handled by `_byteswap_v210()` in the script.

### Colour Space
Fill plane must use `-colorspace bt709 -color_range tv` flags in the ffmpeg command. Without these, luminance is approximately 80mV too high (confirmed on live Kahuna test).

---

## Audio Format (v1.1 target)

Fully documented in `Audio Spec.pdf` in this repository. Summary:

- Audio appended after key plane
- 48kHz, 24-bit PCM, 16 channels (8 stereo pairs)
- 5,760 bytes per frame per channel (at 25fps)
- Header fields `0x1C2`, `0x1E8`, `0x1EC` and `0x1CC` need updating
- ffmpeg extraction command: `-acodec pcm_s24le -ar 48000 -ac 16 -f s24le`
- For 50fps: audio_frame_size = 2,880 bytes (960 samples × 3 bytes)

---

## Known Issues

### Large File Split (>4GB)
Files that would produce an SWS larger than 4GB crash with:
```
struct.error: 'I' format requires 0 <= number <= 4294967295
```
This is in `build_sws_header()` at offset `0x1CC` where `total_size` overflows a uint32.

From hex analysis of a real K-Watch split file:
- Only the first chunk has the 512-byte header
- Subsequent chunks are raw video data with no header
- Chunk size is exactly 2GB (2,147,483,648 bytes)
- Naming convention: `01_OF_03._XX`, `02_OF_03._XX` etc.
- The value at `0x1CC` in split files is not yet fully understood -- needs further analysis

**Do not fix until near a Kahuna with a large file to test.**

---

## Technical Decisions

- **onedir vs onefile PyInstaller:** Must use `--onedir`. The `--onefile` + `--windowed` combination causes ffmpeg binaries to not be bundled correctly on macOS.
- **ffmpeg path:** Must point to the real binary, not the Homebrew symlink (`/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffmpeg` not `/opt/homebrew/bin/ffmpeg`). Symlinks confuse PyInstaller.
- **sys.frozen check:** `_get_ffmpeg_path()` checks `sys.frozen` to find bundled ffmpeg when running as .app, falls back to system PATH when running as script.
- **TGA sequences:** Handled via ffmpeg concat demuxer. A temporary concat file is written listing all TGA frames.
- **Settings persistence:** Stored via Python `shelve` module in the user's home directory.

---

## File Structure

```
~/Developer/MacHuna/
├── machuna.py              # Main application source
├── machuna.icns            # App icon (Apple icon format)
├── machuna_final_1024.png  # Source icon image (1024x1024px)
├── Audio Spec.pdf          # Audio format reverse-engineering notes
├── README.md               # Public-facing repository readme
├── DEVELOPMENT_NOTES.md    # This file
└── .gitignore              # Excludes build/, dist/, *.spec etc.
```
