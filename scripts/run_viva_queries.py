#!/usr/bin/env python3
"""
scripts/run_viva_queries.py - Fast SQL verification suite for the
Railway Data Warehouse viva defense and rubric audit.
Writes all executed queries and output tables directly to reports/viva_query_results.md.
"""
import os
import sys
import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from etl.db_connector import get_engine

OUT_FILE = os.path.join(PROJECT_ROOT, 'reports', 'viva_query_results.md')

def run_query(conn, out_fh, title, sql, max_rows=15):
    print(f"Executing: {title}...", flush=True)
    out_fh.write(f"\n### {title}\n\n")
    out_fh.write("```sql\n" + sql.strip() + "\n```\n\n")
    df = pd.read_sql(text(sql), conn)
    out_fh.write(f"**Results ({len(df)} rows):**\n\n")
    out_fh.write("```\n")
    if len(df) > max_rows:
        out_fh.write(df.head(max_rows).to_string(index=False) + "\n")
        out_fh.write(f"... [{len(df) - max_rows} additional rows omitted]\n")
    else:
        out_fh.write(df.to_string(index=False) + "\n")
    out_fh.write("```\n\n")
    out_fh.flush()

def main():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    engine = get_engine()
    with open(OUT_FILE, 'w', encoding='utf-8') as out_fh:
        out_fh.write("# Railway Data Warehouse - Viva Defense & Verification Query Results\n\n")
        out_fh.write("Live execution against MySQL schema `railway_dw`.\n\n")
        
        with engine.connect() as conn:
            # 1. Row counts across all 8 Dimensions and 8 Fact tables
            sql_counts = """
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
            """
            run_query(conn, out_fh, "1. Schema Inventory: 8 Conformed Dimensions + 8 Business Events (Fact Tables)", sql_counts, 20)

            # 1b. Exact counts for facts
            sql_exact = """
            SELECT 'Fact_TrainSchedule (Event 2)' AS EventFact, COUNT(*) AS ExactRowCount FROM Fact_TrainSchedule
            UNION ALL SELECT 'Fact_JourneyDeparture (Event 3)', COUNT(*) FROM Fact_JourneyDeparture
            UNION ALL SELECT 'Fact_JourneyArrival (Event 4)', COUNT(*) FROM Fact_JourneyArrival
            UNION ALL SELECT 'Fact_JourneyCancellation (Event 5)', COUNT(*) FROM Fact_JourneyCancellation
            UNION ALL SELECT 'Fact_DelayIncident (Event 6)', COUNT(*) FROM Fact_DelayIncident
            UNION ALL SELECT 'Fact_WeatherObservation (Event 7)', COUNT(*) FROM Fact_WeatherObservation
            UNION ALL SELECT 'Fact_TrainDailySnapshot (Event 8)', COUNT(*) FROM Fact_TrainDailySnapshot;
            """
            run_query(conn, out_fh, "1b. Exact Row Counts for Event Facts 2 to 8", sql_exact, 10)

            # 2. SCD Type 2 Verification in Dim_Train
            sql_scd2 = """
            SELECT 
                TrainSK, TrainNumber, TrainName, TrainTypeName, ServiceClass, 
                EffectiveStartDate, EffectiveEndDate, IsCurrent
            FROM Dim_Train
            WHERE TrainNumber IN ('12951', '12009', '22436')
            ORDER BY TrainNumber, TrainSK;
            """
            run_query(conn, out_fh, "2. SCD Type 2 Verification (Dim_Train: Validity Windows + IsCurrent Flag)", sql_scd2)

            # 3. Date Dimension Enrichment
            sql_date = """
            SELECT 
                DateSK, FullDate, DayOfWeekName, IsWeekend, 
                IsIndianHoliday, HolidayName, SeasonName, FiscalQuarter
            FROM Dim_Date
            WHERE FullDate IN ('2025-01-26', '2025-08-15', '2025-10-02', '2025-02-15', '2025-03-08')
            ORDER BY DateSK;
            """
            run_query(conn, out_fh, "3. Date Dimension Enrichment (Holidays, Seasons, Weekends, Fiscal Quarters)", sql_date)

            # 4. Station Dimension (Natural Hierarchy & Cleaned Attributes)
            sql_station = """
            SELECT 
                StationSK, StationCode, StationName, ZoneCode, 
                StationCategory, StateName, Latitude, Longitude
            FROM Dim_Station
            WHERE StationCode IN ('NDLS', 'CSMT', 'HWH', 'MAS', 'SBC')
            ORDER BY StationSK;
            """
            run_query(conn, out_fh, "4. Dim_Station: Natural Hierarchy (ZoneCode -> Category -> Station; Operational Bloat Stripped)", sql_station)

            # 5. Derived Measures in Fact_TrainDelay
            sql_derived = """
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
            """
            run_query(conn, out_fh, "5. Derived Measures in Atomic Fact (IsDelayed, PunctualFlag, SevereDelayFlag, ExcessDelayMinutes)", sql_derived)

            # 6. Periodic Snapshot Aggregated Grain (Event 8)
            sql_snap = """
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
            """
            run_query(conn, out_fh, "6. Fact_TrainDailySnapshot (Event 8: Periodic Pre-Aggregated Daily Grain)", sql_snap)

            # 7. Executive Monthly KPIs Computed from Periodic Snapshot
            sql_kpi = """
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
            """
            run_query(conn, out_fh, "7. Executive Monthly KPIs (Computed from Pre-Aggregated Snapshot)", sql_kpi)

            # 8. Event 3 & 4: Origin Departure vs Terminus Arrival Fact Reconciliation
            sql_od = """
            SELECT 
                'Fact_JourneyDeparture' AS EventFact,
                COUNT(*) AS TotalJourneys,
                SUM(DelayedDepartureFlag) AS DelayedCount,
                ROUND(AVG(DepartureDelayMinutes), 2) AS AvgDelayMinutes
            FROM Fact_JourneyDeparture
            UNION ALL
            SELECT 
                'Fact_JourneyArrival',
                COUNT(*),
                SUM(DelayedArrivalFlag),
                ROUND(AVG(ArrivalDelayMinutes), 2)
            FROM Fact_JourneyArrival;
            """
            run_query(conn, out_fh, "8. Events 3 & 4 Reconciliation: Origin Departures vs Terminus Arrivals", sql_od)

            # 9. Events 5, 6, 7: Journey Feed Verification
            sql_feed = """
            SELECT 
                'Fact_JourneyCancellation (Event 5)' AS EventFact,
                COUNT(*) AS RecordCount,
                SUM(CancellationCount) AS PrimaryMetric
            FROM Fact_JourneyCancellation
            UNION ALL
            SELECT 
                'Fact_DelayIncident (Event 6)',
                COUNT(*),
                SUM(IncidentDelayMinutes)
            FROM Fact_DelayIncident
            UNION ALL
            SELECT 
                'Fact_WeatherObservation (Event 7)',
                COUNT(*),
                SUM(WeatherAffectedFlag)
            FROM Fact_WeatherObservation;
            """
            run_query(conn, out_fh, "9. Events 5, 6, 7: Cancellations, Delay Incidents, Weather Observations", sql_feed)

    print(f"✅ All viva queries completed! Results written to {OUT_FILE}", flush=True)

if __name__ == '__main__':
    main()
