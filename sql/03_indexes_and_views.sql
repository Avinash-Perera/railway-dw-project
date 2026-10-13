-- ========================================================
-- 03. INDEXES AND ANALYTICAL / KPI VIEWS
-- ========================================================
USE railway_dw;

-- Indexes supporting the dominant OLAP patterns on the two loaded fact tables
CREATE INDEX idx_fact_date_station ON Fact_TrainDelay(DateSK, StationSK);
CREATE INDEX idx_fact_train_cat    ON Fact_TrainDelay(TrainSK, DelayCatSK);
CREATE INDEX idx_fact_time         ON Fact_TrainDelay(TimeSK);
CREATE INDEX idx_sched_train       ON Fact_TrainSchedule(TrainSK, StopSequence);

-- Denormalised analytical view (feeds Metabase / Power BI)
CREATE OR REPLACE VIEW vw_RailwayAnalytics AS
SELECT
    f.FactID,
    d.FullDate,
    d.Year,
    d.Quarter,
    d.MonthName,
    d.DayOfWeek,
    d.IsWeekend,
    d.IsHoliday,
    d.HolidayName,
    d.Season,
    tm.TimeOfDayBand,
    tm.IsPeakHour,
    s.StationCode,
    s.StationName,
    s.ZoneName,
    t.TrainNumber,
    t.TrainName,
    t.TrainTypeName,
    t.ServiceClass,
    c.CategoryName AS DelaySeverity,
    f.StopSequence,
    f.DelayMinutes,
    f.TripCount,
    f.IsDelayed,
    f.PunctualFlag,
    f.SevereDelayFlag,
    f.ExcessDelayMinutes
FROM Fact_TrainDelay f
JOIN Dim_Date d          ON f.DateSK = d.DateSK
JOIN Dim_Time tm         ON f.TimeSK = tm.TimeSK
JOIN Dim_Station s       ON f.StationSK = s.StationSK
JOIN Dim_Train t         ON f.TrainSK = t.TrainSK
JOIN Dim_DelayCategory c ON f.DelayCatSK = c.DelayCatSK;

-- KPI 1-3 by month with Goal / Status / Trend (MoM)
CREATE OR REPLACE VIEW vw_KPI_Monthly AS
SELECT
    m.Year,
    m.Month,
    m.TotalTrips,
    m.PunctualityRatePct,
    CASE WHEN m.PunctualityRatePct >= 75 THEN 'Green'
         WHEN m.PunctualityRatePct >= 60 THEN 'Amber' ELSE 'Red' END AS PunctualityStatus,
    ROUND(m.PunctualityRatePct - LAG(m.PunctualityRatePct) OVER (ORDER BY m.Year, m.Month), 2) AS PunctualityMoMChangePts,
    m.SevereDelayRatePct,
    CASE WHEN m.SevereDelayRatePct <= 10 THEN 'Green'
         WHEN m.SevereDelayRatePct <= 15 THEN 'Amber' ELSE 'Red' END AS SevereDelayStatus,
    ROUND(m.SevereDelayRatePct - LAG(m.SevereDelayRatePct) OVER (ORDER BY m.Year, m.Month), 2) AS SevereDelayMoMChangePts,
    m.AvgExcessDelayMin,
    CASE WHEN m.AvgExcessDelayMin <= 10 THEN 'Green'
         WHEN m.AvgExcessDelayMin <= 20 THEN 'Amber' ELSE 'Red' END AS ExcessDelayStatus,
    ROUND(m.AvgExcessDelayMin - LAG(m.AvgExcessDelayMin) OVER (ORDER BY m.Year, m.Month), 2) AS ExcessDelayMoMChangeMin
FROM (
    SELECT
        d.Year,
        d.Month,
        SUM(f.TripCount) AS TotalTrips,
        ROUND(SUM(f.PunctualFlag)    / SUM(f.TripCount) * 100, 2) AS PunctualityRatePct,
        ROUND(SUM(f.SevereDelayFlag) / SUM(f.TripCount) * 100, 2) AS SevereDelayRatePct,
        ROUND(SUM(f.ExcessDelayMinutes) / SUM(f.TripCount), 2)    AS AvgExcessDelayMin
    FROM Fact_TrainDelay f
    JOIN Dim_Date d ON f.DateSK = d.DateSK
    GROUP BY d.Year, d.Month
) m;

-- KPI 4: Weekend Delay Uplift by month
CREATE OR REPLACE VIEW vw_KPI_WeekendUplift AS
SELECT
    x.Year,
    x.Month,
    x.WeekendUpliftPct,
    CASE WHEN x.WeekendUpliftPct <= 5 THEN 'Green'
         WHEN x.WeekendUpliftPct <= 15 THEN 'Amber' ELSE 'Red' END AS WeekendUpliftStatus,
    ROUND(x.WeekendUpliftPct - LAG(x.WeekendUpliftPct) OVER (ORDER BY x.Year, x.Month), 2) AS WeekendUpliftMoMChangePts
FROM (
    SELECT
        d.Year,
        d.Month,
        ROUND((
            (SUM(CASE WHEN d.IsWeekend = 1 THEN f.DelayMinutes END) / SUM(CASE WHEN d.IsWeekend = 1 THEN f.TripCount END)) /
            (SUM(CASE WHEN d.IsWeekend = 0 THEN f.DelayMinutes END) / SUM(CASE WHEN d.IsWeekend = 0 THEN f.TripCount END))
            - 1) * 100, 2) AS WeekendUpliftPct
    FROM Fact_TrainDelay f
    JOIN Dim_Date d ON f.DateSK = d.DateSK
    GROUP BY d.Year, d.Month
) x;

-- KPI 5: Peak-Hour Delay Surge by month (known scheduled time only)
CREATE OR REPLACE VIEW vw_KPI_PeakSurge AS
SELECT
    x.Year,
    x.Month,
    x.PeakSurgePct,
    CASE WHEN x.PeakSurgePct <= 10 THEN 'Green'
         WHEN x.PeakSurgePct <= 25 THEN 'Amber' ELSE 'Red' END AS PeakSurgeStatus,
    ROUND(x.PeakSurgePct - LAG(x.PeakSurgePct) OVER (ORDER BY x.Year, x.Month), 2) AS PeakSurgeMoMChangePts
FROM (
    SELECT
        d.Year,
        d.Month,
        ROUND((
            (SUM(CASE WHEN tm.IsPeakHour = 1 THEN f.DelayMinutes END) / SUM(CASE WHEN tm.IsPeakHour = 1 THEN f.TripCount END)) /
            (SUM(CASE WHEN tm.IsPeakHour = 0 THEN f.DelayMinutes END) / SUM(CASE WHEN tm.IsPeakHour = 0 THEN f.TripCount END))
            - 1) * 100, 2) AS PeakSurgePct
    FROM Fact_TrainDelay f
    JOIN Dim_Date d  ON f.DateSK = d.DateSK
    JOIN Dim_Time tm ON f.TimeSK = tm.TimeSK
    WHERE tm.TimeSK <> 9999
    GROUP BY d.Year, d.Month
) x;