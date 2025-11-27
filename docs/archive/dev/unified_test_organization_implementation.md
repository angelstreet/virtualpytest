# Unified Test Organization System - Complete Implementation Guide

## Overview

This system provides a unified way to organize and manage both **scripts** (Python files) and **testcases** (database-stored test definitions) using folders and tags. Users can organize their tests by typing new folder/tag names or selecting existing ones - the system automatically creates them on save.

---

## 1. Database Schema

### Tables Created

#### 1.1 `folders` - Flat Folder Structure
```sql
CREATE TABLE folders (
  folder_id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Root folder (default)
INSERT INTO folders (folder_id, name) VALUES (0, '(Root)');
```

**Purpose**: Organize tests into functional categories (Navigation, Authentication, EPG, etc.)

**Key Points**:
- Flat structure (no nesting)
- `folder_id = 0` is the root folder (default)
- Unique folder names
- Auto-created when user types new folder name

---

#### 1.2 `tags` - Filtering Labels
```sql
CREATE TABLE tags (
  tag_id SERIAL PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  color VARCHAR(7) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Purpose**: Tag tests for filtering (smoke, regression, nightly, etc.)

**Key Points**:
- Unique tag names (stored lowercase)
- Color assigned from fixed Material Design palette on creation
- Auto-created when user types new tag name
- Tags are optional

**Color Palette** (12 colors):
```python
['#f44336', '#e91e63', '#9c27b0', '#673ab7', 
 '#3f51b5', '#2196f3', '#00bcd4', '#009688',
 '#4caf50', '#8bc34a', '#ff9800', '#ff5722']
