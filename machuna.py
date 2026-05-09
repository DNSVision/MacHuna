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
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, scrolledtext
except ImportError:
    tk = None

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = False  # Disabled -- tkdnd native library incompatible with Homebrew Python/Tk on Apple Silicon
except (ImportError, Exception):
    HAS_DND = False

VERSION = "1.5.16"

# ─────────────────────────────────────────────────────────────
#  SWS format constants (reverse-engineered from binary analysis)
# ─────────────────────────────────────────────────────────────

SWS_MAGIC       = b'S&W Kahuna Still'   # confirmed - used for both stills AND clips
SWS_VERSION     = b'9.6 Release 1'
SWS_COPYRIGHT   = b'Copyright (c) : Grass Valley 2021'
SWS_HEADER_SIZE = 512

# Video standard codes (offset 0x188 in header)
# Video standard codes confirmed by hex analysis of K-Watch reference files (2026-05-09).
# Both 0x188 (standard code) and 0x18C (format variant) confirmed for all listed standards.
# 1080i/59.94 uniquely uses 0xc923 -- the 0x8000 bit appears to flag drop-frame timing.
# Unverified standards (1080p29.97, 1080p30, 2160p variants) removed from dropdown pending
# confirmation against K-Watch reference files. See DEVELOPMENT_NOTES.md roadmap.
VIDEO_STANDARDS = {
    '1080i50':   0x4923,   # confirmed
    '1080i5994': 0xc923,   # confirmed -- 0x8000 bit flags drop-frame timing
    '1080i60':   0x4923,   # confirmed
    '1080p25':   0x4923,   # confirmed
    '1080p50':   0x4923,   # confirmed
    '1080p5994': 0x4923,   # confirmed
    '1080p60':   0x4923,   # confirmed
    '720p50':    0x4923,   # confirmed
    '720p5994':  0x4923,   # confirmed
}

# Format variant field (0x18C) -- Kahuna internal standard index, confirmed by
# hex analysis of K-Watch reference files (2026-05-09). Not a flags field.
FORMAT_VARIANTS = {
    '1080i50':   0x08,   # confirmed
    '1080i5994': 0x05,   # confirmed
    '1080i60':   0x04,   # confirmed
    '1080p25':   0x13,   # confirmed
    '1080p50':   0x18,   # confirmed
    '1080p5994': 0x17,   # confirmed
    '1080p60':   0x16,   # confirmed
    '720p50':    0x10,   # confirmed
    '720p5994':  0x0f,   # confirmed
}

# Reverse lookup: format variant value -> fps. All variant values are unique so
# this gives an unambiguous fps reading. Used by SWSHeader and HulaSWSHeader.
FORMAT_VARIANT_FPS = {
    0x08: 25.0,    # 1080i50   -- 25 frames/sec (50 fields/sec)
    0x05: 29.97,   # 1080i5994 -- 29.97 frames/sec (59.94 fields/sec)
    0x04: 30.0,    # 1080i60   -- 30 frames/sec (60 fields/sec)
    0x13: 25.0,    # 1080p25
    0x18: 50.0,    # 1080p50
    0x17: 59.94,   # 1080p5994
    0x16: 60.0,    # 1080p60
    0x10: 50.0,    # 720p50
    0x0f: 59.94,   # 720p5994
}

FAT32_LIMIT = 4 * 1024 * 1024 * 1024  # 4 GB

_current_ffmpeg_proc = None
_ffmpeg_proc_lock = __import__('threading').Lock()


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
                     has_audio: bool = False,
                     has_key: bool = True,
                     auto_play: bool = False,
                     loop_play: bool = False) -> bytes:
    """Build a 512-byte SWS file header.

    has_key: if False (ignore alpha / no key plane written), 0x1A8 and 0x1B4
             are zeroed and audio offset is calculated after fill only,
             matching confirmed K-Watch behaviour.

    auto_play: sets bit 2 (0x04) of the low byte at 0x188 (confirmed by hex analysis).
    loop_play: sets bit 3 (0x08) of the low byte at 0x188 (confirmed by hex analysis).
    """

    std_code = VIDEO_STANDARDS.get(video_standard, 0x4923)
    if auto_play:
        std_code |= 0x04
    if loop_play:
        std_code |= 0x08
    now_str  = datetime.now().strftime('%a %b %d %H:%M:%S %Y').encode('ascii')

    # Audio parameters (confirmed from K-Watch reference file analysis)
    # audio_frame_size = 0x1680 (5760) -- fixed value in header regardless of fps
    # Actual bytes per frame = round(48000/fps) * 2 bytes * 16 channels
    AUDIO_FRAME_SIZE_HDR = 0x1680  # always 5760 in header (confirmed)
    samples_per_frame    = round(48000 / fps)
    audio_bytes_per_frame = samples_per_frame * 2 * 16
    audio_data_size      = audio_bytes_per_frame * frame_count if has_audio else 0

    # Audio offset is after fill+key if key present, fill only if not
    # Confirmed by hex analysis of K-Watch no-alpha reference file
    planes_size  = plane_size * frame_count * (2 if has_key else 1)
    audio_offset = SWS_HEADER_SIZE + planes_size
    total_size   = audio_offset + audio_data_size

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

    struct.pack_into('>I', hdr, 0x18C, FORMAT_VARIANTS.get(video_standard, 0x18))

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

    # 0x1A8  Play count -- frame count if key present, 0 if no key plane
    # Confirmed: K-Watch zeros this field when no key plane is written
    struct.pack_into('>I', hdr, 0x1A8, frame_count if has_key else 0)

    # 0x1B0  Play rate (float32 BE) = 1.0
    struct.pack_into('>f', hdr, 0x1B0, play_rate)

    # 0x1B4  (plane_size * frame_count + header_size) / 32 -- zeroed if no key plane
    # Confirmed: K-Watch zeros this field when no key plane is written
    val_1b4 = (plane_size * frame_count + SWS_HEADER_SIZE) // 32 if has_key else 0
    struct.pack_into('>I', hdr, 0x1B4, val_1b4)

    # 0x1C2  Audio frame size (uint16 BE) -- 0x1680 (5760) if audio, 0 if not
    struct.pack_into('>H', hdr, 0x1C2, AUDIO_FRAME_SIZE_HDR if has_audio else 0)

    # 0x1CC  Total file size = header + planes + audio data
    # Capped at uint32 max for files >4GB -- _write_sws_split() patches this
    # field with the correct final chunk size before writing chunk 1.
    struct.pack_into('>I', hdr, 0x1CC, min(total_size, 0xFFFFFFFF))

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


def _run_ffmpeg(cmd, capture_output=True, check=False):
    import subprocess as _sp
    global _current_ffmpeg_proc
    with _ffmpeg_proc_lock:
        proc = _sp.Popen(cmd, stdout=_sp.PIPE, stderr=_sp.PIPE)
        _current_ffmpeg_proc = proc
    stdout, stderr = proc.communicate()
    with _ffmpeg_proc_lock:
        _current_ffmpeg_proc = None
    result = _sp.CompletedProcess(cmd, proc.returncode, stdout, stderr)
    if check and proc.returncode != 0:
        raise _sp.CalledProcessError(proc.returncode, cmd, stdout, stderr)
    return result

def _kill_current_ffmpeg():
    global _current_ffmpeg_proc
    with _ffmpeg_proc_lock:
        proc = _current_ffmpeg_proc
    if proc is not None:
        try: proc.kill()
        except Exception: pass

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

    info = {'width': 0, 'height': 0, 'fps': 25.0, 'frame_count': 1, 'has_alpha': False, 'has_audio': False, 'is_interlaced': False}

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

            # Interlace detection
            field_order = stream.get('field_order', 'progressive')
            info['is_interlaced'] = field_order not in ('progressive', 'unknown', '')
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

    _run_ffmpeg(cmd_fill, check=True)
    _byteswap_v210(output_path)

    if extract_alpha:
        alpha_path = output_path + '.alpha.raw'
        # Extract alpha, convert to clean limited-range luma (64=black, 940=white)
        # Use scale2ref to map 0-255 alpha to 64-940 luma range
        cmd_key = [ffmpeg, '-y', '-i', input_path,
                   '-vf', 'alphaextract,format=yuv420p,colorspace=bt709,'
                          'scale=out_range=tv',
                   '-f', 'rawvideo', '-vcodec', 'v210', alpha_path]
        result = _run_ffmpeg(cmd_key)
        if result.returncode != 0 or not os.path.exists(alpha_path) or os.path.getsize(alpha_path) == 0:
            # Simpler fallback
            cmd_key = [ffmpeg, '-y', '-i', input_path,
                       '-vf', 'alphaextract',
                       '-f', 'rawvideo', '-vcodec', 'v210', alpha_path]
            _run_ffmpeg(cmd_key, check=True)
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

    # Extract as 16-bit LE, 16 channels, 48kHz raw PCM.
    # K-Watch channel mapping (confirmed by hex analysis of reference SWS):
    #   Ch1 = Left, Ch2 = silence, Ch3 = Right, Ch4 = silence, Ch5-16 = silence
    # A straight -ac 16 upmix puts L on Ch1 and R on Ch2 which is wrong.
    # Use the pan filter to route explicitly. Unspecified channels are silent.
    # Note: 'c1=0' syntax is invalid in ffmpeg -- just omit silent channels.
    pan_filter = 'pan=16c|c0=c0|c2=c1'
    cmd = [ffmpeg, '-y', '-i', input_path,
           '-vn',
           '-af', pan_filter,
           '-acodec', 'pcm_s16le',
           '-ar', '48000',
           '-f', 's16le',
           output_path]
    result = _run_ffmpeg(cmd)

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
              audio_raw: Optional[str] = None,
              log=print):
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
        _write_sws_split(dest_path, fill_raw, key_raw, header, frame_count, log=log)
    else:
        with open(dest_path, 'wb') as out:
            out.write(header)
            _copy_file(fill_raw, out)
            if key_raw:
                _copy_file(key_raw, out)
            if audio_raw:
                _copy_file(audio_raw, out)
        log(f"  Written: {dest_path}  ({total:,} bytes)")


def _copy_file(src: str, dest_fh):
    with open(src, 'rb') as f:
        while chunk := f.read(1024 * 1024):
            dest_fh.write(chunk)


