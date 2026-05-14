# MacHuna

A macOS application for converting video and still image files to the Grass Valley Kahuna `.SWS` native format, with built-in SWS preview and extraction tools.

## Overview

MacHuna is a Mac-native alternative to the Windows-only K-Watch application included with Grass Valley K-Manager Pro. It converts video, TGA sequences, and still image files to `.SWS` format for use with Grass Valley Kahuna vision mixers, and also extracts `.SWS` files back to standard formats for use on other vision mixing desks.

Converted files are placed into a destination folder, ready to be loaded onto a Kahuna mainframe via USB or network transfer.

## Features

- Converts MOV, MP4, MXF, MKV, AVI and other ffmpeg-supported formats to `.SWS` (K-Watch supports MOV and AVI only)
- Converts TGA sequences to `.SWS` clips — any naming convention (K-Watch, After Effects, custom renders); K-Watch naming is not required
- Converts still images (PNG, TGA, BMP, JPG etc.) to `.SWS` stills
- Extracts `.SWS` files to Kayenne MOV, Kayenne TGA, or Sony TGA format
- Fill and key (alpha) planes correctly encoded as v210 big-endian
- Ignore alpha/key option -- writes fill-only file with no key plane, matching K-Watch behaviour
- Audio support -- 16-bit PCM, 16 channels, correct K-Watch channel mapping (L=Ch1, R=Ch3)
- Include/exclude audio option
- Auto play and Loop play flags baked into the SWS header at conversion time
- Large file support -- files over 4GB are automatically split into 2GB FAT32-safe chunks, matching K-Watch split file format exactly
- Unified format-in / format-out interface -- open a folder and MacHuna detects the input type (SWS, video, TGA/stills) and adapts the Output dropdown and controls accordingly
- Built-in Video Player -- opens .SWS, .TGA sequences, and video files (MOV, MP4, MXF, MKV, AVI) in a quad display (fill, key, composite, audio meters) with transport controls, launched directly from the MacHuna window
- Batch convert with file picker, auto-incrementing file numbers, and Cancel button for stopping mid-batch
- Supports all confirmed standards: 1080i/50, 1080i/59.94, 1080i/60, 1080p/25, 1080p/50, 1080p/59.94, 1080p/60, 720p/50, 720p/59.94 -- all verified against K-Watch reference files
- Progressive-to-interlaced transcoding -- MacHuna weaves pairs of progressive frames into genuine interlaced frames when converting to an interlaced standard (e.g. 1080p/50 → 1080i/50). Frame count halves automatically.
- Interlaced-to-progressive transcoding -- MacHuna bob-deinterlaces interlaced sources to produce the correct number of progressive frames for the target standard (e.g. 1080i/50 → 1080p/50 produces 50fps output at the correct playback speed).
- "TGA source already interlaced" option -- when re-wrapping TGA frames extracted from an existing interlaced SWS, tick this to pass frames through directly rather than applying field-weaving.
- Conversion log written to the destination folder after each batch
- Settings remembered between sessions
- Fully self-contained .app bundle -- no separate ffmpeg installation required

## Requirements

- macOS 12 or later (Apple Silicon)
- ffmpeg (bundled in the .app -- no separate installation needed when running the app)

## Building from Source

Requirements:
- Python 3.12
- ffmpeg installed via Homebrew (`brew install ffmpeg`)
- PyInstaller (`pip3.12 install pyinstaller`)
- Pillow, numpy (`pip3.12 install pillow numpy`)

Run from the project directory:

```bash
python3.12 -m PyInstaller MacHuna.spec -y
```

The built app will appear in the `dist/` folder.

## Usage

### Convert

1. Set your Destination Folder
2. Click **Open Files…** and select a folder
3. MacHuna detects the input type (SWS, video, or TGA/stills) and updates the **Output** dropdown and controls automatically
4. Choose your output format from the **Output** dropdown
5. Set any options (standard, flags, clip name, etc.) as shown
6. Click **Convert** — files are converted in order; click **Cancel** to stop mid-batch

A conversion log is written to the destination folder on completion.

#### Input type detection

| Files in folder | Detected as | Available outputs |
|---|---|---|
| `.SWS` files only | SWS source | Kahuna SWS, Kayenne MOV, Kayenne TGA, Sony TGA |
| Video files only (MOV, MP4, MXF…) | Video source | Kahuna SWS, Kayenne TGA, Sony TGA |
| TGA sequences and/or stills | TGA/stills source | Kahuna SWS |
| Mix of SWS and other files | Error — shown in summary | — |

