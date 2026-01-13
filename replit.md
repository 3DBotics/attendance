# 3DBotics Branch & Payroll Management System

## Overview
A tablet-optimized attendance and payroll management system with selfie verification, DOLE-compliant calculations, and PostgreSQL database for persistent data storage.

## Current State
- MVP implementation complete with all core features
- Flask backend with PostgreSQL database (Replit built-in)
- Tailwind CSS frontend
- Tablet station with camera integration

## Project Architecture

### Backend (Python/Flask)
- `app.py` - Main Flask application with all routes
- `models.py` - PostgreSQL database models and operations using psycopg2
- Database connection via DATABASE_URL environment variable (auto-configured by Replit)

### Frontend Templates
- `templates/base.html` - Base template with Tailwind CSS
- `templates/index.html` - Home page with navigation
- `templates/admin/` - Admin dashboard templates
- `templates/tablet/station.html` - Tablet attendance station

### Static Files
- `static/uploads/` - Selfie photos storage

## Key Features

### Employee Management
- CRUD operations for employees
- 4-digit PIN for authentication
- Daily rate management
- Individual start time (ST) and end time (ET) per employee
- Resignation tracking

### Attendance System
- Selfie capture using HTML5 MediaDevices API
- Multiple clock events per day with purpose tracking:
  - Clock In / Clock Out
  - Lunch Break - Out / In
  - Snack Break - Out / In
  - Emergency (CR, Family, Health) - Out / In
  - Unapproved Undertime - Out
- Each clock event creates a segment in the attendance record
- Tardiness calculated only on first Clock In of the day
- Undertime calculated only on Clock Out or Unapproved Undertime Out
- Grace period configuration

### Payroll Processing
- DOLE-compliant calculations
- Tardiness deduction: (Daily Rate / 8 / 60) * Minutes Late
- Overtime pay: 125% of hourly rate
- Holiday pay: Regular (200%), Special (130%)
- Rate locking for historical accuracy

### Statutory Deductions (2025 Philippine Mandates)
- **SSS**: 15% total (EE: 5%, ER: 10% + EC) using official 2025 MSC bracket table
  - MSC ranges from P5,000 to P35,000
  - EC: P10 for MSC up to P14,500; P30 for MSC P15,000+
- **PhilHealth**: 5% total (EE: 2.5%, ER: 2.5%)
  - Floor: P10,000 (min contribution P250 each)
  - Ceiling: P100,000 (max contribution P2,500 each)
- **Pag-IBIG**: 2% EE / 2% ER
  - Max contribution capped at P200 each

### PDF Payslip Generation
- Professional two-column layout (Earnings left, Deductions right)
- 3DBotics® logo and branding in header
- Clear separation of Employee vs Employer contributions
- Company contributions section shows ER shares (not deducted from employee)
- Locked rate preserved - changing daily rate later doesn't affect old payslips

### Reports
- 13th Month Pay: Total Basic Salary for Year / 12
- Payroll summary reports with PDF download
- Attendance reports

## Running the Application
```bash
python app.py
```
Server runs on `0.0.0.0:5000` for local network access.

## User Preferences
- Large touch-friendly UI for tablet use
- High-contrast text for readability
- PostgreSQL for persistent data storage (persists across deployments)

