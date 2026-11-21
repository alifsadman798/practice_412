# SmartRoute BD 🇧🇩 — Multimodal Transport Route Planner

A database-driven, timetable-aware multimodal transport route planner for Bangladesh, powered by **Python 3.13**, **FastAPI**, **PostgreSQL**, and an offline **interactive SVG vector basemap**.

SmartRoute BD combines intercity buses, Bangladesh Railway trains, and local feeder connections into optimal journey plans with transparent fare calculations, rule-based peak traffic adjustments, and step-by-step route visualization.

---

## 🌟 Key Features

1. **Multimodal Journey Planning:**
   - **Bus Routing:** Shortest path routing across all 64 Bangladesh districts with deterministic reverse-route consistency.
   - **Train Routing:** Bangladesh Railway schedule-aware journeys respecting stop sequences, arrival/departure timetables, train numbers, operating days, and off-days.
   - **Multimodal Engine:** Intelligent combinations of local feeder transport, bus, and train services with realistic transfer buffers (30 mins train/bus, 15 mins local).
   - **Route Comparison:** Instant side-by-side comparison identifying the **Cheapest**, **Fastest**, and **Shortest** travel options.

2. **Offline Interactive Vector Basemap:**
   - Light, clean navigation basemap rendering district administrative boundaries, verified road corridors, and physical railway links.
   - **Auto-Fit Viewport:** Dynamically scales SVG viewBox to fit the selected journey geometry.
   - **High-Contrast Route Geometry:** White under-casing outlines separate active journey tracks from background map geometry.
   - **Collision-Free Stop Labels:** Intelligent pairwise cluster detection positions adjacent stations into opposing quadrants with contrast pill cards.
   - **Interactive Journey Drawer:** Step-by-step itinerary detailing stop order, arrival/departure times, and halt minutes; clicking any station card highlights and pulses its location on the map.
   - **Zero Cloud Map APIs:** 100% self-contained offline vector map; zero external Google Maps, Mapbox, or CDN dependencies.

3. **Transparent Fares & Traffic Estimation:**
   - **Bus Fare:** `50 + (50 × core_city_count) + (2 × total_distance_km)`
   - **Train Fare:** `40 + (1.5 × distance_km) + (60 if intermediate_stops ≤ 2 else 0)`
   - **Local Transport:** Fixed 50 BDT per feeder segment at 30 km/h assumed speed.
   - **Traffic Factors:** 24-hour time-slot traffic modifiers (peak rush hours 08:00–10:00 & 17:00–20:00, night discount 22:00–06:00) and major city congestion multipliers.

4. **Operational Administration Portal:**
   - Protected dashboard (`/admin`) for managing transport disruptions, road closures, schedule updates, user reports, and audit logs.

---

## 🛠️ Technology Stack

- **Backend:** Python 3.13+, FastAPI, Uvicorn, Pydantic v2
- **Database:** PostgreSQL (with SQLAlchemy 2.0 ORM & Alembic migrations)
- **Frontend:** Vanilla JavaScript (ES6+), CSS3, SVG Vector Map (zero external frameworks or CDNs)
- **Default Local Port:** `8001` (`http://127.0.0.1:8001`)

---

## 📁 Repository Structure

