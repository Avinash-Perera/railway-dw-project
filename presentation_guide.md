# Presentation & Contribution Guide
## Railway Data Warehouse — IEEE Academic Submission

**Project Title:** A Multidimensional Data Warehouse and Trend Analytics Framework for Railway Transit Delay Dynamics: A Case Study of Indian Railways  
**Course:** Data Warehousing & Business Intelligence  
**Deliverables:** IEEE Conference Paper · Metabase Dashboard · Python ETL Pipeline · Docker Stack

---

## Part 1: Final Presentation Slide Deck

> Recommended Duration: **15–20 minutes** + 5 min Q&A  
> Tool: PowerPoint / Google Slides / LaTeX Beamer  
> Total Slides: **14**

---

### Slide 1 — Title Slide

**Content:**
- Project title (full)
- Member 1 name & role: *Data Engineer*
- Member 2 name & role: *BI & Analytics Lead*
- University, Department, Date
- Optional: Railway locomotive banner image

**Speaker:** Both members introduce themselves.

---

### Slide 2 — Problem Statement & Motivation

**Content:**
- Indian Railways: 13,000+ trains/day, 23M passengers/day
- Challenge: Fragmented OLTP systems — no strategic delay visibility
- Research question: *"Can a unified OLAP warehouse reveal structural delay patterns across 38M transit records?"*
- Industry significance: schedule optimisation, passenger satisfaction, operational cost

**Speaker:** Member 1

---

### Slide 3 — Dataset Overview

**Content:**
| Source File | Records | Purpose |
|:---|---:|:---|
| `combined_delay.csv` | ~38.5M | Core fact telemetry |
| `station_full_names.csv` | 8,963 | Station dimension |
| `train_details.csv` | 8,720 | Train dimension |
| `combined_schedule.csv` | ~280K | Schedule reference |

- Total raw data: ~1.07 GB
- Observation window: January 2024 – December 2026
- Big Data framework: 4 of 5 Vs (Volume, Velocity, Variety, Veracity)

**Speaker:** Member 1

---

### Slide 4 — Star Schema Architecture

**Content:**
- Diagram of Star Schema (from paper Section III-B)
- Highlight: Fact_TrainDelay at centre
- Emphasise grain: *"One fact = one train arrival at one station on one date"*
- Table: 5 tables, 4 dimension types, 2 measures

> **Key talking point:** Why Star Schema over 3NF? — OLAP query performance, denormalised join paths, intuitive for BI tools.

**Speaker:** Member 1

---

### Slide 5 — ETL Pipeline Design

**Content:**
- Phase 1 → Phase 2 flow diagram
- Phase 1: Dimension loading (Date generated in-memory, Train & Station from CSV)
- Phase 2: Chunked fact loading — 50K rows/chunk, in-memory SK lookup, referential integrity drop
- Key metrics:
  - 38,322,228 rows loaded successfully
  - 4.74 GB final table footprint
  - Execution time: ~18 minutes (full pipeline)

> **Key talking point:** Memory safety — why chunking avoids OOM on 1 GB CSV.

**Speaker:** Member 1

---

### Slide 6 — Infrastructure & Containerisation

**Content:**
- Docker Compose architecture diagram:
  ```
  [Your Mac]
      └── Docker Engine
              ├── railway_dw_mysql   (MySQL 8.0 :3306)
              └── railway_bi_metabase (Metabase :3000)
  ```
- MySQL: `--default-authentication-plugin`, `utf8mb4`, health-check gating
- SQL auto-bootstrap via `/docker-entrypoint-initdb.d/`
- 3 composite B-tree indexes on Fact_TrainDelay for OLAP acceleration

**Speaker:** Member 1

---

### Slide 7 — Analytics Result 1: Delay Severity Distribution

**Content:**
- **Figure 1** (`figure1_delay_severity_pie.png`) — full size on slide
- Key finding callout boxes:
  - ✅ 87% On-Time / Early
  - ⚠️ 8.5% Minor Delay (1–15 min)
  - 🔶 3% Moderate Delay
  - 🔴 1.5% Severe Delay (>45 min)
