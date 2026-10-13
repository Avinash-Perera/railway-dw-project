"""
Fact loaders fed by the large source files.

    combined_schedule.csv -> Fact_TrainSchedule            (Event 2)
    combined_delay.csv    -> Fact_TrainDelay               (Event 1)
                          -> Fact_JourneyDeparture         (Event 3: stop 1 = origin)
                          -> Fact_JourneyArrival           (Event 4: last timetable stop = destination)

All three delay-based facts are produced in ONE streaming pass over the 1 GB file.
Re-running is safe: the fact tables are truncated first (full refresh).
"""
import os
import sys
import time
import numpy as np
import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from etl.db_connector import get_engine
from etl.common import (find_raw_file, normalize_train_no, max_rows, bulk_load,
                        minutes_to_time_sk, UNKNOWN_TIME_SK)

CHUNK_SIZE = 250000
PUNCTUAL_TOLERANCE_MIN = 15      # delay <= 15 min counts as punctual
SEVERE_THRESHOLD_MIN = 45        # delay > 45 min counts as severe
MAX_VALID_ABS_DELAY_MIN = 1440   # |delay| above 24h is treated as a data error

DELAY_FACTS = ['Fact_TrainDelay', 'Fact_JourneyDeparture', 'Fact_JourneyArrival']


def get_mapping_dictionaries(engine):
    """Natural key -> surrogate key lookups (current Train version only)."""
    print("Fetching dimension mappings...")
    with engine.connect() as conn:
        station_df = pd.read_sql("SELECT StationSK, StationCode FROM Dim_Station", conn)
        train_df = pd.read_sql("SELECT TrainSK, TrainNumber FROM Dim_Train WHERE IsCurrent = 1", conn)
    station_map = dict(zip(station_df['StationCode'], station_df['StationSK']))
    train_map = dict(zip(train_df['TrainNumber'], train_df['TrainSK']))
    return station_map, train_map


def truncate(engine, tables):
    with engine.begin() as conn:
        for t in tables:
            conn.execute(text(f"TRUNCATE TABLE {t}"))


def derive_delay_cat_sk(delay_series):
    """Vectorised banding consistent with Dim_DelayCategory."""
    return np.select(
        [delay_series <= 0, delay_series <= 15, delay_series <= 45],
        [1, 2, 3],
        default=4,
    )


def time_to_sk(series):
    """'HH:MM' -> TimeSK (HHMM); invalid / blank -> UNKNOWN_TIME_SK (9999)."""
    text_ = series.astype('string').str.strip().str.slice(0, 5)
    parts = text_.str.extract(r'^(\d{1,2}):(\d{2})$')
    hour = pd.to_numeric(parts[0], errors='coerce')
    minute = pd.to_numeric(parts[1], errors='coerce')
    valid = hour.between(0, 23) & minute.between(0, 59)
    sk = (hour * 100 + minute).where(valid)
    return sk.fillna(UNKNOWN_TIME_SK).astype(int), hour.where(valid), minute.where(valid)


def load_schedule_frame(csv_path):
    """Read and clean combined_schedule.csv (shared by schedule fact + delay time lookup)."""
    sched = pd.read_csv(csv_path, dtype={'train_no': str, 'station_name': str})
    sched['train_no'] = normalize_train_no(sched['train_no'])
    sched['station_name'] = sched['station_name'].astype(str).str.strip()
    sched['station_no'] = sched['station_no'].astype(int)
    sched['ArrivalTimeSK'], arr_h, arr_m = time_to_sk(sched['arrival_time'])
    sched['DepartureTimeSK'], dep_h, dep_m = time_to_sk(sched['departure_time'])
    sched['arr_abs'] = (sched['arrival_day'].fillna(sched['departure_day']).fillna(1) * 1440
                        + arr_h * 60 + arr_m)
    sched['dep_abs'] = (sched['departure_day'].fillna(sched['arrival_day']).fillna(1) * 1440
                        + dep_h * 60 + dep_m)
    return sched


def build_time_lookup(sched):
    """(train_no, station_no) -> scheduled TimeSK (arrival time, else departure time)."""
    lookup = sched[['train_no', 'station_no', 'ArrivalTimeSK', 'DepartureTimeSK']].copy()
    lookup['ScheduledTimeSK'] = np.where(lookup['ArrivalTimeSK'] != UNKNOWN_TIME_SK,
                                         lookup['ArrivalTimeSK'], lookup['DepartureTimeSK'])
    lookup = lookup.drop_duplicates(subset=['train_no', 'station_no'])
    return lookup[['train_no', 'station_no', 'ScheduledTimeSK']]


