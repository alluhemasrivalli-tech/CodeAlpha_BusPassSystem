"""
app.py — RoadWave Cloud Bus Pass System — Flask server.
"""

import os, sys, datetime
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify, render_template, redirect, url_for
from database import BusDatabase
from pass_generator import generate_qr_data, verify_qr, validate_booking

app = Flask(__name__, template_folder="../templates", static_folder="../static")
app.secret_key = "CodeAlpha_BusPass_2024"
db = BusDatabase()
TODAY = lambda: datetime.date.today().isoformat()
CITIES = ["Vijayawada","Hyderabad","Visakhapatnam","Bangalore","Chennai","Tirupati"]


@app.route("/")
def index():
    return render_template("index.html", cities=CITIES, today=TODAY())


@app.route("/search")
def search():
    src  = request.args.get("from", "")
    dst  = request.args.get("to", "")
    date = request.args.get("date", TODAY())
    routes = db.get_routes(src, dst)
    for r in routes:
        booked = db.get_booked_seats(r["id"], date)
        r["available"] = r["total_seats"] - len(booked)
        r["travel_date"] = date
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(routes)
    return render_template("search.html", routes=routes, src=src, dst=dst, date=date,
                           cities=CITIES, today=TODAY())


@app.route("/book/<int:route_id>")
def book_form(route_id):
    route = db.get_route_by_id(route_id)
    if not route: return "Route not found", 404
    date = request.args.get("date", TODAY())
    booked = db.get_booked_seats(route_id, date)
    avail  = db.available_seats(route_id, date, route["total_seats"])
    return render_template("book.html", route=route, date=date, booked=booked, avail=avail, today=TODAY())


@app.route("/book", methods=["POST"])
def do_book():
    d = request.get_json() or request.form
    passenger, phone = d.get("passenger",""), d.get("phone","")
    route_id = int(d.get("route_id", 0))
    travel_date, seat_no = d.get("travel_date",""), d.get("seat_no","")

    ok, err = validate_booking(passenger, phone, travel_date, seat_no)
    if not ok: return jsonify({"success": False, "message": err}), 400

    route = db.get_route_by_id(route_id)
    if not route: return jsonify({"success": False, "message": "Invalid route."}), 400

    result = db.book_pass(passenger, phone, route_id, travel_date, seat_no, route["fare"])
    if not result["success"]: return jsonify(result), 409

    qr = generate_qr_data(result["pass_id"], passenger, route["route_no"], travel_date, seat_no, route["fare"])
    db.conn.execute("UPDATE passes SET qr_code=? WHERE pass_id=?", (qr, result["pass_id"]))
    db.conn.commit()
    result["redirect"] = f"/pass/{result['pass_id']}"
    return jsonify(result)


@app.route("/pass/<pass_id>")
def view_pass(pass_id):
    p = db.get_pass(pass_id)
    if not p: return "Pass not found", 404
    qr_valid = verify_qr(p["qr_code"])["valid"] if p.get("qr_code") else False
    return render_template("pass.html", p=p, qr_valid=qr_valid)


@app.route("/cancel", methods=["POST"])
def cancel():
    d = request.get_json() or request.form
    return jsonify(db.cancel_pass(d.get("pass_id","")))


@app.route("/admin")
def admin():
    passes = db.get_all_passes()
    revenue  = sum(p["fare_paid"] for p in passes if p["status"]=="CONFIRMED")
    confirmed = sum(1 for p in passes if p["status"]=="CONFIRMED")
    cancelled = sum(1 for p in passes if p["status"]=="CANCELLED")
    routes = db.get_routes()
    return render_template("admin.html", passes=passes, routes=routes,
                           revenue=revenue, confirmed=confirmed, cancelled=cancelled)


@app.route("/api/seats")
def api_seats():
    route_id = int(request.args.get("route_id", 0))
    date     = request.args.get("date","")
    route    = db.get_route_by_id(route_id)
    if not route: return jsonify({"error":"Not found"}), 404
    booked = db.get_booked_seats(route_id, date)
    avail  = db.available_seats(route_id, date, route["total_seats"])
    return jsonify({"booked": booked, "available": avail, "total": route["total_seats"]})


if __name__ == "__main__":
    print("=" * 55)
    print("  CodeAlpha — Cloud Bus Pass System")
    print("  Running at: http://127.0.0.1:5000")
    print("=" * 55)
    app.run(debug=True, host="0.0.0.0", port=5000)
