"""Thin wrapper around the LLM provider. Swap providers by changing LLM_PROVIDER."""
import os
import time

PROVIDER = os.environ.get("LLM_PROVIDER", "gemini")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
# Tried in order if the main model is overloaded (503) or rate-limited (429).
GEMINI_FALLBACKS = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")


def chat(system_prompt: str, history: list[dict]) -> str:
    """history: [{"role": "user" | "assistant", "content": str}, ...] -> reply text."""
    if PROVIDER == "claude":
        return _claude(system_prompt, history)
    return _gemini(system_prompt, history)


def _gemini(system_prompt: str, history: list[dict]) -> str:
    from google import genai
    from google.genai import errors, types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    contents = [
        types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[types.Part(text=m["content"])],
        )
        for m in history
    ]
    config = types.GenerateContentConfig(system_instruction=system_prompt)

    last_error = None
    for model in [GEMINI_MODEL] + [m for m in GEMINI_FALLBACKS if m != GEMINI_MODEL]:
        for attempt in range(2):  # one quick retry per model
            try:
                response = client.models.generate_content(
                    model=model, contents=contents, config=config
                )
                return response.text or "Sorry, I couldn't generate a reply. Please try again."
            except (errors.ServerError, errors.ClientError) as e:
                if isinstance(e, errors.ClientError) and e.code not in (404, 429):
                    raise  # bad key / bad request: retrying won't help
                last_error = e
                if attempt == 0 and e.code != 404:
                    time.sleep(2)
                else:
                    break  # move on to the next model
    raise last_error


def _claude(system_prompt: str, history: list[dict]) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=system_prompt,
        messages=history,
    )
    return response.content[0].text
