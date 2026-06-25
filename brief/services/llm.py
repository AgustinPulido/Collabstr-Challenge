import time
import os

import anthropic

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    return _client


SYSTEM_PROMPT = (
    "You are a concise campaign strategist for influencer marketing. "
    "Produce professional, on-brand campaign briefs in plain English. "
    "Be specific, actionable, and avoid filler. "
    "Output must conform exactly to the tool schema provided — no extra keys."
)

BRIEF_TOOL = {
    "name": "campaign_brief",
    "description": "A campaign brief with content angles and creator criteria.",
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "brief": {
                "type": "string",
                "description": "4–6 sentence campaign brief tailored to the inputs.",
            },
            "angles": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Exactly 3 content angle suggestions.",
            },
            "criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Exactly 3 creator selection criteria bullets.",
            },
        },
        "required": ["brief", "angles", "criteria"],
        "additionalProperties": False,
    },
}


def generate_brief(brand: str, platform: str, goal: str, tone: str) -> dict:
    """
    Call Claude and return structured brief data plus telemetry.
    Raises on API error so the view can return a 502.
    """
    user_prompt = (
        f"Brand: {brand}\n"
        f"Platform: {platform}\n"
        f"Goal: {goal}\n"
        f"Tone: {tone}\n\n"
        "Generate the campaign brief now."
    )

    t0 = time.perf_counter()

    response = _get_client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=600,
        temperature=0.5,
        system=SYSTEM_PROMPT,
        tools=[BRIEF_TOOL],
        tool_choice={"type": "tool", "name": "campaign_brief"},
        messages=[{"role": "user", "content": user_prompt}],
    )

    latency_ms = round((time.perf_counter() - t0) * 1000)

    payload = None
    for block in response.content:
        if block.type == "tool_use":
            payload = block.input
            break

    if payload is None:
        raise ValueError("No tool_use block in response")

    usage = response.usage
    return {
        "brief": payload["brief"],
        "angles": payload["angles"],
        "criteria": payload["criteria"],
        "telemetry": {
            "latency_ms": latency_ms,
            "prompt_tokens": usage.input_tokens,
            "completion_tokens": usage.output_tokens,
            "total_tokens": usage.input_tokens + usage.output_tokens,
            "model": response.model,
        },
    }
