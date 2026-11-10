---
name: explain-unknown
description: Add topics to the list of things the user wants to learn in the explain skill's profile (~/.explain_skill/profile.md), so explanations stop assuming them and start logging them. With no argument, it marks the concepts in the IDE's highlighted code or opened file as not yet understood. With no argument and no IDE context, it adds the current project as a learning topic.
argument-hint: "[topic, topic, ...]  (empty = IDE selection, then opened file, then current project)"
disable-model-invocation: true
---

Mark something as **unknown**, so that explanations treat it as unfamiliar and explain it before relying on it.

Before you start, read the "IDE context" and "database" sections of `${CLAUDE_PLUGIN_ROOT}/skills/explain/SKILL.md`. They define how to choose the target, the profile and topic-file formats, the slug rules, and alias matching.

If `~/.explain_skill/profile.md` does not exist, first run the first-use questions from Step 1 of the explain skill and write the profile. Then continue.

## With arguments: whole topics

1. Split `$ARGUMENTS` on commas.
2. For each topic, remove it from `Known` if it is listed there. Match case-insensitively and treat aliases as the same topic.
3. Add the topic to `Learning` unless it is already listed.
4. Don't create `topics/<slug>/` yet. The explain skill creates it when it logs the first concept.

## No argument, IDE selection or opened file: concepts in that code

The user is saying "I don't really understand this code". Your job is to make sure the next explanation covers these concepts instead of assuming them.

1. Read the target: the selected lines, or the whole opened file if nothing is selected.
2. List the concepts the target uses, grouped by topic. For an opened file, include the file's role in the project.
3. If one of those topics is listed under `Known`, don't move it. The user may know most of the topic but not this part. Mention the concept in the report instead.
4. For each concept that is logged under a `Learning` topic, remove its line from `index.md` and delete its detail file. The next explanation will then explain the concept again from the start.
5. If a concept's topic is in neither list, add the topic to `Learning`.

## No argument, no IDE context: the current project

Apply the steps from "With arguments: whole topics" to `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"`, adding a ` (project)` suffix.

## Report

Reply in one short message. Name the target you used, and list what you added, moved, or removed. After a selection or file target, offer to explain it now with `/explain:explain`.
