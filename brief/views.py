import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from better_profanity import profanity

from .services.llm import generate_brief

profanity.load_censor_words()

ALLOWED_PLATFORMS = {"Instagram", "TikTok", "YouTube", "Twitter", "LinkedIn", "Pinterest"}
ALLOWED_GOALS = {"Awareness", "Engagement", "Conversions", "Followers", "Traffic"}
ALLOWED_TONES = {"Professional", "Casual", "Playful", "Inspirational", "Bold"}


def _err(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": msg}, status=status)


@csrf_exempt
@require_POST
@ratelimit(key="ip", rate="20/h", method="POST", block=True)
def generate(request):
    try:
        body = json.loads(request.body)
    except (ValueError, TypeError):
        return _err("Invalid JSON body.")

    brand = (body.get("brand") or "").strip()
    platform = (body.get("platform") or "").strip()
    goal = (body.get("goal") or "").strip()
    tone = (body.get("tone") or "").strip()

    if not brand:
        return _err("brand is required.")
    if len(brand) > 80:
        return _err("brand must be 80 characters or fewer.")
    if profanity.contains_profanity(brand):
        return _err("brand contains inappropriate language.")

    if platform not in ALLOWED_PLATFORMS:
        return _err(f"platform must be one of: {', '.join(sorted(ALLOWED_PLATFORMS))}.")
    if goal not in ALLOWED_GOALS:
        return _err(f"goal must be one of: {', '.join(sorted(ALLOWED_GOALS))}.")
    if tone not in ALLOWED_TONES:
        return _err(f"tone must be one of: {', '.join(sorted(ALLOWED_TONES))}.")

    try:
        result = generate_brief(brand=brand, platform=platform, goal=goal, tone=tone)
    except Exception as exc:
        return _err(f"LLM error: {exc}", status=502)

    return JsonResponse(result)
