# Railway Passenger Congestion and Transit Delay Dynamics
### Multidimensional Data Warehouse (OLAP) & Business Intelligence Platform

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Database](https://img.shields.io/badge/Database-MySQL%208.0-orange.svg)](https://www.mysql.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose%20Ready-2496ED.svg)](https://www.docker.com/)
[![Analytics](https://img.shields.io/badge/BI-Power%20BI%20%7C%20DAX-F2C811.svg)](https://powerbi.microsoft.com/)
[![Research](https://img.shields.io/badge/Publication-IEEE%20Format-red.svg)](https://www.ieee.org/)

---

## 1. Executive Summary & Research Context

Urban and inter-city railway networks operate under tight temporal coupling, making them vulnerable to cascading delays and acute congestion bottlenecks. This repository contains the complete enterprise Data Warehouse (DW) implementation for the research project:

> **"Railway Passenger Congestion and Transit Delay Dynamics"**  
> *Developed in fulfillment of University Data Warehousing guidelines and prepared for IEEE publication.*

The platform converts high-frequency operational transit records (over 1 GB of raw telemetry data) into a clean, query-optimized **Star Schema (OLAP)** data warehouse in MySQL 8.0, powered by an automated, memory-efficient Python ETL orchestration engine and integrated with Power BI DAX analytical models.

---

## 2. Multidimensional Star Schema Architecture

The data warehouse employs a **Star Schema** centered around `Fact_TrainDelay`, optimized for analytical queries (slicing, dicing, drill-down, and roll-up) without complex recursive joins.

```
                         +-----------------------+
                         |       Dim_Date        |
                         +-----------------------+
                         | PK  DateSK (YYYYMMDD) |
                         |     FullDate          |
                         |     Year              |
                         |     Quarter           |
                         |     Month, MonthName  |
                         |     Day, DayOfWeek    |
                         |     IsWeekend         |
                         +-----------+-----------+
                                     |
                                     | 1:N
                                     v
+----------------------+   +-------------------+   +----------------------+
|     Dim_Station      |   |  Fact_TrainDelay  |   |      Dim_Train       |
+----------------------+   +-------------------+   +----------------------+
| PK  StationSK (Surr) |   | PK  FactID        |   | PK  TrainSK (Surr)   |
|     StationCode      |<--+ FK  StationSK     +-->|     TrainNumber      |
|     StationName      |1:N| FK  TrainSK       |1:N|     TrainName        |
+----------------------+   | FK  DateSK        |   |     TrainType        |
                           | FK  DelayCatSK    |   +----------------------+
                           |     DelayMinutes  |
                           |     IsDelayed     |
                           +---------+---------+
                                     ^
                                     | 1:N
                                     |
                         +-----------+-----------+
                         |   Dim_DelayCategory   |
                         +-----------------------+
                         | PK  DelayCatSK        |
                         |     CategoryName      |
                         |     MinDelayMinutes   |
                         |     MaxDelayMinutes   |
                         +-----------------------+
```

### Table Specifications

| Table Name | Classification | Grain | Primary / Surrogate Key | Description |
| :--- | :--- | :--- | :--- | :--- |
| **`Fact_TrainDelay`** | Central Fact | One scheduled arrival at one station on a specific date | `FactID` (BIGINT AUTO_INCREMENT) | Records continuous delay in minutes, delay status flag, and FKs to all dimensions. |
| **`Dim_Date`** | Conformed Dimension | One calendar day | `DateSK` (INT: `YYYYMMDD`) | Pre-populated 2024–2026 calendar including weekend flags, quarters, and days of week. |
| **`Dim_Train`** | Role Dimension | One unique train service | `TrainSK` (INT AUTO_INCREMENT) | Natural key: `TrainNumber`. Attributes: name, type classification. |
| **`Dim_Station`** | Spatial Dimension | One unique station | `StationSK` (INT AUTO_INCREMENT) | Natural key: `StationCode`. Attributes: formal station name. |
| **`Dim_DelayCategory`** | Banded Dimension | Delay severity tier | `DelayCatSK` (INT 1–4) | Categorizes delays: `On-Time (≤0m)`, `Minor (1-15m)`, `Moderate (16-45m)`, `Severe (>45m)`. |

---

## 3. Repository Structure

```text
railway-dw-project/
├── bi_reports/
│   └── dax_measures.txt       # Production DAX measures library for Power BI
├── data/
│   └── raw/                   # Raw source datasets (~1 GB transit telemetry)
│       ├── combined_delay.csv
│       ├── combined_schedule.csv
│       ├── station_full_names.csv
│       └── train_details.csv
├── etl/
│   ├── __init__.py            # Python package declaration
│   ├── db_connector.py        # SQLAlchemy engine with environment variable fallback
│   ├── load_dimensions.py     # Date, Train, and Station dimension population
│   ├── load_fact.py           # Fact table chunked ETL with in-memory SK mapping
│   └── run_etl.py             # Master orchestration pipeline with terminal UI & timing
├── paper/
│   └── figures/               # IEEE research paper visual assets & diagrams
├── sql/
│   ├── 01_create_database.sql # Database creation with utf8mb4 collation
│   ├── 02_create_star_schema.sql # DDL for Star Schema, constraints, & seed dimensions
│   └── 03_indexes_and_views.sql  # Composite indexes and analytical view (vw_RailwayAnalytics)
├── docker-compose.yml         # MySQL 8.0 container service + automated SQL bootstrap
├── Dockerfile                 # Container specification for headless ETL runner
├── requirements.txt           # Python library dependencies
├── run_sql_scripts.py         # Autonomous Python runner for all SQL files in sequence
└── README.md                  # System documentation
```

---

## 4. ETL Pipeline Architecture

The ETL engine is orchestrated via [`etl/run_etl.py`](file:///Volumes/Mac/docker-sandboxes/railway-dw-project/etl/run_etl.py), adhering strictly to dependency ordering:

```
[Raw CSV Telemetry]
        |
        v
+-----------------------------------------------------------+
| PHASE 1: Load Dimensions (load_dimensions.py)             |
|   - Dim_Date: Algorithmic calendar generation (2024-2026) |
|   - Dim_Train: Deduplication & string cleansing           |
|   - Dim_Station: Code-to-Name extraction                  |
+-----------------------------------------------------------+
        |
        v  (Surrogate Keys Generated & Cached)
+-----------------------------------------------------------+
| PHASE 2: Load Central Fact (load_fact.py)                 |
|   - Chunked Processing (50,000 rows/batch)                |
|   - In-memory hash-map lookup for StationSK & TrainSK     |
|   - DateSK transformation (YYYY-MM-DD -> YYYYMMDD)        |
|   - Banding logic -> DelayCatSK (1 to 4)                  |
|   - Referential Integrity Enforcement                     |
|   - High-performance append to Fact_TrainDelay            |
+-----------------------------------------------------------+
```

---

## 5. Quick Start & Execution Guide

### Prerequisites
- [Docker & Docker Desktop](https://www.docker.com/) (Recommended)
- [Python 3.9+](https://www.python.org/)

---

### Step 1: Clone and Set Up Virtual Environment

```bash
# Clone the repository
git clone https://github.com/Avinash-Perera/railway-dw-project.git
cd railway-dw-project

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required dependencies
pip install -r requirements.txt
```

---

### Step 2: Spin Up MySQL 8.0 via Docker

Run the container in detached mode:
```bash
docker compose up -d mysql
```
> **Note:** The `docker-compose.yml` mounts the `./sql` folder to `/docker-entrypoint-initdb.d:ro`. MySQL automatically executes `01_create_database.sql`, `02_create_star_schema.sql`, and `03_indexes_and_views.sql` on its initial boot!

---

### Step 3: Run the Master ETL Pipeline

Execute the master orchestrator to populate all dimensions and the central fact table:
```bash
python etl/run_etl.py
```

#### Terminal Progress Output Example
```text
================================================================================
 🚂  RAILWAY DATA WAREHOUSE — MASTER ETL ORCHESTRATION PIPELINE  🚀
================================================================================
 🎯 Objective : Railway Passenger Congestion & Transit Delay Dynamics (OLAP)
 🏛️  Schema    : MySQL Star Schema (Dimensions + Central Fact)
 ⏰ Started   : 2026-09-03 15:20:00
================================================================================
🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹
📦 [PHASE 1/2] Loading Dimension Tables into Data Warehouse...
   Target Dimensions : Dim_Date, Dim_Train, Dim_Station
🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹
Generating and loading Date dimension...
✅ Successfully loaded 1096 rows into Dim_Date.
Loading Train dimension from .../train_details.csv...
✅ Successfully loaded 11114 rows into Dim_Train.
Loading Station dimension from .../station_full_names.csv...
✅ Successfully loaded 8515 rows into Dim_Station.

✅ [PHASE 1/2 COMPLETED] Dimension tables loaded successfully in 4.12s.

🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹
📊 [PHASE 2/2] Loading Fact Table into Data Warehouse...
   Target Fact Table : Fact_TrainDelay
   Transformations   : DateSK derivation, Surrogate Key lookup mapping,
                       Delay Category banding & IsDelayed boolean flag
🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹🔹
Loading Fact table from .../combined_delay.csv in chunks...
Fetching dimension mappings...
Processing chunk 1...
  -> Inserted 50000 rows for chunk 1.
...
✅ [PHASE 2/2 COMPLETED] Fact table loaded successfully.

================================================================================
🎉 MASTER ETL PIPELINE EXECUTED SUCCESSFULLY!
⏱️  Total Pipeline Runtime: 3m 42.15s (222.15s total)
📈 Data Warehouse is fully populated and ready for OLAP queries & Power BI!
================================================================================
```

---

### Step 4: Verify Data Warehouse Population

Run this SQL query to verify table row counts:
```bash
mysql -h 127.0.0.1 -P 3306 -u root -pdw_password -e "
USE railway_dw;
SELECT 'Dim_Date' AS TableName, COUNT(*) AS RowsCount FROM Dim_Date
UNION ALL SELECT 'Dim_Train', COUNT(*) FROM Dim_Train
UNION ALL SELECT 'Dim_Station', COUNT(*) FROM Dim_Station
UNION ALL SELECT 'Dim_DelayCategory', COUNT(*) FROM Dim_DelayCategory
UNION ALL SELECT 'Fact_TrainDelay', COUNT(*) FROM Fact_TrainDelay;
"
```

---

## 6. Business Intelligence & Power BI Analytics

### Pre-Built Analytical View: `vw_RailwayAnalytics`
The database includes a pre-materialized view denormalizing the Star Schema for fast dashboard consumption:
```sql
SELECT * FROM vw_RailwayAnalytics LIMIT 10;
```

### DAX Measures Library
[`bi_reports/dax_measures.txt`](file:///Volumes/Mac/docker-sandboxes/railway-dw-project/bi_reports/dax_measures.txt) contains 25+ production-ready DAX formulas organized into:
1. **Volume Metrics**: `Total Arrivals`, `Total Delay Minutes`, `Delayed Arrivals Count`.
2. **Operational KPIs**: `On-Time Performance Rate`, `Average Delay Overall`, `Delay Rate`.
3. **IEEE Paper Formulations**:
   - **Weighted Delay Severity Index (DSI)**:
     $$\text{DSI} = \frac{(1 \times \text{Minor}) + (3 \times \text{Moderate}) + (5 \times \text{Severe})}{\text{Total Arrivals}}$$
   - **Station Congestion Index (SCI)**: Multiplies arrival frequency by average delay duration to isolate high-congestion bottlenecks.
   - **Weekend vs. Weekday Ratio**: Measures infrastructure stress over non-commuter travel periods.
4. **Time Intelligence**: `Delay Minutes MTD`, `MoM Delay Growth %`, `Moving 7Day Avg Delay`.

---

## 7. Sample OLAP Queries (Analytical Insights)

### A. Top 10 Most Delayed Train Services
```sql
USE railway_dw;
SELECT 
    t.TrainNumber,
    t.TrainName,
    COUNT(f.FactID) AS TotalStops,
    ROUND(AVG(f.DelayMinutes), 2) AS AvgDelayMinutes,
    SUM(f.IsDelayed) AS DelayedStopsCount
FROM Fact_TrainDelay f
JOIN Dim_Train t ON f.TrainSK = t.TrainSK
GROUP BY t.TrainNumber, t.TrainName
HAVING TotalStops >= 50
ORDER BY AvgDelayMinutes DESC
LIMIT 10;
```

### B. Weekend vs. Weekday Delay Dynamics
```sql
USE railway_dw;
SELECT 
    d.DayOfWeek,
    d.IsWeekend,
    COUNT(f.FactID) AS TotalArrivals,
    ROUND(AVG(f.DelayMinutes), 2) AS AvgDelayMinutes,
    ROUND(SUM(f.IsDelayed) / COUNT(f.FactID) * 100, 2) AS DelayRatePercent
FROM Fact_TrainDelay f
JOIN Dim_Date d ON f.DateSK = d.DateSK
GROUP BY d.DayOfWeek, d.IsWeekend
ORDER BY AvgDelayMinutes DESC;
```

### C. Severe Delay Bottleneck Stations (>45 Minutes)
```sql
USE railway_dw;
SELECT 
    s.StationCode,
    s.StationName,
    COUNT(f.FactID) AS SevereDelayIncidents,
    ROUND(AVG(f.DelayMinutes), 2) AS AvgSevereDelay
FROM Fact_TrainDelay f
JOIN Dim_Station s ON f.StationSK = s.StationSK
WHERE f.DelayCatSK = 4
GROUP BY s.StationCode, s.StationName
ORDER BY SevereDelayIncidents DESC
LIMIT 10;
```

---

## 8. Authors & Academic Attribution

This project is developed as part of academic research on railway transit reliability and smart mobility analytics:
- **Repository**: [railway-dw-project](https://github.com/Avinash-Perera/railway-dw-project)
- **Target Journal/Conference**: IEEE Transactions on Intelligent Transportation Systems (T-ITS) / IEEE Big Data
- **License**: MIT License
