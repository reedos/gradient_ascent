// Build first. ASTRA_PLAYWRIGHT names an existing Playwright installation.
// ASTRA_URL must point to the throwaway local preview, never a live data service.
const { chromium } = require(process.env.ASTRA_PLAYWRIGHT || 'playwright');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const dist = path.join(root, 'site/dist');
const out = path.join(root, 'work/astra-screens');
const base = process.env.ASTRA_URL;
if (!base || !/^http:\/\/127\.0\.0\.1:49(?:[2-8]\d\d|900)\/gradient_ascent\/$/.test(base)) {
  throw new Error('ASTRA_URL must be a loopback preview on a sprint port');
}
const routes = fs.readdirSync(dist, { recursive: true }).filter(p => p.endsWith('index.html'))
  .map(p => p.replaceAll('\\', '/').replace(/index\.html$/, ''))
  .filter(p => !p.startsWith('pilot/')).sort();
const shots = new Set(['', 'techniques/rag/', 'techniques/agentic-rag/', 'learn/', 'timeline/', 'map/', 'worksheet/']);
(async () => {
  fs.mkdirSync(out, {recursive: true});
  const browser = await chromium.launch({ headless: true });
  const results = [];
  try {
    const context = await browser.newContext();
    // Never send analytics or any mutation from the local preview.
    await context.route('**/*', route => {
      const req = route.request();
      if (req.method() !== 'GET' || /cloudflareinsights|gc\.zgo\.at/.test(req.url())) return route.abort();
      return route.continue();
    });
    const page = await context.newPage();
    let errors = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('requestfailed', r => { if (r.url().startsWith(base)) errors.push(`${r.url().slice(base.length)}: ${r.failure()?.errorText}`); });
    page.on('response', r => { if (r.url().startsWith(base) && r.status() >= 400) errors.push(`${r.url().slice(base.length)}: HTTP ${r.status()}`); });
    for (const width of [360, 390, 430, 1440]) {
      await page.setViewportSize({width, height: 900});
      for (const route of routes) {
        errors = [];
        let response = await page.goto(base + route, {waitUntil: 'networkidle'});
        const refresh = await page.evaluate(() => document.querySelector('meta[http-equiv="refresh"]')?.getAttribute('content'));
        if (refresh) {
          const target = new URL(refresh.split(/url=/i)[1], base);
          if (!target.href.startsWith(base)) throw new Error('Unexpected external redirect');
          response = await page.goto(target.href, {waitUntil: 'networkidle'});
        }
        await page.evaluate(() => document.fonts.ready);
        const layout = await page.evaluate(() => {
          const width = document.documentElement.clientWidth;
          return {
            width, scrollWidth: document.documentElement.scrollWidth,
            overflow: [...document.querySelectorAll('main *')].filter(el => {
              const r = el.getBoundingClientRect();
              if (r.width === 0 || getComputedStyle(el).position === 'absolute') return false;
              let parent = el.parentElement;
              while (parent && parent !== document.body) {
                if (['auto', 'scroll', 'hidden', 'clip'].includes(getComputedStyle(parent).overflowX)) return false;
                parent = parent.parentElement;
              }
              return r.right > width + 1 || r.left < -1;
            }).slice(0, 12).map(el => ({tag: el.tagName, cls: el.className, text: el.textContent.slice(0, 90)})),
            accent: getComputedStyle(document.documentElement).getPropertyValue('--accent').trim(),
          };
        });
        const row = {route, width, status: response.status(), ...layout, errors: [...errors]};
        results.push(row);
        if (shots.has(route)) await page.screenshot({path: path.join(out, `${route.replaceAll('/', '-') || 'home'}-${width}.png`), fullPage: false});
      }
      console.log(`Finished ${routes.length} routes at ${width}px`);
      fs.writeFileSync(path.join(out, 'sweep.json'), JSON.stringify(results, null, 2));
    }
  } finally { await browser.close(); }
  const failures = results.filter(r => r.status !== 200 || r.scrollWidth > r.width + 1 || r.errors.length || r.accent !== '#e6ba82');
  console.log(JSON.stringify({checks:results.length, failures}, null, 2));
  process.exitCode = failures.length ? 1 : 0;
})().catch(e => { console.error(e); process.exitCode = 1; });
