# AI Brief Generator — Collabstr Challenge

A minimal Django + jQuery app that generates a structured influencer-marketing campaign brief from four user inputs using Claude Haiku 4.5 (Anthropic).

## Quick Start

```bash
pip install django anthropic better-profanity django-ratelimit
export ANTHROPIC_API_KEY=sk-ant-...        # Windows: $env:ANTHROPIC_API_KEY="sk-ant-..."
python manage.py migrate
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

Get an API key at https://console.anthropic.com.

---

## Prompt Design Choices

The system prompt is kept to four sentences:

> *"You are a concise campaign strategist for influencer marketing. Produce professional, on-brand campaign briefs in plain English. Be specific, actionable, and avoid filler. Output must conform exactly to the tool schema provided — no extra keys."*

**Why so short?**  
Longer system prompts increase token cost and can dilute instruction-following. By front-loading the persona and style constraint and leaning on Anthropic's tool-use schema to enforce structure, we keep the prompt lean while still getting reliable, high-quality output.

**User prompt** is deliberately compact — four labeled key-value pairs plus a single imperative — so there is no ambiguity about what to generate and the model's attention is not diluted by narrative framing.

**Temperature is 0.4** (below the 0.5 cap) to keep outputs deterministic and on-message while allowing enough variation that repeated calls for the same inputs don't feel templated.

---

## Guardrails

| Layer | Mechanism |
|---|---|
| **Allowlist validation** | `platform`, `goal`, and `tone` are matched against fixed Python sets; any unlisted value is rejected with a 400 before the LLM is called. |
| **Profanity filter** | `brand` is checked with `better-profanity` before it reaches the prompt. |
| **Length cap** | `brand` is limited to 80 characters to prevent prompt-injection via very long inputs. |
| **Rate limiting** | `django-ratelimit` enforces 20 POST requests per hour per IP address; the 429 is surfaced to the user in plain language. |
| **Token cap** | `max_tokens=600` on every API call; prevents runaway cost on a single request. |
| **Structured output** | Anthropic tool use with `strict=True` and `additionalProperties: False` means the response is always machine-parseable — no freeform JSON parsing needed. |

---

## Token & Latency Measurement

Every response includes a `telemetry` object:

```json
{
  "telemetry": {
    "latency_ms": 812,
    "prompt_tokens": 174,
    "completion_tokens": 238,
    "total_tokens": 412,
    "model": "claude-haiku-4-5-20251001"
  }
}
```

- **Latency**: measured with `time.perf_counter()` around the `client.messages.create()` call — wall-clock time including network round-trip.
- **Tokens**: read directly from `response.usage` in the Anthropic SDK response object (`input_tokens` + `output_tokens`). No estimation needed; the API returns exact counts.
- These are rendered in a small telemetry bar below every generated brief so reviewers can see cost and speed at a glance.

---

## Loom Demo

https://www.loom.com/share/9cc75a5182604a26b15b649e824d3d58

---

## Project Structure

```
.
├── collabstr_brief/       # Django project config
│   ├── settings.py
│   └── urls.py
├── brief/                 # Feature app
│   ├── views.py           # Input validation, rate limiting, response
│   ├── urls.py
│   └── services/
│       └── llm.py         # Anthropic Claude call, schema, telemetry
└── templates/
    └── index.html         # Single-page UI (HTML/CSS/jQuery)
```
