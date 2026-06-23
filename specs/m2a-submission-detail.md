# M2A Submission Detail Slice

Implement only this first moderation slice in the Flask prototype.

Files likely affected:
- app/main.py
- app/templates/admin.html
- app/templates/submission_detail.html
- tests/test_app.py

Requirements:
1. Add route `GET /admin/submissions/<int:submission_id>`.
2. Page shows submission id, type, status, submitter, raw_data, admin_notes, created_at, reviewed_at, linked_record_kind, linked_record_id.
3. Page has a form to update `status` and `admin_notes`.
4. Add route `POST /admin/submissions/<int:submission_id>/update` to update status/admin_notes and set reviewed_at=CURRENT_TIMESTAMP.
5. `/admin` submission cards must link to the detail page.
6. Keep existing approve/reject/needs-info routes working.
7. Add tests:
   - `/admin` contains link to `/admin/submissions/1`
   - detail page renders `Demo Submitter` and raw submission text
   - update route changes status to `Needs More Information`
8. Run `uv run pytest -q`.

Constraints:
- No auth yet.
- No external side effects.
- No deleting records.
- Keep public pages restricted to approved public records.

Return JSON only, but make the code changes.