# Employee Schedules Database Schema

## Table: employee_schedules

This table stores the weekly schedule for each employee with effective date tracking for history.

### Columns:

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL PRIMARY KEY | Unique identifier |
| employee_id | INTEGER | Foreign key to employees table |
| effective_from | DATE | Date when this schedule becomes active |
| effective_to | DATE | Date when this schedule ends (NULL for current schedule) |
| created_at | TIMESTAMP | When this schedule was created |
| created_by | INTEGER | Admin user who created this schedule |

### Day-specific columns (for each day of the week):

For each day (sunday, monday, tuesday, wednesday, thursday, friday, saturday):

| Column Pattern | Type | Description |
|----------------|------|-------------|
| {day}_is_working | BOOLEAN | Whether this is a working day (false = rest day) |
| {day}_start_time | TIME | Start time for this day |
| {day}_end_time | TIME | End time for this day |

Example:
- sunday_is_working (BOOLEAN)
- sunday_start_time (TIME)
- sunday_end_time (TIME)
- monday_is_working (BOOLEAN)
- monday_start_time (TIME)
- monday_end_time (TIME)
- ... and so on for all 7 days

### Indexes:

- employee_id (for quick lookup)
- effective_from, effective_to (for date range queries)

### Constraints:

- Only one schedule per employee can have effective_to = NULL (current schedule)
- effective_from must be <= effective_to (if effective_to is not NULL)
- Foreign key to employees(id)

### Usage:

1. When creating a new schedule, set the previous schedule's effective_to to the day before the new schedule's effective_from
2. Current schedule always has effective_to = NULL
3. Payroll generation queries for the schedule that was active during the pay period
