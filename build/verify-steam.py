#!/usr/bin/env python3
"""Play-verify the STEAM Play station: full Letter A playthrough with a
stubbed speechSynthesis (records every spoken line, fires onend fast),
on desktop; and a second full playthrough on a 390px mobile viewport
with the real VOICE toggle switched OFF (gates must release instantly).
Screenshots: STEAM build mid-stack + STEAM colour after first swatch."""
import json, sys, time
from playwright.sync_api import sync_playwright

URL = 'http://localhost:8901/'
STUB = """
window.__spoken = [];
const fakeVoices = [
  {name:'Microsoft David', lang:'en-US'},
  {name:'Microsoft Heera', lang:'en-IN'},
  {name:'Google UK English Female', lang:'en-GB'}
];
speechSynthesis.getVoices = () => fakeVoices;
try {
  // plain-object fake voices fail the native SpeechSynthesisVoice type
  // check on u.voice assignment; store the voice via a patched accessor
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


def prompted_target(page, scope):
    """Wait until the host bubble says 'Tap the X!' for a card not yet done
    in the given scope; return the target word."""
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


def play_through(page, shots=False):
    page.click('.tile.ready')
    page.wait_for_selector('#btnPlay')
    page.click('#btnPlay')
    page.wait_for_selector('#bigLetter.pulse')  # pulse = intro lines done, listener live
    page.click('#bigLetter', force=True)  # letter pulses forever; skip stability wait
    # Listen & Tap: follow the host's spoken prompts in the bubble
    page.wait_for_selector('.wcard[data-word]')
    for _ in range(3):
        target = prompted_target(page, '#stage')
        page.click(f'.wcard[data-word="{target}"]')
        page.wait_for_timeout(200)
    # Play & Count
    page.wait_for_selector('.ccard')
    for c in page.query_selector_all('.ccard'):
        c.click()
        page.wait_for_timeout(120)
    # STEAM Play: 5 cells, drive each template generically
    page.wait_for_selector('#badges')
    for cell_i in range(5):
        page.wait_for_function(
            "i => document.querySelectorAll('#badges .badge.on').length >= i",
            arg=cell_i)
        deadline = time.time() + 30
        shot_done = False
        while time.time() < deadline:
            # last cell's completion replaces #stage (badges) with the
            # finish screen, so .finishmsg also counts as "cell done"
            if page.evaluate("document.querySelectorAll('#badges .badge.on').length") > cell_i \
                    or page.query_selector('.finishmsg'):
                break
            if page.query_selector('.obspic'):
                for c in page.query_selector_all('.obspic'):
                    c.click(); page.wait_for_timeout(80)
            elif page.query_selector('.ssort'):
                for size in ('3', '2', '1'):
                    page.click(f'.ssort[data-size="{size}"]')
                    page.wait_for_timeout(120)
            elif page.query_selector('.scount') or page.query_selector('.sc3'):
                for c in page.query_selector_all('.scount, .sc3'):
                    c.click(); page.wait_for_timeout(220)
            elif page.query_selector('.swatch'):
                sw = page.query_selector_all('.swatch')
                sw[0].click(); page.wait_for_timeout(250)
                if shots and not shot_done:
                    page.screenshot(path='verify/shot-steam-colour.png')
                    shot_done = True
                sw[2].click(); page.wait_for_timeout(250)
            elif page.query_selector('#btap'):
                for k in range(4):
                    b = page.query_selector('#btap')
                    if not b:
                        break
                    b.click(); page.wait_for_timeout(220)
                    if shots and k == 1 and not shot_done:
                        page.screenshot(path='verify/shot-steam-build.png')
                        shot_done = True
            elif page.query_selector('.patile'):
                for c in ('k', 'w', 'k', 'w'):
                    page.click(f'.patile[data-c="{c}"]')
                    page.wait_for_timeout(220)
            elif page.query_selector('#steamPlay .wcard[data-word]'):
                target = prompted_target(page, '#steamPlay')
                page.click(f'#steamPlay .wcard[data-word="{target}"]')
                page.wait_for_timeout(200)
            else:
                page.wait_for_timeout(200)
        else:
            raise AssertionError(f'STEAM cell {cell_i} did not complete')
    page.wait_for_selector('.finishmsg')
    stars = page.evaluate("document.querySelectorAll('#starBar .st.on').length")
    assert stars == 4, f'expected 4 stars, got {stars}'
    return page.text_content('.finishmsg')


def main():
    errors = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        # ---- desktop, stubbed voice ----
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
        steam_lines = [s['text'] for s in spoken
                       if 'STEAM' in s['text'] or s['text'].endswith('!') and False]
        for s in spoken:
            print('  SAY:', s['text'])
        page.click('#btnHome2')
        page.close()
        # ---- mobile 390px, voice OFF via the real toggle ----
        page = browser.new_page(viewport={'width': 390, 'height': 844})
        page.on('console', lambda m: errors.append('[mobile] ' + m.text) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errors.append('[mobile] ' + str(e)))
        page.goto(URL)
        page.wait_for_selector('.tile.ready')
        page.click('#tglVoice')  # voice OFF -> gates release instantly
        msg = play_through(page)
        print('MOBILE (voice off) finish:', msg)
        page.close()
        browser.close()
    print('console errors:', errors if errors else 'NONE')
    assert not errors, errors
    print('VERIFY OK')


if __name__ == '__main__':
    main()
