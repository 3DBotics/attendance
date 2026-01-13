import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, date, timedelta
import pytz
from werkzeug.security import generate_password_hash, check_password_hash

MANILA_TZ = pytz.timezone('Asia/Manila')

def get_manila_now():
    """Get current datetime in Asia/Manila timezone"""
    return datetime.now(MANILA_TZ)

def get_db():
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Please ensure your Replit PostgreSQL database is configured. "
            "In the Deployments pane, add DATABASE_URL to your production secrets."
        )
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "could not translate host name" in error_msg:
            raise RuntimeError(
                f"Database connection failed: {error_msg}. "
                "The DATABASE_URL may be misconfigured for production. "
                "Please check your deployment secrets in the Deployments pane."
            )
        raise

def get_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)

def init_db():
    conn = get_db()
    cursor = get_cursor(conn)
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS branches (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            address TEXT,
            gps_latitude REAL,
            gps_longitude REAL,
            gps_radius_meters INTEGER DEFAULT 100,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id SERIAL PRIMARY KEY,
            employee_id TEXT NOT NULL UNIQUE,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            branch_id INTEGER,
            daily_rate REAL NOT NULL DEFAULT 0,
            start_time TEXT DEFAULT '08:00',
            end_time TEXT DEFAULT '17:00',
            pin_hash TEXT NOT NULL,
            photo_path TEXT,
            is_active INTEGER DEFAULT 1,
            is_resigned INTEGER DEFAULT 0,
            resigned_date DATE,
            status TEXT DEFAULT 'active',
            status_reason TEXT,
            status_date DATE,
            id_photo TEXT,
            cv_file TEXT,
            date_of_birth DATE,
            gender TEXT,
            civil_status TEXT,
            address TEXT,
            phone TEXT,
            email TEXT,
            sss_number TEXT,
            philhealth_number TEXT,
            pagibig_number TEXT,
            tin_number TEXT,
            emergency_contact_name TEXT,
            emergency_contact_phone TEXT,
            emergency_contact_relationship TEXT,
            reference_name TEXT,
            reference_phone TEXT,
            reference_company TEXT,
            date_hired DATE,
            position TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (branch_id) REFERENCES branches(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            employee_id INTEGER NOT NULL,
            date DATE NOT NULL,
            time_in TIMESTAMP,
            time_out TIMESTAMP,
            time_in_photo TEXT,
            time_out_photo TEXT,
            time_in_purpose TEXT DEFAULT 'clock_in',
            time_out_purpose TEXT,
            is_holiday INTEGER DEFAULT 0,
            holiday_type TEXT,
            is_overtime_approved INTEGER DEFAULT 0,
            overtime_hours REAL DEFAULT 0,
            tardiness_minutes INTEGER DEFAULT 0,
            undertime_minutes INTEGER DEFAULT 0,
            early_start_approved INTEGER DEFAULT 0,
            early_start_minutes INTEGER DEFAULT 0,
            official_overtime_approved INTEGER DEFAULT 0,
            official_overtime_minutes INTEGER DEFAULT 0,
            requires_admin_review INTEGER DEFAULT 0,
            admin_review_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS requires_admin_review INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE attendance ADD COLUMN IF NOT EXISTS admin_review_reason TEXT")
    except:
        pass
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payroll_periods (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            is_locked INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS statutory_deductions (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            is_percentage INTEGER DEFAULT 0,
            employee_rate REAL DEFAULT 0,
            employer_rate REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payroll_records (
            id SERIAL PRIMARY KEY,
            payroll_period_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            locked_daily_rate REAL NOT NULL,
            days_worked REAL DEFAULT 0,
            regular_pay REAL DEFAULT 0,
            overtime_pay REAL DEFAULT 0,
            holiday_pay REAL DEFAULT 0,
            tardiness_deduction REAL DEFAULT 0,
            undertime_deduction REAL DEFAULT 0,
            gross_pay REAL DEFAULT 0,
            total_deductions REAL DEFAULT 0,
            net_pay REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (payroll_period_id) REFERENCES payroll_periods(id),
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payroll_deduction_items (
            id SERIAL PRIMARY KEY,
            payroll_record_id INTEGER NOT NULL,
            deduction_id INTEGER NOT NULL,
            deduction_name TEXT NOT NULL,
            employee_amount REAL DEFAULT 0,
            employer_amount REAL DEFAULT 0,
            FOREIGN KEY (payroll_record_id) REFERENCES payroll_records(id),
            FOREIGN KEY (deduction_id) REFERENCES statutory_deductions(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS holidays (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL UNIQUE,
            name TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('regular', 'special'))
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id SERIAL PRIMARY KEY,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'sub_admin',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id SERIAL PRIMARY KEY,
            admin_id INTEGER,
            admin_name TEXT,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id INTEGER,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admins(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_auth_codes (
            id SERIAL PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            code_type TEXT NOT NULL CHECK(code_type IN ('early_start', 'overtime')),
            description TEXT,
            is_active INTEGER DEFAULT 1,
            uses_remaining INTEGER DEFAULT -1,
            valid_until DATE,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES admins(id)
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) as cnt FROM admins")
    if cursor.fetchone()['cnt'] == 0:
        from werkzeug.security import generate_password_hash
        cursor.execute("INSERT INTO admins (username, password_hash, full_name, role) VALUES (%s, %s, %s, %s)", 
                      ('admin', generate_password_hash('admin123'), 'Master Administrator', 'master_admin'))
    
    cursor.execute("SELECT COUNT(*) as cnt FROM settings WHERE key = 'grace_period'")
    if cursor.fetchone()['cnt'] == 0:
        cursor.execute("INSERT INTO settings (key, value) VALUES (%s, %s)", ('grace_period', '10'))
        cursor.execute("INSERT INTO settings (key, value) VALUES (%s, %s)", ('work_start_time', '08:00'))
        cursor.execute("INSERT INTO settings (key, value) VALUES (%s, %s)", ('work_end_time', '17:00'))
        cursor.execute("INSERT INTO settings (key, value) VALUES (%s, %s)", ('work_hours', '8'))
    
    cursor.execute("SELECT COUNT(*) as cnt FROM branches")
    if cursor.fetchone()['cnt'] == 0:
        cursor.execute("INSERT INTO branches (name, address) VALUES (%s, %s)", ('Main Branch', 'Default Address'))
    
    cursor.execute("SELECT COUNT(*) as cnt FROM statutory_deductions")
    if cursor.fetchone()['cnt'] == 0:
        cursor.execute("INSERT INTO statutory_deductions (name, is_percentage, employee_rate, employer_rate) VALUES (%s, %s, %s, %s)", ('SSS', 1, 4.5, 9.5))
        cursor.execute("INSERT INTO statutory_deductions (name, is_percentage, employee_rate, employer_rate) VALUES (%s, %s, %s, %s)", ('PhilHealth', 1, 2.5, 2.5))
        cursor.execute("INSERT INTO statutory_deductions (name, is_percentage, employee_rate, employer_rate) VALUES (%s, %s, %s, %s)", ('Pag-IBIG', 0, 100, 100))
    
    conn.commit()
    conn.close()

class Employee:
    @staticmethod
    def create(employee_id, first_name, last_name, branch_id, daily_rate, pin, start_time='08:00', end_time='17:00', **kwargs):
        conn = get_db()
        cursor = get_cursor(conn)
        pin_hash = generate_password_hash(pin)
        try:
            cursor.execute('''
                INSERT INTO employees (
                    employee_id, first_name, last_name, branch_id, daily_rate, pin_hash, 
                    start_time, end_time, status, id_photo, cv_file, date_of_birth, gender,
                    civil_status, address, phone, email, sss_number, philhealth_number,
                    pagibig_number, tin_number, emergency_contact_name, emergency_contact_phone,
                    emergency_contact_relationship, reference_name, reference_phone, 
                    reference_company, date_hired, position
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (
                employee_id, first_name, last_name, branch_id, daily_rate, pin_hash, 
                start_time, end_time, 'active',
                kwargs.get('id_photo'), kwargs.get('cv_file'), kwargs.get('date_of_birth'),
                kwargs.get('gender'), kwargs.get('civil_status'), kwargs.get('address'),
                kwargs.get('phone'), kwargs.get('email'), kwargs.get('sss_number'),
                kwargs.get('philhealth_number'), kwargs.get('pagibig_number'), kwargs.get('tin_number'),
                kwargs.get('emergency_contact_name'), kwargs.get('emergency_contact_phone'),
                kwargs.get('emergency_contact_relationship'), kwargs.get('reference_name'),
                kwargs.get('reference_phone'), kwargs.get('reference_company'),
                kwargs.get('date_hired'), kwargs.get('position')
            ))
            result = cursor.fetchone()
            conn.commit()
            conn.close()
            return result['id']
        except psycopg2.IntegrityError:
            conn.rollback()
            conn.close()
            return None
    
    @staticmethod
    def get_all(include_resigned=False):
        conn = get_db()
        cursor = get_cursor(conn)
        if include_resigned:
            cursor.execute('''
                SELECT e.*, b.name as branch_name 
                FROM employees e 
                LEFT JOIN branches b ON e.branch_id = b.id
                ORDER BY e.last_name, e.first_name
            ''')
        else:
            cursor.execute('''
                SELECT e.*, b.name as branch_name 
                FROM employees e 
                LEFT JOIN branches b ON e.branch_id = b.id
                WHERE e.is_resigned = 0
                ORDER BY e.last_name, e.first_name
            ''')
        employees = cursor.fetchall()
        conn.close()
        return employees
    
    @staticmethod
    def get_by_id(emp_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM employees WHERE id = %s', (emp_id,))
        employee = cursor.fetchone()
        conn.close()
        return employee
    
    @staticmethod
    def get_active():
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            SELECT e.*, b.name as branch_name 
            FROM employees e 
            LEFT JOIN branches b ON e.branch_id = b.id
            WHERE e.is_active = 1 AND e.is_resigned = 0
            ORDER BY e.last_name, e.first_name
        ''')
        employees = cursor.fetchall()
        conn.close()
        return employees
    
    @staticmethod
    def update(emp_id, employee_id, first_name, last_name, branch_id, daily_rate, pin=None, start_time=None, end_time=None, **kwargs):
        conn = get_db()
        cursor = get_cursor(conn)
        
        fields = [
            'employee_id', 'first_name', 'last_name', 'branch_id', 'daily_rate',
            'start_time', 'end_time', 'date_of_birth', 'gender', 'civil_status',
            'address', 'phone', 'email', 'sss_number', 'philhealth_number',
            'pagibig_number', 'tin_number', 'emergency_contact_name', 'emergency_contact_phone',
            'emergency_contact_relationship', 'reference_name', 'reference_phone',
            'reference_company', 'date_hired', 'position'
        ]
        
        values = [
            employee_id, first_name, last_name, branch_id, daily_rate,
            start_time, end_time, kwargs.get('date_of_birth'), kwargs.get('gender'),
            kwargs.get('civil_status'), kwargs.get('address'), kwargs.get('phone'),
            kwargs.get('email'), kwargs.get('sss_number'), kwargs.get('philhealth_number'),
            kwargs.get('pagibig_number'), kwargs.get('tin_number'), kwargs.get('emergency_contact_name'),
            kwargs.get('emergency_contact_phone'), kwargs.get('emergency_contact_relationship'),
            kwargs.get('reference_name'), kwargs.get('reference_phone'), kwargs.get('reference_company'),
            kwargs.get('date_hired'), kwargs.get('position')
        ]
        
        if kwargs.get('id_photo'):
            fields.append('id_photo')
            values.append(kwargs.get('id_photo'))
        
        if kwargs.get('cv_file'):
            fields.append('cv_file')
            values.append(kwargs.get('cv_file'))
        
        if pin:
            fields.append('pin_hash')
            values.append(generate_password_hash(pin))
        
        set_clause = ', '.join([f'{f} = %s' for f in fields])
        set_clause += ', updated_at = CURRENT_TIMESTAMP'
        values.append(emp_id)
        
        cursor.execute(f'UPDATE employees SET {set_clause} WHERE id = %s', values)
        conn.commit()
        conn.close()
    
    @staticmethod
    def change_status(emp_id, status, reason=None):
        conn = get_db()
        cursor = get_cursor(conn)
        is_active = 1 if status == 'active' else 0
        is_resigned = 1 if status in ['resigned', 'terminated', 'others'] else 0
        cursor.execute('''
            UPDATE employees 
            SET status = %s, status_reason = %s, status_date = %s, 
                is_active = %s, is_resigned = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (status, reason, date.today().isoformat(), is_active, is_resigned, emp_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def mark_resigned(emp_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            UPDATE employees 
            SET is_resigned = 1, is_active = 0, resigned_date = %s, status = 'resigned', updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        ''', (date.today().isoformat(), emp_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def verify_pin(emp_id, pin):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT pin_hash FROM employees WHERE id = %s', (emp_id,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return check_password_hash(result['pin_hash'], pin)
        return False

class Attendance:
    @staticmethod
    def time_in(employee_id, photo_path, purpose='clock_in', early_start_approved=False, early_start_code=None):
        conn = get_db()
        cursor = get_cursor(conn)
        manila_now = get_manila_now()
        today = manila_now.strftime('%Y-%m-%d')
        now = manila_now
        
        cursor.execute('SELECT * FROM attendance WHERE employee_id = %s AND date = %s AND time_out IS NULL ORDER BY id DESC LIMIT 1', (employee_id, today))
        open_record = cursor.fetchone()
        
        if open_record:
            conn.close()
            return None, "You have an open attendance record. Please clock out first."
        
        cursor.execute('SELECT start_time, end_time FROM employees WHERE id = %s', (employee_id,))
        emp_schedule = cursor.fetchone()
        work_start = emp_schedule['start_time'] if emp_schedule and emp_schedule['start_time'] else '08:00'
        
        tardiness_minutes = 0
        early_start_minutes = 0
        is_early_start_approved = 0
        
        if purpose == 'clock_in':
            cursor.execute("SELECT value FROM settings WHERE key = 'grace_period'")
            grace_period = int(cursor.fetchone()['value'])
            
            work_start_time = datetime.strptime(f"{today} {work_start}", "%Y-%m-%d %H:%M")
            work_start_time = MANILA_TZ.localize(work_start_time)
            
            diff_to_start = (now - work_start_time).total_seconds()
            if diff_to_start > 12 * 3600:
                work_start_time = work_start_time + timedelta(days=1)
            elif diff_to_start < -12 * 3600:
                work_start_time = work_start_time - timedelta(days=1)
            
            grace_end = work_start_time + timedelta(minutes=grace_period)
            
            cursor.execute('SELECT * FROM attendance WHERE employee_id = %s AND date = %s AND time_in_purpose = %s', (employee_id, today, 'clock_in'))
            first_clock_in = cursor.fetchone()
            if not first_clock_in and now > grace_end:
                diff = now - work_start_time
                tardiness_minutes = int(diff.total_seconds() / 60)
            
            if not first_clock_in and now < work_start_time:
                diff = work_start_time - now
                early_start_minutes = int(diff.total_seconds() / 60)
                if early_start_approved:
                    is_early_start_approved = 1
        
        cursor.execute("SELECT date FROM holidays WHERE date = %s", (today,))
        holiday = cursor.fetchone()
        is_holiday = 1 if holiday else 0
        holiday_type = None
        if holiday:
            cursor.execute("SELECT type FROM holidays WHERE date = %s", (today,))
            holiday_type = cursor.fetchone()['type']
        
        cursor.execute('''
            INSERT INTO attendance (employee_id, date, time_in, time_in_photo, time_in_purpose, tardiness_minutes, is_holiday, holiday_type, early_start_approved, early_start_minutes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        ''', (employee_id, today, now.isoformat(), photo_path, purpose, tardiness_minutes, is_holiday, holiday_type, is_early_start_approved, early_start_minutes))
        result = cursor.fetchone()
        conn.commit()
        record_id = result['id']
        conn.close()
        return record_id, f"{purpose.replace('_', ' ').title()} recorded successfully"
    
    @staticmethod
    def time_out(employee_id, photo_path, purpose='clock_out', official_overtime_approved=False, official_overtime_code=None):
        conn = get_db()
        cursor = get_cursor(conn)
        manila_now = get_manila_now()
        today = manila_now.strftime('%Y-%m-%d')
        now = manila_now
        
        cursor.execute('SELECT * FROM attendance WHERE employee_id = %s AND time_out IS NULL ORDER BY id DESC LIMIT 1', (employee_id,))
        open_record = cursor.fetchone()
        
        if not open_record:
            conn.close()
            return None, "No open attendance record. Please clock in first."
        
        record_date = str(open_record['date'])
        
        cursor.execute('SELECT end_time FROM employees WHERE id = %s', (employee_id,))
        emp_schedule = cursor.fetchone()
        work_end = emp_schedule['end_time'] if emp_schedule and emp_schedule['end_time'] else '17:00'
        
        undertime_minutes = 0
        official_overtime_minutes = 0
        is_official_overtime_approved = 0
        requires_admin_review = 0
        admin_review_reason = None
        
        clock_out_date = now.strftime('%Y-%m-%d')
        
        if purpose == 'clock_out' or purpose == 'unapproved_undertime_out':
            cursor.execute('SELECT start_time FROM employees WHERE id = %s', (employee_id,))
            start_schedule = cursor.fetchone()
            work_start = start_schedule['start_time'] if start_schedule and start_schedule['start_time'] else '08:00'
            
            work_end_time = datetime.strptime(f"{record_date} {work_end}", "%Y-%m-%d %H:%M")
            work_end_time = MANILA_TZ.localize(work_end_time)
            
            work_start_hour = int(work_start.split(':')[0])
            work_end_hour = int(work_end.split(':')[0])
            is_night_shift = work_end_hour < work_start_hour
            
            if is_night_shift:
                work_end_time = work_end_time + timedelta(days=1)
            
            if clock_out_date > record_date and not official_overtime_approved and not is_night_shift:
                requires_admin_review = 1
                admin_review_reason = "Next-day clock-out without overtime approval"
            elif now >= work_end_time:
                if official_overtime_approved:
                    diff = now - work_end_time
                    official_overtime_minutes = int(diff.total_seconds() / 60)
                    is_official_overtime_approved = 1
            else:
                diff = work_end_time - now
                undertime_minutes = int(diff.total_seconds() / 60)
        
        cursor.execute('''
            UPDATE attendance 
            SET time_out = %s, time_out_photo = %s, time_out_purpose = %s, undertime_minutes = %s, 
                official_overtime_approved = %s, official_overtime_minutes = %s,
                requires_admin_review = %s, admin_review_reason = %s
            WHERE id = %s
        ''', (now.isoformat(), photo_path, purpose, undertime_minutes, is_official_overtime_approved, 
              official_overtime_minutes, requires_admin_review, admin_review_reason, open_record['id']))
        conn.commit()
        conn.close()
        return open_record['id'], f"{purpose.replace('_', ' ').title()} recorded successfully"
    
    @staticmethod
    def get_today_status(employee_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM attendance WHERE employee_id = %s AND time_out IS NULL ORDER BY id DESC LIMIT 1', (employee_id,))
        open_record = cursor.fetchone()
        conn.close()
        return open_record
    
    @staticmethod
    def get_today_all_events(employee_id):
        conn = get_db()
        cursor = get_cursor(conn)
        today = get_manila_now().strftime('%Y-%m-%d')
        cursor.execute('SELECT * FROM attendance WHERE employee_id = %s AND date = %s ORDER BY time_in', (employee_id, today))
        records = cursor.fetchall()
        conn.close()
        return records
    
    @staticmethod
    def get_by_date_range(employee_id, start_date, end_date):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            SELECT * FROM attendance 
            WHERE employee_id = %s AND date BETWEEN %s AND %s
            ORDER BY date
        ''', (employee_id, start_date, end_date))
        records = cursor.fetchall()
        conn.close()
        return records
    
    @staticmethod
    def approve_overtime(attendance_id, hours):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            UPDATE attendance 
            SET is_overtime_approved = 1, overtime_hours = %s
            WHERE id = %s
        ''', (hours, attendance_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def delete(attendance_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM attendance WHERE id = %s', (attendance_id,))
        record = cursor.fetchone()
        if record:
            cursor.execute('DELETE FROM attendance WHERE id = %s', (attendance_id,))
            conn.commit()
        conn.close()
        return record
    
    @staticmethod
    def get_by_id(attendance_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            SELECT a.*, e.first_name, e.last_name, e.employee_id as emp_code
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            WHERE a.id = %s
        ''', (attendance_id,))
        record = cursor.fetchone()
        conn.close()
        return record

class AdminAuthCode:
    @staticmethod
    def create(code, code_type, description=None, uses_remaining=-1, valid_until=None, created_by=None):
        conn = get_db()
        cursor = get_cursor(conn)
        try:
            cursor.execute('''
                INSERT INTO admin_auth_codes (code, code_type, description, uses_remaining, valid_until, created_by)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (code, code_type, description, uses_remaining, valid_until, created_by))
            result = cursor.fetchone()
            conn.commit()
            conn.close()
            return result['id']
        except psycopg2.IntegrityError:
            conn.rollback()
            conn.close()
            return None
    
    @staticmethod
    def get_all():
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            SELECT ac.*, a.full_name as created_by_name
            FROM admin_auth_codes ac
            LEFT JOIN admins a ON ac.created_by = a.id
            ORDER BY ac.created_at DESC
        ''')
        codes = cursor.fetchall()
        conn.close()
        return codes
    
    @staticmethod
    def get_active_by_type(code_type):
        conn = get_db()
        cursor = get_cursor(conn)
        today = date.today().isoformat()
        cursor.execute('''
            SELECT * FROM admin_auth_codes 
            WHERE code_type = %s AND is_active = 1 
            AND (valid_until IS NULL OR valid_until >= %s)
            AND (uses_remaining = -1 OR uses_remaining > 0)
        ''', (code_type, today))
        codes = cursor.fetchall()
        conn.close()
        return codes
    
    @staticmethod
    def verify_code(code, code_type):
        conn = get_db()
        cursor = get_cursor(conn)
        today = date.today().isoformat()
        cursor.execute('''
            SELECT * FROM admin_auth_codes 
            WHERE code = %s AND code_type = %s AND is_active = 1 
            AND (valid_until IS NULL OR valid_until >= %s)
            AND (uses_remaining = -1 OR uses_remaining > 0)
        ''', (code, code_type, today))
        auth_code = cursor.fetchone()
        
        if auth_code:
            if auth_code['uses_remaining'] > 0:
                cursor.execute('UPDATE admin_auth_codes SET uses_remaining = uses_remaining - 1 WHERE id = %s', (auth_code['id'],))
                conn.commit()
            conn.close()
            return True
        conn.close()
        return False
    
    @staticmethod
    def update(code_id, code, description, is_active, uses_remaining, valid_until):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            UPDATE admin_auth_codes 
            SET code = %s, description = %s, is_active = %s, uses_remaining = %s, valid_until = %s
            WHERE id = %s
        ''', (code, description, is_active, uses_remaining, valid_until, code_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def delete(code_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('DELETE FROM admin_auth_codes WHERE id = %s', (code_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def generate_random_code(length=6):
        import random
        import string
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class StatutoryDeduction:
    @staticmethod
    def get_all():
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM statutory_deductions ORDER BY name')
        deductions = cursor.fetchall()
        conn.close()
        return deductions
    
    @staticmethod
    def get_active():
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM statutory_deductions WHERE is_active = 1 ORDER BY name')
        deductions = cursor.fetchall()
        conn.close()
        return deductions
    
    @staticmethod
    def create(name, is_percentage, employee_rate, employer_rate):
        conn = get_db()
        cursor = get_cursor(conn)
        try:
            cursor.execute('''
                INSERT INTO statutory_deductions (name, is_percentage, employee_rate, employer_rate)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (name, is_percentage, employee_rate, employer_rate))
            result = cursor.fetchone()
            conn.commit()
            conn.close()
            return result['id']
        except psycopg2.IntegrityError:
            conn.rollback()
            conn.close()
            return None
    
    @staticmethod
    def update(ded_id, name, is_percentage, employee_rate, employer_rate, is_active):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            UPDATE statutory_deductions 
            SET name = %s, is_percentage = %s, employee_rate = %s, employer_rate = %s, is_active = %s
            WHERE id = %s
        ''', (name, is_percentage, employee_rate, employer_rate, is_active, ded_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def delete(ded_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('DELETE FROM statutory_deductions WHERE id = %s', (ded_id,))
        conn.commit()
        conn.close()

class Holiday:
    @staticmethod
    def get_all():
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM holidays ORDER BY date DESC')
        holidays = cursor.fetchall()
        conn.close()
        return holidays
    
    @staticmethod
    def create(date_str, name, holiday_type):
        conn = get_db()
        cursor = get_cursor(conn)
        try:
            cursor.execute('''
                INSERT INTO holidays (date, name, type)
                VALUES (%s, %s, %s)
                RETURNING id
            ''', (date_str, name, holiday_type))
            result = cursor.fetchone()
            conn.commit()
            conn.close()
            return result['id']
        except psycopg2.IntegrityError:
            conn.rollback()
            conn.close()
            return None
    
    @staticmethod
    def delete(holiday_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('DELETE FROM holidays WHERE id = %s', (holiday_id,))
        conn.commit()
        conn.close()

class Branch:
    @staticmethod
    def get_all():
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM branches ORDER BY name')
        branches = cursor.fetchall()
        conn.close()
        return branches
    
    @staticmethod
    def get_by_id(branch_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM branches WHERE id = %s', (branch_id,))
        branch = cursor.fetchone()
        conn.close()
        return branch
    
    @staticmethod
    def get_by_name(name):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM branches WHERE name = %s', (name,))
        branch = cursor.fetchone()
        conn.close()
        return branch
    
    @staticmethod
    def create(name, address):
        conn = get_db()
        cursor = get_cursor(conn)
        try:
            cursor.execute('INSERT INTO branches (name, address) VALUES (%s, %s) RETURNING id', (name, address))
            result = cursor.fetchone()
            conn.commit()
            conn.close()
            return result['id']
        except psycopg2.IntegrityError:
            conn.rollback()
            conn.close()
            return None
    
    @staticmethod
    def update_gps(branch_id, latitude, longitude, radius_meters=100):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            UPDATE branches 
            SET gps_latitude = %s, gps_longitude = %s, gps_radius_meters = %s
            WHERE id = %s
        ''', (latitude, longitude, radius_meters, branch_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def validate_location(branch_name, lat, lng):
        import math
        branch = Branch.get_by_name(branch_name)
        if not branch or not branch['gps_latitude'] or not branch['gps_longitude']:
            return True, "No GPS configured for branch"
        
        branch_lat = branch['gps_latitude']
        branch_lng = branch['gps_longitude']
        radius = branch['gps_radius_meters'] or 100
        
        R = 6371000
        lat1 = math.radians(branch_lat)
        lat2 = math.radians(lat)
        delta_lat = math.radians(lat - branch_lat)
        delta_lng = math.radians(lng - branch_lng)
        
        a = math.sin(delta_lat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        if distance <= radius:
            return True, f"Within {int(distance)}m of branch"
        else:
            return False, f"Location is {int(distance)}m away from branch (max: {radius}m)"
    
    @staticmethod
    def delete(branch_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT COUNT(*) as cnt FROM employees WHERE branch_id = %s', (branch_id,))
        count = cursor.fetchone()['cnt']
        if count > 0:
            conn.close()
            return False, "Cannot delete branch with employees assigned"
        cursor.execute('DELETE FROM branches WHERE id = %s', (branch_id,))
        conn.commit()
        conn.close()
        return True, "Branch deleted successfully"

class Settings:
    @staticmethod
    def get(key):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT value FROM settings WHERE key = %s', (key,))
        result = cursor.fetchone()
        conn.close()
        return result['value'] if result else None
    
    @staticmethod
    def set(key, value):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT id FROM settings WHERE key = %s', (key,))
        if cursor.fetchone():
            cursor.execute('UPDATE settings SET value = %s WHERE key = %s', (value, key))
        else:
            cursor.execute('INSERT INTO settings (key, value) VALUES (%s, %s)', (key, value))
        conn.commit()
        conn.close()

class PayrollPeriod:
    @staticmethod
    def create(name, start_date, end_date):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            INSERT INTO payroll_periods (name, start_date, end_date)
            VALUES (%s, %s, %s)
            RETURNING id
        ''', (name, start_date, end_date))
        result = cursor.fetchone()
        conn.commit()
        period_id = result['id']
        conn.close()
        return period_id
    
    @staticmethod
    def get_all():
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM payroll_periods ORDER BY start_date DESC')
        periods = cursor.fetchall()
        conn.close()
        return periods
    
    @staticmethod
    def get_by_id(period_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM payroll_periods WHERE id = %s', (period_id,))
        period = cursor.fetchone()
        conn.close()
        return period
    
    @staticmethod
    def lock(period_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('UPDATE payroll_periods SET is_locked = 1 WHERE id = %s', (period_id,))
        conn.commit()
        conn.close()

class PayrollRecord:
    @staticmethod
    def generate_for_period(period_id):
        conn = get_db()
        cursor = get_cursor(conn)
        
        cursor.execute('SELECT * FROM payroll_periods WHERE id = %s', (period_id,))
        period = cursor.fetchone()
        if not period:
            conn.close()
            return None
        
        cursor.execute('DELETE FROM payroll_records WHERE payroll_period_id = %s', (period_id,))
        
        employees = Employee.get_all()
        
        cursor.execute("SELECT value FROM settings WHERE key = 'work_hours'")
        default_work_hours = float(cursor.fetchone()['value'])
        
        for emp in employees:
            cursor.execute('''
                SELECT * FROM attendance 
                WHERE employee_id = %s AND date BETWEEN %s AND %s
                ORDER BY date, time_in
            ''', (emp['id'], period['start_date'], period['end_date']))
            attendance_records = cursor.fetchall()
            
            daily_rate = emp['daily_rate']
            
            emp_start = emp['start_time'] if emp['start_time'] else '08:00'
            emp_end = emp['end_time'] if emp['end_time'] else '17:00'
            try:
                start_dt = datetime.strptime(emp_start, '%H:%M')
                end_dt = datetime.strptime(emp_end, '%H:%M')
                emp_work_hours = (end_dt - start_dt).total_seconds() / 3600
                if emp_work_hours <= 0:
                    emp_work_hours = default_work_hours
            except:
                emp_work_hours = default_work_hours
            
            hourly_rate = daily_rate / emp_work_hours
            minute_rate = hourly_rate / 60
            
            daily_data = {}
            emp_work_minutes = emp_work_hours * 60
            
            for att in attendance_records:
                if att['time_in'] and att['time_out']:
                    att_date = str(att['date'])
                    requires_review = att.get('requires_admin_review', 0)
                    
                    if att_date not in daily_data:
                        daily_data[att_date] = {
                            'tardiness': 0,
                            'undertime': 0,
                            'overtime_minutes': 0,
                            'early_start_minutes': 0,
                            'is_holiday': False,
                            'holiday_type': None,
                            'has_clock_in': False,
                            'has_clock_out': False,
                            'actual_work_minutes': 0,
                            'requires_admin_review': False
                        }
                    
                    if requires_review:
                        daily_data[att_date]['requires_admin_review'] = True
                    
                    in_purpose = att['time_in_purpose'] or 'clock_in'
                    out_purpose = att['time_out_purpose'] or 'clock_out'
                    
                    try:
                        time_in_str = str(att['time_in'])
                        time_out_str = str(att['time_out'])
                        
                        if 'T' in time_in_str:
                            time_in = datetime.fromisoformat(time_in_str)
                        else:
                            time_in = datetime.strptime(time_in_str, '%Y-%m-%d %H:%M:%S')
                        
                        if 'T' in time_out_str:
                            time_out = datetime.fromisoformat(time_out_str)
                        else:
                            time_out = datetime.strptime(time_out_str, '%Y-%m-%d %H:%M:%S')
                        
                        if time_out < time_in:
                            segment_minutes = ((24 * 60) - (time_in.hour * 60 + time_in.minute)) + (time_out.hour * 60 + time_out.minute)
                        else:
                            segment_minutes = (time_out - time_in).total_seconds() / 60
                        daily_data[att_date]['actual_work_minutes'] += segment_minutes
                    except Exception as e:
                        pass
                    
                    if in_purpose == 'clock_in' or in_purpose == 'early_start':
                        daily_data[att_date]['tardiness'] = att['tardiness_minutes'] or 0
                        daily_data[att_date]['has_clock_in'] = True
                        if att['early_start_approved']:
                            daily_data[att_date]['early_start_minutes'] += att['early_start_minutes'] or 0
                    
                    if out_purpose == 'clock_out' or out_purpose == 'unapproved_undertime_out' or out_purpose == 'official_overtime':
                        daily_data[att_date]['undertime'] = att['undertime_minutes'] or 0
                        daily_data[att_date]['has_clock_out'] = True
                        if att['official_overtime_approved']:
                            daily_data[att_date]['overtime_minutes'] += att['official_overtime_minutes'] or 0
                    
                    if att['is_holiday']:
                        daily_data[att_date]['is_holiday'] = True
                        daily_data[att_date]['holiday_type'] = att['holiday_type']
            
            total_actual_hours = 0
            total_tardiness = 0
            total_undertime = 0
            total_overtime_minutes = 0
            total_early_start_minutes = 0
            holiday_pay = 0
            days_with_attendance = 0
            
            for att_date, data in daily_data.items():
                if data['has_clock_in']:
                    days_with_attendance += 1
                    actual_minutes = data['actual_work_minutes']
                    
                    actual_hours_today = min(actual_minutes, emp_work_minutes) / 60
                    total_actual_hours += actual_hours_today
                    
                    if not data.get('requires_admin_review', False):
                        if actual_minutes < emp_work_minutes:
                            missing_minutes = emp_work_minutes - actual_minutes
                            total_undertime += missing_minutes
                        
                        total_tardiness += data['tardiness']
                    
                    total_overtime_minutes += data['overtime_minutes']
                    total_early_start_minutes += data['early_start_minutes']
                    
                    if data['is_holiday']:
                        if data['holiday_type'] == 'regular':
                            holiday_pay += daily_rate * 1.0
                        elif data['holiday_type'] == 'special':
                            holiday_pay += daily_rate * 0.3
            
            days_worked = round(total_actual_hours / emp_work_hours, 2) if emp_work_hours > 0 else 0
            regular_pay = total_actual_hours * hourly_rate
            overtime_hours = total_overtime_minutes / 60
            overtime_pay = overtime_hours * hourly_rate * 1.25
            early_start_pay = (total_early_start_minutes / 60) * hourly_rate
            tardiness_deduction = total_tardiness * minute_rate
            undertime_deduction = total_undertime * minute_rate
            
            gross_pay = regular_pay + overtime_pay + early_start_pay + holiday_pay
            
            from pdf_payslip import calculate_sss_contribution, calculate_philhealth_contribution, calculate_pagibig_contribution
            
            monthly_basic_salary = daily_rate * 21.75
            
            sss_ee_monthly, sss_er_monthly = calculate_sss_contribution(monthly_basic_salary)
            philhealth_ee_monthly, philhealth_er_monthly = calculate_philhealth_contribution(monthly_basic_salary)
            pagibig_ee_monthly, pagibig_er_monthly = calculate_pagibig_contribution(monthly_basic_salary)
            
            period_start = datetime.strptime(str(period['start_date']), '%Y-%m-%d')
            period_end = datetime.strptime(str(period['end_date']), '%Y-%m-%d')
            period_days = (period_end - period_start).days + 1
            
            if period_days >= 28:
                proration_factor = 1.0
            elif period_days >= 14:
                proration_factor = 0.5
            else:
                proration_factor = 0.0
            
            sss_ee = round(sss_ee_monthly * proration_factor, 2)
            sss_er = round(sss_er_monthly * proration_factor, 2)
            philhealth_ee = round(philhealth_ee_monthly * proration_factor, 2)
            philhealth_er = round(philhealth_er_monthly * proration_factor, 2)
            pagibig_ee = round(pagibig_ee_monthly * proration_factor, 2)
            pagibig_er = round(pagibig_er_monthly * proration_factor, 2)
            
            total_deductions = sss_ee + philhealth_ee + pagibig_ee
            
            cursor.execute('''
                INSERT INTO payroll_records 
                (payroll_period_id, employee_id, locked_daily_rate, days_worked, regular_pay, 
                 overtime_pay, holiday_pay, tardiness_deduction, undertime_deduction, gross_pay, 
                 total_deductions, net_pay)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (period_id, emp['id'], daily_rate, days_worked, regular_pay, overtime_pay, 
                  holiday_pay, tardiness_deduction, undertime_deduction, gross_pay, 0, gross_pay))
            payroll_record_id = cursor.fetchone()['id']
            
            cursor.execute('''
                INSERT INTO payroll_deduction_items 
                (payroll_record_id, deduction_id, deduction_name, employee_amount, employer_amount)
                VALUES (%s, %s, %s, %s, %s)
            ''', (payroll_record_id, 1, 'SSS', sss_ee, sss_er))
            
            cursor.execute('''
                INSERT INTO payroll_deduction_items 
                (payroll_record_id, deduction_id, deduction_name, employee_amount, employer_amount)
                VALUES (%s, %s, %s, %s, %s)
            ''', (payroll_record_id, 2, 'PhilHealth', philhealth_ee, philhealth_er))
            
            cursor.execute('''
                INSERT INTO payroll_deduction_items 
                (payroll_record_id, deduction_id, deduction_name, employee_amount, employer_amount)
                VALUES (%s, %s, %s, %s, %s)
            ''', (payroll_record_id, 3, 'Pag-IBIG', pagibig_ee, pagibig_er))
            
            net_pay = gross_pay - total_deductions
            cursor.execute('''
                UPDATE payroll_records SET total_deductions = %s, net_pay = %s WHERE id = %s
            ''', (total_deductions, net_pay, payroll_record_id))
        
        conn.commit()
        conn.close()
        return True
    
    @staticmethod
    def get_by_period(period_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            SELECT pr.*, e.first_name, e.last_name, e.employee_id as emp_code
            FROM payroll_records pr
            JOIN employees e ON pr.employee_id = e.id
            WHERE pr.payroll_period_id = %s
            ORDER BY e.last_name, e.first_name
        ''', (period_id,))
        records = cursor.fetchall()
        conn.close()
        return records
    
    @staticmethod
    def get_deduction_items(record_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            SELECT * FROM payroll_deduction_items WHERE payroll_record_id = %s
        ''', (record_id,))
        items = cursor.fetchall()
        conn.close()
        return items
    
    @staticmethod
    def get_13th_month(year):
        conn = get_db()
        cursor = get_cursor(conn)
        
        employees = Employee.get_all(include_resigned=True)
        results = []
        
        for emp in employees:
            cursor.execute('''
                SELECT SUM(regular_pay) as total_basic
                FROM payroll_records pr
                JOIN payroll_periods pp ON pr.payroll_period_id = pp.id
                WHERE pr.employee_id = %s 
                AND EXTRACT(YEAR FROM pp.start_date) = %s
            ''', (emp['id'], int(year)))
            
            result = cursor.fetchone()
            total_basic = result['total_basic'] if result['total_basic'] else 0
            thirteenth_month = total_basic / 12
            
            results.append({
                'employee_id': emp['employee_id'],
                'name': f"{emp['first_name']} {emp['last_name']}",
                'total_basic': total_basic,
                'thirteenth_month': thirteenth_month
            })
        
        conn.close()
        return results

class Admin:
    @staticmethod
    def get_by_username(username):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM admins WHERE username = %s AND is_active = 1', (username,))
        admin = cursor.fetchone()
        conn.close()
        return admin
    
    @staticmethod
    def get_by_id(admin_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT * FROM admins WHERE id = %s', (admin_id,))
        admin = cursor.fetchone()
        conn.close()
        return admin
    
    @staticmethod
    def verify_password(username, password):
        admin = Admin.get_by_username(username)
        if admin and check_password_hash(admin['password_hash'], password):
            return admin
        return None
    
    @staticmethod
    def get_all():
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('SELECT id, username, full_name, role, is_active, created_at FROM admins ORDER BY role, username')
        admins = cursor.fetchall()
        conn.close()
        return admins
    
    @staticmethod
    def create(username, password, full_name, role='sub_admin'):
        conn = get_db()
        cursor = get_cursor(conn)
        try:
            password_hash = generate_password_hash(password)
            cursor.execute('''
                INSERT INTO admins (username, password_hash, full_name, role)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            ''', (username, password_hash, full_name, role))
            result = cursor.fetchone()
            conn.commit()
            conn.close()
            return result['id']
        except psycopg2.IntegrityError:
            conn.rollback()
            conn.close()
            return None
    
    @staticmethod
    def update(admin_id, full_name, role, is_active):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            UPDATE admins SET full_name = %s, role = %s, is_active = %s WHERE id = %s
        ''', (full_name, role, is_active, admin_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def update_password(admin_id, new_password):
        conn = get_db()
        cursor = get_cursor(conn)
        password_hash = generate_password_hash(new_password)
        cursor.execute('UPDATE admins SET password_hash = %s WHERE id = %s', (password_hash, admin_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def delete(admin_id):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute("DELETE FROM admins WHERE id = %s AND role != 'master_admin'", (admin_id,))
        conn.commit()
        conn.close()
    
    @staticmethod
    def is_master_admin(admin_id):
        admin = Admin.get_by_id(admin_id)
        return admin and admin['role'] == 'master_admin'


class DatabaseManager:
    @staticmethod
    def reset_all_data():
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('DELETE FROM payroll_deduction_items')
        cursor.execute('DELETE FROM payroll_records')
        cursor.execute('DELETE FROM payroll_periods')
        cursor.execute('DELETE FROM attendance')
        cursor.execute('DELETE FROM employees')
        cursor.execute('DELETE FROM branches')
        cursor.execute('DELETE FROM activity_logs')
        conn.commit()
        conn.close()
        return True


class ActivityLog:
    @staticmethod
    def log(admin_id, admin_name, action, target_type=None, target_id=None, details=None, ip_address=None):
        conn = get_db()
        cursor = get_cursor(conn)
        manila_now = get_manila_now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO activity_logs (admin_id, admin_name, action, target_type, target_id, details, ip_address, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (admin_id, admin_name, action, target_type, target_id, details, ip_address, manila_now))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_all(limit=100):
        conn = get_db()
        cursor = get_cursor(conn)
        cursor.execute('''
            SELECT * FROM activity_logs 
            ORDER BY created_at DESC 
            LIMIT %s
        ''', (limit,))
        logs = cursor.fetchall()
        conn.close()
        return logs
