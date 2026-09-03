# Changelog — MacHuna

All notable changes to MacHuna are documented here.

---

## v1.6.18 — 2026-09-03

### Fixed
- **A resolved duplicate now clears both rows, not just the one you edited.** With two items set to the same number, correcting one left the *other* still showing `duplicate number` — a stale warning about a problem that no longer existed. Editing a field now re-checks the whole batch rather than only its own row, which is what a duplicate needs: it is a relationship between two rows, so fixing one half frees the other. A three-way clash behaves correctly too — fix one and the remaining pair stay marked, because they are still duplicates of each other. A marked row can also change its reason live (edit a duplicate into a number that already exists in the destination and it switches to `already in use`).
  - The re-check only refreshes rows that are **already** marked, so typing never turns a field red before you have tried to convert. Blank fields are the normal starting state, not something to warn about.
- Resetting the panel now destroys the old row widgets rather than only forgetting about them. They were invisible either way, but they held their old values and marks until something happened to trigger a rebuild.

---

## v1.6.17 — 2026-09-03

### Added
- **A blocked bespoke batch now takes you to the field that needs fixing.** Naming the offending items in the dialog was not much help when only four or five rows are visible at a time. Now, on top of the message:
  - every offending field's hint turns red and says what is wrong with *that* row — `needs a number`, `duplicate number` or `already in use` (`needs a name` / `duplicate name` for Sony TGA), while valid rows keep their neutral grey hint, so scrolling the panel shows exactly what is outstanding;
  - the panel scrolls to the **first** offending row and puts the cursor in its field;
  - typing in a marked field clears its own mark straight away, so the red marks left are the work remaining.
- New `bespoke_row_issues()` returns the per-row problem codes, alongside the existing grouped messages from `validate_bespoke_ids()`. Both are now thin wrappers over one shared analysis pass, so the dialog text and the field marks can never disagree.

### Fixed
- **Issue text no longer truncates.** The panel is measured once when the rows are built, at which point every hint reads `1-9999`; a longer mark such as `duplicate number` then needed more width than the canvas had been given and was clipped to `duplicat…`. The hint column now reserves a fixed width sized for the longest message, so nothing clips and — just as importantly — marking a field never shifts the layout sideways.

### Notes
- **The panel height stays fixed.** Growing it to fit the list was considered and rejected: it only moves the problem to "what happens when the list is taller than the window", which needs a resizable or paged layout rather than a taller frame. That is a job for the planned SwiftUI rewrite; jump-to-field makes the fixed height workable in the meantime.

---

## v1.6.16 — 2026-09-03

### Changed
- **Unticking the bespoke checkbox now clears the whole selection, not just the typed values.** It is the "start over" gesture: the file list, the folders it came from, the detected input type and the typed IDs all go, the summary returns to "No files selected." and Convert greys out. A log line says so, so the list is not seen to vanish without explanation. This is what stops a selection only ever growing — since v1.6.15 items can be *added* to a list, so there needed to be one clear way to empty it. **Open Files… → Select** still replaces the list without clearing anything else.

---

## v1.6.15 — 2026-09-03

### Added
- **Build a batch up from several folders — "Add to List".** The folder browser now offers a second button whenever something is already selected: **Select** replaces the list as before, **Add to List** appends to it. Open a folder, take two files, open another folder, take one more, and you have a three-item batch with three bespoke rows. Items already in the list are not added twice, and the summary line reports the combined selection (`2 folders: 3 video files`).
  - A batch has to stay one kind of job, so items can only be added within the same family: encoding media *to* SWS, or extracting SWS/EIF *back out*. Mixing the two is refused with an explanation rather than silently reinterpreted. Adding SWS to EIF (or the reverse) is allowed and yields the mixed selection MacHuna already supported.
  - New module-level `merge_input_types()` holds the rule, so it is unit-tested outside the GUI.

### Changed
- **Bespoke values are cleared when you untick the checkbox**, not just when you tick it — nothing typed into the panel is held while the mode is off.
- **"Select" now starts the bespoke panel blank**, since it replaces the list. **"Add to List" keeps what you have already typed** and gives the new items blank fields, which is the point of building a list up piece by piece. A selection change while bespoke stays on continues to preserve values, as before.
- Cancelling the folder browser no longer alters the current selection's input type. Previously the scanned folder's type was applied as soon as the dialog opened, before any button was pressed.

