import os
import sys
import pandas as pd
from datetime import date, timedelta
from sqlalchemy import text

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from etl.db_connector import get_engine
from etl.common import (find_raw_file, normalize_train_no, TRAIN_TYPE_MAP,
                        ZONE_NAME_MAP, UNKNOWN_TIME_SK)

# Representative Indian public holidays inside the calendar range (2024-2026).
HOLIDAYS = {
    date(2024, 1, 15): 'Makar Sankranti / Pongal',
    date(2024, 1, 26): 'Republic Day',
    date(2024, 3, 8): 'Maha Shivaratri',
    date(2024, 3, 25): 'Holi',
    date(2024, 3, 29): 'Good Friday',
    date(2024, 4, 11): 'Eid ul-Fitr',
    date(2024, 4, 14): 'Ambedkar Jayanti',
    date(2024, 4, 17): 'Ram Navami',
    date(2024, 4, 21): 'Mahavir Jayanti',
    date(2024, 5, 23): 'Buddha Purnima',
    date(2024, 8, 15): 'Independence Day',
    date(2024, 8, 26): 'Janmashtami',
    date(2024, 10, 2): 'Gandhi Jayanti',
    date(2024, 10, 12): 'Dussehra',
    date(2024, 10, 31): 'Diwali',
    date(2024, 11, 15): 'Guru Nanak Jayanti',
    date(2024, 12, 25): 'Christmas',
    date(2025, 1, 14): 'Makar Sankranti / Pongal',
    date(2025, 1, 26): 'Republic Day',
    date(2025, 2, 26): 'Maha Shivaratri',
    date(2025, 3, 14): 'Holi',
    date(2025, 3, 31): 'Eid ul-Fitr',
    date(2025, 4, 10): 'Mahavir Jayanti',
    date(2025, 4, 14): 'Ambedkar Jayanti',
    date(2025, 4, 18): 'Good Friday',
    date(2025, 5, 12): 'Buddha Purnima',
    date(2025, 8, 9): 'Raksha Bandhan',
    date(2025, 8, 15): 'Independence Day',
    date(2025, 8, 16): 'Janmashtami',
    date(2025, 8, 27): 'Ganesh Chaturthi',
    date(2025, 10, 2): 'Gandhi Jayanti / Dussehra',
    date(2025, 10, 20): 'Diwali',
    date(2025, 11, 5): 'Guru Nanak Jayanti',
    date(2025, 12, 25): 'Christmas',
    date(2026, 1, 14): 'Makar Sankranti / Pongal',
    date(2026, 1, 26): 'Republic Day',
    date(2026, 2, 15): 'Maha Shivaratri',
    date(2026, 3, 4): 'Holi',
    date(2026, 3, 21): 'Eid ul-Fitr',
    date(2026, 4, 3): 'Good Friday',
    date(2026, 4, 14): 'Ambedkar Jayanti',
    date(2026, 8, 15): 'Independence Day',
    date(2026, 10, 2): 'Gandhi Jayanti',
    date(2026, 10, 20): 'Dussehra',
    date(2026, 11, 8): 'Diwali',
    date(2026, 12, 25): 'Christmas',
}

SCD_START_DATE = date(2024, 1, 1)
SCD_OPEN_END_DATE = date(9999, 12, 31)


def season_for_month(month):
    if month in (12, 1, 2):
        return 'Winter'
    if month in (3, 4, 5):
        return 'Summer'
    if month in (6, 7, 8, 9):
        return 'Monsoon'
    return 'Post-Monsoon'


def table_has_rows(engine, table):
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() > 0


def load_date_dimension(engine):
    print("Generating and loading Date dimension...")
    if table_has_rows(engine, 'Dim_Date'):
        print("ℹ️ Dim_Date already populated - skipping.")
        return
    start_date = date(2024, 1, 1)
    end_date = date(2026, 12, 31)

    rows = []
    curr = start_date
    while curr <= end_date:
        rows.append({
            'DateSK': int(curr.strftime("%Y%m%d")),
            'FullDate': curr,
            'Year': curr.year,
            'Quarter': (curr.month - 1) // 3 + 1,
            'QuarterName': f"Q{(curr.month - 1) // 3 + 1}",
            'Month': curr.month,
            'MonthName': curr.strftime('%B'),
            'Day': curr.day,
            'WeekOfYear': int(curr.strftime('%V')),
            'DayOfWeek': curr.strftime('%A'),
            'IsWeekend': 1 if curr.weekday() >= 5 else 0,
            'IsHoliday': 1 if curr in HOLIDAYS else 0,
            'HolidayName': HOLIDAYS.get(curr, 'Regular Day'),
            'Season': season_for_month(curr.month),
        })
        curr += timedelta(days=1)

    pd.DataFrame(rows).to_sql('Dim_Date', con=engine, if_exists='append', index=False)
    print(f"✅ Successfully loaded {len(rows)} rows into Dim_Date.")


def time_band(hour):
    if 7 <= hour <= 9:
        return 'Morning Peak'
    if 17 <= hour <= 19:
        return 'Evening Peak'
    if 5 <= hour <= 6:
        return 'Early Morning'
    if 10 <= hour <= 16:
        return 'Midday'
    if 20 <= hour <= 21:
        return 'Late Evening'
    return 'Night'


