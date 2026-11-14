# SmartRoute BD 🇧🇩

A database-driven, district-aware, schedule-aware multimodal transport route planner and timetable exploration system for Bangladesh, powered by **Python 3.13.16**, **FastAPI**, and **PostgreSQL**.

For a non-technical explanation of what the project does and how its folders fit together, see [the plain-language project overview](docs/project_overview.md).

---

## 🌟 Key Features

1. **Multimodal Route Planning:**
   - **Bus-Only Routes:** Shortest path routing across Bangladesh districts with deterministic reverse-route consistency.
   - **Train-Only Routes:** Schedule-aware Bangladesh Railway journeys respecting ordered stop sequences, directions, operating days, and off-days.
   - **Multimodal Journeys:** Destination-oriented combinations of bus, train, and local transport with realistic transfer buffers (30 mins train/bus, 15 mins local).
   - **Route Comparisons:** Automatic side-by-side comparison identifying the **Cheapest**, **Fastest**, and **Shortest** routes.

2. **Transparent Fare Calculations:**
   - **Bus Fare:** `50 + (50 × core_city_count) + (2 × total_distance_km)`
   - **Train Fare:** `40 + (1.5 × distance_km) + (60 if intermediate_stops ≤ 2 else 0)`
   - **Local Transport:** Fixed 50 BDT per segment at 30 km/h assumed speed.

3. **Rule-Based Traffic-Time Estimation:**
   - 24-hour time-slot traffic factors (peak rush hours 08:00–10:00 & 17:00–20:00, night discount 22:00–06:00).
   - Major city congestion modifiers (Dhaka, Chattogram, Khulna, Rajshahi, Sylhet).
   - Transparent travel-time ranges (Minimum `0.85×`, Expected `1.0×`, Maximum `1.20×`).

4. **Independent Timetable Search:**
   - Search bus schedules by company name, service route ID, or origin/destination without needing a full route search.
   - Search train timetables by train number, train name, or date with live off-day calculations.

5. **Operational Administration Portal:**
   - Protected web dashboard for CRUD operations on districts, locations, distances, bus timetables, train services, and routing rules directly in PostgreSQL.

---

## 📁 Project Structure

```
Smart_route_BD_VS - Anti/
├── data/                               # Curated transport datasets
│   ├── 64_districts.csv                # 121 district distance edges
│   ├── bus_schedule_64_district.csv    # 10,134 bus departure schedules
│   ├── local_distance.csv              # Local upazila/station connections
│   ├── train_routes_final.csv          # 115 intercity train services
│   └── train_stops.csv                 # 1,539 ordered railway stops
├── src/
│   ├── shared/                         # Domain models, enums & constants
│   ├── database/                       # PostgreSQL connection, ORM models, seed & repo
│   ├── data/                           # CSV loader, graph representation & normalization
│   ├── bus/                            # Dijkstra router, bus fare & traffic estimators
│   ├── train/                          # Train scheduler, stops, train fare & timetable
│   ├── multimodal/                     # Transfer buffers, local legs & multimodal engine
│   ├── api/                            # FastAPI application, orchestrator & admin endpoints
│   └── utils/                          # Time calculation and geographic helpers
├── static/                             # Web interface & Admin dashboard frontend
│   ├── index.html                      # Public journey planner & timetable explorer
│   ├── admin.html                      # Administrative database manager
│   ├── app.js                          # Client-side search and rendering
│   ├── admin.js                        # Authenticated CRUD management script
│   └── app.css                         # Modern responsive theme
├── tests/                              # Pytest test suite (30 automated tests)
│   ├── conftest.py                     # SQLite test fixtures & FastAPI TestClient
│   ├── test_core.py                    # Algorithm, fare, traffic & count tests
│   ├── test_api.py                     # API endpoints and validation tests
│   └── test_end_to_end.py              # Full search and admin workflow tests
├── alembic/                            # Database migration files
├── alembic.ini                         # Alembic configuration
├── pytest.ini                          # Pytest configuration
├── requirements.txt                    # Project dependencies
├── .env.example                        # Environment variable template
└── README.md                           # Documentation & hosting guide
```

---

## 🛠️ Prerequisites

- **Python:** 3.13.16
- **PostgreSQL:** Version 14+ (currently running on local port `5432`)
- **Database Credentials:**
  - Database: `smartroute`
  - User: `smartroute`
  - Password: `change-me`
  - Host: `localhost` / `127.0.0.1`
  - Port: `5432`

---

## 🚀 How to Host & Run Locally

### Step 1: Open Terminal in Project Directory
Open PowerShell or your command prompt in this directory:
```powershell
cd "c:\Users\alifs\OneDrive\Desktop\demo project\Smart_route_BD_VS - Anti"
```

### Step 2: Configure Environment Variables
Verify or edit `.env` in the root folder:
```ini
DATABASE_URL=postgresql+psycopg://smartroute:change-me@localhost:5432/smartroute
ADMIN_USERNAME=admin
ADMIN_PASSWORD=12345678
APP_ENV=development
```

### Step 3: Run Database Migrations
Ensure PostgreSQL schema is at the latest revision:
```powershell
alembic upgrade head
```

### Step 4: Seed the Database with Imported Datasets
Load the curated CSV datasets into PostgreSQL:
```powershell
python -m src.database.seed --force
```
*Expected output:*
```
Seeded successfully: {'districts': 73, 'locations': 230, 'district_edges': 121, 'local_edges': 160, 'bus_schedules': 10134, 'train_services': 115, 'train_stops': 1539, 'routing_configs': 3}
```

### Step 5: Start the Local Web Server
Launch the application with Uvicorn:
```powershell
uvicorn src.api.main:app --host 127.0.0.1 --port 8080 --reload
```

---

## 🌐 Accessing the Application

Once the server is running, open your web browser:

| Interface | URL | Description |
|-----------|-----|-------------|
| **Public Website** | [http://127.0.0.1:8080](http://127.0.0.1:8080) | Journey planner, route comparison, bus & train timetable searches |
| **Admin Dashboard** | [http://127.0.0.1:8080/admin](http://127.0.0.1:8080/admin) | Operational record management (Username: `admin`, Password: `12345678`) |
| **Interactive API Docs** | [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs) | Swagger UI for testing all REST endpoints interactively |
| **ReDoc API Docs** | [http://127.0.0.1:8080/redoc](http://127.0.0.1:8080/redoc) | Alternative formatted API specification |

---

## 🧪 Running Automated Tests

Run the complete test suite (unit, algorithm, API, and end-to-end tests):
```powershell
pytest -v
```
*All 30 tests will run and pass.*
