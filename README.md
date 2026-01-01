# AI Meter

See where your AI tokens actually go.

Meter is a tiny OpenAI-compatible proxy that shows which features, prompts, and environments are burning your AI budget.

No dashboards.
No lock-in.
No rewrites.

Just answers.

---

Why

LLM providers show total spend.
They don’t show why.

Meter shows:
- Which feature is expensive
- Which prompt exploded
- Whether dev or prod is leaking money

---

How it works

Your app → Meter → OpenAI

Meter forwards the request, logs usage, and returns the response as-is.

---

Getting started

Point your OpenAI client at Meter:

client = OpenAI(base_url="https://api.meter.dev",

api_key="your-meter-key"

)

---

Add attribution headers:

x-team: support

x-feature: ticket_summary

x-environment: prod

That’s it.

---

Usage

GET /usage

GET /usage?group_by=feature

GET /usage?group_by=team

GET /usage?group_by=environment


---

Status

Early / private alpha.

---

Meter turns AI usage from “magic” into line items.

