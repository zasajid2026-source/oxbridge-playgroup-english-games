#!/usr/bin/env python3
"""Play-verify the STEAM Perform upgrade: full Letter A playthrough on
desktop (stubbed speechSynthesis, records spoken lines) driving the new
perform heroes one at a time — ant walk (screenshot mid-walk), apple
growth (screenshot at the big-tree stage), plus one Watch-again replay —
and a second full playthrough on a 390px mobile viewport with the real
VOICE toggle OFF (performances must still run and complete).
Starts its own static server on port 8902."""
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

URL = 'http://localhost:8902/'
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
    """A performance is running while the Watch-again button is hidden
    after at least one hero was tapped; idle = button visible, or the
    stage slot is still empty (nothing tapped yet in this cell)."""
    page.wait_for_function("""() => {
      const b = document.querySelector('#againBtn');
      if (b && !b.hidden) return true;
      const slot = document.querySelector('#perfSlot');
      return slot && !slot.firstElementChild;
    }""", timeout=timeout)


def drive_steam(page, shots=False):
    page.wait_for_selector('#badges')
    for cell_i in range(5):
        deadline = time.time() + 120
        replayed = False
        while time.time() < deadline:
            if badges_on(page) > cell_i or page.query_selector('.finishmsg'):
                break
            hero = page.query_selector('.perfhero:not(.done)')
            if hero:
                wait_idle(page)
                idx = hero.get_attribute('data-perf')
                hero.click()
                if shots and cell_i == 0 and idx == '0':
                    page.wait_for_timeout(1700)  # ant mid-walk
                    page.screenshot(path='verify/shot-perf-ant-walk.png')
                if shots and cell_i == 0 and idx == '1':
                    page.wait_for_function(
                        "() => document.querySelector('#perfLabel')"
                        ".textContent.includes('big tree')", timeout=20000)
                    page.wait_for_timeout(800)
                    page.screenshot(path='verify/shot-perf-apple-grow.png')
                page.wait_for_function(
                    "i => document.querySelector('.perfhero[data-perf=\"' + i + '\"]')"
                    ".classList.contains('done')", arg=idx, timeout=60000)
                # prove Watch-again replay once (desktop, ant only)
                if shots and cell_i == 0 and idx == '0' and not replayed:
                    replayed = True
                    page.click('#againBtn')
                    page.wait_for_timeout(1200)
                    assert page.query_selector('#perfSlot .actor'), 'replay actor missing'
                continue
            if page.query_selector('#btap'):
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
            else:
                page.wait_for_timeout(250)
        else:
            raise AssertionError(f'STEAM cell {cell_i} did not complete')
    page.wait_for_selector('.finishmsg', timeout=30000)


def play_through(page, shots=False):
    page.click('.tile.ready')
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
    drive_steam(page, shots=shots)
    stars = page.evaluate("document.querySelectorAll('#starBar .st.on').length")
    assert stars == 4, f'expected 4 stars, got {stars}'
    return page.text_content('.finishmsg')


def main():
    server = subprocess.Popen(
        [sys.executable, '-m', 'http.server', '8902'],
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
            msg = play_through(page, shots=True)
            print('DESKTOP finish:', msg)
            spoken = page.evaluate('window.__spoken')
            print('voice picked:', spoken[0]['voice'] if spoken else None,
                  '| rate:', spoken[0]['rate'] if spoken else None)
            for s in spoken:
                print('  SAY:', s['text'])
            need = ['Look! The ant is walking! Ants have six little legs.',
                    'A tiny seed in the soil.', 'Now it is a big tree!',
                    'Red apples grow on the tree!']
            texts = [s['text'] for s in spoken]
            for n in need:
                assert n in texts, f'missing spoken line: {n}'
            page.click('#btnHome2')
            page.close()
            # mobile, voice OFF via the real toggle
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            page.on('console', lambda m: errors.append('[mobile] ' + m.text) if m.type == 'error' else None)
            page.on('pageerror', lambda e: errors.append('[mobile] ' + str(e)))
            page.goto(URL)
            page.wait_for_selector('.tile.ready')
            page.click('#tglVoice')
            msg = play_through(page)
            print('MOBILE (voice off) finish:', msg)
            page.close()
            browser.close()
    finally:
        server.terminate()
    print('console errors:', errors if errors else 'NONE')
    assert not errors, errors
    print('VERIFY OK')


if __name__ == '__main__':
    main()
