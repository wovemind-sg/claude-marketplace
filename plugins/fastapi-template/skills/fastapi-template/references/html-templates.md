# HTML and Static File Templates

Replace `<App Name>` / `<app-name>` with the actual app name.

---

## `templates/base.html`

```html
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{% block title %}<App Name>{% endblock %}</title>
        <link rel="stylesheet" href="/static/css/app.css" />
        <script
            src="https://unpkg.com/htmx.org@2.0.4"
            integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+"
            crossorigin="anonymous"
        ></script>
        {% block head %}{% endblock %}
    </head>
    <body hx-boost="true">
        <div class="page">
            {% block content %}{% endblock %}
        </div>
        <script src="/static/js/app.js"></script>
        <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.9/dist/cdn.min.js"></script>
        {% block scripts %}{% endblock %}
    </body>
</html>
```

Loading order matters:
- HTMX in `<head>` (synchronous, no defer)
- `app.js` before Alpine (so any setup runs first)
- Alpine with `defer` last (needs a complete DOM to scan for `x-data`)

`hx-boost="true"` on `<body>` is not optional — it makes every `<a>` and `<form>` fetch via AJAX and swap `<body>` instead of doing a full-page navigation. In a Capacitor WKWebView, a normal browser navigation (a plain `<a href>` click, a server 303 redirect landed on directly) reloads the whole page — CDN scripts re-fetch, the screen flashes white, and the app stops feeling native. Boosted navigation avoids all of that. Never rely on `<a href>` full-page navigation or a bare `RedirectResponse` as the primary nav path — let hx-boost intercept it.

---

## `templates/index.html`

```html
{% extends "base.html" %}

{% block title %}Home – <App Name>{% endblock %}

{% block content %}
<main>
    <h1><App Name></h1>
</main>
{% endblock %}
```

---

## `templates/prompts/example.txt`

```
You are a helpful assistant for <App Name>.

{% if context %}
Context:
{{ context }}
{% endif %}

Answer the user's question clearly and concisely.
```

Prompt templates are Jinja2 `.txt` files. Render them with `render_prompt("example", context=...)` from `app/ai.py`.

---

## `static/css/app.css`

```css
*, *::before, *::after {
    box-sizing: border-box;
}

body {
    margin: 0;
    font-family: system-ui, -apple-system, sans-serif;
    line-height: 1.5;
}

.page {
    max-width: 1200px;
    margin: 0 auto;
    padding: 1rem;
}
```

---

## `static/js/app.js`

```javascript
// App-wide JavaScript.
// Prefer HTMX attributes and Alpine.js x-data for UI interactions.
// Use this file only for global setup that doesn't belong in a component.
```

---

## HTMX + Alpine.js Patterns

**HTMX** — server-driven updates. The server returns HTML fragments.

```html
<!-- Swap a div on button click -->
<button hx-get="/api/items" hx-target="#items" hx-swap="innerHTML">
    Load Items
</button>
<div id="items"></div>

<!-- Post a form without page reload -->
<form hx-post="/api/items" hx-target="#items" hx-swap="afterbegin">
    <input name="name" />
    <button type="submit">Add</button>
</form>
```

**Alpine.js** — local client-side state (no server round-trip needed).

```html
<!-- Toggle visibility -->
<div x-data="{ open: false }">
    <button @click="open = !open">Toggle</button>
    <p x-show="open">Hello!</p>
</div>

<!-- Simple counter -->
<div x-data="{ count: 0 }">
    <button @click="count++">+</button>
    <span x-text="count"></span>
</div>
```

**Combined** — Alpine manages local state, HTMX fetches server data:

```html
<div x-data="{ loading: false }">
    <button
        hx-get="/api/data"
        hx-target="#result"
        @htmx:before-request="loading = true"
        @htmx:after-request="loading = false"
    >
        <span x-show="!loading">Load</span>
        <span x-show="loading">Loading…</span>
    </button>
    <div id="result"></div>
</div>
```

For more guidance on when to use HTMX vs Alpine, see the `htmx-vs-alpine` skill.