```

---

#### 1.3 `executable_tags` - Unified Tag Mapping
```sql
CREATE TABLE executable_tags (
  executable_type VARCHAR(10) NOT NULL CHECK (executable_type IN ('script', 'testcase')),
  executable_id VARCHAR(255) NOT NULL,
  tag_id INTEGER NOT NULL REFERENCES tags(tag_id) ON DELETE CASCADE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  PRIMARY KEY (executable_type, executable_id, tag_id)
);
```

**Purpose**: Link tags to both scripts and testcases

**Key Points**:
- `executable_type`: 'script' or 'testcase'
- `executable_id`: For scripts: "goto.py", For testcases: UUID
- Unified table for both types

---

#### 1.4 `scripts` - Script Metadata
```sql
CREATE TABLE scripts (
  script_id SERIAL PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  display_name VARCHAR(255),
  description TEXT,
  folder_id INTEGER REFERENCES folders(folder_id) DEFAULT 0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Purpose**: Store metadata for filesystem-based Python scripts

**Key Points**:
- `name`: Script filename (e.g., "goto.py")
- Lightweight metadata only (actual code in filesystem)
- Enables unified listing with testcases

---

#### 1.5 `testcase_definitions` - Updated
```sql
ALTER TABLE testcase_definitions 
ADD COLUMN folder_id INTEGER REFERENCES folders(folder_id) DEFAULT 0;
```

**Purpose**: Add folder support to existing testcase table

**Key Points**:
- All existing testcases default to root folder (0)
- User selects/types folder when saving

---

## 2. Backend Implementation

### 2.1 Database Helpers (`shared/src/lib/database/folder_tag_db.py`)

#### `get_or_create_folder(name: str) -> int`
```python
def get_or_create_folder(name: str) -> int:
    """Get existing folder by name or create new one."""
    if not name or name == "(Root)":
        return 0
    
    # Check if exists
    folder = db.query('SELECT folder_id FROM folders WHERE name = ?', (name,))
    if folder:
        return folder['folder_id']
    
    # Create new
    result = db.insert('folders', {'name': name.strip()})
    return result['folder_id']
```

**Used by**: Testcase save endpoint when user types new folder name

---

#### `get_or_create_tag(name: str) -> dict`
```python
def get_or_create_tag(name: str) -> dict:
    """Get existing tag or create with random color."""
    name = name.strip().lower()
    
    # Check if exists
    tag = db.query('SELECT * FROM tags WHERE name = ?', (name,))
    if tag:
        return tag
    
    # Create with random color
    color = random.choice(TAG_COLORS)
    tag = db.insert('tags', {'name': name, 'color': color})
    return tag
```

**Used by**: Testcase save endpoint when user types new tag name

---

#### `set_executable_tags(type, id, tag_names)`
```python
def set_executable_tags(executable_type: str, executable_id: str, tag_names: List[str]) -> bool:
    """Set tags for script or testcase (replaces existing)."""
    # Delete existing tags
    db.delete('executable_tags', {'executable_type': type, 'executable_id': id})
    
    # Get or create tags and insert mappings
    for tag_name in tag_names:
        tag = get_or_create_tag(tag_name)
        db.insert('executable_tags', {
            'executable_type': type,
            'executable_id': id,
            'tag_id': tag['tag_id']
        })
    return True
```

**Used by**: Testcase save to link tags to testcase

---

### 2.2 API Endpoints

#### `/server/testcase/save` - Enhanced
```python
POST /server/testcase/save
Body:
{
  "testcase_name": "Login with valid credentials",
  "graph_json": {...},
  "description": "Test login flow",
  "userinterface_name": "android_tv",
  "folder": "Authentication",        # NEW: Auto-created if doesn't exist
  "tags": ["smoke", "regression"]    # NEW: Auto-created if don't exist
}

Response:
{
  "success": true,
  "testcase": {
    "testcase_id": "uuid",
    "folder_id": 2,
    "tags": [...] with colors
  }
}
```

**Flow**:
1. Extract `folder` and `tags` from request
2. Call `get_or_create_folder(folder)` → returns `folder_id`
3. For each tag, call `get_or_create_tag(tag)` → returns tag with color
4. Save testcase with `folder_id`
5. Call `set_executable_tags('testcase', testcase_id, tags)`
6. Return saved testcase

---

#### `/server/testcase/folders-tags` - New
```python
GET /server/testcase/folders-tags?team_id=xxx

Response:
{
  "success": true,
  "folders": [
    {"folder_id": 0, "name": "(Root)"},
    {"folder_id": 1, "name": "Navigation"},
    {"folder_id": 2, "name": "Authentication"}
  ],
  "tags": [
    {"tag_id": 1, "name": "smoke", "color": "#4caf50"},
    {"tag_id": 2, "name": "regression", "color": "#2196f3"}
  ]
}
```

**Purpose**: Provide options for folder/tag Autocomplete selectors

**Used by**: Frontend save dialog on mount

---

#### `/server/executable/list` - New Unified Endpoint
```python
GET /server/executable/list?team_id=xxx&folder=&tags=&search=

Response:
{
  "success": true,
  "folders": [
    {
      "id": 0,
      "name": "(Root)",
      "items": [
        {
          "type": "script",
          "id": "goto.py",
          "name": "Go To Channel",
          "tags": []
        }
      ]
    },
    {
      "id": 2,
      "name": "Authentication",
      "items": [
        {
          "type": "testcase",
          "id": "uuid",
          "name": "Login with valid credentials",
          "tags": ["smoke", "regression"],
          "userinterface": "android_tv"
        }
      ]
    }
  ],
  "all_tags": [...],
  "all_folders": ["(Root)", "Navigation", ...]
}
```

**Purpose**: Unified listing of scripts and testcases organized by folders

**Query Params**:
- `folder`: Filter by folder name
- `tags`: Comma-separated tag names (AND logic)
- `search`: Search in name/description

**Used by**: RunTests page (future implementation)

---

## 3. Frontend Implementation

### 3.1 TestCaseBuilder Save Dialog

#### Component: `TestCaseBuilderDialogs.tsx`

**New Props**:
```typescript
interface TestCaseBuilderDialogsProps {
  // ... existing props ...
  testcaseFolder?: string;
  setTestcaseFolder?: (folder: string) => void;
  testcaseTags?: string[];
  setTestcaseTags?: (tags: string[]) => void;
}
```

---

#### Folder Selector (Autocomplete with Create)
```tsx
<Autocomplete
  freeSolo  // Allows typing new values
  value={selectedFolder}
  onChange={(event, newValue) => {
    setSelectedFolder(newValue || "(Root)");
  }}
  options={availableFolders.map(f => f.name)}
  renderInput={(params) => (
    <TextField 
      {...params} 
      label="Folder" 
      helperText="Select existing or type new folder name"
    />
  )}
/>
```

**Behavior**:
- User can select from existing folders
- User can type new folder name → auto-created on save
- Default: "(Root)"

---

#### Tag Selector (Multi-Autocomplete with Create)
```tsx
<Autocomplete
  multiple
  freeSolo  // Allows typing new tags
  value={selectedTags}
  onChange={(event, newValue) => {
    setSelectedTags(newValue);
  }}
  options={availableTags.map(t => t.name)}
  renderTags={(value, getTagProps) =>
    value.map((option, index) => {
      const existingTag = availableTags.find(t => t.name === option);
      const color = existingTag?.color || '#9e9e9e';
      
      return (
        <Chip
          label={option}
          {...getTagProps({ index })}
          sx={{ 
            backgroundColor: color,
            color: 'white'
          }}
        />
      );
    })
  }
  renderInput={(params) => (
    <TextField
      {...params}
      label="Tags"
      placeholder="Select or type new tags..."
    />
  )}
/>
```

**Behavior**:
- User can select multiple existing tags
- User can type new tag names → auto-created on save
- Tags display with their assigned colors
- Existing tags show their database color
- New tags show grey until saved (then get random color)

---

### 3.2 Context Updates

#### `TestCaseBuilderContext.tsx`

**New State**:
```typescript
const [testcaseFolder, setTestcaseFolder] = useState<string>('(Root)');
const [testcaseTags, setTestcaseTags] = useState<string[]>([]);
```

**Updated Save Function**:
```typescript
const saveCurrentTestCase = useCallback(async () => {
  const result = await saveTestCase(
    testcaseName,
    graph,
    description,
    userinterfaceName,
    'default-user',
    testcaseEnvironment,
    true,  // overwrite
    testcaseFolder,  // NEW
    testcaseTags     // NEW
  );
  return result;
}, [testcaseName, description, testcaseEnvironment, testcaseFolder, testcaseTags, ...]);
```

---

### 3.3 Hook Updates

#### `useTestCaseSave.ts`

**Updated Signature**:
```typescript
const saveTestCase = useCallback(async (
  testcaseName: string,
  graphJson: TestCaseGraph,
  description: string,
  userinterfaceName: string,
  createdBy: string,
  environment: string = 'dev',
  overwrite: boolean = false,
  folder?: string,     // NEW
  tags?: string[]      // NEW
) => {
  const response = await fetch('/server/testcase/save', {
    method: 'POST',
    body: JSON.stringify({
      testcase_name: testcaseName,
      graph_json: graphJson,
      description,
      userinterface_name: userinterfaceName,
      created_by: createdBy,
      environment,
      overwrite,
      folder,  // NEW
      tags     // NEW
    })
  });
  return await response.json();
}, []);
```

---

## 4. Data Flow

### 4.1 Save Flow (User Creates Testcase)

```
1. User builds testcase in TestCaseBuilder
2. User clicks "Save" button
3. Save dialog opens and loads folders/tags:
   GET /server/testcase/folders-tags
   
4. User fills in:
   - Name: "Login with valid credentials"
   - Folder: Types "Authentication" (new folder)
   - Tags: Selects "smoke", Types "new-tag" (new tag)
   
5. User clicks Save → Frontend calls:
   POST /server/testcase/save
   {
     "testcase_name": "Login with valid credentials",
     "folder": "Authentication",
     "tags": ["smoke", "new-tag"],
     ...
   }

6. Backend processes:
   a. get_or_create_folder("Authentication") → Creates folder, returns folder_id=5
   b. get_or_create_tag("smoke") → Returns existing {tag_id: 1, color: '#4caf50'}
   c. get_or_create_tag("new-tag") → Creates tag with random color, returns {tag_id: 10, color: '#ff9800'}
   d. Saves testcase with folder_id=5
   e. Links tags: INSERT INTO executable_tags VALUES ('testcase', uuid, 1), ('testcase', uuid, 10)

7. Response returns saved testcase with tags including colors

8. Frontend shows success: "Test case saved to folder 'Authentication' with tags: smoke, new-tag"
```

---

### 4.2 List Flow (Future RunTests Implementation)

```
1. User opens RunTests page
2. Frontend calls:
   GET /server/executable/list?team_id=xxx

3. Backend:
   a. Gets all folders and tags
   b. Gets scripts from filesystem
   c. Gets testcases from database
   d. For each script: get_executable_tags('script', 'goto.py')
   e. For each testcase: get_executable_tags('testcase', uuid)
   f. Groups everything by folder
   g. Returns unified structure

4. Frontend displays:
   📁 (Root)
     🔧 goto.py
     🔧 fullzap.py
   
   📁 Authentication (8)
     🧪 Login with valid credentials [smoke] [regression]
     🧪 Login with invalid password [regression]
     ...

5. User can:
   - Search by name
   - Filter by folder
   - Filter by tags (multi-select)
   - Click to execute (script or testcase)
```

---

## 5. Key Design Decisions

### 5.1 No Auto-Organization
❌ **NOT Implemented**: Automatic folder assignment based on name patterns
✅ **Implemented**: User explicitly chooses folder (select or type)

**Reason**: User control, no surprises, explicit organization

---

### 5.2 Flat Folder Structure
❌ **NOT Implemented**: Nested folders (folders within folders)
✅ **Implemented**: Single-level flat structure

**Reason**: Simplicity, easier to navigate, no deep hierarchies

---

### 5.3 Auto-Create on Type
✅ **Implemented**: Folders and tags auto-created when user types new names

**Reason**: 
- No separate "Create Folder" UI needed
- Seamless UX (select or type)
- Database constraints ensure uniqueness

---

### 5.4 Random Tag Colors
✅ **Implemented**: Fixed palette of 12 Material Design colors, randomly assigned

**Reason**:
- Consistent, professional look
- No user decision fatigue
- Prevents color chaos
- Common practice (GitHub, Linear, Notion)

---

### 5.5 Unified Executable Concept
✅ **Implemented**: Both scripts and testcases treated as "executables"

**Backend knows the difference** (by ID pattern or table lookup)
**Frontend doesn't care** (just "something to run")

**Reason**:
- Consistent UX
- Same organization system for both
- Easy to discover all tests in one place

---

## 6. Migration Steps

### 6.1 Database
```bash
# Run on Supabase:
psql < setup/db/schema/016_folders_and_tags.sql
```

**Creates**:
- folders, tags, executable_tags, scripts tables
- Adds folder_id to testcase_definitions
- Creates root folder
- Sets up RLS policies

---

### 6.2 Testing Checklist

#### TestCaseBuilder Save Dialog
- [ ] Open TestCaseBuilder
- [ ] Click Save
- [ ] Folder selector appears with Autocomplete
- [ ] Tag selector appears with multi-select
- [ ] Type new folder name → shows in dropdown on next save
- [ ] Type new tag name → auto-created with color
- [ ] Save testcase → check database for folder_id and tags
- [ ] Load testcase → folder and tags populated

#### Backend Endpoints
- [ ] GET `/server/testcase/folders-tags` returns folders and tags
- [ ] POST `/server/testcase/save` accepts folder and tags
- [ ] GET `/server/executable/list` returns unified listing
- [ ] Filtering by folder works
- [ ] Filtering by tags works
- [ ] Search works

---

## 7. Future Enhancements

### Phase 2: RunTests Unified Selector
- Replace script dropdown with unified executable selector
- Show folders, tags, search
- Execute scripts or testcases from same UI

### Phase 3: Admin Management UI
- Manage folders (rename, delete)
- Manage tags (rename, change color, delete)
- Bulk operations (move testcases, bulk tag)

### Phase 4: Script Metadata Registration
- Populate `scripts` table with filesystem script metadata
- Allow organizing scripts into folders via UI
- Add tags to scripts

---

## 8. Technical Notes

### 8.1 Performance Considerations
- Folders/tags loaded once per dialog open (cached in component state)
- `/server/executable/list` designed for real-time filtering (no pagination yet)
- Indexes on folder_id, tag_id for fast lookups

### 8.2 Concurrency Safety
- Unique constraints on folder names and tag names prevent duplicates
- `get_or_create_*` functions are idempotent (safe to retry)
- Race conditions handled by database constraints

### 8.3 Data Integrity
- CASCADE DELETE on tags → removes executable_tags mappings
- Foreign keys ensure referential integrity
- RLS policies match existing tables

---

## 9. Files Modified

### Database
- `setup/db/schema/016_folders_and_tags.sql` - New schema
- `setup/db/schema/CURRENT_DATABASE_BACKUP.sql` - Updated backup

### Backend
- `shared/src/lib/database/folder_tag_db.py` - **NEW** Helpers
- `shared/src/lib/database/testcase_db.py` - Updated save/update functions
- `backend_server/src/routes/server_testcase_routes.py` - Updated endpoints
- `backend_server/src/routes/server_executable_routes.py` - **NEW** Unified listing
- `backend_server/src/app.py` - Registered new blueprint

### Frontend
- `frontend/src/components/testcase/builder/TestCaseBuilderDialogs.tsx` - Added selectors
- `frontend/src/contexts/testcase/TestCaseBuilderContext.tsx` - Added state
- `frontend/src/hooks/testcase/useTestCaseSave.ts` - Updated signature
- `frontend/src/hooks/pages/useTestCaseBuilderPage.ts` - Exposed new props
- `frontend/src/pages/TestCaseBuilder.tsx` - Passed props to dialog

---

## 10. Quick Reference

### User Perspective
- **Folder**: Organize tests by function (Navigation, Login, EPG)
- **Tag**: Mark tests for filtering (smoke, regression, nightly)
- **Auto-create**: Just type new names, system creates them
- **Colors**: Tags get random colors automatically

### Developer Perspective
- **Database**: 4 new tables + 1 column addition
- **Backend**: 2 new files, 4 files modified
- **Frontend**: 5 files modified
- **API**: 2 new endpoints, 1 endpoint enhanced

### Key Functions
```python
# Backend
get_or_create_folder(name) → folder_id
get_or_create_tag(name) → {tag_id, name, color}
set_executable_tags(type, id, tags) → bool
```

```typescript
// Frontend
<Autocomplete freeSolo> // Folder selector
<Autocomplete multiple freeSolo> // Tag selector
```

---

**End of Document**

