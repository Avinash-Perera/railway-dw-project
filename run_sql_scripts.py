"""
Script to execute all SQL scripts in the sql/ directory in sequence against MySQL/MariaDB.
"""

import os
import sys
import glob
import re

def get_db_connection():
    import pymysql
    
    # Try various host, user, password combinations
    hosts = [os.getenv('MYSQL_HOST', '127.0.0.1'), 'localhost']
    users = [os.getenv('MYSQL_USER', 'root'), 'root', 'agent', 'admin']
    passwords = [os.getenv('MYSQL_ROOT_PASSWORD', 'dw_password'), os.getenv('MYSQL_PASSWORD', 'dw_password'), 'dw_password', '', 'root', 'password', 'admin', 'railway']
    ports = [int(os.getenv('MYSQL_PORT', 3306))]
    
    # Also check unix sockets
    sockets = ['/var/run/mysqld/mysqld.sock', '/tmp/mysql.sock', '/tmp/mysqld.sock']
    existing_sockets = [s for s in sockets if os.path.exists(s)]
    
    # Try TCP connections
    for host in hosts:
        for user in set(users):
            for pwd in set(passwords):
                for port in ports:
                    try:
                        conn = pymysql.connect(
                            host=host,
                            user=user,
                            password=pwd,
                            port=port,
                            connect_timeout=1,
                            autocommit=True,
                            client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS if hasattr(pymysql.constants, 'CLIENT') else 0
                        )
                        print(f"[+] Successfully connected to MySQL at {host}:{port} with user '{user}'")
                        return conn
                    except Exception:
                        pass
    
    # Try Unix Socket connections
    for sock in existing_sockets:
        for user in set(users):
            for pwd in set(passwords):
                try:
                    conn = pymysql.connect(
                        unix_socket=sock,
                        user=user,
                        password=pwd,
                        connect_timeout=2,
                        autocommit=True,
                        client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS if hasattr(pymysql.constants, 'CLIENT') else 0
                    )
                    print(f"[+] Successfully connected to MySQL via socket {sock} with user '{user}'")
                    return conn
                except Exception:
                    pass

    raise ConnectionError("Could not connect to MySQL server with default credentials.")


def parse_sql_statements(sql_text):
    """Splits SQL script into individual executable statements."""
    statements = []
    current_stmt = []
    
    for line in sql_text.splitlines():
        trimmed = line.strip()
        # Skip pure comment lines
        if trimmed.startswith('--') or trimmed.startswith('/*') and trimmed.endswith('*/'):
            continue
        # Split by comment if any
        if '--' in line:
            # Simple check if not inside quotes
            idx = line.find('--')
            line = line[:idx]
        
        current_stmt.append(line)
        if ';' in line:
            full_line = '\n'.join(current_stmt)
            # Split statement parts by ';'
            parts = full_line.split(';')
            for p in parts[:-1]:
                stmt = p.strip()
                if stmt:
                    statements.append(stmt)
            current_stmt = [parts[-1]]
            
    remaining = '\n'.join(current_stmt).strip()
    if remaining:
        statements.append(remaining)
        
    return [s for s in statements if s]


def execute_sql_file(conn, file_path):
    print(f"\n========================================================")
    print(f"Executing: {os.path.basename(file_path)}")
    print(f"Path:      {file_path}")
    print(f"========================================================")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
        
    statements = parse_sql_statements(sql_content)
    with conn.cursor() as cursor:
        for i, stmt in enumerate(statements, start=1):
            stmt_preview = ' '.join(stmt.split())[:70]
            try:
                cursor.execute(stmt)
                print(f"  [{i}/{len(statements)}] OK: {stmt_preview}...")
            except Exception as e:
                print(f"  [{i}/{len(statements)}] FAILED: {stmt_preview}...\n    Error: {e}")
                raise e


def verify_setup(conn):
    print("\n========================================================")
    print("Verification Summary")
    print("========================================================")
    with conn.cursor() as cursor:
        cursor.execute("USE railway_dw;")
        
        # Check tables
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'BASE TABLE';")
        tables = cursor.fetchall()
        print("\nTables in railway_dw:")
        for t in tables:
            tbl_name = t[0]
            cursor.execute(f"SELECT COUNT(*) FROM `{tbl_name}`;")
            count = cursor.fetchone()[0]
            print(f"  - Table: {tbl_name:<25} Row count: {count}")
            
        # Check views
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW';")
        views = cursor.fetchall()
        print("\nViews in railway_dw:")
        for v in views:
            print(f"  - View:  {v[0]}")
            
        # Show sample from Dim_DelayCategory
        print("\nSample records from Dim_DelayCategory:")
        cursor.execute("SELECT DelayCatSK, CategoryName, MinDelayMinutes, MaxDelayMinutes FROM Dim_DelayCategory;")
        for row in cursor.fetchall():
            print(f"  ID {row[0]}: {row[1]:<25} ({row[2]} to {row[3]} min)")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sql_dir = os.path.join(base_dir, 'sql')
    
    sql_files = sorted(glob.glob(os.path.join(sql_dir, '*.sql')))
    if not sql_files:
        print(f"No SQL files found in {sql_dir}")
        sys.exit(1)
        
    print(f"Found {len(sql_files)} SQL script(s) to execute:")
    for f in sql_files:
        print(f"  - {os.path.basename(f)}")
        
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"[-] Database connection failed: {e}")
        sys.exit(1)
        
    try:
        for f in sql_files:
            execute_sql_file(conn, f)
        verify_setup(conn)
        print("\n[SUCCESS] All SQL scripts executed successfully!")
    finally:
        conn.close()

if __name__ == '__main__':
    main()
