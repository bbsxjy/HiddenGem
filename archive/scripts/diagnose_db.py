"""
Advanced database connection diagnostics.
Handles encoding issues and provides detailed error information.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force UTF-8 encoding for PostgreSQL
os.environ['PGCLIENTENCODING'] = 'UTF8'
os.environ['LANG'] = 'en_US.UTF-8'

print("=" * 70)
print("HiddenGem Database Connection Diagnostics")
print("=" * 70)

# Step 1: Check if Docker is running
print("\n[Step 1/5] Checking Docker...")
import subprocess

try:
    result = subprocess.run(['docker', 'ps'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if result.returncode == 0:
        print("  ✓ Docker is running")

        # Check if postgres container is running
        if 'hiddengem-postgres' in result.stdout or 'timescale' in result.stdout:
            print("  ✓ PostgreSQL container is running")
        else:
            print("  ✗ PostgreSQL container is NOT running")
            print("\n  Run this command to start it:")
            print("    docker-compose up -d")
            sys.exit(1)
    else:
        print("  ✗ Docker is not running or not accessible")
        print("  Please start Docker Desktop")
        sys.exit(1)
except FileNotFoundError:
    print("  ✗ Docker command not found")
    print("  Please install Docker Desktop")
    sys.exit(1)
except Exception as e:
    print(f"  ✗ Error checking Docker: {e}")
    sys.exit(1)

# Step 2: Check if port 5432 is listening
print("\n[Step 2/5] Checking if port 5432 is accessible...")
import socket

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('localhost', 5432))
    sock.close()

    if result == 0:
        print("  ✓ Port 5432 is open and listening")
    else:
        print("  ✗ Port 5432 is not accessible")
        print("\n  Possible reasons:")
        print("    1. PostgreSQL container is not fully started yet (wait 10-20 seconds)")
        print("    2. Port 5432 is being used by another application")
        print("    3. Docker port mapping issue")
        print("\n  Try:")
        print("    docker-compose down")
        print("    docker-compose up -d")
        print("    timeout /t 20")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Error checking port: {e}")
    sys.exit(1)

# Step 3: Try raw psycopg2 connection with error handling
print("\n[Step 3/5] Testing raw PostgreSQL connection...")

try:
    import psycopg2
    from psycopg2 import OperationalError

    # Try connection with explicit encoding
    conn_params = {
        'host': 'localhost',
        'port': 5432,
        'user': 'postgres',
        'password': 'password',
        'dbname': 'postgres',
        'connect_timeout': 5,
        'options': '-c client_encoding=UTF8'
    }

    print(f"  Attempting connection...")
    print(f"    Host: {conn_params['host']}")
    print(f"    Port: {conn_params['port']}")
    print(f"    User: {conn_params['user']}")
    print(f"    Database: {conn_params['dbname']}")

    try:
        conn = psycopg2.connect(**conn_params)
        print("  ✓ Successfully connected to PostgreSQL!")

        # Get version
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"  ✓ PostgreSQL version: {version.split()[0]} {version.split()[1]}")
        cur.close()
        conn.close()

    except OperationalError as e:
        print(f"  ✗ Connection failed: {str(e)[:200]}")
        print("\n  Detailed error information:")

        # Try to decode error message properly
        error_str = str(e)
        if 'connection' in error_str.lower() and 'refused' in error_str.lower():
            print("    ERROR TYPE: Connection Refused")
            print("    MEANING: PostgreSQL server is not accepting connections")
            print("\n  Solutions:")
            print("    1. Wait 10-20 seconds for PostgreSQL to fully start")
            print("    2. Check Docker logs: docker logs hiddengem-postgres")
            print("    3. Restart containers: docker-compose restart")
        elif 'password' in error_str.lower() or 'authentication' in error_str.lower():
            print("    ERROR TYPE: Authentication Failed")
            print("    MEANING: Username or password is incorrect")
            print("\n  Solutions:")
            print("    1. Check .env file for correct password")
            print("    2. Default password should be 'password'")
        else:
            print(f"    ERROR TYPE: Unknown - {error_str[:100]}")

        sys.exit(1)

except ImportError:
    print("  ✗ psycopg2 module not found")
    print("  Install it with: pip install psycopg2-binary")
    sys.exit(1)
except UnicodeDecodeError as e:
    print(f"  ✗ Encoding error: {e}")
    print("\n  This means PostgreSQL returned an error in non-UTF8 encoding")
    print("  The underlying issue is likely connection failure")
    print("\n  Try these steps:")
    print("    1. docker-compose down")
    print("    2. docker-compose up -d")
    print("    3. timeout /t 20  (wait 20 seconds)")
    print("    4. docker logs hiddengem-postgres")
    sys.exit(1)
except Exception as e:
    print(f"  ✗ Unexpected error: {type(e).__name__}: {e}")
    sys.exit(1)

# Step 4: Check/Create hiddengem database
print("\n[Step 4/5] Checking 'hiddengem' database...")

try:
    conn_params['dbname'] = 'postgres'
    conn = psycopg2.connect(**conn_params)
    conn.autocommit = True
    cur = conn.cursor()

    # Check if database exists
    cur.execute("SELECT 1 FROM pg_database WHERE datname='hiddengem'")
    exists = cur.fetchone() is not None

    if exists:
        print("  ✓ Database 'hiddengem' exists")
    else:
        print("  ℹ Database 'hiddengem' does not exist, creating...")
        cur.execute("CREATE DATABASE hiddengem ENCODING 'UTF8'")
        print("  ✓ Database 'hiddengem' created successfully")

    cur.close()
    conn.close()

except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

# Step 5: Test connection to hiddengem database
print("\n[Step 5/5] Testing connection to 'hiddengem' database...")

try:
    conn_params['dbname'] = 'hiddengem'
    conn = psycopg2.connect(**conn_params)

    cur = conn.cursor()
    cur.execute("SELECT current_database(), current_user;")
    db, user = cur.fetchone()
    print(f"  ✓ Connected to database: {db}")
    print(f"  ✓ Connected as user: {user}")

    cur.close()
    conn.close()

except Exception as e:
    print(f"  ✗ Error: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("✓✓✓ ALL CHECKS PASSED ✓✓✓")
print("=" * 70)
print("\nDatabase is ready for initialization!")
print("\nNext step: Run the following command")
print("  python scripts/init_db.py")
print("=" * 70)