def build_last_stop_map(sched):
    """train_no -> stop sequence of the final (destination) stop in the timetable."""
    return sched.groupby('train_no')['station_no'].max().to_dict()


def transform_delay_chunk(chunk, station_map, train_map, time_lookup, last_stop, stats):
    """Transform one raw chunk of combined_delay.csv.
    Returns (Fact_TrainDelay rows, Fact_JourneyDeparture rows, Fact_JourneyArrival rows)."""
    stats['raw'] += len(chunk)

    # Data quality 1: delay not recorded -> not a measurement, exclude
    stats['null_delay'] += int(chunk['delay'].isna().sum())
    chunk = chunk[chunk['delay'].notna()].copy()
    chunk['delay'] = chunk['delay'].astype(float).astype(int)

    # Data quality 2: implausible values (> 24h) are treated as errors
    valid = chunk['delay'].abs() <= MAX_VALID_ABS_DELAY_MIN
    stats['outlier'] += int((~valid).sum())
    chunk = chunk[valid]

    chunk['train_no'] = normalize_train_no(chunk['train_no'])
    chunk['station_name'] = chunk['station_name'].astype(str).str.strip()
    chunk['station_no'] = chunk['station_no'].astype(int)
    chunk['StationSK'] = chunk['station_name'].map(station_map)
    chunk['TrainSK'] = chunk['train_no'].map(train_map)

    # Data quality 3: natural keys that do not exist in the dimensions are skipped
    before = len(chunk)
    chunk = chunk.dropna(subset=['StationSK', 'TrainSK'])
    stats['unmapped'] += before - len(chunk)

    chunk['DateSK'] = chunk['date'].astype(str).str.replace('-', '', regex=False).astype(int)
    chunk = chunk.merge(time_lookup, how='left', on=['train_no', 'station_no'])
    chunk['TimeSK'] = chunk['ScheduledTimeSK'].fillna(UNKNOWN_TIME_SK).astype(int)

    delay = chunk['delay']
    delay_cat = derive_delay_cat_sk(delay).astype(int)
    fact = pd.DataFrame({
        'DateSK': chunk['DateSK'].astype(int),
        'TimeSK': chunk['TimeSK'],
        'StationSK': chunk['StationSK'].astype(int),
        'TrainSK': chunk['TrainSK'].astype(int),
        'DelayCatSK': delay_cat,
        'StopSequence': chunk['station_no'],
        'DelayMinutes': delay,
        'TripCount': 1,
        'IsDelayed': (delay > 0).astype(int),
        'PunctualFlag': (delay <= PUNCTUAL_TOLERANCE_MIN).astype(int),
        'SevereDelayFlag': (delay > SEVERE_THRESHOLD_MIN).astype(int),
        'ExcessDelayMinutes': (delay - PUNCTUAL_TOLERANCE_MIN).clip(lower=0).astype(int),
    })

    # Event 3: departure from origin = stop sequence 1
    dep = fact[fact['StopSequence'] == 1]
    departures = pd.DataFrame({
        'DateSK': dep['DateSK'], 'TrainSK': dep['TrainSK'], 'OriginStationSK': dep['StationSK'],
        'ScheduledTimeSK': dep['TimeSK'],
        'ActualTimeSK': minutes_to_time_sk(dep['TimeSK'], dep['DelayMinutes']),
        'DelayCatSK': dep['DelayCatSK'], 'DepartureDelayMinutes': dep['DelayMinutes'],
        'DepartureCount': 1, 'DelayedDepartureFlag': dep['IsDelayed'],
    })

    # Event 4: arrival at destination = last stop of that train in the timetable
    is_last = chunk['station_no'].values == chunk['train_no'].map(last_stop).values
    arr = fact[is_last & (fact['StopSequence'].values > 1)]
    arrivals = pd.DataFrame({
        'DateSK': arr['DateSK'], 'TrainSK': arr['TrainSK'], 'DestinationStationSK': arr['StationSK'],
        'ScheduledTimeSK': arr['TimeSK'],
        'ActualTimeSK': minutes_to_time_sk(arr['TimeSK'], arr['DelayMinutes']),
        'DelayCatSK': arr['DelayCatSK'], 'ArrivalDelayMinutes': arr['DelayMinutes'],
        'ArrivalCount': 1, 'DelayedArrivalFlag': arr['IsDelayed'],
    })
    return fact, departures, arrivals


