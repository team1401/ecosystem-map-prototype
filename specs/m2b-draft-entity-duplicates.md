# M2B Draft Entity and Duplicate Hints

Implement this moderation slice in the Flask prototype.

Current state:
- Admin submission detail exists at `/admin/submissions/<id>`.
- Admin can update status/admin_notes.
- Tests pass.

Requirements:
1. Add helper logic in `app/main.py` or `app/db.py` to parse `submissions.raw_data` JSON safely.
2. On `/admin/submissions/<id>`, show possible duplicate entity hints based on submitted JSON:
   - exact case-insensitive `name` match: high confidence
   - exact `website` match: high confidence
   - exact case-insensitive `location` match: low confidence
   - keep simple SQL/Python; no new dependencies
3. Add route `POST /admin/submissions/<int:submission_id>/create-draft-entity`.
4. For valid raw JSON with at least `name`, create a row in `entities` with:
   - same ecosystem_id
   - name/type/description/location/website from raw_data when available
   - publication_status = `Draft`
   - visibility = `Public`
   - source = `Submission #<id>`
   - confidence = `Submitted`
   - tags = empty string if missing
5. Update that submission:
   - linked_record_kind = `entity`
   - linked_record_id = new entity id
   - append/admin note indicating draft entity was created
   - reviewed_at = CURRENT_TIMESTAMP
6. Detail page should show a friendly error message if raw JSON is invalid or name is missing. Use query-string status/error message or simple template state; do not add Flask secret/session dependency unless necessary.
7. Do not publish directly. Draft entities should NOT appear on public directory pages because public_clause should continue requiring Approved / Published.
8. Add tests:
   - duplicate hint appears for a same-name pending submission
   - create draft entity from submission creates Draft entity and links submission
   - draft entity does not appear on `/`
   - missing-name submission shows friendly error and does not create entity
9. Run `uv run pytest -q`.

Constraints:
- No authentication yet.
- No external side effects.
- No deleting records.
- No new dependencies.
- Keep changes bounded and readable.

Return JSON only, but make the code changes.