# Which Claude model to build with: decision rules

Source: https://claude.dev/blog/which-claude-model-should-you-build-with/ (Addy Osmani, published Nov 09 2026). Copied on 2026-11-27. Prices are Claude API list prices.

Models available: Claude Haiku 5.5, Claude Sonnet 5.5, Claude Opus 5.5, Claude Fable 5.2. (Claude Mythos 5.2 is for cybersecurity and life sciences research, verification programs only. Do not recommend it.)

## Defaults

- Start most work on Opus 5.5 at its default effort, medium. It is the default model in Claude Code and costs half as much per token as Fable 5.2.
- Move down to Sonnet 5.5 for well-scoped everyday work (bug fix, feature built against a spec). A clear spec alone is not enough: a migration or a performance optimization can have a clear spec and still need Opus 5.5, or Fable 5.2 for a major one.
- Move further down to Haiku 5.5 for the simplest high-volume work (classification, routing, extraction), and for subagents doing a larger model's side tasks.
- Move up to Fable 5.2 for the hardest technical projects in coding, finance and the sciences; when Opus 5.5 at high still falls short; and for long unattended runs.
- Adjust effort before changing model. Past high, one more effort level can cost as much as a bigger model: test the next model up at a lower effort instead. One level down can give the same result at a lower rate.
- Higher effort helps when the model needs to think longer, call more tools or check its own work more. It adds latency. It does not add knowledge or skill the model lacks: that needs a bigger model.

## Task table

| Task | Starting model | Starting effort | Why |
|---|---|---|---|
| Everyday engineering and debugging. Multi-PR feature work | Opus 5.5 | medium (default), then high | Balance of cost and capability for everyday tasks. |
| Classification, routing, tagging, high-volume extraction | Haiku 5.5 | medium (default) | Lowest cost and latency in the family. |
| Subagents that search files, read logs, or summarize | Haiku 5.5 or Sonnet 5.5 | the model's default | Wrong answers are cheap to spot, and the main model has the judgment calls anyway. |
| Chat and interactive sessions | Sonnet 5.5 (or Haiku 5.5 for simple chat at volume) | low or medium | Sonnet 5.5 is fast, especially on low or medium effort. |
| Well-scoped coding: bug fixes, feature iteration, spec-driven work | Sonnet 5.5 | medium, then high for harder tasks | Handles scoped tasks well at half the Opus 5.5 token price. |
| Everyday documents, slides, spreadsheets | Sonnet 5.5 | high (default; medium in Claude Code) | Iterates fast, strong eye for design. For a complex financial model, or a document built from a large pile of source material, start on Opus 5.5. |
| Agent tasks run repeatedly: investigation, review, drafting | Sonnet 5.5 | medium | Well-defined, repeated tasks rarely need a bigger model. |
| Computer use and vision-heavy workflows | Opus 5.5 | medium | Long agentic loops over many screenshots and images, the long-running agentic work Opus 5.5 is built for. |
| Major refactors and migrations, architecture planning, leading many subagents | Fable 5.2 | medium, then high (API default is high) | Most capable generally available model for technical fields. |
| Deep research, scientific or quantitative analysis | Fable 5.2 | medium, then high (API default is high) | Built for the hardest technical projects in coding, finance and the sciences. |
| You aren't sure yet | Opus 5.5 | medium (default) | Claude Code default on Pro, Max, Ultra, Team, Enterprise and the API; platform docs recommend it as the starting point. |

## The four models

| | Haiku 5.5 | Sonnet 5.5 | Opus 5.5 | Fable 5.2 |
|---|---|---|---|---|
| Built for | High-volume, cost-sensitive tasks | Fast, capable help with well-scoped tasks | Daily driver for complex coding and knowledge work | Most ambitious, open-ended technical work |
| Relative latency | Fastest | Fast | Moderate | Moderate |
| Input / output per 1M tokens | $0.10 / $0.50 up to 100K-token prompts; $0.50 / $2.50 over 100K | $2 / $10 | $4 / $20 | $8 / $40 |
| Cache reads per 1M tokens | $0.01 up to 100K; $0.05 over 100K | $0.10 | $0.20 | $0.20 |
| Context window | 1M | 1M | 1M | 1M |
| Max output | 128K | 128K | 128K | 128K |
| Thinking on the API | Adaptive, on by default, can be turned off | Adaptive, on by default; between_tools skips upfront thinking | Adaptive, always on | Adaptive, always on |
| Default effort on the API | medium | high (medium in Claude Code) | medium | high (medium in Claude Code) |
| Fast mode | No | No | Yes | Yes |

