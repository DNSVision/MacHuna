# MacHuna

A macOS application for converting video and still image files to the Grass Valley Kahuna `.SWS` native format, with built-in SWS preview and extraction tools.

## Overview

MacHuna is a Mac-native alternative to the Windows-only K-Watch application included with Grass Valley K-Manager Pro. It converts video, TGA sequences, and still image files to `.SWS` format for use with Grass Valley Kahuna vision mixers, extracts `.SWS` files back to standard formats for use on other vision mixing desks, and reads and writes Grass Valley Kayenne `.eif` native clip files.

Converted files are placed into a destination folder, ready to be loaded onto a Kahuna mainframe via USB or network transfer.

## Features

- Converts MOV, MP4, MXF, MKV, AVI and other ffmpeg-supported formats to `.SWS` (K-Watch supports MOV and AVI only)
- Converts TGA sequences to `.SWS` clips — any naming convention (K-Watch, After Effects, custom renders); K-Watch naming is not required
- Converts still images (PNG, TGA, BMP, JPG etc.) to `.SWS` stills
- **Reads and writes Grass Valley Kayenne `.eif` native clips** *(UNCONFIRMED on hardware — awaiting live Kayenne desk test)*
  - Converts MOV, TGA sequences, and SWS files to `.eif` (slot naming 0001.eif, 0002.eif…)
  - Converts `.eif` files back to Kahuna SWS (lossless direct YCbCr repack), Kayenne TGA, or Sony TGA
- Converts `.SWS` files to other standards within the same format — interlaced↔progressive SWS re-encoding using `tinterlace` (P→I) or `yadif` (I→P); source interlace auto-detected from the SWS header
- Converts TGA sequences and video clips to TGA Sequence output — interlaced↔progressive conversion; frames written to a named subfolder
- Extracts `.SWS` files to Kayenne TGA or Sony TGA format
- Fill and key (alpha) planes correctly encoded as v210 big-endian
- Ignore alpha/key option -- writes fill-only file with no key plane, matching K-Watch behaviour
- Audio support -- 16-bit PCM, 16 channels, correct K-Watch channel mapping (L=Ch1, R=Ch3)
- Include/exclude audio option
- Auto play and Loop play flags baked into the SWS header at conversion time
- Large file support -- files over 4GB are automatically split into 2GB FAT32-safe chunks, matching K-Watch split file format exactly
- Unified format-in / format-out interface -- open a folder and MacHuna detects the input type (SWS, video, TGA/stills) and adapts the Output dropdown and controls accordingly
- Built-in Video Player -- opens .SWS, .TGA sequences, and video files (MOV, MP4, MXF, MKV, AVI) in a quad display (fill, key, composite, audio meters) with transport controls, launched directly from the MacHuna window
- Batch convert with file picker, auto-incrementing file numbers, and Cancel button for stopping mid-batch
- **Bespoke per-item output IDs** (v1.6.13) — instead of an auto-sequence, give each selected item its own output number (Kahuna SWS, Kayenne EIF) or its own 4-character clip name (Sony TGA). Blank, duplicate and already-in-the-destination values block the batch with a message naming the items; nothing is ever overwritten. Bespoke Sony names also let several Sony clips convert in one batch
- Supports all confirmed standards: 1080i/50, 1080i/59.94, 1080i/60, 1080p/25, 1080p/50, 1080p/59.94, 1080p/60 -- all verified against K-Watch reference files. (720p output was withdrawn in v1.6.8 pending hardware verification.)
- Progressive-to-interlaced transcoding -- MacHuna weaves pairs of progressive frames into genuine interlaced frames when converting to an interlaced standard (e.g. 1080p/50 → 1080i/50). Frame count halves automatically. This is only valid when the source runs at the interlaced **field** rate (double the frame rate: 50p→1080i50, 59.94p→1080i5994, 60p→1080i60); a **same-rate** source (e.g. 25p→1080i50) would play at 2× speed if weaved, so MacHuna blocks it with a clear error rather than produce a wrong-speed clip.
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
| `.SWS` files only | SWS source | Kahuna SWS, Kayenne TGA, Kayenne EIF, Sony TGA |
| Video files only (MOV, MP4, MXF…) | Video source | Kahuna SWS, Kayenne TGA, Kayenne EIF, Sony TGA, TGA Sequence |
| TGA sequences and/or stills | TGA/stills source | Kahuna SWS, Kayenne EIF, Sony TGA, TGA Sequence — **stills can only go to Kahuna SWS** |
| `.EIF` files only | EIF source | Kahuna SWS, Kayenne TGA, Sony TGA |
| Mix of `.EIF` and `.SWS` files | EIF+SWS mixed source | Kahuna SWS, Kayenne TGA, Sony TGA |
| Mix of SWS and other non-EIF files | Error — shown in summary | — |

