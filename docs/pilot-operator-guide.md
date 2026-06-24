# Pilot Operator Guide

## Live pilot flow

1. Open `/pilot` for the status dashboard and workflow links.
2. Use `/admin/import` to paste workshop notes, interview notes, survey exports, or copied research snippets.
3. Review created submissions in `/admin`.
4. Open a submission detail page and use `Create Draft Entity`.
5. Open the linked admin entity page, clean fields, then `Publish publicly`.
6. Use `/admin/relationships` to connect entities with relationship types like `supports`, `hosts`, `funds`, `serves`, `needs`, and `offers`.
7. Show `/graph` for the public relationship map.
8. Export `/exports/entities.csv` or `/exports/data.json` for handoff/analysis.

## Human-in-the-loop guardrail

Nothing from import or submission appears publicly until an admin creates/edits a draft and explicitly publishes it. Draft entities remain hidden from public directory and graph pages.

## Suggested evening demo script

- Import two sample assets from notes.
- Review a submission and create a draft entity.
- Edit the draft entity's type/location/description.
- Publish the entity and confirm it appears in the directory.
- Create a relationship from Maya Rivera to the new entity.
- Open the graph and show the new node/edge.
- Download CSV/JSON.

## Current non-goals

- Authentication is not implemented; use Tailscale-only access for pilot safety.
- AI extraction is represented by structured import parsing; LLM extraction can be added behind the same pending-submission queue.
- No destructive delete paths are exposed.
