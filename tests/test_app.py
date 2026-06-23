from app.db import DB_PATH, connect
from app.main import app
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
