# samsung-ifg-decoder

Open-source Samsung IFG / IFEG image decoder for legacy phone firmware assets.

This project decodes a subset of Samsung `.ifg` images used in older feature-phone firmware. The first release supports `IFEG` images with type `0x65000001`, including the wallpaper/idle images found in Samsung B5722 firmware.

## Status

Supported:

- `IFEG` magic: `49 46 45 47`
- Type: `0x65000001`
- Output: 24-bit `.bmp`
- Single-file decode
- Folder/batch decode
- Optional split of `240x960` idle wallpapers into `240x320` panels

Not supported yet:

- `IFEG_95000100`
- `IFEG_15000100` / `IFEG_150001xx`
- `IM`
- `QM` / QMG
- Encoding BMP/JPG back to IFG
- PNG output

## Requirements

- Python 3.10 or newer
- No third-party Python packages

## Usage

Decode one file:

```bash
python samsung_ifg_decoder.py input.ifg output.bmp
```

Decode a folder:

```bash
python samsung_ifg_decoder.py input_folder output_folder
```

Decode a folder recursively:

```bash
python samsung_ifg_decoder.py input_folder output_folder --recursive
```

Decode wallpapers and split `240x960` idle images into three `240x320` panels:

```bash
python samsung_ifg_decoder.py input_folder output_folder --recursive --split-240x320-panels
```

Write a CSV manifest:

```bash
python samsung_ifg_decoder.py input_folder output_folder --recursive --manifest decode_manifest.csv
```

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

## Safety And Legal Notes

This repository does not include Samsung firmware, proprietary wallpapers, decoded assets, malware samples, original Samsung code, or third-party converter binaries.

Users must provide their own `.ifg` files. This project is intended for preservation, interoperability, and personal recovery of legacy phone firmware assets.

## Roadmap

- Add PNG output.
- Add support for `IFEG_95000100`.
- Add support for `IFEG_150001xx`.
- Add support for `IM`.
- Investigate `QM` / QMG handling.
- Add automated tests with redistributable synthetic fixtures.
