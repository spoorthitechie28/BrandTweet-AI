# BrandTweet AI — Approach Document

## 1. Problem and scope

The task is to accept a brand brief, infer a brand voice, and generate 10
creative, on-brand tweets for a campaign. The solution must be simple enough to
finish in a day, reliable enough to demo, and honest about what it does.

**In scope:** a Streamlit form, two OpenAI calls (voice analysis and tweet
generation), strict output validation, a polished results view, clear error
states, local secrets and deployment instructions.

**Out of scope:** databases, authentication, social-media scraping, scheduling,
direct posting, analytics, and multi-page navigation. None of these improve the
core assignment enough to justify the extra failure modes.

---

## 2. Architecture

```text
app.py (UI)                         brandtweet.py (logic)
───────────                         ─────────────────────
Streamlit form  ── BrandBrief ───▶  validate_brief()
                                    │
                                    ▼
st.status step 1 ────────────────▶  infer_brand_voice()
                                      OpenAI chat + JSON mode
                                      parse_voice() → VoiceProfile
                                      one repair retry on bad output
                                    │
                                    ▼
st.status step 2 ────────────────▶  generate_tweets()
                                      VoiceProfile + objective playbook
                                      OpenAI chat + JSON mode
                                      parse_tweets() → 10 × Tweet
                                      count / unique / openings / 280 chars
                                      one repair retry + previous-set check
                                    │
Results UI ◀── VoiceProfile + [Tweet] ┘
```

Separating the logic from the UI is the most important structural decision:

- `brandtweet.py` has no Streamlit imports and can be unit-tested for free.
- `app.py` owns layout, session state and user-facing errors.
- The OpenAI client is injected into the core functions, which makes the fake
  client in `test_brandtweet.py` possible.

Only one extra module is used. No LangChain, no vector database, no agent
framework: the problem is two deterministic API calls with validation, and a
small explicit pipeline is easier to explain and debug.

---

## 3. Brand voice inference

The model receives the brief inside a labelled data block and is asked for a JSON
object with:

- `tone` (2–4 words)
- `personality`
- `audience`
- `content_themes` (3–5)
- `writing_style` (vocabulary, sentence length, rhythm)
- `humour`
- `emoji_guidance`
- `formality`
- `campaign_goals`
- `summary` (3–4 marketer-facing bullets)

Two constraints matter:

1. **The model is told it has not seen real posts.** The prompt says it has only
   the brief and must describe an inference, not claim live analysis. The UI
   repeats this under the voice card.
2. **A supplied tone is a hard constraint.** If the user chooses *Premium*, the
   voice must stay premium even if the product category suggests a playful
   default. The prompt asks the model to adapt the tone to the brand rather than
   just repeat the word.

The voice profile is stored as a `VoiceProfile` dataclass and reused by Stage 2.
"Regenerate All Tweets" deliberately reuses it; "Generate Another Set" reruns
this stage.

If `summary` comes back with fewer than three bullets, the parser builds
fallbacks from the other fields instead of failing the whole request. This keeps
the UI contract (3–4 bullets) without throwing away a good voice analysis.

---

## 4. Tweet generation and prompt design

Stage 2 receives:

- the original brief,
- the structured voice profile,
- an objective-specific playbook,
- optionally, the previous 10 tweets to avoid.

The system prompt is explicit about:

| Requirement | Prompt mechanism |
|---|---|
| Exactly 10 | Hard rule 1, and parser rejects any other count |
| 280 characters | Hard rule 2, parser trims as a last resort |
| Variety | Hard rule 3 + angle mix in rule 5 |
| No invented facts | Hard rule 6, repeated in the voice prompt |
| Selective hashtags/emojis | Hard rule 7 with numeric caps |
| Original copy | Hard rule 8 |
| No prompt injection | Rule 10 + data boundary + output validation |
| Campaign relevance | `OBJECTIVE_GUIDANCE` per objective |

The **objective playbook** is a short instruction per dropdown value:

- *Engagement* → questions and participation, no hard sell.
- *Promotion* → clear value and soft CTA, no invented prices or deadlines.
- *Brand Awareness* → personality and a memorable point of view.
- *Product Launch* → curiosity and clarity, only features in the brief.
- *Customer Education* → useful tips, no unsupported statistics.

