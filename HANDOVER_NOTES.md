# MacHuna - Session Handover Notes

Paste this document into a new Claude session to resume development. Read carefully before asking for any files or writing any code.

---

## Session Anchor

**THIS REPO IS AUTHORED ONLY FROM THE M5** (David, 2026-10-15; see `CLAUDE.md`): the M5 session oversees MacHuna on Mac and PC; M1 sessions pull to verify, relay findings, and never commit or push here. **Latest: engine `v1.15.4` (`96c9859`) released 2026-10-15:** stdin=DEVNULL on all 15 child processes, found by the M1 (ffmpeg hung on Windows) and reproduced on a Mac (a request lost its first byte; a "q" cut 150 frames to 112 with exit 0). **MacHuna 2.5.4 LIVE 2026-10-16** (David typed "2.5.4"; recipient-checked; Swift tag `v2.5.4` on `6d49f1c`, site commit `ae2092f`, both pushed): pins `v1.15.4`; bridge.py stdin=DEVNULL and UTF-8 requests; the build refuses a bridge child process without `stdin=`; `Scripts/stdin-race.py` fails on 2.5.3 and passes on 2.5.4. **NEXT for the M1 (message given to David):** engine pin to v1.15.4 (its overnight plan does this), add swift-ref at `v2.5.4` with its push disabled, re-run its 45 bridge checks without its DEVNULL launcher. **M1 overnight results 2026-10-16, ALL GREEN (checked by pulling MacHuna-PC: `66073a8` pin at v1.15.4, `362b679` build script and record, `a1a46bf` LF for *.sh):** Windows suite 371 passed 0 failed 17 skipped with and without -X utf8; ffmpeg.exe 99b268fd...2693, ffprobe.exe 769e6538...eb1e, GPLv2+, png decoder present, 3.64x on 4 cores, Windows DLLs only; bridge 42/45 on the old bridge (player buffer x2 by design, .pyc false alarm gone in 2.5.4). Revised message sent: swift-ref at v2.5.4, re-run checks (expect 43/45), then the WPF skeleton (bridge connection, one conversion, then the WAV drag-out). Before that, overnight 2026-10-15/16: building ffmpeg 8.1.2 in MSYS2 MINGW64 with exactly the approved configure (tarball sha and ffmpeg.org signature checked); then the four proofs plus "no non-Windows DLLs", suite and bridge checks on the new ffmpeg, then `tools/build-ffmpeg.sh` and its record to MacHuna-PC; report in the morning. **For the PC publish step later:** its GPL source zip must carry the ffmpeg source, the build recipe and the sources of the statically linked zlib, bzip2, xz and winpthreads. Player buffer: the PC interface deletes it after unmapping (no bridge change). **PC decisions settled by David (2026-10-15), recorded in DEVELOPMENT_NOTES "The plan":** interface in C#/.NET WPF; `bridge.py` shared via MacHuna-Swift as a pinned read-only submodule (MacHuna-Swift now tags releases: `v2.5.3` on `e599846`, PUBLISHING.md step 6, Swift `ff799b1`); our own ffmpeg 8.1.2, every native part, no external libraries (AV1 sources will not open on the PC); one download page with Mac and PC buttons, zips handed to the M5, separate `version-pc.json`, a guard so neither release touches the other. **THE MAC COMES FIRST (David 2026-10-17): the release gate is in the roadmap above "Small, for the next engine release"; the Mac parity kit must stay identical.** **PC download choice DECIDED (David, 2026-10-18):** two labelled downloads (Intel/AMD, ARM) with a "Not sure?" line, and the page highlights the right one where the browser can say (roadmap, "Where it lives"). **For the next M1 message:** the PC manifest (version-pc.json) names both downloads and each copy offers its own architecture's. **PC step 14 reviewed 2026-10-18** (built, not committed until David's wording): the 60 s keyed SWS player measurement: ~6.3 MB a cached frame at 200%, ~10 GB for 1600 frames, stopped by a guard at 5.7 GB on the 8 GB M1; loading ~4.2 frames/s under emulation. **Sent "STEP 14 REVIEW (1 PART)":** A) David's wording items 1-4 approved as the M1 wrote them, 5 = "MISSING: <path>" (no em dash); decision 29. B) `version-pc.json` = {version, released, summary, downloads: {x64, arm64}, page}; each copy offers its own build's download, else opens page. C) PC player cache capped at min(1600, a quarter of physical RAM / bytes per frame), past it the Mac's "first N frames cached". The same Retina memory issue exists on the Mac: on the 2.5.5 list to MEASURE, no Mac change now. **WAITING ON: the M1** (A, B, C, commit step 14, report). **Parked, small (David 2026-10-18):** the PC's Player button looks small to him on the PC (fine on the Mac); he thinks it is the PC's position; return to it later, not in the next M1 message. **David tries the PC build himself once the M5 and the M1 are happy it is ready** (after step 16, before the colleague; he withdrew the after-step-14 try-out, 2026-10-18). **PC step 14 DONE 2026-10-18** (MacHuna-PC `7aa0a63`, `93e3e35` decision 29, `ec37454`; checked by pulling): wording, two downloads, player cache capped for the whole process (60 s keyed SWS peak 1,965 MB within 2,047). **WAITING ON: the M1** ("STEP 14 REVIEW 2 (1 PART)": step 15 memory sticks as StickEject.swift, only .DS_Store and true AppleDouble files deleted, system folders never walked; a VHD first, then David's spare stick in Parallels). **PC look (David 2026-10-18):** a PC default of Dark was considered and DECLINED; the default stays Match System as on the Mac. During his own try-out, collect what looks worst and see what polish is worth doing (Windows 11 backdrop, spacing, fonts); not to be raised before then. **For the next M1 message (David spotted it, 2026-10-18):** the PC list's stripes are a fixed 24-pt pattern behind the rows (`MainWindow.xaml` ~15, ~216), so two-line rows and scrolling drift off the bands; fix as the Mac: each row colours itself by alternation, the pattern only fills below the last row, checked by pixels. Bundle the stripe fix with step 15: ONE full suite run at the end covers both. Also ask it to time that full window-suite run (about 600 clicked checks, re-run before every commit) and report it. **PC step 15 BUILT 2026-10-18** (uncommitted until David's wording): memory sticks as StickEject.swift, proven on a FAT32 VHD and on David's real spare stick (its 175 system-folder files fingerprinted unchanged, a real eject); veto fix found by the real stick. **Sent "STEP 15 REVIEW (1 PART)":** wording 1-3 approved ("USB Drive (E:)", refusal reasons inside the Mac's sentence, a window titled "Eject"); the 13d mapping check waits up to 5 s; `$RECYCLE.BIN` left as the Mac's list; real Mac "._" files tested at David's own try-out; the STRIPE FIX; ONE timed full suite run; commit; delete the VHD. **STEP 15 DONE 2026-10-18** (MacHuna-PC `be500c0` app incl. stripe fix, decisions 30-31; `9b478d2` tests; checked by pulling: deletes only .DS_Store and true AppleDouble, skips reparse points; rows shade themselves via AlternationCount, fill only below the last row). Stripes 7/7 by pixels, 6/7 fail on the old brush. **Full window suite timed: 24 min 16 s** (told David). Step 13 part c timed out on a slow spell and threw; leftovers in %TEMP% failed the first rerun; rerun alone 48/48; David committed on that. **Sent "STEP 15 ACCEPTED, THEN STEP 16 (1 PART)":** A step 13 reports a missing window as FAIL not throw, cleans its leftovers at start and in finally, falsified; B REPORT ONLY: where/what/how big the player buffer + WAV left by a force-quit are, and whether anything clears them (Windows never empties %TEMP%), M5 decides; C step 16: PC docs in pc\docs\ from swift-ref v2.5.4, written substitution list, PC-only sections (unzip/run, Intel or ARM, "Windows protected your PC" worded for unsigned, marked REVISE AT SIGNING), only what is built, section-counterpart + drift check (falsified), PDFs by one rerunnable script, Help opens them, no client names; tests steps 14+16 + selftest, NO full suite (that runs once before the zips rebuild); then substitution list and both PDFs to David. **DOCUMENTS (David 2026-10-18):** the M5 manages ALL documentation content and wording; the Mac manual and Quick Start are the master; the M1 drafts the PC editions (it can check each sentence against the running app and authors MacHuna-PC) and sends the TEXT to the M5 BEFORE David, every sentence differing from the Mac's marked, with the substitution list; the M5 checks voice, order, wording, British English, no em dashes, only what is built, then passes it to David with changes marked; when the Mac docs change, the M5 tells the M1 which sections to carry. **Quick Start FIRST and on its own** (David: it matters most), the manual after. Sent "STEP 16: ADDITION (1 PART)". **M1 reported 2026-10-18:** step 13 test fix `1cc1949` (each part in its own try; leftovers cleaned before and in finally, not while another MacHuna runs; falsified) ACCEPTED. Leftovers facts: %TEMP%, `machuna-player-<8>.rgba` (8 slots x w x h x 4 = 63.3 MiB at 1080, any clip length) + `.wav` (192,000 B/s); removed only by player_close; Windows never clears (Storage Sense default off); Mac's $TMPDIR cleared by macOS. **M5 ruling: PC start-up sweep** of only those two patterns, only when no other MacHuna runs, tested and falsified. **Quick Start PC draft** (pc\docs\, check_docs.py 107 Mac section fingerprints, build_docs.py via Edge, refuses em dashes/broken links; cover + 2 pages) reviewed against Mac v2.5.4: recommended to David - updates line "Help ▸ Check for Updates… tells you…" kept (0.x has no automatic check); PC header "MacHuna Quick Start Guide" kept, Mac's wrong header to 2.5.5 list; Before you start rewritten (Extract All…, don't run from inside the zip - M1 to check; x64 vs ARM with Settings ▸ System ▸ About); SmartScreen REVISE AT SIGNING; drop "however the files got onto it"; keep eject-refusal line; **Ctrl+Alt+Up/Down reorder risk** (Intel hotkeys rotate the screen, AltGr) - M1 to report and propose, change nothing yet. Sent "QUICK START REVIEW (1 PART)" (David to approve the rulings; he moved straight on to the notes). **M1 reported (later 2026-10-18):** start-up sweep built (exact mkstemp pattern, not while another MacHuna runs; 3/3, each rule falsified) ACCEPTED; 2c measured: run from inside the zip copies the exe alone, it fails silently (MacHuna.dll missing), so Extract All… wording right; Ctrl+Alt+Up blocked by a global hotkey (measured), AltGr would move rows. **INCIDENT:** the M1 drove Explorer's zip dialogs; David clicked one; an Extract all landed 1,441 files in `\\Mac\Home\Documents` (David's M1 Mac Documents); M1 removed it and a stray second copy. David asked to check his Documents; rule sent: never write to \\Mac\ or David's folders, never drive a save-capable dialog. **Manual PC draft** (754 sentences, 534 word for word, 80 by substitution; check_docs 107/107 falsified; 33 pp; Help opens both PDFs; selftest 31/31; step 14 31/31; step 16 8/8; decision 32 drafted; nothing committed). M5 review sent as "MANUAL REVIEW (1 PART)": page labels "Windows (Intel or AMD)"/"Windows on ARM" in both guides; overview not "same files" (Section 16 TGA exception); drop USB drive in 2.2; 4 GB ample measured?; 2.4 settings location tested?; Q1 drop Mac version tags except old-file warnings; Q2 stale Mac lines to 2.5.5 (added; 4.6 decided, PC copies when Mac builds); Q3 dnsvision.tv/machuna; Q4 no Windows 10 test; Q5 **Alt+Up/Down only** (PC difference, decision). Commit nothing until David approves. **Asked David:** are the Mac manual's example file names real clients/jobs (2.5.5 list)? **M1 applied the manual review** (labels in both guides, 12.1, 12.3; overview "match the Mac's, except the one case in Section 16"; USB drive dropped; "4 GB ample" dropped, never measured (one 60 s conversion ~650 MB); Mac version tags dropped except old-file notes as "MacHuna for Mac x.y"; **Alt+Up/Down only, PC decision 33**, Ctrl+Alt+Up does nothing, step 8 46/46 falsified; steps 5 103/103, 14 31/31, 16 8/8, selftest 31/31 both builds (ARM64 rerun: badssl.com timeouts)). 2.4 settings carry-over NOT tested (code: %APPDATA%\MacHuna). **David read the Quick Start PDF on the M1 and APPROVED both guides** with the M5's one change: 2.1 requirements become "MacHuna needs Windows 11." Sent "GUIDES APPROVED: COMMIT STEP 16 (1 PART)": 2.1 change; 2.4 two-copy settings test agreed (confirm %APPDATA%\MacHuna absent first, delete only if the test made it); the exact delete command + full path for the Documents incident (not yet received); commit step 16 app/tests apart, push; ONE timed full suite; rebuild both zips with SHA-256. **STEP 16 DONE 2026-10-18** (MacHuna-PC `f7dc76d` app: guides, start-up sweep `Leftovers.Sweep` exact regex, skipped while another MacHuna runs; Alt+Up/Down; decisions 32-33; `4002dae` tests; checked by pulling; no em dashes printed). Settings carry-over PASSED (two copies, %APPDATA%\MacHuna, folder made and removed by the test). Delete command CHECKED: one literal path `\\Mac\Home\Documents\MacHuna-0.1.0-windows-arm64`, guarded by creation time after 13:19, no wildcard; David's Documents safe. ONE full suite 25 min 33 s ALL GREEN. Zips rebuilt 14:55: x64 `e8d2ce02...892f29`, arm64 `ad2912d9...fc1e21`, open-source `d0dd8619...c7e76a`; each fresh-unpacked selftest 31/31. **ALL PC BUILD STEPS DONE.** **David's own try-out STARTED** (arm64 zip extracted to `C:\MacHuna-tryout`, own destination folder there; no SmartScreen box because the zip was made locally, a download will show it). **Parallels finding (M1, read-only):** the VM's Documents/Desktop/Downloads/Videos/Pictures/Music ARE `\\Mac\Home\...` (Z: = \\Mac\Home, Y: = iCloud): explains the incident; PC default destination Videos\MacHuna Out = the MAC app's own MacHuna Out, and Clear there deletes outright (no Recycle Bin on a share). FOR DAVID'S LIST (later): different PC default folder name and/or Clear refusing or warning hard when nothing can be recovered; M5 also to check the MAC's Clear on a drive with no Trash. **Try-out findings so far (David):** (1) the Fluent TextBox clear X while typing: REMOVE (David); (2) the player window half-drawn (white empty panels) while a clip loads: fix, window fully drawn at once with a loading state, UI never blocked (low priority, wanted); (3) no drag picture in OR out: IDropTargetHelper on every drop target, a drag image out (icon + count); (4) (M5 note) the extracted folder's 1,441 files make MacHuna.exe hard to find: consider MacHuna.exe alone with the rest in a subfolder, decide after the try-out. Sent "TRY-OUT FIXES, ROUND 1 (1 PART)" for 1-3 (affected steps + selftest, no full suite until the try-out ends, arm64 zip only, commit apart). David paused his try-out while the M1 tests (they drive the screen); new zip to go to a fresh `C:\MacHuna-tryout2`. **ROUND 1 DONE** (MacHuna-PC `04594e4` app, `a3ec390` tests, `43e6c2b` packaging -Arch; pulled): Fluent TextBox "DeleteButton" collapsed by a class handler; player bridge starts in the background (no gain on double-click; first frame 3.7-3.9 s under emulation: ~1.8 s bridge start + decode ~5 fps); drag pictures via IDropTargetHelper in, DragImageBits out (selftest 33/33); new arm64 zip `a21c41fb...cb84` in the M1's scratch `zip-round1`, David extracted to `C:\MacHuna-tryout2`. Player options a (bridge at start, 137 MB) REJECTED by the M5; b "Opening…" HELD until drawing fixed. **David's round 2 findings:** (1) PLAYER NOT FULLY DRAWN, screenshot: Light mode, large WHITE areas, background painted in patches, "Composite" cut to "osite", transport and info bar stop part way; all dark once loaded. The M1's part e said 0.0% white, so it measures the window's own render, not the screen: a TESTING lesson (measure what reaches the screen). Suspect WPF dirty-region painting under Parallels' GPU; diagnose with software rendering, do not ship it yet. (2) Disabled transport buttons (Pause, frame back) are blank grey squares; must show the symbol dimmed, as the Mac. (3) The X still in the list rows' TGA name box (handler misses row boxes). (4) The sound drag-out picture vanishes after a split second (files in/out and sound in fine). "Activate Windows" watermark in the VM: not MacHuna. Sent "TRY-OUT ROUND 2 (1 PART)", with the new loop (fix, quick check, David looks, tests after he agrees, never while he uses it) and David's question: did running the tests straight after each change earn its time (round 1: what was caught, would a quick check have caught it, durations, recommendation). David's view: the tests did earn their keep (he saw them catch breakages). **ROUND 2** (built, not committed; zip `b7f8da06...4b92` in `zip-round2`, David in `C:\MacHuna-tryout3`): row-box X FIXED (click into empty box then type; button template emptied, redone on TextChanged; David confirmed). M1's part e uses CopyFromScreen (Windows' composed screen) and sees complete frames; David's screenshots are Mac screen grabs of the full-screen Parallels space. **David's comparison: `--software-drawing` (RenderOptions SoftwareOnly) shows NO white patches in Light or Dark** -> Parallels' GPU path. Disabled transport buttons empty in DARK mode only (both drawing modes) = REAL contrast bug. Sound drag picture still vanishes: stays while still, goes on movement (tooltip hypothesis wrong). **NEW: closing the player while a clip loads CRASHES all of MacHuna** (David confirmed a crash). Testing answer: round 1's touched steps took 14 min 41 s, caught one real bug (shell data object broke chip drags) and two weak checks; missed the three David found; **M1's recommendation ADOPTED:** package self-check + 5-8 min smoke of the touched steps + 1 min by eye of what David will look at, done his way (mouse); full suite before zips go wider; what only David can see goes in the hand-over line. **DECIDED with David:** before the colleague, fix the crash (first), Dark-mode disabled buttons, the sound drag picture; white patches ASSUMED Parallels: auto software drawing under Parallels only (M1 to say how it detects), hardware elsewhere, the colleague confirms a real PC draws cleanly; remove the .cmd. **Colleague early look AGREED (David):** after round 3, commit rounds 2-3 with tests, full suite, both zips + SHA-256; framed as an early look with specific questions (M5 drafts them); unsigned is fine, Azure still waits for the proper colleague test. **M1 WORKING RULES SAVED** (MacHuna-PC `fc7be24`, top-level `CLAUDE.md`, checked by pulling: rules A-E plus earlier standing rules and three lessons: check foreground/focus before typing, never choose in the PDF "Select an app" chooser, drag pictures and Parallels' screen invisible from inside Windows; its memory points there). The round 3 message had NOT reached the M1 when it reported (it was waiting for round 2 findings); David told to send "TRY-OUT ROUND 3 (1 PART)". **ROUND 3 DONE, DAVID: ALL FIXES WORK** (zip `25f85684...3068`, `C:\MacHuna-tryout4`; not committed): player-close crash = render reading the frame buffer after it was freed (access violation), now one lock, double free harmless, closed at 300/1500/3500 ms with nothing left behind; software drawing chosen automatically when a desktop display device's ID starts `ACPI\VEN_PRL` or names Parallels (.cmd removed, `--software-drawing` kept for diagnosis); player buttons given their own template (disabled = symbol at 35%, background unchanged), checked Light and Dark; sound drag picture: the drag helper's stream state was not kept (refused every time) and enter/leave counted per child, both fixed. **Player button (David 2026-10-18, comparing PC and Mac screenshots):** Mac's (title bar, level with the window controls) stays; PC's floats alone above Output and looks small -> move into the menu row at the right end, height of the row, label "Player" (PC difference), close the gap, same action/Ctrl+Y/tooltip. (The PC's Destination row reading "Destination" was David's own folder name: no bug.) Sent "ROUND 3 ACCEPTED, ONE MORE CHANGE (1 PART)": button via the try-out loop, then on David's yes item 6 for rounds 2, 3 and the button (falsified tests, decisions, commit apart, push, ONE timed full suite, both zips + SHA-256 in pc\dist). **Player button build** (zip `ec9a0c51...5a39`): in the menu row, row height (95 px at 200%), label "Player", gap closed, decision 35; **David approved.** Ctrl+Y is "Play Converted File" (works on a selected converted row, as the Mac's ⌘Y; David confirmed). **Gap found by David:** no menu route to open the player EMPTY on the PC (the Mac has it via its Window menu, which PARITY_PLAN line 35 chose not to copy) -> **add "Open Player" to the Convert menu above Play Converted File, no shortcut** (decision 35). Sent "BUTTON APPROVED: ITEM 6 (1 PART)": Open Player (quick check, no David look), then item 6 for rounds 2, 3, the button and Open Player (falsified tests incl. Ctrl+Y with/without a selected converted row, Light and Dark; Open Player opens empty; decisions; app/tests committed apart; push; ONE timed full suite; both zips + SHA-256 in pc\dist). **Colleague early-look message DRAFTED** (in chat and a scratch TextEdit file, not in any repo): what it is, x64 vs arm64, Extract All, SmartScreen More info/Run anyway, Quick Start; try conversions, the player, a stick; 7 questions (player drawn cleanly? [the key one: confirms white patches were Parallels], time to first picture, conversion time, failures/crashes/unclear messages, anything not found, feels like Windows?, Windows version and System type); screenshots; don't pass it on. David sends the zip by a OneDrive/WeTransfer link (~115 MB). **WAITING ON: the M1** (Open Player + item 6 report: commits, suite time, both SHA-256s); then David sends the colleague the zip and message **TESTERS (David, later 2026-10-18):** instead of one colleague, a call-out on the vision-mixing WhatsApp (M5 tidied wording: real PC, own not locked-down PC, Intel/AMD better test) and a tester email (single WeTransfer link holding the x64, arm64 and open-source zips; Extract All; SmartScreen; 7 questions; ask before passing on); the zips come from the M1's `pc\dist`, David copies them to a shared Desktop folder and sends from the Mac. Open-source zip MUST go with them (GPL). **MAC 2.5.5 + ENGINE v1.16.0 BUILT on the M5 the same evening (David: "yes" to start while testers test; none of it touches the PC's pins).** Engine `3e2ccb3`, `640e3a9`, release `47fc88d` tag **v1.16.0** pushed: no_alpha on every MOV route + `_hula_run_batch`; `scale=flags=bitexact` for a clip's TGA; frozen-app FFmpeg-missing advice; Windows-reserved MOV names; pytest 397 / unittest OK; each test falsified. Swift (all pushed, last `2c61755`): bridge `62206f3` (MOV ignoreKey via `_mov_alpha`, bitexact clip TGA, names as typed, `_handle` replies with the reason and traceback to stderr, missing sound source "can no longer be found"); `9086c27` decision 60 (Ignore key shown for SWS and MOV only, effectiveIgnoreKey; Convert runs only unfinished rows: `doneAs`/`signature` = format+destination+name, finished rows not validated, Convert greys when none pending; `skipReason` still-not-SWS / clip-as-MOV flagged and skipped; refusal with a batch = red `warning` note; notes cleared on add/empty; Write beside names the real folder; tooltip plays; depends; MISSING:); `0009cc0` docs (manual, stale lines removed, `quick_start_header.css`, PUBLISHING.md); `983d257` decision 60.1 (David's 4 answers: TGA Sequence hidden too; player cache = min(1600, quarter of RAM / bytes per frame); Clear: no Mac change, PC to warn "deleted permanently"; skipped-row wording approved); `2c61755` engine pin v1.16.0, version 2.5.5, manual What is New 1.12, PDFs rebuilt (Quick Start header verified via PDFKit). **Built NOTARISED** (`NOTARISE=1 Scripts/bundle.sh`, Accepted, stapled, self-contained, 90 MB): `--selftest` (env -i) PASS incl. 2.5.5 section and help PDFs; `stdin-race.py` PASS; parity kit **44/44** with the built app's bridge and FFmpeg; signed com.dnsvision.machuna 76DH86HPU3, 2.5.5. **MacHuna 2.5.5 LIVE 2026-10-18** (David typed "2.5.5"; site wording approved; `MACHUNA_CONFIRM=2.5.5 ./publish.sh --upload` since no terminal: source zip, app zip, site; all live checks ok; recipient check: live zip sha `54379997...f5b8` = built, spctl accepted Notarized Developer ID; site commit `04b2816`; tag **v2.5.5 on the built commit `2c61755`**, pushed). The 2.5.4 zip stays in the bucket (David's call). David's own /Applications copy still 2.5.4 (the app will offer the update). **PC ITEM 6 DONE** (MacHuna-PC `e916ea2` app incl. Open Player in the Convert menu, decision 35; `ba9085d` tests: ui-tryout 31 checks real mouse/keyboard Light and Dark, selftest 35, 15 broken builds caught; full suite 28:29 all passed except step 15 not run; zips in pc\dist: x64 `6cea19bf...7b1f`, arm64 `3e1478d8...5f27`, open-source `eab77f3d...1f46`). **M5 ruling:** step 15 not needed now (Sticks.cs and EjectDialog.cs unchanged since 15/15; checked by diff), runs at the next full suite; the zips go to the testers as they are; pc\dist left alone. Sent "ITEM 6 ACCEPTED; 2.5.5 IS LIVE (1 PART)": PC catch-up with 2.5.5: re-pin engine v1.16.0 + swift-ref v2.5.5 (push disabled), parity kit on the PC expecting 44/44 incl. the 4 Intel TGA cases, report before building; then copy decisions 60/60.1 (Ignore key SWS+MOV only, MOV no alpha, unfinished rows only, skipped rows same wording, MOV names as typed, PC Clear warns "deleted permanently and cannot be recovered" with wording to the M5 first); try-out loop; full suite with step 15 before the public release. **2026-10-19, PC 2a/2b DONE:** re-pinned engine v1.16.0 (`47fc88d`) + swift-ref v2.5.5 (`2c61755`), push still disabled, to be committed together with the self-test's engine expectation (first part of 2c). **PC parity kit 44/44** incl. the 4 Intel TGA cases (kftga-clip25i, sony-clip25i-bff, tgaseq-clip25i-to-p25, tgaseq-small-p25: bitexact worked), on the shipped x64 route (x64 Python 3.12.10 emulated on the ARM VM, x64 ffmpeg 8.1.2), 1 min 40 s; results `tools\parity\results-pc-x64-2026-10-18.json`. Sent "2c: GO AHEAD" with 6 items its list missed (Ignore key hidden for TGA Sequence; finished rows not checked for already-there; Write beside names the folder written into; PC Saves as = MOV name as typed; plays/depends/MISSING:; decision 18 red note clears) + a 2.5.5 self-test section + **leave the testers' 0.1.0 zips in pc\dist untouched, later tester builds 0.1.1+**. **2c built** (not committed): self-test 39/39, each rule broken once (bridge rules on a patched scratch COPY, swift-ref untouched); stderr check allows only refusal tracebacks. **PC Clear** (SHQueryRecycleBin; \\Mac, Z:, Y: answer no bin): "Delete N items permanently?" / "...on a drive with no Recycle Bin, such as a network or shared folder, so the files will be deleted permanently and cannot be recovered." / "Delete Permanently" (red), Cancel default; APPROVED with 3 conditions: singular "1 item"; any error/unclear answer = no bin (fail safe); test David's stick in the try-out. M1 found: a file too big for the bin is deleted outright without asking; FOF_WANTNUKEWARNING APPROVED, plus check a bin turned off on C:. PC manual's Clear paragraph to the M5. **For the NEXT M1 message (David asked; missed the sent one):** HANDOVER.md at the MacHuna-PC root (anchor, step, built-not-committed, waiting on, next action), updated each commit and on "update your memories...", read at session start (CLAUDE.md rule); the M1's notes and memories stay in MacHuna-PC and on the M1, never engine\, swift-ref\ or the M5's (David: independent). **Then:** conditions built (a bin assumed only on a FIXED drive where SHQueryRecycleBin says OK and it is not switched off by NukeOnDelete/NoRecycleFiles; 7 self-test cases); David's FAT32 stick: removable + 0x80004005 = no bin, he saw the permanent dialog, pressed Cancel; FOF_WANTNUKEWARNING proven on a 500 GB sparse file. **MacHuna-PC `8edc4f9`** (app, pins engine `47fc88d` v1.16.0 + swift-ref `2c61755` v2.5.5, verified by git ls-tree, decision 36, parity results) **+ `115a788`** (tests), self-test 40/40, smoke steps 5/9/10/11/14 passing; PC version **0.1.1**; try-out zip arm64 `caa2e67c...83e7`; pc\dist (testers' 0.1.0) untouched. Sent "CLEAR: ANSWERS; HANDOVER NOTE": no-bin message names "a USB stick" first; one exception to rule A6 for a bin-off test on C: if David agrees (switch straight back); PC manual Clear paragraph approved; its Quick Start Clear line to the M5; HANDOVER.md request sent. **M1 HANDOVER.md DONE:** MacHuna-PC `13383ee` (verified by pull: anchor at its top; its CLAUDE.md reads it first, then git log from the anchor and git status), so the M1 can resume if Claude Code closes. The sparse file was already gone. Stick wording and the manual paragraph get built after the try-out, together. Bin-off test on C:: the M5 advised David yes, after his try-out only, on a scratch folder on C: with the M1's own files, never a shared folder, told before and after. **Then: first tester bug** (0.1.0, the + and Sound arrow menus drawn as boxes): the icon font was set on the buttons and their menus inherited it; never right, tests read UIA names only. David finished 0.1.1 (all 2.5.5 behaviour passed). **PC 0.1.2:** MacHuna-PC `6e176af` (menu fix, stick in the no-bin wording, manual Clear paragraph, decision 37, rule C2: every menu and popup by eye in Light and Dark before any handover) + `2503c4b` (tests\ui-fonts.ps1 32/32 on what is drawn, falsified; HANDOVER.md); zip arm64 `0e4ead56...307d`, self-check 41/41 (proves the tests-only font audit is off). David happy; Write beside on his stick named E:\MacHuna (switching off after a batch matches the Mac). **Bin-off test** (David's yes): SHQueryRecycleBin still said OK with the bin off; MacHuna read NukeOnDelete and warned; setting put back. A tester's idea, one frame of a sequence as a still, PARKED by David (DEVELOPMENT_NOTES, Future Considerations). Sent "NEXT: GUIDES, WINDOW TEST, SUITE": PC guides to 2.5.5 drafted by the M1 and reviewed here before David (Quick Start Clear line given), the window test for finished and skipped rows, the full suite with step 15, a tester build only when David agrees (testers still on 0.1.0). **Testers:** a fixed build goes to them after the guides, window test and full suite (next number, x64 + arm64 + open-source; the M5 updates the email). Meanwhile David sends a note on 0.1.0's three known problems: Clear deletes permanently on a stick or network folder (a Parallels tester's default destination is one); the box menus (drag files in; right-click a row for Sound); "already there" on a second Convert (remove the converted rows with − first; re-adding to a fresh list does not help). **Then, 2026-10-19 afternoon:** PC guides at 2.5.5 approved with two extra 1.3 bullets (Ignore key for MOV, MOV names as typed); committed MacHuna-PC `0b54458`; window test for finished/skipped rows `9856d94` (21 checks). **First real x64 PC tester** (AMD Ryzen, NVIDIA RTX): player clean; **Google Drive for desktop listed as a stick** (likely FAT32 virtual drive; Eject's tidy would delete from the cloud): TOP PRIORITY PC fix, list only physical removable media; the message "CLOUD DRIVE FIX; THE OVERWRITE" re-sent (the first never reached the M1). Order: cloud fix (cause + plan first), full suite, tester build (3 zips, one per tester, David agrees). Testers told to ignore cloud drives in the Eject list. **His 12 suggestions decided by David** -> `DEVELOPMENT_NOTES.md` "For the next Mac release, 2.5.6" (right-click Remove from List on both, rename Play With This Sound, Done line opens the Write beside folder, check-don't-lock; NO completion box, NO per-row play icon; PC-only stronger row highlight queued for the M1 after the tester build). Open: an installer (reverses PC Q5, David's call), the tester's USB write (asked), the rename wording (David to pick; M5 suggested Play With Chosen Sound). **MAC 2.5.6 TOP ITEM, David: roll it into 2.5.6:** a blank-named MOV output silently overwrites an earlier one (engine `_analyse_bespoke_ids` skips blank rows; ffmpeg -y), found by the PC's window test, confirmed here; TGA Sequence case requested from the M1. **WAITING ON: the M1** (cloud drive cause + plan; TGA Sequence case) **and David** (rename wording, installer, the tester's USB answer). **For the PC afterwards:** re-pin engine v1.16.0 + swift-ref v2.5.5, copy decision 60/60.1 (incl. PC Clear warning), re-run parity kit (expect 44/44 incl. the 4 Intel cases). (David 2026-10-18: Documents look fine, nothing missing; the Mac manual's example names are "very generic", not an issue, they stay; the M1 to send its exact delete command and path). **Understanding baseline:** commit `7e63967` - 2026-10-19: x64 tester feedback decided (2.5.6 list), cloud drive fix top PC priority, overwrite bug confirmed and rolled into 2.5.6. Before that, `f55b150` - 2026-10-19: tester update plan and the 0.1.0 known-problems note. Before that, `c550f25` - 2026-10-19: PC 0.1.2 accepted (menu boxes fixed, font test, bin-off test); single-frame idea parked; PC guides to 2.5.5 next. Before that, `11d7289` - 2026-10-19: M1 HANDOVER.md done (13383ee); bin-off test advised yes after the try-out. Before that, `b8f7957` - 2026-10-19: PC 2c committed (8edc4f9, 115a788), PC 0.1.1 in David's try-out; Clear answers + HANDOVER.md request sent. Before that, `7e4ddfe` - 2026-10-19: PC re-pinned to v1.16.0/v2.5.5, PC parity kit 44/44; 2c built; PC Clear wording approved with 3 conditions; HANDOVER.md request queued for the M1. Before that, `68ffb83`: MacHuna 2.5.5 LIVE; PC item 6 accepted, PC 2.5.5 catch-up sent. Before that, `47fc88d`: engine v1.16.0 released; Mac 2.5.5 built and notarised, awaiting David's test. Before that, `2dd29ed`: button approved, Open Player added, item 6 sent, colleague message drafted. Before that, `b3835f0`: round 3 accepted; PC Player button to the menu row with a label. Before that, `8c68fb8`: M1 working rules saved (fc7be24); round 3 still to send. Before that, `267aac6`: round 2 results, round 3 and M1 working rules sent; colleague early look agreed. Before that, `c7fb142`: try-out round 1 done, round 2 sent. Before that, `be765b7`: step 16 done; try-out round 1 fixes sent. Before that, `1c90ade`: guides approved, step 16 commit sent. Before that, `d5bc3ab`: manual draft reviewed, M1 incident recorded. Before that, `28ccbb1`: Quick Start draft reviewed. Before that, `142bec2`: documents division recorded. Before that, `82b6b18`: step 15 accepted, step 16 sent. Before that, `9f5cfa2`: step 15 reviewed. Before that, `d5dacba`. Before that, `f480ed4`: stripe fix to be bundled with step 15 (one full run). Before that, `b5fb211`: the stripe finding noted for the next M1 message. Before that, `08ef90c`: suite-timing request noted for the next M1 message. Before that, `1d45d9b`: PC look note. Before that, `478c2a0`: step 14 reviewed, step 15 sent. Before that, `bc6a0e4`: David's own try-out moved to when the build is ready. Before that, `6d2e5b3`: PC Player button size parked. Before that, `e02b9bb`: the try-it package request noted for the next M1 message. Before that, `cca16f9`: PC step 14 reviewed; Mac player memory on the 2.5.5 list. Progress told David: 13 of 16 + P, ~3-6 h of sessions to the colleague build. Before that, `5a8052b`: PC download choice decided (two labelled downloads, page highlights). Before that, `5989c44`: Azure set-up parked at step 6 (below); still WAITING ON the M1 for the 60 s player measurement and step 14. Before that, `1bb0568`: **PC step 13 (the player) DONE** (MacHuna-PC `7e4ddae`..`014e334`, decision 28, selftest 22/22, ui-step13 48/48; checked by pulling; the fourth quadrant is Audio, as the Mac). M1 decode ~130 ms/frame pipelined under emulation (Mac 22 ms): asked for a 60 s keyed SWS load time and peak memory. **Step 14 sent with rules:** update manifest URL FIXED as `https://dnsvision.tv/machuna/version-pc.json` (baked into every PC copy, never move; the M5 creates it at publish), HTTPS with Windows' trust store and never disabled checks, support `machuna@dnsvision.tv`, differing wording to David first. **WAITING ON: the M1** ("STEP 13 REVIEW (1 PART)"). Earlier the same day: **Azure set-up PARKED at step 6** (memory `project_azure_signing_setup.md`): Microsoft account david@dnsvision.tv (separate from David's personal one), 2FA on; Azure subscription Active on "Azure Plan" (pay-as-you-go), paid by Tide's virtual Online Debit card; Microsoft.CodeSigning registered. Creating the Artifact Signing account starts billing and the identity check (days to weeks), so it is started WHEN THE COLLEAGUE TEST BEGINS. Nothing billable yet. **PC signing explained to David** (Windows has no notarisation: Authenticode + SmartScreen reputation). **DNS Vision is a limited company**, so the route is **Azure Artifact Signing** (the renamed Trusted Signing; ~$9.99/month Basic, paid subscription; individuals only US/Canada; whether a trading history is needed is unclear, confirm with Microsoft). Using the company only to sign a free app is fine (a certificate proves the publisher, not a sale; not legal/tax advice). David's steps: Azure account and paid subscription, an Artifact Signing account, DNS Vision's identity validation (days to weeks; suggested he starts now), a certificate profile with signer role. Then the M1 signs our own exes with a timestamp in `package.ps1`, a clean-PC test, publish unchanged from the M5. Still after the unsigned colleague test. Before that, `7dddcd0`: **PC step 12 DONE** (MacHuna-PC `8c7a720` B8 icon row + B14 2.5.5 items waiting for the Mac, `9af3881` decision 27, `020782e` ui-step12 29/29, `0e0443c` tests end the explorer.exe they start (75 had held 6 GB; ended with David's OK); --selftest 17/17; David's screenshot kept as docs/mac-reference/sound-from-the-clip-dark.png, PC matches; checked by pulling, 45% dimming = CV:2074). **M5 ruling:** keep the PC's drag-out lines ("Saved the sound as X.wav." / "Nothing was saved.") as WINDOWS DIFFERS (Explorer's "Don't copy" can save nothing; the Mac makes "Name 2.wav"); David may overrule. **WAITING ON: the M1** ("STEP 12 REVIEW (1 PART)": step 13 the player in parts 13a views, 13b transport/timing/holding/TGA rate, 13c audio + meters, 13d wiring; timing in the VM is a floor under x64 emulation, the colleague's PC is the real check). Before that, `eaf3046`: PC step 11 reviewed, step 12 sent (sound-column addition and Ignore key included). **Progress told David:** after step 12, 12 of 16 steps + P; left 13 player (biggest), 14, 15 (his stick), 16 (his reading), re-zip, colleague, signing, publish; ~8-15 h of sessions, measured from MacHuna-PC commit times (~1-2 h per step). Estimates now in session hours, not guessed days. Before that, `be1cd75`: "Ignore key" works only for SWS, David's decisions recorded for 2.5.5 (MOV ticked = no alpha channel; hidden for K-Frame TGA, Sony TGA, EIF); the chip and Sound column waveforms kept apart. Before that, `3e29425`: PC step P reviewed; sound-cell addition held for the next M1 message (see WAITING ON). Before that, `766bdb1`. Before that, `e122fe3`. Before that, `ff28491`: the Mac-first release gate (roadmap); parity kit 40/44 on the PC, ruling given (see WAITING ON). Before that, `855a92b`. Before that, `881b994`. Before that, `98ae9b0`: PC step 10 reviewed; 2.5.5 decisions; parallel-support plan (roadmap); colleague gets the PC only when completely finished (David). Before that, `29b0283`. Before that, `ec5803a`. Before that, `b8b9ee6`. Before that, `674abfa`. Before that, `533553c` - 2026-10-16: parity kit built and proved; PC step 9 reviewed; packaging after step 10; no colleague preview; long-path wording approved (see WAITING ON). Before that, `1c0e78e`. Before that, `0d80230`. Before that, `b924a59`: PC step 8. Before that, `aa8edd3`: sound-cell note for step 12. Before that, `7249990`. Before that, `033b2eb`. Before that, `c50cca5`: PC step 6 reviewed. Before that, `089c446`. Before that, `caa803e` - 2026-10-16: MacHuna 2.5.4 live on engine v1.15.4 (Swift tag `v2.5.4`); the M1's overnight ffmpeg build and v1.15.4 pin all green; **swift-ref added at v2.5.4 (MacHuna-PC `83d9dfd`, checked by pulling): 43/45 bridge checks, plain launch, own ffmpeg (the 2 are the player buffer, by design).** PC UTF-8 mode KEPT for parity with the Mac (roadmap). Next: the WPF skeleton, once David approves the .NET SDK on the M1. **How the M5 and M1 work (David, 2026-10-16): in turns, through David.** Each side does its step, then asks the other to confirm it or for the next step; every M5 message to the M1 ends with one clear ask; the M5 tracks whose turn it is and keeps the notes current at each turn. **PC interface step 1 DONE 2026-10-16** (MacHuna-PC `f9a3ce3`, decision 10, checked by pulling): WPF skeleton, `Engine.cs` mirrors `Engine.swift` (one bridge, JSON lines, PATH constructed, PYTHONUTF8, no BOM on stdin, stderr drained), win-x64 self-contained, `--selftest` 10/10, falsified with a foreign ffmpeg on PATH; a UI-thread deadlock found by trace and fixed. Engine finding (check_ffmpeg says "brew install") put on the roadmap for the next engine release. **PC step 2 DONE 2026-10-16** (MacHuna-PC `1183399`, decision 11): one conversion through the real window, driven by UI Automation: Done only from bridge events; SWS identical to `convert_clip()` run directly except the header time (0x148/0x168); Stop leaves the file in progress to finish and the next row Queued. **Stop stays as the Mac does it (M5, 2026-10-16):** "stops after the file in progress" (manual 4.8; the Python app said the same), except EIF routes, which check the cancel flag per frame and leave nothing (manual line ~135). An immediate Stop would change both apps: David's call, not proposed. **PC step 3 DONE 2026-10-16** (MacHuna-PC `3d1fbc4`, decision 12): the WAV drag-out as a Windows virtual file (FileGroupDescriptorW + FileContents): written only when Explorer asks on the drop, to a private %TEMP% folder opened delete-on-close, bytes identical to `write_sound_wav`; cancelled drag writes nothing; real mouse into real Explorer proved by UI Automation; EIF Stop leaves an earlier same-name pair intact. **Accepted (M5, 2026-10-16): on Windows a taken name gets Explorer's own "Copy and Replace / Don't copy" dialog** instead of the Mac's "Name 2.wav", because Windows never tells the source app the drop folder; nothing is replaced unless the user chooses Replace, and "Don't copy" never makes the WAV. Needs David's hands later: real trackpad drags, Desktop/stick/other-app drops, and a real Intel/AMD PC. **PC step 4 DONE 2026-10-16:** drop-failure check 23/23 (MacHuna-PC `57ae7ae`, `cb1dddb`); **`PARITY_PLAN.md`** (`b5a41f3`): Windows translations, 13 tables of every Mac feature (BUILT / NOT YET / WINDOWS DIFFERS), build steps 5-16 + P + T, eight questions. **M5 answers:** Q1 menus (Settings under File, About/Updates/Engine Check under Help) agreed; Q2 PC editions of the manual and Quick Start in `pc\docs`, David reviews wording, agreed; Q3 Add… plus Add Folder… agreed; Q4 keep the stick tidy-up, agreed; **Q5 DECIDED by David: a zip of a folder, no installer**; Q6 all five Mac findings CONFIRMED (see roadmap "2.5.5"; publish.sh's lost checks restored in Swift `d5a0df2`, pushed with David's OK); Q7 reserved names go in the next engine release; Q8 test long paths in step 9, clear message. **Look:** David wants the PC to look as close to the Mac as possible; he takes screenshots of the Mac app (neutral self-test media only: `testmedia/selftest`, no client names) for `MacHuna-PC/docs/mac-reference/`, and compares the M1's PC screenshots of the same states. **PC step 5 DONE 2026-10-16** (MacHuna-PC `05b1c95`, decisions 14-15): the real window shell, menus, Settings, settings.json with the Mac's keys; UIA 103/103; screenshots in `docs/pc-screens` beside David's `docs/mac-reference` (M5 compared the light two-clip window: very close; differences are the planned steps 8 and 12, the row icon, column widths). **Finding (PC decision 15): the x64 build freezes at start-up in 2-12% of launches in the Parallels VM** (MacHuna x64 7/60, a bare WPF window 1/60, MacHuna ARM64 0/60); the M1 blames Windows' x64 emulation. **M5: not proven, and it matters beyond the VM** because Windows-on-ARM laptops run the same emulation (David was told ARM "works"). Asked for memory dumps of frozen starts (where the UI thread waits) before step 6; agreed the 30-launch check for the real-PC test; accent colour follows Windows' accent everywhere, as the Mac follows its own. **Step 5 review and step 6 DONE 2026-10-16** (MacHuna-PC `ee88c25`, `4195e48`, decisions 15-17, checked by pulling): accent follows Windows' accent everywhere; **the freeze traced** with three dumps and a live attach: the DLL loader lock held by a thread inside the x64 emulator, no MacHuna code on any readable stack (bare WPF froze too; native ARM64 0/60, x64 7/60). M5 accepts that it is not MacHuna's code, but it is real for ARM laptops; the M1 recommends also shipping a native ARM64 build. **Open before deciding:** do the x64 child processes (ffmpeg, the bridge's Python) hang under emulation too? Asked the M1 to count. Step 6 adding files: refusals before adding in the Mac's words, sequences, split folders, sidecars ignored, insertion line, File > Open/Open Folder, + menu; UIA 45/45 with real Explorer drags, a broken build caught. **Two Mac findings from it, confirmed in `ConversionView.swift`, decided by the M5 for both apps:** (1) a refusal with a batch already loaded sets `problem` (CV:1734) and greys Convert for a valid batch: make it a red note that does not block, as re-adding already is (CV:1754); (2) the status note is never cleared, so "X is already in the list." outlives a later good add or an emptied list: clear it on a successful add and when the list empties. Both in the 2.5.5 list; the PC builds them now. **Step 6 review and step 7 DONE 2026-10-16** (MacHuna-PC `fb81d3e` decisions 18-19, `bf2c796` decision 20, checked by pulling): the two status fixes built, red measured, each broken once and caught. **Child processes under x64 emulation: ffmpeg -version 0/200 hung, the bridge's Python 0/200**, so only the interface (.NET/WPF) needs to be native ARM64; Python, numpy, Pillow and ffmpeg stay x64. **M5 decision: ship a native ARM64 interface as well as x64** (same code, `-r win-arm64`). How users get the right one (two buttons, or the page choosing) goes to David at packaging. Step 7: formats offered and the adaptive inspector by the Mac's rules, Convert-menu mirrors, the K-Frame TGA desk question word for word (checked against CV:1470-1482); UIA 119/119, a broken build caught. Its test file landed in `fb81d3e` rather than `bf2c796` (hygiene only). Found on the Mac by the screenshot: "Only the 1 progressive file at 50fps or more depend on this" (CV:1478; singular wants "depends"), put in 2.5.5. Two columns both titled "Name" for MOV and K-Frame TGA is the Mac's own design (decision 50), copied faithfully. **SENT 2026-10-17 in "STEP 11 REVIEW" (was HELD): fold "ADDITION FOR STEP 12" into the M5's NEXT message to the M1 (and tell the M1 to ASK DAVID where his Mac example screenshot with sound is, before building step 12; and say the step 11 chip waveform (CV:787, EIF with .eaf) is NOT this one: the Sound column icon is CV:2034/2046, before converting) (David's reminder; M1 to add both to PARITY_PLAN B8 and confirm; David to send a Mac screenshot with sound). Originally: to raise with the M1 at step 12 (sound), from David 2026-10-16:** the PC's Sound cell lacks the Mac's purple waveform icon and the second line "Sound 1.7s · picture 1.7s". The second line is already in PARITY_PLAN B8 as NOT YET; the icon is not listed anywhere, so add it. Cause: the Mac reference screenshots had no sound; give the M1 a Mac screenshot with sound (David has one, self-test media). **Step 7 review and step 8 DONE 2026-10-16** (MacHuna-PC `2a54471` caption "depends", `1814e70` decision 21, `1bee07b` step 8 under the wrong message, relabelled by the empty `116adb4`, no force push; BOMs in four titles, cosmetic; checked by pulling): Naming.cs ports Item.swift; sequential numbering seeded at highest + 1; Tab walks editable fields without trapping; validation through `validate_bespoke_ids` incl. on window activation; Move Up/Down Ctrl+Alt+arrows; column widths as CV:419-485 (checked: Saves as 150/200, Sound 150/210, Status 96/130). --selftest 15/15, ui-step8 44/44, broken builds caught. PC choice accepted: at its minimum window the columns share the room instead of scrolling. **Mac gap found from the step 8 screenshot (sequence + still, Sony TGA):** a still in a batch whose format is not Kahuna SWS shows "Queued" and a Saves as name, and fails only at Convert (`bridge.py:821` "Stills convert to Kahuna SWS only."); nothing in the Swift app says so before. Put on the 2.5.5 list; the PC copies the Mac as it is until then. **Step 9 DONE 2026-10-16** (MacHuna-PC `18e951d`, decision 23, checked by pulling): destination count (Hidden attribute counted as the Mac's hidden flag), Change/Show, Clear to the real Recycle Bin (one item restored in the test), FileSystemWatcher, vanished outputs, Write beside with its three checks (subst drive, IMAPI2 read-only disc, free-space hook). PC translations accepted: same drive = same path root, a drive root is a fine place to write, never Windows' own folders, "can it write" by writing and removing a dot-named probe (Windows ACLs; the Mac uses isWritableFile). **Long paths measured:** 243 chars wrote, 258 failed with a bare FileNotFoundError; checked before Convert (folder + name + ".name.partial" > 259): **wording APPROVED by David 2026-10-16 (the original):** "This destination's path is too long for Windows: the files would need N characters, and Windows allows 259. Choose a destination with a shorter path." **Mac bug confirmed (CV:1251):** after a Write beside batch the status says "Done. N written to <chosen destination>", but the files went beside the sources; use the folder actually written into. On the 2.5.5 list. **Step 10 needs a parity kit from the M5** (to build next): identical self-test SOURCES (not regenerated, since the Mac's ffmpeg and the PC's differ), a runner that drives `bridge.cmd_convert` per case, and the Mac's SHA-256 manifest with the SWS header time (0x148/0x168) masked; carried to the M1 by David as a zip (AirDrop), never in a repo; Mac outputs themselves only for mismatches. **Packaging moved earlier (M1 suggested, M5 decided 2026-10-16):** step P straight after step 10, before 11, so a preview converts every route; P includes the licences and the GPL source zip (a preview handed to anyone is a distribution) and builds x64 and ARM64. **David decided (2026-10-16): no preview; the colleague tests ONCE, at the end.** The colleague tests MacHuna itself (start-up, the window, converting), not the output files on desk hardware: David assumes the files are right because the engine is the same, and the step 10 byte-for-byte parity kit is what backs that assumption. P is still done early and tested on the M1. **Step 10 DONE 2026-10-17** (MacHuna-PC `48de29a`, `62c7d18`, decision 24, checked by pulling): every route through the window, desk answer and Clear frame reach the job, "too long for EIF" exact at the limit (516; 517 with Start; 518 with Both refused), status line with oneLine ported, popover, progress; ui-step10 28/28, broken build caught. **Three Mac findings, all confirmed in the code, on the 2.5.5 list:** the manual's "only the new ones run" is not what Convert does (David to decide; M5 recommends making the code keep the promise); typed MOV names written upper-cased (bridge.py ~818); MOV offered for a batch with a clip, refused at Convert. The kit run was not in this report. **Parity kit on the PC 2026-10-17: 40/44 SAME** (every SWS, EIF and MOV case). The 4 are TGA written by ffmpeg straight from 4:2:2 10-bit sources: Intel scaler rounding, max 3 levels, invisible; `scale=flags=bitexact` fixes it on the PC and changes nothing on the Mac (M5 checked). **M5 ruling:** accept the 4 as known for now, go on to P; the fix goes into the next engine release with the 2.5.5 bridge, then the kit re-run expects 44/44 (roadmap). **Step P DONE 2026-10-17** (MacHuna-PC `204fcfd` parity results, `9a62fa7` packaging decision 25, `6639ad3` its check; checked by pulling): `packaging/package.ps1` builds MacHuna-0.1.0-windows-x64.zip, -arm64.zip, -open-source.zip and SHA256; each a self-contained MacHuna folder (.NET 10, frozen bridge with x64 Python 3.12/numpy/Pillow/Tcl-Tk as the Mac carries for PIL.ImageTk, ffmpeg 8.1.2, engine, Licences); 50 binaries traced by SHA-256, build stops on anything untraced; source zip has the verified ffmpeg tarball, build script and record; unpacked in a bare environment 15/15 on x64 and ARM64; a new check for the user name and repo paths (ASCII and UTF-16) caught a stale debug dll and stops the build. **Measured:** x64 266 MB unpacked / 114 MB zipped, ARM64 277/109; numpy baseline X86_V2 (SSE4.2, POPCNT): Intel/AMD from about 2009; a 60 s 1080p50 4444 clip to SWS (3,000 frames, 31.7 GB) peaks about 650 MB private memory (Task Manager's 6 GB working set is the file-backed key-plane memory map, machuna.py ~734/754). **Ruled by the M5:** rebuild ffmpeg with a neutral `--prefix` (the configure line in ffmpeg.exe/ffprobe.exe names David's Windows user folder; it would be in the public source zip and binaries) before the colleague test, then re-run the parity kit (expect the same 40/44); "0.1.0" is a working number, the public PC version number goes to David at publish. **Item 1 + step 11 DONE 2026-10-17** (MacHuna-PC `31e14c1` ffmpeg --prefix=/machuna, new sha ffmpeg.exe 19aa1849...d749 / ffprobe.exe 1c2f47a4...2567, user name gone, dev-path exceptions empty, kit re-run 40/44 byte-identical to the first; `460ba2c` + `3a2f806` chips, decision 26, ui-step11 25/25; checked by pulling: copy only, .eaf in every drag, count incl. .eaf, "With its audio" hint, all as CV:660-790). **WAITING ON: the M1** (message "STEP 11 REVIEW (1 PART)": B8 gets the Sound column icon + lengths line, the M1 asks David for his Mac sound screenshot, then step 12; Ignore key recorded in PARITY_PLAN, built when the Mac has it). (Before:) message "STEP P REVIEW (1 PART)". **Mac bug found by David in use 2026-10-17, DECIDED, for 2.5.5 + the next engine release (roadmap 2.5.5 list):** "Ignore key" works only for Kahuna SWS output. Ticked with QuickTime MOV: the MOV has NO alpha channel (not solid white); nothing else changes (unticked and keyless MOVs stay as today; SWS untouched). Hidden for K-Frame TGA, Sony TGA and K-Frame EIF (an EIF cannot be keyless). Nothing changed yet; tell the M1 in the next message too, so the PC hides the box the same way. **David decided 2026-10-17:** finished rows are skipped (only new ones run, as the manual says); a row the format cannot take (a still, or a clip with MOV) is flagged before Convert and just skipped, the rest converts. Both for 2.5.5 and the PC. **The kit zip had not reached the M1:** David asked what it was; explained and shown in Finder; David has now put it in the VM (tell the M1 where). **Told David 2026-10-17:** about 3-5 days of sessions to a build for his colleague if the pace holds (kit run, P, 11 chips, 12 sound, 13 player the biggest, 14 help/updates); unsigned means SmartScreen "More info > Run anyway". **David DECIDED 2026-10-17: finish it completely (all steps to 16) before the colleague gets it; "There's no hurry."** (The M5's after-step-14 suggestion is declined.) (Superseded:) **WAITING ON: the M1** (message "STEP 9 REVIEW (1 PART)", revised: item 2 long-path wording approved, item 3 packaging: step 10 window work, not the matrix, then P); **PARITY KIT BUILT 2026-10-16** (git-ignored, `MacHuna-Swift/testmedia/parity-kit/`; zip `MacHuna-parity-kit-2026-10-16.zip`, 33 MB, sha256 `50939bae...881da6`): 44 cases (every format, desk routes, sound files, clear frames, key, interlace, 59.94, scaling), each one batch through `bridge.cmd_scan` + `cmd_convert` with the Mac's request shape; SHA-256 of every file, only the SWS timestamps 0x148/0x168 blanked and batch logs left out. Mac: two runs 44/44 identical (only the SWS seconds bytes differed, proving the mask is needed and no wider); a changed frame, a missing file and a wrong status each caught; the unzipped kit re-run 44/44, exit 0. Made with engine v1.15.4, bridge as v2.5.4, the Mac app's ffmpeg 8.1.2, numpy 2.5.1, Pillow 12.3.0. **Never remake the sources** (the PC compares against these bytes). David AirDrops the zip to the M1. Docs only here since v1.15.4. Before that, commit `b9a8a04` (tag `v1.15.3`) - 2026-10-15: **engine v1.15.3** (text UTF-8 everywhere, for non-Latin clip names on Windows; guard; Mac unchanged) and **v1.15.2** (tests only: clock frozen) released for the PC version. **MacHuna-PC pushed by the M1** (`85f0c2e`, engine pinned to v1.15.1, its push locked; proof checked, M5 clone at `~/Developer/MacHuna-PC` with its push disabled); the M1 is to move its pin to v1.15.3. **Known for the Swift side:** `bridge.py:1367` reads stdin with the default encoding (fine on a Mac; a PC app must use UTF-8 mode or it changes in MacHuna-Swift). Before that, commit `267c509` - 2026-10-15: PC repo `DNSVision/MacHuna-PC` created (private) and the authorship rule updated (M1 authors only that repo). Before it `9c5d6bf`, the M1's PC decisions recorded in the roadmap by the M5; before it `a1d3469`, David's authorship rule (CLAUDE.md, roadmap). **PC decisions recorded** (DEVELOPMENT_NOTES, "The plan (2026-10-15)"): the PC app is an identical copy of the Mac app; built and signed on the M1, published unchanged from the M5 (SHA-256 checked, Cloudflare key never on the M1); unsigned test on a real PC by a colleague first, then Trusted Signing. M1 suite on `815a52f`: 365 passed, 0 failed, 17 skipped. **M1 push lock PROVED (2026-10-15):** the Windows engine clone has push URL `DISABLED-the-M5-is-the-only-author`; a real `git push` was refused (exit 128), pull still fast-forwards, no unpushed commits anywhere (7d5b67b and its backup branch deleted with David's approval). The Swift clone was reported locked too (its proof not yet seen by the M5). The Mac-side M1 clone is being deleted by David. **PC repo CREATED 2026-10-15 (David's decision): `DNSVision/MacHuna-PC`, private, empty at creation.** The M1 authors and pushes it, and only it; the engine and MacHuna-Swift stay M5-only; publishing stays M5-only after David types the version (rule in `CLAUDE.md`). Setup instructions sent to the M1 (resent in three short-lined parts after the relay cut long lines: keep M1 messages short-lined, numbered and self-contained). Waiting on the M1: first push of its local `pc` work (history checked first; `.gitignore` for builds, binaries and test media; submodule `engine` on `main`), engine submodule pinned to `v1.15.1` with push still locked, and the Swift clone's push-lock proof. **Open questions for the M5 to raise:** what the Windows interface is built with; how the PC repo shares `bridge.py` (it lives in the private Swift repo); the gyan.dev ffmpeg needs its own GPL trace; where the PC download page and manifest live. **To raise with David when the M1 is about to write its first build file:** a separate private PC repo with this engine pinned to a tag. Before that, commit `3163bb1` (tag `v1.15.1`) - 2026-10-15: **engine v1.15.1 released and pushed**, found by the M1 running the suite inside Windows: TGA sequences failed on Windows because an ordinary user may not make symlinks (WinError 1314); `_tga_input_args` now falls back to a hard link, then a copy (byte-identical output, 3 fail-first tests, 382 pass). Nothing changes on a Mac, so **MacHuna 2.5.3 stays pinned to `v1.15.0`; move the pin with the next 2.x release**. The PC version is under way on the M1: **v1.15.1 confirmed on Windows** (suite green bar two timing-sensitive tests; a real memory-stick conversion took the copy path, byte-identical to one from C:). Then commit `0a64805` (test only): the two SWS tests in `TestTgaSequenceWithoutSymlinks` now freeze the clock, because an SWS header holds the time to the second (this was also the one unexplained unittest failure on the M5). Before that, commit `b98503a` - 2026-10-15, MacHuna 2.5.3 live (Swift only, engine unchanged; open-source licences and GPL source, see below); Swift repo at `fb1e652`; both pushed. Docs only here since v1.15.0: the Swift-engine port thought experiment, and **the PC version plan** (DEVELOPMENT_NOTES, "Forking for PC" > "The plan (2026-10-15)"). **David may start the PC version in a Claude session on his M1 MacBook Air** (Windows 11 ARM in Parallels, building x64). That session has none of the M5's Claude memories: it must read this file, `CLAUDE.md`, `MacHuna-Swift/CLAUDE.md` and the plan first. Nothing in progress; otherwise next is the desk checks. Before that, commit `30b5d3c` - 2026-10-13, 2.5.2 live. Docs only here since `v1.15.0`. Earlier the same day: an Appearance setting for the Swift app (Match System / Light / Dark, remembered) is on the roadmap under "Possible features", to go with the next release; the app already follows the Mac's dark mode. Before that, `09079bc` - 2026-10-12 (night): the roadmap now records the first real HDR Kahuna file (a client clip, not named in this public repo): PQ, not HLG, peaking at BT.2408 graphics white (level 572), with an ORDINARY 1080p50 header - so the Kahuna does not record HDR in the file and MacHuna cannot detect it from the header. Its sound track is present but all zeros (written silent by the desk; a WAV extracted from it was rightly silent, not a bug). LUTs added as an idea, not scheduled: user's own `.cube`, fill only, one per batch, logged, player first, wait for a real job. **Never name clients, job folders or source files in this repo** (it is public). Before that, commit `a06e703` (tag `v1.15.0`) - 2026-10-12 (late): clear frames (`clear_frames=` on every route, `add_clear_tga_frames`), split SWS as a conversion source (`open_sws`, split-aware `HulaSWSHeader` with the player's key rule), EIF >517 frames refused in words (open question on the roadmap: can a K-Frame hold more?); released and pushed; MacHuna 2.5.0 live on it. **Desk checks wanted:** a clear first frame sitting invisibly on a cued Kahuna; a rescued old split (963 converted SWS to SWS) keying again; a K-Frame export over ~11 s at 1080p50 to read its header. Before that, commit `b9fb78e` (tag `v1.14.0`) - 2026-10-12 (evening): `write_sound_wav`, released and pushed; MacHuna 2.4.0 live on it. Before that, commit `bcbea4e` - 2026-10-12 (afternoon). **v1.13.1 RELEASED and pushed (tag `v1.13.1`, `fa303be`)**: the split fixes, confirmed on a Kahuna the same day (965 = 961, 967 = 966; the old keyed split 963 loaded with NO key, so the release note says reconvert), plus the log line for an unlabelled HD clip ("Source has no colour label, treated as HD colour (BT.709)", David kept HD). 352 tests. **MacHuna 2.3.0 is LIVE on it.** Next: sound export as WAV (2.4.0, top of the roadmap). Before that, commit `068c89c` - 2026-10-12. Docs only since `be33e87`. **NEXT FEATURE, top of the roadmap: save a clip's sound out as a WAV** (David: "a killer feature"; MacHuna 2.4.0, after 2.3.0 ships; a new engine function over the existing proven readers). Agreed order after the Kahuna desk test: release v1.13.1, notarised 2.3.0 to the requesting user privately with four questions (see MacHuna-Swift/CLAUDE.md), then publish on David's typed "2.3.0". Also: a roadmap entry for audio on stereo pairs 2-4 and key audio, deferred (not rejected) until a user needs it, with a proof plan (DEVELOPMENT_NOTES, after the K-Watch manual note). The Swift app also gained three interface fixes that morning (its decisions 49.2, 50, 51; no engine change). Before that, commit `be33e87` - 2026-10-11 (late), on top of tag `v1.13.0`. **UNRELEASED, waiting for a Kahuna desk test: split SWS files written as K-Watch writes them** (commits `9ee023a`, `1077218`): the sound kept at the end of the stream, 0x1A8/0x1B4 no longer blanked (the 2023 reference splits were keyless, which is the only reason they were blank, so every keyed MacHuna split said "no key"), and 0x1CC = the total size wrapped at 4 GB, split or not. Matched byte for byte in layout and sound against K-Watch's 961 (3 parts) and 966 (6 parts) - see CHANGELOG "Unreleased (to be v1.13.1)" and DEVELOPMENT_NOTES (roadmap, "Split SWS files, measured"). **Desk test files** (961, 965, 963, optional 966/967) are on David's WIPE FILES drive and in `MacHuna-Swift/testmedia/desk/2026-10-11-split/`; after the desk, release v1.13.1, move the Swift pin to the tag (it currently points at the unpushed `1077218`), rebuild 2.3.0. Also tonight: the K-Watch & K-Manager Pro manual read (notes in DEVELOPMENT_NOTES), and `MacHuna-Swift/testmedia/` tidied (209 to 61 GB; layout in its README.txt; `make-testmedia.sh` no longer wipes the whole folder). Before that, tag `v1.13.0` - 2026-10-11 (sound for any clip: a user's Kahuna Manager "Add Audio" request, widened by David to every source; SWS keeps a sound's own length; the user's files are in `MacHuna-Swift/testmedia/user-ref/2026-10-11-noticias8/`, git-ignored). Before that, tag `v1.12.5` - 2026-10-10 (portable app layer for a PC fork; see DEVELOPMENT_NOTES 'Forking for PC'). Before that, tag `v1.12.4` - 2026-10-09 (SWS audio fixed: K-Watch layout and true sample count, confirmed by ear on a Kahuna). Before that, tag `v1.12.3` - 2026-10-08 (v1.12.1, plus 59.94/60 as one family, plus the soft-key precision fix found by the regression run on real material). **v1.12.1 is the engine-soundness release** on top of v1.12.0 (the K-Frame desk-session release): a 324-case conversion matrix through MacHuna 2.0's bridge (273 pass every check, 51 refused on purpose, 0 rule breaks, now including 59.94p/29.97i), three independent reviews and a black-box pass by another model; decisions A-M in the roadmap. 312 tests. Built to `dist/` only; `/Applications` is MacHuna 2.0 and was not touched; nothing published.

