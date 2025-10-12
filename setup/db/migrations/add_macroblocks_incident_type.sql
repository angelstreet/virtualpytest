-- Add 'macroblocks' to the incident_type check constraint
-- This allows the alerts table to accept macroblocks incidents
-- Applied: 2025-10-12

-- Drop the existing constraint
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_incident_type_check;

-- Add new constraint with 'macroblocks' included
ALTER TABLE alerts ADD CONSTRAINT alerts_incident_type_check 
  CHECK (incident_type = ANY (ARRAY['blackscreen'::text, 'freeze'::text, 'errors'::text, 'audio_loss'::text, 'macroblocks'::text]));

-- Update comment to reflect new incident type
COMMENT ON COLUMN alerts.incident_type IS 'Type of incident: blackscreen, freeze, errors, audio_loss, or macroblocks';

