"""
Unit tests for MacHuna header builder and format constants.

Run with:  /opt/homebrew/bin/python3.12 -m pytest test_machuna.py -v
       or: /opt/homebrew/bin/python3.12 -m unittest test_machuna -v
"""

import json
import os
import shutil
import struct
import sys
import tempfile
import unittest
import urllib.parse
from pathlib import Path

sys.path.insert(0, '.')
import machuna as m


# ── helpers ───────────────────────────────────────────────────────────────────

def _unpack(fmt, hdr, offset):
    size = struct.calcsize(fmt)
    return struct.unpack(fmt, hdr[offset:offset + size])[0]

def _make_header(**kwargs):
    defaults = dict(
        source_filename='test_source.mov',
        clip_name='testclip',
        width=1920,
        height=1080,
        frame_count=25,
        plane_size=4147200,       # 1920 * 1080 * (10/8 padded) typical v210 size
        video_standard='1080p50',
        fps=50.0,
    )
    defaults.update(kwargs)
    return m.build_sws_header(**defaults)


# ── Format table consistency ───────────────────────────────────────────────────

class TestFormatTables(unittest.TestCase):
    """Checks that VIDEO_STANDARDS, FORMAT_VARIANTS, FORMAT_VARIANT_FPS,
    and FORMAT_VARIANT_DISPLAY are all internally consistent."""

    def test_every_standard_has_format_variant(self):
        for std in m.VIDEO_STANDARDS:
            self.assertIn(std, m.FORMAT_VARIANTS,
                f"'{std}' is in VIDEO_STANDARDS but missing from FORMAT_VARIANTS")

    def test_every_format_variant_value_has_fps(self):
        for std, variant in m.FORMAT_VARIANTS.items():
            self.assertIn(variant, m.FORMAT_VARIANT_FPS,
                f"FORMAT_VARIANTS['{std}'] = 0x{variant:02x} has no entry in FORMAT_VARIANT_FPS")

    def test_every_format_variant_value_has_display_name(self):
        for std, variant in m.FORMAT_VARIANTS.items():
            self.assertIn(variant, m.FORMAT_VARIANT_DISPLAY,
                f"FORMAT_VARIANTS['{std}'] = 0x{variant:02x} has no entry in FORMAT_VARIANT_DISPLAY")

    def test_format_variant_values_are_unique(self):
        variants = list(m.FORMAT_VARIANTS.values())
        self.assertEqual(len(variants), len(set(variants)),
            "Two different standards share the same FORMAT_VARIANTS value — reverse lookups will be ambiguous")

    def test_interlaced_standards_have_interlaced_flag(self):
        interlaced = [s for s in m.VIDEO_STANDARDS if 'i' in s]
        for std in interlaced:
            code = m.VIDEO_STANDARDS[std]
            self.assertTrue(code & 0x8000,
                f"'{std}' looks interlaced but 0x8000 flag is not set in VIDEO_STANDARDS (code=0x{code:04x})")

    def test_progressive_standards_lack_interlaced_flag(self):
        progressive = [s for s in m.VIDEO_STANDARDS if 'p' in s]
        for std in progressive:
            code = m.VIDEO_STANDARDS[std]
            self.assertFalse(code & 0x8000,
                f"'{std}' looks progressive but 0x8000 flag IS set in VIDEO_STANDARDS (code=0x{code:04x})")

    def test_fps_values_are_plausible(self):
        valid = {23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0}
        for variant, fps in m.FORMAT_VARIANT_FPS.items():
            self.assertIn(fps, valid,
                f"FORMAT_VARIANT_FPS[0x{variant:02x}] = {fps} is not a recognised frame rate")


# ── Header fixed fields ────────────────────────────────────────────────────────

class TestHeaderFixedFields(unittest.TestCase):

    def setUp(self):
        self.hdr = _make_header()

    def test_header_is_512_bytes(self):
        self.assertEqual(len(self.hdr), 512)

    def test_magic_bytes(self):
        self.assertEqual(self.hdr[0x00:0x10], m.SWS_MAGIC)

    def test_version_string(self):
        ver = m.SWS_VERSION
        self.assertEqual(self.hdr[0xEC:0xEC + len(ver)], ver)

    def test_copyright_string(self):
        c = m.SWS_COPYRIGHT
        self.assertEqual(self.hdr[0x108:0x108 + len(c)], c)

    def test_header_size_field(self):
        self.assertEqual(_unpack('>I', self.hdr, 0x19C), 512)

    def test_play_rate_is_one(self):
        rate = _unpack('>f', self.hdr, 0x1B0)
        self.assertAlmostEqual(rate, 1.0, places=5)


# ── Header variable fields ─────────────────────────────────────────────────────

class TestHeaderVariableFields(unittest.TestCase):

    def test_width_written_correctly(self):
        hdr = _make_header(width=1280, height=720, video_standard='720p50', fps=50.0)
        self.assertEqual(_unpack('>I', hdr, 0x190), 1280)

    def test_height_fill_and_key_written_correctly(self):
        hdr = _make_header(width=1280, height=720, video_standard='720p50', fps=50.0)
        self.assertEqual(_unpack('>I', hdr, 0x194), 720)
        self.assertEqual(_unpack('>I', hdr, 0x198), 720)

    def test_plane_size_written_correctly(self):
        hdr = _make_header(plane_size=9999)
        self.assertEqual(_unpack('>I', hdr, 0x1A0), 9999)

    def test_frame_count_written_correctly(self):
        hdr = _make_header(frame_count=100)
        self.assertEqual(_unpack('>I', hdr, 0x1A4), 100)

    def test_source_filename_in_header(self):
        hdr = _make_header(source_filename='myclip.mov')
        stored = hdr[0x20:0x20 + len(b'myclip.mov')]
        self.assertEqual(stored, b'myclip.mov')

    def test_source_filename_truncated_at_63_chars(self):
        long_name = 'A' * 100
        hdr = _make_header(source_filename=long_name)
        stored = hdr[0x20:0x20 + 63]
        self.assertEqual(stored, b'A' * 63)

    def test_clip_name_in_header(self):
        hdr = _make_header(clip_name='myclip')
        stored = hdr[0xFB:0xFB + len(b'myclip')]
        self.assertEqual(stored, b'myclip')

    def test_clip_name_truncated_at_11_chars(self):
        hdr = _make_header(clip_name='ABCDEFGHIJKLMNO')
        stored = hdr[0xFB:0xFB + 11]
        self.assertEqual(stored, b'ABCDEFGHIJK')


# ── Video standard codes in header ────────────────────────────────────────────

class TestVideoStandardCodes(unittest.TestCase):

    def _fps_for(self, std):
        return m.FORMAT_VARIANT_FPS[m.FORMAT_VARIANTS[std]]

    def test_standard_code_at_0x188(self):
        for std, expected_code in m.VIDEO_STANDARDS.items():
            fps = self._fps_for(std)
            hdr = _make_header(video_standard=std, fps=fps)
            actual = _unpack('>I', hdr, 0x188)
            self.assertEqual(actual, expected_code,
                f"0x188 wrong for '{std}': got 0x{actual:04x}, expected 0x{expected_code:04x}")

    def test_format_variant_at_0x18c(self):
        for std, expected_variant in m.FORMAT_VARIANTS.items():
            fps = self._fps_for(std)
            hdr = _make_header(video_standard=std, fps=fps)
            actual = _unpack('>I', hdr, 0x18C)
            self.assertEqual(actual, expected_variant,
                f"0x18C wrong for '{std}': got 0x{actual:02x}, expected 0x{expected_variant:02x}")


# ── has_key flag ───────────────────────────────────────────────────────────────

class TestHasKeyFlag(unittest.TestCase):

    def test_has_key_true_sets_play_count(self):
        hdr = _make_header(frame_count=50, has_key=True)
        self.assertEqual(_unpack('>I', hdr, 0x1A8), 50)

    def test_has_key_false_zeros_play_count(self):
        hdr = _make_header(frame_count=50, has_key=False)
        self.assertEqual(_unpack('>I', hdr, 0x1A8), 0)

    def test_has_key_true_sets_0x1b4(self):
        plane_size = 4147200
        frame_count = 25
        hdr = _make_header(plane_size=plane_size, frame_count=frame_count, has_key=True)
        expected = (plane_size * frame_count + 512) // 32
        self.assertEqual(_unpack('>I', hdr, 0x1B4), expected)

    def test_has_key_false_zeros_0x1b4(self):
        hdr = _make_header(has_key=False)
        self.assertEqual(_unpack('>I', hdr, 0x1B4), 0)


# ── auto_play / loop_play flags ────────────────────────────────────────────────

class TestPlaybackFlags(unittest.TestCase):

    def test_auto_play_sets_bit(self):
        hdr = _make_header(auto_play=True)
        code = _unpack('>I', hdr, 0x188)
        self.assertTrue(code & 0x04, "auto_play bit (0x04) not set in 0x188")

    def test_loop_play_sets_bit(self):
        hdr = _make_header(loop_play=True)
        code = _unpack('>I', hdr, 0x188)
        self.assertTrue(code & 0x08, "loop_play bit (0x08) not set in 0x188")

    def test_no_flags_by_default(self):
        hdr = _make_header()
        code = _unpack('>I', hdr, 0x188)
        self.assertFalse(code & 0x04, "auto_play bit set when it shouldn't be")
        self.assertFalse(code & 0x08, "loop_play bit set when it shouldn't be")

    def test_both_flags_together(self):
        hdr = _make_header(auto_play=True, loop_play=True)
        code = _unpack('>I', hdr, 0x188)
        self.assertTrue(code & 0x04)
        self.assertTrue(code & 0x08)


# ── Audio fields ───────────────────────────────────────────────────────────────

class TestAudioFields(unittest.TestCase):

    def test_no_audio_zeros_all_audio_fields(self):
        hdr = _make_header(has_audio=False)
        self.assertEqual(_unpack('>H', hdr, 0x1C2), 0,  "audio frame size should be 0")
        self.assertEqual(_unpack('>I', hdr, 0x1E8), 0,  "audio offset should be 0")
        self.assertEqual(_unpack('>I', hdr, 0x1EC), 0,  "audio format flag should be 0")

    def test_has_audio_sets_frame_size(self):
        hdr = _make_header(has_audio=True)
        self.assertEqual(_unpack('>H', hdr, 0x1C2), 0x1680)

    def test_has_audio_sets_format_flag(self):
        hdr = _make_header(has_audio=True)
        self.assertEqual(_unpack('>I', hdr, 0x1EC), 0x03000000)

    def test_has_audio_sets_nonzero_offset(self):
        hdr = _make_header(has_audio=True)
        self.assertGreater(_unpack('>I', hdr, 0x1E8), 0)

    def test_audio_offset_is_after_video_planes(self):
        plane_size  = 4147200
        frame_count = 25
        hdr = _make_header(plane_size=plane_size, frame_count=frame_count,
                           has_key=True, has_audio=True)
        planes_size  = plane_size * frame_count * 2   # fill + key
        expected_offset = (512 + planes_size) // 32
        self.assertEqual(_unpack('>I', hdr, 0x1E8), expected_offset)

    def test_file_size_field_includes_audio(self):
        plane_size  = 100_000
        frame_count = 10
        fps         = 25.0
        samples_per_frame    = round(48000 / fps)
        audio_bytes_per_frame = samples_per_frame * 2 * 16
        audio_data_size      = audio_bytes_per_frame * frame_count
        planes_size          = plane_size * frame_count * 2
        expected_total = 512 + planes_size + audio_data_size
        hdr = _make_header(plane_size=plane_size, frame_count=frame_count,
                           has_key=True, has_audio=True, fps=fps)
        stored = _unpack('>I', hdr, 0x1CC)
        self.assertEqual(stored, min(expected_total, 0xFFFFFFFF))


# ── Progressive→interlaced rate decision (Fix 9(a)) ────────────────────────────

class TestPToIFieldMap(unittest.TestCase):
    """_p_to_i_field_map decides how a progressive source maps onto an interlaced
    standard: weave only at the field (double) rate; block same-rate and cross-rate
    so a p→i conversion never silently doubles the playback speed."""

    WEAVE = 'tinterlace=mode=interleave_top'

    def test_double_rate_weaves(self):
        # Source at the field rate (2× the interlaced frame rate) — genuine 50Hz
        # interlaced motion. This is the confirmed, unchanged behaviour.
        for fps, std in [(50.0, '1080i50'), (59.94, '1080i5994'), (60.0, '1080i60')]:
            self.assertEqual(m._p_to_i_field_map(fps, std), self.WEAVE,
                             f'{fps} → {std} should weave')

    def test_same_rate_blocks(self):
        # Source at the interlaced FRAME rate — weaving would halve it / double speed.
        for fps, std in [(25.0, '1080i50'), (29.97, '1080i5994'), (30.0, '1080i60')]:
            with self.assertRaises(ValueError, msg=f'{fps} → {std} must block'):
                m._p_to_i_field_map(fps, std)

    def test_cross_rate_blocks(self):
        # Rates that are neither the frame nor the field rate need standards
        # conversion MacHuna does not do.
        for fps, std in [(24.0, '1080i50'), (23.976, '1080i5994'),
                         (50.0, '1080i60'), (30.0, '1080i50')]:
            with self.assertRaises(ValueError, msg=f'{fps} → {std} must block'):
                m._p_to_i_field_map(fps, std)

    def test_near_rate_within_tolerance_weaves(self):
        # 59.94 and 60 are broadcast-equivalent field rates — the 0.5fps tolerance
        # treats them as a match either way.
        self.assertEqual(m._p_to_i_field_map(59.94, '1080i60'), self.WEAVE)
        self.assertEqual(m._p_to_i_field_map(60.0, '1080i5994'), self.WEAVE)

    def test_field_order_defaults_to_tff(self):
        # Fix 10 added the field_order parameter. Every pre-existing caller omits it
        # and must keep the hardware-confirmed TFF weave byte-for-byte.
        self.assertEqual(m._p_to_i_field_map(50.0, '1080i50'), self.WEAVE)
        self.assertEqual(m._p_to_i_field_map(50.0, '1080i50', field_order='TFF'),
                         self.WEAVE)

    def test_bff_weaves_bottom_field_first(self):
        # Fix 10: the Sony TGA path passes the UI toggle through to here.
        self.assertEqual(m._p_to_i_field_map(50.0, '1080i50', field_order='BFF'),
                         'tinterlace=mode=interleave_bottom')

    def test_field_order_does_not_defeat_the_rate_guard(self):
        # Choosing BFF must not turn a blocked same-rate/cross-rate source into an
        # allowed one — the speed guard is independent of which field leads.
        for fo in ('TFF', 'BFF'):
            with self.assertRaises(ValueError, msg=f'25→1080i50 must block ({fo})'):
                m._p_to_i_field_map(25.0, '1080i50', field_order=fo)
            with self.assertRaises(ValueError, msg=f'24→1080i50 must block ({fo})'):
                m._p_to_i_field_map(24.0, '1080i50', field_order=fo)

    def test_same_rate_message_names_the_speed_problem(self):
        # The blocking error must be actionable, not a bare exception.
        try:
            m._p_to_i_field_map(25.0, '1080i50')
            self.fail('expected ValueError')
        except ValueError as e:
            self.assertIn('1080i50', str(e))
            self.assertIn('speed', str(e).lower())


class TestIToPFilter(unittest.TestCase):
    """Fix 9(b): _i_to_p_filter decides how an interlaced source maps onto a
    progressive standard. Bob-deinterlacing doubles the frame count, which is only
    correct when the target is exactly double the source frame rate; every other
    pairing needs an fps resample or the clip plays at the wrong speed."""

    def test_double_rate_target_bobs_without_resample(self):
        # Target is exactly 2x the source frame rate — bobbing lands on it exactly,
        # so no resample should be appended.
        for src_fps, std in [(25.0, '1080p50'), (29.97, '1080p5994'), (30.0, '1080p60')]:
            self.assertEqual(m._i_to_p_filter(src_fps, std), 'yadif=mode=send_field',
                             f'{src_fps} → {std} should bob with no resample')

    def test_same_rate_target_drops_fields_without_resample(self):
        # Target equals the source frame rate — one frame out per frame in.
        self.assertEqual(m._i_to_p_filter(25.0, '1080p25'), 'yadif=mode=send_frame')

    def test_cross_rate_up_appends_resample(self):
        # The Fix 9(b) bug: bobbing 25fps gives 50, but the target is 60/59.94.
        self.assertEqual(m._i_to_p_filter(25.0, '1080p60'),
                         'yadif=mode=send_field,fps=60')
        self.assertEqual(m._i_to_p_filter(25.0, '1080p5994'),
                         'yadif=mode=send_field,fps=59.94')
        # Bobbing 29.97 gives 59.94, but the target is 50 — resample down.
        self.assertEqual(m._i_to_p_filter(29.97, '1080p50'),
                         'yadif=mode=send_field,fps=50')

    def test_cross_rate_down_appends_resample(self):
        # Target below the source frame rate: send_frame keeps the source count,
        # which would run slow at the target rate, so it must resample too.
        self.assertEqual(m._i_to_p_filter(29.97, '1080p25'),
                         'yadif=mode=send_frame,fps=25')
        self.assertEqual(m._i_to_p_filter(30.0, '1080p25'),
                         'yadif=mode=send_frame,fps=25')

    def test_5994_and_60_treated_as_equivalent(self):
        # Broadcast-equivalent rates must not trigger a pointless resample —
        # same 0.5fps tolerance as _p_to_i_field_map.
        self.assertEqual(m._i_to_p_filter(30.0, '1080p5994'), 'yadif=mode=send_field')
        self.assertEqual(m._i_to_p_filter(29.97, '1080p60'), 'yadif=mode=send_field')

    def test_parity_injected_only_when_asked(self):
        # Concat-of-stills callers must pass parity (no field metadata in the
        # stream); real-video callers must not, so yadif reads the stream's flags.
        self.assertEqual(m._i_to_p_filter(25.0, '1080p50', parity='tff'),
                         'yadif=mode=send_field:parity=tff')
        self.assertEqual(m._i_to_p_filter(25.0, '1080p60', parity='bff'),
                         'yadif=mode=send_field:parity=bff,fps=60')
        self.assertNotIn('parity', m._i_to_p_filter(25.0, '1080p50'))

    def test_every_interlaced_to_progressive_pairing_lands_on_target(self):
        # Sweep every real i→p pairing and assert the filter chain accounts for the
        # target rate: either bobbing/dropping already lands on it, or an fps
        # resample to it is present. This is the property the bug violated.
        interlaced = {'1080i50': 25.0, '1080i5994': 29.97, '1080i60': 30.0}
        for src_std, src_fps in interlaced.items():
            for out_std in ('1080p25', '1080p50', '1080p5994', '1080p60'):
                vf = m._i_to_p_filter(src_fps, out_std)
                target = m.FORMAT_VARIANT_FPS[m.FORMAT_VARIANTS[out_std]]
                produced = src_fps * 2 if 'send_field' in vf else src_fps
                if abs(produced - target) > 0.5:
                    self.assertIn(f'fps={target:g}', vf,
                                  f'{src_std} → {out_std} needs a resample to {target}')
                else:
                    self.assertNotIn('fps=', vf,
                                     f'{src_std} → {out_std} should need no resample')


