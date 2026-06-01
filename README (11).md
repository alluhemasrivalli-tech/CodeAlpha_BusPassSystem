# CodeAlpha — Task 3: Cloud-Based Bus Pass System

> **CodeAlpha Cloud Computing Internship**

A full-stack cloud bus ticket booking system built with Python/Flask. Features real-time seat availability, SHA-256 QR-verified digital passes, concurrent booking conflict prevention, and a dark admin dashboard — all with zero external cloud dependencies for local development.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Route Search** | Filter by source, destination, and date |
| **Live Seat Map** | Interactive seat grid — green = available, red = booked |
| **Concurrent Safety** | SQLite UNIQUE constraint prevents double-booking |
| **Digital Pass** | QR code generated with SHA-256 checksum for forgery prevention |
| **QR Verification** | Conductor can verify pass authenticity instantly |
| **Pass Cancellation** | Cancel with automatic seat release |
| **Admin Dashboard** | All bookings, revenue, route stats |
| **Scalability** | WAL mode SQLite → swap to AWS RDS / Azure SQL for production |

---

## 🗂 Project Structure

```
CodeAlpha_BusPassSystem/
│
├── src/
│   ├── app.py              # Flask server (all routes)
│   ├── database.py         # DB layer — routes, passes, bookings
│   └── pass_generator.py   # QR generation, input validation
│
├── templates/
│   ├── index.html          # Home / search
│   ├── search.html         # Route results
│   ├── book.html           # Seat selection + booking form
│   ├── pass.html           # Digital bus pass with QR
│   └── admin.html          # Admin dashboard
│
├── tests/
│   └── test_system.py      # 22 pytest unit tests
│
├── data/                   # SQLite DB (auto-created)
├── requirements.txt
└── README.md
```

---

## 🚀 How to Run (VS Code)

### 1. Clone and open
```bash
git clone https://github.com/<your-username>/CodeAlpha_BusPassSystem.git
cd CodeAlpha_BusPassSystem
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the server
```bash
cd src
python app.py
```

Open: **http://127.0.0.1:5000**

### 5. Run tests
```bash
cd ..
python -m pytest tests/ -v
```

---

## 🎬 Demo Flow (for Screen Recording)

| Step | URL | What to show |
|---|---|---|
| 1 | `http://localhost:5000` | Home page — search form, popular routes |
| 2 | Select cities + date → Search | Route list with available seats |
| 3 | Click Book on any route | Interactive seat map — click a green seat |
| 4 | Fill name + phone → Confirm | Booking confirmation animation |
| 5 | Pass page | Digital pass with QR code + ✔ Verified |
| 6 | `http://localhost:5000/admin` | Dark admin dashboard — stats + all passes |
| 7 | Terminal | `python -m pytest tests/ -v` → 22 passed ✅ |

---

## 🏗 Cloud Architecture (Production)

```
User Browser
      │
      ▼
  Flask App  ←──── AWS Elastic Beanstalk / Azure App Service
      │
      ▼
  SQLite  →  (swap to) AWS RDS PostgreSQL / Azure SQL Database
```

For high-traffic deployment:
- Replace `sqlite3` connection with `psycopg2` (PostgreSQL) in `database.py`
- Deploy Flask on **AWS Elastic Beanstalk** or **Google Cloud Run**
- Use **Redis** for session caching
- Enable **auto-scaling** for peak hours

---

## 🔒 Reliability Features

- **No ticket loss** — every pass stored with unique ID in DB
- **No double booking** — `UNIQUE(route_id, travel_date, seat_no)` DB constraint
- **No fare errors** — fare comes from DB, never user input
- **QR forgery prevention** — SHA-256 checksum embedded in every QR
- **WAL journal mode** — handles concurrent connections safely

---

## 👨‍💻 Author

**[Your Name]**  
CodeAlpha Cloud Computing Intern  
[LinkedIn] | [GitHub]

---

## 📄 License

Submitted as part of the **CodeAlpha Internship Programme**.
