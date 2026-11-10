#!/usr/bin/env python3
"""Detect compliance-relevant signals in a repo: stack, SDKs, permissions, legal pages, data-rights endpoints.

Usage:
  detect_signals.py <repo> [--json]
  detect_signals.py --selftest

Output (--json): {"stack": {...}, "signals": {"<id>": [{"file","line","match"}]}, "missing": [...]}
Regex-based worklist, not a verdict: open every cited file:line before relying on it. "missing" means
"not detected by this script", never "absent". Secret values are redacted in the match text.
Python 3 stdlib only.
"""
import json
import os
import re
import sys

PRUNE = {".git", "node_modules", ".venv", "venv", "dist", "build", "Pods", "DerivedData", ".next", "target",
         "vendor", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".expo", ".gradle",
         "graphify-out", ".playwright-cli", "coverage", ".idea", ".claude", "site-packages"}
LOCKFILES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "go.sum", "Podfile.lock", "Gemfile.lock"}
TEXT_EXT = (".py", ".go", ".ts", ".tsx", ".js", ".jsx", ".swift", ".kt", ".java", ".html", ".jinja", ".j2",
            ".json", ".toml", ".yaml", ".yml", ".plist", ".xml", ".xcprivacy", ".sql", ".cfg", ".ini", ".env.example",
            ".gradle", ".kts", ".txt", ".pbxproj")
TEXT_NAMES = re.compile(r"^(Dockerfile[\w.-]*|Procfile|Podfile|railway\.json|railway\.toml|docker-compose[\w.-]*|go\.mod|security\.txt)$")
MAX_BYTES = 1_000_000
MAX_HITS = 5

# Lines in test files and comment lines never count (stops "# TODO delete account" or a test fixture
# from looking like a shipped endpoint).
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|e2e|fixtures)/|(^|/)test_[^/]*\.py$|_test\.(py|go)$|\.(test|spec)\.[jt]sx?$")
COMMENT = re.compile(r"^\s*(#(?!!)|//|/\*|\*|<!--|--\s|\{#)")
# Markdown is prose (READMEs, plans) and is not content-scanned; a privacy.md/terms.md still counts via PRESENCE.

I = re.I
P = re.compile
MANIFEST = P(r"(^|/)(pyproject\.toml|requirements[^/]*\.txt|setup\.cfg|Pipfile|uv\.lock|poetry\.lock|package\.json|go\.mod|Podfile|build\.gradle(\.kts)?)$")
NATIVE_CFG = P(r"(Info\.plist|AndroidManifest\.xml|app\.json|app\.config\.[jt]s|capacitor\.config\.\w+|\.entitlements)$")

