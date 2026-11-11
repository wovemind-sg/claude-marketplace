#!/usr/bin/env bash
# Build the ui-audit eval fixture: a tiny static site (python3 -m http.server) in a git repo.
# Usage: make_fixture.sh <empty dir> [port, default 8123]
# Branch `pr` = c0 (base) .. c4 (head), checked out. Branch `followup` = c5 on top of c4 (incremental eval).
# Needs a free port and the next one (the skill serves base on port+1).
set -euo pipefail
D=${1:?usage: make_fixture.sh <dir> [port]}
PORT=${2:-8123}
mkdir -p "$D" && cd "$D"
[ -z "$(ls -A .)" ] || { echo "$D is not empty" >&2; exit 1; }
git init -q -b pr
git config user.email fixture@example.com && git config user.name fixture
commit() { git add -A && git commit -q -m "$1"; git tag "$2"; }

# ---- c0: base ----
cat > style.css <<'CSS'
body{font-family:system-ui,sans-serif;margin:0;padding:24px;background:#fff;color:#111}
main{max-width:420px;margin:0 auto}
input,button{font-size:16px;padding:10px;margin:6px 0;width:100%;box-sizing:border-box}
button{background:#2b5cff;color:#fff;border:0;border-radius:6px}
CSS
cat > index.html <<'HTML'
<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=stylesheet href=style.css><title>Home</title>
<main><h1>Acme</h1><p>Book a lesson.</p><a href=login.html>Log in</a></main>
HTML
cat > login.html <<'HTML'
<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=stylesheet href=style.css><title>Log in</title>
<main><h1>Log in</h1>
<form><label>Phone or email<input name=contact id=contact autocomplete=off></label><button type=submit>Continue</button></form></main>
HTML
for f in verify verify-alias; do cat > $f.html <<'HTML'
<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=stylesheet href=style.css><title>Verify</title>
<main><h1>Verify your phone.</h1><p>We sent you a code.</p></main>
HTML
done
cat > old-verify.html <<'HTML'
<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=stylesheet href=style.css><title>Verify (old)</title>
<main><h1>Verify your phone number</h1><p>Enter the code we sent.</p></main>
HTML
cat > client-signup.html <<'HTML'
<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=stylesheet href=style.css><title>Client sign up</title>
<main><h1>Client sign up</h1><form><input placeholder=Name><button>Sign up</button></form></main>
HTML
cat > PR_BODY.md <<'MD'
# PR #7: Unknown-account errors and mobile verification

## What changed
- Logging in with an unknown phone number or email now shows an inline error under the form.
- The same form is on the schedule deep-link page (/schedule.html?token=abc), which is new and shows "Verify your mobile." with a Terms box.
- The verify pages say "Verify your mobile." instead of "Verify your phone."
- old-verify.html now redirects to verify.html.
- client-signup.html is removed.
- Dark mode support in the stylesheet.
MD
mkdir .ui-audit
cat > .ui-audit/config.json <<JSON
{
  "version": 1,
  "platforms": ["web"],
  "default_baseline_mode": "base+head",
  "web": {"launch": "python3 -m http.server $PORT", "cwd": ".", "base_url": "http://localhost:$PORT", "ready_url": "http://localhost:$PORT/index.html"},
  "viewports": {
    "desktop": {"width": 1440, "height": 900},
    "mobile": {"width": 390, "height": 844, "device_scale_factor": 3, "is_mobile": true, "has_touch": true}
  },
  "screens": [
    {"name": "home", "route": "/index.html", "states": [{"name": "default"}]},
    {"name": "login", "route": "/login.html", "states": [{"name": "default"}]},
    {"name": "schedule", "route": "/schedule.html?token=abc", "states": [{"name": "default"}]},
    {"name": "verify", "route": "/verify.html", "states": [{"name": "default"}]},
    {"name": "verify-alias", "route": "/verify-alias.html", "states": [{"name": "default"}]},
    {"name": "old-verify", "route": "/old-verify.html", "states": [{"name": "default"}]},
    {"name": "client-signup", "route": "/client-signup.html", "states": [{"name": "default"}]}
  ],
  "diff": {"threshold": 0.1, "min_changed_pct": 0.01},
  "report": {"default_view": "side"}
}
JSON
commit "c0: base site" c0

# ---- c1: unknown-account error on the login form ----
cat > form.js <<'JS'
document.querySelector('form').addEventListener('submit', function (e) {
  e.preventDefault();
  var v = document.getElementById('contact').value.trim();
  var kind = v.indexOf('@') > -1 ? 'email' : 'phone';
  var p = document.getElementById('err') || document.createElement('p');
  p.id = 'err'; p.style.color = '#c00';
  p.textContent = v ? 'No account found.' : 'Enter your ' + kind + '.';
  this.appendChild(p);
});
JS
sed -i.bak 's#</main>#<script src=form.js></script></main>#' login.html && rm login.html.bak
commit "c1: show No account found. for an unknown phone or email on login" c1

# ---- c2: schedule deep-link page + verify wording ----
cat > schedule.html <<'HTML'
<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=stylesheet href=style.css><title>Schedule</title>
<main><h1>Verify your mobile.</h1>
<form><label>Phone or email<input name=contact id=contact autocomplete=off></label>
<label class=terms><input type=checkbox id=terms style="width:auto"> I accept the Terms</label>
<button type=submit>Continue</button></form>
<script src=form.js></script></main>
HTML
echo '.terms{display:block;margin:8px 0;font-size:14px}' >> style.css
for f in verify verify-alias; do sed -i.bak 's/Verify your phone\./Verify your mobile./' $f.html && rm $f.html.bak; done
commit "c2: schedule deep-link page with Terms box; verify says Verify your mobile." c2

# ---- c3: redirect, delete, dark mode ----
cat > old-verify.html <<'HTML'
<!doctype html><meta charset=utf-8><title>Redirecting</title>
<script>location.replace('verify.html')</script><meta http-equiv=refresh content="0;url=verify.html">
HTML
git rm -q client-signup.html
cat >> style.css <<'CSS'
@media (prefers-color-scheme:dark){body{background:#111;color:#eee}}
CSS
commit "c3: old-verify redirects to verify, remove client-signup, dark mode" c3

# ---- c4: head of the PR ----
git commit -q --allow-empty -m "c4: head of PR" && git tag c4

# ---- c5 (branch followup): rename schedule -> schedule-link, change the error text ----
git checkout -q -b followup
sed -i.bak "s/No account found\./We could not find that account./" form.js && rm form.js.bak
sed -i.bak 's/"name": "schedule"/"name": "schedule-link"/' .ui-audit/config.json && rm .ui-audit/config.json.bak
commit "c5: reword unknown-account error, rename schedule screen to schedule-link" c5
git checkout -q pr
echo "fixture ready in $D (branch pr = c0..c4, branch followup = c5), port $PORT"
