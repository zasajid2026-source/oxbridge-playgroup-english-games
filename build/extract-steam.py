#!/usr/bin/env python3
"""Extract every letter page's STEAM box (5 strand cells) from the book PDF.

Source: ~/workspace/oxbridge/books/kaggle-book-job/book-working.pdf
The STEAM strip sits at the bottom of each letter page: 5 columns
(Science, Technology, Engineering, Art, Mathematics), cell texts set in
ABeeZee 9pt at y 663-702pt on the 657x846pt page.

The book justifies some words with letter-tracking, which the text layer
stores as single letters separated by spaces ("b u s", "p a t h w ay s").
This script de-spaces those runs with dictionary word-segmentation so the
game gets clean, speakable sentences.

Corrected-edition texts are then substituted from the Kaggle patch spec
(~/workspace/oxbridge/books/kaggle-book-job/patch-spec.json): the 10
steam_cell ops (old -> new) plus the p04 full-stop append. Every
substitution is asserted against the extracted printed text first.

Output: build/steam.json  {letter: [{strand, text}, x5]}
"""
import json, os, re, sys
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
PDF = '/home/hatch/workspace/oxbridge/books/kaggle-book-job/book-working.pdf'
SPEC = '/home/hatch/workspace/oxbridge/books/kaggle-book-job/patch-spec.json'
STRANDS = ['Science', 'Technology', 'Engineering', 'Art', 'Mathematics']
LETTER_PAGE = {'a': 2, 'b': 3, 'c': 4, 'd': 6, 'e': 7, 'f': 8, 'g': 10, 'h': 11,
               'i': 12, 'j': 14, 'k': 15, 'l': 16, 'm': 18, 'n': 19, 'o': 20,
               'p': 22, 'q': 23, 'r': 24, 's': 26, 't': 27, 'u': 28, 'v': 30,
               'w': 31, 'x': 32, 'y': 34, 'z': 35}

# ---------------------------------------------------------------- dictionary
# Vocabulary of the 130 STEAM cells + common function words. Used ONLY to
# re-segment letter-tracked runs; untracked words are never touched.
DICT = set('''a an the and or of to in on it is are as at by for with from into through
we our us its their this that these those how what when where who
observe notice explore identify compare count draw colour decorate design create
sort make makes made help helps used use using grow grows growing collect
identify visible carefully creatively differently safely
school bus transportation wheels buses ball rolls bounces round shape cat soft
fur movement baking cakes layers stacked birthday cake dog duck drum produces
sound structure simple patterns toy eyes see things examine strong curved eggs
eagle egg sizes fish live water aquariums provide homes holds bright tropical
fruits size goats eat grapes farmers pathways walking easier fences keep farm
animals safe beautiful hat horse hen ice freezers cold containers liquids cone
cubes jelly jeep transport vehicle pieces king kettle appliance key fits lock
royal crown lions lizards picking fresh lemons rocks support heavy yellow plant
moon different animal movements rocky surfaces shapes monkey mouse birds build
nests net useful catching twigs nest nuts placed near tree owl ostrich differ
legs onion onions shown scene pandas parrots like perch supports pear panda
feathers quail stitching quilt fabric join patchwork pattern rocket travels sky
remote controls robot parts robots rockets sun gives light warmth eating spoon
tomatoes healthy plants trunk branches tiger rain outdoor wet umbrella protects
opens closes sections vegetables van carries people goods vase decorative flows
stream watch time bicycle mountain ray shows bones inside body machines doctors
xylophone bars sounds alternating stripe stripes zebra black white unique zip
bag interlocking teeth work together yoyo going up down string yacht across
changes heated melts becomes warm hens move tools care stitching layers visible
spoon spoons sections stripes axe ant red yak bat have hard wood shiny tool
grown-ups look touch basket stack stones tower path little'''.split())
DICT |= {'x', 'i'}

# Manual text repairs, keyed (letter, strand) — used only if segmentation
# cannot fully resolve a cell (filled in after inspection).
TEXT_OVERRIDES = {}


def strip_punct(tok):
    return tok.strip('.,;:!?').lower()


def is_word(tok):
    return strip_punct(tok) in DICT


def is_fragment(tok):
    """Single letters and short non-word scraps belong to a tracked run."""
    t = strip_punct(tok)
    if len(t) <= 1:
        return True
    return len(t) <= 3 and t not in DICT


