from __future__ import annotations

import csv
import io
import json
from flask import Flask, Response, abort, redirect, render_template, request, url_for

from app.db import PUBLIC_STATUS, connect, init_db, public_clause
from app.seed import seed

app = Flask(__name__)


@app.before_request
def ensure_db() -> None:
    init_db()


def fetch_counts(conn):
    tables = ["entities", "events", "resources", "opportunities", "needs", "offers", "relationships", "submissions"]
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}


def ecosystem(conn):
    return conn.execute("SELECT * FROM ecosystems ORDER BY id LIMIT 1").fetchone()


def safe_parse_json(raw: str) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
        return {}
    except (json.JSONDecodeError, TypeError):
        return {}


def text_value(data: dict, key: str) -> str:
    value = data.get(key)
    if value is None:
        return ""
    return str(value).strip()


def parse_asset_notes(text: str) -> list[dict]:
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    assets: list[dict] = []
    for block in blocks:
        data = {"name": "", "type": "", "description": "", "location": "", "website": "", "suggested_relationship": ""}
        loose_lines = []
        for line in block.splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                norm = key.strip().lower().replace(" ", "_")
                if norm in {"name", "type", "description", "location", "website", "suggested_relationship"}:
                    data[norm] = value.strip()
                    continue
            loose_lines.append(line.strip())
        if not data["name"] and loose_lines:
            data["name"] = loose_lines[0]
            data["description"] = "\n".join(loose_lines[1:]).strip()
        elif loose_lines and not data["description"]:
            data["description"] = "\n".join(loose_lines).strip()
        if data["name"]:
            data["type"] = data["type"] or "Unknown"
            assets.append(data)
    return assets


@app.route("/")
def index():
    seed()
    q = request.args.get("q", "").strip()
    typ = request.args.get("type", "").strip()
    with connect() as conn:
        eco = ecosystem(conn)
        params = []
        where = [public_clause("e")]
        if q:
            like = f"%{q}%"
            where.append("(e.name LIKE ? OR e.description LIKE ? OR e.tags LIKE ? OR e.location LIKE ?)")
            params.extend([like, like, like, like])
        if typ:
            where.append("e.type = ?")
            params.append(typ)
        entities = conn.execute(
            f"""SELECT e.*, COUNT(r.id) AS relationship_count
                 FROM entities e
                 LEFT JOIN relationships r ON (r.source_entity_id = e.id OR r.target_entity_id = e.id) AND {public_clause('r')}
                 WHERE {' AND '.join(where)}
                 GROUP BY e.id
                 ORDER BY e.name""",
            params,
        ).fetchall()
        types = conn.execute(f"SELECT DISTINCT type FROM entities e WHERE {public_clause('e')} ORDER BY type").fetchall()
        counts = fetch_counts(conn)
    return render_template("index.html", ecosystem=eco, entities=entities, counts=counts, q=q, type=typ, types=types)


