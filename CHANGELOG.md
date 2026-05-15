# Changelog

## 0.17.0

- Decode observed A9LL `use_extra_exception` QMG streams.
- Treat extra-exception clear-mask pixels as control-bit raw/delta decisions, with command `7` decoded through the extended delta table.
- Update `--analyze` to walk the extra-exception A9LL path instead of reporting false stream overruns for supported files.

## 0.16.0

- Report A9LL control, command, and raw stream split limits.
- Mark A9LL analysis as `warning` when the current stream walk overruns any expected split point.
- Add manifest fields for split-limit bits, raw limit offset, bytes available before the raw limit, and overrun counts.

## 0.15.0

- Add `--analyze` mode for decode diagnostics without writing image output.
- Report decode status, stream walk status, tile counts, A9LL bit/raw consumption, and W2 stream size summaries.
- Keep decode failures separate from stream-analysis failures for easier reverse engineering of unsupported QMG variants.

## 0.14.0

- Add GitHub Actions CI for Python 3.10, 3.11, and 3.12.
- Run source compilation, unit tests, and CLI version smoke checks on push and pull request.
- Add a README CI badge for public release confidence.

## 0.13.0

- Add `--inspect` mode to print IFG/QMG/IM header and stream metadata without decoding.
- Report QMG raw type, flags, header size, codec mode, alpha split point, and stream offsets.
- Allow metadata-only inspection of observed `QM_0x0B` raw type `0x00` files while keeping decode support disabled for that raw type.

## 0.12.0

- Add a stdlib `unittest` regression suite with synthetic decoder fixtures.
- Cover the W2 odd-pixel tail behavior for raw groups and table runs.
- Cover alpha sample unpacking, RGB565 conversion, and MSB-first bit reading.

## 0.11.0

- Fix W2 depth-1 decoding for odd pixel counts.
- Decode the observed horizontal QMG zoom-bar asset that ends with a single 16-bit tail pixel.
- Document W2's 32-bit output grouping and odd-tail handling.

## 0.10.0

- Decode observed `QM_0x0B_A9LL` animation keyframes as still images.
- Decode observed A9LL alpha streams with alpha-depth flag `1` or `2`.
- Document the observed QM animation header fields and first-frame support limit.

## 0.9.0

- Include `.qmg` files in folder and recursive batch decoding.
- Keep single-file `.qmg` decoding on the same QM path as `.ifg`.
- Avoid batch output collisions when same-stem files with different input extensions are decoded together.

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
