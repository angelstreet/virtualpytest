# AI Disambiguation Architecture

## 🎯 **Clean Component Strategy**

### **Problem**
The disambiguation modal was cluttered inside `AIExecutionPanel`, making it hard to format properly with proper z-index layering.

### **Solution**
Separate the modal rendering from the execution panel using **props-based state lifting**.

---

## 📐 **Architecture Overview**

```
RecHostStreamModal (Parent)
├── AIExecutionPanel (Execution UI)
│   └── useAI() hook
│       └── Provides: disambiguationData, handlers
└── PromptDisambiguation (Modal - Sibling)
    └── Rendered at top level with proper z-index
```

---

## 🔄 **Data Flow**

### **1. PRE-PROCESSING (Before AI Generation)**

```
User types prompt
        ↓
AIExecutionPanel → useAI → executeTask()
        ↓
Frontend calls: /host/ai-disambiguation/analyzePrompt
        ↓
Backend analyzes:
  - Extracts potential node names
  - Checks learned DB mappings
  - Fuzzy matches against available nodes
        ↓
Returns one of:
  ✅ status: 'clear' → Proceed to AI
  ✅ status: 'auto_corrected' → Apply fixes, show toast, proceed
  ⚠️ status: 'needs_disambiguation' → SHOW MODAL
```

### **2. DISAMBIGUATION MODAL FLOW**

```
useAI detects disambiguationData
        ↓
Calls: onDisambiguationDataChange(data, resolve, cancel)
        ↓
RecHostStreamModal receives:
  - disambiguationData
  - resolve handler
  - cancel handler
        ↓
RecHostStreamModal renders PromptDisambiguation modal
        ↓
User selects nodes or cancels
        ↓
Modal calls resolve(selections, saveToDb) or cancel()
        ↓
Handler calls back to useAI
        ↓
If resolved: executeTask() continues
If cancelled: Execution stops
```

### **3. POST-PROCESSING (After AI Returns Plan)**

```
AI returns plan with navigation steps
        ↓
Backend validates each navigation node
        ↓
If invalid nodes found:
  - Apply fuzzy matching
  - Apply learned mappings
  - Auto-correct plan
        ↓
Return corrected plan to frontend
```

---

## 🗂️ **File Structure**

### **Frontend (3 files)**
1. **`PromptDisambiguation.tsx`** - Standalone modal component with MUI
2. **`AIExecutionPanel.tsx`** - Execution UI, hosts useAI hook, passes data to parent
3. **`AIDisambiguation_Types.ts`** - TypeScript type definitions

### **Backend (3 files)**
1. **`ai_prompt_validation.py`** - Pre/post processing logic
2. **`host_ai_disambiguation_routes.py`** - API routes
3. **`ai_prompt_disambiguation_db.py`** - Database operations

---

## 🎨 **Z-Index Layering**

```
MODAL_BACKDROP             250  ← Dark overlay
MODAL_CONTENT              260  ← General modals
SCREENSHOT_MODAL           270
AI_DISAMBIGUATION_MODAL    280  ⭐ Our modal (requires user input)
APPIUM_OVERLAY             290
ANDROID_MOBILE_OVERLAY     300
DEBUG_OVERLAY              310
```

**Key:** Disambiguation modal sits above general modals because it **blocks execution** until resolved.

---

## 💻 **Component Code Structure**

### **RecHostStreamModal.tsx (Parent)**
```tsx
const [disambiguationData, setDisambiguationData] = useState(null);
const [disambiguationResolve, setDisambiguationResolve] = useState(null);
const [disambiguationCancel, setDisambiguationCancel] = useState(null);

const handleDisambiguationDataChange = useCallback((data, resolve, cancel) => {
  setDisambiguationData(data);
  setDisambiguationResolve(() => resolve);
  setDisambiguationCancel(() => cancel);
}, []);

return (
  <>
    <AIExecutionPanel
      onDisambiguationDataChange={handleDisambiguationDataChange}
    />
    
    {/* Top-level modal with proper z-index */}
    {disambiguationData && (
      <PromptDisambiguation
        ambiguities={disambiguationData.ambiguities}
        onResolve={disambiguationResolve}
        onCancel={disambiguationCancel}
      />
    )}
  </>
);
```

### **AIExecutionPanel.tsx (Child)**
```tsx
const { disambiguationData, handleDisambiguationResolve, handleDisambiguationCancel } = useAI();

// Notify parent when disambiguation is needed
useEffect(() => {
  if (onDisambiguationDataChange) {
    onDisambiguationDataChange(
      disambiguationData,
      handleDisambiguationResolve,
      handleDisambiguationCancel
    );
  }
}, [disambiguationData]);

// Only render execution UI, no modal
```

### **PromptDisambiguation.tsx (Modal)**
```tsx
<Modal
  open
  onClose={onCancel}
  sx={{ zIndex: getZIndex('AI_DISAMBIGUATION_MODAL') }}
>
  {/* Selection UI */}
  <Button onClick={() => onResolve(selections, saveToDb)}>
    Proceed
  </Button>
</Modal>
```

---

## 🚀 **Benefits of This Architecture**

1. ✅ **Separation of Concerns**
   - AIExecutionPanel: Handles execution logic
   - PromptDisambiguation: Handles UI presentation
   - RecHostStreamModal: Orchestrates both

2. ✅ **Proper Z-Index Layering**
   - Modal renders at top level, above all other content
   - No CSS conflicts or overflow issues

3. ✅ **Clean Component Hierarchy**
   - Modal is a sibling, not nested inside panel
   - Easier to style and maintain

4. ✅ **Reusable Components**
   - PromptDisambiguation can be used anywhere
   - Not tightly coupled to AIExecutionPanel

5. ✅ **Type Safety**
   - TypeScript interfaces ensure correct data flow
   - Handler signatures prevent runtime errors

---

## 🔧 **Testing the Flow**

1. **Open RecHostStreamModal**
2. **Enable AI Agent mode**
3. **Enter ambiguous prompt:** "go to live fullscreen"
4. **Observe:**
   - Pre-analysis happens automatically
   - Modal appears at top level (properly layered)
   - Can select nodes or edit manually
   - "Remember choices" saves to database
5. **Next time:** Same prompt auto-corrects (no modal)

---

## 📊 **Database Learning**

```sql
ai_prompt_disambiguation
├── team_id
├── userinterface_name
├── user_phrase       "live fullscreen"
├── resolved_node     "live_fullscreen"
├── usage_count       (increments on reuse)
└── last_used_at      (tracks freshness)
```

**Smart auto-correction:**
- First time: User disambiguates manually
- Subsequent times: System auto-applies learned mapping
- High usage_count = higher confidence in mapping

---

## 🎯 **Summary**

**OLD:**
```
AIExecutionPanel
  └── PromptDisambiguation (nested, z-index issues)
```

**NEW:**
```
RecHostStreamModal
  ├── AIExecutionPanel (execution logic only)
  └── PromptDisambiguation (top-level modal, proper z-index)
```

**Result:** Clean separation, proper layering, maintainable code! 🎉
