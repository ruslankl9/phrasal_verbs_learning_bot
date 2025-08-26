**TASK: Implement “Quiz” feature (MCQ on review cards) with Settings limit, inline navigation, HTML render, and summary**

You previously built a Telegram SRS bot (Python 3.11, aiogram v3, SQLite) with inline Menu/Settings, clean UI (single edited message), HTML rendering, and round logic. Add a **Quiz** mode with the details below.

## Feature Overview

* Add a **Quiz** entry to the Main Menu.
* A Quiz session presents **multiple-choice questions**: for each **review-state** phrasal verb, show the **phrasal verb** and **four answer options** (meanings):

  * exactly **1 correct** meaning (from the card being quizzed),
  * **3 distractors** drawn from **all other meanings in the database** (across all phrasal verbs/senses).
* Shuffle options per question.
* Provide a **Settings** field to limit how many questions per Quiz session (default 10).
* If there are **no eligible review cards**, show an informative message and a **Back** button.
* At the end, show a **summary** with per-question feedback:

  * ✅ if correct, ❌ if incorrect.
  * **Bold** the correct meaning.
  * *Italicize* the user’s choice if it was incorrect.
  * Provide buttons: **🔁 Take quiz again** and **◀️ Back to menu**.
* Keep UI **clean**: **edit** the same message for navigation; do not append new bot messages.

## Definitions & Constraints

* **Eligible pool**: cards in `progress.state == 'review'` for the current user.
* **Session question cap**: new setting `quiz_question_limit` (int, default 10, range 5–30) shown in **Settings** with friendly name; editable via your existing inline “value input” pattern (bold field name + italic description, validation, Back).
* **Randomization**:

  * Randomly **sample** up to `quiz_question_limit` cards from the eligible pool (no repeats within a session).
  * For each question, randomly sample 3 **distinct** distractor meanings from the global set of meanings (excluding the correct one); if fewer than 3 are available, reduce to what’s available and fill only as many options as you can (but target 4).
  * Shuffle the 4 options.
* **No SRS update** on Quiz answers (Quiz is practice-only and should not alter due dates/boxes).
* **HTML formatting** must be used throughout, consistent with your existing parse mode.

## UI / Navigation

### Main Menu

* Add a new button: **📝 Quiz** (`callback_data="ui:quiz"`).

### Quiz Start Screen

* If **no eligible review cards**:

  * Show: `No review cards available for quiz today.`
  * Buttons: `◀️ Back`
* Otherwise:

  * Initialize a Quiz session (see State below).
  * Show the **first question**.

### Question Render (HTML)

* Format:

  ```
  <b>{phrasal}</b>

  Choose the correct meaning:
  1) {option A}
  2) {option B}
  3) {option C}
  4) {option D}
  ```
* Inline keyboard: four buttons labeled `1️⃣`, `2️⃣`, `3️⃣`, `4️⃣` (callback carries the chosen index, e.g., `ui:quiz.answer:<qidx>:<optidx>`), plus a `◀️ Back` button that cancels the quiz and returns to the Main Menu (confirm discard with a concise edit-in-place prompt if needed).

### On Answer

* Record the user’s selected option, mark correct/incorrect.
* Move to the **next question**.
* After the last question, render the **summary**.

### Summary Render (HTML)

* Header: `Quiz summary`
* Overall stats: `Correct: X / N`
* Per-question breakdown (numbered):

  ```
  1) <b>{phrasal}</b>
     ✅ <b>{correct meaning}</b>
     (You chose: *{user choice}*)    # only if incorrect
  ```
* Buttons:

  * `🔁 Take quiz again` → re-sample a fresh Quiz session with the same limit and eligible pool (show “no eligible” if none).
  * `◀️ Back to menu`

### Settings (rename already done)

* Add field:

  * **Quiz questions per session** (`user_config.quiz_question_limit`, int 5–30, default 10)
    *How many multiple-choice questions to include in one Quiz session (review cards only).*
  * Validation: integer in \[5, 30]
* Settings list should show:

  * `• Quiz questions per session: 10`
* Provide a button `📝 Quiz questions per session` to open the input prompt (bold name, italic description, Back, validation).

## State & Data

### DB

* Extend `user_ui_state` to include a **transient quiz session** blob, e.g.:

  * `quiz_state_json` (nullable TEXT) storing:

    * `questions`: list of objects:

      * `card_id`
      * `phrasal`
      * `correct_meaning`
      * `options`: list of strings (length 2–4; usually 4)
      * `correct_index` (0–3)
      * `user_choice` (nullable int)
    * `current_q` (int index)
  * CRUD helpers to set/get/clear quiz state

### Building the Quiz

