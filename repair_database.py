#!/usr/bin/env python3
"""
Emergency Database Repair Script
Fixes corrupted time formats and admin password
Run this ONCE in Railway, then delete it
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash

def repair_database():
    print("=" * 60)
    print("EMERGENCY DATABASE REPAIR SCRIPT")
    print("=" * 60)
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL not set")
        return False
    
    try:
        print("\n1. Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        print("✅ Connected successfully")
        
        # Fix 1: Admin Password
        print("\n2. Fixing admin password...")
        cursor.execute("SELECT id, username, password_hash FROM admins WHERE username = 'admin'")
        admin = cursor.fetchone()
        
        if admin:
            if not admin['password_hash'] or len(admin['password_hash']) < 10:
                print(f"   Found corrupted password for admin user")
                new_hash = generate_password_hash('admin123')
                cursor.execute("UPDATE admins SET password_hash = %s WHERE username = 'admin'", (new_hash,))
                print("   ✅ Admin password reset to: admin123")
            else:
                print("   ℹ️  Admin password looks OK, but resetting anyway...")
                new_hash = generate_password_hash('admin123')
                cursor.execute("UPDATE admins SET password_hash = %s WHERE username = 'admin'", (new_hash,))
                print("   ✅ Admin password reset to: admin123")
        else:
            print("   ⚠️  No admin user found, creating one...")
            new_hash = generate_password_hash('admin123')
            cursor.execute(
                "INSERT INTO admins (username, password_hash, full_name, role) VALUES (%s, %s, %s, %s)",
                ('admin', new_hash, 'Master Administrator', 'master_admin')
            )
            print("   ✅ Created admin user with password: admin123")
        
        conn.commit()
        
        # Fix 2: Time Formats in Employees Table
        print("\n3. Fixing time formats in employees table...")
        cursor.execute("SELECT id, employee_id, start_time, end_time FROM employees")
        employees = cursor.fetchall()
        
        fixed_count = 0
        for emp in employees:
            start_time = emp['start_time']
            end_time = emp['end_time']
            
            # Fix start_time if it has seconds
            if start_time and len(start_time.split(':')) == 3:
                new_start = ':'.join(start_time.split(':')[:2])
                cursor.execute("UPDATE employees SET start_time = %s WHERE id = %s", (new_start, emp['id']))
                fixed_count += 1
            
            # Fix end_time if it has seconds
            if end_time and len(end_time.split(':')) == 3:
                new_end = ':'.join(end_time.split(':')[:2])
                cursor.execute("UPDATE employees SET end_time = %s WHERE id = %s", (new_end, emp['id']))
                fixed_count += 1
        
        conn.commit()
        print(f"   ✅ Fixed {fixed_count} time format issues")
        
        # Fix 3: Verify Settings
        print("\n4. Checking settings table...")
        cursor.execute("SELECT key, value FROM settings")
        settings = cursor.fetchall()
        
        required_settings = {
            'grace_period': '10',
            'work_start_time': '08:00',
            'work_end_time': '17:00',
            'work_hours': '8'
        }
        
        for key, default_value in required_settings.items():
            cursor.execute("SELECT COUNT(*) as cnt FROM settings WHERE key = %s", (key,))
            if cursor.fetchone()['cnt'] == 0:
                cursor.execute("INSERT INTO settings (key, value) VALUES (%s, %s)", (key, default_value))
                print(f"   ✅ Added missing setting: {key} = {default_value}")
        
        conn.commit()
        
        # Summary
        print("\n" + "=" * 60)
        print("DATABASE REPAIR COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n✅ All fixes applied:")
        print("   • Admin password reset to: admin123")
        print(f"   • Fixed {fixed_count} time format issues")
        print("   • Verified all required settings")
        print("\n🎉 Your app should now work!")
        print("\nLogin credentials:")
        print("   Username: admin")
        print("   Password: admin123")
        print("\n⚠️  IMPORTANT: Delete this script after running!")
        print("=" * 60)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = repair_database()
    exit(0 if success else 1)
