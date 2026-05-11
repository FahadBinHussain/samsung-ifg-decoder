#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path


VERSION = "0.4.0"
IFEG_TYPE_65000001 = 0x65000001
IFEG_TYPE_95000100 = 0x95000100
IFEG_TYPE_150001_BASE = 0x15000100
IFEG_TYPE_150001_MASK = 0xFFFFFF00
SUPPORTED_IFEG_TYPE_LABELS = ("0x65000001", "0x95000100", "0x150001xx")
DEFAULT_TABLES_JSON = Path(__file__).resolve().parent / "codec_tables.json"
SUPPORTED_OUTPUT_FORMATS = ("bmp", "png")


@dataclass(frozen=True)
class IfegHeader:
    width: int
    height: int
    ifeg_type: int
    raw_word_offset: int


@dataclass(frozen=True)
class CodecTables:
    delta16_simple: list[int]
    delta16_decode_a: list[int]
    delta16_decode_b: list[int]


class BitReader:
    """MSB-first bit reader used by Samsung IFEG streams."""

    def __init__(self, data: bytes, bit_position: int = 0x81) -> None:
        # The original decoder counts bit positions from 1.
        self.data = data
        self.bit_position = bit_position

    def read(self, bit_count: int) -> int:
        if bit_count <= 0:
            return 0

        result = 0
        for _ in range(bit_count):
            zero_based = self.bit_position - 1
            byte_index = zero_based // 8
            bit_in_byte = zero_based % 8
            if byte_index >= len(self.data):
                raise EOFError(f"bit read past end at byte {byte_index}")
            result = (result << 1) | ((self.data[byte_index] >> (7 - bit_in_byte)) & 1)
            self.bit_position += 1
        return result


