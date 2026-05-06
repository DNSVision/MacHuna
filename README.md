# MacHuna

A macOS application for converting video and still image files to the Grass Valley Kahuna `.SWS` native format.

## Overview

MacHuna is a Mac-native alternative to the Windows-only K-Watch application included with Grass Valley K-Manager Pro. It monitors a watch folder for incoming media files and automatically converts them to `.SWS` format for use with Grass Valley Kahuna vision mixers.

Converted files are placed into a destination folder, ready to be loaded onto a Kahuna mainframe via USB or network transfer.

## Features

- Converts MOV, MP4, MXF, MKV, AVI and other ffmpeg-supported formats to `.SWS` (K-Watch supports MOV and AVI only)
- Converts TGA sequences to `.SWS` clips
- Converts still images (PNG, TGA, BMP, JPG etc.) to `.SWS` stills
- Fill and key (alpha) planes correctly encoded as v210 big-endian
- Ignore alpha/key option -- writes fill-only file with no key plane, matching K-Watch behaviour
- Audio support -- 16-bit PCM, 16 channels, correct K-Watch channel mapping (L=Ch1, R=Ch3)
- Include/exclude audio option
- Auto play and Loop play flags baked into the SWS header at conversion time
- Large file support -- files over 4GB are automatically split into 2GB FAT32-safe chunks, matching K-Watch split file format exactly
- Built-in SWS Preview Player -- opens any .SWS file in a quad display (fill, key, composite, audio meters) with transport controls, launched directly from the MacHuna window
- Batch convert with file picker and auto-incrementing file numbers
- Supports 1080i50, 1080i29.97, 1080p25, 1080p50, 720p50, 720p59.94 and more
- Watch folder service runs in background
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
- Pillow, numpy, watchdog (`pip3.12 install pillow numpy watchdog`)

Always run the build command from the project directory:

```bash
cd ~/Developer/MacHuna && python3.12 -m PyInstaller \
  --onedir \
  --windowed \
  --name "MacHuna" \
  --icon machuna.icns \
  --add-binary "/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffmpeg:." \
  --add-binary "/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffprobe:." \
  --add-data "/path/to/machuna_final_1024.png:." \
  --noconfirm \
  machuna.py
```

The built app will appear in the `dist/` folder.

## Usage

### Watch Folder

1. Launch MacHuna.app
2. Set your Watch Folder -- drop source files here
3. Set your Destination Folder -- converted .SWS files appear here
4. Select your video standard
5. Set playback options (Auto play, Loop play) as required
6. Click Start Watching

MacHuna will convert files automatically as they appear and log progress in the app window.

### Batch Convert

1. Set your Destination Folder
2. Set your start number in the Batch Convert section
3. Click Open Files and select MOV, MP4 or still image files
4. Files are converted in alphabetical order with auto-incrementing numbers
5. A conversion log is written to the destination folder after each batch

For TGA sequences, use the Watch Folder service -- batch convert does not support sequences.

### Large Files (>4GB)

Files larger than 4GB are automatically split into 2GB chunks inside a folder named `<number>.SWS`, matching the K-Watch split file format exactly. The Split >4GB option in Settings must be enabled (it is on by default).

## SWS Format

The Kahuna `.SWS` format consists of a 512-byte header followed by v210 big-endian fill and key video planes, with optional 16-channel PCM audio appended. MacHuna reverse-engineered this format from real K-Watch output and has been verified against a live Grass Valley Kahuna mainframe.

## Roadmap

- HLG Rec.2020 colour space option (requires a real HLG SWS file to verify)
- Split file support in SWS Preview Player

## Related Projects

- **SWS to MOV converter** -- planned as a separate app for reverse conversion of .SWS files back to MOV

## Licence

MIT License -- see LICENSE file for details.

## Authors

David Steer / DNS Vision Limited & Claude (Anthropic)
