# Changelog

## 0.8.0

- Decode observed `QM_0x0B_W2` alpha planes with `--with-alpha`.
- Reuse the W2 depth-1/depth-2 decompressor for packed alpha samples.
- Document the W2 alpha stream offset and packed alpha output layout.

## 0.7.0

- Add opt-in `--with-alpha` PNG output.
- Decode observed `QM_0x0B_A9LL` alpha planes as RGBA PNG.
- Leave unsupported alpha planes opaque during batch alpha export instead of failing the whole run.

## 0.6.0

- Add support for observed Samsung B5722 `QM_0x0B` images.
- Decode the A9LL stream variant used by TouchWiz widget and missed-event icons.
- Decode the W2 depth-2 stream variant used by softkey/background assets.
- Update README and format notes with the recovered `QM` header and stream layout.

## 0.5.0

- Add support for observed non-alpha `IM_0x5D` images from Samsung B5722 firmware.
- Decode both standard and `0x20` near-lossless/raw-flag `IM_0x5D` stream variants.
- Update README and format notes with the recovered `IM` header and stream layout.

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
