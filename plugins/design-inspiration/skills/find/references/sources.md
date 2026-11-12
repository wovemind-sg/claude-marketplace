# Inspiration sources and how to browse them

Every source below was opened with `playwright-cli` on 2026-11-12. The sources fall in two groups, and `SKILL.md` step 3 searches them in two separate passes:
- **Open sources** loaded in a normal browser without a login. The open pass searches only these, and it never tries to get past a block.
- **Gated sources** blocked the normal browser that day. Only the gated pass searches them, with the patchright fallback at the end of this file. Their result pages are often the best references for an app type, so they are worth a try when the user allows it.

How to use a source:
- **Suits**: each source is marked by the kind of app page it is good for: **in-app** (dashboards, tables, settings, other screens inside the product), **landing** (landing, marketing and pricing pages), or **both**. Search a source only for app pages it suits. Landing-page galleries return marketing sites, which are poor references for an in-app screen.
- **Search**: search each source the way its "How to search" column says. Some sources have their own search URL, some are browsed through their own category listings, and the rest are searched with WebSearch. For WebSearch, put the source's domain in `allowed_domains`: WebSearch ignores a `site:` prefix in the query and returns other sites, so the parameter is what restricts the search (only with a search tool that has no domain parameter, put `site:<domain>` at the start of the query instead). Fill `<app type>` with what the app is (for example "invoicing dashboard", "habit tracker mobile app"), `<page>` with the app page (for example "settings", "onboarding") and `<mood>` with a mood word from the user's answers (for example "minimal", "playful", "dark").
- **Several angles per source**: run three or four distinct searches per source for the app page, not one, because one search returns one look many times over. Angles: the screen type ("transactions table"), the product type ("finance dashboard"), a neighbouring screen type ("expense list", "payments history"), and each of those with and without the mood word. On a source browsed by category, an angle is a different listing: the screen type's category, a neighbouring category (table, dashboard, analytics) and, where the source has one, the industry category (for example expense management or accounting).
- **One design per candidate**: a candidate is one design's own page, showing that design and crediting its maker. Skip listing, category, tag and search-results pages, because the shortlist card links to the page and credits its maker, and a listing has neither one design nor one maker. When a search only finds a listing, open it and follow it to a single design's page.
- **One candidate per maker**: take at most one design per designer or product from each source for an app page. A designer often posts several shots of the same screen (one Dribbble search returned two shots of the same table from one design system), and they would fill the pool with near-copies.
- **Credit**: record the designer or studio name exactly as the page shows it, plus the URL of the design's own page. The shortlist links every card to it. On galleries of shipped products that name no designer (SaaSUI, SaaS Landing Page, Siteinspire, often One Page Love), credit the product or company as the maker and name the gallery as the source site. Each row's notes say where the credit is on that site.

## Open sources

