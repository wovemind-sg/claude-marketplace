# product-experience-strategist

Expert product strategy, UX/UI design, and business development judgment for Claude, applied to
digital products and end-to-end user flows.

## What it does

Operates as a product strategist, principal UX/UI designer and business development lead in one.
Balances user value, business value, correct flow, compliance and technical feasibility instead of
optimizing for visual polish alone. Covers product decisions, UX/UI design, onboarding, flows,
growth, monetization, subscriptions, AI features, family/children experiences, consent, privacy,
accessibility, and implementation reviews.

For multi-session or multi-agent work (a new flow, a redesign, an implementation handoff), the
skill also loads `references/system.md` — the process layer: roles, approval gates, persistent
memory, job/result protocol, QA routes, and the correction-loop cap.

## When it activates

Triggers on product decisions, UX/UI design or review, onboarding/flow design, growth and
monetization work, subscription design, AI feature design, family/children product experiences,
consent and privacy flows, accessibility, and implementation reviews.

## Installation

```bash
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install product-experience-strategist@wovemind
```

## Requirements

None. The skill is prompt-only and needs no other tools or plugins.

## Environment variables

None.

## Usage

The skill activates automatically for product/UX/design work. You can also invoke it directly:

```
/product-experience-strategist:product-experience-strategist
```

## Example

Ask Claude:

> "Review our signup flow. Users have to create an account before they can see any of the app."

Claude reviews the flow as a product strategist and designer would. It weighs what the user gets against what the business needs at each step, points out where people are likely to drop off (here, asking for an account before showing any value), and proposes a revised flow, for example letting people try the core feature first and asking for an account when they want to save their work. It also checks the parts that are easy to miss, such as consent wording, privacy, accessibility, and whether the change is feasible to build.

## What it does not include

No agents, scripts, or config ship with this skill — it's prompt-only. No taste-profile data,
project memory, decision logs, or run state ship either; those are generated per user and per
project the first time the skill is used on real work.
