#!/usr/bin/env python3
"""Enrich build/steam.json cells with a tap-play template and write the
result into data.js as a `steam` array on every letter.

Play templates (each completable in 1-4 taps, no timer, praise per cell):
  observe — host speaks the printed line; the page's own pictures are shown
            big; the child taps each one ("I see it!")
  tap     — "Tap the X!" among the page's word cards (1 or more targets)
  count   — tap 3 copies of one word picture, counting aloud
  count3  — tap each of the page's 3 different word pictures, counting aloud
  sort    — the 3 word pictures at big/medium/small sizes; tap biggest first
  colour  — tap a colour swatch to colour the word picture's frame (2 taps)
  build   — tap to stack 4 blocks (or path stones); the word picture lands
            on top
  pattern — repeat the black-white-black-white stripe pattern (Z maths)

Derivation is rule-based from the (corrected) printed text, with a small
OVERRIDES table for cells whose object is not named in the text.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)


def nrm(s):
    return re.sub(r'\s+', ' ', s.lower().replace('-', ' ')).strip()


def mentioned(text, words):
    """Words whose name/plural appears in the text, in text order."""
    t = ' ' + nrm(text) + ' '
    hits = []
    for w in words:
        best = None
        for form in {nrm(w['word']), nrm(w['plural']), nrm(w['say'])}:
            m = re.search(r'\b' + re.escape(form) + r'\b', t)
            if m and (best is None or len(form) > best[1]):
                best = (m.start(), len(form))
        if best:
            hits.append((best[0], -best[1], w))
    return [w for _, _, w in sorted(hits, key=lambda h: (h[0], h[1], h[2]['word']))]


# (letter, strand) -> fields merged over the rule-derived play object
OVERRIDES = {
    ('a', 'Technology'): {'play': 'observe', 'imgs': ['axe']},
    ('e', 'Technology'): {'play': 'observe', 'imgs': ['egg']},
    ('k', 'Science'):    {'play': 'observe', 'imgs': ['kettle']},
    ('x', 'Technology'): {'play': 'observe', 'imgs': ['x-ray']},
    ('l', 'Technology'): {'play': 'count', 'word': 'lemon'},
    ('o', 'Technology'): {'play': 'tap', 'target': 'owl'},
    ('p', 'Technology'): {'play': 'tap', 'target': 'pear'},
    ('s', 'Technology'): {'play': 'tap', 'target': 'spoon'},
    ('t', 'Technology'): {'play': 'tap', 'target': 'tomato'},
    ('f', 'Engineering'): {'play': 'observe', 'imgs': ['fish']},
    ('h', 'Engineering'): {'play': 'observe', 'imgs': ['horse', 'hen']},
    ('o', 'Engineering'): {'play': 'observe', 'imgs': ['ostrich']},
    ('k', 'Art'):        {'play': 'colour', 'img': 'king'},
    ('w', 'Art'):        {'play': 'colour', 'img': 'page'},
    ('d', 'Mathematics'): {'play': 'count3'},
    ('q', 'Mathematics'): {'play': 'count', 'word': 'quilt', 'label': 'shapes'},
    ('z', 'Mathematics'): {'play': 'pattern'},
    ('y', 'Science'):    {'play': 'observe', 'imgs': ['yo-yo']},
    ('y', 'Engineering'): {'play': 'observe', 'imgs': ['yo-yo']},
    ('y', 'Art'):        {'play': 'colour', 'img': 'yo-yo'},
    ('w', 'Mathematics'): {'play': 'observe', 'imgs': ['watch', 'wheel']},
    ('c', 'Mathematics'): {'label': 'layers'},
}

# keys kept per play type (everything else is stripped after merging)
PLAY_KEYS = {
    'observe': ('imgs', 'page'),
    'tap': ('target',),
    'count': ('word', 'label'),
    'count3': (),
    'sort': (),
    'colour': ('img',),
    'build': ('img', 'variant'),
    'pattern': (),
}


def derive(letter, cell):
    L = letter
    text = cell['text']
    strand = cell['strand']
    men = mentioned(text, L['words'])
    first = men[0] if men else L['words'][0]
    p = {'play': 'observe'}
    if strand == 'Science':
        p = {'play': 'observe', 'imgs': [w['word'] for w in men] or None}
    elif strand == 'Technology':
        if men:
            p = {'play': 'tap', 'target': first['word']}
        else:
            p = {'play': 'observe', 'imgs': None}  # page picture fallback
    elif strand == 'Engineering':
        tl = text.lower()
        if ('block' in tl or 'stack' in tl or 'join to make' in tl
                or 'twigs make' in tl):
            p = {'play': 'build', 'img': first['word'],
                 'variant': 'path' if 'path' in tl else 'blocks'}
        elif men:
            # wheels / key / shape-of texts: tap the named object, or look
            if 'wheel' in tl or 'fits into' in tl:
                p = {'play': 'tap', 'target': first['word']}
            else:
                p = {'play': 'observe', 'imgs': [w['word'] for w in men]}
        else:
            p = {'play': 'observe', 'imgs': None}
    elif strand == 'Art':
        p = {'play': 'colour', 'img': first['word'] if men else 'page'}
    elif strand == 'Mathematics':
        tl = text.lower()
        if 'sort' in tl or ('compare' in tl and 'sizes' in tl):
            p = {'play': 'sort'}
        elif 'count' in tl:
            p = {'play': 'count', 'word': first['word']}
        elif men:
            p = {'play': 'tap', 'target': first['word']}
        else:
            p = {'play': 'observe', 'imgs': None}
    if p.get('imgs') is None and p['play'] == 'observe':
        p.pop('imgs', None)
        p['page'] = True
    p.update(OVERRIDES.get((L['letter'], strand), {}))
    keep = PLAY_KEYS[p['play']]
    p = {k: v for k, v in p.items() if k == 'play' or k in keep}
    if p['play'] == 'observe':
        if p.get('imgs'):
            p.pop('page', None)
        else:
            p.pop('imgs', None)
            p['page'] = True
    out = {'strand': strand, 'text': text}
    out.update(p)
    return out


def main():
    raw = open(os.path.join(SITE, 'data.js')).read()
    head, rest = raw.split('window.GAME_DATA = ', 1)
    data = json.loads(rest.rstrip().rstrip(';'))
    steam = json.load(open(os.path.join(HERE, 'steam.json')))
    by_letter = {L['letter']: L for L in data['letters']}
    for letter, cells in steam.items():
        L = by_letter[letter]
        L['steam'] = [derive(L, c) for c in cells]
    new = head + 'window.GAME_DATA = ' + json.dumps(data, indent=1) + ';\n'
    open(os.path.join(SITE, 'data.js'), 'w').write(new)
    # summary table for review
    from collections import Counter
    cnt = Counter()
    for L in data['letters']:
        for c in L['steam']:
            cnt[c['play']] += 1
            extra = {k: v for k, v in c.items()
                     if k not in ('strand', 'text', 'play')}
            print(f"{L['upper']} {c['strand'][:4]:5s} {c['play']:8s} {extra}")
    print('\nTemplate counts:', dict(cnt), 'total', sum(cnt.values()))


if __name__ == '__main__':
    main()