def read_u16le(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def read_u32le(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def parse_ifeg_header(data: bytes) -> IfegHeader:
    if len(data) < 16:
        raise ValueError("file is too small for an IFEG header")
    if data[:4] != b"IFEG":
        raise ValueError("not an IFEG file")
    return IfegHeader(
        width=read_u16le(data, 4),
        height=read_u16le(data, 6),
        ifeg_type=read_u32le(data, 8),
        raw_word_offset=read_u32le(data, 12),
    )


def is_ifeg_150001xx(ifeg_type: int) -> bool:
    return (ifeg_type & IFEG_TYPE_150001_MASK) == IFEG_TYPE_150001_BASE


def is_three_stream_ifeg_type(ifeg_type: int) -> bool:
    return ifeg_type == IFEG_TYPE_95000100 or is_ifeg_150001xx(ifeg_type)


def load_table(payload: dict[str, object], path: Path, table_name: str) -> list[int]:
    try:
        values = payload["tables"][table_name]["values_signed"]
    except KeyError as exc:
        raise ValueError(f"{path} is missing tables.{table_name}.values_signed") from exc
    if len(values) < 512:
        raise ValueError(f"{path} {table_name} table is truncated")
    return [int(x) for x in values]


def load_codec_tables(path: Path = DEFAULT_TABLES_JSON) -> CodecTables:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return CodecTables(
        delta16_simple=load_table(payload, path, "delta16_simple"),
        delta16_decode_a=load_table(payload, path, "delta16_decode_a"),
        delta16_decode_b=load_table(payload, path, "delta16_decode_b"),
    )


def decode_ifeg_65000001(data: bytes, delta_table: list[int]) -> tuple[int, int, list[int]]:
    header = parse_ifeg_header(data)
    if header.ifeg_type != IFEG_TYPE_65000001:
        raise ValueError(
            f"unsupported IFEG type 0x{header.ifeg_type:08x}; "
            f"expected 0x{IFEG_TYPE_65000001:08x}"
        )
    if header.width <= 0 or header.height <= 0:
        raise ValueError(f"invalid dimensions {header.width}x{header.height}")

    bit_reader = BitReader(data, bit_position=0x81)
    pixels = [0] * (header.width * header.height)
    raw_cursor = header.raw_word_offset

    blocks_w = (header.width + 3) // 4
    blocks_h = (header.height + 3) // 4
    width_rem = header.width % 4
    height_rem = header.height % 4

    def get_pixel(index: int) -> int:
        if 0 <= index < len(pixels):
            return pixels[index]
        return 0

    def set_pixel(index: int, value: int) -> None:
        if 0 <= index < len(pixels):
            pixels[index] = value & 0xFFFF

    def read_raw_word() -> int:
        nonlocal raw_cursor
        if raw_cursor + 2 > len(data):
            raise EOFError(f"raw word read past end at byte {raw_cursor}")
        value = read_u16le(data, raw_cursor)
        raw_cursor += 2
        return value

    def decode_tile(tile_w: int, tile_h: int, base_index: int) -> None:
        mode = bit_reader.read(2)
        if mode == 0:
            reference_distance = 1
        elif mode == 1:
            reference_distance = header.width
        elif mode == 2:
            reference_distance = header.width + 1
        else:
            for yy in range(tile_h):
                for xx in range(tile_w):
                    src_index = base_index - 1 + xx + yy * header.width
                    dst_index = base_index + xx + yy * header.width
                    set_pixel(dst_index, get_pixel(src_index))
            return

        for yy in range(tile_h):
            for xx in range(tile_w):
                dst_index = base_index + xx + yy * header.width
                src_index = base_index - reference_distance + xx + yy * header.width

                copy_flag = bit_reader.read(1)
                if copy_flag:
                    set_pixel(dst_index, get_pixel(src_index))
                    continue

                code = bit_reader.read(3)
                if code == 7:
                    set_pixel(dst_index, read_raw_word())
                    continue

                extra = bit_reader.read(code + 2)
                table_index = (4 << code) + extra
                if table_index >= len(delta_table):
                    raise ValueError(f"delta table index out of range: {table_index}")
                set_pixel(dst_index, get_pixel(src_index) + delta_table[table_index])

    for block_y in range(blocks_h):
        tile_h = height_rem if block_y == blocks_h - 1 and height_rem else 4
        for block_x in range(blocks_w):
            tile_w = width_rem if block_x == blocks_w - 1 and width_rem else 4
            base_index = block_y * header.width * 4 + block_x * 4
            decode_tile(tile_w, tile_h, base_index)

    return header.width, header.height, pixels


def decode_ifeg_three_stream_16bit(data: bytes, tables: CodecTables) -> tuple[int, int, list[int]]:
    header = parse_ifeg_header(data)
    if not is_three_stream_ifeg_type(header.ifeg_type):
        raise ValueError(
            f"unsupported IFEG type 0x{header.ifeg_type:08x}; "
            f"expected 0x{IFEG_TYPE_95000100:08x} or 0x150001xx"
        )
    if header.width <= 0 or header.height <= 0:
        raise ValueError(f"invalid dimensions {header.width}x{header.height}")
    if len(data) < 29:
        raise ValueError("file is too small for a three-stream IFEG header")
    if data[12:16] != b"\x01\x00\x01\x00" or data[16] not in (0, 1):
        raise ValueError("unsupported three-stream IFEG header")

    split_b = read_u32le(data, 21)
    split_c = read_u32le(data, 25)
    stream_start = 29
    if not (stream_start <= split_b <= split_c <= len(data)):
        raise ValueError(f"invalid three-stream IFEG split points: {split_b}, {split_c}")

    control_bits = BitReader(data[stream_start : split_b + 4], bit_position=1)
    command_bits = BitReader(data[split_b : split_c + 4], bit_position=1)
    raw_words = data[split_c:]
    raw_cursor = 0
    pixels = [0] * (header.width * header.height)

    blocks_w = (header.width + 3) // 4
    blocks_h = (header.height + 3) // 4
    width_rem = header.width % 4
    height_rem = header.height % 4

    def get_pixel(index: int) -> int:
        if 0 <= index < len(pixels):
            return pixels[index]
        return 0

    def set_pixel(index: int, value: int) -> None:
        if 0 <= index < len(pixels):
            pixels[index] = value & 0xFFFF

    def read_raw_word() -> int:
        nonlocal raw_cursor
        if raw_cursor + 2 > len(raw_words):
            raise EOFError(f"raw word read past end at byte {raw_cursor}")
        value = read_u16le(raw_words, raw_cursor)
        raw_cursor += 2
        return value

    def decode_mixed_tile(tile_w: int, tile_h: int, base_index: int, reference_distance: int, table_flag: int) -> None:
        mask = read_raw_word()
        mask_bit = 0
        delta_table = tables.delta16_decode_a if table_flag else tables.delta16_decode_b

        for yy in range(tile_h):
            for xx in range(tile_w):
                dst_index = base_index + xx + yy * header.width
                src_index = base_index - reference_distance + xx + yy * header.width

                if mask & (1 << mask_bit):
                    set_pixel(dst_index, get_pixel(src_index))
                    mask_bit += 1
                    continue

                code = command_bits.read(3)
                if code == 7:
                    set_pixel(dst_index, read_raw_word())
                else:
                    extra = control_bits.read(code + 1)
                    table_index = (2 << code) + extra
                    if table_index >= len(delta_table):
                        raise ValueError(f"delta table index out of range: {table_index}")
                    set_pixel(dst_index, get_pixel(src_index) + delta_table[table_index])
                mask_bit += 1

    def decode_raw_tile(tile_w: int, tile_h: int, base_index: int) -> None:
        for yy in range(tile_h):
            for xx in range(tile_w):
                set_pixel(base_index + xx + yy * header.width, read_raw_word())

    def decode_tile(tile_w: int, tile_h: int, base_index: int) -> None:
        mode = control_bits.read(3)
        if mode == 0:
            decode_mixed_tile(tile_w, tile_h, base_index, 1, control_bits.read(1))
        elif mode == 1:
            decode_mixed_tile(tile_w, tile_h, base_index, header.width, control_bits.read(1))
        elif mode == 2:
            decode_mixed_tile(tile_w, tile_h, base_index, header.width + 1, control_bits.read(1))
        elif mode == 3:
            for yy in range(tile_h):
                for xx in range(tile_w):
                    src_index = base_index - 1 + xx + yy * header.width
                    dst_index = base_index + xx + yy * header.width
                    set_pixel(dst_index, get_pixel(src_index))
        elif mode == 4:
            decode_raw_tile(tile_w, tile_h, base_index)
        else:
            raise ValueError(f"unsupported three-stream IFEG tile mode: {mode}")

    for block_y in range(blocks_h):
        tile_h = height_rem if block_y == blocks_h - 1 and height_rem else 4
        for block_x in range(blocks_w):
            tile_w = width_rem if block_x == blocks_w - 1 and width_rem else 4
            base_index = block_y * header.width * 4 + block_x * 4
            decode_tile(tile_w, tile_h, base_index)

    return header.width, header.height, pixels


def decode_ifeg(data: bytes, tables: CodecTables) -> tuple[int, int, list[int]]:
    header = parse_ifeg_header(data)
    if header.ifeg_type == IFEG_TYPE_65000001:
        return decode_ifeg_65000001(data, tables.delta16_simple)
    if is_three_stream_ifeg_type(header.ifeg_type):
        return decode_ifeg_three_stream_16bit(data, tables)
    supported = ", ".join(SUPPORTED_IFEG_TYPE_LABELS)
    raise ValueError(f"unsupported IFEG type 0x{header.ifeg_type:08x}; this release supports {supported}")


def rgb565_to_rgb888(value: int, bgr565: bool = False) -> tuple[int, int, int]:
    value &= 0xFFFF
    if bgr565:
        b5 = (value >> 11) & 0x1F
        g6 = (value >> 5) & 0x3F
        r5 = value & 0x1F
    else:
        r5 = (value >> 11) & 0x1F
        g6 = (value >> 5) & 0x3F
        b5 = value & 0x1F
    r = (r5 << 3) | (r5 >> 2)
    g = (g6 << 2) | (g6 >> 4)
    b = (b5 << 3) | (b5 >> 2)
    return r, g, b


def write_bmp_rgb888(path: Path, width: int, height: int, pixels: list[int], bgr565: bool = False) -> None:
    row_stride = (width * 3 + 3) & ~3
    pixel_bytes = bytearray(row_stride * height)

    for y in range(height):
        dst_y = height - 1 - y
        row_off = dst_y * row_stride
        for x in range(width):
            r, g, b = rgb565_to_rgb888(pixels[y * width + x], bgr565=bgr565)
            out = row_off + x * 3
            pixel_bytes[out : out + 3] = bytes((b, g, r))

    file_size = 14 + 40 + len(pixel_bytes)
    header = bytearray()
    header += b"BM"
    header += struct.pack("<IHHI", file_size, 0, 0, 54)
    header += struct.pack("<IIIHHIIIIII", 40, width, height, 1, 24, 0, len(pixel_bytes), 2835, 2835, 0, 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + pixel_bytes)


def png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", zlib.crc32(chunk_type + payload) & 0xFFFFFFFF)


def write_png_rgb888(path: Path, width: int, height: int, pixels: list[int], bgr565: bool = False) -> None:
    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)
        for x in range(width):
            scanlines.extend(rgb565_to_rgb888(pixels[y * width + x], bgr565=bgr565))

    payload = bytearray()
    payload += b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += png_chunk(b"IDAT", zlib.compress(bytes(scanlines)))
    payload += png_chunk(b"IEND", b"")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_image_rgb888(path: Path, width: int, height: int, pixels: list[int], bgr565: bool = False) -> None:
    suffix = path.suffix.lower()
    if suffix == ".bmp":
        write_bmp_rgb888(path, width, height, pixels, bgr565=bgr565)
    elif suffix == ".png":
        write_png_rgb888(path, width, height, pixels, bgr565=bgr565)
    else:
        raise ValueError(f"unsupported output extension {path.suffix!r}; use .bmp or .png")


def split_240x320_panels(output_path: Path, width: int, height: int, pixels: list[int], bgr565: bool) -> list[Path]:
    if width != 240 or height % 320 != 0:
        return []

    panel_paths: list[Path] = []
    for panel_index in range(height // 320):
        panel_pixels: list[int] = []
        for y in range(320):
            row_start = (panel_index * 320 + y) * width
            panel_pixels.extend(pixels[row_start : row_start + width])
        panel_path = output_path.with_name(f"{output_path.stem}_panel{panel_index + 1}_240x320{output_path.suffix}")
        write_image_rgb888(panel_path, 240, 320, panel_pixels, bgr565=bgr565)
        panel_paths.append(panel_path)
    return panel_paths


def default_output_for_file(input_path: Path, input_root: Path | None, output_root: Path, output_format: str) -> Path:
    suffix = f".{output_format}"
    if input_root is None:
        return output_root / f"{input_path.stem}{suffix}"
    rel = input_path.relative_to(input_root)
    return (output_root / rel).with_suffix(suffix)


def iter_input_files(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(input_path)
    pattern = "**/*.ifg" if recursive else "*.ifg"
    return sorted(input_path.glob(pattern))


def decode_one_file(
    input_path: Path,
    output_path: Path,
    tables: CodecTables,
    bgr565: bool,
    split_panels: bool,
) -> dict[str, str]:
    data = input_path.read_bytes()
    header = parse_ifeg_header(data)
    width, height, pixels = decode_ifeg(data, tables)
    write_image_rgb888(output_path, width, height, pixels, bgr565=bgr565)

    extra_outputs: list[str] = []
    if split_panels:
        extra_outputs = [str(p) for p in split_240x320_panels(output_path, width, height, pixels, bgr565=bgr565)]

    return {
        "source": str(input_path),
        "output": str(output_path),
        "extra_outputs": ";".join(extra_outputs),
        "width": str(width),
        "height": str(height),
        "type": f"0x{header.ifeg_type:08X}",
        "status": "decoded",
        "error": "",
    }


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["source", "output", "extra_outputs", "width", "height", "type", "status", "error"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Decode Samsung IFG/IFEG images from legacy phone firmware. "
        "This release supports IFEG types 0x65000001, 0x95000100, and 0x150001xx."
    )
    parser.add_argument("input", type=Path, help="input .ifg file or folder")
    parser.add_argument("output", type=Path, help="output .bmp/.png file, or output folder for batch mode")
    parser.add_argument("--recursive", action="store_true", help="recurse into input folders")
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES_JSON, help="codec table JSON path")
    parser.add_argument("--format", choices=SUPPORTED_OUTPUT_FORMATS, default="bmp", help="batch output format")
    parser.add_argument("--bgr565", action="store_true", help="interpret decoded 16-bit pixels as BGR565")
    parser.add_argument("--split-240x320-panels", action="store_true", help="also split 240x960 wallpapers into 240x320 panels")
    parser.add_argument("--manifest", type=Path, help="write a CSV decode manifest")
    parser.add_argument("--version", action="version", version=f"samsung-ifg-decoder {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    tables = load_codec_tables(args.tables)

    input_path = args.input
    output_path = args.output
    input_files = iter_input_files(input_path, recursive=args.recursive)

    if input_path.is_file() and output_path.suffix:
        planned_outputs = {input_path: output_path}
        input_root = None
    else:
        input_root = input_path if input_path.is_dir() else None
        planned_outputs = {
            path: default_output_for_file(path, input_root, output_path, args.format)
            for path in input_files
        }

    rows: list[dict[str, str]] = []
    for source, target in planned_outputs.items():
        try:
            row = decode_one_file(source, target, tables, args.bgr565, args.split_240x320_panels)
            print(f"decoded {source} -> {target} ({row['width']}x{row['height']})")
        except Exception as exc:
            row = {
                "source": str(source),
                "output": str(target),
                "extra_outputs": "",
                "width": "",
                "height": "",
                "type": "",
                "status": "failed",
                "error": str(exc),
            }
            print(f"failed {source}: {exc}", file=sys.stderr)
        rows.append(row)

    if args.manifest:
        write_manifest(args.manifest, rows)

    return 1 if any(row["status"] == "failed" for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
