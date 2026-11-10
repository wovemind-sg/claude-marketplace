# explain

Explains code and concepts in the current project to an engineer who is learning an unfamiliar stack, for example a C++/Python developer who is new to Go and .NET. Each explanation builds only on:

- the topics you marked as **known**, and
- the concepts that earlier explanations already covered, as recorded in a per-topic log.

The skill defines anything outside those two sets before it uses it, compares new ideas to what you already know, and flags "false friends": concepts that look familiar but behave differently. It draws ASCII diagrams for flows, call chains, lifetimes, and concurrency when a picture helps.

## Install

```
claude plugin marketplace add wovemind-sg/claude-marketplace
/plugin install explain@wovemind
```

## Requirements

- Nothing beyond Claude Code. `git` is used, when present, to name the current project after its repository.
- Optional: a connected IDE. Without an argument the skills use the code highlighted in the IDE, or the opened file; with no IDE connected they fall back to the current project.

## Opinionated defaults

| Default | Change it with |
|---|---|
| The learning log lives in `~/.explain_skill/`, shared by every project on the machine | not configurable; edit or delete the files by hand |
| The current project (its git repo name) is registered as a topic you are learning | `/explain:explain-known` with no argument and no IDE marks it known |
| Explanations go only as deep as your known topics and the log allow | `/explain:explain-known` and `/explain:explain-unknown` |

## Skills

### `/explain:explain [code path, symbol, question, or concept]`

Explains the target, grounded in the project's actual code with `path:line` references, and then appends the new concepts to the log. With no argument, it explains the code highlighted in your IDE, or the opened file if nothing is highlighted. Claude also invokes it automatically when you ask it to explain or walk through something.

On first use, it asks which topics you want to learn and which topics you already know well. It registers the current project (the git repo name) as a topic you are learning, because a codebase's components and conventions are as unfamiliar to a newcomer as its language.

### `/explain:explain-known [topic, ...]`

Marks topics as known, and moves them out of the learning list if needed. With no argument, it uses the IDE instead: the concepts in the highlighted code, or in the opened file if nothing is highlighted, are logged as understood. The language itself stays on the learning list. With no argument and no IDE connected, it marks the **current project** as known.

### `/explain:explain-unknown [topic, ...]`

Adds topics to the learning list, and moves them out of the known list if needed. With no argument, it uses the IDE instead: the concepts in the highlighted code or opened file are removed from the log, so the next explanation covers them from the start. With no argument and no IDE connected, it adds the current project.

## Data

Everything lives in `~/.explain_skill/`:

```
~/.explain_skill/
├── profile.md                      # ## Known / ## Learning lists
└── topics/<topic>/
    ├── index.md                    # one line per concept: name, depth, keywords, detail file
    └── <concept>.md                # full notes: summary, depth, analogy, gotchas, history
```

Each explanation reads only the index files for the topics it involves, then opens the detail files whose keywords match the question. The log can grow large without filling the context window. The files are plain Markdown. Edit them by hand if you want to correct what the skill thinks you know.

## Environment variables and settings

None. The plugin has no environment variables and no plugin settings.

## Example

```
/explain:explain-unknown .NET, C#, Go
/explain:explain-known C++, Python
/explain:explain how does internal/worker/pool.go shut down its goroutines?
/explain:explain what is IServiceCollection doing in Program.cs
/explain:explain                  # explain the IDE selection or opened file
/explain:explain-known            # I understand the highlighted code (or, without an IDE: I know this codebase)
```
