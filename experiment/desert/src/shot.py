"""Screenshot an asset in the preview harness (scene lighting). Run under the shared lock:
flock /tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad/heavy.lock \
  python3 shot.py 'glb=assets/sportscar.glb&dist=7&h=1.2&yaw=35' out.png [width height]
"""
import asyncio, sys
from playwright.async_api import async_playwright

async def main(query, out, w=1600, h=900):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': w, 'height': h})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda c: errs.append(c.text) if c.type == 'error' else None)
        await pg.goto('http://localhost:8765/experiment/desert/preview/harness.html?' + query)
        await pg.wait_for_function('window.__ready === true', timeout=300000)
        await pg.wait_for_timeout(500)
        await pg.screenshot(path=out, timeout=300000)
        print(await pg.inner_text('#info'), errs[:3])
        await b.close()

if __name__ == '__main__':
    a = sys.argv
    asyncio.run(main(a[1], a[2], int(a[3]) if len(a) > 3 else 1600, int(a[4]) if len(a) > 4 else 900))
