#!/usr/bin/env python3
"""
Fix Existing Attendance Data
Converts UTC timestamps to Manila timezone and fixes photo paths
Run this ONCE after deployment to fix existing records
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import pytz

MANILA_TZ = pytz.timezone('Asia/Manila')

def fix_existing_data():
    print("=" * 60)
    print("FIX EXISTING ATTENDANCE DATA")
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
        
        # Fix 1: Convert UTC timestamps to Manila timezone
        print("\n2. Fixing timezone for time_in timestamps...")
        cursor.execute("SELECT id, time_in FROM attendance WHERE time_in IS NOT NULL")
        records = cursor.fetchall()
        
        fixed_time_in_count = 0
        for record in records:
            time_in_str = str(record['time_in'])
            try:
                # Parse the timestamp
                if 'T' in time_in_str:
                    # ISO format with timezone
                    dt = datetime.fromisoformat(time_in_str)
                else:
                    # Space-separated format, assume UTC
                    dt = datetime.strptime(time_in_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                    dt = pytz.UTC.localize(dt)
                
                # Convert to Manila time
                manila_dt = dt.astimezone(MANILA_TZ)
                
                # Update the record
                cursor.execute(
                    "UPDATE attendance SET time_in = %s WHERE id = %s",
                    (manila_dt.isoformat(), record['id'])
                )
                fixed_time_in_count += 1
            except Exception as e:
                print(f"   ⚠️  Error processing record {record['id']}: {e}")
        
        conn.commit()
        print(f"   ✅ Fixed {fixed_time_in_count} time_in timestamps")
        
        # Fix 2: Convert UTC timestamps to Manila timezone for time_out
        print("\n3. Fixing timezone for time_out timestamps...")
        cursor.execute("SELECT id, time_out FROM attendance WHERE time_out IS NOT NULL")
        records = cursor.fetchall()
        
        fixed_time_out_count = 0
        for record in records:
            time_out_str = str(record['time_out'])
            try:
                # Parse the timestamp
                if 'T' in time_out_str:
                    # ISO format with timezone
                    dt = datetime.fromisoformat(time_out_str)
                else:
                    # Space-separated format, assume UTC
                    dt = datetime.strptime(time_out_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                    dt = pytz.UTC.localize(dt)
                
                # Convert to Manila time
                manila_dt = dt.astimezone(MANILA_TZ)
                
                # Update the record
                cursor.execute(
                    "UPDATE attendance SET time_out = %s WHERE id = %s",
                    (manila_dt.isoformat(), record['id'])
                )
                fixed_time_out_count += 1
            except Exception as e:
                print(f"   ⚠️  Error processing record {record['id']}: {e}")
        
        conn.commit()
        print(f"   ✅ Fixed {fixed_time_out_count} time_out timestamps")
        
        # Fix 3: Fix photo paths
        print("\n4. Fixing photo paths...")
        cursor.execute("SELECT id, time_in_photo, time_out_photo FROM attendance WHERE time_in_photo IS NOT NULL OR time_out_photo IS NOT NULL")
        records = cursor.fetchall()
        
        fixed_photo_count = 0
        for record in records:
            time_in_photo = record['time_in_photo']
            time_out_photo = record['time_out_photo']
            
            new_time_in_photo = None
            new_time_out_photo = None
            
            if time_in_photo:
                # Remove absolute path prefix
                if time_in_photo.startswith('/home/ubuntu/attendance/'):
                    new_time_in_photo = time_in_photo.replace('/home/ubuntu/attendance/', '')
                elif not time_in_photo.startswith('static/'):
                    # If it doesn't start with static/, assume it's just the filename
                    new_time_in_photo = f"static/uploads/{time_in_photo.split('/')[-1]}"
                else:
                    new_time_in_photo = time_in_photo
            
            if time_out_photo:
                # Remove absolute path prefix
                if time_out_photo.startswith('/home/ubuntu/attendance/'):
                    new_time_out_photo = time_out_photo.replace('/home/ubuntu/attendance/', '')
                elif not time_out_photo.startswith('static/'):
                    # If it doesn't start with static/, assume it's just the filename
                    new_time_out_photo = f"static/uploads/{time_out_photo.split('/')[-1]}"
                else:
                    new_time_out_photo = time_out_photo
            
            if new_time_in_photo or new_time_out_photo:
                cursor.execute(
                    "UPDATE attendance SET time_in_photo = %s, time_out_photo = %s WHERE id = %s",
                    (new_time_in_photo or time_in_photo, new_time_out_photo or time_out_photo, record['id'])
                )
                fixed_photo_count += 1
        
        conn.commit()
        print(f"   ✅ Fixed {fixed_photo_count} photo paths")
        
        # Summary
        print("\n" + "=" * 60)
        print("DATA FIX COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n✅ All fixes applied:")
        print(f"   • Fixed {fixed_time_in_count} time_in timestamps")
        print(f"   • Fixed {fixed_time_out_count} time_out timestamps")
        print(f"   • Fixed {fixed_photo_count} photo paths")
        print("\n🎉 Your attendance records should now display correctly!")
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
    success = fix_existing_data()
    exit(0 if success else 1)
