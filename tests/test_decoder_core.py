import struct
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import samsung_ifg_decoder as decoder


def qm_header(width: int, height: int, *, depth: int = 1) -> decoder.QmHeader:
    flags5 = 0x01
    if depth == 2:
        flags5 |= 0x40
    return decoder.QmHeader(
        width=width,
        height=height,
        version=decoder.QM_VERSION_0B,
        raw_type=0x03,
        flags4=0,
        flags5=flags5,
        encoder_mode=decoder.QM_ENCODER_W2_PASS,
        alpha_depth=1,
        depth=depth,
        alpha_position=0,
        header_size=16,
    )


class BitReaderTests(unittest.TestCase):
    def test_reads_msb_first_from_one_based_position(self) -> None:
        reader = decoder.BitReader(bytes([0b1010_0101]), bit_position=1)

        self.assertEqual(reader.read(4), 0b1010)
        self.assertEqual(reader.read(4), 0b0101)


class QmW2Tests(unittest.TestCase):
    def test_depth1_raw_group_repeats_previous_pixel_for_odd_tail(self) -> None:
        header = qm_header(3, 1)
        body = struct.pack("<IIII", 0, 1, 0, 0)
        body += b"\x00"
        body += struct.pack("<HH", 0x1234, 0xABCD)

        self.assertEqual(decoder.decode_qm_w2_depth1(header, body), [0x1234, 0xABCD, 0xABCD])

    def test_depth1_table_run_clamps_at_odd_tail(self) -> None:
        header = qm_header(3, 1)
        body = struct.pack("<IIII", 1, 1, 1, 0)
        body += struct.pack("<HH", 0x1111, 0x2222)
        body += b"\x01"
        body += b"\x01"

        self.assertEqual(decoder.decode_qm_w2_depth1(header, body), [0x1111, 0x2222, 0x2222])


class AlphaPackingTests(unittest.TestCase):
    def test_unpack_qm_alpha_samples_handles_odd_width(self) -> None:
        header = qm_header(3, 1)

        self.assertEqual(decoder.unpack_qm_alpha_samples(header, [0x1122, 0x3344]), [0x22, 0x11, 0x44])


class InspectTests(unittest.TestCase):
    def test_inspect_reports_qm_raw_type_0_as_supported_no_alpha(self) -> None:
        data = b"QM" + bytes([decoder.QM_VERSION_0B, 0x00, 0x00, 0xC0])
        data += struct.pack("<HHBB", 8, 13, 0, 0)
        data += struct.pack("<II", 32, 36)

        header = decoder.parse_qm_header(data)
        self.assertEqual(header.raw_type, 0x00)
        self.assertEqual(header.header_size, 12)

        row = decoder.inspect_samsung_image(data)
        self.assertEqual(row["family"], "QM")
        self.assertEqual(row["width"], "8")
        self.assertEqual(row["height"], "13")
        self.assertEqual(row["command_offset"], "32")
        self.assertEqual(row["raw_offset"], "36")
        self.assertEqual(row["supported"], "yes")
        self.assertIn("RGB565/no-alpha", row["notes"])

    def test_inspect_reports_w2_body_fields_without_a9ll_offsets(self) -> None:
        data = b"QM" + bytes([decoder.QM_VERSION_0B, 0x03, 0x00, 0x61])
        data += struct.pack("<HHBBI", 3, 1, 0, 0, 32)
        data += struct.pack("<III", 16, 1, 2)

        row = decoder.inspect_samsung_image(data)
        self.assertEqual(row["codec"], "W2")
        self.assertEqual(row["stream_start"], "16")
        self.assertEqual(row["command_offset"], "")
        self.assertEqual(row["raw_offset"], "")
        self.assertIn("w2_intermediate_size=16", row["notes"])


