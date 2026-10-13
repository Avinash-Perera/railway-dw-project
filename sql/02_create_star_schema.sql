-- ========================================================
-- 02. CREATE DIMENSIONAL MODEL (FACT CONSTELLATION)
--     8 business events / 8 conformed dimensions
--     NOTE: this script DROPS and recreates every table.
-- ========================================================
USE railway_dw;

SET FOREIGN_KEY_CHECKS = 0;

-- Facts first, then dimensions
DROP TABLE IF EXISTS Fact_TrainDailySnapshot;
DROP TABLE IF EXISTS Fact_WeatherObservation;
DROP TABLE IF EXISTS Fact_DelayIncident;
DROP TABLE IF EXISTS Fact_JourneyCancellation;
DROP TABLE IF EXISTS Fact_JourneyArrival;
DROP TABLE IF EXISTS Fact_JourneyDeparture;
DROP TABLE IF EXISTS Fact_TrainSchedule;
DROP TABLE IF EXISTS Fact_TrainDelay;
DROP TABLE IF EXISTS Dim_CancellationReason;
DROP TABLE IF EXISTS Dim_DelayReason;
DROP TABLE IF EXISTS Dim_Weather;
DROP TABLE IF EXISTS Dim_DelayCategory;
DROP TABLE IF EXISTS Dim_Time;
DROP TABLE IF EXISTS Dim_Train;
DROP TABLE IF EXISTS Dim_Station;
DROP TABLE IF EXISTS Dim_Date;

SET FOREIGN_KEY_CHECKS = 1;

-- ========================================================
-- DIMENSIONS
-- ========================================================

-- 1. Date Dimension (hierarchy: Year > Quarter > Month > Day)
--    Enriched with business calendar attributes (weekend, holiday, season)
CREATE TABLE Dim_Date (
    DateSK          INT PRIMARY KEY,            -- YYYYMMDD
    FullDate        DATE NOT NULL,
    Year            INT NOT NULL,
    Quarter         INT NOT NULL,
    QuarterName     VARCHAR(10) NOT NULL,       -- e.g. 'Q1'
    Month           INT NOT NULL,
    MonthName       VARCHAR(20) NOT NULL,
    Day             INT NOT NULL,
    WeekOfYear      INT NOT NULL,
    DayOfWeek       VARCHAR(20) NOT NULL,
    IsWeekend       TINYINT NOT NULL,
    IsHoliday       TINYINT NOT NULL DEFAULT 0,
    HolidayName     VARCHAR(60) NOT NULL DEFAULT 'Regular Day',
    Season          VARCHAR(20) NOT NULL        -- Winter / Summer / Monsoon / Post-Monsoon
);

-- 2. Time-of-Day Dimension (minute grain; hierarchy: TimeOfDayBand > Hour24 > Minute)
CREATE TABLE Dim_Time (
    TimeSK          INT PRIMARY KEY,            -- HHMM, 9999 = Unknown
    TimeLabel       VARCHAR(10) NOT NULL,       -- 'HH:MM'
    Hour24          INT NOT NULL,               -- -1 for Unknown
    Minute          INT NOT NULL,               -- -1 for Unknown
    TimeOfDayBand   VARCHAR(30) NOT NULL,
    IsPeakHour      TINYINT NOT NULL            -- 1 = 07:00-09:59 or 17:00-19:59
);

-- 3. Station Dimension (hierarchy: ZoneName > StationName)
--    Operational bloat (street address) is deliberately NOT loaded.
CREATE TABLE Dim_Station (
    StationSK       INT AUTO_INCREMENT PRIMARY KEY,
    StationCode     VARCHAR(20) UNIQUE NOT NULL,    -- natural key
    StationName     VARCHAR(150) NOT NULL,
    ZoneCode        VARCHAR(10) NOT NULL,
    ZoneName        VARCHAR(60) NOT NULL
);

-- 4. Train Dimension - SLOWLY CHANGING DIMENSION TYPE 2
--    (hierarchy: ServiceClass > TrainTypeName > TrainNumber)
--    A change of name / type closes the current row (EffectiveEndDate, IsCurrent=0)
--    and inserts a new row with a new TrainSK.
CREATE TABLE Dim_Train (
    TrainSK             INT AUTO_INCREMENT PRIMARY KEY,
    TrainNumber         VARCHAR(10) NOT NULL,           -- natural key (5-digit, zero padded)
    TrainName           VARCHAR(150),
    TrainTypeCode       VARCHAR(20),
    TrainTypeName       VARCHAR(40) NOT NULL,
    ServiceClass        VARCHAR(30) NOT NULL,
    EffectiveStartDate  DATE NOT NULL,
    EffectiveEndDate    DATE NOT NULL DEFAULT '9999-12-31',
    IsCurrent           TINYINT NOT NULL DEFAULT 1,
    UNIQUE KEY uq_train_version (TrainNumber, EffectiveStartDate)
);

