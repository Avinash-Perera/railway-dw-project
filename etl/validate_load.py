#!/usr/bin/env python3
"""
Independent data-quality & reconciliation checks for the Railway DW.

Re-reads the source CSV files with its own (simple) logic and compares row counts
and checksums with what is physically stored in the warehouse, then checks
referential integrity, derived-measure consistency, SCD2 integrity and the
aggregate snapshot. Writes reports/data_validation_report.md.

Usage:  python3 etl/validate_load.py            (MYSQL_* env vars as for the ETL)
"""
import os
import sys
import time
from datetime import datetime
import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from etl.db_connector import get_engine
from etl.common import find_raw_file, normalize_train_no, max_rows

REPORT = os.path.join(PROJECT_ROOT, 'reports', 'data_validation_report.md')
results = []


def check(group, name, expected, actual):
    ok = expected == actual
    results.append((group, name, expected, actual, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {group}: {name} -> expected {expected}, actual {actual}")


def scalar(conn, sql):
    return conn.execute(text(sql)).scalar()


def fmt(v):
    return f"{v:,}" if isinstance(v, int) else str(v)


def source_delay_profile(stations, trains):
    """Independent pass over combined_delay.csv."""
    p = dict(raw=0, null_delay=0, outlier=0, unmapped=0, loaded=0, sum_delay=0, delayed=0,
             punctual=0, severe=0, excess=0, origin_rows=0)
    monthly = {}
    limit = max_rows()
    for chunk in pd.read_csv(find_raw_file('combined_delay.csv'), chunksize=500000,
                             dtype={'train_no': str, 'station_name': str}):
        if limit is not None and p['raw'] >= limit:
            break
        p['raw'] += len(chunk)
        p['null_delay'] += int(chunk['delay'].isna().sum())
        c = chunk[chunk['delay'].notna()]
        d = c['delay'].astype(float).astype(int)
        good = d.abs() <= 1440
        p['outlier'] += int((~good).sum())
        c, d = c[good], d[good]
        mapped = (c['station_name'].astype(str).str.strip().isin(stations)
                  & normalize_train_no(c['train_no']).isin(trains))
        p['unmapped'] += int((~mapped).sum())
        c, d = c[mapped], d[mapped]
        p['loaded'] += len(c)
        p['sum_delay'] += int(d.sum())
        p['delayed'] += int((d > 0).sum())
        p['punctual'] += int((d <= 15).sum())
        p['severe'] += int((d > 45).sum())
        p['excess'] += int((d - 15).clip(lower=0).sum())
        p['origin_rows'] += int((c['station_no'].astype(int) == 1).sum())
        for m, n in c['date'].str.slice(0, 7).value_counts().items():
            monthly[m] = monthly.get(m, 0) + int(n)
    return p, monthly


def main():
    started = time.time()
    engine = get_engine()
    with engine.connect() as conn:
        db = conn.execute(text("SELECT DATABASE()")).scalar()
        print(f"Validating database '{db}'...\n")

        # ---------------------------------------------------------------- dimensions
        print("1) Dimensions vs. source files")
        st_src = pd.read_csv(find_raw_file('station_full_names.csv'), usecols=['station_name'])
        st_codes = set(st_src['station_name'].dropna().astype(str).str.strip())
        tr_src = pd.read_csv(find_raw_file('train_details.csv'), dtype={'train_no': str}, usecols=['train_no'])
        tr_nos = set(normalize_train_no(tr_src['train_no'].dropna()))
        check('Dimension', 'Dim_Station rows = distinct station codes in source',
              len(st_codes), scalar(conn, "SELECT COUNT(*) FROM Dim_Station"))
        check('Dimension', 'Dim_Train current rows = distinct train numbers in source',
              len(tr_nos), scalar(conn, "SELECT COUNT(*) FROM Dim_Train WHERE IsCurrent = 1"))
        check('Dimension', 'Dim_Date = 1,096 contiguous days (2024-01-01..2026-12-31)', 1096,
              scalar(conn, "SELECT COUNT(*) FROM Dim_Date WHERE FullDate BETWEEN '2024-01-01' AND '2026-12-31'"))
        check('Dimension', 'Dim_Date has no gaps (max-min+1 = rows)', 1096,
              scalar(conn, "SELECT DATEDIFF(MAX(FullDate), MIN(FullDate)) + 1 FROM Dim_Date"))
        check('Dimension', 'Dim_Time = 1,440 minutes + 1 Unknown member', 1441,
              scalar(conn, "SELECT COUNT(*) FROM Dim_Time"))
        check('Dimension', 'Dim_Station natural key unique', 0,
              scalar(conn, "SELECT COUNT(*) - COUNT(DISTINCT StationCode) FROM Dim_Station"))
        check('SCD Type 2', 'Exactly one current row per TrainNumber', 0,
              scalar(conn, "SELECT COUNT(*) FROM (SELECT TrainNumber FROM Dim_Train WHERE IsCurrent = 1 "
                           "GROUP BY TrainNumber HAVING COUNT(*) <> 1) x"))
        check('SCD Type 2', 'Current rows are open-ended (EffectiveEndDate = 9999-12-31)', 0,
              scalar(conn, "SELECT COUNT(*) FROM Dim_Train WHERE IsCurrent = 1 AND EffectiveEndDate <> '9999-12-31'"))
        check('SCD Type 2', 'No overlapping validity periods per train', 0,
              scalar(conn, "SELECT COUNT(*) FROM Dim_Train a JOIN Dim_Train b ON a.TrainNumber = b.TrainNumber "
                           "AND a.TrainSK < b.TrainSK AND a.EffectiveStartDate <= b.EffectiveEndDate "
                           "AND b.EffectiveStartDate <= a.EffectiveEndDate"))

        # ---------------------------------------------------------------- Fact_TrainDelay
        print("\n2) Fact_TrainDelay vs. combined_delay.csv (independent re-read, takes a few minutes)")
        cur_trains = set(pd.read_sql("SELECT TrainNumber FROM Dim_Train WHERE IsCurrent = 1", conn)['TrainNumber'])
        p, monthly_src = source_delay_profile(st_codes, cur_trains)
        w = conn.execute(text("""
            SELECT COUNT(*), COALESCE(SUM(DelayMinutes),0), SUM(IsDelayed), SUM(PunctualFlag),
                   SUM(SevereDelayFlag), SUM(ExcessDelayMinutes), SUM(TripCount),
                   SUM(StopSequence = 1)
            FROM Fact_TrainDelay""")).fetchone()
        w = [int(x or 0) for x in w]
        check('Reconciliation', 'Source rows = loaded + null delay + outliers + unmapped', p['raw'],
              w[0] + p['null_delay'] + p['outlier'] + p['unmapped'])
        check('Reconciliation', 'Fact_TrainDelay row count', p['loaded'], w[0])
        check('Checksum', 'SUM(DelayMinutes)', p['sum_delay'], w[1])
        check('Checksum', 'SUM(IsDelayed)', p['delayed'], w[2])
        check('Checksum', 'SUM(PunctualFlag)', p['punctual'], w[3])
        check('Checksum', 'SUM(SevereDelayFlag)', p['severe'], w[4])
        check('Checksum', 'SUM(ExcessDelayMinutes)', p['excess'], w[5])
        check('Checksum', 'SUM(TripCount) = row count', w[0], w[6])
        mon_db = pd.read_sql("SELECT CONCAT(d.Year,'-',LPAD(d.Month,2,'0')) m, COUNT(*) n FROM Fact_TrainDelay f "
                             "JOIN Dim_Date d ON f.DateSK = d.DateSK GROUP BY d.Year, d.Month", conn)
        mon_db = dict(zip(mon_db['m'], mon_db['n'].astype(int)))
        bad = [m for m in sorted(set(monthly_src) | set(mon_db)) if monthly_src.get(m) != mon_db.get(m)]
        check('Reconciliation', f'Monthly row counts match for all {len(monthly_src)} months', 0, len(bad))
        results.append(('Info', 'Data-quality exclusions',
                        f"null delay {p['null_delay']:,}; |delay|>1440 {p['outlier']:,}; unmapped {p['unmapped']:,}",
                        '', True))

        print("\n3) Derived measures & banding consistency")
        bad_rows = conn.execute(text("""
            SELECT SUM(IsDelayed <> (DelayMinutes > 0)) +
                   SUM(PunctualFlag <> (DelayMinutes <= 15)) +
                   SUM(SevereDelayFlag <> (DelayMinutes > 45)) +
                   SUM(ExcessDelayMinutes <> GREATEST(0, DelayMinutes - 15)) +
                   SUM(TripCount <> 1)
            FROM Fact_TrainDelay""")).scalar()
        check('Derived measure', 'Flags / ExcessDelayMinutes recomputed = stored', 0, int(bad_rows or 0))
        check('Derived measure', 'DelayCatSK band matches Dim_DelayCategory range', 0, scalar(conn, """
            SELECT COUNT(*) FROM Fact_TrainDelay f JOIN Dim_DelayCategory c ON f.DelayCatSK = c.DelayCatSK
            WHERE f.DelayMinutes NOT BETWEEN c.MinDelayMinutes AND c.MaxDelayMinutes"""))
        check('Grain', 'Fact_TrainDelay unique per (DateSK, TrainSK, StopSequence)', 0, scalar(conn,
              "SELECT COUNT(*) - COUNT(DISTINCT DateSK, TrainSK, StopSequence) FROM Fact_TrainDelay"))
        check('Grain', 'Fact_JourneyDeparture unique per (DateSK, TrainSK)', 0, scalar(conn,
              "SELECT COUNT(*) - COUNT(DISTINCT DateSK, TrainSK) FROM Fact_JourneyDeparture"))
        check('Grain', 'Fact_JourneyArrival unique per (DateSK, TrainSK)', 0, scalar(conn,
              "SELECT COUNT(*) - COUNT(DISTINCT DateSK, TrainSK) FROM Fact_JourneyArrival"))

        # ---------------------------------------------------------------- other facts
        print("\n4) Events 2-8")
        sched = pd.read_csv(find_raw_file('combined_schedule.csv'), dtype={'train_no': str, 'station_name': str})
        sched_ok = (sched['station_name'].astype(str).str.strip().isin(st_codes)
                    & normalize_train_no(sched['train_no']).isin(cur_trains))
        check('Event 2', 'Fact_TrainSchedule = mapped timetable rows', int(sched_ok.sum()),
              scalar(conn, "SELECT COUNT(*) FROM Fact_TrainSchedule"))
        check('Event 3', 'Fact_JourneyDeparture = valid source rows at stop 1', p['origin_rows'],
              scalar(conn, "SELECT COUNT(*) FROM Fact_JourneyDeparture"))
        check('Event 3', 'SUM(DepartureDelayMinutes) = SUM(DelayMinutes) at stop 1',
              int(scalar(conn, "SELECT COALESCE(SUM(DelayMinutes),0) FROM Fact_TrainDelay WHERE StopSequence = 1")),
              int(scalar(conn, "SELECT COALESCE(SUM(DepartureDelayMinutes),0) FROM Fact_JourneyDeparture")))
        check('Event 4', 'Fact_JourneyArrival = delay rows at last timetable stop', int(scalar(conn, """
            SELECT COUNT(*) FROM Fact_TrainDelay f
            JOIN (SELECT TrainSK, MAX(StopSequence) s FROM Fact_TrainSchedule GROUP BY TrainSK) l
              ON l.TrainSK = f.TrainSK AND f.StopSequence = l.s AND l.s > 1""")),
              scalar(conn, "SELECT COUNT(*) FROM Fact_JourneyArrival"))
        from etl.load_event_facts import read_journey_feed
        jf = read_journey_feed(find_raw_file('train_delays.csv'))
        check('Event 5', 'Fact_JourneyCancellation = cancelled journeys in feed',
              int((jf['cancellation_status'] == 1).sum()),
              scalar(conn, "SELECT COUNT(*) FROM Fact_JourneyCancellation"))
        check('Event 6', 'Fact_DelayIncident = completed journeys with arrival delay > 0',
              int(((jf['cancellation_status'] == 0) & (jf['arrival_delay_min'] > 0)).sum()),
              scalar(conn, "SELECT COUNT(*) FROM Fact_DelayIncident"))
        check('Event 7', 'Fact_WeatherObservation = all journeys in feed', len(jf),
              scalar(conn, "SELECT COUNT(*) FROM Fact_WeatherObservation"))
        snap = conn.execute(text("SELECT COALESCE(SUM(StopsRecorded),0), COALESCE(SUM(TotalDelayMinutes),0), "
                                 "COALESCE(SUM(DelayedStops),0) FROM Fact_TrainDailySnapshot")).fetchone()
        check('Event 8', 'Snapshot SUM(StopsRecorded) = Fact_TrainDelay rows', w[0], int(snap[0]))
        check('Event 8', 'Snapshot SUM(TotalDelayMinutes) = SUM(DelayMinutes)', w[1], int(snap[1]))
        check('Event 8', 'Snapshot SUM(DelayedStops) = SUM(IsDelayed)', w[2], int(snap[2]))
        check('Event 8', 'Snapshot grain unique (DateSK, TrainSK)', 0, scalar(conn,
              "SELECT COUNT(*) - COUNT(DISTINCT DateSK, TrainSK) FROM Fact_TrainDailySnapshot"))

        # ---------------------------------------------------------------- referential integrity
        print("\n5) Referential integrity (every FK of every fact table)")
        fks = pd.read_sql("""
            SELECT TABLE_NAME t, COLUMN_NAME c, REFERENCED_TABLE_NAME rt, REFERENCED_COLUMN_NAME rc
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY TABLE_NAME, COLUMN_NAME""", conn)
        for r in fks.itertuples():
            orphans = scalar(conn, f"SELECT COUNT(*) FROM {r.t} f WHERE NOT EXISTS "
                                   f"(SELECT 1 FROM {r.rt} d WHERE d.{r.rc} = f.{r.c})")
            check('Referential integrity', f'{r.t}.{r.c} -> {r.rt}', 0, orphans)

        counts = pd.read_sql("""
            SELECT TABLE_NAME FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME""", conn)
        table_counts = [(t, scalar(conn, f"SELECT COUNT(*) FROM {t}")) for t in counts['TABLE_NAME']]

    # ---------------------------------------------------------------- report
    passed = sum(1 for r in results if r[4] and r[0] != 'Info')
    total = sum(1 for r in results if r[0] != 'Info')
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, 'w', encoding='utf-8') as fh:
        fh.write(f"# Data Validation Report - `{db}`\n\n")
        fh.write(f"Generated {datetime.now():%Y-%m-%d %H:%M:%S} by `etl/validate_load.py` "
                 f"in {time.time() - started:.0f}s.\n\n")
        fh.write(f"**Result: {passed}/{total} checks passed.**\n\n## Table row counts\n\n"
                 "| Table | Rows |\n|---|---:|\n")
        for t, n in table_counts:
            fh.write(f"| {t} | {n:,} |\n")
        fh.write("\n## Checks\n\n| Group | Check | Expected | Actual | Result |\n|---|---|---:|---:|:---:|\n")
        for g, name, e, a, ok in results:
            fh.write(f"| {g} | {name} | {fmt(e)} | {fmt(a)} | {'-' if g == 'Info' else ('PASS' if ok else 'FAIL')} |\n")
    print(f"\n{'✅' if passed == total else '❌'} {passed}/{total} checks passed. Report: {REPORT}")
    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
