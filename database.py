"""
database.py — Cloud Bus Pass System database.
SQLite for local dev — swap connection string for AWS RDS / Azure SQL in production.
"""

import sqlite3, os, uuid, datetime
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "buspass.sqlite")


class BusDatabase:
    def __init__(self, db_path: str = DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()
        self._seed_routes()

    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS routes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                route_no     TEXT NOT NULL UNIQUE,
                source       TEXT NOT NULL,
                destination  TEXT NOT NULL,
                fare         REAL NOT NULL,
                distance_km  INTEGER NOT NULL,
                duration_hr  REAL NOT NULL,
                total_seats  INTEGER NOT NULL DEFAULT 40,
                ac           INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS passes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                pass_id     TEXT NOT NULL UNIQUE,
                passenger   TEXT NOT NULL,
                phone       TEXT NOT NULL,
                route_id    INTEGER NOT NULL REFERENCES routes(id),
                travel_date TEXT NOT NULL,
                seat_no     TEXT NOT NULL,
                fare_paid   REAL NOT NULL,
                status      TEXT NOT NULL DEFAULT 'CONFIRMED',
                booked_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                qr_code     TEXT
            );
            CREATE TABLE IF NOT EXISTS bookings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                route_id    INTEGER NOT NULL REFERENCES routes(id),
                travel_date TEXT NOT NULL,
                seat_no     TEXT NOT NULL,
                pass_id     TEXT NOT NULL,
                UNIQUE(route_id, travel_date, seat_no)
            );
        """)
        self.conn.commit()

    def _seed_routes(self):
        if self.conn.execute("SELECT COUNT(*) FROM routes").fetchone()[0] > 0:
            return
        routes = [
            ("AP-001","Vijayawada","Hyderabad",   450.0,275,4.5,40,0),
            ("AP-002","Vijayawada","Visakhapatnam",580.0,350,5.5,40,1),
            ("AP-003","Hyderabad", "Bangalore",   750.0,570,8.0,40,1),
            ("AP-004","Hyderabad", "Chennai",     620.0,630,7.5,36,1),
            ("AP-005","Vijayawada","Chennai",     690.0,430,6.5,40,0),
            ("AP-006","Visakhapatnam","Hyderabad",600.0,620,9.0,36,1),
            ("AP-007","Bangalore", "Chennai",     350.0,345,5.0,40,0),
            ("AP-008","Vijayawada","Tirupati",    520.0,310,5.0,40,1),
        ]
        self.conn.executemany(
            "INSERT INTO routes (route_no,source,destination,fare,distance_km,duration_hr,total_seats,ac) VALUES (?,?,?,?,?,?,?,?)",
            routes)
        self.conn.commit()

    def get_routes(self, source="", destination="") -> List[Dict]:
        q, p = "SELECT * FROM routes WHERE 1=1", []
        if source:      q += " AND LOWER(source) LIKE ?";      p.append(f"%{source.lower()}%")
        if destination: q += " AND LOWER(destination) LIKE ?"; p.append(f"%{destination.lower()}%")
        return [dict(r) for r in self.conn.execute(q, p).fetchall()]

    def get_route_by_id(self, route_id: int) -> Optional[Dict]:
        r = self.conn.execute("SELECT * FROM routes WHERE id=?", (route_id,)).fetchone()
        return dict(r) if r else None

    def get_booked_seats(self, route_id: int, travel_date: str) -> List[str]:
        return [r["seat_no"] for r in self.conn.execute(
            "SELECT seat_no FROM bookings WHERE route_id=? AND travel_date=?",
            (route_id, travel_date)).fetchall()]

    def available_seats(self, route_id: int, travel_date: str, total_seats: int) -> List[str]:
        booked = set(self.get_booked_seats(route_id, travel_date))
        all_seats = [f"{row}{col}" for row in "ABCD" for col in range(1, total_seats//4+1)]
        return [s for s in all_seats if s not in booked]

    def book_pass(self, passenger, phone, route_id, travel_date, seat_no, fare) -> Dict:
        if seat_no in self.get_booked_seats(route_id, travel_date):
            return {"success": False, "message": f"Seat {seat_no} is already booked."}
        pass_id = "BP" + uuid.uuid4().hex[:8].upper()
        try:
            self.conn.execute(
                "INSERT INTO passes (pass_id,passenger,phone,route_id,travel_date,seat_no,fare_paid) VALUES (?,?,?,?,?,?,?)",
                (pass_id, passenger, phone, route_id, travel_date, seat_no, fare))
            self.conn.execute(
                "INSERT INTO bookings (route_id,travel_date,seat_no,pass_id) VALUES (?,?,?,?)",
                (route_id, travel_date, seat_no, pass_id))
            self.conn.commit()
            return {"success": True, "pass_id": pass_id, "seat_no": seat_no, "fare": fare}
        except sqlite3.IntegrityError:
            return {"success": False, "message": f"Seat {seat_no} was just taken. Please choose another."}

    def get_pass(self, pass_id: str) -> Optional[Dict]:
        r = self.conn.execute(
            "SELECT p.*, r.route_no, r.source, r.destination, r.ac FROM passes p JOIN routes r ON p.route_id=r.id WHERE p.pass_id=?",
            (pass_id,)).fetchone()
        return dict(r) if r else None

    def cancel_pass(self, pass_id: str) -> Dict:
        r = self.conn.execute("SELECT * FROM passes WHERE pass_id=?", (pass_id,)).fetchone()
        if not r: return {"success": False, "message": "Pass not found."}
        if r["status"] == "CANCELLED": return {"success": False, "message": "Already cancelled."}
        self.conn.execute("UPDATE passes SET status='CANCELLED' WHERE pass_id=?", (pass_id,))
        self.conn.execute("DELETE FROM bookings WHERE pass_id=?", (pass_id,))
        self.conn.commit()
        return {"success": True, "message": "Pass cancelled. Refund initiated."}

    def get_all_passes(self) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT p.*, r.route_no, r.source, r.destination FROM passes p JOIN routes r ON p.route_id=r.id ORDER BY p.booked_at DESC LIMIT 100"
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
