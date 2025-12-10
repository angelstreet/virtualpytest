# SIMPLE RESULT ANALYSIS SYSTEM

## 🎯 CORE OBJECTIVE
Create a **self-contained, simple system** that can verify if script execution results are reliable using **ONLY available data** (execution.txt and report.html).

## 🆕 UPDATED SKILL NAMES
- `validate` - Core validation skill (was: ultra-simple-validation)
- `analyze` - Failure analysis skill (was: ultra-simple-failure-analysis)

**Why shorter names?**
- ✅ Easier to remember and use
- ✅ Cleaner configuration
- ✅ More intuitive for CLI usage
- ✅ Follows verb-noun pattern

## 🚀 KEY PRINCIPLES

1. **SELF-CONTAINED**: Use only execution.txt and report.html - no test case loading
2. **SIMPLE RULES**: Easy-to-understand validation logic
3. **BINARY DECISIONS**: RELIABLE or UNRELIABLE
4. **CLEAR CLASSIFICATION**: BUG, SCRIPT_ISSUE, SYSTEM_ISSUE, or UNKNOWN
5. **EVIDENCE-BASED**: Provide clear reasoning from available data

## 🔍 VALIDATION RULES

### For ALL Results (PASS or FAIL)

#### ✅ INITIAL STATE CHECK
```
- Look at initial screenshot description in execution.txt
- Check for keywords: "black screen", "no signal", "error", "disconnected"
- Verify device appears normal and responsive
- If any issues found → UNRELIABLE
```

#### ✅ FINAL STATE CHECK
```
- Look at final screenshot description in execution.txt  
- Check for keywords: "black screen", "no signal", "error", "frozen"
- Verify device appears normal and responsive
- If any issues found → UNRELIABLE
```

### For PASS Results

#### ✅ RESULT COHERENCE CHECK
```
- Verify final state matches expected test outcome (from execution.txt)
- Check no error messages or warnings visible in final screenshot
- Confirm device state looks correct for test goal
- If inconsistent → UNRELIABLE_PASS
```

### For FAIL Results

#### ✅ FAILURE ANALYSIS
```
- Look at final screenshot: What does it actually show?
- Check execution.txt: Where exactly did it fail?
- Compare with previous steps: What changed?
- Apply simple classification rules
```

## 🤖 DECISION LOGIC

### PASS Results
```
IF (initial_state_ok AND final_state_ok AND result_coherent)
    → RELIABLE_PASS (can trust this result)
ELSE
    → UNRELIABLE_PASS (needs manual review)
```

### FAIL Results
```
IF (initial_state_ok AND final_state_ok)
    → Apply failure classification rules
ELSE
    → UNRELIABLE_FAILURE (missing critical data)
```

## 🎯 FAILURE CLASSIFICATION (Simple Rules)

### Using ONLY data from execution.txt and report.html:

#### 🔍 STEP 1: Examine Final Screenshot
```
- What elements are visible?
- Any error messages displayed?
- Device state: normal/black/frozen/error?
```

#### 🔍 STEP 2: Find Failure Details
```
- Which step failed? (from execution.txt)
- What error message? (exact text)
- What was expected vs actual?
```

#### 🔍 STEP 3: Check Previous Steps
```
- What actions were performed before failure?
- What was the execution sequence?
- Any patterns or clues about what went wrong?
```

#### ✅ STEP 4: Apply Simple Classification

**RULE 1: BUG (Real Device Issue)**
```
IF (screenshot shows element BUT error says "not found")
    → CLASSIFICATION: BUG
    → REASONING: "Element visible in screenshot but test reports not found"
    → CONFIDENCE: HIGH
```

**RULE 2: SCRIPT_ISSUE (Test Problem)**
```
IF (error mentions selector/timing/expected value/wait)
    → CLASSIFICATION: SCRIPT_ISSUE
    → REASONING: "Test implementation issue - selector, timing, or expectation problem"
    → CONFIDENCE: MEDIUM
```

**RULE 3: SYSTEM_ISSUE (Infrastructure Problem)**
```
IF (screenshot shows black screen/no signal/device disconnected)
    → CLASSIFICATION: SYSTEM_ISSUE
    → REASONING: "Device or connection problem - black screen, no signal, or disconnect"
    → CONFIDENCE: HIGH
```

