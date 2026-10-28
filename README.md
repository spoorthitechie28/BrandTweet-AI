# BrandTweet AI

**Turn a brand brief into ten tweets that sound like the brand wrote them.**

BrandTweet AI is a small Streamlit application that infers a brand voice from a
short brief, then writes a campaign-ready set of 10 tweets for X (Twitter). It
uses a two-stage OpenAI pipeline, validates every response, and never presents
mock content as real AI output.

**Live demo:** _add your Streamlit Community Cloud URL here after deploying (step 7)._

---

## What it does

- Accepts a brand brief: name, industry, campaign objective, product/service,
  audience, preferred tone and extra instructions.
- **Stage 1** infers a structured brand voice: personality, audience, themes,
  vocabulary, humour, emoji guidance, formality and campaign goals.
- **Stage 2** writes **exactly 10 distinct tweets** with a mix of conversational,
  promotional, witty, informative, question and community angles.
- Shows a 3–4 bullet voice summary and 10 tweet cards with character counts and
  a native copy-to-clipboard button.
- Supports **Regenerate All Tweets** (same voice), **Generate Another Set** (new
  voice), **Start Over**, and a `.txt` download.
- Validates outputs before display: exact count, unique tweets, varied openings,
  280-character limit, and no reuse of the previous set.
- Handles missing keys, bad keys, rate limits, timeouts and malformed AI JSON
  with clear messages instead of crashing or faking results.

The app deliberately does **not** scrape social media. The voice is an inference
from the brief, and the UI says so.

---

## How it works

```text
User brief
    │
    ▼
┌──────────────────────────────────────────────┐
│ Stage 1 · infer_brand_voice()                │
│ System prompt + <brand_input> data boundary  │
│ OpenAI JSON mode → validate → repair once    │
│ → VoiceProfile (tone, audience, themes, ...) │
└──────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────┐
│ Stage 2 · generate_tweets()                  │
│ VoiceProfile + objective playbook            │
│ → exactly 10 tweets as JSON                  │
│ → count / uniqueness / openings / 280 chars  │
│ → repair once if validation fails            │
└──────────────────────────────────────────────┘
    │
    ▼
Streamlit results UI
(voice summary, 10 cards, copy, regenerate, download)
```

The core logic lives in `brandtweet.py` and has no Streamlit imports, so it can
be unit-tested on its own. `app.py` is only the interface.

### Prompt-injection protection

- User text is cleaned and stripped of HTML-style tags.
- It is placed inside a `<brand_input>` block that the system prompt explicitly
  labels as **untrusted data, not instructions**.
- The system prompt says to ignore commands inside the block.
- Even if the model ignores that, the parser enforces exactly 10 tweets, the
  length limit and uniqueness. The app has no tools or database for an injected
  instruction to reach.

This is defence in depth for a text-only app, not a guarantee that a language
model can never be manipulated.

---

## Project structure

```text
brandtweet-ai/
├── app.py                 # Streamlit UI only
├── brandtweet.py          # two-stage AI pipeline, prompts, parsing, validation
├── test_brandtweet.py     # 31 offline tests (no API calls)
├── requirements.txt
├── .env.example
├── .gitignore
├── .streamlit/
│   └── config.toml        # light theme and headless server settings
├── README.md
├── APPROACH.md            # architecture, prompt design, testing, limitations
└── EXAMPLES.md            # example outputs and submission checklist
```

---

## Quick start

### 1. Get an OpenAI API key

1. Sign in at <https://platform.openai.com/>.
2. Add a small amount of credit under **Billing** (API access is paid; a new
   account may need credit before requests succeed).
3. Open **API keys → Create new secret key**.
4. Copy the key once. It looks like `sk-...`. Never commit it or share it.

Set a low usage limit while testing. One full run makes two short chat requests.

### 2. Install the project

**Windows PowerShell**

```powershell
cd brandtweet-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks activation, skip it and use the venv's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

**macOS / Linux**

```bash
cd brandtweet-ai
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Python 3.10+ is required (3.11 or 3.12 recommended on Streamlit Cloud).

### 3. Configure the key locally

```powershell
Copy-Item .env.example .env      # macOS/Linux: cp .env.example .env
notepad .env                     # macOS/Linux: nano .env
```

Set:

```dotenv
OPENAI_API_KEY=sk-your-real-key
OPENAI_MODEL=gpt-4.1-mini
```

`.env` is git-ignored. `OPENAI_MODEL` is optional; the default is
`gpt-4.1-mini`. Any supported chat model that can return JSON should work.

### 4. Run

```bash
streamlit run app.py
```

Open <http://localhost:8501>. If the key is missing, the app shows a clear
configuration warning and disables the generate button. It does **not** show
fake tweets.

### 5. Test with two contrasting brands

Use the **Load Zomato example** and **Load Apple example** buttons in the right
panel, then click **Generate 10 Tweets**.

| Check | Zomato example | Apple example |
|---|---|---|
| Objective | Engagement | Brand Awareness |
| Preferred tone | Witty | Premium |
| Expected voice | Playful, food-culture humour, questions, community prompts | Calm, restrained, short declarative lines, no emojis (per instructions) |
| Must be true | Exactly 10 cards, each ≤ 280 chars, no invented offers | Exactly 10 cards, each ≤ 280 chars, no invented specs or dates |

Then verify:

1. The two voice summaries are noticeably different.
2. Each card shows the correct `n / 280` count, and the text matches the count.
3. The copy icon on a card copies that tweet (it is Streamlit's native,
   permission-safe clipboard button).
