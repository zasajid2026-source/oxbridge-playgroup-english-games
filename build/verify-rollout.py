#!/usr/bin/env python3
"""Rollout verification (all letters unlocked + living characters):
- Desktop full playthroughs of letters B, F and S (stubbed voices),
  4 stars each, console clean. F's Science hero is the living fish —
  screenshot mid-swim.
- Partial drives (STEAM Science cell only) for C (living cat,
  screenshot mid-walk) and O (living owl, screenshot mid-flight),
  asserting the exact spoken performance lines.
- Mobile 390px full playthrough of F with the real VOICE toggle OFF.
Letter A regression is covered by build/verify-perform.py.
Starts its own static server on port 8903."""
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

URL = 'http://localhost:8903/'
STUB = """
window.__spoken = [];
const fakeVoices = [
  {name:'Microsoft David', lang:'en-US'},
  {name:'Microsoft Heera', lang:'en-IN'},
  {name:'Google UK English Female', lang:'en-GB'}
];
speechSynthesis.getVoices = () => fakeVoices;
try {
  const store = new WeakMap();
  Object.defineProperty(SpeechSynthesisUtterance.prototype, 'voice', {
    configurable: true,
    get(){ return store.get(this) || null; },
    set(v){ store.set(this, v); }
  });
} catch(e) {}
speechSynthesis.speak = (u) => {
  window.__spoken.push({text: u.text, voice: u.voice ? u.voice.name : null,
                        rate: u.rate, pitch: u.pitch});
  setTimeout(() => { if (u.onend) u.onend(); }, 30);
};
speechSynthesis.cancel = () => {};
"""


def badges_on(page):
    return page.evaluate("document.querySelectorAll('#badges .badge.on').length")


def prompted_target(page, scope):
    deadline = time.time() + 20
    while time.time() < deadline:
        word = page.evaluate("""(scope) => {
          const b = document.querySelector('#hostBubble').textContent;
          const m = b.match(/^Tap the (.+)!$/);
          if (!m) return null;
          const w = m[1].toLowerCase();
          const card = document.querySelector(scope + ' .wcard[data-word="' + w + '"]');
          return (card && !card.classList.contains('done')) ? w : null;
        }""", scope)
        if word:
            return word
        page.wait_for_timeout(150)
    raise AssertionError('no fresh Tap-the prompt appeared')


def wait_idle(page, timeout=30000):
    page.wait_for_function("""() => {
      const b = document.querySelector('#againBtn');
      if (b && !b.hidden) return true;
      const slot = document.querySelector('#perfSlot');
      return slot && !slot.firstElementChild;
    }""", timeout=timeout)


def drive_steam(page, max_cells=5, shots=None):
    """shots: {(cell_i, hero_idx): (delay_ms, path)} — screenshot while
    that hero's performance is running."""
    shots = shots or {}
    page.wait_for_selector('#badges')
    for cell_i in range(max_cells):
        deadline = time.time() + 150
        while time.time() < deadline:
            if badges_on(page) > cell_i or page.query_selector('.finishmsg'):
                break
            hero = page.query_selector('.perfhero:not(.done)')
            if hero:
                wait_idle(page)
                idx = hero.get_attribute('data-perf')
                hero.click()
                shot = shots.get((cell_i, int(idx)))
                if shot:
                    page.wait_for_timeout(shot[0])
                    page.screenshot(path=shot[1])
                page.wait_for_function(
                    "i => document.querySelector('.perfhero[data-perf=\"' + i + '\"]')"
                    ".classList.contains('done')", arg=idx, timeout=90000)
                continue
            if page.query_selector('.obspic:not(.perfhero)'):
                for c in page.query_selector_all('.obspic:not(.perfhero)'):
                    c.click(); page.wait_for_timeout(80)
            elif page.query_selector('#btap'):
                for k in range(4):
                    b = page.query_selector('#btap')
                    if not b:
                        break
                    b.click(); page.wait_for_timeout(220)
            elif page.query_selector('.swatch'):
                sw = page.query_selector_all('.swatch')
                sw[0].click(); page.wait_for_timeout(250)
                sw[2].click(); page.wait_for_timeout(250)
            elif page.query_selector('.ssort'):
                for size in ('3', '2', '1'):
                    page.click(f'.ssort[data-size="{size}"]')
                    page.wait_for_timeout(120)
            elif page.query_selector('.scount, .sc3'):
                for c in page.query_selector_all('.scount, .sc3'):
                    c.click(); page.wait_for_timeout(220)
            elif page.query_selector('.patile'):
                for c in ('k', 'w', 'k', 'w'):
                    page.click(f'.patile[data-c="{c}"]')
                    page.wait_for_timeout(220)
            elif page.query_selector('#steamPlay .wcard[data-word]'):
                target = prompted_target(page, '#steamPlay')
                page.click(f'#steamPlay .wcard[data-word="{target}"]')
                page.wait_for_timeout(200)
            else:
                page.wait_for_timeout(250)
        else:
            raise AssertionError(f'STEAM cell {cell_i} did not complete')


