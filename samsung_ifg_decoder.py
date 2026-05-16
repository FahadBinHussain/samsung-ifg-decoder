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


VERSION = "0.21.0"
IFEG_TYPE_65000001 = 0x65000001
IFEG_TYPE_95000100 = 0x95000100
IFEG_TYPE_150001_BASE = 0x15000100
IFEG_TYPE_150001_MASK = 0xFFFFFF00
IM_FLAG_NEAR_LOSSLESS = 0x20
IM_FLAG_ALPHA_PLANE = 0x80
IM_FLAG_EXTENDED_HEADER = 0x40
QM_VERSION_0B = 0x0B
QM_ENCODER_A9LL = 0
QM_ENCODER_W2_PASS = 1
QM_FLAG_USE_EXTRA_EXCEPTION = 0x80
QM_RAW_TYPE_RGB565_NO_ALPHA = 0x00
QM_RAW_TYPE_RGBA5658 = 0x03
SUPPORTED_QM_RAW_TYPES = (QM_RAW_TYPE_RGB565_NO_ALPHA, QM_RAW_TYPE_RGBA5658)
SUPPORTED_IFEG_TYPE_LABELS = ("0x65000001", "0x95000100", "0x150001xx")
SUPPORTED_INPUT_LABELS = (
    "IFEG 0x65000001",
    "IFEG 0x95000100",
    "IFEG 0x150001xx",
    "IM 0x5D",
    "QM 0x0B",
)
DEFAULT_TABLES_JSON = Path(__file__).resolve().parent / "codec_tables.json"
SUPPORTED_OUTPUT_FORMATS = ("bmp", "png")
SUPPORTED_INPUT_SUFFIXES = (".ifg", ".qmg")
DECODE_MANIFEST_FIELDS = ["source", "output", "extra_outputs", "width", "height", "type", "status", "alpha", "error"]
INSPECT_MANIFEST_FIELDS = [
    "source",
    "family",
    "width",
    "height",
    "type",
    "version",
    "flags",
    "header_size",
    "codec",
    "depth",
    "alpha_depth",
    "alpha_position",
    "command_offset",
    "raw_offset",
    "stream_start",
    "supported",
    "notes",
    "error",
]
ANALYZE_MANIFEST_FIELDS = INSPECT_MANIFEST_FIELDS + [
    "decode_status",
    "decode_error",
    "analysis_status",
    "analysis_error",
    "stream_summary",
    "tile_count",
    "mixed_tiles",
    "copy_tiles",
    "edge_copy_tiles",
    "mask_words",
    "copied_pixels",
    "delta_pixels",
    "literal_pixels",
    "control_bits_read",
    "control_limit_bits",
    "control_overrun_bits",
    "command_bits_read",
    "command_limit_bits",
    "command_overrun_bits",
    "raw_bytes_read",
    "raw_final_offset",
    "raw_limit_offset",
    "raw_limit_bytes",
    "raw_overrun_bytes",
]
QMAGE_DIFF = (
    0x0001, 0x0003, 0x0100, 0x0002, 0x0008, 0x0007, 0x0006, 0x0300,
    0x0010, 0x0004, 0x0200, 0x0009, 0x0040, 0x0018, 0x0005, 0x0020,
    0x000C, 0x000E, 0x000F, 0x000A, 0x00C0, 0x0800, 0x0700, 0x0101,
    0x0400, 0x000B, 0x0030, 0x0011, 0x0080, 0x0600, 0x000D, 0x0012,
    0x001C, 0x0500, 0x001B, 0x001E, 0x0014, 0x001A, 0x0028, 0x0038,
    0x1000, 0x001F, 0x0019, 0x0016, 0x0060, 0x2000, 0x0013, 0x001D,
    0x0103, 0x0024, 0x0017, 0x0015, 0x0102, 0x01C0, 0x0F00, 0x003C,
    0x0301, 0x0C00, 0x1800, 0x0048, 0x0021, 0x0034, 0x0E00, 0x0202,
    0x002C, 0x0070, 0x0A00, 0x0303, 0x0036, 0x0201, 0x003F, 0x0D00,
    0x0180, 0x003E, 0x3000, 0x0900, 0x0078, 0x0022, 0x0050, 0x003A,
    0x0041, 0x0107, 0x0033, 0x0106, 0x0026, 0x002A, 0x00A0, 0x0023,
    0x0029, 0x0088, 0x0044, 0x003D, 0x00E0, 0x0032, 0x002E, 0x0039,
    0x0031, 0x002D, 0x00F0, 0x0140, 0x0B00, 0x003B, 0x0058, 0x4000,
    0x0037, 0x0035, 0x0068, 0x0302, 0x007C, 0x002F, 0x0027, 0x0064,
    0x0090, 0x0074, 0x0203, 0x0104, 0x006C, 0x1100, 0x03C0, 0x00FF,
    0x0025, 0xF000, 0x1F00, 0x0701, 0x0042, 0x007F, 0x002B, 0x0105,
    0x0054, 0x1C00, 0x004C, 0x0801, 0x0043, 0x6000, 0x005C, 0x007E,
    0x00E8, 0x0108, 0x00F8, 0xE000, 0x0206, 0x1E00, 0x0380, 0x0061,
    0x007A, 0x004E, 0x0601, 0x1001, 0x00C8, 0x8000, 0x1D00, 0x00D0,
    0x0072, 0x0049, 0x1600, 0x1A00, 0x0046, 0x7000, 0x010F, 0x0110,
    0x0076, 0x1200, 0x1400, 0x0404, 0x0606, 0x010E, 0x00FC, 0x1700,
    0x006E, 0x00FE, 0x1300, 0x0062, 0x0066, 0xC000, 0x0204, 0x0306,
    0x0063, 0x0707, 0x0280, 0x0602, 0x0055, 0x0047, 0x006A, 0x010C,
    0x0052, 0x0501, 0x00D8, 0x0307, 0x0073, 0x0109, 0x0808, 0x0401,
    0x004A, 0x2020, 0x005A, 0x0702, 0x00B0, 0x0045, 0x0207, 0x0304,
    0x0402, 0x005E, 0x010A, 0x0079, 0x3800, 0x00F4, 0x1500, 0x01E0,
    0x1B00, 0x0071, 0x1010, 0x00C1, 0x00E4, 0x0502, 0x0056, 0x007D,
    0x0081, 0x0077, 0x00CC, 0x0703, 0x010D, 0x0205, 0x0340, 0x5000,
    0x0082, 0x0067, 0xFF00, 0x0120, 0x0069, 0x0098, 0x00C3, 0x1900,
    0x0065, 0x007B, 0x0240, 0x0603, 0x00EC, 0x0059, 0x00FA, 0x0403,
    0x0075, 0x006F, 0x3100, 0x3300, 0x004F, 0x00B8, 0x006D, 0x0208,
    0x004D, 0x0111, 0x0051, 0x020E, 0x00DC, 0x00C4, 0x2100, 0x00A8,
)


@dataclass(frozen=True)
class IfegHeader:
    width: int
    height: int
    ifeg_type: int
    raw_word_offset: int


@dataclass(frozen=True)
class ImHeader:
    width: int
    height: int
    flags: int
    version: int
    stream_header_offset: int
    command_offset: int
    raw_offset: int
    near_lossless: bool


@dataclass(frozen=True)
class QmHeader:
    width: int
    height: int
    version: int
    raw_type: int
    flags4: int
    flags5: int
    encoder_mode: int
    alpha_depth: int
    depth: int
    alpha_position: int
    header_size: int
    is_animation: bool = False
    total_frame_number: int = 1
    current_frame_number: int = 1
    animation_delay_time: int = 0
    animation_no_repeat: int = 0


@dataclass(frozen=True)
class QmAnimationFrame:
    index: int
    offset: int
    data: bytes
    header: QmHeader


@dataclass(frozen=True)
class DecodedQmAnimationFrame:
    index: int
    offset: int
    width: int
    height: int
    pixels: list[int]
    header: QmHeader


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


class ByteReader:
    def __init__(self, data: bytes, offset: int = 0) -> None:
        self.data = data
        self.offset = offset

    def peek_u8(self) -> int:
        if self.offset >= len(self.data):
            return 0
        return self.data[self.offset]

    def read_u8(self) -> int:
        if self.offset >= len(self.data):
            raise EOFError(f"byte read past end at byte {self.offset}")
        value = self.data[self.offset]
        self.offset += 1
        return value

    def read_u16le(self) -> int:
        if self.offset + 2 > len(self.data):
            raise EOFError(f"u16 read past end at byte {self.offset}")
        value = read_u16le(self.data, self.offset)
        self.offset += 2
        return value

    def read_u32le(self) -> int:
        if self.offset + 4 > len(self.data):
            raise EOFError(f"u32 read past end at byte {self.offset}")
        value = read_u32le(self.data, self.offset)
        self.offset += 4
        return value

    def read_bytes(self, size: int) -> bytes:
        if size < 0:
            raise ValueError(f"negative read size {size}")
        if self.offset + size > len(self.data):
            raise EOFError(f"byte block read past end at byte {self.offset}")
        value = self.data[self.offset : self.offset + size]
        self.offset += size
        return value


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