- Insight: Heavy-tailed distribution — small % severe, large absolute count

**Speaker:** Member 2

---

### Slide 8 — Analytics Result 2: Bottleneck Stations

**Content:**
- **Figure 2** (`figure2_top_10_bottleneck_stations.png`) — full size on slide
- Highlight top 3 stations with labels
- Key finding: Top 10 stations = disproportionate share of total delay-hours
- Insight: Pareto principle — fix 10 stations → largest system-wide improvement

**Speaker:** Member 2

---

### Slide 9 — Analytics Result 3: Monthly Delay Trajectory

**Content:**
- **Figure 3** (`figure3_monthly_delay_trajectory.png`) — full size on slide
- Annotate monsoon window (June–September) and holiday peaks
- 3-month moving average highlights structural trend vs seasonal noise
- Insight: Seasonal patterns → dynamic timetable adjustment is data-justified

**Speaker:** Member 2

---

### Slide 10 — Analytics Result 4: Weekend vs. Weekday

**Content:**
- **Figure 4** (`figure4_weekend_vs_weekday_comparison.png`) — full size on slide
- Side-by-side: (a) Trip Volume, (b) Avg Delay Duration
- Key finding: Weekend Minor+Moderate delay rate is higher; Weekday shows more Severe events
- Insight: Asymmetric intervention strategy needed per day-type

**Speaker:** Member 2

---

### Slide 11 — Metabase BI Dashboard

**Content:**
- Screenshot of Metabase interface at `http://localhost:3000`
- Highlight interactive filters: by Year, Station, Train Type
- Show `vw_RailwayAnalytics` as the source view feeding dashboards
- KPIs displayed:
  - Total trips: 38.32M
  - Total delayed: ~5M (13%)
  - Avg delay (delayed only): ~22 min
  - Worst bottleneck station

**Speaker:** Member 2

---

### Slide 12 — Prescriptive Recommendations

**Content:**
| Recommendation | Evidence Source | Impact |
|:---|:---|:---|
| +12–18 min buffer at top 10 stations | Figure 2 — spatial analytics | Reduce cascades |
| Monsoon timetable extension (June–Sep) | Figure 3 — temporal analytics | Match seasonal reality |
| Weekend reserve capacity on top 20 corridors | Figure 4 — behavioural analytics | Target minor delay reduction |
| 95th percentile early warning threshold | Figure 1 — severity distribution | Catch severe events early |

**Speaker:** Member 2

---

### Slide 13 — Limitations & Future Work

**Content:**
- **Current Limitations:**
  - Batch ETL — no real-time ingestion
  - No passenger volume data to weight delay impact
  - Delay reasons not tagged (maintenance, weather, crew)

- **Future Directions:**
  1. Kafka → Flink real-time streaming ETL
  2. XGBoost delay prediction model on historical warehouse
  3. Network graph delay propagation analysis
  4. NLP root-cause tagging from maintenance logs
  5. Congestion × Delay composite impact score

**Speaker:** Both members

---

### Slide 14 — Conclusion

**Content:**
- ✅ 38.32M fact records loaded into MySQL Star Schema DW
- ✅ 4 analytical dimensions explored with publication-quality figures
- ✅ Prescriptive recommendations directly derived from data
- ✅ Fully reproducible containerised stack (Docker Compose)
- ✅ IEEE paper submitted with all supporting artefacts

> *"Data at the scale of the Indian Railways network, when properly warehoused and queried, reveals structural delay patterns invisible to any individual transaction system."*

**Speaker:** Both members — closing statement together.

---

---

## Part 2: Individual Contribution Breakdown

> For assessment purposes — each member's specific deliverables and responsibilities.

---

### 👷 Member 1 — Data Engineer

**Responsibility Domain:** Database Architecture · ETL Pipeline · Infrastructure

