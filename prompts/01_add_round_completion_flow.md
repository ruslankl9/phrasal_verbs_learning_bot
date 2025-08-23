**TASK: Add “Daily Round Completion” flow with ‘Repeat round’ / ‘Finish session’ buttons**

You previously generated a Telegram SRS bot (Python 3.11, aiogram v3, SQLite, session-based Leitner). Now modify it to support **daily rounds**:

## Goal

* A **daily deck** is built once per session (learning due → reviews due → new).
* When the **round** (i.e., the current pass through that deck) is fully consumed, the bot shows a completion message with **two inline buttons**:

  * **Repeat round** — re-run a new round **for the same day**, built from items that are still due/learning today.
  * **Finish session** — close the session; show a short summary (counts) and a hint about tomorrow.

This is **in addition to** the existing logic (Leitner boxes, due dates, daily caps, adaptive new target, overload rebalancing).

## Functional Requirements

### 1) Daily Round Semantics

* **Round** = a finite queue created at the start of `/today` or when the user taps **Repeat round**.
* The round is a **snapshot** of the daily deck at that moment:

  * Priority: `learning due` → `review due (<= today_end)` → `new` (respect daily\_new\_target & review\_limit\_per\_day).
* During a round, **Again** requeues the card **within the same round** (after `k` other cards, as before).
* **Good** applies normal state changes (graduation to review Box 1, box++ with jitter, etc.). If after **Good** the card’s `due_at` moves **after today**, it **must not** appear in subsequent rounds today.
* A round **ends** when the queue becomes empty (no more cards in the current snapshot).

### 2) End-of-Round UI

* When the last card of the current round is processed, send a **completion message**:

  ```
  ✅ Round complete!
  Done this round: X answers (Good: G, Again: A).
  Remaining today: L learning • R reviews due • N new available
  ```
* Add **two inline buttons**:

  * **Repeat round** (`callback_data="round:repeat"`)
  * **Finish session** (`callback_data="round:finish"`)
* Tapping **Repeat round**:

  * Recompute the **next round** for **today** using the same daily rules:

    * include `learning` still pending,
    * include `review` with `due_at <= today_end` subject to `review_limit_per_day` minus what was already served today,
    * include **remaining** `new` up to the user’s **remaining daily\_new\_target** for today, honoring tag filters and `sense_uid` rule.
  * If the recomputed deck is empty, show: “Nothing left for today 🎉”.
* Tapping **Finish session**:

  * End the session; send a final summary:

    ```
    🎯 Session finished.
    Today: Good G / Again A • New learned: U • Reviews done: V
    See you tomorrow at <push_time>!
    ```
  * Do **not** schedule anything extra; normal notification logic remains.

### 3) Tracking Per-Day State

Add minimal per-day/session state (per user) to ensure correct round behavior:

* New table `user_day_state` (or reuse a stats/state table) with:

  * `user_id`
  * `session_date` (DATE, local day)
  * `round_index` (INTEGER, starts at 1 each day)
  * `served_review_count` (INTEGER) — reviews shown today toward `review_limit_per_day`
  * `shown_new_today` (INTEGER) — new cards already introduced today toward daily\_new\_target
  * `good_today`, `again_today` (INTEGER) — counters for summaries
  * `round_card_ids_json` (TEXT) — snapshot list of card ids for the active round (for traceability/debug)
* Reset/rollover this state on **first** `/today` call of a new local day.
* Increment `round_index` after each **Repeat round**.

### 4) Queue/Content Logic Changes

* Refactor `queue.build_daily_queue(...)` into two levels:

  * `queue.compute_daily_candidates(user, today)` → returns three lists `(learning_due, reviews_due_limited, new_candidates_remaining_for_today)`.
  * `queue.build_round_queue(user, today, state)` → creates a **snapshot** list for the round using those candidates and remaining daily caps stored in `user_day_state`.
* On **Again/Good**, keep existing behavior; **requeue within the current round** if the card is still eligible for this round. If the per-round queue is empty after processing, trigger the **End-of-Round UI**.

### 5) Caps & Remainders

* Respect `review_limit_per_day`: if there are more due reviews than remaining capacity, include only up to `remaining_capacity = review_limit_per_day - served_review_count`.
* Respect `daily_new_target`: include only up to `remaining_new = daily_new_target - shown_new_today`.
* On **Repeat round**, recompute using the **remaining** capacities. If both remaining capacities are zero and there is no `learning_due`, the round should be empty → show “Nothing left for today 🎉”.

### 6) Handlers & Keyboards

* Update `handlers/today.py` to:

  * Initialize/reset `user_day_state` at session start (new local date).
  * Start a **round** by calling `build_round_queue(...)`, store the snapshot in `user_day_state.round_card_ids_json`, and begin serving cards.
  * Detect **round end** and render the completion message with the two buttons.
  * Implement callbacks:

    * `round:repeat` → start a **new** round (increment `round_index`) using remaining capacities.
    * `round:finish` → finalize session; send summary + optional hint about `/stats` or `/config`.
* Update `keyboards.py` to include a small helper that returns the “Repeat / Finish” inline keyboard.

### 7) Persistence & Counters

* Increment `served_review_count` whenever a **review** card is **shown** (count unique shows per round or total shows? Choose **unique per day**: count only the first time a review card is served today; repeated Again on the same card within the round doesn’t count against the daily review cap).
* Increment `shown_new_today` when a **new** card is **first introduced** today (not on repeats).
* Maintain `good_today` / `again_today` totals based on user taps.