#### Kahuna SWS output options

- **Standard** — video standard for the output file (1080i50, 1080p50, 720p50, etc.)
- **Split >4GB** — split large files into 2GB FAT32-safe chunks (on by default)
- **Ignore alpha** — write fill-only SWS with no key plane, matching K-Watch behaviour
- **Auto play / Loop play** — baked into the SWS header
- **TGA source interlaced** — tick when TGA frames were captured from an interlaced source
- **Include audio** — include audio if present in the source
- **Start number / Use source file number** — numbering for the output files

**"Use source file number"** — tick this when converting K-Watch named files (e.g. `TNTS201_30_0001.tga`). MacHuna reads the slot number from the filename rather than the Start Number.

#### Kayenne MOV / Kayenne TGA / Sony TGA output options

- **Standard** — video standard for the output (TGA targets; not shown for Kayenne MOV)
- **Clip name** — 4-character clip name (Sony TGA); output files use this name
- **Field order** — BFF or TFF for interlaced standards (Sony TGA always; Kayenne TGA for interlaced standards)
- **Include audio** — include audio in Kayenne MOV output (shown only if source SWS contains audio)

### Video Player

Click the **Video Player** button to open the built-in preview player. Displays fill, key, composite, and audio meters with full transport controls.

Click **Open…** and select a folder. The player scans the folder and lists all playable items — TGA sequences are shown as one entry per sequence. Double-click or press **Open** to load. Supports:

- **.SWS** — full fill, key, composite, and audio meter display
- **TGA sequences** — prompts for frame rate (25fps default); fill, key, and composite shown if the TGAs have an alpha channel
- **.MOV, .MP4, .MXF, .MKV, .AVI** — frames extracted via ffmpeg; alpha channel preserved for formats that carry it (e.g. ProRes 4444); audio meters active

### Large Files (>4GB)

Files larger than 4GB are automatically split into 2GB chunks inside a folder named `<number>.SWS`, matching the K-Watch split file format exactly. The Split >4GB option must be enabled (it is on by default).

## Extraction outputs

MacHuna can extract `.SWS` files back to standard formats:

- **Kayenne MOV** *(UNCONFIRMED on hardware — awaiting live Kayenne desk test)* -- ProRes 4444 with embedded alpha, for Grass Valley Kayenne ClipStore / Image Store
- **Kayenne TGA** *(UNCONFIRMED on hardware)* -- 32-bit RGBA TGA sequence, for Grass Valley Kayenne Image Store
- **Sony TGA** -- 32-bit RGBA TGA sequence, for Sony MVS Image Store

For TGA targets, choose the **Standard** from the dropdown. For progressive standards, frames are extracted as-is. For interlaced standards, pairs of progressive source frames are field-woven into interlaced output. If the source SWS is already interlaced, frames are passed through directly with a log note. A **BFF/TFF field order** toggle appears for interlaced selections and always for Sony TGA. Sony TGA requires a 4-character **clip name** (all output files share this name so they merge cleanly on import).

## SWS Format

The Kahuna `.SWS` format consists of a 512-byte header followed by v210 big-endian fill and key video planes, with optional 16-channel PCM audio appended. MacHuna reverse-engineered this format from real K-Watch output and has been verified against a live Grass Valley Kahuna mainframe.

## Roadmap

### MacHuna conversion engine
- P→I field order hardware confirmation -- TFF is SMPTE standard for 1080i HD and is used by default; unconfirmed on a 1080i Kahuna setup
- HLG Rec.2020 colour space option (requires a real HLG SWS file to verify)
- Split file support in Video Player

### Extraction outputs -- pending hardware verification
All items below are coded and working by analysis; hardware tests on Kayenne and Sony MVS desks are needed to confirm.
- Kayenne MOV output -- ProRes 4444 with correct fps, BT.709; never loaded on a live Kayenne ClipStore
- Kayenne TGA output -- frame naming and format assumed correct; unconfirmed
- Sony MVS clip naming -- 4-char prefix + frame number convention unconfirmed on a live Sony MVS
- Interlaced SWS → Kayenne MOV -- interlace metadata (field order flags) not written to ProRes container; unknown whether a Kayenne desk requires it
- Sony MVS 25i field order -- BFF assumed for PAL/50Hz; toggle present if incorrect
- MOV → TGA -- full path coded, never hardware-tested

## Licence

MIT License -- see LICENSE file for details.

## Authors

David Steer / DNS Vision Limited & Claude (Anthropic)
