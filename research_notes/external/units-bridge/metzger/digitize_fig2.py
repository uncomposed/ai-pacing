"""Re-digitize Fig. 2 of Metzger et al. (arXiv:1612.03238v1) from the figure's embedded raster.

Needs network (arxiv.org), poppler's `pdfimages`, numpy and Pillow. Not part of `make check`; the output
`fig2_digitized.json` is committed and the offline tests read it. Run from anywhere:

    python3 digitize_fig2.py                 # download the pinned PDF to a temporary directory
    python3 digitize_fig2.py --pdf v1.pdf    # use a local copy (its sha256 is still checked)

The PDF is not vendored: arXiv distributes it under its non-exclusive licence only.

Method. Page 12 holds Fig. 2 as an RGB image with a soft mask; the mask carries the drawing (white on black).
- Axis: the six rows that are white across the plot are the decade gridlines 1e5 (top) to 1 (bottom); log10(mass)
  is linear in the row index between them.
- Categories: seven generations equally spaced between the two vertical axis lines.
- Max case (solid squares, 16 x 16 px): in a 16-px column band at each category, the run of exactly 16 rows that
  are fully white. Robonaut triangles and connecting lines never fill all 16 columns for 16 rows.
- Reduced case (open squares, 17 x 17 px, 3-px border): a window whose border rows and columns are white, away
  from the solid square (connecting lines can fill the interior, so it is not tested).
  At Gen 1.0 both cases sit on the same point and the open square is hidden; the solid one is used for both.
Marker centre: top row + (size - 1) / 2.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile
import urllib.request

import numpy as np
from PIL import Image

URL = 'https://arxiv.org/pdf/1612.03238v1'
SHA256 = '637bd6111871f535a945a55539c4bb959ba8e23ea38dae2608896397e171bc62'
GENERATIONS = ['1.0', '2.0', '2.5', '3.0', '4.0', '5.0', '6.0']
OUT = Path(__file__).with_name('fig2_digitized.json')


def fetch(dest):
    with urllib.request.urlopen(URL, timeout=60) as r:
        dest.write_bytes(r.read())


def runs(mask):
    out, y = [], 0
    while y < len(mask):
        if mask[y]:
            y0 = y
            while y < len(mask) and mask[y]:
                y += 1
            out.append((y0, y - 1))
        y += 1
    return out


def digitize(mask):
    w = mask > 128
    grid = [y for y, n in enumerate(w.sum(1)) if n > 400]
    axes = [x for x, n in enumerate(w.sum(0)) if n > 300]
    assert len(grid) == 6 and len(axes) == 2, (grid, axes)
    top, bottom = grid[0], grid[-1]
    px_per_decade = (bottom - top) / 5
    x0, x1 = axes
    centres = [round(x0 + (k + 0.5) * (x1 - x0) / 7) for k in range(7)]
    solid, hollow = [], []
    for xc in centres:
        full = w[:, xc - 7:xc + 9].all(1)
        r16 = [r for r in runs(full) if r[1] - r[0] + 1 in (16, 17)]
        assert len(r16) == 1, (xc, runs(full))
        solid.append(r16[0][0] + 7.5)
        hits = []
        for y0 in range(top, bottom):
            b = w[y0:y0 + 17, xc - 7:xc + 10]
            if b.shape == (17, 17) and b[1:3].all() and b[14:16].all() and b[1:-1, :3].all() and b[1:-1, 14:].all() \
                    and abs(y0 + 8.0 - solid[-1]) > 4:      # a window inside the solid square also has white borders
                hits.append(y0 + 8.0)
        assert len(hits) <= 1, (xc, hits)
        hollow.append(hits[0] if hits else solid[-1])     # hidden under the solid square (Gen 1.0)
    value = lambda y: 10 ** ((bottom - y) / px_per_decade)
    return {
        'axis': {'gridline_rows': grid, 'decades_top_to_bottom': [1e5, 1e4, 1e3, 1e2, 1e1, 1.0],
                 'px_per_decade': px_per_decade, 'axis_columns': axes, 'category_columns': centres},
        'generations': GENERATIONS,
        'years': [2.0 * k for k in range(7)],
        'max': {'centre_rows': solid, 'mass_t': [value(y) for y in solid]},
        'reduced': {'centre_rows': hollow, 'mass_t': [value(y) for y in hollow],
                    'note': 'Gen 1.0 open marker hidden under the solid one; the solid centre is used.'},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', type=Path)
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        pdf = a.pdf or tmp / 'v1.pdf'
        if a.pdf is None:
            fetch(pdf)
        digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
        assert digest == SHA256, f'PDF sha256 {digest} is not the pinned {SHA256}'
        subprocess.run(['pdfimages', '-f', '12', '-l', '12', '-png', str(pdf), str(tmp / 'p12')], check=True)
        masks = sorted(p for p in tmp.glob('p12-*.png') if Image.open(p).size == (781, 477) and Image.open(p).mode == 'L')
        assert masks, 'Fig. 2 soft mask (781 x 477) not found on page 12'
        res = digitize(np.array(Image.open(masks[0])).astype(int))
    res['source'] = {'url': URL, 'sha256': SHA256, 'page': 12, 'image': 'soft mask of the first image on page 12, 781 x 477 px',
                     'record': 'EV-METZGER-2013', 'digitized': '2026-10-25'}
    res['uncertainty'] = {'per_point_px': 1.0, 'per_point_relative': 10 ** (1 / res['axis']['px_per_decade']) - 1,
                          'check': 'reduced Gen 6.0 against 156 t in the abstract'}
    OUT.write_text(json.dumps(res, indent=1) + '\n')
    for case in ('max', 'reduced'):
        print(case, [f'{m:.1f}' for m in res[case]['mass_t']])
    print('wrote', OUT)


if __name__ == '__main__':
    main()
