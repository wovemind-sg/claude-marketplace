---
name: explain-known
description: Mark topics as known well in the explain skill's profile (~/.explain_skill/profile.md), so explanations may assume them. With no argument, it marks the concepts in the IDE's highlighted code or opened file as understood. With no argument and no IDE context, it marks the current project as known.
argument-hint: "[topic, topic, ...]  (empty = IDE selection, then opened file, then current project)"
disable-model-invocation: true
---

Mark something as **known**, so that explanations may rely on it without explaining it.

Before you start, read the "IDE context" and "database" sections of `${CLAUDE_PLUGIN_ROOT}/skills/explain/SKILL.md`. They define how to choose the target, the profile and topic-file formats, the slug rules, and alias matching.

If `~/.explain_skill/profile.md` does not exist, first run the first-use questions from Step 1 of the explain skill and write the profile. Then continue.

## With arguments: whole topics

1. Split `$ARGUMENTS` on commas.
2. For each topic, remove it from `Learning` if it is listed there. Match case-insensitively and treat aliases as the same topic. Keep the ` (project)` suffix on project entries.
3. Add the topic to `Known` unless it is already listed.
4. Keep `topics/<slug>/` as it is. If the user later moves the topic back to learning, the log is still there.

## No argument, IDE selection or opened file: concepts in that code

The user is saying "I understand this code". Don't move the whole language to `Known`. Instead:

1. Read the target: the selected lines, or the whole opened file if nothing is selected.
2. List the concepts the target uses, grouped by topic. Language constructs go under the language's topic. For an opened file, also note the file's role in the project (the component, what it does, and how it connects to other modules), and put that under the project topic.
3. Only concepts that belong to a `Learning` topic need logging. Skip concepts from `Known` topics.
4. For each remaining concept, log it the way Step 7 of the explain skill describes: an index line plus a detail file. Use depth tag `core`. In the detail file's `History`, add `<date>, from <path:lines>: marked known by the user`. If the concept is already logged, add only that `History` line, and raise the depth tag only if it was `surface`.

## No argument, no IDE context: the current project

Apply the steps from "With arguments: whole topics" to `basename "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"`.

## Report

Reply in one short message. Name the target you used (a topic, a selection, a file, or the project). List what you added or moved, and what was already known.