def _write_sws_split(dest_folder: str, fill_raw: str, key_raw: Optional[str],
                     header: bytes, frame_count: int = 1, log=print):
    """Split large SWS into 2GB FAT32-safe chunks inside a named folder.

    Chunk format (confirmed by hex analysis of K-Watch reference split files):
      - Folder named <clip_number>.SWS
      - Chunk filenames: 01_OF_03._XX, 02_OF_03._XX, 03_OF_03._XX ...
      - Chunk 1: patched 512-byte header + video data, exactly 2GB
      - Chunks 2..N-1: raw video data only, exactly 2GB each
      - Final chunk: raw video data only, remainder (any size)

    Header patches for split files (confirmed by hex analysis):
      - 0x1A8 (play count): zeroed
      - 0x1B4: zeroed
      - 0x1CC (total file size): set to size of final chunk only
      - 0x1A4 (frame count): unchanged -- total frames across all chunks
      - All other fields: identical to non-split header

    Data layout within the stream (same as non-split):
      header | all fill frames | all key frames
      (audio is not supported in split files)
    """
    CHUNK_SIZE = 2 * 1024 * 1024 * 1024  # exactly 2GB per chunk

    os.makedirs(dest_folder, exist_ok=True)

    # Calculate total data size so we know the final chunk size in advance.
    # Audio is excluded from split files.
    fill_size = os.path.getsize(fill_raw)
    key_size  = os.path.getsize(key_raw) if key_raw else 0
    total_data = SWS_HEADER_SIZE + fill_size + key_size

    # Number of chunks
    n_chunks = (total_data + CHUNK_SIZE - 1) // CHUNK_SIZE

    # Final chunk size = total minus all full preceding chunks
    full_chunks_size = (n_chunks - 1) * CHUNK_SIZE
    final_chunk_size = total_data - full_chunks_size

    # Build patched header for split files:
    #   0x1A8 = 0  (play count zeroed)
    #   0x1B4 = 0  (zeroed)
    #   0x1CC = final chunk size (not total file size)
    hdr = bytearray(header)
    struct.pack_into('>I', hdr, 0x1A8, 0)
    struct.pack_into('>I', hdr, 0x1B4, 0)
    struct.pack_into('>I', hdr, 0x1CC, final_chunk_size)
    hdr = bytes(hdr)

    log(f"  Split: {n_chunks} chunks  ({total_data:,} bytes total, "
        f"final chunk {final_chunk_size:,} bytes)")

    # Stream data source: header, then all fill frames, then all key frames.
    # Never held entirely in memory -- written chunk by chunk to disk.
    def data_source():
        yield hdr
        with open(fill_raw, 'rb') as f:
            while block := f.read(1024 * 1024):
                yield block
        if key_raw:
            with open(key_raw, 'rb') as f:
                while block := f.read(1024 * 1024):
                    yield block

    chunk_idx  = 0
    bytes_in_chunk = 0
    out_fh     = None
    buf        = b''

    def open_next_chunk():
        nonlocal chunk_idx, bytes_in_chunk, out_fh
        if out_fh:
            out_fh.close()
        chunk_idx += 1
        name = f"{chunk_idx:02d}_OF_{n_chunks:02d}._XX"
        path = os.path.join(dest_folder, name)
        out_fh = open(path, 'wb')
        bytes_in_chunk = 0
        return path

    current_path = open_next_chunk()

    for block in data_source():
        buf += block
        while buf:
            space = CHUNK_SIZE - bytes_in_chunk
            to_write = buf[:space]
            out_fh.write(to_write)
            bytes_in_chunk += len(to_write)
            buf = buf[len(to_write):]

            if bytes_in_chunk == CHUNK_SIZE and chunk_idx < n_chunks:
                log(f"  Written chunk {chunk_idx:02d}: {current_path}  ({bytes_in_chunk:,} bytes)")
                current_path = open_next_chunk()

    if out_fh:
        out_fh.close()
        log(f"  Written chunk {chunk_idx:02d}: {current_path}  ({bytes_in_chunk:,} bytes)")


# ─────────────────────────────────────────────────────────────
#  High-level converters
# ─────────────────────────────────────────────────────────────

def convert_still(input_path: str, file_number: int, dest_dir: str,
                  video_standard: str = '1080i50',
                  split_fat32: bool = True,
                  delete_source: bool = False,
                  log=print,
                  ignore_alpha: bool = False,
                  auto_play: bool = False,
                  loop_play: bool = False):
    """Convert a single TGA/PNG/BMP/JPG still to .SWS."""

    log(f"Converting still: {os.path.basename(input_path)}")
    info = get_video_info(input_path)
    w, h = info['width'], info['height']
    _interlaced_standards = {'1080i50', '1080i5994', '1080i60'}
    if video_standard in _interlaced_standards and not info['is_interlaced']:
        log(f"  WARNING: Source is progressive but {video_standard} is an interlaced standard.")
        log(f"  The header will be correct but the video data will remain progressive.")
        log(f"  On the Kahuna this will play back at double speed.")
        log(f"  For correct interlaced output, use a native interlaced source or convert via K-Watch.")

    with tempfile.TemporaryDirectory() as tmp:
        fill_raw = os.path.join(tmp, 'fill.v210')
        key_raw  = None

        has_alpha = info['has_alpha'] and not ignore_alpha
        log(f"  Size: {w}x{h}, has_alpha={info['has_alpha']}{' (ignored)' if ignore_alpha and info['has_alpha'] else ''}")
        key_raw = convert_to_v210(input_path, fill_raw, extract_alpha=has_alpha)
        if ignore_alpha:
            # No key plane written at all -- matches K-Watch behaviour
            actual_key = None
        elif key_raw is None:
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
            has_key=(actual_key is not None),
            auto_play=auto_play,
            loop_play=loop_play,
        )

        dest_path = os.path.join(dest_dir, f"{file_number}.SWS")
        write_sws(dest_path, fill_raw, actual_key, hdr, split_fat32, frame_count=1, log=log)

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
                 include_audio: bool = True,
                 auto_play: bool = False,
                 loop_play: bool = False):
    """Convert a MOV/MP4/AVI/etc video clip to .SWS."""

    log(f"Converting clip: {os.path.basename(input_path)}")
    info = get_video_info(input_path)
    w, h, fps = info['width'], info['height'], info['fps']
    frame_count = info['frame_count']
    _interlaced_standards = {'1080i50', '1080i5994', '1080i60'}
    if video_standard in _interlaced_standards and not info['is_interlaced']:
        log(f"  WARNING: Source is progressive but {video_standard} is an interlaced standard.")
        log(f"  The header will be correct but the video data will remain progressive.")
        log(f"  On the Kahuna this will play back at double speed.")
        log(f"  For correct interlaced output, use a native interlaced source or convert via K-Watch.")

    has_alpha = info['has_alpha'] and not ignore_alpha
    will_include_audio = include_audio and info['has_audio']
    log(f"  Size: {w}x{h}  FPS: {fps:.2f}  Frames: {frame_count}  has_alpha={info['has_alpha']}{' (ignored)' if ignore_alpha and info['has_alpha'] else ''}  audio={info['has_audio']}{' (included)' if will_include_audio else ' (excluded)' if info['has_audio'] else ''}")

    with tempfile.TemporaryDirectory() as tmp:
        fill_raw   = os.path.join(tmp, 'fill.v210')
        actual_key = None
        audio_raw  = None

        key_raw = convert_to_v210(input_path, fill_raw, extract_alpha=has_alpha)
        if ignore_alpha:
            # No key plane written at all -- matches K-Watch behaviour
            actual_key = None
        elif key_raw:
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
            has_key=(actual_key is not None),
            auto_play=auto_play,
            loop_play=loop_play,
        )

        dest_path = os.path.join(dest_dir, f"{file_number}.SWS")
        write_sws(dest_path, fill_raw, actual_key, hdr, split_fat32,
                  frame_count=frame_count, audio_raw=audio_raw, log=log)

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
                         ignore_alpha: bool = False,
                         auto_play: bool = False,
                         loop_play: bool = False):
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
        _run_ffmpeg(cmd, check=True)

        # Key/alpha
        actual_key = None
        if ignore_alpha:
            # No key plane written at all -- matches K-Watch behaviour
            actual_key = None
        elif has_alpha:
            key_raw = os.path.join(tmp, 'key.v210')
            cmd_key = [ffmpeg, '-y', '-f', 'concat', '-safe', '0',
                       '-i', concat_file,
                       '-frames:v', str(frame_count),
                       '-vf', 'alphaextract,format=yuv420p,colorspace=bt709,scale=out_range=tv',
                       '-f', 'rawvideo', '-vcodec', 'v210', key_raw]
            result = _run_ffmpeg(cmd_key)
            if result.returncode != 0 or not os.path.exists(key_raw) or os.path.getsize(key_raw) == 0:
                cmd_key = [ffmpeg, '-y', '-f', 'concat', '-safe', '0',
                           '-i', concat_file,
                           '-frames:v', str(frame_count),
                           '-vf', 'alphaextract',
                           '-f', 'rawvideo', '-vcodec', 'v210', key_raw]
                _run_ffmpeg(cmd_key, check=True)
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
            has_key=(actual_key is not None),
            auto_play=auto_play,
            loop_play=loop_play,
        )

        dest_path = os.path.join(dest_dir, f"{file_number}.SWS")
        write_sws(dest_path, fill_raw, actual_key, hdr, split_fat32, frame_count=frame_count, log=log)

    if delete_source:
        for f in tga_files:
            os.remove(f)

    log(f"  Done → {dest_path}")

    # Write conversion log to destination folder
    # Sequence identifier = everything before the first underscore in the first TGA filename
    first_name = Path(tga_files[0]).stem
    seq_id = first_name.split('_')[0] if '_' in first_name else first_name
    date_str = datetime.now().strftime('%d-%m-%Y')
    log_filename = f"MacHuna_Log_{file_number}_{seq_id}_{date_str}.txt"
    log_path = os.path.join(dest_dir, log_filename)
    try:
        with open(log_path, 'w') as lf:
            lf.write(f"MacHuna Conversion Log\n")
            lf.write(f"{'=' * 40}\n")
            lf.write(f"Date: {datetime.now().strftime('%d %b %Y')}\n")
            lf.write(f"Standard: {video_standard}\n")
            lf.write(f"{'=' * 40}\n\n")
            lf.write(f"{file_number:4d}  {seq_id}  [OK]\n")
        log(f"  Conversion log saved: {log_filename}")
    except Exception as e:
        log(f"  Could not write log file: {e}")

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
                 auto_play: bool = False,
                 loop_play: bool = False,
                 log=print):
        self.watch_dir      = watch_dir
        self.dest_dir       = dest_dir
        self.video_standard = video_standard
        self.split_fat32    = split_fat32
        self.delete_source  = delete_source
        self.ignore_alpha   = ignore_alpha
        self.include_audio  = include_audio
        self.auto_play      = auto_play
        self.loop_play      = loop_play
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
                                 include_audio=self.include_audio,
                                 auto_play=self.auto_play,
                                 loop_play=self.loop_play)

                elif meta['type'] == 'still' and meta['is_fill']:
                    convert_still(fpath, meta['file_num'], self.dest_dir,
                                  self.video_standard, self.split_fat32,
                                  self.delete_source, self.log,
                                  ignore_alpha=self.ignore_alpha,
                                  auto_play=self.auto_play,
                                  loop_play=self.loop_play)

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
                                 ignore_alpha=self.ignore_alpha,
                                 auto_play=self.auto_play,
                                 loop_play=self.loop_play)

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
#  SWS Preview Player
#  Integrated from SWSPlayer companion app (DNSVision/SWSPlayer).
#  Launched as a tk.Toplevel child window from the MacHuna GUI.
# ─────────────────────────────────────────────────────────────