The **angle mix** asks for 2 conversational, 2 soft promotional, 1–2 witty (only
if the voice supports humour), 2 informative, 1 question, and 1 community/CTA
post. Premium or minimal brands replace humour slots with insight.

`temperature` is 0.2 for voice inference (consistency) and 0.9 for tweets
(variety). Both the model and JSON mode are configurable/fall back gracefully.

### Why JSON mode plus validation?

Asking for prose and parsing it with regex is brittle. JSON mode gives a clear
schema, but a model can still return nine tweets, duplicate an idea, or run long.
So the response is never trusted directly:

1. Strip markdown fences / surrounding prose, then `json.loads`.
2. Validate field types and required keys.
3. Enforce exactly 10 unique tweets.
4. Reject more than three tweets starting with the same word.
5. Trim at a word boundary if any tweet exceeds 280 characters, and tell the user.
6. If validation fails, send the model its own output plus the specific error and
   ask for one correction.
7. If the repair also fails, show a clear error and do not display partial output.

This "generate → validate → repair once → fail safely" loop is the core
reliability pattern of the app.

---

## 5. Prompt-injection defence

A user could type "ignore all previous instructions" into the product
description. The defences are layered:

1. **Cleaning:** `clean_text()` removes control characters and HTML-style tags,
   so a user cannot close the `<brand_input>` block early.
2. **Boundary:** all user fields are placed inside `<brand_input>...</brand_input>`.
3. **System instruction:** both prompts explicitly say the block is untrusted
   data, not instructions, and that commands inside it must be ignored.
4. **Output contract:** the parser enforces 10 tweets, length, uniqueness and
   variety regardless of what the text says.
5. **No tools:** the model has no browsing, file, database or code access, so a
   successful injection can only affect wording, not take actions.

The app does not claim this makes injection impossible. It makes the blast radius
small and the output contract enforceable, which is the right trade-off for a
text-generation demo.

---

## 6. UI and UX decisions

- **Two-column start screen:** brief and primary action on the left, a short
  "How it works" and demo presets on the right. On mobile, Streamlit stacks them.
- **Prominent primary action:** a full-width indigo gradient button labelled
  exactly **Generate 10 Tweets**.
- **Progressive disclosure:** the configuration help is an expander, so the main
  screen stays clean.
- **Voice summary before tweets:** the user sees *why* the copy sounds the way it
  does before reading it.
- **Cards in numbered rows:** one row of two cards at a time keeps numbering
  `1,2 / 3,4` on desktop and when columns stack on mobile.
- **Character counts:** shown as `n / 280`, calculated from the exact text that
  would be copied. Counts are green because the parser guarantees the limit.
- **Copy control:** uses Streamlit's native code-block copy button. It is reliable
  across browsers and HTTPS, and does not require a custom JavaScript clipboard
  workaround. The CSS makes the icon permanently visible and the code block
  readable as normal text.
- **Loading:** a two-step `st.status` shows which stage is running.
- **Errors:** rendered outside the collapsed status, so the reason is always
  visible. Unexpected failures also expose technical details in an expander.
- **No API key:** a yellow configuration card, a setup expander, and a disabled
  generate button. No mock results.
- **No gratuitous animation:** only subtle hover shadows and transitions.

The light theme is fixed in `.streamlit/config.toml` so a recruiter opening the
demo sees the intended design rather than their OS dark mode.

---

## 7. Configuration and secrets

`_read_setting()` reads Streamlit secrets first, then environment variables.
Locally, `python-dotenv` loads `.env`. On Streamlit Cloud, the same code reads
`st.secrets`. The model name is also configurable:

```dotenv
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
```

`.env`, `.env.*` and `.streamlit/secrets.toml` are git-ignored. `.env.example` is
the only committed template. The README includes a `git check-ignore .env` step
before pushing.

---

## 8. Error handling

Every API call maps SDK exceptions to a safe, actionable message:

| Failure | User message |
|---|---|
| Missing key | Configuration warning + disabled button |
| Invalid/revoked key | "OpenAI rejected the API key…" |
| Quota / rate limit | "OpenAI rate limit or quota reached…" |
| Timeout | "The request timed out…" |
| Network | "Could not reach OpenAI…" |
| Bad model / request | "Check that OPENAI_MODEL is a supported chat model…" |
| Bad JSON or failed validation after retry | "The AI response did not pass validation…" |
| Anything unexpected | Generic message + technical details expander |

