# Licensing and SBOM — open source, AI models, assets
last-reviewed: 2026-10-13
applies-when: always (every audit); input = license_scan.py JSON + sbom.present + ai.* + mobile.* signals
sources:
- https://www.gnu.org/licenses/license-list.html
- https://www.gnu.org/licenses/agpl-3.0.html
- https://www.mongodb.com/legal/licensing/server-side-public-license
- https://www.apache.org/licenses/LICENSE-2.0
- https://opensource.org/license/mit
- https://spdx.dev/
- https://cyclonedx.org/
- https://github.com/anchore/syft
- https://github.com/aboutcode-org/scancode-toolkit
- https://pypi.org/project/pip-licenses/
- https://github.com/google/go-licenses
- https://github.com/davglass/license-checker
- https://github.com/meta-llama/llama-models/blob/main/models/llama3_3/LICENSE
- https://ai.google.dev/gemma/terms
- https://openai.com/policies/terms-of-use/
- https://openai.com/policies/business-terms/
- https://www.anthropic.com/legal/commercial-terms
- https://www.anthropic.com/legal/aup
- https://openfontlicense.org/
- https://fontawesome.com/license/free
- https://choosealicense.com/
- https://eur-lex.europa.eu/eli/reg/2024/2847/oj

## Who it applies to and thresholds

| Distribution model | Permissive (MIT, BSD, Apache-2.0, ISC) | Weak copyleft (LGPL, MPL-2.0, EPL) | Strong copyleft (GPL-2.0/3.0) | Network copyleft (AGPL-3.0) | Source-available (SSPL, BUSL, Elastic, Commons Clause) |
|---|---|---|---|---|---|
| SaaS (code runs only on your servers) | Attribution only if you distribute (e.g. JS sent to browser) | No source duty unless modified files are distributed | No duty (no distribution) | Source of modified program owed to network users (AGPL §13) | Usually bars offering it as a service; read terms |
| Distributed native app / desktop / JS bundle | Ship licence + copyright notices (Apache-2.0 §4 also NOTICE file) | MPL: share modified MPL files. LGPL: user must be able to relink — problematic with static linking on iOS | Whole app must be GPL-compatible and source offered; App Store terms widely viewed as conflicting with GPL | Same as GPL plus §13 | Usually not redistributable |

Severity mapping (fixed): strong or network copyleft in a distributed app (`mobile.*`, frontend bundle) = Blocker; strong/network copyleft in SaaS backend = Required (review modifications and AGPL §13); SSPL/source-available = Required; unknown licence = Recommended; permissive missing attribution in distributed app = Required.

| Ecosystem | Licence report command | SBOM command |
|---|---|---|
| Python (`backend.fastapi`) | `pip-licenses --python .venv/bin/python --format=json --with-urls` | `syft dir:. -o cyclonedx-json` or `cyclonedx-py environment .venv` |
| Go (`backend.go`) | `go-licenses report ./...` / `go-licenses check ./... --disallowed_types=forbidden,restricted` | `syft dir:. -o spdx-json` |
| Node / Capacitor / React Native | `npx license-checker --production --json` (per `package.json` root, incl. `mobile/`) | `syft dir:. -o cyclonedx-json` or `npx @cyclonedx/cyclonedx-npm` |
| iOS pods / SPM | `Pods/Target Support Files/*/*-acknowledgements.plist` (CocoaPods auto-generates) | `syft dir:ios -o cyclonedx-json` |
| Android Gradle | `com.google.android.gms.oss-licenses-plugin` or `com.jaredsburrows.license` report | `syft dir:android -o cyclonedx-json` |
| Container images | `scancode` on extracted layers (only if image is distributed) | `syft <image> -o cyclonedx-json` |

## Requirements → checks

