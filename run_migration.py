#!/usr/bin/env python3
"""
One-off migration script to create the employee_schedules table.
This is only needed for databases created before init_db() was updated
to include the employee_schedules table automatically.

Usage:
    DATABASE_URL=<your-postgres-url> python3 run_migration.py
"""
import os
import sys
import psycopg2

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable is not set.")
    print("Usage: DATABASE_URL=<your-postgres-url> python3 run_migration.py")
    sys.exit(1)

# Read the SQL migration script
with open('create_employee_schedules.sql', 'r') as f:
    migration_sql = f.read()

conn = None
try:
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cursor = conn.cursor()

    print("Executing migration script...")
    cursor.execute(migration_sql)

    print("Committing changes...")
    conn.commit()

    print("\n✅ Migration completed successfully!")

    # Verify the table was created
    cursor.execute("SELECT COUNT(*) FROM employee_schedules;")
    count = cursor.fetchone()[0]
    print(f"✅ employee_schedules table created with {count} records migrated")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"\n❌ Migration failed: {str(e)}")
    if conn:
        conn.rollback()
        conn.close()
    sys.exit(1)
