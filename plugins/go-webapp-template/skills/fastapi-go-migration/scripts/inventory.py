#!/usr/bin/env python3
"""Inventory a FastAPI project (fastapi-template shape) so it can be migrated to Go.

Stdlib only (ast, re, json, tomllib, pathlib, argparse) — run with plain `python3`, no venv,
the project itself is never imported.

Usage:
  python3 inventory.py <repo-root> [--json | --md] [--go-routes]

  --md          readable summary (default)
  --json        machine-readable dump (see keys below)
  --go-routes   also scan <repo>/internal/server/*.go for "METHOD /path" string literals and
                print MISSING IN GO / EXTRA IN GO; exit 1 if any Python route has no Go match.

JSON keys: routers, routes, models, templates, jinja_env, env_vars, third_party_imports,
grown_features, cache_decorators, background_tasks, middlewares, exception_handlers,
lifespan_steps, tests, deploy, pyproject, warnings (+ go_routes with --go-routes).

Everything is best effort: unexpected code is skipped and recorded in warnings[], never a crash.

Self-check — on a freshly scaffolded fastapi-template skeleton expect:
  1 route (GET /), 1 model (items, 3 columns), 2 html templates + 1 prompt,
  3 required env vars (ENGINE_URL, REDIS_CONNECTION_STRING, SESSION_SECRET) via _assert_env,
  + OPENROUTER_API_KEY required via the `if not X: raise RuntimeError` check in ai.py
  (a `raise` guarded by `if not VAR` after `VAR = os.getenv(...)` counts as required too).
"""
import argparse
import ast
import json
import re
import sys
import tomllib
from pathlib import Path

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
SKIP_DIRS = {".venv", "venv", "node_modules", ".git", "__pycache__", "site-packages",
             ".mypy_cache", ".pytest_cache", "dist", "build", ".dev"}
SKIP_PARAM_TYPES = {"Request", "Response", "BackgroundTasks", "WebSocket", "HTTPConnection"}
FEATURE_MAP = {
    "arq": "arq", "authlib": "oauth", "apscheduler": "scheduler", "PIL": "pillow",
    "numpy": "numpy", "pandas": "pandas", "fastmcp": "mcp", "mcp": "mcp",
    "smtplib": "email", "aiosmtplib": "email", "dns": "email_mx", "stripe": "stripe",
    "twilio": "twilio", "websockets": "websockets", "qrcode": "qrcode", "markdown": "markdown",
    "pytz": "timezones", "dateutil": "timezones", "jwt": "jwt", "httpx": "http_client",
    "requests": "http_client", "itsdangerous": "itsdangerous", "babel": "i18n", "gettext": "i18n",
}
RESPONSE_TYPES = [  # (call-name tail, type) — order = priority when a route returns several
    ("TemplateResponse", "template"), ("StreamingResponse", "stream"),
    ("RedirectResponse", "redirect"), ("JSONResponse", "json"), ("HTMLResponse", "html"),
    ("PlainTextResponse", "plain"),
]
PATH_PARAM = re.compile(r"\{(\w+)(?::\w+)?\}")
NOISE_CALLS = {"info", "debug", "warning", "error", "exception", "print", "critical"}

W = []  # warnings


def warn(msg):
    W.append(msg)


