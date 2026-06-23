from __future__ import annotations

import json
from flask import Flask, abort, redirect, render_template, request, url_for

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
    return render_template("submission_detail.html", submission=submission)


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
