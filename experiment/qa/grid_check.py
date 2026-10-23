"""Grid and billboard guard check (see ../GUARDRAILS.md). Light: no landing render, ~1 min.
Run from the repo root with a local server:  python3 -m http.server 8765 &  python3 experiment/qa/grid_check.py
Checks, at 1x and 2x pixel density and several window shapes, on both the main site and /experiment:
  1. the grid canvas shows at exactly the window size (the Retina crooked-grid bug)
  2. the bird's-eye camera is centred (x = 0, no drag yaw/pitch)
  3. on /experiment, the intro slide is exactly the billboard face size (1180 x 462) wherever the desert is on
Exit code 1 on any failure."""
import asyncio, re, sys
from playwright.async_api import async_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765'
SIZES = [(1000, 524, 2), (1728, 1117, 2), (1440, 900, 1), (1920, 1080, 1), (2560, 1080, 1), (390, 844, 3)]
async def main():
    bad = []
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        for page in ['/', '/experiment/']:
            for w, h, d in SIZES:
                mob = w < 700
                ctx = await b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=d, is_mobile=mob, has_touch=mob)
                pg = await ctx.new_page()
                await pg.route(re.compile('radio-browser|somafm|srg-ssr|streamguys|vimeo|desert/assets|desert/tex|drivein/assets|drivein/tex'), lambda r: r.abort())
                await pg.goto(BASE + page); await pg.wait_for_timeout(4000)
                r = await pg.evaluate("""() => { const c = document.querySelector('#gl').getBoundingClientRect(), hero = document.querySelector('.card[data-id="hero"]'), work = document.querySelector('.card[data-id="work"]');
                  return { cw: c.width, ch: c.height, w: innerWidth, h: innerHeight, camX: window.__wmp ? Math.round(window.__wmp.camPos().x) : null,
                    look: window.__wmp ? window.__wmp.look : null, desert: document.documentElement.classList.contains('desert-on'),
                    hw: hero && hero.offsetWidth, hh: hero && hero.offsetHeight, ww: work && work.offsetWidth, wh: work && work.offsetHeight }; }""")
                tag = f'{page} {w}x{h}@{d}x'
                if abs(r['cw'] - r['w']) > 1 or abs(r['ch'] - r['h']) > 1: bad.append(f"{tag}: canvas {r['cw']}x{r['ch']} != window {r['w']}x{r['h']}")
                if r['camX'] not in (0, None) or (r['look'] and (r['look']['yaw'] or r['look']['pitch'])): bad.append(f"{tag}: bird's-eye not centred {r['camX']} {r['look']}")
                if page == '/experiment/' and r['desert'] and (abs(r['hw'] - 1180) > 2 or abs(r['hh'] - 462) > 2): bad.append(f"{tag}: intro slide {r['hw']}x{r['hh']}, billboard face is 1180x462")
                if page == '/experiment/' and r['desert'] and (abs(r['ww'] - 1120) > 2 or abs(r['wh'] - 645) > 2): bad.append(f"{tag}: work slide {r['ww']}x{r['wh']}, drive-in screen is 1120x645")
                print('ok ' if not any(x.startswith(tag) for x in bad) else 'BAD', tag, flush=True)
                await ctx.close()
        await b.close()
    print('\n'.join(bad) or 'all checks passed'); sys.exit(1 if bad else 0)
asyncio.run(main())