def parse_im_header(data: bytes) -> ImHeader:
    if len(data) < 17:
        raise ValueError("file is too small for an IM header")
    if data[:2] != b"IM":
        raise ValueError("not an IM file")

    width = read_u16le(data, 2)
    height = read_u16le(data, 4)
    flags = data[6]
    version = data[7]
    if version != 0x5D:
        raise ValueError(f"unsupported IM version 0x{version:02x}; this release supports IM 0x5D")
    if flags & IM_FLAG_ALPHA_PLANE:
        raise ValueError("IM alpha-plane files are not supported yet")
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid dimensions {width}x{height}")

    stream_header_offset = 13 if data[8] & IM_FLAG_EXTENDED_HEADER else 9
    if len(data) < stream_header_offset + 8:
        raise ValueError("file is too small for an IM stream header")

    command_offset = read_u32le(data, stream_header_offset)
    raw_offset = read_u32le(data, stream_header_offset + 4)
    stream_start = stream_header_offset + 8
    if not (stream_start <= command_offset <= raw_offset <= len(data)):
        raise ValueError(
            "invalid IM stream split points: "
            f"{stream_start}, {command_offset}, {raw_offset}, {len(data)}"
        )

    return ImHeader(
        width=width,
        height=height,
        flags=flags,
        version=version,
        stream_header_offset=stream_header_offset,
        command_offset=command_offset,
        raw_offset=raw_offset,
        near_lossless=bool(flags & IM_FLAG_NEAR_LOSSLESS),
    )


