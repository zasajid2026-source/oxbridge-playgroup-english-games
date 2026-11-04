#!/usr/bin/env python3
"""Add the `perf` performance map (build/perf-map.py) to every STEAM
observe cell in data.js, in place. Run after build-steam-data.py; that
script also applies the map itself, so a full data rebuild keeps it."""
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)

spec = importlib.util.spec_from_file_location(
    'perfmap', os.path.join(HERE, 'perf-map.py'))
perfmap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(perfmap)


def main():
    raw = open(os.path.join(SITE, 'data.js')).read()
    head, rest = raw.split('window.GAME_DATA = ', 1)
    data = json.loads(rest.rstrip().rstrip(';'))
    cnt = perfmap.apply_perf(data)
    new = head + 'window.GAME_DATA = ' + json.dumps(data, indent=1) + ';\n'
    open(os.path.join(SITE, 'data.js'), 'w').write(new)
    total = sum(cnt.values())
    print(f'perf heroes mapped: {total} across observe cells')
    for k in sorted(cnt):
        print(f'  {k:10s} {cnt[k]}')


if __name__ == '__main__':
    main()
