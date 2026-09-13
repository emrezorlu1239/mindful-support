"""Exercise the actual Gradio handoff with fixture inference, no GPU downloads."""
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app import create_app
from backend.gpu_tickets import GPUTickets
from ai.runtime import AIRuntime
from test_ai_pipeline import Model, References
from test_bookings import client
from test_admission import booking, join


def test_ticket_owner_result_and_cancellation(tmp_path):
    tickets = GPUTickets()
    runtime = AIRuntime(Model(), References())
    app = create_app(tmp_path / 'tickets.sqlite', ai_runtime=runtime, gpu_tickets=tickets)
    a, b = client(app), client(app)
    booked = booking(a)
    join(a, booked)
    payload = dict(booking_id=booked['id'], request_id=str(uuid4()), message='A difficult day.')
    response = a.post('/api/chat', json=payload)
    assert response.status_code == 202
    key = response.json()['ticket']
    assert b.get('/api/chat/result', params={'ticket': key}).status_code == 404
    row = tickets.rows[key]
    assert app.state.complete_ticket(key, row['owner']) == 'ready'
    result = a.get('/api/chat/result', params={'ticket': key})
    assert result.status_code == 200 and result.json()['reply']
    assert not tickets.rows
    a.post('/api/admission/leave', json={'booking_id': booked['id']})
    assert not runtime.sessions


def test_gradio_http_protocol_and_static_page(tmp_path, monkeypatch):
    monkeypatch.setenv('MINDFUL_DB_PATH', str(tmp_path / 'hosted.sqlite'))
    from app import build_app
    runtime = AIRuntime(Model(), References())
    app = build_app(runtime)
    headers = {'Origin': 'http://localhost:3000', 'Content-Type': 'application/json'}
    with TestClient(app, headers=headers) as c:
        assert c.get('/').status_code == 200
        assert c.post('/api/gpu/gradio_api/call/reply', json={'data': ['x'*43]}).status_code == 401
        assert c.post('/api/bootstrap').status_code == 200
        booked = booking(c)
        join(c, booked)
        ticket = c.post('/api/chat', json=dict(booking_id=booked['id'],
            request_id=str(uuid4()), message='I would like someone to listen.')).json()['ticket']
        queued = c.post('/api/gpu/gradio_api/call/reply', json={'data': [ticket]})
        assert queued.status_code == 200, queued.text
        event_id = queued.json()['event_id']
        stream = c.get('/api/gpu/gradio_api/call/reply/' + event_id)
        assert 'event: complete' in stream.text, stream.text
        assert 'ready' in stream.text and 'listen' not in stream.text
        result = c.get('/api/chat/result', params={'ticket': ticket})
        assert result.status_code == 200, result.text
        assert result.json()['reply']
        assert len(c.get('/api/chat/history', params={'booking_id': booked['id']}).json()['messages']) == 2
        c.post('/api/admission/leave', json={'booking_id': booked['id']})
        assert not runtime.sessions
