**TASK: Update Card Rendering (HTML layout) + Randomize Round Order**

You previously built a Telegram SRS bot (Python 3.11, aiogram v3). Apply the following UX changes:

## Goals

1. **Card render format (HTML)**
   Render each card using HTML (respecting current parse mode). Desired layout (preserve blank lines as shown):

```
🆕
<b>act on</b>

<i>to take action based on advice or info</i>
Examples:
- We acted on the feedback.
- The police acted on a tip.

Tags: #work #daily
```

Rules:

* Show **🆕 on a separate line only if the card is shown to the user for the first time ever** (i.e., this card was not previously seen by this user; do not show 🆕 on subsequent days). If you already track “first seen”, use that; otherwise infer “new” when `progress.state == "learning"` and `repetitions == 0` and `last_seen_at is NULL` (or equivalent).
* **Phrasal verb in bold**: `<b>{phrasal}</b>`
* **Meaning in italics** on its own line: `<i>{meaning_en}</i>`
* Then a literal line `Examples:` followed by **N bullet lines**, one per example string, each starting with `- ` (dash+space). Support arbitrary number of examples (2–3 typical).
* Then `Tags:` line with **space-separated hashtags** built from `tags` (lowercase, non-word chars replaced with `_`), e.g. `Tags: #work #daily`.
* Escape all user/content strings safely for HTML. Keep overall message under Telegram limits.
* Preserve clean blank lines exactly as shown above (empty lines between sections).

2. **Randomize order of cards in a round**

* Today’s round queue must be **shuffled** so cards do **not** follow DB insertion order.
* Maintain the **priority buckets** (learning due → review due → new), but **shuffle within each bucket**, then concatenate in that order.
* In-session requeues (for **Again**) should still insert after `k` cards (as configured), but the base round should be randomized at creation or recomputation.

## Implementation Details

### Files to Modify

* `srsbot/formatters.py`

  * Add/modify a function like:

    ```python
    def html_card_message(card, progress, is_new: bool, tags: list[str]) -> str:
        """
        Returns an HTML-formatted message body according to the new spec.
        - Safely escape user/content values for HTML.
        - Build hashtag line from tags (normalized).
        """
    ```
  * Helpers:

    * `escape_html(s: str) -> str`
    * `normalize_tag(s: str) -> str`  # lowercase; replace non \[a-z0-9\_] with \_
  * Logic:

    * `badge = "🆕\n" if is_new else ""`
    * Compose with blank lines exactly as shown.

* `srsbot/handlers/today.py` (or wherever you assemble/send the card message)

  * Ensure `parse_mode=ParseMode.HTML` (aiogram v3 style) is used on send/edit.
  * Compute `is_new` for the card (first presentation to this user). Use existing fields if present (e.g., `last_seen_at is None`), else determine by `progress.repetitions == 0 and progress.state == "learning" and not previously shown today`.
  * Call the new formatter for each card render.
  * Keep the existing inline keyboard (Again/Good, Finish session).

* `srsbot/queue.py`

  * In `build_round_queue(...)` (or equivalent), after selecting each bucket:

    * `random.shuffle(learning_due)`
    * `random.shuffle(reviews_due_limited)`
    * `random.shuffle(new_candidates)`
    * Then concatenate: `queue = learning_due + reviews_due_limited + new_candidates`.
  * Ensure deterministic randomness is **not** required. If you want reproducibility for tests, allow an optional seed parameter in tests.

* `srsbot/ui.py` (if you centralize send/edit logic)

  * Confirm that `parse_mode=HTML` is used consistently for card messages.
  * No extra changes needed except ensuring edits keep HTML parse mode.

### HTML Safety

* Always escape phrasal, meaning, and examples before insertion.
* Hashtags derived from tags should be sanitized:

  ```python
  tag = re.sub(r'[^a-z0-9_]+', '_', tag.lower()).strip('_')
  ```

  Skip empty tags after normalization.

### “New” Badge Determination

* Preferred: `is_new = progress.last_seen_at is None` (first time ever).
* If not tracked yet, approximate: `is_new = (progress.state == "learning" and progress.repetitions == 0 and progress.lapses == 0 and first_time_shown_today_for_this_card)`; store/update `last_seen_at` upon first render.

### Tests

* Add/extend tests:

  * `tests/test_format_card_html.py`

    * Given a card with multiple examples and tags, ensure output matches HTML spec:

      * Optional `🆕` line present/absent
      * `<b>` around phrasal, `<i>` around meaning
      * `Examples:` line and N bullets with `- `
      * `Tags: #tag1 #tag2` with normalized tags
      * Proper HTML escaping (e.g., `<`, `>`, `&`, quotes) in examples/meaning.
  * `tests/test_queue_shuffle.py`

    * Build a round with known ordered inputs; assert that:

      * Relative bucket order is preserved (learning before review before new)
      * Within each bucket, order differs from the original most of the time (may seed RNG for deterministic assertion).

### Acceptance Criteria

1. Card messages render with **HTML** exactly as specified, including optional top-line **🆕** for first-time cards, bold phrasal, italic meaning, variable-count examples with `- ` bullets, and `Tags: #...` line.
2. All string content is safely escaped for HTML, tags normalized to hashtags.
3. Round composition preserves bucket priority but is **shuffled within buckets**.
4. In-session behavior (Again/Good, Finish session) remains unchanged aside from the new rendering.
5. `parse_mode=HTML` is consistently used when sending/editing card messages.

Please implement code, unit tests, and any minor README note about the HTML rendering format.
