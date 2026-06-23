# Ecosystem Mapping & Community Asset Discovery Prototype

Runnable local MVP based on the proposal document.

## Features

- Ecosystems, entities, events, resources, opportunities, needs, offers, relationships, submissions.
- Public search and category browsing.
- Entity profile pages with relationship context.
- Submission form for community-contributed assets/relationships.
- Admin review queue with approve/reject actions.
- Basic relationship graph view.
- SQLite seed data for an independent-musician pilot.

## Run

```bash
uv sync --extra dev
uv run python -m app.seed
uv run flask --app app.main run --debug --port 5057
```

Open: http://127.0.0.1:5057

## Test

```bash
uv run pytest
```
