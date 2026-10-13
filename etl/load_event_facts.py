"""
Loaders for the remaining business events.

    train_delays.csv (journey-level operational feed, 30 journeys)
        -> Fact_JourneyCancellation   (Event 5: rows with cancellation_status = 1)
        -> Fact_DelayIncident         (Event 6: delayed, non-cancelled journeys + primary delay reason)
        -> Fact_WeatherObservation    (Event 7: weather recorded for every journey)
    Fact_TrainDelay (already loaded)
        -> Fact_TrainDailySnapshot    (Event 8: periodic snapshot, one row per train per date)

Re-running is safe: every target fact table is truncated first.
"""
import csv
import os
import sys
import pandas as pd
from sqlalchemy import text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from etl.db_connector import get_engine
from etl.common import find_raw_file, normalize_train_no, bulk_load

JOURNEY_COLUMNS = ['train_number', 'train_name', 'train_type', 'source_station', 'destination_station',
                   'journey_date', 'scheduled_departure', 'actual_departure', 'departure_delay_min',
                   'scheduled_arrival', 'actual_arrival', 'arrival_delay_min', 'cancellation_status',
                   'cancellation_reason', 'delay_reason', 'zone', 'weather_condition']


def read_journey_feed(csv_path):
    """Read train_delays.csv, repairing cancelled rows that are missing one field.

    Data quality: cancelled journeys have 16 instead of 17 fields - the empty
    'actual_arrival' value was dropped by the source system. The missing empty
    field is re-inserted after 'scheduled_arrival' so every column lines up.
    """
    rows, repaired = [], 0
    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.reader(fh)
        header = next(reader)
        assert header == JOURNEY_COLUMNS, f"Unexpected header in {csv_path}: {header}"
        for rec in reader:
            if not rec:
                continue
            if len(rec) == len(JOURNEY_COLUMNS) - 1:
                rec = rec[:10] + [''] + rec[10:]
                repaired += 1
            if len(rec) != len(JOURNEY_COLUMNS):
                raise ValueError(f"Malformed row in {csv_path}: {rec}")
            rows.append(rec)
    df = pd.DataFrame(rows, columns=JOURNEY_COLUMNS).replace({'': None})
    df['TrainNumber'] = normalize_train_no(df['train_number'])
    df['DateSK'] = df['journey_date'].str.replace('-', '', regex=False).astype(int)
    for col in ('departure_delay_min', 'arrival_delay_min', 'cancellation_status'):
        df[col] = pd.to_numeric(df[col]).fillna(0).astype(int)
    print(f"Read {len(df)} journeys from {os.path.basename(csv_path)} ({repaired} cancelled rows repaired).")
    return df


def lookups(engine):
    with engine.connect() as conn:
        q = lambda sql: pd.read_sql(sql, conn)
        return {
            'station': dict(q("SELECT StationCode, StationSK FROM Dim_Station").values),
            'train': dict(q("SELECT TrainNumber, TrainSK FROM Dim_Train WHERE IsCurrent = 1").values),
            'cancel': dict(q("SELECT CancellationReasonName, CancellationReasonSK FROM Dim_CancellationReason").values),
            'reason': dict(q("SELECT DelayReasonName, DelayReasonSK FROM Dim_DelayReason").values),
            'weather': dict(q("SELECT WeatherCondition, WeatherSK FROM Dim_Weather").values),
            'dates': set(q("SELECT DateSK FROM Dim_Date")['DateSK']),
        }


def delay_cat(minutes):
    return 1 if minutes <= 0 else 2 if minutes <= 15 else 3 if minutes <= 45 else 4


