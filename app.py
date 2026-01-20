import os
import base64
import requests as http_requests
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, send_file
from models import (
    init_db, Employee, Attendance, StatutoryDeduction, 
    Holiday, Branch, Settings, PayrollPeriod, PayrollRecord, get_db, get_cursor, ActivityLog,
    Admin, DatabaseManager, get_manila_now, AdminAuthCode
)
from pdf_payslip import generate_payslip_pdf

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', 'dev-secret-key')

UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

init_db()

# Database already fixed via Supabase SQL Editor

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def master_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('admin_login'))
        if session.get('admin_role') != 'master_admin':
            flash('Access denied. Master Admin privileges required.', 'error')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def staff_access_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please login to access this page', 'error')
            return redirect(url_for('admin_login'))
        if session.get('admin_role') not in ['master_admin', 'staff']:
            flash('Access denied. Staff or Master Admin privileges required.', 'error')
            return redirect(url_for('admin_dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_admin():
    if 'admin_id' in session:
        return Admin.get_by_id(session['admin_id'])
    return None

def can_edit_delete():
    return session.get('admin_role') == 'master_admin'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        admin = Admin.verify_password(username, password)
        if admin:
            session['admin_id'] = admin['id']
            session['admin_name'] = admin['full_name']
            session['admin_role'] = admin['role']
            session['admin_username'] = admin['username']
            ActivityLog.log(admin['id'], admin['full_name'], 'LOGIN', details='Admin logged in', ip_address=request.remote_addr)
            flash(f'Welcome back, {admin["full_name"]}!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'error')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    if 'admin_id' in session:
        ActivityLog.log(session['admin_id'], session.get('admin_name'), 'LOGOUT', details='Admin logged out', ip_address=request.remote_addr)
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    employees = Employee.get_all(include_resigned=True)
    branches = Branch.get_all()
    return render_template('admin/dashboard.html', employees=employees, branches=branches, can_edit_delete=can_edit_delete())

@app.route('/admin/employees')
@login_required
def admin_employees():
    employees = Employee.get_all(include_resigned=True)
    branches = Branch.get_all()
    return render_template('admin/employees.html', employees=employees, branches=branches, can_edit_delete=can_edit_delete())

def validate_and_save_id_photo(photo_data, employee_id):
    import base64
    import re
    from PIL import Image
    from io import BytesIO
    
    if not photo_data or not photo_data.startswith('data:image/'):
        return None
    
    match = re.match(r'data:image/(jpeg|png|webp);base64,(.+)', photo_data)
    if not match:
        return None
    
    try:
        img_bytes = base64.b64decode(match.group(2))
        if len(img_bytes) > 5 * 1024 * 1024:
            return None
        
        safe_emp_id = re.sub(r'[^a-zA-Z0-9_-]', '', employee_id)
        import secrets
        filename = f"id_{safe_emp_id}_{secrets.token_hex(8)}.jpg"
        photo_path = f"static/uploads/id_photos/{filename}"
        os.makedirs('static/uploads/id_photos', exist_ok=True)
        
        img = Image.open(BytesIO(img_bytes))
        img = img.convert('RGB')
        max_size = (400, 400)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        # Return base64 string instead of path to ensure persistence on Railway
        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=70)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/jpeg;base64,{img_str}"
    except Exception:
        return None

def validate_and_save_cv(cv_file, employee_id):
    import re
    if not cv_file or not cv_file.filename:
        return None
    
    if not cv_file.filename.lower().endswith('.pdf'):
        return None
    
    cv_file.seek(0, 2)
    size = cv_file.tell()
    cv_file.seek(0)
    if size > 10 * 1024 * 1024:
        return None
    
    header = cv_file.read(5)
    cv_file.seek(0)
    if header != b'%PDF-':
        return None
    
    safe_emp_id = re.sub(r'[^a-zA-Z0-9_-]', '', employee_id)
    import secrets
    filename = f"cv_{safe_emp_id}_{secrets.token_hex(8)}.pdf"
    cv_path = f"static/uploads/cv_files/{filename}"
    os.makedirs('static/uploads/cv_files', exist_ok=True)
    cv_file.save(cv_path)
    return cv_path

@app.route('/admin/employees/add', methods=['POST'])
@staff_access_required
def add_employee():
    data = request.form
    start_time = data.get('start_time', '08:00')
    end_time = data.get('end_time', '17:00')
    
    id_photo_path = validate_and_save_id_photo(data.get('id_photo'), data['employee_id'])
    cv_file_path = validate_and_save_cv(request.files.get('cv_file'), data['employee_id'])
    
    result = Employee.create(
        data['employee_id'],
        data['first_name'],
        data['last_name'],
        data['branch_id'],
        float(data['daily_rate']),
        data['pin'],
        start_time,
        end_time,
        id_photo=id_photo_path,
        cv_file=cv_file_path,
        date_of_birth=data.get('date_of_birth') or None,
        gender=data.get('gender') or None,
        civil_status=data.get('civil_status') or None,
        address=data.get('address') or None,
        phone=data.get('phone') or None,
        email=data.get('email') or None,
        sss_number=data.get('sss_number') or None,
        philhealth_number=data.get('philhealth_number') or None,
        pagibig_number=data.get('pagibig_number') or None,
        tin_number=data.get('tin_number') or None,
        emergency_contact_name=data.get('emergency_contact_name') or None,
        emergency_contact_phone=data.get('emergency_contact_phone') or None,
        emergency_contact_relationship=data.get('emergency_contact_relationship') or None,
        reference_name=data.get('reference_name') or None,
        reference_phone=data.get('reference_phone') or None,
        reference_company=data.get('reference_company') or None,
        date_hired=data.get('date_hired') or None,
        position=data.get('position') or None
    )
    if result:
        ActivityLog.log(session['admin_id'], session['admin_name'], 'CREATE', 'employee', result, f"Added employee {data['first_name']} {data['last_name']}", request.remote_addr)
        flash('Employee added successfully', 'success')
    else:
        flash('Employee ID already exists', 'error')
    return redirect(url_for('admin_employees'))

@app.route('/admin/employees/<int:emp_id>/edit', methods=['POST'])
@staff_access_required
def edit_employee(emp_id):
    data = request.form
    pin = data.get('pin') if data.get('pin') else None
    start_time = data.get('start_time', '08:00')
    end_time = data.get('end_time', '17:00')
    
    id_photo_path = validate_and_save_id_photo(data.get('id_photo'), data['employee_id'])
    cv_file_path = validate_and_save_cv(request.files.get('cv_file'), data['employee_id'])
    
    Employee.update(
        emp_id,
        data['employee_id'],
        data['first_name'],
        data['last_name'],
        data['branch_id'],
        float(data['daily_rate']),
        pin,
        start_time,
        end_time,
        id_photo=id_photo_path,
        cv_file=cv_file_path,
        date_of_birth=data.get('date_of_birth') or None,
        gender=data.get('gender') or None,
        civil_status=data.get('civil_status') or None,
        address=data.get('address') or None,
        phone=data.get('phone') or None,
        email=data.get('email') or None,
        sss_number=data.get('sss_number') or None,
        philhealth_number=data.get('philhealth_number') or None,
        pagibig_number=data.get('pagibig_number') or None,
        tin_number=data.get('tin_number') or None,
        emergency_contact_name=data.get('emergency_contact_name') or None,
        emergency_contact_phone=data.get('emergency_contact_phone') or None,
        emergency_contact_relationship=data.get('emergency_contact_relationship') or None,
        reference_name=data.get('reference_name') or None,
        reference_phone=data.get('reference_phone') or None,
        reference_company=data.get('reference_company') or None,
        date_hired=data.get('date_hired') or None,
        position=data.get('position') or None
    )
    ActivityLog.log(session['admin_id'], session['admin_name'], 'UPDATE', 'employee', emp_id, f"Updated employee {data['first_name']} {data['last_name']}", request.remote_addr)
    flash('Employee updated successfully', 'success')
    return redirect(url_for('admin_employees'))

@app.route('/admin/employees/<int:emp_id>/json')
@login_required
def get_employee_json(emp_id):
    from flask import jsonify
    emp = Employee.get_by_id(emp_id)
    if not emp:
        return jsonify({'error': 'Employee not found'}), 404
    
    conn = get_db()
    cursor = get_cursor(conn)
    cursor.execute('SELECT name FROM branches WHERE id = %s', (emp['branch_id'],))
    branch = cursor.fetchone()
    conn.close()
    
    return jsonify({
        'id': emp['id'],
        'employee_id': emp['employee_id'],
        'first_name': emp['first_name'],
        'last_name': emp['last_name'],
        'branch_id': emp['branch_id'],
        'branch_name': branch['name'] if branch else None,
        'daily_rate': emp['daily_rate'],
        'start_time': emp['start_time'],
        'end_time': emp['end_time'],
        'status': emp['status'] if 'status' in emp.keys() else ('resigned' if emp['is_resigned'] else 'active'),
        'status_reason': emp['status_reason'] if 'status_reason' in emp.keys() else None,
        'status_date': emp['status_date'] if 'status_date' in emp.keys() else None,
        'id_photo': emp['id_photo'] if 'id_photo' in emp.keys() else None,
        'cv_file': emp['cv_file'] if 'cv_file' in emp.keys() else None,
        'date_of_birth': emp['date_of_birth'] if 'date_of_birth' in emp.keys() else None,
        'gender': emp['gender'] if 'gender' in emp.keys() else None,
        'civil_status': emp['civil_status'] if 'civil_status' in emp.keys() else None,
        'address': emp['address'] if 'address' in emp.keys() else None,
        'phone': emp['phone'] if 'phone' in emp.keys() else None,
        'email': emp['email'] if 'email' in emp.keys() else None,
        'sss_number': emp['sss_number'] if 'sss_number' in emp.keys() else None,
        'philhealth_number': emp['philhealth_number'] if 'philhealth_number' in emp.keys() else None,
        'pagibig_number': emp['pagibig_number'] if 'pagibig_number' in emp.keys() else None,
        'tin_number': emp['tin_number'] if 'tin_number' in emp.keys() else None,
        'emergency_contact_name': emp['emergency_contact_name'] if 'emergency_contact_name' in emp.keys() else None,
        'emergency_contact_phone': emp['emergency_contact_phone'] if 'emergency_contact_phone' in emp.keys() else None,
        'emergency_contact_relationship': emp['emergency_contact_relationship'] if 'emergency_contact_relationship' in emp.keys() else None,
        'reference_name': emp['reference_name'] if 'reference_name' in emp.keys() else None,
        'reference_phone': emp['reference_phone'] if 'reference_phone' in emp.keys() else None,
        'reference_company': emp['reference_company'] if 'reference_company' in emp.keys() else None,
        'date_hired': emp['date_hired'] if 'date_hired' in emp.keys() else None,
        'position': emp['position'] if 'position' in emp.keys() else None
    })

@app.route('/admin/employees/<int:emp_id>/status', methods=['POST'])
@master_admin_required
def change_employee_status(emp_id):
    data = request.form
    status = data.get('status')
    reason = data.get('status_reason')
    
    if not status or not reason:
        flash('Status and reason are required', 'error')
        return redirect(url_for('admin_employees'))
    
    Employee.change_status(emp_id, status, reason)
    ActivityLog.log(session['admin_id'], session['admin_name'], 'STATUS_CHANGE', 'employee', emp_id, f"Changed status to {status}: {reason}", request.remote_addr)
    flash(f'Employee status changed to {status}', 'success')
    return redirect(url_for('admin_employees'))

@app.route('/admin/employees/<int:emp_id>/resign', methods=['POST'])
@master_admin_required
def resign_employee(emp_id):
    emp = Employee.get_by_id(emp_id)
    Employee.mark_resigned(emp_id)
    ActivityLog.log(session['admin_id'], session['admin_name'], 'RESIGN', 'employee', emp_id, f"Marked employee as resigned", request.remote_addr)
    flash('Employee marked as resigned', 'success')
    return redirect(url_for('admin_employees'))

@app.route('/admin/attendance')
@login_required
def admin_attendance():
    employees = Employee.get_all()
    today = get_manila_now().strftime('%Y-%m-%d')
    
    date_from = request.args.get('date_from', today)
    date_to = request.args.get('date_to', today)
    employee_filter = request.args.get('employee_id', '')
    
    conn = get_db()
    cursor = get_cursor(conn)
    
    if employee_filter:
        cursor.execute('''
            SELECT a.*, e.first_name, e.last_name, e.employee_id as emp_code
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            WHERE a.date BETWEEN %s AND %s AND a.employee_id = %s
            ORDER BY a.date DESC, a.time_in DESC
        ''', (date_from, date_to, employee_filter))
    else:
        cursor.execute('''
            SELECT a.*, e.first_name, e.last_name, e.employee_id as emp_code
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            WHERE a.date BETWEEN %s AND %s
            ORDER BY a.date DESC, a.time_in DESC
        ''', (date_from, date_to))
    
    attendance_records = cursor.fetchall()
    conn.close()
    
    return render_template('admin/attendance.html', 
                         employees=employees, 
                         attendance=attendance_records,
                         today=today,
                         date_from=date_from,
                         date_to=date_to,
                         employee_filter=employee_filter)

@app.route('/admin/attendance/overtime', methods=['POST'])
@master_admin_required
def approve_overtime():
    data = request.form
    Attendance.approve_overtime(int(data['attendance_id']), float(data['hours']))
    flash('Overtime approved', 'success')
    return redirect(url_for('admin_attendance'))

@app.route('/admin/payroll')
@login_required
def admin_payroll():
    periods = PayrollPeriod.get_all()
    return render_template('admin/payroll.html', periods=periods)

@app.route('/admin/payroll/create', methods=['POST'])
@master_admin_required
def create_payroll_period():
    data = request.form
    period_id = PayrollPeriod.create(
        data['name'],
        data['start_date'],
        data['end_date']
    )
    PayrollRecord.generate_for_period(period_id)
    flash('Payroll period created and records generated', 'success')
    return redirect(url_for('admin_payroll'))

@app.route('/admin/payroll/<int:period_id>')
@login_required
def view_payroll(period_id):
    period = PayrollPeriod.get_by_id(period_id)
    records = PayrollRecord.get_by_period(period_id)
    
    records_with_deductions = []
    for record in records:
        deductions = PayrollRecord.get_deduction_items(record['id'])
        records_with_deductions.append({
            'record': record,
            'deductions': deductions
        })
    
    return render_template('admin/payroll_view.html', 
                         period=period, 
                         records=records_with_deductions)

@app.route('/admin/payroll/<int:period_id>/lock', methods=['POST'])
@master_admin_required
def lock_payroll(period_id):
    PayrollPeriod.lock(period_id)
    flash('Payroll period locked', 'success')
    return redirect(url_for('view_payroll', period_id=period_id))

@app.route('/admin/payroll/<int:period_id>/regenerate', methods=['POST'])
@master_admin_required
def regenerate_payroll(period_id):
    period = PayrollPeriod.get_by_id(period_id)
    if period['is_locked']:
        flash('Cannot regenerate locked payroll period', 'error')
    else:
        PayrollRecord.generate_for_period(period_id)
        flash('Payroll records regenerated', 'success')
    return redirect(url_for('view_payroll', period_id=period_id))

@app.route('/admin/payroll/record/<int:record_id>/pdf')
@login_required
def download_payslip_pdf(record_id):
    conn = get_db()
    cursor = get_cursor(conn)
    
    cursor.execute('''
        SELECT pr.*, e.first_name, e.last_name, e.employee_id as emp_code,
               e.position, b.name as branch_name
        FROM payroll_records pr
        JOIN employees e ON pr.employee_id = e.id
        LEFT JOIN branches b ON e.branch_id = b.id
        WHERE pr.id = %s
    ''', (record_id,))
    record = cursor.fetchone()
    
    if not record:
        conn.close()
        flash('Payroll record not found', 'error')
        return redirect(url_for('admin_payroll'))
    
    cursor.execute('SELECT * FROM payroll_periods WHERE id = %s', (record['payroll_period_id'],))
    period = cursor.fetchone()
    
    cursor.execute('SELECT * FROM payroll_deduction_items WHERE payroll_record_id = %s', (record_id,))
    deductions = cursor.fetchall()
    conn.close()
    
    payroll_data = {
        'locked_daily_rate': record['locked_daily_rate'],
        'days_worked': record['days_worked'],
        'regular_pay': record['regular_pay'],
        'overtime_pay': record['overtime_pay'],
        'holiday_pay': record['holiday_pay'],
        'tardiness_deduction': record['tardiness_deduction'],
        'undertime_deduction': record['undertime_deduction'],
        'gross_pay': record['gross_pay'],
        'total_deductions': record['total_deductions'],
        'net_pay': record['net_pay']
    }
    
    employee_data = {
        'first_name': record['first_name'],
        'last_name': record['last_name'],
        'employee_id': record['emp_code'],
        'position': record['position'],
        'branch_name': record['branch_name']
    }
    
    period_data = {
        'name': period['name'],
        'start_date': period['start_date'],
        'end_date': period['end_date']
    }
    
    deductions_list = [dict(d) for d in deductions]
    
    pdf_buffer = generate_payslip_pdf(payroll_data, employee_data, period_data, deductions_list)
    
    filename = f"Payslip_{record['first_name']}_{record['last_name']}_{period['name'].replace(' ', '_')}.pdf"
    
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/admin/13th-month')
@login_required
def thirteenth_month():
    manila_now = get_manila_now()
    year = request.args.get('year', manila_now.year)
    results = PayrollRecord.get_13th_month(year)
    years = list(range(manila_now.year - 5, manila_now.year + 1))
    return render_template('admin/13th_month.html', results=results, year=int(year), years=years)

@app.route('/admin/settings')
@login_required
def admin_settings():
    deductions = StatutoryDeduction.get_all()
    holidays = Holiday.get_all()
    settings = {
        'grace_period': Settings.get('grace_period'),
        'work_start_time': Settings.get('work_start_time'),
        'work_end_time': Settings.get('work_end_time'),
        'work_hours': Settings.get('work_hours')
    }
    return render_template('admin/settings.html', 
                         deductions=deductions, 
                         holidays=holidays,
                         settings=settings)

@app.route('/admin/settings/general', methods=['POST'])
@master_admin_required
def update_general_settings():
    data = request.form
    Settings.set('grace_period', data['grace_period'])
    flash('Settings updated', 'success')
    return redirect(url_for('admin_settings'))

@app.route('/admin/deductions/add', methods=['POST'])
@master_admin_required
def add_deduction():
    data = request.form
    is_percentage = 1 if data.get('is_percentage') else 0
    result = StatutoryDeduction.create(
        data['name'],
        is_percentage,
        float(data['employee_rate']),
        float(data['employer_rate'])
    )
    if result:
        flash('Deduction added', 'success')
    else:
        flash('Deduction name already exists', 'error')
    return redirect(url_for('admin_settings'))

@app.route('/admin/deductions/<int:ded_id>/edit', methods=['POST'])
@master_admin_required
def edit_deduction(ded_id):
    data = request.form
    is_percentage = 1 if data.get('is_percentage') else 0
    is_active = 1 if data.get('is_active') else 0
    StatutoryDeduction.update(
        ded_id,
        data['name'],
        is_percentage,
        float(data['employee_rate']),
        float(data['employer_rate']),
        is_active
    )
    flash('Deduction updated', 'success')
    return redirect(url_for('admin_settings'))

@app.route('/admin/deductions/<int:ded_id>/delete', methods=['POST'])
@master_admin_required
def delete_deduction(ded_id):
    password = request.form.get('password')
    if not Admin.verify_password(session['admin_username'], password):
        flash('Invalid password. Delete cancelled.', 'error')
        return redirect(url_for('admin_settings'))
    StatutoryDeduction.delete(ded_id)
    ActivityLog.log(session['admin_id'], session['admin_name'], 'DELETE', 'deduction', ded_id, 'Deleted statutory deduction', request.remote_addr)
    flash('Deduction deleted', 'success')
    return redirect(url_for('admin_settings'))

@app.route('/admin/holidays/add', methods=['POST'])
@master_admin_required
def add_holiday():
    data = request.form
    result = Holiday.create(data['date'], data['name'], data['type'])
    if result:
        flash('Holiday added', 'success')
    else:
        flash('Holiday already exists for this date', 'error')
    return redirect(url_for('admin_settings'))

@app.route('/admin/holidays/<int:holiday_id>/delete', methods=['POST'])
@master_admin_required
def delete_holiday(holiday_id):
    password = request.form.get('password')
    if not Admin.verify_password(session['admin_username'], password):
        flash('Invalid password. Delete cancelled.', 'error')
        return redirect(url_for('admin_settings'))
    Holiday.delete(holiday_id)
    ActivityLog.log(session['admin_id'], session['admin_name'], 'DELETE', 'holiday', holiday_id, 'Deleted holiday', request.remote_addr)
    flash('Holiday deleted', 'success')
    return redirect(url_for('admin_settings'))

@app.route('/admin/branches/add', methods=['POST'])
@master_admin_required
def add_branch():
    data = request.form
    result = Branch.create(data['name'], data.get('address', ''))
    if result:
        ActivityLog.log(session['admin_id'], session['admin_name'], 'CREATE', 'branch', result, f"Added branch {data['name']}", request.remote_addr)
        flash('Branch added successfully', 'success')
    else:
        flash('Branch name already exists', 'error')
    return redirect(url_for('admin_branches'))

@app.route('/admin/branches/<int:branch_id>/gps', methods=['POST'])
@master_admin_required
def update_branch_gps(branch_id):
    data = request.form
    try:
        lat = float(data['latitude']) if data.get('latitude') and data['latitude'].strip() else None
        lng = float(data['longitude']) if data.get('longitude') and data['longitude'].strip() else None
        radius_str = data.get('radius', '100').strip()
        radius = int(radius_str) if radius_str else 100
        radius = max(10, min(1000, radius))
    except (ValueError, TypeError):
        flash('Invalid GPS coordinates or radius', 'error')
        return redirect(url_for('admin_branches'))
    
    Branch.update_gps(branch_id, lat, lng, radius)
    flash('Branch GPS location updated', 'success')
    return redirect(url_for('admin_branches'))

@app.route('/admin/branches')
@login_required
def admin_branches():
    branches = Branch.get_all()
    return render_template('admin/branches.html', branches=branches, can_edit_delete=can_edit_delete())

@app.route('/admin/branches/<int:branch_id>/delete', methods=['POST'])
@master_admin_required
def delete_branch(branch_id):
    password = request.form.get('password')
    if not Admin.verify_password(session['admin_username'], password):
        flash('Invalid password. Delete cancelled.', 'error')
        return redirect(url_for('admin_branches'))
    success, message = Branch.delete(branch_id)
    if success:
        ActivityLog.log(session['admin_id'], session['admin_name'], 'DELETE', 'branch', branch_id, message, request.remote_addr)
        flash(message, 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('admin_branches'))

@app.route('/admin/admins')
@master_admin_required
def admin_admins():
    admins = Admin.get_all()
    return render_template('admin/admins.html', admins=admins)

@app.route('/admin/admins/add', methods=['POST'])
@master_admin_required
def add_admin():
    data = request.form
    result = Admin.create(data['username'], data['password'], data['full_name'], data.get('role', 'sub_admin'))
    if result:
        ActivityLog.log(session['admin_id'], session['admin_name'], 'CREATE', 'admin', result, f"Created admin {data['username']}", request.remote_addr)
        flash('Admin user created', 'success')
    else:
        flash('Username already exists', 'error')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/<int:admin_id>/update', methods=['POST'])
@master_admin_required
def update_admin(admin_id):
    data = request.form
    is_active = 1 if data.get('is_active') else 0
    Admin.update(admin_id, data['full_name'], data['role'], is_active)
    if data.get('new_password'):
        Admin.update_password(admin_id, data['new_password'])
    ActivityLog.log(session['admin_id'], session['admin_name'], 'UPDATE', 'admin', admin_id, f"Updated admin account", request.remote_addr)
    flash('Admin updated', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/admins/<int:admin_id>/delete', methods=['POST'])
@master_admin_required
def delete_admin(admin_id):
    password = request.form.get('password')
    if not Admin.verify_password(session['admin_username'], password):
        flash('Invalid password. Delete cancelled.', 'error')
        return redirect(url_for('admin_admins'))
    target_admin = Admin.get_by_id(admin_id)
    if target_admin and target_admin['role'] == 'master_admin':
        flash('Cannot delete master admin', 'error')
        return redirect(url_for('admin_admins'))
    Admin.delete(admin_id)
    ActivityLog.log(session['admin_id'], session['admin_name'], 'DELETE', 'admin', admin_id, 'Deleted admin account', request.remote_addr)
    flash('Admin deleted', 'success')
    return redirect(url_for('admin_admins'))

@app.route('/admin/auth-codes')
@master_admin_required
def admin_auth_codes():
    codes = AdminAuthCode.get_all()
    return render_template('admin/auth_codes.html', codes=codes)

@app.route('/admin/auth-codes/add', methods=['POST'])
@master_admin_required
def add_auth_code():
    data = request.form
    code = data.get('code') or AdminAuthCode.generate_random_code()
    code_type = data['code_type']
    description = data.get('description', '')
    uses_remaining = int(data.get('uses_remaining', -1))
    valid_until = data.get('valid_until') or None
    allowable_hours = float(data.get('allowable_hours', 0))
    
    result = AdminAuthCode.create(code, code_type, description, uses_remaining, valid_until, session['admin_id'], allowable_hours=allowable_hours)
    if result:
        ActivityLog.log(session['admin_id'], session['admin_name'], 'CREATE', 'auth_code', result, f"Created {code_type} auth code: {code}", request.remote_addr)
        flash(f'Authorization code created: {code}', 'success')
    else:
        flash('Code already exists', 'error')
    return redirect(url_for('admin_auth_codes'))

@app.route('/admin/auth-codes/<int:code_id>/edit', methods=['POST'])
@master_admin_required
def edit_auth_code(code_id):
    data = request.form
    is_active = 1 if data.get('is_active') else 0
    uses_remaining = int(data.get('uses_remaining', -1))
    valid_until = data.get('valid_until') or None
    allowable_hours = float(data.get('allowable_hours', 0))
    
    AdminAuthCode.update(code_id, data['code'], data.get('description', ''), is_active, uses_remaining, valid_until, allowable_hours=allowable_hours)
    ActivityLog.log(session['admin_id'], session['admin_name'], 'UPDATE', 'auth_code', code_id, 'Updated auth code', request.remote_addr)
    flash('Authorization code updated', 'success')
    return redirect(url_for('admin_auth_codes'))

@app.route('/admin/auth-codes/<int:code_id>/delete', methods=['POST'])
@master_admin_required
def delete_auth_code(code_id):
    AdminAuthCode.delete(code_id)
    ActivityLog.log(session['admin_id'], session['admin_name'], 'DELETE', 'auth_code', code_id, 'Deleted auth code', request.remote_addr)
    flash('Authorization code deleted', 'success')
    return redirect(url_for('admin_auth_codes'))

@app.route('/admin/auth-codes/generate', methods=['POST'])
@master_admin_required
def generate_auth_code():
    code = AdminAuthCode.generate_random_code()
    return jsonify({'success': True, 'code': code})

@app.route('/admin/database-reset', methods=['POST'])
@master_admin_required
def database_reset():
    password = request.form.get('password')
    confirm_text = request.form.get('confirm_text', '')
    if confirm_text != 'DELETE ALL DATA':
        flash('Confirmation text does not match. Reset cancelled.', 'error')
        return redirect(url_for('admin_settings'))
    if not Admin.verify_password(session['admin_username'], password):
        flash('Invalid password. Reset cancelled.', 'error')
        return redirect(url_for('admin_settings'))
    DatabaseManager.reset_all_data()
    ActivityLog.log(session['admin_id'], session['admin_name'], 'DATABASE_RESET', None, None, 'All employee and attendance data deleted', request.remote_addr)
    flash('All employee and attendance data has been deleted', 'success')
    return redirect(url_for('admin_settings'))

@app.route('/tablet')
def tablet_station():
    employees = Employee.get_active()
    return render_template('tablet/station.html', employees=employees)

@app.route('/api/verify-pin', methods=['POST'])
def verify_pin():
    data = request.json
    employee_id = data.get('employee_id')
    pin = data.get('pin')
    
    if Employee.verify_pin(employee_id, pin):
        status = Attendance.get_today_status(employee_id)
        has_open_record = status is not None
        return jsonify({
            'success': True, 
            'has_open_record': has_open_record,
            'current_purpose': status['time_in_purpose'] if has_open_record else None
        })
    return jsonify({'success': False, 'message': 'Invalid PIN'})

@app.route('/api/record-attendance', methods=['POST'])
def record_attendance():
    data = request.json
    employee_id = data.get('employee_id')
    action = data.get('action')
    purpose = data.get('purpose', 'clock_in' if action == 'time_in' else 'clock_out')
    photo_data = data.get('photo')
    early_start_approved = data.get('early_start_approved', False)
    official_overtime_approved = data.get('official_overtime_approved', False)
    is_remote_field = data.get('is_remote_field', False)
    remote_field_hours = data.get('remote_field_hours', 0)
    
    if photo_data:
        photo_data = photo_data.split(',')[1]
        photo_bytes = base64.b64decode(photo_data)
        timestamp = get_manila_now().strftime('%Y%m%d_%H%M%S')
        filename = f"{employee_id}_{purpose}_{timestamp}.jpg"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(photo_bytes))
        img = img.convert('RGB')
        max_size = (640, 480)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        img.save(filepath, 'JPEG', quality=60, optimize=True)
        photo_path = filepath
    else:
        photo_path = None
    
    if action == 'time_in':
        record_id, message = Attendance.time_in(employee_id, photo_path, purpose, early_start_approved, is_remote_field=is_remote_field, remote_field_hours=remote_field_hours)
    else:
        record_id, message = Attendance.time_out(employee_id, photo_path, purpose, official_overtime_approved)
    
    if record_id:
        return jsonify({'success': True, 'message': message})
    return jsonify({'success': False, 'message': message})

@app.route('/api/verify-auth-code', methods=['POST'])
def verify_auth_code():
    data = request.json
    code = data.get('code')
    code_type = data.get('code_type')
    
    conn = get_db()
    cursor = get_cursor(conn)
    today = date.today().isoformat()
    cursor.execute('''
        SELECT * FROM admin_auth_codes 
        WHERE code = %s AND code_type = %s AND is_active = TRUE 
        AND (valid_until IS NULL OR valid_until >= %s)
        AND (uses_remaining = -1 OR uses_remaining > 0)
    ''', (code, code_type, today))
    auth_code = cursor.fetchone()
    
    if auth_code:
        if auth_code['uses_remaining'] > 0:
            cursor.execute('UPDATE admin_auth_codes SET uses_remaining = uses_remaining - 1 WHERE id = %s', (auth_code['id'],))
            conn.commit()
        
        allowable_hours = auth_code.get('allowable_hours', 0)
        conn.close()
        return jsonify({
            'success': True, 
            'message': 'Code verified successfully',
            'allowable_hours': allowable_hours
        })
    
    conn.close()
    return jsonify({'success': False, 'message': 'Invalid or expired code'})

@app.route('/api/employees')
def api_employees():
    employees = Employee.get_active()
    return jsonify([dict(e) for e in employees])

@app.route('/api/reverse-geocode', methods=['POST'])
def reverse_geocode():
    data = request.json
    lat = data.get('lat')
    lng = data.get('lng')
    
    if not lat or not lng:
        return jsonify({'success': False, 'place': 'Unknown location'})
    
    try:
        response = http_requests.get(
            f'https://nominatim.openstreetmap.org/reverse',
            params={
                'format': 'json',
                'lat': lat,
                'lon': lng,
                'zoom': 18,
                'addressdetails': 1
            },
            headers={'User-Agent': '3DBotics-Payroll/1.0'},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            address = result.get('address', {})
            place_parts = []
            if address.get('road'):
                place_parts.append(address['road'])
            if address.get('suburb') or address.get('neighbourhood'):
                place_parts.append(address.get('suburb') or address.get('neighbourhood'))
            if address.get('city') or address.get('town') or address.get('municipality'):
                place_parts.append(address.get('city') or address.get('town') or address.get('municipality'))
            
            place = ', '.join(place_parts) if place_parts else result.get('display_name', 'Unknown location')
            return jsonify({'success': True, 'place': place[:60]})
    except Exception as e:
        pass
    
    return jsonify({'success': False, 'place': 'Location unavailable'})

@app.route('/api/validate-location', methods=['POST'])
def validate_location():
    data = request.json
    branch_name = data.get('branch')
    lat = data.get('lat')
    lng = data.get('lng')
    
    if not lat or not lng:
        return jsonify({'valid': True, 'message': 'GPS not available'})
    
    is_valid, message = Branch.validate_location(branch_name, lat, lng)
    return jsonify({'valid': is_valid, 'message': message})

@app.route('/admin/attendance/<int:attendance_id>/delete', methods=['POST'])
@master_admin_required
def delete_attendance(attendance_id):
    password = request.form.get('password')
    if not Admin.verify_password(session.get('admin_username', ''), password):
        flash('Invalid password. Delete cancelled.', 'error')
        return redirect(url_for('admin_attendance'))
    
    record = Attendance.get_by_id(attendance_id)
    if record:
        details = f"Deleted attendance for {record['first_name']} {record['last_name']} ({record['emp_code']}) on {record['date']}"
        Attendance.delete(attendance_id)
        ActivityLog.log(
            admin_id=session.get('admin_id', 1),
            admin_name=session.get('admin_name', 'Admin'),
            action='DELETE_ATTENDANCE',
            target_type='attendance',
            target_id=attendance_id,
            details=details,
            ip_address=request.remote_addr
        )
        flash('Attendance record deleted', 'success')
    else:
        flash('Attendance record not found', 'error')
    return redirect(url_for('admin_attendance'))

@app.route('/admin/activity-logs')
@login_required
def activity_logs():
    logs = ActivityLog.get_all(limit=200)
    return render_template('admin/activity_logs.html', logs=logs)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
