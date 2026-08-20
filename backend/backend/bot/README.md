# Bot

The actual end-user-facing product: a Telegram bot. This folder is what makes
MamaCare AI "usable at the end of 8 weeks" rather than a set of scripts that
only run on a developer's laptop.

Receives a message from a Telegram user → calls `backend`'s `POST /chat` →
sends the answer back, with the disclaimer `modules/safety` attached.
Deliberately thin: all real logic (retrieval, generation, safety) lives in
`backend`, reached over HTTP — the bot is just a transport. That's what makes
adding a second channel (WhatsApp, web) later a new thin adapter here, not a
rewrite of the AI pipeline.

Why Telegram and not WhatsApp for the 8-week build: WhatsApp's Business API
requires Meta business verification, which is a real, uncontrolled approval
delay — a bad risk to take against a fixed 8-week window. Telegram's bot API
is free, has no approval gate, and is a legitimate real-world chat channel.
WhatsApp is the documented next step after handover (see
`docs/ARCHITECTURE.md`).

**Input:** Telegram messages
**Output:** calls to `backend` API, replies to the user
**Owner track:** API/Bot track
**Sprint:** 1 ("hello world" round trip: bot → API → canned response — this
proves the whole system is wired together before any real AI logic exists),
2–4 (wire to real `/chat`, polish UX)
