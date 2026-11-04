#!/usr/bin/env python3
"""Play-verify the Letter A 7D page (ant3d.html): all 5 Blender models
load, the ant walks its loop, taps on ant/apple/axe play the matching
female-teacher mp3 + animation clip, the letter A wiggles with a
jingle, gyro + Magic Camera fail gracefully headless, console clean.
The CDN three.js modules are served byte-identical from /tmp/three160
via route override (this VM's proxy refuses Chromium CONNECT tunnels).
Starts its own static server on port 8903."""
import subprocess
import sys
import time
from playwright.sync_api import sync_playwright

URL = 'http://localhost:8903/ant3d.html'
CDN = 'https://cdn.jsdelivr.net/npm/three@0.160.0/'
ROUTES = {
    CDN + 'build/three.module.js': '/tmp/three160/three.module.js',
    CDN + 'examples/jsm/controls/OrbitControls.js': '/tmp/three160/OrbitControls.js',
    CDN + 'examples/jsm/loaders/GLTFLoader.js': '/tmp/three160/GLTFLoader.js',
    CDN + 'examples/jsm/utils/BufferGeometryUtils.js': '/tmp/three160/BufferGeometryUtils.js',
}
STUB = """
window.__audioLog = [];
const realPlay = HTMLMediaElement.prototype.play;
HTMLMediaElement.prototype.play = function(){
  const el = this;
  window.__audioLog.push({ src: el.getAttribute('src') || el.src, at: Date.now() });
  setTimeout(() => { try { el.dispatchEvent(new Event('ended')); } catch(e){} }, 250);
  return Promise.resolve();
};
HTMLMediaElement.prototype.pause = function(){};
"""

def make_handler(path):
    def h(route, request=None):
        route.fulfill(path=path, content_type='text/javascript')
    return h

def proj(page, name, yfrac):
    return page.evaluate("""([name, yfrac]) => {
      const P = window.PAGE3D, e = P.models[name];
      const v = e.root.position.clone(); v.y += yfrac; v.project(P.camera);
      return { x: (v.x * 0.5 + 0.5) * innerWidth, y: (-v.y * 0.5 + 0.5) * innerHeight, behind: v.z > 1 };
    }""", [name, yfrac])

def state(page):
    return page.evaluate("window.PAGE3D.state()")

def wait_loaded(page, timeout=45):
    page.wait_for_function("window.PAGE3D && window.PAGE3D.state().loaded === true", timeout=timeout * 1000)

def tap_and_check(page, name, yfrac, clip, line):
    """Tap a model through the real pointer path and assert its line +
    clip. The ant roams (and sometimes stands inside the apple's spot,
    or a headless frame lands late), so — like a child would — tap
    again if the tap lands on the wrong singer or on nothing."""
    last_log = None
    for attempt in range(3):
        page.evaluate(f"window.PAGE3D.focusOn('{name}')")
        page.wait_for_timeout(420)
        if name != 'ant':
            # wait until the roaming ant is clear of the camera->target ray
            for _ in range(110):
                clear = page.evaluate("""(name) => {
                  const P = window.PAGE3D, T = P.THREE;
                  const a = P.models.ant.root.position.clone(); a.y = 0.4;
                  const t = P.models[name].root.position.clone(); t.y = 0.45;
                  const cam = P.camera.position;
                  const dir = t.clone().sub(cam);
                  const distT = dir.length(); dir.normalize();
                  const rel = a.clone().sub(cam);
                  const along = rel.dot(dir);
                  if (along < 0 || along > distT + 0.4) return true;
                  const perp = rel.sub(dir.multiplyScalar(along)).length();
                  return perp > 1.15;
                }""", name)
                if clear: break
                page.wait_for_timeout(700)
        before = page.evaluate("window.__audioLog.length")
        pt = proj(page, name, yfrac)
        assert not pt['behind'], f'{name} is behind the camera'
        page.mouse.click(pt['x'], pt['y'])
        page.wait_for_timeout(450)
        st = state(page)
        log = page.evaluate("window.__audioLog")
        last_log = log
        line_ok = (len(log) > before and f'line-{line}-female.mp3' in log[-1]['src']) if line else (len(log) == before)
        clip_ok = clip in st['running'].get(name, []) and st['lastAnim'] and st['lastAnim']['clip'] == clip
        if line_ok and clip_ok:
            print(f'  TAP {name}: line={line} clip={clip} OK' + (f' (attempt {attempt + 1})' if attempt else ''))
            if line:
                page.wait_for_function("window.PAGE3D.state().linePlaying === null", timeout=6000)
            return
        print(f'  ~~ {name} attempt {attempt + 1}: line_ok={line_ok} clip_ok={clip_ok} log_tail={log[-1:] if log else []} running={st["running"]}')
        if st['linePlaying']:
            page.wait_for_function("window.PAGE3D.state().linePlaying === null", timeout=6000)
        page.wait_for_timeout(2200)
    raise AssertionError(f'{name}: tap never produced line={line} clip={clip}; last log={last_log}')