def open_and_play(page, letter):
    idx = ord(letter) - 97
    tiles = page.query_selector_all('.tile.ready')
    assert len(tiles) == 26, f'expected 26 ready tiles, got {len(tiles)}'
    tiles[idx].click()
    page.wait_for_selector('#btnPlay')
    page.click('#btnPlay')
    page.wait_for_selector('#bigLetter.pulse')
    page.click('#bigLetter', force=True)
    page.wait_for_selector('.wcard[data-word]')
    for _ in range(3):
        target = prompted_target(page, '#stage')
        page.click(f'.wcard[data-word="{target}"]')
        page.wait_for_timeout(200)
    page.wait_for_selector('.ccard')
    for c in page.query_selector_all('.ccard'):
        c.click()
        page.wait_for_timeout(120)


def play_through(page, letter, shots=None):
    open_and_play(page, letter)
    drive_steam(page, shots=shots)
    page.wait_for_selector('.finishmsg', timeout=30000)
    stars = page.evaluate("document.querySelectorAll('#starBar .st.on').length")
    assert stars == 4, f'{letter}: expected 4 stars, got {stars}'
    return page.text_content('.finishmsg')


def science_only(page, letter, shots, expect_line):
    open_and_play(page, letter)
    drive_steam(page, max_cells=1, shots=shots)
    assert badges_on(page) >= 1, f'{letter}: Science badge did not fill'
    texts = [s['text'] for s in page.evaluate('window.__spoken')]
    assert expect_line in texts, f'{letter}: missing spoken line {expect_line!r}'
    print(f'  {letter.upper()} Science OK — heard: {expect_line}')


def main():
    server = subprocess.Popen(
        [sys.executable, '-m', 'http.server', '8903'],
        cwd='/home/hatch/workspace/oxbridge/playgroup-games',
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={'width': 1280, 'height': 800})
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.add_init_script(STUB)
            page.goto(URL)
            page.wait_for_selector('.tile.ready')

            for letter in ('b', 'f', 's'):
                shots = {(0, 0): (1500, 'verify/shot-live-fish.png')} if letter == 'f' else None
                msg = play_through(page, letter, shots=shots)
                print(f'DESKTOP {letter.upper()} finish:', msg)
                page.click('#btnHome2')
                page.wait_for_selector('.tile.ready')

            texts = [s['text'] for s in page.evaluate('window.__spoken')]
            assert 'Look! The fish is swimming!' in texts, 'fish line missing'
            print('  fish line OK')

            science_only(page, 'c', {(0, 0): (1700, 'verify/shot-live-cat.png')},
                         'Look! The cat is walking!')
            page.click('#btnHome')
            page.wait_for_selector('.tile.ready')
            science_only(page, 'o', {(0, 0): (1500, 'verify/shot-live-owl.png')},
                         'Look! The owl is flying!')
            page.close()

            # mobile, voice OFF via the real toggle — letter F in full
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            page.on('console', lambda m: errors.append('[mobile] ' + m.text) if m.type == 'error' else None)
            page.on('pageerror', lambda e: errors.append('[mobile] ' + str(e)))
            page.goto(URL)
            page.wait_for_selector('.tile.ready')
            page.click('#tglVoice')
            msg = play_through(page, 'f')
            print('MOBILE (voice off) F finish:', msg)
            page.close()
            browser.close()
    finally:
        server.terminate()
    print('console errors:', errors if errors else 'NONE')
    assert not errors, errors
    print('VERIFY OK')


if __name__ == '__main__':
    main()