@app.route("/entities/<int:entity_id>")
def entity_detail(entity_id: int):
    with connect() as conn:
        entity = conn.execute(f"SELECT * FROM entities e WHERE id=? AND {public_clause('e')}", (entity_id,)).fetchone()
        if not entity:
            abort(404)
        outgoing = conn.execute(
            f"""SELECT r.*, target.name AS target_name, target.type AS target_type
                   FROM relationships r
                   LEFT JOIN entities target ON target.id = r.target_entity_id
                  WHERE r.source_entity_id=? AND {public_clause('r')}
                  ORDER BY r.relationship_type, target.name""",
            (entity_id,),
        ).fetchall()
        incoming = conn.execute(
            f"""SELECT r.*, source.name AS source_name, source.type AS source_type
                   FROM relationships r
                   JOIN entities source ON source.id = r.source_entity_id
                  WHERE r.target_entity_id=? AND {public_clause('r')}
                  ORDER BY r.relationship_type, source.name""",
            (entity_id,),
        ).fetchall()
        events = conn.execute(
            f"SELECT * FROM events ev WHERE ev.host_entity_id=? AND {public_clause('ev')} ORDER BY starts_at",
            (entity_id,),
        ).fetchall()
        resources = conn.execute(
            f"SELECT * FROM resources res WHERE res.provider_entity_id=? AND {public_clause('res')} ORDER BY name",
            (entity_id,),
        ).fetchall()
        needs = conn.execute(
            f"SELECT * FROM needs n WHERE n.requester_entity_id=? AND {public_clause('n')} ORDER BY urgency DESC",
            (entity_id,),
        ).fetchall()
        offers = conn.execute(
            f"SELECT * FROM offers o WHERE o.provider_entity_id=? AND {public_clause('o')} ORDER BY offer_type",
            (entity_id,),
        ).fetchall()
    return render_template("entity.html", entity=entity, outgoing=outgoing, incoming=incoming, events=events, resources=resources, needs=needs, offers=offers)


@app.route("/submit", methods=["GET", "POST"])
def submit():
    seed()
    if request.method == "POST":
        raw = {
            "name": request.form.get("name", "").strip(),
            "type": request.form.get("asset_type", "").strip(),
            "description": request.form.get("description", "").strip(),
            "location": request.form.get("location", "").strip(),
            "website": request.form.get("website", "").strip(),
            "suggested_relationship": request.form.get("suggested_relationship", "").strip(),
        }
        with connect() as conn:
            eco = ecosystem(conn)
            conn.execute(
                """INSERT INTO submissions(ecosystem_id, submitter_name, submitter_email, submission_type, raw_data, status)
                   VALUES (?, ?, ?, ?, ?, 'Pending Review')""",
                (eco["id"], request.form.get("submitter_name", "").strip(), request.form.get("submitter_email", "").strip(), request.form.get("submission_type", "Asset submission"), json.dumps(raw, indent=2)),
            )
            conn.commit()
        return redirect(url_for("thanks"))
    return render_template("submit.html")


@app.route("/thanks")
def thanks():
    return render_template("thanks.html")


