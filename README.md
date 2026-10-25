# Math Study Buddy

Pick a grade, topic and difficulty; the bot explains the concept, then quizzes you, checks answers, tracks score, and shows step-by-step solutions on request.

## Run locally (Windows)
1. Get a free Gemini key: https://aistudio.google.com/apikey
2. Put it in `.streamlit/secrets.toml` as `GEMINI_API_KEY = "..."`
3. `.venv\Scripts\streamlit run app.py` (opens http://localhost:8501)

## Files
- `app.py` UI + chat loop + score · `prompts.py` tutor behaviour · `llm.py` LLM wrapper · `topics.json` grades/topics

## Switch to Claude later
Set `LLM_PROVIDER = "claude"` and `ANTHROPIC_API_KEY` in secrets, and add `anthropic` to requirements.txt.

## Deploy (free)
Push to GitHub (secrets.toml is gitignored) → https://share.streamlit.io → New app → pick repo, `app.py` → Settings → Secrets → paste `GEMINI_API_KEY`.
