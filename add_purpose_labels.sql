-- Add columns to store original purpose labels
ALTER TABLE attendance 
ADD COLUMN IF NOT EXISTS time_in_purpose_label VARCHAR(50),
ADD COLUMN IF NOT EXISTS time_out_purpose_label VARCHAR(50);

-- Update existing records to have proper labels based on current purpose
UPDATE attendance 
SET time_in_purpose_label = CASE 
    WHEN time_in_purpose = 'clock_in' THEN 'Clock In'
    ELSE time_in_purpose
END
WHERE time_in_purpose_label IS NULL;

UPDATE attendance 
SET time_out_purpose_label = CASE 
    WHEN time_out_purpose = 'clock_out' THEN 'Clock Out'
    ELSE time_out_purpose
END
WHERE time_out_purpose_label IS NULL;