# ---------- ast helpers ----------
def dotted(node):
    if isinstance(node, ast.Call):
        return dotted(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def tail(node):
    d = dotted(node)
    return d.rsplit(".", 1)[-1] if d else None


def unparse(node):
    try:
        return ast.unparse(node) if node is not None else ""
    except Exception:
        return ""


def const_str(node):
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def kw(call, name):
    for k in call.keywords:
        if k.arg == name:
            return k.value
    return None


def body_nodes(stmts):
    """Walk statements recursively but do not descend into nested function/class defs."""
    for s in stmts:
        if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield s
        for child in ast.iter_child_nodes(s):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                continue
            yield from _walk_skip_defs(child)


def _walk_skip_defs(node):
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        yield from _walk_skip_defs(child)


def depends_names(text):
    return re.findall(r"\bDepends\(\s*([\w.]+)", text)


# ---------- project scan ----------
def iter_files(root, suffix):
    for p in sorted(root.rglob(f"*{suffix}")):
        if not any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            yield p


def parse_modules(root):
    mods = []
    for p in iter_files(root, ".py"):
        rel = p.relative_to(root).as_posix()
        try:
            src = p.read_text(encoding="utf-8", errors="replace")
            mods.append((rel, ast.parse(src), src))
        except SyntaxError as e:
            warn(f"{rel}: syntax error, skipped ({e.msg} line {e.lineno})")
    return mods


class Project:
    def __init__(self, root, mods):
        self.root, self.mods = root, mods
        self.app_vars = {"app"}
        self.routers = []  # dicts
        self.router_own_prefix = {}  # var -> prefix from APIRouter(prefix=)
        self.included_by = {}  # var -> (parent_var, prefix)
        self.dep_aliases = {}  # DBSessionDependency -> get_db_session
        self.pydantic_models = set()
        self._collect()

    def _collect(self):
        for rel, tree, _ in self.mods:
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    name, val = node.targets[0].id, node.value
                    t = tail(val) if isinstance(val, ast.Call) else None
                    if t == "APIRouter":
                        prefix = const_str(kw(val, "prefix")) or ""
                        deps = depends_names(unparse(kw(val, "dependencies")))
                        self.routers.append({"file": rel, "var_name": name, "prefix": prefix, "dependencies": deps})
                        self.router_own_prefix[name] = prefix
                    elif t == "FastAPI":
                        self.app_vars.add(name)
                    elif isinstance(val, ast.Subscript) and dotted(val.value) == "Annotated" and "Depends(" in unparse(val):
                        self.dep_aliases[name] = (depends_names(unparse(val)) or ["?"])[0]
                elif isinstance(node, ast.ClassDef):
                    bases = {tail(b) for b in node.bases}
                    is_table = any(k.arg == "table" and getattr(k.value, "value", False) is True for k in node.keywords)
                    if bases & {"BaseModel", "SQLModel"} and not is_table:
                        self.pydantic_models.add(node.name)
                elif isinstance(node, ast.Call) and tail(node) == "include_router" and node.args:
                    parent = dotted(node.func)
                    parent = parent.rsplit(".", 1)[0] if parent and "." in parent else "app"
                    sub = dotted(node.args[0])
                    if sub:
                        self.included_by[sub] = (parent, const_str(kw(node, "prefix")) or "")

    def full_prefix(self, var, _seen=()):
        if var in self.app_vars or var in _seen:
            return ""
        own = self.router_own_prefix.get(var, "")
        parent, inc = self.included_by.get(var, ("app", ""))
        return self.full_prefix(parent, _seen + (var,)) + inc + own


# ---------- routes ----------
def classify_param(arg, default, path_params, proj):
    name = arg.arg
    ann = unparse(arg.annotation)
    txt = f"{ann} {unparse(default)}"
    ann_name = ann.split("[")[0].split(".")[-1]
    if ann_name in SKIP_PARAM_TYPES:
        return None, []
    if "Depends(" in txt:
        return None, depends_names(txt)
    if ann_name in proj.dep_aliases:
        return None, [ann_name]
    if re.search(r"\bForm\(", txt):
        return "form", []
    if re.search(r"\bFile\(|\bUploadFile\b", txt):
        return "file", []
    if re.search(r"\bBody\(", txt):
        return "body", []
    if re.search(r"\bHeader\(|\bCookie\(", txt):
        return None, []
    if re.search(r"\bPath\(", txt) or name in path_params:
        return "path", []
    if ann_name in proj.pydantic_models:
        return "body", []
    return "query", []


def route_from_func(fn, deco, method, path, var, rel, proj):
    full_path = proj.full_prefix(var) + path
    path_params = set(PATH_PARAM.findall(full_path))
    params = {"path": [], "query": [], "form": [], "body": [], "file": []}
    deps = depends_names(unparse(kw(deco, "dependencies")))
    a = fn.args
    all_args = a.posonlyargs + a.args + a.kwonlyargs
    defaults = [None] * (len(a.posonlyargs) + len(a.args) - len(a.defaults)) + list(a.defaults) + list(a.kw_defaults)
    for arg, default in zip(all_args, defaults):
        if arg.arg == "self":
            continue
        kind, d = classify_param(arg, default, path_params, proj)
        if kind:
            params[kind].append(arg.arg)
        deps.extend(x for x in d if x not in deps)
    src = unparse(fn)
    kinds = set()
    for n in body_nodes(fn.body):
        if isinstance(n, ast.Return) and n.value is not None:
            t = tail(n.value) if isinstance(n.value, ast.Call) else None
            matched = next((rt for ct, rt in RESPONSE_TYPES if t == ct), None)
            if matched:
                kinds.add(matched)
            elif isinstance(n.value, (ast.Dict, ast.List, ast.ListComp, ast.DictComp)):
                kinds.add("json")
            elif isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                kinds.add("html" if tail(kw(deco, "response_class")) == "HTMLResponse" else "plain")
    if kw(deco, "response_model") is not None:
        kinds.add("json")
    if not kinds:  # response built in a variable then returned: resp = RedirectResponse(...); return resp
        kinds.update(rt for ct, rt in RESPONSE_TYPES if f"{ct}(" in src)
    order = [rt for _, rt in RESPONSE_TYPES]
    ranked = sorted(kinds, key=order.index)
    response_type = "|".join(ranked) or "unknown"  # several kinds -> "template|redirect" (primary first)
    tpls = []
    for n in body_nodes(fn.body):
        if not isinstance(n, ast.Call):
            continue
        t = tail(n)
        s = None
        if t == "TemplateResponse":
            s = const_str(kw(n, "name")) or next((const_str(x) for x in n.args if const_str(x)), None)
        elif t == "get_template" and n.args:
            s = const_str(n.args[0])
        elif t == "render_prompt" and n.args and const_str(n.args[0]):
            s = f"prompts/{const_str(n.args[0])}.txt"
        if s and s not in tpls:
            tpls.append(s)
    codes = set()
    for n in body_nodes(fn.body):
        if isinstance(n, ast.Call):
            if tail(n) == "HTTPException" and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, int):
                codes.add(n.args[0].value)
            sc = kw(n, "status_code")
            if isinstance(sc, ast.Constant) and isinstance(sc.value, int):
                codes.add(sc.value)
            elif sc is not None:
                m = re.search(r"HTTP_(\d{3})", unparse(sc))
                if m:
                    codes.add(int(m.group(1)))
    return {
        "method": method, "path": full_path, "func": fn.name, "file": rel, "line": fn.lineno,
        "params": params, "dependencies": deps, "response_type": response_type,
        "templates_rendered": tpls,
        "hx_headers": sorted(set(re.findall(r"HX-[A-Za-z-]+", src))),
        "status_codes": sorted(codes),
    }


