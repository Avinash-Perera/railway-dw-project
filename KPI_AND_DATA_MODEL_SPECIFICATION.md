# Indian Railways Transit Delay Analytics
## Data Warehouse Model & KPI Specification Document

---

## 1. Dimensional Data Model (Kimball Star Schema)

This dimensional model supports large-scale Online Analytical Processing (OLAP) across **38,322,228 fact records**. The grain of the fact table represents **one train arrival at one specific station on one specific calendar date**.

```text
                  +-----------------------------------+
                  |            Dim_Station            |
                  +-----------------------------------+
                  | * StationSK (PK)                  |
                  | - StationCode                     |
                  | - StationName                     |
                  +-----------------+-----------------+
                                    | 1
                                    |
                                    | M
+----------------------+  M       +---+--------------------+       M  +----------------------+
|       Dim_Date       +----------+    Fact_TrainDelay     +----------+      Dim_Train       |
+----------------------+          +------------------------+          +----------------------+
| * DateSK (PK)        |        1 | * FactID (PK)          | 1        | * TrainSK (PK)       |
| - FullDate           |          | # DateSK (FK)          |          | - TrainNumber        |
| - Year               |          | # StationSK (FK)       |          | - TrainName          |
| - Quarter            |          | # TrainSK (FK)         |          | - TrainType          |
| - Month              |          | # DelayCatSK (FK)      |          +----------------------+
| - MonthName          |          |                        |
| - Day                |          | --- MEASURES ---       |
| - DayOfWeek          |          | - DelayMinutes - Measure (Additive)
| - IsWeekend          |          | - IsDelayed    - Measure (Semi-Additive / Flag)
+----------------------+          | - TripCount    - Measure (Additive / COUNT(*))
                                  +-----------+------------+
                                              | M
                                              |
                                              | 1
                                  +-----------+------------+
                                  |   Dim_DelayCategory    |
                                  +------------------------+
                                  | * DelayCatSK (PK)      |
                                  | - CategoryName         |
                                  | - MinDelayMinutes      |
                                  | - MaxDelayMinutes      |
                                  +------------------------+
```

### Table & Measure Dictionary

#### 1. Central Fact Table: `Fact_TrainDelay`
*   **FactID**: Surrogate primary key (`BIGINT AUTO_INCREMENT`).
*   **Foreign Keys**: `DateSK`, `StationSK`, `TrainSK`, `DelayCatSK`.
*   **`DelayMinutes` (Measure)**: Numeric additive measure recording the delay in minutes ($\le 0$ means early or on-time).
*   **`IsDelayed` (Measure / Flag)**: Binary flag (`0` = On-Time/Early, `1` = Delayed $>0$ minutes).
*   **`TripCount` (Measure)**: Base count of individual train arrival events (`COUNT(*)`).

#### 2. Dimension Tables
*   **`Dim_Station`**: Conformed spatial dimension (8,963 stations). Attributes: `StationSK` (PK), `StationCode`, `StationName`.
*   **`Dim_Date`**: Conformed calendar dimension (1,096 days). Attributes: `DateSK` (PK, YYYYMMDD), `FullDate`, `Year`, `Quarter`, `Month`, `MonthName`, `Day`, `DayOfWeek`, `IsWeekend` (0/1).
*   **`Dim_Train`**: Conformed service dimension (8,720 trains). Attributes: `TrainSK` (PK), `TrainNumber`, `TrainName`, `TrainType` (Passenger/Express/Superfast/Freight).
*   **`Dim_DelayCategory`**: Banded severity dimension. Attributes: `DelayCatSK` (PK: 1 to 4), `CategoryName` ('On-Time / Early', 'Minor Delay', 'Moderate Delay', 'Severe Delay'), `MinDelayMinutes`, `MaxDelayMinutes`.

---

## 2. Key Performance Indicators (KPI) Matrix

To satisfy executive benchmarking and enable cross-station/department comparison, all metrics are normalized as **percentages, ratios, and rates** rather than unstandardized raw totals.

