import os
import pandas as pd
import numpy as np
from sqlalchemy import text
from etl.db_connector import get_engine

def get_mapping_dictionaries(engine):
    """
    Fetches the dimension tables to create lookup dictionaries for mapping
    natural keys to surrogate keys.
    """
    print("Fetching dimension mappings...")
    
    # 1. Fetch Station mappings
    with engine.connect() as conn:
        station_df = pd.read_sql("SELECT StationSK, StationCode FROM Dim_Station", conn)
        station_map = dict(zip(station_df['StationCode'], station_df['StationSK']))
        
        # 2. Fetch Train mappings
        train_df = pd.read_sql("SELECT TrainSK, TrainNumber FROM Dim_Train", conn)
        train_map = dict(zip(train_df['TrainNumber'], train_df['TrainSK']))
        
    return station_map, train_map

def derive_delay_cat_sk(delay_minutes):
    """
    Maps continuous delay minutes to the banded DelayCatSK.
    Based on Dim_DelayCategory rules:
    1: <= 0 (On-Time / Early)
    2: 1 - 15 (Minor Delay)
    3: 16 - 45 (Moderate Delay)
    4: > 45 (Severe Delay)
    """
    if delay_minutes <= 0:
        return 1
    elif 1 <= delay_minutes <= 15:
        return 2
    elif 16 <= delay_minutes <= 45:
        return 3
    else:
        return 4

def load_fact_table(engine, csv_path):
    print(f"Loading Fact table from {csv_path} in chunks...")
    
    # Pre-fetch lookup dictionaries
    station_map, train_map = get_mapping_dictionaries(engine)
    
    chunk_size = 50000
    chunk_iter = pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False)
    
    total_rows = 0
    total_inserted = 0
    
    for i, chunk in enumerate(chunk_iter, start=1):
        print(f"Processing chunk {i}...")
        total_rows += len(chunk)
        
        # 1. Fill null delays with 0
        chunk['delay'] = chunk['delay'].fillna(0).astype(int)
        
        # 2. Generate DateSK
        # date format in csv: '2025-02-08' -> DateSK: 20250208
        chunk['DateSK'] = chunk['date'].astype(str).str.replace('-', '').astype(int)
        
        # 3. Map StationSK
        chunk['station_name'] = chunk['station_name'].astype(str).str.strip()
        chunk['StationSK'] = chunk['station_name'].map(station_map)
        
        # 4. Map TrainSK
        # Format train_no to string, just like in Dim_Train
        chunk['train_no'] = chunk['train_no'].astype(str).str.strip()
        chunk['TrainSK'] = chunk['train_no'].map(train_map)
        
        # Drop rows where we couldn't find a matching dimension (referential integrity)
        # In a real DW, we might assign these to a generic "Unknown" SK (-1)
        chunk = chunk.dropna(subset=['StationSK', 'TrainSK'])
        
        # 5. Derive DelayCatSK
        chunk['DelayCatSK'] = chunk['delay'].apply(derive_delay_cat_sk)
        
        # 6. Determine IsDelayed (boolean indicator)
        chunk['IsDelayed'] = (chunk['delay'] > 0).astype(int)
        
        # Prepare the final DataFrame matching Fact_TrainDelay schema
        fact_df = pd.DataFrame({
            'DateSK': chunk['DateSK'].astype(int),
            'StationSK': chunk['StationSK'].astype(int),
            'TrainSK': chunk['TrainSK'].astype(int),
            'DelayCatSK': chunk['DelayCatSK'].astype(int),
            'DelayMinutes': chunk['delay'].astype(int),
            'IsDelayed': chunk['IsDelayed'].astype(int)
        })
        
        # 7. Append to MySQL Fact table
        try:
            fact_df.to_sql('Fact_TrainDelay', con=engine, if_exists='append', index=False)
            total_inserted += len(fact_df)
            print(f"  -> Inserted {len(fact_df)} rows for chunk {i}.")
        except Exception as e:
            print(f"  -> ⚠️ Error inserting chunk {i}: {e}")
            
    print(f"✅ Fact load complete. Inserted {total_inserted} / {total_rows} rows successfully.")

def main():
    engine = get_engine()
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_data_dir = os.path.join(base_dir, 'data', 'raw')
    
    fact_csv = os.path.join(raw_data_dir, 'combined_delay.csv')
    
    load_fact_table(engine, fact_csv)

if __name__ == "__main__":
    main()