def collect_routes(proj):
    routes, unknown_vars = [], set()
    for rel, tree, _ in proj.mods:
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in fn.decorator_list:
                if not (isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute)):
                    continue
                attr, var = deco.func.attr, dotted(deco.func.value)
                methods = []
                if attr in HTTP_METHODS:
                    methods = [attr.upper()]
                elif attr == "api_route":
                    m = kw(deco, "methods")
                    methods = [const_str(x).upper() for x in getattr(m, "elts", []) if const_str(x)] or ["GET"]
                elif attr == "websocket":
                    methods = ["WS"]
                if not methods:
                    continue
                path = const_str(deco.args[0]) if deco.args else const_str(kw(deco, "path"))
                if path is None:
                    warn(f"{rel}:{fn.lineno}: route {fn.name} has non-literal path, skipped")
                    continue
                if var not in proj.app_vars and var not in proj.router_own_prefix:
                    unknown_vars.add(var)
                for method in methods:
                    try:
                        routes.append(route_from_func(fn, deco, method, path, var, rel, proj))
                    except Exception as e:  # never crash on odd code
                        warn(f"{rel}:{fn.lineno}: could not analyse route {fn.name}: {e}")
    for v in sorted(unknown_vars, key=str):
        warn(f"route decorator on unknown object {v!r} (not an APIRouter/FastAPI assignment) — prefix assumed ''")
    return routes


