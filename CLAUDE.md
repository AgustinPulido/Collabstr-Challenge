# AI Brief Generator — Claude Code Context

## What this project is

A minimal Django 5.2 + jQuery single-page app that generates structured influencer-marketing campaign briefs. The user fills in four fields (brand, platform, goal, tone); the backend calls Claude and returns a JSON payload (brief text, 3 content angles, 3 creator criteria) plus telemetry (tokens, latency, model).

Built as a Collabstr developer challenge. The final deliverable is a GitHub repo + live URL + Loom demo emailed to clayton@collabstr.com.

## Stack

| Layer | Tech |
|---|---|
| Web framework | Django 5.2 |
| LLM | Anthropic Claude (`claude-haiku-4-5`), tool use for structured output |
| Frontend | Vanilla HTML/CSS + jQuery AJAX (no framework) |
| Rate limiting | `django-ratelimit` (20 req/hour per IP) |
| Profanity filter | `better-profanity` (guards `brand` field) |
| Container | Docker + Gunicorn (`docker-compose.yml`) |
| DB | SQLite (no models — stateless app) |

## Project layout

```
.
├── collabstr_brief/        # Django project config
│   ├── settings.py         # ANTHROPIC_API_KEY, STATICFILES_DIRS, SILENCED_SYSTEM_CHECKS
│   └── urls.py
├── brief/                  # Feature app
│   ├── views.py            # Input validation, profanity check, rate limit, 502 on LLM error
│   ├── urls.py             # "" → index, "api/generate/" → views.generate
│   └── services/
│       └── llm.py          # Claude call, BRIEF_TOOL schema, telemetry dict
├── static/
│   └── css/
│       └── main.css        # All styles (extracted from inline)
├── templates/
│   └── index.html          # SPA — loads static CSS, jQuery AJAX
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Key files to know

### `brief/services/llm.py`
Single public function: `generate_brief(brand, platform, goal, tone) -> dict`.
- Uses `anthropic.Anthropic()` client (lazy-initialised, reads `ANTHROPIC_API_KEY` env var).
- Calls `client.messages.create()` with `tools=[BRIEF_TOOL]` and `tool_choice={"type":"tool","name":"campaign_brief"}` to force structured output.
- Model: `claude-haiku-4-5`, `temperature=0.4`, `max_tokens=600`.
- Parses result: iterates `response.content`, finds block with `block.type == "tool_use"`, reads `block.input` (already a dict — no `json.loads` needed).
- Returns: `{brief, angles, criteria, telemetry: {latency_ms, prompt_tokens, completion_tokens, total_tokens, model}}`.

### `brief/views.py`
- Validates `platform`/`goal`/`tone` against fixed allow-lists before calling the LLM.
- Caps `brand` at 80 chars; runs `better-profanity` check.
- Returns 502 with `{"error": "LLM error: ..."}` on any exception from `generate_brief`.

### `collabstr_brief/settings.py`
Notable non-default settings:
```python
ALLOWED_HOSTS = ["*"]
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
STATICFILES_DIRS = [BASE_DIR / 'static']
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]
```

## Running locally

```bash
pip install -r requirements.txt
cp .env.example .env          # fill in ANTHROPIC_API_KEY
python manage.py migrate
python manage.py runserver
```

## Running with Docker

```bash
cp .env.example .env          # fill in ANTHROPIC_API_KEY
docker compose up --build
```

App is at `http://localhost:8000`.

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | From https://console.anthropic.com |
| `DJANGO_SECRET_KEY` | Prod only | Long random string; defaults to insecure placeholder |

## LLM design notes

- **Why tool use for structured output?** Guarantees machine-parseable JSON every call; no fragile regex or retry logic needed.
- **Why Haiku 4.5?** Fast and cheap — appropriate for a demo with simple generation tasks. The original implementation used GPT-4o mini for the same reason.
- **Temperature 0.4** — below the 0.5 cap; keeps output consistent without feeling templated.
- **No `temperature` on Opus 4.7/4.8** — these models reject the parameter with a 400. Only applies if upgrading the model.

## Guardrails

| Layer | Where |
|---|---|
| Allow-list validation | `brief/views.py` — platform, goal, tone |
| Profanity filter | `brief/views.py` — brand name only |
| Brand length cap | `brief/views.py` — 80 chars |
| Rate limit | `@ratelimit(key="ip", rate="20/h")` in views.py |
| Token cap | `max_tokens=600` in llm.py |
| Structured output | `strict=True` + `additionalProperties: False` in BRIEF_TOOL |

## What's NOT here (intentional)

- No auth / user accounts — stateless demo
- No database models — nothing is persisted
- No async / Celery — synchronous call is fine for a demo
- No test suite — out of scope for the challenge