-- 5. Delay Category (banded dimension)
CREATE TABLE Dim_DelayCategory (
    DelayCatSK      INT PRIMARY KEY,
    CategoryName    VARCHAR(50) NOT NULL,
    MinDelayMinutes INT NOT NULL,
    MaxDelayMinutes INT NOT NULL
);

INSERT INTO Dim_DelayCategory (DelayCatSK, CategoryName, MinDelayMinutes, MaxDelayMinutes) VALUES
(1, 'On-Time / Early', -9999, 0),
(2, 'Minor Delay (1-15 min)', 1, 15),
(3, 'Moderate Delay (16-45 min)', 16, 45),
(4, 'Severe Delay (>45 min)', 46, 99999);

-- 6. Weather Dimension
CREATE TABLE Dim_Weather (
    WeatherSK           INT PRIMARY KEY,
    WeatherCondition    VARCHAR(30) NOT NULL,
    WeatherSeverity     VARCHAR(20) NOT NULL
);

INSERT INTO Dim_Weather (WeatherSK, WeatherCondition, WeatherSeverity) VALUES
(1, 'Clear', 'None'),
(2, 'Rain', 'Moderate'),
(3, 'Fog', 'Moderate'),
(4, 'Storm', 'Severe'),
(5, 'Unknown', 'Unknown');

-- 7. Delay Reason Dimension
CREATE TABLE Dim_DelayReason (
    DelayReasonSK       INT PRIMARY KEY,
    DelayReasonName     VARCHAR(40) NOT NULL,
    DelayReasonGroup    VARCHAR(30) NOT NULL
);

INSERT INTO Dim_DelayReason (DelayReasonSK, DelayReasonName, DelayReasonGroup) VALUES
(1, 'On Time', 'No Delay'),
(2, 'Minor Delay', 'No Delay'),
(3, 'Signal Issue', 'Infrastructure'),
(4, 'Signal Failure', 'Infrastructure'),
(5, 'Track Maintenance', 'Infrastructure'),
(6, 'Congestion', 'Traffic'),
(7, 'Late Incoming Train', 'Traffic'),
(8, 'Technical Issue', 'Rolling Stock'),
(9, 'Unknown', 'Unknown');

-- 8. Cancellation Reason Dimension
CREATE TABLE Dim_CancellationReason (
    CancellationReasonSK    INT PRIMARY KEY,
    CancellationReasonName  VARCHAR(40) NOT NULL,
    CancellationGroup       VARCHAR(30) NOT NULL
);

INSERT INTO Dim_CancellationReason (CancellationReasonSK, CancellationReasonName, CancellationGroup) VALUES
(1, 'Not Cancelled', 'None'),
(2, 'Weather Disruption', 'Environmental'),
(3, 'Flooding', 'Environmental'),
(4, 'Technical Issue', 'Rolling Stock'),
(5, 'Operational Issue', 'Operations'),
(6, 'Unknown', 'Unknown');

-- ========================================================
-- FACT TABLES - one per business event
-- Fact tables hold only surrogate keys, numeric measures and degenerate keys.
-- ========================================================

-- EVENT 1: Train arrival at a station (delay measurement)  [LOADED: combined_delay.csv]
-- Grain: one train arriving at one station on one calendar date.
CREATE TABLE Fact_TrainDelay (
    FactID              BIGINT AUTO_INCREMENT PRIMARY KEY,
    DateSK              INT NOT NULL,
    TimeSK              INT NOT NULL,               -- scheduled time at that stop
    StationSK           INT NOT NULL,
    TrainSK             INT NOT NULL,
    DelayCatSK          INT NOT NULL,
    StopSequence        INT NOT NULL,               -- degenerate dimension (station_no)
    -- raw measure
    DelayMinutes        INT NOT NULL DEFAULT 0,     -- negative = early
    -- derived measures
    TripCount           INT NOT NULL DEFAULT 1,
    IsDelayed           TINYINT NOT NULL DEFAULT 0, -- DelayMinutes > 0
    PunctualFlag        TINYINT NOT NULL DEFAULT 0, -- DelayMinutes <= 15 (tolerance)
    SevereDelayFlag     TINYINT NOT NULL DEFAULT 0, -- DelayMinutes > 45
    ExcessDelayMinutes  INT NOT NULL DEFAULT 0,     -- GREATEST(0, DelayMinutes - 15)
    FOREIGN KEY (DateSK)     REFERENCES Dim_Date(DateSK),
    FOREIGN KEY (TimeSK)     REFERENCES Dim_Time(TimeSK),
    FOREIGN KEY (StationSK)  REFERENCES Dim_Station(StationSK),
    FOREIGN KEY (TrainSK)    REFERENCES Dim_Train(TrainSK),
    FOREIGN KEY (DelayCatSK) REFERENCES Dim_DelayCategory(DelayCatSK)
);

