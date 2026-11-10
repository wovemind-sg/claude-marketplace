# flagd deployment & operations reference

Worked from flagd repo `main` @ `b13483f` (2026-09-18). Component versions at that commit
(`.release-please-manifest.json`): **flagd v0.16.3** (2026-09-10), **flagd-proxy v0.9.9**, **core v0.17.0**.
Image tags follow `flagd/vX.Y.Z` git tags; `latest` and `X.Y.Z` on GHCR.

## Contents

1. [What flagd is / architecture](#1-what-flagd-is--architecture)
2. [Install](#2-install)
3. [Ports](#3-ports)
4. [`flagd start` CLI reference](#4-flagd-start-cli-reference)
5. [Config file (`--config`)](#5-config-file---config)
6. [Sync sources: `--uri` and `--sources`](#6-sync-sources---uri-and---sources)
7. [Merging, resync, file watching](#7-merging-resync-file-watching)
8. [Selectors & flag sets](#8-selectors--flag-sets)
9. [gRPC sync service, in-process providers, flagd-proxy](#9-grpc-sync-service-in-process-providers-flagd-proxy)
10. [Evaluation context from the server side (`-X`, `-H`)](#10-evaluation-context-from-the-server-side--x--h)
11. [TLS, CORS, sockets, request limits](#11-tls-cors-sockets-request-limits)
12. [Monitoring: health, metrics, traces](#12-monitoring-health-metrics-traces)
13. [FIPS 140-3 build](#13-fips-140-3-build)
14. [Kubernetes](#14-kubernetes)
15. [Versioning, support, naming](#15-versioning-support-naming)
16. [Troubleshooting (deployment)](#16-troubleshooting-deployment)

## 1. What flagd is / architecture

flagd is an OpenFeature-compliant feature-flag **evaluation engine** shipped as a Unix-style daemon
(Go, single static binary, distroless image). It holds no database: it **syncs** flag definitions
(JSON/YAML, schema `https://flagd.dev/schema/v0/flags.json`) from one or more sources, merges them
into an in-memory store, evaluates JSONLogic targeting, and pushes change notifications to clients.

Two deployment topologies:

| Mode | Client side | Wire | Where evaluation runs |
| --- | --- | --- | --- |
| **RPC** | flagd *RPC provider* (SDK) | `evaluation.proto` gRPC / Connect HTTP on **8013**, or OFREP REST on **8016**; `EventStream` pushes `configuration_change` | in flagd (<10 ms typical, thousands eval/s). Works from `curl`. |
| **In-process** | flagd *in-process provider* embeds the engine | `sync.proto` `SyncFlags` stream from flagd's sync service on **8015** (or any sync.proto server, e.g. flagd-proxy) | in the app; zero I/O per evaluation |

Sync providers (all first-class, all mergeable): `file` (fsnotify/polling), `http(s)` (poll + ETag),
`grpc(s)` (stream), `kubernetes` (FeatureFlag CR watch), `gcs`, `azblob`, `s3` (poll). New sources
implement the Go `ISync` interface (`Init/Sync/ReSync/IsReady`); events fan in over a channel to the store.

**flagd-proxy** (`ghcr.io/open-feature/flagd-proxy`, experimental) is a pub/sub server speaking
`sync.proto` on 8015: it watches Kubernetes `FeatureFlag` CRs on demand and broadcasts changes to any
number of flagd sidecars / in-process providers, so only one component needs RBAC to the API server.

flagd performs **no authentication or authorization** on any endpoint; run it inside a trust boundary.

Source: https://flagd.dev/architecture/ , https://flagd.dev/architecture-decisions/multiple-sync-sources/

## 2. Install

### Docker (recommended)

```shell
docker pull ghcr.io/open-feature/flagd:latest          # or :0.16.3, :latest-fips, :0.16.3-fips
docker run --rm -it --name flagd \
  -p 8013:8013 -p 8014:8014 -p 8015:8015 -p 8016:8016 \
  -v "$(pwd)":/etc/flagd \
  ghcr.io/open-feature/flagd:latest start --uri file:./etc/flagd/demo.flagd.json
```

- Image: `gcr.io/distroless/static:nonroot`, runs as UID/GID **65532**, `ENTRYPOINT` is the flagd
  binary, so the first arg is the subcommand `start`. No shell inside.
- Mounted flag files must be readable by UID 65532 (`chmod o+r`). Only `.json/.yaml/.yml` for `file:`.
- WORKDIR is `/`; `file:./etc/flagd/x.json` and `file:/etc/flagd/x.json` are equivalent.
- Windows: keep files and Docker runtime both inside WSL (mixed filesystems break file watching).
- Images are cosign-signed and ship an SBOM; multi-arch `linux/amd64,linux/arm64`.

Dockerfile base: `FROM ghcr.io/open-feature/flagd:latest`.

### Docker Compose

```yaml
services:
  flagd:
    image: ghcr.io/open-feature/flagd:latest
    volumes:
      - ./flags:/flags:ro
    command: ["start", "--uri", "file:./flags/demo.flagd.json"]
    ports:
      - "8013:8013"   # evaluation gRPC/HTTP
      - "8014:8014"   # health + metrics
      - "8015:8015"   # sync (in-process providers)
      - "8016:8016"   # OFREP
```

### Binary (GitHub Releases)

Archives at https://github.com/open-feature/flagd/releases. Naming (version has no `v`):

```text
flagd_0.16.3_Linux_x86_64.tar.gz   flagd_0.16.3_Linux_arm64.tar.gz
flagd_0.16.3_Darwin_x86_64.tar.gz  flagd_0.16.3_Darwin_arm64.tar.gz
flagd_0.16.3_Windows_x86_64.zip    flagd_0.16.3_Windows_i386.zip
flagd-fips_0.16.3_<OS>_<arch>.tar.gz   # FIPS variant, Linux/Darwin only
```

```shell
V=0.16.3
curl -sSLo flagd.tgz "https://github.com/open-feature/flagd/releases/download/flagd%2Fv${V}/flagd_${V}_Linux_x86_64.tar.gz"
tar -xzf flagd.tgz && sudo install -m 0755 flagd_linux_amd64 /usr/local/bin/flagd && flagd version
```

Binary inside the tarball is `flagd_<goos>_<goarch>` (e.g. `flagd_darwin_arm64`); archive also holds LICENSE, CHANGELOG.md, README.md, sbom.xml.

- `go install github.com/open-feature/flagd/flagd@latest` is **not recommended** (module depends on
  local workspace modules). Build from source instead: `git clone https://github.com/open-feature/flagd && cd flagd && go work init ./core ./flagd && CGO_ENABLED=0 go build -o bin/flagd ./flagd`.
- Homebrew: no official formula is documented by the project. Use the Darwin tarball.
- Snap: `flagd/snap/snapcraft.yaml` exists (name `flagd`, strict confinement, plugs `home network network-bind`); store publication is not documented, so verify with `snap info flagd` before relying on it.

### systemd

`systemd/flagd.service` from the repo (place binary on PATH, flags at `/etc/flagd/flags.json`):

```ini
[Unit]
Description="A feature flag daemon with a Unix philosophy"

[Service]
User=root
WorkingDirectory=/etc/flagd
ExecStart=flagd start --uri file:flags.json
Restart=always

[Install]
WantedBy=multi-user.target
```

Harden: `User=flagd`, `DynamicUser=yes`, `ExecStart=/usr/local/bin/flagd start --uri file:/etc/flagd/flags.json --log-format json`,
`Environment=FLAGD_PORT=8013`. Then `sudo systemctl daemon-reload && sudo systemctl enable --now flagd && curl -s localhost:8014/readyz`.

### Kubernetes

- Raw manifests: `config/deployments/flagd/{deployment,service}.yaml` (see §14).
- **OpenFeature Operator** (sidecar injection, CRDs, flagd-proxy management) via Helm (see §14).

Source: https://flagd.dev/installation/ , https://flagd.dev/quick-start/ , GitHub `flagd/build.Dockerfile`, `.github/workflows/release-please.yaml`, `systemd/flagd.service`, `snap/snapcraft.yaml`

## 3. Ports

Verified against `flagd start --help` (`docs/reference/flagd-cli/flagd_start.md`) and `flagd/cmd/start.go`:

| Port | Flag | Env | Protocols | Serves |
| --- | --- | --- | --- | --- |
| **8013** | `-p/--port` | `FLAGD_PORT` | gRPC + Connect HTTP/JSON (h2c) | `flagd.evaluation.v1/v2.Service` ResolveBoolean/String/Int/Float/Object/ResolveAll/EventStream |
| **8014** | `-m/--management-port` | `FLAGD_MANAGEMENT_PORT` | HTTP + gRPC health | `/healthz`, `/readyz`, `/metrics` (Prometheus), gRPC health-check service |
| **8015** | `-g/--sync-port` | `FLAGD_SYNC_PORT` | gRPC, gRPC-Web, Connect (h2c) + plain HTTP | `flagd.sync.v1.FlagSyncService` SyncFlags/FetchAllFlags/GetMetadata; `GET /v1/flags` |
| **8016** | `-r/--ofrep-port` | `FLAGD_OFREP_PORT` | HTTP REST | `POST /ofrep/v1/evaluate/flags[/{key}]`, `GET /ofrep/v1/sse/{channel}` |

Note: a few older doc pages (selector-syntax, troubleshooting, migration guide) show `localhost:8014/ofrep/...`; that is stale. OFREP is **8016**.

Source: https://flagd.dev/reference/cheat-sheet/#default-ports , https://flagd.dev/reference/flagd-cli/flagd_start/

## 4. `flagd start` CLI reference

Env var rule: `FLAGD_` + flag name upper-cased with `-`→`_` (viper `SetEnvPrefix("FLAGD")`).
Precedence: CLI flag > env var > `--config` file > default. Root (persistent) flags: `--config <file>`
(default `$HOME/.agent.yaml`), `-x/--debug` (`FLAGD_DEBUG=true`). `flagd version` prints version, commit, build date, variant, FIPS mode.

| Flag | Short | Env | Default | Meaning |
| --- | --- | --- | --- | --- |
| `--uri` | `-f` | `FLAGD_URI` | `[]` | Sync source URI; repeatable. Prefix selects provider (§6). Later URIs win on duplicate keys. `file:` only `.json/.yaml/.yml`. |
| `--sources` | `-s` | `FLAGD_SOURCES` | `""` | JSON array of `SourceConfig` (§6). Ignored when `--config` is set (sources then come from file). |
| `--port` | `-p` | `FLAGD_PORT` | `8013` | Evaluation service port. |
| `--management-port` | `-m` | `FLAGD_MANAGEMENT_PORT` | `8014` | Health, readiness, metrics, gRPC health. |
| `--sync-port` | `-g` | `FLAGD_SYNC_PORT` | `8015` | Flag sync service (gRPC, gRPC-Web, Connect). |
| `--ofrep-port` | `-r` | `FLAGD_OFREP_PORT` | `8016` | OFREP REST service. |
| `--sync-http-enabled` | | `FLAGD_SYNC_HTTP_ENABLED` | `true` | Serve `GET /v1/flags` on sync port. `=false` disables. |
| `--disable-sync-metadata` | | `FLAGD_DISABLE_SYNC_METADATA` | `false` | Disable sync service `GetMetadata` RPC. Will default to `true` in a later minor (documented future flip). |
| `--socket-path` | `-d` | `FLAGD_SOCKET_PATH` | `""` | Unix socket for evaluation gRPC; HTTP gateway proxies to it internally. |
| `--sync-socket-path` | `-e` | `FLAGD_SYNC_SOCKET_PATH` | `""` | Unix socket for sync gRPC. |
| `--server-cert-path` | `-c` | `FLAGD_SERVER_CERT_PATH` | `""` | PEM cert; with key enables TLS on all served ports. |
| `--server-key-path` | `-k` | `FLAGD_SERVER_KEY_PATH` | `""` | PEM key (`tls.LoadX509KeyPair`). |
| `--cors-origin` | `-C` | `FLAGD_CORS_ORIGIN` | `[]` | Allowed origins; repeatable; `*` = all. |
| `--log-format` | `-z` | `FLAGD_LOG_FORMAT` | `console` | `console` or `json`. |
| `--debug` | `-x` | `FLAGD_DEBUG` | `false` | Debug-level logging (zap). |
| `--context-value` | `-X` | `FLAGD_CONTEXT_VALUE` | `{}` | `key=value` static context added to every evaluation; repeatable. |
| `--context-from-header` | `-H` | `FLAGD_CONTEXT_FROM_HEADER` | `{}` | `Header-Name=contextKey` mapping; repeatable. |
| `--metrics-exporter` | `-t` | `FLAGD_METRICS_EXPORTER` | `""` (=Prometheus) | `otel` switches to OTLP push; requires `--otel-collector-uri`. |
| `--otel-collector-uri` | `-o` | `FLAGD_OTEL_COLLECTOR_URI` | `""` | OTLP **gRPC** endpoint, e.g. `localhost:4317`. Enables trace export; unset = no traces. |
| `--otel-cert-path` | `-D` | `FLAGD_OTEL_CERT_PATH` | `""` | Client cert for mTLS to collector. |
| `--otel-key-path` | `-K` | `FLAGD_OTEL_KEY_PATH` | `""` | Client key for collector. |
| `--otel-ca-path` | `-A` | `FLAGD_OTEL_CA_PATH` | `""` | CA for collector TLS. |
| `--otel-reload-interval` | `-I` | `FLAGD_OTEL_RELOAD_INTERVAL` | `1h` | Reload collector TLS material from disk. (Flag is not viper-bound in 0.16.3; set via env/config if it seems ignored.) |
| `--stream-deadline` | | `FLAGD_STREAM_DEADLINE` | `0` | Server-side max age for sync/event streams (`0` = none). Clients reconnect on expiry; useful for load re-balancing. |
| `--max-request-body` | `-B` | `FLAGD_MAX_REQUEST_BODY` | `1000000` | Bytes. Exceed → HTTP 413 (OFREP) / 429 (Connect) / `resource_exhausted` (sync). `0` disables (unbounded on sync). |
| `--max-request-header` | `-R` | `FLAGD_MAX_REQUEST_HEADER` | `1000000` | Bytes. Exceed → HTTP 431. `0` = Go default 1 MiB. |
| `--ofrep-sse-enabled` | | `FLAGD_OFREP_SSE_ENABLED` | `true` | OFREP SSE change notifications at `/ofrep/v1/sse/{channel}` (channel = selector expression). |
| `--ofrep-sse-inactivity-delay` | | `FLAGD_OFREP_SSE_INACTIVITY_DELAY` | `120` | Seconds advertised to SSE clients before they drop idle connections. |
| `--ofrep-sse-public-url` | | `FLAGD_OFREP_SSE_PUBLIC_URL` | `""` | `scheme://host` advertised as SSE origin when flagd sits behind a proxy. |
| `--keep-alive-min-time` | | `FLAGD_KEEP_ALIVE_MIN_TIME` | `30s` | **No-op** since sync moved to Connect/net-http; warns if non-default. |
| `--keep-alive-permit-without-stream` | | `FLAGD_KEEP_ALIVE_PERMIT_WITHOUT_STREAM` | `true` | **No-op**; accepted for compatibility. Idle connections with no streams are reclaimed after 5 min. |
| `--config` | | | `$HOME/.agent.yaml` | YAML config file (§5). |

Minimal run: `flagd start --uri file:/etc/flagd/flags.json`. Production baseline:

```shell
flagd start --uri file:/etc/flagd/flags.json --log-format json \
  -X environment=production -X region=eu-west-1 \
  --metrics-exporter otel --otel-collector-uri otel-collector:4317 \
  --cors-origin https://app.example.com
```

Source: https://flagd.dev/reference/flagd-cli/flagd_start/ , https://flagd.dev/reference/flagd-cli/flagd/ , GitHub `flagd/cmd/start.go`

## 5. Config file (`--config`)

Keys are the long flag names. `uri` is a list, `sources` a list of SourceConfig objects. When `--config`
is passed, `--sources` on the CLI is ignored (sources are unmarshalled from the file); `--uri` still appends.

```yaml
# /etc/flagd/flagd.yaml   ->   flagd start --config /etc/flagd/flagd.yaml
port: 8013
management-port: 8014
sync-port: 8015
ofrep-port: 8016
log-format: json
cors-origin: ["*"]
context-value:
  environment: production
uri:
  - file:/etc/flagd/base-flags.json
sources:
  - uri: https://flags.example.com/flags.json
    provider: http
    interval: 10
    authHeader: "Bearer ${TOKEN_IS_NOT_EXPANDED}"   # viper does not expand env here; template the file yourself
  - uri: flag-server:8080
    provider: grpc
    tls: true
    certPath: /certs/ca.pem
    selector: "flagSetId=payments"
```

Source: https://flagd.dev/reference/sync-configuration/#source-configuration , GitHub `flagd/cmd/start.go`, `flagd/cmd/root.go`

## 6. Sync sources: `--uri` and `--sources`

### `--uri` shorthand (provider implied by prefix)

| Prefix | Provider | Example |
| --- | --- | --- |
| `file:` | `file` (fsnotify in k8s, `os.Stat` polling elsewhere) | `--uri file:/etc/flagd/flags.json` (relative paths allowed: `file:etc/flags.yaml`) |
| `http://`, `https://` | `http` (poll, default 5 s, ETag/304) | `--uri https://flags.example.com/flags.json` |
| `grpc://`, `grpcs://` | `grpc` (stream; `grpcs` = TLS with system CAs) | `--uri grpc://flag-server:8080` |
| `envoy://`, `dns://`, `uds://`, `xds://` | `grpc` with custom gRPC name resolver | `--uri envoy://localhost:9211/test.service` |
| `core.openfeature.dev/<ns>/<name>` | `kubernetes` (FeatureFlag CR watch; needs RBAC) | `--uri core.openfeature.dev/default/my-flags` |
| `gs://` | `gcs` (Application Default Credentials) | `--uri gs://my-bucket/flags.json` |
| `azblob://` | `azblob` (`AZURE_STORAGE_ACCOUNT` + azureblob env vars) | `--uri azblob://my-container/flags.json` |
| `s3://` | `s3` (AWS credential chain) | `--uri s3://my-bucket/flags.json` |

Format detection for file/http/blob: by extension (`.json`, `.yaml`, `.yml`), else by `Content-Type`.

### `--sources` JSON (full control)

`uri` here does **not** carry the prefix (except http/https). Provider chosen by `provider`.

| Field | Type | Applies to | Meaning |
| --- | --- | --- | --- |
| `uri` | string, required | all | Path / URL / host:port / `ns/name` / `gs://…` etc. |
| `provider` | string, required | all | `file`, `fsnotify`, `fileinfo`, `http`, `grpc`, `kubernetes`, `gcs`, `azblob`, `s3` |
| `interval` | uint32 s | http, gcs, azblob, s3 | Poll interval. Default 5, max 86400. |
| `intervalSeed` | string | http, gcs, azblob, s3 | Deterministic jitter seed (FNV-1a) so replicas poll at different offsets; set to pod name in k8s. |
| `timeoutS` | int s | http | Request timeout. |
| `authHeader` | string | http | Full `Authorization` value: `"Bearer …"`, `"Basic …"`. |
| `headers` | map | http, grpc | Extra request headers / gRPC metadata (e.g. `{"Flagd-Selector":"flagSetId=x"}`, tenant headers). |
| `oauth` | object | http | `{clientID, clientSecret, tokenURL}` or `{folder, ReloadDelayS, tokenURL}`; `folder` reads files `client-id` / `client-secret`, reloaded every `ReloadDelayS` seconds (secret rotation without restart). |
| `tls` | bool | grpc | Use TLS (default false = insecure). |
| `certPath` | string | grpc | CA/cert PEM for TLS; unset = system roots. |
| `providerID` | string | grpc | Sent in `SyncFlagsRequest.provider_id`; identifies this flagd to the server. |
| `selector` | string | grpc | Selector sent upstream (`flagSetId=…`, `source=…`, or legacy bare value). Required when syncing from flagd-proxy (`core.openfeature.dev/ns/name`). |
| `maxMsgSize` | int bytes | grpc | Max receive message size; default 4 MiB. |
| `incrementalUpdates` | bool | grpc | **Experimental.** Updates replace only flags whose `flagSetId` appears in the payload; others persist (no GC until restart or empty update for that id). |

```shell
flagd start --sources='[
  {"uri":"/etc/flagd/flags.json","provider":"file"},
  {"uri":"https://flags.example.com/flags.json","provider":"http","interval":10,"timeoutS":5,"authHeader":"Bearer TOKEN","intervalSeed":"'"$HOSTNAME"'"},
  {"uri":"flag-server:8080","provider":"grpc","tls":true,"certPath":"/certs/ca.pem","providerID":"checkout-flagd","selector":"flagSetId=checkout","maxMsgSize":5242880},
  {"uri":"default/my-flags","provider":"kubernetes"},
  {"uri":"s3://my-bucket/flags.json","provider":"s3","interval":30}
]'
```

Startup fails fast with the provider's error on a malformed URI. Cloud providers: GCS uses ADC
(`GOOGLE_APPLICATION_CREDENTIALS`), Azure uses `AZURE_STORAGE_ACCOUNT` (+ key/SAS env per gocloud
azureblob), S3 uses the standard AWS chain (`AWS_REGION`, `AWS_ACCESS_KEY_ID`, IRSA, etc.).

Source: https://flagd.dev/reference/sync-configuration/ , https://flagd.dev/concepts/syncs/

## 7. Merging, resync, file watching

- **Merge order**: sources are merged in definition order; a later source **overrides** an earlier one
  on duplicate `flagSetId+key`. `--uri A --uri B --uri C` → C wins over B wins over A. `--uri` entries
  come before `--sources`/config entries.
- **Resync**: when a delete in one source removes a merged flag, flagd requests a full `ReSync` from
  all sources and rebuilds the store, so a shadowed definition from a lower-priority source reappears
  instead of `FLAG_NOT_FOUND`.
- **Do not** put the same `flagSetId+key` in two sources intentionally; priority is defined but
  "not recommended" and relative priority within incremental gRPC updates is undefined.
- **File watching**: `file` = `fsnotify` when flagd detects Kubernetes, `fileinfo` (timer + `os.Stat`)
  otherwise; force with `provider: fsnotify|fileinfo`. Editors and `cp` emit several FS events per save
  → duplicate change events. For production point the watched path at a **symlink** and swap the
  target atomically (this is how kubelet updates ConfigMap mounts). Deleting the file is a delete event.
- **HTTP polling**: sends `If-None-Match`; `304` skips parsing. Set `intervalSeed` per replica to
  avoid thundering herd. Change detection hashes the payload (SHA3-256), so identical re-fetches are no-ops.
- **gRPC**: near-instant push; on stream loss the client reconnects with backoff; expect the server to
  send a full snapshot on (re)connect.
- **Readiness** (`/readyz`) returns 412 until *every* configured source has completed one successful sync.

Source: https://flagd.dev/concepts/syncs/#merging , https://flagd.dev/troubleshooting/#extra-duplicate-events-in-file-syncs

## 8. Selectors & flag sets

A **flag set** is a logical group identified by `metadata.flagSetId`, set either on the whole document
or per flag (flag-level overrides set-level). `flagSetId + key` is the unique flag identity, so the same
key may exist in different sets (use the array form `"flags": [{"key": …, "metadata": {"flagSetId": …}}]`).
Flags with no `flagSetId` belong to the "null" set (internally a UUIDv4).

```json
{ "$schema": "https://flagd.dev/schema/v0/flags.json",
  "metadata": { "flagSetId": "payment-service", "version": "v1.2.0" },
  "flags": { "new-checkout": { "state": "ENABLED", "variants": {"on": true, "off": false}, "defaultVariant": "on" } } }
```

**Selector syntax** (single key=value only, in 0.16.x):

| Expression | Meaning |
| --- | --- |
| `flagSetId=payment-service` | flags in that set (preferred) |
| `flagSetId=` | flags with no flagSetId |
| `source=/etc/flagd/flags.json` | flags from that configured source URI (legacy) |
| `my-flags.json` (no `=`) | treated as `source=` (backward compatibility) |

Where a selector is supplied, highest priority first: gRPC metadata `Flagd-Selector` → HTTP header
`Flagd-Selector` → URL path segment (SSE channel) → `?selector=` query → request-body `selector` field
→ per-source `selector` in `--sources` (lowest; applies to what flagd pulls upstream). Applies uniformly
to evaluation RPCs, OFREP, `EventStream` (header only), `SyncFlags`/`FetchAllFlags`, `GET /v1/flags`.
The applied selector is reflected back in response `metadata` for debugging.

Errors: malformed selector → 400 / `invalid_argument`; unknown key (`bogus=1`) → 400 (OFREP), 404
(`/v1/flags`), `invalid_argument` (sync); valid but empty → 200 with empty result.

```shell
curl -H 'Flagd-Selector: flagSetId=payment-service' -X POST localhost:8016/ofrep/v1/evaluate/flags
curl -H 'Flagd-Selector: flagSetId=payment-service' localhost:8015/v1/flags
```

**Migration from source selectors**: (1) add `metadata.flagSetId` to each config; (2) change provider
`selector("config/app.json")` → `selector("flagSetId=my-app")`; (3) verify with the curl above. Old
selectors keep working; flag sets may span sources and one source may hold many sets.

Source: https://flagd.dev/concepts/selectors/ , https://flagd.dev/reference/selector-syntax/ , https://flagd.dev/guides/migrating-to-flag-sets/ , https://flagd.dev/architecture-decisions/decouple-flag-source-and-set/

## 9. gRPC sync service, in-process providers, flagd-proxy

flagd is itself a **sync.proto server** on 8015 (Connect handler: gRPC, gRPC-Web, Connect JSON over
h2c or TLS). It streams the merged store (filtered by selector) to in-process providers, or to other flagd instances.

```shell
# Unary fetch (JSON, no gRPC client needed)
curl -X POST localhost:8015/flagd.sync.v1.FlagSyncService/FetchAllFlags -H 'Content-Type: application/json' -d '{}'
# Plain cacheable document (ETag + Last-Modified, honours If-None-Match / If-Modified-Since)
curl -i localhost:8015/v1/flags
# Streaming (needs protos; flagd has no gRPC reflection)
git clone https://github.com/open-feature/flagd-schemas.git && PROTO_DIR=flagd-schemas/protobuf
grpcurl -plaintext -import-path "$PROTO_DIR" -proto flagd/sync/v1/sync.proto \
  -d '{"selector":"flagSetId=app-flags"}' localhost:8015 flagd.sync.v1.FlagSyncService/SyncFlags
```

- In-process provider config (Java shown; others analogous): `resolverType(IN_PROCESS).host("flagd").port(8015).selector("flagSetId=app")`.
- **Chain flagd instances**: `flagd start --uri http://central-flagd:8015/v1/flags` (polling, 304 steady
  state) or `--uri grpc://central-flagd:8015` (push). Subset: `--sources='[{"uri":"http://central:8015/v1/flags","provider":"http","headers":{"Flagd-Selector":"flagSetId=payments"}}]'`.
- Keepalive: no server enforcement policy any more; any client ping cadence is accepted. Idle
  connections with zero streams are closed after 5 min. `--stream-deadline` forces periodic reconnects.
- HTTP/2 must be allowed end-to-end for gRPC streams (error "unexpected EOS on empty DATA frame" = a proxy blocked h2).
- `GetMetadata` RPC exists but is slated for removal; set `--disable-sync-metadata` now if clients do not need it.

**flagd-proxy** (`ghcr.io/open-feature/flagd-proxy:latest`, v0.9.9): CLI `flagd-proxy start`
`-p/--port` (default **8015**, sync.proto), `-m/--management-port` (default **8016**, health/metrics),
`-z/--log-format`, `--keep-alive-min-time` (30s), `--keep-alive-permit-without-stream` (true), root `-x/--debug`, `--config`.
Clients request a CR with `selector: core.openfeature.dev/<ns>/<name>`; the proxy starts one Kubernetes
watch per CR and fans it out; watch stops when the last subscriber leaves. Deploy from `config/deployments/kube-flagd-proxy/` (§14).

Source: https://flagd.dev/reference/grpc-sync-service/ , https://flagd.dev/reference/cheat-sheet/#syncing-flag-configuration , GitHub `flagd-proxy/README.md`, `flagd-proxy/cmd/start.go`

## 10. Evaluation context from the server side (`-X`, `-H`)

- `-X key=value` (**static context**): injected into every evaluation. Use for `environment`, `region`, `service`, cluster.
- `-H Header-Name=contextKey` (**header-mapped context**): copies an HTTP/gRPC request header into the context (gateway/auth-proxy integration, tenant IDs).
- Merge priority: **header-mapped > static > request body**. Operators can therefore force values clients cannot override.

```shell
flagd start --uri file:./flags.json -X environment=production -X region=us-east-1 -H "X-User-Id=userId" -H "X-Tenant=tenant"
```

Pair with `OTEL_RESOURCE_ATTRIBUTES` so the same dimensions appear in telemetry.

Source: https://flagd.dev/reference/flag-definitions/#static-context--x-flag

## 11. TLS, CORS, sockets, request limits

- **Serve TLS**: `--server-cert-path /certs/tls.crt --server-key-path /certs/tls.key`. One pair covers
  8013/8015/8016 (gRPC, Connect, OFREP, `/v1/flags`). Without it gRPC runs plaintext over h2c. flagd
  reads the PEM once at start; rotate by restarting (or terminate TLS in a mesh/ingress).
- **Consume TLS**: `grpcs://` or `"tls": true` (+ `certPath` for private CA); `https://` for HTTP sources.
- **OTel collector TLS**: `-D/-K/-A` (cert/key/CA), reloaded every `--otel-reload-interval`.
- **CORS** (browser clients on OFREP/Connect): `-C https://app.example.com -C https://admin.example.com` or `-C '*'`.
- **Unix sockets**: `-d /run/flagd/eval.sock` (evaluation gRPC), `-e /run/flagd/sync.sock` (sync gRPC). Sidecar-local IPC without TCP.
- **Limits**: bodies > `--max-request-body` (1 MB) → 413/429/`resource_exhausted`; headers > `--max-request-header` (1 MB) → 431. Servers have read timeouts (0.16.1+).
- No auth anywhere: front flagd with a mesh/ingress if exposing beyond localhost/cluster.

Source: https://flagd.dev/reference/flagd-cli/flagd_start/ , https://flagd.dev/reference/grpc-sync-service/#request-limits

## 12. Monitoring: health, metrics, traces

**Probes** (management port 8014): `GET /healthz` → 200 as soon as the process serves.
`GET /readyz` → **412** until every sync source has synced once, then 200 forever (never regresses).
gRPC standard health service (`grpc.health.v1.Health`) also on 8014 — use `grpc_health_probe -addr=:8014`.

**Metrics**: default exporter is Prometheus at `http://localhost:8014/metrics`. Switch to OTLP push with
`--metrics-exporter otel --otel-collector-uri otel-collector:4317` (gRPC OTLP; also enables traces).
`OTEL_RESOURCE_ATTRIBUTES="deployment.environment=prod,service.version=0.16.3"` and
`OTEL_EXPORTER_OTLP_ENDPOINT` are honoured. In Prometheus, OTel names are transformed (`.`→`_`, counters gain `_total`).

| OTel metric | Type | Notes / attributes |
| --- | --- | --- |
| `http.server.request.duration` | histogram (s) | eval + OFREP HTTP; buckets 5 ms…10 s; semconv HTTP attrs |
| `http.server.request.body.size`, `http.server.response.body.size` | histogram (bytes) | |
| `feature_flag.flagd.impression` | counter | per evaluation; `feature_flag.key`, `feature_flag.result.variant`, `feature_flag.provider.name=flagd` |
| `feature_flag.flagd.result.reason` | counter | `feature_flag.reason` = `STATIC`, `DEFAULT`, `TARGETING_MATCH`, `DISABLED`, `ERROR`… |
| `rpc.server.duration` (ms), `rpc.server.request.size`, `rpc.server.response.size`, `rpc.server.requests_per_rpc`, `rpc.server.responses_per_rpc` | | sync service; `rpc.service=flagd.sync.v1.FlagSyncService`, `rpc.method`, `rpc.grpc.status_code` |
| `feature_flag.flagd.sync.active_streams` | gauge | `selector`, `provider_id` |
| `feature_flag.flagd.sync.stream.duration` | histogram (s, 30 s…3 h) | + `reason` = `normal_close`, `deadline_exceeded`, `client_disconnect`, `error` |

**Traces** (only when `--otel-collector-uri` set): spans `flagEvaluationService(resolveX)` (server) →
`jsonEvaluator(resolveX)` (internal); `jsonEvaluator(setState)` on config reload.

Scrape `flagd:8014` from Prometheus. Collector tip: set `resource_to_telemetry_conversion.enabled: true` on the prometheus exporter to surface resource attrs as labels.

Source: https://flagd.dev/reference/monitoring/

## 13. FIPS 140-3 build

- Two variants every release: **standard** and **FIPS** (Go Cryptographic Module v1.0.0, CMVP cert #5247, CAVP A6650, FIPS 140-3 approved mode). flagd itself is not CMVP-submitted.
- Get it: `docker pull ghcr.io/open-feature/flagd:latest-fips` (or `:0.16.3-fips`); archives `flagd-fips_0.16.3_Linux_x86_64.tar.gz` etc. Also `flagd-proxy:latest-fips`.
- Build: `GOFIPS140=v1.0.0 CGO_ENABLED=0 go build -tags fips140 -o bin/flagd-fips ./flagd`. Use the literal `v1.0.0`, not `certified`/`inprocess`. Tag without `GOFIPS140` → binary refuses to start.
- Verify: `go version -m bin/flagd-fips | grep -E 'GOFIPS140|DefaultGODEBUG|tags'` → `-tags=fips140,fips140v1.0`, `DefaultGODEBUG=fips140=on`, `GOFIPS140=v1.0.0-c2097c7c`. `flagd version` prints `build variant: fips` / `FIPS 140-3 mode: enabled`; startup log repeats it.
- Enforcement: `GODEBUG=fips140=off` makes a FIPS build **refuse to run**. No override flag.
- TLS restricted to TLS 1.2/1.3; AES-GCM (and 2 CBC-SHA256 suites on 1.2); ECDHE P-256/384/521, X25519MLKEM768, SecP256r1MLKEM768, SecP384r1MLKEM1024; certs RSA ≥ 2048, ECDSA P-256/384/521, Ed25519. **Excluded**: ChaCha20-Poly1305, plain X25519, SHA-1, 3DES, RC4, TLS 1.0/1.1. Applies to inbound *and* outbound (sync sources, kube-apiserver) — check peers before switching.
- Not released for `windows/386`, `linux/386` in FIPS form; Go FIPS unavailable on wasm/openbsd/aix.
- Non-security hashing (MurmurHash3 for fractional, FNV-1a jitter, SHA3-256 change detection) is unaffected. Cloud SDKs (S3/GCS/Azure) link non-approved primitives but only on credential/integrity paths; tracked in `docs/reference/fips-crypto-closure.txt`.
- flagd stores no keys; TLS keys and sync secrets are read from files/config and held as Go strings — protect with file perms and short-lived credentials.

Source: https://flagd.dev/reference/fips-140-3/

## 14. Kubernetes

### Plain Deployment (no operator) — from `config/deployments/flagd/`

```yaml
apiVersion: v1
kind: ConfigMap
metadata: { name: open-feature-flags }
data:
  flags: |
    { "$schema": "https://flagd.dev/schema/v0/flags.json",
      "flags": { "myStringFlag": { "state": "ENABLED", "variants": { "key1": "val1", "key2": "val2" }, "defaultVariant": "key1" } } }
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: flagd, labels: { app: flagd } }
spec:
  replicas: 2
  strategy: { type: RollingUpdate, rollingUpdate: { maxSurge: 1, maxUnavailable: 0 } }
  selector: { matchLabels: { app: flagd } }
  template:
    metadata: { labels: { app: flagd, app.kubernetes.io/name: flagd } }
    spec:
      containers:
        - name: flagd
          image: ghcr.io/open-feature/flagd:0.16.3
          args: ["start", "--uri", "file:/etc/flagd/config.json", "--log-format", "json"]
          ports:
            - { containerPort: 8013, name: eval }
            - { containerPort: 8014, name: mgmt }
            - { containerPort: 8015, name: sync }
            - { containerPort: 8016, name: ofrep }
          readinessProbe: { httpGet: { path: /readyz, port: 8014 }, initialDelaySeconds: 5, periodSeconds: 5 }
          livenessProbe:  { httpGet: { path: /healthz, port: 8014 }, initialDelaySeconds: 5, periodSeconds: 60 }
          volumeMounts: [{ name: config-volume, mountPath: /etc/flagd }]
      volumes:
        - name: config-volume
          configMap: { name: open-feature-flags, items: [{ key: flags, path: config.json }] }
---
apiVersion: v1
kind: Service
metadata: { name: flagd-svc }
spec:
  selector: { app.kubernetes.io/name: flagd }
  ports:
    - { name: eval, port: 8013, targetPort: 8013 }
    - { name: sync, port: 8015, targetPort: 8015 }
    - { name: ofrep, port: 8016, targetPort: 8016 }
```

ConfigMap mounts update via symlink swap (atomic, single fsnotify event) but can lag up to kubelet
sync period (~1 min). Multiple replicas behind a Service may briefly disagree after a change.

### Kubernetes sync (`core.openfeature.dev/ns/name`) RBAC

flagd (or flagd-proxy) reading `FeatureFlag` CRs needs `get/list/watch` on `featureflags.core.openfeature.dev`.
The operator ships ClusterRole `open-feature-operator-flagd-kubernetes-sync`; bind your ServiceAccount to it
(`config/deployments/kube-flagd-proxy/crb.yaml` does this for `flagd-proxy/default`). Pods that need it
carry annotation `openfeature.dev/allowkubernetessync: "true"` so the operator adds the binding.

### flagd-proxy — from `config/deployments/kube-flagd-proxy/`

```shell
kubectl create namespace flagd-proxy
kubectl apply -f config/deployments/kube-flagd-proxy/   # deployment (8015), service flagd-proxy-svc, ClusterRoleBinding
```

```yaml
# consumer flagd (sidecar or standalone) subscribing to a CR through the proxy
args:
  - start
  - --sources
  - '[{"uri":"flagd-proxy-svc.flagd-proxy.svc.cluster.local:8015","provider":"grpc","selector":"core.openfeature.dev/default/end-to-end"}]'
---
apiVersion: core.openfeature.dev/v1beta1
kind: FeatureFlag
metadata: { name: end-to-end, namespace: default }
spec:
  flagSpec:
    flags:
      color:
        state: ENABLED
        variants: { red: "CC0000", green: "00CC00", blue: "0000CC" }
        defaultVariant: red
```

### OpenFeature Operator (OFO)

The operator is a separate project; flagd docs only link to it. The following is from the OFO repo
(https://github.com/open-feature/open-feature-operator/tree/main/docs) — verify field names against the
installed CRD (`kubectl explain featureflagsource.spec`).

```shell
# prerequisite: cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/latest/download/cert-manager.yaml
kubectl wait --for=condition=Available -n cert-manager deploy/cert-manager-webhook --timeout=120s
# operator via Helm
helm repo add openfeature https://open-feature.github.io/open-feature-operator/ && helm repo update
helm upgrade --install openfeature openfeature/open-feature-operator --namespace open-feature-operator-system --create-namespace
```

CRDs (`core.openfeature.dev/v1beta1`): `FeatureFlag` (the flag document under `spec.flagSpec`),
`FeatureFlagSource` (how the injected flagd is started: sources, ports, evaluator, OTel), `InProcessConfiguration`
(env vars injected for in-process providers), `Flagd` (standalone flagd Deployment+Service+optional Ingress/Gateway managed by OFO).

```yaml
apiVersion: core.openfeature.dev/v1beta1
kind: FeatureFlagSource
metadata: { name: app-flags-source, namespace: default }
spec:
  sources:
    - source: default/end-to-end      # <ns>/<FeatureFlag name>
      provider: kubernetes            # kubernetes | filepath (ConfigMap mount) | http | grpc | flagd-proxy
  port: 8013
  managementPort: 8014
  evaluator: json
  probesEnabled: true
  debugLogging: false
  # otelCollectorUri: otel-collector.observability:4317
  # envVarPrefix: FLAGD          # env prefix used when injecting into the app container
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: my-app }
spec:
  template:
    metadata:
      annotations:
        openfeature.dev/enabled: "true"                               # inject flagd sidecar
        openfeature.dev/featureflagsource: "default/app-flags-source" # comma-separated list allowed
        # in-process instead of sidecar (no flagd container; app gets FLAGD_* env pointing at flagd-proxy):
        # openfeature.dev/inprocessconfiguration: "default/my-inprocess-config"
        # openfeature.dev/allowkubernetessync: "true"                 # only if the pod itself needs CR RBAC
    spec:
      containers:
        - name: app
          image: my-app:1.0
```

With the sidecar the app talks to `localhost:8013` (RPC provider). With `provider: flagd-proxy` OFO deploys
flagd-proxy in its namespace and sidecars subscribe via gRPC; with `openfeature.dev/inprocessconfiguration`
no sidecar is injected and the in-process provider syncs from flagd-proxy on 8015.

Source: https://flagd.dev/reference/openfeature-operator/overview/ , GitHub `config/deployments/`, `flagd-proxy/README.md`, OFO docs (external)

## 15. Versioning, support, naming

- Monorepo, independent release-please tracks: `flagd/vX.Y.Z`, `flagd-proxy/vX.Y.Z`, `core/vX.Y.Z`. Pre-1.0 today; ecosystem policy: **minor** = features, may break with deprecation; **patch** = critical fixes only, never changes bundled schema or defaults.
- Deprecations: announced in a minor, kept ≥ 3 minors **or** 12 months (longer wins), runtime warnings, removed in a later minor. Documented future flips (e.g. `--disable-sync-metadata` → `true`) count as breaking.
- Breaking for the daemon includes: flag/env names, types or defaults; metric renames; URI prefixes; merge precedence; startup fail-open/close; exposed API versions.
- ~3 minors "supported"; best-effort SLO: CVEs 14 days, severe bugs 31 days. Artifacts immutable, SHA-256 published, images cosign-signed.
- Recent notable: 0.16.0 `DISABLED` flags now resolve successfully with `reason=DISABLED` (was `FLAG_DISABLED` error); 0.16.1 server read timeouts; 0.16.3 FIPS variant, `GET /v1/flags`, OFREP SSE.
- **Naming**: always lower-case single word "flagd" (like sshd/systemd) in packages, variables, docs.

Source: https://flagd.dev/architecture-decisions/semantic-versioning-policy/ , https://flagd.dev/reference/naming/ , GitHub `flagd/CHANGELOG.md`

## 16. Troubleshooting (deployment)

| Symptom | Cause / fix |
| --- | --- |
| `bind: address already in use` on 8013/8014/8015/8016 | Another flagd or app on the port. Change with `-p/-m/-g/-r` or `FLAGD_*_PORT`. flagd-proxy also defaults to 8015/8016 — do not co-locate without remapping. |
| Container exits immediately, `open …: permission denied` / `no such file` | Image runs as UID 65532; `chmod o+r` the file, check the mount path matches `--uri`, and remember only `.json/.yaml/.yml` extensions are accepted for `file:`. |
| `/readyz` stuck at 412 | Some source has never synced: bad URL/creds, unreachable gRPC target, k8s RBAC missing, invalid JSON/schema. Run with `--debug`; every source must succeed once. |
| Flags not updating after editing file | On non-k8s hosts `file` polls via `os.Stat` (mtime); with Docker Desktop bind mounts on macOS/Windows events may not propagate — use WSL or `provider: fileinfo`. Use a symlink + atomic swap in production. |
| Duplicate change events on save | Editor/FS behaviour; harmless. Symlink swap yields one event. |
| HTTP source never changes | Server returning stale `ETag`/304, or `interval` too large (max 86400). Confirm with `curl -i` and `If-None-Match`. |
| `Received unexpected EOS on empty DATA frame` | HTTP/2 blocked between client and 8015; allow h2/gRPC on the LB/ingress or terminate TLS with h2 enabled. |
| gRPC sync clients reconnecting every ~60–90 s (older versions) | Was grpc-go keepalive enforcement (`ENHANCE_YOUR_CALM`); fixed in 0.16.1+ (now no enforcement). Upgrade. |
| Selector returns nothing / everything | Syntax is `flagSetId=x` (not `:`); header beats body beats source config; `flagSetId=` selects the null set; check reflected `metadata` in the response. |
| `--sources` ignored | You also passed `--config`; sources then come only from the file. |
| FIPS image fails handshake with a source / client | Peer offers only ChaCha20, plain X25519, or RSA < 2048. Fix peer or use the standard image. |
| Metrics empty in Prometheus after `--metrics-exporter otel` | OTLP mode disables `/metrics`; scrape the collector's prometheus exporter instead. |

Debug quickly: `flagd start --debug --log-format json --uri … 2>&1 | jq .`, then
`curl -s localhost:8014/readyz -o /dev/null -w '%{http_code}\n'` and
`curl -X POST localhost:8016/ofrep/v1/evaluate/flags -H 'Content-Type: application/json' -d '{}'`.

Source: https://flagd.dev/troubleshooting/ , https://flagd.dev/reference/monitoring/#readiness--liveness-probes