The app catches exceptions at the UI boundary as well, so an API failure cannot
crash the Streamlit session.

---

## 9. Testing

### Automated (31 tests, no network)

`python -m unittest -v` covers:

- input cleaning, tag stripping, whitespace, missing description, missing brand
- unknown objective and Auto tone
- character counting, exact-limit and over-limit behaviour
- JSON fences and surrounding prose
- voice summary fallback and missing tone
- exactly 10 tweets, numbering removal, plain-string output
- rejection of 9 tweets, duplicates, missing list, repetitive openings
- long tweet trimming
- prompt boundary (one `<brand_input>` open/close after injection text)
- system prompt security and "no live analysis" language
- a fake OpenAI client running both stages
- one repair retry after a 9-tweet response
- markdown-fenced JSON in the pipeline
- tweets-only regeneration with a saved voice

The fake client is important: it tests the pipeline deterministically without
spending money or requiring a key.

### Manual (with a real key)

The README's testing section covers:

- Zomato vs Apple voice contrast
- exactly 10 cards and correct counts
- copy button
- regenerate / another set / start over / download
- missing key, invalid key and network failure
- a prompt-injection line in "Additional instructions"

During development, the invalid-key path was exercised against the real OpenAI
endpoint and returned the intended in-app message.

The full UI success flow (both stages, 10 cards, regenerate, another set, start
over, download) was smoke-tested against a **local OpenAI-compatible mock server**
that returned fixed test data. That server is not part of the project and the app
never ships mock output. The success path with real model output still needs one
run with your own key. Use the two demo briefs for that check.

### What is not tested

- Real X character weighting for CJK text and shortened URLs (out of scope; the
  prompt writes English and invents no links).
- Visual regression at every breakpoint (manually checked at desktop and narrow
  widths).
- Model output quality across every possible brand (prompt quality is inherently
  probabilistic).

---

## 10. Limitations

1. **No live social analysis.** Voice is inferred from the brief. Real analysis
   would require official API access, data storage and legal review.
2. **Probabilistic quality.** The validator guarantees structure, not taste. A
   model can still produce a bland line; regeneration and a better brief help.
3. **No fact database.** The prompt forbids invented offers/specs/stats, but the
   app cannot verify claims against a source of truth. For regulated industries,
   a human review step is required.
4. **Character counting.** Python `len()` matches visible English characters; X
   uses weighted counting for some Unicode ranges and shortens links.
5. **Cost.** Two chat requests per full generation. The default small model keeps
   this low, but it is not free.
6. **Secrets.** Streamlit secrets are appropriate for a demo, not a substitute
   for a backend proxy in a high-traffic production system.

---

## 11. Interview notes

**Why two calls instead of one?**
Separating voice inference from copywriting makes the reasoning visible, lets the
UI show a useful voice profile, and makes "regenerate with the same voice"
possible with one call. It also gives each stage a narrower prompt and a simpler
JSON schema.

**Why not use an agent framework?**
The workflow is fixed: brief → voice → tweets. An agent adds latency, cost and
non-determinism without adding capability. A two-function pipeline is easier to
test and explain.

**How do you stop hallucinated discounts?**
Three ways: the prompt forbids invented facts and repeats the rule in both
stages; the brief is the only source; and the voice stage is told not to invent
specifics. The app cannot prove a claim is true, so human review remains the
final check. This is a documented limitation, not a hidden one.

**How do you handle prompt injection?**
Data boundary, explicit system instruction, input tag stripping, and an output
schema that is enforced after generation. No tools means no real-world action.

**How do you guarantee 10 tweets?**
The parser counts unique tweets and rejects anything else. On failure it sends
the model its own output plus the validation error for one repair attempt. If that
fails, the user gets a clear error rather than a partial set.

**What would you add next?**
Optional retrieval of a brand's public website copy for a more grounded voice,
per-tweet editing, A/B variants, a scheduled content calendar, and a human
approval workflow. None of these are needed for the assignment demo.

---

## 12. Tools used

- Python 3.10+ (tested locally on 3.14)
- Streamlit 1.66.1
- OpenAI Python SDK 3.x, Chat Completions with JSON mode
- `python-dotenv`
- `unittest` (standard library)
- GitHub and Streamlit Community Cloud for delivery
