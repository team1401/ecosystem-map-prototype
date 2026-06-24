# Ecosystem Mapping & Community Asset Discovery Prototype

Runnable pilot based on the proposal document.

## Current pilot features

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
- CSV and JSON exports.
- SQLite seed data for an independent-musician ecosystem pilot.

## Run

```bash
uv sync --extra dev
uv run python -m app.seed
uv run flask --app app.main run --debug --port 5057
```

Open locally: http://127.0.0.1:5057

If Tailscale Serve is active, open: https://helix.tail4532cc.ts.net:5057/

## Pilot dashboard

Start here:

```text
/pilot
```

Operator guide:

```text
docs/pilot-operator-guide.md
```

## Export

```text
/exports/entities.csv
/exports/data.json
```

## Test

```bash
uv run pytest
```