4. **Regenerate All Tweets** keeps the same voice and writes new copy.
5. **Generate Another Set** re-runs voice analysis and changes the voice.
6. **Start Over** empties the form and removes the results.
7. **Download .txt** downloads the voice summary and all 10 tweets.

More test cases and a submission checklist are in [EXAMPLES.md](EXAMPLES.md).

### 6. Run the automated tests

The tests use a fake OpenAI client, so they are free and do not need a key:

```bash
python -m unittest -v
```

Expected: `Ran 31 tests ... OK`.

They cover input cleaning, description validation, JSON extraction, the
3–4 bullet summary fallback, exact-count/duplicate/opening/length checks,
character counting, prompt-injection boundaries, and a full two-stage pipeline
with a repair retry.

---

## Deploy to GitHub

This folder is already a local git repository with one commit on `main`. You do
not need to initialise or commit again.

1. In GitHub, create an **empty** repository named `brandtweet-ai`. Do **not**
   add a README, `.gitignore` or licence, so the first push does not conflict.
2. From the project folder, connect it and push:

```bash
git remote add origin https://github.com/YOUR-USERNAME/brandtweet-ai.git
git push -u origin main
```

If you copied these files somewhere else and there is no `.git` folder, create a
repository first instead:

```bash
git init
git add .
git commit -m "Build BrandTweet AI"
git branch -M main
```

Before pushing, confirm secrets are ignored:

```bash
git status              # .env must not appear
git check-ignore .env   # should print .env
```

If `.env` was ever committed, rotate the key in OpenAI immediately and remove
it from git history. A file deleted in a later commit is still in history.

---

## Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io/> and sign in with GitHub.
2. Click **Create app** (or **New app**).
3. Choose your repository, branch `main`, and main file path `app.py`.
4. Optionally set the app URL slug, e.g. `brandtweet-ai`.
5. Open **Advanced settings → Python version** and choose **3.12** (3.11 also
   works). The pinned Streamlit version supports these.
6. Open **Advanced settings → Secrets** and paste:

   ```toml
   OPENAI_API_KEY = "sk-your-real-key"
   OPENAI_MODEL = "gpt-4.1-mini"
   ```

   This is the deployment equivalent of `.env`. It is stored encrypted by
   Streamlit and is not in GitHub.
7. Click **Deploy**. The first build installs `requirements.txt` and takes a
   few minutes.
8. When the app is running, copy the public URL:
   `https://YOUR-APP-NAME.streamlit.app`
9. Paste that URL into the **Live demo** line at the top of this README and in
   your submission.
10. If you change a secret later, use **App settings → Secrets → Save**; the app
    restarts automatically.

### Troubleshooting deployment

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` | Make sure `requirements.txt` is committed at the repo root and the app path is `app.py`. |
| "OpenAI API key not configured" on the live app | Add `OPENAI_API_KEY` under **App settings → Secrets**, save, and reboot the app. |
| `AuthenticationError` / "OpenAI rejected the API key" | The key is wrong, revoked, or has no credit. Create a new key and update the secret. |
| `RateLimitError` / quota message | Check OpenAI billing/usage limits, wait, then retry. |
| `BadRequestError` after changing the model | Set `OPENAI_MODEL` to a supported chat model such as `gpt-4.1-mini`. |
| App sleeps | Free Streamlit apps sleep when idle; open the URL to wake it before a demo. |
| Build fails on Python version | Set the app's Python version to 3.12 and redeploy. |

---

## Local troubleshooting

| Problem | Solution |
|---|---|
| `streamlit` is not recognised | Activate the venv, or run `python -m streamlit run app.py`. |
| PowerShell says "running scripts is disabled" | Use `.\.venv\Scripts\python.exe -m streamlit run app.py` instead of activating. |
| Port 8501 already in use | `streamlit run app.py --server.port 8502`. |
| Key not picked up | The file must be named exactly `.env` in the project folder, with no quotes around the value. Restart Streamlit after editing. |
| `insufficient_quota` | Add credit to the OpenAI account; a valid key without billing cannot generate. |
| Text is trimmed | The model exceeded 280 characters. The app trims at a word boundary and tells you. Regenerate if needed. |

---

## Cost and privacy

- Each generation uses two short chat requests. Regenerating tweets with the
  same voice uses one request.
- Inputs are sent to the OpenAI API for processing. The app has no database and
  does not save briefs or results on the server.
- Do not paste confidential material into any third-party AI tool.
- `streamlit` session state keeps results only for the current browser session.

---

## Limitations and next steps

- Voice is **inferred from the brief**, not measured from real posts. Live social
  analysis would need official API access, storage and legal review.
- Character counts use Python `len()` (code points), which matches normal English
  copy. X applies different weighting to some Unicode ranges and shortens links;
  the app does not shorten URLs because it does not invent them.
- Hashtag/emoji frequency is guided by the prompt, not hard-failed by the parser.
- There is no login, database, scheduling or direct posting. Those are out of
  scope for the assignment and would add cost and security work.
- Quality depends on the model. `gpt-4.1-mini` is a good cost/speed default;
  a larger model can be selected with `OPENAI_MODEL`.

See [APPROACH.md](APPROACH.md) for the design rationale and interview notes.

---

## Tech stack

- Python 3.10+
- Streamlit 1.66
- OpenAI Python SDK (Chat Completions, JSON mode)
- `python-dotenv` for local secrets
- Streamlit Community Cloud for hosting
