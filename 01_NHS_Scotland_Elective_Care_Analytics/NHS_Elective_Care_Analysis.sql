/* NHS Scotland Elective Care Analysis 
Source: Public Health Scotland (PHS) Specialty & HBT Open Data
Author: Olumayowa Osimosu
*/

-- =============================================
-- 1.0 ENVIRONMENT SETUP
-- =============================================
USE master;
GO

-- Reset database for clean re-runs
IF EXISTS (SELECT * FROM sys.databases WHERE name = 'NHS_WaitingTimes_Project')
BEGIN
    ALTER DATABASE NHS_WaitingTimes_Project SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
    DROP DATABASE NHS_WaitingTimes_Project;
END
GO

CREATE DATABASE NHS_WaitingTimes_Project;
GO

USE NHS_WaitingTimes_Project;
GO

-- Staging table for raw CSV ingestion
CREATE TABLE [dbo].[Stg_Treatment_Waits](
    [MonthEnding] [int] NOT NULL,
    [HBT] [varchar](50) NOT NULL,
    [PatientType] [varchar](100),
    [WaitType] [varchar](50),
    [Specialty] [varchar](255),
    [Waits] [int] DEFAULT 0,
    [WaitsOver12Weeks] [int] DEFAULT 0,
    [WaitsOver52Weeks] [int] DEFAULT 0,
    [MedianWait] [float] NULL,
    [90thPercentile] [float] NULL
);
GO

-- =============================================
-- 2.0 TRANSFORMATION & MAPPING LOGIC
-- =============================================
GO
CREATE OR ALTER VIEW vw_Clean_Treatment_Waits AS
SELECT 
    CAST(CAST(MonthEnding AS VARCHAR) AS DATE) AS CalendarDate, 
    -- Map legacy/technical HBT codes to readable Board names
    CASE 
        WHEN HBT IN ('S08000022', 'S08000032') THEN 'NHS Lanarkshire'
        WHEN HBT IN ('S08000030', 'S27000001') THEN 'NHS Golden Jubilee'
        WHEN HBT IN ('S08000016', 'SB0801') THEN 'NHS Borders'
        WHEN HBT IN ('S08000028', 'S08000029') THEN 'NHS Fife'
        WHEN HBT = 'S08000015' THEN 'NHS Lothian'
        WHEN HBT = 'S08000017' THEN 'NHS Dumfries & Galloway'
        WHEN HBT = 'S08000019' THEN 'NHS Forth Valley'
        WHEN HBT = 'S08000020' THEN 'NHS Grampian'
        WHEN HBT = 'S08000021' THEN 'NHS Highland'
        WHEN HBT = 'S08000023' THEN 'NHS Orkney'
        WHEN HBT = 'S08000024' THEN 'NHS Greater Glasgow & Clyde'
        WHEN HBT = 'S08000025' THEN 'NHS Shetland'
        WHEN HBT = 'S08000026' THEN 'NHS Western Isles'
        WHEN HBT = 'S08000027' THEN 'NHS Ayrshire & Arran'
        WHEN HBT = 'S08000031' THEN 'NHS Tayside'
        WHEN HBT = 'S92000003' THEN 'Scotland (National Total)'
        ELSE HBT 
    END AS Health_Board_Name,
    -- Map Specialty codes to Clinical Departments
    CASE 
        WHEN Specialty IN ('C11', 'AH') THEN 'Trauma & Orthopaedics'
        WHEN Specialty = 'CB' THEN 'Urology'
        WHEN Specialty = 'C9' THEN 'Plastic Surgery'
        WHEN Specialty = 'D4' THEN 'ENT'
        WHEN Specialty = 'C5' THEN 'Oral & Maxillofacial Surgery'
        WHEN Specialty = 'F2' THEN 'Gynaecology'
        WHEN Specialty = 'C8' THEN 'General Surgery'
        WHEN Specialty = 'D3' THEN 'Ophthalmology'
        WHEN Specialty = 'AG' THEN 'Cardiology'
        WHEN Specialty = 'C4' THEN 'Haematology'
        WHEN Specialty = 'C6' THEN 'Infectious Diseases'
        WHEN Specialty = 'A7' THEN 'Dermatology'
        WHEN Specialty = 'C7' THEN 'Medical Oncology'
        WHEN Specialty = 'A9' THEN 'Occupational Medicine'
        WHEN Specialty = 'C13' THEN 'Nephrology'
        WHEN Specialty = 'CA' THEN 'Surgical Oncology'
        WHEN Specialty = 'C12' THEN 'Rheumatology'
        WHEN Specialty = 'Z9' THEN 'Not Specified / Other'
        ELSE Specialty 
    END AS Specialty_Name,
    PatientType,
    WaitType,
    Waits,
    WaitsOver12Weeks,
    WaitsOver52Weeks,
    -- Handling zero/null metrics for downstream calc safety
    NULLIF(MedianWait, 0) AS MedianWait,
    NULLIF([90thPercentile], 0) AS [90thPercentile]