## Recent Changes
- December 30, 2025: CRITICAL FIX - Added anomaly detection for cross-day clock-outs without overtime approval. When an employee clocks out the next day without using Official Overtime, the system flags the record as "Requires Admin Review" instead of computing incorrect tardiness/undertime. Flagged records are excluded from payroll deduction calculations.
- December 28, 2025: CRITICAL FIX - Overnight shift undertime calculation corrected. When employee clocks in on day 1 and clocks out on day 2, no undertime is calculated (they worked past their scheduled end time). Previously, the system incorrectly calculated undertime by comparing to the wrong day's schedule.
- December 28, 2025: FIX - Attendance display now shows the actual clock-out date when different from clock-in date (e.g., "(12-28) 12:17" for overnight shifts).
- December 27, 2025: FIX - Attendance now records actual clock-in/out times (e.g., 6:43am) instead of clamping to schedule. Payroll still calculates based on official hours unless approved.
- December 27, 2025: FIX - Profile photos now accept JPEG, PNG, and WebP formats (previously only JPEG worked)
- December 26, 2025: CRITICAL - Migrated from SQLite to PostgreSQL for persistent data in production deployments
- December 18, 2025: Added PDF Payslip download with 3DBotics branding and professional two-column layout
- December 18, 2025: Implemented 2025 Philippine statutory deduction formulas (SSS bracket table, PhilHealth, Pag-IBIG)
- December 18, 2025: Added employer contribution tracking on payslips (not deducted from employee net pay)
- December 18, 2025: Rate locking ensures historical payslips remain accurate when daily rate is changed
- December 18, 2025: CRITICAL FIX - Payroll now calculates pay based on actual hours worked, not just days present
- December 18, 2025: Days worked is now a decimal representing actual vs scheduled hours (e.g., 0.14 for partial day)
- December 18, 2025: Undertime properly calculated as scheduled hours minus actual hours worked
- December 17, 2025: Added comprehensive employee records system with 20+ fields (personal info, government IDs, emergency contacts, references)
- December 17, 2025: Added real-time camera capture for employee ID photos with secure upload validation
- December 17, 2025: Added CV/Resume PDF upload with MIME type and size validation
- December 17, 2025: Added employee status options (Active, Resigned, Terminated, Others) with required reason field
- December 17, 2025: Added employee view modal showing full details
- December 17, 2025: Removed Add Branch button from employees page (use Branches tab)
- December 17, 2025: Removed general Work Start/End Time from settings (now per-employee)
- December 17, 2025: Implemented individual employee schedules (ST/ET) with admin authorization codes for early start and overtime approval
- December 17, 2025: Added Official Early Start and Official Overtime buttons with one-time code verification
- December 17, 2025: Payroll now uses individual employee work hours for rate calculations (1.25x for approved overtime)
- December 18, 2025: Fixed clock-out to work across midnight (overnight shifts can now clock out the next day)
- December 17, 2025: Added date range filtering and employee filter to admin attendance view (full history access)
- December 17, 2025: Fixed cross-midnight tardiness/undertime calculation (handles overnight shifts correctly)
- December 17, 2025: Fixed payroll calculation to properly count unique dates (not individual attendance segments) as days worked
- December 17, 2025: Implemented multi-event attendance with purpose selection (Clock In/Out, Lunch/Snack Breaks, Emergency, Unapproved Undertime)
- December 17, 2025: Removed navigation to admin panel from tablet station (prevents unauthorized access)
- December 17, 2025: Fixed timezone to use Asia/Manila (Philippines) for all timestamps
- December 17, 2025: Added dedicated Branches management page with Add Branch functionality
- December 17, 2025: Database reset now includes deleting all branches (count goes to 0)
- December 17, 2025: Implemented complete admin authentication with role-based access control
- December 17, 2025: Added master admin and sub-admin roles with permission restrictions
- December 17, 2025: Sub-admins can only view - edit/delete buttons hidden for non-master admins
- December 17, 2025: Password-protected delete operations for all destructive actions
- December 17, 2025: Database reset with double confirmation ("DELETE ALL DATA" + password)
- December 17, 2025: Activity logging for all admin actions with IP tracking
- December 17, 2025: Added GPS geofencing with configurable radius per branch
- December 17, 2025: Implemented reverse geocoding for human-readable location names in watermarks
- December 17, 2025: Added "INVALID LOCATION" watermark for out-of-bounds attendance
- December 17, 2025: Fixed time format to 12-hour AM/PM across all watermarks
- December 17, 2025: Styled logo with white circular background and teal double-ring border
- December 17, 2025: Added Branch GPS Settings admin page for location configuration
- December 17, 2025: Applied 3DBotics branding (teal #2D4A5E, cyan #6ECEDA, coral #E8886A, lime #C4D93E)
- December 2024: Initial MVP implementation

## Admin Authentication
- Default master admin: username `admin`, password `admin123` (change after first login)
- Master admins have full control: create/edit/delete employees, branches, payroll, admins
- Sub-admins can only view data and compute salaries (monitor-only access)
- All destructive operations require password re-confirmation
- Session-based authentication with secure cookies
