#!/usr/bin/env python3
"""Play-verify letter-a-video.html: book-page stage, hotspot rings on the
right pictures, guided flow A→ant→apple→axe with stubbed TTS (fake
en-IN female 'Heera' voice, picker must choose her, rate 0.82/pitch 1.05)
and stubbed media playback (records src, fires 'ended' after 1.1 s).
Asserts prompt order, per-tap video files, wrong-tap correction, finish
state, free-play replay, console clean. Starts its own server on 8904."""
import subprocess, sys, time, os
from playwright.sync_api import sync_playwright

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8904
URL = f'http://localhost:{PORT}/letter-a-video.html'
VER = os.path.join(SITE, 'verify')
os.makedirs(VER, exist_ok=True)

STUB = """
window.__spoken = [];
window.__mediaLog = [];
const fakeVoices = [
  { name: 'Google US English', lang: 'en-US', default: true, localService: false, voiceURI: 'g' },
  { name: 'Microsoft Zira - English (United States)', lang: 'en-US', default: false, localService: true, voiceURI: 'z' },
  { name: 'Microsoft Heera - English (India)', lang: 'en-IN', default: false, localService: true, voiceURI: 'h' }
];
/* Fake utterance class: the page sets u.voice to a getVoices() entry, and
   assigning a plain object to a REAL utterance's voice throws (WebIDL).
   A JS-class utterance accepts the fake voice as a plain property. */
class FakeUtterance {
  constructor(text){ this.text = text; this.voice = null; this.rate = 1; this.pitch = 1;
                     this.volume = 1; this.lang = ''; this.onend = null; this.onerror = null; }
}
window.SpeechSynthesisUtterance = FakeUtterance;
try {
  Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: {
    getVoices: () => fakeVoices,
    speak(u){ window.__spoken.push({ text: u.text, voice: u.voice ? u.voice.name : null, rate: u.rate, pitch: u.pitch });
      setTimeout(() => { try { u.onend && u.onend(); } catch(e){} }, 120); },
    cancel(){}, pause(){}, resume(){},
    speaking: false, pending: false, paused: false,
    addEventListener(){}, removeEventListener(){}
  }});
} catch(e) { window.__stubErr = String(e); }
HTMLMediaElement.prototype.play = function(){
  const el = this;
  window.__mediaLog.push(el.getAttribute('src') || el.src);
  setTimeout(() => { try { el.dispatchEvent(new Event('ended')); } catch(e){} }, 1100);
  return Promise.resolve();
};
HTMLMediaElement.prototype.pause = function(){};
"""

fails = []
def check(name, ok, extra=''):
    print(('PASS' if ok else 'FAIL'), '-', name, extra)
    if not ok: fails.append(name)

def state(page):
    return page.evaluate("window.FLOW.state()")

def wait_idle(page, timeout=20000):
    page.wait_for_function(
        "() => { const s = window.FLOW.state(); return !s.busy && !s.videoOpen && !s.voiceBusy && s.voiceQueued === 0; }",
        timeout=timeout)

def spoken(page):
    return page.evaluate("window.__spoken.map(s => s.text)")

def tap_and_verify_video(page, hid, fname):
    page.click(f'.hot[data-id="{hid}"]')
    page.wait_for_function("window.FLOW.state().videoOpen === true", timeout=8000)
    # currentSrc lags one resource-selection behind the src attribute;
    # poll until the media element settles on the expected file.
    try:
        page.wait_for_function(
            f"window.FLOW.state().vidCur.endsWith('/{fname}')", timeout=5000)
        ok, cur = True, state(page)['vidCur']
    except Exception:
        ok, cur = False, state(page)['vidCur']
    check(f'tap {hid} opens {fname}', ok, f"(cur={cur})")
    return state(page)