```text
practice_412/
├── alembic/                            # Database schema migration history (0001 to 0006)
│   ├── env.py
│   └── versions/
├── data/                               # 5 authoritative CSVs & verified runtime geography
│   ├── 64_districts.csv                # Authoritative 64 Bangladesh districts & 121 distance edges
│   ├── bus_schedule_64_district_with_fares.csv # Authoritative 10,134 bus departure schedules
│   ├── local_distance.csv              # Authoritative 202 local feeder connections
│   ├── train_routes_final.csv          # Authoritative 115 intercity train services
│   ├── train_stops.csv                 # Authoritative 1,539 railway station timetables
│   └── geographic/                     # Verified runtime geographic assets
│       ├── bus_corridor_geometry.geojson      # 11 verified highway corridors
│       ├── bus_schedule_route_lookup.csv      # Bus route matching lookup
│       ├── csv_location_master.csv            # Unified station, district & local place catalog
│       ├── district_boundaries_simplified.json# 64 district boundary SVG paths for light basemap
│       ├── local_geometry_lookup.csv          # Feeder link schematic connector lookup
│       ├── railway_link_geometry.geojson      # 190 verified mainline rail links
│       └── train_service_hop_lookup.csv       # Train consecutive stop hop lookup
├── src/                                # Core application source code
│   ├── api/                            # FastAPI app, endpoints, orchestrator & geo routes
│   ├── auth/                           # Security, password hashing & JWT tokens
│   ├── bus/                            # Dijkstra router, bus fare & traffic estimators
│   ├── data/                           # Graph builder, normalization & store
│   ├── database/                       # PostgreSQL connection, models, seeder & repo
│   ├── disruptions/                    # Road closures, disruption service & admin routes
│   ├── multimodal/                     # Multimodal routing engine & transfer buffer
│   ├── shared/                         # Domain models, enums & constants
│   ├── train/                          # Train scheduler, timetable, fare & waiting models
│   └── utils/                          # Time, projection & geographic helpers
├── static/                             # Web interface & Admin dashboard frontend
│   ├── admin.html                      # Administrative moderation dashboard
│   ├── admin.js                        # Authenticated admin management script
│   ├── app.css                         # Modern responsive stylesheet
│   ├── app.js                          # Client-side map & journey planner application
│   ├── index.html                      # Public journey planner & interactive vector map
│   └── images/                         # Frontend map assets
│       ├── bangladesh-districts-map.jpg
│       └── hero-transport.jpg
├── .vscode/                            # VS Code debugger & task configurations (Port 8001)
│   ├── launch.json
│   ├── settings.json
│   └── tasks.json
├── .env.example                        # Environment template with safe placeholders
├── .gitignore                          # Git ignore rules
├── alembic.ini                         # Alembic migration configuration
├── requirements.txt                    # Python package dependencies
├── run.bat                             # Windows batch one-click launcher
├── run.ps1                             # PowerShell one-click launcher
└── README.md                           # Project documentation
```

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- **Python:** 3.13 or compatible (3.11+)
- **PostgreSQL:** Local or remote PostgreSQL instance (running on port 5432 by default)

### 2. Clone and Setup Environment
```bash
git clone https://github.com/alifsadman798/practice_412.git
cd practice_412

# Create virtual environment
python -m venv .venv

# Activate environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env` and adjust the PostgreSQL credentials if needed:
```bash
cp .env.example .env
```
Default `.env` configuration:
```env
DATABASE_URL=postgresql+psycopg://smartroute:change-me@localhost:5432/smartroute
ADMIN_USERNAME=admin
ADMIN_PASSWORD=12345678
APP_ENV=development
PORT=8001
```

### 4. Database Setup & Migrations
Create the PostgreSQL database `smartroute` and run Alembic migrations:
```bash
alembic upgrade head
```

### 5. Run the Application
Start the server using any of the following methods:

- **PowerShell (Recommended):**
  ```powershell
  .\run.ps1
  ```
- **Command Prompt:**
  ```cmd
  run.bat
  ```
- **Direct Uvicorn Command:**
  ```bash
  uvicorn src.api.main:app --host 127.0.0.1 --port 8001 --reload
  ```

---

## 🌐 Application Access Points

- **Journey Planner & Interactive Map:** [http://127.0.0.1:8001](http://127.0.0.1:8001)
- **Admin Management Portal:** [http://127.0.0.1:8001/admin](http://127.0.0.1:8001/admin)
  - Default Admin Username: `admin`
  - Default Admin Password: `12345678`
- **Interactive OpenAPI / Swagger Documentation:** [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

---

## 🗺️ Known Geographic & Operational Notes

- **Offline Vector Map:** District boundaries and geometry layers are rendered client-side using SVG paths without external geocoding or vector-tile servers.
- **Railway Link Coverage:** 190 physical mainline railway links connect all active Bangladesh Railway passenger stations. Chord junctions across complex railway yards use direct station connectors pending sub-meter yard centerline traces.
- **Local Feeder Coverage:** 202 local feeder connections provide schematic transit links between local upazilas/places and parent district administrative hubs.