class TestEifFpsResample(unittest.TestCase):
    """Fix 14: convert_clip_to_eif must resample the source to the EIF header
    rate (25/50) so the number of frames written matches the fps stamped in the
    header. Otherwise a non-25/50 source (30/29.97/60/59.94fps) is extracted at
    its own rate while the header claims 25/50, and the K-Frame plays it at the
    wrong speed."""

    class _Stop(Exception):
        """Sentinel raised once we've captured what we need, to avoid running
        ffmpeg / the frame encoder."""

    def setUp(self):
        self._orig_info   = m.get_video_info
        self._orig_v210   = m.convert_to_v210
        self._orig_header = m._build_eif_header
        self.captured = {}

        def fake_v210(input_path, output_path, **kwargs):
            # Record the resample instruction and leave a sparse 1-frame file
            # so frame_count computes to 1 (no real bytes written to disk).
            self.captured['vf_extra'] = kwargs.get('vf_extra')
            with open(output_path, 'wb') as f:
                f.truncate(m._EIF_PLANE_SIZE)
            return None  # no key plane

        def fake_header(clip_name, frame_count, fps, **_kw):
            self.captured['header_fps'] = fps
            raise TestEifFpsResample._Stop

        m.convert_to_v210   = fake_v210
        m._build_eif_header = fake_header

    def tearDown(self):
        m.get_video_info   = self._orig_info
        m.convert_to_v210  = self._orig_v210
        m._build_eif_header = self._orig_header

    def _run_for(self, source_fps):
        m.get_video_info = lambda p: {
            'fps': source_fps, 'has_alpha': False, 'has_audio': False,
            'width': 1920, 'height': 1080,
        }
        with self.assertRaises(TestEifFpsResample._Stop):
            m.convert_clip_to_eif('dummy.mov', '.', log=lambda *a, **k: None)
        return self.captured['vf_extra'], self.captured['header_fps']

    def test_resample_target_always_matches_header_fps(self):
        # The invariant that guarantees correct playback speed: whatever rate we
        # resample to must equal the rate we stamp in the header.
        for src in (24.0, 23.976, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0):
            vf_extra, header_fps = self._run_for(src)
            self.assertEqual(vf_extra, f'fps={header_fps:g}',
                             msg=f'{src}fps: resample {vf_extra} != header {header_fps}')

    def test_60fps_source_resampled_to_50(self):
        vf_extra, _ = self._run_for(60.0)
        self.assertEqual(vf_extra, 'fps=50')

    def test_5994_source_resampled_to_50(self):
        vf_extra, _ = self._run_for(59.94)
        self.assertEqual(vf_extra, 'fps=50')

    def test_30fps_source_resampled_to_25(self):
        vf_extra, _ = self._run_for(30.0)
        self.assertEqual(vf_extra, 'fps=25')

    def test_2997_source_resampled_to_25(self):
        vf_extra, _ = self._run_for(29.97)
        self.assertEqual(vf_extra, 'fps=25')

    def test_already_25_stays_25(self):
        vf_extra, _ = self._run_for(25.0)
        self.assertEqual(vf_extra, 'fps=25')

    def test_already_50_stays_50(self):
        vf_extra, _ = self._run_for(50.0)
        self.assertEqual(vf_extra, 'fps=50')


# ── Bespoke per-item output IDs ────────────────────────────────────────────────

class TestBespokeNormalise(unittest.TestCase):
    """normalise_bespoke_value: what counts as a usable ID."""

    def test_number_in_range(self):
        self.assertEqual(m.normalise_bespoke_value('7', m.BESPOKE_MODE_SWS), 7)
        self.assertEqual(m.normalise_bespoke_value(' 42 ', m.BESPOKE_MODE_EIF), 42)
        self.assertEqual(m.normalise_bespoke_value('9999', m.BESPOKE_MODE_SWS), 9999)

    def test_number_blank_or_out_of_range(self):
        for bad in ('', '   ', '0', '10000', 'abc', '1.5', '-3', None):
            self.assertIsNone(m.normalise_bespoke_value(bad, m.BESPOKE_MODE_SWS), bad)

    def test_sony_name_four_alnum_uppercased(self):
        self.assertEqual(m.normalise_bespoke_value('wipe', m.BESPOKE_MODE_SONY), 'WIPE')
        self.assertEqual(m.normalise_bespoke_value(' bg01 ', m.BESPOKE_MODE_SONY), 'BG01')

    def test_sony_name_rejected(self):
        for bad in ('', 'ABC', 'ABCDE', 'AB-1', 'AB 1', None):
            self.assertIsNone(m.normalise_bespoke_value(bad, m.BESPOKE_MODE_SONY), bad)

    def test_output_names(self):
        self.assertEqual(m.bespoke_output_name(7, m.BESPOKE_MODE_SWS), '7.SWS')
        self.assertEqual(m.bespoke_output_name(7, m.BESPOKE_MODE_EIF), '0007.eif')
        self.assertEqual(m.bespoke_output_name('WIPE', m.BESPOKE_MODE_SONY), 'WIPE')


class TestBespokeValidation(unittest.TestCase):
    """validate_bespoke_ids: blank/range, in-batch duplicates, destination clashes.

    Every failure blocks — there is no overwrite path — so each test asserts
    both that a problem is reported and that the offending item is named.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dest = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    # -- valid batches --

    def test_valid_numbers_pass(self):
        entries = [('clip_a.mov', '1'), ('clip_b.mov', '2'), ('clip_c.mov', '9999')]
        self.assertEqual(m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SWS, self.dest), [])

    def test_valid_sony_names_pass(self):
        entries = [('clip_a.mov', 'WIPE'), ('clip_b.mov', 'bg01')]
        self.assertEqual(m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SONY, self.dest), [])

    # -- blank / out of range --

    def test_blank_field_blocks_and_names_item(self):
        entries = [('clip_a.mov', '3'), ('clip_b.mov', '')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SWS, self.dest)
        self.assertEqual(len(problems), 1)
        self.assertIn('clip_b.mov', problems[0])
        self.assertNotIn('clip_a.mov', problems[0])

    def test_out_of_range_number_blocks(self):
        entries = [('clip_a.mov', '0'), ('clip_b.mov', '10000'), ('clip_c.mov', '5')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SWS, self.dest)
        self.assertEqual(len(problems), 1)
        self.assertIn('clip_a.mov', problems[0])
        self.assertIn('clip_b.mov', problems[0])

    def test_short_sony_name_blocks(self):
        entries = [('clip_a.mov', 'AB'), ('clip_b.mov', 'GOOD')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SONY, self.dest)
        self.assertEqual(len(problems), 1)
        self.assertIn('clip_a.mov', problems[0])

    # -- duplicates within the batch --

    def test_duplicate_numbers_block(self):
        entries = [('clip_a.mov', '4'), ('clip_b.mov', '4'), ('clip_c.mov', '5')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SWS, self.dest)
        self.assertEqual(len(problems), 1)
        self.assertIn('clip_a.mov', problems[0])
        self.assertIn('clip_b.mov', problems[0])
        self.assertNotIn('clip_c.mov', problems[0])

    def test_duplicate_numbers_ignore_leading_zeros(self):
        entries = [('clip_a.mov', '7'), ('clip_b.mov', '007')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_EIF, self.dest)
        self.assertEqual(len(problems), 1)

    def test_duplicate_sony_names_block_case_insensitively(self):
        entries = [('clip_a.mov', 'WIPE'), ('clip_b.mov', 'wipe')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SONY, self.dest)
        self.assertEqual(len(problems), 1)
        self.assertIn('clip_a.mov', problems[0])
        self.assertIn('clip_b.mov', problems[0])

    # -- collisions with the destination folder --

    def test_existing_sws_file_blocks(self):
        Path(self.dest, '3.SWS').write_bytes(b'x')
        entries = [('clip_a.mov', '3'), ('clip_b.mov', '4')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SWS, self.dest)
        self.assertEqual(len(problems), 1)
        self.assertIn('3.SWS', problems[0])
        self.assertIn('clip_a.mov', problems[0])

    def test_existing_split_sws_folder_blocks(self):
        # A >4GB SWS is written as a folder called <N>.SWS, not a file.
        Path(self.dest, '12.SWS').mkdir()
        entries = [('clip_a.mov', '12')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SWS, self.dest)
        self.assertEqual(len(problems), 1)
        self.assertIn('split-file folder', problems[0])
        self.assertIn('12.SWS', problems[0])

    def test_existing_eif_slot_blocks(self):
        Path(self.dest, '0004.eif').write_bytes(b'x')
        entries = [('clip_a.mov', '4'), ('clip_b.mov', '5')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_EIF, self.dest)
        self.assertEqual(len(problems), 1)
        self.assertIn('0004.eif', problems[0])

    def test_existing_sony_folder_blocks(self):
        Path(self.dest, 'WIPE').mkdir()
        entries = [('clip_a.mov', 'wipe'), ('clip_b.mov', 'BG01')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SONY, self.dest)
        self.assertEqual(len(problems), 1)
        self.assertIn('WIPE', problems[0])
        self.assertIn('clip_a.mov', problems[0])

    def test_unrelated_files_do_not_block(self):
        Path(self.dest, '3.SWS').write_bytes(b'x')
        entries = [('clip_a.mov', '4'), ('clip_b.mov', '5')]
        self.assertEqual(m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SWS, self.dest), [])

    def test_missing_destination_folder_skips_collision_check(self):
        entries = [('clip_a.mov', '1')]
        self.assertEqual(
            m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SWS,
                                   os.path.join(self.dest, 'not_created_yet')), [])

    # -- all three at once --

    def test_all_three_problems_reported_together(self):
        Path(self.dest, '9.SWS').write_bytes(b'x')
        entries = [('clip_a.mov', ''), ('clip_b.mov', '2'),
                   ('clip_c.mov', '2'), ('clip_d.mov', '9')]
        problems = m.validate_bespoke_ids(entries, m.BESPOKE_MODE_SWS, self.dest)
        self.assertEqual(len(problems), 3)


class TestMergeInputTypes(unittest.TestCase):
    """merge_input_types: which selections can be combined by "Add to List"."""

    def test_first_selection_takes_the_incoming_type(self):
        self.assertEqual(m.merge_input_types(None, 'from_sws'), 'from_sws')

    def test_same_type_is_unchanged(self):
        for t in ('to_sws_only', 'mov_only', 'from_sws', 'from_eif', 'mixed_eif_sws'):
            self.assertEqual(m.merge_input_types(t, t), t)

    def test_mov_widens_to_to_sws_only_when_mixed_with_other_media(self):
        self.assertEqual(m.merge_input_types('mov_only', 'to_sws_only'), 'to_sws_only')
        self.assertEqual(m.merge_input_types('to_sws_only', 'mov_only'), 'to_sws_only')

    def test_sws_plus_eif_becomes_mixed(self):
        self.assertEqual(m.merge_input_types('from_sws', 'from_eif'), 'mixed_eif_sws')
        self.assertEqual(m.merge_input_types('from_eif', 'from_sws'), 'mixed_eif_sws')
        self.assertEqual(m.merge_input_types('mixed_eif_sws', 'from_sws'), 'mixed_eif_sws')

    def test_encoding_and_extracting_cannot_be_combined(self):
        for a, b in (('to_sws_only', 'from_sws'), ('from_sws', 'mov_only'),
                     ('mov_only', 'from_eif'), ('mixed_eif_sws', 'to_sws_only')):
            self.assertIsNone(m.merge_input_types(a, b), f'{a}+{b}')

    def test_unknown_type_is_rejected(self):
        self.assertIsNone(m.merge_input_types('to_sws_only', 'mixed_error'))
        self.assertIsNone(m.merge_input_types('mixed_error', 'to_sws_only'))


class TestBespokeRowIssues(unittest.TestCase):
    """bespoke_row_issues: the per-row codes that mark fields in the panel.

    Index-aligned with the rows, so the GUI can flag exactly the fields that
    need attention rather than only naming them in the dialog.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dest = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_all_good_rows_are_none(self):
        entries = [('a.mov', '1'), ('b.mov', '2')]
        self.assertEqual(m.bespoke_row_issues(entries, m.BESPOKE_MODE_SWS, self.dest),
                         [None, None])

    def test_only_the_offending_rows_are_flagged(self):
        entries = [('a.mov', '1'), ('b.mov', ''), ('c.mov', '3')]
        self.assertEqual(m.bespoke_row_issues(entries, m.BESPOKE_MODE_SWS, self.dest),
                         [None, m.BESPOKE_ISSUE_INVALID, None])

    def test_both_halves_of_a_duplicate_are_flagged(self):
        entries = [('a.mov', '4'), ('b.mov', '5'), ('c.mov', '4')]
        self.assertEqual(m.bespoke_row_issues(entries, m.BESPOKE_MODE_SWS, self.dest),
                         [m.BESPOKE_ISSUE_DUPLICATE, None, m.BESPOKE_ISSUE_DUPLICATE])

    def test_collision_row_is_flagged(self):
        Path(self.dest, '7.SWS').write_bytes(b'x')
        entries = [('a.mov', '6'), ('b.mov', '7')]
        self.assertEqual(m.bespoke_row_issues(entries, m.BESPOKE_MODE_SWS, self.dest),
                         [None, m.BESPOKE_ISSUE_EXISTS])

    def test_split_folder_collision_is_flagged(self):
        Path(self.dest, '8.SWS').mkdir()
        self.assertEqual(m.bespoke_row_issues([('a.mov', '8')], m.BESPOKE_MODE_SWS, self.dest),
                         [m.BESPOKE_ISSUE_EXISTS])

    def test_duplicate_wins_over_collision_on_the_same_row(self):
        # Both are the same edit to fix, and "duplicate" is the more specific
        # thing to tell the user about.
        Path(self.dest, '3.SWS').write_bytes(b'x')
        entries = [('a.mov', '3'), ('b.mov', '3')]
        self.assertEqual(m.bespoke_row_issues(entries, m.BESPOKE_MODE_SWS, self.dest),
                         [m.BESPOKE_ISSUE_DUPLICATE, m.BESPOKE_ISSUE_DUPLICATE])

    def test_sony_names_flagged_the_same_way(self):
        Path(self.dest, 'WIPE').mkdir()
        entries = [('a.mov', 'ABC'), ('b.mov', 'wipe'), ('c.mov', 'GOOD')]
        self.assertEqual(m.bespoke_row_issues(entries, m.BESPOKE_MODE_SONY, self.dest),
                         [m.BESPOKE_ISSUE_INVALID, m.BESPOKE_ISSUE_EXISTS, None])

    def test_codes_stay_aligned_with_every_row(self):
        entries = [('a.mov', str(i)) for i in range(1, 8)]
        self.assertEqual(len(m.bespoke_row_issues(entries, m.BESPOKE_MODE_EIF, self.dest)), 7)

    def test_hint_column_is_wide_enough_for_every_issue_text(self):
        # The panel is measured once at rebuild; a mark wider than the reserved
        # column would be clipped (the v1.6.17 truncation bug).
        longest = max(len(t) for pair in (("needs a name", "needs a number"),
                                          ("duplicate name", "duplicate number"),
                                          ("already in use", "already in use"))
                      for t in pair)
        self.assertGreaterEqual(m._BESPOKE_HINT_WIDTH, longest)


if __name__ == '__main__':
    unittest.main(verbosity=2)


# ── update check ──────────────────────────────────────────────────────────────
#
# These decide whether somebody is told to go and download software, so they are
# worth covering properly. The network fetch itself is not unit tested; the
# parsing and comparison around it are.

class TestParseVersion(unittest.TestCase):

    def test_plain_three_part(self):
        self.assertEqual(m.parse_version('1.6.21'), (1, 6, 21, 0))

    def test_short_forms_pad_out(self):
        self.assertEqual(m.parse_version('1.7'), m.parse_version('1.7.0'))
        self.assertEqual(m.parse_version('2'), (2, 0, 0, 0))

    def test_whitespace_tolerated(self):
        self.assertEqual(m.parse_version('  1.6.21  '), (1, 6, 21, 0))

    def test_rejects_anything_it_cannot_read_exactly(self):
        for bad in ('1.7.0-beta1', 'v1.7.0', '1.7.0a', '1..7', '1.7.', '', '   ',
                    'one.seven', '1.7.0.0.0', None, 1.7, ['1', '7']):
            with self.subTest(bad=bad):
                self.assertIsNone(m.parse_version(bad))


class TestIsUpdateAvailable(unittest.TestCase):

    def test_newer_patch_is_an_update(self):
        self.assertTrue(m.is_update_available('1.6.22', '1.6.21'))

    def test_newer_minor_beats_a_bigger_patch_number(self):
        # plain string comparison gets this wrong: '1.7.0' sorts below '1.6.21'
        self.assertTrue(m.is_update_available('1.7.0', '1.6.21'))

    def test_same_version_is_not_an_update(self):
        self.assertFalse(m.is_update_available('1.6.21', '1.6.21'))

    def test_older_is_never_an_update(self):
        # a rolled-back or mistyped manifest must never prompt a downgrade
        self.assertFalse(m.is_update_available('1.6.20', '1.6.21'))

    def test_equivalent_short_form_is_not_an_update(self):
        self.assertFalse(m.is_update_available('1.7', '1.7.0'))

    def test_unreadable_version_is_never_an_update(self):
        self.assertFalse(m.is_update_available('banana', '1.6.21'))
        self.assertFalse(m.is_update_available('1.7.0', 'banana'))

    def test_defaults_to_the_running_version(self):
        self.assertFalse(m.is_update_available(m.VERSION))


