# Jinja2 → html/template

The go-webapp-template `render.go` parses each page together with `base.html` and `templates/partials/*.html`, then executes `base.html`. A page is a file of `{{define}}` blocks. Prompt files under `templates/prompts/` use `text/template` — the same syntax without HTML escaping.

Read this file before converting any template. Convert templates **after** the handlers that render them, so you know what the data looks like, and convert one page at a time with its partials.

## Four additions to `render.go`

Grown projects use layouts, custom filters, template globals and context variables set by dependencies. The skeleton's `render.go` needs these four small changes before the first page is ported. Make them in session 1.

**(a) Layout chains.** Jinja pages often extend an intermediate layout (`{% extends "layouts/app.html" %}` which itself extends `base.html`). Put a comment on the first line of the page: `{{/* extends layouts/app.html */}}`. In `parse()`, read that comment (regex `^\{\{/\* extends (.+?) \*/\}\}`) and build the page's parse set as `base.html` + each layout in the chain + partials + the page. Pages without the comment get `base.html` + partials + page as today. This keeps a layout's `{{define}}` blocks from leaking into pages that don't use it.

**(b) FuncMap.** Add to `funcs` in `render.go`:

```go
"dict": func(kv ...any) (map[string]any, error) {   // {{template "badge" (dict "Text" "x" "Kind" "info")}}
    if len(kv)%2 != 0 { return nil, errors.New("dict: odd number of args") }
    m := make(map[string]any, len(kv)/2)
    for i := 0; i < len(kv); i += 2 {
        k, ok := kv[i].(string)
        if !ok { return nil, fmt.Errorf("dict: key %v is not a string", kv[i]) }
        m[k] = kv[i+1]
    }
    return m, nil
},
"default": func(def, v any) any {                   // {{default "—" .Description}}  (note: default FIRST, value last, so it pipes: {{.Description | default "—"}})
    if v == nil { return def }
    if s, ok := v.(string); ok && s == "" { return def }
    if p, ok := v.(*string); ok { if p == nil || *p == "" { return def }; return *p }
    return v
},
"add": func(a, b int) int { return a + b },
"sub": func(a, b int) int { return a - b },
"join": strings.Join,                               // {{join .Tags ", "}}
"safe": func(s string) template.HTML { return template.HTML(s) },  // ONLY for server-sanitised HTML
```

plus one Go function per custom Jinja filter the inventory lists under `jinja_env.filters` (`price`, `phone`, `markdown_plain`, ...). Port the Python body literally; Jinja filters are pure functions. A filter that reaches into the request or the DB is not a filter — it becomes data the handler computes.

**(c) Globals.** Jinja `templates.env.globals` (`app_name`, `dev_mode`, analytics keys, constants) and dependency-set `request.state.*` values both become fields every render gets. Add to `server.go`:

```go
// view merges per-request globals into page data so templates can rely on them.
func (s *Server) view(r *http.Request, data map[string]any) map[string]any {
    if data == nil { data = map[string]any{} }
    data["AppName"] = appName
    data["DevMode"] = s.Dev
    data["Authenticated"] = s.Cookies.IsAuthenticated(r)
    data["Path"] = r.URL.Path
    // + anything from request context set by middleware, e.g. data["Admin"] = isAdmin(r.Context())
    return data
}
```

and call `s.tmpl.Render(w, "x.html", s.view(r, map[string]any{...}))` from every handler. Pure-function globals (`now()`, `asset_v("x.css")`) go in the FuncMap instead.

**(d) `missingkey=error`.** In `parse()`, `template.New("").Funcs(funcs).Option("missingkey=error").ParseFS(...)`. Jinja renders an undefined variable as empty; `html/template` renders `<no value>` for a missing map key. With this option it errors instead, so every context variable you forgot to port fails in the render-all-pages test rather than shipping as a blank. Keep it on permanently.

## Syntax table

