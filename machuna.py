#!/usr/bin/env python3
"""
MacHuna for macOS
Translates broadcast media assets between formats: MOV, MP4, MXF, TGA sequences,
and still images to/from Grass Valley Kahuna .SWS, Kayenne MOV, Kayenne TGA, and Sony TGA.

Requirements:
    brew install ffmpeg   (or: https://ffmpeg.org/download.html)
    pip3 install pillow numpy

Usage:
    python3 machuna.py --gui
    python3 machuna.py --convert /path/to/file.mov --number 42 --dest /path/to/destination
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

VERSION = "1.5.38"

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
# The 0x8000 bit flags interlaced scanning -- all interlaced standards use 0xc923,
# all progressive standards use 0x4923. Confirmed by P->I transcode analysis (2026-05-09).
# Unverified standards (1080p29.97, 1080p30, 2160p variants) removed from dropdown pending
# confirmation against K-Watch reference files. See DEVELOPMENT_NOTES.md roadmap.
VIDEO_STANDARDS = {
    '1080i50':   0xc923,   # confirmed -- 0x8000 = interlaced flag
    '1080i5994': 0xc923,   # confirmed -- 0x8000 = interlaced flag
    '1080i60':   0xc923,   # confirmed by pattern -- 0x8000 = interlaced flag
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

# Human-readable standard names for display, keyed by format variant (0x18C).
FORMAT_VARIANT_DISPLAY = {
    0x08: '1080i/50',   0x05: '1080i/59.94', 0x04: '1080i/60',
    0x13: '1080p/25',   0x18: '1080p/50',    0x17: '1080p/59.94',
    0x16: '1080p/60',   0x10: '720p/50',     0x0f: '720p/59.94',
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
                    width: int = 0, height: int = 0,
                    vf_extra: str = ''):
    """Convert input to raw v210 using ffmpeg, then byte-swap to big-endian.

    ffmpeg outputs v210 as little-endian 32-bit words.
    Kahuna expects big-endian 32-bit words.
    We swap each 4-byte word after conversion.
    vf_extra: additional ffmpeg video filter appended to the chain (e.g. tinterlace=...)
    """
    vf_key = 'alphaextract,format=gray'

    ffmpeg = _get_ffmpeg_path('ffmpeg')
    cmd_fill = [ffmpeg, '-y', '-i', input_path]
    vf_parts = []
    if width and height:
        vf_parts.append(f'scale={width}:{height}')
    if vf_extra:
        vf_parts.append(vf_extra)
    if vf_parts:
        cmd_fill += ['-vf', ','.join(vf_parts)]
    cmd_fill += ['-colorspace', 'bt709', '-color_range', 'tv', '-f', 'rawvideo', '-vcodec', 'v210', output_path]

    _run_ffmpeg(cmd_fill, check=True)
    _byteswap_v210(output_path)

    if extract_alpha:
        alpha_path = output_path + '.alpha.raw'
        # Extract alpha, convert to clean limited-range luma (64=black, 940=white)
        # vf_extra (e.g. tinterlace) must be appended so key frame count matches fill.
        vf_key = 'alphaextract,format=yuv420p,colorspace=bt709,scale=out_range=tv'
        if vf_extra:
            vf_key += f',{vf_extra}'
        cmd_key = [ffmpeg, '-y', '-i', input_path,
                   '-vf', vf_key,
                   '-f', 'rawvideo', '-vcodec', 'v210', alpha_path]
        result = _run_ffmpeg(cmd_key)
        if result.returncode != 0 or not os.path.exists(alpha_path) or os.path.getsize(alpha_path) == 0:
            # Simpler fallback
            vf_key_fallback = 'alphaextract'
            if vf_extra:
                vf_key_fallback += f',{vf_extra}'
            cmd_key = [ffmpeg, '-y', '-i', input_path,
                       '-vf', vf_key_fallback,
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
    if video_standard in _interlaced_standards:
        log(f"  Note: still image stored as progressive data in an interlaced ({video_standard}) wrapper — normal for graphics.")

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
    do_p_to_i = video_standard in _interlaced_standards and not info['is_interlaced']
    do_i_to_p = info['is_interlaced'] and video_standard not in _interlaced_standards

    if do_p_to_i:
        # Weave pairs of progressive frames into interlaced frames (TFF best-guess).
        # Frame count halves; fps halves (e.g. 50p -> 25fps for 1080i/50).
        # Field order TFF is SMPTE standard for 1080i HD -- confirm on Kahuna hardware.
        vf_tinterlace  = 'tinterlace=mode=interleave_top'
        output_frame_count = frame_count // 2
        output_fps         = FORMAT_VARIANT_FPS[FORMAT_VARIANTS[video_standard]]
        log(f"  Transcoding progressive→interlaced (TFF): {frame_count} frames @ {fps:.2f}fps → {output_frame_count} frames @ {output_fps:.2f}fps")
    elif do_i_to_p:
        # Deinterlace interlaced source to progressive output.
        # The SWS format variant determines playback fps, so we must produce the
        # correct number of frames for that fps — not the source frame rate.
        target_fps = FORMAT_VARIANT_FPS[FORMAT_VARIANTS[video_standard]]
        output_fps = target_fps
        if target_fps > fps:
            # Bob deinterlace: each field becomes a frame (doubles frame rate),
            # then resample to exact target fps (handles cross-rate cases like i50→p60).
            vf_tinterlace = f'yadif=mode=send_field,fps={target_fps}'
            output_frame_count = int(round(frame_count * target_fps / fps))
        else:
            # Target fps ≤ source frame rate: simple deinterlace, same frame count.
            vf_tinterlace = 'yadif=mode=send_frame'
            output_frame_count = frame_count
        log(f"  Transcoding interlaced→progressive: {frame_count} frames @ {fps:.2f}fps → ~{output_frame_count} frames @ {output_fps:.2f}fps")
    else:
        vf_tinterlace      = ''
        output_frame_count = frame_count
        output_fps         = fps

    has_alpha = info['has_alpha'] and not ignore_alpha
    will_include_audio = include_audio and info['has_audio']
    log(f"  Size: {w}x{h}  FPS: {fps:.2f}  Frames: {frame_count}  has_alpha={info['has_alpha']}{' (ignored)' if ignore_alpha and info['has_alpha'] else ''}  audio={info['has_audio']}{' (included)' if will_include_audio else ' (excluded)' if info['has_audio'] else ''}")

    with tempfile.TemporaryDirectory() as tmp:
        fill_raw   = os.path.join(tmp, 'fill.v210')
        actual_key = None
        audio_raw  = None

        key_raw = convert_to_v210(input_path, fill_raw, extract_alpha=has_alpha, vf_extra=vf_tinterlace)
        if ignore_alpha:
            # No key plane written at all -- matches K-Watch behaviour
            actual_key = None
        elif key_raw:
            actual_key = os.path.join(tmp, 'key.v210')
            os.rename(fill_raw + '.alpha.raw', actual_key)
        else:
            actual_key = os.path.join(tmp, 'key.v210')
            _generate_white_key(fill_raw, actual_key)

        # v210 plane_size is exact from dimensions: ceil(width/6)*16*height
        # Derive actual frame count from file size -- more reliable than ffprobe estimate,
        # especially after tinterlace which may output a different count than frame_count//2.
        plane_size         = ((w + 5) // 6) * 16 * h
        output_frame_count = os.path.getsize(fill_raw) // plane_size

        # Extract audio if requested and present
        if will_include_audio:
            audio_path = os.path.join(tmp, 'audio.pcm')
            if extract_audio(input_path, audio_path, output_frame_count, output_fps):
                audio_raw = audio_path
                log(f"  Audio extracted: {os.path.getsize(audio_raw):,} bytes")
            else:
                log(f"  Audio extraction failed -- writing without audio")

        src_name = os.path.basename(input_path)
        clip_name  = Path(input_path).stem  # use filename stem as clip name

        hdr = build_sws_header(
            source_filename=src_name,
            clip_name=clip_name,
            width=w, height=h,
            frame_count=output_frame_count,
            plane_size=plane_size,
            video_standard=video_standard,
            is_still=False,
            fps=output_fps,
            has_audio=(audio_raw is not None),
            has_key=(actual_key is not None),
            auto_play=auto_play,
            loop_play=loop_play,
        )

        dest_path = os.path.join(dest_dir, f"{file_number}.SWS")
        write_sws(dest_path, fill_raw, actual_key, hdr, split_fat32,
                  frame_count=output_frame_count, audio_raw=audio_raw, log=log)

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
                         loop_play: bool = False,
                         write_log: bool = True,
                         source_interlaced: bool = False):
    """Convert a numbered TGA sequence into a single multi-frame .SWS clip."""

    log(f"Converting TGA sequence: {len(tga_files)} frames → {file_number}.SWS")
    info = get_video_info(tga_files[0])
    w, h = info['width'], info['height']
    frame_count = len(tga_files)
    has_alpha = info['has_alpha'] and not ignore_alpha

    _interlaced_standards = {'1080i50', '1080i5994', '1080i60'}
    # p→i: field-weave progressive frames into interlaced output
    do_p_to_i = video_standard in _interlaced_standards and not source_interlaced
    # i→p: source is interlaced (25/29.97/30fps) but target is progressive (50/59.94/60fps)
    #       duplicate each frame to preserve duration
    do_i_to_p = source_interlaced and video_standard not in _interlaced_standards

    if do_p_to_i:
        vf_tinterlace = 'tinterlace=mode=interleave_top'
        log(f"  Progressive→interlaced (TFF): {frame_count} frames → {frame_count // 2} frames")
    elif do_i_to_p:
        vf_tinterlace = None
        log(f"  Interlaced→progressive: duplicating {frame_count} frames → {frame_count * 2} frames")
    elif source_interlaced and video_standard in _interlaced_standards:
        vf_tinterlace = None
        log(f"  Source frames already interlaced — passing through as {video_standard}")
    else:
        vf_tinterlace = None

    with tempfile.TemporaryDirectory() as tmp:
        # Build a concat demuxer file — list each frame twice for i→p to preserve duration
        concat_file = os.path.join(tmp, 'concat.txt')
        with open(concat_file, 'w') as f:
            for tga in sorted(tga_files):
                f.write(f"file '{tga}'\n")
                if do_i_to_p:
                    f.write(f"file '{tga}'\n")

        fill_raw = os.path.join(tmp, 'fill.v210')
        ffmpeg = _get_ffmpeg_path('ffmpeg')
        cmd = [ffmpeg, '-y', '-f', 'concat', '-safe', '0', '-i', concat_file]
        if vf_tinterlace:
            cmd += ['-vf', vf_tinterlace]
        elif not do_i_to_p:
            cmd += ['-frames:v', str(frame_count)]
        cmd += ['-f', 'rawvideo', '-vcodec', 'v210', fill_raw]
        _run_ffmpeg(cmd, check=True)

        # Key/alpha
        actual_key = None
        if ignore_alpha:
            # No key plane written at all -- matches K-Watch behaviour
            actual_key = None
        elif has_alpha:
            key_raw = os.path.join(tmp, 'key.v210')
            vf_key1 = 'alphaextract,format=yuv420p,colorspace=bt709,scale=out_range=tv'
            vf_key2 = 'alphaextract'
            if vf_tinterlace:
                vf_key1 += f',{vf_tinterlace}'
                vf_key2 += f',{vf_tinterlace}'
            cmd_key = [ffmpeg, '-y', '-f', 'concat', '-safe', '0',
                       '-i', concat_file,
                       '-vf', vf_key1,
                       '-f', 'rawvideo', '-vcodec', 'v210', key_raw]
            result = _run_ffmpeg(cmd_key)
            if result.returncode != 0 or not os.path.exists(key_raw) or os.path.getsize(key_raw) == 0:
                cmd_key = [ffmpeg, '-y', '-f', 'concat', '-safe', '0',
                           '-i', concat_file,
                           '-vf', vf_key2,
                           '-f', 'rawvideo', '-vcodec', 'v210', key_raw]
                _run_ffmpeg(cmd_key, check=True)
            _byteswap_v210(key_raw)
            actual_key = key_raw
        else:
            actual_key = os.path.join(tmp, 'key.v210')
            _generate_white_key(fill_raw, actual_key)

        _byteswap_v210(fill_raw)

        # Derive actual output frame count from file size — reliable after tinterlace.
        plane_size         = ((w + 5) // 6) * 16 * h
        output_frame_count = os.path.getsize(fill_raw) // plane_size
        log(f"  plane_size: {plane_size:,}  output frames: {output_frame_count}")
        src_name  = os.path.basename(tga_files[0])
        clip_name = Path(tga_files[0]).stem

        hdr = build_sws_header(
            source_filename=src_name,
            clip_name=clip_name,
            width=w, height=h,
            frame_count=output_frame_count,
            plane_size=plane_size,
            video_standard=video_standard,
            is_still=False,
            has_key=(actual_key is not None),
            auto_play=auto_play,
            loop_play=loop_play,
        )

        dest_path = os.path.join(dest_dir, f"{file_number}.SWS")
        write_sws(dest_path, fill_raw, actual_key, hdr, split_fat32,
                  frame_count=output_frame_count, log=log)

    if delete_source:
        for f in tga_files:
            os.remove(f)

    log(f"  Done → {dest_path}")

    if write_log:
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

# Matches generic TGA sequence frames: base name + optional separator + frame number
# Covers: shot_0001.tga  shot.0001.tga  shot-0001.tga  FEDX0000.tga
_GENERIC_TGA_RE = re.compile(r'^(.+?)(?:[._-]?)(\d+)$')
GENERIC_TGA_QUIET_SECS = 3.0

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


def _fmt_timecode(frame_count: int, fps: float) -> str:
    """Return compact wall-clock duration, omitting leading zero HH: or HH:MM: sections."""
    if not fps:
        return "--"
    total = frame_count / fps
    hh = int(total // 3600)
    mm = int((total % 3600) // 60)
    ss = total % 60
    if hh:
        return f"{hh:02d}:{mm:02d}:{ss:05.2f}s"
    if mm:
        return f"{mm:02d}:{ss:05.2f}s"
    return f"{ss:.2f}s"


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
        self.standard     = FORMAT_VARIANT_DISPLAY.get(fmt_variant, f'0x{fmt_variant:02x}')
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


class _PlayerHeader:
    """Minimal header-like object for TGA sequences and video files."""
    def __init__(self, fps: float, frame_count: int,
                 has_key: bool = False, has_audio: bool = False, standard: str = ''):
        self.fps         = fps
        self.frame_count = frame_count
        self.has_key     = has_key
        self.has_audio   = has_audio
        self.loop_play   = False
        self.auto_play   = False
        self.standard    = standard


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


class _GenericFrameCache:
    """Frame cache for TGA sequences and video files (non-SWS)."""
    def __init__(self, path: str, header: _PlayerHeader):
        self.path      = path   # folder for TGA sequences, file path for video
        self.header    = header
        self.frames    = []     # list of [fill_img, key_img, comp_img]
        self.audio_pcm = None


def _tga_sequence_files(first_tga: str) -> list:
    """Return sorted list of TGA paths sharing the same sequence base name as first_tga."""
    folder = os.path.dirname(os.path.abspath(first_tga))
    m = _GENERIC_TGA_RE.match(Path(first_tga).stem)
    if m:
        base = m.group(1)
        result = []
        for f in os.listdir(folder):
            if not f.lower().endswith('.tga'):
                continue
            fm = _GENERIC_TGA_RE.match(Path(f).stem)
            if fm and fm.group(1) == base:
                result.append(os.path.join(folder, f))
        return sorted(result)
    return sorted(
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith('.tga')
    )


def _find_tga_sequences(folder: str) -> list:
    """Scan folder and return list of (base_name, sorted_file_paths) for each TGA sequence found."""
    groups = {}
    for fname in os.listdir(folder):
        if not fname.lower().endswith('.tga'):
            continue
        if not os.path.isfile(os.path.join(folder, fname)):
            continue
        m = _GENERIC_TGA_RE.match(Path(fname).stem)
        if m:
            base = m.group(1)
            seq_num = int(m.group(2))
            groups.setdefault(base, []).append((seq_num, os.path.join(folder, fname)))
    result = []
    for base, entries in sorted(groups.items()):
        if len(entries) >= 2:
            result.append((base, [p for _, p in sorted(entries)]))
    return result


def _load_tga_frames(tga_files: list, progress_cb=None):
    """Load TGA sequence into (frames, has_key).
    frames = list of [fill_img, key_img, comp_img] PIL Images at PANEL_W × PANEL_H.
    """
    n = len(tga_files)
    frames  = []
    has_key = False

    for i, path in enumerate(tga_files):
        if progress_cb:
            progress_cb(int(i / n * 95), f"Loading frame {i + 1}/{n}...")
        img = Image.open(path)
        if img.mode not in ('RGBA', 'RGB', 'L', 'LA'):
            img = img.convert('RGBA')
        has_alpha = 'A' in img.getbands()
        if has_alpha:
            has_key = True

        fill = img.convert('RGB').resize((PANEL_W, PANEL_H), Image.BILINEAR)

        if has_alpha:
            alpha_arr = np.array(img.split()[3].resize((PANEL_W, PANEL_H), Image.BILINEAR))
            key_img   = Image.fromarray(alpha_arr, 'L')
            comp_img  = Image.fromarray(_make_composite(np.array(fill), alpha_arr), 'RGB')
        else:
            key_img  = None
            comp_img = fill

        frames.append([fill, key_img, comp_img])

    if progress_cb:
        progress_cb(100, "Ready.")
    return frames, has_key


def _load_video_frames(path: str, progress_cb=None):
    """Extract frames from a video file via ffmpeg.
    Returns (frames, fps, frame_count).
    frames = list of [fill_img, None, fill_img] at PANEL_W × PANEL_H.
    Uses subprocess directly (not _run_ffmpeg) so Stop/Cancel don't affect it.
    """
    import json
    ffprobe = _get_ffmpeg_path('ffprobe')
    ffmpeg  = _get_ffmpeg_path('ffmpeg')

    if progress_cb:
        progress_cb(2, "Reading file info...")

    info_result = subprocess.run(
        [ffprobe, '-v', 'error', '-select_streams', 'v:0',
         '-show_entries', 'stream=r_frame_rate,width,height,nb_frames,pix_fmt',
         '-of', 'json', path],
        capture_output=True
    )
    info    = json.loads(info_result.stdout or b'{}')
    streams = info.get('streams', [{}])
    s       = streams[0] if streams else {}

    rfr = s.get('r_frame_rate', '25/1')
    try:
        num, den = rfr.split('/')
        fps = float(num) / float(den)
    except Exception:
        fps = 25.0

    width    = int(s.get('width',  1920))
    height   = int(s.get('height', 1080))
    pix_fmt  = s.get('pix_fmt', '')
    # yuva*, rgba, argb, bgra, ya8, etc. all contain 'a' indicating alpha channel
    has_alpha_src = 'a' in pix_fmt

    nb = s.get('nb_frames')
    if nb and nb != 'N/A':
        frame_count_hint = int(nb)
    else:
        cnt = subprocess.run(
            [ffprobe, '-v', 'error', '-select_streams', 'v:0',
             '-count_packets', '-show_entries', 'stream=nb_read_packets',
             '-of', 'json', path],
            capture_output=True
        )
        cnt_s = json.loads(cnt.stdout or b'{}').get('streams', [{}])
        frame_count_hint = int(cnt_s[0].get('nb_read_packets', 0)) if cnt_s else 0

    # Extract video frames — use rgba when source has alpha so key plane is preserved
    out_pix_fmt     = 'rgba' if has_alpha_src else 'rgb24'
    bytes_per_pixel = 4      if has_alpha_src else 3

    if progress_cb:
        progress_cb(5, f"Extracting frames ({width}×{height} @ {fps:.3f}fps)...")

    proc = subprocess.Popen(
        [ffmpeg, '-i', path, '-f', 'rawvideo', '-pix_fmt', out_pix_fmt, 'pipe:1'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )

    frame_bytes = width * height * bytes_per_pixel
    frames = []
    while True:
        raw = proc.stdout.read(frame_bytes)
        if len(raw) < frame_bytes:
            break
        arr      = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, bytes_per_pixel)
        fill_img = Image.fromarray(arr[:, :, :3], 'RGB').resize((PANEL_W, PANEL_H), Image.BILINEAR)
        if has_alpha_src:
            alpha_rs = np.array(
                Image.fromarray(arr[:, :, 3], 'L').resize((PANEL_W, PANEL_H), Image.BILINEAR)
            )
            key_img  = Image.fromarray(alpha_rs, 'L')
            comp_img = Image.fromarray(_make_composite(np.array(fill_img), alpha_rs), 'RGB')
            frames.append([fill_img, key_img, comp_img])
        else:
            frames.append([fill_img, None, fill_img])
        if progress_cb and frame_count_hint:
            pct = 5 + int(len(frames) / frame_count_hint * 78)
            progress_cb(min(pct, 83), f"Extracting frame {len(frames)}...")

    proc.wait()

    # Extract audio — convert to 16-channel 16-bit LE PCM at 48kHz (player format)
    audio_pcm = None
    if progress_cb:
        progress_cb(86, "Extracting audio...")
    audio_result = subprocess.run(
        [ffmpeg, '-i', path, '-vn', '-ac', '2', '-ar', '48000', '-f', 's16le', 'pipe:1'],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    raw_stereo = audio_result.stdout
    if raw_stereo:
        stereo   = np.frombuffer(raw_stereo, dtype='<i2').reshape(-1, 2)
        expanded = np.zeros((len(stereo), 16), dtype='<i2')
        expanded[:, 0] = stereo[:, 0]   # L → ch0  (K-Watch mapping)
        expanded[:, 2] = stereo[:, 1]   # R → ch2  (K-Watch mapping)
        audio_pcm = expanded.tobytes()

    if progress_cb:
        progress_cb(100, "Ready.")
    return frames, fps, len(frames), audio_pcm, has_alpha_src


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
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
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
            if self._stop_event.is_set():
                return
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

        ttk.Button(transport, text="Open...",
                   command=self._open_file).pack(side='right', padx=4)

        # Status / progress
        status_frame = tk.Frame(self)
        status_frame.pack(fill='x', padx=pad, pady=(0, pad))
        self._status_var = tk.StringVar(value="Click Open… to select a folder containing SWS, TGA, or video files.")
        tk.Label(status_frame, textvariable=self._status_var,
                 font=('Helvetica', 10), anchor='w').pack(side='left', fill='x', expand=True)
        self._progress = ttk.Progressbar(status_frame, length=200, mode='determinate')
        self._progress.pack(side='right', padx=(8, 0))

    # ── File open ────────────────────────────────────────────

    def _open_file(self):
        folder = filedialog.askdirectory(
            title="Select Folder",
            parent=self,
            initialdir=self._initial_dir if self._initial_dir else None,
        )
        if not folder:
            return
        self._initial_dir = folder

        items = _scan_folder_for_player(folder)
        if not items:
            messagebox.showinfo("No Supported Files",
                                "No supported files found in that folder.",
                                parent=self)
            return

        if len(items) == 1:
            self._load_from_item(items[0])
            return

        chosen = self._pick_from_folder(items, Path(folder).name)
        if chosen:
            self._load_from_item(chosen)

    def _pick_from_folder(self, items: list, folder_name: str):
        """Show a single-select dialog listing all playable items in a folder."""
        result = [None]
        dlg = tk.Toplevel(self)
        dlg.title("Open File")
        dlg.resizable(False, False)
        dlg.transient(self)

        ttk.Label(dlg, text=f"Folder: {folder_name}",
                  font=('Helvetica', 11, 'bold')).pack(anchor='w', padx=8, pady=(8, 4))

        list_frame = ttk.Frame(dlg)
        list_frame.pack(fill='both', expand=True, padx=8, pady=2)
        lb = tk.Listbox(list_frame, selectmode='single', height=min(len(items), 16),
                        width=60, font=('Menlo', 11))
        sb = ttk.Scrollbar(list_frame, command=lb.yview)
        lb.config(yscrollcommand=sb.set)
        lb.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        for item in items:
            lb.insert('end', '  ' + item['display'])
        lb.select_set(0)

        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(fill='x', padx=8, pady=8)

        def ok():
            sel = lb.curselection()
            if sel:
                result[0] = items[sel[0]]
            dlg.destroy()

        def cancel():
            dlg.destroy()

        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(side='right', padx=4)
        ttk.Button(btn_frame, text="Open",   command=ok).pack(side='right', padx=4)
        lb.bind('<Double-1>', lambda _e: ok())

        dlg.update_idletasks()
        px = self.winfo_x() + (self.winfo_width()  - dlg.winfo_width())  // 2
        py = self.winfo_y() + (self.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{px}+{py}")
        dlg.grab_set()
        dlg.focus_force()

        self.wait_window(dlg)
        return result[0]

    def _load_from_item(self, item: dict):
        if item['type'] == 'sws':
            self._load_sws(item['path'])
        elif item['type'] == 'tga_seq':
            self._load_tga(item['files'][0])
        else:
            self._load_video(item['path'])

    def _reset_display(self):
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

    def _load_sws(self, path: str):
        self._reset_display()

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
        std = header.standard.replace('/', '')
        tc  = _fmt_timecode(header.frame_count, header.fps)
        self._info_var.set(
            f"{std}  {header.frame_count}frms  {tc}  "
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

    def _load_tga(self, path: str):
        fps = self._ask_fps()
        if fps is None:
            return
        self._reset_display()
        tga_files = _tga_sequence_files(path)
        n         = len(tga_files)
        folder    = os.path.dirname(os.path.abspath(path))
        self.title(f"SWS Preview Player — {Path(folder).name}")
        self._info_var.set(f"TGA sequence  {n}frms  {fps}fps — loading...")
        self._status_var.set("Loading TGA frames...")
        self._progress['value'] = 0
        self.update()

        def load():
            def progress(pct, msg):
                self.after(0, lambda: self._on_progress(pct, msg))
            try:
                frames, has_key = _load_tga_frames(tga_files, progress)
                hdr   = _PlayerHeader(fps=fps, frame_count=n, has_key=has_key)
                cache = _GenericFrameCache(folder, hdr)
                cache.frames = frames
                self.after(0, lambda: self._on_load_complete(cache, hdr))
            except Exception as e:
                import traceback; traceback.print_exc()
                msg = str(e)
                self.after(0, lambda m=msg: self._on_load_error(m))

        threading.Thread(target=load, daemon=True).start()

    def _load_video(self, path: str):
        self._reset_display()
        self.title(f"SWS Preview Player — {Path(path).name}")
        self._info_var.set("Video — loading...")
        self._status_var.set("Extracting frames...")
        self._progress['value'] = 0
        self.update()

        def load():
            def progress(pct, msg):
                self.after(0, lambda: self._on_progress(pct, msg))
            try:
                frames, fps, frame_count, audio_pcm, has_key = _load_video_frames(path, progress)
                hdr   = _PlayerHeader(fps=fps, frame_count=frame_count,
                                      has_key=has_key, has_audio=bool(audio_pcm))
                cache = _GenericFrameCache(path, hdr)
                cache.frames    = frames
                cache.audio_pcm = audio_pcm
                self.after(0, lambda: self._on_load_complete(cache, hdr))
            except Exception as e:
                import traceback; traceback.print_exc()
                msg = str(e)
                self.after(0, lambda m=msg: self._on_load_error(m))

        threading.Thread(target=load, daemon=True).start()

    def _ask_fps(self) -> Optional[float]:
        """Show a small dialog to pick frame rate for a TGA sequence."""
        result = [None]
        dlg = tk.Toplevel(self)
        dlg.title("Frame Rate")
        dlg.resizable(False, False)
        dlg.transient(self)

        tk.Label(dlg, text="Select frame rate for this TGA sequence:",
                 font=('Helvetica', 12)).pack(padx=16, pady=(16, 8))

        fps_var = tk.StringVar(value="25")
        cb = ttk.Combobox(dlg, textvariable=fps_var, width=10,
                          values=["23.976", "25", "29.97", "30", "50", "59.94", "60"],
                          state='readonly')
        cb.pack(padx=16, pady=8)

        def ok():
            try:
                result[0] = float(fps_var.get())
            except ValueError:
                result[0] = 25.0
            dlg.destroy()

        def cancel():
            dlg.destroy()

        btn_row = tk.Frame(dlg)
        btn_row.pack(pady=(0, 16))
        ttk.Button(btn_row, text="OK",     command=ok).pack(side='left', padx=8)
        ttk.Button(btn_row, text="Cancel", command=cancel).pack(side='left', padx=8)

        dlg.update_idletasks()
        px = self.winfo_x() + (self.winfo_width()  - dlg.winfo_width())  // 2
        py = self.winfo_y() + (self.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{px}+{py}")
        dlg.grab_set()
        dlg.focus_force()

        self.wait_window(dlg)
        return result[0]

    def _on_progress(self, pct: int, msg: str):
        self._progress['value'] = pct
        self._status_var.set(msg)
        self.update_idletasks()

    def _on_load_complete(self, cache, header):
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

        # Update info bar for TGA/video (SWS info already set before load thread)
        if isinstance(header, _PlayerHeader):
            tc      = _fmt_timecode(n, header.fps)
            fps_str = f"{header.fps:.3f}".rstrip('0').rstrip('.')
            self._info_var.set(
                f"{fps_str}fps  {n}frms  {tc}  "
                f"Key: {'Yes' if header.has_key else 'No'}  Audio: {'Yes' if header.has_audio else 'No'}"
            )

        if not header.has_key:
            self._key_canvas.delete('nokey')
            self._key_canvas.create_text(
                PANEL_W // 2, PANEL_H // 2,
                text="No key plane", fill='#555555',
                font=('Helvetica', 14), tags='nokey'
            )

        has_audio_str = "with audio" if cache.audio_pcm else "no audio"
        try:
            sz_mb    = os.path.getsize(cache.path) / 1024 / 1024
            size_str = f"  ({sz_mb:.1f} MB)"
        except OSError:
            size_str = ""
        self._status_var.set(
            f"Loaded {n} frame{'s' if n != 1 else ''}  {has_audio_str}{size_str}"
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
#  Hula — SWS / MOV Extractor (integrated from DNSVision/Hula)
#  Converts .SWS or .MOV files to Kayenne MOV, Kayenne TGA,
#  or Sony TGA format.
#  NOTE: Kayenne TGA output parameters are UNCONFIRMED pending hardware
#  verification. Sony TGA parameters are confirmed for Sony MVS.
# ─────────────────────────────────────────────────────────────

HULA_TARGET_KAYENNE_MOV = "Kayenne MOV"
HULA_TARGET_KAYENNE_TGA = "Kayenne TGA"   # UNCONFIRMED — awaiting hardware verification
HULA_TARGET_SONY_TGA    = "Sony TGA"
_HULA_TGA_TARGETS = {HULA_TARGET_KAYENNE_TGA, HULA_TARGET_SONY_TGA}

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
        self.fmt_variant = struct.unpack_from('>I', raw, _HULA_OFF_FMT_VARIANT)[0]
        self.fps         = self._get_fps(std_code, self.fmt_variant)
        self.standard    = FORMAT_VARIANT_DISPLAY.get(self.fmt_variant, f'0x{self.fmt_variant:02x}')

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
    folder   = clip_name.upper()[:4] if target == HULA_TARGET_SONY_TGA else stem
    dest_dir = os.path.join(dest_parent, folder)
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
            else:  # Sony TGA
                cn = clip_name.upper()[:4].ljust(4)
                filename = f"{cn}{i:04d}.tga"
            rgba_img.save(os.path.join(dest_dir, filename), format='TGA')
            if (i + 1) % 10 == 0 or i + 1 == header.frame_count:
                log(f"  Frame {i + 1}/{header.frame_count}")
    log(f"  Done → {dest_dir}  ({header.frame_count} TGA files)")
    return dest_dir


def _hula_convert_tga_interlaced(sws_path: str, dest_parent: str,
                                  target: str = HULA_TARGET_SONY_TGA,
                                  clip_name: str = 'WIPE',
                                  field_order: str = 'BFF', log=print):
    """Convert a progressive SWS to an interlaced TGA sequence by field-weaving.

    Each pair of consecutive source frames is woven into one interlaced frame.
    field_order: 'BFF' or 'TFF'.  Output frame count = input frame count // 2.
    [UNCONFIRMED: Kayenne TGA output parameters pending hardware verification]
    """
    stem     = Path(sws_path).stem
    folder   = clip_name.upper()[:4] if target == HULA_TARGET_SONY_TGA else stem
    dest_dir = os.path.join(dest_parent, folder)
    os.makedirs(dest_dir, exist_ok=True)
    header   = HulaSWSHeader(sws_path)
    std = header.standard.replace('/', '')
    if header.fps < 48.0:
        raise ValueError(
            f"{Path(sws_path).name} is {std} ({header.fps:.4g}fps) — "
            f"interlaced output requires a 50fps or higher progressive source."
        )
    log(f"  {header}")
    n         = header.frame_count
    out_count = n // 2
    if n % 2:
        log(f"  Warning: odd frame count ({n}) — last source frame skipped")
    fill_off = SWS_HEADER_SIZE
    key_off  = SWS_HEADER_SIZE + header.plane_size * n
    log(f"  Weaving {n} frames → {out_count} interlaced frames ({field_order})...")
    cn = clip_name.upper()[:4].ljust(4)
    with open(sws_path, 'rb') as f:
        for i in range(out_count):
            f.seek(fill_off + (2 * i) * header.plane_size)
            fill_a = f.read(header.plane_size)
            f.seek(fill_off + (2 * i + 1) * header.plane_size)
            fill_b = f.read(header.plane_size)
            key_a = key_b = None
            if header.has_key:
                f.seek(key_off + (2 * i) * header.plane_size)
                key_a = f.read(header.plane_size)
                f.seek(key_off + (2 * i + 1) * header.plane_size)
                key_b = f.read(header.plane_size)
            rgb_a, alpha_a = _hula_decode_frame(fill_a, key_a,
                                                header.width, header.height)
            rgb_b, alpha_b = _hula_decode_frame(fill_b, key_b,
                                                header.width, header.height)
            rgb_out   = np.empty_like(rgb_a)
            alpha_out = np.empty_like(alpha_a)
            if field_order == 'TFF':
                rgb_out[0::2]   = rgb_a[0::2]
                rgb_out[1::2]   = rgb_b[1::2]
                alpha_out[0::2] = alpha_a[0::2]
                alpha_out[1::2] = alpha_b[1::2]
            else:  # BFF
                rgb_out[1::2]   = rgb_a[1::2]
                rgb_out[0::2]   = rgb_b[0::2]
                alpha_out[1::2] = alpha_a[1::2]
                alpha_out[0::2] = alpha_b[0::2]
            rgba_img = Image.merge('RGBA', [
                Image.fromarray(rgb_out[:, :, 0], 'L'),
                Image.fromarray(rgb_out[:, :, 1], 'L'),
                Image.fromarray(rgb_out[:, :, 2], 'L'),
                Image.fromarray(alpha_out, 'L'),
            ])
            if target == HULA_TARGET_KAYENNE_TGA:
                filename = f"{i + 1:04d}.tga"
            else:
                filename = f"{cn}{i:04d}.tga"
            rgba_img.save(os.path.join(dest_dir, filename), format='TGA')
            if (i + 1) % 10 == 0 or i + 1 == out_count:
                log(f"  Frame {i + 1}/{out_count}")
    log(f"  Done → {dest_dir}  ({out_count} TGA files)")
    return dest_dir


def _hula_convert_mov_to_tga(mov_path: str, dest_parent: str,
                              target: str, standard: str,
                              clip_name: str = 'WIPE',
                              field_order: str = 'BFF', log=print):
    """Convert a MOV file to a TGA sequence using the selected video standard.

    Progressive standards → direct frame extraction.
    Interlaced standards → frame pairs field-woven into interlaced output.
    [UNCONFIRMED: Kayenne TGA output parameters pending hardware verification]
    """
    stem      = Path(mov_path).stem
    is_sony   = target == HULA_TARGET_SONY_TGA
    folder    = clip_name.upper()[:4] if is_sony else stem
    dest_dir  = os.path.join(dest_parent, folder)
    os.makedirs(dest_dir, exist_ok=True)
    cn        = clip_name.upper()[:4].ljust(4) if is_sony else None
    interlaced = 'i' in standard

    ffmpeg = _get_ffmpeg_path('ffmpeg')

    if not interlaced:
        # Progressive: extract frames directly to dest with correct naming.
        if is_sony:
            pattern = os.path.join(dest_dir, f"{cn}%04d.tga")
            cmd = [ffmpeg, '-y', '-i', mov_path, '-vsync', '0',
                   '-start_number', '0', pattern]
        else:
            pattern = os.path.join(dest_dir, '%04d.tga')
            cmd = [ffmpeg, '-y', '-i', mov_path, '-vsync', '0',
                   '-start_number', '1', pattern]
        log(f"  Extracting {os.path.basename(mov_path)} → TGA ({standard})...")
        _run_ffmpeg(cmd, check=True)
        count = len(list(Path(dest_dir).glob('*.tga')))
        log(f"  Done → {dest_dir}  ({count} TGA files)")
    else:
        # Interlaced: extract all frames to temp PNGs, then field-weave pairs.
        log(f"  Extracting frames from {os.path.basename(mov_path)} for field-weaving ({standard})...")
        with tempfile.TemporaryDirectory() as tmp:
            frame_pat = os.path.join(tmp, 'frame_%06d.png')
            cmd = [ffmpeg, '-y', '-i', mov_path, '-vsync', '0',
                   '-start_number', '0', frame_pat]
            _run_ffmpeg(cmd, check=True)
            frames = sorted(Path(tmp).glob('frame_*.png'))
            n = len(frames)
            if n < 2:
                raise ValueError(
                    f"Need at least 2 source frames for interlaced output, got {n}.")
            out_count = n // 2
            if n % 2:
                log(f"  Warning: odd frame count ({n}) — last frame skipped")
            log(f"  Weaving {n} frames → {out_count} interlaced frames ({field_order})...")
            for i in range(out_count):
                arr_a = np.array(Image.open(frames[i * 2]).convert('RGBA'))
                arr_b = np.array(Image.open(frames[i * 2 + 1]).convert('RGBA'))
                out = np.empty_like(arr_a)
                if field_order == 'TFF':
                    out[0::2] = arr_a[0::2]
                    out[1::2] = arr_b[1::2]
                else:  # BFF
                    out[1::2] = arr_a[1::2]
                    out[0::2] = arr_b[0::2]
                woven = Image.fromarray(out, 'RGBA')
                filename = f"{i + 1:04d}.tga" if not is_sony else f"{cn}{i:04d}.tga"
                woven.save(os.path.join(dest_dir, filename), format='TGA')
                if (i + 1) % 10 == 0 or i + 1 == out_count:
                    log(f"  Frame {i + 1}/{out_count}")
        log(f"  Done → {dest_dir}  ({out_count} TGA files)")


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
        _run_ffmpeg(base_cmd, check=True)
    log(f"  Done → {out_path}")
    return out_path


def _hula_run_batch(input_paths: list, dest_dir: str, target: str,
                    standard: str = '1080p50',
                    clip_name: str = 'WIPE', field_order: str = 'BFF',
                    log=print):
    """Convert a list of SWS or MOV files to the specified extraction target."""
    os.makedirs(dest_dir, exist_ok=True)
    ok = fail = 0
    interlaced = 'i' in standard
    for idx, path in enumerate(input_paths, start=1):
        log(f"\n[{idx}/{len(input_paths)}] {os.path.basename(path)}")
        try:
            ext = Path(path).suffix.lower()
            if ext == '.mov':
                if target == HULA_TARGET_KAYENNE_MOV:
                    raise ValueError(
                        "MOV input is not supported for Kayenne MOV output. "
                        "Select a TGA target or use an SWS file.")
                _hula_convert_mov_to_tga(path, dest_dir, target, standard,
                                         clip_name=clip_name,
                                         field_order=field_order, log=log)
            elif target == HULA_TARGET_KAYENNE_MOV:
                _hula_convert_mov(path, dest_dir, idx, log=log)
            elif interlaced:
                src_header = HulaSWSHeader(path)
                if src_header.fps >= 48.0:
                    # Progressive source: field-weave pairs of frames into interlaced output.
                    _hula_convert_tga_interlaced(path, dest_dir, target=target,
                                                 clip_name=clip_name,
                                                 field_order=field_order, log=log)
                else:
                    # Source is already interlaced: pass frames through as-is.
                    log(f"  Source is {src_header.standard} ({src_header.fps:.4g}fps) "
                        f"— already interlaced, outputting as interlaced TGA frames. "
                        f"If re-importing into MacHuna, tick 'TGA source already interlaced'.")
                    _hula_convert_tga(path, dest_dir, target,
                                      clip_name=clip_name, log=log)
            else:
                _hula_convert_tga(path, dest_dir, target,
                                  clip_name=clip_name, log=log)
            ok += 1
        except Exception as e:
            log(f"  ERROR: {e}")
            fail += 1
    log(f"\n{'='*40}")
    log(f"Complete: {ok} succeeded, {fail} failed.")


# ─────────────────────────────────────────────────────────────
#  Simple Tkinter GUI
# ─────────────────────────────────────────────────────────────

def _ask_confirm(parent, message: str) -> bool:
    """Simple OK/Cancel dialog with no app icon."""
    result = [False]
    dlg = tk.Toplevel(parent)
    dlg.title("")
    dlg.resizable(False, False)
    dlg.grab_set()
    tk.Label(dlg, text=message, padx=20, pady=16).pack()
    btn_frame = tk.Frame(dlg)
    btn_frame.pack(pady=(0, 12))
    ttk.Button(btn_frame, text="Cancel",
               command=lambda: dlg.destroy()).pack(side='left', padx=8)
    ttk.Button(btn_frame, text="OK",
               command=lambda: (result.__setitem__(0, True), dlg.destroy())
               ).pack(side='left', padx=8)
    dlg.update_idletasks()
    px = parent.winfo_x() + (parent.winfo_width()  - dlg.winfo_width())  // 2
    py = parent.winfo_y() + (parent.winfo_height() - dlg.winfo_height()) // 2
    dlg.geometry(f"+{px}+{py}")
    parent.wait_window(dlg)
    return result[0]


def _scan_folder_unified(folder: str) -> tuple:
    """Scan a folder for all supported files.

    Returns (items, input_type, has_audio_clips, has_tga_seq).
    input_type: 'from_sws' | 'mov_only' | 'to_sws_only' | 'mixed_error'
    """
    video_exts = {'.mov', '.mp4', '.avi', '.mxf', '.mkv'}
    still_exts = {'.png', '.bmp', '.jpg', '.jpeg'}

    sequences    = _find_tga_sequences(folder)
    seq_frames   = {f for _, files in sequences for f in files}

    sws_items = []
    vid_items = []
    still_items = []

    for fname in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        ext = Path(fname).suffix.lower()
        if ext == '.sws':
            try:
                h = HulaSWSHeader(fpath)
                tc = _fmt_timecode(h.frame_count, h.fps)
                display = f"{fname:<28}  {h.standard}  {h.frame_count}fr  {tc}"
            except Exception:
                display = fname
            sws_items.append({'type': 'sws', 'path': fpath,
                               'display': display, 'source_num': None})
        elif ext in video_exts and fpath not in seq_frames:
            meta = parse_filename(fname)
            vid_items.append({'type': 'clip', 'path': fpath,
                               'source_num': meta['file_num'] if meta else None,
                               'display': fname})
        elif ext in still_exts and fpath not in seq_frames:
            meta = parse_filename(fname)
            still_items.append({'type': 'still', 'path': fpath,
                                 'source_num': meta['file_num'] if meta else None,
                                 'display': fname})

    seq_items = []
    for base, files in sequences:
        kw = parse_filename(Path(files[0]).name)
        source_num = kw['file_num'] if kw and kw['type'] == 'tga_seq' else None
        seq_items.append({
            'type': 'tga_seq', 'base': base, 'files': files, 'source_num': source_num,
            'display': f"{base.rstrip('._- ')}  ({len(files)} frames)",
        })

    has_sws    = bool(sws_items)
    has_vid    = bool(vid_items)
    has_stills = bool(still_items)
    has_seqs   = bool(seq_items)

    if has_sws and (has_vid or has_stills or has_seqs):
        return [], 'mixed_error', False, False

    if has_sws:
        sws_has_aud = False
        for item in sws_items:
            try:
                if HulaSWSHeader(item['path']).has_audio:
                    sws_has_aud = True
                    break
            except Exception:
                pass
        return sws_items, 'from_sws', sws_has_aud, False

    has_aud = False
    if has_vid:
        for vi in vid_items[:3]:  # probe first few to avoid scanning everything
            try:
                if get_video_info(vi['path']).get('has_audio'):
                    has_aud = True
                    break
            except Exception:
                pass

    if has_vid and not has_stills and not has_seqs:
        return vid_items, 'mov_only', has_aud, False

    items = seq_items + vid_items + still_items
    return items, 'to_sws_only', has_aud, bool(seq_items)


def _scan_folder_for_items(folder: str) -> list:
    """Scan a folder and return items for the browser.
    TGA sequences are collapsed to one entry; other files listed individually."""
    supported = {'.mov', '.mp4', '.avi', '.mxf', '.png', '.bmp', '.jpg', '.jpeg', '.tga'}
    sequences = _find_tga_sequences(folder)
    seq_all_frames = {f for _, files in sequences for f in files}

    items = []
    for base, files in sequences:
        kw = parse_filename(Path(files[0]).name)
        source_num = kw['file_num'] if kw and kw['type'] == 'tga_seq' else None
        items.append({
            'type': 'tga_seq', 'base': base, 'files': files, 'source_num': source_num,
            'display': f"{base.rstrip('._- ')}  ({len(files)} frames)",
        })

    for fname in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        ext = Path(fname).suffix.lower()
        if ext not in supported or fpath in seq_all_frames:
            continue
        meta = parse_filename(fname)
        kind = 'clip' if ext in {'.mov', '.mp4', '.avi', '.mxf'} else 'still'
        items.append({
            'type': kind, 'path': fpath,
            'source_num': meta['file_num'] if meta else None,
            'display': fname,
        })

    return items


def _scan_folder_for_player(folder: str) -> list:
    """Scan folder for files the player can open. TGA sequences collapsed to one entry."""
    video_exts = {'.mov', '.mp4', '.avi', '.mxf', '.mkv'}
    sequences  = _find_tga_sequences(folder)
    seq_frames = {f for _, files in sequences for f in files}
    items = []

    for fname in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        if Path(fname).suffix.lower() == '.sws':
            try:
                h = HulaSWSHeader(fpath)
                tc = _fmt_timecode(h.frame_count, h.fps)
                display = f"{fname:<28}  {h.standard}  {h.frame_count}fr  {tc}"
            except Exception:
                display = fname
            items.append({'type': 'sws', 'path': fpath, 'display': display})

    for base, files in sequences:
        items.append({
            'type': 'tga_seq', 'files': files,
            'display': f"{base.rstrip('._- ')}  ({len(files)} frames)",
        })

    for fname in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, fname)
        if not os.path.isfile(fpath):
            continue
        if Path(fname).suffix.lower() in video_exts and fpath not in seq_frames:
            items.append({'type': 'clip', 'path': fpath, 'display': fname})

    return items


def _group_files_for_batch(paths: list) -> list:
    """
    Group a list of file paths for batch conversion.
    TGA files with the same base name are combined into a single tga_seq item
    (all siblings in the folder are collected, not just the selected frames).
    Other files become individual clip/still items.
    Returns a list of dicts sorted sequences-first then alphabetically.
    """
    tga_groups = {}   # base -> sorted file list (all siblings)
    others     = []

    for path in sorted(paths):
        ext = Path(path).suffix.lower()
        if ext == '.tga':
            m = _GENERIC_TGA_RE.match(Path(path).stem)
            if m:
                base = m.group(1)
                if base not in tga_groups:
                    siblings = _tga_sequence_files(path)
                    if len(siblings) >= 2:
                        # Check K-Watch naming for embedded slot number
                        kw = parse_filename(Path(path).name)
                        source_num = kw['file_num'] if kw and kw['type'] == 'tga_seq' else None
                        tga_groups[base] = {'files': siblings, 'source_num': source_num}
                    else:
                        meta = parse_filename(Path(path).name)
                        others.append({'type': 'still', 'path': path,
                                       'source_num': meta['file_num'] if meta else None})
            else:
                meta = parse_filename(Path(path).name)
                others.append({'type': 'still', 'path': path,
                               'source_num': meta['file_num'] if meta else None})
        elif ext in {'.mov', '.mp4', '.avi', '.mxf'}:
            meta = parse_filename(Path(path).name)
            others.append({'type': 'clip', 'path': path,
                           'source_num': meta['file_num'] if meta else None})
        else:
            meta = parse_filename(Path(path).name)
            others.append({'type': 'still', 'path': path,
                           'source_num': meta['file_num'] if meta else None})

    seq_items = [{'type': 'tga_seq', 'base': base,
                  'files': info['files'], 'source_num': info['source_num']}
                 for base, info in sorted(tga_groups.items())]
    return seq_items + others


def _write_batch_log(results: list, dest_dir: str, standard: str, log_fn):
    """Write MacHuna_Log_DD-MM-YYYY.txt to dest_dir."""
    date_str = datetime.now().strftime('%d-%m-%Y')
    log_filename = f"MacHuna_Log_{date_str}.txt"
    log_path = os.path.join(dest_dir, log_filename)
    try:
        max_len = max(len(name) for _, name, _ in results)
        with open(log_path, 'w') as f:
            f.write("MacHuna Conversion Log\n")
            f.write(f"{'=' * 40}\n")
            f.write(f"Date: {datetime.now().strftime('%d %b %Y')}\n")
            f.write(f"Standard: {standard}\n")
            f.write(f"{'=' * 40}\n\n")
            for fnum, name, status in results:
                f.write(f"{fnum:4d}  {name:<{max_len}}  [{status}]\n")
        log_fn(f"Conversion log saved: {log_filename}")
    except Exception as e:
        log_fn(f"  Could not write log file: {e}")


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
                    'dest':             dest_var.get(),
                    'standard':         std_var.get(),
                    'split':            split_var.get(),
                    'ignore_alpha':     ignore_alpha_var.get(),
                    'include_audio':    include_audio_var.get(),
                    'auto_play':        auto_play_var.get(),
                    'loop_play':        loop_play_var.get(),
                    'source_interlaced': source_interlaced_var.get(),
                    'start_num':        start_num_var.get(),
                    'clip_name':        clip_name_var.get(),
                    'field_order':      field_order_var.get(),
                    'output_format':    output_var.get(),
                    'window_geometry':  root.geometry(),
                }, f)
        except Exception:
            pass

    try:
        root = TkinterDnD.Tk() if HAS_DND else tk.Tk()
    except Exception:
        root = tk.Tk()
    root.title(f"MacHuna v{VERSION}")
    root.resizable(True, True)
    root.minsize(620, 380)
    # Restore saved window geometry, or use a sensible default
    _saved_geo = load_settings().get('window_geometry', '1085x460')
    root.geometry(_saved_geo)

    # ── Style ──
    style = ttk.Style()
    style.theme_use('aqua' if sys.platform == 'darwin' else 'clam')

    pad = dict(padx=8, pady=4)

    # ── Destination folder row ──
    frm2 = ttk.LabelFrame(root, text="Destination Folder")
    frm2.pack(fill='x', **pad)
    dest_var = tk.StringVar()
    ttk.Entry(frm2, textvariable=dest_var, width=60).pack(side='left', fill='x', expand=True, **pad)
    ttk.Button(frm2, text="Browse…",
               command=lambda: dest_var.set(filedialog.askdirectory())).pack(side='left', **pad)
    def _open_dest_folder():
        d = dest_var.get().strip()
        if d and os.path.isdir(d):
            subprocess.run(['open', d])
        elif d:
            messagebox.showwarning("Destination Folder", f"Folder not found:\n{d}")
        else:
            messagebox.showwarning("Destination Folder", "No Destination Folder set.")
    ttk.Button(frm2, text="Open in Finder",
               command=_open_dest_folder).pack(side='left', **pad)

    # ── Output format constants ──
    OUTPUT_KAHUNA_SWS  = "Kahuna SWS"
    OUTPUT_KAYENNE_MOV = "Kayenne MOV"
    OUTPUT_KAYENNE_TGA = "Kayenne TGA"
    OUTPUT_SONY_TGA    = "Sony TGA"

    # ── State ──
    _selected_items  = []
    _input_type      = [None]   # 'to_sws_only' | 'mov_only' | 'from_sws'
    _has_audio_clips = [False]
    _has_tga_seq     = [False]

    # ── All tk variables (defined before load_settings) ──
    std_var               = tk.StringVar(value='1080i50')
    split_var             = tk.BooleanVar(value=True)
    ignore_alpha_var      = tk.BooleanVar(value=False)
    include_audio_var     = tk.BooleanVar(value=True)
    auto_play_var         = tk.BooleanVar(value=False)
    loop_play_var         = tk.BooleanVar(value=False)
    source_interlaced_var = tk.BooleanVar(value=False)
    start_num_var         = tk.IntVar(value=1)
    use_source_num_var    = tk.BooleanVar(value=False)
    clip_name_var         = tk.StringVar(value='WIPE')
    field_order_var       = tk.StringVar(value='BFF')
    output_var            = tk.StringVar()

    # ── Load saved settings ──
    s = load_settings()
    if s.get('dest'):             dest_var.set(s['dest'])
    if s.get('standard'):         std_var.set(s['standard'])
    if 'split'             in s:  split_var.set(s['split'])
    if 'ignore_alpha'      in s:  ignore_alpha_var.set(s['ignore_alpha'])
    if 'include_audio'     in s:  include_audio_var.set(s['include_audio'])
    if 'auto_play'         in s:  auto_play_var.set(s['auto_play'])
    if 'loop_play'         in s:  loop_play_var.set(s['loop_play'])
    if 'source_interlaced' in s:  source_interlaced_var.set(s['source_interlaced'])
    if 'start_num'         in s:  start_num_var.set(s['start_num'])
    if 'clip_name'         in s:  clip_name_var.set(s['clip_name'])
    if 'field_order'       in s:  field_order_var.set(s['field_order'])
    # hula_clip / hula_field_order: backwards-compat with pre-v1.5.33 settings
    if 'hula_clip'         in s and 'clip_name' not in s:
        clip_name_var.set(s['hula_clip'])
    if 'hula_field_order'  in s and 'field_order' not in s:
        field_order_var.set(s['hula_field_order'])

    # ── Convert section ──
    frm_convert = ttk.LabelFrame(root, text="Convert")
    frm_convert.pack(fill='x', **pad)

    # Top row: Open Files + summary + Output dropdown
    frm_row_open = tk.Frame(frm_convert)
    frm_row_open.pack(fill='x', anchor='w')
    open_btn = ttk.Button(frm_row_open, text="Open Files…")
    open_btn.pack(side='left', **pad)
    summary_var = tk.StringVar(value="No files selected.")
    ttk.Label(frm_row_open, textvariable=summary_var,
              foreground='#555555').pack(side='left', padx=(0, 12))
    ttk.Label(frm_row_open, text="Output:").pack(side='left')
    output_cb = ttk.Combobox(frm_row_open, textvariable=output_var,
                              width=22, state='disabled')
    output_cb.pack(side='left', padx=(4, 0))

    # Adaptive option rows (pack/forget in _update_adaptive_controls)
    frm_row_std = tk.Frame(frm_convert)
    std_cb = ttk.Combobox(frm_row_std, textvariable=std_var, width=12,
                           values=list(VIDEO_STANDARDS.keys()), state='readonly')
    ttk.Label(frm_row_std, text="Standard:").pack(side='left', padx=(8, 4), pady=4)
    std_cb.pack(side='left', pady=4)

    frm_row_flags = tk.Frame(frm_convert)
    ttk.Checkbutton(frm_row_flags, text="Split >4GB (FAT32)", variable=split_var).pack(side='left', **pad)
    ttk.Checkbutton(frm_row_flags, text="Ignore alpha/key",   variable=ignore_alpha_var).pack(side='left', **pad)
    ttk.Checkbutton(frm_row_flags, text="Auto play",          variable=auto_play_var).pack(side='left', **pad)
    ttk.Checkbutton(frm_row_flags, text="Loop play",          variable=loop_play_var).pack(side='left', **pad)

    frm_row_tga_opts = tk.Frame(frm_convert)
    chk_tga_int = ttk.Checkbutton(frm_row_tga_opts, text="TGA source interlaced",
                                   variable=source_interlaced_var)
    chk_audio_tosws = ttk.Checkbutton(frm_row_tga_opts, text="Include audio",
                                       variable=include_audio_var)

    frm_row_hula_tga = tk.Frame(frm_convert)
    frm_clip_inner = tk.Frame(frm_row_hula_tga)
    ttk.Label(frm_clip_inner, text="Clip name (4 chars):").pack(side='left')
    vcmd = root.register(lambda P: len(P) <= 4 and (P == '' or P.isalnum()))
    ttk.Entry(frm_clip_inner, textvariable=clip_name_var, width=5,
              validate='key', validatecommand=(vcmd, '%P')).pack(side='left', padx=(4, 4))
    ttk.Label(frm_clip_inner,
              text="(all clips share this name — they will merge on import)",
              foreground='#888888').pack(side='left')
    frm_field_inner = tk.Frame(frm_row_hula_tga)
    ttk.Label(frm_field_inner, text="Field order:").pack(side='left', padx=(0, 4))
    for _fo in ('BFF', 'TFF'):
        tk.Radiobutton(frm_field_inner, text=_fo,
                       variable=field_order_var, value=_fo).pack(side='left')

    frm_row_hula_mov = tk.Frame(frm_convert)
    ttk.Checkbutton(frm_row_hula_mov, text="Include audio",
                    variable=include_audio_var).pack(side='left', **pad)

    # Action row
    batch_cancel_event = threading.Event()
    cancel_btn  = ttk.Button(frm_row_open, text="✕  Cancel", state='disabled')
    convert_btn = ttk.Button(frm_row_open, text="Convert",   state='disabled')
    convert_btn.pack(side='left', **pad)
    cancel_btn.pack(side='left', **pad)

    frm_row_actions = tk.Frame(frm_convert)
    frm_row_actions.pack(fill='x', anchor='w')
    frm_numbering = tk.Frame(frm_row_actions)
    ttk.Label(frm_numbering, text="Start number:").pack(side='left', padx=(8, 4), pady=4)
    ttk.Spinbox(frm_numbering, from_=1, to=9999, textvariable=start_num_var,
                width=6).pack(side='left', pady=4)
    ttk.Checkbutton(frm_numbering, text="Use source file number",
                    variable=use_source_num_var).pack(side='left', padx=(8, 0), pady=4)
    ttk.Button(frm_row_actions, text="Video Player",
               command=lambda: SWSPlayer(root, initial_dir=dest_var.get())
               ).pack(side='right', **pad)

    def _update_adaptive_controls(*_):
        out = output_var.get()
        is_interlaced_std = 'i' in std_var.get()
        for frm in (frm_row_std, frm_row_flags, frm_row_tga_opts,
                    frm_row_hula_tga, frm_row_hula_mov, frm_numbering):
            frm.pack_forget()
        if not out:
            return
        bf = dict(fill='x', anchor='w', before=frm_row_actions)
        if out != OUTPUT_KAYENNE_MOV:
            frm_row_std.pack(**bf)
        if out == OUTPUT_KAHUNA_SWS:
            frm_row_flags.pack(**bf)
            show_tga = _has_tga_seq[0]
            show_aud = _has_audio_clips[0]
            chk_tga_int.pack_forget()
            chk_audio_tosws.pack_forget()
            if show_tga:
                chk_tga_int.pack(side='left', **pad)
            if show_aud:
                chk_audio_tosws.pack(side='left', **pad)
            if show_tga or show_aud:
                frm_row_tga_opts.pack(**bf)
            frm_numbering.pack(side='left')
        elif out == OUTPUT_KAYENNE_MOV:
            if _has_audio_clips[0]:
                frm_row_hula_mov.pack(**bf)
        elif out in (OUTPUT_KAYENNE_TGA, OUTPUT_SONY_TGA):
            is_sony = (out == OUTPUT_SONY_TGA)
            frm_clip_inner.pack_forget()
            frm_field_inner.pack_forget()
            if is_sony:
                frm_clip_inner.pack(side='left', padx=(8, 0), pady=4)
            if is_sony or is_interlaced_std:
                frm_field_inner.pack(side='left', padx=(16, 8), pady=4)
                frm_row_hula_tga.pack(**bf)

    def _update_output_options():
        itype = _input_type[0]
        if itype == 'from_sws':
            opts = [OUTPUT_KAYENNE_MOV, OUTPUT_KAYENNE_TGA, OUTPUT_SONY_TGA]
        elif itype == 'mov_only':
            opts = [OUTPUT_KAHUNA_SWS, OUTPUT_KAYENNE_TGA, OUTPUT_SONY_TGA]
        elif itype == 'to_sws_only':
            opts = [OUTPUT_KAHUNA_SWS]
        else:
            opts = []
        output_cb['values'] = opts
        output_cb.config(state='readonly' if opts else 'disabled')
        if output_var.get() not in opts:
            output_var.set(opts[0] if opts else '')
        _update_adaptive_controls()

    std_cb.bind('<<ComboboxSelected>>', _update_adaptive_controls)
    output_cb.bind('<<ComboboxSelected>>', _update_adaptive_controls)

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

    def open_files():
        folder = filedialog.askdirectory(title="Select folder to convert", parent=root)
        if not folder:
            return

        items, itype, has_aud, has_tga = _scan_folder_unified(folder)

        if itype == 'mixed_error':
            messagebox.showwarning("Open Files",
                "This folder contains a mix of SWS files and other formats.\n"
                "Use a folder with either SWS files or media files, not both.",
                parent=root)
            return
        if not items:
            log(f"No supported files found in {os.path.basename(folder)}.")
            return

        _input_type[0]      = itype
        _has_audio_clips[0] = has_aud
        _has_tga_seq[0]     = has_tga

        # ── Folder browser dialog ──
        dlg = tk.Toplevel(root)
        dlg.title("Select Items to Convert")
        dlg.resizable(False, False)
        dlg.transient(root)
        dlg.grab_set()

        pad2 = {'padx': 8, 'pady': 4}
        ttk.Label(dlg, text=f"Folder: {os.path.basename(folder)}",
                  font=('Helvetica', 11, 'bold')).pack(anchor='w', **pad2)

        list_frame = ttk.Frame(dlg)
        list_frame.pack(fill='both', expand=True, padx=8, pady=2)
        lb = tk.Listbox(list_frame, selectmode='extended', height=min(len(items), 16),
                        width=60, font=('Menlo', 11))
        sb = ttk.Scrollbar(list_frame, command=lb.yview)
        lb.config(yscrollcommand=sb.set)
        lb.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        for item in items:
            lb.insert('end', '  ' + item['display'])
        lb.select_set(0, 'end')

        dlg_status = tk.StringVar(value=f"{len(items)} item(s). Select all or choose individually.")
        ttk.Label(dlg, textvariable=dlg_status, foreground='#888888').pack(anchor='w', padx=8)

        btn_frame_dlg = ttk.Frame(dlg)
        btn_frame_dlg.pack(fill='x', padx=8, pady=8)

        def on_select():
            sel = lb.curselection()
            if not sel:
                dlg_status.set("Select at least one item.")
                return
            chosen = [items[i] for i in sel]
            _selected_items.clear()
            _selected_items.extend(chosen)

            counts = {}
            for item in chosen:
                counts[item['type']] = counts.get(item['type'], 0) + 1
            parts = []
            if 'tga_seq' in counts:
                n = counts['tga_seq']
                parts.append(f"{n} TGA sequence{'s' if n > 1 else ''}")
            if 'clip' in counts:
                n = counts['clip']
                parts.append(f"{n} video file{'s' if n > 1 else ''}")
            if 'still' in counts:
                n = counts['still']
                parts.append(f"{n} still{'s' if n > 1 else ''}")
            if 'sws' in counts:
                n = counts['sws']
                parts.append(f"{n} SWS file{'s' if n > 1 else ''}")
            summary_var.set(f"{os.path.basename(folder)}: " + ', '.join(parts))

            convert_btn.config(state='normal')
            dlg.destroy()
            _update_output_options()

        ttk.Button(btn_frame_dlg, text="Cancel", command=dlg.destroy).pack(side='right', padx=2)
        ttk.Button(btn_frame_dlg, text="Select", command=on_select).pack(side='right', padx=2)

        dlg.update_idletasks()
        px = root.winfo_x() + (root.winfo_width()  - dlg.winfo_width())  // 2
        py = root.winfo_y() + (root.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{px}+{py}")

    open_btn.config(command=open_files)

    def on_convert():
        d = dest_var.get().strip()
        if not d:
            log("Please set a Destination Folder before converting.")
            return
        if not _selected_items:
            log("No items selected.")
            return
        out   = output_var.get()
        itype = _input_type[0]

        try:
            check_ffmpeg()
        except RuntimeError as e:
            log(f"ERROR: {e}")
            return

        # Warning for unconfirmed MOV→TGA path
        if itype == 'mov_only' and out in (OUTPUT_KAYENNE_TGA, OUTPUT_SONY_TGA):
            if not _ask_confirm(root,
                    "MOV → TGA has not been tested on hardware.\n\n"
                    "The output may not load correctly on a Kayenne\n"
                    "or Sony MVS desk.\n\nProceed anyway?"):
                return

        if out == OUTPUT_SONY_TGA and len(clip_name_var.get().strip()) != 4:
            messagebox.showerror("Convert",
                                 "Clip name must be exactly 4 characters for Sony TGA output.",
                                 parent=root)
            return

        if out == OUTPUT_SONY_TGA and len(_selected_items) > 1:
            messagebox.showerror("Convert",
                                 "Sony TGA output can only convert one clip at a time.\n\n"
                                 "All frames would be written to the same folder and the\n"
                                 "second clip would overwrite the first.\n\n"
                                 "Please select a single clip and convert again.",
                                 parent=root)
            return

        def _run_to_sws():
            start_num  = start_num_var.get()
            use_src    = use_source_num_var.get()
            next_slot  = start_num
            results    = []
            cancelled  = False
            for item in _selected_items:
                if batch_cancel_event.is_set():
                    log("Batch cancelled.")
                    cancelled = True
                    break
                fnum = item['source_num'] if use_src and item['source_num'] else next_slot
                if not (use_src and item['source_num']):
                    next_slot += 1
                try:
                    if item['type'] == 'tga_seq':
                        convert_tga_sequence(
                            item['files'], fnum, d,
                            std_var.get(), split_var.get(), False, log,
                            ignore_alpha=ignore_alpha_var.get(),
                            auto_play=auto_play_var.get(),
                            loop_play=loop_play_var.get(),
                            write_log=False,
                            source_interlaced=source_interlaced_var.get())
                        results.append((fnum, item['base'].rstrip('._- '), 'OK'))
                    elif item['type'] == 'clip':
                        convert_clip(
                            item['path'], fnum, d,
                            std_var.get(), split_var.get(), False, log,
                            ignore_alpha=ignore_alpha_var.get(),
                            include_audio=include_audio_var.get(),
                            auto_play=auto_play_var.get(),
                            loop_play=loop_play_var.get())
                        results.append((fnum, Path(item['path']).stem, 'OK'))
                    else:
                        convert_still(
                            item['path'], fnum, d,
                            std_var.get(), split_var.get(), False, log,
                            ignore_alpha=ignore_alpha_var.get(),
                            auto_play=auto_play_var.get(),
                            loop_play=loop_play_var.get())
                        results.append((fnum, Path(item['path']).stem, 'OK'))
                except Exception as e:
                    import traceback
                    name = item.get('base') or Path(item.get('path', '')).name
                    log(f"  ERROR: {name}: {e}\n{traceback.format_exc()}")
                    results.append((fnum, name, f'ERROR: {e}'))
            if results and not cancelled:
                _write_batch_log(results, d, std_var.get(), log)
                if not use_src:
                    root.after(0, lambda v=next_slot: start_num_var.set(v))

        def _run_from_sws():
            target_map = {
                OUTPUT_KAYENNE_MOV: HULA_TARGET_KAYENNE_MOV,
                OUTPUT_KAYENNE_TGA: HULA_TARGET_KAYENNE_TGA,
                OUTPUT_SONY_TGA:    HULA_TARGET_SONY_TGA,
            }
            hula_target = target_map.get(out, HULA_TARGET_KAYENNE_TGA)
            paths = [item['path'] for item in _selected_items]
            _hula_run_batch(paths, d, hula_target,
                            standard=std_var.get(),
                            clip_name=clip_name_var.get().strip().upper(),
                            field_order=field_order_var.get(),
                            log=log)

        def worker():
            batch_cancel_event.clear()
            root.after(0, lambda: cancel_btn.config(state='normal'))
            root.after(0, lambda: convert_btn.config(state='disabled'))
            try:
                if out == OUTPUT_KAHUNA_SWS:
                    _run_to_sws()
                else:
                    _run_from_sws()
            finally:
                root.after(0, lambda: cancel_btn.config(state='disabled'))
                root.after(0, lambda: convert_btn.config(state='normal'))

        threading.Thread(target=worker, daemon=True).start()

    convert_btn.config(command=on_convert)

    def cancel_batch():
        batch_cancel_event.set()
        log("Cancelling — current file will complete before stopping.")
        cancel_btn.config(state='disabled')

    cancel_btn.config(command=cancel_batch)

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
  # Convert a single file
  python3 machuna.py --convert myclip.mov --number 42 --dest ~/Desktop/SWS

  # Launch GUI
  python3 machuna.py --gui
        """
    )
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

    parser.print_help()


if __name__ == '__main__':
    main()

