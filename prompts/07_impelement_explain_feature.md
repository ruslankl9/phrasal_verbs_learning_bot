**TASK: Add “Explain” feature to card UI (inline), with OpenAI-compatible API call, caching, and clean navigation**

You previously built a Telegram SRS bot (Python 3.11, aiogram v3, SQLite), with HTML rendering, single-message UI, and handlers for Today/rounds. Implement **Explain**:

## What to build

### 1) New “Explain” button on card UI

* Update the **card inline keyboard** to add a third button on a **second row**:

  * Row 1: `Again` · `Good`
  * Row 2: `💡 Explain`
* Callback: `ui:card.explain:<card_id>` (or progress id).
* Pressing **Explain** must **not alter** SRS state, round queues, or the current card’s position.

### 2) Explain screen (inline, same message)

* On tap of **Explain**:

  1. **Edit the same message** to show a **loading placeholder** (HTML):

     ```
     <b>Explain</b>

     ⏳ Loading an explanation... Please wait a moment.
     ```

     (Feel free to tweak the copy but keep it short and friendly; no new message, always edit.)
  2. Launch an **async request** to an **OpenAI-compatible API** (see §3) with a concise prompt (see §3 Prompt).
  3. If a cached explanation exists in DB for this `card_id`, **skip the API call** and render from cache.
  4. When the explanation text is available, **edit the same message** to display it with a **Back** button that returns to the **same card view**:

     * Title: `<b>Explain</b>`
     * Body: the **exact formatting** returned by the model (pass through as is), rendered with the same parse mode you already use (HTML). Do not add extra wrappers that would break formatting.
     * Inline buttons: `[◀️ Back]` (callback `ui:card.explain.back:<card_id>`)
* **Back** must restore the **original card message** (re-render the card with Again/Good/Explain buttons), **without changing the card’s SRS state** or queue.

### 3) OpenAI-compatible API call

* Add configuration in `srsbot/config.py`:

  * `EXPLAIN_API_BASE` (str, required): base URL of OpenAI-compatible API (e.g., `https://api.openai.com/v1`)
  * `EXPLAIN_API_KEY` (str | None, optional): API key; if absent, don’t send Authorization header
  * `EXPLAIN_MODEL` (str, default e.g. `gpt-4o-mini` or another code/chat model available at the chosen endpoint)
  * `EXPLAIN_TIMEOUT_SECONDS` (int, default 30)
* Implement a small client in `srsbot/explain_client.py` with a single async function:

  ```python
  async def get_explanation(prompt: str) -> str:
      """
      Calls the OpenAI-compatible /chat/completions (or /completions) endpoint with given prompt
      and returns the raw text content. Use EXPLAIN_API_BASE, EXPLAIN_API_KEY, EXPLAIN_MODEL.
      """
  ```

  * Prefer `openai` package to send a single user message (the endpoint expose `/v1/responses` endpoint).
  * Temperature low/moderate (e.g., 0.3–0.5).
  * Handle non-200 responses and timeouts:

    * Log details to app logger (do **not** show to user).
    * Raise a typed error handled by the handler to show a friendly message.

#### Prompt template (adjust grammar slightly; keep it lightweight)

Build a single string from the current **card render** (phrasal, meaning, examples, tags) and pass it as **user** content:

```
Explain the following card for an English learner who is not a native speaker.
Use clear B1-level English. Give only explanations; no questions, no chit-chat.
Add helpful details to make the meaning easy to understand. Keep it concise.

CARD:
{card_text_human_readable}
```

* `card_text_human_readable` should include phrasal, meaning, and examples in plain text or simple HTML (whichever you pass through consistently). Do not include internal fields like sense\_uid.

### 4) Caching explanations

* Create a new table in `srsbot/db.py` migrations:

  ```sql
  CREATE TABLE IF NOT EXISTS explain_cache (
    card_id INTEGER PRIMARY KEY,
    content TEXT NOT NULL,           -- raw explanation text as returned (HTML-safe)
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
  );
  ```
* Repository helpers:

  * `get_explanation_cached(card_id: int) -> str | None`
  * `store_explanation(card_id: int, content: str) -> None`
* When Explain is requested:

  * Check cache; if hit → render from cache.
  * If miss → call API, store response, then render.
