import app.main as main_module
from app.db import DB_PATH, connect
from app.demo import load_demo
from app.main import app
from app.package import generate_packet
from app.seed import seed


def client():
    if DB_PATH.exists():
        DB_PATH.unlink()
    seed()
    app.config.update(TESTING=True)
    return app.test_client()


def test_home_loads_entities():
    rv = client().get('/')
    assert rv.status_code == 200
    assert b'River City Independent Music' in rv.data
    assert b'Maya Rivera' in rv.data


def test_entity_profile_shows_relationships():
    rv = client().get('/entities/1')
    assert rv.status_code == 200
    assert b'Outgoing relationships' in rv.data
    assert b'The Lantern Room' in rv.data


def test_submission_enters_review_queue():
    c = client()
    rv = c.post('/submit', data={
        'submitter_name':'Tester',
        'submitter_email':'tester@example.org',
        'submission_type':'Asset submission',
        'name':'Test Venue',
        'asset_type':'Venue',
        'description':'A test venue',
    }, follow_redirects=True)
    assert rv.status_code == 200
    admin = c.get('/admin')
    assert b'Test Venue' in admin.data


def test_graph_loads():
    rv = client().get('/graph')
    assert rv.status_code == 200
    assert b'cytoscape' in rv.data


def test_admin_page_links_to_submission_detail():
    rv = client().get('/admin')
    assert rv.status_code == 200
    assert b'/admin/submissions/1' in rv.data
    assert b'Review submission #1' in rv.data


def test_submission_detail_page_renders_data():
    rv = client().get('/admin/submissions/1')
    assert rv.status_code == 200
    assert b'Demo Submitter' in rv.data
    assert b'Maya Rivera collaborated with Northbank Studio' in rv.data
    assert b'Save review update' in rv.data


def test_update_submission_status_and_notes():
    c = client()
    rv = c.post(
        '/admin/submissions/1/update',
        data={'status': 'Needs More Information', 'admin_notes': 'Ask for source URL'},
        follow_redirects=True,
    )
    assert rv.status_code == 200
    assert b'Status:</strong> Needs More Information' in rv.data
    assert b'Ask for source URL' in rv.data
    with connect() as conn:
        row = conn.execute('SELECT status, admin_notes, reviewed_at FROM submissions WHERE id=1').fetchone()
    assert row['status'] == 'Needs More Information'
    assert row['admin_notes'] == 'Ask for source URL'
    assert row['reviewed_at'] is not None


def test_duplicate_hint():
    c = client()
    c.post('/submit', data={
        'submitter_name': 'Tester',
        'submission_type': 'Asset submission',
        'name': 'Maya Rivera',
        'website': 'https://example.org/maya'
    })
    
    with connect() as conn:
        sub_id = conn.execute("SELECT id FROM submissions ORDER BY id DESC LIMIT 1").fetchone()[0]
        
    rv = c.get(f'/admin/submissions/{sub_id}')
    assert b'Possible Duplicates' in rv.data
    assert b'Maya Rivera' in rv.data
    assert b'High' in rv.data


def test_create_draft_entity():
    c = client()
    c.post('/submit', data={
        'submitter_name': 'Tester',
        'submission_type': 'Asset submission',
        'name': 'New Draft Entity Test',
        'asset_type': 'Venue',
    })
    
    with connect() as conn:
        sub_id = conn.execute("SELECT id FROM submissions ORDER BY id DESC LIMIT 1").fetchone()[0]
        
    rv = c.post(f'/admin/submissions/{sub_id}/create-draft-entity', follow_redirects=True)
    assert rv.status_code == 200
    
    with connect() as conn:
        sub = conn.execute("SELECT linked_record_kind, linked_record_id, admin_notes FROM submissions WHERE id=?", (sub_id,)).fetchone()
        assert sub['linked_record_kind'] == 'entity'
        assert sub['linked_record_id'] is not None
        assert 'Created draft entity' in sub['admin_notes']
        
        ent = conn.execute("SELECT publication_status, name FROM entities WHERE id=?", (sub['linked_record_id'],)).fetchone()
        assert ent['publication_status'] == 'Draft'
        assert ent['name'] == 'New Draft Entity Test'