def segment(blob):
    """Split a spaceless blob into dictionary words (fewest words, then
    longest words preferred). Returns list or None if not fully coverable."""
    n = len(blob)
    best = [None] * (n + 1)
    best[0] = []
    for i in range(n):
        if best[i] is None:
            continue
        for j in range(i + 1, n + 1):
            w = blob[i:j]
            if w in DICT:
                cand = best[i] + [w]
                cur = best[j]
                if cur is None or (len(cand), -sum(len(x) ** 2 for x in cand)) < \
                        (len(cur), -sum(len(x) ** 2 for x in cur)):
                    best[j] = cand
    return best[n]


def cleanup(raw):
    # hyphen-fragments join with the next token: 'X-' + 'ray' -> 'X-ray'
    toks = raw.split()
    merged = []
    for t in toks:
        if merged and merged[-1].endswith('-'):
            merged[-1] += t
        else:
            merged.append(t)
    out = []
    i = 0
    while i < len(merged):
        if is_fragment(merged[i]):
            j = i
            run = []
            while j < len(merged) and is_fragment(merged[j]):
                run.append(merged[j])
                j += 1
            blob = ''.join(strip_punct(t) for t in run)
            words = segment(blob)
            if words is None:
                return None, blob
            # preserve a trailing punctuation mark from the last run token
            tail = ''
            m = re.search(r'([.,;:!?])$', run[-1])
            if m:
                tail = m.group(1)
            words[-1] += tail
            out.extend(words)
            i = j
        else:
            out.append(merged[i])
            i += 1
    txt = ' '.join(out)
    txt = txt[0].upper() + txt[1:] if txt else txt
    return txt, None


def col_of(x0):
    if x0 < 177:
        return 0
    if x0 < 279:
        return 1
    if x0 < 381:
        return 2
    if x0 < 482:
        return 3
    return 4


def extract(doc, pno):
    page = doc[pno - 1]
    cols = {i: [] for i in range(5)}
    d = page.get_text('dict')
    for block in d['blocks']:
        if block['type'] != 0:
            continue
        for line in block['lines']:
            spans = [s for s in line['spans']
                     if s['font'].startswith('ABeeZee') and 660 < s['bbox'][1] < 705]
            if not spans:
                continue
            y = round(spans[0]['bbox'][1], 1)
            for s in spans:
                cols[col_of(s['bbox'][0])].append((y, round(s['bbox'][0], 1), s['text']))
    cells = []
    for i in range(5):
        # group by line (y), join spans in x order, lines in y order
        lines = {}
        for y, x, t in cols[i]:
            lines.setdefault(y, []).append((x, t))
        parts = [''.join(t for _, t in sorted(v)) for _, v in sorted(lines.items())]
        raw = re.sub(r'\s+', ' ', ' '.join(parts)).strip()
        cells.append(raw)
    return cells


def norm(t):
    return re.sub(r'[^a-z0-9]', '', t.lower())


def main():
    doc = pymupdf.open(PDF)
    spec = json.load(open(SPEC))
    steam_ops = {}
    for op in spec['ops']:
        if op['type'] == 'steam_cell':
            strand = STRANDS[{78: 0, 180: 1, 281: 2}[op['cell_x']]]
            page_letter = [L for L, p in LETTER_PAGE.items() if p == op['page']][0]
            steam_ops[(page_letter, strand)] = op

    result, problems = {}, []
    for letter, pno in LETTER_PAGE.items():
        raws = extract(doc, pno)
        cells = []
        for si, strand in enumerate(STRANDS):
            raw = raws[si]
            txt, bad = cleanup(raw)
            key = (letter, strand)
            if txt is None:
                if key in TEXT_OVERRIDES:
                    txt = TEXT_OVERRIDES[key]
                else:
                    problems.append(f'{letter}-{strand}: UNRESOLVED blob {bad!r} from {raw!r}')
                    txt = raw
            # corrected-edition substitution
            if key in steam_ops:
                op = steam_ops[key]
                if norm(txt) != norm(op['old']):
                    problems.append(f'{letter}-{strand}: printed mismatch\n'
                                    f'  extracted {txt!r}\n  spec old  {op["old"]!r}')
                else:
                    txt = op['new']
            if key == ('c', 'Art'):
                # p04-fullstop: corrected edition adds the missing full stop
                if not txt.endswith('.'):
                    txt += '.'
            cells.append({'strand': strand, 'text': txt})
        result[letter] = cells

    for letter in LETTER_PAGE:
        for c in result[letter]:
            print(letter.upper(), c['strand'][:4], '|', c['text'])
    if problems:
        print('\nPROBLEMS:')
        for p in problems:
            print(' ', p)
        sys.exit(1)
    json.dump(result, open(os.path.join(HERE, 'steam.json'), 'w'), indent=1)
    print('\nOK — wrote build/steam.json (26 letters x 5 cells)')


if __name__ == '__main__':
    main()