def parse_qm_header(data: bytes, strict: bool = True) -> QmHeader:
    if len(data) < 12:
        raise ValueError("file is too small for a QM header")
    if data[:2] != b"QM":
        raise ValueError("not a QM file")

    version = data[2]
    raw_type = data[3]
    flags4 = data[4]
    flags5 = data[5]
    width = read_u16le(data, 6)
    height = read_u16le(data, 8)

    if strict and version != QM_VERSION_0B:
        raise ValueError(f"unsupported QM version 0x{version:02x}; this release supports QM 0x0B")
    if strict and raw_type not in SUPPORTED_QM_RAW_TYPES:
        raise ValueError(
            f"unsupported QM raw type 0x{raw_type:02x}; "
            "this release supports RGB565 no-alpha and RGBA5658 color data"
        )
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid dimensions {width}x{height}")

    transparency = raw_type in (QM_RAW_TYPE_RGBA5658, 0x06)
    is_animation = bool(flags4 & 0x80)
    if is_animation:
        if len(data) < 24:
            raise ValueError("file is too small for a QM animation header")
        total_frame_number = read_u16le(data, 16)
        current_frame_number = read_u16le(data, 18)
        animation_delay_time = read_u16le(data, 20)
        animation_no_repeat = data[22]
        header_size = 24
    else:
        total_frame_number = 1
        current_frame_number = 1
        animation_delay_time = 0
        animation_no_repeat = 0
        header_size = 16 if transparency else 12

    alpha_position = read_u32le(data, 12) if transparency or is_animation else 0

    return QmHeader(
        width=width,
        height=height,
        version=version,
        raw_type=raw_type,
        flags4=flags4,
        flags5=flags5,
        encoder_mode=flags5 & 0x07,
        alpha_depth=2 if flags5 & 0x20 else 1,
        depth=2 if flags5 & 0x40 else 1,
        alpha_position=alpha_position,
        header_size=header_size,
        is_animation=is_animation,
        total_frame_number=total_frame_number,
        current_frame_number=current_frame_number,
        animation_delay_time=animation_delay_time,
        animation_no_repeat=animation_no_repeat,
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


def decode_im_v5d_16bit(data: bytes, tables: CodecTables) -> tuple[int, int, list[int]]:
    header = parse_im_header(data)
    control_bits = BitReader(data, bit_position=header.stream_header_offset * 8 + 65)
    command_bits = BitReader(data, bit_position=header.command_offset * 8 + 1)
    raw_cursor = header.raw_offset
    pixels = [0] * (header.width * header.height)
    delta_table = tables.delta16_decode_b

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

    def decode_delta(reference_value: int) -> int:
        code = command_bits.read(3)
        if not header.near_lossless and code == 7:
            return read_raw_word()

        extra = control_bits.read(code + 1)
        table_index = (2 << code) + extra
        if table_index >= len(delta_table):
            raise ValueError(f"delta table index out of range: {table_index}")
        return reference_value + delta_table[table_index]

    def decode_mixed_tile(tile_w: int, tile_h: int, base_index: int, reference_distance: int) -> None:
        mask = read_raw_word()
        mask_bit = 0
        for yy in range(tile_h):
            for xx in range(tile_w):
                dst_index = base_index + xx + yy * header.width
                src_index = dst_index - reference_distance

                if mask & (1 << mask_bit):
                    set_pixel(dst_index, get_pixel(src_index))
                elif header.near_lossless and control_bits.read(1):
                    set_pixel(dst_index, read_raw_word())
                else:
                    set_pixel(dst_index, decode_delta(get_pixel(src_index)))
                mask_bit += 1

    def decode_copy_tile(tile_w: int, tile_h: int, base_index: int) -> None:
        for yy in range(tile_h):
            for xx in range(tile_w):
                dst_index = base_index + xx + yy * header.width
                set_pixel(dst_index, get_pixel(dst_index - 1))

    for block_y in range(blocks_h):
        tile_h = height_rem if block_y == blocks_h - 1 and height_rem else 4
        for block_x in range(blocks_w):
            tile_w = width_rem if block_x == blocks_w - 1 and width_rem else 4
            base_index = block_y * header.width * 4 + block_x * 4
            mode = control_bits.read(2)
            if mode == 0:
                decode_mixed_tile(tile_w, tile_h, base_index, 1)
            elif mode == 1:
                decode_mixed_tile(tile_w, tile_h, base_index, header.width)
            elif mode == 2:
                decode_mixed_tile(tile_w, tile_h, base_index, header.width + 1)
            else:
                decode_copy_tile(tile_w, tile_h, base_index)

    return header.width, header.height, pixels


def qm_ref_pixel(pixels: list[int], width: int, height: int, x: int, y: int) -> int:
    if 0 <= x < width and 0 <= y < height:
        return pixels[y * width + x]
    return 0


def qm_has_extra_exception(header: QmHeader) -> bool:
    return bool(header.flags5 & QM_FLAG_USE_EXTRA_EXCEPTION)


def decode_qm_a9ll_extra_exception(
    data: bytes,
    header: QmHeader,
    tables: CodecTables,
    command_offset: int,
    raw_offset: int,
    stream_start: int,
) -> tuple[int, int, list[int]]:
    raw_limit = qm_a9ll_color_raw_limit(data, header, raw_offset)
    if not (stream_start <= command_offset <= raw_offset <= raw_limit <= len(data)):
        raise ValueError(
            "invalid QM A9LL extra-exception split points: "
            f"{stream_start}, {command_offset}, {raw_offset}, {raw_limit}, size={len(data)}"
        )

    control_bits = BitReader(data[stream_start:command_offset], bit_position=1)
    command_bits = BitReader(data[command_offset:raw_offset], bit_position=1)
    raw_words = ByteReader(data[:raw_limit], raw_offset)
    delta_table = tables.delta16_decode_b
    pixels = [0] * (header.width * header.height)
    directions = [(-1, 0), (0, -1), (-1, -1)]

    def set_pixel(x: int, y: int, value: int) -> None:
        if 0 <= x < header.width and 0 <= y < header.height:
            pixels[y * header.width + x] = value & 0xFFFF

    def copy_edge_tile(x: int, y: int, tile_w: int, tile_h: int) -> None:
        for yy in range(tile_h):
            for xx in range(tile_w):
                set_pixel(x + xx, y + yy, qm_ref_pixel(pixels, header.width, header.height, x + xx - 1, y + yy))

    for y in range(0, header.height, 4):
        for x in range(0, header.width, 4):
            tile_w = min(4, header.width - x)
            tile_h = min(4, header.height - y)
            mode = control_bits.read(2)

            if mode < 3:
                mask = raw_words.read_u16le()
                mask_bit = 0
                ref_x_delta, ref_y_delta = directions[mode]
                for yy in range(4):
                    for xx in range(4):
                        if x + xx >= header.width or y + yy >= header.height:
                            continue

                        ref_value = qm_ref_pixel(
                            pixels,
                            header.width,
                            header.height,
                            x + xx + ref_x_delta,
                            y + yy + ref_y_delta,
                        )
                        if mask & (1 << mask_bit):
                            set_pixel(x + xx, y + yy, ref_value)
                        elif control_bits.read(1):
                            set_pixel(x + xx, y + yy, raw_words.read_u16le())
                        else:
                            command = command_bits.read(3)
                            extra = control_bits.read(command + 1)
                            table_index = (2 << command) + extra
                            if table_index >= len(delta_table):
                                raise ValueError(f"QM A9LL delta table index out of range: {table_index}")
                            set_pixel(x + xx, y + yy, ref_value + delta_table[table_index])
                        mask_bit += 1
            elif x > 0:
                copy_edge_tile(x, y, tile_w, tile_h)

    return header.width, header.height, pixels


def decode_qm_a9ll(data: bytes, header: QmHeader, tables: CodecTables) -> tuple[int, int, list[int]]:
    if len(data) < header.header_size + 8:
        raise ValueError("QM A9LL file is too small for stream split points")

    command_offset = read_u32le(data, header.header_size)
    raw_offset = read_u32le(data, header.header_size + 4)
    stream_start = header.header_size + 8
    if not (stream_start <= command_offset <= raw_offset <= len(data)):
        raise ValueError(f"invalid QM A9LL stream split points: {command_offset}, {raw_offset}")

    if qm_has_extra_exception(header):
        return decode_qm_a9ll_extra_exception(data, header, tables, command_offset, raw_offset, stream_start)

    control_bits = BitReader(data[stream_start:], bit_position=1)
    command_bits = BitReader(data[command_offset:], bit_position=1)
    raw_words = ByteReader(data, raw_offset)
    delta_table = tables.delta16_decode_b[2:258]
    pixels = [0] * (header.width * header.height)
    directions = [(-1, 0), (0, -1), (-1, -1)]

    def set_pixel(x: int, y: int, value: int) -> None:
        if 0 <= x < header.width and 0 <= y < header.height:
            pixels[y * header.width + x] = value & 0xFFFF

    def copy_edge_tile(x: int, y: int, tile_w: int, tile_h: int) -> None:
        for yy in range(tile_h):
            for xx in range(tile_w):
                set_pixel(x + xx, y + yy, qm_ref_pixel(pixels, header.width, header.height, x + xx - 1, y + yy))

    for y in range(0, header.height, 4):
        for x in range(0, header.width, 4):
            tile_w = min(4, header.width - x)
            tile_h = min(4, header.height - y)
            mode = control_bits.read(2)

            if mode < 3:
                mask = raw_words.read_u16le()
                mask_bit = 0
                ref_x_delta, ref_y_delta = directions[mode]
                for yy in range(4):
                    for xx in range(4):
                        if x + xx >= header.width or y + yy >= header.height:
                            continue

                        ref_value = qm_ref_pixel(
                            pixels,
                            header.width,
                            header.height,
                            x + xx + ref_x_delta,
                            y + yy + ref_y_delta,
                        )
                        if mask & (1 << mask_bit):
                            set_pixel(x + xx, y + yy, ref_value)
                        else:
                            command = command_bits.read(3)
                            if command == 7:
                                set_pixel(x + xx, y + yy, raw_words.read_u16le())
                            else:
                                extra = control_bits.read(command + 1)
                                table_index = (2 << command) + extra - 2
                                if table_index >= len(delta_table):
                                    raise ValueError(f"QM A9LL delta table index out of range: {table_index}")
                                set_pixel(x + xx, y + yy, ref_value + delta_table[table_index])
                        mask_bit += 1
            elif x > 0:
                copy_edge_tile(x, y, tile_w, tile_h)

    return header.width, header.height, pixels


def copy_qm_block(
    dst: list[int],
    src: list[int],
    width: int,
    height: int,
    dst_x: int,
    dst_y: int,
    src_x: int,
    src_y: int,
    block_w: int,
    block_h: int,
) -> None:
    for yy in range(block_h):
        for xx in range(block_w):
            x = dst_x + xx
            y = dst_y + yy
            if 0 <= x < width and 0 <= y < height:
                dst[y * width + x] = qm_ref_pixel(src, width, height, src_x + xx, src_y + yy)


def decode_qm_a9ll_animation_delta(
    data: bytes,
    header: QmHeader,
    tables: CodecTables,
    ref_pixels: list[int],
) -> tuple[int, int, list[int]]:
    if header.encoder_mode != QM_ENCODER_A9LL:
        raise ValueError("QM animation delta frames require A9LL")
    if not header.is_animation or header.current_frame_number <= 1:
        raise ValueError("QM animation delta decoder requires frame 2 or later")
    if len(ref_pixels) != header.width * header.height:
        raise ValueError("QM animation reference frame dimensions do not match")
    if len(data) < header.header_size + 8:
        raise ValueError("QM A9LL animation frame is too small for stream split points")

    byte_stream_offset = read_u32le(data, header.header_size)
    bit_stream_start = header.header_size + 8
    if not (bit_stream_start <= byte_stream_offset <= len(data)):
        raise ValueError(f"invalid QM A9LL animation split point: {byte_stream_offset}")

    bits = BitReader(data[bit_stream_start:], bit_position=1)
    bytes_in = ByteReader(data, byte_stream_offset)
    delta_table = tables.delta16_decode_b[2:258]
    pixels = [0] * (header.width * header.height)
    directions = [(-1, 0), (0, -1), (-1, -1)]

    def set_pixel(x: int, y: int, value: int) -> None:
        if 0 <= x < header.width and 0 <= y < header.height:
            pixels[y * header.width + x] = value & 0xFFFF

    def decode_pixel_from(source: list[int], x: int, y: int, ref_x: int, ref_y: int) -> None:
        ref_value = qm_ref_pixel(source, header.width, header.height, ref_x, ref_y)
        if bits.read(1):
            set_pixel(x, y, ref_value)
            return

        bit_count = bits.read(3)
        if bit_count == 7:
            set_pixel(x, y, bytes_in.read_u16le())
            return

        extra = bits.read(bit_count + 1)
        table_index = (2 << bit_count) + extra - 2
        if table_index >= len(delta_table):
            raise ValueError(f"QM animation delta table index out of range: {table_index}")
        set_pixel(x, y, ref_value + delta_table[table_index])

    def copy_edge_tile(x: int, y: int, tile_w: int, tile_h: int) -> None:
        for yy in range(tile_h):
            for xx in range(tile_w):
                set_pixel(x + xx, y + yy, qm_ref_pixel(pixels, header.width, header.height, x + xx - 1, y + yy))

    def decode_block2(x: int, y: int) -> None:
        mode = bits.read(2)
        if mode < 3:
            ref_x_delta, ref_y_delta = directions[mode]
            for yy in range(4):
                for xx in range(4):
                    decode_pixel_from(pixels, x + xx, y + yy, x + xx + ref_x_delta, y + yy + ref_y_delta)
        elif x > 0:
            copy_edge_tile(x, y, 4, 4)

    def decode_block3(x: int, y: int, mv_x: int, mv_y: int) -> None:
        mode = bits.read(3)
        if mode < 3:
            ref_x_delta, ref_y_delta = directions[mode]
            for yy in range(4):
                for xx in range(4):
                    decode_pixel_from(pixels, x + xx, y + yy, x + xx + ref_x_delta, y + yy + ref_y_delta)
        elif mode == 3:
            if x > 0:
                copy_edge_tile(x, y, 4, 4)
        elif mode == 4:
            for yy in range(4):
                for xx in range(4):
                    decode_pixel_from(ref_pixels, x + xx, y + yy, x + xx, y + yy)
        elif mode == 5:
            copy_qm_block(pixels, ref_pixels, header.width, header.height, x, y, x, y, 4, 4)
        elif mode == 6:
            for yy in range(4):
                for xx in range(4):
                    decode_pixel_from(ref_pixels, x + xx, y + yy, x + xx + mv_x, y + yy + mv_y)
        else:
            if x + mv_x < 0 or x + mv_x + 4 > header.width or y + mv_y < 0 or y + mv_y + 4 > header.height:
                return
            copy_qm_block(pixels, ref_pixels, header.width, header.height, x, y, x + mv_x, y + mv_y, 4, 4)

    def decode_macroblock(x: int, y: int) -> None:
        if bits.read(1):
            if bits.read(1):
                copy_qm_block(pixels, ref_pixels, header.width, header.height, x, y, x, y, 16, 16)
                return

            if not bits.read(1):
                mv_x = bits.read(8) - 0x7F
                mv_y = bits.read(7) - 0x3F
                if x + mv_x < 0 or x + mv_x + 16 > header.width or y + mv_y < 0 or y + mv_y + 16 > header.height:
                    raise ValueError("QM animation motion vector points outside the reference frame")
                if bits.read(1):
                    copy_qm_block(pixels, ref_pixels, header.width, header.height, x, y, x + mv_x, y + mv_y, 16, 16)
                    return
            else:
                mv_x = 0
                mv_y = 0

            for block_y in range(y, y + 16, 4):
                for block_x in range(x, x + 16, 4):
                    decode_block3(block_x, block_y, mv_x, mv_y)
            return

        for block_y in range(y, y + 16, 4):
            for block_x in range(x, x + 16, 4):
                decode_block2(block_x, block_y)

    def decode_edge_macroblock(xpos: int, ypos: int) -> None:
        if bits.read(1):
            raise ValueError("QM animation skip-edge macroblocks are not supported")

        for y in range(ypos, min(ypos + 16, header.height), 4):
            for x in range(xpos, min(xpos + 16, header.width), 4):
                if x + 4 <= header.width and y + 4 <= header.height:
                    mode = bits.read(2)
                    if mode < 3:
                        ref_x_delta, ref_y_delta = directions[mode]
                        for yy in range(4):
                            for xx in range(4):
                                decode_pixel_from(pixels, x + xx, y + yy, x + xx + ref_x_delta, y + yy + ref_y_delta)
                    elif x > 0:
                        copy_edge_tile(x, y, min(4, header.width - x), min(4, header.height - y))
                else:
                    for yy in range(4):
                        for xx in range(4):
                            if x + xx < header.width and y + yy < header.height:
                                set_pixel(x + xx, y + yy, bytes_in.read_u16le())

    for y in range(0, header.height, 16):
        for x in range(0, header.width, 16):
            if header.width - x >= 16 and header.height - y >= 16:
                decode_macroblock(x, y)
            else:
                decode_edge_macroblock(x, y)

    return header.width, header.height, pixels


def find_qm_animation_frame_offsets(data: bytes, first_header: QmHeader) -> list[tuple[int, QmHeader]]:
    candidates: list[tuple[int, QmHeader]] = []
    search_offset = 0
    while True:
        offset = data.find(b"QM", search_offset)
        if offset < 0:
            break
        search_offset = offset + 1
        try:
            header = parse_qm_header(data[offset:], strict=False)
        except (struct.error, ValueError):
            continue
        if (
            header.version == first_header.version
            and header.raw_type == first_header.raw_type
            and header.width == first_header.width
            and header.height == first_header.height
            and header.flags4 == first_header.flags4
            and header.is_animation
            and header.total_frame_number == first_header.total_frame_number
            and 1 <= header.current_frame_number <= first_header.total_frame_number
        ):
            candidates.append((offset, header))

    expected = 1
    frames: list[tuple[int, QmHeader]] = []
    for offset, header in sorted(candidates):
        if header.current_frame_number == expected:
            frames.append((offset, header))
            expected += 1
            if expected > first_header.total_frame_number:
                break

    if len(frames) != first_header.total_frame_number or not frames or frames[0][0] != 0:
        raise ValueError(
            "could not locate all QM animation frame records "
            f"(found {len(frames)}, expected {first_header.total_frame_number})"
        )
    return frames


def split_qm_animation_frames(data: bytes) -> list[QmAnimationFrame]:
    first_header = parse_qm_header(data)
    if not first_header.is_animation:
        raise ValueError("not a QM animation")
    if first_header.encoder_mode != QM_ENCODER_A9LL:
        raise ValueError("QM animation frame export currently supports A9LL")

    offsets = find_qm_animation_frame_offsets(data, first_header)
    frames: list[QmAnimationFrame] = []
    for index, (offset, header) in enumerate(offsets, start=1):
        next_offset = offsets[index][0] if index < len(offsets) else len(data)
        frames.append(QmAnimationFrame(index=index, offset=offset, data=data[offset:next_offset], header=header))
    return frames


def decode_qm_animation_frames(data: bytes, tables: CodecTables) -> list[DecodedQmAnimationFrame]:
    frames = split_qm_animation_frames(data)
    decoded: list[DecodedQmAnimationFrame] = []
    ref_pixels: list[int] | None = None

    for frame in frames:
        if frame.header.current_frame_number == 1:
            width, height, pixels = decode_qm(frame.data, tables)
        else:
            if ref_pixels is None:
                raise ValueError("QM animation delta frame is missing a reference frame")
            width, height, pixels = decode_qm_a9ll_animation_delta(frame.data, frame.header, tables, ref_pixels)
        decoded.append(
            DecodedQmAnimationFrame(
                index=frame.index,
                offset=frame.offset,
                width=width,
                height=height,
                pixels=pixels,
                header=frame.header,
            )
        )
        ref_pixels = pixels

    return decoded


def unpack_qm_alpha_samples(header: QmHeader, samples: list[int]) -> list[int]:
    sample_width = (header.width + 1) // 2
    expected_samples = sample_width * header.height
    if len(samples) < expected_samples:
        raise ValueError(f"alpha stream decoded {len(samples)} packed samples, expected {expected_samples}")

    alpha = [255] * (header.width * header.height)
    for y in range(header.height):
        for sample_x in range(sample_width):
            value = samples[y * sample_width + sample_x]
            x = sample_x * 2
            if x < header.width:
                alpha[y * header.width + x] = value & 0xFF
            if x + 1 < header.width:
                alpha[y * header.width + x + 1] = (value >> 8) & 0xFF
    return alpha


def qm_alpha_sample_header(header: QmHeader) -> QmHeader:
    return QmHeader(
        width=(header.width + 1) // 2,
        height=header.height,
        version=header.version,
        raw_type=header.raw_type,
        flags4=header.flags4,
        flags5=header.flags5,
        encoder_mode=header.encoder_mode,
        alpha_depth=header.alpha_depth,
        depth=header.alpha_depth,
        alpha_position=header.alpha_position,
        header_size=header.header_size,
        is_animation=header.is_animation,
        total_frame_number=header.total_frame_number,
        current_frame_number=header.current_frame_number,
        animation_delay_time=header.animation_delay_time,
        animation_no_repeat=header.animation_no_repeat,
    )


def decode_qm_a9ll_alpha(data: bytes, header: QmHeader, tables: CodecTables) -> list[int]:
    if header.encoder_mode != QM_ENCODER_A9LL:
        raise ValueError("QM A9LL alpha output requires an A9LL stream")
    if header.alpha_depth not in (1, 2):
        raise ValueError(f"unsupported QM A9LL alpha depth {header.alpha_depth}")
    if not (header.header_size < header.alpha_position < len(data)):
        raise ValueError(f"invalid QM A9LL alpha position {header.alpha_position}")

    body = data[header.alpha_position :]
    if len(body) < 8:
        raise ValueError("QM A9LL alpha body is too small")

    command_offset = read_u32le(body, 0)
    raw_offset = read_u32le(body, 4)
    if not (8 <= command_offset <= raw_offset <= len(body)):
        raise ValueError(f"invalid QM A9LL alpha split points: {command_offset}, {raw_offset}")

    sample_header = qm_alpha_sample_header(header)
    sample_width = sample_header.width
    samples = [0] * (sample_width * sample_header.height)
    control_bits = BitReader(body[8:raw_offset], bit_position=1)
    command_bits = BitReader(body[command_offset:raw_offset], bit_position=1)
    raw_words = ByteReader(body, raw_offset)
    delta_table = tables.delta16_decode_b[2:258]
    directions = [(-1, 0), (0, -1), (-1, -1)]

    def get_sample(x: int, y: int) -> int:
        if 0 <= x < sample_width and 0 <= y < header.height:
            return samples[y * sample_width + x]
        return 0

    def set_sample(x: int, y: int, value: int) -> None:
        if 0 <= x < sample_width and 0 <= y < header.height:
            samples[y * sample_width + x] = value & 0xFFFF

    for y in range(0, header.height, 4):
        for sample_x in range(0, sample_width, 4):
            mode = control_bits.read(2)
            tile_w = min(4, sample_width - sample_x)
            tile_h = min(4, header.height - y)

            if mode < 3:
                mask = raw_words.read_u16le()
                mask_bit = 0
                ref_x_delta, ref_y_delta = directions[mode]
                for yy in range(4):
                    for xx in range(4):
                        if sample_x + xx >= sample_width or y + yy >= header.height:
                            continue

                        ref_value = get_sample(sample_x + xx + ref_x_delta, y + yy + ref_y_delta)
                        if mask & (1 << mask_bit):
                            set_sample(sample_x + xx, y + yy, ref_value)
                        else:
                            command = command_bits.read(3)
                            if command == 7:
                                set_sample(sample_x + xx, y + yy, raw_words.read_u16le())
                            else:
                                extra = control_bits.read(command + 1)
                                table_index = (2 << command) + extra - 2
                                if table_index >= len(delta_table):
                                    raise ValueError(f"QM alpha delta table index out of range: {table_index}")
                                set_sample(sample_x + xx, y + yy, ref_value + delta_table[table_index])
                        mask_bit += 1
            elif sample_x > 0:
                for yy in range(tile_h):
                    for xx in range(tile_w):
                        set_sample(sample_x + xx, y + yy, get_sample(sample_x + xx - 1, y + yy))

    return unpack_qm_alpha_samples(header, samples)


def write_u16le_buffer(data: bytearray, offset: int, value: int) -> None:
    struct.pack_into("<H", data, offset, value & 0xFFFF)


def read_qm_w2_value(reader: ByteReader) -> int:
    value = 0
    while reader.peek_u8() == 0xFF:
        reader.read_u8()
        value += 0xFF
    return value + reader.read_u8()


def decode_qm_w2_depth1(header: QmHeader, data: bytes) -> list[int]:
    if len(data) < 16:
        raise ValueError("QM W2 depth-1 body is too small")

    table_count = read_u32le(data, 0)
    index_size = read_u32le(data, 4)
    run_size = read_u32le(data, 8)
    index_start = 16 + table_count * 4
    run_start = index_start + index_size
    raw_start = run_start + run_size
    if not (16 <= index_start < len(data) and index_start <= run_start < len(data) and run_start <= raw_start <= len(data)):
        raise ValueError(
            "invalid QM W2 depth-1 stream split points: "
            f"{table_count}, {index_size}, {run_size}, size={len(data)}"
        )

    index_reader = ByteReader(data[index_start:])
    run_reader = ByteReader(data[run_start:])
    raw_reader = ByteReader(data[raw_start:])
    output_size = header.width * header.height * 2
    output = bytearray(output_size)
    cursor = 0

    while cursor + 4 <= output_size:
        index = read_qm_w2_value(index_reader)
        if index == 0:
            value = raw_reader.read_u32le()
            encoded = value.to_bytes(4, "little")
            output[cursor : cursor + 4] = encoded
            cursor += 4
            continue

        table_index = index - 1
        if table_index >= table_count:
            raise ValueError(f"QM W2 table index out of range: {table_index}")
        run = read_qm_w2_value(run_reader) + 1
        value = data[16 + table_index * 4 : 16 + table_index * 4 + 4]
        write_count = min(run, (output_size - cursor) // 4)
        for _ in range(write_count):
            output[cursor : cursor + 4] = value
            cursor += 4
        if write_count < run:
            break

    while cursor < output_size:
        if cursor >= 2:
            output[cursor : cursor + 2] = output[cursor - 2 : cursor]
        cursor += 2

    return [read_u16le(output, offset) for offset in range(0, output_size, 2)]


def qm_w2_strip1(
    bit_reader: BitReader,
    index_reader: ByteReader,
    raw_reader: ByteReader,
    rel: list[int],
    output: bytearray,
    cursor: int,
) -> None:
    output[cursor : cursor + 4] = raw_reader.read_bytes(4)
    cursor += 4

    for index in range(6):
        if not (index & 1) and not bit_reader.read(1):
            rel[0] = index_reader.read_u8() if bit_reader.read(1) else raw_reader.read_u16le()

        if not bit_reader.read(1):
            if not bit_reader.read(1):
                ref_offset = cursor - rel[0] * 2
                if ref_offset < 0:
                    raise ValueError("invalid QM W2 strip reference")
                value = read_u16le(output, ref_offset) ^ QMAGE_DIFF[index_reader.read_u8()]
            else:
                value = raw_reader.read_u16le()
        else:
            ref_offset = cursor - rel[0] * 2
            if ref_offset < 0:
                raise ValueError("invalid QM W2 strip copy reference")
            value = read_u16le(output, ref_offset)
        write_u16le_buffer(output, cursor, value)
        cursor += 2


def qm_w2_strip2(
    bit_reader: BitReader,
    index_reader: ByteReader,
    raw_reader: ByteReader,
    rel: list[int],
    output: bytearray,
    cursor: int,
) -> None:
    mask = index_reader.read_u8()
    for index in range(8):
        if not (index & 1) and not bit_reader.read(1):
            rel[0] = index_reader.read_u8() if bit_reader.read(1) else raw_reader.read_u16le()

        if not (mask & (1 << (7 - index))):
            if not bit_reader.read(1):
                ref_offset = cursor - rel[0] * 2
                if ref_offset < 0:
                    raise ValueError("invalid QM W2 strip reference")
                value = read_u16le(output, ref_offset) ^ QMAGE_DIFF[index_reader.read_u8()]
            else:
                value = raw_reader.read_u16le()
        else:
            ref_offset = cursor - rel[0] * 2
            if ref_offset < 0:
                raise ValueError("invalid QM W2 strip copy reference")
            value = read_u16le(output, ref_offset)
        write_u16le_buffer(output, cursor, value)
        cursor += 2


def decode_qm_w2_depth2(header: QmHeader, data: bytes) -> list[int]:
    if len(data) < 12:
        raise ValueError("QM W2 depth-2 body is too small")

    intermediate_size = read_u32le(data, 0)
    if intermediate_size < 16:
        raise ValueError(f"invalid QM W2 intermediate size {intermediate_size}")
    control_size = read_u32le(data, 4)
    index_size = read_u32le(data, 8)
    if 12 + control_size + index_size > len(data):
        raise ValueError(
            "invalid QM W2 depth-2 stream split points: "
            f"{control_size}, {index_size}, size={len(data)}"
        )

    bit_reader = BitReader(data[12:], bit_position=1)
    index_reader = ByteReader(data[12 + control_size :])
    raw_reader = ByteReader(data[12 + control_size + index_size :])
    intermediate = bytearray(intermediate_size)
    rel = [1]

    qm_w2_strip1(bit_reader, index_reader, raw_reader, rel, intermediate, 0)
    cursor = 16
    while cursor < (intermediate_size & ~15):
        if not bit_reader.read(1):
            if not bit_reader.read(1):
                intermediate[cursor : cursor + 16] = raw_reader.read_bytes(16)
            else:
                ref_offset = cursor - rel[0] * 2
                if ref_offset < 0:
                    raise ValueError("invalid QM W2 block copy reference")
                for index in range(8):
                    write_u16le_buffer(intermediate, cursor + index * 2, read_u16le(intermediate, ref_offset + index * 2))
        else:
            qm_w2_strip2(bit_reader, index_reader, raw_reader, rel, intermediate, cursor)
        cursor += 16

    remainder = intermediate_size & 15
    if remainder:
        intermediate[cursor : cursor + remainder] = index_reader.read_bytes(remainder)

    return decode_qm_w2_depth1(header, bytes(intermediate))


def decode_qm_w2_alpha(data: bytes, header: QmHeader) -> list[int]:
    if header.encoder_mode != QM_ENCODER_W2_PASS:
        raise ValueError("QM W2 alpha output requires a W2 stream")
    if header.alpha_depth not in (1, 2):
        raise ValueError(f"unsupported QM W2 alpha depth {header.alpha_depth}")

    alpha_offset = header.header_size + header.alpha_position
    if not (header.header_size < alpha_offset < len(data)):
        raise ValueError(f"invalid QM W2 alpha position {header.alpha_position}")

    sample_header = qm_alpha_sample_header(header)
    body = data[alpha_offset:]
    if header.alpha_depth == 1:
        samples = decode_qm_w2_depth1(sample_header, body)
    else:
        samples = decode_qm_w2_depth2(sample_header, body)
    return unpack_qm_alpha_samples(header, samples)


def decode_qm(data: bytes, tables: CodecTables) -> tuple[int, int, list[int]]:
    header = parse_qm_header(data)
    if header.is_animation:
        if header.current_frame_number != 1:
            raise ValueError("QM animation delta frames are not supported yet")
        if header.encoder_mode != QM_ENCODER_A9LL:
            raise ValueError("QM animation keyframe support currently requires A9LL")

    if header.encoder_mode == QM_ENCODER_A9LL:
        return decode_qm_a9ll(data, header, tables)

    if header.encoder_mode == QM_ENCODER_W2_PASS:
        body = data[header.header_size :]
        if header.depth == 1:
            return header.width, header.height, decode_qm_w2_depth1(header, body)
        if header.depth == 2:
            return header.width, header.height, decode_qm_w2_depth2(header, body)
        raise ValueError(f"unsupported QM W2 depth {header.depth}")

    raise ValueError(f"unsupported QM encoder mode {header.encoder_mode}")


def decode_ifeg(data: bytes, tables: CodecTables) -> tuple[int, int, list[int]]:
    header = parse_ifeg_header(data)
    if header.ifeg_type == IFEG_TYPE_65000001:
        return decode_ifeg_65000001(data, tables.delta16_simple)
    if is_three_stream_ifeg_type(header.ifeg_type):
        return decode_ifeg_three_stream_16bit(data, tables)
    supported = ", ".join(SUPPORTED_IFEG_TYPE_LABELS)
    raise ValueError(f"unsupported IFEG type 0x{header.ifeg_type:08x}; this release supports {supported}")


def decode_samsung_image(data: bytes, tables: CodecTables) -> tuple[int, int, list[int], str]:
    if data[:4] == b"IFEG":
        header = parse_ifeg_header(data)
        width, height, pixels = decode_ifeg(data, tables)
        return width, height, pixels, f"IFEG_0x{header.ifeg_type:08X}"
    if data[:2] == b"IM":
        header = parse_im_header(data)
        width, height, pixels = decode_im_v5d_16bit(data, tables)
        return width, height, pixels, f"IM_0x{header.version:02X}"
    if data[:2] == b"QM":
        header = parse_qm_header(data)
        width, height, pixels = decode_qm(data, tables)
        if header.encoder_mode == QM_ENCODER_A9LL:
            stream_label = "A9LL"
        elif header.encoder_mode == QM_ENCODER_W2_PASS:
            stream_label = f"W2D{header.depth}"
        else:
            stream_label = f"MODE{header.encoder_mode}"
        if header.is_animation:
            stream_label = f"{stream_label}_ANIM_KEY"
        return width, height, pixels, f"QM_0x{header.version:02X}_{stream_label}"
    supported = ", ".join(SUPPORTED_INPUT_LABELS)
    raise ValueError(f"unsupported image family; this release supports {supported}")


def decode_samsung_alpha(data: bytes, tables: CodecTables) -> list[int] | None:
    if data[:2] != b"QM":
        return None
    header = parse_qm_header(data)
    if header.raw_type != QM_RAW_TYPE_RGBA5658:
        return None
    if header.encoder_mode == QM_ENCODER_A9LL and header.alpha_depth in (1, 2):
        return decode_qm_a9ll_alpha(data, header, tables)
    if header.encoder_mode == QM_ENCODER_W2_PASS and header.alpha_depth in (1, 2):
        return decode_qm_w2_alpha(data, header)
    return None


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


def write_png_rgba888(
    path: Path,
    width: int,
    height: int,
    pixels: list[int],
    alpha: list[int],
    bgr565: bool = False,
) -> None:
    if len(alpha) != width * height:
        raise ValueError(f"alpha plane has {len(alpha)} pixels, expected {width * height}")

    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)
        for x in range(width):
            r, g, b = rgb565_to_rgb888(pixels[y * width + x], bgr565=bgr565)
            scanlines.extend((r, g, b, alpha[y * width + x] & 0xFF))

    payload = bytearray()
    payload += b"\x89PNG\r\n\x1a\n"
    payload += png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
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


def write_qm_animation_frame_images(data: bytes, output_path: Path, tables: CodecTables, bgr565: bool) -> list[Path]:
    decoded_frames = decode_qm_animation_frames(data, tables)
    frame_dir = output_path.with_name(f"{output_path.stem}_frames")
    frame_paths: list[Path] = []
    for frame in decoded_frames:
        frame_path = frame_dir / f"{output_path.stem}_frame_{frame.index:03d}{output_path.suffix}"
        write_image_rgb888(frame_path, frame.width, frame.height, frame.pixels, bgr565=bgr565)
        frame_paths.append(frame_path)
    return frame_paths


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
    candidates = input_path.rglob("*") if recursive else input_path.glob("*")
    return sorted(
        path
        for path in candidates
        if path.is_file() and path.suffix.lower() in SUPPORTED_INPUT_SUFFIXES
    )


def disambiguate_output_path(output_path: Path, input_path: Path, used_outputs: set[str]) -> Path:
    output_key = str(output_path).lower()
    if output_key not in used_outputs:
        used_outputs.add(output_key)
        return output_path

    suffix_stem = input_path.suffix.lower().lstrip(".") or "image"
    candidate = output_path.with_name(f"{output_path.stem}_{suffix_stem}{output_path.suffix}")
    candidate_key = str(candidate).lower()
    counter = 2
    while candidate_key in used_outputs:
        candidate = output_path.with_name(f"{output_path.stem}_{suffix_stem}_{counter}{output_path.suffix}")
        candidate_key = str(candidate).lower()
        counter += 1
    used_outputs.add(candidate_key)
    return candidate


def plan_batch_outputs(
    input_files: list[Path],
    input_root: Path | None,
    output_root: Path,
    output_format: str,
) -> dict[Path, Path]:
    planned_outputs: dict[Path, Path] = {}
    used_outputs: set[str] = set()
    for path in input_files:
        output_path = default_output_for_file(path, input_root, output_root, output_format)
        planned_outputs[path] = disambiguate_output_path(output_path, path, used_outputs)
    return planned_outputs


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def qm_encoder_label(encoder_mode: int) -> str:
    if encoder_mode == QM_ENCODER_A9LL:
        return "A9LL"
    if encoder_mode == QM_ENCODER_W2_PASS:
        return "W2"
    return f"MODE{encoder_mode}"


def qm_type_label(header: QmHeader) -> str:
    label = f"QM_0x{header.version:02X}_{qm_encoder_label(header.encoder_mode)}"
    if header.encoder_mode == QM_ENCODER_W2_PASS:
        label = f"{label}D{header.depth}"
    if header.is_animation:
        label = f"{label}_ANIM"
    return label


def qm_stream_offsets(data: bytes, header: QmHeader) -> tuple[str, str, str]:
    if header.encoder_mode == QM_ENCODER_W2_PASS:
        return "", "", str(header.header_size)
    if len(data) < header.header_size + 8:
        return "", "", ""
    command_offset = read_u32le(data, header.header_size)
    raw_offset = read_u32le(data, header.header_size + 4)
    stream_start = header.header_size + 8
    return str(command_offset), str(raw_offset), str(stream_start)


def inspect_samsung_image(data: bytes) -> dict[str, str]:
    row = {field: "" for field in INSPECT_MANIFEST_FIELDS}
    row["supported"] = "no"

    try:
        if data[:4] == b"IFEG":
            header = parse_ifeg_header(data)
            supported = header.ifeg_type == IFEG_TYPE_65000001 or is_three_stream_ifeg_type(header.ifeg_type)
            row.update(
                {
                    "family": "IFEG",
                    "width": str(header.width),
                    "height": str(header.height),
                    "type": f"IFEG_0x{header.ifeg_type:08X}",
                    "version": "",
                    "header_size": "16",
                    "raw_offset": str(header.raw_word_offset),
                    "supported": yes_no(supported),
                    "notes": "" if supported else "unsupported IFEG type",
                }
            )
            return row

        if data[:2] == b"IM":
            width = read_u16le(data, 2) if len(data) >= 6 else 0
            height = read_u16le(data, 4) if len(data) >= 6 else 0
            flags = data[6] if len(data) > 6 else 0
            version = data[7] if len(data) > 7 else 0
            extended_header = bool(len(data) > 8 and data[8] & IM_FLAG_EXTENDED_HEADER)
            alpha_plane = bool(flags & IM_FLAG_ALPHA_PLANE)
            near_lossless = bool(flags & IM_FLAG_NEAR_LOSSLESS)
            stream_header_offset = 13 if extended_header else 9
            command_offset = raw_offset = ""
            if len(data) >= stream_header_offset + 8:
                command_offset = str(read_u32le(data, stream_header_offset))
                raw_offset = str(read_u32le(data, stream_header_offset + 4))
            supported = version == 0x5D and not alpha_plane and width > 0 and height > 0
            notes: list[str] = []
            if version != 0x5D:
                notes.append("unsupported IM version")
            if alpha_plane:
                notes.append("IM alpha-plane variant")
            row.update(
                {
                    "family": "IM",
                    "width": str(width) if width else "",
                    "height": str(height) if height else "",
                    "type": f"IM_0x{version:02X}",
                    "version": f"0x{version:02X}",
                    "flags": (
                        f"flags=0x{flags:02X};near_lossless={yes_no(near_lossless)};"
                        f"alpha_plane={yes_no(alpha_plane)};extended_header={yes_no(extended_header)}"
                    ),
                    "header_size": str(stream_header_offset + 8),
                    "command_offset": command_offset,
                    "raw_offset": raw_offset,
                    "stream_start": str(stream_header_offset + 8),
                    "supported": yes_no(supported),
                    "notes": ";".join(notes),
                }
            )
            return row

        if data[:2] == b"QM":
            header = parse_qm_header(data, strict=False)
            command_offset, raw_offset, stream_start = qm_stream_offsets(data, header)
            can_attempt_decode = (
                header.version == QM_VERSION_0B
                and header.raw_type in SUPPORTED_QM_RAW_TYPES
                and header.encoder_mode in (QM_ENCODER_A9LL, QM_ENCODER_W2_PASS)
                and (not header.is_animation or header.current_frame_number == 1)
            )
            notes = []
            if header.version != QM_VERSION_0B:
                notes.append("unsupported QM version")
            if header.raw_type == QM_RAW_TYPE_RGB565_NO_ALPHA:
                notes.append("RGB565/no-alpha raw type")
            elif header.raw_type not in SUPPORTED_QM_RAW_TYPES:
                notes.append("unsupported QM raw type")
            if qm_has_extra_exception(header):
                notes.append("use_extra_exception flag set")
            if header.is_animation and header.current_frame_number != 1:
                notes.append("animation delta frame")
            if header.encoder_mode == QM_ENCODER_W2_PASS and len(data) >= header.header_size + 12:
                if header.depth == 2:
                    notes.append(
                        "w2_intermediate_size="
                        f"{read_u32le(data, header.header_size)};"
                        f"w2_control_size={read_u32le(data, header.header_size + 4)};"
                        f"w2_index_size={read_u32le(data, header.header_size + 8)}"
                    )
                else:
                    notes.append(
                        "w2_table_count="
                        f"{read_u32le(data, header.header_size)};"
                        f"w2_index_size={read_u32le(data, header.header_size + 4)};"
                        f"w2_run_size={read_u32le(data, header.header_size + 8)}"
                    )
            supported = yes_no(can_attempt_decode)
            row.update(
                {
                    "family": "QM",
                    "width": str(header.width),
                    "height": str(header.height),
                    "type": qm_type_label(header),
                    "version": f"0x{header.version:02X}",
                    "flags": (
                        f"raw_type=0x{header.raw_type:02X};flags4=0x{header.flags4:02X};"
                        f"flags5=0x{header.flags5:02X};animation={yes_no(header.is_animation)}"
                    ),
                    "header_size": str(header.header_size),
                    "codec": qm_encoder_label(header.encoder_mode),
                    "depth": str(header.depth),
                    "alpha_depth": str(header.alpha_depth),
                    "alpha_position": str(header.alpha_position) if header.alpha_position else "",
                    "command_offset": command_offset,
                    "raw_offset": raw_offset,
                    "stream_start": stream_start,
                    "supported": supported,
                    "notes": ";".join(notes),
                }
            )
            return row

        row["error"] = "unsupported image family"
        return row
    except Exception as exc:
        row["error"] = str(exc)
        return row


def inspect_one_file(input_path: Path) -> dict[str, str]:
    row = inspect_samsung_image(input_path.read_bytes())
    row["source"] = str(input_path)
    return row


def format_inspect_row(row: dict[str, str]) -> str:
    dimensions = f"{row['width']}x{row['height']}" if row["width"] and row["height"] else "unknown-size"
    parts = [row["source"], row["type"] or row["family"] or "unknown", dimensions, f"supported={row['supported']}"]
    if row["codec"]:
        parts.append(f"codec={row['codec']}")
    if row["flags"]:
        parts.append(row["flags"])
    if row["command_offset"] and row["raw_offset"]:
        parts.append(f"command={row['command_offset']} raw={row['raw_offset']}")
    elif row["command_offset"]:
        parts.append(f"command={row['command_offset']}")
    elif row["raw_offset"]:
        parts.append(f"raw={row['raw_offset']}")
    if row["notes"]:
        parts.append(f"notes={row['notes']}")
    if row["error"]:
        parts.append(f"error={row['error']}")
    return " | ".join(parts)


def qm_a9ll_color_raw_limit(data: bytes, header: QmHeader, raw_start: int) -> int:
    if header.raw_type in (QM_RAW_TYPE_RGBA5658, 0x06) and raw_start < header.alpha_position <= len(data):
        return header.alpha_position
    return len(data)


def analyze_qm_a9ll_stream(data: bytes, header: QmHeader) -> dict[str, str]:
    stats: dict[str, str] = {}
    command_offset, raw_offset, stream_start = qm_stream_offsets(data, header)
    if not command_offset or not raw_offset or not stream_start:
        raise ValueError("A9LL stream offsets are unavailable")

    command_start = int(command_offset)
    raw_start = int(raw_offset)
    control_start = int(stream_start)
    if not (control_start <= command_start <= raw_start <= len(data)):
        raise ValueError(
            "invalid A9LL stream split points: "
            f"{control_start}, {command_start}, {raw_start}, size={len(data)}"
        )

    raw_limit = qm_a9ll_color_raw_limit(data, header, raw_start)
    if qm_has_extra_exception(header):
        control_bits = BitReader(data[control_start:command_start], bit_position=1)
        command_bits = BitReader(data[command_start:raw_start], bit_position=1)
        raw_words = ByteReader(data[:raw_limit], raw_start)
    else:
        control_bits = BitReader(data[control_start:], bit_position=1)
        command_bits = BitReader(data[command_start:], bit_position=1)
        raw_words = ByteReader(data, raw_start)

    mixed_tiles = 0
    copy_tiles = 0
    edge_copy_tiles = 0
    mask_words = 0
    copied_pixels = 0
    delta_pixels = 0
    literal_pixels = 0
    last_tile = ""
    last_mode = ""

    try:
        for y in range(0, header.height, 4):
            for x in range(0, header.width, 4):
                last_tile = f"{x},{y}"
                tile_w = min(4, header.width - x)
                tile_h = min(4, header.height - y)
                mode = control_bits.read(2)
                last_mode = str(mode)
                if mode < 3:
                    mixed_tiles += 1
                    mask = raw_words.read_u16le()
                    mask_words += 1
                    mask_bit = 0
                    for yy in range(4):
                        for xx in range(4):
                            if x + xx >= header.width or y + yy >= header.height:
                                continue
                            if mask & (1 << mask_bit):
                                copied_pixels += 1
                            elif qm_has_extra_exception(header):
                                if control_bits.read(1):
                                    raw_words.read_u16le()
                                    literal_pixels += 1
                                else:
                                    command = command_bits.read(3)
                                    control_bits.read(command + 1)
                                    delta_pixels += 1
                            else:
                                command = command_bits.read(3)
                                if command == 7:
                                    raw_words.read_u16le()
                                    literal_pixels += 1
                                else:
                                    control_bits.read(command + 1)
                                    delta_pixels += 1
                            mask_bit += 1
                elif x > 0:
                    copy_tiles += 1
                    copied_pixels += tile_w * tile_h
                else:
                    edge_copy_tiles += 1
    except Exception as exc:
        stats["analysis_status"] = "failed"
        stats["analysis_error"] = f"{type(exc).__name__}: {exc}; tile={last_tile}; mode={last_mode}"
    else:
        stats["analysis_status"] = "ok"

    control_bits_read = max(0, control_bits.bit_position - 1)
    command_bits_read = max(0, command_bits.bit_position - 1)
    control_limit_bits = max(0, command_start - control_start) * 8
    command_limit_bits = max(0, raw_start - command_start) * 8
    control_overrun_bits = max(0, control_bits_read - control_limit_bits)
    command_overrun_bits = max(0, command_bits_read - command_limit_bits)
    raw_available_bytes = max(0, len(data) - raw_start)
    raw_limit_bytes = max(0, raw_limit - raw_start)
    raw_bytes_read = max(0, raw_words.offset - raw_start)
    raw_overrun_bytes = max(0, raw_words.offset - raw_limit)
    overruns = []
    if control_overrun_bits:
        overruns.append(f"control stream overran split by {control_overrun_bits} bits")
    if command_overrun_bits:
        overruns.append(f"command stream overran split by {command_overrun_bits} bits")
    if raw_overrun_bytes:
        overruns.append(f"raw stream overran color limit by {raw_overrun_bytes} bytes")
    if overruns and stats.get("analysis_status") == "ok":
        stats["analysis_status"] = "warning"
        stats["analysis_error"] = "; ".join(overruns)

    tile_columns = (header.width + 3) // 4
    tile_rows = (header.height + 3) // 4
    stats.update(
        {
            "stream_summary": (
                f"control_bytes={command_start - control_start};"
                f"command_bytes={raw_start - command_start};"
                f"raw_bytes={raw_available_bytes};"
                f"raw_limit_bytes={raw_limit_bytes}"
            ),
            "tile_count": str(tile_columns * tile_rows),
            "mixed_tiles": str(mixed_tiles),
            "copy_tiles": str(copy_tiles),
            "edge_copy_tiles": str(edge_copy_tiles),
            "mask_words": str(mask_words),
            "copied_pixels": str(copied_pixels),
            "delta_pixels": str(delta_pixels),
            "literal_pixels": str(literal_pixels),
            "control_bits_read": str(control_bits_read),
            "control_limit_bits": str(control_limit_bits),
            "control_overrun_bits": str(control_overrun_bits),
            "command_bits_read": str(command_bits_read),
            "command_limit_bits": str(command_limit_bits),
            "command_overrun_bits": str(command_overrun_bits),
            "raw_bytes_read": str(raw_bytes_read),
            "raw_final_offset": str(raw_words.offset),
            "raw_limit_offset": str(raw_limit),
            "raw_limit_bytes": str(raw_limit_bytes),
            "raw_overrun_bytes": str(raw_overrun_bytes),
        }
    )
    return stats


def analyze_qm_w2_stream(data: bytes, header: QmHeader) -> dict[str, str]:
    stats: dict[str, str] = {}
    body_start = header.header_size
    body_size = len(data) - body_start
    if body_size < 12:
        raise ValueError(f"QM W2 body is too small: {body_size}")

    if header.depth == 2:
        intermediate_size = read_u32le(data, body_start)
        control_size = read_u32le(data, body_start + 4)
        index_size = read_u32le(data, body_start + 8)
        raw_size = body_size - 12 - control_size - index_size
        stats["stream_summary"] = (
            f"body_bytes={body_size};intermediate_size={intermediate_size};"
            f"control_bytes={control_size};index_bytes={index_size};raw_bytes={raw_size}"
        )
    else:
        table_count = read_u32le(data, body_start)
        index_size = read_u32le(data, body_start + 4)
        run_size = read_u32le(data, body_start + 8)
        raw_size = body_size - 16 - table_count * 4 - index_size - run_size
        stats["stream_summary"] = (
            f"body_bytes={body_size};table_count={table_count};"
            f"index_bytes={index_size};run_bytes={run_size};raw_bytes={raw_size}"
        )

    stats["analysis_status"] = "ok"
    return stats


def analyze_samsung_image(data: bytes, tables: CodecTables) -> dict[str, str]:
    row = {field: "" for field in ANALYZE_MANIFEST_FIELDS}
    row.update(inspect_samsung_image(data))

    try:
        decode_samsung_image(data, tables)
    except Exception as exc:
        row["decode_status"] = "failed"
        row["decode_error"] = str(exc)
    else:
        row["decode_status"] = "decoded"

    if row["family"] != "QM":
        row["analysis_status"] = "ok" if not row["error"] else "failed"
        row["analysis_error"] = row["error"]
        return row

    try:
        header = parse_qm_header(data, strict=False)
        if header.encoder_mode == QM_ENCODER_A9LL:
            row.update(analyze_qm_a9ll_stream(data, header))
        elif header.encoder_mode == QM_ENCODER_W2_PASS:
            row.update(analyze_qm_w2_stream(data, header))
        else:
            row["analysis_status"] = "skipped"
            row["analysis_error"] = f"unsupported QM encoder mode {header.encoder_mode}"
    except Exception as exc:
        row["analysis_status"] = "failed"
        row["analysis_error"] = str(exc)

    return row


def analyze_one_file(input_path: Path, tables: CodecTables) -> dict[str, str]:
    row = analyze_samsung_image(input_path.read_bytes(), tables)
    row["source"] = str(input_path)
    return row


def format_analyze_row(row: dict[str, str]) -> str:
    dimensions = f"{row['width']}x{row['height']}" if row["width"] and row["height"] else "unknown-size"
    parts = [
        row["source"],
        row["type"] or row["family"] or "unknown",
        dimensions,
        f"decode={row['decode_status'] or 'unknown'}",
        f"analysis={row['analysis_status'] or 'unknown'}",
    ]
    if row["tile_count"]:
        parts.append(
            f"tiles={row['tile_count']} mixed={row['mixed_tiles']} copy={row['copy_tiles']} edge={row['edge_copy_tiles']}"
        )
    if row["literal_pixels"] or row["delta_pixels"] or row["copied_pixels"]:
        parts.append(
            f"pixels literal={row['literal_pixels']} delta={row['delta_pixels']} copied={row['copied_pixels']}"
        )
    if row["control_bits_read"] or row["command_bits_read"] or row["raw_bytes_read"]:
        parts.append(
            f"read control_bits={row['control_bits_read'] or '0'} "
            f"command_bits={row['command_bits_read'] or '0'} raw_bytes={row['raw_bytes_read'] or '0'}"
        )
    if row["control_overrun_bits"] or row["command_overrun_bits"] or row["raw_overrun_bytes"]:
        parts.append(
            f"overrun control_bits={row['control_overrun_bits'] or '0'} "
            f"command_bits={row['command_overrun_bits'] or '0'} raw_bytes={row['raw_overrun_bytes'] or '0'}"
        )
    if row["raw_limit_offset"]:
        parts.append(
            f"raw_limit={row['raw_limit_offset']} "
            f"limit_bytes={row['raw_limit_bytes'] or '0'} overrun={row['raw_overrun_bytes'] or '0'}"
        )
    if row["stream_summary"]:
        parts.append(row["stream_summary"])
    if row["decode_error"]:
        parts.append(f"decode_error={row['decode_error']}")
    if row["analysis_error"]:
        parts.append(f"analysis_error={row['analysis_error']}")
    if row["notes"]:
        parts.append(f"notes={row['notes']}")
    return " | ".join(parts)


def decode_one_file(
    input_path: Path,
    output_path: Path,
    tables: CodecTables,
    bgr565: bool,
    split_panels: bool,
    with_alpha: bool,
    extract_animation_frames: bool,
) -> dict[str, str]:
    data = input_path.read_bytes()
    width, height, pixels, type_label = decode_samsung_image(data, tables)
    alpha_status = ""
    if with_alpha:
        if output_path.suffix.lower() != ".png":
            raise ValueError("--with-alpha requires PNG output")
        alpha = decode_samsung_alpha(data, tables)
        if alpha is None:
            alpha = [255] * (width * height)
            alpha_status = "opaque"
        else:
            alpha_status = "decoded"
        write_png_rgba888(output_path, width, height, pixels, alpha, bgr565=bgr565)
    else:
        write_image_rgb888(output_path, width, height, pixels, bgr565=bgr565)

    extra_outputs: list[str] = []
    if split_panels:
        extra_outputs.extend(str(p) for p in split_240x320_panels(output_path, width, height, pixels, bgr565=bgr565))
    if extract_animation_frames and data[:2] == b"QM":
        try:
            header = parse_qm_header(data)
        except ValueError:
            header = None
        if header is not None and header.is_animation:
            extra_outputs.extend(str(p) for p in write_qm_animation_frame_images(data, output_path, tables, bgr565=bgr565))

    return {
        "source": str(input_path),
        "output": str(output_path),
        "extra_outputs": ";".join(extra_outputs),
        "width": str(width),
        "height": str(height),
        "type": type_label,
        "status": "decoded",
        "alpha": alpha_status,
        "error": "",
    }


def write_manifest(path: Path, rows: list[dict[str, str]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = DECODE_MANIFEST_FIELDS
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Decode Samsung IFG/QMG/IFEG/IM images from legacy phone firmware. "
        "This release supports IFEG types 0x65000001, 0x95000100, 0x150001xx, "
        "IM 0x5D, and QM 0x0B."
    )
    parser.add_argument("input", type=Path, help="input .ifg/.qmg file or folder")
    parser.add_argument("output", type=Path, nargs="?", help="output .bmp/.png file, or output folder for batch mode")
    parser.add_argument("--inspect", action="store_true", help="print image headers and stream metadata without decoding")
    parser.add_argument("--analyze", action="store_true", help="inspect headers and walk supported streams to report decode diagnostics")
    parser.add_argument("--recursive", action="store_true", help="recurse into input folders")
    parser.add_argument("--tables", type=Path, default=DEFAULT_TABLES_JSON, help="codec table JSON path")
    parser.add_argument("--format", choices=SUPPORTED_OUTPUT_FORMATS, default="bmp", help="batch output format")
    parser.add_argument("--bgr565", action="store_true", help="interpret decoded 16-bit pixels as BGR565")
    parser.add_argument("--split-240x320-panels", action="store_true", help="also split 240x960 wallpapers into 240x320 panels")
    parser.add_argument("--with-alpha", action="store_true", help="write PNG with decoded alpha when supported")
    parser.add_argument("--extract-animation-frames", action="store_true", help="also export observed QM A9LL animation frames")
    parser.add_argument("--manifest", type=Path, help="write a CSV decode manifest")
    parser.add_argument("--version", action="version", version=f"samsung-ifg-decoder {VERSION}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    input_path = args.input
    input_files = iter_input_files(input_path, recursive=args.recursive)

    if args.inspect and args.analyze:
        parser.error("--inspect and --analyze cannot be used together")

    if args.inspect:
        rows = []
        for source in input_files:
            row = inspect_one_file(source)
            rows.append(row)
            print(format_inspect_row(row))
        if args.manifest:
            write_manifest(args.manifest, rows, INSPECT_MANIFEST_FIELDS)
        return 1 if any(row["error"] for row in rows) else 0

    if args.analyze:
        tables = load_codec_tables(args.tables)
        rows = []
        for source in input_files:
            row = analyze_one_file(source, tables)
            rows.append(row)
            print(format_analyze_row(row))
        if args.manifest:
            write_manifest(args.manifest, rows, ANALYZE_MANIFEST_FIELDS)
        return 1 if any(row["error"] for row in rows) else 0

    if args.output is None:
        parser.error("output is required unless --inspect or --analyze is used")

    tables = load_codec_tables(args.tables)
    output_path = args.output

    if input_path.is_file() and output_path.suffix:
        if args.with_alpha and output_path.suffix.lower() != ".png":
            print("--with-alpha requires a .png output path", file=sys.stderr)
            return 2
        planned_outputs = {input_path: output_path}
        input_root = None
    else:
        input_root = input_path if input_path.is_dir() else None
        output_format = "png" if args.with_alpha else args.format
        planned_outputs = plan_batch_outputs(input_files, input_root, output_path, output_format)

    rows: list[dict[str, str]] = []
    for source, target in planned_outputs.items():
        try:
            row = decode_one_file(
                source,
                target,
                tables,
                args.bgr565,
                args.split_240x320_panels,
                args.with_alpha,
                args.extract_animation_frames,
            )
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
                "alpha": "",
                "error": str(exc),
            }
            print(f"failed {source}: {exc}", file=sys.stderr)
        rows.append(row)

    if args.manifest:
        write_manifest(args.manifest, rows, DECODE_MANIFEST_FIELDS)

    return 1 if any(row["status"] == "failed" for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
