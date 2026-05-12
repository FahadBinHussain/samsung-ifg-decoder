# Format Notes

These notes document the currently implemented Samsung `IFEG_65000001`, `IFEG_95000100`, `IFEG_150001xx`, `IM_0x5D`, and `QM_0x0B` paths. They are incomplete and will change as more IFG/QMG variants are decoded.

## IFEG Header

`IFEG` files begin with:

| Offset | Size | Meaning |
| ---: | ---: | --- |
| `0x00` | 4 | ASCII magic `IFEG` |
| `0x04` | 2 | width, little-endian `u16` |
| `0x06` | 2 | height, little-endian `u16` |
| `0x08` | 4 | type, little-endian `u32` |
| `0x0c` | varies | subtype-specific payload metadata |

This decoder currently supports types `0x65000001`, `0x95000100`, and the `0x150001xx` family.

## IM 0x5D Header

Observed B5722 `IM` files begin with:

| Offset | Size | Meaning |
| ---: | ---: | --- |
| `0x00` | 2 | ASCII magic `IM` |
| `0x02` | 2 | width, little-endian `u16` |
| `0x04` | 2 | height, little-endian `u16` |
| `0x06` | 1 | flags; bit `0x20` selects the near-lossless/raw-flag pixel path |
| `0x07` | 1 | version; supported value `0x5D` |
| `0x08` | 1 | layout flags; bit `0x40` moves the stream header from `0x09` to `0x0d` |

For non-alpha `IM_0x5D` files, the stream header contains two little-endian split points:

| Layout | Stream header | Control stream | Command stream | Raw/mask stream |
| --- | ---: | ---: | ---: | ---: |
| `data[0x08] & 0x40 == 0` | `0x09` | `0x11` | `u32 @ 0x09` | `u32 @ 0x0d` |
| `data[0x08] & 0x40 != 0` | `0x0d` | `0x15` | `u32 @ 0x0d` | `u32 @ 0x11` |

`IM` files with the high bit set in `data[0x06]` appear to include alpha-plane metadata and are not implemented yet.

## QM 0x0B Header

Observed B5722 `QM` files appear with both `.ifg` and `.qmg` extensions and begin with:

| Offset | Size | Meaning |
| ---: | ---: | --- |
| `0x00` | 2 | ASCII magic `QM` |
| `0x02` | 1 | version; supported value `0x0B` |
| `0x03` | 1 | raw type; observed value `0x03` for RGBA5658-style resources |
| `0x04` | 1 | flags; bit `0x80` appears to mark animation frames |
| `0x05` | 1 | codec flags; low three bits select the implemented stream variant |
| `0x06` | 2 | width, little-endian `u16` |
| `0x08` | 2 | height, little-endian `u16` |
| `0x0a` | 1 | additional flags |
| `0x0b` | 1 | additional flags |
| `0x0c` | 4 | observed metadata/alpha-position field |
| `0x10` | varies | codec body |

The decoder exports the RGB565 color plane by default. With `--with-alpha`, it also exports decoded alpha for observed A9LL and W2 alpha streams as RGBA PNG.

## QM 0x0B A9LL Stream

For observed files where `data[0x05] & 0x07 == 0`, the body uses a `4x4` tile grid with three streams:

| Offset | Size | Meaning |
| ---: | ---: | --- |
| `0x10` | 4 | command stream absolute offset |
| `0x14` | 4 | raw/mask stream absolute offset |
| `0x18` | varies | control bitstream |

Each tile starts with a 2-bit mode from the control stream:

| Mode | Meaning |
| ---: | --- |
| `0` | mixed tile using reference pixel `x - 1, y` |
| `1` | mixed tile using reference pixel `x, y - 1` |
| `2` | mixed tile using reference pixel `x - 1, y - 1` |
| `3` | copy from previous pixel for the whole tile when `x > 0` |

Mixed tiles read a 16-bit mask from the raw/mask stream. A set mask bit copies from the reference pixel. A clear mask bit reads a 3-bit command from the command stream. Command `7` reads a raw 16-bit pixel; other commands read `command + 1` extra bits from the control stream and apply a delta from:

```text
codec_tables.json -> tables.delta16_decode_b.values_signed[2:258]
```

## QM 0x0B A9LL Alpha Stream

Observed A9LL alpha bodies start at the header's `0x0c` split point. The alpha body begins with two offsets relative to the alpha body:

| Body offset | Size | Meaning |
| ---: | ---: | --- |
| `0x00` | 4 | command stream offset |
| `0x04` | 4 | raw/mask stream offset |
| `0x08` | varies | control bitstream |

The decoded alpha samples are packed two pixels per 16-bit value: low byte first, high byte second. The tile grid is therefore `4x4` over packed samples, equivalent to `8x4` output pixels. Mixed alpha tiles use the same 2-bit mode, 16-bit mask, 3-bit command, raw word, and delta-table pattern as the color A9LL stream.

## QM 0x0B W2 Stream

For observed files where `data[0x05] & 0x07 == 1`, the body starts at `0x10` and uses the W2 pass. B5722 samples use depth `2` (`data[0x05] & 0x40 != 0`), which first expands an intermediate buffer and then runs the W2 depth-1 table/RLE pass.

The implemented depth-2 body begins with:

| Body offset | Size | Meaning |
| ---: | ---: | --- |
| `0x00` | 4 | intermediate W2 depth-1 buffer size |
| `0x04` | 4 | control bitstream byte count |
| `0x08` | 4 | index/exception stream byte count |
| `0x0c` | varies | control bitstream, then index/exception stream, then raw stream |

