# Data Validation Report - `railway_dw_stage`

Generated 2026-10-13 04:55:20 by `etl/validate_load.py` in 4s.

**Result: 68/68 checks passed.**

## Table row counts

| Table | Rows |
|---|---:|
| Dim_CancellationReason | 6 |
| Dim_Date | 1,096 |
| Dim_DelayCategory | 4 |
| Dim_DelayReason | 9 |
| Dim_Station | 8,963 |
| Dim_Time | 1,441 |
| Dim_Train | 8,720 |
| Dim_Weather | 5 |
| Fact_DelayIncident | 20 |
| Fact_JourneyArrival | 52,002 |
| Fact_JourneyCancellation | 9 |
| Fact_JourneyDeparture | 55,272 |
| Fact_TrainDailySnapshot | 56,653 |
| Fact_TrainDelay | 930,924 |
| Fact_TrainSchedule | 172,108 |
| Fact_WeatherObservation | 30 |

## Checks

| Group | Check | Expected | Actual | Result |
|---|---|---:|---:|:---:|
| Dimension | Dim_Station rows = distinct station codes in source | 8,963 | 8,963 | PASS |
| Dimension | Dim_Train current rows = distinct train numbers in source | 8,720 | 8,720 | PASS |
| Dimension | Dim_Date = 1,096 contiguous days (2024-01-01..2026-12-31) | 1,096 | 1,096 | PASS |
| Dimension | Dim_Date has no gaps (max-min+1 = rows) | 1,096 | 1,096 | PASS |
| Dimension | Dim_Time = 1,440 minutes + 1 Unknown member | 1,441 | 1,441 | PASS |
| Dimension | Dim_Station natural key unique | 0 | 0 | PASS |
| SCD Type 2 | Exactly one current row per TrainNumber | 0 | 0 | PASS |
| SCD Type 2 | Current rows are open-ended (EffectiveEndDate = 9999-12-31) | 0 | 0 | PASS |
| SCD Type 2 | No overlapping validity periods per train | 0 | 0 | PASS |
| Reconciliation | Source rows = loaded + null delay + outliers + unmapped | 1,000,000 | 1,000,000 | PASS |
| Reconciliation | Fact_TrainDelay row count | 930,924 | 930,924 | PASS |
| Checksum | SUM(DelayMinutes) | 54,862,355 | 54,862,355 | PASS |
| Checksum | SUM(IsDelayed) | 785,212 | 785,212 | PASS |
| Checksum | SUM(PunctualFlag) | 445,088 | 445,088 | PASS |
| Checksum | SUM(SevereDelayFlag) | 258,528 | 258,528 | PASS |
| Checksum | SUM(ExcessDelayMinutes) | 45,914,135 | 45,914,135 | PASS |
| Checksum | SUM(TripCount) = row count | 930,924 | 930,924 | PASS |
| Reconciliation | Monthly row counts match for all 13 months | 0 | 0 | PASS |
| Info | Data-quality exclusions | null delay 66,218; |delay|>1440 511; unmapped 2,347 |  | - |
| Derived measure | Flags / ExcessDelayMinutes recomputed = stored | 0 | 0 | PASS |
| Derived measure | DelayCatSK band matches Dim_DelayCategory range | 0 | 0 | PASS |
| Event 2 | Fact_TrainSchedule = mapped timetable rows | 172,108 | 172,108 | PASS |
| Event 3 | Fact_JourneyDeparture = valid source rows at stop 1 | 55,272 | 55,272 | PASS |
| Event 3 | SUM(DepartureDelayMinutes) = SUM(DelayMinutes) at stop 1 | 883,698 | 883,698 | PASS |
| Event 4 | Fact_JourneyArrival = delay rows at last timetable stop | 52,002 | 52,002 | PASS |
| Event 5 | Fact_JourneyCancellation = cancelled journeys in feed | 9 | 9 | PASS |
| Event 6 | Fact_DelayIncident = completed journeys with arrival delay > 0 | 20 | 20 | PASS |
| Event 7 | Fact_WeatherObservation = all journeys in feed | 30 | 30 | PASS |
| Event 8 | Snapshot SUM(StopsRecorded) = Fact_TrainDelay rows | 930,924 | 930,924 | PASS |
| Event 8 | Snapshot SUM(TotalDelayMinutes) = SUM(DelayMinutes) | 54,862,355 | 54,862,355 | PASS |
| Event 8 | Snapshot SUM(DelayedStops) = SUM(IsDelayed) | 785,212 | 785,212 | PASS |
| Event 8 | Snapshot grain unique (DateSK, TrainSK) | 0 | 0 | PASS |
| Referential integrity | Fact_DelayIncident.DateSK -> Dim_Date | 0 | 0 | PASS |
| Referential integrity | Fact_DelayIncident.DelayCatSK -> Dim_DelayCategory | 0 | 0 | PASS |
| Referential integrity | Fact_DelayIncident.DelayReasonSK -> Dim_DelayReason | 0 | 0 | PASS |
| Referential integrity | Fact_DelayIncident.StationSK -> Dim_Station | 0 | 0 | PASS |
| Referential integrity | Fact_DelayIncident.TrainSK -> Dim_Train | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyArrival.ActualTimeSK -> Dim_Time | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyArrival.DateSK -> Dim_Date | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyArrival.DelayCatSK -> Dim_DelayCategory | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyArrival.DestinationStationSK -> Dim_Station | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyArrival.ScheduledTimeSK -> Dim_Time | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyArrival.TrainSK -> Dim_Train | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyCancellation.CancellationReasonSK -> Dim_CancellationReason | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyCancellation.DateSK -> Dim_Date | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyCancellation.DestinationStationSK -> Dim_Station | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyCancellation.OriginStationSK -> Dim_Station | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyCancellation.TrainSK -> Dim_Train | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyDeparture.ActualTimeSK -> Dim_Time | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyDeparture.DateSK -> Dim_Date | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyDeparture.DelayCatSK -> Dim_DelayCategory | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyDeparture.OriginStationSK -> Dim_Station | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyDeparture.ScheduledTimeSK -> Dim_Time | 0 | 0 | PASS |
| Referential integrity | Fact_JourneyDeparture.TrainSK -> Dim_Train | 0 | 0 | PASS |
| Referential integrity | Fact_TrainDailySnapshot.DateSK -> Dim_Date | 0 | 0 | PASS |
| Referential integrity | Fact_TrainDailySnapshot.TrainSK -> Dim_Train | 0 | 0 | PASS |
| Referential integrity | Fact_TrainDelay.DateSK -> Dim_Date | 0 | 0 | PASS |
| Referential integrity | Fact_TrainDelay.DelayCatSK -> Dim_DelayCategory | 0 | 0 | PASS |
| Referential integrity | Fact_TrainDelay.StationSK -> Dim_Station | 0 | 0 | PASS |
| Referential integrity | Fact_TrainDelay.TimeSK -> Dim_Time | 0 | 0 | PASS |
| Referential integrity | Fact_TrainDelay.TrainSK -> Dim_Train | 0 | 0 | PASS |
| Referential integrity | Fact_TrainSchedule.ArrivalTimeSK -> Dim_Time | 0 | 0 | PASS |
| Referential integrity | Fact_TrainSchedule.DepartureTimeSK -> Dim_Time | 0 | 0 | PASS |
| Referential integrity | Fact_TrainSchedule.StationSK -> Dim_Station | 0 | 0 | PASS |
| Referential integrity | Fact_TrainSchedule.TrainSK -> Dim_Train | 0 | 0 | PASS |
| Referential integrity | Fact_WeatherObservation.DateSK -> Dim_Date | 0 | 0 | PASS |
| Referential integrity | Fact_WeatherObservation.StationSK -> Dim_Station | 0 | 0 | PASS |
| Referential integrity | Fact_WeatherObservation.TrainSK -> Dim_Train | 0 | 0 | PASS |
| Referential integrity | Fact_WeatherObservation.WeatherSK -> Dim_Weather | 0 | 0 | PASS |