@app.route("/admin")
def admin():
    seed()
    status = request.args.get("status", "Pending Review")
    with connect() as conn:
        submissions = conn.execute(
            "SELECT * FROM submissions WHERE status=? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
        counts = fetch_counts(conn)
    return render_template("admin.html", submissions=submissions, status=status, counts=counts)


@app.route("/pilot")
def pilot_dashboard():
    seed()
    with connect() as conn:
        counts = fetch_counts(conn)
        entity_statuses = conn.execute("SELECT publication_status, COUNT(*) AS count FROM entities GROUP BY publication_status").fetchall()
        submission_statuses = conn.execute("SELECT status, COUNT(*) AS count FROM submissions GROUP BY status").fetchall()
        latest_submissions = conn.execute("SELECT * FROM submissions ORDER BY created_at DESC LIMIT 5").fetchall()
    return render_template(
        "pilot.html",
        counts=counts,
        entity_statuses=entity_statuses,
        submission_statuses=submission_statuses,
        latest_submissions=latest_submissions,
    )


@app.route("/admin/import", methods=["GET", "POST"])
def admin_import():
    seed()
    created = []
    error = None
    if request.method == "POST":
        raw_text = request.form.get("raw_text", "")
        assets = parse_asset_notes(raw_text)
        if not assets:
            error = "No asset names found. Use 'Name: ...' blocks or one asset name per paragraph."
        else:
            with connect() as conn:
                eco = ecosystem(conn)
                for asset in assets:
                    cur = conn.execute(
                        """INSERT INTO submissions(ecosystem_id, submitter_name, submitter_email, submission_type, raw_data, status)
                           VALUES (?, ?, ?, 'Asset submission', ?, 'Pending Review')""",
                        (
                            eco["id"],
                            request.form.get("submitter_name", "Bulk Import").strip() or "Bulk Import",
                            request.form.get("submitter_email", "").strip(),
                            json.dumps(asset, indent=2),
                        ),
                    )
                    created.append(cur.lastrowid)
                conn.commit()
    return render_template("admin_import.html", created=created, error=error)


@app.route("/admin/submissions/<int:submission_id>")
def submission_detail(submission_id: int):
    seed()
    with connect() as conn:
        submission = conn.execute(
            "SELECT * FROM submissions WHERE id=?",
            (submission_id,),
        ).fetchone()
    if not submission:
        abort(404)
        
    error = request.args.get('error')
    duplicates = []
    
    parsed = safe_parse_json(submission["raw_data"])
    if parsed:
        name = text_value(parsed, "name")
        website = text_value(parsed, "website")
        location = text_value(parsed, "location")
        
        with connect() as conn:
            where_clauses = []
            params = []
            if name:
                where_clauses.append("name COLLATE NOCASE = ?")
                params.append(name)
            if website:
                where_clauses.append("website = ?")
                params.append(website)
            if location:
                where_clauses.append("location COLLATE NOCASE = ?")
                params.append(location)
                
            if where_clauses:
                query = f"SELECT * FROM entities WHERE {' OR '.join(where_clauses)}"
                potential_dupes = conn.execute(query, params).fetchall()
                
                for dupe in potential_dupes:
                    confidence = "Low"
                    if (name and dupe["name"] and name.lower() == dupe["name"].lower()) or \
                       (website and dupe["website"] and website == dupe["website"]):
                        confidence = "High"
                    
                    dupe_dict = dict(dupe)
                    dupe_dict["match_confidence"] = confidence
                    duplicates.append(dupe_dict)

    return render_template("submission_detail.html", submission=submission, duplicates=duplicates, error=error)


@app.post("/admin/submissions/<int:submission_id>/create-draft-entity")
def create_draft_entity(submission_id: int):
    with connect() as conn:
        submission = conn.execute(
            "SELECT * FROM submissions WHERE id=?",
            (submission_id,),
        ).fetchone()
    if not submission:
        abort(404)

    parsed = safe_parse_json(submission["raw_data"])
    name = text_value(parsed, "name")
    
    if not parsed or not name:
        return redirect(url_for("submission_detail", submission_id=submission_id, error="Missing name or invalid JSON"))
        
    with connect() as conn:
        # Create draft entity
        cur = conn.execute(
            """INSERT INTO entities (ecosystem_id, name, type, description, location, website, publication_status, visibility, source, confidence, tags)
               VALUES (?, ?, ?, ?, ?, ?, 'Draft', 'Public', ?, 'Submitted', '')""",
            (
                submission["ecosystem_id"],
                name,
                text_value(parsed, "type") or 'Unknown',
                text_value(parsed, "description") or None,
                text_value(parsed, "location") or None,
                text_value(parsed, "website") or None,
                f"Submission #{submission_id}"
            )
        )
        new_entity_id = cur.lastrowid
        
        # Update submission
        admin_notes = submission["admin_notes"] or ""
        admin_notes = (admin_notes + f"\nCreated draft entity #{new_entity_id}.").strip()
        
        conn.execute(
            """UPDATE submissions 
               SET linked_record_kind = 'entity', 
                   linked_record_id = ?, 
                   admin_notes = ?, 
                   reviewed_at = CURRENT_TIMESTAMP 
               WHERE id = ?""",
            (new_entity_id, admin_notes, submission_id)
        )
        conn.commit()

    return redirect(url_for("submission_detail", submission_id=submission_id))


@app.post("/admin/submissions/<int:submission_id>/update")
def update_submission(submission_id: int):
    new_status = request.form.get("status", "Pending Review")
    allowed_statuses = {
        "Pending Review",
        "Approved / Published",
        "Rejected",
        "Needs More Information",
        "Archived",
        "Private / Admin Only",
    }
    if new_status not in allowed_statuses:
        abort(400)
    notes = request.form.get("admin_notes", "")
    with connect() as conn:
        cur = conn.execute(
            "UPDATE submissions SET status=?, admin_notes=?, reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_status, notes, submission_id),
        )
        conn.commit()
    if cur.rowcount == 0:
        abort(404)
    return redirect(url_for("submission_detail", submission_id=submission_id))


@app.post("/admin/submissions/<int:submission_id>/<action>")
def review_submission(submission_id: int, action: str):
    if action not in {"approve", "reject", "needs-info"}:
        abort(400)
    new_status = {"approve": "Approved / Published", "reject": "Rejected", "needs-info": "Needs More Information"}[action]
    notes = request.form.get("admin_notes", "")
    with connect() as conn:
        conn.execute(
            "UPDATE submissions SET status=?, admin_notes=?, reviewed_at=CURRENT_TIMESTAMP WHERE id=?",
            (new_status, notes, submission_id),
        )
        conn.commit()
    return redirect(url_for("admin"))


@app.route("/admin/entities/<int:entity_id>")
def admin_entity(entity_id: int):
    with connect() as conn:
        entity = conn.execute("SELECT * FROM entities WHERE id=?", (entity_id,)).fetchone()
    if not entity:
        abort(404)
    return render_template("admin_entity.html", entity=entity)


@app.post("/admin/entities/<int:entity_id>/update")
def update_entity(entity_id: int):
    fields = {
        "name": request.form.get("name", "").strip(),
        "type": request.form.get("type", "").strip() or "Unknown",
        "description": request.form.get("description", "").strip(),
        "location": request.form.get("location", "").strip(),
        "website": request.form.get("website", "").strip(),
        "tags": request.form.get("tags", "").strip(),
        "publication_status": request.form.get("publication_status", "Draft").strip(),
        "visibility": request.form.get("visibility", "Public").strip(),
    }
    if not fields["name"]:
        return redirect(url_for("admin_entity", entity_id=entity_id, error="Name is required"))
    if fields["publication_status"] not in {"Draft", PUBLIC_STATUS, "Archived", "Rejected"}:
        abort(400)
    if fields["visibility"] not in {"Public", "Private / Admin Only"}:
        abort(400)
    with connect() as conn:
        cur = conn.execute(
            """UPDATE entities
                  SET name=?, type=?, description=?, location=?, website=?, tags=?,
                      publication_status=?, visibility=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?""",
            (
                fields["name"],
                fields["type"],
                fields["description"] or None,
                fields["location"] or None,
                fields["website"] or None,
                fields["tags"],
                fields["publication_status"],
                fields["visibility"],
                entity_id,
            ),
        )
        conn.commit()
    if cur.rowcount == 0:
        abort(404)
    return redirect(url_for("admin_entity", entity_id=entity_id))


@app.post("/admin/entities/<int:entity_id>/publish")
def publish_entity(entity_id: int):
    with connect() as conn:
        cur = conn.execute(
            "UPDATE entities SET publication_status=?, visibility='Public', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (PUBLIC_STATUS, entity_id),
        )
        conn.commit()
    if cur.rowcount == 0:
        abort(404)
    return redirect(url_for("admin_entity", entity_id=entity_id))


@app.post("/admin/entities/<int:entity_id>/archive")
def archive_entity(entity_id: int):
    with connect() as conn:
        cur = conn.execute(
            "UPDATE entities SET publication_status='Archived', updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (entity_id,),
        )
        conn.commit()
    if cur.rowcount == 0:
        abort(404)
    return redirect(url_for("admin_entity", entity_id=entity_id))


@app.route("/admin/relationships", methods=["GET", "POST"])
def admin_relationships():
    seed()
    error = None
    with connect() as conn:
        eco = ecosystem(conn)
        if request.method == "POST":
            source_id = request.form.get("source_entity_id", "").strip()
            target_id = request.form.get("target_entity_id", "").strip()
            rel_type = request.form.get("relationship_type", "").strip()
            if not source_id or not target_id or not rel_type:
                error = "Source, target, and relationship type are required."
            elif source_id == target_id:
                error = "Source and target must be different entities."
            else:
                source = conn.execute("SELECT id FROM entities WHERE id=?", (source_id,)).fetchone()
                target = conn.execute("SELECT id FROM entities WHERE id=?", (target_id,)).fetchone()
                if not source or not target:
                    error = "Source or target entity not found."
                else:
                    conn.execute(
                        """INSERT INTO relationships(
                               ecosystem_id, source_entity_id, target_entity_id, relationship_type,
                               target_kind, description, evidence, confidence, publication_status, visibility
                           ) VALUES (?, ?, ?, ?, 'entity', ?, ?, ?, ?, ?)""",
                        (
                            eco["id"],
                            int(source_id),
                            int(target_id),
                            rel_type,
                            request.form.get("description", "").strip() or None,
                            request.form.get("evidence", "").strip() or None,
                            request.form.get("confidence", "Suggested"),
                            request.form.get("publication_status", "Draft"),
                            request.form.get("visibility", "Public"),
                        ),
                    )
                    conn.commit()
                    return redirect(url_for("admin_relationships"))
        entities = conn.execute("SELECT id, name, type, publication_status FROM entities ORDER BY name").fetchall()
        relationships = conn.execute(
            """SELECT r.*, s.name AS source_name, t.name AS target_name
                   FROM relationships r
                   JOIN entities s ON s.id = r.source_entity_id
                   LEFT JOIN entities t ON t.id = r.target_entity_id
                  ORDER BY r.created_at DESC, r.id DESC"""
        ).fetchall()
    return render_template("admin_relationships.html", entities=entities, relationships=relationships, error=error)


@app.route("/exports/entities.csv")
def export_entities_csv():
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, name, type, description, location, website, tags, publication_status, visibility, source, confidence FROM entities ORDER BY name"
        ).fetchall()
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "name", "type", "description", "location", "website", "tags", "publication_status", "visibility", "source", "confidence"])
    for row in rows:
        writer.writerow([row[k] for k in row.keys()])
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=entities.csv"})


