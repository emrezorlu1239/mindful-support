"""Verify the published service using fictional data and clean up its sessions."""
import json
import threading
import time
import os
from pathlib import Path
from uuid import uuid4
import requests

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://zorlu5454-mindful-support.hf.space'


def main():
    deadline = time.monotonic() + 240
    while True:
        try:
            expected = os.environ.get('MINDFUL_EXPECT_SPACE_SHA')
            if expected:
                runtime = requests.get('https://huggingface.co/api/spaces/Zorlu5454/mindful-support',
                    params={'t':time.time()},timeout=12).json().get('runtime', {})
                if runtime.get('stage') != 'RUNNING' or runtime.get('sha') != expected:
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Expected deployment is not ready')
                    time.sleep(12)
                    continue
            health = requests.get(BASE + '/api/health', timeout=12)
            if health.status_code == 200 and health.json().get('chat_enabled'):
                break
        except requests.RequestException:
            pass
        if time.monotonic() >= deadline:
            raise RuntimeError('Hosted model did not become ready within four minutes')
        time.sleep(12)
    print('Hosted model health is ready.', flush=True)
    clients = [requests.Session(), requests.Session()]
    bookings = []
    done = threading.Event()
    if os.environ.get('MINDFUL_TEST_HF_AUTH') == '1':
        values = {}
        for line in (ROOT / 'private/API_KEYS.txt').read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                values[key.strip()] = value.strip().strip('"').strip("'")
        for c in clients:
            c.headers['Authorization'] = 'Bearer ' + values['HF_TOKEN']
    for c in clients:
        c.headers.update({'Origin': BASE, 'Content-Type': 'application/json'})
    def heartbeat():
        while not done.wait(20):
            for c in clients:
                try: c.post(BASE + '/api/admission/status', timeout=10)
                except requests.RequestException: pass
    thread = None
    try:
        a, b = clients
        for c in clients:
            assert c.post(BASE + '/api/bootstrap', timeout=20).status_code == 200
            r = c.post(BASE + '/api/bookings', json={'first_name':'Synthetic','last_name':'Release',
                'gender':'unspecified','language':'en','adult_consent':True}, timeout=20)
            assert r.status_code == 201, r.text
            bookings.append(r.json()['id'])
        first, second = bookings
        assert a.post(BASE + '/api/admission/join', json={'booking_id':first}, timeout=20).json()['state'] == 'active'
        waiting = b.post(BASE + '/api/admission/join', json={'booking_id':second}, timeout=20).json()
        assert waiting['state'] == 'waiting' and waiting['people_ahead'] >= 1
        thread = threading.Thread(target=heartbeat, daemon=True); thread.start()
        turns = []
        messages = [
            'I have had a tiring day at work and would like someone to listen.',
            'The hardest part is feeling that I am never doing enough. Can we talk about that?',
            'I feel guilty taking a break even after finishing my tasks. Please ask one gentle question.',
        ]
        for index, message in enumerate(messages):
            payload = {'booking_id':first,'request_id':str(uuid4()),'message':message}
            r = a.post(BASE + '/api/chat', json=payload, timeout=20)
            assert r.status_code == 202, r.text
            ticket = r.json()['ticket']
            start = time.monotonic()
            q = a.post(BASE + '/api/gpu/gradio_api/call/reply', json={'data':[ticket]}, timeout=20)
            assert q.status_code == 200, q.text
            completed = False
            with a.get(BASE + '/api/gpu/gradio_api/call/reply/' + q.json()['event_id'], stream=True, timeout=100) as events:
                assert events.status_code == 200
                for line in events.iter_lines():
                    if line == b'event: error': raise RuntimeError('Hosted GPU event failed')
                    if line == b'event: complete': completed = True; break
            assert completed
            r = a.get(BASE + '/api/chat/result', params={'ticket':ticket}, timeout=20)
            assert r.status_code == 200, r.text
            result = r.json()
            assert result['reply']
            turns.append({'seconds':round(time.monotonic()-start,2), 'result':result})
            assert len(a.get(BASE + '/api/chat/history', params={'booking_id':first}, timeout=20).json()['messages']) == 2*(index+1)
            print('Hosted turn %s completed (%ss; fallback=%s).' % (index+1, turns[-1]['seconds'], result.get('fallback')), flush=True)
        assert not turns[0]['result'].get('fallback'), 'First benchmark requires a checked model answer'
        assert b.get(BASE + '/api/chat/history', params={'booking_id':first}, timeout=20).status_code == 403
        assert a.post(BASE + '/api/admission/leave', json={'booking_id':first}, timeout=20).status_code == 200
        assert b.post(BASE + '/api/admission/status', timeout=20).json()['state'] == 'active'
        report = {'date':'2026-09-14','url':BASE,'passed':True,'scope':'Live hosting integration with synthetic data; not clinical validation',
                  'health':health.json(),'authenticated_test':os.environ.get('MINDFUL_TEST_HF_AUTH') == '1','turns':turns,
                  'checks':['ready model and references','FIFO queue','real ZeroGPU checked reply','parent session history',
                            'history ownership','queue promotion']}
        (ROOT / 'docs/LIVE_RELIABILITY_CHECK.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Live reply, session history, ownership and queue promotion passed.', flush=True)
    finally:
        done.set()
        if thread: thread.join(timeout=25)
        for c, booking in zip(clients, bookings):
            try:
                c.post(BASE + '/api/admission/leave', json={'booking_id':booking}, timeout=15)
                c.delete(BASE + '/api/bookings/' + booking, timeout=15)
            except requests.RequestException: pass
        for c in clients: c.close()


if __name__ == '__main__':
    main()
