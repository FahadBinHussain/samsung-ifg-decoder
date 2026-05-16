# Synthetic Samples

These fixtures are hand-built byte streams for public tests and demos. They are not copied from Samsung firmware, wallpapers, decoded assets, or third-party tools.

Each `.hex` file stores one tiny input file as hexadecimal text. Convert one to a binary file before passing it to the CLI:

```bash
python -c "from pathlib import Path; p=Path('samples/synthetic/qm_w2_odd_tail.hex'); h=''.join(line.split('#',1)[0] for line in p.read_text().splitlines()); Path('qm_w2_odd_tail.qmg').write_bytes(bytes.fromhex(h))"
python samsung_ifg_decoder.py qm_w2_odd_tail.qmg qm_w2_odd_tail.png
```

Included fixtures:

- `im_v5d_extended_near_lossless.hex`: minimal `IM_0x5D` file with near-lossless and extended-header flags.
- `qm_a9ll_rgb565_no_alpha.hex`: minimal raw type `0x00` A9LL QMG using the observed extra-exception branch.
- `qm_w2_odd_tail.hex`: minimal W2 depth-1 QMG with an odd pixel count.
