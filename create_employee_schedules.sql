-- Create employee_schedules table for dynamic day-by-day schedule management
CREATE TABLE IF NOT EXISTS employee_schedules (
    id SERIAL PRIMARY KEY,
    employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
    effective_from DATE NOT NULL,
    effective_to DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES admins(id),
    
    -- Sunday schedule
    sunday_is_working BOOLEAN DEFAULT false,
    sunday_start_time TIME,
    sunday_end_time TIME,
    
    -- Monday schedule
    monday_is_working BOOLEAN DEFAULT true,
    monday_start_time TIME DEFAULT '08:00',
    monday_end_time TIME DEFAULT '17:00',
    
    -- Tuesday schedule
    tuesday_is_working BOOLEAN DEFAULT true,
    tuesday_start_time TIME DEFAULT '08:00',
    tuesday_end_time TIME DEFAULT '17:00',
    
    -- Wednesday schedule
    wednesday_is_working BOOLEAN DEFAULT true,
    wednesday_start_time TIME DEFAULT '08:00',
    wednesday_end_time TIME DEFAULT '17:00',
    
    -- Thursday schedule
    thursday_is_working BOOLEAN DEFAULT true,
    thursday_start_time TIME DEFAULT '08:00',
    thursday_end_time TIME DEFAULT '17:00',
    
    -- Friday schedule
    friday_is_working BOOLEAN DEFAULT true,
    friday_start_time TIME DEFAULT '08:00',
    friday_end_time TIME DEFAULT '17:00',
    
    -- Saturday schedule
    saturday_is_working BOOLEAN DEFAULT true,
    saturday_start_time TIME DEFAULT '08:00',
    saturday_end_time TIME DEFAULT '17:00',
    
    -- Constraints
    CONSTRAINT valid_date_range CHECK (effective_to IS NULL OR effective_from <= effective_to),
    CONSTRAINT one_current_schedule_per_employee UNIQUE (employee_id, effective_to) DEFERRABLE INITIALLY DEFERRED
);

-- Create indexes for performance
CREATE INDEX idx_employee_schedules_employee_id ON employee_schedules(employee_id);
CREATE INDEX idx_employee_schedules_dates ON employee_schedules(effective_from, effective_to);
CREATE INDEX idx_employee_schedules_current ON employee_schedules(employee_id, effective_to) WHERE effective_to IS NULL;

-- Migrate existing employee schedules from employees table
INSERT INTO employee_schedules (
    employee_id, 
    effective_from, 
    effective_to,
    monday_is_working, monday_start_time, monday_end_time,
    tuesday_is_working, tuesday_start_time, tuesday_end_time,
    wednesday_is_working, wednesday_start_time, wednesday_end_time,
    thursday_is_working, thursday_start_time, thursday_end_time,
    friday_is_working, friday_start_time, friday_end_time,
    saturday_is_working, saturday_start_time, saturday_end_time,
    sunday_is_working, sunday_start_time, sunday_end_time
)
SELECT 
    id as employee_id,
    CURRENT_DATE as effective_from,
    NULL as effective_to,
    true, start_time, end_time,  -- Monday
    true, start_time, end_time,  -- Tuesday
    true, start_time, end_time,  -- Wednesday
    true, start_time, end_time,  -- Thursday
    true, start_time, end_time,  -- Friday
    true, start_time, end_time,  -- Saturday
    false, NULL, NULL            -- Sunday (rest day)
FROM employees
WHERE start_time IS NOT NULL AND end_time IS NOT NULL;

-- Add comment to the table
COMMENT ON TABLE employee_schedules IS 'Stores employee work schedules with day-by-day configuration and history tracking';
