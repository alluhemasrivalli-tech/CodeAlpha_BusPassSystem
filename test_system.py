"""
test_system.py — Unit tests for Cloud Bus Pass System.
Run: python -m pytest tests/ -v
"""

import sys, os, datetime
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from database import BusDatabase
from pass_generator import generate_qr_data, verify_qr, validate_booking


# ── Database Tests ─────────────────────────────────────────────────────────────

@pytest.fixture
def db(tmp_path):
    d = BusDatabase(str(tmp_path / "test.sqlite"))
    yield d
    d.close()

class TestDatabase:
    def test_routes_seeded(self, db):
        routes = db.get_routes()
        assert len(routes) == 8

    def test_search_by_source(self, db):
        routes = db.get_routes(source="vijayawada")
        assert all("Vijayawada" in r["source"] for r in routes)

    def test_search_by_dest(self, db):
        routes = db.get_routes(destination="hyderabad")
        assert len(routes) >= 1

    def test_book_pass(self, db):
        route = db.get_routes()[0]
        result = db.book_pass("Test User", "9876543210", route["id"], "2027-01-15", "A1", route["fare"])
        assert result["success"]
        assert result["pass_id"].startswith("BP")

    def test_duplicate_seat_rejected(self, db):
        route = db.get_routes()[0]
        db.book_pass("User A", "9876543210", route["id"], "2027-01-15", "B1", route["fare"])
        result = db.book_pass("User B", "9000000001", route["id"], "2027-01-15", "B1", route["fare"])
        assert not result["success"]
        assert "already booked" in result["message"]

    def test_same_seat_different_dates(self, db):
        route = db.get_routes()[0]
        r1 = db.book_pass("User A", "9876543210", route["id"], "2027-01-15", "C1", route["fare"])
        r2 = db.book_pass("User B", "9000000001", route["id"], "2027-01-16", "C1", route["fare"])
        assert r1["success"] and r2["success"]

    def test_get_pass(self, db):
        route = db.get_routes()[0]
        result = db.book_pass("Alice", "9876543210", route["id"], "2027-01-15", "A2", route["fare"])
        p = db.get_pass(result["pass_id"])
        assert p["passenger"] == "Alice"
        assert p["seat_no"] == "A2"

    def test_cancel_pass(self, db):
        route = db.get_routes()[0]
        result = db.book_pass("Bob", "9876543210", route["id"], "2027-01-15", "D1", route["fare"])
        cancel = db.cancel_pass(result["pass_id"])
        assert cancel["success"]
        # Seat should now be free
        booked = db.get_booked_seats(route["id"], "2027-01-15")
        assert "D1" not in booked

    def test_cancel_nonexistent(self, db):
        result = db.cancel_pass("BPXXXXXXXX")
        assert not result["success"]

    def test_available_seats(self, db):
        route = db.get_routes()[0]
        avail = db.available_seats(route["id"], "2027-03-01", route["total_seats"])
        assert len(avail) == route["total_seats"]

    def test_all_passes(self, db):
        route = db.get_routes()[0]
        db.book_pass("X", "9000000001", route["id"], "2027-01-20", "A3", route["fare"])
        db.book_pass("Y", "9000000002", route["id"], "2027-01-20", "A4", route["fare"])
        passes = db.get_all_passes()
        assert len(passes) == 2


# ── QR / Pass Generator Tests ─────────────────────────────────────────────────

class TestQR:
    def test_generate_and_verify(self):
        qr = generate_qr_data("BPTEST001","Alice","AP-001","2027-01-15","A1",450.0)
        result = verify_qr(qr)
        assert result["valid"]

    def test_tampered_qr_fails(self):
        import json
        qr   = generate_qr_data("BPTEST002","Bob","AP-002","2027-01-16","B2",580.0)
        data = json.loads(qr)
        data["passenger"] = "Hacker"
        tampered = json.dumps(data)
        result = verify_qr(tampered)
        assert not result["valid"]

    def test_invalid_json(self):
        result = verify_qr("not-json-at-all")
        assert not result["valid"]


# ── Input Validation Tests ────────────────────────────────────────────────────

class TestValidation:
    def test_valid_input(self):
        ok, _ = validate_booking("Ravi Kumar","9876543210","2027-06-01","A1")
        assert ok

    def test_empty_name(self):
        ok, msg = validate_booking("","9876543210","2027-06-01","A1")
        assert not ok and "name" in msg.lower()

    def test_short_phone(self):
        ok, msg = validate_booking("Alice","123","2027-06-01","A1")
        assert not ok and "phone" in msg.lower()

    def test_past_date(self):
        ok, msg = validate_booking("Alice","9876543210","2020-01-01","A1")
        assert not ok and "past" in msg.lower()

    def test_invalid_seat(self):
        ok, msg = validate_booking("Alice","9876543210","2027-06-01","X99")
        assert not ok and "seat" in msg.lower()

    def test_bad_date_format(self):
        ok, msg = validate_booking("Alice","9876543210","15-01-2027","A1")
        assert not ok