class TestParseUpdateManifest(unittest.TestCase):

    GOOD = json.dumps({
        'version': '1.7.0',
        'released': '2026-09-08',
        'summary': 'Something changed.',
        'download': 'https://downloads.dnsvision.tv/MacHuna-1.7.0.zip',
    })

    def test_reads_a_good_manifest(self):
        out = m.parse_update_manifest(self.GOOD)
        self.assertEqual(out['version'], '1.7.0')
        self.assertEqual(out['summary'], 'Something changed.')
        self.assertTrue(out['download'].startswith('https://'))

    def test_summary_is_optional(self):
        raw = json.dumps({'version': '1.7.0', 'download': 'https://example.com/a.zip'})
        self.assertEqual(m.parse_update_manifest(raw)['summary'], '')

    def test_rejects_malformed_manifests(self):
        for raw in ('', 'not json at all', '[]', 'null', '"a string"',
                    json.dumps({'download': 'https://example.com/a.zip'}),
                    json.dumps({'version': '1.7.0'}),
                    json.dumps({'version': 'beta', 'download': 'https://e.com/a'})):
            with self.subTest(raw=raw[:40]):
                self.assertIsNone(m.parse_update_manifest(raw))

    def test_download_url_must_be_https(self):
        # the URL is handed straight to `open`, so anything else is refused
        for url in ('http://downloads.dnsvision.tv/a.zip', 'file:///etc/passwd',
                    'javascript:alert(1)', 'ftp://example.com/a.zip', '', 42):
            with self.subTest(url=url):
                raw = json.dumps({'version': '1.7.0', 'download': url})
                self.assertIsNone(m.parse_update_manifest(raw))

    def test_live_manifest_url_is_https(self):
        self.assertTrue(m.UPDATE_MANIFEST_URL.startswith('https://'))


class TestContactEmail(unittest.TestCase):

    def test_body_carries_the_details_a_report_needs(self):
        body = m.build_contact_body('problem',
                                    {'standard': '1080i50', 'output': 'Kahuna SWS'})
        self.assertIn(m.VERSION, body)
        self.assertIn('1080i50', body)
        self.assertIn('Kahuna SWS', body)
        self.assertIn('What happened:', body)

    def test_feature_request_asks_a_different_question(self):
        body = m.build_contact_body('feature')
        self.assertIn('What I would like MacHuna to do:', body)
        self.assertNotIn('What happened:', body)

    def test_absent_context_lines_are_left_out(self):
        body = m.build_contact_body('problem', {'standard': '1080i50'})
        self.assertNotIn('Source', body)
        self.assertNotIn('Log', body)

    def test_mailto_is_addressed_and_encoded(self):
        url = m.build_mailto('problem', {'standard': '1080i50'})
        self.assertTrue(url.startswith('mailto:%s?' % m.CONTACT_EMAIL))
        self.assertNotIn(' ', url)          # spaces must be percent-encoded
        self.assertIn('subject=', url)
        self.assertIn('body=', url)

    def test_mailto_survives_a_round_trip(self):
        url = m.build_mailto('feature')
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        self.assertIn(m.VERSION, query['subject'][0])
        self.assertIn('What I would like MacHuna to do:', query['body'][0])


# ── unverified-output notices (v1.7.1) ────────────────────────────────────────

class TestUnverifiedOutputNotes(unittest.TestCase):
    """The mechanism for warning that an output has never been loaded on its
    desk. Emptied on 2026-10-08: K-Frame EIF and K-Frame TGA were confirmed on
    a live K-Frame on 2026-10-07, and David lifted the Sony TGA warning on his
    own judgement the same day. The mechanism stays for the next new output."""

    def test_kahuna_sws_is_never_warned_about(self):
        self.assertIsNone(m.unverified_output_note('Kahuna SWS'))

    def test_no_desk_output_carries_a_hardware_warning(self):
        for out in ('Kahuna SWS', 'K-Frame EIF', 'K-Frame TGA', 'Sony TGA',
                    'TGA Sequence', 'QuickTime MOV'):
            with self.subTest(out=out):
                self.assertIsNone(m.unverified_output_note(out))
        self.assertEqual(m.UNVERIFIED_OUTPUT_NOTES, {})

    def test_unknown_output_is_silent(self):
        self.assertIsNone(m.unverified_output_note('something else'))
        self.assertIsNone(m.unverified_output_note(''))

    def test_the_proceed_anyway_dialogs_are_gone(self):
        """The Tk app asked "has not been tested on hardware... Proceed
        anyway?" before EIF output and MOV to TGA. Both are now proven."""
        src = Path(m.__file__).read_text()
        self.assertFalse('has not been tested on hardware' in src)
        self.assertFalse('Proceed anyway?' in src)

    def test_no_unconfirmed_markers_remain_for_lifted_outputs(self):
        src = Path(m.__file__).read_text()
        for marker in ('UNCONFIRMED: EIF output', 'UNCONFIRMED: generated EIF',
                       'UNCONFIRMED: K-Frame TGA', 'UNCONFIRMED — awaiting'):
            with self.subTest(marker=marker):
                self.assertFalse(marker in src, f'{marker!r} still in machuna.py')

    def test_quicktime_mov_is_not_a_desk_output(self):
        # A ProRes 4444 file is an ordinary video file. There is no desk to
        # confirm it against, so warning about it would be false caution -
        # the same reasoning that keeps Kahuna SWS silent.
        self.assertIsNone(m.unverified_output_note('QuickTime MOV'))
        self.assertIsNone(m.missing_feature_note('QuickTime MOV'))


class TestMissingFeatureNotes(unittest.TestCase):
    """The mechanism for declaring a feature ABSENT, as distinct from
    unproven. Its one entry, EIF audio, was retired on 2026-10-08 when .eaf
    writing landed; the mechanism stays for the next one."""

    def test_eif_audio_is_no_longer_declared_missing(self):
        self.assertIsNone(m.missing_feature_note('K-Frame EIF'))

    def test_no_output_currently_declares_a_missing_feature(self):
        for out in ('Kahuna SWS', 'K-Frame EIF', 'K-Frame TGA', 'Sony TGA',
                    'TGA Sequence', 'QuickTime MOV'):
            with self.subTest(out=out):
                self.assertIsNone(m.missing_feature_note(out))
        self.assertEqual(m.MISSING_FEATURE_NOTES, {})


class TestUsableGeometry(unittest.TestCase):
    """The settings file outlives an update. Every user from before the item
    list has a geometry saved from when the window was 460px tall, and would
    otherwise open too small to see the log."""

    def test_too_short_is_grown(self):
        self.assertEqual(m.usable_geometry('1085x460'), '1085x700')

    def test_position_is_preserved_while_growing(self):
        self.assertEqual(m.usable_geometry('1085x460+35+113'), '1085x700+35+113')
        self.assertEqual(m.usable_geometry('900x400-10-20'), '1000x700-10-20')

    def test_a_deliberately_large_window_is_left_alone(self):
        for g in ('1400x900+10+10', '1600x1000', '1120x740'):
            with self.subTest(g=g):
                self.assertEqual(m.usable_geometry(g), g)

    def test_only_the_short_dimension_changes(self):
        self.assertEqual(m.usable_geometry('1600x400'), '1600x700')
        self.assertEqual(m.usable_geometry('700x900'), '1000x900')

    def test_missing_or_malformed_falls_back_to_the_default(self):
        default = f'{m.WINDOW_DEFAULT_W}x{m.WINDOW_DEFAULT_H}'
        for g in (None, '', '   ', 'rubbish', '1085', 'x460', '10x20x30', 42):
            with self.subTest(g=g):
                self.assertEqual(m.usable_geometry(g), default)

    def test_the_default_clears_the_minimum(self):
        self.assertGreaterEqual(m.WINDOW_DEFAULT_W, m.WINDOW_MIN_W)
        self.assertGreaterEqual(m.WINDOW_DEFAULT_H, m.WINDOW_MIN_H)


# ── structural guards ─────────────────────────────────────────────────────────
#
# These read machuna.py's own syntax tree. They exist because of a real bug: the
# per-row "done" marking was wired into only one of four conversion paths, so
# three of them converted perfectly and then said nothing. A behavioural test
# caught it eventually; these would have caught it immediately, and will catch
# the next path somebody adds.
#
# They assert that a call EXISTS, not that it is correct - a weak claim, but the
# one that the expensive bugs have actually violated.

def _launch_gui_tree():
    import ast
    src = Path(__file__).with_name('machuna.py').read_text()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.FunctionDef) and node.name == 'launch_gui':
            return node
    raise AssertionError('launch_gui not found in machuna.py')


def _nested_functions(tree):
    import ast
    return {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}


def _calls_within(node):
    import ast
    names = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            f = sub.func
            if isinstance(f, ast.Name):
                names.add(f.id)
            elif isinstance(f, ast.Attribute):
                names.add(f.attr)
        # a call passed to root.after as a lambda still counts
        elif isinstance(sub, ast.Name):
            names.add(sub.id)
    return names


class TestEveryConversionPathReportsBack(unittest.TestCase):
    """Every runner must mark its rows, or a conversion succeeds in silence."""

    RUNNERS = ('_run_to_sws', '_run_to_eif', '_run_to_tga_seq', '_run_from_sws')

    def setUp(self):
        self.fns = _nested_functions(_launch_gui_tree())

    def test_all_four_runners_exist(self):
        for name in self.RUNNERS:
            with self.subTest(runner=name):
                self.assertIn(name, self.fns)

    def test_every_runner_marks_its_rows(self):
        for name in self.RUNNERS:
            with self.subTest(runner=name):
                self.assertIn('_mark_row', _calls_within(self.fns[name]),
                              f'{name} converts without ever marking a row done - '
                              f'the conversion works and the list stays blank')

    def test_every_runner_writes_a_batch_log(self):
        for name in self.RUNNERS:
            if name == '_run_from_sws':
                continue          # hands the whole batch to _hula_run_batch
            with self.subTest(runner=name):
                self.assertIn('_write_batch_log', _calls_within(self.fns[name]))

    def test_no_runner_still_uses_the_removed_numbering_controls(self):
        gone = ('start_num_var', 'use_source_num_var', 'eif_slot_var', 'bespoke_var')
        for name in self.RUNNERS:
            names = _calls_within(self.fns[name])
            for dead in gone:
                with self.subTest(runner=name, name=dead):
                    self.assertNotIn(dead, names)


class TestRemovedCodeStaysRemoved(unittest.TestCase):
    """Things deleted on purpose, which a well-meaning edit could reintroduce."""

    def setUp(self):
        self.src = Path(__file__).with_name('machuna.py').read_text()

    def test_parse_filename_is_gone(self):
        # removed with "Use source file number"; its only consumer
        self.assertNotIn('def parse_filename', self.src)

    def test_no_source_num_on_scanned_items(self):
        self.assertNotIn("'source_num'", self.src)

    def test_update_check_does_not_use_pythons_https(self):
        # the bundled app carries Homebrew's libssl, whose CA path exists on no
        # other Mac - Python HTTPS would fail everywhere but the build machine,
        # silently. See fetch_update_manifest().
        for banned in ('urllib.request', 'urlopen', 'http.client', 'requests.get'):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, self.src)

    def test_certificate_verification_is_never_disabled(self):
        for banned in ('_create_unverified_context', 'CERT_NONE',
                       'verify=False', '--insecure', 'check_hostname = False'):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, self.src)


# ── split SWS files ───────────────────────────────────────────────────────────

class TestSplitDetection(unittest.TestCase):
    """A clip over 4GB is a FOLDER of 2GB chunks. The player could not open one
    at all: the file dialog navigates into the folder, so the user reached a
    chunk, and only the first chunk has a header."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _make(self, name, parts):
        d = os.path.join(self.tmp, name)
        os.makedirs(d, exist_ok=True)
        for p, data in parts.items():
            with open(os.path.join(d, p), 'wb') as f:
                f.write(data)
        return d

    def test_a_complete_set_is_found_in_order(self):
        d = self._make('1.SWS', {'02_OF_03._XX': b'b', '01_OF_03._XX': b'a',
                                 '03_OF_03._XX': b'c'})
        self.assertEqual([os.path.basename(p) for p in m.split_parts(d)],
                         ['01_OF_03._XX', '02_OF_03._XX', '03_OF_03._XX'])

    def test_ordering_is_numeric_not_alphabetical(self):
        parts = {f'{i:02d}_OF_12._XX': b'x' for i in range(1, 13)}
        d = self._make('2.SWS', parts)
        got = [os.path.basename(p) for p in m.split_parts(d)]
        self.assertEqual(got[0], '01_OF_12._XX')
        self.assertEqual(got[-1], '12_OF_12._XX')

    def test_an_incomplete_set_is_refused(self):
        # a missing chunk means a truncated clip; playing what survived would
        # be worse than refusing
        d = self._make('3.SWS', {'01_OF_03._XX': b'a', '03_OF_03._XX': b'c'})
        self.assertEqual(m.split_parts(d), [])

    def test_chunks_disagreeing_about_the_total_are_refused(self):
        d = self._make('4.SWS', {'01_OF_03._XX': b'a', '02_OF_04._XX': b'b'})
        self.assertEqual(m.split_parts(d), [])

    def test_an_ordinary_folder_is_not_a_split(self):
        d = self._make('5.SWS', {'notes.txt': b'x'})
        self.assertEqual(m.split_parts(d), [])
        self.assertEqual(m.resolve_split(d), [])

    def test_selecting_any_part_resolves_the_whole_clip(self):
        d = self._make('6.SWS', {'01_OF_02._XX': b'a', '02_OF_02._XX': b'b'})
        for part in ('01_OF_02._XX', '02_OF_02._XX'):
            with self.subTest(part=part):
                self.assertEqual(len(m.resolve_split(os.path.join(d, part))), 2)

    def test_a_plain_file_is_not_a_split(self):
        f = os.path.join(self.tmp, 'plain.SWS')
        open(f, 'wb').write(b'x')
        self.assertEqual(m.resolve_split(f), [])
        self.assertEqual(m.resolve_split(os.path.join(self.tmp, 'nope')), [])


class TestSplitReader(unittest.TestCase):
    """Reads across the chunk joins as though they were one file."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        d = os.path.join(self.tmp, '1.SWS')
        os.makedirs(d)
        self.data = bytes(range(256)) * 40          # 10240 bytes
        for i, start in enumerate(range(0, len(self.data), 4096), start=1):
            with open(os.path.join(d, f'{i:02d}_OF_03._XX'), 'wb') as f:
                f.write(self.data[start:start + 4096])
        self.r = m.SplitReader(m.split_parts(d))

    def tearDown(self):
        self.r.close()

    def test_total_size_spans_every_chunk(self):
        self.assertEqual(self.r.total, len(self.data))

    def test_reading_the_whole_thing_matches(self):
        self.r.seek(0)
        self.assertEqual(self.r.read(), self.data)

    def test_a_read_spanning_a_join_is_correct(self):
        # the case that matters: a frame straddling two chunks
        self.r.seek(4000)
        self.assertEqual(self.r.read(200), self.data[4000:4200])

    def test_a_read_spanning_two_joins_is_correct(self):
        self.r.seek(4090)
        self.assertEqual(self.r.read(4100), self.data[4090:8190])

    def test_seek_and_tell_agree(self):
        self.r.seek(1234)
        self.assertEqual(self.r.tell(), 1234)
        self.r.read(10)
        self.assertEqual(self.r.tell(), 1244)

    def test_reading_past_the_end_returns_what_exists(self):
        self.r.seek(len(self.data) - 10)
        self.assertEqual(self.r.read(500), self.data[-10:])
        self.assertEqual(self.r.read(10), b'')