| Jinja2 | html/template |
|---|---|
| `{% extends "base.html" %}` | nothing — delete; the page is only `{{define}}` blocks |
| `{% extends "layouts/x.html" %}` | `{{/* extends layouts/x.html */}}` first line (see (a)) |
| `{% block title %}X{% endblock %}` in a page | `{{define "title"}}X{{end}}` |
| `{% block x %}default{% endblock %}` in base/layout | `{{block "x" .}}default{{end}}` |
| `{{ super() }}` | no equivalent — copy the parent block's content into the page's define |
| `{% include "partials/row.html" %}` | the partial file wraps its body in `{{define "row"}}...{{end}}`; the page uses `{{template "row" .}}`. Partials are parsed into every page, so two partials with the same define name collide — the inventory lists basenames; rename on collision. |
| `{% include "x.html" ignore missing %}` | drop the include |
| `{% macro badge(text, kind="info") %}...{% endmacro %}` | `{{define "badge"}}<span class="badge-{{.Kind}}">{{.Text}}</span>{{end}}` in `templates/partials/macros.html` |
| `{{ badge("New") }}` / `{{ badge("New", kind="warn") }}` | `{{template "badge" (dict "Text" "New" "Kind" "info")}}` — defaults are not expressible; pass every argument |
| `{% call panel("Title") %}body{% endcall %}` / `{{ caller() }}` | no equivalent — split into `panel-open` and `panel-close` defines, or move the body into a named define passed by name |
| `{% from "macros.html" import badge %}` / `{% import %}` | delete the line |
| `{% set x = expr %}` | `{{$x := expr}}` (first assignment) |
| `{% set x = other %}` later (reassign), incl. inside loops | `{{$x = other}}` (no colon) |
| `{% set html %}...{% endset %}` (block set) | precompute in the handler |
| `{% with a = b %}...{% endwith %}` | `{{$a := b}}...` — do **not** use Go's `{{with}}`; it rebinds the dot, a different thing |
| `{% if a and not b %}` / `{% elif c %}` / `{% else %}` | `{{if and .A (not .B)}}` / `{{else if .C}}` / `{{else}}` ... `{{end}}` |
| `a == b`, `a != b`, `a < b`, `a >= b` | `eq .A .B`, `ne .A .B`, `lt .A .B`, `ge .A .B` — prefix, and both sides must be the same basic kind (`int` vs `int64` errors) |
| `x in list` / `x not in list` | precompute a bool in the handler (`data["IsAdmin"]`) or add a `has` func |
| `a if cond else b` | `{{if cond}}a{{else}}b{{end}}` |
| `x is none` / `x is not none` | `{{if not .X}}` / `{{if .X}}` — a nil pointer, empty string, 0 and empty slice are all false |
| `x is defined` / `x is undefined` | every key must exist (see (d)). Provide it from `view()` or the handler; the check disappears |
| `obj.attr` | `.Attr` — Go fields must be exported (Capitalised) |
| `d["key"]` / `d.key` on a dict | `.key` on a map works; `index .D "key"` when the key is a variable or not an identifier |
| `list[0]` / `list[-1]` | `index .L 0` / `index .L (sub (len .L) 1)` |
| `obj.method()` | `.Method` — niladic methods are called automatically; methods with args: `.Method "arg"` |
| `{% for x in xs %}...{% else %}empty{% endfor %}` | `{{range .Xs}}...{{else}}empty{{end}}` — inside the range the dot is the element; the page data is `$` |
| `loop.index0` / `loop.index` | `{{range $i, $x := .Xs}}` then `$i` / `add $i 1` |
| `loop.first` / `loop.last` | `eq $i 0` / `eq $i (sub (len $.Xs) 1)` |
| `loop.revindex`, `loop.cycle`, `loop.length`, nested `loop.parent` | precompute into the slice elements |
| `{% for k, v in d.items() %}` | `{{range $k, $v := .D}}` — Go iterates map keys **sorted**; if order matters, build a slice of `{Key, Value}` pairs in the handler |
| `{{ x\|length }}` | `{{len .X}}` |
| `{{ x\|tojson }}` | `{{json .X}}` (returns `template.JS`); the enclosing attribute **must be single-quoted**: `x-data='{{json .State}}'`. The inventory counts double-quoted `tojson` attributes — fix every one. |
| `{{ html\|safe }}` | pass `template.HTML(html)` from the handler, or `{{safe .HTML}}` — only for content the server sanitised (bluemonday). Never on user input. |
| `{{ x\|default("—") }}` | `{{.X \| default "—"}}` (see (b)) |
| `{{ x\|default("—", true) }}` (boolean mode: also replaces falsy) | `{{with .X}}{{.}}{{else}}—{{end}}` |
| `{{ x\|e }}` / `{{ x\|escape }}` / `{{ x\|string }}` | drop the filter |
| `{{ xs\|join(", ") }}` | `{{join .Xs ", "}}` |
| `\|upper` `\|lower` `\|title` `\|capitalize` `\|trim` `\|replace(a,b)` `\|truncate(n)` | FuncMap wrappers around `strings.*` only when used in more than two places; otherwise compute the string in the handler |
| `\|int` `\|float` `\|round` `\|abs` `\|format(...)` / `"%d" % x` | precompute, or `{{printf "%.2f" .X}}` |
| `\|urlencode` | `{{urlquery .X}}` (builtin) |
| `\|map(attribute=)`, `\|selectattr`, `\|rejectattr`, `\|list`, `\|first`, `\|last`, `\|max`, `\|min`, `\|sum`, `\|sort`, `\|groupby`, `\|unique`, `\|batch`, `\|slice` | always precompute in the handler — templates have no lambdas, and the handler is where this logic belongs anyway |
| `{{ dt.strftime("%Y-%m-%d") }}` / `\|strftime` | `{{.Dt.Format "2006-01-02"}}` (Go reference time layout; `%H:%M` → `15:04`, `%b %d` → `Jan 02`) |
| `{{ price(x) }}` custom filter/global | `{{price .X}}` FuncMap entry (see (b)) |
| `{{ url_for('static', path='/css/app.css') }}` | literal `/static/css/app.css` |
| `{{ url_for('item_detail', item_id=item.id) }}` | literal path with the parameter interpolated: `/items/{{.ID}}`. The inventory resolves route function names to paths. There is no reverse routing in Go. |
| `{{ request.url.path }}`, `{{ request.query_params.q }}`, `{{ request.cookies.get("x") }}`, `{{ request.state.user }}` | the handler (or `view()`) puts the value in `data`: `.Path`, `.Query.q`, `.User` |
| `{# comment #}` | `{{/* comment */}}` |
| `{%- ... -%}` whitespace control | `{{- ... -}}` |
| `{% raw %}{{ literal }}{% endraw %}` | `{{"{{"}} literal {{"}}"}}` — rare; Alpine expressions don't need it because Alpine uses `x-text`, not braces |
| `{% autoescape false %}` | not supported; use `template.HTML` per value |

