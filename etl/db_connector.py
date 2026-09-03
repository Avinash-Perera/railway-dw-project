import os
from sqlalchemy import create_engine

def get_engine():
    """
    Creates and returns a SQLAlchemy engine connected to the MySQL data warehouse.
    Uses environment variables for configuration with defaults falling back to
    the project specifications.
    """
    host = os.getenv('MYSQL_HOST', '127.0.0.1')
    port = os.getenv('MYSQL_PORT', '3306')
    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', 'dw_password')
    database = os.getenv('MYSQL_DB', 'railway_dw')
    
    # Connection string format for PyMySQL
    connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    
    # Create the engine
    engine = create_engine(connection_string, pool_pre_ping=True)
    return engine