# Content signals: id -> list of (path_filter or None, pattern).
SIGNALS = {
    "backend.fastapi": [(MANIFEST, P(r"\bfastapi\b", I)), (None, P(r"^\s*from fastapi import|FastAPI\(\)"))],
    "backend.go": [(P(r"(^|/)go\.mod$"), P(r"^module\s+\S+"))],
    "db.postgres": [(None, P(r"\b(psycopg2?|asyncpg|sqlalchemy|jackc/pgx|lib/pq|DATABASE_URL)\b|postgres(ql)?(\+\w+)?://", I))],
    "cache.redis": [(None, P(r"\b(redis|aioredis|go-redis|REDIS_URL)\b|rediss?://|^\s*(from|import)\s+arq\b|[\"']arq[\"'>=<~ ]", I))],
    "deploy.railway": [(None, P(r"\bRAILWAY_[A-Z_]+\b|\.up\.railway\.app|railway\.(app|com)/"))],
    "mobile.capacitor": [(P(r"(^|/)package\.json$"), P(r"\"@capacitor/core\""))],
    "mobile.react_native": [(P(r"(^|/)package\.json$"), P(r"\"(react-native|expo)\"\s*:"))],
    "auth.accounts": [(None, P(r"\b(password_hash|hashed_password|passlib|get_current_user|login_required|createUserWithEmailAndPassword|signInWithPassword|SessionMiddleware)\b|^\s*class\s+User\b"))],
    "auth.oauth.google": [(None, P(r"accounts\.google\.com|GoogleSignIn|google-auth-library|capacitor-google-auth|@react-native-google-signin|GoogleAuthProvider|oauth2\.googleapis\.com"))],
    "auth.oauth.apple": [(None, P(r"appleid\.apple\.com|ASAuthorizationAppleID|SignInWithApple|sign-in-with-apple|expo-apple-authentication|usesAppleSignIn", I))],
    "auth.oauth.github": [(None, P(r"github\.com/login/oauth"))],
    "auth.oauth.facebook": [(None, P(r"facebook\.com/(v[\d.]+/)?dialog/oauth|FBSDKLoginKit|react-native-fbsdk|FacebookAuthProvider"))],
    "auth.oauth.microsoft": [(None, P(r"login\.microsoftonline\.com"))],
    "pay.stripe": [(None, P(r"^\s*(import|from)\s+stripe\b|[\"']stripe[\"']|@stripe/|stripe-go|js\.stripe\.com|api\.stripe\.com|\bSTRIPE_[A-Z_]+|\bstripe\.\w+\.(create|retrieve|construct_event)"))],
    "pay.revenuecat": [(None, P(r"revenuecat|react-native-purchases|purchases-capacitor", I))],
    "pay.storekit": [(None, P(r"^\s*import StoreKit\b|SKPaymentQueue|\bProduct\.products\(|\bTransaction\.updates\b|expo-in-app-purchases|react-native-iap"))],
    "pay.playbilling": [(None, P(r"com\.android\.billingclient|com\.android\.vending\.BILLING|\bBillingClient\b"))],
    "pay.paddle": [(None, P(r"paddle\.js|paddle\.com|paddle-python|paddle_billing|@paddle/|\bPADDLE_[A-Z_]+"))],
    "pay.lemonsqueezy": [(None, P(r"lemon\s?squeezy", I))],
    "ai.anthropic": [(None, P(r"^\s*(import|from)\s+anthropic\b|[\"']anthropic[\"']|@anthropic-ai/sdk|\bAsyncAnthropic\(|\bAnthropic\(|api\.anthropic\.com|ANTHROPIC_API_KEY|anthropic-sdk-go"))],
    "ai.openai": [(None, P(r"^\s*(import|from)\s+openai\b|[\"']openai[\"']|\bAsync(Azure)?OpenAI\(|\bOpenAI\(|api\.openai\.com|OPENAI_API_KEY|go-openai|openai-go"))],
    "ai.openrouter": [(None, P(r"openrouter", I))],
    "ai.google": [(None, P(r"google-generativeai|google\.genai|google-genai|generativelanguage\.googleapis|@google/generative-ai|vertexai|\bgemini-[\d.]"))],
    "ai.litellm": [(None, P(r"\blitellm\b", I))],
    "ai.langchain": [(None, P(r"\blangchain", I))],
    "ai.ollama": [(None, P(r"\bollama\b", I))],
    "track.analytics.firebase": [(None, P(r"firebase[-_/]?analytics|@capacitor-firebase/analytics|@react-native-firebase/analytics|FirebaseAnalytics", I))],
    "track.analytics.google": [(None, P(r"gtag\(|googletagmanager\.com|google-analytics\.com|\bGA_MEASUREMENT_ID\b"))],
    "track.analytics.segment": [(None, P(r"@segment/|analytics-node|segment\.(io|com)|segment-analytics", I))],
    "track.analytics.mixpanel": [(None, P(r"mixpanel", I))],
    "track.analytics.posthog": [(None, P(r"posthog", I))],
    "track.analytics.amplitude": [(None, P(r"@amplitude/|amplitude-js|amplitude\.com|amplitude\.init|Amplitude\.(init|instance)"))],
    "track.analytics.sentry": [(None, P(r"sentry[-_]sdk|@sentry/|sentry\.io|Sentry\.init|sentry_sdk\.init|getsentry/sentry-go", I))],
    "track.analytics.plausible": [(None, P(r"plausible\.io", I))],
    "track.analytics.hotjar": [(None, P(r"hotjar|clarity\.ms", I))],
    "comm.email": [(None, P(r"\b(resend|sendgrid|postmark|mailgun|smtplib|aiosmtplib|fastapi[-_]mail|nodemailer|SMTP_HOST|amazonses|sesv2)\b|client\(\s*[\"']ses[\"']", I))],
    "comm.push": [(None, P(r"firebase[-_]?messaging|fcm\.googleapis|\bFCM\b|\bAPNs\b|\bapns2?\b|pywebpush|web-push|@capacitor/push-notifications|expo-notifications|UNUserNotificationCenter|PushManager"))],
    "comm.sms": [(None, P(r"\b(twilio|vonage|nexmo|messagebird|plivo)\b|sns\.publish", I))],
    "web.cookies": [(None, P(r"set_cookie\(|document\.cookie|SessionMiddleware|http\.SetCookie|res\.cookie\(|Set-Cookie", I))],
    "perm.location": [(None, P(r"NSLocation\w*UsageDescription|android\.permission\.ACCESS_(FINE|COARSE|BACKGROUND)_LOCATION|@capacitor/geolocation|expo-location|navigator\.geolocation|CLLocationManager"))],
    "perm.camera": [(None, P(r"NSCameraUsageDescription|android\.permission\.CAMERA|@capacitor/camera|expo-camera|expo-image-picker|AVCaptureDevice"))],
    "perm.mic": [(None, P(r"NSMicrophoneUsageDescription|android\.permission\.RECORD_AUDIO|expo-av|expo-audio|getUserMedia\(\s*\{[^}]*audio"))],
    "perm.contacts": [(None, P(r"NSContactsUsageDescription|android\.permission\.READ_CONTACTS|expo-contacts|@capacitor-community/contacts|CNContactStore"))],
    "perm.biometrics": [(None, P(r"NSFaceIDUsageDescription|android\.permission\.USE_(BIOMETRIC|FINGERPRINT)|expo-local-authentication|LAContext|BiometricPrompt"))],
    "perm.health": [(None, P(r"NSHealth\w*UsageDescription|android\.permission\.BODY_SENSORS|android\.permission\.health\.|HKHealthStore|react-native-health"))],
    "legal.privacy_policy_page": [(None, P(r"[\"'][\w/{}.-]*/privacy[\w/-]*[\"']|privacy[-_ ]policy|privacy\.(html|jinja|j2|md)", I))],
    "legal.terms_page": [(None, P(r"[\"'][\w/{}.-]*/(terms|tos)[\w/-]*[\"']|terms[-_ ]of[-_ ](service|use)|terms\.(html|jinja|j2|md)", I))],
    "account.delete_endpoint": [(None, P(r"delete[_-]?(my[_-]?)?account|/account/delete|deleteAccount|deleteUser\b|\bdelete_\w*(user|profile|family|my)_?data\b|[\"'][^\"']*/(account|me|privacy|settings|profile|users?)/delete[\w-]*[\"']|@\w+\.delete\(\s*[\"'][^\"']*/(users?(/\{\w+\})?|me|account)/?[\"']|DELETE\s+/(api/)?(v\d/)?(users?(/\{\w+\})?|me|account)/?[\"'\s]", I))],
    "account.export_endpoint": [(None, P(r"export[_-]?(my[_-]?)?(user[_-]?)?data|data[_-]?export|download[_-]?(my[_-]?)?data|/account/export", I))],
    "consent.banner": [(None, P(r"cookie.?consent|cookie[-_]banner|(?-i:\bCMP\b)|klaro|onetrust|cookiebot|osano|termly|AppTrackingTransparency|requestTrackingPermissions", I))],
    "retention.job": [(None, P(r"\b(cron|celery|apscheduler|add_job|repeat_every|beat_schedule|cron_jobs)\b.{0,80}(delete|purge|retention|cleanup|expire)|\b(purge|retention|cleanup)_\w+.{0,80}\b(cron|add_job|beat_schedule)\b", I))],
    "log.pii_risk": [(None, P(r"\b(log(ger|ging)?|slog|console)\.(info|debug|warning|warn|error|log|Info|Debug|Warn|Error)\w*\(.*\b(email|phone|password|token|ssn)\b", I))],
    "security.encryption": [(None, P(r"\b(fernet|AES|bcrypt|argon2|pgcrypto|scrypt|CryptoKit|EncryptedSharedPreferences|SecureStore|Keychain)\b|cryptography\.", I))],
    "security.tls": [(None, P(r"sslmode=|ssl=true|rediss://|requirepass|HTTPSRedirectMiddleware|Strict-Transport-Security|\btls\.Config\b", I))],
    "security.secrets_in_repo": [(None, P(r"sk_live_[0-9A-Za-z]{10,}|sk-ant-[\w-]{20,}|sk-(proj-)?[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|-----BEGIN ([A-Z]+ )?PRIVATE KEY-----|xox[baprs]-[\w-]{10,}|ghp_[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{35}"))],
    "security.txt": [(None, P(r"/\.well-known/security\.txt"))],
    "sbom.present": [(P(r"\.(ya?ml)$"), P(r"\b(syft|cyclonedx|anchore/sbom-action|spdx)\b", I))],
}
# Path-presence signals: id -> path regex (hit recorded at line 1).
PRESENCE = {
    "deploy.railway": P(r"(^|/)(railway\.json|railway\.toml)$"),
    "mobile.ios": P(r"\.xcodeproj/|(^|/)(Info\.plist|Podfile)$"),
    "mobile.ios.privacy_manifest": P(r"(^|/)PrivacyInfo\.xcprivacy$"),
    "mobile.android": P(r"(^|/)(AndroidManifest\.xml|build\.gradle(\.kts)?)$"),
    "mobile.capacitor": P(r"(^|/)capacitor\.config\.\w+$"),
    "legal.privacy_policy_page": P(r"(^|/)privacy[\w-]*\.(html|jinja|j2|md|tsx|jsx)$", I),
    "legal.terms_page": P(r"(^|/)(terms|tos)[\w-]*\.(html|jinja|j2|md|tsx|jsx)$", I),
    "security.txt": P(r"(^|/)security\.txt$"),
    "sbom.present": P(r"(^|/)([\w.-]*bom\.json|[\w.-]*\.spdx(\.json)?|sbom[\w.-]*)$", I),
}
SECRET_IDS = {"security.secrets_in_repo"}
FAMILIES = ("auth.oauth.", "pay.", "ai.", "track.analytics.", "perm.")
STACK_GROUPS = ("backend", "db", "cache", "deploy", "mobile")


