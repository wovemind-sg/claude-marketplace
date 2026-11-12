# Inspiration sources and how to browse them

Every source below was opened with `playwright-cli` on 2026-11-12. The sources fall in two groups, and `SKILL.md` step 3 searches them in two separate passes:
- **Open sources** loaded in a normal browser without a login. The open pass searches only these, and it never tries to get past a block.
- **Gated sources** blocked the normal browser that day. Only the gated pass searches them, with the patchright fallback at the end of this file. Their result pages are often the best references for an app type, so they are worth a try when the user allows it.

How to use a source:
- **Suits**: each source is marked by the kind of app page it is good for: **in-app** (dashboards, tables, settings, other screens inside the product), **landing** (landing, marketing and pricing pages), or **both**. Search a source only for app pages it suits. Landing-page galleries return marketing sites, which are poor references for an in-app screen.
- **Search**: call WebSearch with the source's domain in `allowed_domains` and the query from the table. WebSearch ignores a `site:` prefix in the query and returns results from other sites, so the parameter is what restricts the search. Only with a search tool that has no domain parameter, put `site:<domain>` at the start of the query instead. Fill `<app type>` with what the app is (for example "invoicing dashboard", "habit tracker mobile app") and `<page>` with the app page (for example "settings", "onboarding"). Also add a mood word from the user's answers (for example "minimal", "playful", "dark"). Searching first gives direct links to single designs, so you avoid scrolling infinite feeds.
- **One design per candidate**: a candidate is one design's own page, showing that design and crediting its maker. Skip listing, category, tag and search-results pages, because the shortlist card links to the page and credits its maker, and a listing has neither one design nor one maker. When search only finds a listing, open it and follow it to a single design's page.
- **Full-size image**: open the design's own page (not the feed) and read `meta[property="og:image"]` with `playwright-cli eval "document.querySelector('meta[property=\"og:image\"]')?.content"`. That is usually the largest still the site serves. When it is missing or is a generic site banner, screenshot the main image element or the visible page instead (see "Screenshots" under Browsing).
- **Credit**: record the designer or studio name exactly as the page shows it, plus the URL of the design's own page. The shortlist links every card to it. On curated galleries of shipped products that name no designer (SaaS Landing Page, Siteinspire, often One Page Love), credit the product or company as the maker and name the gallery as the source site.

## Open sources

| Source | Suits | Good for | Domain | Query | Notes |
|---|---|---|---|---|---|
| Dribbble | in-app | App screens, dashboards, mobile UI, components, single shots | `dribbble.com` | `shots <app type> <page> <mood>` | Keep only `dribbble.com/shots/...` results. `https://dribbble.com/search/<term>` also loads without login (110 images on 2026-11-12). Shots are often concept work, not shipped products. Prefer them for visual style, not for flows. |
| Awwwards | landing | Award-winning marketing sites, bold layouts, motion | `awwwards.com` | `sites <app type> <mood>` | Keep only `awwwards.com/sites/...` results. Feed at `https://www.awwwards.com/websites/`. Each site page has a large screenshot and the studio credit. A cookie banner can cover the bottom of the screenshot. |
| One Page Love | landing | Landing pages and one-page sites, clean type | `onepagelove.com` | `<app type> <mood>` | Each entry page has `og:image` with the full screenshot. |
| Recent.design (formerly Godly) | both | Hand-picked current web design, interfaces, branding, motion | `recent.design` | `<app type> <mood>` | `godly.website` redirects here. Tabs: Websites, Interface, App Screenshots; use Interface and App Screenshots for in-app pages. Images open the original site; credit the site's maker. |
| Collect UI | in-app | Single UI patterns by category (dashboard, login, settings, pricing, empty state) | `collectui.com` | `<page> UI design inspiration` | Search returns category pages such as `https://collectui.com/designs/dashboard-ui-design-inspiration`; you can also open that URL pattern directly. A category page is a listing: do not use it as a candidate. Each tile carries `data-impression-id`, and one design's own page is the category URL plus `/<that id>` (checked 2026-11-12). It opens that design with "Design by <name>" and a "View on X" link to the original post. Get the ids with `playwright-cli eval "[...document.querySelectorAll('[data-impression-type=design]')].map(e=>e.dataset.impressionId).slice(0,8).join(' ')"`, open one design's URL, credit the named designer, and link that design URL. |
| SaaS Landing Page | landing | SaaS marketing pages, pricing and feature sections | `saaslandingpage.com` | `<app type>` | Shows real shipped products, so it suits "make it look like a real product". No designer named: credit the product. |
| Siteinspire | landing | Restrained, typographic, editorial sites | `siteinspire.com` | `<app type> <mood>` | Good for calm, content-first directions. No designer named on most entries: credit the product. |

Dropped: Screenlane redirects to Pageflows (paid, Cloudflare challenge). Mobbin keeps its screens behind login and a paid plan.

## Browsing (every subagent)

Every search subagent, in either pass, follows these rules.

Run `playwright-cli` from a scratch directory, never from the user's repo. It creates `.playwright-cli/` in the current directory. Use your own named session so parallel workers do not share a browser: `cd "$WORK" && playwright-cli -s=<subagent name> open <url>`, then `resize 1440 900`, `goto`, `eval` and `screenshot --filename=<abs path>`. Save screenshots only in your own folder, `$WORK/shots/<subagent name>/`, so parallel workers never mix files. Close it when done (`playwright-cli -s=<name> close`).

**Recognize a block.** After each `goto`, run `playwright-cli -s=S eval "location.href + ' | ' + document.title + ' | ' + document.images.length"`. The page is blocked when any of these is true:
- the title is "Just a moment...", "Attention Required!" or "Access denied";
- the text says "Verify you are human" or "Performing security verification";
- `location.href` is `chrome-error://chromewebdata/`, or `goto` reports `ERR_HTTP_RESPONSE_CODE_FAILURE` or a 403;
- the body is nearly empty, with 0 to 2 images where the site normally shows dozens.

A blocked page is not a candidate. Record it as blocked and move on: never try to get past it by any means, never click a captcha or "Verify you are human" box, and never screenshot a challenge page into the shortlist.

**Screenshots.** Take viewport-only screenshots at a 1440 by 900 desktop window (`playwright-cli -s=S resize 1440 900` once after `open`), and never pass `--full-page`. Shoot the design itself: the main design image element (`playwright-cli -s=S screenshot "<selector>" --filename=<abs path>`) when the page shows it inside site chrome, otherwise the visible page. A full-page capture of a gallery page can be 1440 by 11000 pixels: unreadable when viewed, mostly the gallery's own chrome, and it bloats the published page (one run reached 8 MB of media).

**Polite pacing.** Open one page at a time per worker, wait for it to load (a few seconds), and never retry a failed page in a loop. Try each page once, then move on. Open only design pages you might use, not whole feeds. Stay signed out.

## Gated sources

Only the gated pass searches these (`SKILL.md` step 3), following the Browsing rules plus the patchright fallback below. Many entries name no designer: credit the product or company as the maker and name the gallery as the source site.

| Source | Suits | Good for | Domain | Query | What happened in playwright-cli |
|---|---|---|---|---|---|
| Behance | both | Full case studies: many screens of one product, design systems | `behance.net` | `gallery <app type> <page>` | HTTP 400 (`net::ERR_HTTP_RESPONSE_CODE_FAILURE`), on search and on gallery pages. Keep only `behance.net/gallery/...` results. |
| Land-book | landing | Landing pages and product sites, tagged by industry and style | `land-book.com` | `<app type> <mood>` | Cloudflare "Performing security verification / Verify you are human". |
| Lapa Ninja | landing | Landing pages by category, with designer credits | `lapa.ninja` | `<app type>` | Cloudflare "Attention Required!" page. |

## Patchright fallback (gated pass only)

This section applies only to the gated pass: one subagent per app page that searches the gated sources above. No other subagent gets it or uses it. In the gated pass, a page that is blocked in `playwright-cli` gets one patchright attempt; that attempt is the only exception to the Browsing rule "record it as blocked and move on". Patchright is a Playwright build that is harder for bot checks to spot. It runs on demand through `uv`, so nothing is installed for good. Save this snippet as `patchright_shot.py` in the scratch directory:

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

Run it with `uv run --with patchright python -I "$WORK/patchright_shot.py" "<url>" "$WORK/shots/<subagent name>/<card id>.png"`. If it says the browser is missing, run `uv run --with patchright patchright install chromium` once. `page.screenshot` captures only the visible window, never the full page. Patchright's own docs recommend a headed browser (`headless=False`) and a persistent context, so a window opens briefly. After it finishes, read the printed title and look at the screenshot. If it still shows a challenge, give up on that page and move on. Never click a captcha or "Verify you are human" box.

Claude Code's permission check can refuse this command as bot-check circumvention. If it does, stop using patchright for the rest of the run and record every gated page not loaded as refused. Do not retry, do not reword the command, and do not try another route around the refusal. Report every page skipped this way, by source, so the final reply can name each skipped source and tell the user they can allow `uv run --with patchright` in their permission settings.