---

## v1.6.14 — 2026-09-03

### Changed
- **Bespoke fields now start blank every time you return to them.** Typed values were being kept for the whole session, so ticking the checkbox again — or starting a second batch — showed the numbers from the previous one. They are now cleared whenever you tick the checkbox on, and again once a bespoke batch has finished. Values are still kept across a **selection change** while bespoke mode stays on, which is the case where retyping them would be a nuisance. Carrying old numbers any further either invites reusing a number that has just been written, or leaves a guaranteed collision sitting in the field.
- **The bespoke panel's scrollbar now sits immediately beside the list** rather than out at the right-hand edge of the window. The panel is sized to its content instead of stretching to the full window width.

---

## v1.6.13 — 2026-09-03

### Added
- **Bespoke per-item output IDs on batch convert.** A new checkbox alongside the existing numbering and naming controls lets you set each selected item's output identity individually, instead of relying on the auto-sequence. Offered for the three outputs where MacHuna chooses the name: **Kahuna SWS** and **Kayenne EIF** ("Use bespoke numbering", an output number per item, 1-9999) and **Sony TGA** ("Use bespoke names", a 4-character clip name per item). Kayenne TGA and TGA Sequence are unaffected — they name themselves from the source and already batch cleanly.
  - Ticking it shows a scrollable panel with one row per selected item: the item's name and its own input field. **Fields start blank on purpose**, so it is obvious at a glance which items still need an ID. Changing the selection refreshes the list but keeps values already typed for items that are still selected.
  - While bespoke mode is on, the control it replaces is hidden — Start number and "Use source file number" for SWS, Start slot for EIF, the shared Clip name field for Sony TGA.
- **Multiple Sony TGA clips in one batch.** Sony TGA output was capped at one clip per batch because every clip shared the single Clip name field and would have overwritten the others in one folder. Bespoke names give each clip its own name, and therefore its own folder, so a Sony batch can now convert several clips at once. **The one-clip-at-a-time guard is retained when bespoke names are not in use** — the overwrite it prevents is still real there.

### Changed
- **Three blocking checks run before a bespoke batch starts**, all naming the offending items so they can be corrected:
  1. every row must hold a valid, in-range value;
  2. no two items may share a value within the batch;
  3. no value may collide with what is already in the destination folder — for SWS that covers both `N.SWS` as a file and `N.SWS/` as a split-file folder, for EIF `NNNN.eif`, for Sony a folder of that clip name.
  There is deliberately **no overwrite option**: a clash has to be resolved by changing the value.
- Default (unticked) behaviour is unchanged in every respect — Start number auto-increment, "Use source file number", and the EIF start slot all work exactly as before.

---

## v1.6.12 — 2026-08-05

### Fixed
- **Interlaced→progressive no longer plays at the wrong speed when the rates differ (Fix 9(b)).** Bob-deinterlacing turns each field into a frame, doubling the frame count. That lands on the target exactly only when the progressive target is double the interlaced source's frame rate (i50→p50, i5994→p5994). Every other pairing was left at whatever rate the deinterlace happened to produce, while the output claimed the target rate, so the clip ran fast or slow. A new shared helper `_i_to_p_filter()` now appends an explicit fps resample whenever deinterlacing alone would miss the target, and is used by all four i→p paths. Verified with real conversions: a 4s 25fps interlaced source aimed at 1080p60 produced 200 frames before (3.33s, too fast) and 240 after (4.00s, correct).
  - This also fixed a **previously unrecorded instance in `convert_clip` itself**, the path the review notes cited as the good example to copy. Its down-rate branch kept the source frame count and stamped the target rate on it, so a 29.97fps interlaced source converted to 1080p25 SWS ran 20% slow (120 frames before, 100 after). This one affects SWS output, so it is the more consequential of the two.
  - **Raw TGA sequences are unchanged and still assume the source standard matches the chosen output family.** A TGA pile has no declared frame rate anywhere in MacHuna, so there is no real rate to resample from. The assumption is now explicit in the code rather than implied by a magic number. Fixing it properly needs a UI field declaring a sequence's rate.