### Prompt templates (`templates/prompts/*.txt`)

Same table, executed by `text/template` (`ai.New` parses them). No escaping, no FuncMap by default — if a prompt used a custom filter, pass the already-formatted string in the data. `{{ theme }}` → `{{.Theme}}`; `{% if theme %}` → `{{if .Theme}}`. Keys are whatever the Go call passes as `PromptContext`; use a `map[string]any` with the same names capitalised, or a struct.

## Autoescaping differences that bite

`html/template` is *contextual*: it escapes according to where the value lands (HTML text, attribute, URL, JS, CSS). Jinja escapes only HTML characters. Consequences:

- A value in `href`/`src`/`action` that is not `http(s)`/`mailto`/relative becomes `#ZgotmplZ`. For intentionally dynamic URLs (`javascript:`, `data:`, deep links `myapp://`), pass `template.URL(v)`.
- A value inside a `style="..."` attribute is CSS-escaped; dynamic CSS needs `template.CSS`.
- A value inside `<script>...</script>` or an `on*=` attribute is JSON-encoded (strings get quotes). `var x = "{{.X}}"` becomes `var x = "\"value\""` — write `var x = {{.X}}` and let Go quote it.
- Dynamic attribute **names** (`{{.Attr}}="x"`) and dynamic tag names are rejected.
- `{{.X}}` where `.X` is a nil map value prints `<no value>` without (d); with (d) it errors.
- `template.HTML` inside an attribute is still attribute-escaped — `safe` only helps in text content.

## Render-all-pages test

Add `internal/server/render_test.go` that calls `ParseTemplates(os.DirFS("../.."), false)` and executes every page in `t.pages` with representative data (one struct per page, built from what the handler passes). With `missingkey=error` this catches every un-ported variable and every Jinja construct left behind (`{%` in a Go template is a parse error). Run it after each page is converted.
