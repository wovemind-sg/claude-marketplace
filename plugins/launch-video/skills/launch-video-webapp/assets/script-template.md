# Launch video — APP NAME

Voice: Rachel
Format: vertical
Language: en
Base URL: http://localhost:8000
Background: #0B1220, #182447, #6E8CFF

<!--
  How this file works (you can delete these comments):
  - Each "## N. Title (avatar)" section is spoken by the on-camera presenter.
  - Each "## N. Title (demo)" section is voice-over while the app is shown on a phone.
  - Write exactly what should be said. Short sentences sound best.
  - A demo section's text is a first draft, not final: it describes what happens on
    screen and doubles as the spec for its flow file. Once that beat is recorded, the
    text gets resized to almost fill the recording's actual length (~2.3-2.5 words/sec)
    — so don't tune word count here, just describe the action.
  - Background: dark, darker, glow-accent hex colors for the space behind the phone —
    pull these from the app's own palette (CSS variables, Tailwind config, brand colors,
    logo, primary button color), not a generic default. Leave the line out to fall back
    to a neutral dark-indigo look.
  - Optional lines for demo sections:
      Zoom: top | center | bottom | none       (which part of the screen to enlarge —
                                                 every preset crops ~17% off each edge, so
                                                 it clips full-width headers/bars; use
                                                 "none" on edge-to-edge screens)
      Hold: 1.5                                (seconds to keep the screen after the voice ends)
  - Aim for 60–90 seconds total: about 150–220 words.
-->

## 1. Intro (avatar)
Hi, I'm Alex. If you've ever spent an evening chasing customers for payments over WhatsApp, this is for you.

## 2. Create an invoice (demo)
Zoom: none
Hold: 1.5
Open the app, tap New Invoice, pick the customer, and enter the amount. That's it — the invoice is ready.

## 3. Send and get paid (demo)
Zoom: bottom
Tap Send. Your customer gets a WhatsApp message with a PayNow link, and you get notified the moment they pay.

## 4. Outro (avatar)
No more chasing, no more spreadsheets. Try APP NAME free today — the link is below.
