"""Render several harness views of one GLB in a single browser session (run under the shared lock).
python3 shots.py assets/car_sports.glb outprefix [views]  ; views: comma list of name:dist:h:yaw[:tx:ty:tz:fov]"""
import asyncio, sys
from playwright.async_api import async_playwright

DEFAULT = 'side:9:1.0:90,f34:8:1.1:35,r34:8:1.1:145,front:7:0.9:0,wheel:2.6:0.5:70:0:0.35:1.33:35'

async def main(glb, prefix, views, w=1280, h=720):
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        pg = await b.new_page(viewport={'width': w, 'height': h})
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        for v in views.split(','):
            f = v.split(':')
            q = f'glb={glb}&dist={f[1]}&h={f[2]}&yaw={f[3]}'
            if len(f) >= 7: q += f'&tx={f[4]}&ty={f[5]}&tz={f[6]}'
            if len(f) >= 8: q += f'&fov={f[7]}'
            await pg.goto('http://localhost:8765/experiment/drivein/preview/harness.html?' + q)
            await pg.wait_for_function('window.__ready === true', timeout=300000)
            await pg.wait_for_timeout(300)
            await pg.screenshot(path=f'{prefix}_{f[0]}.png')
        print(await pg.inner_text('#info'), errs[:3])
        await b.close()

if __name__ == '__main__':
    a = sys.argv
    asyncio.run(main(a[1], a[2], a[3] if len(a) > 3 else DEFAULT))