FROM [dbo].[Stg_Treatment_Waits];
GO

-- =============================================
-- 3.0 DATA VALIDATION (QA)
-- =============================================

-- Row count verify
SELECT COUNT(*) AS RecordsLoaded FROM [dbo].[Stg_Treatment_Waits];

-- Scan for orphan dates or null boards
SELECT 
    SUM(CASE WHEN MonthEnding IS NULL THEN 1 ELSE 0 END) AS NullDates,
    SUM(CASE WHEN HBT IS NULL THEN 1 ELSE 0 END) AS NullBoards,
    SUM(CASE WHEN Waits IS NULL THEN 1 ELSE 0 END) AS NullWaits
FROM [dbo].[Stg_Treatment_Waits];

-- =============================================
-- 4.0 KEY PERFORMANCE INDICATORS
-- =============================================

-- 4.1 Regional Breach Density (Ongoing List Only)
SELECT TOP 5
    Health_Board_Name AS [Health Board],
    FORMAT(SUM(Waits), 'N0') AS [Total Ongoing],
    FORMAT(SUM(WaitsOver52Weeks), 'N0') AS [52Wk Backlog],
    CAST(ROUND(CAST(SUM(WaitsOver52Weeks) AS FLOAT) / NULLIF(SUM(Waits), 0) * 100, 2) AS VARCHAR) + '%' AS [Breach Density]
FROM vw_Clean_Treatment_Waits
WHERE Health_Board_Name <> 'Scotland (National Total)'
AND WaitType = 'Ongoing' 
GROUP BY Health_Board_Name
ORDER BY SUM(WaitsOver52Weeks) DESC;

-- 4.2 Wait-Time Inequality (Median vs 90th Pctl)
SELECT TOP 10
    Specialty_Name,
    ROUND(AVG(MedianWait), 1) AS [Median Wait],
    ROUND(AVG([90thPercentile]), 1) AS [90th Pctl],
    ROUND(AVG([90thPercentile]) / NULLIF(AVG(MedianWait), 0), 1) AS [Inequality Ratio]
FROM vw_Clean_Treatment_Waits
WHERE WaitType = 'Ongoing'
AND Specialty_Name <> 'Not Specified / Other'
GROUP BY Specialty_Name
HAVING AVG([90thPercentile]) > 360 -- Filter for legal wait guarantee failures
ORDER BY [90th Pctl] DESC;

-- 4.3 Backlog Velocity (MoM % Change)
WITH MonthlyStats AS (
    SELECT 
        CalendarDate,
        SUM(WaitsOver52Weeks) AS Total_Breaches
    FROM vw_Clean_Treatment_Waits
    WHERE Health_Board_Name = 'Scotland (National Total)'
    AND WaitType = 'Ongoing'
    GROUP BY CalendarDate
)
SELECT 
    CalendarDate,
    FORMAT(Total_Breaches, 'N0') AS [Current Backlog],
    FORMAT(LAG(Total_Breaches) OVER (ORDER BY CalendarDate), 'N0') AS [Prev Backlog],
    -- Calculation for Recovery Speed
    CAST(ROUND((CAST(Total_Breaches AS FLOAT) - LAG(Total_Breaches) OVER (ORDER BY CalendarDate)) 
        / NULLIF(LAG(Total_Breaches) OVER (ORDER BY CalendarDate), 0) * 100, 2) AS VARCHAR) + '%' AS [MoM Velocity]
FROM MonthlyStats
ORDER BY CalendarDate DESC;

-- 4.4 Master Export for Dashboarding
SELECT 
    Health_Board_Name,
    Specialty_Name,
    FORMAT(SUM(Waits), 'N0') AS [Waitlist Size],
    FORMAT(SUM(WaitsOver12Weeks), 'N0') AS [12Wk_Breaches],
    FORMAT(SUM(WaitsOver52Weeks), 'N0') AS [52Wk_Breaches],
    ROUND(AVG([90thPercentile]), 1) AS [90th_Pctl_Days]
FROM vw_Clean_Treatment_Waits
WHERE CalendarDate = '2025-11-30' 
  AND WaitType = 'Ongoing'
  AND Health_Board_Name <> 'Scotland (National Total)'
GROUP BY Health_Board_Name, Specialty_Name
ORDER BY SUM(WaitsOver52Weeks) DESC;