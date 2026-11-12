# Inspiration sources and how to browse them

Every source below was opened with `playwright-cli` on 2026-11-12. "Loads" means it showed designs without a login. The ones under "Needs the patchright fallback" blocked `playwright-cli` that day. Search them anyway: their result pages are often the best references for an app type.

How to use a source:
- **Search**: run the `site:` query with WebSearch. Fill `<app type>` with what the app is (for example "invoicing dashboard", "habit tracker mobile app") and `<page>` with the app page (for example "settings", "onboarding"). Also add a mood word from the user's answers (for example "minimal", "playful", "dark"). Searching first gives direct links to single designs, so you avoid scrolling infinite feeds.
- **Full-size image**: open the design's own page (not the feed) and read `meta[property="og:image"]` with `playwright-cli eval "document.querySelector('meta[property=\"og:image\"]')?.content"`. That is usually the largest still the site serves. When it is missing or is a generic site banner, screenshot the main image element or the visible page instead.
- **Credit**: record the designer or studio name exactly as the page shows it, plus the URL of the design's own page. The shortlist links every card to it.

## Load in playwright-cli

| Source | Good for | Search query | Notes |
|---|---|---|---|
| Dribbble | App screens, dashboards, mobile UI, components, single shots | `site:dribbble.com/shots <app type> <page> <mood>` | `https://dribbble.com/search/<term>` also loads without login (110 images on 2026-11-12). Shots are often concept work, not shipped products. Prefer them for visual style, not for flows. |
| Awwwards | Award-winning marketing sites, bold layouts, motion | `site:awwwards.com/sites <app type> <mood>` | Feed at `https://www.awwwards.com/websites/`. Each site page has a large screenshot and the studio credit. A cookie banner can cover the bottom of the screenshot. |
| One Page Love | Landing pages and one-page sites, clean type | `site:onepagelove.com <app type> <mood>` | Each entry page has `og:image` with the full screenshot. |
| Recent.design (formerly Godly) | Hand-picked current web design, interfaces, branding, motion | `site:recent.design <app type> <mood>` | `godly.website` redirects here. Tabs: Websites, Interface, App Screenshots. Images open the original site; credit the site's maker. |
| Collect UI | Single UI patterns by category (login, settings, pricing, 404, empty state) | `site:collectui.com <page>` | Curates Dribbble shots by pattern. Credit the Dribbble designer and link the Dribbble shot when the page names one. |
| SaaS Landing Page | SaaS marketing pages, pricing and feature sections | `site:saaslandingpage.com <app type>` | Shows real shipped products, so it suits "make it look like a real product". |
| Siteinspire | Restrained, typographic, editorial sites | `site:siteinspire.com <app type> <mood>` | Good for calm, content-first directions. |

## Need the patchright fallback

| Source | Good for | Search query | What happened in playwright-cli |
|---|---|---|---|
| Behance | Full case studies: many screens of one product, design systems | `site:behance.net/gallery <app type> <page>` | HTTP 400 (`net::ERR_HTTP_RESPONSE_CODE_FAILURE`), on search and on gallery pages. |
| Land-book | Landing pages and product sites, tagged by industry and style | `site:land-book.com <app type> <mood>` | Cloudflare "Performing security verification / Verify you are human". |
| Lapa Ninja | Landing pages by category, with designer credits | `site:lapa.ninja <app type>` | Cloudflare "Attention Required!" page. |

Dropped: Screenlane redirects to Pageflows (paid, Cloudflare challenge). Mobbin keeps its screens behind login and a paid plan.

## Browsing

Run `playwright-cli` from a scratch directory, never from the user's repo. It creates `.playwright-cli/` in the current directory. Use your own named session so parallel workers do not share a browser: `cd "$WORK" && playwright-cli -s=<source>-<page> open <url>`, then `goto`, `eval` and `screenshot --filename=<abs path>`. Close it when done (`playwright-cli -s=<name> close`).

**Recognize a block.** After each `goto`, run `playwright-cli -s=S eval "location.href + ' | ' + document.title + ' | ' + document.images.length"`. The page is blocked when any of these is true:
- the title is "Just a moment...", "Attention Required!" or "Access denied";
- the text says "Verify you are human" or "Performing security verification";
- `location.href` is `chrome-error://chromewebdata/`, or `goto` reports `ERR_HTTP_RESPONSE_CODE_FAILURE` or a 403;
- the body is nearly empty, with 0 to 2 images where the site normally shows dozens.

A blocked page is not a candidate. Never screenshot a challenge page into the shortlist.

**Patchright fallback.** Patchright is a Playwright build that is harder for bot checks to spot. It runs on demand through `uv`, so nothing is installed for good. Save this snippet as `patchright_shot.py` in the scratch directory:

Verified on 2026-11-12 against Land-book's Cloudflare page: playwright-cli got the "Verify you are human" challenge, while this snippet loaded the real gallery (title "Landbook - website design inspiration gallery") and screenshotted it.

```python
import sys, tempfile
from patchright.sync_api import sync_playwright

url, out = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(tempfile.mkdtemp(), headless=False, no_viewport=True)
    page = ctx.new_page()
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(8000)  # give a challenge page time to clear on its own
    print(page.title())
    page.screenshot(path=out)
    ctx.close()
```

Run it with `uv run --with patchright python -I "$WORK/patchright_shot.py" "<url>" "$WORK/shots/<card id>.png"`. If it says the browser is missing, run `uv run --with patchright patchright install chromium` once. Patchright's own docs recommend a headed browser (`headless=False`) and a persistent context, so a window opens briefly. After it finishes, read the printed title and look at the screenshot. If it still shows a challenge, give up on that page and move on. Never click a captcha or "Verify you are human" box.

Claude Code's auto mode can refuse this command as bot-check circumvention. If it does, skip that page. Do not try another route around the refusal. Tell the user which sources were skipped, and that they can allow `uv run --with patchright` in their permission settings.

**Polite pacing.** Open one page at a time per worker, wait for it to load (a few seconds), and never retry a failed page in a loop. Try at most once with playwright-cli and once with patchright, then move on. Open only design pages you might use, not whole feeds. Stay signed out.
