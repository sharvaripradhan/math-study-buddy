# Math Study Buddy: Code Explained

## The big idea

Streamlit **re-runs `app.py` from top to bottom every time you click or type**. Anything that must survive between runs is kept in `st.session_state`, which is the app's memory.

```
You click/type  ->  app.py runs top to bottom  ->  ask() sends the whole chat to Gemini
      ^                                                      |
      +-- screen redraws with the new message  <-  reply saved in session_state
```

## The files

| File | Job |
|---|---|
| `topics.json` | Data only: which topics exist for each grade |
| `prompts.py` | The tutor's personality and rules, plus the canned button messages |
| `llm.py` | Talks to the AI provider (Gemini, or Claude if you switch) |
| `app.py` | Everything you see on screen, plus the control flow |
| `requirements.txt` | Packages needed (used when deploying) |
| `.streamlit/secrets.toml` | Your API key (gitignored, never upload it) |

## `prompts.py`

- **`START_MESSAGE`, `HINT_MESSAGE`, `SOLUTION_MESSAGE`, `NEXT_MESSAGE`**: hidden "commands" sent to the AI when you press Start or a button. For example, the Hint button sends *"I'm stuck. Please give me a small hint..."* as if you had typed it.
- **`build_system_prompt(grade, topic, difficulty)`**: returns the instruction sheet the AI reads before every reply. The rules are:
  - Explain the concept first, then ask one question at a time.
  - Start verdicts with `[CORRECT]` or `[INCORRECT]`, and solutions with `[SOLUTION]`.
  - Never reveal the answer unless asked.
  - Write math in LaTeX.

  The tags exist so `app.py` can read the verdict and keep score. Most of the tutor's behaviour is controlled by this one text, so edit it to change how the bot teaches.

## `llm.py`

- **Top constants**: which provider and model to use, read from environment variables with defaults (`LLM_PROVIDER`, `GEMINI_MODEL`, `CLAUDE_MODEL`).
- **`chat(system_prompt, history)`**: the only function the rest of the app calls. It picks Gemini or Claude and returns the reply as text. Swapping AI providers means changing only this file.
- **`_gemini(...)`**:
  1. Creates a client with your key from `GEMINI_API_KEY`.
  2. Converts the chat history into Gemini's format (Gemini calls the AI side `"model"`, not `"assistant"`).
  3. Calls `generate_content`, passing the system prompt as `system_instruction`.
  4. Returns the text, or a fallback message if the reply is empty.
- **`_claude(...)`**: the same idea for Anthropic's API. Unused unless `LLM_PROVIDER=claude`.

The AI has **no memory of its own**. The full conversation is re-sent on every request, which is how it knows which question it asked.

## `app.py`, top to bottom

**Setup**
- `set_page_config` sets the browser tab title and icon.
- A loop copies your keys from `.streamlit/secrets.toml` into environment variables, because `llm.py` reads `os.environ`. The `try/except` handles the case where there is no secrets file.

**Constants**
- `TOPICS` loads `topics.json`. `DIFFICULTIES` is the slider's choices.
- `TAG_RE` is a regular expression that finds `[CORRECT]`, `[INCORRECT]` or `[SOLUTION]` at the very start of a reply.

**Memory (`session_state`)**
- `messages`: the chat log. Each entry has a role, the content, and a `hidden` flag.
- `settings`: the chosen (grade, topic, difficulty), or `None` before you start.
- `correct` and `attempted`: the score.
- `setdefault` only sets these on the first run, so they are not wiped on every rerun.

**`ask(user_text, hidden=False)`**: the core function. Every action goes through it.
1. Adds your message to `messages`. `hidden=True` keeps it out of the display (the Start message is hidden, so you don't see "Begin the lesson now...").
2. Builds `history` by stripping each message down to its role and content.
3. Calls `llm.chat(...)` inside a "Thinking..." spinner. If it fails (bad key, quota, no internet), it removes your message, shows a red error, and exits, so the app keeps running.
4. Looks for a tag at the start of the reply:
   - `[CORRECT]` or `[INCORRECT]`: `attempted` goes up by 1, and `correct` goes up by 1 only for CORRECT.
   - `[SOLUTION]`: no score change, so asking for the answer doesn't count.
   - The tag is then cut off, so you never see it.
5. Saves the cleaned reply as an assistant message.

**Sidebar**
- Grade dropdown, then a topic dropdown listing only that grade's topics, then the difficulty slider.
- **Start session** clears the chat and score, saves your choices, and calls `ask(START_MESSAGE, hidden=True)`. The AI replies with the explanation and Question 1.
- The score appears as `correct / attempted`.

**Welcome screen**
If no session has started, it shows the "pick a grade..." hint and `st.stop()` ends the run there, so nothing below it appears.

**Showing the chat**
It prints the caption (grade, topic, difficulty), then loops through `messages`, skipping hidden ones. Each message is drawn as a chat bubble, and `st.markdown` turns `$...$` into proper math.

**The three buttons**
Hint, Show solution and Next question each call `ask()` with their canned message, then `st.rerun()` to redraw immediately. Without the rerun, the new reply would only show after your next interaction.

**Text box**
`st.chat_input` is the box at the bottom. Whatever you type goes to `ask()`, which is how you submit answers or ask your own questions.

## One full round

1. You press **Start session** (for example Grade 12, Integration, Hard). Messages and score reset, and `ask()` sends the hidden start command plus the system prompt to Gemini.
2. Gemini returns the explanation and Question 1, and the bubble appears.
3. You type your answer. `ask()` re-sends the whole chat, and Gemini replies `[CORRECT] Yes!...`. The tag is stripped, the score becomes 1/1, `st.rerun()` redraws, and the sidebar updates.
4. You press **Show solution**. Gemini replies `[SOLUTION] 1. ... 2. ...` and the score is unchanged.
5. You press **Next question** and the cycle continues.

## Known limitations

- If the AI forgets to add the tag, that answer is not scored.
- If **Start session** fails (for example a quota error), the session is set but the chat is empty. You see the error and need to press Start again.
- Nothing is saved to disk. Refreshing the browser resets the session and score.
