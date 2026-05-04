#!/usr/bin/env python3
"""
MacHuna for macOS
Converts TGA stills, TGA sequences, and MOV/MP4 files to Grass Valley Kahuna .SWS format.
Replicates the core functionality of K-Watch (K-Manager Pro) without requiring Windows/Parallels.

Requirements:
    pip3 install watchdog
    brew install ffmpeg   (or: https://ffmpeg.org/download.html)

Usage:
    python3 kwatch_converter.py --watch /path/to/watch --dest /path/to/destination
    python3 kwatch_converter.py --gui   (launches simple GUI)
    python3 kwatch_converter.py --convert /path/to/file.mov --number 42 --dest /path/to/destination
"""

import argparse
import os
import re
import struct
import subprocess
import sys
import tempfile
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = False  # Disabled -- tkdnd native library incompatible with Homebrew Python/Tk on Apple Silicon
except (ImportError, Exception):
    HAS_DND = False

# ─────────────────────────────────────────────────────────────
#  SWS format constants (reverse-engineered from binary analysis)
# ─────────────────────────────────────────────────────────────

SWS_MAGIC       = b'S&W Kahuna Still'   # confirmed - used for both stills AND clips
SWS_VERSION     = b'9.6 Release 1'
SWS_COPYRIGHT   = b'Copyright (c) : Grass Valley 2021'
SWS_HEADER_SIZE = 512

# Video standard codes (offset 0x188 in header)
# Both 1080i50 and 1080p50 confirmed as 0x4923
# FPS field at 0x18C is always 0x18 (24) regardless of actual frame rate
VIDEO_STANDARDS = {
    '1080i50':   0x4923,   # confirmed
    '1080i5994': 0x4923,   # estimated
    '1080i60':   0x4923,   # estimated
    '1080p25':   0x4923,   # estimated
    '1080p50':   0x4923,   # confirmed
    '1080p2997': 0x4923,   # estimated
    '1080p30':   0x4923,   # estimated
    '1080p5994': 0x4923,   # estimated
    '1080p60':   0x4923,   # estimated
    '720p50':    0x4813,   # estimated
    '720p5994':  0x4814,   # estimated
    '2160p25':   0x5923,   # estimated
    '2160p50':   0x5923,   # estimated
    '2160p2997': 0x5923,   # estimated
}

FAT32_LIMIT = 4 * 1024 * 1024 * 1024  # 4 GB


# ─────────────────────────────────────────────────────────────
#  Header builder
# ─────────────────────────────────────────────────────────────

