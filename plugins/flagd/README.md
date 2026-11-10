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
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install flagd@wovemind
```

## Requirements

None for the skill itself. To run what it writes you need flagd (as a Docker image, a binary or on Kubernetes) and, in your application, the OpenFeature SDK with the flagd provider for your language.

## Usage

The skill triggers automatically when flagd, OFREP, the OpenFeature flagd provider, or self-hosted feature flags come up. Invoke explicitly with `/flagd:flagd`.

Example prompts:

- "Add a 10% rollout of `new-checkout` for logged-in users to our flagd config"
- "Run flagd in docker-compose next to my FastAPI app and evaluate a flag from Python"
- "Why does my in-process flagd provider return the default for every flag?"
- "Gate the feature on app version >= 2.3.0 using flagd semver targeting"

## Example

Ask Claude:

> "Add a 10% rollout of `new-checkout` to our flagd config."

Claude adds a flag whose targeting uses `fractional`, which buckets users by their `targetingKey`:

```json
{
  "$schema": "https://flagd.dev/schema/v0/flags.json",
  "flags": {
    "new-checkout": {
      "state": "ENABLED",
      "variants": { "on": true, "off": false },
      "defaultVariant": "off",
      "targeting": { "fractional": [["on", 10], ["off", 90]] }
    }
  }
}
```

It also reminds you that your application must pass a `targetingKey` (for example the user id) in the evaluation context. Without one, the evaluation fails and your code falls back to its default value.

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
