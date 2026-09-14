"""Loopback-only booking foundation. No model or conversation persistence."""
import asyncio
import hashlib
import json
import os
import secrets
import sqlite3
import time
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware
from backend.admission import AdmissionQueue, LEASE_SECONDS, initialize

ROOT = Path(__file__).resolve().parents[1]
COOKIE = "mindful_local_access"
ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000"}
DURATION = 20 * 60
TTL = 24 * 60 * 60

class BookingInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    gender: Literal["unspecified", "female", "male", "other"]
    language: Literal["tr", "en"]
    # Legacy fields accepted for old local clients; the current UI is chat-only.
    mode: Literal["chat", "avatar"] = "chat"
    avatar: Literal["female", "male"] = "female"
    starts_at: datetime | None = None
    adult_consent: Literal[True]

    @field_validator("first_name", "last_name")
    @classmethod
    def name_has_no_controls(cls, value):
        if any(ord(c) < 32 for c in value):
            raise ValueError("Control characters are not allowed")
        return value

    @field_validator("starts_at")
    @classmethod
    def timezone_required(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("An explicit timezone is required")
        return value

def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat().replace("+00:00", "Z")

class AdmissionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    booking_id: str = Field(min_length=32, max_length=32, pattern=r"^[a-f0-9]+$")

class ChatInput(AdmissionInput):
    request_id: str = Field(min_length=36, max_length=36, pattern=r"^[a-f0-9-]+$")
    message: str = Field(min_length=1, max_length=1500)

def create_app(db_path=None, now=time.time, capacity=None, queue_limit=32, ai_runtime=None,
               public_origin=None, gpu_tickets=None):
    origins = ORIGINS
    hosts = ["localhost", "127.0.0.1", "testserver"]
    if public_origin:
        parsed = urlsplit(public_origin)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('A fixed HTTPS origin is required.')
        origins = {public_origin}
        hosts = [parsed.hostname, "localhost", "127.0.0.1"]
    if ai_runtime is None and os.environ.get("MINDFUL_ENABLE_AI") == "1":
        from ai.runtime import load_approved_runtime
        ai_runtime = load_approved_runtime()
    vector_ready = False
    index_path = ROOT / "data" / "knowledge.sqlite"
    corpus_path = ROOT / "knowledge" / "passages.json"
    if index_path.exists() and corpus_path.exists():
        try:
            with sqlite3.connect(f"file:{index_path.as_posix()}?mode=ro", uri=True) as index:
                metadata = dict(index.execute("SELECT key,value FROM metadata"))
                expected_revision = json.loads((ROOT / "ai" / "model-lock.json").read_text(encoding="utf-8"))["intfloat/multilingual-e5-small"]["revision"]
                vector_ready = (metadata.get("corpus_sha256") == hashlib.sha256(corpus_path.read_bytes()).hexdigest()
                                and metadata.get("revision") == expected_revision
                                and index.execute("SELECT COUNT(*) FROM passages").fetchone()[0] > 0)
        except (sqlite3.Error, ValueError, KeyError, OSError):
            vector_ready = False
    capacity = int(capacity if capacity is not None else os.environ.get("MINDFUL_MAX_CONCURRENT_SESSIONS", "1"))
    if not 1 <= capacity <= 4 or not 1 <= queue_limit <= 100:
        raise ValueError("Capacity must be 1–4 and queue limit must be 1–100.")
    if ai_runtime is not None and capacity!=1:
        raise ValueError("The evaluated AI configuration supports one active session.")
    queue = AdmissionQueue(now, capacity, queue_limit)
    db_path = Path(db_path or os.environ.get("MINDFUL_DB_PATH", ROOT / "data" / "appointments.sqlite"))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def database():
        con = sqlite3.connect(db_path, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA secure_delete=ON")
        try:
            with con:
                yield con
        finally:
            con.close()

    with database() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS owners (
                token_hash TEXT PRIMARY KEY,
                expires_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id TEXT PRIMARY KEY,
                owner_hash TEXT NOT NULL REFERENCES owners(token_hash) ON DELETE CASCADE,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                gender TEXT NOT NULL,
                language TEXT NOT NULL,
                mode TEXT NOT NULL,
                avatar TEXT NOT NULL,
                starts_at INTEGER NOT NULL UNIQUE,
                ends_at INTEGER NOT NULL,
                consent_version TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_bookings_owner ON bookings(owner_hash, starts_at);
            CREATE INDEX IF NOT EXISTS idx_owner_expiry ON owners(expires_at);
        """)
        initialize(con)

    def cleanup():
        with database() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("DELETE FROM bookings WHERE ends_at < ? AND id NOT IN (SELECT booking_id FROM admissions)", (int(now()) - TTL,))
            con.execute("DELETE FROM owners WHERE expires_at <= ?", (int(now()),))
            queue.advance(con)
            if ai_runtime:
                active_ids = {row[0] for row in con.execute("SELECT booking_id FROM admissions WHERE state='active'")}
                ai_runtime.prune(active_ids)
                if gpu_tickets:
                    gpu_tickets.prune(active_ids)

    async def janitor():
        while True:
            await asyncio.sleep(5)
            await asyncio.to_thread(cleanup)

    @asynccontextmanager
    async def lifespan(_app):
        cleanup()
        task = asyncio.create_task(janitor())
        yield
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    app = FastAPI(title="Mindful Support", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=hosts)
    limits = {}

    @app.middleware("http")
    async def local_boundary(request: Request, call_next):
        if request.method in {"POST", "DELETE", "PUT", "PATCH"}:
            if request.headers.get("origin") not in origins:
                return JSONResponse({"detail": "Untrusted request origin."}, status_code=403)
            if request.method == "POST" and "application/json" not in request.headers.get("content-type", ""):
                return JSONResponse({"detail": "JSON content type required."}, status_code=415)
            body = b""
            async for chunk in request.stream():
                body += chunk
                if len(body) > 8192:
                    return JSONResponse({"detail": "Request too large."}, status_code=413)
            request._body = body
        minute = int(now()) // 60
        try:
            identity = "owner:" + owner(request)
        except HTTPException:
            identity = "ip:" + (request.client.host if request.client else "unknown")
        key = (identity, minute)
        for old in list(limits):
            if old[1] < minute:
                del limits[old]
        limits[key] = limits.get(key, 0) + 1
        if limits[key] > 120:
            return JSONResponse({"detail": "Too many requests. Try again shortly."}, status_code=429)
        response = await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, _exc):
        # Do not echo submitted identity fields in error responses.
        return JSONResponse({"detail": "Invalid booking details, timezone, or adult consent."}, status_code=422)

    def owner(request):
        token = request.cookies.get(COOKIE, "")
        if not token or len(token) > 128:
            raise HTTPException(401, "Local access session required.")
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        with database() as con:
            row = con.execute("SELECT expires_at FROM owners WHERE token_hash=?", (token_hash,)).fetchone()
        if not row or row["expires_at"] <= now():
            raise HTTPException(401, "Local access session expired.")
        return token_hash

    def slot_times():
        first = (int(now()) // DURATION + 1) * DURATION
        return [first + i * DURATION for i in range(12)]

    def public_booking(row):
        return {key: (iso(row[key]) if key in {"starts_at", "ends_at"} else row[key])
                for key in ("id", "starts_at", "ends_at", "language", "mode", "avatar", "booking_type")} | {"status": "reserved"}

    @app.get("/api/health")
    def health():
        enabled = bool(ai_runtime and ai_runtime.ready)
        return {"status": "ok", "stage": "local_ai" if enabled else "local_preparation", "model_ready": enabled,
                "fine_tuned": enabled, "chat_enabled": enabled, "vector_database_ready": vector_ready,
                "session_capacity": capacity, "queue_limit": queue_limit}

    @app.post("/api/bootstrap")
    def bootstrap(request: Request, response: Response):
        cleanup()
        try:
            owner(request)
            return {"ready": True}
        except HTTPException:
            token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            with database() as con:
                con.execute("INSERT INTO owners VALUES (?, ?)", (token_hash, int(now()) + TTL))
            response.set_cookie(COOKIE, token, max_age=TTL, httponly=True, secure=bool(public_origin), samesite="strict", path="/api")
            return {"ready": True}

    @app.get("/api/slots")
    def slots():
        with database() as con:
            occupied = {r["starts_at"] for r in con.execute("SELECT starts_at FROM bookings WHERE ends_at>? AND booking_type='scheduled'", (int(now()),))}
        return [{"starts_at": iso(s), "ends_at": iso(s + DURATION), "available": s not in occupied} for s in slot_times()]

    @app.get("/api/bookings")
    def bookings(request: Request):
        current = owner(request)
        with database() as con:
            rows = con.execute("""SELECT * FROM bookings WHERE owner_hash=? AND completed_at IS NULL
                AND (ends_at>? OR id IN (SELECT booking_id FROM admissions)) ORDER BY starts_at""", (current, int(now()))).fetchall()
        return [public_booking(row) for row in rows]

    @app.post("/api/bookings", status_code=201)
    def book(data: BookingInput, request: Request):
        current = owner(request)
        timestamp = int(data.starts_at.timestamp()) if data.starts_at else int(now())
        if data.starts_at and (data.starts_at.microsecond or timestamp not in slot_times()):
            raise HTTPException(422, "Choose an available future time.")
        booking_id = secrets.token_hex(16)
        try:
            with database() as con:
                con.execute("BEGIN IMMEDIATE")
                count = con.execute("""SELECT COUNT(*) FROM bookings WHERE owner_hash=? AND completed_at IS NULL
                    AND (ends_at>? OR id IN (SELECT booking_id FROM admissions))""", (current, int(now()))).fetchone()[0]
                if count >= 3:
                    raise HTTPException(429, "At most three active appointments are allowed.")
                con.execute("INSERT INTO bookings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
                    (booking_id,current,data.first_name,data.last_name,data.gender,data.language,
                     data.mode,data.avatar,timestamp,timestamp+DURATION,"experimental-v2",int(now()),
                     "scheduled" if data.starts_at else "immediate"))
                row = con.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
                return public_booking(row)
        except sqlite3.IntegrityError:
            raise HTTPException(409, "This time has just been reserved. Choose another time.")

    @app.delete("/api/bookings/{booking_id}")
    def cancel(booking_id: str, request: Request):
        current = owner(request)
        with database() as con:
            con.execute("BEGIN IMMEDIATE")
            removed = con.execute("DELETE FROM bookings WHERE id=? AND owner_hash=?", (booking_id, current)).rowcount
            queue.advance(con)
        if not removed:
            raise HTTPException(404, "Appointment not found.")
        if ai_runtime:
            ai_runtime.forget(booking_id)
        if gpu_tickets:
            gpu_tickets.forget(booking_id)
        return {"cancelled": True}

    @app.post("/api/admission/join")
    def join(data: AdmissionInput, request: Request):
        current = owner(request)
        with database() as con:
            con.execute("BEGIN IMMEDIATE")
            queue.advance(con)
            queue.join(con, current, data.booking_id)
            return queue.snapshot(con, current, public_booking)

    @app.post("/api/admission/status")
    def admission_status(request: Request):
        current = owner(request)
        with database() as con:
            con.execute("BEGIN IMMEDIATE")
            queue.advance(con)
            con.execute("UPDATE admissions SET lease_until=? WHERE owner_hash=?",
                        (int(now()) + LEASE_SECONDS, current))
            return queue.snapshot(con, current, public_booking)

    @app.post("/api/admission/leave")
    def leave(data: AdmissionInput, request: Request):
        current = owner(request)
        with database() as con:
            con.execute("BEGIN IMMEDIATE")
            queue.advance(con)
            queue.leave(con, current, data.booking_id)
            owns_booking = con.execute("SELECT 1 FROM bookings WHERE id=? AND owner_hash=?",
                                       (data.booking_id, current)).fetchone()
            if ai_runtime and owns_booking:
                ai_runtime.forget(data.booking_id)
            if gpu_tickets and owns_booking:
                gpu_tickets.forget(data.booking_id)
            return queue.snapshot(con, current, public_booking)

    def active_booking(current, booking_id=None):
        with database() as con:
            con.execute("BEGIN IMMEDIATE")
            queue.advance(con)
            row = con.execute("""SELECT b.id,b.language FROM admissions a
                JOIN bookings b ON b.id=a.booking_id WHERE a.owner_hash=? AND a.state='active'""",
                (current,)).fetchone()
        if not row or (booking_id is not None and row["id"] != booking_id):
            return None
        return row

    @app.get("/api/chat/history")
    def chat_history(booking_id: str, request: Request):
        current = owner(request)
        if not active_booking(current, booking_id):
            raise HTTPException(403, "Active session required.")
        return {"messages": ai_runtime.history(booking_id) if ai_runtime else []}

    @app.post("/api/chat")
    async def chat(request: Request):
        current = owner(request)
        admitted = active_booking(current)
        if not admitted:
            raise HTTPException(403, "An active session is required. Join through your appointment.")
        if not ai_runtime or not ai_runtime.ready:
            raise HTTPException(503, "Chat is unavailable: model training and evaluation have not been completed.")
        try:
            data = ChatInput.model_validate(await request.json())
            if not data.message.strip():
                raise ValueError("Empty message")
        except ValueError:
            raise HTTPException(422, "Invalid chat request.")
        if data.booking_id != admitted["id"]:
            raise HTTPException(403, "Active session does not match.")
        if gpu_tickets:
            return JSONResponse({'transport': 'gradio', 'ticket': gpu_tickets.issue(current, data)}, status_code=202)
        return await asyncio.to_thread(run_chat, current, data)

    def run_chat(current, data):
        admitted = active_booking(current, data.booking_id)
        if not admitted:
            raise HTTPException(403, 'Active session required.')
        from ai.runtime import ModelBusy, SessionLimit, SessionEnded, ComputeUnavailable
        try:
            return ai_runtime.respond(data.booking_id, data.request_id,
                data.message.strip(), admitted["language"], lambda: bool(active_booking(current, data.booking_id)))
        except ComputeUnavailable as exc:
            raise HTTPException(429 if exc.code == "gpu_quota" else 503, {"code": exc.code})
        except ModelBusy:
            raise HTTPException(429, "A reply is already being prepared. Please wait.")
        except SessionLimit:
            raise HTTPException(429, "This session has reached its message limit.")
        except SessionEnded:
            raise HTTPException(409, "The session ended before the reply was ready.")
        except ValueError:
            raise HTTPException(422, "The request could not be processed.")
        except Exception:
            # Model/library exceptions may contain prompt data; never log or echo them.
            raise HTTPException(503, "The model could not complete this reply.")

    if gpu_tickets:
        @app.get('/api/chat/result')
        def chat_result(ticket: str, request: Request):
            status, result = gpu_tickets.result(ticket, owner(request))
            return JSONResponse(result, status_code=status)

        def gpu_owner(request):
            try:
                current = owner(request)
                return current if active_booking(current) else None
            except HTTPException:
                return None

        app.state.gpu_owner = gpu_owner
        app.state.complete_ticket = lambda ticket, current: gpu_tickets.complete(ticket, current, run_chat)

    return app
