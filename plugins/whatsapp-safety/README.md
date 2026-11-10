# whatsapp-safety

Claude Code skill. Guides agents interact WhatsApp via **Evolution API** without connected number flagged, restricted, or banned permanent.

Evolution API drive *unofficial* WhatsApp Web session — no official protection, ban usually permanent for number. Skill encode behaviors keep automation look human: account warm-up, human-paced randomized delays, message spinning, consent/opt-in discipline, safe group handling, early ban-signal detection.

## What it does

Ask Claude send WhatsApp messages, manage groups, run outreach, wire Evolution API webhooks — skill trigger, steer implementation toward safe patterns. It:

- Classify task by ban risk (reply-driven → cold outreach), warn on high-risk work.
- Provide copy-ready safe sender (number validation, typing presence, randomized human delays, per-recipient content spinning, daily caps, error back-off).
- Cover account warm-up ramps, rate limits, content rules, group/participant safety, incident response.
- Include concrete Evolution API v2 endpoint patterns.

## Installation

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install whatsapp-safety@wovemind
```

To test changes from a local clone instead, run these from the root of the clone:

```
/plugin marketplace add ./
/plugin install whatsapp-safety@wovemind
```

## Requirements

- An Evolution API server (version 2) that you run yourself, with a WhatsApp number connected to one of its instances.
- Permission to message the people you send to: your own number, and recipients who opted in.
- The `evolution-api` plugin from this marketplace is optional. It holds the full endpoint reference; this plugin covers how to use those endpoints safely.

## Usage

Skill trigger automatic on WhatsApp/Evolution-API tasks. Read decision guide, load only reference files relevant to task:

| File | When it's used |
|------|----------------|
| `references/account-warmup.md` | New number or number < ~2 weeks old |
| `references/rate-limiting.md` | Any proactive send — pacing, delays, caps |
| `references/message-content.md` | Message bodies — spinning, avoiding spam patterns |
| `references/outreach-and-broadcast.md` | Cold outreach or broadcasting (highest risk) |
| `references/groups.md` | Creating groups, adding participants |
| `references/evolution-api.md` | Concrete endpoint calls, webhooks, safe sender code |
| `references/incident-response.md` | Warning signs, temporary restriction, or a ban |

## Environment variables

Example code in `references/evolution-api.md` reads:

| Variable | Description |
|----------|-------------|
| `EVO_BASE` | Base URL of your Evolution API instance |
| `EVO_INSTANCE` | Instance name for the connected number |
| `EVO_APIKEY` | Evolution API key (sent as the `apikey` header) |

Keep these in env vars — never hardcode or commit.

## Example

> "Send a WhatsApp message to these 40 customers letting them know their order shipped."

Skill classify medium-risk (opted-in customers), Claude build paced sender: validate each number on WhatsApp, set typing presence, spin shipping message per recipient, spread sends randomized 20–90s delays inside working hours, cap daily volume, halt if failures climb — instead naive for-loop blast identical text.

## Note

Skill about **operational safety** of automation you're authorized run (own bot/number, opted-in recipients). Steer away from spam and cold-blasting strangers — violates WhatsApp's terms, gets numbers banned — recommend official WhatsApp Business Platform for proactive messaging at scale.