class TestDataOffset(unittest.TestCase):
    """Where the video planes start is written at 0x19C, and is not always 512.

    Some K-Watch files carry a 3072-byte header. Reading those from 512 starts
    every frame 2560 bytes early - exactly half a v210 line - and the picture
    appears split down the middle with the halves swapped. Found by David on a
    1440-frame UCL clip once split files could be opened at all.
    """

    def _hdr(self, value):
        raw = bytearray(machuna_header_stub())
        struct.pack_into('>I', raw, m.OFF_DATA_START, value)
        return bytes(raw)

    def test_the_declared_offset_is_used(self):
        self.assertEqual(m.sws_data_offset(self._hdr(3072)), 3072)
        self.assertEqual(m.sws_data_offset(self._hdr(512)), 512)

    def test_implausible_values_fall_back_to_512(self):
        for bad in (0, 4, 511, 513, 1 << 24, 0xFFFFFFFF):
            with self.subTest(bad=bad):
                self.assertEqual(m.sws_data_offset(self._hdr(bad)), m.SWS_HEADER_SIZE)

    def test_a_short_or_empty_header_falls_back(self):
        self.assertEqual(m.sws_data_offset(b''), m.SWS_HEADER_SIZE)
        self.assertEqual(m.sws_data_offset(b'\x00' * 16), m.SWS_HEADER_SIZE)

    def test_machuna_writes_its_own_header_size_there(self):
        # the field has always been written; it was simply never read back
        hdr = m.build_sws_header('x.mov', 'clip', 1920, 1080, 5529600, 10, '1080p50')
        self.assertEqual(struct.unpack_from('>I', hdr, m.OFF_DATA_START)[0],
                         m.SWS_HEADER_SIZE)
        self.assertEqual(m.sws_data_offset(hdr), m.SWS_HEADER_SIZE)

    def test_half_a_v210_line_is_the_shear_that_was_seen(self):
        # 1920-pixel v210 line is 5120 bytes; 3072 - 512 is half of it, which is
        # why the picture looked split down the middle rather than scrambled
        line = (1920 // 6) * 16
        self.assertEqual(3072 - m.SWS_HEADER_SIZE, line // 2)


def machuna_header_stub():
    return m.build_sws_header('x.mov', 'clip', 1920, 1080, 5529600, 10, '1080p50')


class TestVersionOrderingAcrossTheTensBoundary(unittest.TestCase):
    """1.10.0 must sort above 1.9.x.

    Compared as strings, "1.10.0" < "1.9.3", so every user on 1.9.x would be
    told they were up to date forever. The comparison is numeric and this
    keeps it that way.
    """

    def test_ten_is_newer_than_nine(self):
        self.assertTrue(m.is_update_available('1.10.0', '1.9.3'))
        self.assertTrue(m.is_update_available('1.10.1', '1.10.0'))
        self.assertTrue(m.is_update_available('2.0.0', '1.99.99'))

    def test_nine_is_not_newer_than_ten(self):
        self.assertFalse(m.is_update_available('1.9.3', '1.10.0'))
        self.assertFalse(m.is_update_available('1.10.0', '1.10.0'))


class TestOutputLabelsMatchTheirNotes(unittest.TestCase):
    """The dropdown labels double as keys into the warning dictionaries.

    They live inside launch_gui() where no unit test can reach them, so if a
    rename touches one side and not the other, every hardware warning silently
    stops appearing and the suite stays green. That nearly happened during the
    Kayenne-to-K-Frame rename: the labels and the keys are the same strings by
    convention and nothing enforced it. This does.
    """

    def _output_constants(self):
        import ast
        consts = {}
        for node in ast.walk(_launch_gui_tree()):
            if not isinstance(node, ast.Assign):
                continue
            for t in node.targets:
                if (isinstance(t, ast.Name) and t.id.startswith('OUTPUT_')
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)):
                    consts[t.id] = node.value.value
        return consts

    def test_the_constants_are_found_at_all(self):
        # If this breaks, the guard below is silently testing nothing.
        consts = self._output_constants()
        self.assertGreaterEqual(len(consts), 5, consts)
        self.assertIn('Kahuna SWS', consts.values())

    def test_every_warned_output_is_a_real_dropdown_label(self):
        labels = set(self._output_constants().values())
        for key in m.UNVERIFIED_OUTPUT_NOTES:
            with self.subTest(key=key):
                self.assertIn(
                    key, labels,
                    f"{key!r} has a hardware warning but is not a dropdown "
                    f"label, so the warning can never be shown. Labels: {sorted(labels)}")

    def test_every_missing_feature_note_is_a_real_dropdown_label(self):
        labels = set(self._output_constants().values())
        for key in m.MISSING_FEATURE_NOTES:
            with self.subTest(key=key):
                self.assertIn(key, labels, f"{key!r} is not a dropdown label")


DESK_2026_10_07 = Path(os.path.expanduser(
    '~/Developer/MacHuna-Swift/testmedia/desk/2026-10-07-kframe'))
KNOCKOUT_WIPE = Path(os.path.expanduser(
    '~/Desktop/TEST WIPES/50P/MOVS/With Sound/KNOCKOUT_WIPE.mov'))


def _write_eaf(path, samples24, frames, spf=1920, tag_extra=0):
    """Write an .eaf in the layout PROVEN on a live K-Frame on 2026-10-07: four
    channels of 32-bit little-endian words, a signed 24-bit sample in bits
    23:0 and a tag in bits 31:24 (channel << 4, plus status bits on
    SDI-recorded clips). The desk accepted a file written exactly this way and
    exported it back byte-identical (0922), so this helper is anchored to the
    desk, not to the reader it tests. samples24: int array, shape (n, 4)."""
    import numpy as np
    s = np.asarray(samples24, dtype=np.int64)
    n = s.shape[0]
    words = np.zeros((n, 4), dtype=np.uint32)
    for ch in range(4):
        words[:, ch] = ((s[:, ch] & 0xFFFFFF).astype(np.uint32)
                        | np.uint32(((ch << 4) | tag_extra) << 24))
    head = bytearray(128)
    struct.pack_into('<I', head, 0x00, 285365)
    struct.pack_into('<H', head, 0x60, 0x0484 if spf == 1920 else 0x04A4)
    struct.pack_into('<H', head, 0x62, spf)
    struct.pack_into('<I', head, 0x64, n)
    struct.pack_into('<I', head, 0x6A, frames)
    Path(path).write_bytes(bytes(head) + words.astype('<u4').tobytes())


def _stereo24(pcm_bytes):
    """read_eaf_stereo24's output: interleaved little-endian s32, the 24-bit
    sample in the top 24 bits. Returned as 24-bit values, shape (n, 2)."""
    import numpy as np
    return np.frombuffer(pcm_bytes, dtype='<i4').reshape(-1, 2).astype(np.int64) >> 8


class TestEafAudio(unittest.TestCase):
    """The .eaf reader.

    The first reader and its tests shared one misunderstanding (8 channels of
    16-bit big-endian), so they agreed perfectly and both were wrong: EIF to
    MOV audio came out at 8-bit resolution with a DC offset on the right. The
    format was settled on a live K-Frame on 2026-10-07. These tests assert on
    decoded samples, and the most important ones compare against files the
    DESK wrote from sources whose audio is known exactly.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _tone(self, n, period, amp):
        import numpy as np
        rng = np.random.default_rng(period)
        s = np.round(amp * np.sin(np.arange(n) * 2 * np.pi / period)).astype(np.int64)
        return (s & ~0xFF) | rng.integers(0, 256, n)     # genuinely 24-bit

    def test_reads_left_and_right_as_full_24_bit_samples(self):
        import numpy as np
        n = 1920 * 3
        left, right = self._tone(n, 64, 3_000_000), self._tone(n, 96, -2_500_000)
        p = os.path.join(self.tmp, 'a.eaf')
        _write_eaf(p, np.stack([left, right, np.zeros(n), np.zeros(n)], 1), 3)
        got = _stereo24(m.read_eaf_stereo24(p, log=lambda *a: None))
        self.assertTrue(np.array_equal(got[:, 0], left), 'left is not bit-exact')
        self.assertTrue(np.array_equal(got[:, 1], right), 'right is not bit-exact')

    def test_the_tag_byte_never_reaches_the_audio(self):
        """The old reader put the tag in the right channel's low byte: a DC
        offset of 16. Silence must decode as silence, on both channels, even
        with the status bits SDI-recorded clips carry (0x44, 0x4C seen)."""
        import numpy as np
        n = 1920
        for extra in (0x0, 0x4, 0xC, 0x40 | 0xC):
            p = os.path.join(self.tmp, f'tag{extra}.eaf')
            _write_eaf(p, np.zeros((n, 4)), 1, tag_extra=extra)
            got = _stereo24(m.read_eaf_stereo24(p, log=lambda *a: None))
            with self.subTest(status_bits=hex(extra)):
                self.assertEqual(int(np.abs(got).max()), 0)

    def test_negative_samples_keep_their_sign(self):
        import numpy as np
        vals = np.array([-1, -256, -(1 << 23), (1 << 23) - 1, 1, 0], dtype=np.int64)
        n = len(vals)
        p = os.path.join(self.tmp, 'sign.eaf')
        _write_eaf(p, np.stack([vals, -vals.clip(-(1 << 23) + 1), np.zeros(n), np.zeros(n)], 1), 1)
        got = _stereo24(m.read_eaf_stereo24(p, log=lambda *a: None))
        self.assertEqual(got[:, 0].tolist(), vals.tolist())

    def test_the_16_bit_reading_is_the_top_16_bits_of_each_sample(self):
        """read_eaf_stereo keeps its original contract - interleaved LE s16 -
        because MacHuna 2.0's player bridge plays and meters those bytes
        directly. It must now be the top 16 bits of the real 24-bit sample."""
        import numpy as np
        n = 1920
        left, right = self._tone(n, 64, 3_000_000), self._tone(n, 50, -1_500_000)
        p = os.path.join(self.tmp, 's16.eaf')
        _write_eaf(p, np.stack([left, right, np.zeros(n), np.zeros(n)], 1), 1, tag_extra=0x4C)
        got = np.frombuffer(m.read_eaf_stereo(p, log=lambda *a: None), dtype='<i2').reshape(-1, 2)
        self.assertTrue(np.array_equal(got[:, 0], left >> 8))
        self.assertTrue(np.array_equal(got[:, 1], right >> 8))

    def test_truncated_and_missing_files_return_none(self):
        self.assertIsNone(m.read_eaf_stereo(os.path.join(self.tmp, 'nope.eaf')))
        self.assertIsNone(m.read_eaf_stereo24(os.path.join(self.tmp, 'nope.eaf')))
        short = os.path.join(self.tmp, 'short.eaf')
        head = bytearray(128)
        struct.pack_into('<I', head, 0x64, 99999)
        Path(short).write_bytes(bytes(head) + b'\x00' * 100)
        self.assertIsNone(m.read_eaf_stereo(short, log=lambda *a: None))
        self.assertIsNone(m.read_eaf_stereo24(short, log=lambda *a: None))

    def test_companion_path_swaps_the_extension(self):
        self.assertTrue(m.eaf_path_for('/x/0003.eif').endswith('0003.eaf'))


@unittest.skipUnless(DESK_2026_10_07.is_dir(),
                     'K-Frame desk-session files (2026-10-07) not on this machine')
class TestEafAgainstTheDesk(unittest.TestCase):
    """Files a live K-Frame wrote from sources whose audio is known exactly.
    The ground truth for the reader."""

    def _read(self, name):
        p = DESK_2026_10_07 / name
        if not p.exists():
            self.skipTest(f'{name} not present')
        return _stereo24(m.read_eaf_stereo24(str(p), log=lambda *a: None))

    def test_0922_our_own_file_returned_by_the_desk_is_bit_exact_24_bit(self):
        import numpy as np
        got = self._read('audio/desk_0922.eaf')
        want = np.load(DESK_2026_10_07 / 'audio' / '0922_samples.npy')
        self.assertTrue(np.array_equal(got, want))

    def test_0920_short_24_bit_stereo_imported_by_the_desk(self):
        """The desk's MOV import keeps the top 16 bits and zero-pads to the
        clip length. The reader must return exactly that."""
        import numpy as np
        got = self._read('audio/desk_0920.eaf')
        src = np.load(DESK_2026_10_07 / 'audio' / '0920_samples.npy')
        self.assertEqual(len(got), 30 * 1920)
        self.assertTrue(np.array_equal(got[:len(src)], src & ~0xFF))
        self.assertEqual(int(np.abs(got[len(src):]).max()), 0, 'padding must be silent')

    def test_0921_first_two_of_four_channels_are_left_and_right(self):
        import numpy as np
        got = self._read('audio/desk_0921.eaf')
        src = np.load(DESK_2026_10_07 / 'audio' / '0921_samples.npy')
        self.assertTrue(np.array_equal(got, src[:, :2] & ~0xFF))

    def test_0900_knockout_wipe_matches_its_source_mov(self):
        import numpy as np, subprocess
        if not KNOCKOUT_WIPE.exists():
            self.skipTest('KNOCKOUT_WIPE.mov not present')
        got = self._read('0900.eaf')
        raw = subprocess.run([m._get_ffmpeg_path('ffmpeg'), '-v', 'error', '-i', str(KNOCKOUT_WIPE),
                              '-map', '0:a:0', '-f', 's16le', '-'], capture_output=True, check=True).stdout
        src = np.frombuffer(raw, dtype='<i2').reshape(-1, 2).astype(np.int64) << 8
        self.assertTrue(np.array_equal(got, src))
        # The 16-bit reading the player uses gives back the 16-bit source exactly.
        s16 = np.frombuffer(m.read_eaf_stereo(str(DESK_2026_10_07 / '0900.eaf'),
                                              log=lambda *a: None), dtype='<i2').reshape(-1, 2)
        self.assertTrue(np.array_equal(s16.astype(np.int64), src >> 8))


class TestEifToMovAudio(unittest.TestCase):
    """End to end through the real conversion: an EIF with an .eaf becomes a
    MOV whose audio is the .eaf's left and right, bit for bit, at 24-bit."""

    def setUp(self):
        if not shutil.which('ffmpeg') and not os.path.exists(m._get_ffmpeg_path('ffmpeg')):
            self.skipTest('ffmpeg not available')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_mov_audio_is_the_eaf_left_and_right_bit_for_bit(self):
        import numpy as np, subprocess
        from PIL import Image
        tgas = []
        for i in range(2):
            t = os.path.join(self.tmp, f'f{i:04d}.tga')
            Image.new('RGBA', (1920, 1080), (10, 20, 30, 255)).save(t)
            tgas.append(t)
        eif = m.convert_tga_seq_to_eif(tgas, self.tmp, 'AUD', 25.0,
                                       log=lambda *a: None, out_name='0001')
        n = 2 * 1920
        rng = np.random.default_rng(7)
        left = rng.integers(-(1 << 23), 1 << 23, n)
        right = rng.integers(-(1 << 23), 1 << 23, n)
        _write_eaf(m.eaf_path_for(eif), np.stack([left, right, np.zeros(n), np.zeros(n)], 1), 2)
        out = os.path.join(self.tmp, 'mov')
        os.makedirs(out)
        mov = m._hula_convert_eif_to_mov(eif, out, include_audio=True, log=lambda *a: None)
        raw = subprocess.run([m._get_ffmpeg_path('ffmpeg'), '-v', 'error', '-i', mov, '-map', '0:a:0',
                              '-f', 's32le', '-c:a', 'pcm_s32le', '-'],
                             capture_output=True, check=True).stdout
        got = np.frombuffer(raw, dtype='<i4').reshape(-1, 2).astype(np.int64) >> 8
        self.assertEqual(len(got), n)
        self.assertTrue(np.array_equal(got[:, 0], left), 'MOV left is not the .eaf left')
        self.assertTrue(np.array_equal(got[:, 1], right), 'MOV right is not the .eaf right')


class TestEafWriter(unittest.TestCase):
    """write_eaf, held to the file a live K-Frame accepted and exported back
    unchanged (0922, 2026-10-07), and to the layout rules proven that day."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    @unittest.skipUnless((DESK_2026_10_07 / 'audio' / 'desk_0922.eaf').exists(),
                         'desk-session file 0922 not on this machine')
    def test_reproduces_the_file_the_desk_returned_byte_for_byte(self):
        import numpy as np
        stereo = np.load(DESK_2026_10_07 / 'audio' / '0922_samples.npy')
        out = os.path.join(self.tmp, '0922.eaf')
        m.write_eaf(out, stereo, frame_count=30, fps=25.0)
        self.assertEqual(Path(out).read_bytes(),
                         (DESK_2026_10_07 / 'audio' / 'desk_0922.eaf').read_bytes())

    def test_header_fields_at_both_rates(self):
        import numpy as np
        for fps, spf, rate in ((25.0, 1920, 0x0484), (50.0, 960, 0x04A4)):
            out = os.path.join(self.tmp, f'h{int(fps)}.eaf')
            m.write_eaf(out, np.zeros((100, 2), dtype=np.int64), frame_count=4, fps=fps)
            head = Path(out).read_bytes()[:128]
            with self.subTest(fps=fps):
                self.assertEqual(struct.unpack_from('<I', head, 0x00)[0], 285365)
                self.assertEqual(struct.unpack_from('<H', head, 0x60)[0], rate)
                self.assertEqual(struct.unpack_from('<H', head, 0x62)[0], spf)
                self.assertEqual(struct.unpack_from('<I', head, 0x64)[0], 4 * spf)
                self.assertEqual(struct.unpack_from('<I', head, 0x6A)[0], 4)
                self.assertEqual(os.path.getsize(out), 128 + 4 * spf * 16)

    def test_short_audio_is_padded_with_silence_and_long_audio_trimmed(self):
        import numpy as np
        rng = np.random.default_rng(3)
        for n in (1000, 1920 * 2, 9999):
            src = rng.integers(-(1 << 23), 1 << 23, (n, 2))
            out = os.path.join(self.tmp, f'len{n}.eaf')
            m.write_eaf(out, src, frame_count=2, fps=25.0)
            got = _stereo24(m.read_eaf_stereo24(out, log=lambda *a: None))
            keep = min(n, 3840)
            with self.subTest(samples=n):
                self.assertEqual(len(got), 3840)
                self.assertTrue(np.array_equal(got[:keep], src[:keep]))
                self.assertEqual(int(np.abs(got[keep:]).max(initial=0)), 0)


def _sws_audio(path):
    """An SWS's audio as (n, 16) s16, read from the file on disk."""
    import numpy as np
    h = m.HulaSWSHeader(path)
    if not h.has_audio:
        return None
    raw = Path(path).read_bytes()[h.audio_offset:]
    a = np.frombuffer(raw, dtype='<i2')
    return a[:len(a) // 16 * 16].reshape(-1, 16).astype(np.int64)


class TestAudioRoutes(unittest.TestCase):
    """Every route that carries audio, end to end, read back from disk. David's
    requirement (2026-10-08): whatever the source, the output carries exactly
    what the TARGET desk expects. Bit-exact where nothing is lost; 24-bit into
    a 16-bit SWS keeps the top 16 bits, as the K-Frame's own import does."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which('ffmpeg') and not os.path.exists(m._get_ffmpeg_path('ffmpeg')):
            raise unittest.SkipTest('ffmpeg not available')
        import numpy as np, subprocess, wave
        cls.tmp = tempfile.mkdtemp()
        cls.ff = m._get_ffmpeg_path('ffmpeg')
        rng = np.random.default_rng(1007)

        def wav(path, chans, rate=48000, bits=24):
            a = np.stack(chans, 1).astype(np.int64)
            if bits == 24:
                b = (a & 0xFFFFFF).astype('<u4').view(np.uint8).reshape(-1, 4)[:, :3].tobytes()
            else:
                b = a.astype('<i2').tobytes()
            with wave.open(path, 'wb') as w:
                w.setnchannels(a.shape[1]); w.setsampwidth(bits // 8)
                w.setframerate(rate); w.writeframes(b)

        def mov(name, chans, fps=25, rate=48000, bits=24):
            w = os.path.join(cls.tmp, name + '.wav')
            wav(w, chans, rate, bits)
            out = os.path.join(cls.tmp, name + '.mov')
            # Limit the PICTURE input by duration. '-frames:v 6' on the output
            # stops the whole file there and cuts longer audio mid-block, so
            # the "long audio" source silently was not long.
            subprocess.run([cls.ff, '-y', '-v', 'error', '-t', f'{6 / fps:g}', '-f', 'lavfi',
                            '-i', f'testsrc=size=192x108:rate={fps}', '-i', w, '-map', '0:v',
                            '-map', '1:a', '-c:v', 'prores_ks',
                            '-c:a', f'pcm_s{bits}le', out], check=True)
            return out

        def tone(n, bits=24):
            full = 1 << (bits - 1)
            return rng.integers(-full // 4, full // 4, n)

        n25 = 6 * 1920
        cls.L, cls.R, cls.M = tone(n25), tone(n25), tone(n25)
        cls.src = {
            'stereo24': mov('stereo24', [cls.L, cls.R]),
            'mono24': mov('mono24', [cls.M]),
            'quad24': mov('quad24', [cls.L, cls.R, tone(n25), tone(n25)]),
            'short24': mov('short24', [cls.L[:5000], cls.R[:5000]]),
            'long24': mov('long24', [np.concatenate([cls.L, cls.L]), np.concatenate([cls.R, cls.R])]),
            'stereo441': mov('stereo441', [tone(6 * 1764, 16), tone(6 * 1764, 16)], rate=44100, bits=16),
            'stereo24_50': mov('stereo24_50', [cls.L[:6 * 960], cls.R[:6 * 960]], fps=50),
        }
        cls.L16, cls.R16 = tone(n25, 16), tone(n25, 16)
        cls.src['stereo16'] = mov('stereo16', [cls.L16, cls.R16], bits=16)
        cls.src['mono16'] = mov('mono16', [cls.L16], bits=16)
        cls.src['silent'] = os.path.join(cls.tmp, 'silent.mov')
        subprocess.run([cls.ff, '-y', '-v', 'error', '-f', 'lavfi', '-i',
                        'testsrc=size=192x108:rate=25', '-frames:v', '6',
                        '-c:v', 'prores_ks', cls.src['silent']], check=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def test_the_test_sources_are_what_the_tests_assume(self):
        """A source that is not what it claims makes every test on it
        meaningless - the long-audio file once came out shorter than the clip."""
        import subprocess
        def audio_samples(path):
            out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
                                  '-show_entries', 'stream=duration_ts', '-of', 'csv=p=0', path],
                                 capture_output=True, text=True).stdout.strip()
            return int(out)
        self.assertEqual(audio_samples(self.src['stereo24']), 6 * 1920)
        self.assertEqual(audio_samples(self.src['short24']), 5000)
        self.assertEqual(audio_samples(self.src['long24']), 12 * 1920)
        self.assertEqual(m.get_video_info(self.src['mono24'])['audio_channels'], 1)
        self.assertEqual(m.get_video_info(self.src['quad24'])['audio_channels'], 4)

    def _dir(self, name):
        d = os.path.join(self.tmp, name)
        shutil.rmtree(d, True)
        os.makedirs(d)
        return d

    def _dir_path(self, name):
        """The SWS that _sws() wrote into this folder."""
        return os.path.join(self.tmp, name, '1.SWS')

    def _eif(self, src, out_dir, **kw):
        return m.convert_clip_to_eif(self.src[src], self._dir(out_dir), log=lambda *a: None,
                                     out_name='0001', **kw)

    def _flag(self, eif):
        return struct.unpack_from('<I', Path(eif).read_bytes()[:0x64], 0x60)[0]

    def _eaf24(self, eif):
        return _stereo24(m.read_eaf_stereo24(m.eaf_path_for(eif), log=lambda *a: None))

    # ── source to EIF ──────────────────────────────────────────────────────
    def test_24_bit_stereo_to_eif_is_bit_exact(self):
        import numpy as np
        eif = self._eif('stereo24', 'e_s24')
        got = self._eaf24(eif)
        self.assertEqual(len(got), 6 * 1920)
        self.assertTrue(np.array_equal(got[:, 0], self.L))
        self.assertTrue(np.array_equal(got[:, 1], self.R))
        self.assertEqual(self._flag(eif), 0x07, 'the .eif must announce its audio')

    def test_16_bit_stereo_to_eif_is_the_sample_shifted_up(self):
        import numpy as np
        got = self._eaf24(self._eif('stereo16', 'e_s16'))
        self.assertTrue(np.array_equal(got[:, 0], self.L16 << 8))
        self.assertTrue(np.array_equal(got[:, 1], self.R16 << 8))

    def test_50fps_uses_960_samples_per_frame(self):
        import numpy as np
        eif = self._eif('stereo24_50', 'e_50')
        got = self._eaf24(eif)
        self.assertEqual(len(got), 6 * 960)
        self.assertTrue(np.array_equal(got[:, 0], self.L[:6 * 960]))
        head = Path(m.eaf_path_for(eif)).read_bytes()[:128]
        self.assertEqual(struct.unpack_from('<H', head, 0x62)[0], 960)

    def test_mono_goes_to_both_channels(self):
        import numpy as np
        got = self._eaf24(self._eif('mono24', 'e_mono'))
        self.assertTrue(np.array_equal(got[:, 0], self.M))
        self.assertTrue(np.array_equal(got[:, 1], self.M))

    def test_four_channels_take_the_first_two(self):
        import numpy as np
        got = self._eaf24(self._eif('quad24', 'e_quad'))
        self.assertTrue(np.array_equal(got[:, 0], self.L))
        self.assertTrue(np.array_equal(got[:, 1], self.R))

    def test_short_audio_is_padded_and_long_audio_trimmed(self):
        import numpy as np
        short = self._eaf24(self._eif('short24', 'e_short'))
        self.assertEqual(len(short), 6 * 1920)
        self.assertTrue(np.array_equal(short[:5000, 0], self.L[:5000]))
        self.assertEqual(int(np.abs(short[5000:]).max()), 0)
        long_ = self._eaf24(self._eif('long24', 'e_long'))
        self.assertEqual(len(long_), 6 * 1920)
        self.assertTrue(np.array_equal(long_[:, 0], self.L))

    def test_44_1khz_is_resampled_to_the_clip_length(self):
        got = self._eaf24(self._eif('stereo441', 'e_441'))
        self.assertEqual(len(got), 6 * 1920)
        self.assertGreater(int(abs(got).max()), 0)

    def test_include_audio_off_writes_no_eaf_and_says_so(self):
        eif = self._eif('stereo24', 'e_off', include_audio=False)
        self.assertFalse(os.path.exists(m.eaf_path_for(eif)))
        self.assertEqual(self._flag(eif), 0x03)

    def test_a_source_without_audio_writes_no_eaf(self):
        eif = self._eif('silent', 'e_silent')
        self.assertFalse(os.path.exists(m.eaf_path_for(eif)))
        self.assertEqual(self._flag(eif), 0x03)

    def test_a_stale_eaf_is_replaced_or_removed(self):
        """Decision 2026-10-08: .eif and .eaf are one output. A leftover .eaf
        would put an old clip's sound on air with a new picture."""
        import numpy as np
        d = self._dir('e_stale')
        stale = os.path.join(d, '0001.eaf')
        m.write_eaf(stale, np.full((3840, 2), 12345, dtype=np.int64), 2, 25.0)
        m.convert_clip_to_eif(self.src['silent'], d, log=lambda *a: None, out_name='0001')
        self.assertFalse(os.path.exists(stale), 'stale .eaf survived an audio-less EIF')
        m.write_eaf(stale, np.full((3840, 2), 12345, dtype=np.int64), 2, 25.0)
        eif = m.convert_clip_to_eif(self.src['stereo24'], d, log=lambda *a: None, out_name='0001')
        self.assertTrue(np.array_equal(self._eaf24(eif)[:, 0], self.L), 'stale .eaf not replaced')

    def test_tga_sequence_to_eif_has_no_audio_and_clears_a_stale_eaf(self):
        import numpy as np
        from PIL import Image
        d = self._dir('e_tga')
        stale = os.path.join(d, '0001.eaf')
        m.write_eaf(stale, np.ones((1920, 2), dtype=np.int64), 1, 25.0)
        t = os.path.join(d, 'f0000.tga')
        Image.new('RGBA', (1920, 1080), (1, 2, 3, 255)).save(t)
        eif = m.convert_tga_seq_to_eif([t], d, 'T', 25.0, log=lambda *a: None, out_name='0001')
        self.assertFalse(os.path.exists(stale))
        self.assertEqual(self._flag(eif), 0x03)

    # ── SWS to EIF, EIF to SWS, and SWS mono ───────────────────────────────
    def _sws(self, src, out_dir, std='1080p25'):
        d = self._dir(out_dir)
        m.convert_clip(self.src[src], 1, d, video_standard=std, include_audio=True,
                       split_fat32=False, log=lambda *a: None)
        return os.path.join(d, '1.SWS')

    def test_sws_to_eif_carries_the_sws_left_and_right(self):
        import numpy as np
        sws = self._sws('stereo16', 's_for_eif')
        a = _sws_audio(sws)
        eif = m.convert_sws_to_eif(sws, self._dir('se'), log=lambda *a: None, out_name='0002')
        got = self._eaf24(eif)
        self.assertTrue(np.array_equal(got[:, 0], a[:, 0] << 8))
        self.assertTrue(np.array_equal(got[:, 1], a[:, 2] << 8))
        self.assertEqual(self._flag(eif), 0x07)

    def test_a_5994_sws_becomes_a_50fps_eif_of_the_same_length(self):
        """Decision A: it used to map 59.94 frames 1:1 onto 50fps (plays slow)
        while the .eaf was padded to the new length."""
        import numpy as np
        sws = self._clip_sws('stereo16', '1080p5994', 'sws5994')
        h = m.HulaSWSHeader(sws)
        a = _sws_audio(sws)
        eif = m.convert_sws_to_eif(sws, self._dir('sws5994_eif'), log=lambda *a: None, out_name='0003')
        e = m.EIFHeader(eif)
        self.assertEqual(e.fps, 50.0)
        self.assertAlmostEqual(e.frame_count / 50.0, h.frame_count / h.fps, delta=1 / 50.0)
        got = self._eaf24(eif)
        self.assertEqual(len(got), e.frame_count * 960)
        n = min(len(a), len(got))
        self.assertTrue(np.array_equal(got[:n, 0], a[:n, 0] << 8))

    def test_an_interlaced_5994_sws_cannot_become_an_eif(self):
        import subprocess
        src = os.path.join(self.tmp, 'p5994.mov')
        subprocess.run([m._get_ffmpeg_path('ffmpeg'), '-y', '-v', 'error', '-t', '0.2', '-f', 'lavfi',
                        '-i', 'testsrc=size=192x108:rate=60000/1001', '-c:v', 'prores_ks', src], check=True)
        d = self._dir('i5994')
        m.convert_clip(src, 1, d, video_standard='1080i5994', include_audio=False,
                       split_fat32=False, log=lambda *a: None)
        with self.assertRaises(ValueError):
            m.convert_sws_to_eif(os.path.join(d, '1.SWS'), self._dir('i5994_eif'),
                                 log=lambda *a: None, out_name='0004')

    def test_eif_to_sws_puts_the_eaf_on_the_kahuna_channels(self):
        """L on channel 1, R on channel 3, the rest silent; 24-bit keeps its
        top 16 bits."""
        import numpy as np
        eif = self._eif('stereo24', 'es_src')
        d = self._dir('es_out')
        sws = m.convert_eif_to_sws(eif, 9, d, split_fat32=False, log=lambda *a: None)
        a = _sws_audio(sws)
        self.assertIsNotNone(a, 'the SWS header must declare its audio')
        self.assertEqual(len(a), 6 * 1920)
        self.assertTrue(np.array_equal(a[:, 0], self.L >> 8))
        self.assertTrue(np.array_equal(a[:, 2], self.R >> 8))
        others = [c for c in range(16) if c not in (0, 2)]
        self.assertEqual(int(np.abs(a[:, others]).max()), 0)

    def test_eif_without_eaf_to_sws_has_no_audio(self):
        eif = self._eif('silent', 'es_silent_src')
        sws = m.convert_eif_to_sws(eif, 9, self._dir('es_silent'), split_fat32=False,
                                   log=lambda *a: None)
        self.assertIsNone(_sws_audio(sws))

    # ── SWS to SWS (another standard) keeps its audio ─────────────────────
    def _sws_to_sws(self, src_std, out_std, **kw):
        import numpy as np
        # A 25p source for 1080p25; a 50p source for the 50Hz standards (a 25p
        # source cannot become 1080i50 - that same-rate weave is blocked).
        mov = 'stereo16' if src_std == '1080p25' else 'stereo24_50'
        src = self._sws(mov, f's2s_src_{src_std}', std=src_std)
        out = m.convert_sws_to_sws(src, 3, self._dir(f's2s_{src_std}_{out_std}'), out_std,
                                   split_fat32=False, log=lambda *a: None, **kw)
        return _sws_audio(src), out

    def test_sws_to_sws_keeps_its_audio_through_every_standard_change(self):
        """Interlaced to progressive doubles the frames and progressive to
        interlaced halves them; the duration, and so the audio, is the same."""
        import numpy as np
        for src_std, out_std in (('1080p25', '1080p25'), ('1080p50', '1080i50'),
                                 ('1080i50', '1080p50')):
            a, out = self._sws_to_sws(src_std, out_std)
            b = _sws_audio(out)
            with self.subTest(src=src_std, out=out_std):
                self.assertIsNotNone(b, 'the output SWS must carry the audio')
                n = min(len(a), len(b))
                self.assertGreater(n, 0)
                self.assertTrue(np.array_equal(b[:n, 0], a[:n, 0]))
                self.assertTrue(np.array_equal(b[:n, 2], a[:n, 2]))
                h = m.HulaSWSHeader(out)
                self.assertEqual(len(b), h.frame_count * int(round(48000 / h.fps)))

    def test_sws_to_sws_header_states_the_real_file_size(self):
        """Independent review, 2026-10-08: with audio, the header's total size
        (0x1CC) assumed 25fps audio and was wrong for every other rate."""
        for src_std, out_std in (('1080p50', '1080p50'), ('1080i50', '1080p50'),
                                 ('1080p25', '1080p25')):
            _a, out = self._sws_to_sws(src_std, out_std)
            declared = struct.unpack_from('>I', Path(out).read_bytes()[:0x200], 0x1CC)[0]
            with self.subTest(src=src_std, out=out_std):
                self.assertEqual(declared, os.path.getsize(out))

    def test_sws_to_sws_interlaced_to_interlaced_is_not_woven_again(self):
        """Independent review + matrix, 2026-10-08: i50 to i50 wove the
        already-woven frames again - half the length, fields mixed, half the
        audio. Present since the routing lived in the GUI."""
        import numpy as np
        a, out = self._sws_to_sws('1080i50', '1080i50')
        src = m.HulaSWSHeader(self._dir_path('s2s_src_1080i50'))
        h = m.HulaSWSHeader(out)
        self.assertEqual(h.frame_count, src.frame_count)
        b = _sws_audio(out)
        self.assertEqual(len(b), len(a))
        self.assertTrue(np.array_equal(b[:, 0], a[:, 0]))

    def test_sws_to_sws_interlaced_at_another_rate_is_refused(self):
        src = self._sws('stereo24_50', 's2s_ref_i', std='1080i50')
        with self.assertRaises(ValueError):
            m.convert_sws_to_sws(src, 4, self._dir('s2s_ref_i_out'), '1080i5994',
                                 split_fat32=False, log=lambda *a: None)

    def test_sws_to_sws_progressive_at_another_rate_keeps_its_duration(self):
        """Decision A (David, 2026-10-08): convert the rate, so the clip plays
        at the right speed and its audio fits."""
        import numpy as np
        for src_std, out_std in (('1080p50', '1080p25'), ('1080p25', '1080p50'),
                                 ('1080p50', '1080p5994')):
            a, out = self._sws_to_sws(src_std, out_std)
            src_h = m.HulaSWSHeader(self._dir_path(f's2s_src_{src_std}'))
            h = m.HulaSWSHeader(out)
            src_dur = src_h.frame_count / src_h.fps
            with self.subTest(src=src_std, out=out_std):
                self.assertAlmostEqual(h.frame_count / h.fps, src_dur, delta=1.0 / h.fps)
                b = _sws_audio(out)
                n = min(len(a), len(b))
                self.assertTrue(np.array_equal(b[:n, 0], a[:n, 0]))
                self.assertEqual(len(b), h.frame_count * int(round(48000 / h.fps)))

    def test_sws_to_sws_include_audio_off_writes_none(self):
        _a, out = self._sws_to_sws('1080p25', '1080p25', include_audio=False)
        self.assertIsNone(_sws_audio(out))

    def test_the_tk_app_uses_the_engine_sws_to_sws(self):
        """The routing used to be written out inside the GUI (and again in the
        Swift bridge), and both copies dropped the audio. One copy now."""
        src = Path(m.__file__).read_text()
        gui = src[src.index('def launch_gui'):]
        self.assertIn('convert_sws_to_sws(', gui)
        self.assertFalse('does not carry audio through' in src)

    def test_a_cancelled_eif_does_not_leave_a_stale_eaf(self):
        """Cancelling leaves a half-written picture; the old .eaf beside it
        must not survive to be paired with it."""
        import numpy as np, threading
        from PIL import Image
        cancel = threading.Event(); cancel.set()
        d = self._dir('e_cancel')
        stale = os.path.join(d, '0001.eaf')
        t = os.path.join(d, 'f0000.tga')
        Image.new('RGBA', (1920, 1080), (1, 2, 3, 255)).save(t)
        routes = {
            'clip': lambda: m.convert_clip_to_eif(self.src['stereo24'], d, log=lambda *a: None,
                                                  out_name='0001', cancel_event=cancel),
            'sws': lambda: m.convert_sws_to_eif(self._sws('stereo16', 'e_cancel_sws'), d,
                                                log=lambda *a: None, out_name='0001',
                                                cancel_event=cancel),
            'tga': lambda: m.convert_tga_seq_to_eif([t], d, 'T', 25.0, log=lambda *a: None,
                                                    out_name='0001', cancel_event=cancel),
        }
        for route, run in routes.items():
            m.write_eaf(stale, np.full((1920, 2), 77, dtype=np.int64), 1, 25.0)
            run()
            with self.subTest(route=route):
                self.assertFalse(os.path.exists(stale))
                # Nor the half-written picture: a partial file with a valid slot
                # name could be loaded onto a desk by mistake (David, 2026-10-08).
                self.assertFalse(os.path.exists(os.path.join(d, '0001.eif')),
                                 'a cancelled conversion left a partial .eif')

    def test_the_tk_app_does_not_mark_a_cancelled_eif_done(self):
        """Independent review, 2026-10-08: the EIF converters return None when
        cancelled (and delete the partial file), but the Tk batch appended 'OK'
        regardless, so the row showed done and a re-run skipped it."""
        src = Path(m.__file__).read_text()
        body = src[src.index('        def _run_to_eif():'):]
        body = body[:body.index('        def _run_to_tga_seq():')]
        self.assertIn('made is None', body, 'the converter result must be checked')
        self.assertLess(body.index('made is None'), body.index("results.append((out_name, name, 'OK'))"))

    # ── MOV to SWS at another frame rate (decision A, 2026-10-08) ──────────
    def _clip_sws(self, src, std, out_dir):
        d = self._dir(out_dir)
        m.convert_clip(self.src[src], 1, d, video_standard=std, include_audio=True,
                       split_fat32=False, log=lambda *a: None)
        return os.path.join(d, '1.SWS')

    def test_a_progressive_clip_at_another_rate_keeps_its_duration_and_audio(self):
        """It kept every frame and stamped the standard's rate, so 25p on a
        1080p50 SWS played at double speed with audio sized for 25fps."""
        import numpy as np
        for src, std, src_dur in (('stereo16', '1080p50', 0.24), ('stereo24_50', '1080p25', 0.12),
                                  ('stereo16', '1080p5994', 0.24)):
            out = self._clip_sws(src, std, f'rate_{src}_{std}')
            h = m.HulaSWSHeader(out)
            a = _sws_audio(out)
            with self.subTest(src=src, std=std):
                self.assertAlmostEqual(h.frame_count / h.fps, src_dur, delta=1.0 / h.fps)
                self.assertEqual(len(a), h.frame_count * int(round(48000 / h.fps)))
                ref = self.L16 if src == 'stereo16' else (self.L[:6 * 960] >> 8)
                n = min(len(ref), len(a))
                self.assertTrue(np.array_equal(a[:n, 0], ref[:n]))

    def test_an_interlaced_clip_at_another_interlaced_rate_is_refused(self):
        import subprocess
        src = os.path.join(self.tmp, 'i25.mov')
        subprocess.run([m._get_ffmpeg_path('ffmpeg'), '-y', '-v', 'error', '-t', '0.24', '-f', 'lavfi',
                        '-i', 'testsrc=size=192x108:rate=25', '-vf', 'setfield=tff',
                        '-flags', '+ilme+ildct', '-c:v', 'prores_ks', src], check=True)
        with self.assertRaises(ValueError):
            m.convert_clip(src, 1, self._dir('i25_to_i5994'), video_standard='1080i5994',
                           include_audio=False, split_fat32=False, log=lambda *a: None)

    # ── Dual mono: two mono tracks (decision E, 2026-10-08) ────────────────
    def _dual_mono(self):
        import subprocess, wave, numpy as np
        w1, w2 = os.path.join(self.tmp, 'dm1.wav'), os.path.join(self.tmp, 'dm2.wav')
        for path, data in ((w1, self.L16), (w2, self.R16)):
            with wave.open(path, 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
                w.writeframes(data.astype('<i2').tobytes())
        out = os.path.join(self.tmp, 'dualmono.mov')
        if not os.path.exists(out):
            subprocess.run([m._get_ffmpeg_path('ffmpeg'), '-y', '-v', 'error', '-t', '0.24', '-f', 'lavfi',
                            '-i', 'testsrc=size=192x108:rate=25', '-i', w1, '-i', w2,
                            '-map', '0:v', '-map', '1:a', '-map', '2:a', '-c:v', 'prores_ks',
                            '-c:a', 'pcm_s16le', out], check=True)
        return out

    def test_dual_mono_puts_track_1_left_and_track_2_right(self):
        """Independent review: track 1 went to both sides and track 2 was
        thrown away. Common in broadcast ProRes."""
        import numpy as np
        src = self._dual_mono()
        d = self._dir('dm_sws')
        m.convert_clip(src, 1, d, video_standard='1080p25', include_audio=True,
                       split_fat32=False, log=lambda *a: None)
        a = _sws_audio(os.path.join(d, '1.SWS'))
        self.assertTrue(np.array_equal(a[:, 0], self.L16), 'SWS left is not track 1')
        self.assertTrue(np.array_equal(a[:, 2], self.R16), 'SWS right is not track 2')
        eif = m.convert_clip_to_eif(src, self._dir('dm_eif'), log=lambda *a: None, out_name='0001')
        got = self._eaf24(eif)
        self.assertTrue(np.array_equal(got[:, 0], self.L16 << 8), 'EIF left is not track 1')
        self.assertTrue(np.array_equal(got[:, 1], self.R16 << 8), 'EIF right is not track 2')

    def test_a_split_sws_says_it_has_no_audio_and_the_log_says_why(self):
        """Decision F (David, 2026-10-08): a split SWS (over 4GB) cannot carry
        audio - the split layout's audio is unknown - so it is written without,
        the log says so, and the header no longer claims audio it lacks."""
        eif = self._eif('stereo24', 'split_src')
        d = self._dir('split_out')
        lines = []
        old_limit = m.FAT32_LIMIT
        m.FAT32_LIMIT = 1024 * 1024          # force a split on a small clip
        try:
            m.convert_eif_to_sws(eif, 5, d, split_fat32=True, log=lines.append)
        finally:
            m.FAT32_LIMIT = old_limit
        chunks = sorted(Path(d, '5.SWS').glob('01_OF_*'))
        self.assertTrue(chunks, 'the clip should have been split')
        self.assertFalse(m.HulaSWSHeader(str(chunks[0])).has_audio,
                         'a split SWS must not claim audio it does not contain')
        self.assertTrue(any('audio' in l.lower() and 'split' in l.lower() for l in lines),
                        'the log must say the audio was left out')

    def test_a_failed_eif_leaves_nothing_half_written(self):
        """Independent review, 2026-10-08: a failure partway through (not a
        cancel) left a partial .eif with a valid slot name, and any old .eaf."""
        import numpy as np
        from PIL import Image
        d = self._dir('e_fail')
        t = [os.path.join(d, f'f{i:04d}.tga') for i in range(3)]
        for p in t:
            Image.new('RGBA', (1920, 1080), (1, 2, 3, 255)).save(p)
        sws = self._sws('stereo16', 'e_fail_sws')
        routes = {
            'clip': lambda: m.convert_clip_to_eif(self.src['stereo24'], d, log=lambda *a: None,
                                                  out_name='0001'),
            'sws': lambda: m.convert_sws_to_eif(sws, d, log=lambda *a: None, out_name='0001'),
            'tga': lambda: m.convert_tga_seq_to_eif(t, d, 'T', 25.0, log=lambda *a: None,
                                                    out_name='0001'),
        }
        encoders = ('_encode_eif_frame_from_yuv', '_encode_eif_frame_from_rgba')
        for route, run in routes.items():
            m.write_eaf(os.path.join(d, '0001.eaf'), np.ones((1920, 2), dtype=np.int64), 1, 25.0)
            real = {fn: getattr(m, fn) for fn in encoders}
            calls = [0]
            def wrap(fn):
                def boom(*a, **k):
                    calls[0] += 1
                    if calls[0] == 2:
                        raise OSError('disk full (simulated)')
                    return real[fn](*a, **k)
                return boom
            for fn in encoders:
                setattr(m, fn, wrap(fn))
            try:
                with self.subTest(route=route):
                    with self.assertRaises(OSError):
                        run()
                    self.assertFalse(os.path.exists(os.path.join(d, '0001.eif')), 'partial .eif left')
                    self.assertFalse(os.path.exists(os.path.join(d, '0001.eaf')), 'old .eaf left')
            finally:
                for fn in encoders:
                    setattr(m, fn, real[fn])

    def _two_track_mov(self, name, t1, t2, layout1=None, layout2=None, stereo2=None):
        """A MOV with two audio tracks of known samples. t1/t2: int16 arrays;
        stereo2: a second channel for track 2 (making it stereo); layout1/2:
        ffmpeg channel-layout labels to stamp on each track."""
        import subprocess, wave, numpy as np
        out = os.path.join(self.tmp, name + '.mov')
        w1, w2 = os.path.join(self.tmp, name + '_1.wav'), os.path.join(self.tmp, name + '_2.wav')
        def wav(path, chans):
            a = np.stack(chans, 1).astype('<i2')
            with wave.open(path, 'wb') as w:
                w.setnchannels(a.shape[1]); w.setsampwidth(2); w.setframerate(48000)
                w.writeframes(a.tobytes())
        wav(w1, [t1]); wav(w2, [t2] if stereo2 is None else [t2, stereo2])
        graph = []
        maps = ['-map', '0:v']
        for i, lay in ((1, layout1), (2, layout2)):
            if lay:
                graph.append(f'[{i}:a]aformat=channel_layouts={lay}[a{i}]'); maps += ['-map', f'[a{i}]']
            else:
                maps += ['-map', f'{i}:a']
        cmd = [m._get_ffmpeg_path('ffmpeg'), '-y', '-v', 'error', '-t', '0.24', '-f', 'lavfi',
               '-i', 'testsrc=size=192x108:rate=25', '-i', w1, '-i', w2]
        if graph:
            cmd += ['-filter_complex', ';'.join(graph)]
        subprocess.run(cmd + maps + ['-c:v', 'prores_ks', '-c:a', 'pcm_s16le', out], check=True)
        return out

    def _sws_and_eaf_lr(self, src, tag):
        import numpy as np
        d = self._dir(f'tt_{tag}')
        m.convert_clip(src, 1, d, video_standard='1080p25', include_audio=True,
                       split_fat32=False, log=lambda *a: None)
        a = _sws_audio(os.path.join(d, '1.SWS'))
        eif = m.convert_clip_to_eif(src, self._dir(f'tt_{tag}_eif'), log=lambda *a: None,
                                    out_name='0001')
        self.assertTrue(os.path.exists(m.eaf_path_for(eif)), 'the EIF must carry its audio')
        e = self._eaf24(eif) >> 8
        return a[:, 0], a[:, 2], e[:, 0], e[:, 1]

    def test_dual_mono_survives_a_stereo_second_track_and_channel_labels(self):
        """Second review, 2026-10-08: ffmpeg's track merge reorders channels by
        their labels. A stereo second track lost track 1; FR/FL-labelled tracks
        swapped; FC+FL gave an EIF with no audio at all."""
        import numpy as np
        L, R, X = self.L16, self.R16, (self.L16 // 2)
        cases = {
            'mono_then_stereo': dict(t1=L, t2=R, stereo2=X),
            'labelled_FR_FL': dict(t1=L, t2=R, layout1='FR', layout2='FL'),
            'labelled_FC_FL': dict(t1=L, t2=R, layout1='FC', layout2='FL'),
        }
        for name, kw in cases.items():
            src = self._two_track_mov(name, **kw)
            sl, sr, el, er = self._sws_and_eaf_lr(src, name)
            with self.subTest(case=name):
                self.assertTrue(np.array_equal(sl, L), 'SWS left must be track 1')
                self.assertTrue(np.array_equal(sr, R), 'SWS right must be track 2')
                self.assertTrue(np.array_equal(el[:len(L)], L), 'EIF left must be track 1')
                self.assertTrue(np.array_equal(er[:len(R)], R), 'EIF right must be track 2')

    def test_dual_mono_with_a_shorter_second_track_keeps_all_of_track_1(self):
        import numpy as np
        src = self._two_track_mov('short_t2', t1=self.L16, t2=self.R16[:3000])
        sl, sr, el, er = self._sws_and_eaf_lr(src, 'short_t2')
        self.assertTrue(np.array_equal(sl, self.L16), 'track 1 was cut short')
        self.assertTrue(np.array_equal(sr[:3000], self.R16[:3000]))
        self.assertEqual(int(np.abs(sr[3000:]).max()), 0, 'right must be silent after track 2 ends')
        self.assertTrue(np.array_equal(el[:len(self.L16)], self.L16))

    def test_mono_to_sws_goes_to_both_kahuna_channels(self):
        """Decision 2026-10-08. v1.11.0 put mono on the left only."""
        import numpy as np
        a = _sws_audio(self._sws('mono16', 's_mono'))
        self.assertTrue(np.array_equal(a[:, 0], self.L16))
        self.assertTrue(np.array_equal(a[:, 2], self.L16))

    def test_stereo_to_sws_is_unchanged(self):
        import numpy as np
        a = _sws_audio(self._sws('stereo16', 's_stereo'))
        self.assertTrue(np.array_equal(a[:, 0], self.L16))
        self.assertTrue(np.array_equal(a[:, 2], self.R16))
        others = [c for c in range(16) if c not in (0, 2)]
        self.assertEqual(int(np.abs(a[:, others]).max()), 0)


class TestKFrameTgaFromTheSource(unittest.TestCase):
    """Decision 44 (2026-10-08), engine half: K-Frame TGA works its output out
    from the SOURCE. A TGA sequence has no rate or scan of its own - the desk
    imports frames at whatever it is set to - so the only real choice is for a
    progressive source at 50fps or more, which a 50i desk wants woven in pairs.
    Anything already interlaced, or at 25fps, goes through frame for frame.

    The bug this fixes: a 1080i50 standard wove an ALREADY interlaced MOV a
    second time, giving half the frames with fields from two different frames
    in each (found 2026-10-07 preparing the desk tests). Driven through
    _hula_run_batch, the dispatcher both apps call."""

    @classmethod
    def setUpClass(cls):
        if not shutil.which('ffmpeg') and not os.path.exists(m._get_ffmpeg_path('ffmpeg')):
            raise unittest.SkipTest('ffmpeg not available')
        import subprocess
        from PIL import Image
        cls.tmp = tempfile.mkdtemp()
        ff = m._get_ffmpeg_path('ffmpeg')

        def mov(name, fps, interlaced=False):
            out = os.path.join(cls.tmp, name + '.mov')
            cmd = [ff, '-y', '-v', 'error', '-t', f'{6 / fps:g}', '-f', 'lavfi',
                   '-i', f'testsrc=size=192x108:rate={fps}']
            if interlaced:
                cmd += ['-vf', 'setfield=tff', '-flags', '+ilme+ildct']
            subprocess.run(cmd + ['-c:v', 'prores_ks', out], check=True)
            return out
        cls.i25 = mov('i25', 25, interlaced=True)
        cls.p25 = mov('p25', 25)
        cls.p50 = mov('p50', 50)

        tgas = []
        for i in range(4):
            t = os.path.join(cls.tmp, f'f{i:04d}.tga')
            Image.new('RGBA', (1920, 1080), (40 * i, 90, 140, 255)).save(t)
            tgas.append(t)
        d = os.path.join(cls.tmp, 'eifs')
        os.makedirs(d)
        cls.e25 = m.convert_tga_seq_to_eif(tgas, d, 'E', 25.0, log=lambda *a: None, out_name='0025')
        cls.e50 = m.convert_tga_seq_to_eif(tgas, d, 'E', 50.0, log=lambda *a: None, out_name='0050')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, True)

    def _tgas(self, src, standard):
        out = tempfile.mkdtemp(dir=self.tmp)
        m._hula_run_batch([src], out, m.HULA_TARGET_KFRAME_TGA, standard=standard,
                          log=lambda *a: None)
        return sorted(Path(out).rglob('*.tga'))

    def _source_frames(self, src):
        import numpy as np, subprocess
        raw = subprocess.run([m._get_ffmpeg_path('ffmpeg'), '-v', 'error', '-i', src,
                              '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, dtype=np.uint8).reshape(-1, 108, 192, 4)

    def test_an_interlaced_mov_is_never_woven_again(self):
        import numpy as np
        from PIL import Image
        frames = self._tgas(self.i25, '1080i50')
        src = self._source_frames(self.i25)
        self.assertEqual(len(frames), len(src), 'an interlaced source must keep every frame')
        for i, f in enumerate(frames):
            with self.subTest(frame=i):
                self.assertTrue(np.array_equal(np.array(Image.open(f).convert('RGBA')), src[i]))

    def test_a_25p_mov_keeps_every_frame_on_an_interlaced_standard(self):
        self.assertEqual(len(self._tgas(self.p25, '1080i50')), 6)

    def test_a_50p_mov_is_woven_for_an_interlaced_desk(self):
        self.assertEqual(len(self._tgas(self.p50, '1080i50')), 3)

    def test_a_50p_mov_keeps_every_frame_for_a_progressive_desk(self):
        self.assertEqual(len(self._tgas(self.p50, '1080p50')), 6)

    def test_a_25fps_eif_goes_through_on_an_interlaced_standard(self):
        """A 25fps EIF holds woven 50i (the desk stores it that way, 2026-10-07).
        It used to be refused with an error."""
        self.assertEqual(len(self._tgas(self.e25, '1080i50')), 4)

    def test_a_50fps_eif_is_woven_for_an_interlaced_desk(self):
        self.assertEqual(len(self._tgas(self.e50, '1080i50')), 2)

    # ── Sony TGA follows the same rule (David, 2026-10-08) ─────────────────
    def _sony(self, src, standard):
        out = tempfile.mkdtemp(dir=self.tmp)
        m._hula_run_batch([src], out, m.HULA_TARGET_SONY_TGA, standard=standard,
                          clip_name='TEST', log=lambda *a: None)
        return sorted(p.name for p in Path(out).rglob('*.tga'))

    def test_sony_never_weaves_an_interlaced_mov_again(self):
        import numpy as np
        from PIL import Image
        out = tempfile.mkdtemp(dir=self.tmp)
        m._hula_run_batch([self.i25], out, m.HULA_TARGET_SONY_TGA, standard='1080i50',
                          clip_name='TEST', log=lambda *a: None)
        frames = sorted(Path(out).rglob('*.tga'))
        src = self._source_frames(self.i25)
        self.assertEqual([f.name for f in frames], [f'TEST{i:04d}.tga' for i in range(len(src))])
        for i, f in enumerate(frames):
            with self.subTest(frame=i):
                self.assertTrue(np.array_equal(np.array(Image.open(f).convert('RGBA')), src[i]))

    def test_sony_takes_a_25fps_eif_frame_for_frame(self):
        self.assertEqual(len(self._sony(self.e25, '1080i50')), 4)

    def test_sony_still_weaves_a_50p_source(self):
        self.assertEqual(self._sony(self.p50, '1080i50'), [f'TEST{i:04d}.tga' for i in range(3)])
        self.assertEqual(len(self._sony(self.e50, '1080i50')), 2)

    def test_the_desk_question_is_asked_only_for_fast_progressive_sources(self):
        """The app asks "Is the desk 50p or 50i?" only when the answer changes
        the output."""
        self.assertTrue(m.kframe_tga_asks_desk_format(self.p50))
        self.assertTrue(m.kframe_tga_asks_desk_format(self.e50))
        self.assertFalse(m.kframe_tga_asks_desk_format(self.i25))
        self.assertFalse(m.kframe_tga_asks_desk_format(self.p25))
        self.assertFalse(m.kframe_tga_asks_desk_format(self.e25))

    def test_the_desk_question_for_sws_sources(self):
        """Review: the helper's SWS branch had no test."""
        d = tempfile.mkdtemp(dir=self.tmp)
        m.convert_clip(self.p50, 1, d, video_standard='1080p50', include_audio=False,
                       split_fat32=False, log=lambda *a: None)
        m.convert_clip(self.p50, 2, d, video_standard='1080i50', include_audio=False,
                       split_fat32=False, log=lambda *a: None)
        self.assertTrue(m.kframe_tga_asks_desk_format(os.path.join(d, '1.SWS')))
        self.assertFalse(m.kframe_tga_asks_desk_format(os.path.join(d, '2.SWS')))


class TestInterlacedTgaToEif(unittest.TestCase):
    """An interlaced TGA sequence becomes an EIF the way a K-Frame stores 50i:
    the woven frames as they are, at 25fps. Desk session 2026-10-07: the
    desk's own import of a 50i MOV stored woven 25fps frames, and MacHuna's
    woven 25fps EIF (0912) played correctly on a 1080i 25Hz desk. This route
    used to deinterlace to 50fps progressive, disagreeing with both."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _woven(self, n, size=(1920, 1080)):
        """Frames whose two fields are different colours, as interlace is."""
        import numpy as np
        from PIL import Image
        paths = []
        for i in range(n):
            a = np.zeros((size[1], size[0], 4), dtype=np.uint8)
            a[0::2] = (200, 30 + 40 * i, 30, 255)      # top field
            a[1::2] = (30, 30, 200, 255)               # bottom field
            p = os.path.join(self.tmp, f'w{size[0]}_{i:04d}.tga')
            Image.fromarray(a, 'RGBA').save(p)
            paths.append(p)
        return paths

    def _head(self, eif):
        h = Path(eif).read_bytes()[:0x100]
        return (struct.unpack_from('<I', h, 0x06C)[0], struct.unpack_from('<I', h, 0x0FC)[0],
                struct.unpack_from('<I', h, 0x064)[0])

    def test_woven_frames_are_kept_one_for_one_at_25fps(self):
        tgas = self._woven(4)
        for asked in (25.0, 50.0):
            d = tempfile.mkdtemp(dir=self.tmp)
            eif = m.convert_tga_seq_to_eif(tgas, d, 'I', asked, log=lambda *a: None,
                                           out_name='0001', source_interlaced=True)
            with self.subTest(fps_asked=asked):
                self.assertEqual(self._head(eif), (4, 40000, 0x00010484))

    def test_the_picture_is_exactly_the_woven_frames(self):
        """Same bytes as writing those frames as a plain 25fps sequence: no
        deinterlacing, no field blending."""
        tgas = self._woven(3)
        a = m.convert_tga_seq_to_eif(tgas, tempfile.mkdtemp(dir=self.tmp), 'I', 25.0,
                                     log=lambda *a: None, out_name='0001', source_interlaced=True)
        b = m.convert_tga_seq_to_eif(tgas, tempfile.mkdtemp(dir=self.tmp), 'I', 25.0,
                                     log=lambda *a: None, out_name='0001')
        self.assertEqual(Path(a).read_bytes(), Path(b).read_bytes())

    def test_scaling_keeps_the_fields_apart(self):
        """A 720-line interlaced source scaled to 1080 must not blend its two
        fields into each other."""
        import numpy as np
        tgas = self._woven(1, size=(1280, 720))
        eif = m.convert_tga_seq_to_eif(tgas, self.tmp, 'S', 25.0, log=lambda *a: None,
                                       out_name='0001', source_interlaced=True)
        h = m.EIFHeader(eif)
        with open(eif, 'rb') as f:
            f.seek(h.video_start)
            w = np.frombuffer(f.read(m._EIF_UNIT_BYTES), dtype='<u4').reshape(360, 1920)
        y = ((w >> 10) & 0x3FF).astype(int)[:, 960]
        top, bottom = y[0::2], y[1::2]
        # The two fields stay distinct all the way down: every top-field line
        # keeps one value, every bottom-field line the other.
        self.assertEqual(len(set(top[2:-2])), 1, 'top field lines were blended')
        self.assertEqual(len(set(bottom[2:-2])), 1, 'bottom field lines were blended')
        self.assertNotEqual(top[10], bottom[10])


class TestTkPlayerEifAudio(unittest.TestCase):
    """The Tk Video Player played EIF clips silent: EIFHeader.has_audio was a
    hard-coded False with a "not decoded yet" TODO. It now plays the .eaf."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _eif_with_audio(self):
        import numpy as np
        from PIL import Image
        t = os.path.join(self.tmp, 'f0000.tga')
        Image.new('RGBA', (1920, 1080), (5, 6, 7, 255)).save(t)
        eif = m.convert_tga_seq_to_eif([t], self.tmp, 'P', 25.0, log=lambda *a: None, out_name='0001')
        rng = np.random.default_rng(9)
        stereo = rng.integers(-(1 << 23), 1 << 23, (1920, 2))
        m.write_eaf(m.eaf_path_for(eif), stereo, 1, 25.0)
        return eif, stereo

    def test_the_player_gets_the_eaf_on_its_kahuna_channels(self):
        import numpy as np
        eif, stereo = self._eif_with_audio()
        pcm = m._player_audio_for_eif(eif)
        self.assertIsNotNone(pcm)
        a = np.frombuffer(pcm, dtype='<i2').reshape(-1, 16)
        self.assertTrue(np.array_equal(a[:, 0], stereo[:, 0] >> 8))
        self.assertTrue(np.array_equal(a[:, 2], stereo[:, 1] >> 8))
        self.assertEqual(int(np.abs(a[:, [1] + list(range(3, 16))]).max()), 0)

    def test_eif_header_reports_its_companion(self):
        eif, _ = self._eif_with_audio()
        self.assertTrue(m.EIFHeader(eif).has_audio)
        os.remove(m.eaf_path_for(eif))
        self.assertFalse(m.EIFHeader(eif).has_audio)
        self.assertIsNone(m._player_audio_for_eif(eif))

    def test_a_folder_of_eifs_with_audio_says_so(self):
        """The Tk app shows Include audio only when the scan reports audio;
        EIF folders always said none, so EIF to SWS could not offer it."""
        eif, _ = self._eif_with_audio()
        _items, itype, has_aud, _seq = m._scan_folder_unified(self.tmp)
        self.assertEqual(itype, 'from_eif')
        self.assertTrue(has_aud)
        os.remove(m.eaf_path_for(eif))
        self.assertFalse(m._scan_folder_unified(self.tmp)[2])

    def test_an_unreadable_sws_beside_eifs_does_not_break_the_scan(self):
        """Independent review, 2026-10-08: macOS writes hidden ._ companions on
        FAT32 sticks. A ._1.SWS beside an EIF made the whole folder fail to
        load, because the v1.12.0 audio check read every SWS unguarded."""
        eif, _ = self._eif_with_audio()
        os.remove(m.eaf_path_for(eif))     # no audio, so the scan has to read the SWS
        Path(self.tmp, '._1.SWS').write_bytes(b'\x00' * 4096)
        _items, itype, has_aud, _seq = m._scan_folder_unified(self.tmp)
        self.assertEqual(itype, 'mixed_eif_sws')
        self.assertFalse(has_aud)

    def test_the_tk_app_passes_include_audio_to_eif_to_sws(self):
        src = Path(m.__file__).read_text()
        gui = src[src.index('def launch_gui'):]
        call = gui[gui.index('convert_eif_to_sws('):]
        call = call[:call.index('results.append')]     # the whole call
        self.assertIn('include_audio=include_audio_var.get()', call)

    def test_the_player_loader_uses_it(self):
        src = Path(m.__file__).read_text()
        body = src[src.index('    def _load_eif(self, path: str):'):]
        body = body[:body.index('\n    def ', 10)]
        self.assertIn('_player_audio_for_eif(', body)


class TestEifEncodingFromRgb(unittest.TestCase):
    """The RGB-to-EIF encoder (TGA sequences, and SWS that needs scaling)
    picked every other pixel's colour and truncated instead of rounding, so
    every such EIF was slightly dark and its colour aliased at sharp edges.
    Adopted 2026-10-08: round, and filter the colour [1,2,1] centred on the
    sample that is kept, which brought the TGA route much closer to the
    desk-proven MOV route."""

    def _planes(self, rgba):
        import numpy as np
        u0, u1, u2 = m._encode_eif_frame_from_rgba(rgba)
        w = np.frombuffer(u0 + u1 + u2, dtype='<u4').reshape(1080, 1920)
        C = (w & 0x3FF).astype(int)
        return ((w >> 10) & 0x3FF).astype(int), C[:, 0::2], C[:, 1::2], ((w >> 20) & 0x3FF).astype(int)

    def test_values_are_rounded_not_truncated(self):
        import numpy as np
        rgba = np.full((1080, 1920, 4), (128, 128, 128, 128), dtype=np.uint8)
        Y, Cb, Cr, K = self._planes(rgba)
        # 128/255 * 876 + 64 = 503.72: rounds to 504, truncation gave 503.
        self.assertEqual(int(Y[0, 0]), 504)
        self.assertEqual(int(K[0, 0]), 504)
        self.assertEqual((int(Cb[0, 0]), int(Cr[0, 0])), (512, 512))

    def test_colour_at_a_sharp_edge_is_filtered_not_picked(self):
        import numpy as np
        rgba = np.zeros((1080, 1920, 4), dtype=np.uint8); rgba[..., 3] = 255
        rgba[:, :1001] = (255, 0, 0, 255)     # red up to and including column 1000
        rgba[:, 1001:] = (0, 0, 255, 255)     # blue from column 1001
        _Y, Cb, _Cr, _K = self._planes(rgba)
        cb = lambda rgb: (rgb[2] / 255 - (0.2126 * rgb[0] + 0.0722 * rgb[2]) / 255) / 1.8556 * 896 + 512
        red, blue = cb((255, 0, 0)), cb((0, 0, 255))
        self.assertEqual(int(Cb[0, 499]), int(np.rint(red)))                     # column 998: all red
        # Column 1000 is red, its neighbours 999 (red) and 1001 (blue):
        # (red + 2*red + blue) / 4. Picking would have given pure red.
        self.assertEqual(int(Cb[0, 500]), int(np.rint((red * 3 + blue) / 4)))    # column 1000: blended
        self.assertEqual(int(Cb[0, 501]), int(np.rint(blue)))                    # column 1002: all blue

    @unittest.skipUnless((DESK_2026_10_07 / '0912.eif').exists(),
                         'desk-session files not on this machine')
    def test_tga_route_sits_close_to_the_desk_proven_mov_route(self):
        """TNTS's own TGAs (which loaded correctly on the K-Frame) against
        0912, the desk-proven EIF of the same picture from the 12-bit MOV."""
        import numpy as np
        from PIL import Image
        tgas = sorted((DESK_2026_10_07 / 'tga' / 'as_1080p50' / 'TNTS 50i').glob('*.tga'))
        if not tgas:
            self.skipTest('TNTS TGAs not present')
        ref = (DESK_2026_10_07 / '0912.eif').read_bytes()
        U, H = m._EIF_UNIT_BYTES, 18260
        for n in (12, 20):
            Y, _cb, _cr, _k = self._planes(np.array(Image.open(tgas[n]).convert('RGBA')))
            w = np.frombuffer(ref[H + n * 3 * U:H + (n + 1) * 3 * U], dtype='<u4').reshape(1080, 1920)
            ry = ((w >> 10) & 0x3FF).astype(int)
            with self.subTest(frame=n):
                self.assertLess(abs(float(np.mean(Y - ry))), 0.1, 'brightness is biased')
                self.assertLess(float(np.abs(Y - ry).mean()), 0.2)


class TestEifFromAKeyedClipOfAnySize(unittest.TestCase):
    """Found by the full conversion matrix, 2026-10-08, and present since EIF
    output began: a MOV with a key that was not already 1920x1080 crashed on
    the way to EIF. The picture was scaled to 1920x1080 but the key was
    extracted at the source size, so the key ran out a few lines in."""

    def setUp(self):
        if not shutil.which('ffmpeg') and not os.path.exists(m._get_ffmpeg_path('ffmpeg')):
            self.skipTest('ffmpeg not available')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_a_small_keyed_clip_becomes_an_eif_with_its_key_in_place(self):
        import numpy as np, subprocess
        src = os.path.join(self.tmp, 'small.mov')
        subprocess.run([m._get_ffmpeg_path('ffmpeg'), '-y', '-v', 'error', '-t', '0.12', '-f', 'lavfi',
                        '-i', 'testsrc2=size=192x108:rate=25', '-vf',
                        "format=yuva444p12le,geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='if(lt(X,96),4095,0)'",
                        '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', src], check=True)
        eif = m.convert_clip_to_eif(src, self.tmp, log=lambda *a: None, out_name='0001')
        h = m.EIFHeader(eif)
        self.assertEqual(h.frame_count, 3)
        with open(eif, 'rb') as f:
            f.seek(h.video_start + 3 * m._EIF_UNIT_BYTES)       # second frame
            w = np.frombuffer(f.read(3 * m._EIF_UNIT_BYTES), dtype='<u4').reshape(1080, 1920)
        key = ((w >> 20) & 0x3FF).astype(int)
        # Opaque on the left half, clear on the right, scaled with the picture.
        self.assertGreater(key[540, 400], 900)
        self.assertLess(key[540, 1500], 100)


class TestInterlacedTgaToProgressiveSws(unittest.TestCase):
    """Decision B (David, 2026-10-08): an interlaced TGA sequence going to a
    progressive SWS at the frame rate (25/29.97/30p) gets one deinterlaced
    frame per interlaced frame. It always split each frame into two fields,
    right for 50p but at 25p doubling the frames and halving the speed."""

    def setUp(self):
        if not shutil.which('ffmpeg') and not os.path.exists(m._get_ffmpeg_path('ffmpeg')):
            self.skipTest('ffmpeg not available')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        import numpy as np
        from PIL import Image
        self.tgas = []
        for i in range(6):
            a = np.zeros((108, 192, 4), dtype=np.uint8); a[..., 3] = 255
            a[0::2, :, 0] = 40 * i; a[1::2, :, 2] = 200
            p = os.path.join(self.tmp, f'I_{i:04d}.tga')
            Image.fromarray(a, 'RGBA').save(p); self.tgas.append(p)

    def _frames(self, std):
        d = tempfile.mkdtemp(dir=self.tmp)
        out = m.convert_tga_sequence(self.tgas, 1, d, std, False, False, lambda *a: None,
                                     write_log=False, source_interlaced=True)
        return m.HulaSWSHeader(out).frame_count

    def test_frame_rate_progressive_keeps_one_frame_per_interlaced_frame(self):
        self.assertEqual(self._frames('1080p25'), 6)

    def test_field_rate_progressive_still_splits_the_fields(self):
        self.assertEqual(self._frames('1080p50'), 12)
        self.assertEqual(self._frames('1080p5994'), 12)


class TestEifToSwsHonoursTheStandard(unittest.TestCase):
    """Decisions C and D (David, 2026-10-08). EIF to SWS ignored the chosen
    standard (25fps always became 1080p25, though a 25fps EIF usually holds
    woven 50i), and a keyless EIF - whose stored key is opaque throughout -
    gained a solid key plane, against "no key in, no key out"."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _eif(self, fps, frames, keyed):
        import numpy as np
        from PIL import Image
        tgas = []
        for i in range(frames):
            a = np.zeros((1080, 1920, 4), dtype=np.uint8)
            a[..., 0] = 20 * i; a[..., 1] = 100; a[..., 3] = 255
            if keyed:
                a[:, 960:, 3] = 0
            p = os.path.join(self.tmp, f'k{int(keyed)}_{fps}_{i:04d}.tga')
            Image.fromarray(a, 'RGBA').save(p); tgas.append(p)
        return m.convert_tga_seq_to_eif(tgas, self.tmp, 'E', float(fps), log=lambda *a: None,
                                        out_name=f'{int(keyed)}{fps:03d}')

    def _sws(self, eif, std):
        d = tempfile.mkdtemp(dir=self.tmp)
        return m.convert_eif_to_sws(eif, 1, d, video_standard=std, split_fat32=False,
                                    log=lambda *a: None)

    def test_a_25fps_eif_can_be_1080i50(self):
        h = m.HulaSWSHeader(self._sws(self._eif(25, 4, True), '1080i50'))
        self.assertEqual(h.standard.replace('/', ''), '1080i50')
        self.assertEqual(h.frame_count, 4)

    def test_a_50fps_eif_is_woven_for_1080i50(self):
        import numpy as np
        out = self._sws(self._eif(50, 4, True), '1080i50')
        h = m.HulaSWSHeader(out)
        self.assertEqual((h.standard.replace('/', ''), h.frame_count), ('1080i50', 2))
        # Lines alternate between the two source frames (different red levels).
        rgb, _a = m._hula_decode_frame(Path(out).read_bytes()[h.data_offset:h.data_offset + h.plane_size],
                                       None, h.width, h.height)
        self.assertNotEqual(int(rgb[100, 100, 0]), int(rgb[101, 100, 0]))
        self.assertEqual(int(rgb[100, 100, 0]), int(rgb[102, 100, 0]))

    def test_other_progressive_rates_keep_the_duration(self):
        h = m.HulaSWSHeader(self._sws(self._eif(50, 4, True), '1080p25'))
        self.assertEqual((h.frame_count, h.fps), (2, 25.0))
        h = m.HulaSWSHeader(self._sws(self._eif(25, 4, True), '1080p50'))
        self.assertEqual((h.frame_count, h.fps), (8, 50.0))

    def test_other_interlaced_rates_are_refused(self):
        with self.assertRaises(ValueError):
            self._sws(self._eif(25, 2, True), '1080i5994')

    def test_a_keyless_eif_gives_an_sws_without_a_key_plane(self):
        self.assertFalse(m.HulaSWSHeader(self._sws(self._eif(25, 2, False), '1080p25')).has_key)
        self.assertTrue(m.HulaSWSHeader(self._sws(self._eif(25, 2, True), '1080p25')).has_key)


REFERENCE_EIF_DIR = Path(os.path.expanduser('~/Desktop/TEST WIPES/50i/EIF'))


def _reference_files_readable():
    """Existing is not the same as listable.

    macOS 27 reset the TCC grants, so this directory reports as present while
    listing it raises PermissionError. Checking is_dir() alone let the test
    run against nothing and fail for a reason that has nothing to do with the
    code under test.
    """
    try:
        return any(REFERENCE_EIF_DIR.glob('*.eif'))
    except OSError:
        return False


@unittest.skipUnless(_reference_files_readable(),
                     'reference K-Frame files not readable on this machine')
class TestEafAgainstRealFiles(unittest.TestCase):
    """The six real .eaf files. Their audio must line up with their video."""

    def test_audio_duration_equals_video_duration(self):
        checked = 0
        for eif in sorted(REFERENCE_EIF_DIR.glob('*.eif')):
            pcm = m.read_eaf_stereo(m.eaf_path_for(str(eif)), log=lambda *a: None)
            if pcm is None:
                continue
            h = m.EIFHeader(str(eif))
            audio_s = (len(pcm) // 4) / float(m.EAF_SAMPLE_RATE)   # stereo s16: 4 bytes per sample
            video_s = h.frame_count / h.fps
            with self.subTest(clip=eif.name):
                self.assertAlmostEqual(audio_s, video_s, places=2)
            checked += 1
        self.assertGreater(checked, 0, 'no .eaf companions found to check')

    def test_clips_without_a_companion_read_as_no_audio(self):
        for eif in sorted(REFERENCE_EIF_DIR.glob('*.eif')):
            if not Path(m.eaf_path_for(str(eif))).exists():
                with self.subTest(clip=eif.name):
                    self.assertIsNone(m.read_eaf_stereo(m.eaf_path_for(str(eif))))


REFERENCE_EIF_DIRS = (REFERENCE_EIF_DIR,
                      Path(os.path.expanduser('~/Desktop/TEST WIPES/50P/EIF')))

# EIF header 0x064 rate code, as every desk-made reference file has it:
# 0x10484 in all 18 at 25fps, 0x104A4 in all 10 at 50fps.
EIF_RATE_CODE = {25: 0x00010484, 50: 0x000104A4}


def _eif_rate_and_duration(path):
    with open(path, 'rb') as f:
        head = f.read(0x100)
    return struct.unpack_from('<I', head, 0x064)[0], struct.unpack_from('<I', head, 0x0FC)[0]


class TestEifRateCode(unittest.TestCase):
    """The K-Frame reads 0x064 as the clip's rate. Desk session 2026-10-07: a
    25fps MacHuna EIF carrying the 50fps code played too fast on a 1080i 25Hz
    desk, and the same file with only that field corrected played correctly.

    Driven through every EIF writer, because all four call the header builder
    and a fix that reached only one would be the "one of four paths" failure
    this suite has seen before. Read back from the file on disk."""

    def setUp(self):
        if not shutil.which('ffmpeg') and not os.path.exists(m._get_ffmpeg_path('ffmpeg')):
            self.skipTest('ffmpeg not available')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.quiet = lambda *a, **k: None

    def _mov(self, fps):
        import subprocess
        out = os.path.join(self.tmp, f'src{fps}.mov')
        subprocess.run([m._get_ffmpeg_path('ffmpeg'), '-y', '-v', 'error', '-f', 'lavfi',
                        '-i', f'testsrc=size=192x108:rate={fps}',
                        '-frames:v', '2', '-c:v', 'prores_ks', '-profile:v', '3',
                        '-pix_fmt', 'yuv422p10le', out], check=True)
        return out

    def _outputs(self, fps):
        """One EIF from each of the four writers, all at this rate."""
        made = {}
        d = os.path.join(self.tmp, f'out{fps}')
        os.makedirs(d, exist_ok=True)
        src = self._mov(fps)

        made['clip'] = m.convert_clip_to_eif(src, d, log=self.quiet, out_name=f'clip{fps}')

        from PIL import Image
        tgas = []
        for i in range(2):
            p = os.path.join(self.tmp, f't{fps}_{i:04d}.tga')
            Image.new('RGBA', (1920, 1080), (40 * i, 80, 160, 255)).save(p)
            tgas.append(p)
        made['tga'] = m.convert_tga_seq_to_eif(tgas, d, f'TGA{fps}', float(fps),
                                               log=self.quiet, out_name=f'tga{fps}')
        if fps == 25:
            # An interlaced TGA sequence is always written at 25fps, woven, as
            # a K-Frame stores 50i; so it is checked here, even when asked for 50.
            made['tga_interlaced'] = m.convert_tga_seq_to_eif(
                tgas, d, 'TGAI', 50.0, log=self.quiet, out_name='tgai',
                source_interlaced=True)

        # convert_sws_to_eif takes its rate from the SWS: 1080i50 is 25fps, 1080p50 is 50.
        sws_dir = os.path.join(self.tmp, f'sws{fps}')
        os.makedirs(sws_dir, exist_ok=True)
        std = '1080i50' if fps == 25 else '1080p50'
        sws_src = self._mov(50)     # 50p source: woven to 1080i50, or kept for 1080p50
        m.convert_clip(sws_src, 7, sws_dir, video_standard=std, include_audio=False,
                       split_fat32=False, log=self.quiet)
        made['sws'] = m.convert_sws_to_eif(os.path.join(sws_dir, '7.SWS'), d,
                                           log=self.quiet, out_name=f'sws{fps}')
        return made

    def test_every_writer_stamps_the_rate_code_for_its_own_rate(self):
        for fps, dur in ((25, 40000), (50, 20000)):
            for route, path in self._outputs(fps).items():
                rate, got_dur = _eif_rate_and_duration(path)
                with self.subTest(route=route, fps=fps):
                    self.assertEqual(got_dur, dur, 'frame duration must say the clip rate')
                    self.assertEqual(hex(rate), hex(EIF_RATE_CODE[fps]),
                                     f'0x064 must be the {fps}fps rate code')

    @unittest.skipUnless(_reference_files_readable(),
                         'reference K-Frame files not readable on this machine')
    def test_builder_matches_every_desk_made_file(self):
        """The expected codes above come from the desk, not from memory: every
        reference file's own 0x064 must equal what the builder writes for that
        file's rate."""
        checked = 0
        for folder in REFERENCE_EIF_DIRS:
            for eif in sorted(folder.glob('*.eif')):
                rate, dur = _eif_rate_and_duration(eif)
                fps = 1_000_000 // dur
                built = struct.unpack_from('<I', m._build_eif_header('X', 1, float(fps)), 0x064)[0]
                with self.subTest(clip=f'{folder.parent.name}/{eif.name}', fps=fps):
                    self.assertEqual(rate, EIF_RATE_CODE[fps])
                    self.assertEqual(hex(built), hex(rate))
                checked += 1
        self.assertEqual(checked, 28, 'expected all 28 desk-made reference files')


class TestMovNaming(unittest.TestCase):
    """QuickTime MOV names.

    Unlike a slot number, a blank field here is VALID and means "name it after
    the source" - that was the behaviour before naming existed and it stays
    the default. So the interesting cases are that blank passes validation,
    and that several blanks do not accuse each other of being duplicates.
    """

    MODE = 'mov'

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_blank_is_valid_and_means_source_name(self):
        self.assertEqual(m.normalise_bespoke_value('', self.MODE), '')
        self.assertEqual(m.normalise_bespoke_value('   ', self.MODE), '')

    def test_a_typed_name_becomes_that_file(self):
        v = m.normalise_bespoke_value('Wipe 01', self.MODE)
        self.assertEqual(v, 'Wipe 01')
        self.assertEqual(m.bespoke_output_name(v, self.MODE), 'Wipe 01.mov')

    def test_a_typed_extension_is_not_doubled(self):
        v = m.normalise_bespoke_value('promo.mov', self.MODE)
        self.assertEqual(m.bespoke_output_name(v, self.MODE), 'promo.mov')

    def test_names_that_would_not_survive_a_filesystem_are_refused(self):
        for bad in ('a/b', 'a:b', 'a*b', 'a?b', '.hidden', 'x' * 65):
            with self.subTest(bad=bad):
                self.assertIsNone(m.normalise_bespoke_value(bad, self.MODE))

    def test_several_blank_rows_are_not_duplicates_of_each_other(self):
        entries = [('one', ''), ('two', ''), ('three', '')]
        codes, problems = m._analyse_bespoke_ids(entries, self.MODE, self.tmp)
        self.assertEqual(codes, [None, None, None], problems)
        self.assertEqual(problems, [])

    def test_two_rows_with_the_same_typed_name_are_blocked(self):
        entries = [('one', 'same'), ('two', 'same'), ('three', '')]
        codes, problems = m._analyse_bespoke_ids(entries, self.MODE, self.tmp)
        self.assertIsNotNone(codes[0])
        self.assertIsNotNone(codes[1])
        self.assertIsNone(codes[2], 'the blank row should be untouched')
        self.assertTrue(problems)

    def test_a_name_that_already_exists_in_the_destination_is_blocked(self):
        Path(self.tmp, 'taken.mov').write_bytes(b'x')
        codes, problems = m._analyse_bespoke_ids([('one', 'taken')], self.MODE, self.tmp)
        self.assertIsNotNone(codes[0])
        self.assertTrue(any('taken.mov' in p for p in problems), problems)

    def test_a_blank_row_cannot_collide_with_the_destination(self):
        # Nothing is typed, so there is no value to clash with anything.
        Path(self.tmp, 'taken.mov').write_bytes(b'x')
        codes, problems = m._analyse_bespoke_ids([('one', '')], self.MODE, self.tmp)
        self.assertEqual(codes, [None])
        self.assertEqual(problems, [])


class TestMovFrameRate(unittest.TestCase):
    """A QuickTime MOV is not a broadcast standard.

    Tying its rate to the seven verified Kahuna standards made 30fps material
    unconvertible: the only 30fps entries there are INTERLACED, so reaching 30
    meant weaving fields into a QuickTime. David hit it within minutes of
    v1.10.1 shipping - a 30fps sequence came out at double speed.
    """

    def test_the_rates_the_sws_list_could_not_offer_progressively(self):
        # These are the ones that caused the bug: present in VIDEO_STANDARDS
        # only as interlaced standards, so unreachable without a field weave.
        self.assertIn('30', m.MOV_FRAME_RATES)
        self.assertIn('29.97', m.MOV_FRAME_RATES)

    def test_no_sws_standard_offers_30_progressive(self):
        """Guard on the reason this bug existed, so it is not reintroduced."""
        progressive = {s: m.FORMAT_VARIANT_FPS.get(m.FORMAT_VARIANTS.get(s, 0))
                       for s in m.VIDEO_STANDARDS if 'i' not in s}
        self.assertNotIn(30.0, progressive.values(),
                         'a progressive 30fps SWS standard now exists - the MOV '
                         'rate control may no longer be needed for that case')

    def test_rates_parse_to_sensible_numbers(self):
        for r in m.MOV_FRAME_RATES:
            with self.subTest(rate=r):
                self.assertAlmostEqual(m.parse_mov_fps(r), float(r), places=3)

    def test_nonsense_falls_back_rather_than_crashing(self):
        default = float(m.DEFAULT_MOV_FPS)
        for bad in ('', '   ', 'abc', None, '0', '-5', '9999'):
            with self.subTest(bad=bad):
                self.assertEqual(m.parse_mov_fps(bad), default)


class TestMovDurationFollowsTheStatedRate(unittest.TestCase):
    """The outcome, not the setting: the file must actually last that long.

    Asserting on the rate we passed in would have passed happily while the
    bug was live, because the rate was never wrong - it was the wrong rate.
    """

    def setUp(self):
        if not shutil.which('ffmpeg') and not os.path.exists(m._get_ffmpeg_path('ffmpeg')):
            self.skipTest('ffmpeg not available')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _sequence(self, n, w=64, h=64):
        from PIL import Image
        import numpy as np
        files = []
        for i in range(n):
            a = np.zeros((h, w, 4), dtype=np.uint8)
            a[:, :, 0] = (i * 8) % 256
            a[:, :, 3] = 255
            f = os.path.join(self.tmp, 'f%04d.tga' % i)
            Image.fromarray(a, 'RGBA').save(f, format='TGA')
            files.append(f)
        return files

    def _duration(self, path):
        import subprocess
        ff = m._get_ffmpeg_path('ffprobe')
        out = subprocess.run([ff, '-v', 'error', '-show_entries', 'format=duration',
                              '-of', 'csv=p=0', path], capture_output=True, text=True)
        return float(out.stdout.strip())

    def test_thirty_frames_at_thirty_fps_lasts_one_second(self):
        files = self._sequence(30)
        out = m.convert_tga_seq_to_mov(files, self.tmp, 'thirty', 30.0,
                                       log=lambda *a: None)
        self.assertAlmostEqual(self._duration(out), 1.0, places=1)

    def test_the_same_frames_at_sixty_fps_last_half_a_second(self):
        """The old behaviour, now reachable only by asking for it."""
        files = self._sequence(30)
        out = m.convert_tga_seq_to_mov(files, self.tmp, 'sixty', 60.0,
                                       log=lambda *a: None)
        self.assertAlmostEqual(self._duration(out), 0.5, places=1)


class TestMovRateComesFromItsOwnControl(unittest.TestCase):
    """Structural guard, because the behavioural tests cannot see this.

    The double-speed bug lived in _run_to_tga_seq, inside launch_gui(), which
    no unit test can reach. Tests of convert_tga_seq_to_mov pass happily while
    the GUI hands it the wrong number - verified by reintroducing the bug and
    watching them stay green. This asserts the runner reaches for the MOV rate
    control rather than the SWS Standard dropdown.
    """

    def test_the_tga_runner_uses_the_mov_rate_control(self):
        fns = _nested_functions(_launch_gui_tree())
        self.assertIn('_run_to_tga_seq', fns)
        names = _calls_within(fns['_run_to_tga_seq'])
        self.assertIn('parse_mov_fps', names,
                      '_run_to_tga_seq no longer parses a MOV frame rate - a MOV '
                      'may have gone back to taking its rate from the SWS '
                      'Standard list, which has no progressive 30fps')
        self.assertIn('mov_fps_var', names,
                      '_run_to_tga_seq no longer reads the MOV rate control')

    def test_the_rate_control_is_actually_built(self):
        # A guard on a control that does not exist would assert nothing.
        src = Path(__file__).with_name('machuna.py').read_text()
        self.assertIn('frm_row_movfps', src)
        self.assertIn('mov_fps_var', src)


class TestMovDeinterlacing(unittest.TestCase):
    """A MOV is never WOVEN, but an interlaced source must still be DEINTERLACED.

    Those are two different things and v1.10.2 wrongly dropped both, on the
    reasoning that ProRes carries no field-order flag. True, and irrelevant:
    if the incoming frames already contain fields, a progressive file made
    from them stays combed. Spotted by David.
    """

    def setUp(self):
        if not shutil.which('ffmpeg') and not os.path.exists(m._get_ffmpeg_path('ffmpeg')):
            self.skipTest('ffmpeg not available')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _interlaced_sequence(self, n, w=64, h=64):
        from PIL import Image
        import numpy as np
        files = []
        for i in range(n):
            a = np.zeros((h, w, 4), dtype=np.uint8)
            a[0::2, :, 0] = 255          # one field
            a[1::2, :, 1] = 255          # the other
            a[:, :, 3] = 255
            f = os.path.join(self.tmp, 'i%04d.tga' % i)
            Image.fromarray(a, 'RGBA').save(f, format='TGA')
            files.append(f)
        return files

    def _probe(self, path):
        import subprocess
        ff = m._get_ffmpeg_path('ffprobe')
        out = subprocess.run([ff, '-v', 'error', '-show_entries',
                              'stream=nb_frames', '-show_entries', 'format=duration',
                              '-of', 'csv=p=0', path], capture_output=True, text=True)
        parts = out.stdout.split()
        return int(parts[0]), float(parts[1])

    def test_bobbing_doubles_the_frames_and_keeps_the_duration(self):
        files = self._interlaced_sequence(25)
        out = m.convert_tga_seq_to_mov(
            files, self.tmp, 'bob', 25.0,
            vf='yadif=mode=send_field:parity=tff', out_fps=50.0,
            log=lambda *a: None)
        frames, duration = self._probe(out)
        self.assertEqual(frames, 50, 'bob should give one frame per field')
        self.assertAlmostEqual(duration, 1.0, places=1,
                               msg='deinterlacing must not change how long it runs')

    def test_out_fps_defaults_to_the_source_rate(self):
        """Without deinterlacing nothing changes, so the two rates must match."""
        files = self._interlaced_sequence(25)
        out = m.convert_tga_seq_to_mov(files, self.tmp, 'plain', 25.0,
                                       log=lambda *a: None)
        frames, duration = self._probe(out)
        self.assertEqual(frames, 25)
        self.assertAlmostEqual(duration, 1.0, places=1)


class TestMovRunnerStillDeinterlaces(unittest.TestCase):
    """Structural guard: the behavioural tests above cannot see the GUI.

    v1.10.2 removed the deinterlace path from _run_to_tga_seq's MOV branch
    while every test stayed green, because that code lives in launch_gui().
    """

    def test_the_mov_branch_reads_the_interlaced_tickbox(self):
        fns = _nested_functions(_launch_gui_tree())
        names = _calls_within(fns['_run_to_tga_seq'])
        self.assertIn('src_interlaced', names,
                      'the MOV branch no longer consults the interlaced tickbox - '
                      'an interlaced TGA sequence would come out combed')
        # mov_vf / mov_out exist only to carry the deinterlace filter and the
        # doubled output rate. (Keyword-argument names are not Name nodes, so
        # asserting on 'out_fps' itself would silently pass regardless.)
        self.assertIn('mov_vf', names,
                      'the MOV branch no longer builds a deinterlace filter')
        self.assertIn('mov_out', names,
                      'the MOV branch no longer computes a doubled output rate, '
                      'so bobbed frames would be thrown away again')


class TestKeylessSourceGetsNoKeyPlane(unittest.TestCase):
    """A source with no alpha produces an SWS with no key plane.

    MacHuna used to generate a flat plane here, copying K-Watch. Confirmed on a
    live Kahuna on 2026-09-18: that plane loads as a black key and keys out to
    nothing, so it was never usable - it only doubled the file size. This is
    MacHuna's first deliberate divergence from K-Watch, made on evidence.
    """

    def test_generate_white_key_stays_deleted(self):
        src = Path(__file__).with_name('machuna.py').read_text()
        self.assertNotIn('_generate_white_key', src,
                         'the flat key plane is back - it loads as a black key '
                         'on a Kahuna and keys out to nothing')

    def test_no_flat_key_pattern_anywhere_in_the_writer(self):
        # The v210 bytes that produced Y=64. Documented in DEVELOPMENT_NOTES as
        # reference; must not reappear as something the app writes.
        src = Path(__file__).with_name('machuna.py').read_text()
        self.assertNotIn('0x20, 0x01, 0x02, 0x00, 0x04, 0x08, 0x00, 0x40', src)


class TestKeylessConversionOutcome(unittest.TestCase):
    """The observable result, not the code: header says no key, file is half."""

    def setUp(self):
        if not shutil.which('ffmpeg') and not os.path.exists(m._get_ffmpeg_path('ffmpeg')):
            self.skipTest('ffmpeg not available')
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def _keyless_clip(self):
        """A small progressive clip with no alpha channel at all."""
        import subprocess
        out = os.path.join(self.tmp, 'nokey.mov')
        ff = m._get_ffmpeg_path('ffmpeg')
        subprocess.run([ff, '-y', '-v', 'error', '-f', 'lavfi',
                        '-i', 'testsrc=size=192x108:rate=50:duration=0.2',
                        '-c:v', 'prores_ks', '-profile:v', '3',
                        '-pix_fmt', 'yuv422p10le', out], check=True)
        return out

    def test_a_keyless_source_writes_no_key_plane_either_way(self):
        src = self._keyless_clip()
        self.assertFalse(m.get_video_info(src)['has_alpha'], 'test source must have no alpha')
        sizes = {}
        for ignore in (False, True):
            d = os.path.join(self.tmp, 'ig' if ignore else 'keep')
            os.makedirs(d, exist_ok=True)
            m.convert_clip(src, 1, d, video_standard='1080p50', ignore_alpha=ignore,
                           include_audio=False, split_fat32=False, log=lambda *a: None)
            p = os.path.join(d, '1.SWS')
            h = m.HulaSWSHeader(p)
            with self.subTest(ignore_alpha=ignore):
                self.assertFalse(h.has_key,
                                 'a source with no alpha must not produce a key plane')
            sizes[ignore] = os.path.getsize(p)
        self.assertEqual(sizes[False], sizes[True],
                         'the tickbox must make no difference when there is no alpha')
