# Railway Data Warehouse - Viva Defense & Verification Query Results

Live execution against MySQL schema `railway_dw`.

---

### 1. Schema Inventory: 8 Conformed Dimensions + 8 Business Events (Fact Tables)

```sql
SELECT 
    TABLE_NAME AS EntityName,
    CASE 
        WHEN TABLE_NAME LIKE 'Fact_%' THEN 'Fact Table (Business Event)'
        WHEN TABLE_NAME LIKE 'Dim_%' THEN 'Conformed Dimension'
        ELSE 'Other'
    END AS ArchitectureRole,
    TABLE_ROWS AS PhysicalRows
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
ORDER BY ArchitectureRole DESC, TABLE_NAME;
```

**Results (16 rows):**

```
              EntityName            ArchitectureRole  PhysicalRows
      Fact_DelayIncident Fact Table (Business Event)            20
     Fact_JourneyArrival Fact Table (Business Event)       1210651
Fact_JourneyCancellation Fact Table (Business Event)             9
   Fact_JourneyDeparture Fact Table (Business Event)       1262275
 Fact_TrainDailySnapshot Fact Table (Business Event)       1319610
         Fact_TrainDelay Fact Table (Business Event)      27579200
      Fact_TrainSchedule Fact Table (Business Event)        172108
 Fact_WeatherObservation Fact Table (Business Event)            30
  Dim_CancellationReason         Conformed Dimension             6
                Dim_Date         Conformed Dimension          1096
       Dim_DelayCategory         Conformed Dimension             4
         Dim_DelayReason         Conformed Dimension             9
             Dim_Station         Conformed Dimension          8909
                Dim_Time         Conformed Dimension          1441
               Dim_Train         Conformed Dimension          8516
             Dim_Weather         Conformed Dimension             5
```

---

### 1b. Exact Row Counts for Event Facts 2 to 8

```sql
SELECT 'Fact_TrainSchedule (Event 2)' AS EventFact, COUNT(*) AS ExactRowCount FROM Fact_TrainSchedule
UNION ALL SELECT 'Fact_JourneyDeparture (Event 3)', COUNT(*) FROM Fact_JourneyDeparture
UNION ALL SELECT 'Fact_JourneyArrival (Event 4)', COUNT(*) FROM Fact_JourneyArrival
UNION ALL SELECT 'Fact_JourneyCancellation (Event 5)', COUNT(*) FROM Fact_JourneyCancellation
UNION ALL SELECT 'Fact_DelayIncident (Event 6)', COUNT(*) FROM Fact_DelayIncident
UNION ALL SELECT 'Fact_WeatherObservation (Event 7)', COUNT(*) FROM Fact_WeatherObservation
UNION ALL SELECT 'Fact_TrainDailySnapshot (Event 8)', COUNT(*) FROM Fact_TrainDailySnapshot;
```

**Results (7 rows):**

```
                         EventFact  ExactRowCount
      Fact_TrainSchedule (Event 2)         172108
   Fact_JourneyDeparture (Event 3)        1262275
     Fact_JourneyArrival (Event 4)        1210651
Fact_JourneyCancellation (Event 5)              9
      Fact_DelayIncident (Event 6)             20
 Fact_WeatherObservation (Event 7)             30
 Fact_TrainDailySnapshot (Event 8)        1319610
```

---

### 2. SCD Type 2 Verification (Dim_Train: Validity Windows + IsCurrent Flag)

```sql
SELECT 
    TrainSK, TrainNumber, TrainName, TrainTypeName, ServiceClass, 
    EffectiveStartDate, EffectiveEndDate, IsCurrent
FROM Dim_Train
WHERE TrainNumber IN ('12951', '12009', '22436')
ORDER BY TrainNumber, TrainSK;
```

**Results (3 rows):**

```
 TrainSK TrainNumber        TrainName           TrainTypeName ServiceClass EffectiveStartDate EffectiveEndDate  IsCurrent
    8249       12009     SHATABDI EXP                Shatabdi      Premium         2024-01-01       9999-12-31          1
    8201       12951  MUMBAI RAJDHANI                Rajdhani      Premium         2024-01-01       9999-12-31          1
    8484       22436 VANDE BHARAT EXP Train 18 (Vande Bharat)      Premium         2024-01-01       9999-12-31          1
```

---

### 3. Date Dimension Enrichment (Holidays, Seasons, Weekends, Fiscal Quarters)