# ---------- models ----------
def collect_models(proj):
    models = []
    for rel, tree, _ in proj.mods:
        for cls in ast.walk(tree):
            if not isinstance(cls, ast.ClassDef):
                continue
            if not any(k.arg == "table" and getattr(k.value, "value", None) is True for k in cls.keywords):
                continue
            table, schema, cols, rels = cls.name.lower(), None, [], []
            for st in cls.body:
                if isinstance(st, ast.Assign) and isinstance(st.targets[0], ast.Name):
                    if st.targets[0].id == "__tablename__":
                        table = const_str(st.value) or table
                    elif st.targets[0].id == "__table_args__":
                        m = re.search(r"['\"]schema['\"]\s*:\s*['\"](\w+)['\"]", unparse(st.value))
                        schema = m.group(1) if m else None
                elif isinstance(st, ast.AnnAssign) and isinstance(st.target, ast.Name):
                    name, ann = st.target.id, unparse(st.annotation)
                    if name.startswith("__") or ann.startswith("ClassVar"):
                        continue
                    d = st.value
                    field = d if isinstance(d, ast.Call) and tail(d) in {"Field", "Column"} else None
                    if isinstance(d, ast.Call) and tail(d) == "Relationship":
                        rels.append(name)
                        continue
                    nullable = bool(re.search(r"\bOptional\[|\|\s*None\b", ann))
                    py_default = False
                    if field is not None:
                        dv = kw(field, "default")
                        if dv is not None and not (isinstance(dv, ast.Constant) and dv.value is None):
                            py_default = True
                        if kw(field, "default_factory") is not None:
                            py_default = True
                        if isinstance(dv, ast.Constant) and dv.value is None:
                            nullable = True
                        if field.args and isinstance(field.args[0], ast.Constant) and field.args[0].value is None:
                            nullable = True
                    elif d is not None:
                        if isinstance(d, ast.Constant) and d.value is None:
                            nullable = True
                        else:
                            py_default = True
                    sa_type = None
                    if field is not None:
                        sac = kw(field, "sa_column")
                        if isinstance(sac, ast.Call) and sac.args:
                            sa_type = unparse(sac.args[0]).split("(")[0]
                        elif kw(field, "sa_type") is not None:
                            sa_type = unparse(kw(field, "sa_type")).split("(")[0]
                    cols.append({
                        "name": name, "py_type": ann, "nullable": nullable,
                        "primary_key": field is not None and getattr(kw(field, "primary_key"), "value", False) is True,
                        "foreign_key": const_str(kw(field, "foreign_key")) if field is not None else None,
                        "index": field is not None and getattr(kw(field, "index"), "value", False) is True,
                        "unique": field is not None and getattr(kw(field, "unique"), "value", False) is True,
                        "python_default": py_default, "sa_type": sa_type,
                    })
            models.append({"class": cls.name, "table": table, "schema": schema, "file": rel, "line": cls.lineno,
                           "columns": cols, "relationships": rels})
    return models


# ---------- templates ----------
JINJA_EXPR = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.S)


def collect_templates(root):
    tdir = root / "templates"
    files = list(iter_files(tdir, ".html")) + sorted((tdir / "prompts").glob("*.txt")) if tdir.is_dir() else []
    srcs = {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8", errors="replace") for p in files}
    all_macros = set()
    for s in srcs.values():
        all_macros.update(re.findall(r"\{%-?\s*macro\s+(\w+)\s*\(", s))
    out = []
    for rel, s in srcs.items():
        jinja = " ".join(JINJA_EXPR.findall(s))
        defined = re.findall(r"\{%-?\s*macro\s+(\w+)\s*\(", s)
        used = sorted({m for m in re.findall(r"(?<![\w.])(?:\w+\.)?(\w+)\s*\(", jinja) if m in all_macros and m not in defined})
        filters = {}
        for f in re.findall(r"\|\s*(\w+)", jinja):
            filters[f] = filters.get(f, 0) + 1
        ext = re.search(r"\{%-?\s*extends\s+[\"']([^\"']+)", s)
        out.append({
            "file": rel,
            "extends": ext.group(1) if ext else None,
            "includes": re.findall(r"\{%-?\s*include\s+[\"']([^\"']+)", s),
            "macros_defined": defined,
            "macros_used": used,
            "from_imports": re.findall(r"\{%-?\s*(?:from|import)\s+[\"']([^\"']+)", s),
            "filters": dict(sorted(filters.items(), key=lambda kv: -kv[1])),
            "loop_vars": sorted(set(re.findall(r"\bloop\.\w+", jinja))),
            "url_for": re.findall(r"\burl_for\(\s*[\"']([^\"']+)", s),
            "request_reads": sorted(set(re.findall(r"\brequest(?:\.\w+)+", jinja))),
            "set_blocks": len(re.findall(r"\{%-?\s*set\b", s)),
            "safe_sites": len(re.findall(r"\|\s*safe\b", s)),
            "raw_blocks": len(re.findall(r"\{%-?\s*raw\b", s)),
            "tojson_double_quoted_attrs": len(re.findall(r"=\s*\"[^\"]*\|\s*tojson\b", s)),
        })
    return out


# ---------- misc python scans ----------
def collect_jinja_env(proj):
    env = {"filters": [], "globals": [], "tests": []}
    for rel, tree, _ in proj.mods:
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Subscript):
                tgt = node.targets[0]
                attr = tgt.value.attr if isinstance(tgt.value, ast.Attribute) else None
                if attr in env and "env" in (dotted(tgt.value) or ""):
                    env[attr].append({"name": const_str(tgt.slice) or unparse(tgt.slice), "file": rel, "line": node.lineno})
            elif isinstance(node, ast.Call) and tail(node) == "update" and isinstance(node.func, ast.Attribute):
                owner = node.func.value
                attr = owner.attr if isinstance(owner, ast.Attribute) else None
                if attr in env and "env" in (dotted(owner) or "") and node.args and isinstance(node.args[0], ast.Dict):
                    for k in node.args[0].keys:
                        env[attr].append({"name": const_str(k) or unparse(k), "file": rel, "line": node.lineno})
                    for k in node.keywords:
                        env[attr].append({"name": k.arg, "file": rel, "line": node.lineno})
    return env