def test_draft_entity_hidden():
    c = client()
    c.post('/submit', data={
        'submitter_name': 'Tester',
        'submission_type': 'Asset submission',
        'name': 'Secret Draft Entity',
    })
    with connect() as conn:
        sub_id = conn.execute("SELECT id FROM submissions ORDER BY id DESC LIMIT 1").fetchone()[0]
    c.post(f'/admin/submissions/{sub_id}/create-draft-entity')
    
    rv = c.get('/')
    assert b'Secret Draft Entity' not in rv.data


def test_missing_name_error():
    c = client()
    with connect() as conn:
        conn.execute("INSERT INTO submissions (ecosystem_id, submitter_name, submission_type, raw_data, status) VALUES (1, 'Tester', 'Asset submission', '{}', 'Pending Review')")
        sub_id = conn.execute("SELECT id FROM submissions ORDER BY id DESC LIMIT 1").fetchone()[0]
        conn.commit()
        
    rv = c.post(f'/admin/submissions/{sub_id}/create-draft-entity', follow_redirects=True)
    assert b'Missing name or invalid JSON' in rv.data
    
    with connect() as conn:
        sub = conn.execute("SELECT linked_record_kind FROM submissions WHERE id=?", (sub_id,)).fetchone()
        assert sub['linked_record_kind'] is None


def test_null_raw_fields_do_not_crash():
    c = client()
    with connect() as conn:
        conn.execute(
            "INSERT INTO submissions (ecosystem_id, submitter_name, submission_type, raw_data, status) VALUES (1, 'Tester', 'Asset submission', ?, 'Pending Review')",
            ('{"name": "Null Field Entity", "type": null, "description": null, "location": null, "website": null}',),
        )
        sub_id = conn.execute("SELECT id FROM submissions ORDER BY id DESC LIMIT 1").fetchone()[0]
        conn.commit()
    rv = c.post(f'/admin/submissions/{sub_id}/create-draft-entity', follow_redirects=True)
    assert rv.status_code == 200
    with connect() as conn:
        entity = conn.execute("SELECT name, type FROM entities WHERE name='Null Field Entity'").fetchone()
    assert entity['name'] == 'Null Field Entity'
    assert entity['type'] == 'Unknown'


def create_draft(c, name='Publish Me'):
    c.post('/submit', data={
        'submitter_name': 'Tester',
        'submission_type': 'Asset submission',
        'name': name,
        'asset_type': 'Venue',
        'description': 'Draft description',
    })
    with connect() as conn:
        sub_id = conn.execute("SELECT id FROM submissions ORDER BY id DESC LIMIT 1").fetchone()[0]
    c.post(f'/admin/submissions/{sub_id}/create-draft-entity')
    with connect() as conn:
        return conn.execute("SELECT linked_record_id FROM submissions WHERE id=?", (sub_id,)).fetchone()[0]


