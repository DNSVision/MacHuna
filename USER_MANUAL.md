# MacHuna v1.6.2 — User Manual

**Broadcast Media Format Converter**

DNS Vision Limited — For Vision Mixers, TDs, and Support Engineers

---

## Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Main Window](#3-main-window)
4. [Converting Files](#4-converting-files)
5. [Kahuna SWS Output](#5-kahuna-sws-output)
6. [Kayenne EIF — Native Kayenne Format](#6-kayenne-eif--native-kayenne-format)
7. [Extraction Outputs — Kayenne and Sony MVS](#7-extraction-outputs--kayenne-and-sony-mvs)
8. [TGA Sequences](#8-tga-sequences)
9. [Audio](#9-audio)
10. [Video Player](#10-video-player)
11. [Large File Support (>4GB)](#11-large-file-support-4gb)
12. [SWS Format Reference](#12-sws-format-reference)
13. [Troubleshooting](#13-troubleshooting)
14. [Known Limitations](#14-known-limitations)
15. [Authors](#15-authors)

---

## 1. Overview

MacHuna is a macOS application for translating broadcast media assets between formats. It converts video clips, TGA sequences, and still images to Grass Valley Kahuna `.SWS` format, reads and writes Grass Valley Kayenne `.EIF` native clips, and extracts `.SWS` files back to standard formats for use on Kayenne and Sony MVS desks.

It is a Mac-native alternative to the Windows-only K-Watch application included with Grass Valley K-Manager Pro.

### 1.1 What MacHuna Does

| Direction | From | To |
|---|---|---|
| Kahuna SWS | MOV, MP4, MXF, MKV, AVI, TGA sequences, PNG, BMP, JPG | `.SWS` (Grass Valley Kahuna) |
| Kayenne EIF | MOV, MP4, MXF, TGA sequences, `.SWS` | `.EIF` (Grass Valley Kayenne) *(UNCONFIRMED on hardware)* |
| Kayenne EIF → SWS | `.EIF` | `.SWS` (Grass Valley Kahuna) *(UNCONFIRMED on hardware)* |
| Kayenne EIF → TGA | `.EIF` | 32-bit RGBA TGA sequence *(UNCONFIRMED on hardware)* |
| Kayenne MOV | `.SWS` | ProRes 4444 MOV with embedded alpha *(UNCONFIRMED on hardware)* |
| Kayenne TGA | `.SWS` | 32-bit RGBA TGA sequence *(UNCONFIRMED on hardware)* |
| Sony TGA | `.SWS` | 32-bit RGBA TGA sequence (Sony MVS naming) |

### 1.2 Supported Standards

All nine standards below have been confirmed against K-Watch reference files and verified on a live Grass Valley Kahuna mainframe.

| Standard | fps | Region |
|---|---|---|
| 1080i/50 | 25 | UK / Europe |
| 1080i/59.94 | 29.97 | USA / Japan |
| 1080i/60 | 30 | — |
| 1080p/25 | 25 | UK / Europe |
| 1080p/50 | 50 | UK / Europe |
| 1080p/59.94 | 59.94 | USA / Japan |
| 1080p/60 | 60 | — |
| 720p/50 | 50 | — |
| 720p/59.94 | 59.94 | USA / Japan |

### 1.3 Key Differences from K-Watch

- Runs natively on macOS — no Windows, no Parallels
- Accepts a wider range of input formats (K-Watch supports MOV and AVI only)
- Converts between Kahuna SWS, Kayenne EIF, and Sony MVS formats in one app
- Reads and writes Kayenne `.EIF` native clips — format reverse-engineered from real Kayenne hardware
- Built-in Video Player for checking `.SWS` and `.EIF` files without a Kahuna or Kayenne desk

> **NOTE** MacHuna replicates K-Watch's conversion functionality. It does not replicate K-Manager Pro's network upload to mainframe or project synchronisation features.

---

## 2. Installation

MacHuna is distributed as a self-contained `.app` bundle. ffmpeg is bundled inside — no separate installation required.

### 2.1 First Launch

1. Copy `MacHuna.app` to your Applications folder, or run it from any location
2. On first launch, right-click the app and choose **Open** to bypass macOS Gatekeeper
3. Subsequent launches work by double-clicking normally

> **NOTE** Gatekeeper may warn that the app is from an unidentified developer. This is expected — MacHuna is not signed with an Apple Developer certificate. Right-click → Open bypasses this check.

### 2.2 Settings

MacHuna saves all settings automatically on quit. Settings are stored at:

```
~/.kwatch_settings.json
```

To reset to defaults, quit MacHuna and delete this file.

---

## 3. Main Window

The MacHuna window has three rows:

| Row | Purpose |
|---|---|
| **Destination Folder** | Where converted files are written |
| **Convert** | Open files, choose output format, convert |
| **Log** | Conversion progress and errors |

The Convert row adapts automatically based on what files you open. MacHuna detects the input type and shows only the controls that are relevant.

---

## 4. Converting Files

The workflow is the same regardless of what you are converting or what you are converting it to:

1. Set your **Destination Folder**
2. Click **Open Files…** and select a folder
3. MacHuna scans the folder, detects the input type, and populates the file list
4. Choose your **Output** format from the dropdown
5. Set any options that appear (standard, clip name, field order, etc.)
6. Click **Convert**

A conversion log is written to the Destination Folder when the batch completes.

### 4.1 Input Type Detection

MacHuna reads the contents of the folder you open and determines the input type automatically:

| Files found in folder | Detected as | Available outputs |
|---|---|---|
| `.SWS` files only | SWS source | Kahuna SWS, Kayenne MOV, Kayenne TGA, Sony TGA |
| `.EIF` files only | EIF source | Kahuna SWS, Kayenne TGA, Sony TGA |
| Mix of `.EIF` and `.SWS` files | EIF + SWS source | Kahuna SWS, Kayenne TGA, Sony TGA |
| Video files only (MOV, MP4, MXF…) | Video source | Kahuna SWS, Kayenne TGA, Sony TGA, Kayenne EIF |
| TGA sequences and/or stills | TGA / stills source | Kahuna SWS, Kayenne EIF |
| Mix of SWS and other files | Error — shown in summary | — |

> **NOTE** If you see a "mixed input" error, the folder contains both `.SWS` files and other file types. Move them into separate folders and convert each folder independently.

### 4.2 The File List

The file list shows one entry per item to be converted:

- **TGA sequences** are collapsed to a single line: `TNTS201  (30 frames)` — you do not need to select individual frames
- **Video files** appear by filename
- **Stills** appear by filename
- **EIF files** appear by filename

Click entries to select or deselect them. By default, all files are selected.

### 4.3 Numbering

For Kahuna SWS output, the **Start Number** field sets the number assigned to the first output file. Subsequent files are numbered sequentially.

**Use source file number** — tick this when re-converting K-Watch named files (e.g. `TNTS201_30_0001.tga`). MacHuna reads the slot number from the filename rather than the Start Number. Useful when a conversion needs to replace a specific existing slot on the Kahuna.

For Kayenne EIF output, a **Start slot** spinner sets the first slot number (e.g. `0001`). Output files are named `0001.eif`, `0002.eif`, and so on.

### 4.4 Cancel

Click **Cancel** during a conversion to stop after the current file. The conversion log is not written if cancelled mid-batch.

---

## 5. Kahuna SWS Output

When outputting to Kahuna SWS, the following options are available:

| Option | Description |
|---|---|
| **Standard** | Target video standard. 1080p/50 is most common for UK/European broadcast. |
| **Split >4GB** | On by default. Files over 4GB are split into 2GB FAT32-safe chunks. See Section 11. |
| **Ignore alpha** | No key plane is written. Output is fill-only, matching K-Watch no-alpha behaviour. Use for fill-only content or when the Kahuna output does not use a downstream keyer. |
| **Auto play** | Sets the Auto Play flag in the SWS header. The Kahuna begins playback when the clip is loaded. |
| **Loop play** | Sets the Loop Play flag in the SWS header. The Kahuna loops the clip continuously. |
| **TGA source interlaced** | See Section 8.2. |
| **Include audio** | Embeds audio from the source into the .SWS file. Shown only when audio is detected in the source. See Section 9. |

### 5.1 Progressive to Interlaced (P→I)

When converting a progressive source to an interlaced standard, MacHuna field-weaves pairs of progressive frames into genuine interlaced frames. The frame count halves — a 50fps progressive source becomes 25fps interlaced output. This is the correct behaviour for the Kahuna.

Example: 100 frames of 1080p/50 source → 50 frames of 1080i/50 output.

### 5.2 Interlaced to Progressive (I→P)

When converting an interlaced source to a progressive standard, MacHuna bob-deinterlaces to produce the correct number of progressive frames. Playback speed on the Kahuna is preserved.

Example: 50 frames of 1080i/50 source → 100 frames of 1080p/50 output.

---

## 6. Kayenne EIF — Native Kayenne Format

> **IMPORTANT — Hardware Status**
> EIF write and conversion paths have been verified correct by analysis against real Kayenne-produced reference files, but **none have been tested on a live Kayenne desk**. MacHuna will warn you before converting to or from EIF. Verify the first import carefully.

MacHuna can read and write Grass Valley Kayenne `.EIF` files — the native clip format used by Kayenne ClipStore and Image Store. The format was fully reverse-engineered from real Kayenne-produced files.

### 6.1 What is EIF?

`.EIF` is the Kayenne's native clip container. Each file holds a complete clip — fill and key combined in a single proprietary pixel format. The format stores 1920×1080 progressive video only; frame rates are either 25fps or 50fps. Files are named by slot number: `0001.eif`, `0002.eif`, and so on.

### 6.2 Converting TO EIF

Any of the following inputs can be converted to Kayenne EIF:

| Input | Notes |
|---|---|
| MOV, MP4, MXF, MKV, AVI | Alpha channel (fill + key) preserved if present |
| TGA sequence | Progressive or interlaced source — see TGA source interlaced option |
| Kahuna SWS | Lossless direct YCbCr repack — no RGB conversion |

**Output options:**

| Option | Description |
|---|---|
| **Start slot** | First slot number for output files. Files are named `0001.eif`, `0002.eif` etc. and increment per item in the batch. |
| **TGA source interlaced** | Shown when source is a TGA sequence. Tick when TGA frames are from an interlaced source. MacHuna deinterlaces each frame using yadif (field separation, TFF) to produce 50fps progressive EIF output. |

EIF output is always 1920×1080. Sources of other sizes are scaled. Frame rate is rounded to the nearest EIF-supported rate (25fps or 50fps).

### 6.3 Converting FROM EIF

EIF files can be converted to the following outputs:

| Output | Notes |
|---|---|
| **Kahuna SWS** | Lossless direct YCbCr repack. Output standard auto-derived from EIF frame rate (25fps → 1080p/25, 50fps → 1080p/50). |
| **Kayenne TGA** | Full-resolution 1920×1080 32-bit RGBA TGA sequence. Frames numbered `0001.tga` onwards. |
| **Sony TGA** | 32-bit RGBA TGA sequence with 4-character clip name prefix. |

For TGA outputs, select the **Standard** to control whether MacHuna field-weaves frames (interlaced standard) or extracts them as-is (progressive standard). The same field order and clip name options as regular extraction apply — see Section 7.

### 6.4 EIF in the Video Player

The built-in Video Player opens `.EIF` files directly. Frame rate is detected automatically from the file header — no prompt required. Fill, key, and composite panels are all populated. See Section 10.

---

## 7. Extraction Outputs — Kayenne and Sony MVS

> **IMPORTANT — Hardware Status**
> The extraction output paths have been confirmed correct by code analysis. However, Kayenne MOV and Kayenne TGA outputs have **never been loaded on a live Kayenne desk**, and Sony TGA clip naming has **never been verified on a live Sony MVS**. MacHuna will warn you before converting to these targets. Use with that caveat in mind and verify the first import on your desk carefully.

### 7.1 Output Targets

| Output | Format | Destination desk |
|---|---|---|
| **Kayenne MOV** | ProRes 4444 with embedded alpha. BT.709. Audio muxed if present. | Grass Valley Kayenne ClipStore / Image Store |
| **Kayenne TGA** | 32-bit RGBA TGA sequence. Frames numbered `0001.tga` onwards. One subfolder per SWS. | Grass Valley Kayenne Image Store |
| **Sony TGA** | 32-bit RGBA TGA sequence. Frames numbered `XXXX0000.tga` (4-character clip name + frame number). One subfolder per SWS. | Sony MVS Image Store |

### 7.2 Workflow

1. Open a folder of `.SWS` files
2. Select the output target from the **Output** dropdown
3. Set any options shown (Standard, Clip name, Field order, Include audio)
4. Click **Convert**

### 7.3 Standard (TGA outputs)

For Kayenne TGA and Sony TGA, select the **Standard** matching your target desk's video standard. This determines whether MacHuna applies field-weaving (for interlaced output standards) or extracts frames as-is (for progressive standards).

- **Progressive standard selected:** frames extracted directly from the SWS
- **Interlaced standard selected:** if the source SWS is already interlaced, frames are passed through. If the source is progressive, pairs of frames are field-woven into interlaced output.

MacHuna logs a note describing what it did for each file.

### 7.4 Field Order (TGA outputs)

A **BFF / TFF** toggle appears for interlaced standards, and always for Sony TGA. BFF (Bottom Field First) is assumed for PAL/50Hz. If you see motion artefacts or comb effects on the desk after import, switch to TFF and reconvert.

### 7.5 Sony TGA — Clip Name

Enter a **4-character alphanumeric clip name** (e.g. `WIPE`). All TGA frames in the batch share this name — on the Sony MVS, files with the same 4-character prefix are grouped into a single clip on import.

If you are converting multiple distinct clips in one batch, be aware they will all share the same clip name. Convert each clip separately if they need to appear as separate clips on the desk.

### 7.6 Kayenne MOV — Include Audio

If the source `.SWS` files contain audio, an **Include audio** option appears. Tick this to mux the audio into the ProRes MOV output.

### 7.7 Output Structure

| Output | File naming |
|---|---|
| Kayenne MOV | `0001.mov`, `0002.mov` … written flat into the Destination Folder |
| Kayenne TGA | Subfolder per SWS, named after the SWS stem. Frames `0001.tga` … inside. |
| Sony TGA | Subfolder per SWS, named after the 4-character clip name. Frames `XXXX0000.tga` … inside. |

### 7.8 ProRes 4444 Round-Trip Quality

Converting SWS → Kayenne MOV → SWS involves a YCbCr/RGB/YCbCr colour space round-trip and ProRes encoding. ProRes 4444 is a high-quality intermediate and the generational loss per pass is very small, but it is not lossless. For production use, a single conversion pass is the intended workflow.

---

## 8. TGA Sequences

TGA sequences are multi-frame clips stored as individually numbered still images. MacHuna handles them through the folder browser — you do not need to select individual frames.

MacHuna accepts any numbered TGA naming convention — K-Watch names, After Effects exports, third-party renders, or anything else:

```
TNTS201_30_0001.tga   (K-Watch naming)
FEDX0000.tga          (letters + digits, no separator)
shot_0001.tga         (underscore separator)
render.0001.tga       (dot separator)
```

The only requirement is that frames are numbered sequentially.

### 8.1 In the Folder Browser

When you open a folder containing a TGA sequence, MacHuna collapses the entire sequence to a single entry:

```
TNTS201  (30 frames)
```

Select this entry and convert as normal. MacHuna handles the frame ordering automatically.

### 8.2 TGA Source Already Interlaced

If you are re-wrapping TGA frames that were previously extracted from an interlaced SWS (e.g. via MacHuna's extraction outputs), tick **TGA source interlaced**. This tells MacHuna to pass frames through directly without applying field-weaving. Without this, MacHuna would incorrectly treat the already-interlaced frames as progressive and weave them again.

When **TGA source interlaced** is ticked and you select a **progressive** target standard (e.g. 1080p/50), MacHuna deinterlaces the frames using yadif (`send_field`, TFF per SMPTE 274M) rather than duplicating them — each interlaced frame is separated into two progressive fields, doubling the frame count with correct, smooth motion. Any alpha/key channel is deinterlaced with the identical filter so fill and key stay aligned.

### 8.3 Alpha Channel

- If TGA files have an alpha channel, the key plane is extracted automatically
- If no alpha is present and Ignore alpha is off, a solid white key plane is generated
- If Ignore alpha is ticked, no key plane is written regardless

### 8.4 Audio

Audio is not supported in TGA sequence conversions.

---

## 9. Audio

MacHuna extracts audio from source files and embeds it in the `.SWS` file in K-Watch native format.

### 9.1 Audio Format

| | |
|---|---|
| Encoding | 16-bit signed little-endian PCM |
| Sample rate | 48,000 Hz |
| Channels | 16 channels interleaved |
| Channel mapping | Ch1 = Left, Ch3 = Right, all others silent |
| Samples per frame | 48000 ÷ fps (e.g. 960 samples at 50fps, 1920 at 25fps) |

The channel mapping (L=Ch1, R=Ch3) matches the K-Watch convention, confirmed by hex analysis of K-Watch reference files. MacHuna uses an explicit ffmpeg pan filter — a straight `-ac 16` upmix does not produce the correct layout.

### 9.2 Notes

- Audio is appended after the key plane in the `.SWS` file
- If the source has no audio and Include audio is ticked, the option is simply ignored — no error
- Audio detection in third-party `.SWS` files uses the audio offset and format flag fields (0x1E8 and 0x1EC). The audio frame size field at 0x1C2 is unreliable across workflows and is not used for detection

---

## 10. Video Player

The built-in Video Player lets you check a file without needing a Kahuna or Kayenne desk. Click the **Video Player** button to open it.

### 10.1 Accepted Inputs

| Input | Fill / Key / Composite | Audio |
|---|---|---|
| `.SWS` | Yes | Yes (if present in file) |
| `.EIF` (Kayenne native) | Yes — fill, key, and composite all populated | No |
| `.TGA` sequence (pick any frame) | Yes (if TGAs have alpha) | No |
| `.MOV`, `.MP4`, `.MXF`, `.MKV`, `.AVI` | Yes (alpha preserved for ProRes 4444 etc.) | Yes |

Click **Open…** and select a file. For TGA sequences, pick any frame from the sequence — MacHuna loads the whole sequence. When opening a TGA sequence, you will be prompted for the frame rate (25fps default). For EIF files, the frame rate is detected automatically from the header.

### 10.2 Display Layout

| Panel | Content |
|---|---|
| **Fill** | The video content plane |
| **Key** | The alpha/key plane (greyscale) |
| **Composite** | Fill composited over a chequerboard using the key as alpha — shows transparency |
| **Audio** | VU meters for left and right channels |

### 10.3 Transport Controls

| Control | Action |
|---|---|
| Cue | Jump to the first frame |
| Play | Begin playback at the clip's native frame rate |
| Pause | Pause at the current frame |
| Stop | Stop and return to the first frame |

### 10.4 Notes

- Multiple player windows can be open simultaneously
- Split `.SWS` files (>4GB, multi-chunk) cannot currently be previewed
- Audio playback uses the sounddevice library. If not installed, the player opens without audio but VU meters are still drawn

---

## 11. Large File Support (>4GB)

Files larger than 4GB are automatically split into 2GB chunks when **Split >4GB** is enabled (on by default). The split format exactly matches K-Watch output and has been confirmed working on a live Kahuna mainframe.

### 11.1 Split File Structure

```
201.SWS/
  01_OF_03._XX   (512-byte header + video data, exactly 2GB)
  02_OF_03._XX   (video data, exactly 2GB)
  03_OF_03._XX   (video data, remainder)
```

- Chunk 1 contains the SWS header followed by video data
- Subsequent chunks contain raw video data only
- The header in chunk 1 carries the total frame count across all chunks
- Audio is not supported in split files

> **IMPORTANT** When transferring to a Kahuna via USB, copy the entire `.SWS` folder (e.g. `201.SWS/`), not the individual chunk files inside it.

---

## 12. SWS Format Reference

This section is for support engineers and developers. It documents the SWS binary format as reverse-engineered from K-Watch reference files and verified against a live Grass Valley Kahuna mainframe.

### 12.1 File Layout

| Range | Content |
|---|---|
| `0x000 – 0x1FF` | 512-byte header (big-endian) |
| `0x200 – N` | Fill plane: v210 big-endian, `plane_size × frame_count` bytes |
| `N – M` | Key plane: v210 big-endian, same size as fill plane (absent if `play_count == 0`) |
| `M – EOF` | Audio data: 16-bit LE PCM, 16ch, 48kHz (absent if audio offset == 0) |

### 12.2 Key Header Fields

| Offset | Type | Description |
|---|---|---|
| `0x188` | uint32 BE | Video standard code (OR'd with playback flags — see 12.4) |
| `0x18C` | uint32 BE | Format variant code (unambiguous fps lookup — all nine values are unique) |
| `0x190` | uint32 BE | Width in pixels |
| `0x194` | uint32 BE | Height in pixels (fill plane) |
| `0x1A0` | uint32 BE | Plane size (bytes per frame, fill or key) |
| `0x1A4` | uint32 BE | Frame count |
| `0x1A8` | uint32 BE | Play count (= frame count; 0 if no key plane) |
| `0x1B4` | uint32 BE | `(plane_size × frame_count + 512) / 32`; 0 if no key |
| `0x1C2` | uint16 BE | Audio frame size — unreliable, do not use for detection |
| `0x1CC` | uint32 BE | Total file size in bytes |
| `0x1E8` | uint32 BE | Audio data offset ÷ 32 (0 if no audio) |
| `0x1EC` | uint32 BE | Audio format flag: `0x03000000` if audio present |

### 12.3 Audio Detection

Reliable method: `aud_offset (0x1E8) > 0` AND `aud_fmt (0x1EC) == 0x03000000`.

Do not rely on the audio frame size field at `0x1C2`. K-Watch writes `0x1680`, but third-party tools may write different values. MacHuna uses the offset and format flag fields for all audio detection.

### 12.4 Playback Flags

Bits 2 (`0x04`) and 3 (`0x08`) of the low byte at `0x188` are OR'd into the video standard code:

| Flag | Bit | Value |
|---|---|---|
| Auto Play | 2 | `0x04` |
| Loop Play | 3 | `0x08` |

### 12.5 Interlaced Flag

Bit 15 (`0x8000`) of `0x188` is set for all interlaced standards. The standard code for all interlaced formats is `0xC923`.

---

## 13. Troubleshooting

### Kahuna showing black key / no key

- If **Ignore alpha** is ticked, no key plane is written — correct behaviour
- If the source has no alpha channel and Ignore alpha is off, a solid white key is generated automatically
- If you are expecting a real key but getting white, check your source file has a valid alpha channel

### Audio not playing on Kahuna

- Confirm **Include audio** is ticked
- Confirm the source file has an audio track (MacHuna hides Include audio if no audio is detected)
- Audio is resampled to 48kHz by ffmpeg if the source is at a different rate — this is automatic

### File >4GB not loading on Kahuna

- Confirm **Split >4GB** is enabled
- Copy the entire `.SWS` folder to the USB drive, not the individual chunk files inside it
- The USB drive must be FAT32-formatted

### Conversion fails with ffmpeg error

- Check the Log area for the ffmpeg error message
- Confirm the source file is not corrupted — try opening it in another application
- Confirm the Destination Folder path exists and is writable

### Extraction output not loading on Kayenne or Sony MVS

- Note that Kayenne MOV and Kayenne TGA outputs have not been confirmed on a live Kayenne desk
- Sony TGA clip naming has not been confirmed on a live Sony MVS
- Check that the correct Standard is selected for the target desk's video format
- For Sony TGA: confirm the 4-character clip name matches your expected import workflow
- For interlaced output: if motion artefacts appear, try switching the Field Order toggle (BFF ↔ TFF)

### EIF file not loading on Kayenne desk

- EIF write output has not yet been tested on a live Kayenne desk — proceed with caution
- Confirm the file is named with the correct 4-digit slot number (e.g. `0001.eif`)
- Confirm the destination folder or USB drive is formatted correctly for Kayenne
- Check the Log area for any conversion warnings

### TGA sequence not appearing as a single entry in the file list

- Confirm the TGA files are in the same folder with no other file types present
- MacHuna detects TGA sequences by parsing numbered filenames — files must be numbered sequentially. Any naming convention works (K-Watch, After Effects, custom renders, etc.) as long as the base name is consistent and frames are numbered.

### File plays at double speed on Kahuna

This can happen if:
- A progressive source was converted to a Kahuna SWS without using the progressive standard, and there is a mismatch between the frame count and the interlaced header
- A TGA sequence from an interlaced source was converted without ticking **TGA source interlaced** — MacHuna field-weaved the already-interlaced frames, halving the frame count again

Check the conversion log for any warnings about P→I or interlaced detection.

---

## 14. Known Limitations

- **Apple Silicon only** — Intel Mac builds are not supported
- **Split .SWS files** cannot be previewed in the Video Player
- **TGA sequence audio** is not supported
- **HLG Rec.2020** colour space is not implemented (requires a reference HLG .SWS file to reverse-engineer the header values)
- **EIF write and conversion** — coded and working by analysis, but not yet confirmed on a live Kayenne desk. MacHuna warns before converting to or from EIF. Verify your first import carefully.
- **EIF audio** — companion `.eaf` audio files used by some Kayenne clips are not currently supported. EIF files are always loaded without audio in the Video Player.
- **Extraction outputs unconfirmed on hardware** — Kayenne MOV, Kayenne TGA, and Sony MVS TGA naming have not been verified on live desks. MacHuna will warn you before converting to these targets.

---

## 15. Authors

David Steer / DNS Vision Limited & Claude (Anthropic)

MacHuna was built collaboratively using AI-assisted development. The SWS format was reverse-engineered from K-Watch reference files and verified against a live Grass Valley Kahuna mainframe. The Kayenne EIF format was reverse-engineered from real Kayenne-produced clips.
