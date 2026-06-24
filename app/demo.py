from __future__ import annotations

from app.db import PUBLIC_STATUS, PUBLIC_VISIBILITY, connect, init_db
from app.seed import seed


def upsert_entity(conn, ecosystem_id: int, name: str, type_: str, description: str, location: str, website: str | None = None) -> int:
    row = conn.execute("SELECT id FROM entities WHERE name=?", (name,)).fetchone()
    if row:
        conn.execute(
            """UPDATE entities SET type=?, description=?, location=?, website=?, publication_status=?, visibility=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
            (type_, description, location, website, PUBLIC_STATUS, PUBLIC_VISIBILITY, row["id"]),
        )
        return row["id"]
    cur = conn.execute(
        """INSERT INTO entities(ecosystem_id, name, type, description, location, website, tags, publication_status, visibility, source, confidence)
           VALUES (?, ?, ?, ?, ?, ?, '', ?, ?, 'Demo pilot data', 'Verified')""",
        (ecosystem_id, name, type_, description, location, website, PUBLIC_STATUS, PUBLIC_VISIBILITY),
    )
    return cur.lastrowid


def ensure_relationship(conn, ecosystem_id: int, source_id: int, target_id: int, relationship_type: str, description: str) -> None:
    exists = conn.execute(
        "SELECT id FROM relationships WHERE source_entity_id=? AND target_entity_id=? AND relationship_type=?",
        (source_id, target_id, relationship_type),
    ).fetchone()
    if exists:
        conn.execute(
            "UPDATE relationships SET description=?, publication_status=?, visibility=?, confidence='Verified' WHERE id=?",
            (description, PUBLIC_STATUS, PUBLIC_VISIBILITY, exists["id"]),
        )
        return
    conn.execute(
        """INSERT INTO relationships(ecosystem_id, source_entity_id, target_entity_id, relationship_type, description, evidence, confidence, publication_status, visibility)
           VALUES (?, ?, ?, ?, ?, 'Demo pilot relationship', 'Verified', ?, ?)""",
        (ecosystem_id, source_id, target_id, relationship_type, description, PUBLIC_STATUS, PUBLIC_VISIBILITY),
    )


def load_demo() -> None:
    init_db()
    seed()
    with connect() as conn:
        eco = conn.execute("SELECT id FROM ecosystems ORDER BY id LIMIT 1").fetchone()["id"]
        eastside = upsert_entity(conn, eco, "Eastside Arts Collective", "Organization", "Youth arts collective with rehearsal, mural, and event programming.", "East River District", "https://example.org/eastside")
        tools = upsert_entity(conn, eco, "Community Tool Library", "Resource", "Shared equipment library for events, installations, and neighborhood projects.", "Warehouse Row", None)
        maker = upsert_entity(conn, eco, "Northbank Maker Space", "Workspace", "Fabrication and repair workspace with mentorship nights.", "Northbank", "https://example.org/makers")
        maya = conn.execute("SELECT id FROM entities WHERE name='Maya Rivera'").fetchone()["id"]
        ensure_relationship(conn, eco, maya, eastside, "supports", "Maya mentors youth performers and helps coordinate showcases.")
        ensure_relationship(conn, eco, eastside, tools, "uses", "The collective borrows equipment for pop-up performances.")
        ensure_relationship(conn, eco, maker, tools, "supports", "The maker space repairs and maintains shared equipment.")
        conn.commit()


if __name__ == "__main__":
    load_demo()
    print("Demo pilot data loaded")
