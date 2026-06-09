# 3DBotics Attendance & Payroll System

A full-featured employee attendance tracking and payroll management system built with Flask and PostgreSQL. Designed for use with a tablet kiosk station for selfie-based clock-in/out with GPS geofencing.

---

## Features

- **Tablet Kiosk Station** — Employees select their name, enter a 4-digit PIN, and take a selfie to clock in or out. Supports multiple attendance purposes (Clock In/Out, Lunch Break, Snack Break, Emergency, Overtime, Remote/Field).
- **GPS Geofencing** — Each branch has a configurable GPS radius. Attendance photos are watermarked with location status; out-of-bounds records are flagged.
- **Admin Panel** — Full CRUD for employees, branches, payroll periods, statutory deductions, and holidays.
- **Role-Based Access Control** — Three roles: `master_admin` (full access), `staff` (add/edit employees), `sub_admin` (view and compute payroll only).
- **Payroll Generation** — Automatic computation of regular pay, overtime (1.25×), holiday pay, tardiness/undertime deductions, and Philippine statutory contributions (SSS, PhilHealth, Pag-IBIG) using 2025 rates.
- **PDF Payslips** — Downloadable per-employee payslips with full deduction breakdown.
- **13th Month Pay** — Automatic computation per employee per calendar year.
- **Authorization Codes** — One-time codes for early start, official overtime, and remote/field work approval.
- **Activity Logs** — All admin actions are logged with IP address for audit purposes.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, Flask |
| Database | PostgreSQL (Supabase or self-hosted) |
| Frontend | Jinja2 templates, TailwindCSS, Font Awesome |
| PDF | ReportLab |
| Auth | Werkzeug password hashing, Flask sessions |
| Deployment | Gunicorn |

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- A PostgreSQL database (Supabase recommended for cloud deployments)

### Installation

```bash
# Clone the repository
git clone https://github.com/3DBotics/attendance.git
cd attendance

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:password@host:5432/dbname"
export SESSION_SECRET="your-secret-key-here"

# Optional: Supabase storage for photos
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-anon-key"

# Run the application
python main.py
```

The app will be available at `http://localhost:5000`.

The database schema is created automatically on first startup via `init_db()`.

### Default Admin Credentials

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | Master Admin |

**Change the default password immediately after first login.**

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `SESSION_SECRET` | Yes | Flask session secret key |
| `SUPABASE_URL` | No | Supabase project URL (for photo storage) |
| `SUPABASE_KEY` | No | Supabase anon key |

---

## Admin Roles

| Role | Permissions |
|---|---|
| `master_admin` | Full access: create/edit/delete employees, branches, payroll, admins, settings |
| `staff` | Add and edit employee information; cannot terminate employees or manage payroll |
| `sub_admin` | View-only: can view and compute payroll but cannot make changes |

---

## Attendance Purposes

| Purpose | Action | Description |
|---|---|---|
| `clock_in` | Time In | Standard start of work day |
| `early_start` | Time In | Requires admin authorization code |
| `remote_field` | Time In | Work from home / field work; bypasses GPS check |
| `clock_out` | Time Out | Standard end of work day |
| `official_overtime` | Time Out | Approved overtime; paid at 1.25× hourly rate |
| `unapproved_undertime_out` | Time Out | Leaving before scheduled end time |
| `lunch_break_out` / `lunch_break_in` | Both | Lunch break tracking |
| `snack_break_out` / `snack_break_in` | Both | Snack break tracking |
| `emergency_out` / `emergency_in` | Both | Emergency leave tracking |

---

## Project Structure

```
attendance/
├── app.py                          # Flask application, routes, and API endpoints
├── models.py                       # Database models and business logic
├── pdf_payslip.py                  # PDF payslip generation and statutory contribution calculators
├── main.py                         # Application entry point
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Modern Python project metadata
├── create_employee_schedules.sql   # One-off migration (only needed for pre-existing databases)
├── run_migration.py                # Runner for the above migration
├── add_purpose_labels.sql          # One-off migration for purpose label columns
├── static/
│   ├── logo.png
│   └── uploads/                    # Employee photos and CV files
└── templates/
    ├── base.html
    ├── index.html
    ├── admin/
    │   ├── base_admin.html
    │   ├── dashboard.html
    │   ├── employees.html
    │   ├── attendance.html
    │   ├── payroll.html
    │   ├── payroll_view.html
    │   ├── 13th_month.html
    │   ├── settings.html
    │   ├── branches.html
    │   ├── admins.html
    │   ├── auth_codes.html
    │   ├── activity_logs.html
    │   └── login.html
    └── tablet/
        └── station.html            # Tablet kiosk UI
```

---

## Statutory Contribution Rates (2025)

| Contribution | Employee Share | Employer Share |
|---|---|---|
| SSS | 5% of MSC | 10% of MSC + EC |
| PhilHealth | 2.5% of monthly salary | 2.5% of monthly salary |
| Pag-IBIG | 2% (max ₱200) | 2% (max ₱200) |

Contributions are prorated for payroll periods shorter than a full month.

---

## Deployment

For production, use Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

The application is designed for deployment on Railway, Render, or any platform that supports Python and PostgreSQL.