def load_fact_table(engine, csv_path, sched):
    print(f"Loading Fact_TrainDelay / Fact_JourneyDeparture / Fact_JourneyArrival from {csv_path}...")
    truncate(engine, DELAY_FACTS)
    station_map, train_map = get_mapping_dictionaries(engine)
    time_lookup = build_time_lookup(sched)
    last_stop = build_last_stop_map(sched)

    stats = {'raw': 0, 'null_delay': 0, 'outlier': 0, 'unmapped': 0}
    inserted = {t: 0 for t in DELAY_FACTS}
    limit = max_rows()
    started = time.time()
    chunk_iter = pd.read_csv(csv_path, chunksize=CHUNK_SIZE, low_memory=False,
                             dtype={'train_no': str, 'station_name': str})

    for i, chunk in enumerate(chunk_iter, start=1):
        if limit is not None and stats['raw'] >= limit:
            break
        fact, dep, arr = transform_delay_chunk(chunk, station_map, train_map, time_lookup,
                                               last_stop, stats)
        inserted['Fact_TrainDelay'] += bulk_load(engine, fact, 'Fact_TrainDelay')
        inserted['Fact_JourneyDeparture'] += bulk_load(engine, dep, 'Fact_JourneyDeparture')
        inserted['Fact_JourneyArrival'] += bulk_load(engine, arr, 'Fact_JourneyArrival')
        if i % 10 == 0 or i == 1:
            rate = stats['raw'] / max(time.time() - started, 1e-6)
            print(f"  -> chunk {i}: {stats['raw']:,} source rows read, "
                  f"{inserted['Fact_TrainDelay']:,} fact rows ({rate:,.0f} rows/s)")

    excluded = stats['null_delay'] + stats['outlier'] + stats['unmapped']
    print(f"✅ Fact_TrainDelay load complete: {inserted['Fact_TrainDelay']:,} inserted "
          f"from {stats['raw']:,} source rows.")
    print(f"   Data-quality exclusions -> null delay: {stats['null_delay']:,}, "
          f"|delay| > {MAX_VALID_ABS_DELAY_MIN} min: {stats['outlier']:,}, "
          f"unmapped keys: {stats['unmapped']:,}")
    print(f"   Reconciliation: {stats['raw']:,} raw = {inserted['Fact_TrainDelay']:,} loaded + "
          f"{excluded:,} excluded -> "
          f"{'OK' if stats['raw'] == inserted['Fact_TrainDelay'] + excluded else 'MISMATCH'}")
    print(f"✅ Fact_JourneyDeparture: {inserted['Fact_JourneyDeparture']:,} rows | "
          f"Fact_JourneyArrival: {inserted['Fact_JourneyArrival']:,} rows")
    return stats, inserted


def load_schedule_fact(engine, sched):
    print("Loading Fact_TrainSchedule...")
    truncate(engine, ['Fact_TrainSchedule'])
    station_map, train_map = get_mapping_dictionaries(engine)
    df = sched.copy()
    df['StationSK'] = df['station_name'].map(station_map)
    df['TrainSK'] = df['train_no'].map(train_map)
    before = len(df)
    df = df.dropna(subset=['StationSK', 'TrainSK'])
    df = df.sort_values(['train_no', 'station_no'])

    dwell = (df['dep_abs'] - df['arr_abs'])
    dwell = dwell.where(dwell >= 0).fillna(0)
    segment = df.groupby('train_no')['distance_from_origin'].diff().fillna(0).clip(lower=0)

    fact = pd.DataFrame({
        'TrainSK': df['TrainSK'].astype(int),
        'StationSK': df['StationSK'].astype(int),
        'ArrivalTimeSK': df['ArrivalTimeSK'],
        'DepartureTimeSK': df['DepartureTimeSK'],
        'StopSequence': df['station_no'].astype(int),
        'DistanceFromOriginKm': df['distance_from_origin'].fillna(0).astype(int),
        'ArrivalDayOffset': df['arrival_day'].fillna(df['departure_day']).fillna(1).astype(int),
        'DepartureDayOffset': df['departure_day'].fillna(df['arrival_day']).fillna(1).astype(int),
        'StopCount': 1,
        'ScheduledDwellMinutes': dwell.astype(int),
        'SegmentDistanceKm': segment.astype(int),
    })
    bulk_load(engine, fact, 'Fact_TrainSchedule')
    print(f"✅ Loaded {len(fact):,} rows into Fact_TrainSchedule ({before - len(df):,} unmapped skipped).")


def main():
    engine = get_engine()
    sched = load_schedule_frame(find_raw_file('combined_schedule.csv'))
    load_schedule_fact(engine, sched)
    load_fact_table(engine, find_raw_file('combined_delay.csv'), sched)


if __name__ == "__main__":
    main()