| Requirement | Law/section | Check in code/config | Evidence to cite | Severity if unmet | Owner | Fix |
|---|---|---|---|---|---|---|
| No strong/network copyleft in distributed binaries | GPL-3.0 §5–6; AGPL-3.0 §13; GPL-2.0 §2–3 | license_scan.py `class == strong_copyleft` where `via` is the mobile/Node frontend root (`mobile.ios`, `mobile.android`, `mobile.capacitor`, `mobile.react_native`) | Package name, version, licence, manifest path | Blocker | engineer | Replace the dependency, obtain a commercial licence, or open-source the app under a compatible licence. |
| Copyleft in SaaS backend reviewed | AGPL-3.0 §13; GPL (no distribution = no duty) | `strong_copyleft` under `backend.fastapi`/`backend.go` roots; check if package is modified (vendored dir, fork URL in requirements/go.mod `replace`) | Package + whether modified | Required | lawyer | If AGPL and modified, publish source to network users or replace. |
| LGPL in native apps relinkable | LGPL-2.1 §6 / LGPL-3.0 §4 | `weak_copyleft` LGPL in `mobile.ios`/`mobile.android` deps; static vs dynamic framework (Podfile `use_frameworks!`) | Package + link mode | Required | engineer | Use dynamic linking or provide object files for relinking; else replace. |
| Source-available licences respected | SSPL §13; BUSL additional use grant; Elastic v2 | license_scan `flags` with SSPL/BUSL/Elastic; also infra images (MongoDB, Elasticsearch, Redis ≥7.4 licence) | Package/image + licence | Required | lawyer | Confirm your use is permitted (not offering the software itself as a service) or switch to OSI alternative (e.g. Valkey, OpenSearch). |
| Unknown licences resolved | Copyright default = all rights reserved | license_scan `class == unknown` | Package list | Recommended | engineer | Look up licence (registry, repo LICENSE); install missing tool (`go-licenses`) and rescan. |
| Attribution / NOTICE for permissive deps | MIT ("above copyright notice … shall be included"); BSD clause 2; Apache-2.0 §4(a),(d) | `NOTICE`, `THIRD-PARTY-LICENSES*`, in-app "Open source licences" screen in `mobile.*`; web bundle licence comments/`*.LICENSE.txt` | Path or "not found" | Required for distributed apps; Recommended for SaaS | engineer | Generate: `pip-licenses --with-license-file --format=markdown`, `go-licenses report ./...`, `npx license-checker --production --out THIRD-PARTY-LICENSES.txt`; ship in bundle + settings screen. |
| SBOM produced per release | CRA Annex I Part II(1) (from 2027-12-11, in-scope products); US EO 14028 (federal buyers) | `sbom.present` (`*.cdx.json`, `*.spdx.json`, `bom.xml`) or CI step running `syft` | Path/workflow or "not detected" | Recommended (Required for CRA-scope distributed apps by 2027-12-11) | engineer | `syft dir:. -o cyclonedx-json > sbom.cdx.json` in CI per release; keep with release artifacts. |
| Deep licence scan before major distribution | Copyright | Vendored code dirs (`vendor/`, `third_party/`, copied snippets) | Dir list | Recommended | engineer | Run `scancode -clpieu --json-pp scan.json <dir>` on vendored/copied code. |
| Open-weights model licence obeyed (Llama) | Llama 3.x Community Licence §1.b.i, §1.b.iv, §2 | `ai.ollama`, model names in config (grep `llama`) | Model id file:line | Required | founder | Display "Built with Llama"; ship licence + Notice; follow Acceptable Use Policy; derived models named "Llama…"; >700M MAU needs Meta licence. |
| Open-weights model licence obeyed (Gemma and others) | Gemma Terms of Use + Prohibited Use Policy | `ai.google`/`ai.ollama` with `gemma`; other model ids (Mistral, Qwen) → read model card licence | Model id file:line | Required | founder | Pass use restrictions through to your users' terms; keep notice; record each model's licence in `docs/legal/`. |
| AI API output/usage terms respected | OpenAI Terms of Use / Services Agreement; Anthropic Commercial Terms + AUP | `ai.openai`, `ai.anthropic`, `ai.openrouter` (+ upstream provider terms) | SDK init file:line | Recommended; Required if outputs used to train a competing model | founder | Do not use outputs to develop competing models; follow each provider's usage policy; OpenRouter routes inherit upstream provider terms. |
| Fonts licensed for embedding/redistribution | SIL OFL 1.1 (bundling allowed, not sold alone, Reserved Font Names); commercial font EULAs | `*.ttf`, `*.otf`, `*.woff2` in repo/app bundle; Google Fonts links | Font file paths | Recommended; Required for commercial fonts without app-embedding licence | founder | Keep OFL text next to fonts; buy app/web embedding licence for commercial fonts. |
| Icons and images licensed | Font Awesome Free: icons CC BY 4.0, fonts OFL, code MIT; stock image licences | Grep `fontawesome`, `@fortawesome`, image dirs; stock-site filenames | Package/asset paths | Recommended | founder | Keep attribution (FA Free comments are sufficient); keep stock licence receipts in `docs/legal/assets/`. |
| JS bundles keep licence comments | MIT/BSD/Apache notice-retention clauses | Bundler config: terser `extractComments`, esbuild `legalComments`, Vite `build.minify` settings; `*.LICENSE.txt` emitted in `dist/` | Config file:line | Recommended (web) / Required (bundled into `mobile.capacitor` app) | engineer | Emit legal comments to a linked file; ship it in the app bundle. |
| Platform SDK terms accepted | Firebase/Google APIs ToS; Apple DPLA; RevenueCat/Stripe ToS | `track.analytics.firebase`, `pay.*`, `auth.oauth.*` SDKs present | SDK list | Note | founder | Keep a register of accepted vendor terms in `docs/legal/`. |
| Copied code snippets attributed | CC BY-SA 4.0 (Stack Overflow); source licence of copied file | grep for `stackoverflow.com` / `Copyright (c)` headers in first-party code | file:line | Recommended | engineer | Add attribution comment and licence, or rewrite. |
| Dependency licence policy in CI | Good practice (CRA Art. 13(5) due diligence) | CI step running `go-licenses check` or `license-checker --failOn "GPL;AGPL"` | Workflow file or "not found" | Recommended | engineer | Fail builds on forbidden licence classes for distributed targets. |
| Your own repo licence chosen | Copyright | Root `LICENSE` file; `license` field in `pyproject.toml`/`package.json` | Path or "not found" | Note for private repos; Recommended for public repos | founder | Private: add proprietary notice. Public: pick licence via choosealicense.com compatible with your deps. |
| CRA vulnerability handling of components | CRA Art. 13(5) (due diligence on third-party components), Annex I Part II | CI scanners (`pip-audit`, `govulncheck`, `npm audit`) per security-baseline.md | CI workflow file or "not found" | Note until 2027-12-11; then Required for in-scope apps | engineer | Track components via SBOM; patch known vulns. |

## Deadlines

| Date | Obligation | Applies from / in force since |
|---|---|---|
| 2026-09-11 | CRA vulnerability/incident reporting (eu-digital-acts.md) | in force |
| 2027-12-11 | CRA essential requirements incl. SBOM (Annex I Part II(1)) and component due diligence | future |

## Needs a lawyer
- Any strong/network-copyleft dependency in a shipped app, or AGPL in a modified backend.
- Whether SSPL/BUSL terms permit your hosted use.
- Llama/Gemma licence obligations when fine-tuning or redistributing weights.
- Using AI outputs for model training or in ways restricted by provider terms.
- Dual-licensing or open-sourcing your own code.