* **Preserve formatting**: do not modify the model’s text. If your global parse mode is HTML, ensure the explanation is compatible (either sanitize/escape if needed, or instruct the model implicitly to use simple paragraphs, lists, and `<b>/<i>` only).

### 5) Errors

* If the API fails or times out:

  * Edit the message to:

    ```
    <b>Explain</b>

    ❌ Sorry, we couldn’t load the explanation this time.
    Please try again later.
    ```
  * Provide buttons: `[◀️ Back]` (return to the card).
  * Log the error details (status code, body, exception) to your logger, but **never** show details to the user.

### 6) Navigation & Clean UI (single message)

* Use your existing `ui.show_screen`/edit-in-place approach:

  * Tapping **Explain** edits the same message to “Loading...”
  * Then edits again to the final explanation (or error) with **Back**.
  * Tapping **Back** re-renders the **same card** (Again/Good/Explain), maintaining its place in the current round and preserving its state (learning/review, streaks unaffected).
* The **Explain** feature must **not** influence SRS memory scheduling.

## Files to add/modify

* **Add** `srsbot/explain_client.py`

  * Async HTTP client (e.g., `aiohttp` or `httpx[async]`) using env/config.
  * `get_explanation(prompt: str) -> str` as specified.

* **Modify** `srsbot/config.py`

  * Load `EXPLAIN_API_BASE`, `EXPLAIN_API_KEY`, `EXPLAIN_MODEL`, `EXPLAIN_TIMEOUT_SECONDS` from env with defaults.

* **Modify** `srsbot/db.py`

  * Migration to add `explain_cache` table.
  * CRUD helpers for cache.

* **Modify** `srsbot/formatters.py`

  * Add small helper to produce `card_text_human_readable` for the prompt (reuse existing HTML/plain parts).
  * Add `format_explain_loading_html()` and `format_explain_error_html()` helpers (short strings shown above).

* **Modify** `srsbot/keyboards.py`

  * Update card keyboard builder to add `💡 Explain` on a second row.
  * Add `kb_explain_back(card_id)` for a single Back button.

* **Modify** `srsbot/handlers/today.py` (or the file serving cards)

  * Add callbacks:

    * `ui:card.explain:<card_id>` → show loading, fetch cached or call API, render explanation with Back.
    * `ui:card.explain.back:<card_id>` → re-render the exact same card view (Again/Good/Explain) without changing state.
  * Ensure the current **card context** (card\_id/progress) is resolvable to re-render upon Back.

* **README.md**

  * Document Explain feature, env vars, caching, and privacy note (no user PII sent, only card content).

## HTML & Safety

* Keep parse mode consistent (HTML).
* If you pass model output directly to Telegram as HTML:

  * Consider a minimal sanitizer: allow only a safe subset (`<b>`, `<i>`, `<u>`, `<code>`, `<pre>`, `<br>`, `<ul>`, `<ol>`, `<li>`, `<p>`), or instruct the model to avoid complex tags. At minimum, escape `<`/`>` in unexpected places to avoid Telegram parse errors.
* The loading and error messages are short and edited in place.

## Tests (pytest)

* `tests/test_explain_cache.py`

  * Cache miss → calls client, stores result, next call is cache hit (no client call).
* `tests/test_explain_flow.py`

  * Tapping Explain shows loading, then final explanation with Back.
  * Tapping Back restores the same card view (keyboard with Again/Good/Explain).
* `tests/test_explain_prompt.py`

  * Ensure prompt builder includes phrasal, meaning, and examples; concise; no internal fields.

## Acceptance Criteria

1. Card UI has **💡 Explain** on a second row; tapping it does **not** alter SRS state or position.
2. Explain screen:

   * Shows **Loading** placeholder immediately via message edit.
   * Uses cache if present; otherwise calls the configured OpenAI-compatible API with the specified prompt.
   * On success, shows the explanation with **Back**; formatting is preserved for Telegram (HTML).
   * On error, shows a friendly error with **Back**; logs technical details only.
3. **Back** restores the **same card** and keyboard in the same message, keeping queues and SRS intact.
4. Explanations are cached in SQLite by `card_id`.
5. All navigation and renders **edit the single active UI message** (no message spam).
6. Env vars are respected; missing API key works if server doesn’t require it.

Keep code typed (mypy), formatted (ruff/black), with concise docstrings for new helpers.
