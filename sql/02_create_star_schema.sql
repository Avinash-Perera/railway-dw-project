-- ========================================================
-- 02. CREATE STAR SCHEMA (DIMENSIONS & FACT)
-- ========================================================
USE railway_dw;

-- Drop tables if they already exist (drop Fact first due to foreign keys)
DROP TABLE IF EXISTS Fact_TrainDelay;
DROP TABLE IF EXISTS Dim_Station;
DROP TABLE IF EXISTS Dim_Train;
DROP TABLE IF EXISTS Dim_Date;
DROP TABLE IF EXISTS Dim_DelayCategory;

-- 1. Date Dimension
CREATE TABLE Dim_Date (
    DateSK INT PRIMARY KEY,
    FullDate DATE NOT NULL,
    Year INT NOT NULL,
    Quarter INT NOT NULL,
    Month INT NOT NULL,
    MonthName VARCHAR(20) NOT NULL,
    Day INT NOT NULL,
    DayOfWeek VARCHAR(20) NOT NULL,
    IsWeekend TINYINT NOT NULL
);

-- 2. Train Dimension
CREATE TABLE Dim_Train (
    TrainSK INT AUTO_INCREMENT PRIMARY KEY,
    TrainNumber VARCHAR(20) UNIQUE NOT NULL,
    TrainName VARCHAR(150),
    TrainType VARCHAR(50)
);

-- 3. Station Dimension
CREATE TABLE Dim_Station (
    StationSK INT AUTO_INCREMENT PRIMARY KEY,
    StationCode VARCHAR(20) UNIQUE NOT NULL,
    StationName VARCHAR(150) NOT NULL
);

-- 4. Delay Category Dimension (Banded Dimension)
CREATE TABLE Dim_DelayCategory (
    DelayCatSK INT PRIMARY KEY,
    CategoryName VARCHAR(50) NOT NULL,
    MinDelayMinutes INT NOT NULL,
    MaxDelayMinutes INT NOT NULL
);

-- Populate standard Delay Categories immediately
INSERT INTO Dim_DelayCategory (DelayCatSK, CategoryName, MinDelayMinutes, MaxDelayMinutes) VALUES
(1, 'On-Time / Early', -9999, 0),
(2, 'Minor Delay (1-15 min)', 1, 15),
(3, 'Moderate Delay (16-45 min)', 16, 45),
(4, 'Severe Delay (>45 min)', 46, 99999);

-- 5. Fact Table (Transaction Grain: One train arriving at one station per day)
CREATE TABLE Fact_TrainDelay (
    FactID BIGINT AUTO_INCREMENT PRIMARY KEY,
    DateSK INT NOT NULL,
    StationSK INT NOT NULL,
    TrainSK INT NOT NULL,
    DelayCatSK INT NOT NULL,
    DelayMinutes INT NOT NULL DEFAULT 0,
    IsDelayed TINYINT NOT NULL DEFAULT 0,
    
    -- Foreign Key Constraints linking to Dimension Tables
    FOREIGN KEY (DateSK) REFERENCES Dim_Date(DateSK),
    FOREIGN KEY (StationSK) REFERENCES Dim_Station(StationSK),
    FOREIGN KEY (TrainSK) REFERENCES Dim_Train(TrainSK),
    FOREIGN KEY (DelayCatSK) REFERENCES Dim_DelayCategory(DelayCatSK)
);