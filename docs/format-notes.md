# Format Notes

These notes document the currently implemented Samsung `IFEG_65000001` path. They are incomplete and will change as more IFG variants are decoded.

## IFEG Header

`IFEG` files begin with:

| Offset | Size | Meaning |
| ---: | ---: | --- |
| `0x00` | 4 | ASCII magic `IFEG` |
| `0x04` | 2 | width, little-endian `u16` |
| `0x06` | 2 | height, little-endian `u16` |
| `0x08` | 4 | type, little-endian `u32` |
| `0x0c` | 4 | raw-word stream offset for `0x65000001` |

This decoder currently supports type `0x65000001`.

## Tile Layout

Images are decoded as a grid of tiles. Most tiles are `4x4`; edge tiles can be smaller when width or height is not divisible by four.

For example, a `240x320` image is decoded as `60 x 80` tiles.

## Bitstream

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

## Output Pixels

Decoded pixels are 16-bit values. The CLI writes them as 24-bit BMP using RGB565 expansion by default. Use `--bgr565` if you are testing files that appear color-swapped.

## Known Samsung B5722 Families

Observed in B5722 firmware:

| Family | Status |
| --- | --- |
| `IFEG_65000001` | supported |
| `IFEG_95000100` | not yet supported |
| `IFEG_15000100` / `IFEG_150001xx` | not yet supported |
| `IM` | not yet supported |
| `QM` | not yet supported |