### 8) Edge Cases

* If the user taps **Repeat round** but nothing qualifies (no learning due, no remaining reviews capacity, no new left) → show “Nothing left for today 🎉” and keep **Finish session** as a button.
* If user leaves mid-round and comes back later the same day with `/today`, resume the current round from stored snapshot/position. If snapshot can’t be resumed cleanly, recompute a fresh round from remaining capacities.
* Cards that moved to the future (after **Good**) must not be considered for subsequent rounds today.
* If the user changes `daily_new_target` or `review_limit_per_day` mid-day via `/config`, recompute remaining capacities accordingly when starting the next round.

## Code Changes (by file)

1. **`srsbot/db.py`**

   * Migration: add `user_day_state` table:

     ```sql
     CREATE TABLE IF NOT EXISTS user_day_state (
       user_id INTEGER NOT NULL,
       session_date TEXT NOT NULL,
       round_index INTEGER NOT NULL DEFAULT 1,
       served_review_count INTEGER NOT NULL DEFAULT 0,
       shown_new_today INTEGER NOT NULL DEFAULT 0,
       good_today INTEGER NOT NULL DEFAULT 0,
       again_today INTEGER NOT NULL DEFAULT 0,
       round_card_ids_json TEXT,
       PRIMARY KEY (user_id, session_date)
     );
     CREATE INDEX IF NOT EXISTS ix_user_day_state_user_date ON user_day_state(user_id, session_date);
     ```
   * Helpers: `get_day_state(user_id, date)`, `init_or_get_day_state(...)`, `update_day_state(...)`, `increment_counters(...)`.

2. **`srsbot/queue.py`**

   * Add:

     * `compute_daily_candidates(user, today, state) -> (learning_due, reviews_due_limited, new_candidates_remaining)`
     * `build_round_queue(user, today, state) -> list[Card]`
     * Ensure **unique-per-day** accounting: when adding a review card for the first time today, increment `served_review_count`. When introducing a new card for the first time today, increment `shown_new_today`.
   * Keep intra-round requeue after Again (`after_k = user_config.intra_spacing_k`).

3. **`srsbot/handlers/today.py`**

   * On `/today`:

     * Resolve local `today` date.
     * `state = init_or_get_day_state(user_id, today)`. If `session_date` != today, reset all day counters and `round_index=1`.
     * If no active snapshot or snapshot exhausted, call `build_round_queue(...)`. If empty → message “Nothing left for today 🎉”.
     * Serve the first card.
   * On answer callbacks (**Again/Good**):

     * Apply SRS update (existing logic).
     * If card still eligible this round, requeue within the round; else remove from current snapshot.
     * If snapshot empty → render **End-of-Round UI** (with counts and “remaining today” computed from candidates and remaining capacities).
   * New callbacks:

     * `round:repeat`: increment `round_index`, recompute with `build_round_queue(...)`. If empty → show “Nothing left for today 🎉”; include a **Finish session** button.
     * `round:finish`: finalize; show session summary; suggest `/stats` or when the next push is.

4. **`srsbot/keyboards.py`**

   * Add:

     ```python
     def round_end_keyboard():
         return InlineKeyboardMarkup(
             inline_keyboard=[
                 [InlineKeyboardButton(text="🔁 Repeat round", callback_data="round:repeat"),
                  InlineKeyboardButton(text="✅ Finish session", callback_data="round:finish")]
             ]
         )
     ```
   * Use existing **Again/Good** keyboard for cards.

5. **`srsbot/formatters.py`**

   * Add helpers to render round completion and final session summary messages:

     * `format_round_complete(good, again, remaining_learning, remaining_reviews, remaining_new)`
     * `format_session_finished(good_total, again_total, learned_today, reviews_done)`

6. **`srsbot/content.py`**

   * Ensure “new candidates” respect remaining `daily_new_target - shown_new_today` and `sense_uid` rules.
   * Exclude cards whose `due_at` is after today.

7. **`README.md`**

   * Document “Daily Rounds”: definition, End-of-Round UI, Repeat vs Finish, day caps, and how the bot decides when “today is done”.

## Tests (pytest)

Add/extend:

* `test_queue.py`

  * Builds a round with learning/reviews/new respecting **remaining** capacities.
  * After exhausting the snapshot, round is empty → triggers round-end.
* `test_rounds.py` (new)

  * End-of-round summary is shown.
  * **Repeat round** recomputes using remaining capacities; cards scheduled to the future are excluded; learning still appears.
  * **Finish session** sends final summary and stops serving cards for today.
* `test_daily_caps.py`

  * `served_review_count` increments on first serve per review card per day; **Again** repeats of the same card within the round do not increment it.
  * `shown_new_today` increments only when a new card is first introduced today.

## Acceptance Criteria

* At the exact moment the current round queue becomes empty, the bot **always** sends the round completion message with the two buttons.
* **Repeat round** starts a new round using only what remains for **today** (learning due, reviews under remaining cap, new under remaining new cap).
* **Finish session** ends the day’s interaction cleanly with a summary; `/today` later the same day should re-open a new round only if something remains (e.g., user changed caps or new content became available).
* No regression of SRS logic (graduation, box increments, jitter, tag filters, `sense_uid` rule).

Keep code typed, documented, and consistent with the existing architecture.
