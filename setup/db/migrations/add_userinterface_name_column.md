# Migration: Add userinterface_name Column

## Date
2025-10-19

## Purpose
Add `userinterface_name` column to `verifications_references` table for clearer, more coherent reference organization.

## Changes

### Database Schema
```sql
-- Add userinterface_name column
ALTER TABLE verifications_references 
ADD COLUMN IF NOT EXISTS userinterface_name TEXT;

-- Migrate existing data
UPDATE verifications_references 
SET userinterface_name = device_model 
WHERE userinterface_name IS NULL;

-- Create index
CREATE INDEX IF NOT EXISTS idx_verifications_references_userinterface_name 
ON verifications_references(userinterface_name);

-- Update unique constraint
ALTER TABLE verifications_references 
DROP CONSTRAINT IF EXISTS verifications_references_team_id_name_device_model_reference_key;

ALTER TABLE verifications_references 
ADD CONSTRAINT verifications_references_team_id_name_userinterface_reference_key 
UNIQUE (team_id, name, userinterface_name, reference_type);
```

## Rationale

### Before (Confusing)
- Database column: `device_model`
- Actual data stored: userinterface names (e.g., `"horizon_android_tv"`)
- ❌ Naming confusion: column says "device_model" but contains userinterface names

### After (Clear)
- Primary column: `userinterface_name` 
- Legacy column: `device_model` (kept in sync for backward compatibility)
- ✅ Clear naming: column name matches data content

## Workflow

### Save
```
Frontend → Backend → Database
userinterface_name: "horizon_android_tv"
↓
save_reference(userinterface_name="horizon_android_tv")
↓
DB: userinterface_name = "horizon_android_tv"
    device_model = "horizon_android_tv" (kept in sync)
```

### Fetch
```
Database → Backend filtering → Frontend
DB: All references
↓
Filter: ONLY refs where userinterface_name in valid_userinterfaces
↓
Frontend: Group by userinterface_name
```

### Lookup
```
Frontend: userInterface.name = "horizon_android_tv"
↓
getModelReferences("horizon_android_tv")
↓
references["horizon_android_tv"] = {...}
```

## Code Changes

### Backend
1. `shared/src/lib/supabase/verifications_references_db.py` - Updated to use `userinterface_name` parameter
2. `backend_host/src/controllers/verification/image_helpers.py` - Pass `userinterface_name` to save_reference
3. `backend_server/src/services/verification_service.py` - Filter by `userinterface_name`

### Frontend
1. `frontend/src/contexts/device/DeviceDataContext.tsx` - Group by `userinterface_name`
2. `frontend/src/components/actions/ActionItem.tsx` - Lookup by `userInterface.name`
3. `frontend/src/hooks/navigation/useNodeEdit.ts` - Lookup by `userInterface.name`

## Migration Safety
- ✅ Existing data migrated automatically
- ✅ Legacy `device_model` column kept for backward compatibility
- ✅ Both columns kept in sync during save
- ✅ Fetch uses `userinterface_name` (primary) with `device_model` fallback

## Future Cleanup
After all systems verified working:
1. Remove `device_model` column
2. Remove all `device_model` references in code
3. Keep only `userinterface_name`