| # | KPI (Percentage / Rate) | Calculation (Formula using Schema Measures) | Business Purpose & Goal | Comparison & Drill-down Hierarchy |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Network Punctuality Rate (%)** | $$\frac{\sum(\text{IsDelayed} = 0)}{\sum(\text{TripCount})} \times 100$$ | **Purpose**: Measures global transit punctuality and schedule adherence across all network services.<br>**Goal**: $\ge 90.0\%$ On-Time | **Trend**: Current Month vs. Previous Month (MoM), Weekday vs. Weekend.<br>**Drill-down**: Year $\rightarrow$ Quarter $\rightarrow$ Month $\rightarrow$ Station $\rightarrow$ Train |
| **2** | **Severe Bottleneck Ratio (%)** | $$\frac{\sum(\text{DelayCatSK} = 4)}{\sum(\text{TripCount})} \times 100$$ | **Purpose**: Pinpoints localized station congestion causing cascading failures ($>45$ min delay).<br>**Goal**: $\le 2.0\%$ Severe Delays | **Trend**: Station vs. National Average benchmark.<br>**Drill-down**: Region / Division $\rightarrow$ Station $\rightarrow$ Delay Category |
| **3** | **Passenger Reliability Score (%)** | $$\frac{\sum(\text{IsDelayed} = 0 \text{ AND } \text{TrainType} \ne \text{'Freight'})}{\sum(\text{TripCount} \text{ WHERE } \text{TrainType} \ne \text{'Freight'})} \times 100$$ | **Purpose**: Evaluates service reliability specifically impacting passenger transit and citizen satisfaction.<br>**Goal**: $\ge 95.0\%$ Passenger Reliability | **Trend**: Passenger Services vs. Freight Fleet.<br>**Drill-down**: TrainType (Express, Mail, Local) $\rightarrow$ TrainNumber |
| **4** | **Monsoon Vulnerability Index (%)** | $$\left(\frac{\text{AVG}(\text{DelayMinutes})_{\text{Monsoon}}}{\text{AVG}(\text{DelayMinutes})_{\text{Dry Season}}} - 1\right) \times 100$$ | **Purpose**: Quantifies seasonal network performance deterioration during heavy monsoon precipitation.<br>**Goal**: Keep monsoon degradation $\le 15.0\%$ above baseline | **Trend**: Monsoon Window (Jun–Sep) vs. Dry Window (Feb–May).<br>**Drill-down**: Year $\rightarrow$ Season $\rightarrow$ Month $\rightarrow$ High-Risk Corridor |
| **5** | **Peak-Hour Congestion Surge Rate (%)** | $$\frac{\text{AVG}(\text{DelayMinutes})_{\text{Peak}} - \text{AVG}(\text{DelayMinutes})_{\text{OffPeak}}}{\text{AVG}(\text{DelayMinutes})_{\text{OffPeak}}} \times 100$$ | **Purpose**: Quantifies excess queue delay introduced during morning and evening rush hours for capacity planning.<br>**Goal**: $\le 10.0\%$ Surge Delay | **Trend**: Peak Rush Hours vs. Off-Peak Operating Hours.<br>**Drill-down**: Station $\rightarrow$ DayOfWeek $\rightarrow$ Hour of Day |

---

## 3. Mapping KPIs to Major Business Views

The defined KPIs provide complete visibility across four distinct business perspectives:

1.  **Operational View** $\rightarrow$ **KPI 1 (Network Punctuality Rate)**
    *   Directly tracks day-to-day dispatch execution and operational schedule compliance.
2.  **Management & Infrastructure Planning View** $\rightarrow$ **KPI 2 (Severe Bottleneck Ratio) & KPI 5 (Peak-Hour Congestion Surge Rate)**
    *   Isolates high-friction junction nodes needing track expansion, platform restructuring, or revised buffer allocation.
3.  **Customer / Citizen View** $\rightarrow$ **KPI 3 (Passenger Reliability Score)**
    *   Protects commuter and intercity passenger transit experience independent of industrial freight operations.
4.  **Environmental / Seasonal View** $\rightarrow$ **KPI 4 (Monsoon Vulnerability Index)**
    *   Informs seasonal timetable adjustments and preventative track maintenance prior to monsoon onset.

---

## 4. Connection to Four Analytics Types

| Analytics Stage | Associated Dashboard Card & Question | Core KPI / Output Metric |
| :--- | :--- | :--- |
| **Descriptive Analytics** *(What happened?)* | Delay Severity Donut Chart & Punctuality Gauge | **KPI 1: Network Punctuality Rate (87.0%)** and volume breakdown by severity class. |
| **Diagnostic Analytics** *(Why did it happen?)* | Top 10 Severe Delay Stations Horizontal Bar Chart | **KPI 2: Severe Bottleneck Ratio**, identifying major junction nodes amplifying delays $2.3\times$ higher than average. |
| **Predictive Analytics** *(What will happen?)* | Monthly Delay Trajectory Line Chart | **KPI 4: Monsoon Vulnerability Index**, anticipating seasonal spikes peaking in July at double the baseline. |
| **Prescriptive Analytics** *(What should we do?)* | Recommended Schedule Buffer Table | Recommending tiered timetable adjustments (+12 to 18 mins buffer at top bottlenecks) to prevent cascade propagation. |