def collect_env_vars(proj):
    found = {}  # name -> record

    def add(name, default, required, rel, line):
        r = found.setdefault(name, {"name": name, "default": None, "required": False, "file": rel, "line": line})
        r["required"] = r["required"] or required
        if r["default"] is None and default is not None:
            r["default"] = default

    for rel, tree, _ in proj.mods:
        var_to_env = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                d = dotted(node) or ""
                t = d.rsplit(".", 1)[-1]
                name = const_str(node.args[0]) if node.args else None
                if name is None:
                    continue
                if t in {"getenv", "get"} and (d.startswith("os.") or d in {"getenv", "environ.get"}):
                    if t == "get" and not d.endswith("environ.get"):
                        continue
                    default = unparse(node.args[1]) if len(node.args) > 1 else unparse(kw(node, "default")) or None
                    add(name, default, False, rel, node.lineno)
                elif t in {"_assert_env", "MustEnv", "require_env", "assert_env"}:
                    add(name, None, True, rel, node.lineno)
            elif isinstance(node, ast.Subscript) and dotted(node.value) in {"os.environ", "environ"}:
                name = const_str(node.slice)
                if name:
                    add(name, None, True, rel, node.lineno)
            if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and isinstance(node.value, ast.Call):
                d = dotted(node.value) or ""
                if d.endswith(("getenv", "environ.get")) and node.value.args and const_str(node.value.args[0]):
                    var_to_env[node.targets[0].id] = const_str(node.value.args[0])
        for node in ast.walk(tree):  # `if not VAR: raise ...` after VAR = os.getenv(...)
            if isinstance(node, ast.If) and isinstance(node.test, ast.UnaryOp) and isinstance(node.test.op, ast.Not) \
                    and isinstance(node.test.operand, ast.Name) and node.test.operand.id in var_to_env \
                    and any(isinstance(s, ast.Raise) for s in node.body):
                add(var_to_env[node.test.operand.id], None, True, rel, node.lineno)
    return sorted(found.values(), key=lambda r: (not r["required"], r["name"]))


