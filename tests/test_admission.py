import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier

import pytest
from backend.app import COOKIE, create_app
from backend.admission import LEASE_SECONDS, SESSION_SECONDS
from test_bookings import client, payload, system


def booking(c, scheduled=False):
    data = payload(c)
    if not scheduled:
        data['starts_at'] = None
    result = c.post('/api/bookings', json=data)
    assert result.status_code == 201, result.text
    return result.json()


def join(c, b):
    return c.post('/api/admission/join', json={'booking_id': b['id']})


def status(c):
    result = c.post('/api/admission/status')
    assert result.status_code == 200, result.text
    return result.json()


def leave(c, b):
    return c.post('/api/admission/leave', json={'booking_id': b['id']})


def test_immediate_entry_fifo_and_model_gate(system):
    app, _, _ = system
    a, b, c = [client(app) for _ in range(3)]
    ba, bb, bc = [booking(x) for x in (a, b, c)]
    assert ba['starts_at'] == bb['starts_at'] == bc['starts_at']
    assert join(a, ba).json()['state'] == 'active'
    rb = join(b, bb).json()
    rc = join(c, bc).json()
    assert (rb['state'], rb['people_ahead'], rb['queue_position']) == ('waiting', 1, 1)
    assert (rc['people_ahead'], rc['queue_position']) == (2, 2)
    assert b.post('/api/chat').status_code == 403
    assert a.post('/api/chat').status_code == 503
    assert leave(a, ba).status_code == 200
    assert status(b)['state'] == 'active'
    assert status(c)['people_ahead'] == 1
    assert join(a, ba).status_code == 410
    assert a.get('/api/bookings').json() == []
    assert leave(b, bb).status_code == 200
    assert status(c)['state'] == 'active'


@pytest.mark.parametrize('capacity', [1, 2])
def test_concurrent_admission_across_app_instances(tmp_path, capacity):
    clock = [1_800_000_000.0]
    path = tmp_path/'shared.sqlite'
    apps = [create_app(path, now=lambda: clock[0], capacity=capacity) for _ in range(2)]
    clients = [client(apps[i % 2]) for i in range(8)]
    bookings = [booking(c) for c in clients]
    barrier = Barrier(8)
    def enter(pair):
        c, b = pair
        barrier.wait()
        return join(c, b).status_code
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(enter, zip(clients, bookings))) == [200]*8
    results = [status(c) for c in clients]
    assert sum(r['state'] == 'active' for r in results) == capacity
    assert sorted(r['queue_position'] for r in results if r['state'] == 'waiting') == list(range(1, 9-capacity))
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM admissions WHERE state='active'").fetchone()[0] == capacity


def test_owner_isolation_idempotency_and_stale_leave(system):
    a, b = client(system[0]), client(system[0])
    ba, bb = booking(a), booking(b)
    assert join(b, ba).status_code == 404
    first = join(a, ba).json()
    assert join(a, ba).json() == first
    ba2 = booking(a)
    assert join(a, ba2).status_code == 409
    assert leave(b, ba).json()['state'] == 'idle'
    assert status(a)['state'] == 'active'
    leave(a, ba)
    assert join(a, ba2).json()['state'] == 'active'
    assert leave(a, ba).json()['state'] == 'active'
    assert status(a)['booking']['id'] == ba2['id']
    assert join(b, bb).json()['state'] == 'waiting'


def test_disconnect_expiry_promotes_live_waiter(system):
    app, clock, _ = system
    a, b = client(app), client(app)
    ba, bb = booking(a), booking(b)
    join(a, ba)
    join(b, bb)
    clock[0] += 60
    assert status(b)['state'] == 'waiting'
    clock[0] += 31
    assert status(b)['state'] == 'active'
    assert status(a)['state'] == 'idle'
    assert a.post('/api/chat').status_code == 403
    assert join(a, ba).status_code == 410


def test_stale_waiter_removed_and_rejoin_at_tail(system):
    app, clock, _ = system
    a, b, c = [client(app) for _ in range(3)]
    ba, bb, bc = [booking(x) for x in (a, b, c)]
    for cl, bk in ((a, ba), (b, bb), (c, bc)):
        join(cl, bk)
    clock[0] += 60
    status(a)
    status(c)
    clock[0] += 31
    assert status(c)['people_ahead'] == 1
    assert status(b)['state'] == 'idle'
    assert join(b, bb).json()['queue_position'] == 2


def test_promotion_does_not_keep_absent_waiter_alive(system):
    app, clock, _ = system
    a, b = client(app), client(app)
    ba, bb = booking(a), booking(b)
    join(a, ba)
    join(b, bb)
    clock[0] += 80
    leave(a, ba)
    clock[0] += 11
    assert status(b)['state'] == 'idle'


def test_hard_session_deadline_and_wait_beyond_booking_end(system):
    app, clock, _ = system
    a, b = client(app), client(app)
    ba, bb = booking(a), booking(b)
    join(a, ba)
    join(b, bb)
    for _ in range(19):
        clock[0] += 60
        status(a)
        status(b)
    clock[0] += 61
    assert status(a)['state'] == 'idle'
    rb = status(b)
    assert rb['state'] == 'active'
    assert rb['deadline'] == int(clock[0]) + SESSION_SECONDS
    assert len(b.get('/api/bookings').json()) == 1
    # Idempotent joining still works after the original booking end.
    assert join(b, bb).json()['state'] == 'active'


