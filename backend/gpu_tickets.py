"""Short-lived, owner-bound handoff; Gradio receives no conversation content."""
import secrets
import threading
import time
from fastapi import HTTPException


class GPUTickets:
    def __init__(self, now=time.time):
        self.now = now
        self.lock = threading.RLock()
        self.rows = {}

    def prune(self, active_ids=None):
        with self.lock:
            for key, row in list(self.rows.items()):
                if row['expires'] <= self.now() or active_ids is not None and row['data'].booking_id not in active_ids:
                    del self.rows[key]

    def forget(self, booking_id):
        with self.lock:
            for key, row in list(self.rows.items()):
                if row['data'].booking_id == booking_id:
                    del self.rows[key]

    def issue(self, owner, data):
        with self.lock:
            self.prune()
            for key, row in self.rows.items():
                if row['owner'] == owner:
                    if row['data'] == data:
                        return key
                    raise HTTPException(429, 'A reply is already pending.')
            if len(self.rows) >= 4:
                raise HTTPException(429, 'The model is busy.')
            key = secrets.token_urlsafe(32)
            self.rows[key] = dict(owner=owner, data=data, expires=self.now()+120, state='pending')
            return key

    def _owned(self, key, owner):
        self.prune()
        row = self.rows.get(key)
        if row is None or row['owner'] != owner:
            raise HTTPException(404, 'Reply request expired.')
        return row

    def complete(self, key, owner, run):
        with self.lock:
            row = self._owned(key, owner)
            if row['state'] != 'pending':
                return 'ready'
            row['state'] = 'running'
        try:
            output = run(owner, row['data'])
            status = 200
        except HTTPException as exc:
            status, output = exc.status_code, {'detail': exc.detail}
        except Exception:
            status, output = 503, {'detail': 'GPU service unavailable. Please try later.'}
        with self.lock:
            if self.rows.get(key) is row:
                row.update(state='done', status=status, output=output)
        return 'ready'

    def result(self, key, owner):
        with self.lock:
            row = self._owned(key, owner)
            if row['state'] != 'done':
                return 202, {'pending': True}
            del self.rows[key]
            return row['status'], row['output']