try:
    import sounddevice as sd
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False

import numpy as np
from PIL import Image, ImageTk

# Header field offsets (player read side -- matches build_sws_header write side)
OFF_MAGIC       = 0x000
OFF_STD_CODE    = 0x188
OFF_FMT_VARIANT = 0x18C
OFF_WIDTH       = 0x190
OFF_HEIGHT   = 0x194
OFF_PLANE_SZ = 0x1A0
OFF_FRAMES   = 0x1A4
OFF_PLAY_CNT = 0x1A8
OFF_AUD_FSZ  = 0x1C2
OFF_AUD_OFF  = 0x1E8
OFF_AUD_FMT  = 0x1EC

# FPS lookup from video standard code (flag bits stripped before lookup)
STD_CODE_FPS = {
    0x4923: 50.0,
    0x4921: 59.94,
    0x4925: 25.0,
    0x4813: 50.0,
    0x4814: 59.94,
    0x4817: 50.0,
    0x4816: 59.94,
}

# Panel display size for quad layout
PANEL_W = 480
PANEL_H = 270


class SWSHeader:
    """Parsed SWS file header (player read side)."""

    def __init__(self, path: str):
        with open(path, 'rb') as f:
            raw = f.read(SWS_HEADER_SIZE)
        if len(raw) < SWS_HEADER_SIZE:
            raise ValueError("File too small to be a valid SWS file.")
        magic = raw[OFF_MAGIC:OFF_MAGIC + 16]
        if magic != SWS_MAGIC:
            raise ValueError(f"Not a valid SWS file (bad magic: {magic!r})")

        self.std_code    = struct.unpack_from('>I', raw, OFF_STD_CODE)[0]
        self.width       = struct.unpack_from('>I', raw, OFF_WIDTH)[0]
        self.height      = struct.unpack_from('>I', raw, OFF_HEIGHT)[0]
        self.plane_size  = struct.unpack_from('>I', raw, OFF_PLANE_SZ)[0]
        self.frame_count = struct.unpack_from('>I', raw, OFF_FRAMES)[0]
        self.play_count  = struct.unpack_from('>I', raw, OFF_PLAY_CNT)[0]
        self.has_key     = (self.play_count > 0)

        aud_frame_size   = struct.unpack_from('>H', raw, OFF_AUD_FSZ)[0]
        aud_offset_div32 = struct.unpack_from('>I', raw, OFF_AUD_OFF)[0]
        aud_fmt          = struct.unpack_from('>I', raw, OFF_AUD_FMT)[0]

        # Use audio offset and format flag to detect audio -- more robust than
        # checking aud_frame_size == 0x1680, which varies between workflows.
        self.has_audio    = (aud_offset_div32 > 0 and aud_fmt == 0x03000000)
        self.audio_offset = aud_offset_div32 * 32 if self.has_audio else 0
        fmt_variant       = struct.unpack_from('>I', raw, OFF_FMT_VARIANT)[0]
        self.fps          = self._get_fps(self.std_code, fmt_variant)
        self.auto_play    = bool(self.std_code & 0x04)
        self.loop_play    = bool(self.std_code & 0x08)

    @staticmethod
    def _get_fps(std_code: int, fmt_variant: int = 0) -> float:
        if fmt_variant in FORMAT_VARIANT_FPS:
            return FORMAT_VARIANT_FPS[fmt_variant]
        # Fallback for third-party files with unrecognised format variant
        low16 = std_code & 0xFFFF
        if low16 in STD_CODE_FPS:
            return STD_CODE_FPS[low16]
        for mask in [~0x04 & 0xFFFF, ~0x08 & 0xFFFF, ~0x0C & 0xFFFF]:
            candidate = low16 & mask
            if candidate in STD_CODE_FPS:
                return STD_CODE_FPS[candidate]
        return 25.0


