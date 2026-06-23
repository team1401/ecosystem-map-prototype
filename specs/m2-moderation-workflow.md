# M2 Moderation Workflow Slice

## Repository
`/workspace` inside the agent container corresponds to the ecosystem mapping prototype repo.

## Goal
Improve the existing Flask/SQLite prototype's admin moderation workflow while preserving the lean MVP. Implement a bounded, tested slice.

## Current app
- Flask app: `app/main.py`
- SQLite schema/helpers: `app/db.py`
- Seed data: `app/seed.py`
- Templates: `app/templates/*.html`
- Tests: `tests/test_app.py`

## Required behavior

### 1. Submission detail/edit page
Add an admin detail page for one submission:
- Route: `GET /admin/submissions/<id>`
- Shows submitter, status, type, raw JSON/body, admin notes, created/reviewed timestamps.
- Provides forms to update status and admin notes.
- Provides a link back to `/admin`.

### 2. Admin queue links
On `/admin`, each submission card should link to its detail page.

### 3. Create draft entity from an asset submission
On the submission detail page, add a button/form to create a draft entity from a submission when possible.
- Route: `POST /admin/submissions/<id>/create-draft-entity`
- Parse `submissions.raw_data` as JSON.
- Use fields if present: `name`, `type`, `description`, `location`, `website`.
- Insert into `entities` with:
  - same `ecosystem_id`
  - `publication_status = 'Draft'`
  - `visibility = 'Public'`
  - `source = 'Submission #<id>'`
  - `confidence = 'Submitted'`
- Update submission linked fields:
  - `linked_record_kind = 'entity'`
  - `linked_record_id = <new entity id>`
  - append/update admin note indicating draft entity was created
- Do not publish directly.
- If required fields are missing, show a friendly error on the detail page, not a stack trace.

### 4. Duplicate hints
On the submission detail page, show possible duplicate entities based on raw submitted `name`, `website`, or `location`.
- Name duplicate: exact case-insensitive match should be high confidence.
- Website duplicate: exact URL match should be high confidence.
- Location alone should be weak signal; show only as low confidence and do not block creation.
- Keep implementation simple; no external libraries.

### 5. Correction/removal request support
Improve the submission form and admin rendering so correction/removal submissions are explicit:
- Submission type options must include `Correction` and `Removal request`.
- Admin detail should label those clearly.
- No destructive delete behavior. Requests only enter review.

### 6. Tests
Add/extend tests for:
- Admin queue links to detail page.
- Detail page renders pending submission.
- Creating a draft entity from a valid submission creates a Draft entity and links the submission.
- Duplicate hints appear for same-name submitted entity.
- Removal request submission enters review and does not delete anything.

## Constraints
- No authentication yet.
- No external side effects.
- No emails, publishing, APIs, or secrets.
- Keep public pages limited to Approved / Published + Public records.
- Keep code simple and readable.
- Run `uv run pytest -q` and ensure it passes.

## Expected final output
Return JSON-only summary per Zeroshot instructions, but make the actual code changes and tests in the repo.