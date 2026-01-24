#!/usr/bin/env python3
import psycopg2

# Supabase connection string from screenshot
DATABASE_URL = "postgresql://postgres:[YOUR-PASSWORD]@db.xstexctqfpnkjgobonca.supabase.co:5432/postgres"

# Read the SQL migration script
with open('create_employee_schedules.sql', 'r') as f:
    migration_sql = f.read()

# Connect to Supabase and execute migration
try:
    print("Connecting to Supabase database...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cursor = conn.cursor()
    
    print("Executing migration script...")
    cursor.execute(migration_sql)
    
    print("Committing changes...")
    conn.commit()
    
    print("\n✅ Migration completed successfully!")
    
    # Verify the table was created
    cursor.execute("""
        SELECT COUNT(*) FROM employee_schedules;
    """)
    count = cursor.fetchone()[0]
    print(f"✅ employee_schedules table created with {count} records migrated")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n❌ Migration failed: {str(e)}")
    if conn:
        conn.rollback()
        conn.close()
    exit(1)
