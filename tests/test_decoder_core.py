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
    def test_inspect_reports_qm_raw_type_0_without_enabling_decode(self) -> None:
        data = b"QM" + bytes([decoder.QM_VERSION_0B, 0x00, 0x00, 0xC0])
        data += struct.pack("<HHBB", 8, 13, 0, 0)
        data += struct.pack("<II", 32, 36)

        with self.assertRaisesRegex(ValueError, "raw type"):
            decoder.parse_qm_header(data)

        header = decoder.parse_qm_header(data, strict=False)
        self.assertEqual(header.raw_type, 0x00)
        self.assertEqual(header.header_size, 12)

        row = decoder.inspect_samsung_image(data)
        self.assertEqual(row["family"], "QM")
        self.assertEqual(row["width"], "8")
        self.assertEqual(row["height"], "13")
        self.assertEqual(row["command_offset"], "32")
        self.assertEqual(row["raw_offset"], "36")
        self.assertEqual(row["supported"], "no")
        self.assertIn("raw type", row["notes"])

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


class ColorTests(unittest.TestCase):
    def test_rgb565_to_rgb888(self) -> None:
        self.assertEqual(decoder.rgb565_to_rgb888(0xF800), (255, 0, 0))
        self.assertEqual(decoder.rgb565_to_rgb888(0x07E0), (0, 255, 0))
        self.assertEqual(decoder.rgb565_to_rgb888(0x001F), (0, 0, 255))


if __name__ == "__main__":
    unittest.main()
