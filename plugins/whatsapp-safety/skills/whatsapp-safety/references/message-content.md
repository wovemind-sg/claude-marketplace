# Message Content

WhatsApp cluster ident + near-ident msgs across recipients, detect bulk campaigns. Same body many numbers — even delayed — classic spam fingerprint. Content also drive *recipient* behavior: spammy msg get blocked/reported, block/report rate = WhatsApp's strongest ban signal. So content safety = two things: don't look templated, don't provoke blocks.

## Vary every message ("spinning")

Never send byte-identical bodies at volume. Add natural variation per recipient:

- **Personalize** with recipient name + genuine context you have.
- **Vary greeting/phrasing** — rotate openings, synonyms, sentence order.
- **Vary length/structure** — not every msg same shape.

```python
import random

GREETINGS = ["Hi {name},", "Hey {name}!", "Hello {name},", "{name}, hope you're well —"]
CLOSERS   = ["Thanks!", "Cheers,", "Appreciate it 🙏", "Talk soon,"]

def spin(name, core):
    g = random.choice(GREETINGS).format(name=name)
    c = random.choice(CLOSERS)
    return f"{g}\n\n{core}\n\n{c}"
```

Spinning cut fingerprint but **not** make cold spam safe — if underlying msg unsolicited, variation only slow detection. Consent still matter most (`references/outreach-and-broadcast.md`).

## Avoid spammy content patterns

Things raise flags/trigger blocks:

- **Links, esp shortened URLs** (bit.ly etc) in first-contact msgs. Link-heavy outbound to strangers heavily penalized. Must include link → prefer full reputable domain, only to people who expect it.
- **Attachments to strangers** — unexpected media/docs get reported fast.
- **Money/urgency/promo language** — "free", "winner", "act now", "limited offer", excess emoji/ALL CAPS.
- **Long walls of text** to someone who never asked.

## Make it easy to opt out

For proactive/marketing-adjacent msg: include simple honest opt-out ("reply STOP to stop"). Honor immediately + permanently — record number, never message again. Lowers block/report rate directly, that protect number.

## Rich content

- **Send media sparingly**, only when contextually expected. Set presence (`recording`/`composing`) first.
- **Don't lead with media** on first contact.
- Use link previews/formatting naturally, like person would — not stuffed tracking links.

## First-contact messages specifically

Messaging someone first time → msg should read like real person reach out: short, specific, reference how you got number or prior relationship, no links, no attachments, clear who you are. Anything read like template blast get blocked.