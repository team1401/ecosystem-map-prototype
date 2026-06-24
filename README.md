# Ecosystem Mapping & Community Asset Discovery Prototype

Runnable community asset discovery workflow based on the proposal document.

## Current features

- Public asset directory with search/type filtering.
- Public entity profile pages with relationship context.
- Public Cytoscape relationship graph.
- Public submission form.
- Admin review queue.
- Submission detail pages with duplicate hints.
- One-click draft entity creation from submissions.
- Admin entity edit/publish/archive workflow.
- Relationship creation/review workflow.
- Bulk import of structured field notes into pending submissions.
- CSV exports for entities and relationships.
- JSON export for the full working dataset.
- Markdown report export for shareable project handoff.
- SQLite seed/demo data for an independent-musician ecosystem.

## Run

```bash
uv sync --extra dev
uv run python -m app.seed
uv run python -m app.demo
uv run flask --app app.main run --debug --port 5057
```

Open locally: http://127.0.0.1:5057

If Tailscale Serve is active, open: https://helix.tail4532cc.ts.net:5057/

## Operator workflow

```text
/admin/import              paste field notes into pending submissions
/admin                     review queue
/admin/submissions/<id>    review detail, duplicate hints, create draft entity
/admin/entities/<id>       edit/publish/archive entity
/admin/relationships       create evidence-backed relationships
/graph                     public relationship map
```

Operator guide:

```text
docs/operator-guide.md
```

## Export deliverables

```text
/exports/entities.csv
/exports/relationships.csv
/exports/data.json
/exports/report.md
```

## Test

```bash
uv run pytest
```