def ids_for_line(rel, line):
    """Signal IDs matched by one line of file `rel` (pure; used by scan and selftest)."""
    if COMMENT.match(line):
        return {}
    out = {}
    for sid, rules in SIGNALS.items():
        for path_rx, rx in rules:
            if path_rx and not path_rx.search(rel):
                continue
            m = rx.search(line)
            if m:
                out[sid] = m.group(0)
                break
    return out


def redact(sid, text):
    return text[:6] + "...[redacted]" if sid in SECRET_IDS else text.strip()[:120]


def wanted(name):
    return name.endswith(TEXT_EXT) or bool(TEXT_NAMES.match(name)) or name == "PrivacyInfo.xcprivacy"


def scan(repo):
    hits = {}
    me = os.path.realpath(__file__)

    def add(sid, rel, ln, text):
        lst = hits.setdefault(sid, [])
        if len(lst) < MAX_HITS:
            lst.append({"file": rel, "line": ln, "match": redact(sid, text)})

    for root, dirs, files in os.walk(repo):
        if "pyvenv.cfg" in files:  # any virtualenv, whatever it is named
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in PRUNE]
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, repo).replace(os.sep, "/")
            for sid, rx in PRESENCE.items():
                if rx.search(rel):
                    add(sid, rel, 1, "file present")
            if not wanted(name) or name in LOCKFILES or TEST_PATH.search(rel) or os.path.realpath(path) == me:
                continue
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    for ln, line in enumerate(fh, 1):
                        for sid, m in ids_for_line(rel, line).items():
                            add(sid, rel, ln, m if sid in SECRET_IDS else line)
            except OSError:
                continue
    return hits


