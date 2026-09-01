-- ========================================================
-- 03. CREATE INDEXES AND ANALYTICAL VIEWS
-- ========================================================
USE railway_dw;

-- Create Indexes on Foreign Keys to speed up OLAP/Power BI queries
CREATE INDEX idx_fact_date ON Fact_TrainDelay(DateSK);
CREATE INDEX idx_fact_station ON Fact_TrainDelay(StationSK);
CREATE INDEX idx_fact_train ON Fact_TrainDelay(TrainSK);
CREATE INDEX idx_fact_delaycat ON Fact_TrainDelay(DelayCatSK);

-- Create an Analytical View to easily see the data with text descriptions
CREATE OR REPLACE VIEW vw_RailwayAnalytics AS
SELECT 
    f.FactID,
    d.FullDate,
    d.Year,
    d.MonthName,
    d.DayOfWeek,
    d.IsWeekend,
    s.StationCode,
    s.StationName,
    t.TrainNumber,
    t.TrainName,
    t.TrainType,
    c.CategoryName AS DelaySeverity,
    f.DelayMinutes,
    f.IsDelayed
FROM Fact_TrainDelay f
JOIN Dim_Date d ON f.DateSK = d.DateSK
JOIN Dim_Station s ON f.StationSK = s.StationSK
JOIN Dim_Train t ON f.TrainSK = t.TrainSK
JOIN Dim_DelayCategory c ON f.DelayCatSK = c.DelayCatSK;