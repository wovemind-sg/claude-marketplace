---
name: explain
description: Explain code, a file, a flow, or a concept in the current project to a user who is learning an unfamiliar stack, building only on the topics they already know well plus what earlier explanations covered, and log each new concept to ~/.explain_skill/. Use whenever the user asks to explain, walk through, break down, or help them understand code, an idiom, a language feature, a framework concept, an architecture, or how something in the codebase works — e.g. "what does this goroutine do", "how does DI work in this .NET service", "walk me through the request flow", "why is this a struct and not a class" — even if they don't say "explain".
argument-hint: "<code path, symbol, question, or concept>"
---

Explain `$ARGUMENTS` to someone learning an unfamiliar stack. If `$ARGUMENTS` is empty, see "IDE context" below to decide what to explain. The user is typically an experienced engineer who is fluent in some languages and new to others. A good explanation meets them where they are: it builds on what they know, defines everything else, and never assumes background they have not shown.

The core rule: **an explanation may rely only on (a) topics the user marked as known, and (b) concepts already recorded in their learning log.** Anything else is new, and you must introduce it before you use it. Engineers new to a stack are rarely confused by the big idea; they get lost on one unexplained term in the middle of the explanation. The log exists so you can tell which terms those are.

## IDE context

When Claude Code is connected to an IDE, the conversation contains notes from the IDE. One note says the user selected lines N–M of a file, and it includes the selected text. Another note says the user opened a file. Use only the most recent note of each kind. If no argument is given, choose the target in this order:

1. **Highlighted code**: the selected lines.
2. **Opened file**: the whole file currently open in the IDE.
3. **Neither**: the code or concept the user just asked about in the chat. For `explain-known` and `explain-unknown`, the fallback is the current project instead.

Name the target in your first line, for example "Explaining `pool.go:40-58` (your selection)", so the user can see which input you used.

## The database: `~/.explain_skill/`

```
~/.explain_skill/
├── profile.md                  ← known topics + topics being learned
└── topics/
    └── <topic-slug>/
        ├── index.md            ← one line per concept: name, depth, keywords, detail file
        └── <concept-slug>.md   ← full notes for one concept
```

The log grows with every explanation, so it uses progressive disclosure. The index stays small enough to read in full. Each detail file is read only when its concept matters for the current explanation. Don't put detail in `index.md`, and don't read every detail file "just in case". Reading everything would fill the context window with notes that don't matter.

`profile.md`:

```markdown
# Explain profile

## Known
- C++
- Python

## Learning
- .NET
- C#
- Go
- orders-service (project)
```

`topics/go/index.md` has one line per concept, with keywords for matching and a pointer to the concept's detail file:

```markdown
# Go

- **goroutines** [core] — go statement, concurrency, scheduler, lightweight thread → goroutines.md
- **defer** [surface] — cleanup, function exit, LIFO, resource release → defer.md
```

The depth tag is one of `surface`, `core`, or `deep`. Keywords are the terms a future question or future code might use for this concept, including the analogous terms from `Known` topics. Choose keywords so that matching a question against the index finds the concept.

`topics/go/goroutines.md` holds the full notes for one concept:

```markdown
# goroutines (Go)

**Summary:** Lightweight threads managed by the Go runtime and multiplexed onto OS threads. You start one with `go f()`.
**Depth:** core. Covers starting goroutines, their lifetime, and the leak risk. Does not cover scheduler internals or GOMAXPROCS.
**Analogy used:** std::thread plus a thread pool (C++). Where the analogy breaks: goroutines are cheap enough to create one per request.
**Gotchas covered:** the loop-variable capture change in Go 1.22.
**History:**
- 2026-09-23, from internal/worker/pool.go: introduced while explaining how the worker pool shuts down.
```

Slug rules: lowercase, `.NET` → `dotnet`, `C#` → `csharp`, `C++` → `cpp`, and any other run of non-alphanumeric characters → `-`. Match topic names case-insensitively and treat obvious aliases as the same topic (`golang` = `Go`, `dotnet` = `.NET`), so the log does not split one topic across two directories.

Each entry records what you actually explained, at the depth you explained it. If you only touched a concept on the surface, say so, and write what you left out in the detail file ("did not cover buffered vs unbuffered"). Later explanations then know what they can rely on and what still needs explaining.

## Step 1 — Load or create the profile

Read `~/.explain_skill/profile.md`.

If it does not exist, this is the first use. Ask the user two questions in one message, then stop and wait for the answer:

1. Which topics do you want to learn? (languages, frameworks, tools — e.g. ".NET, C#, Go")
2. Which topics do you already know well? (e.g. "C++, Python")

Write `profile.md` from the answers, then continue with the original request. Don't guess the answers from context. The whole skill rests on this baseline being what the user said, not what you inferred.

## Step 2 — Register the current project

Get the project name with `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"`. If that name is in neither `Known` nor `Learning`, add `<name> (project)` to `Learning`. Tell the user in one line that you did this and that `/explain:explain-known` marks it as known. A codebase is its own topic: its components, conventions, and domain terms are just as unfamiliar to a newcomer as the language is.