def test_scheduled_start_enforced_and_cancel_promotes(system):
    app, clock, _ = system
    a, b = client(app), client(app)
    ba = booking(a, scheduled=True)
    assert join(a, ba).status_code == 425
    clock[0] = datetime.fromisoformat(ba['starts_at'].replace('Z', '+00:00')).timestamp()
    assert join(a, ba).json()['state'] == 'active'
    bb = booking(b)
    assert join(b, bb).json()['state'] == 'waiting'
    assert a.delete('/api/bookings/' + ba['id']).status_code == 200
    assert status(b)['state'] == 'active'


def test_waiting_leave_releases_position(system):
    a, b, c = [client(system[0]) for _ in range(3)]
    ba, bb, bc = [booking(x) for x in (a,b,c)]
    join(a, ba)
    join(b, bb)
    join(c, bc)
    leave(b, bb)
    assert status(c)['people_ahead'] == 1
    assert join(b, bb).json()['people_ahead'] == 2


def test_queue_is_bounded(tmp_path):
    app = create_app(tmp_path/'bounded.sqlite', queue_limit=1)
    a,b,c = [client(app) for _ in range(3)]
    ba,bb,bc = [booking(x) for x in (a,b,c)]
    join(a,ba)
    join(b,bb)
    assert join(c,bc).status_code == 429
    leave(b,bb)
    assert join(c,bc).json()['state'] == 'waiting'


def test_restart_preserves_queue_and_drops_expired_leases(system):
    app, clock, path = system
    a, b = client(app), client(app)
    ba, bb = booking(a), booking(b)
    join(a,ba)
    join(b,bb)
    restarted = create_app(path, now=lambda: clock[0])
    from fastapi.testclient import TestClient
    from test_bookings import HEADERS
    b2 = TestClient(restarted, headers=HEADERS)
    b2.cookies.set(COOKIE, b.cookies.get(COOKIE), path='/api')
    assert status(b2)['state'] == 'waiting'
    clock[0] += LEASE_SECONDS + 1
    assert status(b2)['state'] == 'idle'


def test_legacy_database_migration_preserves_booking(tmp_path):
    path = tmp_path/'legacy.sqlite'
    now = 1_800_000_000
    token = 'legacy-test-token'
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with sqlite3.connect(path) as con:
        con.executescript("""
            CREATE TABLE owners(token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL);
            CREATE TABLE bookings(
                id TEXT PRIMARY KEY, owner_hash TEXT NOT NULL REFERENCES owners(token_hash) ON DELETE CASCADE,
                first_name TEXT NOT NULL, last_name TEXT NOT NULL, gender TEXT NOT NULL,
                language TEXT NOT NULL, mode TEXT NOT NULL, avatar TEXT NOT NULL,
                starts_at INTEGER NOT NULL UNIQUE, ends_at INTEGER NOT NULL,
                consent_version TEXT NOT NULL, created_at INTEGER NOT NULL);
        """)
        con.execute("INSERT INTO owners VALUES (?,?)", (token_hash, now+86400))
        con.execute("INSERT INTO bookings VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    ('a'*32, token_hash, 'Sample', 'Person', 'unspecified', 'en','chat','female',
                     now, now+1200, 'legacy-v1', now))
    app = create_app(path, now=lambda: now)
    from fastapi.testclient import TestClient
    from test_bookings import HEADERS
    c = TestClient(app, headers=HEADERS)
    c.cookies.set(COOKIE, token, path='/api')
    rows = c.get('/api/bookings').json()
    assert rows[0]['id'] == 'a'*32 and rows[0]['booking_type'] == 'scheduled'
    assert join(c, rows[0]).json()['state'] == 'active'
    with sqlite3.connect(path) as con:
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        assert con.execute("SELECT first_name, consent_version FROM bookings").fetchone() == ('Sample','legacy-v1')


def test_heartbeat_rates_are_isolated_per_owner(system):
    a, b = client(system[0]), client(system[0])
    # Both clients share the same IP, as happens behind the local development proxy.
    for _ in range(121):
        result = a.post('/api/admission/status')
    assert result.status_code == 429
    assert b.post('/api/admission/status').status_code == 200


def test_full_capacity_burst_and_orderly_drain(tmp_path):
    app = create_app(tmp_path / 'burst.sqlite', queue_limit=32)
    clients = [client(app) for _ in range(40)]
    rows = [booking(c) for c in clients]
    with ThreadPoolExecutor(max_workers=16) as pool:
        results = list(pool.map(lambda pair: join(*pair).status_code, zip(clients, rows)))
    assert results.count(200) == 33
    assert results.count(429) == 7
    snapshots = [status(c) for c in clients]
    assert sum(s['state'] == 'active' for s in snapshots) == 1
    waiting = sorted((s['queue_position'], i) for i,s in enumerate(snapshots) if s['state'] == 'waiting')
    assert [position for position, _ in waiting] == list(range(1, 33))
    active = next(i for i,s in enumerate(snapshots) if s['state'] == 'active')
    for _, next_index in waiting:
        assert leave(clients[active], rows[active]).status_code == 200
        assert status(clients[next_index])['state'] == 'active'
        active = next_index
    leave(clients[active], rows[active])
    assert status(clients[active])['active_count'] == 0