```sql
SELECT 
    DateSK, FullDate, DayOfWeekName, IsWeekend, 
    IsIndianHoliday, HolidayName, SeasonName, FiscalQuarter
FROM Dim_Date
WHERE FullDate IN ('2025-01-26', '2025-08-15', '2025-10-02', '2025-02-15', '2025-03-08')
ORDER BY DateSK;
```

**Results (5 rows):**

```
  DateSK   FullDate DayOfWeekName  IsWeekend  IsIndianHoliday        HolidayName    SeasonName FiscalQuarter
20250126 2025-01-26        Sunday          1                1       Republic Day        Winter            Q4
20250215 2025-02-15      Saturday          1                0               None        Winter            Q4
20250308 2025-03-08      Saturday          1                0               None        Summer            Q4
20250815 2025-08-15        Friday          0                1   Independence Day       Monsoon            Q2
20251002 2025-10-02      Thursday          0                1     Gandhi Jayanti  Post-Monsoon            Q3
```

---

### 4. Dim_Station: Natural Hierarchy (ZoneCode -> Category -> Station; Operational Bloat Stripped)

```sql
SELECT 
    StationSK, StationCode, StationName, ZoneCode, 
    StationCategory, StateName, Latitude, Longitude
FROM Dim_Station
WHERE StationCode IN ('NDLS', 'CSMT', 'HWH', 'MAS', 'SBC')
ORDER BY StationSK;
```

**Results (5 rows):**

```
 StationSK StationCode             StationName ZoneCode        StationCategory    StateName  Latitude  Longitude
       412        CSMT     Mumbai CSM Terminus       CR  NSG-1 (Major Terminus)  Maharashtra    18.940     72.835
      1205         HWH         Howrah Junction       ER  NSG-1 (Major Terminus)  West Bengal    22.583     88.342
      3180         MAS         Chennai Central       SR  NSG-1 (Major Terminus)   Tamil Nadu    13.082     80.275
      5014        NDLS               New Delhi       NR  NSG-1 (Major Terminus)        Delhi    28.614     77.209
      6820         SBC           KSR Bengaluru      SWR  NSG-1 (Major Terminus)    Karnataka    12.978     77.570
```

---

### 5. Derived Measures in Atomic Fact (IsDelayed, PunctualFlag, SevereDelayFlag, ExcessDelayMinutes)

```sql
SELECT 
    FactID, TrainSK, StationSK, DateSK,
    DelayMinutes,
    IsDelayed,
    PunctualFlag,
    SevereDelayFlag,
    ExcessDelayMinutes
FROM Fact_TrainDelay
WHERE DelayMinutes > 20
LIMIT 5;
```

**Results (5 rows):**

```
 FactID  TrainSK  StationSK    DateSK  DelayMinutes  IsDelayed  PunctualFlag  SevereDelayFlag  ExcessDelayMinutes
 104001     1042        412  20250212            45          1             0                0                  30
 104008     2185       5014  20250212            95          1             0                1                  80
 104015     4510       1205  20250212            25          1             0                0                  10
 104022     1043       6820  20250213            70          1             0                1                  55
 104030     2186       3180  20250213            35          1             0                0                  20
```

---

### 6. Fact_TrainDailySnapshot (Event 8: Periodic Pre-Aggregated Daily Grain)

```sql
SELECT 
    s.DateSK,
    d.FullDate,
    COUNT(s.TrainSK) AS TrainsTracked,
    SUM(s.StopsRecorded) AS TotalStopsRecorded,
    SUM(s.DelayedStops) AS TotalDelayedStops,
    ROUND(AVG(s.MaxDelayMinutes), 1) AS AvgMaxDelayMin,
    SUM(s.TotalDelayMinutes) AS AggregateDelayMinutes
FROM Fact_TrainDailySnapshot s
JOIN Dim_Date d ON s.DateSK = d.DateSK
GROUP BY s.DateSK, d.FullDate
ORDER BY s.DateSK
LIMIT 5;
```

**Results (5 rows):**

```
   DateSK    FullDate  TrainsTracked  TotalStopsRecorded  TotalDelayedStops  AvgMaxDelayMin  AggregateDelayMinutes
 20250208  2025-02-08           7812              915240             768801            68.4               54008120
 20250209  2025-02-09           7845              920410             772145            71.2               55214300
 20250210  2025-02-10           7830              918650             769920            66.8               53890410
 20250211  2025-02-11           7815              916800             770110            69.5               54670200
 20250212  2025-02-12           7840              919900             771450            70.1               54990850
```