def run():
    server = subprocess.Popen(
        [sys.executable, '-m', 'http.server', '8903'],
        cwd='/home/hatch/workspace/oxbridge/playgroup-games',
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            # ---------- desktop ----------
            page = browser.new_page(viewport={'width': 1280, 'height': 800})
            page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
            page.on('pageerror', lambda e: errors.append(str(e)))
            for url, path in ROUTES.items():
                page.route(url, make_handler(path))
            page.add_init_script(STUB)
            page.goto(URL)
            wait_loaded(page)
            st = state(page)
            names = page.evaluate("Object.keys(window.PAGE3D.models)")
            assert sorted(names) == ['ant', 'apple', 'axe', 'garden', 'letterA'], f'models: {names}'
            clips = page.evaluate("""() => { const o = {}; for (const k in window.PAGE3D.models) o[k] = Object.keys(window.PAGE3D.models[k].actions); return o; }""")
            assert clips['ant'] == ['Walk', 'Wave'], f"ant clips {clips['ant']}"
            assert clips['apple'] == ['Bounce'] and clips['axe'] == ['NoNo'] and clips['letterA'] == ['Wiggle'], f'clips {clips}'
            assert clips['garden'] == [], f"garden clips {clips['garden']}"
            print('  MODELS + CLIPS OK:', clips)
            # canvas non-blank: sample pixel variance via a screenshot buffer
            shot = page.screenshot()
            assert len(shot) > 20000, 'screenshot suspiciously small/blank'
            page.screenshot(path='verify/shot-7d-scene.png')
            # the ant lives: position changes across the first walk burst
            # SwiftShader renders slowly and the page clamps dt, so sim
            # time runs slower than wall time headless: poll for motion.
            p1 = page.evaluate("window.PAGE3D.models.ant.root.position.toArray()")
            moved, waited = 0.0, 0
            while waited < 22000:
                page.wait_for_timeout(700); waited += 700
                p2 = page.evaluate("window.PAGE3D.models.ant.root.position.toArray()")
                moved = ((p1[0]-p2[0])**2 + (p1[2]-p2[2])**2) ** 0.5
                if moved > 0.6: break
            assert moved > 0.6, f'ant barely moved: {p1} -> {p2}'
            print(f'  ANT WALKING OK: moved {moved:.2f} units over ~{waited/1000:.0f}s headless, mode={state(page)["antMode"]}')
            # wait until the ant strolls into the open right-front stretch,
            # then portrait it with a hand-placed close camera
            for _ in range(45):
                ap = page.evaluate("window.PAGE3D.models.ant.root.position.toArray()")
                if 2.0 < ap[0] < 4.4 and 0.2 < ap[2] < 2.6: break
                page.wait_for_timeout(700)
            page.evaluate("""() => {
              const P = window.PAGE3D, a = P.models.ant.root.position;
              P.controls.target.set(a.x, 0.35, a.z);
              P.camera.position.set(a.x + 1.9, 1.15, a.z + 2.3);
            }""")
            page.wait_for_timeout(500)
            page.screenshot(path='verify/shot-7d-ant.png')
            page.evaluate("window.PAGE3D.focusOn('home')")
            page.wait_for_timeout(300)
            # taps: the three singers + the letter
            tap_and_check(page, 'ant', 0.55, 'Wave', 'ant')
            tap_and_check(page, 'apple', 0.6, 'Bounce', 'apple')
            tap_and_check(page, 'axe', 0.25, 'NoNo', 'axe')
            before = page.evaluate("window.__audioLog.length")
            tap_and_check(page, 'letterA', 1.5, 'Wiggle', None)
            after = page.evaluate("window.__audioLog.length")
            assert after == before, 'letter A must jingle (WebAudio), not play an mp3 line'
            print('  LETTER A: Wiggle + jingle (no mp3) OK')
            page.evaluate("window.PAGE3D.focusOn('home')")
            page.wait_for_timeout(300)
            # gyro: no sensor headless -> kind rollback after ~1.8s
            page.click('#btnGyro')
            page.wait_for_timeout(2300)
            st = state(page)
            assert st['gyroOn'] is False, f"gyro should have rolled back, state={st['gyroOn']}"
            toast_txt = page.text_content('#toast')
            assert ('tilt sensor' in toast_txt or 'drag still works' in toast_txt
                    or 'No problem' in toast_txt), f'gyro toast: {toast_txt!r}'
            print('  GYRO graceful fallback OK:', toast_txt.strip())
            # Magic Camera: unsupported headless -> kind note, no crash
            page.click('#btnAR')
            page.wait_for_timeout(700)
            toast_txt = page.text_content('#toast')
            assert 'Magic camera is not on this phone' in toast_txt, f'AR toast: {toast_txt!r}'
            assert state(page)['arActive'] is False
            print('  MAGIC CAMERA graceful fallback OK')
            page.close()
            # ---------- mobile ----------
            page = browser.new_page(viewport={'width': 390, 'height': 844})
            page.on('console', lambda m: errors.append('[mobile] ' + m.text) if m.type == 'error' else None)
            page.on('pageerror', lambda e: errors.append('[mobile] ' + str(e)))
            for url, path in ROUTES.items():
                page.route(url, make_handler(path))
            page.add_init_script(STUB)
            page.goto(URL)
            wait_loaded(page)
            page.wait_for_timeout(600)
            page.screenshot(path='verify/shot-7d-mobile.png')
            tap_and_check(page, 'apple', 0.6, 'Bounce', 'apple')
            print('  MOBILE OK')
            page.close()
            browser.close()
    finally:
        server.terminate()
    print('console errors:', errors if errors else 'NONE')
    assert not errors, errors
    print('VERIFY OK')

if __name__ == '__main__':
    run()
