# MacHuna v1.5.4 - User Manual

**Grass Valley Kahuna SWS Converter**

DNS Vision Limited - For use by Vision Mixers, TDs, and Support Engineers

---

## Contents

1. [Overview](#1-overview)
2. [Installation](#2-installation)
3. [Main Window](#3-main-window)
4. [Batch Convert](#4-batch-convert)
5. [TGA Sequence Conversion](#5-tga-sequence-conversion)
6. [Audio](#6-audio)
7. [SWS Preview Player](#7-sws-preview-player)
8. [Hula SWS Extractor](#8-hula-sws-extractor)
9. [Large File Support](#9-large-file-support-4gb)
10. [SWS Format Reference](#10-sws-format-reference)
11. [Troubleshooting](#11-troubleshooting)
12. [Known Limitations](#12-known-limitations)
13. [Related Projects](#13-related-projects)
14. [Authors](#14-authors)

---

## 1. Overview

MacHuna is a macOS application for converting video and still image files to the Grass Valley Kahuna .SWS native format. It is a Mac-native alternative to the Windows-only K-Watch application from Grass Valley's K-Manager Pro suite.

MacHuna also includes two built-in tools accessible from the main window:

- **SWS Preview Player** - preview any .SWS file with fill, key, composite, and audio metering
- **Hula SWS Extractor** - convert .SWS files back to standard formats for use on Kayenne and Sony MVS desks

### 1.1 Supported Platforms

| | |
|---|---|
| macOS | Apple Silicon (M-series). macOS 12 or later. |
| ffmpeg | Bundled inside the .app. No separate installation required. |
| Video standards | 1080i50, 1080i29.97, 1080p25, 1080p50, 720p50, 720p59.94 and others |
| Input formats | MOV, MP4, MXF, MKV, AVI, TGA sequences, PNG, BMP, JPG stills |
| Output format | .SWS (Grass Valley Kahuna native) |

### 1.2 Key Differences from K-Watch

- Runs natively on macOS - no Windows or Parallels required
- Accepts a wider range of input formats (K-Watch is limited to MOV and AVI)
- Batch convert via file picker in addition to Watch Folder service
- Built-in SWS preview and extraction tools

> **NOTE** MacHuna replicates the K-Watch conversion functionality. It does not replicate K-Manager Pro's network upload to mainframe or project synchronisation features.

---

## 2. Installation

MacHuna is distributed as a self-contained .app bundle. No separate software installation is required.

### 2.1 First Launch

- Copy MacHuna.app to your Applications folder or run it from any location
- On first launch, right-click the app and select Open to bypass macOS Gatekeeper
- Subsequent launches can be performed by double-clicking normally

> **NOTE** Gatekeeper may show a warning on first launch because the app is not signed with an Apple Developer certificate. This is expected for internal tools.

### 2.2 Settings

MacHuna saves all settings automatically on quit. Settings are stored at:

```
~/.kwatch_settings.json
```

Settings include Watch Folder path, Destination Folder path, video standard, all checkboxes, start number, window size, and Hula settings. To reset to defaults, delete this file.

---

## 3. Main Window

The MacHuna window is divided into four sections: Watch Folder, Destination Folder, Settings, and Batch Convert. A scrolling log area runs along the bottom.

### 3.1 Watch Folder

The Watch Folder is monitored continuously when the service is running. Any compatible file dropped into this folder is automatically detected and converted.

- Set the path using the Browse button or by typing directly
- TGA sequences must use the Watch Folder - batch convert does not support sequences
- Files are processed in the order they are detected

> **NOTE** K-Watch naming conventions apply for TGA sequences. See Section 5 for details.

### 3.2 Destination Folder

Converted .SWS files are written here. The folder is created automatically if it does not exist.

- For Watch Folder conversions, this is where .SWS files are placed
- For Batch Convert, this is also the destination
- The SWS Player file picker defaults to this folder for convenience

### 3.3 Settings

| Setting | Description |
|---|---|
| Video Standard | Select the target video standard. 1080i50 is the most common for UK/European broadcast. This must match the Kahuna's operating standard. |
| Split >4GB (FAT32) | Enabled by default. Files larger than 4GB are automatically split into 2GB chunks in the K-Watch split file format. Required for FAT32-formatted USB drives. |
| Delete source after conversion | If ticked, the source file is deleted after a successful conversion. Off by default. |
| Ignore alpha/key | If ticked, no key plane is written. The .SWS file contains fill only, with header fields zeroed to match K-Watch no-alpha behaviour. Use for fill-only content. |
| Include audio | On by default. Audio is extracted and embedded in the .SWS file where present in the source. See Section 6 for audio format details. |
| Auto play | Sets the Auto Play flag in the SWS header. The Kahuna will begin playback automatically when the clip is loaded. |
| Loop play | Sets the Loop Play flag in the SWS header. The Kahuna will loop the clip continuously. |

### 3.4 Start Watching / Stop

The Start Watching button launches the Watch Folder service. MacHuna monitors the Watch Folder in the background and converts files as they arrive. Click Stop to end the service.

> **NOTE** The service continues running until Stop is clicked or the application is quit. Quitting MacHuna while the service is running will stop the service cleanly.

---

## 4. Batch Convert

Batch Convert allows manual conversion of MOV, MP4, and still image files using a file picker. It is the recommended workflow for converting individual clips and stills outside of a watch folder environment.

### 4.1 Workflow

- Set the Destination Folder
- Set the Start Number - this is the file number assigned to the first converted file. Subsequent files are numbered sequentially.
- Click Open Files and select one or more files
- Files are sorted alphabetically and converted in that order
- A conversion log (.txt) is written to the Destination Folder on completion
- The Start Number field auto-increments after each batch for back-to-back sessions

> **NOTE** Batch Convert is for MOVs and single-frame stills only. TGA sequences must use the Watch Folder service.

### 4.2 Output Naming

- Stills: 1.SWS, 2.SWS, 3.SWS ...
- Clips: 1.SWS, 2.SWS, 3.SWS ...
- Large files (>4GB): a folder named 1.SWS containing 01_OF_03._XX, 02_OF_03._XX etc.

### 4.3 SWS Player Button

The SWS Player button opens the built-in preview player. See Section 7 for full details.

### 4.4 Hula Button

The Hula button opens the Hula SWS Extractor. See Section 8 for full details.

---

## 5. TGA Sequence Conversion

TGA sequences represent multi-frame clips stored as individual numbered still images. MacHuna converts them to .SWS clips via the Watch Folder service using the ffmpeg concat demuxer.

### 5.1 Naming Convention

MacHuna uses the K-Watch naming convention to identify TGA sequences. Files must be named:

```
NAME{NUM}[F][K][A]_{TOTAL}_{SEQ:04d}.TGA
```

For example: `wipe1FA_53_0001.TGA`, `wipe1FA_53_0002.TGA` ... `wipe1FA_53_0053.TGA`

| Part | Description |
|---|---|
| NAME | Clip name prefix (e.g. wipe) |
| {NUM} | File number (e.g. 1) |
| [F][K][A] | Optional flags: F=fill, K=key, A=audio |
| {TOTAL} | Total frame count |
| {SEQ:04d} | 4-digit zero-padded frame sequence number |

> **IMPORTANT** After the first character of the clip name, avoid using the letters A, F or K in upper case. The parser reads filenames right to left and will interpret them as Audio, Fill or Key flags, causing the sequence to be misidentified.

### 5.2 Alpha / Key Handling

- If the TGA files contain an alpha channel, the key plane is extracted automatically
- If no alpha is present and Ignore alpha is off, a solid white key plane is generated
- If Ignore alpha is ticked, no key plane is written regardless of alpha content

---

## 6. Audio

MacHuna extracts audio from source files and embeds it in the .SWS file in the K-Watch native format.

### 6.1 Audio Format

| | |
|---|---|
| Encoding | 16-bit signed little-endian PCM |
| Sample rate | 48,000 Hz |
| Channels | 16 channels interleaved |
| Channel mapping | Ch1 = Left, Ch3 = Right, all others silent (K-Watch convention) |
| Samples per frame | 48000 / fps (e.g. 960 at 50fps, 1920 at 25fps) |

### 6.2 Notes for Engineers

- Audio is appended after the key plane in the .SWS file
- The channel mapping (L=Ch1, R=Ch3) is confirmed by hex analysis of K-Watch reference files. A straight ffmpeg -ac 16 upmix is incorrect - MacHuna uses an explicit pan filter.
- Audio detection in third-party .SWS files uses the audio offset and format flag fields (0x1E8 and 0x1EC). The audio frame size field (0x1C2) is unreliable across workflows and is not used.
- TGA sequence audio is not supported.

---

## 7. SWS Preview Player

The built-in SWS Player allows preview of any .SWS file directly from MacHuna without needing a Kahuna mainframe. It is launched via the SWS Player button in the Batch Convert row.

### 7.1 Display Layout

The player shows four panels:

- **Fill** - the video content plane
- **Key** - the alpha/key plane (greyscale)
- **Composite** - fill composited over a chequerboard using the key as alpha, showing transparency
- **Audio** - VU meters for left and right channels

### 7.2 Transport Controls

| Control | Action |
|---|---|
| Cue | Return to the first frame |
| Play | Begin playback at the clip's native frame rate |
| Pause | Pause at the current frame |
| Stop | Stop and return to the first frame |

### 7.3 Notes

- Multiple player windows can be open simultaneously
- The file picker defaults to the configured Destination Folder
- Audio playback requires sounddevice to be installed (`pip3.12 install sounddevice`). If not installed, the player opens without audio but metering is still shown.
- Split .SWS files (>4GB, multi-chunk) are not currently supported in the player

---

## 8. Hula SWS Extractor

Hula converts .SWS files back to standard media formats for use on other vision mixing desks. It is launched via the Hula button in the Batch Convert row.

Hula is also available as a standalone application ([DNSVision/Hula](https://github.com/DNSVision/Hula)) for use on machines without MacHuna.

### 8.1 Output Targets

| Target | Format | Use |
|---|---|---|
| Kayenne MOV | ProRes 4444 with embedded alpha channel. BT.709. Audio muxed where present. | Grass Valley Kayenne ClipStore or Image Store |
| Kayenne TGA | 32-bit RGBA TGA sequence. Frames numbered 0001.tga onwards. Subfolder per clip. | Grass Valley Kayenne Image Store |
| Sony MVS TGA | 32-bit RGBA TGA sequence. Frames numbered XXXX0000.tga onwards where XXXX is a 4-character clip name. Subfolder per clip. | Sony MVS Image Store |

### 8.2 Workflow

- Set a Destination Folder
- Select one or more .SWS files using Open Files
- Select the output target
- For Sony MVS TGA, enter a 4-character alphanumeric clip name (e.g. WIPE)
- Click Convert

### 8.3 Output Structure

TGA outputs are written to subfolders named after the source SWS file stem, inside the chosen Destination Folder. MOV outputs are written flat into the Destination Folder, numbered 0001.mov, 0002.mov etc.

### 8.4 Sony MVS Clip Name

The Sony MVS groups all TGA files sharing the same 4-character name prefix into a single clip on import, sorted by the numeric prefix. Import each subfolder separately on the desk to keep clips distinct. All clips in a single Hula batch share the same clip name - a warning is shown in the UI.

### 8.5 Kayenne TGA Notes

Frames are numbered 0001.tga onwards. The first frame must not be 0000 - this is a confirmed Kayenne requirement. The Seq button must be enabled on the desk when loading.

### 8.6 ProRes 4444 Quality

A round trip from .SWS to ProRes MOV and back to .SWS will produce a small amount of image degradation due to the YCbCr/RGB/YCbCr conversion and ProRes encoding. ProRes 4444 is a high-quality intermediate format and the degradation per generation is very small. For production use, a single conversion pass is the intended workflow.

---

## 9. Large File Support (>4GB)

Files larger than 4GB are automatically split into 2GB chunks when the Split >4GB option is enabled (on by default). The split format exactly matches K-Watch output and has been confirmed working on a live Kahuna mainframe.

### 9.1 Split File Structure

```
1.SWS/
  01_OF_03._XX   (header + video data, exactly 2GB)
  02_OF_03._XX   (video data, exactly 2GB)
  03_OF_03._XX   (video data, remainder)
```

- Chunk 1 contains the 512-byte header followed by video data
- All subsequent chunks contain raw video data only
- The header in chunk 1 carries the total frame count across all chunks
- Audio is not supported in split files

> **NOTE** When transferring to Kahuna via USB, the entire .SWS folder (e.g. 1.SWS/) must be copied, not the individual chunk files.

---

## 10. SWS Format Reference

This section is intended for support engineers and developers. It documents the SWS binary format as reverse-engineered from K-Watch reference files and verified on a live Kahuna mainframe.

### 10.1 File Layout

| Offset | Content |
|---|---|
| 0x000 - 0x1FF | 512-byte header (big-endian) |
| 0x200 - N | Fill plane: v210 big-endian, plane_size x frame_count bytes |
| N - M | Key plane: v210 big-endian, same size as fill plane (absent if play_count == 0) |
| M - EOF | Audio data: 16-bit LE PCM, 16ch, 48kHz (absent if audio offset == 0) |

### 10.2 Key Header Fields

| Offset | Type | Description |
|---|---|---|
| 0x188 | uint32 BE | Video standard code (OR'd with playback flags) |
| 0x190 | uint32 BE | Width in pixels |
| 0x194 | uint32 BE | Height in pixels |
| 0x1A0 | uint32 BE | Plane size (bytes per frame) |
| 0x1A4 | uint32 BE | Frame count |
| 0x1A8 | uint32 BE | Play count (= frame count; 0 if no key plane) |
| 0x1B4 | uint32 BE | (plane_size x frame_count + 512) / 32; 0 if no key |
| 0x1C2 | uint16 BE | Audio frame size: 0x1680 if audio present (unreliable - do not use for detection) |
| 0x1CC | uint32 BE | Total file size |
| 0x1E8 | uint32 BE | Audio data offset / 32 (0 if no audio) |
| 0x1EC | uint32 BE | Audio format flag: 0x03000000 if audio present |

### 10.3 Audio Detection

Reliable audio detection: aud_offset (0x1E8) > 0 AND aud_fmt (0x1EC) == 0x03000000. The audio frame size field at 0x1C2 is not reliable - K-Watch writes 0x1680, but third-party tools may write different values.

### 10.4 Playback Flags

Bits 2 (0x04) and 3 (0x08) of the low byte at 0x188 are OR'd into the video standard code:

- Bit 2 (0x04): Auto Play
- Bit 3 (0x08): Loop Play

Example for 1080i50 base code 0x4923: Auto Play only = 0x4927, Loop Play only = 0x492B, both = 0x492F.

---

## 11. Troubleshooting

### Watch Folder not picking up files

- Confirm the service is running (Start Watching button should be greyed out, Stop should be active)
- Check the file naming convention if converting TGA sequences - files must match the K-Watch pattern
- Check the Log area for error messages

### Batch Convert not converting

- For Watch Folder conversion, MOV/MP4 filenames must end with a number (e.g. Clip1.mov). This is not required for Batch Convert via Open Files.
- Check the Destination Folder is set
- Check the Log for ffmpeg errors

### Kahuna showing black key / no key

- If Ignore alpha is ticked, no key plane is written - this is correct behaviour
- If the source file has no alpha channel and Ignore alpha is off, a solid white key is generated automatically
- Check source file has a valid alpha channel if a real key is expected

### Audio not playing on Kahuna

- Confirm Include audio is ticked in Settings
- Confirm the source file has an audio track
- Audio is 16-bit LE PCM at 48kHz. If the source is at a different sample rate, ffmpeg resamples automatically

### File >4GB not loading on Kahuna

- Confirm Split >4GB is enabled
- Ensure the entire .SWS folder (e.g. 1.SWS/) is copied to the USB drive, not individual chunk files
- FAT32-formatted USB drives are required for split files

### Hula - MOV not recognised by MacHuna

- Hula-generated MOVs use the ProRes 4444 codec with embedded alpha
- When converting back via MacHuna Batch Convert, ensure the file is named with a trailing number (e.g. Clip1.mov)
- For Watch Folder conversion, the K-Watch naming convention applies

---

## 12. Known Limitations

- Apple Silicon only - Intel Mac builds are not supported
- Split .SWS files (>4GB) cannot be previewed in the SWS Player
- TGA sequence audio is not supported
- HLG Rec.2020 colour space is not implemented (requires a reference HLG .SWS file to verify header values)
- Sony MVS 50i output is not yet implemented - planned for a future release

---

## 13. Related Projects

- [DNSVision/MacHuna](https://github.com/DNSVision/MacHuna)
- [DNSVision/Hula](https://github.com/DNSVision/Hula) - standalone SWS extractor

---

## 14. Authors

David Steer / DNS Vision Limited & Claude (Anthropic)

MacHuna was built collaboratively using AI-assisted development. The SWS format was reverse-engineered from K-Watch reference files and verified against a live Grass Valley Kahuna mainframe.
