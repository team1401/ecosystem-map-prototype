from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

from app.db import ROOT, connect, public_clause
from app.demo import load_demo


def fetch_counts(conn):
    tables = ["entities", "events", "resources", "opportunities", "needs", "offers", "relationships", "submissions"]
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}


def ecosystem(conn):
    return conn.execute("SELECT * FROM ecosystems ORDER BY id LIMIT 1").fetchone()


def write_csv(path: Path, headers: list[str], rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row[h] for h in headers])


def build_report() -> str:
    with connect() as conn:
        eco = ecosystem(conn)
        counts = fetch_counts(conn)
        entities = conn.execute(
            f"SELECT name, type, location, description, website FROM entities e WHERE {public_clause('e')} ORDER BY type, name"
        ).fetchall()
        relationships = conn.execute(
            f"""SELECT s.name AS source_name, r.relationship_type, t.name AS target_name, r.description, r.confidence
                   FROM relationships r
                   JOIN entities s ON s.id = r.source_entity_id
                   LEFT JOIN entities t ON t.id = r.target_entity_id
                  WHERE {public_clause('r')}
                  ORDER BY s.name, r.relationship_type, t.name"""
        ).fetchall()
        pending = conn.execute("SELECT COUNT(*) AS count FROM submissions WHERE status='Pending Review'").fetchone()["count"]
    lines = [
        f"# {eco['name']} — Community Asset Discovery Report",
        "",
        f"Location: {eco['location'] or 'TBD'}",
        f"Theme: {eco['theme'] or 'TBD'}",
        "",
        "## Inventory Snapshot",
        "",
    ]
    for key in ["entities", "relationships", "submissions", "events", "resources", "opportunities", "needs", "offers"]:
        lines.append(f"- {key.title()}: {counts.get(key, 0)}")
    lines.extend([f"- Pending review submissions: {pending}", "", "## Published Assets", ""])
    for e in entities:
        website = f" — {e['website']}" if e["website"] else ""
        location = f" ({e['location']})" if e["location"] else ""
        lines.append(f"- **{e['name']}** — {e['type']}{location}{website}")
        if e["description"]:
            lines.append(f"  - {e['description']}")
    lines.extend(["", "## Relationship Map", ""])
    for r in relationships:
        lines.append(f"- **{r['source_name']}** → `{r['relationship_type']}` → **{r['target_name'] or 'Unresolved target'}** ({r['confidence']})")
        if r["description"]:
            lines.append(f"  - {r['description']}")
    lines.extend([
        "",
        "## Operator Next Actions",
        "",
        "- Review pending submissions and convert valid items into draft entities.",
        "- Publish only verified public assets.",
        "- Add evidence-backed relationships for each asset.",
        "- Export CSV/JSON after each curation pass.",
    ])
    return "\n".join(lines) + "\n"


def generate_packet(output_root: Path | None = None) -> Path:
    load_demo()
    output_root = output_root or (ROOT / "deliverables")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    packet = output_root / f"community-asset-discovery-{stamp}"
    packet.mkdir(parents=True, exist_ok=False)
    with connect() as conn:
        entity_rows = conn.execute(
            "SELECT id, name, type, description, location, website, tags, publication_status, visibility, source, confidence FROM entities ORDER BY name"
        ).fetchall()
        relationship_rows = conn.execute(
            """SELECT r.id, s.name AS source_name, r.relationship_type, t.name AS target_name,
                      r.description, r.evidence, r.confidence, r.publication_status, r.visibility
                   FROM relationships r
                   JOIN entities s ON s.id = r.source_entity_id
                   LEFT JOIN entities t ON t.id = r.target_entity_id
                  ORDER BY s.name, r.relationship_type, t.name"""
        ).fetchall()
        payload = {}
        for table in ["ecosystems", "entities", "relationships", "submissions", "events", "resources", "opportunities", "needs", "offers"]:
            payload[table] = [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]
    write_csv(packet / "entities.csv", ["id", "name", "type", "description", "location", "website", "tags", "publication_status", "visibility", "source", "confidence"], entity_rows)
    write_csv(packet / "relationships.csv", ["id", "source_name", "relationship_type", "target_name", "description", "evidence", "confidence", "publication_status", "visibility"], relationship_rows)
    (packet / "data.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (packet / "community-asset-discovery-report.md").write_text(build_report(), encoding="utf-8")
    (packet / "README.md").write_text(
        "# Community Asset Discovery Deliverable Packet\n\n"
        "Files:\n"
        "- `community-asset-discovery-report.md` — narrative inventory/report.\n"
        "- `entities.csv` — asset inventory.\n"
        "- `relationships.csv` — relationship edge list.\n"
        "- `data.json` — full working dataset.\n",
        encoding="utf-8",
    )
    shutil.make_archive(str(packet), "zip", packet)
    return packet


if __name__ == "__main__":
    packet = generate_packet()
    print(packet)
    print(f"{packet}.zip")