def build_report(repo):
    hits = scan(repo)
    stack = {g: sorted(s.split(".", 1)[1] for s in hits if s.startswith(g + ".")) for g in STACK_GROUPS}
    fixed = sorted({s for s in list(SIGNALS) + list(PRESENCE) if not s.startswith(FAMILIES)})
    missing = [s for s in fixed if s not in hits]
    missing += [f + "*" for f in FAMILIES if not any(s.startswith(f) for s in hits)]
    return {"stack": stack, "signals": dict(sorted(hits.items())), "missing": missing}


def selftest():
    cases = [
        ("pyproject.toml", 'dependencies = ["fastapi>=0.110"]', "backend.fastapi"),
        ("app/db.py", 'engine = create_async_engine("postgresql+asyncpg://x")', "db.postgres"),
        ("app/main.py", 'redis = Redis.from_url(os.environ["REDIS_URL"])', "cache.redis"),
        ("ios/App/App/Info.plist", "<key>NSCameraUsageDescription</key>", "perm.camera"),
        ("android/app/src/main/AndroidManifest.xml", '<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>', "perm.location"),
        ("app/routes/account.py", '@router.delete("/api/me")', "account.delete_endpoint"),
        ("app/billing.py", "import stripe", "pay.stripe"),
        ("app/routers/settings.py", '@settings_router.post("/privacy/delete", response_class=HTMLResponse)', "account.delete_endpoint"),
        ("app/ai.py", "client = AsyncOpenAI(base_url='https://openrouter.ai/api/v1')", "ai.openrouter"),
        ("app/auth.py", 'logger.info("login ok for %s", user.email)', "log.pii_risk"),
        ("templates/base.html", '<a href="/privacy">Privacy</a>', "legal.privacy_policy_page"),
        ("package.json", '"@capacitor/core": "^6.0.0",', "mobile.capacitor"),
        ("app/config.py", 'KEY = "sk_live_abcdefghijklmnop1234"', "security.secrets_in_repo"),
        ("app/jobs.py", "cron(purge_expired_sessions, hour=3)", "retention.job"),
    ]
    negatives = [
        ("app/routes/account.py", "# TODO: delete account endpoint", "account.delete_endpoint"),
        ("app/billing.py", "# We use Stripe; import stripe later", "pay.stripe"),
        ("app/dependencies.py", 'ACCOUNT_DELETED = "account_deleted"', "account.delete_endpoint"),
        ("app/routers/api/me.py", '@me_router.delete("/me/avatar")', "account.delete_endpoint"),
        ("src/index.ts", "export default function App() {}", "account.export_endpoint"),
    ]
    fails = [(r, l, s) for r, l, s in cases if s not in ids_for_line(r, l)]
    fails += [(r, l, "NOT " + s) for r, l, s in negatives if s in ids_for_line(r, l)]
    assert TEST_PATH.search("tests/test_account.py") and not TEST_PATH.search("app/account.py")
    assert redact("security.secrets_in_repo", "sk_live_abcdefghijklmnop").endswith("[redacted]")
    for f in fails:
        print("FAIL:", f)
    print("selftest", "FAILED" if fails else "ok", f"({len(cases) + len(negatives)} cases)")
    return 1 if fails else 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    args = [a for a in argv if not a.startswith("--")]
    if len(args) != 1 or not os.path.isdir(args[0]):
        print(__doc__)
        return 2
    rep = build_report(args[0])
    if "--json" in argv:
        print(json.dumps(rep, indent=2))
        return 0
    print("stack:", ", ".join(f"{g}={'/'.join(v)}" for g, v in rep["stack"].items() if v) or "none detected")
    print(f"{'signal':32} {'hits':>4}  first evidence")
    for sid, lst in rep["signals"].items():
        print(f"{sid:32} {len(lst):>4}  {lst[0]['file']}:{lst[0]['line']}")
    print("not detected:", ", ".join(rep["missing"]) or "-")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
