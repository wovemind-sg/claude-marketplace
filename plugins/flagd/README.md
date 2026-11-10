# flagd

Complete reference skill for [flagd](https://flagd.dev/), the OpenFeature feature-flag evaluation engine.

## Purpose

Gives Claude everything it needs to work with flagd without browsing:

- write and debug flag definition files (`*.flagd.json` / `.yaml`): variants, JSON Logic targeting, `fractional` rollouts, `sem_ver` gates, `$evaluators`, metadata and flag sets
- install and run flagd (Docker, binary, systemd, Kubernetes via the OpenFeature Operator), configure sync sources (`--uri`, `--sources`), selectors, static/header context, metrics
- wire an application to flagd with the OpenFeature SDK and the flagd provider in Go, Java, Node.js, browser, Python, .NET, PHP or Rust, in RPC, in-process or offline mode
- call flagd directly over Connect/gRPC, OFREP, and the sync service (`curl`, `grpcurl`)
- troubleshoot common failures, and know where to look online when the bundled docs don't cover a topic

## Install

```
/plugin marketplace add wovemind-sg/claude-marketplace
/plugin install flagd@wovemind
```

## Usage

The skill triggers automatically when flagd, OFREP, the OpenFeature flagd provider, or self-hosted feature flags come up. Invoke explicitly with `/flagd:flagd`.

Example prompts:

- "Add a 10% rollout of `new-checkout` for logged-in users to our flagd config"
- "Run flagd in docker-compose next to my FastAPI app and evaluate a flag from Python"
- "Why does my in-process flagd provider return the default for every flag?"
- "Gate the feature on app version >= 2.3.0 using flagd semver targeting"

## Layout

```
skills/flagd/
├── SKILL.md                     overview, mental model, quick start, working rules
└── references/
    ├── flag-definitions.md      flag file format, targeting operators, worked examples
    ├── deployment.md            install, CLI reference, sync sources, k8s, monitoring
    ├── providers.md             per-language OpenFeature + flagd provider setup
    ├── api.md                   evaluation/sync/OFREP protocols, curl + grpcurl
    ├── troubleshooting.md       symptom → cause → fix, FAQ, debug checklist
    └── resources.md             online sources to consult when the skill is silent
```

## Environment variables

None required by the skill itself. flagd and its providers read `FLAGD_*` variables; these are documented in the reference files.

## Source

References distilled from the `docs/` directory of https://github.com/open-feature/flagd (commit b13483f, 2026-09-18) and the OpenFeature contrib provider READMEs. Re-run the distillation when flagd ships a new minor version.