#### Kahuna SWS output options

- **Standard** — video standard for the output file (1080i50, 1080p50, 1080p25, etc.)
- **Split >4GB** — split large files into 2GB FAT32-safe chunks (on by default)
- **Ignore alpha** — write fill-only SWS with no key plane, matching K-Watch behaviour
- **Auto play / Loop play** — baked into the SWS header
- **TGA source interlaced** — tick when TGA frames were captured from an interlaced source
- **Include audio** — include audio if present in the source
- **Start number / Use source file number** — numbering for the output files

**"Use source file number"** — tick this when converting K-Watch named files (e.g. `TNTS201_30_0001.tga`). MacHuna reads the slot number from the filename rather than the Start Number.

**"Use bespoke numbering"** (v1.6.13) — tick this to set each item's output number yourself rather than take an auto-sequence. A scrollable panel lists every selected item with its own field (1-9999); the Start number and "Use source file number" controls are hidden while it is on. Fields start blank on purpose, so it is obvious which items still need a number. Before converting, MacHuna blocks the batch if any field is blank or out of range, if two items share a number, or if a number would collide with something already in the destination (`12.SWS` as a file or as a split-file folder). Clashes must be corrected — there is no overwrite option. The same checkbox appears for Kayenne EIF output, where the number becomes the slot (`0012.eif`). It is not offered for Kayenne TGA or TGA Sequence output, which name their folders from the source file.

#### Kayenne MOV / Kayenne TGA / Sony TGA output options

- **Standard** — video standard for the output (TGA targets; not shown for Kayenne MOV)
- **Clip name** — 4-character clip name (Sony TGA); output files use this name. With one shared name, Sony TGA converts one clip per batch (a second clip would overwrite the first in the same folder)
- **Use bespoke names** (v1.6.13; Sony TGA) — give each selected clip its own 4-character name instead, one per row in a scrollable panel, replacing the shared Clip name field. Each name becomes its own output folder, so **several Sony clips can be converted in one batch**. Blank, malformed, duplicate, or already-present names block the batch with a message naming the clips
- **Field order** — BFF or TFF for interlaced standards (Sony TGA always; Kayenne TGA for interlaced standards). Honoured in both conversion directions since v1.6.12; before that it was ignored for Sony TGA output from TGA/clip input. The conversion log records which order was applied.
- **Include audio** — include audio in Kayenne MOV output (shown only if source SWS contains audio)

#### Kayenne EIF output options *(UNCONFIRMED on hardware)*

- **Slot number** — starting slot number for output files (0001, 0002… — 4-digit zero-padded). Increments per batch item. Kayenne requires this naming convention.
- **TGA source interlaced** — shown when source is a TGA sequence. Tick when TGA frames are from an interlaced source; MacHuna deinterlaces each frame using yadif (field separation, TFF) to produce 50fps progressive EIF.

EIF output is always 1920×1080 progressive. Frame rate is rounded to the nearest EIF-supported rate (25fps or 50fps). An UNCONFIRMED notice appears on the output; awaiting live Kayenne hardware test.

#### TGA Sequence output options

- **Standard** — controls the conversion direction. Selecting an interlaced standard (e.g. 1080i/50) with a progressive source applies `tinterlace=mode=interleave_top` to produce genuinely interlaced output (frame count halves). This requires a double-rate (field-rate) source; a same-rate source (e.g. 25p → 1080i/50) is blocked with an error to avoid a 2×-speed clip. Selecting a progressive standard with an interlaced source applies yadif, plus an fps resample when the target rate is not double the source's frame rate (since v1.6.12 — cross-rate pairings such as 1080i/50 → 1080p/60 previously played at the wrong speed). A loose TGA sequence has no frame rate to work from, so it assumes the source standard matches the chosen output family.
- **TGA source interlaced** — shown when input is a TGA sequence. Tick when the source frames are from an interlaced source (e.g. extracted from 1080i/50 SWS).

Output frames are written as `0001.tga, 0002.tga…` in a subfolder named after the source sequence or clip, inside the destination folder. One subfolder per input item.