def map_keys(df, lk):
    """Surrogate key lookups. Unknown reason/weather values map to the 'Unknown' member."""
    out = df.copy()
    out['TrainSK'] = out['TrainNumber'].map(lk['train'])
    out['OriginStationSK'] = out['source_station'].map(lk['station'])
    out['DestinationStationSK'] = out['destination_station'].map(lk['station'])
    out['CancellationReasonSK'] = out['cancellation_reason'].map(lk['cancel']).fillna(lk['cancel']['Unknown'])
    out['DelayReasonSK'] = out['delay_reason'].map(lk['reason']).fillna(lk['reason']['Unknown'])
    out['WeatherSK'] = out['weather_condition'].map(lk['weather']).fillna(lk['weather']['Unknown'])
    ok = (out[['TrainSK', 'OriginStationSK', 'DestinationStationSK']].notna().all(axis=1)
          & out['DateSK'].isin(lk['dates']))
    if (~ok).any():
        print(f"  ⚠️ {int((~ok).sum())} journeys skipped (train/station/date not in dimensions)")
    out = out[ok]
    for c in ('TrainSK', 'OriginStationSK', 'DestinationStationSK', 'CancellationReasonSK',
              'DelayReasonSK', 'WeatherSK'):
        out[c] = out[c].astype(int)
    return out


def load_journey_events(engine, csv_path):
    tables = ['Fact_JourneyCancellation', 'Fact_DelayIncident', 'Fact_WeatherObservation']
    with engine.begin() as conn:
        for t in tables:
            conn.execute(text(f"TRUNCATE TABLE {t}"))
    df = map_keys(read_journey_feed(csv_path), lookups(engine))

    # Event 5 - cancellations
    c = df[df['cancellation_status'] == 1]
    cancel = pd.DataFrame({
        'DateSK': c['DateSK'], 'TrainSK': c['TrainSK'],
        'OriginStationSK': c['OriginStationSK'], 'DestinationStationSK': c['DestinationStationSK'],
        'CancellationReasonSK': c['CancellationReasonSK'], 'CancellationCount': 1,
    })

    # Event 6 - delay incidents: journeys that ran and arrived late, measured at the destination
    d = df[(df['cancellation_status'] == 0) & (df['arrival_delay_min'] > 0)]
    incident = pd.DataFrame({
        'DateSK': d['DateSK'], 'TrainSK': d['TrainSK'], 'StationSK': d['DestinationStationSK'],
        'DelayReasonSK': d['DelayReasonSK'], 'DelayCatSK': d['arrival_delay_min'].map(delay_cat),
        'IncidentDelayMinutes': d['arrival_delay_min'], 'IncidentCount': 1,
    })

    # Event 7 - weather observed at the origin for every journey (incl. cancelled ones)
    weather = pd.DataFrame({
        'DateSK': df['DateSK'], 'TrainSK': df['TrainSK'], 'StationSK': df['OriginStationSK'],
        'WeatherSK': df['WeatherSK'], 'ObservationCount': 1,
        'JourneyDelayMinutes': df['arrival_delay_min'],
        'WeatherAffectedFlag': (df['weather_condition'].fillna('Unknown') != 'Clear').astype(int),
    })

    for name, frame in (('Fact_JourneyCancellation', cancel), ('Fact_DelayIncident', incident),
                        ('Fact_WeatherObservation', weather)):
        bulk_load(engine, frame, name)
        print(f"✅ Loaded {len(frame):,} rows into {name}.")


def load_daily_snapshot(engine):
    """Event 8 - periodic snapshot aggregated inside the warehouse from Fact_TrainDelay."""
    print("Building Fact_TrainDailySnapshot from Fact_TrainDelay (GROUP BY DateSK, TrainSK)...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE Fact_TrainDailySnapshot"))
        conn.execute(text("""
            INSERT INTO Fact_TrainDailySnapshot
                (DateSK, TrainSK, StopsRecorded, DelayedStops, MaxDelayMinutes,
                 TotalDelayMinutes, TotalExcessDelayMinutes)
            SELECT DateSK, TrainSK, SUM(TripCount), SUM(IsDelayed), MAX(DelayMinutes),
                   SUM(DelayMinutes), SUM(ExcessDelayMinutes)
            FROM Fact_TrainDelay
            GROUP BY DateSK, TrainSK"""))
        n = conn.execute(text("SELECT COUNT(*) FROM Fact_TrainDailySnapshot")).scalar()
    print(f"✅ Loaded {n:,} rows into Fact_TrainDailySnapshot.")


def main():
    engine = get_engine()
    load_journey_events(engine, find_raw_file('train_delays.csv'))
    load_daily_snapshot(engine)


if __name__ == "__main__":
    main()