def build_sws_header(source_filename: str,
                     clip_name: str,
                     width: int,
                     height: int,
                     frame_count: int,
                     plane_size: int,
                     video_standard: str = '1080p50',
                     play_rate: float = 1.0,
                     is_still: bool = True,
                     fps: float = 25.0,
                     has_audio: bool = False) -> bytes:
    """Build a 512-byte SWS file header."""

    std_code = VIDEO_STANDARDS.get(video_standard, 0x4923)
    now_str  = datetime.now().strftime('%a %b %d %H:%M:%S %Y').encode('ascii')

    # Audio parameters (confirmed from K-Watch reference file analysis)
    # audio_frame_size = 0x1680 (5760) -- fixed value in header regardless of fps
    # Actual bytes per frame = round(48000/fps) * 2 bytes * 16 channels
    AUDIO_FRAME_SIZE_HDR = 0x1680  # always 5760 in header (confirmed)
    samples_per_frame    = round(48000 / fps)
    audio_bytes_per_frame = samples_per_frame * 2 * 16
    audio_data_size      = audio_bytes_per_frame * frame_count if has_audio else 0
    audio_offset         = SWS_HEADER_SIZE + plane_size * 2 * frame_count  # after fill+key
    total_size           = audio_offset + audio_data_size

    hdr = bytearray(SWS_HEADER_SIZE)

    # 0x000  Magic string (16 bytes) — always 'S&W Kahuna Still' even for clips
    hdr[0x00:0x10] = SWS_MAGIC

    # 0x020  Source filename (64 bytes, null-padded)
    src = source_filename.encode('ascii', 'replace')[:63]
    hdr[0x20:0x20 + len(src)] = src

    # 0x0EB  Version string (with leading null byte as seen in originals)
    hdr[0xEB] = 0x00
    ver = SWS_VERSION
    hdr[0xEC:0xEC + len(ver)] = ver

    # 0x0FB  Clip name = source filename stem
    cname = clip_name.encode('ascii', 'replace')[:11]
    hdr[0xFB:0xFB + len(cname)] = cname

    # 0x108  Copyright string
    hdr[0x108:0x108 + len(SWS_COPYRIGHT)] = SWS_COPYRIGHT

    # 0x148  Creation timestamp (32 bytes)
    ts = now_str[:31]
    hdr[0x148:0x148 + len(ts)] = ts

    # 0x168  Modification timestamp (32 bytes)
    hdr[0x168:0x168 + len(ts)] = ts

    # 0x188  Video standard code (uint32 big-endian)
    struct.pack_into('>I', hdr, 0x188, std_code)

    # 0x18C  Format variant field — always 0x18 (24) regardless of fps
    struct.pack_into('>I', hdr, 0x18C, 0x18)

    # 0x190  Width (uint32 BE)
    struct.pack_into('>I', hdr, 0x190, width)

    # 0x194  Height fill (uint32 BE)
    struct.pack_into('>I', hdr, 0x194, height)

    # 0x198  Height key (uint32 BE)
    struct.pack_into('>I', hdr, 0x198, height)

    # 0x19C  Header size (uint32 BE) = 512
    struct.pack_into('>I', hdr, 0x19C, SWS_HEADER_SIZE)

    # 0x1A0  Fill plane size = one frame's worth of v210 data
    struct.pack_into('>I', hdr, 0x1A0, plane_size)

    # 0x1A4  Frame count (uint32 BE)
    struct.pack_into('>I', hdr, 0x1A4, frame_count)

    # 0x1A8  Play count = frame count (confirmed from clip analysis)
    struct.pack_into('>I', hdr, 0x1A8, frame_count)

    # 0x1B0  Play rate (float32 BE) = 1.0
    struct.pack_into('>f', hdr, 0x1B0, play_rate)

    # 0x1B4  (plane_size * frame_count + header_size) / 32
    val_1b4 = (plane_size * frame_count + SWS_HEADER_SIZE) // 32
    struct.pack_into('>I', hdr, 0x1B4, val_1b4)

    # 0x1C2  Audio frame size (uint16 BE) -- 0x1680 (5760) if audio, 0 if not
    struct.pack_into('>H', hdr, 0x1C2, AUDIO_FRAME_SIZE_HDR if has_audio else 0)

    # 0x1CC  Total file size = header + (fill+key) planes + audio data
    struct.pack_into('>I', hdr, 0x1CC, total_size)

    # 0x1E8  Audio data offset / 32 (0 if no audio)
    struct.pack_into('>I', hdr, 0x1E8, (audio_offset // 32) if has_audio else 0)

    # 0x1EC  Audio format flag: 0x03000000 (0 if no audio)
    struct.pack_into('>I', hdr, 0x1EC, 0x03000000 if has_audio else 0)

    return bytes(hdr)


# ─────────────────────────────────────────────────────────────
#  FFmpeg helpers
# ─────────────────────────────────────────────────────────────

def _get_ffmpeg_path(binary: str = 'ffmpeg') -> str:
    """Return the path to ffmpeg/ffprobe.
    
    When running as a PyInstaller .app bundle, look inside the bundle first.
    Falls back to the system PATH (Homebrew etc.) when running as a script.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller extracts binaries to sys._MEIPASS at runtime
        bundled = os.path.join(sys._MEIPASS, binary)
        if os.path.exists(bundled):
            return bundled
    return binary


def check_ffmpeg():
    """Raise if ffmpeg is not found."""
    try:
        subprocess.run([_get_ffmpeg_path('ffmpeg'), '-version'], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        raise RuntimeError(
            "ffmpeg not found. Install with: brew install ffmpeg\n"
            "Or download from https://ffmpeg.org/download.html"
        )


def get_video_info(input_path: str) -> dict:
    """Return dict with width, height, fps, frame_count, has_alpha."""
    cmd = [
        _get_ffmpeg_path('ffprobe'), '-v', 'quiet', '-print_format', 'json',
        '-show_streams', '-show_format', input_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    import json
    data = json.loads(result.stdout)

    info = {'width': 0, 'height': 0, 'fps': 25.0, 'frame_count': 1, 'has_alpha': False, 'has_audio': False}

    for stream in data.get('streams', []):
        if stream.get('codec_type') == 'video':
            info['width'] = stream.get('width', 0)
            info['height'] = stream.get('height', 0)

            # Frame rate
            fps_str = stream.get('r_frame_rate', '25/1')
            try:
                num, den = fps_str.split('/')
                info['fps'] = float(num) / float(den)
            except Exception:
                info['fps'] = 25.0

            # Frame count
            nb = stream.get('nb_frames')
            if nb:
                info['frame_count'] = int(nb)
            else:
                dur = float(data.get('format', {}).get('duration', 0))
                info['frame_count'] = max(1, int(dur * info['fps']))

            # Alpha detection
            pix_fmt = stream.get('pix_fmt', '')
            info['has_alpha'] = 'a' in pix_fmt or pix_fmt in (
                'rgba', 'bgra', 'yuva420p', 'yuva422p', 'yuva444p'
            )
            # TGA files always have alpha in our use case
            if input_path.lower().endswith('.tga'):
                info['has_alpha'] = True

        elif stream.get('codec_type') == 'audio':
            info['has_audio'] = True

    return info


def convert_to_v210(input_path: str, output_path: str,
                    extract_alpha: bool = False,
                    width: int = 0, height: int = 0):
    """Convert input to raw v210 using ffmpeg, then byte-swap to big-endian.
    
    ffmpeg outputs v210 as little-endian 32-bit words.
    Kahuna expects big-endian 32-bit words.
    We swap each 4-byte word after conversion.
    """
    vf_fill = 'null'
    vf_key  = 'alphaextract,format=gray'

    ffmpeg = _get_ffmpeg_path('ffmpeg')
    cmd_fill = [ffmpeg, '-y', '-i', input_path]
    if width and height:
        cmd_fill += ['-vf', f'scale={width}:{height},{vf_fill}']
    cmd_fill += ['-colorspace', 'bt709', '-color_range', 'tv', '-f', 'rawvideo', '-vcodec', 'v210', output_path]

    subprocess.run(cmd_fill, capture_output=True, check=True)
    _byteswap_v210(output_path)

    if extract_alpha:
        alpha_path = output_path + '.alpha.raw'
        # Extract alpha, convert to clean limited-range luma (64=black, 940=white)
        # Use scale2ref to map 0-255 alpha to 64-940 luma range
        cmd_key = [ffmpeg, '-y', '-i', input_path,
                   '-vf', 'alphaextract,format=yuv420p,colorspace=bt709,'
                          'scale=out_range=tv',
                   '-f', 'rawvideo', '-vcodec', 'v210', alpha_path]
        result = subprocess.run(cmd_key, capture_output=True)
        if result.returncode != 0 or not os.path.exists(alpha_path) or os.path.getsize(alpha_path) == 0:
            # Simpler fallback
            cmd_key = [ffmpeg, '-y', '-i', input_path,
                       '-vf', 'alphaextract',
                       '-f', 'rawvideo', '-vcodec', 'v210', alpha_path]
            subprocess.run(cmd_key, capture_output=True, check=True)
        _byteswap_v210(alpha_path)
        return alpha_path
    return None


def _byteswap_v210(path: str):
    """Swap bytes within each 32-bit word in a raw v210 file (LE -> BE)."""
    import numpy as np
    data = np.fromfile(path, dtype='>u4')   # read as big-endian uint32
    data.byteswap(inplace=True)             # swap to little-endian
    data.tofile(path)                       # write back


def _generate_white_key(fill_raw: str, output_path: str):
    """Generate a solid white v210 key plane matching the size of the fill plane.
    
    White in v210 big-endian is the repeating 8-byte pattern:
    20 01 02 00 04 08 00 40  (confirmed from K-Watch reference file)
    """
    fill_size = os.path.getsize(fill_raw)
    pattern = bytes([0x20, 0x01, 0x02, 0x00, 0x04, 0x08, 0x00, 0x40])
    repeats = fill_size // len(pattern)
    with open(output_path, 'wb') as f:
        f.write(pattern * repeats)
        # Handle any remainder (shouldn't happen with valid v210 data)
        remainder = fill_size % len(pattern)
        if remainder:
            f.write(pattern[:remainder])


def extract_audio(input_path: str, output_path: str, frame_count: int, fps: float) -> bool:
    """Extract audio from input file and write as raw 16-bit LE PCM, 16 channels, 48kHz.

    Format confirmed by hex analysis of K-Watch reference SWS files:
    - 16-bit signed little-endian samples (matches common MOV source format)
    - 16 channels interleaved (source channels padded to 16 with silence)
    - 48,000 Hz sample rate
    - Samples per frame = 48000 / fps (e.g. 960 at 50fps, 1920 at 25fps)
    - Bytes per frame = samples_per_frame x 2 bytes x 16 channels
    - Padded with zero bytes to exact frame alignment if necessary

    Returns True if audio was extracted successfully, False if source has no audio.
    """
    ffmpeg = _get_ffmpeg_path('ffmpeg')

    # Extract as 16-bit LE, 16 channels, 48kHz raw PCM
    cmd = [ffmpeg, '-y', '-i', input_path,
           '-vn',
           '-acodec', 'pcm_s16le',
           '-ar', '48000',
           '-ac', '16',
           '-f', 's16le',
           output_path]
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return False

    # Verify and pad to exact frame alignment
    samples_per_frame = round(48000 / fps)
    bytes_per_frame   = samples_per_frame * 2 * 16  # 2 bytes/sample, 16 channels
    expected_size     = bytes_per_frame * frame_count
    actual_size       = os.path.getsize(output_path)

    if actual_size < expected_size:
        # Pad with silence to exact length
        with open(output_path, 'ab') as f:
            f.write(b'\x00' * (expected_size - actual_size))
    elif actual_size > expected_size:
        # Truncate to exact length
        with open(output_path, 'r+b') as f:
            f.truncate(expected_size)

    return True


# ─────────────────────────────────────────────────────────────
#  SWS writer
# ─────────────────────────────────────────────────────────────

def write_sws(dest_path: str,
              fill_raw: str,
              key_raw: Optional[str],
              header: bytes,
              split_fat32: bool = True,
              frame_count: int = 1,
              audio_raw: Optional[str] = None):
    """Write the final .SWS file (or split folder if > 4GB).
    
    Structure (confirmed from PC binary analysis):
      header
      fill_frame1, fill_frame2, ..., fill_frameN
      key_frame1,  key_frame2,  ..., key_frameN
      audio_data  (if present)
    """

    fill_size  = os.path.getsize(fill_raw)
    key_size   = os.path.getsize(key_raw) if key_raw else 0
    audio_size = os.path.getsize(audio_raw) if audio_raw else 0
    total      = SWS_HEADER_SIZE + fill_size + key_size + audio_size

    if split_fat32 and total > FAT32_LIMIT:
        _write_sws_split(dest_path, fill_raw, key_raw, header, frame_count)
    else:
        with open(dest_path, 'wb') as out:
            out.write(header)
            _copy_file(fill_raw, out)
            if key_raw:
                _copy_file(key_raw, out)
            if audio_raw:
                _copy_file(audio_raw, out)
        print(f"  Written: {dest_path}  ({total:,} bytes)")


def _copy_file(src: str, dest_fh):
    with open(src, 'rb') as f:
        while chunk := f.read(1024 * 1024):
            dest_fh.write(chunk)


def _write_sws_split(dest_folder: str, fill_raw: str, key_raw: Optional[str], header: bytes, frame_count: int = 1):
    """Split large SWS into FAT32-safe chunks inside a .SWS folder."""
    os.makedirs(dest_folder, exist_ok=True)

    CHUNK = FAT32_LIMIT - 1

    chunks = []

    def stream():
        yield header
        if key_raw and frame_count > 1:
            plane_size = os.path.getsize(fill_raw) // frame_count
            with open(fill_raw, 'rb') as ff, open(key_raw, 'rb') as kf:
                for _ in range(frame_count):
                    yield ff.read(plane_size)
                    yield kf.read(plane_size)
        else:
            with open(fill_raw, 'rb') as f:
                while data := f.read(1024 * 1024):
                    yield data
            if key_raw:
                with open(key_raw, 'rb') as f:
                    while data := f.read(1024 * 1024):
                        yield data

    buf = b''
    for piece in stream():
        buf += piece
        while len(buf) >= CHUNK:
            chunks.append(buf[:CHUNK])
            buf = buf[CHUNK:]
    if buf:
        chunks.append(buf)

    total = len(chunks)
    for i, chunk_data in enumerate(chunks):
        name = f"{i+1:02d}_OF_{total:02d}__XX"
        path = os.path.join(dest_folder, name)
        with open(path, 'wb') as f:
            f.write(chunk_data)
        print(f"  Written chunk: {path}  ({len(chunk_data):,} bytes)")


# ─────────────────────────────────────────────────────────────
#  High-level converters
# ─────────────────────────────────────────────────────────────

def convert_still(input_path: str, file_number: int, dest_dir: str,
                  video_standard: str = '1080i50',
                  split_fat32: bool = True,
                  delete_source: bool = False,
                  log=print,
                  ignore_alpha: bool = False):
    """Convert a single TGA/PNG/BMP/JPG still to .SWS."""

    log(f"Converting still: {os.path.basename(input_path)}")
    info = get_video_info(input_path)
    w, h = info['width'], info['height']

    with tempfile.TemporaryDirectory() as tmp:
        fill_raw = os.path.join(tmp, 'fill.v210')
        key_raw  = None

        has_alpha = info['has_alpha'] and not ignore_alpha
        log(f"  Size: {w}x{h}, has_alpha={info['has_alpha']}{' (ignored)' if ignore_alpha and info['has_alpha'] else ''}")
        key_raw = convert_to_v210(input_path, fill_raw, extract_alpha=has_alpha)
        if key_raw is None:
            actual_key = os.path.join(tmp, 'key.v210')
            _generate_white_key(fill_raw, actual_key)
        else:
            actual_key = os.path.join(tmp, 'key.v210')
            os.rename(fill_raw + '.alpha.raw', actual_key)

        plane_size = os.path.getsize(fill_raw)
        src_name   = os.path.basename(input_path)
        clip_name  = f"{file_number}_1_000"

        hdr = build_sws_header(
            source_filename=src_name,
            clip_name=clip_name,
            width=w, height=h,
            frame_count=1,
            plane_size=plane_size,
            video_standard=video_standard,
            is_still=True,
        )

        dest_path = os.path.join(dest_dir, f"{file_number}.SWS")
        write_sws(dest_path, fill_raw, actual_key, hdr, split_fat32, frame_count=1)

    if delete_source:
        os.remove(input_path)
        log(f"  Deleted source: {input_path}")

    log(f"  Done → {dest_path}")
    return dest_path


def convert_clip(input_path: str, file_number: int, dest_dir: str,
                 video_standard: str = '1080i50',
                 split_fat32: bool = True,
                 delete_source: bool = False,
                 log=print,
                 ignore_alpha: bool = False,
                 include_audio: bool = True):
    """Convert a MOV/MP4/AVI/etc video clip to .SWS."""

    log(f"Converting clip: {os.path.basename(input_path)}")
    info = get_video_info(input_path)
    w, h, fps = info['width'], info['height'], info['fps']
    frame_count = info['frame_count']

    has_alpha = info['has_alpha'] and not ignore_alpha
    will_include_audio = include_audio and info['has_audio']
    log(f"  Size: {w}x{h}  FPS: {fps:.2f}  Frames: {frame_count}  has_alpha={info['has_alpha']}{' (ignored)' if ignore_alpha and info['has_alpha'] else ''}  audio={info['has_audio']}{' (included)' if will_include_audio else ' (excluded)' if info['has_audio'] else ''}")

    with tempfile.TemporaryDirectory() as tmp:
        fill_raw   = os.path.join(tmp, 'fill.v210')
        actual_key = None
        audio_raw  = None

        key_raw = convert_to_v210(input_path, fill_raw, extract_alpha=has_alpha)
        if key_raw:
            actual_key = os.path.join(tmp, 'key.v210')
            os.rename(fill_raw + '.alpha.raw', actual_key)
        else:
            actual_key = os.path.join(tmp, 'key.v210')
            _generate_white_key(fill_raw, actual_key)

        # Extract audio if requested and present
        if will_include_audio:
            audio_path = os.path.join(tmp, 'audio.pcm')
            if extract_audio(input_path, audio_path, frame_count, fps):
                audio_raw = audio_path
                log(f"  Audio extracted: {os.path.getsize(audio_raw):,} bytes")
            else:
                log(f"  Audio extraction failed -- writing without audio")

        plane_size = os.path.getsize(fill_raw) // frame_count
        src_name   = os.path.basename(input_path)
        clip_name  = Path(input_path).stem  # use filename stem as clip name

        hdr = build_sws_header(
            source_filename=src_name,
            clip_name=clip_name,
            width=w, height=h,
            frame_count=frame_count,
            plane_size=plane_size,
            video_standard=video_standard,
            is_still=False,
            fps=fps,
            has_audio=(audio_raw is not None),
        )

        dest_path = os.path.join(dest_dir, f"{file_number}.SWS")
        write_sws(dest_path, fill_raw, actual_key, hdr, split_fat32,
                  frame_count=frame_count, audio_raw=audio_raw)

    if delete_source:
        os.remove(input_path)
        log(f"  Deleted source: {input_path}")

    log(f"  Done → {dest_path}")
    return dest_path


def convert_tga_sequence(tga_files: list, file_number: int, dest_dir: str,
                         video_standard: str = '1080i50',
                         split_fat32: bool = True,
                         delete_source: bool = False,
                         log=print,
                         ignore_alpha: bool = False):
    """Convert a numbered TGA sequence into a single multi-frame .SWS clip."""

    log(f"Converting TGA sequence: {len(tga_files)} frames → {file_number}.SWS")
    info = get_video_info(tga_files[0])
    w, h = info['width'], info['height']
    frame_count = len(tga_files)
    has_alpha = info['has_alpha'] and not ignore_alpha

    with tempfile.TemporaryDirectory() as tmp:
        # Build a concat demuxer file
        concat_file = os.path.join(tmp, 'concat.txt')
        with open(concat_file, 'w') as f:
            for tga in sorted(tga_files):
                f.write(f"file '{tga}'\n")

        fill_raw = os.path.join(tmp, 'fill.v210')
        ffmpeg = _get_ffmpeg_path('ffmpeg')
        cmd = [ffmpeg, '-y', '-f', 'concat', '-safe', '0',
               '-i', concat_file,
               '-frames:v', str(frame_count),
               '-f', 'rawvideo', '-vcodec', 'v210', fill_raw]
        subprocess.run(cmd, capture_output=True, check=True)

        # Key/alpha
        actual_key = None
        if has_alpha:
            key_raw = os.path.join(tmp, 'key.v210')
            cmd_key = [ffmpeg, '-y', '-f', 'concat', '-safe', '0',
                       '-i', concat_file,
                       '-frames:v', str(frame_count),
                       '-vf', 'alphaextract,format=yuv420p,colorspace=bt709,scale=out_range=tv',
                       '-f', 'rawvideo', '-vcodec', 'v210', key_raw]
            result = subprocess.run(cmd_key, capture_output=True)
            if result.returncode != 0 or not os.path.exists(key_raw) or os.path.getsize(key_raw) == 0:
                cmd_key = [ffmpeg, '-y', '-f', 'concat', '-safe', '0',
                           '-i', concat_file,
                           '-frames:v', str(frame_count),
                           '-vf', 'alphaextract',
                           '-f', 'rawvideo', '-vcodec', 'v210', key_raw]
                subprocess.run(cmd_key, capture_output=True, check=True)
            _byteswap_v210(key_raw)
            actual_key = key_raw
        else:
            actual_key = os.path.join(tmp, 'key.v210')
            _generate_white_key(fill_raw, actual_key)

        _byteswap_v210(fill_raw)

        fill_file_size = os.path.getsize(fill_raw)
        plane_size = fill_file_size // frame_count
        log(f"  fill_raw size: {fill_file_size:,}  frame_count: {frame_count}  plane_size: {plane_size:,}")
        src_name   = os.path.basename(tga_files[0])
        clip_name  = Path(tga_files[0]).stem

        hdr = build_sws_header(
            source_filename=src_name,
            clip_name=clip_name,
            width=w, height=h,
            frame_count=frame_count,
            plane_size=plane_size,
            video_standard=video_standard,
            is_still=False,
        )

        dest_path = os.path.join(dest_dir, f"{file_number}.SWS")
        write_sws(dest_path, fill_raw, actual_key, hdr, split_fat32, frame_count=frame_count)

    if delete_source:
        for f in tga_files:
            os.remove(f)

    log(f"  Done → {dest_path}")
    return dest_path


# ─────────────────────────────────────────────────────────────
#  File naming parser (K-Watch conventions)
# ─────────────────────────────────────────────────────────────

def parse_filename(filename: str) -> Optional[dict]:
    """
    Parse a K-Watch style filename and return metadata.
    Returns None if the file doesn't match any known pattern.

    Patterns:
      Still:    NAME{NUM}[F][K][A].EXT
                e.g. Still001.TGA  Still001F.BMP  Still001FA.TGA
      Clip TGA: NAME{NUM}[F][K][A]_{TOTAL}_{SEQ:04d}.TGA
                e.g. Clip1A_6_0001.TGA  wipe1FA_53_0001.TGA
      MOV/AVI:  NAME{NUM}.EXT
                e.g. Newsclip1.MOV  5.AVI
    """
    name = Path(filename).stem
    ext  = Path(filename).suffix.lower()

    # Scan right-to-left for the file number and optional F/K/A flags
    # TGA sequence: ends in _NNNN (4-digit sequence number)
    tga_seq_match = re.match(
        r'^(.*?)(\d+)([FfKkAa]{0,2})_(\d+)_(\d{4})$', name
    )
    if tga_seq_match and ext == '.tga':
        clip_name = tga_seq_match.group(1)
        file_num  = int(tga_seq_match.group(2))
        flags     = tga_seq_match.group(3).upper()
        total     = int(tga_seq_match.group(4))
        seq       = int(tga_seq_match.group(5))
        return {
            'type':      'tga_seq',
            'clip_name': clip_name,
            'file_num':  file_num,
            'flags':     flags,   # combination of F, K, A
            'total':     total,
            'seq':       seq,
            'is_fill':   'K' not in flags,
            'is_key':    'K' in flags,
            'has_audio': 'A' in flags,
        }

    # Still: ends in digits + optional flags, no sequence suffix
    still_match = re.match(r'^(.*?)(\d+)([FfKkAa]{0,2})$', name)
    if still_match and ext in ('.tga', '.bmp', '.png', '.jpg', '.jpeg', '.tif', '.tiff'):
        clip_name = still_match.group(1)
        file_num  = int(still_match.group(2))
        flags     = still_match.group(3).upper()
        return {
            'type':      'still',
            'clip_name': clip_name,
            'file_num':  file_num,
            'flags':     flags,
            'is_fill':   'K' not in flags,
            'is_key':    'K' in flags,
            'has_audio': 'A' in flags,
        }

    # MOV/AVI/MP4: just needs a number at the end of the stem
    clip_match = re.match(r'^(.*?)(\d+)$', name)
    if clip_match and ext in ('.mov', '.mp4', '.avi', '.mxf', '.m4v', '.mkv',
                               '.h264', '.h265', '.mts', '.m2ts'):
        return {
            'type':      'clip',
            'clip_name': clip_match.group(1),
            'file_num':  int(clip_match.group(2)),
            'flags':     '',
            'is_fill':   True,
            'is_key':    False,
            'has_audio': True,
        }

    return None


# ─────────────────────────────────────────────────────────────
#  Watch folder service
# ─────────────────────────────────────────────────────────────

class WatchService:
    """Monitors a folder and converts files as they arrive."""

    POLL_INTERVAL = 2.0  # seconds

    def __init__(self, watch_dir: str, dest_dir: str,
                 video_standard: str = '1080i50',
                 split_fat32: bool = True,
                 delete_source: bool = False,
                 ignore_alpha: bool = False,
                 include_audio: bool = True,
                 log=print):
        self.watch_dir      = watch_dir
        self.dest_dir       = dest_dir
        self.video_standard = video_standard
        self.split_fat32    = split_fat32
        self.delete_source  = delete_source
        self.ignore_alpha   = ignore_alpha
        self.include_audio  = include_audio
        self.log            = log
        self._stop_event    = threading.Event()
        self._seen           = set()
        self._pending_seqs: dict = {}  # file_num -> {seq -> path}

        os.makedirs(dest_dir, exist_ok=True)

    def start(self):
        self.log(f"Watching: {self.watch_dir}")
        self.log(f"Output:   {self.dest_dir}")
        self.log(f"Standard: {self.video_standard}")
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        return t

    def stop(self):
        self._stop_event.set()

    def _run(self):
        while not self._stop_event.is_set():
            self._scan()
            time.sleep(self.POLL_INTERVAL)

    def _scan(self):
        try:
            entries = sorted(os.listdir(self.watch_dir))
        except OSError:
            return

        for fname in entries:
            fpath = os.path.join(self.watch_dir, fname)
            if not os.path.isfile(fpath):
                continue
            if fname in self._seen:
                continue

            meta = parse_filename(fname)
            if meta is None:
                continue

            # Wait until the file has finished being written
            if not self._file_stable(fpath):
                continue

            self._seen.add(fname)

            try:
                if meta['type'] == 'clip':
                    convert_clip(fpath, meta['file_num'], self.dest_dir,
                                 self.video_standard, self.split_fat32,
                                 self.delete_source, self.log,
                                 ignore_alpha=self.ignore_alpha,
                                 include_audio=self.include_audio)

                elif meta['type'] == 'still' and meta['is_fill']:
                    convert_still(fpath, meta['file_num'], self.dest_dir,
                                  self.video_standard, self.split_fat32,
                                  self.delete_source, self.log,
                                  ignore_alpha=self.ignore_alpha)

                elif meta['type'] == 'tga_seq' and meta['is_fill']:
                    self._accumulate_seq(fname, fpath, meta, entries)

            except Exception as e:
                import traceback
                self.log(f"  ERROR converting {fname}: {e}")
                self.log(f"  {traceback.format_exc()}")

    def _accumulate_seq(self, fname, fpath, meta, all_entries):
        """Collect all TGA frames for a sequence then convert when complete."""
        fnum  = meta['file_num']
        total = meta['total']

        if fnum not in self._pending_seqs:
            self._pending_seqs[fnum] = {}
        self._pending_seqs[fnum][meta['seq']] = fpath

        if len(self._pending_seqs[fnum]) == total:
            frames = [self._pending_seqs[fnum][i+1] for i in range(total)]
            del self._pending_seqs[fnum]
            convert_tga_sequence(frames, fnum, self.dest_dir,
                                 self.video_standard, self.split_fat32,
                                 self.delete_source, self.log,
                                 ignore_alpha=self.ignore_alpha)

    @staticmethod
    def _file_stable(path: str, wait: float = 0.5) -> bool:
        """Return True if the file size hasn't changed in `wait` seconds."""
        try:
            s1 = os.path.getsize(path)
            time.sleep(wait)
            s2 = os.path.getsize(path)
            return s1 == s2 and s1 > 0
        except OSError:
            return False


# ─────────────────────────────────────────────────────────────
#  Simple Tkinter GUI
# ─────────────────────────────────────────────────────────────

def launch_gui():
    try:
        import tkinter as tk
        from tkinter import ttk, filedialog, scrolledtext
    except ImportError:
        print("tkinter not available. Use command-line mode.")
        return

    import json

    SETTINGS_FILE = os.path.join(os.path.expanduser('~'), '.kwatch_settings.json')

    def load_settings():
        try:
            with open(SETTINGS_FILE) as f:
                return json.load(f)
        except Exception:
            return {}

    def save_settings():
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump({
                    'watch':    watch_var.get(),
                    'dest':     dest_var.get(),
                    'standard': std_var.get(),
                    'split':    split_var.get(),
                    'delete':   delete_var.get(),
                    'ignore_alpha': ignore_alpha_var.get(),
                    'include_audio': include_audio_var.get(),
                    'start_num': start_num_var.get(),
                }, f)
        except Exception:
            pass

    try:
        root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    except Exception:
        root = tk.Tk()
    root.title("MacHuna v1.0")
    root.geometry("700x600")
    root.resizable(True, True)

    # ── Style ──
    style = ttk.Style()
    style.theme_use('aqua' if sys.platform == 'darwin' else 'clam')

    pad = dict(padx=8, pady=4)

    # ── Watch folder row ──
    frm1 = ttk.LabelFrame(root, text="Watch Folder")
    frm1.pack(fill='x', **pad)
    watch_var = tk.StringVar()
    ttk.Entry(frm1, textvariable=watch_var, width=60).pack(side='left', fill='x', expand=True, **pad)
    ttk.Button(frm1, text="Browse…",
               command=lambda: watch_var.set(filedialog.askdirectory())).pack(side='left', **pad)

    # ── Destination folder row ──
    frm2 = ttk.LabelFrame(root, text="Destination Folder")
    frm2.pack(fill='x', **pad)
    dest_var = tk.StringVar()
    ttk.Entry(frm2, textvariable=dest_var, width=60).pack(side='left', fill='x', expand=True, **pad)
    ttk.Button(frm2, text="Browse…",
               command=lambda: dest_var.set(filedialog.askdirectory())).pack(side='left', **pad)

    # ── Settings row ──
    frm3 = ttk.LabelFrame(root, text="Settings")
    frm3.pack(fill='x', **pad)

    ttk.Label(frm3, text="Video Standard:").pack(side='left', **pad)
    std_var = tk.StringVar(value='1080i50')
    std_cb  = ttk.Combobox(frm3, textvariable=std_var, width=12,
                            values=list(VIDEO_STANDARDS.keys()), state='readonly')
    std_cb.pack(side='left', **pad)

    split_var         = tk.BooleanVar(value=True)
    delete_var        = tk.BooleanVar(value=False)
    ignore_alpha_var  = tk.BooleanVar(value=False)
    include_audio_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(frm3, text="Split >4GB (FAT32)", variable=split_var).pack(side='left', **pad)
    ttk.Checkbutton(frm3, text="Delete source after conversion", variable=delete_var).pack(side='left', **pad)
    ttk.Checkbutton(frm3, text="Ignore alpha/key", variable=ignore_alpha_var).pack(side='left', **pad)
    ttk.Checkbutton(frm3, text="Include audio", variable=include_audio_var).pack(side='left', **pad)

    # ── Load saved settings ──
    s = load_settings()
    if s.get('watch'):    watch_var.set(s['watch'])
    if s.get('dest'):     dest_var.set(s['dest'])
    if s.get('standard'): std_var.set(s['standard'])
    if 'split'        in s: split_var.set(s['split'])
    if 'delete'       in s: delete_var.set(s['delete'])
    if 'ignore_alpha'   in s: ignore_alpha_var.set(s['ignore_alpha'])
    if 'include_audio'  in s: include_audio_var.set(s['include_audio'])
    if 'start_num'      in s: start_num_var.set(s['start_num'])

    # ── Buttons ──
    frm4 = ttk.Frame(root)
    frm4.pack(fill='x', **pad)

    service_ref = [None]
    run_btn = ttk.Button(frm4, text="▶  Start Watching")
    stop_btn = ttk.Button(frm4, text="⏹  Stop", state='disabled')
    run_btn.pack(side='left', **pad)
    stop_btn.pack(side='left', **pad)

    # ── Open Files / Batch Convert row ──
    frm5 = ttk.LabelFrame(root, text="Batch Convert")
    frm5.pack(fill='x', **pad)

    ttk.Label(frm5, text="Start number:").pack(side='left', **pad)
    start_num_var = tk.IntVar(value=1)
    start_num_entry = ttk.Spinbox(frm5, from_=1, to=9999, textvariable=start_num_var, width=6)
    start_num_entry.pack(side='left', **pad)

    open_btn = ttk.Button(frm5, text="Open Files…")
    open_btn.pack(side='left', **pad)

    # ── Log area ──
    log_frame = ttk.LabelFrame(root, text="Log")
    log_frame.pack(fill='both', expand=True, **pad)
    log_text = scrolledtext.ScrolledText(log_frame, height=20, font=('Menlo', 11))
    log_text.pack(fill='both', expand=True, padx=4, pady=4)

    def log(msg):
        ts = datetime.now().strftime('%H:%M:%S')
        log_text.insert('end', f"[{ts}] {msg}\n")
        log_text.see('end')
        root.update_idletasks()

    def on_drop(event):
        """Handle files dropped onto the log area."""
        d = dest_var.get().strip()
        if not d:
            log("ERROR: Please set a Destination Folder before dropping files.")
            return

        # Parse the drop data -- tkinterdnd2 returns paths wrapped in {} if they contain spaces
        raw = event.data.strip()
        paths = []
        # Handle paths wrapped in braces (spaces in filenames)
        import shlex
        try:
            paths = shlex.split(raw)
        except ValueError:
            # Fallback: strip braces manually
            paths = [p.strip('{}') for p in re.findall(r'\{[^}]+\}|\S+', raw)]

        # Filter to supported file types
        supported = {'.mov', '.mp4', '.avi', '.mxf', '.tga', '.png', '.bmp', '.jpg', '.jpeg'}
        valid = [p for p in paths if Path(p).suffix.lower() in supported]

        if not valid:
            log("ERROR: No supported files in drop.")
            return

        # Ask for starting file number
        import tkinter.simpledialog as simpledialog
        start_num = simpledialog.askinteger(
            "File Number",
            f"Starting file number for {len(valid)} file(s):",
            initialvalue=1, minvalue=1, maxvalue=9999, parent=root
        )
        if start_num is None:
            return  # user cancelled

        try:
            check_ffmpeg()
        except RuntimeError as e:
            log(f"ERROR: {e}")
            return

        def convert_dropped():
            for i, path in enumerate(sorted(valid)):
                fnum = start_num + i
                ext = Path(path).suffix.lower()
                try:
                    if ext in {'.mov', '.mp4', '.avi', '.mxf'}:
                        convert_clip(path, fnum, d,
                                     std_var.get(), split_var.get(),
                                     delete_var.get(), log,
                                     ignore_alpha=ignore_alpha_var.get(),
                                     include_audio=include_audio_var.get())
                    elif ext == '.tga' and Path(path).stat().st_size > 0:
                        convert_still(path, fnum, d,
                                      std_var.get(), split_var.get(),
                                      delete_var.get(), log,
                                      ignore_alpha=ignore_alpha_var.get())
                    else:
                        convert_still(path, fnum, d,
                                      std_var.get(), split_var.get(),
                                      delete_var.get(), log,
                                      ignore_alpha=ignore_alpha_var.get())
                except Exception as e:
                    import traceback
                    log(f"  ERROR converting {Path(path).name}: {e}")
                    log(f"  {traceback.format_exc()}")

        threading.Thread(target=convert_dropped, daemon=True).start()

    # ── Wire up drag and drop to log area ──
    if HAS_DND:
        log_text.drop_target_register(DND_FILES)
        log_text.dnd_bind('<<Drop>>', on_drop)
        log(f"Drag and drop enabled -- drop files onto the log area to convert.")

    def open_files():
        """Open a file picker for batch conversion."""
        d = dest_var.get().strip()
        if not d:
            log("ERROR: Please set a Destination Folder before converting files.")
            return

        supported_types = [
            ('Video & Image files', '*.mov *.mp4 *.avi *.mxf *.tga *.png *.bmp *.jpg *.jpeg'),
            ('Video files', '*.mov *.mp4 *.avi *.mxf'),
            ('Image files', '*.tga *.png *.bmp *.jpg *.jpeg'),
            ('All files', '*.*'),
        ]
        paths = filedialog.askopenfilenames(
            title="Select files to convert",
            filetypes=supported_types,
            parent=root
        )
        if not paths:
            return

        start_num = start_num_var.get()
        valid = sorted(paths)  # alphabetical order

        log(f"Batch convert: {len(valid)} file(s) starting at number {start_num}")
        for i, p in enumerate(valid):
            log(f"  {start_num + i} ← {Path(p).name}")

        try:
            check_ffmpeg()
        except RuntimeError as e:
            log(f"ERROR: {e}")
            return

        def convert_batch():
            results = []
            for i, path in enumerate(valid):
                fnum = start_num + i
                ext = Path(path).suffix.lower()
                try:
                    if ext in {'.mov', '.mp4', '.avi', '.mxf'}:
                        convert_clip(path, fnum, d,
                                     std_var.get(), split_var.get(),
                                     delete_var.get(), log,
                                     ignore_alpha=ignore_alpha_var.get(),
                                     include_audio=include_audio_var.get())
                    else:
                        convert_still(path, fnum, d,
                                      std_var.get(), split_var.get(),
                                      delete_var.get(), log,
                                      ignore_alpha=ignore_alpha_var.get())
                    results.append((fnum, Path(path).name, 'OK'))
                except Exception as e:
                    import traceback
                    log(f"  ERROR converting {Path(path).name}: {e}")
                    log(f"  {traceback.format_exc()}")
                    results.append((fnum, Path(path).name, f'ERROR: {e}'))

            # Write conversion log to destination folder
            if results:
                from datetime import datetime as dt
                log_filename = f"MacHuna_Log_{dt.now().strftime('%Y%m%d_%H%M%S')}.txt"
                log_path = os.path.join(d, log_filename)
                try:
                    with open(log_path, 'w') as f:
                        f.write(f"MacHuna Conversion Log\n")
                        f.write(f"{'=' * 40}\n")
                        f.write(f"Date: {dt.now().strftime('%d %b %Y %H:%M:%S')}\n")
                        f.write(f"Standard: {std_var.get()}\n")
                        f.write(f"{'=' * 40}\n\n")
                        for fnum, fname, status in results:
                            f.write(f"{fnum:4d}  {fname}  [{status}]\n")
                    log(f"Conversion log saved: {log_filename}")
                except Exception as e:
                    log(f"  Could not write log file: {e}")

            # Advance start number for next batch
            root.after(0, lambda: start_num_var.set(start_num + len(valid)))

        threading.Thread(target=convert_batch, daemon=True).start()

    open_btn.config(command=open_files)

    def start_watching():
        w = watch_var.get().strip()
        d = dest_var.get().strip()
        if not w or not d:
            log("ERROR: Please set both Watch and Destination folders.")
            return
        try:
            check_ffmpeg()
        except RuntimeError as e:
            log(f"ERROR: {e}")
            return
        save_settings()
        svc = WatchService(w, d, std_var.get(), split_var.get(), delete_var.get(),
                           ignore_alpha=ignore_alpha_var.get(),
                           include_audio=include_audio_var.get(), log=log)
        svc.start()
        service_ref[0] = svc
        run_btn.config(state='disabled')
        stop_btn.config(state='normal')
        log("Service started.")

    def stop_watching():
        if service_ref[0]:
            service_ref[0].stop()
            service_ref[0] = None
        run_btn.config(state='normal')
        stop_btn.config(state='disabled')
        log("Service stopped.")

    run_btn.config(command=start_watching)
    stop_btn.config(command=stop_watching)

    root.mainloop()


# ─────────────────────────────────────────────────────────────
#  CLI entry point
# ─────────────────────────────────────────────────────────────

def main():
    # When bundled as a .app, always launch GUI
    if getattr(sys, 'frozen', False):
        launch_gui()
        return

    parser = argparse.ArgumentParser(
        description='MacHuna — Mac replacement for Grass Valley K-Watch',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start folder watch service
  python3 kwatch_converter.py --watch ~/Desktop/KWatch --dest ~/Desktop/SWS

  # Convert a single file
  python3 kwatch_converter.py --convert myclip.mov --number 42 --dest ~/Desktop/SWS

  # Launch GUI
  python3 kwatch_converter.py --gui
        """
    )
    parser.add_argument('--watch',    help='Folder to watch for incoming files')
    parser.add_argument('--dest',     help='Destination folder for .SWS files')
    parser.add_argument('--convert',  help='Convert a single file immediately')
    parser.add_argument('--number',   type=int, default=1, help='File number for --convert')
    parser.add_argument('--standard', default='1080i50',
                        choices=list(VIDEO_STANDARDS.keys()),
                        help='Output video standard (default: 1080i50)')
    parser.add_argument('--no-split', action='store_true',
                        help='Do not split files >4GB')
    parser.add_argument('--delete-source', action='store_true',
                        help='Delete source files after conversion')
    parser.add_argument('--gui',      action='store_true', help='Launch GUI')

    args = parser.parse_args()

    if args.gui:
        launch_gui()
        return

    try:
        check_ffmpeg()
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    split = not args.no_split

    if args.convert:
        if not args.dest:
            print("ERROR: --dest is required with --convert")
            sys.exit(1)
        os.makedirs(args.dest, exist_ok=True)
        ext = Path(args.convert).suffix.lower()
        if ext == '.tga':
            convert_still(args.convert, args.number, args.dest,
                          args.standard, split, args.delete_source)
        else:
            convert_clip(args.convert, args.number, args.dest,
                         args.standard, split, args.delete_source)
        return

    if args.watch and args.dest:
        svc = WatchService(args.watch, args.dest, args.standard,
                           split, args.delete_source)
        t = svc.start()
        print("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            svc.stop()
            print("\nStopped.")
        return

    parser.print_help()


if __name__ == '__main__':
    main()

