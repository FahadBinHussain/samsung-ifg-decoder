# samsung-ifg-decoder

[![CI](https://github.com/FahadBinHussain/samsung-ifg-decoder/actions/workflows/ci.yml/badge.svg)](https://github.com/FahadBinHussain/samsung-ifg-decoder/actions/workflows/ci.yml)

Open-source Samsung IFG / QMG / IFEG / IM / QM image decoder for legacy phone firmware assets.

This project decodes a subset of Samsung `.ifg` and `.qmg` images used in older feature-phone firmware. Current releases support `IFEG` images with types `0x65000001`, `0x95000100`, and `0x150001xx`, `IM` version `0x5D`, and observed `QM` version `0x0B` images, including many image assets found in Samsung B5722 firmware.

## Status

Supported:

- `IFEG` magic: `49 46 45 47`
- Type: `0x65000001`
- Type: `0x95000100`
- Type family: `0x150001xx`
- `IM` magic: `49 4D`, version byte `0x5D`
- `QM` magic: `51 4D`, version byte `0x0B`, observed A9LL, A9LL `use_extra_exception`, and W2 depth-2 streams
- Odd-pixel-count W2 assets observed in QMG UI strips
- Output: 24-bit `.bmp` or `.png`
- Optional RGBA `.png` output for observed `QM_0x0B_A9LL` and `QM_0x0B_W2` alpha planes
- First-frame decode for observed `QM_0x0B_A9LL` animation keyframes
- Single-file decode
- Folder/batch decode for `.ifg` and `.qmg`
- Optional split of `240x960` idle wallpapers into `240x320` panels

Not supported yet:

- Other `QM` / QMG versions and full animation frame export
- `IM` alpha-plane variants
- Encoding BMP/JPG back to IFG

## Requirements

- Python 3.10 or newer
- No third-party Python packages

## Test

Run the synthetic regression suite:

```bash
python -m unittest discover -s tests
```

## Usage

Decode one file:

```bash
python samsung_ifg_decoder.py input.ifg output.bmp
```

Decode one file as PNG:

```bash
python samsung_ifg_decoder.py input.ifg output.png
```

Decode a folder of `.ifg` and `.qmg` files:

```bash
python samsung_ifg_decoder.py input_folder output_folder
```

Decode a folder as PNG:

```bash
python samsung_ifg_decoder.py input_folder output_folder --format png
```

Decode a folder recursively:

```bash
python samsung_ifg_decoder.py input_folder output_folder --recursive
```

Write RGBA PNG when a supported alpha plane is present:

```bash
python samsung_ifg_decoder.py input.ifg output.png --with-alpha
```

Decode wallpapers and split `240x960` idle images into three `240x320` panels:

```bash
python samsung_ifg_decoder.py input_folder output_folder --recursive --split-240x320-panels
```

Write a CSV manifest:

```bash
python samsung_ifg_decoder.py input_folder output_folder --recursive --manifest decode_manifest.csv
```

Inspect headers without decoding:

```bash
python samsung_ifg_decoder.py input_folder --inspect --recursive --manifest inspect_manifest.csv
```

Analyze decode diagnostics without writing images:

```bash
python samsung_ifg_decoder.py input_folder --analyze --recursive --manifest analyze_manifest.csv
```

For A9LL QMG files, analysis also reports expected control, command, and raw stream limits, then warns when the current stream walk overruns a split point. The observed `use_extra_exception` A9LL branch is decoded and analyzed with its separate raw/delta decision bit path.

## What Files Do

- `samsung_ifg_decoder.py` is the decoder and command-line tool.
- `codec_tables.json` contains functional lookup tables used by the decoder.
- `docs/format-notes.md` documents what is currently known about the format.
- `samples/README.md` explains why firmware samples are not included.

## Example B5722 Wallpaper Result

B5722 firmware contains idle images such as:

- `Master/a/images/idle/idle_011.ifg`
- `Master/a/images/idle/idle_021.ifg`
- ...

These are `IFEG_65000001`, usually `240x960`. Use `--split-240x320-panels` to export phone-screen-sized panels.

## Example B5722 UI Assets

B5722 firmware also contains many `IFEG_95000100`, `IFEG_150001xx`, `IM_0x5D`, and `QM_0x0B` images, especially widget, menu, dialpad, and UI assets. These can appear as `.ifg` or `.qmg` files and can be decoded with the same commands:

```bash
python samsung_ifg_decoder.py input.ifg output.png
```

## Safety And Legal Notes

This repository does not include Samsung firmware, proprietary wallpapers, decoded assets, malware samples, original Samsung code, or third-party converter binaries.

Users must provide their own `.ifg` / `.qmg` files. This project is intended for preservation, interoperability, and personal recovery of legacy phone firmware assets.

## Roadmap

- Broaden `QM` / QMG version coverage and full animation frame export.
- Investigate `IM` alpha-plane variants.
- Add more automated tests with redistributable synthetic fixtures.