- **Sony TGA field order toggle now works (Fix 10).** The TFF/BFF control was displayed for Sony TGA output but ignored: the weave and the deinterlace parity were both hardcoded to TFF, so switching to BFF changed nothing. It is now honoured in all four places, for TGA-sequence and video-clip inputs, in both conversion directions. The conversion log states which field order was applied. `_p_to_i_field_map` gained a `field_order` parameter defaulting to `'TFF'`, so every other caller, including the hardware-confirmed SWS weave, is byte-for-byte unchanged. *(Which setting a Sony MVS actually wants remains hardware-unconfirmed — this makes the toggle functional so the desk test can answer that.)*
- **Stills no longer vanish silently on clip-style outputs (Fix 4).** A still selected with Kayenne EIF, Sony TGA or TGA Sequence output produced nothing at all: no file, no error, no log entry, because none of those paths has a handler for a single-image item. MacHuna now blocks the combination up front with an error naming the files. **Stills convert to Kahuna SWS only** — a single frame is not a clip, and single-frame EIF/TGA output is deliberately out of scope. Stills→SWS is unaffected. *(The same silent gap was found in the EIF output path, which the original review missed; one guard covers all three.)*

### Changed
- `USER_MANUAL.md`, `README.md` and `DEVELOPMENT_NOTES.md` corrected where they implied stills were valid input for clip-style outputs. The contradiction between those documents is what kept the question reopening.

---

## v1.6.11 — 2026-07-09

### Fixed
- **Video clip → EIF no longer plays at the wrong speed for non-25/50fps sources (Fix 14).** `convert_clip_to_eif` extracted frames at the *source* rate but stamped the EIF header at the nearest supported rate (25 or 50fps). When those two rates differed — any 29.97, 30, 59.94 or 60fps source — the frame count and the header disagreed, so a Kayenne played the clip at the wrong speed and duration (e.g. a 10s/60fps clip ran for 12s in slow motion). MacHuna now resamples the source to the chosen EIF rate during extraction, so the number of frames written always matches the header fps and the clip keeps its original duration. The resample is applied to both the fill and key planes, so they stay frame-synced. Sources already at 25 or 50fps are unaffected. *(EIF output as a whole remains hardware-unconfirmed — this corrects playback speed, not desk acceptance.)*

---

## v1.6.10 — 2026-07-08