* Query eligible review cards for the user (distinct card\_ids).
* Sample up to `quiz_question_limit`.
* Build a **global pool of meanings** from all senses (excluding the correct one when sampling distractors). Use concise `meaning_en`.
* For each selected card:

  * Create 3 unique distractors (if possible).
  * Compose `options = [correct] + distractors`, then `random.shuffle`.
  * Store `correct_index` after shuffle.
* Persist `quiz_state_json`.

### Handlers / Routing

* New file: `srsbot/handlers/quiz.py`

  * `open_quiz(user_id)` — entry from Main Menu; builds session or shows “no eligible”.
  * `render_question(user_id)` — renders current question with inline options.
  * Callback `ui:quiz.answer:<qidx>:<optidx>`:

    * Ignore if `qidx != current_q` (stale), else record `user_choice`, increment `current_q`, and:

      * if more questions → `render_question(...)`
      * else → `render_summary(...)`
  * Callback `ui:quiz.again` → rebuild a fresh quiz session (same flow as start).
  * Callback `ui:quiz.back` → discard quiz session (clear state) and go back to Main Menu via `ui.show_screen`.
* Update `srsbot/handlers/menu.py` to include **📝 Quiz** button action.
* Ensure all navigation uses your **single-message** UI helper (`ui.show_screen`), editing in place; delete+send only if required.
* Do **not** alter SRS progress during Quiz.

### Keyboards

* `srsbot/keyboards.py`:

  * `kb_quiz_question()` → four option buttons `1️⃣ 2️⃣ 3️⃣ 4️⃣` + `◀️ Back`
  * `kb_quiz_summary()` → `🔁 Take quiz again`, `◀️ Back to menu`

### Formatters

* `srsbot/formatters.py`:

  * `format_quiz_question_html(phrasal, options: list[str]) -> str`
  * `format_quiz_summary_html(items: list[QuestionResult]) -> str`

    * Include overall correct/total.
    * For each item:

      * ✅ if `user_choice == correct_index`, otherwise ❌.
      * **Bold** correct meaning.
      * If incorrect, add `(You chose: *{user_choice_text}*)`.
  * Escape all content for HTML.

### Settings Integration

* `srsbot/handlers/settings.py`:

  * Add button “📝 Quiz questions per session” → input prompt (bold title, italic description, `Please enter a new value:`).
  * Validation: integer \[5, 30]; on invalid, show concise `❌ Invalid value...` and re-render the same input screen with Back.
  * On success, persist to `user_config.quiz_question_limit` and return to **Settings** list.

## Edge Cases

* If global meanings pool is too small to produce 3 distractors for some cards:

  * Use fewer distractors (min 1), but keep a valid MCQ; prefer at least 2 options.
  * Never include duplicate options; never include the correct meaning as a distractor.
* If the eligible review pool is empty:

  * Show “No review cards available for quiz today.” with `◀️ Back`.
* If user navigates Back mid-quiz:

  * Clear `quiz_state_json` and return to Main Menu.
* If callbacks arrive out of order (stale question index), ignore gracefully (reply with answerCallbackQuery alert like “This question is no longer active” and keep current screen).

## Tests (pytest)

* `tests/test_quiz_build.py`

  * Given a corpus of review cards and meanings, building a quiz:

    * samples at most `quiz_question_limit`,
    * each question has correct+3 (or fewer) distinct distractors,
    * options shuffled; `correct_index` aligns with content.
* `tests/test_quiz_flow.py`

  * Simulate answering N questions; verify per-question recording and summary formatting (✅/❌, bold correct, italic user choice if wrong).
* `tests/test_settings_quiz_limit.py`

  * Validate editing `quiz_question_limit` via Settings input (range \[5, 30], errors on invalid, success path updates value and returns to Settings).

## Acceptance Criteria

1. Main Menu includes **📝 Quiz**.
2. Quiz builds from **review-state** cards, up to **Settings → Quiz questions per session** (default 10), with 3 global distractors per question when available, shuffled.
3. Question UI uses **HTML** with bold phrasal and numbered options, plus inline option buttons and **◀️ Back**.
4. Summary shows total correct/total and per-question lines with ✅/❌, **bold** correct meaning, and *(You chose: …)* italic if wrong. Buttons: `🔁 Take quiz again`, `◀️ Back to menu`.
5. No SRS state changes due to Quiz.
6. Clean UI: navigation edits the single active message (or delete+send), no message spam.
7. Settings includes **Quiz questions per session** with friendly name, inline input prompt (bold title, italic description), validation, Back.
8. Edge cases (no eligible cards, limited distractors, stale callbacks) handled gracefully.

Keep code typed (mypy), formatted (ruff/black), with docstrings for new helpers, and update **README.md** (add a “Quiz” section describing usage, Settings, and behavior).
