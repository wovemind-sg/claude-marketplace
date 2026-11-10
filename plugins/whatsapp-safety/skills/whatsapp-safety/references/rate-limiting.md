# Rate Limiting & Human Pacing

WhatsApp fingerprint *timing*. Human slow, irregular, bursty natural way; bot fast, regular, relentless. Goal not "go slow" — look organic human. Fixed `sleep(3)` between every message near-as suspicious as no delay — real human never send even intervals.

## Delay between messages

Use **randomized** delays, not constants. Reasonable ranges (tune down new numbers, per `references/account-warmup.md`):

- Between two proactive messages, different recipients: **random 20–90 sec**, occasional longer gap.
- Add **typing delay proportional to message length** before send — roughly time person take to type. 200-char message not appear instantly.
- Sprinkle **occasional long pause** (few min) like human got distracted. Perfectly steady cadence, even if slow, bot tell.

```python
import random, time

def human_delay(base_min=20, base_max=90):
    delay = random.uniform(base_min, base_max)
    # ~10% of the time, take a longer "distraction" break
    if random.random() < 0.1:
        delay += random.uniform(120, 300)
    time.sleep(delay)

def typing_delay(text):
    # ~1 char per 60–120 ms, floor a couple seconds, cap so it stays believable
    seconds = min(max(len(text) * random.uniform(0.06, 0.12), 2), 12)
    time.sleep(seconds)
```

## Typing presence

Set "typing…" presence before send — recipient (and WhatsApp) see human composing. See `references/evolution-api.md` for `/chat/sendPresence` call. Sequence: set `composing` → wait `typing_delay(text)` → send.

## Volume caps

Even warmed-up, established number respect ceiling. Rough safe ceiling for mature number (more conservative if unsure):

- **Proactive messages:** ~80–150/day, spread across day — not one block.
- **Per hour:** keep well under ~30–40 proactive sends; burst riskier than daily total.
- **New contacts (never messaged before):** small fraction of daily total — cold volume dangerous kind.

Reply traffic (answer people who messaged you) much safer, no tight cap need, but still not instant-fire.

## Working hours

Only send during plausible waking hours in **recipient's** timezone (roughly 08:00–21:00). Message at 3am both ineffective and bot signal. Queue anything outside window for next morning.

## Spread, don't batch

Send 100 messages tight 10-min loop far more dangerous than 100 spread naturally across day, even same total. Design sender as **paced queue** drip message out, not for-loop drain list fast as delay allow. Add jitter to *when* queue wake up too.

## Back off on errors

If sends start fail, or delivery not progress (sent but never delivered), or Evolution API return error — **stop run**. Climbing failure rate often precede ban. See `references/incident-response.md`. Don't retry-hammer — accelerate ban.