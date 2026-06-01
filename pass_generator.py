"""
pass_generator.py — QR pass generation and input validation.
"""

import hashlib, json, datetime, re


def generate_qr_data(pass_id, passenger, route_no, travel_date, seat_no, fare) -> str:
    payload = {"pass_id": pass_id, "passenger": passenger, "route": route_no,
               "date": travel_date, "seat": seat_no, "fare": fare,
               "issued": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
    s = json.dumps(payload, separators=(",", ":"))
    payload["chk"] = hashlib.sha256(s.encode()).hexdigest()[:12]
    return json.dumps(payload, separators=(",", ":"))


def verify_qr(qr_string: str) -> dict:
    try:
        p = json.loads(qr_string)
        chk = p.pop("chk", "")
        expected = hashlib.sha256(json.dumps(p, separators=(",", ":")).encode()).hexdigest()[:12]
        p["chk"] = chk
        return {"valid": chk == expected, "payload": p}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def validate_booking(passenger, phone, travel_date, seat_no) -> tuple:
    if not passenger.strip() or len(passenger.strip()) < 2:
        return False, "Passenger name must be at least 2 characters."
    if not re.match(r"^[a-zA-Z\s\-']+$", passenger.strip()):
        return False, "Name may only contain letters, spaces, hyphens."
    if len(re.sub(r"\D", "", phone)) < 10:
        return False, "Phone must have at least 10 digits."
    try:
        d = datetime.datetime.strptime(travel_date, "%Y-%m-%d").date()
        if d < datetime.date.today():
            return False, "Travel date cannot be in the past."
    except ValueError:
        return False, "Invalid date format."
    if not re.match(r"^[A-D]\d+$", seat_no):
        return False, f"Invalid seat: {seat_no}"
    return True, ""