def load_time_dimension(engine):
    print("Generating and loading Time dimension...")
    if table_has_rows(engine, 'Dim_Time'):
        print("ℹ️ Dim_Time already populated - skipping.")
        return
    rows = []
    for hour in range(24):
        for minute in range(60):
            band = time_band(hour)
            rows.append({
                'TimeSK': hour * 100 + minute,
                'TimeLabel': f"{hour:02d}:{minute:02d}",
                'Hour24': hour,
                'Minute': minute,
                'TimeOfDayBand': band,
                'IsPeakHour': 1 if band in ('Morning Peak', 'Evening Peak') else 0,
            })
    rows.append({'TimeSK': UNKNOWN_TIME_SK, 'TimeLabel': 'Unknown', 'Hour24': -1,
                 'Minute': -1, 'TimeOfDayBand': 'Unknown', 'IsPeakHour': 0})
    pd.DataFrame(rows).to_sql('Dim_Time', con=engine, if_exists='append', index=False)
    print(f"✅ Successfully loaded {len(rows)} rows into Dim_Time.")


def load_train_dimension(engine, csv_path):
    """Initial load of the SCD Type 2 train dimension (one open, current row per train)."""
    print(f"Loading Train dimension from {csv_path}...")
    if table_has_rows(engine, 'Dim_Train'):
        print("ℹ️ Dim_Train already populated - skipping.")
        return
    df = pd.read_csv(csv_path, dtype={'train_no': str}, encoding='utf-8', encoding_errors='replace')
    df = df.dropna(subset=['train_no'])
    df['TrainNumber'] = normalize_train_no(df['train_no'])
    df = df.drop_duplicates(subset=['TrainNumber'])

    df['TrainName'] = df['train_name'].astype(str).str.strip().str.slice(0, 150)
    df['TrainTypeCode'] = df['type_code'].astype(str).str.strip()
    df['TrainTypeName'] = df['TrainTypeCode'].map(lambda c: TRAIN_TYPE_MAP.get(c, ('Other', 'Other'))[0])
    df['ServiceClass'] = df['TrainTypeCode'].map(lambda c: TRAIN_TYPE_MAP.get(c, ('Other', 'Other'))[1])
    df['EffectiveStartDate'] = SCD_START_DATE
    df['EffectiveEndDate'] = SCD_OPEN_END_DATE
    df['IsCurrent'] = 1

    df = df[['TrainNumber', 'TrainName', 'TrainTypeCode', 'TrainTypeName', 'ServiceClass',
             'EffectiveStartDate', 'EffectiveEndDate', 'IsCurrent']]
    df.to_sql('Dim_Train', con=engine, if_exists='append', index=False)
    print(f"✅ Successfully loaded {len(df)} rows into Dim_Train.")


def apply_train_scd2_change(engine, train_number, new_name=None, new_type_code=None, change_date=None):
    """
    SCD Type 2 update: expire the current row of a train and insert a new version.
    """
    change_date = change_date or date.today()
    train_number = str(train_number).zfill(5)
    with engine.begin() as conn:
        current = conn.execute(text(
            "SELECT TrainName, TrainTypeCode FROM Dim_Train "
            "WHERE TrainNumber = :n AND IsCurrent = 1"), {'n': train_number}).fetchone()
        if current is None:
            raise ValueError(f"No current row for train {train_number}")
        name = new_name or current[0]
        type_code = new_type_code or current[1]
        type_name, service_class = TRAIN_TYPE_MAP.get(type_code, ('Other', 'Other'))
        conn.execute(text(
            "UPDATE Dim_Train SET EffectiveEndDate = :d, IsCurrent = 0 "
            "WHERE TrainNumber = :n AND IsCurrent = 1"),
            {'d': change_date - timedelta(days=1), 'n': train_number})
        conn.execute(text(
            "INSERT INTO Dim_Train (TrainNumber, TrainName, TrainTypeCode, TrainTypeName, "
            "ServiceClass, EffectiveStartDate, EffectiveEndDate, IsCurrent) "
            "VALUES (:n, :nm, :tc, :tn, :sc, :sd, :ed, 1)"),
            {'n': train_number, 'nm': name, 'tc': type_code, 'tn': type_name,
             'sc': service_class, 'sd': change_date, 'ed': SCD_OPEN_END_DATE})


def load_station_dimension(engine, csv_path):
    print(f"Loading Station dimension from {csv_path}...")
    if table_has_rows(engine, 'Dim_Station'):
        print("ℹ️ Dim_Station already populated - skipping.")
        return
    df = pd.read_csv(csv_path, encoding='utf-8', encoding_errors='replace')
    df = df.rename(columns={
        'station_name': 'StationCode',
        'station_full_name': 'StationName',
        'station_zone': 'ZoneCode',
    })
    # station_address is intentionally dropped (non-analytical operational attribute)
    df = df[['StationCode', 'StationName', 'ZoneCode']]
    df = df.dropna(subset=['StationCode'])
    df['StationCode'] = df['StationCode'].astype(str).str.strip()
    df['StationName'] = df['StationName'].fillna(df['StationCode']).astype(str).str.strip().str.slice(0, 150)
    df['ZoneCode'] = df['ZoneCode'].fillna('Unknown').astype(str).str.strip()
    df['ZoneName'] = df['ZoneCode'].map(lambda z: ZONE_NAME_MAP.get(z, 'Unclassified (' + z + ')'))
    df = df.drop_duplicates(subset=['StationCode'])
    df.to_sql('Dim_Station', con=engine, if_exists='append', index=False)
    print(f"✅ Successfully loaded {len(df)} rows into Dim_Station.")


def main():
    engine = get_engine()
    load_date_dimension(engine)
    load_time_dimension(engine)
    load_train_dimension(engine, find_raw_file('train_details.csv'))
    load_station_dimension(engine, find_raw_file('station_full_names.csv'))


if __name__ == "__main__":
    main()