## Step 3 — Build the baseline

Read `topics/<slug>/index.md` for every `Learning` topic the question involves. That is always the project's topic, plus each language or framework the code uses. The **baseline** is:

- every `Known` topic, which you may assume the user knows in depth, and
- every concept listed in those indexes, at the depth tag recorded.

Open a concept's detail file only when that concept appears in this explanation, which you can tell by matching keywords against the question and the code. Also open it when the depth tag leaves you unsure whether you can rely on the concept, or when you want to reuse the analogy that was used before. Opening two or three detail files is normal. Opening all of them is a sign you are not using the keywords.

## Step 4 — Investigate before explaining

Read the actual code in the project: follow the call chain, the types, and the config that wires things together. Cite locations as `path:line`. An explanation grounded in the user's real code sticks much better than a generic tutorial, and it catches cases where the project uses a concept in an unusual way.

If the request is a pure concept ("what is a channel") with no code attached, look for a real use of it in the project and use that as the example when one exists.

## Step 5 — Plan: find every new concept

List every concept the explanation needs. Mark each one as either in the baseline or new. For each new concept:

- If it is small, define it inline where it first appears, in one or two sentences.
- If it is large, or if other ideas depend on it, give a short primer before the main explanation.
- Anchor it to the **most comparable topic in the user's `Known` list**. Choose separately for each concept, and don't default to one favorite language. For example, compare a goroutine to Kotlin coroutines if the user knows Kotlin, or to OS threads plus a scheduler if they only know C. Compare C# LINQ to Java streams or to Python comprehensions, whichever the user knows. If no known topic has an honest analogy, explain the concept from first principles. A forced analogy is worse than none. The languages named in this file are illustrations only. Always work from the actual `Known` list.
- Say where the analogy breaks. Watch for **false friends**: things that look like a known concept but behave differently. Examples are Go slices sharing their backing array, C# `struct` being a value type while `class` is a reference type, `defer` being function-scoped rather than block-scoped, and `async void` in C#. These cause the bugs experienced engineers write in a new language, so flag them explicitly.

Don't use a term that is not in the baseline without defining it first. This includes terms that seem obvious to someone who already works in the stack, such as "middleware pipeline", "receiver", "NuGet", or "LINQ". If a concept is already in the log, refer to it briefly ("the `context.Context` we covered before") instead of re-explaining it. This is how the explanations build on each other.

## Step 6 — Explain

Use this shape. Drop any section that adds nothing for the specific question:

1. **TL;DR** — two or three sentences.
2. **New concepts** — the primers from Step 5, if any.
3. **Walk-through** — the actual explanation, grounded in the project's code with `path:line` references. Show short code excerpts where they help; the user should not have to open five files to follow along.
4. **Diagram** — see below.
5. **Gotchas** — false friends and surprising behavior relevant to this code.
6. **Logged** — one line listing the concepts you are adding to the log.

### Graphics

Draw a diagram when the thing being explained has structure that prose flattens: a request flow, a call chain across layers, object ownership or lifetimes, concurrency (goroutines and channels, async continuations), a startup and registration sequence, or a type hierarchy. Skip the diagram for a single idiom or a one-function answer, because a diagram there is just noise.

Draw diagrams as ASCII or Unicode box-and-arrow art inside a code block. The terminal renders code blocks faithfully, but it does not render Mermaid. Keep diagrams narrow (about 80 columns) and label the arrows with what flows along them: calls, data, messages, or ownership.

```
HTTP request
    │
    ▼
┌────────────┐  next()   ┌────────────┐  next()   ┌──────────────────┐
│ Auth       │ ────────▶ │ Logging    │ ────────▶ │ OrdersController │
│ Middleware │ ◀──────── │ Middleware │ ◀──────── │ .Get(id)         │
└────────────┘  response └────────────┘  response └──────────────────┘
```

When a flow is too big for about 40 lines of ASCII, split it into an overview diagram and a zoomed-in diagram. Don't cram everything into one.

## Step 7 — Update the log

For each concept you introduced or deepened, update both of its files in `topics/<topic-slug>/`. Create the directory and an `index.md` with a `# <Topic>` header if they do not exist. Rules:

- **New concept:** write `<concept-slug>.md` in the detail format shown above, then add one line to `index.md` with the name, depth tag, keywords, and file name.
- **Concept already logged:** update its detail file in place. Add a `History` line, and revise `Depth`, `Gotchas covered`, or `Analogy used` if they changed. In the index, change the depth tag and add keywords only if they changed. Don't add a second index line.
- Keep each index line to one line. If you need more words, put them in the detail file.
- Language concepts go under the language's topic. Project-specific knowledge goes under the project's topic: what a component does, how modules connect, domain terms, and conventions. One explanation often adds to both.
- Don't log topics listed under `Known`, since those need no tracking.

Write the log after you give the explanation, so the user never waits on bookkeeping. Don't skip the log. A missed entry means the next explanation will either re-explain the concept or, worse, treat it as unknown.
