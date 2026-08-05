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
    its own rate while the header claims 25/50, and the Kayenne plays it at the
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

        def fake_header(clip_name, frame_count, fps):
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