def collect_imports(proj):
    local_pkgs = {p.stem for p in proj.root.iterdir() if p.suffix == ".py"} | \
                 {p.name for p in proj.root.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
    third, features = {}, set()
    for rel, tree, src in proj.mods:
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for n in names:
                top = n.split(".")[0]
                if top in FEATURE_MAP:
                    features.add(FEATURE_MAP[top])
                if top in sys.stdlib_module_names or top in local_pkgs:
                    continue
                third.setdefault(top, [])
                if rel not in third[top]:
                    third[top].append(rel)
        if re.search(r"\bWebSocket\b|\.websocket\(", src):
            features.add("websockets")
    return dict(sorted(third.items())), sorted(features)


def collect_decorator_stuff(proj):
    caches, bg, mws, handlers, lifespan = [], [], [], [], []
    for rel, tree, _ in proj.mods:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for deco in node.decorator_list:
                    t, d = tail(deco), dotted(deco) or ""
                    if t == "cache":
                        c = deco if isinstance(deco, ast.Call) else None
                        caches.append({"func": node.name, "namespace": const_str(kw(c, "namespace")) if c else None,
                                       "expire": unparse(kw(c, "expire")) or None if c else None, "file": rel, "line": node.lineno})
                    elif t == "middleware" and isinstance(deco, ast.Call):
                        mws.append({"name": node.name, "file": rel, "line": node.lineno})
                    elif t == "exception_handler" and isinstance(deco, ast.Call) and deco.args:
                        handlers.append({"exc_type": unparse(deco.args[0]), "file": rel, "line": node.lineno})
                    if t == "asynccontextmanager" and node.name == "lifespan" or (node.name == "lifespan" and not lifespan):
                        seen = []
                        for n in body_nodes(node.body):
                            if isinstance(n, ast.Call):
                                d2 = dotted(n)
                                if d2 and d2.rsplit(".", 1)[-1] not in NOISE_CALLS and d2 not in seen:
                                    seen.append(d2)
                        lifespan = seen
            elif isinstance(node, ast.Call):
                t = tail(node)
                if t == "add_task" and node.args:
                    bg.append({"file": rel, "line": node.lineno, "func_added": unparse(node.args[0])})
                elif t == "add_middleware" and node.args:
                    mws.append({"name": unparse(node.args[0]), "file": rel, "line": node.lineno})
                elif t == "add_exception_handler" and node.args:
                    handlers.append({"exc_type": unparse(node.args[0]), "file": rel, "line": node.lineno})
    return caches, bg, mws, handlers, lifespan


def collect_tests(proj):
    dirs = sorted({p.relative_to(proj.root).as_posix() for p in proj.root.rglob("*")
                   if p.is_dir() and p.name in {"tests", "test"} and not any(x in SKIP_DIRS for x in p.parts)})
    importing = []
    for rel, tree, _ in proj.mods:
        if not any(rel.startswith(d + "/") for d in dirs):
            continue
        for node in ast.walk(tree):
            mod = None
            if isinstance(node, ast.Import):
                mod = next((a.name for a in node.names if a.name.split(".")[0] == "app"), None)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module.split(".")[0] == "app":
                mod = node.module
            if mod:
                importing.append(rel)
                break
    conftest = proj.root / "tests" / "conftest.py"
    snippet = None
    if conftest.exists():
        for line in conftest.read_text(encoding="utf-8", errors="replace").splitlines():
            if re.search(r"uvicorn|Popen|subprocess", line):
                snippet = line.strip()
                break
    return {"dirs": dirs, "files_importing_app": importing, "conftest_server_start": snippet}


def read_or_none(p):
    return p.read_text(encoding="utf-8", errors="replace").strip() if p.exists() else None


def collect_deploy(root):
    mk = read_or_none(root / "Makefile") or ""
    targets = [t for t in re.findall(r"^([A-Za-z_][\w-]*):(?!=)", mk, re.M) if t != "PHONY"]
    wfs = []
    for p in sorted((root / ".github" / "workflows").glob("*.y*ml")):
        s = p.read_text(encoding="utf-8", errors="replace")
        wfs.append({"file": p.relative_to(root).as_posix(), "uses_uv": bool(re.search(r"\buv\b|setup-uv", s)),
                    "uses_alembic": "alembic" in s, "uses_pytest": "pytest" in s})
    return {"procfile": read_or_none(root / "Procfile"), "start_sh": read_or_none(root / "start.sh"),
            "makefile_targets": targets, "workflows": wfs}


def collect_pyproject(root):
    p = root / "pyproject.toml"
    if not p.exists():
        warn("pyproject.toml not found")
        return {"name": None, "dependencies": []}
    try:
        data = tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        warn(f"pyproject.toml: {e}")
        return {"name": None, "dependencies": []}
    proj = data.get("project", {})
    return {"name": proj.get("name"), "dependencies": proj.get("dependencies", [])}


# ---------- go routes ----------
def norm_route(method, path, go=False):
    if go:
        path = path.replace("/{$}", "/")
        path = re.sub(r"\{\w+\.\.\.\}", "{*}", path)
    else:
        path = re.sub(r"\{\w+:path\}", "{*}", path)
    path = re.sub(r"\{\w+\}", "{_}", path)
    if len(path) > 1:
        path = path.rstrip("/")
    return f"{method} {path or '/'}"


def go_routes_check(root, routes):
    go = {}  # normalised -> literal as written in Go
    for p in sorted((root / "internal" / "server").glob("*.go")):
        for m, path in re.findall(r"\"(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS) (/[^\"]*)\"", p.read_text(encoding="utf-8", errors="replace")):
            if not path.startswith("/static/"):
                go.setdefault(norm_route(m, path, go=True), f"{m} {path}")
    py = {norm_route(r["method"], r["path"]): f"{r['method']} {r['path']}" for r in routes if r["method"] != "WS"}
    missing = sorted(py[k] for k in py if k not in go)
    extra = sorted(go[k] for k in go if k not in py)
    return {"missing_in_go": missing, "extra_in_go": extra}


# ---------- output ----------
def md_report(inv):
    L = []
    say = L.append
    say(f"# FastAPI inventory: {inv['pyproject']['name'] or '(no pyproject name)'}")
    say(f"routes {len(inv['routes'])} | models {len(inv['models'])} | templates {len(inv['templates'])} | "
        f"env vars {len(inv['env_vars'])} ({sum(e['required'] for e in inv['env_vars'])} required) | "
        f"grown features {len(inv['grown_features'])} | warnings {len(inv['warnings'])}\n")
    say("## Routes")
    by_file = {}
    for r in inv["routes"]:
        by_file.setdefault(r["file"], []).append(r)
    for f, rs in by_file.items():
        say(f"\n### {f}")
        say("| method | path | func | response | deps | params | templates |")
        say("|---|---|---|---|---|---|---|")
        for r in rs:
            ps = ", ".join(f"{k}:{'/'.join(v)}" for k, v in r["params"].items() if v)
            say(f"| {r['method']} | `{r['path']}` | {r['func']} | {r['response_type']} | {', '.join(r['dependencies'])} | {ps} | {', '.join(r['templates_rendered'])} |")
    if inv["routers"]:
        say("\nRouters: " + "; ".join(f"{x['var_name']} ({x['file']}, prefix={x['prefix']!r}{', deps=' + ','.join(x['dependencies']) if x['dependencies'] else ''})" for x in inv["routers"]))
    say("\n## Models")
    for m in inv["models"]:
        say(f"\n### {m['class']} -> {m['schema'] + '.' if m['schema'] else ''}{m['table']} ({m['file']})")
        say("| column | type | null | pk | fk | idx | uniq | py default | sa type |")
        say("|---|---|---|---|---|---|---|---|---|")
        for c in m["columns"]:
            say(f"| {c['name']} | `{c['py_type']}` | {'y' if c['nullable'] else ''} | {'y' if c['primary_key'] else ''} | {c['foreign_key'] or ''} | "
                f"{'y' if c['index'] else ''} | {'y' if c['unique'] else ''} | {'y' if c['python_default'] else ''} | {c['sa_type'] or ''} |")
        if m["relationships"]:
            say(f"relationships: {', '.join(m['relationships'])}")
    say("\n## Templates")
    for t in inv["templates"]:
        bits = []
        if t["extends"]:
            bits.append(f"extends {t['extends']}")
        if t["includes"]:
            bits.append("includes " + ", ".join(t["includes"]))
        if t["from_imports"]:
            bits.append("imports " + ", ".join(t["from_imports"]))
        if t["macros_defined"]:
            bits.append("macros " + ", ".join(t["macros_defined"]))
        if t["macros_used"]:
            bits.append("uses macros " + ", ".join(t["macros_used"]))
        if t["filters"]:
            bits.append("filters " + ", ".join(f"{k}x{v}" for k, v in list(t["filters"].items())[:5]))
        if t["url_for"]:
            bits.append("url_for " + ", ".join(t["url_for"]))
        if t["request_reads"]:
            bits.append("request" + ", request".join(t["request_reads"]))
        if t["loop_vars"]:
            bits.append(", ".join(t["loop_vars"]))
        for k in ("set_blocks", "safe_sites", "raw_blocks"):
            if t[k]:
                bits.append(f"{k}={t[k]}")
        if t["tojson_double_quoted_attrs"]:
            bits.append(f"**tojson in double-quoted attr x{t['tojson_double_quoted_attrs']}**")
        say(f"- `{t['file']}`: " + ("; ".join(bits) or "plain"))
    je = inv["jinja_env"]
    if any(je.values()):
        say("\n## Jinja env customs")
        for k, items in je.items():
            for i in items:
                say(f"- {k[:-1]} `{i['name']}` ({i['file']}:{i['line']})")
    say("\n## Env vars (required first)")
    for e in inv["env_vars"]:
        say(f"- {'**' if e['required'] else ''}{e['name']}{'**' if e['required'] else ''}"
            f"{' default=' + e['default'] if e['default'] else ''} ({e['file']}:{e['line']})")
    say("\n## Grown features")
    say(", ".join(inv["grown_features"]) or "none")
    say("third-party: " + ", ".join(inv["third_party_imports"]) if inv["third_party_imports"] else "third-party: none")
    for k, label in (("cache_decorators", "Cache decorators"), ("background_tasks", "Background tasks"),
                     ("middlewares", "Middlewares"), ("exception_handlers", "Exception handlers")):
        if inv[k]:
            say(f"\n## {label}")
            for x in inv[k]:
                desc = {k2: v for k2, v in x.items() if k2 not in ("file", "line")}
                say(f"- {', '.join(f'{a}={b}' for a, b in desc.items() if b is not None)} ({x['file']}:{x['line']})")
    if inv["lifespan_steps"]:
        say("\n## Lifespan steps\n" + ", ".join(inv["lifespan_steps"]))
    t, d = inv["tests"], inv["deploy"]
    say("\n## Tests")
    say(f"dirs: {', '.join(t['dirs']) or 'none'}; files importing app: {len(t['files_importing_app'])}; "
        f"conftest server start: {t['conftest_server_start'] or 'none'}")
    say("\n## Deploy")
    say(f"Procfile: {d['procfile'] or 'none'}")
    say(f"start.sh: {'present' if d['start_sh'] else 'none'}; Makefile targets: {', '.join(d['makefile_targets']) or 'none'}")
    for w in d["workflows"]:
        say(f"- {w['file']}: uv={w['uses_uv']} alembic={w['uses_alembic']} pytest={w['uses_pytest']}")
    say(f"pyproject deps: {len(inv['pyproject']['dependencies'])}")
    if inv["warnings"]:
        say("\n## Warnings")
        for w in inv["warnings"]:
            say(f"- {w}")
    return "\n".join(L)


def build(root):
    proj = Project(root, parse_modules(root))
    caches, bg, mws, handlers, lifespan = collect_decorator_stuff(proj)
    third, features = collect_imports(proj)
    return {
        "routers": proj.routers,
        "routes": collect_routes(proj),
        "models": collect_models(proj),
        "templates": collect_templates(root),
        "jinja_env": collect_jinja_env(proj),
        "env_vars": collect_env_vars(proj),
        "third_party_imports": third,
        "grown_features": features,
        "cache_decorators": caches,
        "background_tasks": bg,
        "middlewares": mws,
        "exception_handlers": handlers,
        "lifespan_steps": lifespan,
        "tests": collect_tests(proj),
        "deploy": collect_deploy(root),
        "pyproject": collect_pyproject(root),
        "warnings": W,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true")
    g.add_argument("--md", action="store_true")
    ap.add_argument("--go-routes", action="store_true")
    args = ap.parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        sys.exit(f"not a directory: {root}")
    inv = build(root)
    rc = 0
    if args.go_routes:
        inv["go_routes"] = go_routes_check(root, inv["routes"])
        rc = 1 if inv["go_routes"]["missing_in_go"] else 0
    if args.json:
        json.dump(inv, sys.stdout, indent=2)
        print()
    else:
        print(md_report(inv))
        if args.go_routes:
            gr = inv["go_routes"]
            print("\n## Go route check")
            print("MISSING IN GO:\n" + ("\n".join(f"- {x}" for x in gr["missing_in_go"]) or "- (none)"))
            print("EXTRA IN GO:\n" + ("\n".join(f"- {x}" for x in gr["extra_in_go"]) or "- (none)"))
    sys.exit(rc)


if __name__ == "__main__":
    main()
