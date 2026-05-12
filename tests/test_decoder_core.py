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


class ColorTests(unittest.TestCase):
    def test_rgb565_to_rgb888(self) -> None:
        self.assertEqual(decoder.rgb565_to_rgb888(0xF800), (255, 0, 0))
        self.assertEqual(decoder.rgb565_to_rgb888(0x07E0), (0, 255, 0))
        self.assertEqual(decoder.rgb565_to_rgb888(0x001F), (0, 0, 255))


if __name__ == "__main__":
    unittest.main()
