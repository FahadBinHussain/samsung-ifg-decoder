# Changelog

## 0.4.0

- Add support for the `IFEG_150001xx` three-stream 16-bit family.
- Validate the new path against the local Samsung B5722 `IFEG_150001xx` corpus.
- Update README, format notes, and codec table notes.

## 0.3.0

- Add support for `IFEG_95000100` three-stream 16-bit images.
- Validate the new path against the local Samsung B5722 `IFEG_95000100` corpus.
- Update codec table notes and format documentation.

## 0.2.0

- Add PNG output for single-file decoding.
- Add `--format png` for folder/batch decoding.
- Split wallpaper panels now use the selected output extension.

## 0.1.0

- Initial public release scaffold.
- Decode Samsung `IFEG_65000001` images to BMP.
- Batch folder decoding.
- Optional recursive decoding.
- Optional `240x960` to `240x320` wallpaper panel splitting.
- CSV manifest output.
