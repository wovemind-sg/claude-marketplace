# Groups & Participants

Group actions high-risk — affect people who didn't choose interact with you. Adding stranger to group = proactive intrusion — they report group and you, mass group-adds classic spam pattern. New number that creates groups + bulk-adds participants = obvious bot.

## Creating groups

- **Create slowly.** Don't spin up many groups short window. Handful per day max for established number; near-zero for new one.
- **Warm up number on messaging first** (`references/account-warmup.md`) before it creates groups.
- Give groups real name, description, icon — blank throwaway groups look automated.

## Adding participants — the danger zone

- **Prefer invite links over direct adds.** Direct add = pulled in without consent; join via link = they chose it. Links convert intrusion into opt-in. Generate group invite link, share it, instead of programmatically adding numbers.
- **Only direct-add people who expect it** — they asked to join, or clearly consented.
- **Pace adds heavily.** Adding many participants rapidly = strong ban signal. Space out with randomized delays like message sends (`references/rate-limiting.md`), cap per-day.
- **Never bulk-add scraped or purchased number lists.** Classic get-banned-in-minutes move.
- Some numbers **can't be added** (privacy settings block it) — normal, don't retry-hammer, skip them. Repeated failed adds look bad.

## Sending in groups

- Don't blast identical messages across many groups — same duplicate-content fingerprint as DMs (`references/message-content.md`).
- Respect group members: relevant, wanted content only. Members leaving/reporting hurts number.
- Use mentions naturally; don't @-everyone repeatedly.

## Managing membership

- Rapid remove/add cycles look manipulative — avoid churn.
- Announcement-style groups → set admin-only posting so number not associated with member spam.
- For genuine broadcast needs, consider **WhatsApp Channels** (one-to-many, follower opt-in) instead of stuffing people into groups.

## Evolution API group endpoints

See `references/evolution-api.md` for concrete `/group/*` calls (create, fetch invite code, update participants). Apply same pacing, presence, validation discipline to group ops as to sends.