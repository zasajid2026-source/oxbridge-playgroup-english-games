"""Perform-archetype map for STEAM *observe* cells.

Owner's order (2026-11-04): when a STEAM activity asks the child to
OBSERVE a process, the game must PERFORM it — tap the ant and it walks
in its natural way; tap the apple and the growth of an apple tree is
shown stage by stage.

Every observe cell gets a `perf` list (one entry per hero picture):
  img     word name from the letter's own words (book picture, untouched)
  page    True for the whole book-page thumbnail cells
  do      the performance archetype:
    walk     crop walks across the stage, pauses, turns, walks back
    hop      crop hops in little arcs
    swim     crop swims across with a sine drift (+ bubbles)
    fly      crop flies across the top of the stage
    rise     crop rises up with a sparkle trail, floats back down
    roll     crop rolls across (circle-masked; variant 'bounce' arcs)
    spin     crop spins round in place (circle-masked)
    glow     crop shines: brightness pulses + halo
    melt     crop melts down into a puddle (variant 'wobble': jelly
             squash-and-stretch, then back to shape)
    flow     crop drifts like flowing water (variant 'rain': rain
             falls over the static book page instead)
    wave     sound rings expand from the crop (variant 'steam': puffs
             of steam rise from the crop)
    updown   crop bounces up and down (yo-yo, string shown)
    attract  small clips slide in toward the crop (engine-ready; no
             current cell uses it)
    grow-tree / grow-plant
             flat-diagram growth sequence, stage by stage, ending with
             the book's own fruit picture (fruit: apple|grapes|tomato)
    look     fallback — the old observe behaviour (big picture, tap,
             tick): used where the printed cell is a look/notice/
             identify beat rather than an observable process
  say     optional spoken line override during the performance
  variant / fruit: archetype parameters

apply_perf(data) mutates the parsed GAME_DATA dict in place and returns
a Counter of archetypes used (counted per hero).
"""

