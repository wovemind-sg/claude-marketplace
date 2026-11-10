# Security baseline — "appropriate technical and organisational measures"
last-reviewed: 2026-10-13
applies-when: always (every audit); rows keyed to stack signals backend.fastapi, backend.go, db.postgres, cache.redis, deploy.railway, mobile.*
sources:
- https://eur-lex.europa.eu/eli/reg/2016/679/oj
- https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- https://owasp.org/www-project-application-security-verification-standard/
- https://www.rfc-editor.org/rfc/rfc9116
- https://securitytxt.org/
- https://www.postgresql.org/docs/current/libpq-ssl.html
- https://redis.io/docs/latest/operate/oss_and_stack/management/security/
- https://docs.railway.com/reference/private-networking
- https://docs.railway.com/reference/backups
- https://docs.railway.com/reference/volumes
- https://pypi.org/project/pip-audit/
- https://go.dev/doc/security/vuln/
- https://docs.npmjs.com/cli/v10/commands/npm-audit
- https://eur-lex.europa.eu/eli/reg/2024/2847/oj

## Who it applies to and thresholds

| Scope point | Rule |
|---|---|
| Legal hook | No law lists controls; regulators judge "appropriate" measures against risk and state of the art: GDPR/UK GDPR Art. 32, Israel Protection of Privacy (Data Security) Regulations 2017, Singapore PDPA s.24 (protection obligation), US state laws and FTC Act s.5 ("reasonable security"). Each jurisdiction module cross-refers here. |
| Size | Applies to every company; the expected level scales with data sensitivity and volume, not company size. |
| Evidence rule | A missing control is a Blocker only with `file:line` proof of the gap (e.g. plaintext password column, secret committed). Absence of a policy document is Required, never Blocker. |
| CRA | Downloadable apps may be "products with digital elements" — vulnerability handling and reporting duties live in eu-digital-acts.md. Rows below are the prerequisites. |

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| TLS on every public endpoint | GDPR Art. 32(1)(a); PDPA s.24 | `security.tls`; `deploy.railway` (edge TLS on `*.up.railway.app` and custom domains); grep for `http://` API base URLs in `mobile.*` config and `capacitor.config.*` | file:line of plaintext URL | Blocker if credentials or personal data sent over `http://`; else Recommended | engineer | Use https everywhere; set HSTS; remove `cleartext`/`NSAllowsArbitraryLoads` exceptions. |
| Encrypted DB connection | GDPR Art. 32 | `db.postgres`: grep `DATABASE_URL`, `sslmode`, `connect_args`; Railway private networking (`*.railway.internal`) counts as private transport | DSN construction file:line | Recommended (Required when DB reached over public proxy without `sslmode=require`) | engineer | Use private networking, or `sslmode=require`/`verify-full` on public URLs. |
| Redis protected | GDPR Art. 32 | `cache.redis`: grep `REDIS_URL`, `rediss://`, `requirepass`/password in URL; public TCP proxy enabled? | Client init file:line | Required if Redis reachable publicly without auth; else Recommended | engineer | Keep Redis on private network only; require password; `rediss://` if crossing public network. |
| Passwords hashed with a slow KDF | GDPR Art. 32; OWASP Password Storage | `auth.accounts`: grep `bcrypt`, `argon2`, `passlib`, `scrypt`, `golang.org/x/crypto`; flag `md5`, `sha1`, `sha256(` on passwords | Hash call file:line | Blocker if plaintext or fast hash; Required if KDF params weak | engineer | Argon2id (or bcrypt cost ≥10); rehash on next login. |
| No secrets in repo | GDPR Art. 32; store/vendor ToS | `security.secrets_in_repo`; `.env` listed in `.gitignore`; `git log -p -S` on key prefixes | file:line only — never copy the value | Blocker | engineer | Rotate the secret first, then remove and purge history; load from Railway variables. |
| Encryption at rest | GDPR Art. 32(1)(a); Art. 34(3)(a) (encrypted breach may avoid user notice) | `security.encryption`; Railway docs do not state volume encryption — ask/confirm with vendor; field-level encryption for `perm.health`, `perm.biometrics`, tokens | Model fields storing sensitive data | Recommended; Required for special-category data | engineer | Field-level encryption (e.g. Fernet/KMS) for sensitive columns; confirm provider disk encryption in writing. |
| Backups and tested restore | GDPR Art. 32(1)(c) availability/resilience | `deploy.railway` volume Backups tab (daily kept 6 d, weekly 27 d, monthly 89 d); `docs/` restore test record | Backup schedule screenshot/note or "not found" | Required | engineer | Enable scheduled backups; restore into a test environment quarterly; note that wiping a volume deletes its backups — keep an off-platform `pg_dump`. |
| Backups respect erasure/retention | GDPR Art. 5(1)(e), 17 | Retention of backups documented next to `retention.job` | Policy text | Recommended | founder | State backup expiry in notice; re-apply deletions on restore. |
| No personal data/secrets in logs | GDPR Art. 5(1)(c), 32 | `log.pii_risk`; grep logging of `request.body`, `email`, `token`, `Authorization` | Log call file:line | Required (Blocker if passwords/tokens logged) | engineer | Redact fields; structured logging allow-list; short log retention. |
| Brute-force and rate limiting on auth | GDPR Art. 32; OWASP ASVS V2 | `auth.accounts`: grep `slowapi`, `limiter`, `rate`, `x/time/rate`, lockout counters on login/OTP routes | Login route file:line | Required | engineer | Rate-limit login, signup, OTP, password reset by IP and account. |
| MFA on admin and infrastructure accounts | GDPR Art. 32(1)(b) | Admin routes (`/admin`) + answers about Railway/GitHub/store console MFA | Answer or route | Required | founder | Enforce MFA on Railway, GitHub, App Store Connect, Play Console, email domain, and admin panel. |
| Access control / least privilege | GDPR Art. 25, 32 | Object-level authz on user-scoped queries (grep `user_id ==`/`WHERE user_id`); shared prod credentials | Unscoped query file:line | Blocker if IDOR proven; else Recommended | engineer | Scope every query by owner; separate prod access; remove ex-staff. |
| Dependency vulnerability scanning | GDPR Art. 32(1)(d) testing; CRA Annex I (from 2027) | CI files (`.github/workflows/*`) running `pip-audit`, `govulncheck ./...`, `npm audit`; Dependabot/Renovate config | Workflow file or "not found" | Recommended (Required for distributed native apps under CRA from 2027-12-11) | engineer | Add scanners to CI; patch criticals within a set SLA. |
| security.txt + vulnerability disclosure policy | RFC 9116; CRA Annex I Part II (coordinated vulnerability disclosure policy) | `security.txt` (`/.well-known/security.txt` with `Contact:` and `Expires:`) | Route/static file or "not detected" | Recommended (Required for CRA-scope products) | engineer | Serve `/.well-known/security.txt`; publish a short disclosure policy. |
| Incident response runbook | GDPR Art. 33–34 (72 h); PDPA s.26D (3 days); Israel Data Security Regs | `docs/` incident/runbook file | Path or "not found" | Required | founder | One-page runbook: contacts, triage, evidence, regulator clocks per jurisdiction, user notice template. Feeds the breach rows in privacy modules. |
| Session/token security | OWASP ASVS V3 | Cookie flags `Secure`, `HttpOnly`, `SameSite`; token storage in `mobile.*` (Keychain/Keystore, not localStorage/AsyncStorage) | Cookie set / storage call file:line | Required | engineer | Set flags; move tokens to secure storage plugin. |
| Production debug and docs exposure off | OWASP ASVS V14 | `backend.fastapi`: `FastAPI(debug=True)`, `docs_url`/`openapi_url` left public on admin APIs; `backend.go`: `pprof` imported on public mux; `mobile.android`: `android:debuggable="true"` | file:line | Required (Blocker if debug traceback exposes secrets) | engineer | Disable debug in prod; gate `/docs` and `pprof` behind auth or private network. |
| CSRF protection on cookie-authenticated forms | OWASP ASVS V4/V13 | Cookie sessions (`web.cookies`, `SessionMiddleware`) + POST forms without CSRF token (grep `csrf`) | Form/route file:line | Required | engineer | Add CSRF tokens or `SameSite=Lax/Strict` + origin check. |
| CORS restricted | OWASP ASVS V14 | grep `CORSMiddleware`, `allow_origins=["*"]` with `allow_credentials=True`; Go `Access-Control-Allow-Origin: *` | Config file:line | Required when wildcard + credentials; else Recommended | engineer | Allow-list exact origins (incl. `capacitor://localhost`, `https://localhost` for `mobile.capacitor`). |
| Security headers | OWASP Secure Headers | Middleware setting `Content-Security-Policy`, `Strict-Transport-Security`, `X-Content-Type-Options`, `frame-ancestors` | Middleware file:line or "not found" | Recommended | engineer | Add header middleware; start CSP in report-only. |
| Injection-safe data access | OWASP ASVS V5 | grep raw SQL built with f-strings/`%`/`fmt.Sprintf` passed to `execute`/`Query` | file:line | Blocker if user input reaches query string; else Note | engineer | Use bound parameters / ORM. |
| Upload validation | OWASP File Upload | Upload routes (`UploadFile`, `multipart`): size limit, type check, storage outside web root, no user-controlled paths | Route file:line | Required | engineer | Enforce size/type, random filenames, scan or re-encode images. |
| Webhook signature verification | Vendor docs (Stripe, RevenueCat, Paddle) | `pay.*` webhook routes call signature verify (`construct_event`, `Webhook-Signature`, auth header check) | Route file:line | Blocker if unverified webhook grants entitlements | engineer | Verify signature/shared secret; reject replays. |
| OAuth flow integrity | RFC 9700 (OAuth security BCP) | `auth.oauth.*`: `state` validated, PKCE for native/public clients, redirect URI allow-list | Callback file:line | Required | engineer | Validate `state`, use PKCE, exact redirect URIs. |
| Reset/verification tokens | OWASP Forgot Password | Token expiry, single use, hashed at rest (grep `reset_token`, `verify_token`) | Model/route file:line | Required | engineer | Expire ≤1 h, single-use, store hash only. |
| Audit log of admin and security events | GDPR Art. 5(2) accountability, Art. 33(5) | grep logger calls for logins, role changes, data exports, admin actions | Logger file:line or "not found" | Recommended | engineer | Append-only audit table with retention; alert on anomalies. |
| Mobile local data protection | OWASP MASVS-STORAGE | `mobile.android`: `android:allowBackup="true"` with tokens in prefs; `mobile.ios`: data protection class; `mobile.capacitor`: `@capacitor/preferences` holding tokens | Manifest/plugin file:line | Required | engineer | Disable backup for sensitive data; use secure-storage plugins. |
| Key and credential rotation | GDPR Art. 32(1)(d) | Answer: rotation process; offboarding checklist in `docs/` | Path or "not found" | Recommended | founder | Rotate API keys yearly and on staff departure; document where each secret lives. |
| Real personal data kept out of non-prod | GDPR Art. 5(1)(b)–(c), 32 | Railway environments: staging seeded from prod dumps? grep scripts for `pg_dump` → staging restore | Script file:line | Recommended | engineer | Use synthetic or anonymised seed data in staging/preview environments. |
| Card data never touches your servers | PCI DSS v4.0 (SAQ A eligibility) | `pay.stripe`/`pay.paddle`: hosted Checkout/Elements only; grep for `card_number`, `cvc` fields posted to own routes | Form/route file:line | Blocker if raw card data hits your backend | engineer | Use hosted checkout or tokenising elements only. |
| Email sender authentication | Gmail/Yahoo bulk-sender rules (2024); anti-phishing | `comm.email` sending domain has SPF, DKIM, DMARC (check DNS: `dig TXT _dmarc.<domain>`) | DNS output | Recommended | engineer | Publish SPF/DKIM via provider; DMARC `p=quarantine` once aligned. |
| Session expiry and revocation | OWASP ASVS V3 | Session/JWT lifetime config (grep `max_age`, `exp`, `timedelta(days=`); logout invalidates server session; sessions revoked on password change | Config file:line | Recommended | engineer | Idle + absolute timeouts; revoke all sessions on password reset. |
| Dependencies pinned with lockfiles | Supply-chain integrity (CRA Annex I) | `uv.lock`/`requirements*.txt` with hashes, `go.sum`, `package-lock.json` committed | Path or "not found" | Recommended | engineer | Commit lockfiles; enable Dependabot/Renovate. |
| Admin interface not publicly discoverable | OWASP ASVS V4 | `/admin` routes on the public app without MFA/IP restriction (grep `prefix="/admin"`, `sqladmin`, `django-admin`) | Route file:line | Required | engineer | Put admin behind SSO+MFA or private network; log access. |
| Periodic access review of prod and console accounts | GDPR Art. 32(1)(d), 32(4) | Answer: last review date of Railway/GitHub/store console members | Member lists | Recommended | founder | Quarterly review of who has prod and console access. |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2018-05-25 | GDPR Art. 32 security of processing | in force |
| 2026-09-11 | CRA reporting of actively exploited vulnerabilities/severe incidents (see eu-digital-acts.md) | in force |
| 2027-12-11 | CRA full essential requirements incl. vulnerability handling, SBOM | future |

## Needs a lawyer
- Whether a specific incident meets the "risk to rights and freedoms" threshold for regulator or user notification.
- Whether the product is a CRA "product with digital elements" or pure SaaS (out of scope).
- Contractual security commitments (SLA, security addendum) promised to B2B customers.