def test_admin_can_edit_and_publish_draft_entity():
    c = client()
    entity_id = create_draft(c)
    rv = c.get(f'/admin/entities/{entity_id}')
    assert rv.status_code == 200
    assert b'Publish publicly' in rv.data
    assert b'Publish Me' in rv.data

    c.post(f'/admin/entities/{entity_id}/update', data={
        'name': 'Published Pilot Venue',
        'type': 'Venue',
        'description': 'Updated before publishing',
        'location': 'River City',
        'website': 'https://pilot.example.org',
        'tags': 'pilot,venue',
        'publication_status': 'Draft',
        'visibility': 'Public',
    })
    assert b'Published Pilot Venue' not in c.get('/').data

    rv = c.post(f'/admin/entities/{entity_id}/publish', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Approved / Published' in rv.data
    public = c.get('/')
    assert b'Published Pilot Venue' in public.data


def test_relationship_creation_appears_on_graph():
    c = client()
    target_id = create_draft(c, 'Relationship Target')
    c.post(f'/admin/entities/{target_id}/publish')
    rv = c.post('/admin/relationships', data={
        'source_entity_id': '1',
        'target_entity_id': str(target_id),
        'relationship_type': 'supports',
        'description': 'Maya supports the pilot target',
        'evidence': 'Pilot interview',
        'confidence': 'Verified',
        'publication_status': 'Approved / Published',
        'visibility': 'Public',
    }, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Maya Rivera' in rv.data
    assert b'Relationship Target' in rv.data
    graph = c.get('/graph')
    assert b'supports' in graph.data
    assert b'Relationship Target' in graph.data
    public = c.get('/relationships')
    assert public.status_code == 200
    assert b'Maya supports the pilot target' in public.data
    assert b'Relationship Target' in public.data


def test_public_relationships_tab_uses_public_route():
    c = client()
    rv = c.get('/')
    assert rv.status_code == 200
    assert b'href="/relationships"' in rv.data
    assert b'href="/admin/relationships">Relationships' not in rv.data
    rels = c.get('/relationships')
    assert rels.status_code == 200
    assert b'Public relationship map' in rels.data
    assert b'Maya Rivera' in rels.data
    assert b'Northbank Studio' in rels.data


def test_exports_include_entities_and_json():
    c = client()
    csv_rv = c.get('/exports/entities.csv')
    assert csv_rv.status_code == 200
    assert b'id,name,type' in csv_rv.data
    assert b'Maya Rivera' in csv_rv.data
    rel_rv = c.get('/exports/relationships.csv')
    assert rel_rv.status_code == 200
    assert b'source_name,relationship_type,target_name' in rel_rv.data
    report_rv = c.get('/exports/report.md')
    assert report_rv.status_code == 200
    assert b'Community Asset Discovery Report' in report_rv.data
    assert b'## Relationship Map' in report_rv.data
    json_rv = c.get('/exports/data.json')
    assert json_rv.status_code == 200
    assert b'"entities"' in json_rv.data
    assert b'"relationships"' in json_rv.data


def test_bulk_import_creates_pending_submissions():
    c = client()
    rv = c.post('/admin/import', data={
        'submitter_name': 'Workshop Notes',
        'raw_text': 'Name: Eastside Arts Collective\nType: Organization\nLocation: East River\nDescription: Youth arts programming.\n\nName: Community Tool Library\nType: Resource\nDescription: Shared equipment.'
    }, follow_redirects=True)
    assert rv.status_code == 200
    assert b'Created 2 submissions' in rv.data
    with connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM submissions WHERE submitter_name='Workshop Notes'").fetchone()[0]
    assert count == 2
    admin = c.get('/admin')
    assert b'Eastside Arts Collective' in admin.data
    assert b'Community Tool Library' in admin.data


def test_demo_data_loads_idempotently():
    c = client()
    load_demo()
    load_demo()
    rv = c.get('/')
    assert b'Eastside Arts Collective' in rv.data
    assert b'Community Tool Library' in rv.data
    graph = c.get('/graph')
    assert b'supports' in graph.data


def test_pilot_page_removed():
    assert client().get('/pilot').status_code == 404


def test_generate_deliverable_packet(tmp_path):
    client()
    packet = generate_packet(tmp_path)
    assert (packet / 'entities.csv').exists()
    assert (packet / 'relationships.csv').exists()
    assert (packet / 'data.json').exists()
    report = packet / 'community-asset-discovery-report.md'
    assert report.exists()
    assert 'Community Asset Discovery Report' in report.read_text()
    assert packet.with_suffix('.zip').exists()


def test_links_respect_script_name_prefix():
    c = client()
    rv = c.get('/', environ_overrides={'SCRIPT_NAME': '/ecosystem-map'})
    assert rv.status_code == 200
    assert b'href="/ecosystem-map/graph"' in rv.data
    assert b'href="/ecosystem-map/relationships"' in rv.data
    assert b'href="/ecosystem-map/exports/report.md"' in rv.data


def test_public_read_only_hides_private_nav_links(monkeypatch):
    c = client()
    monkeypatch.setattr(main_module, 'PUBLIC_READ_ONLY', True)
    rv = c.get('/')
    assert b'href="/relationships"' in rv.data
    assert b'href="/submit"' not in rv.data
    assert b'href="/admin"' not in rv.data
    assert b'href="/admin/import"' not in rv.data
