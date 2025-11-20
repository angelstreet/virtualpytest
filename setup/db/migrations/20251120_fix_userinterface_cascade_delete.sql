-- Migration: Fix userinterface delete cascade for verifications_references table
-- Date: 2025-11-20
-- Issue: Deleting userinterfaces fails when they have associated verification references
-- Solution: Add ON DELETE CASCADE to userinterface_id foreign key

-- Drop existing foreign key constraint
ALTER TABLE verifications_references 
DROP CONSTRAINT IF EXISTS verifications_references_userinterface_id_fkey;

-- Recreate with ON DELETE CASCADE
ALTER TABLE verifications_references 
ADD CONSTRAINT verifications_references_userinterface_id_fkey 
FOREIGN KEY (userinterface_id) 
REFERENCES userinterfaces(id) 
ON DELETE CASCADE;

-- Verification query
SELECT 
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
JOIN information_schema.referential_constraints AS rc
    ON rc.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name = 'verifications_references'
    AND kcu.column_name = 'userinterface_id';

