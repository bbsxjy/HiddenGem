"""
Simple database connection test.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2

print("=" * 60)
print("Database Connection Test")
print("=" * 60)

# Test connection parameters
params = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'password',
    'dbname': 'postgres',  # Connect to default postgres database first
    'client_encoding': 'utf8'
}

print(f"\n[1/3] Testing connection to PostgreSQL server...")
print(f"      Host: {params['host']}")
print(f"      Port: {params['port']}")
print(f"      User: {params['user']}")

try:
    conn = psycopg2.connect(**params)
    conn.close()
    print("      ✓ Connection successful!")
except Exception as e:
    print(f"      ✗ Connection failed: {e}")
    print("\n" + "=" * 60)
    print("DIAGNOSIS:")
    print("=" * 60)
    print("PostgreSQL server is not accessible. Please check:")
    print("  1. Is Docker running? Run: docker ps")
    print("  2. Is PostgreSQL container running? Run: docker ps | findstr postgres")
    print("  3. Start containers: docker-compose up -d")
    print("  4. Check logs: docker logs hiddengem-postgres")
    sys.exit(1)

print(f"\n[2/3] Checking if database 'hiddengem' exists...")
params['dbname'] = 'postgres'
try:
    conn = psycopg2.connect(**params)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname='hiddengem'")
    exists = cur.fetchone() is not None

    if exists:
        print("      ✓ Database 'hiddengem' exists")
    else:
        print("      ✗ Database 'hiddengem' does not exist")
        print("      Creating database...")
        conn.autocommit = True
        cur.execute("CREATE DATABASE hiddengem")
        print("      ✓ Database 'hiddengem' created")

    cur.close()
    conn.close()
except Exception as e:
    print(f"      ✗ Error: {e}")
    sys.exit(1)

print(f"\n[3/3] Testing connection to 'hiddengem' database...")
params['dbname'] = 'hiddengem'
try:
    conn = psycopg2.connect(**params)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"      ✓ Connected to hiddengem database")
    print(f"      PostgreSQL version: {version.split(',')[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"      ✗ Connection failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("SUCCESS - Database is ready!")
print("=" * 60)
print("\nYou can now run: python scripts/init_db.py")
