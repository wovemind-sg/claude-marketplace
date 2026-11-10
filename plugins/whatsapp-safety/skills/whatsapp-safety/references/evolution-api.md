# Evolution API — Safe Patterns

Concrete Evolution API calls implement safety rules mechanically. Endpoint paths follow Evolution API v2; verify against your version's docs (`/docs` on your instance). All requests take `apikey` header, target named `{instance}`. Base URL + API key belong env vars — never hardcode or commit.

> Endpoint shapes vary between Evolution API versions/forks. Treat as templates, confirm exact path/body on your instance before running at volume.

## Connection & instance health

Unhealthy session (frequent disconnects, re-pairing, `connectionUpdate` flapping) breaks delivery, looks suspicious. Check state before sending.

```bash
# Connection state — expect "open"
curl -s "$BASE/instance/connectionState/$INSTANCE" -H "apikey: $APIKEY"
```

- Don't send while state `connecting`/`close`. Wait for `open`.
- Avoid running same number on phone + multiple Evolution sessions at once — multi-device conflicts cause drops, scrutiny.
- Re-scan QR frequent → WhatsApp notices. Keep session stable.

## 1. Validate number exists on WhatsApp

Send only real WhatsApp numbers. Drop rest.

```bash
curl -s -X POST "$BASE/chat/whatsappNumbers/$INSTANCE" \
  -H "apikey: $APIKEY" -H "Content-Type: application/json" \
  -d '{"numbers":["5511999999999"]}'
# → array with exists:true/false and the JID to send to
```

## 2. Typing presence before sending

Make WhatsApp + recipient see human composing.

```bash
curl -s -X POST "$BASE/chat/sendPresence/$INSTANCE" \
  -H "apikey: $APIKEY" -H "Content-Type: application/json" \
  -d '{"number":"5511999999999","presence":"composing","delay":4000}'
```

Sequence per message: set `composing` → wait length-proportional typing delay → send. See `references/rate-limiting.md`.

## 3. Send text (with built-in delay)

`sendText` supports `delay` (ms) — Evolution applies before delivering. Use it, *also* pace at app level between recipients.

```bash
curl -s -X POST "$BASE/message/sendText/$INSTANCE" \
  -H "apikey: $APIKEY" -H "Content-Type: application/json" \
  -d '{"number":"5511999999999","text":"Hi Ana, ...","delay":3500}'
```

## 4. A safe sender in Python

Encodes operating loop from SKILL.md — validate, presence, human delay, spun content, caps, back-off.

```python
import os, random, time, requests

BASE, INSTANCE, APIKEY = os.environ["EVO_BASE"], os.environ["EVO_INSTANCE"], os.environ["EVO_APIKEY"]
H = {"apikey": APIKEY, "Content-Type": "application/json"}

def exists_on_whatsapp(number):
    r = requests.post(f"{BASE}/chat/whatsappNumbers/{INSTANCE}", headers=H, json={"numbers": [number]})
    data = r.json()
    return bool(data) and data[0].get("exists")

def set_typing(number, seconds):
    requests.post(f"{BASE}/chat/sendPresence/{INSTANCE}", headers=H,
                  json={"number": number, "presence": "composing", "delay": int(seconds * 1000)})

def send_text(number, text):
    return requests.post(f"{BASE}/message/sendText/{INSTANCE}", headers=H,
                         json={"number": number, "text": text, "delay": random.randint(2500, 5000)})

def send_batch(recipients, build_message, daily_cap=100):
    sent, failures = 0, 0
    for name, number in recipients:
        if sent >= daily_cap:
            break
        if failures >= 3:                      # back off — climbing failures precede bans
            print("Too many failures, halting."); break
        if not exists_on_whatsapp(number):
            continue                            # skip non-WhatsApp numbers, don't count as send
        text = build_message(name)              # spun/personalized per recipient
        typing = min(max(len(text) * random.uniform(0.06, 0.12), 2), 12)
        set_typing(number, typing); time.sleep(typing)
        r = send_text(number, text)
        if r.status_code >= 300:
            failures += 1; continue
        sent += 1
        delay = random.uniform(20, 90)          # human, randomized inter-message gap
        if random.random() < 0.1:               # occasional long pause
            delay += random.uniform(120, 300)
        time.sleep(delay)
    return sent, failures
```

## 5. Groups

```bash
# Create a group
curl -s -X POST "$BASE/group/create/$INSTANCE" -H "apikey: $APIKEY" -H "Content-Type: application/json" \
  -d '{"subject":"Team updates","participants":["5511999999999"]}'

# Get invite link — prefer sharing this over direct-adding strangers (see references/groups.md)
curl -s "$BASE/group/inviteCode/$INSTANCE?groupJid=<jid>" -H "apikey: $APIKEY"

# Update participants (add/remove) — pace these like sends, cap per day
curl -s -X POST "$BASE/group/updateParticipant/$INSTANCE" -H "apikey: $APIKEY" -H "Content-Type: application/json" \
  -d '{"groupJid":"<jid>","action":"add","participants":["5511999999999"]}'
```

## 6. Webhooks — prefer reply-driven flows

Reply traffic = lowest-risk WhatsApp activity. Configure webhook so inbound messages drive automation — turns proactive risk into safe responses.

```bash
curl -s -X POST "$BASE/webhook/set/$INSTANCE" -H "apikey: $APIKEY" -H "Content-Type: application/json" \
  -d '{"webhook":{"url":"https://your.app/wa","events":["MESSAGES_UPSERT","CONNECTION_UPDATE","SEND_MESSAGE"]}}'
```

- Subscribe `CONNECTION_UPDATE` to detect drops/bans early (`references/incident-response.md`).
- Use `MESSAGES_UPSERT` to reply within conversations — low risk, no caps needed beyond not-instant.
- Ignore/skip messages from `status@broadcast` + own JID, avoid loops.
- **Testing tip:** webhook receiver behind proxy redirecting http→https → `curl` POSTs fail silently (empty body, exit 0) unless `-L` added. Test exact webhook URL before trusting it.

## Housekeeping

- Keep base URL + API key env vars; never commit.
- Log every send (number, time, status) — audit volume + failure rate.
- Mark inbound messages read (`/chat/markMessageAsRead`) — normal human behavior, small trust signal.