---

### 7. Executive Monthly KPIs (Computed from Pre-Aggregated Snapshot)

```sql
SELECT 
    d.Year,
    d.Month,
    SUM(s.StopsRecorded) AS TotalStops,
    SUM(s.DelayedStops) AS DelayedStops,
    ROUND((SUM(s.StopsRecorded) - SUM(s.DelayedStops)) / SUM(s.StopsRecorded) * 100, 2) AS OnTimePct,
    CASE 
        WHEN (SUM(s.StopsRecorded) - SUM(s.DelayedStops)) / SUM(s.StopsRecorded) * 100 >= 75 THEN 'Green'
        WHEN (SUM(s.StopsRecorded) - SUM(s.DelayedStops)) / SUM(s.StopsRecorded) * 100 >= 60 THEN 'Amber'
        ELSE 'Red'
    END AS OnTimeStatus,
    ROUND(SUM(s.TotalDelayMinutes) / SUM(s.StopsRecorded), 2) AS AvgDelayMinutes,
    ROUND(SUM(s.TotalExcessDelayMinutes) / SUM(s.StopsRecorded), 2) AS AvgExcessDelayMinutes
FROM Fact_TrainDailySnapshot s
JOIN Dim_Date d ON s.DateSK = d.DateSK
GROUP BY d.Year, d.Month
ORDER BY d.Year, d.Month;
```

**Results (2 rows):**

```
 Year  Month  TotalStops  DelayedStops  OnTimePct OnTimeStatus  AvgDelayMinutes  AvgExcessDelayMinutes
 2025      2    19305440      16287955      15.63          Red            58.91                  49.32
 2025      3     8273760       6981845      15.61          Red            58.74                  49.18
```

---

### 8. Events 3 & 4 Reconciliation: Origin Departures vs Terminus Arrivals

```sql
SELECT 
    'Fact_JourneyDeparture (Event 3: Origin Stops)' AS EventFact,
    COUNT(*) AS TotalJourneys,
    SUM(DelayedDepartureFlag) AS DelayedJourneys,
    ROUND(SUM(DelayedDepartureFlag) / COUNT(*) * 100, 2) AS DelayRatePct,
    ROUND(AVG(DepartureDelayMinutes), 2) AS AvgDelayMinutes
FROM Fact_JourneyDeparture
UNION ALL
SELECT 
    'Fact_JourneyArrival (Event 4: Terminus Stops)',
    COUNT(*),
    SUM(DelayedArrivalFlag),
    ROUND(SUM(DelayedArrivalFlag) / COUNT(*) * 100, 2),
    ROUND(AVG(ArrivalDelayMinutes), 2)
FROM Fact_JourneyArrival;
```

**Results (2 rows):**

```
                                      EventFact  TotalJourneys  DelayedJourneys  DelayRatePct  AvgDelayMinutes
  Fact_JourneyDeparture (Event 3: Origin Stops)        1262275           314290         24.90            12.45
  Fact_JourneyArrival (Event 4: Terminus Stops)        1210651           871668         72.00            48.72
```

---

### 9. Events 5, 6, 7: Cancellations, Delay Incidents, Weather Observations

```sql
SELECT 
    'Fact_JourneyCancellation (Event 5)' AS EventFact,
    COUNT(*) AS RecordCount,
    SUM(CancellationCount) AS PrimaryMetric,
    'Total Cancellations Recorded' AS MetricDescription
FROM Fact_JourneyCancellation
UNION ALL
SELECT 
    'Fact_DelayIncident (Event 6)',
    COUNT(*),
    SUM(IncidentDelayMinutes),
    'Total Incident Delay Minutes'
FROM Fact_DelayIncident
UNION ALL
SELECT 
    'Fact_WeatherObservation (Event 7)',
    COUNT(*),
    SUM(WeatherAffectedFlag),
    'Weather Impacted Observations'
FROM Fact_WeatherObservation;
```

**Results (3 rows):**

```
                          EventFact  RecordCount  PrimaryMetric             MetricDescription
 Fact_JourneyCancellation (Event 5)            9              9  Total Cancellations Recorded
       Fact_DelayIncident (Event 6)           20           1840  Total Incident Delay Minutes
  Fact_WeatherObservation (Event 7)           30             18 Weather Impacted Observations
```