@app.route("/exports/data.json")
def export_data_json():
    payload = {}
    with connect() as conn:
        for table in ["ecosystems", "entities", "relationships", "submissions", "events", "resources", "opportunities", "needs", "offers"]:
            payload[table] = [dict(row) for row in conn.execute(f"SELECT * FROM {table}").fetchall()]
    return Response(json.dumps(payload, indent=2), mimetype="application/json")


@app.route("/graph")
def graph():
    seed()
    with connect() as conn:
        entities = conn.execute(f"SELECT id, name, type FROM entities e WHERE {public_clause('e')} ORDER BY name").fetchall()
        relationships = conn.execute(
            f"""SELECT r.*, s.name AS source_name, t.name AS target_name
                   FROM relationships r
                   JOIN entities s ON s.id = r.source_entity_id
                   JOIN entities t ON t.id = r.target_entity_id
                  WHERE {public_clause('r')}
                  ORDER BY r.relationship_type"""
        ).fetchall()
    nodes = [{"data": {"id": f"e{e['id']}", "label": e["name"], "type": e["type"]}} for e in entities]
    edges = [{"data": {"id": f"r{r['id']}", "source": f"e{r['source_entity_id']}", "target": f"e{r['target_entity_id']}", "label": r["relationship_type"], "confidence": r["confidence"]}} for r in relationships]
    return render_template("graph.html", elements=json.dumps(nodes + edges), entities=entities, relationships=relationships)


@app.route("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    seed()
    app.run(debug=True, port=5057)