### Video Player

Click the **Video Player** button to open the built-in preview player. Displays fill, key, composite, and audio meters with full transport controls.

Click **Open…** and pick a file. Supports:

- **.SWS** — full fill, key, composite, and audio meter display; standard, frame count, duration, and timecode shown in info strip
- **TGA sequences** — select any frame from the sequence; prompts for frame rate (25fps default); fill, key, and composite shown if the TGAs have an alpha channel
- **.MOV, .MP4, .MXF, .MKV, .AVI** — frames extracted via ffmpeg; alpha channel preserved for formats that carry it (e.g. ProRes 4444); audio meters active
- **.EIF** — Grass Valley Kayenne native format; frame rate auto-detected from header; key and composite panels populated; fill, key, and composite display with transport controls

The info strip shows the format of the loaded file (SWS, TGA, MOV, EIF) alongside frame count and duration.

### Large Files (>4GB)

Files larger than 4GB are automatically split into 2GB chunks inside a folder named `<number>.SWS`, matching the K-Watch split file format exactly. The Split >4GB option must be enabled (it is on by default).

## Extraction outputs

MacHuna can extract `.SWS` files back to standard formats, and also convert `.eif` clips in multiple directions:

### From SWS

- **Kahuna SWS** -- re-encode to a different standard within the SWS format; useful for interlaced↔progressive conversion (e.g. 1080p50 SWS → 1080i50 SWS, or vice versa). Source interlace state is auto-detected from the SWS header. P→I uses `tinterlace=mode=interleave_top` (TFF) and requires a double-rate source — a same-rate source SWS (e.g. 1080p/25 → 1080i/50) is blocked with an error rather than doubled in speed; I→P uses `yadif`. The output clip name and key state follow the source SWS; embedded audio is not carried through (a warning is logged if the source has audio).
- **Kayenne TGA** *(UNCONFIRMED on hardware)* -- 32-bit RGBA TGA sequence, for Grass Valley Kayenne Image Store
- **Sony TGA** -- 32-bit RGBA TGA sequence, for Sony MVS Image Store

For TGA targets, choose the **Standard** from the dropdown. For progressive standards, frames are extracted as-is. For interlaced standards, pairs of progressive source frames are field-woven into interlaced output. If the source SWS is already interlaced, frames are passed through directly with a log note. A **BFF/TFF field order** toggle appears for interlaced selections and always for Sony TGA. Sony TGA requires a 4-character **clip name** (all output files share this name so they merge cleanly on import), or a bespoke name per clip when several clips are converted together.

For Kahuna SWS output, the Standard dropdown controls the output standard and conversion direction. The Split >4GB and Ignore alpha options apply.

### From EIF *(UNCONFIRMED on hardware)*

- **Kayenne EIF → Kahuna SWS** -- lossless direct YCbCr repack; no RGB round-trip; output standard auto-derived from EIF fps
- **Kayenne EIF → Kayenne TGA** -- full-resolution 1920×1080 RGBA TGA sequence, progressive or interlaced
- **Kayenne EIF → Sony TGA** -- 32-bit RGBA with 4-char clip name prefix, progressive or interlaced

All EIF conversion paths are UNCONFIRMED pending live hardware test. See Roadmap below.

## SWS Format

The Kahuna `.SWS` format consists of a 512-byte header followed by v210 big-endian fill and key video planes, with optional 16-channel PCM audio appended. MacHuna reverse-engineered this format from real K-Watch output and has been verified against a live Grass Valley Kahuna mainframe.

## Roadmap

The authoritative roadmap lives in [`DEVELOPMENT_NOTES.md`](DEVELOPMENT_NOTES.md) under "Roadmap (canonical)". In short, the feature set is essentially complete and the remaining work is mostly **hardware verification**:

- **EIF** write and conversion paths are coded and verified by analysis, but not yet confirmed on a live Grass Valley Kayenne desk (the top priority).
- **Extraction outputs** (Kayenne TGA, Sony MVS TGA) need confirming on real Kayenne and Sony MVS hardware.
- A few small code items (cross-rate interlaced-to-progressive resample, Sony TGA field-order toggle) and future options (HLG Rec.2020, EIF to MOV) remain.

See `DEVELOPMENT_NOTES.md` for the full status list.

## Licence

MIT License -- see LICENSE file for details.

## Authors

David Steer / DNS Vision Limited & Claude (Anthropic)
