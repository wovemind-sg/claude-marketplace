# Writing Playwright flows for demo beats

One flow per demo beat at `video/flows/beat-NN.py`. Claude writes these; the user never
edits them. `record_web.py` opens ONE phone-sized browser page (390×844 CSS px, recorded
at 3× = 1170×2532) and calls every beat's `run(page, base_url)` back-to-back in order,
recording the whole thing as a single take that's cut into `beat-NN.mp4` clips afterwards.
A `pause(page, seconds)` helper is injected into each module.

Because it's the same `page` for the whole take, beat 2's flow starts exactly on the
screen where beat 1's ended — you don't need to re-navigate there, and a splash screen
or login only really shows up once. Just don't call `page.goto(base_url + ...)` again
inside a later beat unless the story genuinely returns to that page.

## Skeleton

```python
def run(page, base_url):
    page.goto(base_url + "/login")
    pause(page, 1.5)                       # let the viewer see the screen
    page.get_by_label("Phone number").click()
    pause(page, 0.6)
    page.get_by_label("Phone number").press_sequentially("+65 8123 4567", delay=70)   # types like a human
    pause(page, 0.8)
    page.get_by_role("button", name="Continue").click()
    page.wait_for_load_state("networkidle")
    pause(page, 2)
```

## Making it look like a demo, not a test

- Pause 1.5–2.5 s on every new screen before doing anything, and ~0.6 s between clicks.
  Every screen is one the viewer is seeing for the first time — give them a moment to
  read it before the demo moves on.
- Type with `press_sequentially(text, delay=60..90)`, never `fill()` — instant text looks fake.
- Scroll gently: `page.mouse.wheel(0, 300)` in 2–3 steps with pauses, not one jump.
- End each beat on a settled screen (no spinner). `page.wait_for_load_state("networkidle")`.
- Never show real customer data or secrets. Fictional names only.
- Hide dev-only noise: cookie banners, debug toolbars. Dismiss them in the flow or set a
  cookie/localStorage flag before `goto`:
  `page.context.add_cookies([...])` / `page.add_init_script("localStorage.setItem('cookie_ok','1')")`.

## Selectors

Prefer, in order: `get_by_role("button", name="Save")`, `get_by_label("Amount")`,
`get_by_text("New invoice")`, `get_by_placeholder(...)`, then CSS `page.locator("#id")`.
When unsure what's on the page, take a screenshot: `page.screenshot(path="video/work/peek.png")`
and look at it, or dump `page.content()`.

## Logging in

If beats need a signed-in user: log in inside beat 1's flow (it's good footage, and every
later beat inherits the session automatically since it's the same page). If the login
shouldn't be shown on camera, set the auth cookie from a test account via
`page.context.add_cookies(...)` at the very top of beat 1's `run`, before its first
`goto`. Credentials go in `video/flows/env.py` (gitignored) and are imported by the flows;
never hard-code them. Ask the user for a test account only if the repo has no
seed/fixture — as one action.

## Running the app locally

The app must be reachable at `Base URL:` from `script.md`. Start it yourself in the
background (`uvicorn app.main:app --port 8000 &`, `npm run dev &`, docker compose…) and
wait until `curl -s -o /dev/null -w "%{http_code}" $BASE_URL` returns 200/302. If it needs
a `.env`, database or Redis that isn't running, get it running before recording; ask the
user only for values you can't find (one at a time). A staging URL works too — just set
`Base URL:` to it, but never record against production with real data.

## Desktop web apps

If the product is desktop-first and looks wrong on a phone, record with
`record_web.py video --desktop` (1440×900) and set `Format: landscape` in
`script.md`. `assemble.py` then frames it as a landscape screen instead of a phone —
the phone frame is still drawn but wide; that's acceptable for a browser app.