## Tie-breaks and cost per finished task

- Price per token is not cost per task. Opus 5.5 at high matched the previous Fable (5.1) at max on Terminal-Bench 3.0 with half the tokens. Fable 5.2 at high matched Opus 5.5 at max on FrontierCode 2.0 (45.3% vs 45.5%) for about half the cost per task. So before raising Opus 5.5 past high on a hard task, test Fable 5.2. For everyday work Opus 5.5 at medium is the place to start.
- Small models do well on high-volume work with checkable outputs and are less suited to long agentic loops.
- Price the hardest tasks, not only the typical ones: they carry most of the spend.
- Latency: for replies a person waits on, start Sonnet 5.5 at low or medium. Effort and latency are roughly correlated.
- Effort cost (Opus 5.5, SWE-bench Pro): medium is about 2.5 points lower for about 70% of the cost of high; low is about 8 points lower for about a third of the cost; xhigh is about 1.4 points higher for 2.5 times the cost of high.
- Faster output from the same model: fast mode (Opus 5.5 and Fable 5.2 only), at premium pricing.
- Haiku 5.5 is the only model whose token price varies by prompt length (over 100K tokens costs 5 times as much, still a quarter of Sonnet 5.5). It pays off most on short prompts (a twentieth of Sonnet 5.5's input price). With long prompts on every call, compare on cost per finished task.
- A lean main context matters more the bigger the main model is. Keep the expensive model's context for decisions; let cheaper subagents do the verbose reading.
- Judgment-heavy or large-scope work leans to the bigger model. Cheap-to-verify, high-volume work leans to the smaller model. Unsure: Opus 5.5 medium.

## Escalation order when a model is not good enough

1. Check the model can verify its own work (a test, a build, a script that calls the endpoint). Often cheaper and lower latency than changing effort.
2. Raise effort one level.
3. Move to the next model up, starting at a lower effort than you used on the smaller one.

If outcomes can be checked automatically, run everything at a low level and re-run only the failures at a high one. Example: Opus 5.5 at low with failures re-run at high passed about 97% of tasks at about $0.17 each, against 95.3% at $0.29 with every task at high.

## Mixing models

- Switch models at a natural break. The prompt cache belongs to the model that wrote it; the first turn on a new model pays the cache-write price on the whole conversation. Run /compact first in Claude Code, or start a fresh session with a short written plan.
- A model never reads thinking blocks of a model above it, so a move down a tier loses earlier reasoning. A move from Fable 5.2 to any other model drops its reasoning.
- Put subagents on smaller models (model: haiku or model: sonnet in the subagent definition; CLAUDE_CODE_SUBAGENT_MODEL sets the default). Keep small models on work where a mistake is cheap to spot: finding files, running tests, reading logs. Keep code edits and judgment calls on the main model.
- Delegate bulk work bigger than one context window: a top-tier lead splits the work among many cheaper parallel workers. Example: an Opus 5.5 lead with up to 25 Sonnet 5.5 workers cost about a third less than Opus 5.5 alone, with about the same score. Skip it for one chain of dependent steps or work that fits in one context window.
- Advisor tool (beta): a cheaper executor asks a stronger advisor. No pairing in the platform cost guide clearly beat the executor alone. Measure the executor's consult rate first.
- opusplan (Opus plans, Sonnet carries out) puts code edits on Sonnet, the reverse of the advice above. Measure before making it a default.
- When the routing rule is simple (one model per step type), let code pick the model rather than a model.

## Compatibility notes

- Opus 5.5 and Fable 5.2 always think; turning thinking off returns an error.
- tool_choice of any or tool returns a 400 error on Sonnet 5.5, Opus 5.5 and Fable 5.2. Use auto with strict tools.
- Computer use works on all four through the computer_toolset_20260801 toolset.
- Haiku 4.5 to 5.5: replace budget_tokens with an effort level, drop non-default temperature/top_p/top_k, end messages with a user turn.
- Fable 5.2 preserved thinking: API returns 400 if anything before a Fable 5.2 thinking block changed. Keep history append-only.
- Safety classifiers on Opus 5.5, Sonnet 5.5 and Fable 5.2 may re-run flagged cybersecurity or biology requests on an older model in Claude Code.

## Measure on your own work

Published results give a starting model. Test candidates on real tasks with an outcome check each, at two or three effort levels, each in its own session. Keep a multi-model setup only if it beats every single-model point on a score-vs-spend chart. Quick check in Claude Code: run one backlog task on two models with /model and compare /usage.
