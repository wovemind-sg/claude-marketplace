# Web forms

Used by SKILL.md step 4. Each form is driven with `playwright-cli` (see the `playwright-cli` skill and `plugins/ui-audit/skills/capture/references/web.md`). Run it from a scratch directory so `.playwright-cli/` stays out of the repository.

```bash
playwright-cli -s=<directory id> open --headed --persistent "<url>"
playwright-cli -s=<directory id> snapshot      # read refs, then fill/click by ref
```

Login lives only in the browser profile. Never export cookies or storage state to a file, and never type a password: if the page asks for sign-in, the owner does it in the open window.

Rules for every form: fill, snapshot, stop at the final control named below, ask the owner, and click only after the answer "submit". Values marked "confirm on first live run" have not been seen in the live form yet; check the snapshot and correct this file afterwards.

## Anthropic directory (`anthropic`)

- URL: https://claude.ai/directory/manage
- Sign-in: the owner's claude.ai account; paid plan and GitHub push access to the repository are required.
- Path: Submit new, then Plugin bundle. One plugin per submission, at most 10 per 24 hours for the organization.
- Fields (all confirm on first live run): repository URL, plugin path or name (the plugin's folder under `plugins/`), name and description (the plugin's `description` in `marketplace.json`), license, category.
- Stop at: the final "Submit" button of the Plugin bundle form.
- Success signal: confirm on first live run; expect a confirmation message or the plugin appearing on the Submissions page.

## claudemarketplaces.com (`claudemarketplaces`)

- URL: https://claudemarketplaces.com/submit
- Sign-in: GitHub, done by the owner.
- Fields (confirm on first live run): repository URL (the repo's GitHub URL). Choose the free review option only. Never touch card, coupon or payment fields; if the page cannot proceed without payment, stop and report it.
- Stop at: the final submit button of the free option.
- Success signal: confirm on first live run; expect a confirmation message. The listing may appear at `/plugins/<owner>-<repo>` later (unverified).

## claudepluginhub.com (`claudepluginhub`)

- URL: https://claudepluginhub.com/tools/submit-plugin
- Sign-in: the owner signs in on the site (confirm on first live run which provider).
- Fields (confirm on first live run): one GitHub repository URL. The repository needs a valid `.claude-plugin/marketplace.json`.
- Stop at: the form's final submit button.
- Success signal: confirm on first live run; expect a confirmation message or a listing at `/plugins/<owner>-<repo>`.
