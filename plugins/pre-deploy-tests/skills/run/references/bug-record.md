# Bug record

The format every test agent writes a finding in, and the run skill writes a numbered bug in. The fix skill and the bug review page read these files, so keep the field names and headings exactly as below.

## Where the files go

- **Test agent (a finding):** one folder per finding, `.pre-deploy-tests/bugs/inbox/<session>-<copy>/<slug>/` (for example `bugs/inbox/03-webkit/checkout-button-hidden/`), holding `finding.md`, the captures and any reproduction script. Agents never pick a bug number: two agents running side by side would pick the same one.
- **Run skill (a bug):** after each session it merges the findings into `.pre-deploy-tests/bugs/BUG-NNN/`:

  ```
  bugs/BUG-NNN/
    bug.md          the record below, with the id filled in
    captures/       <copy>-<size>-<orientation>[-<n>].png | .webm | .mov | .mp4
    repro.<ext>     the reproduction script, if one was used (repro-<copy>.<ext> when the copies needed different scripts)
  ```

## The record

`finding.md` and `bug.md` use the same layout. A finding writes `id: pending`; the run skill replaces it with `BUG-NNN`.

```markdown
# <title: the symptom in plain words, under 80 characters>

- id: BUG-NNN
- severity: Blocker | Major | Minor | Cosmetic
- area: <the test area, e.g. Forms, Layout, Permissions, Native shell>
- where: <one line per place it occurs: copy, size, orientation, screen or route>
  - webkit, phone 390x844, landscape, /checkout
  - chromium, phone 390x844, landscape, /checkout
- found by: <session NN, test item T-NNN, model>
- reproduced: <n>/3 (<copy>), one entry per copy

## Meaning
What the bug means for a user, in one or two sentences: who hits it, when, and what they lose.

## Expected
What should happen.

## Actual
What happens instead. Quote error messages exactly.

## Steps
1. Numbered steps from a fresh start (the URL or app launch, the test account by its environment variable name, every click and typed value), so a person or an agent repeats it with no other context.

## Captures
- captures/webkit-phone-landscape.png: what it shows
- captures/chromium-phone-landscape.webm: what it shows

## Reproduction script
`repro.js`: how to run it (`playwright-cli -s=repro run-code --filename=repro.js` with the URL to set), or "none".

## Suspected cause
`file:line` and why, from reading the code, or "unknown". Read only: never edit to test a theory.

## Fix prompt
The prompt below, filled in.
```

## Rules for each field

- **Reproduce three times** from a fresh page or a relaunched app before recording. Write the count: `3/3` is a bug; `1/3` or `2/3` is still recorded, with "intermittent" in Actual. `0/3` after one sighting: record it only if a capture shows it, and say so.
- **Captures.** A UI bug always has one. Static (wrong layout, clipped or overlapping text, wrong color, missing element): a screenshot (`.png`). Movement (an animation, a transition, a flicker, a scroll or a gesture that goes wrong, anything that happens over time): a recording under 10 seconds (web `.webm`; iOS `.mov`, converted to `.webm` with ffmpeg when it is installed; Android `.mp4`). A logic bug with no visible symptom needs no capture; one of the error message helps.
- **Reproduction script.** Any script you wrote or ran to reach or show the bug (a `playwright-cli run-code` file, a curl command, an `adb` or `simctl` sequence) is saved next to the finding, not deleted, and named in the record. It goes into the repo only as a file in `.pre-deploy-tests/`, never into the app's own tests.
- **No secrets.** Name test credentials by their environment variable. Never write a password, token or personal data into a record, a capture name or a script.

## Severity

Pick the highest that fits. When unsure between two, pick the higher and say why in Meaning.

| Severity | Means | Examples |
|---|---|---|
| Blocker | A core flow cannot be finished, data is lost or exposed, a security check fails, or the app crashes or will not start. No workaround. | Sign-up never completes; another user's data shows; the app crashes on launch on iOS. |
| Major | A feature gives the wrong result or cannot be used on a supported platform, size, orientation or browser, and a workaround exists. | The save button is off-screen in landscape on phones; a total is wrong; a form loses input on back. |
| Minor | It works, but wrongly in a way users notice, and the fix for the user is easy. | A wrong error message; the keyboard covers a field until scrolled; focus jumps. |
| Cosmetic | Looks wrong only; nothing stops working. | Misaligned icon; inconsistent spacing; a truncated label with a tooltip. |

The run skill's verdict is "Not ready" when any Blocker or Major is open.

## How to write the fix prompt

The fix prompt is what an implementing agent reads when it fixes this bug, with no access to this test run. Make it self-contained:

```
Fix BUG-NNN: <title>.

Symptom: <Actual, in one or two sentences, with where it occurs (copies, sizes, orientations, screen)>.
Steps to reproduce:
1. ...
Expected: <Expected>.
Suspected cause: <file:line and why, or "unknown: start from <screen or handler>">.
Reproduction script: .pre-deploy-tests/bugs/BUG-NNN/repro.<ext> (how to run it), or none.
Verify: re-run the steps (or the script) on every place listed above and confirm <Expected>; for a UI bug, take an "after" capture at the same size, orientation and copy as the "before" capture.
Change only what this bug needs.
```