| Deliverable | Details |
|:---|:---|
| **Star Schema Design** | Designed all 5 table schemas (`Fact_TrainDelay`, `Dim_Date`, `Dim_Train`, `Dim_Station`, `Dim_DelayCategory`), surrogate key strategy, and grain definition |
| **SQL DDL Scripts** | Authored all 3 SQL scripts: `01_create_database.sql`, `02_create_star_schema.sql`, `03_indexes_and_views.sql` including 3 composite B-tree indexes and `vw_RailwayAnalytics` view |
| **ETL Phase 1** | Implemented `load_dimensions.py` — in-memory Dim_Date generation (1,096 rows), CSV-to-SQL loading for Dim_Train (8,720) and Dim_Station (8,963) |
| **ETL Phase 2** | Implemented `load_fact.py` — 50K-row chunked ingestion, in-memory SK lookup maps, DateSK derivation, DelayCatSK banding, IsDelayed flag, referential integrity enforcement. Loaded **38,322,228 rows** |
| **Master Orchestrator** | Wrote `run_etl.py` — Phase 1 → Phase 2 orchestration with timing, error handling, and terminal UI banner |
| **Containerisation** | Authored `docker-compose.yml` (MySQL + Metabase services, health-check gating), `Dockerfile` (ETL runner), environment variable configuration |
| **DB Connector** | Implemented `etl/db_connector.py` — SQLAlchemy engine factory with environment variable fallback chain |
| **Paper Sections** | Sections I (Introduction), III (Methodology — all subsections), VI (Conclusion) |

**Technical Stack Used:** MySQL 8.0, Python 3, SQLAlchemy, Pandas, Docker Compose, Bash

---

### 📊 Member 2 — BI & Analytics Lead

**Responsibility Domain:** Analytics · Visualisation · Business Intelligence · Paper Writing

| Deliverable | Details |
|:---|:---|
| **Figure Generation Script** | Authored `generate_paper_figures.py` — 4 publication-quality matplotlib/seaborn figures queried from live MySQL warehouse |
| **Figure 1** | Delay severity donut chart with percentage annotations and 38.32M total trip centre label |
| **Figure 2** | Top 10 bottleneck stations horizontal bar with cumulative delay hours and avg delay per trip |
| **Figure 3** | Monthly delay trajectory dual-axis chart — avg delay line + 3-month MA + delay rate bar subplot |
| **Figure 4** | Weekend vs. weekday grouped bar comparison — trip volume and avg delay duration side-by-side |
| **Metabase Dashboard** | Configured Metabase connection to `railway_dw`, designed interactive dashboards with filters on Year, Station, Train Type, KPI cards |
| **OLAP Query Design** | Wrote all 4 analytical SQL queries (descriptive, spatial, temporal, behavioural) powering both figures and dashboard |
| **DAX Measures** | Authored `bi_reports/dax_measures.txt` — Power BI DAX measures library for all KPIs |
| **Paper Sections** | Abstract, Index Terms, Section II (Literature Review), Section IV (Experimental Results — all sub-sections), Section V (Prescriptive Recommendations) |
| **Presentation Guide** | This document — slide content, flow, and contribution breakdown |

**Technical Stack Used:** Python 3, Matplotlib, Seaborn, Metabase, SQL (MySQL), DAX, Markdown

---

## Part 3: Quick-Reference Project Metrics

| Metric | Value |
|:---|:---|
| **Total Fact Records** | 38,322,228 |
| **Unique Stations** | 8,963 |
| **Unique Train Services** | 8,720 |
| **Observation Period** | Jan 2024 – Dec 2026 |
| **Raw Data Volume** | ~1.07 GB |
| **Fact Table Footprint** | ~4.74 GB (data + indexes) |
| **ETL Chunk Size** | 50,000 rows |
| **MySQL Version** | 8.0.46 |
| **Python Version** | 3.14 |
| **Schema Type** | Kimball Star Schema |
| **BI Tool** | Metabase (port 3000) |
| **Containerisation** | Docker Compose v2 |
| **On-Time Rate** | ~87% |
| **Severe Delay Rate** | ~1.5% |

---

*Document prepared for academic submission and internal assessment.*