**MacHuna 2.5.4 is LIVE at dnsvision.tv (2026-10-16), pinned to `v1.15.4`** (no program MacHuna starts can read the app's requests: before it, about 1 request in 200 could be lost while the bridge itself ran ffmpeg, such as saving a WAV; Swift decision 59; tag `v2.5.4`). Before it, **2.5.3 (2026-10-15), pinned to `v1.15.0`** (Swift only: the app now carries its open-source licences and the GPL source of its FFmpeg, x264, x265 and LAME is published beside every release; 2.0 to 2.5.2 shipped GPL ffmpeg with neither. Swift decision 58, `MacHuna-Swift/Scripts/licences.py`. **Any PC version must do the same.**) Before it, **2.5.2 (2026-10-13), pinned to `v1.15.0`** (Swift only: a clip dropped anywhere in the list is added - since 2.3.0 a second clip could only be added by dropping it onto an existing row; Swift decision 57). Before it, **2.5.1 (2026-10-13), pinned to `v1.15.0`** (Swift only: the Quick Start Guide in the Help menu, the empty list and on the download page, offered once by a strip; Settings > Appearance, Match System / Light / Dark; verified from the live URL as a recipient). **The Quick Start Guide lists features and lives in three places (the Swift repo, the app's Help menu, the download page): whenever a significant feature is added or changed, update `MacHuna-Swift/QUICK_START.md`, rebuild its PDF and the app, and publish the site** (David, 2026-10-13; MacHuna-Swift CLAUDE.md and PUBLISHING.md say how). Before it, **2.5.0 (2026-10-12), pinned to `v1.15.0`** (clear frames; split SWS files convertible; "too long for EIF" before Convert; verified from the live URL as a recipient). Before it, **2.4.0 (2026-10-12), pinned to `v1.14.0`** (save a row's sound as a WAV by dragging it from the Sound column; Swift decision 53; verified from the live URL as a recipient). Before it, **2.3.0 (2026-10-12), pinned to `v1.13.1`** (sound for any clip; split SWS fixed and confirmed on a Kahuna; verified from the live URL as a recipient: notarised, Gatekeeper accepts). Before it, **2.2.1 (2026-10-09), pinned to `v1.12.4`** (SWS sound fixed and confirmed by ear on a Kahuna). Before it, 2.2.0 pinned to `v1.12.3` (2.1.0 brought the engine; 2.2.0 added the memory-stick eject, a Swift-only feature). Still needs hardware: the 2.1 SWS-route changes on a Kahuna, and Sony on a Sony desk. The Swift checklist is in `DEVELOPMENT_NOTES.md` (roadmap, "Swift bridge changes that MUST land with the engine pin move"): pass `include_audio` on the EIF routes and EIF to SWS, replace the bridge's own SWS-to-SWS routing with `convert_sws_to_sws`, remove `Item.swift`'s copy of the hardware warnings, update the Swift app's own manual to match, run `--selftest`. Then build decisions 42-44 (`MacHuna-Swift/DESIGN_DECISIONS.md`). That unblocks the promo film.

**`publish.sh` IN THIS REPO NOW REFUSES TO RUN.** Documentation alone was not enough: on 2026-09-26 a dry run printed "Ready to publish v1.11.0" with every one of its guards satisfied, because all of them compare this repo against *itself* and nothing here knows what is live. Publishing it would have put v1.11.0 over MacHuna 2.0 and offered every user a downgrade. **The procedure now lives in `MacHuna-Swift/PUBLISHING.md` and nowhere else.** Its header documents the deliberate manual route for restoring the old 1.11.0 zip to the bucket without announcing it as an update.

**The roadmap was reconciled** against 2.0 having shipped: distribution moved to the Swift repo, the Apple Developer item is done rather than parked, and the Swift app's own open items are in the one canonical list. Two instructions in `CLAUDE.md` were actively dangerous and are corrected - step 8 said to copy a Python build over `/Applications/MacHuna.app`, which is now the notarised 2.0 app.

**Still open, and untouched by any of this:** the K-Frame desk session. The `.eif` `0x60` bit 2 audio flag, the KNOCKOUT_WIPE round trip, and the rest of the checklist in `DEVELOPMENT_NOTES.md`.

**Previous baseline:** commit `b2f8dd8` - 2026-09-25. Docs only since the v1.11.0 parking: **the code is untouched and stays that way.**

**MACHUNA 2.0.0 SHIPPED ON 2026-09-25, AND IT IS THE SWIFT APP.** `DNSVision/MacHuna-Swift` is now what dnsvision.tv/machuna serves: notarised by Apple, Developer ID signed, stapled, and verified from the live URL with the download quarantine flag set (`accepted, source=Notarized Developer ID`). It took over this repo's update channel and its bundle identifier, so a v1.11.0 copy checking for updates is offered it. **The 1.11.0 zip has been deleted from the R2 bucket** at David's instruction; a verified copy is kept locally at `dist/released/MacHuna-1.11.0.zip` (gitignored) in case it is ever wanted again.

**What that means for this repo.** It is no longer what people download. It remains the **reference implementation**, the **base for the Windows fork**, and **where the K-Frame desk findings will land**. `machuna.py` stays frozen at 1.11.0, and the Swift app drives it unchanged - so a desk fix made here reaches users through the Swift release, not through a Python build. Nothing in `publish.sh` or `website/` here should be run again; that job moved to the Swift repo's copies.

**Still open, and unchanged by any of this:** the K-Frame desk session. The `.eif` `0x60` bit 2 audio flag, the KNOCKOUT_WIPE round trip, and the rest of the checklist in `DEVELOPMENT_NOTES.md`. Shipping a new interface proved nothing about the hardware questions.

**Previous baseline:** commit `b5bb372` - 2026-09-25. Docs only since the v1.11.0 parking: the code is untouched. Two measurement findings were added, both in `DEVELOPMENT_NOTES.md`: **EIF files record no scan type** and the `50i` samples measure progressive 25fps, and **MOV audio into SWS is bit-identical** (81,600 samples, zero length difference, -180 dBFS largest difference), which also confirms programme audio sits on channels 0 and 2.

*(At that point)* **the Mac app `DNSVision/MacHuna-Swift` v2.0.0** was self-contained and ready to publish, pending Apple Developer approval - it has since shipped, as above. `machuna.py` stays frozen at 1.11.0 as the reference implementation and the base for the Windows fork.

**Previous baseline:** commit `e37c144` - 2026-09-25. Docs only since the v1.11.0 parking: the code is unchanged. The one substantive addition is a measurement finding, **EIF files record no scan type and the `50i` samples are progressive 25fps** (see that section in `DEVELOPMENT_NOTES.md`, plus `tools_eif_comb_test.py`), raised because EIF to TGA converts 1:1 with no deinterlacing.

**Previous baseline:** commit `2d71a1c` - 2026-09-18. **v1.11.0 is built, released and PUBLISHED**, and this repo is now **PARKED** at tag `v1.11.0` - see "Swift Rewrite" below. dnsvision.tv/machuna serves v1.11.0 and the manifest announces it.

*(This line said v1.10.3 was the published release until 2026-09-24. It was stale from the v1.11.0 publish onwards, so any session resuming from it started with a false picture. Corrected when the Swift work began.)*

**v1.11.0 - a keyless source gets NO key plane.** CONFIRMED ON A LIVE KAHUNA 2026-09-18 and **the first thing MacHuna deliberately does differently from K-Watch.** The old flat plane loads as a black key and does not key; without it the desk shows Fill only and labels the file `C` not `CK`. Halves every keyless file (896 MB to 448 MB on a 52-frame wipe). `_generate_white_key` removed. **This closes the white-key item that sat in the roadmap for months.**

**Still open on the desk list: the P-to-I field order test (803/804 in Wipes/MacHuna/DESK TESTS).** Blocked 2026-09-18 because the desk was locked to 1080p50 for a show - those files are 1080i50 and field order is meaningless on a progressive desk. Needs a genuine 1080i Kahuna. The files are built and waiting.

**v1.10.0-v1.10.3 are one feature and two of my mistakes.** QuickTime MOV output (SWS, EIF or TGA sequence → ProRes 4444 with the key as alpha and audio where the source has it), plus `.eaf` audio reading. v1.10.1 added per-item naming; v1.10.2 gave MOV its own frame-rate control; v1.10.3 restored deinterlacing. **David found every one of the three gaps within minutes of opening the app**, after I had verified the feature four different ways.

**The pattern, and it is the thing to carry forward: I kept testing that the conversion WORKED, never that it was USABLE on real material.** v1.10.0 converted correctly but gave no way to name the file. v1.10.1 had no way to express 30fps, because I had wired MOV to the SWS Standard dropdown whose only 30fps entries are interlaced - so his 30fps sequence played at double speed. v1.10.2 then removed the interlace option entirely on the reasoning that ProRes has no field-order flag. **That reasoning is true of WEAVING and irrelevant to DEINTERLACING** - frames that already contain fields stay combed in a "progressive" file. Ask what a real job looks like, not just whether the bytes come out.

**How MOV works now.** Frame rate control (23.976-60) appears for TGA input only; SWS and EIF declare their rate in the header. **TGA source interlaced** deinterlaces by bobbing: one frame per field, so 25fps interlaced becomes 50fps progressive of the same length. `convert_tga_seq_to_mov` takes a separate `out_fps` for exactly that - pinning the output back to the source rate would throw the bobbed frames away. A MOV is never woven into interlace.

**Testing lesson worth more than the code.** The first tests written for the frame-rate bug were worthless: they drove `convert_tga_seq_to_mov` directly and **passed with the bug deliberately reintroduced**, because the fault lived in `_run_to_tga_seq` inside `launch_gui()`. Structural guards now cover both MOV behaviours, and both were falsified by breaking them. Note the limit: they catch the block being *deleted*, not *neutered* while the names survive.

**`.eaf` reading is CONFIRMED BY EAR** (David, 2026-09-17): correct audio, correct pitch, correct speed from `0003.eif`. One listen that confirms 48kHz, big-endian and the channel-1/3 choice together. The MOV's audio is bit-identical to the `.eaf` source.

**macOS floor is 26 and that is deliberate** - see `DEVELOPMENT_NOTES.md`. It comes from Homebrew bottles and pip wheels following the build machine, not from the code. The page now states it honestly instead of promising macOS 12. Do not propose fixing it unless a user reports a failure.

**Known, not scheduled:** nothing on the Convert screen says the MOV output will be progressive - you have to know. David asked exactly that question. A line of text beside the tickbox would settle it.

**DESK SESSION - READ THIS FIRST WHEN WE RESUME.** David will sit beside the K-Frame with the laptop and Claude live, so run from source, not `dist/`. Work from the checklist in `DEVELOPMENT_NOTES.md` ("EIF Roadmap - hardware verification first"). **Top two: (1) the `.eif` `0x60` bit 2 audio-flag test - MacHuna sets it on every file and never writes the companion; do NOT change that byte beforehand; (2) the KNOCKOUT_WIPE round trip, baselined with falsifiable predictions in `DEVELOPMENT_NOTES.md`.** Also: should a keyless source get a key plane at all, `.eaf` channel mapping, tail length, clip-name/slot rules.

**Open:** the Kayenne desk session (booked - EIF `0x60` audio-flag test first, then `.eaf` channel mapping, which is the last thing standing between MacHuna and writing EIF audio); and the white-key investigation, now the only code-only item left.

**v1.9.1 - the data offset is read from the header, not assumed.** Some SWS files put the video planes after a **3072-byte header**, not 512. `0x19C` has always said so (MacHuna writes its own header size there) and nothing ever read it back, so those files were read **2560 bytes early = exactly half a 1920-pixel v210 line**, and the picture looked split down the middle with the halves swapped. **Four extraction paths had the same hardcoded 512**, so converting such a file to EIF/K-Frame TGA/Sony TGA/TGA-sequence sheared it silently. Invisible until v1.9.0 because the affected files were big enough to be split and splits could not be opened at all - fixing one bug exposed the other. Use `sws_data_offset()`; never hardcode 512 for where data starts. Verified across all seven joins of an 8-part clip in both planes.

**v1.9.0 - the Video Player opens split files, and loads long clips at all.** A user could not check a 20-second graphic bed. A clip over 4GB is a *folder* of 2GB chunks, and the macOS file dialog navigates into folders rather than selecting them - so they reached a single chunk, and only the first carries a header. The folder **or any chunk inside it** now loads the whole clip; the info strip says `Split: 3 parts`.

**The real blocker was never the split format.** `PlayerFrameCache._load` read the entire video plane in one call - **5.5 GB in a single object** for a 1000-frame 1080p clip, before decoding started. It now decodes in batches of 20 frames, peaking at 1.37 GB, and the finished cache is pixel-identical (verified frame by frame, fill/key/composite, against the old path). A single 4GB file would have failed identically.

**Two things I got wrong, both worth remembering.** I proposed on-demand streaming decode, having *assumed* frames were held at full resolution - they are stored at panel size (480x270), so **playback decodes nothing at all** and streaming would have solved the wrong problem, while making frame-stepping worse if transport controls are ever added. What forced the re-read was David pointing out that playback already stutters with everything in memory. Then I was about to strip two stutter counter-measures for "not working", when all I actually knew was the stutter persisted - not that they had no effect. **Read the code; and do not confuse "the problem remains" with "this change did nothing".**

**Known limitation, documented not fixed: the first-play stutter.** It is not decoding. The likely cause is `_playback_loop` scheduling each frame then sleeping a fixed interval **without checking the previous frame was drawn** - no back-pressure, so slow draws queue and arrive in bunches, which fits short clips, long clips, and it settling after a few plays. Fixing it means pacing against display completion: real video-player engineering on a feature whose job is a confidence check. Deliberately not attempted; the native rewrite gets a proper media view. Two counter-measures are kept in `_on_load_complete` with **cost measured at effectively nothing and benefit unproven** - the comment says so, so nobody assumes they are load-bearing or removes them assuming they are useless.

**Also fixed:** `has_key` for split files (was read from byte `0x1A8`, which splits zero; now derived from total size) and the audio length (`getsize()` on what is a folder).

**150 tests.** New coverage for split detection and reading across chunk joins. Four GUI drivers now live in the session scratchpad: interaction, pixel alignment, end-to-end conversion, and split playback.

**Open:** the K-Frame desk session (booked, agenda recorded in memory - the EIF `0x60` audio-flag test first); EIF audio reading, buildable now; and the white-key investigation.

**On resuming:** run `git log --oneline 5948e77..HEAD` and `git status -s` to see what changed since the baseline, and reconcile against the code before trusting this document. Update this block (commit + date + one line of what moved) at the end of any session that changes the repo. See "Staying current between sessions" in `CLAUDE.md`.

*(Note: the per-session narrative below stops at v1.6.6. v1.6.7-v1.6.11 are recorded in `CHANGELOG.md` and the version-history line in `DEVELOPMENT_NOTES.md`, not here.)*

---

## Recent Session Notes (June 2026 — v1.6.6)

### v1.6.6 — Sony TGA output for TGA sequence input

- `OUTPUT_SONY_TGA` added to `to_sws_only` output options in `_update_output_options()`.
- `_update_adaptive_controls()` Sony TGA branch now also shows `chk_tga_int` ("TGA source interlaced") when `_has_tga_seq[0]` is set.
- `worker()` routing: `elif out == OUTPUT_TGA_SEQ or (out == OUTPUT_SONY_TGA and itype == 'to_sws_only')` routes to `_run_to_tga_seq()` instead of falling through to `_run_from_sws()`.
- `_run_to_tga_seq()` extended: detects `is_sony = (out == OUTPUT_SONY_TGA)` at the top. When Sony: output folder is the 4-char clip name (`cn`), output pattern is `CN%04d.tga`, start number is `0` (Sony 0-based). Otherwise unchanged.
- Existing guards (4-char clip name validation, single-clip guard) already applied to all `OUTPUT_SONY_TGA` cases — no changes needed there.

---

## Recent Session Notes (June 2026 — v1.6.5)

### v1.6.5 — SWS→SWS conversion + TGA Sequence output + Kayenne MOV removed

**SWS→SWS standards conversion (i↔p):**
- "Kahuna SWS" added to the Output dropdown when input type is `from_sws`.
- Routed through `_run_to_sws()` → new `sws` branch: extracts SWS frames to a temp TGA dir via `_hula_convert_tga`, then calls `convert_tga_sequence` to re-encode.
- Source interlace auto-detected from SWS header (`'i' in HulaSWSHeader.standard`) — no user checkbox.
- I→P uses `yadif=mode=send_field:parity=tff` (target fps > source fps) or `yadif=mode=send_frame:parity=tff` (same/lower). P→I uses `tinterlace=mode=interleave_top`. Passed via new `_vf_override` parameter on `convert_tga_sequence` to bypass the existing frame-duplication path for i→p.

**TGA Sequence output:**
- New constant `OUTPUT_TGA_SEQ = "TGA Sequence"` added to output constants.
- Appears in `to_sws_only` (TGA/stills input) and `mov_only` (video clip input) dropdown options.
- New function `_run_to_tga_seq()` handles conversion via ffmpeg concat demuxer (TGA input) or direct `-i` (clip input). P→I: tinterlace. I→P: yadif. Passthrough: no filter.
- Routed in `worker()` via `elif out == OUTPUT_TGA_SEQ`.
- "TGA source interlaced" checkbox is shown when input has TGA sequences.
- Output: `0001.tga, 0002.tga…` in `{dest}/{sequence_base}/` subfolder.

**Kayenne MOV removed from SWS output options:**
- Removed from `_update_output_options()` `from_sws` branch.
- Removed from `_run_from_sws()` `target_map`.
- Withdrawn because it was unconfirmed on hardware and not consistently available across all input types.

**`convert_tga_sequence` change:**
- Added `_vf_override: str = None` parameter (internal). When set, bypasses automatic filter detection and uses the supplied ffmpeg filter string directly. Also suppresses frame duplication in the concat file (`do_i_to_p = False`). Used by the SWS→SWS i→p path to apply yadif. Default is None — no change to existing callers.

---

## Recent Session Notes (May 2026 — v1.6.2)

### v1.6.2 — EIF→EIF routing bug fixed; doc corrections

- Removed "Kayenne EIF" from the Output dropdown when the input is EIF files (or a mixed EIF+SWS folder). EIF→EIF conversion was never implemented — `_run_to_eif()` has no handler for `item['type'] == 'eif'`, so EIF files were silently skipped. The option is now absent rather than offering a no-op. Sourcing SWS→EIF from a mixed folder still works via the SWS path.
- Corrected README input detection table (removed Kayenne EIF from EIF source output options).
- Updated HANDOVER_NOTES v1.5.41 historical notes (internal contradiction: bits[29:20] was described as a "constant framing marker" in the confirmed encoding section, then correctly as the key channel two paragraphs later).
- Updated Feature Summary to include EIF features.
- Updated project memory file version.

---

## Recent Session Notes (May 2026 — v1.6.1)

### v1.6.1 — Code cleanup

Post-EIF deep review. No functional changes.

- Removed five dead functions that were superseded by earlier refactors: `_pick_from_folder`, `_load_from_item` (replaced by `askopenfilename` direct picker), `_scan_folder_for_items`, `_scan_folder_for_player` (replaced by `_scan_folder_unified`), `_group_files_for_batch` (replaced by unified batch path).
- Extracted shared EIF bit-decode logic into module-level `_eif_parse_unit(raw) -> (yuv, key)` helper; removed duplicated inner `_unit_arrays` from both `_decode_eif_frame` and `_decode_eif_frame_rgba`.
- Moved `_EIF_UNIT_BYTES` constant from mid-file to the EIF constants block; removed three redundant `import numpy as np` from function bodies.
- Fixed Video Player status bar: still read "select a folder" after the switch to file picker.

---

## Recent Session Notes (May 2026 — v1.6.0)

### v1.6.0 — Full EIF feature set

This release completed the EIF (Grass Valley Kayenne native format) feature set. EIF was reverse-engineered from real Kayenne-produced files across v1.5.39–v1.5.43, with all conversion paths added in v1.6.0.

**What was added:**
- EIF as a conversion output: TGA sequences, MOV, and SWS files can all be converted to `.eif`. Slot naming uses 4-digit zero-padded filenames (0001.eif, 0002.eif…) matching Kayenne's naming convention. A slot spinbox lets the user set the starting slot number.
- TGA source interlaced option for EIF output: uses ffmpeg frame duplication (same concat-repeat approach as TGA→SWS interlaced path) to produce 50fps progressive EIF from 25fps interlaced TGA.
- Batch log written to destination folder after EIF batches.
- EIF as a conversion input: EIF files now appear in the main conversion picker. Folders with EIF only (`from_eif`) and mixed EIF+SWS (`mixed_eif_sws`) both route to EIF-aware outputs.
- EIF → Kahuna SWS: lossless direct YCbCr repack using `_eif_frame_to_v210be`. No RGB round-trip. Output standard auto-derived from EIF fps (ignores user's Standard dropdown).
- EIF → Kayenne TGA: full-res 1920×1080 RGBA TGA sequence, progressive or field-woven interlaced.
- EIF → Sony TGA: 32-bit RGBA with 4-char clip name prefix, progressive or field-woven interlaced.
- Video Player file picker changed from folder picker to standard file picker (files can be clicked directly).
- Format label added to Player info strip for all formats (SWS, TGA, MOV, EIF).

**What is NOT yet confirmed on hardware:**
All EIF write paths are UNCONFIRMED pending a live Kayenne desk test. See DEVELOPMENT_NOTES.md "EIF Hardware Unknowns and Roadmap" for the full table and priority test steps. Key outstanding items:
- EIF write output — never loaded on a live Kayenne desk
- 25fps EIF movi chunk tag at 0x8DC — assumed, no 25fps reference file available
- EIF→Kayenne TGA / EIF→Sony TGA — coded, never hardware-tested
- EIF audio (.eaf companion files) — not implemented; format unknown
- Tail length discrepancy (128 vs 140 bytes for fc≥36)

**EIF pixel format (confirmed from real hardware):**
- 32-bit LE word per pixel: bits[29:20]=key, bits[19:10]=Y, bits[9:0]=C (even=Cb, odd=Cr)
- Three 360-row units stacked vertically = 1920×1080 per frame
- Frame duration at header 0x0FC: 40000µs = 25fps, 20000µs = 50fps

---

## Recent Session Notes (May 2026 — v1.5.41)

### v1.5.41 — EIF key channel decoded; v1.5.40 — EIF colour decode fixed

EIF pixel format fully reverse-engineered from a real mountain bike clip (UCI DOWNHILL WORLD CUP title card, file `0003.eif`).

**Confirmed EIF pixel encoding (final — as implemented):**
- Each 32-bit LE word = one pixel: `bits[29:20]` = key (10-bit limited: 64=transparent, 940=opaque), `bits[19:10]` = Y luma, `bits[9:0]` = chroma C
- Chroma assignment: **even columns = Cb, odd columns = Cr** (standard 4:2:2 horizontal subsampling)
- Each unit is **360 rows × 1920 columns** (not 540×1920 as originally assumed)
- Three units stacked vertically = **1920×1080** complete frame

Note: v1.5.40 initially interpreted `bits[29:20]` as a "constant framing marker" (because wipe key clips have key=940=fully opaque throughout, which looks like a constant). v1.5.41 confirmed it is the key channel — wipe-pattern clips have key values that vary spatially and temporally. v210-based decode was entirely wrong; the current custom bit-field decode is correct.

**Key channel behaviour (confirmed v1.5.41):**
- For fill clips (e.g. DOWNHILL title card): key is always 940 = fully opaque
- For wipe/key clips (e.g. 0301.eif): key ramps from 64 to 940 and back, producing the correct wipe matte
- `EIFHeader.has_key = True` always; fill, key, and composite panels all populated

**Still unknown:**
- Tail section after `video_end` — suspected audio or some index; not yet decoded
- Audio: companion `.eaf` files believed to carry audio; `has_audio` remains False for now

---

## Recent Session Notes (May 2026 — v1.5.39)

### v1.5.39 — EIF playback (experimental)

Grass Valley Kayenne `.eif` format reverse-engineered via hex analysis of a live Kayenne-produced file. Confirmed findings:

- **Container**: GV proprietary header (220 bytes) + RIFF/AVI thumbnail + EIF metadata + pre-video fill + video data
- **Header fields** (all little-endian): clip name at `0x004` (null-terminated ASCII), flags at `0x060`, logical frame count at `0x06C`, video start at `0x070`, video end at `0x080`
- **Video data**: 360 rows × 1920 cols × 4 bytes/pixel, 2,764,800 bytes/unit, 3 units per frame stacked vertically = 1920×1080

---

## Recent Session Notes (May 2026 — v1.5.38)

### v1.5.38 — Video Player folder picker + fps dialog fix

- **Video Player folder picker**: Open… in the player now prompts for a folder (not a file). Scans for SWS, TGA sequences, and video files; TGA sequences collapsed to one entry per sequence. Shows a single-select list; double-click or Open loads the item. Mirrors the Convert window's existing folder browser behaviour. If only one item is in the folder, it loads directly.
- **TGA fps picker fix**: The frame-rate dialog after selecting a TGA sequence could appear behind the window or be unresponsive. Fixed by correctly sequencing `transient()`, `update_idletasks()`, `grab_set()`, and `focus_force()`.

---

## Recent Session Notes (May 2026 — v1.5.33)

### v1.5.33 — Unified format-in / format-out interface

MacHuna and Hula are now one tool. The separate Hula button and HulaWindow are gone. A single Convert section with input autodetection and an adaptive Output dropdown handles all conversion directions:

- **Folder scan → autodetect**: SWS files → FROM-SWS outputs (Kayenne MOV / Kayenne TGA / Sony TGA). MOV/video files → Kahuna SWS or TGA (with hardware-unconfirmed warning for MOV→TGA). Mixed video/TGA/stills → Kahuna SWS only.
- **Adaptive controls**: Standard, Split >4GB, Ignore alpha, Auto play, Loop play, TGA source interlaced, Include audio, Clip name (Sony TGA), BFF/TFF field order — shown only when relevant.
- **Sony TGA folder naming**: output subfolder now named after the 4-character clip name rather than the SWS stem.
- **"Video Player" button**: replaces "SWS Player" label; more accurate since it accepts SWS, TGA sequences, and video files.
- **`HulaWindow` class**: removed in post-v1.5.33 cleanup. All extraction engine functions (`_hula_run_batch`, `_hula_convert_tga`, `_hula_convert_mov`, etc.) remain unchanged.

The unified UI was the long-term direction discussed in v1.5.31 session notes. The hardware unknowns (Kayenne MOV, Kayenne TGA, Sony MVS clip naming, MOV→TGA) remain unconfirmed — the unconfirmed warning dialogue handles this at runtime.

---

## Recent Session Notes (May 2026 — v1.5.32)

### v1.5.32 — TGA Workflow Overhaul

Watch Folder and Slot Override were removed. MacHuna is positioned as a field tool for freelancers, not a networked server app. Watch Folder was a legacy of the K-Watch workflow that David confirmed would never be used in practice.

Key changes:
- **Smart folder browser**: "Open Files…" opens a folder picker; TGA sequences are collapsed to one entry (e.g. `TNTS201  (30 frames)`), video files and stills listed individually. User selects items and clicks Convert.
- **"Use source file number" checkbox**: replaces Slot Override. K-Watch files have slot number embedded in filename; ticking this uses it. Unticked = sequential from Start Number.
- **i→p TGA fix**: ticking "TGA source interlaced" when converting to a progressive standard now duplicates each frame to preserve duration (was playing at double speed before).
- **"Include audio" contextual**: moved into the folder browser dialog, only appears when audio is detected in a video file. Hidden for TGA-only folders.

---

## Recent Session Notes (May 2026 — v1.5.31)

### Unified App — Strategic Discussion (May 2026)

A strategic discussion was held about MacHuna's long-term direction. The core insight: MacHuna started as an SWS converter with Hula added as an optional extra. But the conversion engine now handles MOV, TGA, and SWS in both directions — making it more accurately described as a fully featured format conversion engine for broadcast media. Hula is no longer a bolt-on; it is the other half of the engine.

**The proposal:** Retire the separate Hula window and unify everything into a single format-in / format-out UI. The user picks an input format and an output format; the UI adapts to expose only the controls relevant to that combination (video standard, P/I options, field order, clip name, etc.). No more "is this a MacHuna job or a Hula job?" question.

**Why not do it now:** Six Hula output paths remain UNCONFIRMED on hardware (see Hula Hardware Unknowns table). A unified UI implies that all format combinations are equally reliable. Merging before those paths are confirmed would embed untested code deeper into the main product. The three pending Kahuna tests (below) validate the TO-SWS direction but do not touch the FROM-SWS (Hula) paths at all.

**What is needed before merging:**

1. Kahuna hardware test (imminent — highest priority):
   - 1080i/50 MOV → 1080p/50 SWS plays at correct speed (main v1.5.31 fix)
   - 1080p/50 → 1080i/50 SWS regression check
   - TGA i→i with "TGA source already interlaced" checkbox — correct speed on hardware
   - These confirm the MacHuna conversion engine (TO SWS direction) but do NOT clear the Hula (FROM SWS) unknowns.

2. Kayenne hardware tests (no timeline):
   - SWS → Kayenne MOV — load on a live Kayenne ClipStore / Image Store
   - SWS → Kayenne TGA — verify frame naming and format on hardware

3. Sony MVS hardware tests (no timeline):
   - SWS → Sony TGA — verify 4-char clip naming convention on a live desk
   - Sony MVS 25i field order — BFF assumed; confirm or flip on hardware

4. MOV → TGA via Hula — full path coded, never hardware-tested (not desk-specific; can be tested independently)

Once all FROM-SWS paths are confirmed, the unification can proceed cleanly.

**Near-term stepping stone (optional):** If the Hula/MacHuna split feels awkward before the full rearchitect is ready, a lower-risk improvement would be replacing the separate Hula Toplevel window with two tabs in the main window — "To SWS" and "From SWS" — without touching the underlying conversion logic.

---

### Hula Code Review and Bugfixes (v1.5.31)

A full analysis of Hula's conversion paths for interlaced and progressive sources was conducted. Two bugs were found and fixed:

1. **Interlaced SWS → interlaced TGA target was incorrectly rejected.** The batch runner sent all interlaced-standard selections to `_hula_convert_tga_interlaced`, which guards `fps < 48.0`. An interlaced SWS (25fps) was rejected. Fix: batch runner reads source header fps first. Progressive sources (fps ≥ 48) go to `_hula_convert_tga_interlaced` for field-weaving as before. Interlaced sources go to `_hula_convert_tga` (straight frame dump — frames already woven) with a log message advising the "TGA source already interlaced" checkbox for round-trips.

2. **Hula MOV encoder could not be cancelled.** `_hula_convert_mov` used `subprocess.run` directly, bypassing `_run_ffmpeg`. Stop/Cancel had no effect during long encodes. Fixed to use `_run_ffmpeg(cmd, check=True)`.

### Hula Hardware Unknowns (as of v1.5.31)

A full audit of the extraction output paths identified several items that are coded but unconfirmed on real hardware. These are all documented in full in DEVELOPMENT_NOTES.md under "Extraction output hardware unknowns". Summary:

- **Kayenne MOV and TGA outputs** — logic is correct by analysis, never loaded on a live Kayenne ClipStore/Image Store
- **Sony MVS clip naming** — naming convention assumed, not verified by live desk import
- **Interlaced SWS → MOV: interlace metadata** — ProRes container has no field-order flags; unknown whether a Kayenne desk cares. Potential fix: add `-field_order tb/bb` to ffmpeg encode.
- **Sony MVS 25i field order** — BFF assumed; toggle present if wrong
- **MOV → TGA** — full path coded and routes correctly, never hardware-tested

These are the main items to address in the next hardware test session. No code changes needed until hardware feedback is available.

---



### Development Workflow (updated)
David now uses Claude Code CLI directly. Claude has full file system access and can read, edit, and commit files without patch scripts. The old patch script workaround is no longer needed. Test command remains `python3.12 ~/Developer/MacHuna/machuna.py --gui`.

### Code Review Fixes (v1.5.10-v1.5.15, May 2026)
A comprehensive code review was conducted at the start of this session. Six bugs were found and fixed:

1. **Format variant (0x18C) wrong for 7 of 9 standards - fixed in v1.5.10.** The v1.5.8 reverse engineering confirmed the correct per-standard values but the code was never updated - it still used the v1.5.5 simple interlaced/progressive logic. A `FORMAT_VARIANTS` dict now maps each standard to its confirmed value. A `FORMAT_VARIANT_FPS` reverse lookup was also added (used by fixes 3 and 4 below).

2. **Ignore alpha not respected for TGA sequences - fixed in v1.5.11.** `convert_tga_sequence` was always generating a white key plane when `ignore_alpha=True` instead of omitting the key plane entirely. Also fixed the missing `has_key` argument in its `build_sws_header` call.

3. **Stop/Cancel could not kill ffmpeg during audio extraction or TGA sequence conversion - fixed in v1.5.12.** Several ffmpeg calls were using `subprocess.run` directly instead of the `_run_ffmpeg` wrapper, making them invisible to `_kill_current_ffmpeg()`. All ffmpeg calls now go through the wrapper.

4. **SWSPlayer and Hula reported wrong fps for most standards - fixed in v1.5.13.** Both header parsers were looking up fps from the standard code (0x188), but eight standards share code 0x4923 so the lookup was ambiguous. Both now read the format variant (0x18C) first and use `FORMAT_VARIANT_FPS` for an unambiguous lookup, with the old standard code lookup retained as fallback for third-party files.

5. **SWSPlayer played interlaced files at double speed - fixed in v1.5.14.** `FORMAT_VARIANT_FPS` was returning the field rate (50/59.94/60) for interlaced standards instead of the frame rate (25/29.97/30). Each SWS frame is a full frame, not a field. Confirmed on hardware with a 1080i/50 wipe.

6. **SWSPlayer playback jitter - fixed in v1.5.15.** The playback loop was sleeping relative to each frame's start time, so sleep overshoot accumulated as drift. The loop now sleeps to an absolute target time derived from a fixed origin, so any overshoot self-corrects on the next frame.

7. **Batch Convert TGA ambiguity - fixed in v1.5.16.** TGA files removed from the Batch Convert file picker entirely. Batch Convert now accepts MOV, MP4, MXF, MKV, AVI, PNG, BMP, and JPG only. TGA sequences are handled via the smart folder browser.

**Remaining items from the review (no action needed):**
- Video Player memory usage - frames cached in memory, fine for short clips but a known limitation for longer material. Document rather than fix.
- Single-file architecture - machuna.py contains conversion engine, header builder, GUI, Video Player, extraction engine, audio, settings, CLI. Suggested future modularisation: sws.py, player.py, extraction.py, audio.py, gui.py. Not urgent.

**Positive findings:** Header builder, split-file streaming, audio channel mapping and pan filter all specifically praised.

### Auto Play / Loop Flags
Tested on real Kahuna hardware - Auto Play and Auto Play & Loop flags do not trigger expected behaviour. Crucially, the same files converted by K-Watch also fail to trigger the behaviour. Conclusion: MacHuna is correctly matching K-Watch output. The operational purpose of these flags is unclear - may require GPI trigger, specific store configuration, or particular firmware. Parked pending further investigation.

### Video Standard Codes - Full Verification (v1.5.8/v1.5.9, May 2026)
This was a major reverse engineering session. All nine supported video standards were verified by running K-Watch on Parallels and hex-dumping the output headers. Key findings:

- Both 0x188 (standard code) AND 0x18C (format variant) must be set correctly - we previously only knew 0x188
- 0x18C is NOT a simple interlaced/progressive flag - it is an index into the Kahuna's internal standard table
- All interlaced standards use standard code 0xc923 -- the 0x8000 bit flags interlaced scanning (not drop-frame). Confirmed by P→I transcode analysis (2026-05-09)
- Full confirmed table in DEVELOPMENT_NOTES.md

**How to verify a new standard:** Convert any file in K-Watch with the target standard. Run `xxd -l 512 output.SWS` and read 0x188 (4 bytes) and 0x18C (4 bytes).

**K-Watch behaviour notes:**
- K-Watch can transcode from any source standard to any output standard
- K-Watch requires a full restart when changing output standards - otherwise conversions fail or error
- K-Watch is unreliable with still images (TGA stills often fail to convert)
- K-Watch on Parallels on M1 takes several minutes per 60-frame clip

**Unverified standards removed from dropdown (v1.5.9):** 1080p/29.97, 1080p/30, 2160p variants. These need K-Watch reference files before being added back.

**Progressive-to-interlaced warning (v1.5.8):** MacHuna detects source scan type via ffprobe `field_order` and logs a warning if a progressive source is converted to an interlaced standard. The file loads on the Kahuna but plays at double speed. Genuine interlaced output is the next major feature - see Roadmap.
**Critical discovery confirmed by hex analysis of K-Watch reference files:**

- Offset 0x18C (format variant field) was previously hardcoded to 0x18 in MacHuna
- K-Watch writes 0x08 for 1080i50 and 0x18 for 1080p50
- 0x08 = interlaced, 0x18 = progressive
- MacHuna was writing 0x18 for all standards, causing the Kahuna to display interlaced files as "1080p/50 A" rather than "1080i/50"
- Fixed in v1.5.5: `_interlaced_standards = {'1080i50', '1080i5994', '1080i60'}`, fmt_variant = 0x08 if interlaced else 0x18
- **Only 1080i50 and 1080p50 have been confirmed against K-Watch reference files. All other standards are assumed to follow the same pattern but are unverified on hardware.**

### Format Standards - General
- Only 1080p50 has been properly tested in production
- Other standards (1080i50, 1080p25) are untested on hardware
- 720p/50 and 720p/59.94 were withdrawn in v1.6.8 (export never hardware-verified + plane_size wrong for 1280-wide). 720p/59.94 has genuine broadcast demand (ABC/Fox) and is a reinstatement candidate — see DEVELOPMENT_NOTES Format Support Rationale
- Format fusion on the Kahuna means a mismatched file will often still work
- Full hardware test of all standards would require cooperation from truck owners - significant effort for little operational benefit given David's workflow is almost entirely 1080p50
- Recommendation: mark untested standards clearly in DEVELOPMENT_NOTES (done) rather than removing them

### Stop Button / Cancel Batch (v1.5.7)
- **Cancel Batch button** added to main button row - enables when Open Files batch starts, kills current ffmpeg and stops after current file
- **Stop button** calls `_kill_current_ffmpeg()` to kill the active ffmpeg process immediately
- Kill is immediate for long MOV conversions; for rapid TGA floods already-queued files may still convert - acceptable limitation
- A global `_current_ffmpeg_proc` and `_ffmpeg_proc_lock` track the active subprocess via `_run_ffmpeg()` wrapper
- Killing ffmpeg raises `subprocess.CalledProcessError` with SIGKILL (-9) - caught and logged. Correct behaviour, not a bug.
- Conversion log is not written if batch is cancelled

### File Delivery Method
Claude Code CLI has direct file system access and edits machuna.py directly using the Edit tool. No patch scripts needed. Always test with `python3.12 ~/Developer/MacHuna/machuna.py --gui` before building.

---

## What These Projects Are

**MacHuna** (`DNSVision/MacHuna`) is a macOS application that converts video and still image files to the Grass Valley Kahuna `.SWS` native format. It is a Mac-native alternative to the Windows-only K-Watch application. Built by David Steer (DNS Vision Limited) and Claude (Anthropic) using AI-assisted development with no prior coding background on David's part.

MacHuna also extracts `.SWS` files back to standard media formats for K-Frame and Sony MVS desks (SWS → K-Frame TGA, Sony TGA, and QuickTime MOV). This extraction engine was originally built as a standalone app (`DNSVision/Hula`), integrated into MacHuna v1.5.0, and unified into the main Convert interface in v1.5.33. The standalone repo is **archived and no longer maintained**.

MacHuna repo is currently **private**.

---

## Current Versions

- **MacHuna (engine):** v1.16.0 (2026-10-18, Ignore key for MOV (no alpha), bitexact TGA from a clip, reinstall advice when FFmpeg is missing, Windows-reserved MOV names refused; Mac parity kit 44/44; MacHuna 2.5.5 to pin it). v1.15.4 (2026-10-15, stdin=DEVNULL on every child process: on a Mac ffmpeg could eat request bytes and a "q" cut a job short with success; on Windows it hung; MacHuna 2.5.4 pins it, live 2026-10-16, with the same fix in bridge.py). v1.15.3 (2026-10-15, text UTF-8 everywhere for Windows: ffprobe report, logs, settings; guard; Mac unchanged; MacHuna-PC to pin it, MacHuna 2.5.3 stays on v1.15.0). v1.15.2 (2026-10-15, tests only: the SWS header time is frozen in the symlink-fallback tests; code identical to v1.15.1; MacHuna-PC pins it). v1.15.1 (2026-10-15, TGA sequences convert on Windows: a refused symlink falls back to a hard link, then a copy; Mac unchanged, so MacHuna 2.5.3 stays on v1.15.0 until its next release). v1.15.0 (2026-10-12, clear frames; split SWS as a source; EIF 517-frame limit refused in words; MacHuna 2.5.0 pins it). v1.14.0 (2026-10-12, `write_sound_wav`: a clip's whole sound as a WAV; MacHuna 2.4.0 pins it). v1.13.1 (2026-10-12, split SWS files as K-Watch writes them, confirmed on a Kahuna; reconvert keyed splits made earlier; colour-label log line; MacHuna 2.3.0 pins it). v1.13.0 (2026-10-11, sound for any clip: `sound_file=` on every SWS/EIF/MOV route, and an SWS keeps its sound's own length as Kahuna Manager does; MacHuna 2.3.0 pins it). v1.12.5 (2026-10-10, portable app layer for a PC fork; MacHuna 2.2.1 stays on v1.12.4, which it needs nothing from v1.12.5 to change). v1.12.4 (2026-10-09, SWS audio fixed and confirmed by ear on a Kahuna). Before that, v1.12.3 (2026-10-08, key precision fix from the real-material regression run): v1.12.1, the engine-soundness release (matrix, three reviews, black-box pass, decisions A-M). MacHuna 2.0 still pins v1.11.0 until its engine move.
- **Hula (standalone, archived):** v0.1.1 — no longer maintained, use MacHuna's extraction outputs

---

## Local File Locations

| File/Folder | Location |
|---|---|
| MacHuna source | `~/Developer/MacHuna/machuna.py` |
| MacHuna built app | `~/Developer/MacHuna/dist/MacHuna.app` |
| MacHuna repo | `https://github.com/DNSVision/MacHuna` |
| Settings | `~/.kwatch_settings.json` |
| PDF generation template | `~/Developer/MacHuna/manual_template.html` |

---

## Development Environment

- **Machine:** MacBook Air M5 (Apple Silicon) - all development and building happens here
- **Python:** 3.12 (`/opt/homebrew/bin/python3.12`)
- **ffmpeg:** Homebrew; resolved from PATH via `shutil.which` (version not pinned)
- **PyInstaller:** pip3.12
- **Key libraries:** Pillow, numpy, tkinter, sounddevice, tkinterdnd2-universal

---

## Build Commands

### MacHuna

```bash
python3.12 -m PyInstaller MacHuna.spec -y
```

### User Manual PDF

```bash
pandoc ~/Developer/MacHuna/USER_MANUAL.md \
  -o ~/Desktop/MacHuna_User_Manual.html \
  --template=/Users/davidsteer/Developer/MacHuna/manual_template.html
```

Then open in Safari and File > Print > Save as PDF.

---

## GitHub Push Workflow

```bash
cd ~/Developer/MacHuna
git add .
git commit -m "Description"
git push
```

---

## MacHuna Repo Contents

```
~/Developer/MacHuna/
├── machuna.py              # Main source (~2,700 lines)
├── machuna.icns            # App icon
├── machuna_final_1024.png  # Icon source image
├── Audio Spec.pdf          # Historical reference - superseded, see DEVELOPMENT_NOTES
├── README.md               # Public overview
├── USER_MANUAL.md          # User manual (renders in GitHub)
├── manual_template.html    # Pandoc template for PDF generation
├── DEVELOPMENT_NOTES.md    # Engineering continuity document
├── CHANGELOG.md            # Version history
└── .gitignore
```

---

## MacHuna Feature Summary

- Batch Convert - smart folder browser for MOVs, TGA sequences, and stills
- Cancel Batch button - kills current ffmpeg and stops batch after current file
- Stop button - kills current ffmpeg immediately
- Video standards: seven offered (all confirmed by K-Watch hex analysis) -- 1080i/50, 1080i/59.94, 1080i/60, 1080p/25, 1080p/50, 1080p/59.94, 1080p/60. (720p/50 and 720p/59.94 header bytes were also confirmed but their SWS output was withdrawn in v1.6.8 — never hardware-verified, plane_size wrong for 1280-wide.)
- Progressive-to-interlaced mismatch warning logged automatically
- Input formats: MOV, MP4, MXF, MKV, AVI, TGA sequences, PNG, BMP, JPG
- Fill and key planes encoded as v210 big-endian
- Ignore alpha/key option
- Audio: K-Watch layout, 32 bytes a sample in eight 4-byte slots, each [lead byte][16-bit sample, big-endian][0]; left in slot 1, right in slot 2, slots 3-8 silent; total sample count at 0x1C0 (uint32) (v1.12.4; the old 16ch LE L=Ch1/R=Ch3 layout was wrong - see DEVELOPMENT_NOTES 'Audio Format')
- Auto play / Loop play flags
- Large file support: >4GB split into 2GB FAT32-safe chunks
- Built-in Video Player (fill, key, composite, audio meters) -- supports SWS, TGA sequences, MOV/MP4/MXF/AVI, and K-Frame EIF
- Built-in extraction engine (SWS/EIF → K-Frame TGA, Sony TGA, QuickTime MOV)
- **K-Frame EIF read** -- Video Player opens .eif files with fill, key, and composite panels; frame rate auto-detected from header
- **K-Frame EIF write** (UNCONFIRMED on hardware) -- converts MOV, TGA sequences, and SWS to .eif with slot-numbered output (0001.eif, 0002.eif...)
- **K-Frame EIF conversion** (UNCONFIRMED on hardware) -- EIF → Kahuna SWS (lossless YCbCr repack), EIF → K-Frame TGA, EIF → Sony TGA
- Window size persisted between sessions
- Settings saved to `~/.kwatch_settings.json`

---

## Extraction Output Summary

- Converts .SWS to three output targets:
  - QuickTime MOV: ProRes 4444 with embedded alpha, BT.709, audio muxed if present (from the SWS, or an EIF's companion .eaf). Not a desk format - nothing to confirm
  - K-Frame TGA: 32-bit RGBA, frames 0001.tga onwards, subfolder per SWS
  - Sony TGA: 32-bit RGBA, frames XXXX0000.tga (4-char clip name prefix), subfolder named after clip
- Progressive or interlaced output via Standard dropdown (TGA targets)
- Field order toggle (BFF/TFF) for interlaced standards; always shown for Sony TGA
- Batch conversion supported
- Per-file metadata shown at load time: standard, frame count, duration

---

## Code Structure in machuna.py

The file is a single script. Key sections in order:

1. Imports and constants (including `_current_ffmpeg_proc` and `_ffmpeg_proc_lock`)
2. `_run_ffmpeg()` - tracked ffmpeg subprocess wrapper
3. `_kill_current_ffmpeg()` - kills active ffmpeg process
4. SWS header builder and conversion functions
5. SWSPlayer classes (PlayerFrameCache, PlayerAudio, SWSPlayer)
6. Extraction engine — HulaSWSHeader, _hula_* converter functions
7. launch_gui() - main GUI

The v210 decoder functions (`_v210_plane_to_yuv`, `_yuv_to_rgb8`, `_yuv_to_gray8`) are shared between SWSPlayer and the extraction engine — do not duplicate.

---

## Known Issues

- PortAudio AUHAL errors in terminal when running as script on macOS 26 beta - harmless, invisible in built .app
- macOS 26 beta / Homebrew PortAudio instability - not worth investigating until macOS 26 goes final
- Auto Play / Loop flags - do not trigger on hardware, but K-Watch files also fail - not a MacHuna bug
- Ignore Alpha / TGA sequences - fixed in v1.5.11. Now correctly omits key plane when Ignore Alpha is ticked.
- Stop during rapid TGA flood - kills current ffmpeg but already-queued files may still convert. Acceptable limitation.

---

## Roadmap

The canonical roadmap is in `DEVELOPMENT_NOTES.md` under "Roadmap (canonical - the one list to work from)". Do not keep a separate copy here - read it there and reconcile against the code.

Everything that used to live in this section is folded into that list, including the two items that were only recorded here: the **Windows port** (community contribution once repos go public - the core Python has no Mac-specific dependencies beyond ffmpeg path handling and the macOS menu code) and **going public** (do the live K-Frame/Sony hardware tests first, then make the repo public).

---

## Swift Rewrite - STARTED 2026-09-24, and it is NOT what this section used to say

**This repo is PARKED at v1.11.0** (tag `v1.11.0`). The Swift work lives in
**`DNSVision/MacHuna-Swift`**, and its decision record is the authority:
`MacHuna-Swift/DESIGN_DECISIONS.md`. Read that before doing any Swift work.

**What changed, and why the old plan here was wrong.** This section used to
describe four Swift packages (FormatKit, TranscodeKit, PlayerKit, App) gated on
the roadmap being complete and hardware-tested. David brought the work forward
on 2026-09-24 because K-Frame access kept being cancelled, and the architecture
changed with it:

- **`machuna.py` is FROZEN at v1.11.0 and does all the conversion.** The Swift
  app is a new interface that drives it. Not a line of the Python changes.
- **There is no FormatKit.** The format code is not ported. Keeping one copy
  means every K-Frame desk finding is fixed once rather than twice, and the
  Python has to keep living anyway as the base for the PC fork.
- **The player comes across as a re-skin**, not a rewrite. Python decodes, Swift
  draws.
- **The full Swift rewrite of the pipeline is still planned**, but as a LATER
  phase, gated on finishing the K-Frame testing and getting this repo into a
  state that can be handed over for the PC fork.

**What is still true from the old plan:** ffmpeg stays, shelled out to as a
bundled binary; the `mac-arsed-mac-app` skill drives the UI work; the app will
need sandbox and security-scoped bookmarks.

**`design/` is superseded.** Its mockup and menu model are reference for how the
thinking started, not a spec. The current mockups are a canvas linked from
`DESIGN_DECISIONS.md`.

---

## Important Technical Notes

### SWS Format
- 512-byte big-endian header
- Fill plane: v210 big-endian
- Key plane: v210 big-endian (absent if play_count at 0x1A8 == 0)
- Audio: 16-bit LE PCM, 16ch, 48kHz (absent if aud_offset at 0x1E8 == 0)
- Audio detection: use aud_offset > 0 AND aud_fmt == 0x03000000. Do NOT use 0x1C2 - unreliable.
- Full header reference in DEVELOPMENT_NOTES.md

### Video Standard Codes - All Confirmed
Full table confirmed by K-Watch hex analysis (2026-05-09). Both fields required:

| Standard | 0x188 | 0x18C |
|---|---|---|
| 1080i/50 | `0xc923` | `0x08` |
| 1080i/59.94 | `0xc923` | `0x05` |
| 1080i/60 | `0xc923` | `0x04` |
| 1080p/25 | `0x4923` | `0x13` |
| 1080p/50 | `0x4923` | `0x18` |
| 1080p/59.94 | `0x4923` | `0x17` |
| 1080p/60 | `0x4923` | `0x16` |
| 720p/50 *(output withdrawn v1.6.8)* | `0x4923` | `0x10` |
| 720p/59.94 *(output withdrawn v1.6.8)* | `0x4923` | `0x0f` |

0x18C is a Kahuna internal standard index, not a flags field. Do not assume values for unverified standards.

### v210 Decode
- ffmpeg 7.x has a confirmed bug decoding v210 from raw files (returncode 69). Never use ffmpeg for v210 decode.
- Use the pure numpy decoder. The `.copy()` before `byteswap()` is critical - do not remove it.

### Audio
- ~~Channel mapping L=Ch1, R=Ch3 by hex analysis~~ WRONG: the analysis read K-Watch one byte out of step. Real layout (2026-10-09, by ear on a Kahuna): 32 bytes a sample in eight 4-byte slots, each [lead byte][16-bit sample, big-endian][0]; left in slot 1, right in slot 2, slots 3-8 silent; total sample count at 0x1C0 (uint32)
- Standard ffmpeg -ac 16 upmix is wrong - MacHuna uses an explicit pan filter

### PyInstaller
- Must use --onedir. --onefile + --windowed does not bundle ffmpeg correctly on macOS.
- ffmpeg path must point to real binary, not Homebrew symlink.

### ffmpeg Process Tracking
- `_run_ffmpeg()` wraps subprocess.Popen and registers the process in `_current_ffmpeg_proc`
- `_kill_current_ffmpeg()` kills the registered process if one exists
- Both Stop and Cancel Batch call `_kill_current_ffmpeg()`
- Killing ffmpeg mid-conversion raises CalledProcessError with SIGKILL (-9) - caught and logged

---

## Coding Preferences (David)

- British English spelling and grammar throughout
- No em dashes - use hyphens instead
- Plain-spoken tone when writing in David's voice
- Metric measurements unless otherwise requested
- No Chrome, no Google products
- Version bumps: patch version (x.x.X) for bugfixes, minor version (x.X.0) for new features
- Deliver code changes via Claude Code CLI (direct file edit), not patch scripts or file downloads

---

## Working on machuna.py

Claude Code reads and edits `machuna.py` directly - do not work from a cached copy. Read the current file (it changes frequently) and reconcile against the Session Anchor at the top of this document before editing. See "Staying current between sessions" in `CLAUDE.md`.

There is no standalone Hula repo to maintain - `DNSVision/Hula` is archived. All Hula development happens in `machuna.py`.
