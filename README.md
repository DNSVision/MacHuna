# MacHuna

A macOS application for converting video and still image files to the Grass Valley Kahuna `.SWS` native format.

## Overview

MacHuna is a watch folder-based converter that monitors a folder for incoming media files and automatically converts them to `.SWS` format for use with Grass Valley Kahuna vision mixers. It is a Mac-native replacement for the Windows-only K-Watch application included with Grass Valley K-Manager Pro.

Converted files are placed into a destination folder, ready to be loaded onto a Kahuna mainframe via USB or network transfer.

## Features

- Converts MOV, MP4 and other common video formats to `.SWS`
- Converts TGA sequences to `.SWS` clips
- Converts still images (PNG, TGA, BMP etc.) to `.SWS` stills
- Fill and key (alpha) planes correctly encoded as v210 big-endian
- Supports 1080i25, 1080i29.97, 1080p25, 1080p50, 1080p59.94, 720p50, 720p59.94
- Automatic FAT32 split for files over 4GB
- Watch folder service runs in background
- Settings remembered between sessions
- Fully self-contained .app bundle -- no separate ffmpeg installation required

## Requirements

- macOS 12 or later (Apple Silicon or Intel)
- ffmpeg (bundled in the .app -- no separate installation needed when running the app)

## Building from Source

Requirements:
- Python 3.12
- ffmpeg installed via Homebrew (`brew install ffmpeg`)
- PyInstaller (`pip3.12 install pyinstaller`)
- Pillow, numpy (`pip3.12 install pillow numpy`)

Build command:

```bash
python3.12 -m PyInstaller \
  --onedir \
  --windowed \
  --name "MacHuna" \
  --icon machuna.icns \
  --add-binary "/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffmpeg:." \
  --add-binary "/opt/homebrew/Cellar/ffmpeg/7.1.1_3/bin/ffprobe:." \
  --noconfirm \
  machuna.py
```

The built app will appear in the `dist/` folder.

## Usage

1. Launch MacHuna.app
2. Set your Watch Folder -- drop source files here
3. Set your Destination Folder -- converted .SWS files appear here
4. Select your video standard
5. Click Start Watching
6. Drop MOV, TGA sequences or still images into the Watch Folder

MacHuna will convert files automatically and log progress in the app window.

## SWS Format

The Kahuna `.SWS` format consists of a 512-byte header followed by v210 big-endian fill and key video planes. MacHuna reverse-engineered this format from real K-Watch output and has been verified against a live Kahuna mainframe.

## Roadmap

- Audio support (spec documented in `Audio Spec.pdf`)
- SWS to MOV conversion
- Ignore alpha/key option
- Drag and drop into watch window
- Preview viewer (fill, key and audio)
- HLG Rec.2020 colour space option

## Licence

MIT License -- see LICENSE file for details.

## Author

David Steer / DNS Vision Limited
