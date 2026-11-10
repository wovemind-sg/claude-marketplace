# Engineer handoff section

The format of the section that `review-ui-change` writes into the PR body and that `engineer-review-ui-change` reads back. Both skills depend on it, so keep the markers and the D-numbering exactly as shown.

The reader is an engineer who was not part of the design session and has no context. Write in plain English, name pages and elements the way a user would, and make every item stand on its own.

```
<!-- ui-change-guard:engineer-handoff -->
## UI change review: engineer handoff (<VERDICT>, <YYYY-MM-DD>, <short sha>)

**What the designer was going for:** <2-4 sentences on the intent of the change, taken from the conversation and the commit messages. If neither says, write "Not stated" instead of guessing.>

### Decisions needed

#### D1. <title> (Blocker | Warning | Needs engineer)
- Where: `<file>:<line>` (<page or element in user terms>)
- What changed and why it may break: <evidence: grep hit, consumer file:line, measurement>
- Question for you: <one yes/no or pick-one decision the engineer must make>
- Suggested fix: <smallest safe action>

#### D2. ...

### Checked and fine
- <short list of removals or risks that were traced and found harmless>
<!-- /ui-change-guard:engineer-handoff -->
```

Rules:

- One D-item per Blocker, Warning, and Needs-engineer finding in the report. Skip Notes. IDs are D1, D2, ... in report order and stay stable within one section, so the engineer skill and its final PR comment can refer back to them.
- The start and end markers must be on their own lines. They let a later run replace or remove the section without touching the rest of the PR body.
- Each "Question for you" must be answerable by one decision. Split a finding that needs two decisions into two items.