def _v210_plane_to_yuv(raw_be: bytes, width: int, height: int,
                       frame_count: int) -> np.ndarray:
    """Decode big-endian v210 plane to float32 YCbCr (frame_count, H, W, 3).
    Pure numpy -- ffmpeg 7.x has a bug decoding v210 from raw files."""
    words = np.frombuffer(raw_be, dtype='>u4').copy()
    words.byteswap(inplace=True)
    words = words.view('<u4')

    padded_w         = ((width + 47) // 48) * 48
    line_bytes       = padded_w * 8 // 3
    line_pad         = ((line_bytes + 127) // 128) * 128
    total_line_words = line_pad // 4
    active_words     = line_bytes // 4
    frame_words      = total_line_words * height

    results = np.zeros((frame_count, height, width, 3), dtype=np.float32)

    for f in range(frame_count):
        frame = words[f * frame_words: (f + 1) * frame_words]
        frame = frame.reshape(height, total_line_words)[:, :active_words]
        groups_per_line = active_words // 4
        frame = frame[:, :groups_per_line * 4].reshape(height, groups_per_line, 4)

        w0, w1, w2, w3 = frame[:,:,0], frame[:,:,1], frame[:,:,2], frame[:,:,3]

        cb0 = ((w0 >>  0) & 0x3FF).astype(np.float32)
        y0  = ((w0 >> 10) & 0x3FF).astype(np.float32)
        cr0 = ((w0 >> 20) & 0x3FF).astype(np.float32)
        y1  = ((w1 >>  0) & 0x3FF).astype(np.float32)
        cb2 = ((w1 >> 10) & 0x3FF).astype(np.float32)
        y2  = ((w1 >> 20) & 0x3FF).astype(np.float32)
        cr2 = ((w2 >>  0) & 0x3FF).astype(np.float32)
        y3  = ((w2 >> 10) & 0x3FF).astype(np.float32)
        cb4 = ((w2 >> 20) & 0x3FF).astype(np.float32)
        y4  = ((w3 >>  0) & 0x3FF).astype(np.float32)
        cr4 = ((w3 >> 10) & 0x3FF).astype(np.float32)
        y5  = ((w3 >> 20) & 0x3FF).astype(np.float32)

        n   = groups_per_line
        yuv = np.zeros((height, n * 6, 3), dtype=np.float32)
        yuv[:, 0::6, 0] = y0;  yuv[:, 0::6, 1] = cb0; yuv[:, 0::6, 2] = cr0
        yuv[:, 1::6, 0] = y1;  yuv[:, 1::6, 1] = cb0; yuv[:, 1::6, 2] = cr0
        yuv[:, 2::6, 0] = y2;  yuv[:, 2::6, 1] = cb2; yuv[:, 2::6, 2] = cr2
        yuv[:, 3::6, 0] = y3;  yuv[:, 3::6, 1] = cb2; yuv[:, 3::6, 2] = cr2
        yuv[:, 4::6, 0] = y4;  yuv[:, 4::6, 1] = cb4; yuv[:, 4::6, 2] = cr4
        yuv[:, 5::6, 0] = y5;  yuv[:, 5::6, 1] = cb4; yuv[:, 5::6, 2] = cr4

        results[f] = yuv[:, :width, :]

    return results


def _yuv_to_rgb8(yuv: np.ndarray) -> np.ndarray:
    """BT.709 limited-range YCbCr (10-bit float) -> RGB uint8."""
    yn  = (yuv[:,:,0] -  64.0) / (940.0 -  64.0)
    cbn = (yuv[:,:,1] - 512.0) / (960.0 -  64.0)
    crn = (yuv[:,:,2] - 512.0) / (960.0 -  64.0)
    r = yn + 1.5748 * crn
    g = yn - 0.1873 * cbn - 0.4681 * crn
    b = yn + 1.8556 * cbn
    return np.clip(np.stack([r, g, b], axis=-1) * 255.0, 0, 255).astype(np.uint8)


def _yuv_to_gray8(yuv: np.ndarray) -> np.ndarray:
    """Y channel (10-bit float) -> grayscale uint8."""
    return np.clip((yuv[:,:,0] - 64.0) / (940.0 - 64.0) * 255.0, 0, 255).astype(np.uint8)


def _player_decode_rgb(raw_be: bytes, width: int, height: int, frame_count: int) -> list:
    """Decode BE v210 plane to list of RGB PIL Images at PANEL_W x PANEL_H."""
    yuv = _v210_plane_to_yuv(raw_be, width, height, frame_count)
    images = []
    for f in range(frame_count):
        img = Image.fromarray(_yuv_to_rgb8(yuv[f]), 'RGB')
        images.append(img.resize((PANEL_W, PANEL_H), Image.BILINEAR))
    return images


def _player_decode_gray(raw_be: bytes, width: int, height: int, frame_count: int) -> list:
    """Decode BE v210 plane to list of grayscale arrays at PANEL_W x PANEL_H."""
    yuv = _v210_plane_to_yuv(raw_be, width, height, frame_count)
    arrays = []
    for f in range(frame_count):
        img = Image.fromarray(_yuv_to_gray8(yuv[f]), 'L')
        arrays.append(np.array(img.resize((PANEL_W, PANEL_H), Image.BILINEAR)))
    return arrays


_CHECKER = None

def _get_chequerboard(h: int, w: int, square: int = 16) -> np.ndarray:
    """Return a chequerboard RGB array (H, W, 3)."""
    global _CHECKER
    if _CHECKER is not None and _CHECKER.shape[:2] == (h, w):
        return _CHECKER
    tile = np.zeros((square * 2, square * 2, 3), dtype=np.uint8)
    tile[:square, :square] = 180
    tile[square:, square:] = 180
    tile[:square, square:] = 100
    tile[square:, :square] = 100
    reps_h = (h + tile.shape[0] - 1) // tile.shape[0]
    reps_w = (w + tile.shape[1] - 1) // tile.shape[1]
    checker = np.tile(tile, (reps_h, reps_w, 1))[:h, :w]
    _CHECKER = checker
    return _CHECKER


def _make_composite(fill_rgb: np.ndarray, key_gray: np.ndarray) -> np.ndarray:
    """Composite fill over chequerboard using key as alpha mask."""
    h, w = fill_rgb.shape[:2]
    checker = _get_chequerboard(h, w)
    alpha = key_gray.astype(np.float32) / 255.0
    alpha = alpha[:, :, np.newaxis]
    composite = (fill_rgb.astype(np.float32) * alpha +
                 checker.astype(np.float32) * (1.0 - alpha))
    return composite.astype(np.uint8)


class PlayerFrameCache:
    """Loads and decodes all frames from an SWS file into memory."""

    def __init__(self, path: str, header: SWSHeader, progress_cb=None):
        self.path      = path
        self.header    = header
        self.frames    = []       # list of [fill_img, key_img, composite_img] PIL Images
        self.audio_pcm = None     # raw bytes: 16ch 16-bit LE 48kHz
        self.cancelled = False
        self._load(progress_cb)

    def _load(self, progress_cb):
        h = self.header
        file_size = os.path.getsize(self.path)

        with open(self.path, 'rb') as f:
            if progress_cb:
                progress_cb(5, "Reading fill plane...")
            f.seek(SWS_HEADER_SIZE)
            fill_plane_bytes = h.plane_size * h.frame_count
            fill_raw = f.read(fill_plane_bytes)

            if progress_cb:
                progress_cb(15, "Decoding fill plane...")
            fill_images = _player_decode_rgb(fill_raw, h.width, h.height, h.frame_count)
            del fill_raw

            self.frames = [[img, None, None] for img in fill_images]

            if h.has_key and not self.cancelled:
                if progress_cb:
                    progress_cb(50, "Reading key plane...")
                f.seek(SWS_HEADER_SIZE + fill_plane_bytes)
                key_raw = f.read(fill_plane_bytes)

                if progress_cb:
                    progress_cb(60, "Decoding key plane...")
                key_arrays = _player_decode_gray(key_raw, h.width, h.height, h.frame_count)
                del key_raw

                if progress_cb:
                    progress_cb(75, "Building composites...")
                for i, (frame_data, key_gray) in enumerate(zip(self.frames, key_arrays)):
                    if self.cancelled:
                        break
                    key_img  = Image.fromarray(key_gray, 'L')
                    comp_rgb = _make_composite(np.array(frame_data[0]), key_gray)
                    comp_img = Image.fromarray(comp_rgb, 'RGB')
                    frame_data[1] = key_img
                    frame_data[2] = comp_img
            else:
                for frame_data in self.frames:
                    frame_data[2] = frame_data[0]

            if h.has_audio and not self.cancelled:
                if progress_cb:
                    progress_cb(90, "Loading audio...")
                audio_len = file_size - h.audio_offset
                if audio_len > 0:
                    f.seek(h.audio_offset)
                    self.audio_pcm = f.read(audio_len)

        if progress_cb:
            progress_cb(100, "Ready.")


class PlayerAudio:
    """Plays 16-bit LE PCM audio (16ch, 48kHz) via sounddevice. L=ch0, R=ch2."""

    def __init__(self, pcm_bytes: bytes, fps: float, frame_count: int):
        self.pcm_bytes   = pcm_bytes
        self.fps         = fps
        self.frame_count = frame_count
        self._stream     = None
        self._thread     = None
        self._stop_event = threading.Event()
        self._pos        = 0

    def start(self, frame_index: int = 0):
        self.stop()
        samples_per_frame = round(48000 / self.fps)
        bytes_per_frame   = samples_per_frame * 2 * 16
        self._pos         = frame_index * bytes_per_frame
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._play, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _play(self):
        if not HAS_AUDIO:
            return
        try:
            pcm_slice = self.pcm_bytes[self._pos:]
            if not pcm_slice:
                return
            samples = np.frombuffer(pcm_slice, dtype='<i2')
            total_samples = len(samples) // 16
            if total_samples == 0:
                return
            samples = samples[:total_samples * 16].reshape(-1, 16)
            stereo = np.zeros((total_samples, 2), dtype=np.float32)
            stereo[:, 0] = samples[:, 0].astype(np.float32) / 32768.0
            stereo[:, 1] = samples[:, 2].astype(np.float32) / 32768.0

            self._stream = None
            time.sleep(0.05)
            self._stream = sd.OutputStream(samplerate=48000, channels=2, dtype='float32')
            self._stream.start()

            chunk_size = 4800
            pos = 0
            while pos < len(stereo) and not self._stop_event.is_set():
                self._stream.write(stereo[pos:pos + chunk_size])
                pos += chunk_size
        except Exception as e:
            print(f"Audio playback error: {e}")
        finally:
            try:
                if self._stream:
                    self._stream.stop()
                    self._stream.close()
            except Exception:
                pass


def _player_compute_rms(pcm_bytes: bytes, frame_idx: int, fps: float) -> tuple:
    """Return (left_db, right_db) RMS levels for the given frame."""
    samples_per_frame = round(48000 / fps)
    bytes_per_frame   = samples_per_frame * 2 * 16
    start             = frame_idx * bytes_per_frame
    if start >= len(pcm_bytes):
        return (-80.0, -80.0)
    chunk = np.frombuffer(pcm_bytes[start:start + bytes_per_frame], dtype='<i2')
    total = len(chunk) // 16
    if total == 0:
        return (-80.0, -80.0)
    chunk = chunk[:total * 16].reshape(-1, 16)
    left  = chunk[:, 0].astype(np.float32) / 32768.0
    right = chunk[:, 2].astype(np.float32) / 32768.0
    rms_l = np.sqrt(np.mean(left  ** 2)) if len(left)  else 0.0
    rms_r = np.sqrt(np.mean(right ** 2)) if len(right) else 0.0
    db_l  = 20 * np.log10(rms_l) if rms_l > 0 else -80.0
    db_r  = 20 * np.log10(rms_r) if rms_r > 0 else -80.0
    return (max(-80.0, db_l), max(-80.0, db_r))


class SWSPlayer(tk.Toplevel):
    """SWS Preview Player window -- launched from MacHuna as a non-modal Toplevel."""

    def __init__(self, parent, initial_dir: str = ''):
        super().__init__(parent)
        self.title("SWS Preview Player")
        self.resizable(False, False)
        self._initial_dir = initial_dir

        self._cache: Optional[PlayerFrameCache] = None
        self._current_frame = 0
        self._playing = False
        self._play_thread = None
        self._stop_event = threading.Event()
        self._audio_player: Optional[PlayerAudio] = None
        self._tk_images = {}
        self._photo_fill = []
        self._photo_key  = []
        self._photo_comp = []

        self._build_ui()

        # Centre over parent window
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        py = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        pad = 4

        # Info strip
        info_frame = tk.Frame(self)
        info_frame.pack(fill='x', padx=pad, pady=(pad, 0))
        self._info_var = tk.StringVar(value="No file loaded")
        tk.Label(info_frame, textvariable=self._info_var,
                 font=('Helvetica', 11)).pack(side='left')

        # Quad panel grid
        quad = tk.Frame(self)
        quad.pack(padx=pad, pady=pad)

        label_cfg  = dict(font=('Helvetica', 10), anchor='w')
        canvas_cfg = dict(width=PANEL_W, height=PANEL_H,
                          bg='#888888', highlightthickness=1,
                          highlightbackground='#cccccc')

        fill_col = tk.Frame(quad)
        fill_col.grid(row=0, column=0, padx=(0, pad//2), pady=(0, pad//2))
        tk.Label(fill_col, text="Fill", **label_cfg).pack(fill='x')
        self._fill_canvas = tk.Canvas(fill_col, **canvas_cfg)
        self._fill_canvas.pack()
        self._fill_item = self._fill_canvas.create_image(0, 0, anchor='nw')

        key_col = tk.Frame(quad)
        key_col.grid(row=0, column=1, padx=(pad//2, 0), pady=(0, pad//2))
        tk.Label(key_col, text="Key", **label_cfg).pack(fill='x')
        self._key_canvas = tk.Canvas(key_col, **canvas_cfg)
        self._key_canvas.pack()
        self._key_item = self._key_canvas.create_image(0, 0, anchor='nw')

        comp_col = tk.Frame(quad)
        comp_col.grid(row=1, column=0, padx=(0, pad//2), pady=(pad//2, 0))
        tk.Label(comp_col, text="Composite", **label_cfg).pack(fill='x')
        self._comp_canvas = tk.Canvas(comp_col, **canvas_cfg)
        self._comp_canvas.pack()
        self._comp_item = self._comp_canvas.create_image(0, 0, anchor='nw')

        meter_col = tk.Frame(quad)
        meter_col.grid(row=1, column=1, padx=(pad//2, 0), pady=(pad//2, 0))
        tk.Label(meter_col, text="Audio", **label_cfg).pack(fill='x')
        self._meter_canvas = tk.Canvas(meter_col, **canvas_cfg)
        self._meter_canvas.pack()
        self._draw_meters(-80.0, -80.0)

        # Transport controls
        transport = tk.Frame(self)
        transport.pack(pady=(0, pad))

        self._cue_btn   = ttk.Button(transport, text="⏮  Cue",   command=self._on_cue)
        self._play_btn  = ttk.Button(transport, text="▶  Play",  command=self._on_play)
        self._pause_btn = ttk.Button(transport, text="⏸  Pause", command=self._on_pause)
        self._stop_btn  = ttk.Button(transport, text="⏹  Stop",  command=self._on_stop)

        self._cue_btn.pack(side='left', padx=4)
        self._play_btn.pack(side='left', padx=4)
        self._pause_btn.pack(side='left', padx=4)
        self._stop_btn.pack(side='left', padx=4)

        self._frame_var = tk.StringVar(value="Frame: --/--")
        tk.Label(transport, textvariable=self._frame_var,
                 font=('Helvetica', 11)).pack(side='left', padx=12)

        ttk.Button(transport, text="Open SWS...",
                   command=self._open_file).pack(side='right', padx=4)

        # Status / progress
        status_frame = tk.Frame(self)
        status_frame.pack(fill='x', padx=pad, pady=(0, pad))
        self._status_var = tk.StringVar(value="Open a .SWS file to begin.")
        tk.Label(status_frame, textvariable=self._status_var,
                 font=('Helvetica', 10), anchor='w').pack(side='left', fill='x', expand=True)
        self._progress = ttk.Progressbar(status_frame, length=200, mode='determinate')
        self._progress.pack(side='right', padx=(8, 0))

    # ── File open ────────────────────────────────────────────

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="Open SWS File",
            initialdir=self._initial_dir if self._initial_dir else None,
            filetypes=[("Grass Valley SWS", "*.SWS *.sws"), ("All files", "*.*")]
        )
        if not path:
            return
        self._load_file(path)

    def _load_file(self, path: str):
        self._on_stop()
        self._photo_fill = []
        self._photo_key  = []
        self._photo_comp = []
        self._fill_canvas.itemconfigure(self._fill_item, image='')
        self._key_canvas.itemconfigure(self._key_item, image='')
        self._key_canvas.delete('nokey')
        self._comp_canvas.itemconfigure(self._comp_item, image='')
        self._draw_meters(-80.0, -80.0)
        self._frame_var.set("Frame: --/--")

        try:
            header = SWSHeader(path)
        except Exception as e:
            messagebox.showerror("Invalid File", str(e), parent=self)
            return

        self.title(f"SWS Preview Player — {Path(path).name}")
        flags = []
        if header.auto_play:  flags.append("Auto Play")
        if header.loop_play:  flags.append("Loop Play")
        flags_str = f"  [{', '.join(flags)}]" if flags else ""
        self._info_var.set(
            f"{header.width}×{header.height}  {header.fps:.2f}fps  "
            f"{header.frame_count} frames  "
            f"Key: {'Yes' if header.has_key else 'No'}  "
            f"Audio: {'Yes' if header.has_audio else 'No'}"
            f"{flags_str}"
        )
        self._status_var.set("Loading frames...")
        self._progress['value'] = 0

        if not header.has_key:
            self._key_canvas.create_text(
                PANEL_W // 2, PANEL_H // 2,
                text="No key plane", fill='#555555',
                font=('Helvetica', 14), tags='nokey'
            )

        self.update()

        def load():
            def progress(pct, msg):
                self.after(0, lambda: self._on_progress(pct, msg))
            try:
                cache = PlayerFrameCache(path, header, progress_cb=progress)
                self.after(0, lambda: self._on_load_complete(cache, header))
            except Exception as e:
                import traceback; traceback.print_exc()
                msg = str(e)
                self.after(0, lambda m=msg: self._on_load_error(m))

        threading.Thread(target=load, daemon=True).start()

    def _on_progress(self, pct: int, msg: str):
        self._progress['value'] = pct
        self._status_var.set(msg)
        self.update_idletasks()

    def _on_load_complete(self, cache: PlayerFrameCache, header: SWSHeader):
        self._cache = cache
        self._current_frame = 0
        self._progress['value'] = 100
        n = len(cache.frames)

        self._status_var.set("Converting frames for display...")
        self.update_idletasks()

        self._photo_fill = []
        self._photo_key  = []
        self._photo_comp = []
        for fill_img, key_img, comp_img in cache.frames:
            self._photo_fill.append(ImageTk.PhotoImage(fill_img))
            self._photo_key.append(ImageTk.PhotoImage(key_img) if key_img else None)
            self._photo_comp.append(ImageTk.PhotoImage(comp_img) if comp_img else None)

        has_audio_str = "with audio" if cache.audio_pcm else "no audio"
        self._status_var.set(
            f"Loaded {n} frame{'s' if n != 1 else ''}  {has_audio_str}  "
            f"({os.path.getsize(self._cache.path) / 1024 / 1024:.1f} MB)"
        )
        self._show_frame(0)

        if not HAS_AUDIO and header.has_audio:
            self._status_var.set(
                self._status_var.get() +
                "  [sounddevice not installed -- audio meters only]"
            )

    def _on_load_error(self, msg: str):
        self._status_var.set(f"Error: {msg}")
        messagebox.showerror("Load Error", msg, parent=self)

    # ── Frame display ─────────────────────────────────────────

    def _show_frame(self, idx: int):
        if not self._cache or not self._photo_fill or idx >= len(self._photo_fill):
            return

        photo = self._photo_fill[idx]
        self._tk_images['fill'] = photo
        self._fill_canvas.itemconfigure(self._fill_item, image=photo)

        key_photo = self._photo_key[idx] if self._photo_key else None
        if key_photo:
            self._key_canvas.delete('nokey')
            self._tk_images['key'] = key_photo
            self._key_canvas.itemconfigure(self._key_item, image=key_photo)
        else:
            self._key_canvas.itemconfigure(self._key_item, image='')
            self._key_canvas.delete('nokey')
            self._key_canvas.create_text(
                PANEL_W // 2, PANEL_H // 2,
                text="No key plane", fill='#555555',
                font=('Helvetica', 14), tags='nokey'
            )

        comp_photo = self._photo_comp[idx] if self._photo_comp else None
        if comp_photo:
            self._tk_images['comp'] = comp_photo
            self._comp_canvas.itemconfigure(self._comp_item, image=comp_photo)

        if self._cache.audio_pcm:
            l_db, r_db = _player_compute_rms(
                self._cache.audio_pcm, idx, self._cache.header.fps
            )
            self._draw_meters(l_db, r_db)
        else:
            self._draw_meters(None, None)

        self._frame_var.set(f"Frame: {idx + 1}/{len(self._cache.frames)}")
        self._current_frame = idx

    # ── Audio meters ──────────────────────────────────────────

    def _draw_meters(self, l_db, r_db):
        c = self._meter_canvas
        c.delete('all')
        w, h = PANEL_W, PANEL_H
        c.create_rectangle(0, 0, w, h, fill='#111111', outline='')

        if l_db is None:
            c.create_text(w // 2, h // 2,
                          text="No audio", fill='#999999', font=('Helvetica', 14))
            return

        bar_w = 60; gap = 40
        x_l = (w - bar_w * 2 - gap) // 2
        x_r = x_l + bar_w + gap
        top = 30; bottom = h - 40
        bar_h = bottom - top
        db_min = -60.0; db_max = 0.0

        def db_to_y(db):
            clamped = max(db_min, min(db_max, db))
            return bottom - int((clamped - db_min) / (db_max - db_min) * bar_h)

        def bar_colour(db):
            if db > -6:   return '#ff4444'
            if db > -18:  return '#ffcc00'
            return '#44cc44'

        for db, x in [(l_db, x_l), (r_db, x_r)]:
            c.create_rectangle(x, top, x + bar_w, bottom, fill='#222222', outline='')
            y = db_to_y(db)
            if y < bottom:
                c.create_rectangle(x, y, x + bar_w, bottom,
                                   fill=bar_colour(db), outline='')
            for mark_db in [-60, -48, -36, -24, -18, -12, -6, 0]:
                my = db_to_y(float(mark_db))
                c.create_line(x, my, x + bar_w, my, fill='#444444', width=1)
                c.create_text(x - 4, my, text=str(mark_db),
                              fill='#666666', font=('Helvetica', 8), anchor='e')

        c.create_text(x_l + bar_w // 2, bottom + 14, text="L",
                      fill='#888888', font=('Helvetica', 11))
        c.create_text(x_r + bar_w // 2, bottom + 14, text="R",
                      fill='#888888', font=('Helvetica', 11))
        c.create_text(w // 2, 14, text="Audio Levels (dBFS)",
                      fill='#666666', font=('Helvetica', 10))

    # ── Transport ─────────────────────────────────────────────

    def _on_cue(self):
        self._on_stop()

    def _on_play(self):
        if not self._cache or self._playing:
            return
        self._playing = True
        self._stop_event.clear()
        if self._cache.audio_pcm and HAS_AUDIO:
            self._audio_player = PlayerAudio(
                self._cache.audio_pcm,
                self._cache.header.fps,
                len(self._cache.frames)
            )
            self._audio_player.start(self._current_frame)
        self._play_thread = threading.Thread(
            target=self._playback_loop, daemon=True
        )
        self._play_thread.start()

    def _on_pause(self):
        if not self._playing:
            return
        self._playing = False
        self._stop_event.set()
        if self._audio_player:
            self._audio_player.stop()

    def _on_stop(self):
        self._playing = False
        self._stop_event.set()
        if self._audio_player:
            self._audio_player.stop()
            self._audio_player = None
        self._current_frame = 0
        if self._cache:
            self.after(0, lambda: self._show_frame(0))

    def _playback_loop(self):
        if not self._cache:
            return
        fps       = self._cache.header.fps
        frame_dur = 1.0 / fps
        n_frames  = len(self._cache.frames)
        idx       = self._current_frame
        loop      = self._cache.header.loop_play

        # Use absolute origin time so sleep overshoot in one frame is
        # automatically recovered in the next, preventing drift accumulation.
        t_origin  = time.perf_counter()
        frame_num = 0

        while not self._stop_event.is_set():
            captured = idx
            self.after(0, lambda i=captured: self._show_frame(i))
            idx += 1
            frame_num += 1
            if idx >= n_frames:
                if loop:
                    idx = 0
                    t_origin  = time.perf_counter()
                    frame_num = 0
                    if self._audio_player:
                        self._audio_player.stop()
                        self._audio_player = PlayerAudio(
                            self._cache.audio_pcm,
                            self._cache.header.fps,
                            n_frames
                        )
                        self._audio_player.start(0)
                else:
                    self._playing = False
                    self.after(0, self._on_playback_ended)
                    return
            sleep = (t_origin + frame_num * frame_dur) - time.perf_counter()
            if sleep > 0:
                time.sleep(sleep)

    def _on_playback_ended(self):
        self._playing = False
        if self._audio_player:
            self._audio_player.stop()
            self._audio_player = None
        self._on_cue()

    # ── Close ─────────────────────────────────────────────────

    def _on_close(self):
        self._on_stop()
        self.destroy()



# ─────────────────────────────────────────────────────────────
#  Hula — SWS Extractor (integrated from DNSVision/Hula)
#  Converts .SWS files back to Kayenne MOV, Kayenne TGA,
#  or Sony MVS TGA format.
# ─────────────────────────────────────────────────────────────

HULA_TARGET_KAYENNE_MOV = "Kayenne MOV"
HULA_TARGET_KAYENNE_TGA = "Kayenne TGA"
HULA_TARGET_SONY_MVS    = "Sony MVS TGA"

# Header field offsets for SWS read side (Hula uses read only)
_HULA_OFF_STD_CODE = 0x188
_HULA_OFF_WIDTH    = 0x190
_HULA_OFF_HEIGHT   = 0x194
_HULA_OFF_PLANE_SZ = 0x1A0
_HULA_OFF_FRAMES   = 0x1A4
_HULA_OFF_PLAY_CNT    = 0x1A8
_HULA_OFF_FMT_VARIANT = 0x18C
_HULA_OFF_AUD_OFF     = 0x1E8
_HULA_OFF_AUD_FMT     = 0x1EC

# FPS lookup (same as SWSHeader in player section -- kept separate for clarity)
_HULA_STD_CODE_FPS = {
    0x4923: 50.0,  0x4921: 59.94, 0x4925: 25.0,
    0x4813: 50.0,  0x4814: 59.94, 0x4817: 50.0,
    0x4816: 59.94,
}


class HulaSWSHeader:
    """Parse the 512-byte SWS header for Hula's read-only use."""

    def __init__(self, path: str):
        with open(path, 'rb') as f:
            raw = f.read(SWS_HEADER_SIZE)
        if len(raw) < SWS_HEADER_SIZE:
            raise ValueError("File too small to be a valid SWS file.")
        if raw[0:16] != SWS_MAGIC:
            raise ValueError(f"Not a valid SWS file (bad magic: {raw[0:16]!r})")
        self.width       = struct.unpack_from('>I', raw, _HULA_OFF_WIDTH)[0]
        self.height      = struct.unpack_from('>I', raw, _HULA_OFF_HEIGHT)[0]
        self.plane_size  = struct.unpack_from('>I', raw, _HULA_OFF_PLANE_SZ)[0]
        self.frame_count = struct.unpack_from('>I', raw, _HULA_OFF_FRAMES)[0]
        self.play_count  = struct.unpack_from('>I', raw, _HULA_OFF_PLAY_CNT)[0]
        self.has_key     = (self.play_count > 0)
        aud_off_div32    = struct.unpack_from('>I', raw, _HULA_OFF_AUD_OFF)[0]
        aud_fmt          = struct.unpack_from('>I', raw, _HULA_OFF_AUD_FMT)[0]
        self.has_audio   = (aud_off_div32 > 0 and aud_fmt == 0x03000000)
        self.audio_offset = aud_off_div32 * 32 if self.has_audio else 0
        std_code         = struct.unpack_from('>I', raw, _HULA_OFF_STD_CODE)[0]
        fmt_variant      = struct.unpack_from('>I', raw, _HULA_OFF_FMT_VARIANT)[0]
        self.fps         = self._get_fps(std_code, fmt_variant)

    @staticmethod
    def _get_fps(std_code: int, fmt_variant: int = 0) -> float:
        if fmt_variant in FORMAT_VARIANT_FPS:
            return FORMAT_VARIANT_FPS[fmt_variant]
        # Fallback for third-party files with unrecognised format variant
        low16 = std_code & 0xFFFF
        if low16 in _HULA_STD_CODE_FPS:
            return _HULA_STD_CODE_FPS[low16]
        for mask in [~0x04 & 0xFFFF, ~0x08 & 0xFFFF, ~0x0C & 0xFFFF]:
            if (low16 & mask) in _HULA_STD_CODE_FPS:
                return _HULA_STD_CODE_FPS[low16 & mask]
        return 25.0

    def __repr__(self):
        return (f"HulaSWSHeader({self.width}x{self.height}, "
                f"frames={self.frame_count}, plane_size={self.plane_size}, "
                f"has_key={self.has_key}, has_audio={self.has_audio}, fps={self.fps})")


def _hula_decode_frame(fill_bytes: bytes, key_bytes: bytes,
                       width: int, height: int):
    """Decode one frame from fill and key plane slices.
    Returns (rgb uint8 HxWx3, alpha uint8 HxW).
    Reuses the v210 decoder already present in machuna.py."""
    fill_yuv = _v210_plane_to_yuv(fill_bytes, width, height, 1)
    rgb      = _yuv_to_rgb8(fill_yuv[0])
    if key_bytes:
        key_yuv = _v210_plane_to_yuv(key_bytes, width, height, 1)
        alpha   = _yuv_to_gray8(key_yuv[0])
    else:
        alpha = np.full((height, width), 255, dtype=np.uint8)
    return rgb, alpha


def _hula_extract_audio_stereo(sws_path: str, header: HulaSWSHeader,
                                tmp_dir: str, log=print):
    """Extract Ch0 (L) and Ch2 (R) from SWS 16ch PCM as stereo temp file."""
    if not header.has_audio:
        return None
    file_size  = os.path.getsize(sws_path)
    audio_size = file_size - header.audio_offset
    if audio_size <= 0:
        return None
    with open(sws_path, 'rb') as f:
        f.seek(header.audio_offset)
        raw = f.read(audio_size)
    samples = np.frombuffer(raw, dtype='<i2')
    total   = len(samples) // 16
    if total == 0:
        return None
    samples = samples[:total * 16].reshape(-1, 16)
    stereo  = np.zeros((total, 2), dtype='<i2')
    stereo[:, 0] = samples[:, 0]
    stereo[:, 1] = samples[:, 2]
    stereo_path = os.path.join(tmp_dir, 'hula_audio_stereo.pcm')
    stereo.tofile(stereo_path)
    log(f"  Audio extracted: {total} samples, stereo")
    return stereo_path


def _hula_convert_tga(sws_path: str, dest_parent: str,
                      target: str, clip_name: str = 'WIPE', log=print):
    """Convert one SWS to a TGA sequence subfolder."""
    stem     = Path(sws_path).stem
    dest_dir = os.path.join(dest_parent, stem)
    os.makedirs(dest_dir, exist_ok=True)
    header   = HulaSWSHeader(sws_path)
    log(f"  {header}")
    fill_off = SWS_HEADER_SIZE
    key_off  = SWS_HEADER_SIZE + header.plane_size * header.frame_count
    log(f"  Decoding {header.frame_count} frame(s)...")
    with open(sws_path, 'rb') as f:
        for i in range(header.frame_count):
            f.seek(fill_off + i * header.plane_size)
            fill_bytes = f.read(header.plane_size)
            key_bytes  = None
            if header.has_key:
                f.seek(key_off + i * header.plane_size)
                key_bytes = f.read(header.plane_size)
            rgb, alpha = _hula_decode_frame(fill_bytes, key_bytes,
                                            header.width, header.height)
            rgba_img = Image.merge('RGBA', [
                Image.fromarray(rgb[:, :, 0], 'L'),
                Image.fromarray(rgb[:, :, 1], 'L'),
                Image.fromarray(rgb[:, :, 2], 'L'),
                Image.fromarray(alpha, 'L'),
            ])
            if target == HULA_TARGET_KAYENNE_TGA:
                filename = f"{i + 1:04d}.tga"
            else:
                cn = clip_name.upper()[:4].ljust(4)
                filename = f"{cn}{i:04d}.tga"
            rgba_img.save(os.path.join(dest_dir, filename), format='TGA')
            if (i + 1) % 10 == 0 or i + 1 == header.frame_count:
                log(f"  Frame {i + 1}/{header.frame_count}")
    log(f"  Done → {dest_dir}  ({header.frame_count} TGA files)")
    return dest_dir


def _hula_convert_mov(sws_path: str, dest_parent: str,
                      mov_number: int, log=print) -> str:
    """Convert one SWS to a ProRes 4444 MOV with embedded alpha."""
    header   = HulaSWSHeader(sws_path)
    log(f"  {header}")
    fill_off = SWS_HEADER_SIZE
    key_off  = SWS_HEADER_SIZE + header.plane_size * header.frame_count
    out_path = os.path.join(dest_parent, f"{mov_number:04d}.mov")
    with tempfile.TemporaryDirectory() as tmp:
        raw_rgba = os.path.join(tmp, 'rgba_raw.rgba')
        log(f"  Decoding {header.frame_count} frame(s) to RGBA...")
        with open(sws_path, 'rb') as f_in, open(raw_rgba, 'wb') as f_out:
            for i in range(header.frame_count):
                f_in.seek(fill_off + i * header.plane_size)
                fill_bytes = f_in.read(header.plane_size)
                key_bytes  = None
                if header.has_key:
                    f_in.seek(key_off + i * header.plane_size)
                    key_bytes = f_in.read(header.plane_size)
                rgb, alpha = _hula_decode_frame(fill_bytes, key_bytes,
                                                header.width, header.height)
                rgba = np.dstack([rgb, alpha[:, :, np.newaxis]])
                f_out.write(rgba.tobytes())
                if (i + 1) % 10 == 0 or i + 1 == header.frame_count:
                    log(f"  Frame {i + 1}/{header.frame_count}")
        stereo_pcm = _hula_extract_audio_stereo(sws_path, header, tmp, log)
        ffmpeg     = _get_ffmpeg_path('ffmpeg')
        fps_str    = f"{header.fps:.6g}"
        base_cmd   = [ffmpeg, '-y',
                      '-f', 'rawvideo', '-pix_fmt', 'rgba',
                      '-s', f"{header.width}x{header.height}",
                      '-r', fps_str, '-i', raw_rgba]
        if stereo_pcm:
            base_cmd += ['-f', 's16le', '-ar', '48000', '-ac', '2',
                         '-i', stereo_pcm]
        base_cmd += ['-c:v', 'prores_ks', '-profile:v', '4444',
                     '-pix_fmt', 'yuva444p10le',
                     '-color_primaries', 'bt709',
                     '-color_trc', 'bt709',
                     '-colorspace', 'bt709']
        if stereo_pcm:
            base_cmd += ['-c:a', 'pcm_s16le', '-ar', '48000']
        base_cmd.append(out_path)
        log("  Encoding ProRes 4444...")
        result = subprocess.run(base_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"ffmpeg encode failed (rc={result.returncode}):\n"
                f"{result.stderr[-2000:]}"
            )
    log(f"  Done → {out_path}")
    return out_path


def _hula_run_batch(sws_paths: list, dest_dir: str, target: str,
                    clip_name: str = 'WIPE', log=print):
    """Convert a list of SWS files. Called from HulaWindow worker thread."""
    os.makedirs(dest_dir, exist_ok=True)
    ok = fail = 0
    for idx, path in enumerate(sws_paths, start=1):
        log(f"\n[{idx}/{len(sws_paths)}] {os.path.basename(path)}")
        try:
            if target == HULA_TARGET_KAYENNE_MOV:
                _hula_convert_mov(path, dest_dir, idx, log=log)
            else:
                _hula_convert_tga(path, dest_dir, target,
                                  clip_name=clip_name, log=log)
            ok += 1
        except Exception as e:
            log(f"  ERROR: {e}")
            fail += 1
    log(f"\n{'='*40}")
    log(f"Complete: {ok} succeeded, {fail} failed.")


class HulaWindow(tk.Toplevel):
    """Hula SWS Extractor -- non-modal child window launched from MacHuna."""

    def __init__(self, parent, settings: dict, save_cb):
        super().__init__(parent)
        self.title("Hula — SWS Extractor")
        self.resizable(False, False)
        self._save_cb    = save_cb   # callable to persist settings
        self._settings   = settings  # shared dict
        self._selected   = []
        self._build_ui(settings)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        # Centre over parent
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width()  - self.winfo_width())  // 2
        py = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")

    def _build_ui(self, s: dict):
        PAD = 8
        pad = dict(padx=PAD, pady=4)

        # Destination
        dest_frame = ttk.LabelFrame(self, text="Destination Folder")
        dest_frame.pack(fill='x', **pad)
        self._dest_var = tk.StringVar(value=s.get('hula_dest', ''))
        ttk.Entry(dest_frame, textvariable=self._dest_var, width=52).pack(
            side='left', fill='x', expand=True)
        ttk.Button(dest_frame, text="Browse…",
                   command=self._browse_dest).pack(side='left', padx=(PAD, 0))

        # Output target
        tgt_frame = ttk.LabelFrame(self, text="Output Target")
        tgt_frame.pack(fill='x', **pad)
        self._target_var = tk.StringVar(
            value=s.get('hula_target', HULA_TARGET_KAYENNE_MOV))
        for label in (HULA_TARGET_KAYENNE_MOV,
                      HULA_TARGET_KAYENNE_TGA,
                      HULA_TARGET_SONY_MVS):
            tk.Radiobutton(tgt_frame, text=label,
                           variable=self._target_var, value=label,
                           command=self._on_target_change
                           ).pack(side='left', padx=(0, PAD))

        # Clip name (Sony MVS only)
        clip_frame = tk.Frame(tgt_frame)
        clip_frame.pack(side='left', padx=(PAD * 2, 0))
        tk.Label(clip_frame, text="Clip name (4 chars):").pack(side='left')
        self._clip_var = tk.StringVar(value=s.get('hula_clip', 'WIPE'))
        vcmd = self.register(lambda P: len(P) <= 4 and (P == '' or P.isalnum()))
        self._clip_entry = ttk.Entry(clip_frame, textvariable=self._clip_var,
                                     width=5, validate='key',
                                     validatecommand=(vcmd, '%P'))
        self._clip_entry.pack(side='left', padx=(4, 0))
        tk.Label(clip_frame,
                 text="(all clips share this name — they will merge on import)",
                 font=('Helvetica', 10), fg='#888888'
                 ).pack(side='left', padx=(8, 0))

        # Files
        files_frame = ttk.LabelFrame(self, text="SWS Files")
        files_frame.pack(fill='x', **pad)
        self._files_var = tk.StringVar(value="No files selected.")
        tk.Label(files_frame, textvariable=self._files_var,
                 font=('Helvetica', 11), anchor='w'
                 ).pack(side='left', fill='x', expand=True)
        ttk.Button(files_frame, text="Open Files…",
                   command=self._open_files).pack(side='left', padx=(PAD, 0))

        # Buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(fill='x', **pad)
        self._convert_btn = ttk.Button(btn_frame, text="Convert",
                                       command=self._do_convert)
        self._convert_btn.pack(side='left')
        self._clear_btn = ttk.Button(btn_frame, text="Clear Log")
        self._clear_btn.pack(side='left', padx=(PAD, 0))

        # Log
        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill='both', expand=True, **pad)
        self._log_box = scrolledtext.ScrolledText(
            log_frame, width=80, height=16,
            font=('Menlo', 11), state='disabled')
        self._log_box.pack(fill='both', expand=True)

        def clear_log():
            self._log_box.config(state='normal')
            self._log_box.delete('1.0', 'end')
            self._log_box.config(state='disabled')

        self._clear_btn.config(command=clear_log)
        self._on_target_change()

    def _browse_dest(self):
        d = filedialog.askdirectory(title="Choose destination folder",
                                    parent=self)
        if d:
            self._dest_var.set(d)

    def _open_files(self):
        paths = filedialog.askopenfilenames(
            title="Select SWS files", parent=self,
            filetypes=[('SWS files', '*.SWS *.sws'), ('All files', '*.*')])
        if paths:
            self._selected = sorted(paths)
            n = len(self._selected)
            self._files_var.set(f"{n} file{'s' if n != 1 else ''} selected.")

    def _on_target_change(self):
        is_sony = self._target_var.get() == HULA_TARGET_SONY_MVS
        self._clip_entry.config(state='normal' if is_sony else 'disabled')

    def _log(self, msg: str):
        def _append():
            self._log_box.config(state='normal')
            self._log_box.insert('end', msg + '\n')
            self._log_box.see('end')
            self._log_box.config(state='disabled')
        self.after(0, _append)

    def _do_convert(self):
        dest  = self._dest_var.get().strip()
        tgt   = self._target_var.get()
        cname = self._clip_var.get().strip().upper()
        if not dest:
            messagebox.showerror("Hula", "Please set a destination folder.",
                                 parent=self)
            return
        if not self._selected:
            messagebox.showerror("Hula", "Please select at least one SWS file.",
                                 parent=self)
            return
        if tgt == HULA_TARGET_SONY_MVS and len(cname) != 4:
            messagebox.showerror("Hula",
                                 "Sony MVS clip name must be exactly 4 characters.",
                                 parent=self)
            return
        try:
            check_ffmpeg()
        except RuntimeError as e:
            messagebox.showerror("Hula", str(e), parent=self)
            return
        # Persist settings
        self._settings['hula_dest']   = dest
        self._settings['hula_target'] = tgt
        self._settings['hula_clip']   = cname
        self._save_cb()
        self._convert_btn.config(state='disabled')

        def worker():
            try:
                _hula_run_batch(list(self._selected), dest, tgt,
                                clip_name=cname, log=self._log)
            finally:
                self.after(0, lambda: self._convert_btn.config(state='normal'))

        threading.Thread(target=worker, daemon=True).start()

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
                    'auto_play': auto_play_var.get(),
                    'loop_play': loop_play_var.get(),
                    'start_num': start_num_var.get(),
                    'hula_dest':   s.get('hula_dest', ''),
                    'hula_target': s.get('hula_target', HULA_TARGET_KAYENNE_MOV),
                    'hula_clip':   s.get('hula_clip', 'WIPE'),
                    'window_geometry': root.geometry(),
                }, f)
        except Exception:
            pass

    try:
        root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    except Exception:
        root = tk.Tk()
    root.title(f"MacHuna v{VERSION}")
    root.resizable(True, True)
    root.minsize(620, 340)
    # Restore saved window geometry, or use a sensible default
    _saved_geo = load_settings().get('window_geometry', '1121x592')
    root.geometry(_saved_geo)

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
    auto_play_var     = tk.BooleanVar(value=False)
    loop_play_var     = tk.BooleanVar(value=False)
    ttk.Checkbutton(frm3, text="Split >4GB (FAT32)", variable=split_var).pack(side='left', **pad)
    ttk.Checkbutton(frm3, text="Delete source after conversion", variable=delete_var).pack(side='left', **pad)
    ttk.Checkbutton(frm3, text="Ignore alpha/key", variable=ignore_alpha_var).pack(side='left', **pad)
    ttk.Checkbutton(frm3, text="Include audio", variable=include_audio_var).pack(side='left', **pad)
    ttk.Checkbutton(frm3, text="Auto play", variable=auto_play_var).pack(side='left', **pad)
    ttk.Checkbutton(frm3, text="Loop play", variable=loop_play_var).pack(side='left', **pad)

    # ── Load saved settings ──
    start_num_var = tk.IntVar(value=1)  # must be defined before load_settings references it
    s = load_settings()
    if s.get('watch'):    watch_var.set(s['watch'])
    if s.get('dest'):     dest_var.set(s['dest'])
    if s.get('standard'): std_var.set(s['standard'])
    if 'split'        in s: split_var.set(s['split'])
    if 'delete'       in s: delete_var.set(s['delete'])
    if 'ignore_alpha'   in s: ignore_alpha_var.set(s['ignore_alpha'])
    if 'include_audio'  in s: include_audio_var.set(s['include_audio'])
    if 'auto_play'      in s: auto_play_var.set(s['auto_play'])
    if 'loop_play'      in s: loop_play_var.set(s['loop_play'])
    if 'start_num'      in s: start_num_var.set(s['start_num'])
    # Hula settings live in the same dict -- HulaWindow reads them directly
    # s is passed by reference so HulaWindow can update it in place

    # ── Buttons ──
    frm4 = ttk.Frame(root)
    frm4.pack(fill='x', **pad)

    service_ref = [None]
    batch_cancel_event = threading.Event()  # set to request batch cancellation

    run_btn    = ttk.Button(frm4, text="▶  Start Watching")
    stop_btn   = ttk.Button(frm4, text="⏹  Stop", state='disabled')
    cancel_btn = ttk.Button(frm4, text="✕  Cancel Batch", state='disabled')
    run_btn.pack(side='left', **pad)
    stop_btn.pack(side='left', **pad)
    cancel_btn.pack(side='left', **pad)

    # ── Open Files / Batch Convert row ──
    frm5 = ttk.LabelFrame(root, text="Batch Convert")
    frm5.pack(fill='x', **pad)

    ttk.Label(frm5, text="Start number:").pack(side='left', **pad)
    start_num_entry = ttk.Spinbox(frm5, from_=1, to=9999, textvariable=start_num_var, width=6)
    start_num_entry.pack(side='left', **pad)

    open_btn = ttk.Button(frm5, text="Open Files…")
    open_btn.pack(side='left', **pad)

    ttk.Label(frm5, text="MOV, MP4, MXF, PNG, BMP, JPG only. For TGA sequences use the Watch Folder.",
              foreground='#888888').pack(side='left', **pad)

    ttk.Button(frm5, text="SWS Player",
               command=lambda: SWSPlayer(root, initial_dir=dest_var.get())).pack(side='right', **pad)
    ttk.Button(frm5, text="Hula",
               command=lambda: HulaWindow(root, s, save_settings)).pack(side='right', **pad)

    # ── Log area ──
    log_frame = ttk.LabelFrame(root, text="Log")
    log_frame.pack(fill='both', expand=True, **pad)

    log_toolbar = ttk.Frame(log_frame)
    log_toolbar.pack(fill='x', padx=4, pady=(4, 0))
    ttk.Button(log_toolbar, text="Clear Log",
               command=lambda: log_text.delete('1.0', 'end')).pack(side='right')

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
            batch_cancel_event.clear()
            root.after(0, lambda: cancel_btn.config(state='normal'))
            for i, path in enumerate(sorted(valid)):
                if batch_cancel_event.is_set():
                    log("Batch conversion cancelled.")
                    break
                fnum = start_num + i
                ext = Path(path).suffix.lower()
                try:
                    if ext in {'.mov', '.mp4', '.avi', '.mxf'}:
                        convert_clip(path, fnum, d,
                                     std_var.get(), split_var.get(),
                                     delete_var.get(), log,
                                     ignore_alpha=ignore_alpha_var.get(),
                                     include_audio=include_audio_var.get(),
                                     auto_play=auto_play_var.get(),
                                     loop_play=loop_play_var.get())
                    elif ext == '.tga' and Path(path).stat().st_size > 0:
                        convert_still(path, fnum, d,
                                      std_var.get(), split_var.get(),
                                      delete_var.get(), log,
                                      ignore_alpha=ignore_alpha_var.get(),
                                      auto_play=auto_play_var.get(),
                                      loop_play=loop_play_var.get())
                    else:
                        convert_still(path, fnum, d,
                                      std_var.get(), split_var.get(),
                                      delete_var.get(), log,
                                      ignore_alpha=ignore_alpha_var.get(),
                                      auto_play=auto_play_var.get(),
                                      loop_play=loop_play_var.get())
                except Exception as e:
                    import traceback
                    log(f"  ERROR converting {Path(path).name}: {e}")
                    log(f"  {traceback.format_exc()}")
            root.after(0, lambda: cancel_btn.config(state='disabled'))

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
            ('Video & Image files', '*.mov *.mp4 *.avi *.mxf *.png *.bmp *.jpg *.jpeg'),
            ('Video files', '*.mov *.mp4 *.avi *.mxf'),
            ('Image files', '*.png *.bmp *.jpg *.jpeg'),
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
            batch_cancel_event.clear()
            root.after(0, lambda: cancel_btn.config(state='normal'))
            results = []
            cancelled = False
            for i, path in enumerate(valid):
                if batch_cancel_event.is_set():
                    log("Batch conversion cancelled.")
                    cancelled = True
                    break
                fnum = start_num + i
                ext = Path(path).suffix.lower()
                try:
                    if ext in {'.mov', '.mp4', '.avi', '.mxf'}:
                        convert_clip(path, fnum, d,
                                     std_var.get(), split_var.get(),
                                     delete_var.get(), log,
                                     ignore_alpha=ignore_alpha_var.get(),
                                     include_audio=include_audio_var.get(),
                                     auto_play=auto_play_var.get(),
                                     loop_play=loop_play_var.get())
                    else:
                        convert_still(path, fnum, d,
                                      std_var.get(), split_var.get(),
                                      delete_var.get(), log,
                                      ignore_alpha=ignore_alpha_var.get(),
                                      auto_play=auto_play_var.get(),
                                      loop_play=loop_play_var.get())
                    results.append((fnum, Path(path).stem, 'OK'))
                except Exception as e:
                    import traceback
                    log(f"  ERROR converting {Path(path).name}: {e}")
                    log(f"  {traceback.format_exc()}")
                    results.append((fnum, Path(path).stem, f'ERROR: {e}'))

            root.after(0, lambda: cancel_btn.config(state='disabled'))

            # Write conversion log to destination folder
            if results and not cancelled:
                from datetime import datetime as dt
                date_str = dt.now().strftime('%d-%m-%Y')
                log_filename = f"MacHuna_Log_{date_str}.txt"
                log_path = os.path.join(d, log_filename)
                try:
                    max_len = max(len(fname) for _, fname, _ in results)
                    with open(log_path, 'w') as f:
                        f.write(f"MacHuna Conversion Log\n")
                        f.write(f"{'=' * 40}\n")
                        f.write(f"Date: {dt.now().strftime('%d %b %Y')}\n")
                        f.write(f"Standard: {std_var.get()}\n")
                        f.write(f"{'=' * 40}\n\n")
                        for fnum, fname, status in results:
                            f.write(f"{fnum:4d}  {fname:<{max_len}}  [{status}]\n")
                    log(f"Conversion log saved: {log_filename}")
                except Exception as e:
                    log(f"  Could not write log file: {e}")

            # Advance start number for next batch
            root.after(0, lambda: start_num_var.set(start_num + len(valid)))

        threading.Thread(target=convert_batch, daemon=True).start()

    open_btn.config(command=open_files)

    def cancel_batch():
        batch_cancel_event.set()
        log("Cancelling batch -- current file will complete before stopping.")
        cancel_btn.config(state='disabled')

    cancel_btn.config(command=cancel_batch)

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
                           include_audio=include_audio_var.get(),
                           auto_play=auto_play_var.get(),
                           loop_play=loop_play_var.get(),
                           log=log)
        svc.start()
        service_ref[0] = svc
        run_btn.config(state='disabled')
        stop_btn.config(state='normal')
        log("Service started.")

    def stop_watching():
        if service_ref[0]:
            service_ref[0].stop()
            service_ref[0] = None
        _kill_current_ffmpeg()
        run_btn.config(state='normal')
        stop_btn.config(state='disabled')
        log("Service stopped.")

    run_btn.config(command=start_watching)
    stop_btn.config(command=stop_watching)

    def on_closing():
        save_settings()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # On macOS, Cmd+Q fires the tk::mac::Quit event rather than WM_DELETE_WINDOW
    root.createcommand('tk::mac::Quit', on_closing)

    # macOS About box -- wire up via the application menu
    # tk::mac::ShowAbout is silently overridden by the PyInstaller default panel,
    # so we build an explicit menubar and intercept the About item directly.
    # Custom Toplevel used for centred text and correct app icon.
    def show_about():
        win = tk.Toplevel(root)
        win.title("About MacHuna")
        win.resizable(False, False)
        win.grab_set()  # modal

        # Try to show the app icon
        icon_loaded = False
        try:
            icon_path = None
            if getattr(sys, 'frozen', False):
                # PyInstaller extracts --add-data files to sys._MEIPASS
                icon_path = os.path.join(sys._MEIPASS, 'machuna_final_1024.png')
            else:
                # Running as a script: look next to machuna.py
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         'machuna_final_1024.png')
            if icon_path and os.path.exists(icon_path):
                from PIL import Image, ImageTk
                img = Image.open(icon_path).resize((96, 96), Image.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                lbl_icon = tk.Label(win, image=photo)
                lbl_icon.image = photo  # keep reference
                lbl_icon.pack(pady=(20, 8))
                icon_loaded = True
        except Exception:
            pass

        if not icon_loaded:
            tk.Label(win, text="🚀", font=('Helvetica', 48)).pack(pady=(20, 8))

        tk.Label(win, text=f"MacHuna v{VERSION}",
                 font=('Helvetica', 16, 'bold'), justify='center').pack()
        tk.Label(win, text="Mac alternative for Grass Valley K-Watch",
                 font=('Helvetica', 12), justify='center').pack(pady=(8, 0))
        tk.Label(win, text="Authors: David Steer & Claude (Anthropic)",
                 font=('Helvetica', 12), justify='center').pack(pady=(4, 0))

        ttk.Button(win, text="OK", command=win.destroy).pack(pady=20)

        win.update_idletasks()
        # Centre over main window
        x = root.winfo_x() + (root.winfo_width()  - win.winfo_width())  // 2
        y = root.winfo_y() + (root.winfo_height() - win.winfo_height()) // 2
        win.geometry(f"+{x}+{y}")

    menubar = tk.Menu(root)
    apple_menu = tk.Menu(menubar, name='apple')
    menubar.add_cascade(menu=apple_menu)
    apple_menu.add_command(label="About MacHuna", command=show_about)
    apple_menu.add_separator()
    root.config(menu=menubar)

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

