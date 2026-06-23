from app.main import app
from app.seed import seed


def client():
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
