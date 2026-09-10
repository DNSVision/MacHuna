# MacHuna v1.9.0 — User Manual

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
11. [Updates and Getting in Touch](#11-updates-and-getting-in-touch)
12. [Large File Support (>4GB)](#12-large-file-support-4gb)
13. [SWS Format Reference](#13-sws-format-reference)
14. [Troubleshooting](#14-troubleshooting)
15. [Known Limitations](#15-known-limitations)
16. [Authors](#16-authors)

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
| Kayenne TGA | `.SWS`, `.EIF` | 32-bit RGBA TGA sequence *(UNCONFIRMED on hardware)* |
| Sony TGA | `.SWS`, `.EIF`, TGA sequences | 32-bit RGBA TGA sequence (Sony MVS naming) |
| TGA Sequence | TGA sequences, video clips | 32-bit RGBA TGA sequence (i↔p standards conversion) |

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

**Download it from [dnsvision.tv/machuna](https://dnsvision.tv/machuna).** That page always carries the current release, the release notes and this manual.

### 2.1 First Launch

MacHuna is not signed with an Apple Developer certificate, so the first time you open it macOS says it cannot verify the developer and refuses. This is expected. Three steps, once per machine:

1. Move **MacHuna.app** to your **Applications** folder and double-click it. macOS shows a warning and will not open it. Click **Done**
2. Open **System Settings ▸ Privacy & Security** and scroll down. There is a line about MacHuna being blocked, with an **Open Anyway** button. Click it and confirm with Touch ID or your password
3. MacHuna opens, and opens normally from then on

> **NOTE** Older instructions said to right-click the app and choose **Open**. That no longer works on current versions of macOS, which removed the shortcut: you have to go through System Settings as above.

**Checking which version you have.** MacHuna's title bar shows it, and **Help ▸ Check for Updates…** tells you whether it is the current release. In Finder, select `MacHuna.app` and press ⌘I: the version is shown in the Get Info panel, and the title bar shows it once running. Before v1.6.20 the bundle reported its version as 0.0.0, so if Get Info says 0.0.0 you are running v1.6.19 or earlier. This matters if you keep more than one copy of the app.

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
| **Convert** | Add files, choose output format, set what each one is called, convert |
| **Log** | Conversion progress and errors, five lines |

The Convert row adapts automatically based on what files you open. MacHuna detects the input type and shows only the controls that are relevant.

The **item list** in the middle of the Convert row takes whatever height the window has spare, so making the window taller shows more rows at once. The log stays at five lines: the rows themselves now carry the outcome of a conversion, and the full record is written to the log file in your Destination Folder.

---

## 4. Converting Files

The workflow is the same regardless of what you are converting or what you are converting it to:

1. Set your **Destination Folder**
2. Click **Open Files…** and select a folder. Once something is loaded the button reads **Add Files…**, since you are usually adding to the list rather than starting again
3. MacHuna scans the folder, detects the input type, and populates the item list
4. Choose your **Output** format from the dropdown
5. Set any options that appear (standard, field order, etc.)
6. **Give each row a number or name**, or tick **Number sequentially** — see Section 4.4
7. Click **Convert**

A conversion log is written to the Destination Folder when the batch completes.

### 4.1 Input Type Detection

MacHuna reads the contents of the folder you open and determines the input type automatically:

| Files found in folder | Detected as | Available outputs |
|---|---|---|
| `.SWS` files only | SWS source | Kahuna SWS, Kayenne TGA, Kayenne EIF, Sony TGA |
| `.EIF` files only | EIF source | Kahuna SWS, Kayenne TGA, Sony TGA |
| Mix of `.EIF` and `.SWS` files | EIF + SWS source | Kahuna SWS, Kayenne TGA, Sony TGA |
| Video files only (MOV, MP4, MXF…) | Video source | Kahuna SWS, Kayenne TGA, Kayenne EIF, Sony TGA, TGA Sequence |
| TGA sequences and/or stills | TGA / stills source | Kahuna SWS, Kayenne EIF, Sony TGA, TGA Sequence — see note below |
| Mix of SWS and other files | Error — shown in summary | — |

> **NOTE** If you see a "mixed input" error, the folder contains both `.SWS` files and other file types. Move them into separate folders and convert each folder independently.

> **NOTE — stills go to Kahuna SWS only.** A still image is a single frame, not a clip, so MacHuna does not convert stills to Kayenne EIF, Sony TGA or TGA Sequence output. Those outputs need a clip or a TGA sequence. If a still is selected with one of them, MacHuna names the file and stops rather than converting it. Deselect the still, or choose Kahuna SWS. A folder holding both stills and TGA sequences is fine: select the sequence and leave the stills unticked.

### 4.2 The File List

The file list shows one entry per item to be converted:

- **TGA sequences** are collapsed to a single line: `TNTS201  (30 frames)` — you do not need to select individual frames
- **Video files** appear by filename
- **Stills** appear by filename
- **EIF files** appear by filename

Click entries to select or deselect them. By default, all files are selected.

**Building a batch from more than one folder (v1.6.15).** Once you have a selection, opening another folder gives you two buttons:

- **Select** — replaces the list with what you have chosen here (the original behaviour)
- **Add to List** — appends it to what is already selected

So you can take two files from one folder, one from another, and convert all three in a single batch. Items already in the list are not added twice, and the summary line next to **Open Files…** reports the whole selection (e.g. `2 folders: 3 video files`).

One batch has to be one kind of job, so you can only add items of a compatible type: media being encoded **to** SWS, or SWS/EIF files being extracted **back out**. Trying to mix the two is refused with an explanation — use **Select** to start a fresh list instead. Adding EIF files to SWS files (or the reverse) is fine.

Cancelling the folder browser leaves your current selection untouched.

### 4.3 The Item List

Once files are selected, MacHuna shows **one row per item**, and that row tells you what the item is about to be called:

```
  BAY-PSG-50HD.mov        [ 200 ]   → 200.SWS            ✕
  EPL-ARS-50HD.mov        [ 201 ]   → 201.SWS            ✕
  TNTS201  (30 frames)    [ 202 ]   → 202.SWS            ✕
```

This replaced the old **Start number** and **Start slot** boxes in v1.8.0. Before that, batch numbering was invisible: you set a starting number, pressed Convert, and found out what each file had been called by reading the log afterwards. Now you can see it, and change it, before anything is written.

The list appears for **every** output, not only numbered ones. Kayenne TGA and TGA Sequence name their output from the source filename, so those rows are shown greyed and read‑only — you cannot change them, but you can see what you are getting.

### 4.4 Numbering

**Type a number into each row**, or tick **Number sequentially** and let MacHuna fill them in.

| | |
|---|---|
| **Number sequentially, ticked** | A number appears in the first row and the rest follow from it. Change the first row and everything below re‑numbers. The other rows are locked until the first has a value, so it is clear where to type |
| **Unticked** | Every row is yours to fill in. This is the default: filling a scattered set of empty slots on the desk is at least as common as numbering a batch straight through |

The setting is remembered between sessions. The **numbers are not** — every batch starts from 1 unless you say otherwise.

> **Why numbers do not carry over.** Until v1.8.0 the Start number advanced automatically after each batch and persisted between sessions. That only made sense while the numbers were invisible: wipes rarely stay in the destination folder, so carrying on from where the last batch finished was usually noise. Now that every number is on screen before you convert, there is nothing to remember on your behalf.

**Sony MVS TGA** works the same way but takes a **4‑character clip name** per row instead of a number, and has no sequential option — names cannot sensibly be counted upwards.

**Kayenne EIF** takes a slot number per row and writes `0001.eif`, `0002.eif` and so on.

#### Checks before anything is written

Three checks run when you press Convert, and any of them stops the batch:

1. **Nothing may be blank**, or outside 1–9999
2. **No two rows may share a number or name**
3. **Nothing may collide with the destination folder** — an existing `12.SWS`, whether a file or a split‑file folder, an existing `0012.eif`, or a Sony clip‑name folder

There is no overwrite option. Every offending row is marked in red with the reason (`duplicate number`, `already in destination`), the list scrolls to the first one and puts the cursor in it, and correcting a duplicate clears its partner's mark too.

### 4.5 After Converting

**The list stays on screen.** Converted rows lock and show **✓ done**; anything that failed shows **✗** and the reason.

```
  BAY-PSG-50HD.mov        [ 200 ]   ✓ done              ✕
  EPL-ARS-50HD.mov        [ 201 ]   ✓ done              ✕
  TNTS201  (30 frames)    [ 202 ]   ✗ no video stream   ✕
```

**Convert only ever runs rows without a status**, so nothing is converted twice. You can add more files to a finished batch and press Convert again: only the new ones run, and if you are numbering sequentially they carry on from the highest number in the list rather than starting again.

- **✕** removes a single row. With sequential numbering on, the rows below close the gap; with your own numbers typed, they keep them. A converted row never renumbers — the file it wrote already exists
- **Clear All**, below the list, empties everything and starts again

> **Nothing is converted twice.** Before v1.8.0, MacHuna emptied the list after every conversion to guarantee this, because items could only ever be *added* to a selection. Locking converted rows gives the same guarantee while keeping the list as a record of what was done.

### 4.6 Cancel

Click **Cancel** during a conversion to stop after the current file. The conversion log is not written if cancelled mid-batch.

---

## 5. Kahuna SWS Output

When outputting to Kahuna SWS, the following options are available:

| Option | Description |
|---|---|
| **Standard** | Target video standard. 1080p/50 is most common for UK/European broadcast. |
| **Split >4GB** | On by default. Files over 4GB are split into 2GB FAT32-safe chunks. See Section 12. |
| **Ignore alpha** | No key plane is written. Output is fill-only, matching K-Watch no-alpha behaviour. Use for fill-only content or when the Kahuna output does not use a downstream keyer. |
| **Auto play** | Sets the Auto Play flag in the SWS header. The Kahuna begins playback when the clip is loaded. |
| **Loop play** | Sets the Loop Play flag in the SWS header. The Kahuna loops the clip continuously. |
| **TGA source interlaced** | See Section 8.2. |
| **Include audio** | Embeds audio from the source into the .SWS file. Shown only when audio is detected in the source. See Section 9. |

> **SWS → SWS standards conversion:** when the source is itself an SWS file, the output header's clip name follows the source SWS's name, and the output key state follows the source (a keyless source produces keyless output). **Audio is not carried through an SWS → SWS conversion** — if the source SWS contains embedded audio, it is dropped and a warning is written to the log.

### 5.1 Progressive to Interlaced (P→I)

When converting a progressive source to an interlaced standard, MacHuna field-weaves pairs of progressive frames into genuine interlaced frames. The frame count halves — a 50fps progressive source becomes 25fps interlaced output. This is the correct behaviour for the Kahuna.

Example: 100 frames of 1080p/50 source → 50 frames of 1080i/50 output.

**The source must run at the interlaced field rate (double the frame rate).** Weaving pairs of frames only keeps the right duration when the source is a genuine field-rate stream:

| Progressive source | Interlaced target | Result |
|--------------------|-------------------|--------|
| 50p | 1080i/50 | ✅ correct — weaves to 25 interlaced frames |
| 59.94p | 1080i/59.94 | ✅ correct |
| 60p | 1080i/60 | ✅ correct |
| 25p | 1080i/50 | ⛔ blocked — would play at 2× speed |
| 29.97p | 1080i/59.94 | ⛔ blocked |
| 30p | 1080i/60 | ⛔ blocked |

If you give MacHuna a **same-rate** progressive source (e.g. a 25p file destined for 1080i/50) or any other incompatible rate, it will **stop with a clear error and write no file**, rather than silently produce a clip that plays at the wrong speed. Convert the source to the correct field rate first (e.g. 25p → 50p), or choose a progressive output standard. *(This rate check applies to video-clip, SWS→SWS and clip→TGA conversions, which carry a known frame rate. A loose TGA image sequence has no frame rate to check and is still assumed to be a double-rate field stream.)*

### 5.2 Interlaced to Progressive (I→P)

When converting an interlaced source to a progressive standard, MacHuna bob-deinterlaces to produce the correct number of progressive frames. Playback speed on the Kahuna is preserved.

Example: 50 frames of 1080i/50 source → 100 frames of 1080p/50 output.

**Cross-rate conversions (corrected in v1.6.12).** Deinterlacing doubles the frame count, which lands on the target rate exactly only when the progressive standard is double the interlaced source's frame rate — 1080i/50 → 1080p/50, or 1080i/59.94 → 1080p/59.94. Any other pairing needs a rate change on top, and before v1.6.12 MacHuna did not apply one, so the clip played fast or slow:

| Source | Target | Before v1.6.12 | Now |
|---|---|---|---|
| 1080i/50 | 1080p/50 | correct | correct |
| 1080i/50 | 1080p/60 | ran fast | correct |
| 1080i/59.94 | 1080p/50 | ran fast | correct |
| 1080i/59.94 | 1080p/25 | ran 20% slow | correct |

This applies to video clips, SWS→SWS, and TGA outputs. **A loose TGA image sequence is the exception:** it carries no frame rate anywhere, so MacHuna assumes the source standard matches the output family you pick (an interlaced pile aimed at 1080p/50 is treated as 1080i/50 material). That assumption is right for normal use. If you are converting a TGA sequence across families — interlaced 50Hz frames aimed at a 60Hz progressive standard — convert via a video clip or SWS instead, so MacHuna has a real frame rate to work from.

---

## 6. Kayenne EIF — Native Kayenne Format

> **EIF clips have no audio (v1.7.1).** Kayenne stores clip audio in a companion `.eaf` file, and that format has not been worked out yet — no real `.eaf` has ever been available to analyse. `has_audio` is always false, so **any audio on your source is dropped when converting to EIF**. MacHuna warns you in the log when the selection contains audio. This is a missing feature rather than a fault, and it is the one thing in this manual that is *known* not to work rather than merely untested. If you can supply a `.eaf` file from a Kayenne clip that has audio, that alone would unblock it: **machuna@dnsvision.tv**.

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
| **Slot (per row)** | Each row in the item list carries its own slot number, written as `0001.eif`, `0002.eif` and so on. Tick **Number sequentially** to fill them in from the first row. See Section 4.4. |
| **TGA source interlaced** | Shown when source is a TGA sequence. Tick when TGA frames are from an interlaced source. MacHuna deinterlaces each frame using yadif (field separation, TFF) to produce 50fps progressive EIF output. |

EIF output is always 1920×1080. Sources of other sizes are scaled. Frame rate is rounded to the nearest EIF-supported rate (25fps or 50fps), and the video is resampled to that rate so the clip keeps its original duration and plays at the correct speed — for example a 60fps source becomes a 50fps EIF clip of the same length.

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
> The extraction output paths have been confirmed correct by code analysis. However, Kayenne TGA output has **never been loaded on a live Kayenne desk**, and Sony TGA clip naming has **never been verified on a live Sony MVS**. MacHuna will warn you before converting to these targets. Use with that caveat in mind and verify the first import on your desk carefully.
>
> *(The former Kayenne MOV output was withdrawn in v1.6.5 — it was never confirmed on hardware and could not be offered consistently across input types.)*

### 7.1 Output Targets

| Output | Format | Destination desk |
|---|---|---|
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

A **TFF / BFF** toggle appears for interlaced standards, and always for Sony TGA. **TFF (Top Field First) is the default** — it is the SMPTE standard for HD (including 1080i) and is correct for all known 1080i HD workflows (default since v1.6.3). If you see motion artefacts or comb effects on the desk after import, switch to BFF and reconvert.

> **Fixed in v1.6.12.** For Sony TGA output from a TGA sequence or a video clip, this toggle was displayed but had no effect — the conversion was hardcoded to TFF, so switching to BFF changed nothing in the output. It now works in both conversion directions, and the conversion log states which field order was applied, so you can confirm what was used. If you tested Sony TGA output before v1.6.12 and concluded BFF did not help, that test was not valid and is worth repeating.

### 7.5 Sony TGA — Clip Name

Enter a **4-character alphanumeric clip name** (e.g. `WIPE`). All TGA frames in the batch share this name — on the Sony MVS, files with the same 4-character prefix are grouped into a single clip on import.

**Each clip takes its own 4‑character name from the item list** (see Section 4.4), so each becomes its own output folder and several Sony clips convert together. The shared Clip name field that once forced one clip at a time is gone as of v1.8.0.

### 7.6 Output Structure

| Output | File naming |
|---|---|
| Kayenne TGA | Subfolder per SWS, named after the SWS stem. Frames `0001.tga` … inside. |
| Sony TGA | Subfolder per SWS, named after the 4-character clip name. Frames `XXXX0000.tga` … inside. |

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

### 8.3 TGA Sequence Output

When the input is a TGA sequence or a video clip, **TGA Sequence** appears as an output option. This re-writes the frames as a new numbered TGA sequence in a subfolder, applying an interlaced↔progressive conversion according to the selected **Standard** — useful for converting a sequence between field standards without going through SWS. Progressive→interlaced uses field-weaving (`tinterlace`); interlaced→progressive uses yadif deinterlacing. Both follow the **Field order** toggle where it is shown, and default to TFF otherwise. The alpha/key channel is preserved throughout.

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
| `.SWS` **split files** (a folder of `01_OF_03._XX` parts) | Yes | Split files carry no audio |
| `.EIF` (Kayenne native) | Yes — fill, key, and composite all populated | No |
| `.TGA` sequence (pick any frame) | Yes (if TGAs have alpha) | No |
| `.MOV`, `.MP4`, `.MXF`, `.MKV`, `.AVI` | Yes (alpha preserved for ProRes 4444 etc.) | Yes |

Click **Open…** and select a file. For TGA sequences, pick any frame from the sequence — MacHuna loads the whole sequence.

**Split files (v1.9.0).** A clip over 4GB is stored as a *folder* named `<n>.SWS` containing `01_OF_03._XX`, `02_OF_03._XX` and so on. **Select the folder if your file dialog lets you, or open it and pick any one of the parts** — either loads the entire clip, not just the part you clicked. The info strip confirms it with `Split: 3 parts`. Before v1.9.0 these could not be opened at all: the dialog treats the folder as somewhere to navigate into, so you reached a single chunk, and only the first chunk carries a header. When opening a TGA sequence, you will be prompted for the frame rate (25fps default). For EIF files, the frame rate is detected automatically from the header.

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

### 10.4 Playback Stutter

**Playback can stutter for the first few plays of a clip, then settles.** This is a limitation of the player, not a fault in your file — if a clip stutters on the first pass and plays cleanly on the second, the clip is fine.

The player exists as a confidence check: to see that a clip is what you expected before it goes to a desk. It is not a broadcast playout tool, and smooth first-pass playback would need it rebuilt around a proper media view. That is a job for the native rewrite rather than something to patch here.

### 10.5 Notes

- Multiple player windows can be open simultaneously
- Split `.SWS` files (>4GB, multi-chunk) cannot currently be previewed
- Audio playback uses the sounddevice library. If not installed, the player opens without audio but VU meters are still drawn

---

## 11. Updates and Getting in Touch

Everything in this section lives in the **Help** menu, which is new in v1.7.0.

### 11.1 The Help Menu

| Item | What it does |
|---|---|
| **MacHuna User Manual** | Opens this document. It is bundled inside the app, so it works with no internet and always matches the version you are running |
| **Check for Updates…** | Checks now, and always tells you the result |
| **Report a Problem…** | Opens an email with the details already filled in |
| **Suggest a Feature…** | The same, for things MacHuna does not do yet |

### 11.2 Update Notifications

A few seconds after MacHuna opens, it reads a small file at `dnsvision.tv/machuna/version.json` in the background to see whether a newer version exists. This never delays the window opening.

**If a newer version is available**, a strip appears across the top of the MacHuna window with the version number, a line about what changed, a **Download** button and a **Dismiss** button. Download opens the download page in your browser; MacHuna never installs anything itself.

**If you are up to date, offline, or the check fails for any reason, nothing at all appears.** No error, no delay, no message. This is deliberate. MacHuna is used in OB trucks and galleries with no route to the internet, and an app that hangs on startup or nags about a network it cannot reach would be worse than useless. The request gives up after five seconds and is forgotten.

**Dismiss** hides the strip for that session. Choosing **Check for Updates…** from the menu shows it again, because asking is a request to be told.

> **What is actually sent: nothing about you.** MacHuna reads one small public file and nothing else. It sends no information about you, your machine, your files or your conversions, and there is no usage tracking of any kind. The request is an ordinary web fetch, the same as opening a page in a browser.

**Check for Updates…** does the same check but always reports back: a newer version, "You're on the latest version", or "Couldn't check for updates just now". Only the automatic check on launch is silent.

### 11.3 Hardware-Status Notices

Some of MacHuna's outputs have been confirmed on the desk they are for, and some have not. From v1.7.1 the log says which, at the head of every batch.

| Output | What the log says |
|---|---|
| **Kahuna SWS** | Nothing. It is confirmed on a live Kahuna mainframe across all seven standards, so a warning would be false caution |
| **Kayenne EIF, Kayenne TGA, Kayenne MOV, Sony MVS TGA** | A note that the output has never been loaded on that desk, and an invitation to get in touch if you can test it |
| **Kayenne EIF, when the source has audio** | An additional note that the audio is being dropped — see Section 6 |

These are notes, not errors. Nothing is blocked and no dialog appears. The conversion runs exactly as it always did; you are simply told where it stands so you can decide whether to check the result before trusting it on air.

The full status of every output is also published at [dnsvision.tv/machuna](https://dnsvision.tv/machuna).

### 11.4 Reporting a Problem

**Help ▸ Report a Problem…** opens a panel showing exactly what is about to be shared, then hands it to your own mail app as a draft.

The draft arrives already carrying the things that otherwise take three emails to establish: the MacHuna version, your macOS version, your Mac model, and the standard, output format and source files you had selected. You write what happened in your own words in the spaces at the top.

Three buttons:

- **Open Email** — opens the draft in your mail app. **Nothing is sent until you send it.** You can edit or delete any part of it first, and on a truck with no signal it simply waits in your outbox
- **Copy Details** — copies the same text to the clipboard, for anyone whose Mac has no mail app set up
- **Show Log in Finder** — appears when a conversion log exists in your destination folder. That log usually answers the question on its own, so attaching it helps

**Suggest a Feature…** is the same panel with different prompts, for a format, a standard or a naming convention your facility needs.

Both go to **machuna@dnsvision.tv**.

---

## 12. Large File Support (>4GB)

Files larger than 4GB are automatically split into 2GB chunks when **Split >4GB** is enabled (on by default). The split format exactly matches K-Watch output and has been confirmed working on a live Kahuna mainframe.

### 12.1 Split File Structure

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

## 13. SWS Format Reference

This section is for support engineers and developers. It documents the SWS binary format as reverse-engineered from K-Watch reference files and verified against a live Grass Valley Kahuna mainframe.

### 13.1 File Layout

| Range | Content |
|---|---|
| `0x000 – 0x1FF` | 512-byte header (big-endian) |
| `0x200 – N` | Fill plane: v210 big-endian, `plane_size × frame_count` bytes |
| `N – M` | Key plane: v210 big-endian, same size as fill plane (absent if `play_count == 0`) |
| `M – EOF` | Audio data: 16-bit LE PCM, 16ch, 48kHz (absent if audio offset == 0) |

### 13.2 Key Header Fields

| Offset | Type | Description |
|---|---|---|
| `0x188` | uint32 BE | Video standard code (OR'd with playback flags — see 13.4) |
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

### 13.3 Audio Detection

Reliable method: `aud_offset (0x1E8) > 0` AND `aud_fmt (0x1EC) == 0x03000000`.

Do not rely on the audio frame size field at `0x1C2`. K-Watch writes `0x1680`, but third-party tools may write different values. MacHuna uses the offset and format flag fields for all audio detection.

### 13.4 Playback Flags

Bits 2 (`0x04`) and 3 (`0x08`) of the low byte at `0x188` are OR'd into the video standard code:

| Flag | Bit | Value |
|---|---|---|
| Auto Play | 2 | `0x04` |
| Loop Play | 3 | `0x08` |

### 13.5 Interlaced Flag

Bit 15 (`0x8000`) of `0x188` is set for all interlaced standards. The standard code for all interlaced formats is `0xC923`.

---

## 14. Troubleshooting

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

- Note that Kayenne TGA output has not been confirmed on a live Kayenne desk
- Sony TGA clip naming has not been confirmed on a live Sony MVS
- Check that the correct Standard is selected for the target desk's video format
- For Sony TGA: confirm the 4-character clip name matches your expected import workflow
- For interlaced output: if motion artefacts appear, try switching the Field Order toggle (TFF ↔ BFF; TFF is the default)

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

## 15. Known Limitations

- **Apple Silicon only** — Intel Mac builds are not supported
- **Split .SWS files** cannot be previewed in the Video Player
- **TGA sequence audio** is not supported
- **HLG Rec.2020** colour space is not implemented (requires a reference HLG .SWS file to reverse-engineer the header values)
- **EIF write and conversion** — coded and working by analysis, but not yet confirmed on a live Kayenne desk. MacHuna warns before converting to or from EIF. Verify your first import carefully.
- **EIF audio** — companion `.eaf` audio files used by some Kayenne clips are not currently supported. EIF files are always loaded without audio in the Video Player.
- **Extraction outputs unconfirmed on hardware** — Kayenne TGA and Sony MVS TGA naming have not been verified on live desks. MacHuna will warn you before converting to these targets.
- **Kayenne MOV output withdrawn** (v1.6.5) — it was never confirmed on hardware; use Kayenne TGA or Kayenne EIF instead.

---

## 16. Authors

David Steer / DNS Vision Limited & Claude (Anthropic)

MacHuna was built collaboratively using AI-assisted development. The SWS format was reverse-engineered from K-Watch reference files and verified against a live Grass Valley Kahuna mainframe. The Kayenne EIF format was reverse-engineered from real Kayenne-produced clips.