-- EVENT 2: Scheduled stop of a train (timetable)  [LOADED: combined_schedule.csv]
-- Grain: one scheduled stop of one train at one station (static timetable, no date).
CREATE TABLE Fact_TrainSchedule (
    ScheduleFactID          BIGINT AUTO_INCREMENT PRIMARY KEY,
    TrainSK                 INT NOT NULL,
    StationSK               INT NOT NULL,
    ArrivalTimeSK           INT NOT NULL,
    DepartureTimeSK         INT NOT NULL,
    StopSequence            INT NOT NULL,           -- degenerate dimension
    DistanceFromOriginKm    INT NOT NULL DEFAULT 0,
    ArrivalDayOffset        INT NOT NULL DEFAULT 1,
    DepartureDayOffset      INT NOT NULL DEFAULT 1,
    -- derived measures
    StopCount               INT NOT NULL DEFAULT 1,
    ScheduledDwellMinutes   INT NOT NULL DEFAULT 0,
    SegmentDistanceKm       INT NOT NULL DEFAULT 0, -- distance since previous stop
    FOREIGN KEY (TrainSK)         REFERENCES Dim_Train(TrainSK),
    FOREIGN KEY (StationSK)       REFERENCES Dim_Station(StationSK),
    FOREIGN KEY (ArrivalTimeSK)   REFERENCES Dim_Time(TimeSK),
    FOREIGN KEY (DepartureTimeSK) REFERENCES Dim_Time(TimeSK)
);

-- EVENT 3: Journey departure from origin  [LOADED: derived from combined_delay.csv, stop sequence 1]
-- Grain: one journey departing its origin station on one date.
CREATE TABLE Fact_JourneyDeparture (
    DepartureFactID         BIGINT AUTO_INCREMENT PRIMARY KEY,
    DateSK                  INT NOT NULL,
    TrainSK                 INT NOT NULL,
    OriginStationSK         INT NOT NULL,
    ScheduledTimeSK         INT NOT NULL,
    ActualTimeSK            INT NOT NULL,
    DelayCatSK              INT NOT NULL,
    DepartureDelayMinutes   INT NOT NULL DEFAULT 0,
    DepartureCount          INT NOT NULL DEFAULT 1,
    DelayedDepartureFlag    TINYINT NOT NULL DEFAULT 0,
    FOREIGN KEY (DateSK)          REFERENCES Dim_Date(DateSK),
    FOREIGN KEY (TrainSK)         REFERENCES Dim_Train(TrainSK),
    FOREIGN KEY (OriginStationSK) REFERENCES Dim_Station(StationSK),
    FOREIGN KEY (ScheduledTimeSK) REFERENCES Dim_Time(TimeSK),
    FOREIGN KEY (ActualTimeSK)    REFERENCES Dim_Time(TimeSK),
    FOREIGN KEY (DelayCatSK)      REFERENCES Dim_DelayCategory(DelayCatSK)
);

-- EVENT 4: Journey arrival at final destination  [LOADED: derived from combined_delay.csv, last timetable stop]
-- Grain: one journey arriving at its destination station on one date.
CREATE TABLE Fact_JourneyArrival (
    ArrivalFactID           BIGINT AUTO_INCREMENT PRIMARY KEY,
    DateSK                  INT NOT NULL,
    TrainSK                 INT NOT NULL,
    DestinationStationSK    INT NOT NULL,
    ScheduledTimeSK         INT NOT NULL,
    ActualTimeSK            INT NOT NULL,
    DelayCatSK              INT NOT NULL,
    ArrivalDelayMinutes     INT NOT NULL DEFAULT 0,
    ArrivalCount            INT NOT NULL DEFAULT 1,
    DelayedArrivalFlag      TINYINT NOT NULL DEFAULT 0,
    FOREIGN KEY (DateSK)               REFERENCES Dim_Date(DateSK),
    FOREIGN KEY (TrainSK)              REFERENCES Dim_Train(TrainSK),
    FOREIGN KEY (DestinationStationSK) REFERENCES Dim_Station(StationSK),
    FOREIGN KEY (ScheduledTimeSK)      REFERENCES Dim_Time(TimeSK),
    FOREIGN KEY (ActualTimeSK)         REFERENCES Dim_Time(TimeSK),
    FOREIGN KEY (DelayCatSK)           REFERENCES Dim_DelayCategory(DelayCatSK)
);