The intermediate depth-1 buffer begins with:

| Offset | Size | Meaning |
| ---: | ---: | --- |
| `0x00` | 4 | 32-bit table entry count |
| `0x04` | 4 | index stream byte count |
| `0x08` | 4 | run stream byte count |
| `0x10` | varies | 32-bit table entries, index stream, run stream, raw stream |

## QM 0x0B W2 Alpha Stream

Observed W2 alpha bodies start at `0x10 + header[0x0c]`. The alpha body uses the same W2 depth-1 or depth-2 stream layout as the color body, selected by the alpha-depth bit in `data[0x05]`.

Like A9LL alpha, W2 alpha output is packed two pixels per 16-bit value: low byte first, high byte second. The decoder therefore runs W2 over a sample image whose width is `(width + 1) // 2`, then expands the packed samples to one alpha byte per output pixel.

## Tile Layout

Images are decoded as a grid of tiles. Most tiles are `4x4`; edge tiles can be smaller when width or height is not divisible by four.

For example, a `240x320` image is decoded as `60 x 80` tiles.

## IFEG_65000001 Bitstream

The bitstream starts at bit position `0x81` using one-based, MSB-first bit indexing.

Each tile starts with a 2-bit mode:

| Mode | Meaning |
| ---: | --- |
| `0` | reference prior pixel at distance `1` |
| `1` | reference prior row at distance `width` |
| `2` | reference upper-left pixel at distance `width + 1` |
| `3` | copy from previous pixel for the whole tile |

For modes `0`, `1`, and `2`, each pixel then reads:

1. A 1-bit copy flag.
2. If the flag is set, copy from the reference pixel.
3. Otherwise read a 3-bit command.
4. Command `7` reads a raw 16-bit pixel from the raw-word stream.
5. Other commands read `command + 2` extra bits and use `codec_tables.json` to apply a delta from the reference pixel.

The active table for this release is:

```text
codec_tables.json -> tables.delta16_simple.values_signed
```

## IFEG_95000100 / IFEG_150001xx Streams

`IFEG_95000100` and `IFEG_150001xx` use the same `4x4` tile grid but a three-stream body. The observed B5722 layout starts with this internal payload header:

| Offset | Size | Meaning |
| ---: | ---: | --- |
| `0x0c` | 5 | observed marker bytes `01 00 01 00` followed by `00` or `01` |
| `0x11` | 4 | auxiliary split point observed in files; not required by this decoder path |
| `0x15` | 4 | control/command stream split point |
| `0x19` | 4 | command/raw stream split point |
| `0x1d` | varies | stream data |

The decoder builds:

- control stream: bytes from `0x1d` through `split_b + 4`
- command stream: bytes from `split_b` through `split_c + 4`
- raw-word stream: bytes from `split_c` to EOF

The small overlap matches the recovered decoder behavior and gives the bit reader enough lookahead at stream boundaries.

Each tile starts with a 3-bit mode:

| Mode | Meaning |
| ---: | --- |
| `0` | mixed tile using reference distance `1` |
| `1` | mixed tile using reference distance `width` |
| `2` | mixed tile using reference distance `width + 1` |
| `3` | copy from previous pixel for the whole tile |
| `4` | raw 16-bit pixels for the whole tile |

Mixed tiles read a 16-bit raw mask. A set mask bit copies from the reference pixel. A clear mask bit reads either a raw 16-bit pixel or a delta command. Delta commands use:

```text
codec_tables.json -> tables.delta16_decode_a.values_signed
codec_tables.json -> tables.delta16_decode_b.values_signed
```

## IM 0x5D V-Codec Stream

The implemented `IM_0x5D` path uses the same `4x4` tile grid. Each tile starts with a 2-bit mode from the control stream:

| Mode | Meaning |
| ---: | --- |
| `0` | mixed tile using reference distance `1` |
| `1` | mixed tile using reference distance `width` |
| `2` | mixed tile using reference distance `width + 1` |
| `3` | copy from previous pixel for the whole tile |

Mixed tiles read a 16-bit mask from the raw/mask stream. A set mask bit copies from the reference pixel. A clear mask bit decodes a new pixel.

For standard `IM_0x5D` files, a clear mask bit reads a 3-bit command from the command stream. Command `7` reads a raw 16-bit pixel from the raw/mask stream. Other commands read `command + 1` extra bits from the control stream and apply a delta from:

```text
codec_tables.json -> tables.delta16_decode_b.values_signed
```

For files with flag `data[0x06] & 0x20`, a clear mask bit first reads a 1-bit raw flag from the control stream. If set, the pixel is read raw from the raw/mask stream; otherwise it uses the same delta table. In this path command `7` is also a delta command, using an 8-bit extra value.

## Output Pixels

Decoded pixels are 16-bit values. The CLI writes them as 24-bit BMP using RGB565 expansion by default. Use `--bgr565` if you are testing files that appear color-swapped.

## Known Samsung B5722 Families

Observed in B5722 firmware:

| Family | Status |
| --- | --- |
| `IFEG_65000001` | supported |
| `IFEG_95000100` | supported |
| `IFEG_15000100` / `IFEG_150001xx` | supported |
| `IM_0x5D` | supported for observed non-alpha B5722 files |
| `QM_0x0B` | supported for observed B5722 A9LL and W2 depth-2 `.ifg` / `.qmg` files; A9LL and W2 alpha output is supported with `--with-alpha` |
