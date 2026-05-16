import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import samsung_ifg_decoder as decoder


FIXTURE_ROOT = ROOT / "samples" / "synthetic"


def load_hex_fixture(name: str) -> bytes:
    payload = []
    for line in (FIXTURE_ROOT / name).read_text(encoding="utf-8").splitlines():
        payload.append(line.split("#", 1)[0])
    return bytes.fromhex("".join(payload))


class SyntheticFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tables = decoder.load_codec_tables(decoder.DEFAULT_TABLES_JSON)

    def test_im_v5d_extended_near_lossless_fixture_decodes(self) -> None:
        data = load_hex_fixture("im_v5d_extended_near_lossless.hex")

        row = decoder.inspect_samsung_image(data)
        width, height, pixels, type_label = decoder.decode_samsung_image(data, self.tables)

        self.assertEqual(row["family"], "IM")
        self.assertEqual(row["supported"], "yes")
        self.assertIn("near_lossless=yes", row["flags"])
        self.assertIn("extended_header=yes", row["flags"])
        self.assertEqual((width, height, type_label), (4, 4, "IM_0x5D"))
        self.assertEqual(pixels, [0] * 16)

    def test_qm_a9ll_no_alpha_fixture_decodes(self) -> None:
        data = load_hex_fixture("qm_a9ll_rgb565_no_alpha.hex")

        width, height, pixels, type_label = decoder.decode_samsung_image(data, self.tables)

        self.assertEqual((width, height, type_label), (4, 1, "QM_0x0B_A9LL"))
        self.assertEqual(pixels, [0x1234] * 4)
        self.assertIsNone(decoder.decode_samsung_alpha(data, self.tables))

    def test_qm_w2_odd_tail_fixture_decodes(self) -> None:
        data = load_hex_fixture("qm_w2_odd_tail.hex")

        width, height, pixels, type_label = decoder.decode_samsung_image(data, self.tables)

        self.assertEqual((width, height, type_label), (3, 1, "QM_0x0B_W2D1"))
        self.assertEqual(pixels, [0x1234, 0xABCD, 0xABCD])


if __name__ == "__main__":
    unittest.main()