def main():
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT), '--bind', '127.0.0.1'],
                           cwd=SITE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.0)
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
            ctx = browser.new_context(viewport={'width': 390, 'height': 844},
                                      device_scale_factor=2, has_touch=True, is_mobile=True)
            page = ctx.new_page()
            errors = []
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            page.on('pageerror', lambda e: errors.append(str(e)))
            page.add_init_script(STUB)
            page.goto(URL)
            page.wait_for_function("document.querySelector('#pageImg').naturalWidth > 0", timeout=15000)
            page.wait_for_timeout(600)

            stub_ok = page.evaluate("Array.isArray(window.__spoken) && window.speechSynthesis.getVoices().length === 3")
            check('TTS stub active', stub_ok)

            st = state(page)
            check('initial: guided, target a', st['mode'] == 'guided' and st['target'] == 'a', str(st))

            # hotspot geometry vs expected % of pagewrap
            geo = page.evaluate("""() => {
              const w = document.querySelector('#pagewrap').getBoundingClientRect();
              const out = {};
              document.querySelectorAll('.hot').forEach(h => {
                const r = h.getBoundingClientRect();
                out[h.dataset.id] = { l: (r.left - w.left) / w.width * 100, t: (r.top - w.top) / w.height * 100,
                                      wd: r.width / w.width * 100, ht: r.height / w.height * 100 };
              });
              return out;
            }""")
            exp = {'a': (8, 5, 30, 21), 'axe': (2, 30, 28, 20), 'apple': (22, 47, 25, 20), 'ant': (46, 54, 21, 14)}
            for k, (l, t, wd, ht) in exp.items():
                g = geo[k]
                ok = all(abs(g[a] - b) < 1.6 for a, b in zip(('l', 't', 'wd', 'ht'), (l, t, wd, ht)))
                check(f'hotspot {k} geometry', ok, str({kk: round(vv, 1) for kk, vv in g.items()}))

            page.screenshot(path=f'{VER}/shot-video-ring-a.png')

            # intro speech on first touch (tap the hint line, not a hotspot)
            page.click('.hint')
            page.wait_for_function("window.__spoken.length >= 1", timeout=8000)
            wait_idle(page)
            sp = page.evaluate("window.__spoken")
            check('intro line spoken', sp[0]['text'] == 'This is your book page! Touch A!', str(sp[0]))
            check('picker chose en-IN female Heera', sp[0]['voice'] and 'Heera' in sp[0]['voice'], str(sp[0]['voice']))
            check('rate 0.82 / pitch 1.05', abs(sp[0]['rate'] - 0.82) < 0.001 and abs(sp[0]['pitch'] - 1.05) < 0.001,
                  f"rate={sp[0]['rate']} pitch={sp[0]['pitch']}")

            # wrong tap: apple while target is A
            page.click('.hot[data-id="apple"]')
            page.wait_for_function("window.__spoken.length >= 2", timeout=8000)
            wait_idle(page)
            sp = spoken(page)
            check('wrong tap correction line', sp[-1] == "That's the apple! Touch A!", sp[-1])
            st = state(page)
            check('wrong tap: no advance, no video', st['idx'] == 0 and not st['videoOpen']
                  and page.evaluate("window.__mediaLog.length") == 0, str(st))

            PRAISE = {'Well done!', 'Great job!', 'Wonderful!', 'Super!', 'Very good!', 'You did it!'}

            # A
            tap_and_verify_video(page, 'a', 'video-a.mp4')
            page.wait_for_function("window.__spoken.some(s => s.text === 'A! A says ah! I am A!')", timeout=8000)
            check('A open-line spoken over jingle', True)
            wait_idle(page)
            sp = spoken(page)
            check('after A: praise then ant prompt', sp[-1] == 'Now touch the ant!' and sp[-2] in PRAISE, str(sp[-2:]))
            page.screenshot(path=f'{VER}/shot-video-ring-ant.png')

            # ant (screenshot overlay while its video is open)
            page.click('.hot[data-id="ant"]')
            page.wait_for_function("window.FLOW.state().videoOpen === true", timeout=8000)
            try:
                page.wait_for_function(
                    "window.FLOW.state().vidCur.endsWith('/video-ant.mp4')", timeout=5000)
                ant_ok, ant_cur = True, state(page)['vidCur']
            except Exception:
                ant_ok, ant_cur = False, state(page)['vidCur']
            check('tap ant opens video-ant.mp4', ant_ok, ant_cur)
            page.wait_for_timeout(250)
            page.screenshot(path=f'{VER}/shot-video-overlay.png')
            wait_idle(page)
            sp = spoken(page)
            check('after ant: praise then apple prompt', sp[-1] == 'Now touch the apple!' and sp[-2] in PRAISE, str(sp[-2:]))
            page.screenshot(path=f'{VER}/shot-video-ring-apple.png')

            # apple
            tap_and_verify_video(page, 'apple', 'video-apple.mp4')
            wait_idle(page)
            sp = spoken(page)
            check('after apple: praise then axe prompt', sp[-1] == 'Now touch the axe!' and sp[-2] in PRAISE, str(sp[-2:]))
            page.screenshot(path=f'{VER}/shot-video-ring-axe.png')

            # axe -> finish
            tap_and_verify_video(page, 'axe', 'video-axe.mp4')
            page.wait_for_function("window.FLOW.state().mode === 'free'", timeout=10000)
            wait_idle(page)
            sp = spoken(page)
            check('finish line spoken', 'You did it! A, ant, apple, axe!' in sp, str(sp[-1]))
            st = state(page)
            check('finish state: 4 done', sorted(st['done']) == ['a', 'ant', 'apple', 'axe'], str(st['done']))
            nstars = page.evaluate("document.querySelectorAll('#starBar .st.on').length")
            check('4 stars lit', nstars == 4, str(nstars))
            check('watch-again button visible', page.is_visible('#watchBtn'))
            page.wait_for_timeout(500)
            page.screenshot(path=f'{VER}/shot-video-finish.png')

            # free play: tap ant again replays its video
            page.click('.hot[data-id="ant"]')
            page.wait_for_function("window.FLOW.state().videoOpen === true", timeout=8000)
            try:
                page.wait_for_function(
                    "window.FLOW.state().vidCur.endsWith('/video-ant.mp4')", timeout=5000)
                fp_ok, fp_cur = True, state(page)['vidCur']
            except Exception:
                fp_ok, fp_cur = False, state(page)['vidCur']
            check('free play replays video-ant.mp4', fp_ok, fp_cur)
            wait_idle(page)
            st = state(page)
            check('free play stays free', st['mode'] == 'free', str(st['mode']))

            media = page.evaluate("window.__mediaLog")
            print('MEDIA LOG:', media)
            print('SPOKEN TRANSCRIPT:')
            for i, t in enumerate(spoken(page)): print(f'  {i+1}. {t}')
            check('media log order', media == ['videos/video-a.mp4', 'videos/video-ant.mp4',
                                               'videos/video-apple.mp4', 'videos/video-axe.mp4',
                                               'videos/video-ant.mp4'], str(media))
            ctx.close()

            # desktop pass
            ctx2 = browser.new_context(viewport={'width': 1280, 'height': 800})
            p2 = ctx2.new_page()
            p2.on('console', lambda m: errors.append('[desktop] ' + m.text) if m.type == 'error' else None)
            p2.on('pageerror', lambda e: errors.append('[desktop] ' + str(e)))
            p2.add_init_script(STUB)
            p2.goto(URL)
            p2.wait_for_function("document.querySelector('#pageImg').naturalWidth > 0", timeout=15000)
            p2.wait_for_timeout(500)
            st = p2.evaluate("window.FLOW.state()")
            check('desktop: guided, target a', st['mode'] == 'guided' and st['target'] == 'a', str(st))
            p2.screenshot(path=f'{VER}/shot-video-desktop.png')
            ctx2.close()
            browser.close()

            check('console clean', not errors, '; '.join(errors[:4]))
    finally:
        srv.terminate()
    print('\nRESULT:', 'ALL PASS' if not fails else f'FAILURES: {fails}')
    return 1 if fails else 0

if __name__ == '__main__':
    sys.exit(main())
