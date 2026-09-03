import os
import pandas as pd
from datetime import date, timedelta
from etl.db_connector import get_engine

def load_date_dimension(engine):
    print("Generating and loading Date dimension...")
    start_date = date(2024, 1, 1)
    end_date = date(2026, 12, 31)
    
    dates_data = []
    curr_date = start_date
    while curr_date <= end_date:
        date_sk = int(curr_date.strftime("%Y%m%d"))
        dates_data.append({
            'DateSK': date_sk,
            'FullDate': curr_date,
            'Year': curr_date.year,
            'Quarter': (curr_date.month - 1) // 3 + 1,
            'Month': curr_date.month,
            'MonthName': curr_date.strftime('%B'),
            'Day': curr_date.day,
            'DayOfWeek': curr_date.strftime('%A'),
            'IsWeekend': 1 if curr_date.weekday() >= 5 else 0
        })
        curr_date += timedelta(days=1)
        
    df_date = pd.DataFrame(dates_data)
    
    try:
        df_date.to_sql('Dim_Date', con=engine, if_exists='append', index=False)
        print(f"✅ Successfully loaded {len(df_date)} rows into Dim_Date.")
    except Exception as e:
        print(f"⚠️ Dim_Date may already be populated or an error occurred: {e}")

def load_train_dimension(engine, csv_path):
    print(f"Loading Train dimension from {csv_path}...")
    try:
        # train_no,train_name,type_code
        df_train = pd.read_csv(csv_path)
        
        # Rename columns to match Dim_Train schema
        df_train = df_train.rename(columns={
            'train_no': 'TrainNumber',
            'train_name': 'TrainName',
            'type_code': 'TrainType'
        })
        
        # Clean data
        df_train = df_train.dropna(subset=['TrainNumber'])
        df_train['TrainNumber'] = df_train['TrainNumber'].astype(str).str.strip()
        df_train = df_train.drop_duplicates(subset=['TrainNumber'])
        
        df_train.to_sql('Dim_Train', con=engine, if_exists='append', index=False)
        print(f"✅ Successfully loaded {len(df_train)} rows into Dim_Train.")
    except Exception as e:
        print(f"⚠️ Error loading Dim_Train: {e}")

def load_station_dimension(engine, csv_path):
    print(f"Loading Station dimension from {csv_path}...")
    try:
        # station_name,station_full_name,station_zone,station_address
        df_station = pd.read_csv(csv_path)
        
        # Rename columns to match Dim_Station schema
        df_station = df_station.rename(columns={
            'station_name': 'StationCode',
            'station_full_name': 'StationName'
        })
        
        # Select only the needed columns
        df_station = df_station[['StationCode', 'StationName']]
        
        # Clean data
        df_station = df_station.dropna(subset=['StationCode'])
        df_station['StationCode'] = df_station['StationCode'].astype(str).str.strip()
        df_station = df_station.drop_duplicates(subset=['StationCode'])
        
        df_station.to_sql('Dim_Station', con=engine, if_exists='append', index=False)
        print(f"✅ Successfully loaded {len(df_station)} rows into Dim_Station.")
    except Exception as e:
        print(f"⚠️ Error loading Dim_Station: {e}")

def main():
    engine = get_engine()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_data_dir = os.path.join(base_dir, 'data', 'raw')
    
    train_csv = os.path.join(raw_data_dir, 'train_details.csv')
    station_csv = os.path.join(raw_data_dir, 'station_full_names.csv')
    
    load_date_dimension(engine)
    load_train_dimension(engine, train_csv)
    load_station_dimension(engine, station_csv)

if __name__ == "__main__":
    main()