PERF = {
    # A Science is the owner's own pair of examples: the ant walks, and
    # the apple's growth is performed stage by stage.
    ('a', 'Science'): [
        {'img': 'ant', 'do': 'walk',
         'say': 'Look! The ant is walking! Ants have six little legs.'},
        {'img': 'apple', 'do': 'grow-tree', 'fruit': 'apple'},
    ],
    ('a', 'Technology'): [{'img': 'axe', 'do': 'look'}],
    ('b', 'Science'): [
        {'img': 'ball', 'do': 'roll', 'variant': 'bounce',
         'say': 'Look! The ball rolls and bounces!'}],
    ('c', 'Science'): [{'img': 'cat', 'do': 'walk'}],
    ('d', 'Science'): [{'img': 'dog', 'do': 'walk'},
                       {'img': 'duck', 'do': 'swim'}],
    ('d', 'Engineering'): [{'img': 'drum', 'do': 'roll'}],
    ('e', 'Science'): [{'img': 'eye', 'do': 'look'}],
    ('e', 'Technology'): [{'img': 'egg', 'do': 'look'}],
    ('e', 'Engineering'): [{'img': 'egg', 'do': 'look'}],
    ('f', 'Science'): [{'img': 'fish', 'do': 'swim'}],
    ('f', 'Engineering'): [{'img': 'fish', 'do': 'look'}],
    ('g', 'Science'): [{'img': 'goat', 'do': 'walk'},
                       {'img': 'grapes', 'do': 'grow-plant',
                        'fruit': 'grapes'}],
    ('h', 'Science'): [{'img': 'horse', 'do': 'walk'},
                       {'img': 'hen', 'do': 'hop'}],
    ('h', 'Engineering'): [{'img': 'horse', 'do': 'look'},
                           {'img': 'hen', 'do': 'look'}],
    ('i', 'Science'): [
        {'img': 'ice', 'do': 'melt', 'say': 'Look! The ice is melting!'}],
    ('i', 'Engineering'): [{'page': True, 'do': 'look'}],
    ('j', 'Science'): [
        {'img': 'jelly', 'do': 'melt', 'variant': 'wobble',
         'say': 'Look! The jelly wobbles! Wobble, wobble!'}],
    ('k', 'Science'): [
        {'img': 'kettle', 'do': 'wave', 'variant': 'steam',
         'say': 'Look! Hot steam goes up! We watch. We do not touch.'}],
    ('l', 'Science'): [{'img': 'lion', 'do': 'walk'},
                       {'img': 'lizard', 'do': 'walk'}],
    ('m', 'Science'): [
        {'img': 'moon', 'do': 'glow',
         'say': 'Look! The moon shines in the night sky!'}],
    ('n', 'Science'): [{'img': 'nest', 'do': 'look'}],
    ('o', 'Science'): [{'img': 'owl', 'do': 'fly'},
                       {'img': 'ostrich', 'do': 'walk'}],
    ('o', 'Engineering'): [
        {'img': 'ostrich', 'do': 'walk',
         'say': 'Look at the strong legs! Walking, walking!'}],
    ('p', 'Science'): [{'img': 'panda', 'do': 'walk'},
                       {'img': 'parrot', 'do': 'fly'}],
    ('p', 'Engineering'): [{'img': 'parrot', 'do': 'look'}],
    ('q', 'Science'): [{'img': 'quail', 'do': 'fly'}],
    ('r', 'Science'): [
        {'img': 'rocket', 'do': 'rise',
         'say': 'Look! The rocket goes up, up, up!'}],
    ('r', 'Engineering'): [{'img': 'robot', 'do': 'look'},
                           {'img': 'rocket', 'do': 'look'}],
    ('s', 'Science'): [
        {'img': 'sun', 'do': 'glow',
         'say': 'Look! The sun shines! It gives us light and warmth.'}],
    ('s', 'Engineering'): [{'img': 'spoon', 'do': 'look'}],
    ('t', 'Science'): [{'img': 'tomato', 'do': 'grow-plant',
                        'fruit': 'tomato'}],
    ('t', 'Engineering'): [{'img': 'tree', 'do': 'look'}],
    ('u', 'Science'): [
        {'page': True, 'do': 'flow', 'variant': 'rain',
         'say': 'Look! Rain is falling! Everything gets wet.'}],
    ('u', 'Engineering'): [{'img': 'umbrella', 'do': 'look'}],
    ('v', 'Science'): [{'img': 'vegetables', 'do': 'look'}],
    ('w', 'Science'): [
        {'img': 'water', 'do': 'flow',
         'say': 'Look! The water flows and flows!'}],
    ('w', 'Mathematics'): [
        {'img': 'watch', 'do': 'look'},
        {'img': 'wheel', 'do': 'spin',
         'say': 'Look! The wheel goes round and round!'}],
    ('x', 'Science'): [
        {'img': 'x-ray', 'do': 'glow',
         'say': 'Look! The special photo shows our bones!'}],
    ('x', 'Technology'): [{'img': 'x-ray', 'do': 'glow'}],
    ('x', 'Engineering'): [
        {'img': 'xylophone', 'do': 'wave',
         'say': 'Listen! Ting, ting! The xylophone makes music!'}],
    ('y', 'Science'): [
        {'img': 'yo-yo', 'do': 'updown',
         'say': 'Look! The yo-yo goes up and down!'}],
    ('y', 'Technology'): [
        {'page': True, 'do': 'swim',
         'say': 'Look! The yacht sails on the water!'}],
    ('y', 'Engineering'): [
        {'img': 'yo-yo', 'do': 'updown',
         'say': 'Up and down! The string holds the yo-yo!'}],
    ('z', 'Science'): [{'img': 'zebra', 'do': 'walk'}],
    ('z', 'Engineering'): [{'img': 'zip', 'do': 'look'}],
}


def apply_perf(data):
    """Add `perf` to every observe cell of the parsed GAME_DATA dict.
    Asserts every mapped hero resolves to one of the letter's own word
    pictures (or the page thumbnail), so a data typo fails loudly."""
    from collections import Counter
    cnt = Counter()
    seen = set()
    for L in data['letters']:
        words = {w['word'] for w in L['words']}
        for cell in L.get('steam', []):
            if cell.get('play') != 'observe':
                continue
            key = (L['letter'], cell['strand'])
            assert key in PERF, f'no perf mapping for observe cell {key}'
            perf = PERF[key]
            for p in perf:
                if p.get('page'):
                    assert cell.get('page'), \
                        f'{key}: page perf on non-page cell'
                else:
                    assert p['img'] in words, \
                        f"{key}: hero {p['img']!r} not in {L['letter']} words"
                cnt[p['do']] += 1
            cell['perf'] = perf
            seen.add(key)
    missing = set(PERF) - seen
    assert not missing, f'perf mappings with no observe cell: {missing}'
    return cnt
