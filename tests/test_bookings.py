import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.app import COOKIE, TTL, create_app

HEADERS = {'origin': 'http://localhost:3000', 'content-type': 'application/json'}


@pytest.fixture
def system(tmp_path):
    clock = [1_800_000_000.0]
    path = tmp_path / 'test.sqlite'
    app = create_app(path, now=lambda: clock[0])
    return app, clock, path


def client(app):
    c = TestClient(app, headers=HEADERS)
    assert c.post('/api/bootstrap').status_code == 200
    return c


def payload(c, index=0):
    return dict(first_name='Sample', last_name='Person', gender='unspecified',
                language='tr', mode='avatar', avatar='female',
                starts_at=c.get('/api/slots').json()[index]['starts_at'], adult_consent=True)


def test_cookie_is_http_only_and_no_model_claim(system):
    app, _, _ = system
    with TestClient(app, headers=HEADERS) as c:
        r = c.post('/api/bootstrap')
        cookie = r.headers['set-cookie'].lower()
        assert 'httponly' in cookie and 'samesite=strict' in cookie and 'max-age=86400' in cookie
        assert 'no-store' == r.headers['cache-control']
        health = c.get('/api/health').json()
        assert not health['fine_tuned'] and not health['chat_enabled']
        assert c.post('/api/chat', json={'message': 'sample'}).status_code == 403


def test_owner_isolation_and_cancel_releases_slot(system):
    app, _, _ = system
    a, b = client(app), client(app)
    data = payload(a)
    r = a.post('/api/bookings', json=data)
    assert r.status_code == 201
    booking = r.json()
    assert 'first_name' not in booking and 'owner_hash' not in booking
    assert len(a.get('/api/bookings').json()) == 1
    assert b.get('/api/bookings').json() == []
    assert b.delete('/api/bookings/' + booking['id']).status_code == 404
    assert b.post('/api/bookings', json=data).status_code == 409
    assert a.delete('/api/bookings/' + booking['id']).status_code == 200
    assert b.post('/api/bookings', json=data).status_code == 201


def test_simultaneous_booking_is_atomic(system):
    app, _, _ = system
    clients = [client(app), client(app)]
    data = payload(clients[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda c: c.post('/api/bookings', json=data).status_code, clients))
    assert sorted(statuses) == [201, 409]


@pytest.mark.parametrize('changes', [
    {'adult_consent': False}, {'first_name': '  '}, {'language': 'xx'},
    {'mode': 'video'}, {'avatar': 'unknown'}, {'first_name': 'x' * 61},
    {'starts_at': '2001-01-01T00:00:00Z'}, {'starts_at': '2026-09-09T15:00:00'},
    {'unexpected': 'private text'},
])
def test_validation_does_not_echo_personal_data(system, changes):
    c = client(system[0])
    data = payload(c) | changes
    r = c.post('/api/bookings', json=data)
    assert r.status_code == 422
    assert 'Sample' not in r.text and 'private text' not in r.text
    assert c.get('/api/bookings').json() == []


def test_untrusted_origin_and_large_payload_blocked(system):
    c = client(system[0])
    assert c.post('/api/bootstrap', headers={'origin': 'https://evil.example'}).status_code == 403
    assert c.post('/api/bookings', content='x' * 9000).status_code == 413


def test_expiry_removes_owner_and_booking(system):
    app, clock, path = system
    c = client(app)
    assert c.post('/api/bookings', json=payload(c)).status_code == 201
    old_cookie = c.cookies.get(COOKIE)
    clock[0] += TTL + 1
    assert c.get('/api/bookings').status_code == 401
    assert c.post('/api/bootstrap').status_code == 200
    assert c.cookies.get(COOKIE) != old_cookie
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT COUNT(*) FROM bookings').fetchone()[0] == 0


def test_max_three_active_bookings(system):
    c = client(system[0])
    for i in range(3):
        assert c.post('/api/bookings', json=payload(c, i)).status_code == 201
    assert c.post('/api/bookings', json=payload(c, 3)).status_code == 429


def test_unauthenticated_and_no_conversation_table(system):
    app, _, path = system
    c = TestClient(app, headers=HEADERS)
    assert c.get('/api/bookings').status_code == 401
    with sqlite3.connect(path) as con:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert tables == {'owners', 'bookings', 'admissions'}