### Fixed
- **Progressive→interlaced no longer produces a 2×-speed clip from a same-rate source (Fix 9(a)).** The p→i path field-weaves *pairs* of progressive frames into one interlaced frame, which halves the frame count. That is only correct when the source runs at the interlaced **field** rate (double the frame rate) — 50p→1080i50, 59.94p→1080i5994, 60p→1080i60. A **same-rate** source (25p→1080i50, 29.97p→1080i5994, 30p→1080i60) was being weaved too, silently halving the duration and playing at double speed. MacHuna now checks the source frame rate before weaving:
  - **Field rate (double):** weaves as before — unchanged, hardware-confirmed.
  - **Same frame rate:** blocked with a clear error (weaving would double the speed); no file is written. Carrying same-rate progressive as PsF is deliberately deferred pending a live-Kahuna test.
  - **Any other rate** (needs standards conversion, which MacHuna does not do): blocked with a clear error.
  - The rate decision lives in one shared helper, `_p_to_i_field_map()`, applied to every p→i path that knows its source frame rate: **video clip → SWS**, **SWS → SWS** (using the source SWS header's fps), and **clip → TGA** extraction.
- Raw **TGA-sequence** p→i paths are unchanged: a bare pile of TGA files carries no frame rate, so it is still assumed to be a double-rate field stream and weaved. This assumption is now documented in the code. (A same-rate 25p TGA render remains a parked case — no UI to declare a sequence's rate yet.)

### Tests
- Added `TestPToIFieldMap` covering the weave / same-rate-block / cross-rate-block decision and the tolerance handling (37 → 42 tests).

---

## v1.6.9 — 2026-07-08

### Fixed
- **SWS→SWS conversion metadata — clip name, key plane, and audio.** When converting an SWS between standards (e.g. 1080i/50 → 1080p/50), three problems are corrected:
  - The output header's **clip name** now follows the **source SWS's name** instead of the placeholder `0001` that came from the temporary intermediate frames. (New `clip_name_override` argument on `convert_tga_sequence`, passed by the SWS→SWS path.)
  - A **keyless source SWS no longer gains a phantom key plane.** The frame extractor always writes RGBA, so a source with no key was being silently re-encoded with an opaque key; the output key state now follows the source (`has_key`).
  - **Embedded audio** in a source SWS is not carried through the TGA-intermediate SWS→SWS pipeline. This was previously silent — the log now prints a clear warning that the audio was dropped.
- Added a `clip name: … key: …` line to the SWS write log so the above is visible during conversion. Validated in-app: 1080i/50 → 1080p/50 logged `clip name: 51  key: yes`.

### Investigated — no change
- **TGA-Sequence / Sony-TGA output alpha.** A review flagged that `yadif`/`tinterlace` might drop the key/alpha on these outputs. Verified empirically (RGBA test frames pushed through both filters, alpha channel measured before/after) that **alpha is preserved correctly** and the output TGAs retain their alpha — no code change required. Recorded here and in DEVELOPMENT_NOTES to prevent re-investigation.

### Documentation
- **USER_MANUAL brought fully current and a formatted PDF added.** Removed all Kayenne MOV output references (withdrawn v1.6.5), corrected the field-order default to TFF (BFF is the fallback, per v1.6.3), rebuilt the input→output tables to match `_update_output_options()` exactly, and documented the newer SWS→SWS, TGA-Sequence and Sony-TGA-from-TGA outputs. A styled PDF (`MacHuna_User_Manual.pdf`) is generated from the Markdown via `pandoc … --pdf-engine=weasyprint -c manual_style.css`.

---

## v1.6.8 — 2026-07-08

### Removed
- **720p/50 and 720p/59.94 withdrawn from the output standards.** Both are removed from the Standard dropdown (GUI and CLI) and from all four SWS format-constant tables. The *header bytes* for these standards were confirmed against K-Watch reference files, but the actual SWS **output was never verified on hardware**, and the v210 `plane_size` calculation is wrong for 1280-wide (non-48-multiple) output — so selecting 720p produced a corrupt file. This is a "broken and unverifiable export" withdrawal, **not** an "obsolete format" one: 720p/59.94 is still actively broadcast by ABC, Fox and their affiliates in 2026. It remains a genuine candidate for reinstatement once a K-Watch 720p reference file is available (to confirm the fill-plane layout) and hardware is on hand to verify — at which point the `plane_size` formula must also be corrected to the 128-byte line-alignment rule the decoder already uses. The confirmed 720p header bytes are retained in DEVELOPMENT_NOTES and HANDOVER_NOTES for that future work.

---

## v1.6.7 — 2026-07-08

### Fixed
- **TGA sequence → Kahuna SWS, interlaced source → progressive target now uses yadif deinterlacing instead of frame duplication.** When "TGA source interlaced" is ticked and a progressive target standard is selected, MacHuna previously wrote each interlaced frame twice into the ffmpeg concat list — doubling the frame count but leaving combed, juddery motion. It now applies `yadif=mode=send_field:parity=tff`, separating each interlaced frame into two progressive fields (TFF per SMPTE 274M) for correct, smooth motion. This matches the yadif approach already used by the TGA→EIF path (v1.6.4) and the SWS→SWS i↔p path (v1.6.5), honouring the "no frame duplication anywhere" requirement. The alpha/key chain automatically inherits the same filter, so fill and key stay frame-for-frame aligned. Validated in-app: a 30-frame interlaced source produced 60 progressive frames with a structurally sound SWS and smooth playback.

### Changed
- **`USER_MANUAL.md` added to the release checklist in `CLAUDE.md`.** The manual was previously omitted from the per-release update list, which allowed it to drift out of date behind the code. It is now an explicit checklist item.

---

## v1.6.6 — 2026-06-28

### Added
- **Sony TGA output for TGA sequence input.** Sony TGA now appears in the Output dropdown when the input is TGA sequences or stills. Enables direct TGA→Sony TGA conversion with full interlaced↔progressive handling — tick "TGA source interlaced" to indicate the source field state, select the target standard, and enter the 4-character clip name. Output frames are named `CN0000.tga, CN0001.tga…` in a `CN/` subfolder, matching the Sony MVS naming convention. P→I uses `tinterlace=mode=interleave_top` (TFF); I→P uses yadif.

---

## v1.6.5 — 2026-06-28

### Added
- **SWS→SWS standards conversion (interlaced↔progressive).** When the input is SWS files, the Output dropdown now includes "Kahuna SWS". Selecting it converts between standards — e.g. a progressive SWS collection can be re-output as interlaced SWS, or vice versa, with the Standard dropdown controlling the target. P→I uses `tinterlace=mode=interleave_top` (TFF); I→P uses `yadif=mode=send_field:parity=tff` (doubles frame count for higher target fps) or `yadif=mode=send_frame:parity=tff` (same frame count). Source interlace state is auto-detected from the SWS header — no user checkbox needed. Implemented as a two-step pipeline: frames extracted to a temporary TGA sequence, then re-encoded to SWS via the existing TGA→SWS path.
- **TGA Sequence output.** A new "TGA Sequence" output option appears when the input is TGA sequences or video clips. Converts between formats — useful for i↔p standards conversion within the TGA format. P→I uses `tinterlace=mode=interleave_top` (TFF); I→P uses yadif. For TGA input, source interlace state is set by the existing "TGA source interlaced" checkbox. Output frames are named `0001.tga, 0002.tga…` in a subfolder named after the source sequence or clip, inside the destination folder.

### Removed
- **Kayenne MOV removed from SWS output options.** The "Kayenne MOV" option has been removed from the Output dropdown when the input is SWS files. The format was unconfirmed on hardware and is withdrawn until it can be verified and offered consistently across all input types. Kayenne TGA, Kayenne EIF, and Sony TGA remain as SWS extraction targets.

---

## v1.6.4 — 2026-06-04

### Fixed
- **TGA→EIF interlaced path now uses yadif deinterlacing instead of frame duplication.** When "Source is interlaced" is ticked, each interlaced TGA frame is now properly separated into two progressive fields using `yadif=mode=send_field:parity=tff`, rather than the previous approach of writing each frame twice in the ffmpeg concat list. The EIF output is the same 50fps format and frame count, but motion is correctly rendered (smooth, no comb artefacts from duplicated fields). TFF parity is explicit per SMPTE 274M.

---

## v1.6.3 — 2026-05-15

### Changed
- **Field order default changed from BFF to TFF.** On engineer advice, TFF is the correct default for 1080i HD in all known workflows. The BFF option is retained in the UI as a fallback. TFF now appears first (left) in the radio button pair. Applies to all TGA extraction outputs (Kayenne TGA, Sony TGA) and EIF→TGA paths.

---

## v1.6.2 — 2026-05-15

### Fixed
- **EIF→EIF conversion was silently broken.** The Output dropdown offered "Kayenne EIF" as an output option when the input folder contained EIF files, but `_run_to_eif()` had no handler for EIF input items — they were silently skipped with no output and no error. The option is now removed from the dropdown when the input type is EIF-only or mixed EIF+SWS. SWS→EIF from a mixed folder continues to work correctly via the SWS handler.

---

## v1.6.1 — 2026-05-14

### Changed — code cleanup
- Removed five dead functions/methods left over from the folder-picker era: `_pick_from_folder`, `_load_from_item`, `_scan_folder_for_items`, `_scan_folder_for_player`, `_group_files_for_batch`
- Extracted shared EIF bit-field decode logic into a module-level `_eif_parse_unit` helper; removed duplicated inner `_unit_arrays` functions from `_decode_eif_frame` and `_decode_eif_frame_rgba`
- Moved `_EIF_UNIT_BYTES` constant to the EIF constants block; removed redundant `import numpy as np` from three functions
- Fixed Video Player status bar text (still said "select a folder" after switch to file picker)

---

## v1.6.0 — 2026-05-14

### Added — EIF read/write (Grass Valley Kayenne native format)

This release adds comprehensive EIF support: MacHuna can now read, write, and convert Kayenne `.eif` files in every direction. EIF is Kayenne's native clip format, reverse-engineered from real Kayenne-produced files.

**EIF as a conversion output (TGA seq / MOV / SWS → EIF):**
- New **Kayenne EIF** option in the Output dropdown. Converts any supported input to `.eif` format ready for Kayenne ClipStore / Image Store.
- Slot naming spinbox: output files are named `0001.eif`, `0002.eif` etc. (4-digit zero-padded), incrementing per batch item. Kayenne requires this naming convention.
- **TGA source interlaced** option available when converting TGA sequences to EIF. When ticked, MacHuna uses ffmpeg frame duplication (each frame listed twice in the concat file) to convert 25fps interlaced TGA frames to 50fps progressive EIF — the same approach used for TGA→SWS interlaced conversion.
- A conversion log is written to the destination folder after each EIF batch (consistent with SWS batch behaviour).
- EIF is always 1920×1080 progressive. Sources of other sizes are scaled. Frame rate rounded to nearest supported rate (25fps or 50fps). Output is `UNCONFIRMED` pending live Kayenne hardware test.

**EIF as a conversion input (EIF → SWS / Kayenne TGA / Sony TGA):**
- EIF files are now visible in the main conversion picker. Folders containing only `.eif` files are detected as `from_eif`; folders with a mix of `.eif` and `.sws` files are detected as `mixed_eif_sws`. Both expose all output options.
- **EIF → Kahuna SWS** — lossless direct YCbCr repack. Both formats store 10-bit BT.709 limited-range YCbCr; MacHuna maps EIF bit-fields directly to v210 BE words with no RGB round-trip. Output standard is auto-derived from EIF fps (25fps → 1080p25, 50fps → 1080p50); the user's Standard dropdown selection is ignored to prevent frame-rate mismatch. `UNCONFIRMED` pending Kahuna hardware test.
- **EIF → Kayenne TGA** — decodes EIF frames to full-resolution 1920×1080 RGBA TGA sequence. Progressive output: one TGA per EIF frame. Interlaced output: pairs of EIF frames field-woven to produce 50i TGA. Naming: `0001.tga`, `0002.tga` … `UNCONFIRMED` pending Kayenne hardware test.
- **EIF → Sony TGA** — decodes EIF frames to 32-bit RGBA TGA sequence. Progressive output (1:1 frame mapping) or interlaced output (field-woven pairs). Naming: `{clip_name}{frame:04d}.tga` (4-char clip name prefix). `UNCONFIRMED` pending Sony MVS hardware test.

### Added — Video Player improvements

- **File picker replaces folder picker.** The Video Player **Open…** button now opens a standard file picker rather than a folder picker. Files in the destination folder can be clicked directly without navigating into the folder. All file types remain supported; extension routing is handled in code after the pick.
- **Format label in info strip.** The player header row now shows the format of the loaded file for all types: `SWS`, `TGA`, `MOV`, `EIF`. Previously only EIF had a format indicator.

### Added — EIF Video Player improvements (backported from v1.5.39–v1.5.43)

*(These were released as patch versions but are grouped here as part of the v1.6.0 EIF feature set.)*

- **EIF frame rate auto-detected from header** (v1.5.42) — `0x0FC` stores frame duration in microseconds (40000 µs = 25fps, 20000 µs = 50fps). No fps prompt on open.
- **EIF key channel decoded** (v1.5.41) — `bits[29:20]` of each EIF word = key level (10-bit limited range: 64=transparent, 940=opaque). Wipe mattes and alpha channels now visible in key and composite panels.
- **EIF colour decode corrected** (v1.5.40) — Full pixel format reverse-engineered from real Kayenne footage (UCI Downhill World Cup title card). Each 32-bit LE word: bits[29:20]=key, bits[19:10]=Y, bits[9:0]=chroma C (even columns=Cb, odd=Cr, 4:2:2). Three 360-row units stack vertically to form 1920×1080.
- **EIF playback** (v1.5.39) — Grass Valley Kayenne `.eif` files open in the Video Player with full transport controls and quad display.

### Fixed

- **EIF→SWS double-speed playback.** When a 25fps EIF was converted to SWS with a 50fps standard selected, the output SWS had a 50fps header but only 25fps worth of frames — playing at double speed. MacHuna now auto-derives the output standard from the EIF fps, overriding the user's Standard dropdown selection for this conversion path.

### Known limitations and unconfirmed items (EIF)

The EIF write and conversion paths are coded and verified by analysis against real Kayenne-produced reference files, but none have been tested on live Kayenne hardware. Full detail in DEVELOPMENT_NOTES.md under "EIF hardware unknowns and roadmap".

- **EIF write output** — UNCONFIRMED. Never loaded on a live Kayenne ClipStore / Image Store.
- **25fps EIF movi chunk tag** — UNCONFIRMED. No 25fps reference EIF files were available for comparison; the 8-byte movi chunk tag at 0x8DC is assumed (`b'RIFFRIFF'`) rather than confirmed from hardware.
- **EIF tail length (128 vs 140 bytes)** — KNOWN GAP. Generated files use a 128-byte tail sentinel. Real files with frame count ≥ 36 have a 140-byte tail. Unknown whether Kayenne validates tail length.
- **EIF audio (.eaf companion files)** — NOT IMPLEMENTED. Kayenne companion `.eaf` files are suspected to carry audio. `has_audio` is always False. EIF audio format entirely unknown.
- **EIF→Kayenne TGA / EIF→Sony TGA** — UNCONFIRMED on hardware.
- **EIF→SWS lossless repack** — UNCONFIRMED on Kahuna hardware (round-trip verified in software only).
- **1080i content in EIF** — UNKNOWN. EIF is always stored progressively. How Kayenne handles originally-interlaced content is unknown.
- **Clip name and slot range requirements** — UNKNOWN. Whether Kayenne validates the embedded clip name or requires contiguous slot numbers is unconfirmed.

---

## v1.5.43 — 2026-05-14

### Added
- **Kayenne EIF output.** MOV/TGA sequences/SWS files can now be converted to Kayenne `.eif` format. Select "Kayenne EIF" from the Output dropdown. An UNCONFIRMED warning is shown (pending hardware verification on a live Kayenne desk). EIF is always 1920×1080; sources of other sizes are scaled. Frame rate is rounded to the nearest EIF-supported rate (25fps or 50fps). The output file uses the source filename stem as both filename and clip name.

---

## v1.5.42 — 2026-05-14

### Fixed
- **EIF frame rate now read from header.** `0x0FC` in the EIF header stores the frame duration in microseconds (40000 µs = 25 fps, 20000 µs = 50 fps). The Video Player no longer prompts for frame rate when opening an EIF file — it is detected automatically.
- **EIF key channel now correctly reported.** Video Player info bar was showing "Key: No" for EIF files despite always having a key. Fixed by passing `has_key=True` to the player header.

---

## v1.5.41 — 2026-05-14

### Fixed
- **EIF key/alpha channel now decoded.** `bits[29:20]` of each EIF word is the key level (10-bit limited range: 64=transparent, 940=opaque), not a constant framing marker as previously assumed. For fill clips, this is always 940 (fully opaque). For wipe/key clips, it contains the actual wipe ramp or alpha matte. The Video Player now shows the key in the key panel and the correctly composited image (over chequerboard) in the composite panel.

---

## v1.5.40 — 2026-05-14

### Fixed
- **EIF colour decode corrected.** EIF pixel format reverse-engineered from real mountain bike footage (UCI DOWNHILL clip). Each 32-bit LE word: bits[29:20]=key, bits[19:10]=Y luma, bits[9:0]=chroma (even columns=Cb, odd=Cr, 4:2:2). Each unit is 360 rows × 1920 columns; three units stack vertically to form 1920×1080. Previous decode treated data as standard v210 groups, forcing the key bits into chroma positions and producing entirely wrong colours (pink/magenta). Fill colours now decode correctly.

---

## v1.5.39 — 2026-05-14

### New
- **EIF playback in Video Player (experimental).** The Video Player now opens Grass Valley Kayenne `.eif` files. EIF is Kayenne's native clip format with a proprietary pixel encoding. MacHuna reads the header (clip name, frame count, video data offsets), decodes all three units per frame, and displays the full 1920×1080 image in the fill panel with full transport controls. No audio or key plane support yet. Frame rate is not encoded in the header — the fps prompt appears on open as with TGA sequences.

---

## v1.5.38 — 2026-05-14

### Improved
- **Video Player now uses folder-based file picker.** Clicking Open… in the Video Player now prompts for a folder rather than an individual file. The player scans the folder and shows a list of all playable items — TGA sequences are collapsed to one entry per sequence (same behaviour as the main Convert window). Double-click or press Open to load; if the folder contains only one item it loads directly without showing the list.

### Fixed
- **TGA fps picker dialog unresponsive on macOS.** The frame-rate dialog that appears after selecting a TGA sequence could appear behind the player window or fail to accept clicks. Fixed by calling `transient()` and `grab_set()` after the window is fully rendered, and adding `focus_force()`.
- **Video Player window title.** Title bar still read "SWS Preview Player" despite the rename in v1.5.33; now correctly shows "Video Player".

---

## v1.5.37 — 2026-05-14

### Fixed
- **Sony TGA multi-file guard.** Selecting more than one clip and converting to Sony TGA would silently overwrite the first clip's frames with the second (both land in the same folder, named after the single clip name). MacHuna now blocks this with a clear error dialog and asks the user to select a single clip.

---

## v1.5.36 — 2026-05-14

### Fixed
- **MOV → Sony TGA output folder now named after the 4-character clip name.** Previously the output folder used the MOV filename stem instead of the clip name, so a file like `myclip.mov` would produce a folder called `myclip` rather than `WIPE` (or whatever clip name was set). The MOV→TGA path now matches the existing SWS→TGA behaviour.

---

## v1.5.35 — 2026-05-13

### Docs
- README and USER_MANUAL now explicitly state that TGA sequences do not need to follow K-Watch naming conventions. Any consistently named, sequentially numbered sequence is accepted (K-Watch, After Effects, custom renders, etc.). Examples added to USER_MANUAL Section 7.

---

## v1.5.34 — 2026-05-13

### Fixed
- **TGA sequences without separators now detected correctly.** Files named with a plain letters+digits pattern (e.g. `FEDX0000.tga`) were silently skipped because the sequence-detection regex required a separator character (`_`, `.`, or `-`) between the base name and the frame number. The separator is now optional, so `FEDX0000.tga … FEDX0051.tga` is correctly grouped as a single TGA sequence.

---

## v1.5.33 — 2026-05-13

### Changed
- **Unified format-in / format-out interface.** MacHuna and Hula are no longer separate tools. A single Convert section replaces the old Settings row, Batch Convert row, and Hula button. The user opens a folder, the app detects what's inside (SWS files, video files, TGA sequences, stills), and the Output dropdown adapts to show only the valid targets for what was found.
- **Input autodetection.** Scanning a folder of SWS files offers Kayenne MOV / Kayenne TGA / Sony TGA as output options. Scanning a folder of MOV/video files offers Kahuna SWS / Kayenne TGA / Sony TGA. Mixed folders (video + TGA sequences + stills) offer Kahuna SWS only. Mixed SWS + other formats shows an error.
- **Adaptive controls.** Options shown depend on input type and selected output: Standard dropdown, Split >4GB, Ignore alpha, Auto play, Loop play, TGA source interlaced, Include audio, Clip name (Sony TGA), BFF/TFF field order (TGA outputs). Controls not relevant to the current conversion are hidden.
- **MOV → TGA path surfaced.** Previously coded but not accessible from the UI. Now available when a folder of MOV files is scanned and a TGA output is selected. A warning dialogue confirms the path is unconfirmed on hardware before proceeding.
- **Sony TGA output folder named after clip name.** Previously the output subfolder was named after the source SWS stem. Now uses the 4-character clip name (e.g. `WIPE/`) to match Sony MVS import conventions.
- **"SWS Player" renamed "Video Player"** — more accurately describes what it does (accepts SWS, TGA sequences, MOV/MP4/MXF/AVI).
- **HulaWindow removed from GUI.** The separate Hula Toplevel window is no longer launched. All Hula conversion logic is unchanged and now routed through the unified interface. The `HulaWindow` class is retained in the source for reference but is no longer called.

---

## v1.5.32 — 2026-05-13

### Changed
- **Watch Folder removed.** MacHuna is a field tool for freelancers, not a networked server app. Watch Folder was a legacy of the K-Watch workflow and is no longer needed. `WatchService` and all associated UI removed.
- **Slot Override removed.** Replaced with a "Use source file number" checkbox in Batch Convert. K-Watch named files (e.g. `TNTS201_30_0001.tga`) carry their slot number in the filename; ticking this uses it directly. Unticked: all items sequence from Start Number.
- **Smart folder browser replaces file picker.** "Open Files…" now opens a folder picker. The app scans the folder and shows a custom browser listing one entry per TGA sequence (collapsed with frame count) plus any other supported files. No more scrolling through hundreds of individual TGA frames.
- **"Include audio" moved to folder browser dialog.** Only shown when at least one video file with an audio track is detected. Hidden for TGA-only folders. Framed as "Exclude audio" (default = include).
- **"TGA source already interlaced" label shortened** to "TGA source interlaced".

### Fixed
- **TGA sequence → progressive standard played at double speed.** When a TGA sequence captured from an interlaced source (e.g. 1080i/50, 25fps display rate) was converted to a progressive standard (e.g. 1080p/50, 50fps), the frame count was unchanged, halving the duration. Fix: when "TGA source interlaced" is ticked and the target is progressive, each frame is duplicated in the concat to produce double the frame count and preserve duration.

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
