"""Transactional FIFO admission. Stores access metadata only, never messages."""
from fastapi import HTTPException

LEASE_SECONDS = 90
SESSION_SECONDS = 1200


def initialize(con):
    # Rebuild the v1 table transactionally: immediate bookings may share a timestamp.
    con.execute("BEGIN IMMEDIATE")
    columns = {r[1] for r in con.execute("PRAGMA table_info(bookings)")}
    if "booking_type" not in columns:
        con.execute("""CREATE TABLE bookings_v2 (
            id TEXT PRIMARY KEY,
            owner_hash TEXT NOT NULL REFERENCES owners(token_hash) ON DELETE CASCADE,
            first_name TEXT NOT NULL, last_name TEXT NOT NULL, gender TEXT NOT NULL,
            language TEXT NOT NULL, mode TEXT NOT NULL, avatar TEXT NOT NULL,
            starts_at INTEGER NOT NULL, ends_at INTEGER NOT NULL,
            consent_version TEXT NOT NULL, created_at INTEGER NOT NULL,
            booking_type TEXT NOT NULL CHECK(booking_type IN ('scheduled','immediate')),
            completed_at INTEGER
        )""")
        con.execute("INSERT INTO bookings_v2 SELECT *, 'scheduled', NULL FROM bookings")
        con.execute("DROP TABLE bookings")
        con.execute("ALTER TABLE bookings_v2 RENAME TO bookings")
    con.execute("CREATE INDEX IF NOT EXISTS idx_bookings_owner ON bookings(owner_hash, starts_at)")
    con.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_scheduled_start
                   ON bookings(starts_at) WHERE booking_type='scheduled'""")
    con.execute("""CREATE TABLE IF NOT EXISTS admissions (
        seq INTEGER PRIMARY KEY,
        booking_id TEXT NOT NULL UNIQUE REFERENCES bookings(id) ON DELETE CASCADE,
        owner_hash TEXT NOT NULL UNIQUE REFERENCES owners(token_hash) ON DELETE CASCADE,
        state TEXT NOT NULL CHECK(state IN ('waiting','active')),
        lease_until INTEGER NOT NULL,
        started_at INTEGER,
        deadline INTEGER
    )""")
    con.execute("CREATE INDEX IF NOT EXISTS idx_admission_state ON admissions(state, seq)")


class AdmissionQueue:
    def __init__(self, now, capacity, queue_limit):
        self.now = now
        self.capacity = capacity
        self.queue_limit = queue_limit

    def advance(self, con):
        """Caller owns BEGIN IMMEDIATE; expiry and promotion share that transaction."""
        timestamp = int(self.now())
        con.execute("""UPDATE bookings SET completed_at=? WHERE id IN (
            SELECT booking_id FROM admissions WHERE state='active'
            AND (lease_until<=? OR deadline<=?))""", (timestamp, timestamp, timestamp))
        con.execute("DELETE FROM admissions WHERE lease_until<=? OR deadline<=?",
                    (timestamp, timestamp))
        active = con.execute("SELECT COUNT(*) FROM admissions WHERE state='active'").fetchone()[0]
        free = max(0, self.capacity - active)
        candidates = con.execute(
            "SELECT seq FROM admissions WHERE state='waiting' ORDER BY seq LIMIT ?", (free,)
        ).fetchall()
        for row in candidates:
            # Promotion must not extend a disconnected waiter's heartbeat.
            con.execute("""UPDATE admissions SET state='active', started_at=?, deadline=?
                           WHERE seq=?""", (timestamp, timestamp + SESSION_SECONDS, row["seq"]))

    def snapshot(self, con, owner_hash, public_booking):
        row = con.execute("SELECT * FROM admissions WHERE owner_hash=?", (owner_hash,)).fetchone()
        counts = dict(con.execute("SELECT state, COUNT(*) FROM admissions GROUP BY state").fetchall())
        result = {"state": "idle", "capacity": self.capacity,
                  "active_count": counts.get("active", 0),
                  "waiting_count": counts.get("waiting", 0), "people_ahead": 0,
                  "queue_position": 0, "model_ready": False}
        if row:
            booking = con.execute("SELECT * FROM bookings WHERE id=?", (row["booking_id"],)).fetchone()
            before = con.execute(
                "SELECT COUNT(*) FROM admissions WHERE state='waiting' AND seq<?", (row["seq"],)
            ).fetchone()[0]
            waiting = row["state"] == "waiting"
            result.update(state=row["state"], booking=public_booking(booking),
                          people_ahead=counts.get("active", 0) + before if waiting else 0,
                          queue_position=before + 1 if waiting else 0,
                          lease_until=row["lease_until"], deadline=row["deadline"])
        return result

    def join(self, con, owner_hash, booking_id):
        timestamp = int(self.now())
        booking = con.execute("SELECT * FROM bookings WHERE id=? AND owner_hash=?",
                              (booking_id, owner_hash)).fetchone()
        if not booking:
            raise HTTPException(404, "Appointment not found.")
        existing = con.execute("SELECT * FROM admissions WHERE owner_hash=?", (owner_hash,)).fetchone()
        if existing:
            if existing["booking_id"] != booking_id:
                raise HTTPException(409, "Finish or leave your current session first.")
            con.execute("UPDATE admissions SET lease_until=? WHERE owner_hash=?",
                        (timestamp + LEASE_SECONDS, owner_hash))
            return
        if booking["completed_at"] is not None or booking["ends_at"] <= timestamp:
            raise HTTPException(410, "This appointment has ended. Create a new appointment.")
        if booking["starts_at"] > timestamp:
            raise HTTPException(425, "Your appointment time has not started yet.")
        waiting = con.execute("SELECT COUNT(*) FROM admissions WHERE state='waiting'").fetchone()[0]
        active = con.execute("SELECT COUNT(*) FROM admissions WHERE state='active'").fetchone()[0]
        if active >= self.capacity and waiting >= self.queue_limit:
            raise HTTPException(429, "The waiting room is full. Please try again later.")
        con.execute("""INSERT INTO admissions
            (booking_id, owner_hash, state, lease_until) VALUES (?,?,'waiting',?)""",
                    (booking_id, owner_hash, timestamp + LEASE_SECONDS))
        self.advance(con)

    def leave(self, con, owner_hash, booking_id):
        row = con.execute("SELECT * FROM admissions WHERE owner_hash=? AND booking_id=?",
                          (owner_hash, booking_id)).fetchone()
        if row:
            if row["state"] == "active":
                con.execute("UPDATE bookings SET completed_at=? WHERE id=?",
                            (int(self.now()), booking_id))
            con.execute("DELETE FROM admissions WHERE booking_id=?", (booking_id,))
        self.advance(con)
