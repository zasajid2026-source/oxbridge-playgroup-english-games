#!/usr/bin/env python3
"""Extract word-picture crops + page thumbnails from the book PDF.

Crops are EXACTLY as printed (plain square crops of the page render,
no filters / re-styling) so children recognise the same pictures in the
physical book. Spec lives in crops.json:
  {"b-bus": {"page": 3, "cx": 495, "cy": 231, "size": 720, "dx": 0, "dy": 0}, ...}
cx/cy are normalised 0-1000 points on the full page render (from visual
grounding); size is the square side in px at 200 dpi; dx/dy are px nudges.
Scene rects (pt) come from ../explore/labels.json.
"""
import json, os, sys
import pymupdf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
PDF = '/home/hatch/workspace/oxbridge/books/kaggle-book-job/book-working.pdf'
SCALE = 200 / 72.0

def main():
    spec = json.load(open(os.path.join(HERE, 'crops.json')))
    labels = json.load(open(os.path.join(SITE, 'explore', 'labels.json')))
    scene_pt = {v['page']: v['scene'] for v in labels.values()}
    only = sys.argv[1].split(',') if len(sys.argv) > 1 else None
    doc = pymupdf.open(PDF)
    by_page = {}
    for name, s in spec.items():
        if only and name not in only and not any(name.startswith(o) for o in only):
            continue
        by_page.setdefault(s['page'], []).append((name, s))
    for pno, items in sorted(by_page.items()):
        pix = doc[pno - 1].get_pixmap(dpi=200)
        tmp = f'/tmp/render-p{pno}.png'
        pix.save(tmp)
        img = Image.open(tmp).convert('RGB')
        W, H = img.size
        sc = scene_pt[pno]
        sx0, sy0, sx1, sy1 = [v * SCALE for v in sc]
        for name, s in items:
            size = s['size']
            cx = s['cx'] / 1000 * W + s.get('dx', 0)
            cy = s['cy'] / 1000 * H + s.get('dy', 0)
            x0 = int(max(sx0, min(cx - size / 2, sx1 - size)))
            y0 = int(max(sy0, min(cy - size / 2, sy1 - size)))
            out = os.path.join(SITE, 'img', name + '.webp')
            img.crop((x0, y0, x0 + size, y0 + size)).save(out, 'WEBP', quality=82)
            print('crop', name, (x0, y0, size), os.path.getsize(out))
        letter = [k for k, v in labels.items() if v['page'] == pno][0]
        thumb = img.copy()
        thumb.thumbnail((760, 1200))
        tout = os.path.join(SITE, 'img', f'page-{letter}.webp')
        thumb.save(tout, 'WEBP', quality=80)
        print('thumb', letter, thumb.size, os.path.getsize(tout))
        img.close()
        os.remove(tmp)

if __name__ == '__main__':
    main()