**RULE 4: UNKNOWN (Need More Data)**
```
IF (unclear from available data OR conflicting evidence)
    → CLASSIFICATION: UNKNOWN
    → REASONING: "Cannot determine from available data - needs manual review"
    → CONFIDENCE: LOW
```

## 📋 OUTPUT FORMAT

### For RELIABLE Results
```yaml
analysis_result:
  status: RELIABLE
  confidence: HIGH
  validation:
    initial_state: OK
    final_state: OK
    result_coherence: OK
  evidence:
    - Initial screenshot: [description from execution.txt]
    - Final screenshot: [description from execution.txt]
    - Execution flow: [summary from execution.txt]
  recommendation: TRUST_RESULT
```

### For UNRELIABLE Results
```yaml
analysis_result:
  status: UNRELIABLE
  confidence: MEDIUM|LOW
  classification: BUG|SCRIPT_ISSUE|SYSTEM_ISSUE|UNKNOWN
  validation:
    initial_state: OK|FAIL
    final_state: OK|FAIL
    result_coherence: OK|FAIL|N/A
  evidence:
    - Final screenshot shows: [description]
    - Error message: [exact text]
    - Failed step: [step name]
    - Previous actions: [summary]
  reasoning: [detailed reasoning using simple rules]
  recommendation: REVIEW_MANUALLY|DISCARD_RESULT
```

## 🛠️ IMPLEMENTATION PLAN

### Phase 1: Core Validation Skill
```yaml
name: validate
version: 1.0.0
description: Self-contained result validation using only available data

system_prompt: |
  ULTRA SIMPLE VALIDATION - Use ONLY execution.txt and report.html
  
  CHECKLIST:
  1. Initial state OK? (no black screen, no signal issues, device responsive)
  2. Final state OK? (no black screen, no errors, device responsive)
  3. For PASS: Result coherent? (final state matches test goal)
  
  DECISION:
  - All checks OK → RELIABLE
  - Any check fails → UNRELIABLE

tools:
  - read_execution_logs
  - parse_report_data
  - check_screenshot_descriptions
```

### Phase 2: Simple Failure Analyzer
```yaml
name: analyze
version: 1.0.0
description: Self-contained failure analysis using simple rules

system_prompt: |
  ULTRA SIMPLE FAILURE ANALYSIS - Use ONLY available data
  
  SIMPLE RULES:
  1. If element visible but "not found" error → BUG
  2. If selector/timing/expectation error → SCRIPT_ISSUE
  3. If black screen/no signal → SYSTEM_ISSUE
  4. If unclear → UNKNOWN
  
  Always provide clear evidence and reasoning!

tools:
  - read_execution_logs
  - parse_report_data
  - extract_screenshot_info
  - find_failure_details
```

### Phase 3: Update Analyzer Configuration
```yaml
# In analyzer.yaml
available_skills:
  - validate
  - analyze
  - generate-simple-report
```

## 🎯 KEY BENEFITS

✅ **Self-contained** - Uses only data we actually have
✅ **Simple rules** - Easy to understand and maintain
✅ **Clear decisions** - Binary reliable/unreliable output
✅ **Actionable** - Clear recommendations (TRUST/REVIEW/DISCARD)
✅ **No dependencies** - Doesn't require test case loading
✅ **Fast to implement** - Can be built and tested quickly
✅ **Easy to enhance** - Simple foundation for future improvements
✅ **Short names** - `validate` and `analyze` are clean and intuitive

## 🧪 TESTING APPROACH

1. **Test with real execution.txt files**
2. **Verify simple rules work correctly**
3. **Check output format is clear**
4. **Validate classification accuracy**
5. **Ensure self-contained operation**

## 📈 FUTURE ENHANCEMENTS

- Add more sophisticated screenshot analysis
- Include timing analysis
- Add historical data comparison
- Implement confidence scoring
- Add automated learning from manual reviews

## 🎯 FINAL SUMMARY

**What we've created**:
- `validate` skill: Simple binary reliability check
- `analyze` skill: Detailed failure classification  
- Clean, short names that are easy to use
- Self-contained system using only available data
- Simple rules anyone can understand

**Files created**:
- `validate.yaml` - Core validation skill
- `analyze.yaml` - Failure analysis skill
- Updated `analyzer.yaml` with new skills
- Comprehensive documentation

This simple system provides a **working, reliable foundation** that solves the core problem: preventing unreliable results from being trusted, using only the data we actually have available.