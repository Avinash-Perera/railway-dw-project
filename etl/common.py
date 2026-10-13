"""
Shared helpers / reference mappings for the Railway DW ETL.
"""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def find_raw_file(filename):
    """Locate a source CSV in data/raw, data, or the project root."""
    candidates = [
        os.path.join(PROJECT_ROOT, 'data', 'raw', filename),
        os.path.join(PROJECT_ROOT, 'data', filename),
        os.path.join(PROJECT_ROOT, filename),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"{filename} not found in: {candidates}")


def max_rows():
    """Optional ETL_MAX_ROWS env var limits fact rows (for quick testing)."""
    value = os.getenv('ETL_MAX_ROWS')
    return int(value) if value else None


def normalize_train_no(series):
    """Train numbers are 5-digit zero padded in the delay/schedule files."""
    return series.astype(str).str.strip().str.replace(r'\.0$', '', regex=True).str.zfill(5)


# Train type code -> (readable name, service class)
TRAIN_TYPE_MAP = {
    'PASS-TRAINS': ('Passenger', 'Passenger'),
    'EXP-TRAINS':  ('Express', 'Mail / Express'),
    'SF-TRAINS':   ('Superfast', 'Mail / Express'),
    'PRM-TRAINS':  ('Premium', 'Premium'),
    'T18-TRAINS':  ('Train 18 (Vande Bharat)', 'Premium'),
    'SHT-TRAINS':  ('Shatabdi', 'Premium'),
    'GRB-TRAINS':  ('Garib Rath', 'Premium'),
    'RAJ-TRAINS':  ('Rajdhani', 'Premium'),
}

ZONE_NAME_MAP = {
    'NR': 'Northern Railway', 'ECR': 'East Central Railway',
    'SCR': 'South Central Railway', 'SR': 'Southern Railway',
    'WR': 'Western Railway', 'ER': 'Eastern Railway',
    'NWR': 'North Western Railway', 'NFR': 'Northeast Frontier Railway',
    'NER': 'North Eastern Railway', 'CR': 'Central Railway',
    'NCR': 'North Central Railway', 'SWR': 'South Western Railway',
    'SER': 'South Eastern Railway', 'ECOR': 'East Coast Railway',
    'SECR': 'South East Central Railway', 'WCR': 'West Central Railway',
    'KR': 'Konkan Railway', 'SCOR': 'South Coast Railway',
}

UNKNOWN_TIME_SK = 9999


def minutes_to_time_sk(sched_sk, delay_min):
    """Scheduled TimeSK (HHMM) + delay minutes -> actual TimeSK (wraps past midnight).
    Unknown scheduled time stays Unknown."""
    import numpy as np
    sched_sk = np.asarray(sched_sk, dtype='int64')
    delay_min = np.asarray(delay_min, dtype='int64')
    known = sched_sk != UNKNOWN_TIME_SK
    total = ((sched_sk // 100) * 60 + sched_sk % 100 + delay_min) % 1440
    return np.where(known, (total // 60) * 100 + total % 60, UNKNOWN_TIME_SK).astype('int64')


def bulk_load(engine, df, table):
    """Append a DataFrame to a MySQL table.

    Fast path: write a temp TSV and run LOAD DATA LOCAL INFILE (one atomic statement).
    Fallback : pandas.to_sql (multi-row INSERTs) if LOCAL INFILE is disabled on the server.
    """
    import tempfile
    if df.empty:
        return 0
    cols = ', '.join(df.columns)
    fd, path = tempfile.mkstemp(suffix='.tsv')
    os.close(fd)
    try:
        df.to_csv(path, sep='\t', header=False, index=False, na_rep='\\N', lineterminator='\n')
        raw = engine.raw_connection()
        try:
            cur = raw.cursor()
            cur.execute(
                f"LOAD DATA LOCAL INFILE '{path}' INTO TABLE {table} "
                f"FIELDS TERMINATED BY '\\t' LINES TERMINATED BY '\\n' ({cols})")
            loaded = cur.rowcount
            cur.execute("SHOW COUNT(*) WARNINGS")
            warnings = cur.fetchone()[0]
            if loaded != len(df) or warnings:
                raw.rollback()
                raise RuntimeError(f"Bulk load into {table}: expected {len(df)} rows, "
                                   f"loaded {loaded}, warnings {warnings}")
            raw.commit()
            return len(df)
        except RuntimeError:
            raise
        except Exception as exc:
            raw.rollback()
            if 'local' not in str(exc).lower() and '1148' not in str(exc) and '3948' not in str(exc):
                raise
        finally:
            raw.close()
    finally:
        os.remove(path)
    df.to_sql(table, con=engine, if_exists='append', index=False, chunksize=10000)
    return len(df)