-- EVENT 5: Journey cancellation  [LOADED: train_delays.csv, cancellation_status = 1]
-- Grain: one cancelled journey on one date.
CREATE TABLE Fact_JourneyCancellation (
    CancellationFactID      BIGINT AUTO_INCREMENT PRIMARY KEY,
    DateSK                  INT NOT NULL,
    TrainSK                 INT NOT NULL,
    OriginStationSK         INT NOT NULL,
    DestinationStationSK    INT NOT NULL,
    CancellationReasonSK    INT NOT NULL,
    CancellationCount       INT NOT NULL DEFAULT 1,
    FOREIGN KEY (DateSK)               REFERENCES Dim_Date(DateSK),
    FOREIGN KEY (TrainSK)              REFERENCES Dim_Train(TrainSK),
    FOREIGN KEY (OriginStationSK)      REFERENCES Dim_Station(StationSK),
    FOREIGN KEY (DestinationStationSK) REFERENCES Dim_Station(StationSK),
    FOREIGN KEY (CancellationReasonSK) REFERENCES Dim_CancellationReason(CancellationReasonSK)
);

-- EVENT 6: Delay incident attributed to a cause  [LOADED: train_delays.csv, delayed journeys]
-- Grain: one delayed journey attributed to one primary delay reason.
CREATE TABLE Fact_DelayIncident (
    IncidentFactID          BIGINT AUTO_INCREMENT PRIMARY KEY,
    DateSK                  INT NOT NULL,
    TrainSK                 INT NOT NULL,
    StationSK               INT NOT NULL,
    DelayReasonSK           INT NOT NULL,
    DelayCatSK              INT NOT NULL,
    IncidentDelayMinutes    INT NOT NULL DEFAULT 0,
    IncidentCount           INT NOT NULL DEFAULT 1,
    FOREIGN KEY (DateSK)        REFERENCES Dim_Date(DateSK),
    FOREIGN KEY (TrainSK)       REFERENCES Dim_Train(TrainSK),
    FOREIGN KEY (StationSK)     REFERENCES Dim_Station(StationSK),
    FOREIGN KEY (DelayReasonSK) REFERENCES Dim_DelayReason(DelayReasonSK),
    FOREIGN KEY (DelayCatSK)    REFERENCES Dim_DelayCategory(DelayCatSK)
);

-- EVENT 7: Weather observation during a journey  [LOADED: train_delays.csv, all journeys]
-- Grain: one weather condition recorded for one journey on one date.
CREATE TABLE Fact_WeatherObservation (
    WeatherFactID           BIGINT AUTO_INCREMENT PRIMARY KEY,
    DateSK                  INT NOT NULL,
    TrainSK                 INT NOT NULL,
    StationSK               INT NOT NULL,
    WeatherSK               INT NOT NULL,
    ObservationCount        INT NOT NULL DEFAULT 1,
    JourneyDelayMinutes     INT NOT NULL DEFAULT 0,
    WeatherAffectedFlag     TINYINT NOT NULL DEFAULT 0,
    FOREIGN KEY (DateSK)    REFERENCES Dim_Date(DateSK),
    FOREIGN KEY (TrainSK)   REFERENCES Dim_Train(TrainSK),
    FOREIGN KEY (StationSK) REFERENCES Dim_Station(StationSK),
    FOREIGN KEY (WeatherSK) REFERENCES Dim_Weather(WeatherSK)
);

-- EVENT 8: Daily train performance snapshot (periodic snapshot)  [LOADED: aggregated from Fact_TrainDelay]
-- Grain: one train on one date (aggregated from Fact_TrainDelay).
CREATE TABLE Fact_TrainDailySnapshot (
    SnapshotFactID          BIGINT AUTO_INCREMENT PRIMARY KEY,
    DateSK                  INT NOT NULL,
    TrainSK                 INT NOT NULL,
    StopsRecorded           INT NOT NULL DEFAULT 0,
    DelayedStops            INT NOT NULL DEFAULT 0,
    MaxDelayMinutes         INT NOT NULL DEFAULT 0,
    TotalDelayMinutes       INT NOT NULL DEFAULT 0,
    TotalExcessDelayMinutes INT NOT NULL DEFAULT 0,
    FOREIGN KEY (DateSK)  REFERENCES Dim_Date(DateSK),
    FOREIGN KEY (TrainSK) REFERENCES Dim_Train(TrainSK)
);