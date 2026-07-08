"""
Unit tests for MacHuna header builder and format constants.

Run with:  /opt/homebrew/bin/python3.12 -m pytest test_machuna.py -v
       or: /opt/homebrew/bin/python3.12 -m unittest test_machuna -v
"""

import struct
import sys
import unittest

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

    def test_same_rate_message_names_the_speed_problem(self):
        # The blocking error must be actionable, not a bare exception.
        try:
            m._p_to_i_field_map(25.0, '1080i50')
            self.fail('expected ValueError')
        except ValueError as e:
            self.assertIn('1080i50', str(e))
            self.assertIn('speed', str(e).lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
