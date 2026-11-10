# Warning Signs & Incident Response

Bans rare no warning. Catch early signal, halt before temp restrict → perm ban. Full ban usually gone forever. Priority: **stop early**.

## Early warning signs — halt moment you see these

- **Messages send but never "delivered"** (single check, no double) across multi recipients — maybe shadow-restricted.
- **Rising failure rate** from Evolution API sends, or send calls timing out.
- **Frequent disconnects / QR re-pair prompts** (`connectionUpdate` flapping to `close`). WhatsApp forcing you off.
- **Recipients reply "who is this?" / annoyed**, or blocks notice — block/report top ban driver.
- **Temp restriction notice** in WhatsApp app on phone.

See any mid-run: **stop sending immediately.** No retry-hammer — retries during soft restrict speed hard ban.

## If temp restricted (not full ban)

- **Go silent.** Stop automation hours-days. Let number cool off.
- **Resume reply-only, human-paced traffic**, ramp slow per `references/account-warmup.md` — treat like fresh warm-up.
- **Cut volume drastic**, long-term. Prior rate too aggressive for this number's trust level.
- Review trigger: cold outreach? dup content? too-fast bursts? new number no warm-up? Fix root cause, not symptom.

## If number fully banned

- WhatsApp bans generally **permanent** for that number, appeals rarely work. Don't count recovery.
- Can request review in-app ("Request a review"), but assume number lost.
- **Don't spin new number immediately, repeat same behavior** — same pattern/device/IP fingerprint → same fast ban. Fix *behavior* first (consent, warm-up, pacing, content), then start new number, warm proper.

## Prevention checklist (revisit after any incident)

- [ ] Number warmed up before automation (`references/account-warmup.md`)
- [ ] All recipients opted in / messaged first (`references/outreach-and-broadcast.md`)
- [ ] Message bodies spun, not identical (`references/message-content.md`)
- [ ] Delays randomized, human-paced, within working hours (`references/rate-limiting.md`)
- [ ] Numbers validated before send; invalid dropped
- [ ] Daily/hourly caps enforced, back-off on errors wired in
- [ ] Opt-out honored; blocked/reporting recipients removed permanent
- [ ] Connection health monitored via `CONNECTION_UPDATE`

## Protecting business, not just this number

WhatsApp important to user's operation → resilient answer: **official WhatsApp Business Platform (Cloud API)** w/ approved templates for proactive stuff, reserve unofficial Evolution API automation for low-risk reply-driven flows. Treat every unofficial number expendable, never route critical volume through single un-warmed number.