class AnalyzeTests(unittest.TestCase):
    def test_analyze_walks_minimal_a9ll_stream(self) -> None:
        tables = decoder.CodecTables([], [], [])
        data = b"QM" + bytes([decoder.QM_VERSION_0B, 0x03, 0x00, 0x00])
        data += struct.pack("<HHBBI", 4, 4, 0, 0, 0)
        data += struct.pack("<II", 25, 25)
        data += b"\xC0"

        row = decoder.analyze_samsung_image(data, tables)
        self.assertEqual(row["decode_status"], "decoded")
        self.assertEqual(row["analysis_status"], "ok")
        self.assertEqual(row["tile_count"], "1")
        self.assertEqual(row["edge_copy_tiles"], "1")
        self.assertEqual(row["control_bits_read"], "2")

    def test_analyze_keeps_decode_failure_separate_from_stream_walk(self) -> None:
        tables = decoder.CodecTables([], [], [])
        data = b"QM" + bytes([decoder.QM_VERSION_0B, 0x06, 0x00, 0xC0])
        data += struct.pack("<HHBBI", 4, 4, 0, 0, 0)
        data += struct.pack("<II", 25, 25)
        data += b"\xC0"

        row = decoder.analyze_samsung_image(data, tables)
        self.assertEqual(row["decode_status"], "failed")
        self.assertIn("raw type", row["decode_error"])
        self.assertEqual(row["analysis_status"], "ok")
        self.assertEqual(row["tile_count"], "1")

    def test_analyze_warns_when_a9ll_raw_stream_overruns_alpha_split(self) -> None:
        tables = decoder.CodecTables([], [], [])
        data = b"QM" + bytes([decoder.QM_VERSION_0B, 0x03, 0x00, 0x00])
        data += struct.pack("<HHBBI", 4, 4, 0, 0, 28)
        data += struct.pack("<II", 25, 26)
        data += b"\x00"
        data += b"\xE0"
        data += b"\xFE\xFF"
        data += b"\x34\x12"

        row = decoder.analyze_samsung_image(data, tables)
        self.assertEqual(row["decode_status"], "decoded")
        self.assertEqual(row["analysis_status"], "warning")
        self.assertEqual(row["raw_limit_offset"], "28")
        self.assertEqual(row["raw_limit_bytes"], "2")
        self.assertEqual(row["raw_bytes_read"], "4")
        self.assertEqual(row["raw_overrun_bytes"], "2")
        self.assertIn("overran color limit", row["analysis_error"])

    def test_analyze_warns_when_a9ll_command_stream_overruns_split(self) -> None:
        tables = decoder.CodecTables([], [], [])
        data = b"QM" + bytes([decoder.QM_VERSION_0B, 0x03, 0x00, 0x00])
        data += struct.pack("<HHBBI", 4, 4, 0, 0, 0)
        data += struct.pack("<II", 25, 25)
        data += b"\x00"
        data += b"\xFE\xFF"
        data += b"\x34\x12"

        row = decoder.analyze_samsung_image(data, tables)
        self.assertEqual(row["decode_status"], "decoded")
        self.assertEqual(row["analysis_status"], "warning")
        self.assertEqual(row["command_limit_bits"], "0")
        self.assertEqual(row["command_bits_read"], "3")
        self.assertEqual(row["command_overrun_bits"], "3")
        self.assertEqual(row["raw_overrun_bytes"], "0")
        self.assertIn("command stream overran", row["analysis_error"])


class QmA9llTests(unittest.TestCase):
    def test_raw_type_0_decodes_a9ll_rgb565_without_alpha(self) -> None:
        tables = decoder.CodecTables([], [], [0] * 512)
        tables.delta16_decode_b[256] = 1
        data = b"QM" + bytes([decoder.QM_VERSION_0B, decoder.QM_RAW_TYPE_RGB565_NO_ALPHA, 0x00, decoder.QM_FLAG_USE_EXTRA_EXCEPTION])
        data += struct.pack("<HHBB", 4, 4, 0, 0)
        data += struct.pack("<II", 22, 23)
        data += b"\x20\x00"
        data += b"\xE0"
        data += b"\xFC\xFF"
        data += b"\x34\x12"

        width, height, pixels, type_label = decoder.decode_samsung_image(data, tables)
        self.assertEqual((width, height), (4, 4))
        self.assertEqual(type_label, "QM_0x0B_A9LL")
        self.assertEqual(pixels[:4], [0x1234, 0x1235, 0x1235, 0x1235])
        self.assertIsNone(decoder.decode_samsung_alpha(data, tables))

    def test_use_extra_exception_decodes_raw_flag_and_command_7_delta(self) -> None:
        tables = decoder.CodecTables([], [], [0] * 512)
        tables.delta16_decode_b[256] = 1
        data = b"QM" + bytes([decoder.QM_VERSION_0B, 0x03, 0x00, decoder.QM_FLAG_USE_EXTRA_EXCEPTION])
        data += struct.pack("<HHBBI", 4, 4, 0, 0, 31)
        data += struct.pack("<II", 26, 27)
        data += b"\x20\x00"
        data += b"\xE0"
        data += b"\xFC\xFF"
        data += b"\x34\x12"

        width, height, pixels, type_label = decoder.decode_samsung_image(data, tables)
        self.assertEqual((width, height), (4, 4))
        self.assertEqual(type_label, "QM_0x0B_A9LL")
        self.assertEqual(pixels[:4], [0x1234, 0x1235, 0x1235, 0x1235])

        row = decoder.analyze_samsung_image(data, tables)
        self.assertEqual(row["decode_status"], "decoded")
        self.assertEqual(row["analysis_status"], "ok")
        self.assertEqual(row["literal_pixels"], "1")
        self.assertEqual(row["delta_pixels"], "1")
        self.assertEqual(row["command_bits_read"], "3")
        self.assertEqual(row["control_bits_read"], "12")
        self.assertEqual(row["raw_bytes_read"], "4")
        self.assertEqual(row["raw_overrun_bytes"], "0")


class ColorTests(unittest.TestCase):
    def test_rgb565_to_rgb888(self) -> None:
        self.assertEqual(decoder.rgb565_to_rgb888(0xF800), (255, 0, 0))
        self.assertEqual(decoder.rgb565_to_rgb888(0x07E0), (0, 255, 0))
        self.assertEqual(decoder.rgb565_to_rgb888(0x001F), (0, 0, 255))


if __name__ == "__main__":
    unittest.main()