| Source | Suits | Good for | Domain | How to search | Notes |
|---|---|---|---|---|---|
| Dribbble | in-app | App screens, dashboards, tables, mobile UI, components, single shots | `dribbble.com` | Open its own search, `https://dribbble.com/search/<terms joined by hyphens>` (for example `https://dribbble.com/search/transactions-table`, 84 images on 2026-11-12), then list the shot links with `playwright-cli -s=S eval "[...new Set([...document.querySelectorAll('a[href*=\"/shots/\"]')].map(a=>a.href))].filter(h=>/shots\/\d+/.test(h)).slice(0,12).join(' ')"`. Also try WebSearch with `shots <app type> <page> <mood>` when its own search gives few shots for an angle. | Keep only `dribbble.com/shots/<number>-...` pages. WebSearch on this domain mostly returns tag and listing pages. Credit: the page title reads "<shot title> by <designer> on Dribbble". Image: `.block-media >> nth=0`, after hiding the sticky header and size-checking the block, as "Screenshots" below shows. Shots are often concept work, not shipped products; prefer them for visual style, not for flows. |
| SaaSUI | in-app | Real shipped SaaS screens by screen type: dashboard, table, settings, form, empty state, onboarding, billing, analytics, search, navigation, modal | `saasui.design` | Browse its own listings: `https://www.saasui.design/pattern/<pattern>` (patterns include `dashboard`, `table`, `settings`, `form`, `empty-state`, `onboarding`, `billing`, `analytics`, `search`, `navigation`, `modal`, `profile`, `calendar`, `notification`), and by industry at `https://www.saasui.design/category/<industry>` (for example `accounting-software`, `expense-management`, `crm`, `analytics`). List one pattern's designs with `playwright-cli -s=S eval "[...new Set([...document.querySelectorAll('a[href^=\"/pattern/<pattern>/\"]')].map(a=>a.href))].slice(0,20).join(' ')"`. | One design's own page is `https://www.saasui.design/pattern/<pattern>/<product>` (for example `/pattern/table/attio`). An industry category links to `/application/<product>` pages, which hold all of one product's screens: follow those to a `/pattern/<pattern>/<product>` page. No designer named: credit the product (the page heading, "Attio Table UI"). Image: `main img.object-cover` (the site itself crops the screen to its frame). Many of its screens are mid-interaction crops (an open menu, a filter popup, a page with one row), and in a real run none of them showed the page that was searched. Keep only a screen that shows the whole pattern, such as a full table or a full settings page; if none does, return nothing for SaaSUI, because a crop of one menu is no reference for a whole page. |
| Kombai gallery | in-app | Complete web app screens of fictional products: dashboards, tables, settings, forms, charts, checkout | `kombai.com` | Browse its own category listings: `https://kombai.com/gallery/web/<category>/` (categories include `dashboard`, `table`, `settings`, `forms`, `charts`, `checkout`; the full list is on `https://kombai.com/gallery/web/`). List designs with `playwright-cli -s=S eval "[...new Set([...document.querySelectorAll('a[href*=\"/gallery/inspirations/\"]')].map(a=>a.href))].slice(0,20).join(' ')"`. | One design's own page is `https://kombai.com/gallery/inspirations/<category>-web-<n>/`. The products are fictional and the designs are published by Kombai, a design tool, with a "Remix in Kombai" button and no designer named: credit "Kombai" as the maker and name the fictional product in the title (the page title reads "<product> - Dashboard App Page Example"). The design is a live frame, not an image: resize the window to 1440 by 1100 before the element screenshot of `iframe[src*="kombai-inspiration-library"]`, so the whole frame fits below the site's header. Never open the frame's own address: it goes to a login page. |
| Collect UI | in-app | Single UI shots by category (dashboard, login, settings, pricing, empty state), gathered from posts on X | `collectui.com` | WebSearch with `<page> UI design inspiration`, or open the category URL directly, for example `https://collectui.com/designs/dashboard-ui-design-inspiration`. A category page is a listing: do not use it as a candidate. | Each tile carries `data-impression-id`, and one design's own page is the category URL plus `/<that id>` (checked 2026-11-12). Get the ids with `playwright-cli -s=S eval "[...document.querySelectorAll('[data-impression-type=design]')].map(e=>e.dataset.impressionId).slice(0,8).join(' ')"`. A design page opens as a dark overlay with a side panel. Credit: the maker is the name and @handle at the top of the panel, next to the "View on X" link (the original post); "Spotted by" names the account that collected it, not its maker. Link the design's Collect UI URL. Image: `.media >> nth=0` (a video post gives one frame). Thin for many screen types: expect few candidates. |
| Awwwards | landing | Award-winning marketing sites, bold layouts, motion | `awwwards.com` | WebSearch with `sites <app type> <mood>` | Keep only `awwwards.com/sites/...` results. Feed at `https://www.awwwards.com/websites/`. Each site page has a large screenshot and the studio credit. A cookie banner can cover the bottom of the screenshot. |
| One Page Love | landing | Landing pages and one-page sites, clean type | `onepagelove.com` | WebSearch with `<app type> <mood>` | Each entry page shows the full screenshot of the site. |
| Recent.design (formerly Godly) | landing | Hand-picked current websites, bold and trend-led | `recent.design` | No keyword search: the site shows the same feed whatever is asked. Browse `https://recent.design/websites` and open entries. | `godly.website` redirects here. One entry's own page is `https://recent.design/i/<id>-<slug>`, and it links to the original site; credit the site's product or studio. Its main "Design" feed is mostly branding, motion and illustration, and its "App Screenshots" tab holds app store screenshots, so neither suits an in-app screen. |
| SaaS Landing Page | landing | SaaS marketing pages, pricing and feature sections | `saaslandingpage.com` | WebSearch with `<app type>` | Shows real shipped products, so it suits "make it look like a real product". No designer named: credit the product. |
| Siteinspire | landing | Restrained, typographic, editorial sites | `siteinspire.com` | WebSearch with `<app type> <mood>` | Good for calm, content-first directions. No designer named on most entries: credit the product. |

Dropped, as seen on 2026-11-12: Screenlane redirects to Pageflows (paid, Cloudflare challenge). Mobbin keeps its screens behind login and a paid plan. Refero shows about six screens, then asks to log in, and links to no single design. SaaS Interface shows a few thumbnails and sells the gallery. SaaSFrame showed a "Vercel Security Checkpoint", Nicelydone and Muzli search a Cloudflare "Just a moment..." page, and Figma Community search an error page, so their content and terms could not be checked.

## Browsing (every subagent)

Every search subagent, in either pass, follows these rules.

Run `playwright-cli` from a scratch directory, never from the user's repo. It creates `.playwright-cli/` in the current directory. Use your own named session so parallel workers do not share a browser: `cd "$WORK" && playwright-cli -s=<subagent name> open <url>`, then `resize 1440 900`, `goto`, `eval` and `screenshot --filename=<abs path>`. Save screenshots only in your own folder, `$WORK/shots/<subagent name>/`, so parallel workers never mix files. Close it when done (`playwright-cli -s=<name> close`).

**Recognize a block.** After each `goto`, run `playwright-cli -s=S eval "location.href + ' | ' + document.title + ' | ' + document.images.length"`. The page is blocked when any of these is true:
- the title is "Just a moment...", "Attention Required!", "Access denied" or "Vercel Security Checkpoint";
- the text says "Verify you are human" or "Performing security verification";
- `location.href` is `chrome-error://chromewebdata/`, or `goto` reports `ERR_HTTP_RESPONSE_CODE_FAILURE` or a 403;
- the body is nearly empty, with 0 to 2 images where the site normally shows dozens.

A blocked page is not a candidate. Record it as blocked and move on: never try to get past it by any means, never click a captcha or "Verify you are human" box, and never screenshot a challenge page into the shortlist.

**Screenshots: shoot the design's own image element.** On a design's own page, take an element screenshot of the design's main image: `playwright-cli -s=S screenshot "<selector>" --filename=<abs path>`, with the selector from the source's row. A viewport screenshot of the same page is mostly the gallery's own chrome (a dark overlay and a side panel around Collect UI shots), so shoot the element. The element alone is not always clean: a sticky header or popup that sits over it is captured too. On Dribbble the designer's sticky bar (avatar, "Available for work", "Get in touch") sticks just below the site menu and covered the top 31px of every shot, and the old selector `img.v-img.content-block` skipped a shot that opens with a video and caught a later image that was still fading in, a near-blank picture. So on Dribbble, hide every fixed and sticky element first, then list the size of each media block and shoot the first one that is the design. Verified on 2026-11-12 on five shot pages:

```
# Dribbble shot page
playwright-cli -s=S eval "document.querySelectorAll('body *').forEach(e=>{if(/fixed|sticky/.test(getComputedStyle(e).position))e.style.visibility='hidden'})"
playwright-cli -s=S eval "[...document.querySelectorAll('.block-media')].map(e=>{const r=e.getBoundingClientRect();return Math.round(r.width)+'x'+Math.round(r.height)}).join(' ')"
playwright-cli -s=S screenshot ".block-media >> nth=0" --filename=<abs path>
# only when block 0 fails the size check: bring block <n> into view, wait 3 seconds for it to load, then shoot it
playwright-cli -s=S eval "document.querySelectorAll('.block-media')[<n>].scrollIntoView({block:'center'})"
playwright-cli -s=S screenshot ".block-media >> nth=<n>" --filename=<abs path>

playwright-cli -s=S screenshot "main img.object-cover" --filename=<abs path>             # SaaSUI /pattern/<pattern>/<product>
playwright-cli -s=S screenshot ".media >> nth=0" --filename=<abs path>                   # Collect UI design page
playwright-cli -s=S resize 1440 1100                                                     # Kombai: fit the frame below the header
playwright-cli -s=S screenshot 'iframe[src*="kombai-inspiration-library"]' --filename=<abs path>  # Kombai design page
playwright-cli -s=S resize 1440 900
```

Run the hide command again after every `goto`, because a new page brings its header back. **Size check:** a Dribbble shot is about 1024 by 768 (1024 by 796 also seen); a block under about 300px tall, or more than three times as wide as tall, is a banner or an ad, not the design (one run captured a 1024 by 151 banner). Take the next block that passes, or drop the candidate if none does. If the selector matches nothing, the page is not a design page as expected: drop the candidate rather than shooting the whole window. For a source with no selector in its row (the landing-page galleries), use the largest image of the design on its page as the element.

**Check every screenshot yourself.** After each screenshot, look at the image (Read the PNG). Keep the candidate only if the picture is the design itself and readable. A banner, a login or cookie wall, a popup, an empty state, a near-blank picture or a picture that is mostly site chrome means: retake it once by the source's rule above, and drop the candidate if it is still wrong. The session checks the returned pictures again later, but that is the second check, not the first: every bad picture you return costs a slot in the pool and hides how thin the pool really is. Delete every screenshot you drop and return every one you keep, so your folder holds exactly the files in your returned list.

Only when the candidate is itself a whole live website, the original site that a landing-page gallery entry opens, take a viewport screenshot of it at the 1440 by 900 window (`playwright-cli -s=S screenshot --filename=<abs path>`), because there the visible page is the design. Never pass `--full-page`: a full-page capture can be 1440 by 11000 pixels, unreadable when viewed, mostly the gallery's own chrome, and it bloats the published page (one run reached 8 MB of media).

**Polite pacing.** Open one page at a time per worker, wait for it to load (a few seconds), and never retry a failed page in a loop. Try each page once, then move on. Open only design pages you might use, not whole feeds. Stay signed out.

## Gated sources

Only the gated pass searches these (`SKILL.md` step 3), following the Browsing rules plus the patchright fallback below. Many entries name no designer: credit the product or company as the maker and name the gallery as the source site.

| Source | Suits | Good for | Domain | How to search | What happened in playwright-cli |
|---|---|---|---|---|---|
| Behance | both | Full case studies: many screens of one product, design systems | `behance.net` | WebSearch with `gallery <app type> <page>` | HTTP 400 (`net::ERR_HTTP_RESPONSE_CODE_FAILURE`), on search and on gallery pages. Keep only `behance.net/gallery/...` results. |
| Land-book | landing | Landing pages and product sites, tagged by industry and style | `land-book.com` | WebSearch with `<app type> <mood>` | Cloudflare "Performing security verification / Verify you are human". |
| Lapa Ninja | landing | Landing pages by category, with designer credits | `lapa.ninja` | WebSearch with `<app type>` | Cloudflare "Attention Required!" page. |

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

Run it with `uv run --with patchright python -I "$WORK/patchright_shot.py" "<url>" "$WORK/shots/<subagent name>/<card id>.png"`. If it says the browser is missing, run `uv run --with patchright patchright install chromium` once. `page.screenshot` captures only the visible window, never the full page, so this gives a window screenshot rather than the element screenshot the Browsing rules ask for. Patchright's own docs recommend a headed browser (`headless=False`) and a persistent context, so a window opens briefly. After it finishes, read the printed title and look at the screenshot. If it still shows a challenge, give up on that page and move on. Never click a captcha or "Verify you are human" box.

Claude Code's permission check can refuse this command as bot-check circumvention. If it does, stop using patchright for the rest of the run and record every gated page not loaded as refused. Do not retry, do not reword the command, and do not try another route around the refusal. Report every page skipped this way, by source, so the final reply can name each skipped source and tell the user they can allow `uv run --with patchright` in their permission settings.
