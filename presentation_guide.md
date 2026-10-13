# Presentation & Report Structure Guide
## Indian Railways Data Warehouse — Assignment & Viva Defense

**Group 19 Members:** `MS25905854` (Avinash Perera) & `MS25905922`  
**Course:** Data Warehousing & Business Intelligence (Lecturer: Dr. Dinesh Asanka)  
**Deliverables:**
1. **Report Submission (Word `.docx` / PDF):** Generated via [`generate_submission_docx.py`](file:///Volumes/Mac/docker-sandboxes/railway-dw-project/generate_submission_docx.py) / [`KPI_AND_DATA_MODEL_SPECIFICATION.md`](file:///Volumes/Mac/docker-sandboxes/railway-dw-project/KPI_AND_DATA_MODEL_SPECIFICATION.md) (audited by the lecturer's **n8n AI workflow**).
2. **Presentation Slide Deck (PowerPoint `.pptx` / Google Slides):** Used during the live group presentation & viva defense.

---

## Part 1: Report Structure (Word `.docx` / PDF for n8n AI Audit)

Dr. Dinesh Asanka explicitly stated in the lecture (Transcript pp. 31–32) that all submitted reports are parsed through an **n8n AI workflow** that checks whether:
- You have **8 to 10 Business Events** modeled as Fact tables.
- Your **Star Schema / Fact Constellation** follows the **16-Mark Design Checklist** (Derived Measures, No Operational Bloat, Surrogate vs. Natural Keys, SCD Type 2 with Start/End/IsCurrent, Enriched Date Dimension, Natural Hierarchies in strict order, Explicit FK Joins, Consistent Naming).
- Your **5+ KPIs** each define all **4 Mandatory Properties** (**Value** formula as a percentage/rate, single numeric **Goal**, **Status** Green/Amber/Red bands, and **Trend** period comparison).
- Every measure in your KPI formulas **physically exists with the exact same column name** in your Fact/Dimension tables (**Traceability**).

### Mandatory Sections in Your Word (`.docx`) Report:
1. **Section 1 — Domain Overview & Data Sources:** Brief introduction to Indian Railways delay analytics and the 5 source CSV datasets (`combined_delay.csv`, `combined_schedule.csv`, `train_details.csv`, `station_full_names.csv`, `train_delays.csv`).
2. **Section 2 — Business Events Identification (8 Events):** Table listing all 8 Business Events, their corresponding Fact Table names (`Fact_TrainDelay`, `Fact_TrainSchedule`, `Fact_JourneyDeparture`, `Fact_JourneyArrival`, `Fact_JourneyCancellation`, `Fact_DelayIncident`, `Fact_WeatherObservation`, `Fact_TrainDailySnapshot`), explicit **Grain** ("one row = ..."), and **Raw + Derived Measures**.
3. **Section 3 — Enterprise Bus Matrix:** Visual matrix (`paper/figures/fig_bus_matrix.png` + Markdown/Word table) mapping the **8 Business Events (rows)** against the **8 Conformed Dimensions (columns)** with `X` marks.
4. **Section 4 — Dimensional Model (Star Schema Diagram & Dictionary):**
   - Full **Star Schema diagram with explicit FK join lines** (`paper/figures/fig_star_traindelay.png`).
   - **Dimension Table Dictionary** (showing Surrogate PK, Natural Key, Analytical Attributes, stripped operational bloat like `station_address`, SCD Type 2 columns in `Dim_Train`, Holiday/Weekend/Season enrichment in `Dim_Date`, and Natural Hierarchy drill-down order).
   - **Fact Table Measure Dictionary** (explicitly separating Raw Measures vs. Derived Measures).
5. **Section 5 — 16-Mark Rubric Compliance Checklist:** Table explicitly proving how your design satisfies each of the 8 grading criteria + SQL example of **SCD Type 2** row expiration and insertion.
6. **Section 6 — Key Performance Indicators (5 Complete KPIs):** Structured table/cards for all 5 KPIs showing:
   - **Value:** Explicit mathematical formula using exact schema column names.
   - **Goal:** Single concrete numeric threshold (e.g., `>= 75.0%`, `<= 10.0%`).
   - **Status:** Explicit numeric ranges for **Green**, **Amber**, and **Red**.
   - **Trend:** Month-over-Month (MoM) directional comparison.
7. **Section 7 — KPI-to-Schema Traceability Matrix:** Table mapping every variable in every KPI formula directly to `TableName.ColumnName` and its FK join path.
8. **Section 8 — System & ETL Process Architecture (Bonus):** Updated process diagram (`component_diagram.mmd`), data quality filtering rules, and 68/68 validation summary (`reports/data_validation_report.md`).

---

## Part 2: Presentation Slide Deck Structure (12 Slides — PowerPoint)

During the live presentation (see Transcript pp. 19–41, including **your Group 19 check-in at `1:50:18` on p. 39**), Dr. Dinesh immediately asks to see **two things first**:
1. *"Can I see the design?"* (Your **Star Schema with join lines** + **Enterprise Bus Matrix**)
2. *"Let's see the KPIs — how do you calculate this? Are these measures available in the above design? What is your Goal, Status, and Trend?"*

### Slide-by-Slide Blueprint:

* **Slide 1 — Title & Team Introduction**
  * Project Title: *Indian Railways Transit Delay & Operations Data Warehouse*
  * Group 19: `MS25905854` (Avinash Perera) & `MS25905922`
* **Slide 2 — Business Problem & Source Data Feeds**
  * Operational challenge: 38.4M+ station arrival records across 8,963 stations and 8,720 trains.
  * Table of the 5 operational CSV sources and observation window (`2024–2026`).
* **Slide 3 — The 8 Business Events & Fact Table Grains**
  * Table of all **8 Business Events** (`Fact_TrainDelay`, `Fact_TrainSchedule`, `Fact_JourneyDeparture`, `Fact_JourneyArrival`, `Fact_JourneyCancellation`, `Fact_DelayIncident`, `Fact_WeatherObservation`, `Fact_TrainDailySnapshot`), their exact **Grain**, and loaded row counts.
* **Slide 4 — Enterprise Bus Matrix (8 Events × 8 Conformed Dimensions)**
  * Full-bleed visual of `paper/figures/fig_bus_matrix.png`.
  * Explain how conformed dimensions (`Dim_Date`, `Dim_Time`, `Dim_Station`, `Dim_Train`, etc.) unify all 8 fact tables into a **Fact Constellation**.
* **Slide 5 — Primary Star Schema (`Fact_TrainDelay`) & Derived Measures**
  * Full-bleed visual of `paper/figures/fig_star_traindelay.png` showing explicit `N : 1` foreign key join lines.
  * Call out **Raw Measure** (`DelayMinutes`) vs. **5 Derived Measures** (`TripCount`, `IsDelayed`, `PunctualFlag`, `SevereDelayFlag`, `ExcessDelayMinutes`) and **Degenerate Dimension** (`StopSequence`).
* **Slide 6 — Conformed Dimensions, Hierarchies & Anti-Pattern Compliance**
  * Show how the design avoids every student mistake from Lecture Checklist:
    * **Surrogate vs. Natural Keys:** `StationSK`/`TrainSK` (PK & Fact FK) vs. `StationCode`/`TrainNumber` (NK in Dimension only).
    * **Operational Bloat Removed:** `station_address` stripped from `Dim_Station`.
    * **Verbose Descriptors:** `EXP-TRAINS` $\rightarrow$ `Express`, `NR` $\rightarrow$ `Northern Railway`.
    * **Natural Hierarchies (Strict Order in Single Table):**
      * `Dim_Date`: `Year > Quarter > Month > Day`
      * `Dim_Station`: `ZoneName > StationName`
      * `Dim_Train`: `ServiceClass > TrainTypeName > TrainNumber`
* **Slide 7 — SCD Type 2 (`Dim_Train`) & Enriched `Dim_Date` / `Dim_Time`**
  * Show `Dim_Train` SCD Type 2 columns (`EffectiveStartDate`, `EffectiveEndDate`, `IsCurrent`) with a concrete before/after row example when a train is reclassified from `Express` to `Superfast`.
  * Show `Dim_Date` enrichment (`IsWeekend`, `IsHoliday`, `HolidayName`, `Season`) and `Dim_Time` (`TimeOfDayBand`, `IsPeakHour`).
* **Slide 8 — KPI Overview: The 5 Rate/Ratio KPIs & 4 Mandatory Properties**
  * Summary table of all **5 KPIs** showing **Value (Formula)**, **Goal (Single Target)**, **Status (Green / Amber / Red ranges)**, and **Trend (MoM)**:
    1. **Network Punctuality Rate (%)** — Goal: $\ge 75\%$
    2. **Severe Delay Rate (%)** — Goal: $\le 10\%$
    3. **Average Excess Delay per Trip (min)** — Goal: $\le 10\text{ min}$
    4. **Weekend Delay Uplift (%)** — Goal: $\le 5\%$
    5. **Peak-Hour Delay Surge (%)** — Goal: $\le 10\%$
* **Slide 9 — KPI Traceability Matrix (Proving Every KPI Formula Exists in the Schema)**
  * Side-by-side mapping: `KPI Formula Variable` $\rightarrow$ `Physical Fact/Dimension Column` (`Fact_TrainDelay.PunctualFlag`, `Fact_TrainDelay.TripCount`, `Dim_Date.IsWeekend`, `Dim_Time.IsPeakHour`, etc.).
  * *Why this slide is crucial:* Directly answers Dr. Dinesh's question from page 39: *"So, are these parameters available in the previous design, in the above design?"*
* **Slide 10 — End-to-End ETL & Data Warehouse Process Architecture**
  * Updated process diagram (`component_diagram.mmd` / `paper/figures/fig_etl_pipeline.png`) showing the 4 ETL phases, data quality rules (null delay exclusion, $>1440\text{ min}$ outlier filter, 5-digit train number normalization), and 68/68 automated validation checks.
* **Slide 11 — Analytical Dashboard & Monthly KPI Trends**
  * Charts from `paper/figures/` + monthly KPI table from `vw_KPI_Monthly`, `vw_KPI_WeekendUplift`, and `vw_KPI_PeakSurge` showing actual values, Green/Amber/Red status, and MoM trend.
* **Slide 12 — Conclusion & Viva Q&A Readiness**
  * Summary of achievements: 8 Business Events, 8 Conformed Dimensions, 16/16 Rubric compliance, 5 fully traceable KPIs, and live MySQL 8.0 + Docker implementation.
