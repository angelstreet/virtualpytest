# React StrictMode Deduplication Guide

## The Problem

React StrictMode intentionally double-invokes effects, reducers, and other functions to help detect side effects. This can cause duplicate API calls when using `useEffect` hooks that make network requests.

### Common Symptoms:
- Duplicate API requests in development mode
- Double execution of expensive operations
- Race conditions from multiple simultaneous requests
- Unnecessary server load during development

## The Simple Solution

Use `useRef` flags to track request state and prevent duplicates.

### Basic Pattern

```typescript
import { useEffect, useRef } from 'react';

const MyComponent = () => {
  const isRequestInProgress = useRef(false);
  const hasExecutedOnMount = useRef(false);

  useEffect(() => {
    // Pattern 1: Execute only once on mount
    if (!hasExecutedOnMount.current) {
      hasExecutedOnMount.current = true;
      executeOnMount();
    }
  }, []);

  useEffect(() => {
    const makeApiCall = async () => {
      // Pattern 2: Prevent duplicate requests
      if (isRequestInProgress.current) {
        console.log('Request already in progress, ignoring duplicate');
        return;
      }

      isRequestInProgress.current = true;
      
      try {
        await apiCall();
      } finally {
        isRequestInProgress.current = false;
      }
    };

    makeApiCall();
  }, [dependency]);
};
```

## Real-World Examples

### 1. Video Generation (Mount-only execution)

```typescript
// ❌ BAD: Will execute twice in StrictMode
useEffect(() => {
  executeVideoGeneration();
}, []);

// ✅ GOOD: Execute only once
const hasExecutedOnMount = useRef(false);

useEffect(() => {
  if (!hasExecutedOnMount.current) {
    hasExecutedOnMount.current = true;
    executeVideoGeneration();
  }
}, []);
```

### 2. Batch Translation (Dependency-based execution)

```typescript
// ❌ BAD: Rapid dropdown changes cause duplicate requests
useEffect(() => {
  translateContent(language);
}, [language]);

// ✅ GOOD: Prevent duplicate translation requests
const isTranslationInProgress = useRef(false);
const currentTranslationLanguage = useRef<string | null>(null);

useEffect(() => {
  const handleTranslation = async () => {
    // Skip if same request already in progress
    if (isTranslationInProgress.current && currentTranslationLanguage.current === language) {
      console.log(`Translation already in progress for ${language}, ignoring duplicate`);
      return;
    }

    isTranslationInProgress.current = true;
    currentTranslationLanguage.current = language;

    try {
      await translateContent(language);
    } finally {
      isTranslationInProgress.current = false;
      currentTranslationLanguage.current = null;
    }
  };

  handleTranslation();
}, [language]);
```

### 3. Script Analysis (Complex key-based deduplication)

```typescript
// ✅ GOOD: Handle multiple changing dependencies
const isAnalysisInProgress = useRef(false);
const currentAnalysisKey = useRef<string | null>(null);

useEffect(() => {
  const analyzeScript = async () => {
    const analysisKey = `${script}-${device}-${host}`;
    
    if (isAnalysisInProgress.current && currentAnalysisKey.current === analysisKey) {
      console.log(`Analysis already in progress for ${analysisKey}, ignoring duplicate`);
      return;
    }

    isAnalysisInProgress.current = true;
    currentAnalysisKey.current = analysisKey;

    try {
      await performAnalysis(script, device, host);
    } finally {
      isAnalysisInProgress.current = false;
      currentAnalysisKey.current = null;
    }
  };

  analyzeScript();
}, [script, device, host]);
```

## When to Use Each Pattern

### Pattern 1: Mount-only execution
- **Use for**: Initial data loading, one-time setup
- **Key**: `hasExecutedOnMount` ref
- **Dependencies**: `[]` (empty array)

### Pattern 2: Simple request deduplication  
- **Use for**: Single API calls triggered by state changes
- **Key**: `isRequestInProgress` ref
- **Dependencies**: `[singleDependency]`

### Pattern 3: Complex key-based deduplication
- **Use for**: API calls with multiple changing parameters
- **Key**: `currentRequestKey` ref to track unique combinations
- **Dependencies**: `[param1, param2, param3]`

## What NOT to Do

### ❌ Over-engineering with complex systems
```typescript
// DON'T: Create complex server-layer deduplication
// DON'T: Build global request tracking systems
// DON'T: Add 409 status code handling for duplicates
```

### ❌ Ignoring the problem
```typescript
// DON'T: Let duplicate requests happen
// DON'T: Assume it's "just development"
// DON'T: Add setTimeout delays as workarounds
```

## Benefits of This Approach

1. **Simple**: Just a few lines of code
2. **Effective**: Prevents all duplicate requests
3. **Performant**: No overhead in production
4. **Maintainable**: Easy to understand and debug
5. **Targeted**: Fixes the root cause, not symptoms

## Testing

```typescript
// Verify deduplication works:
console.log('Request started'); // Should only see once per unique request
```

## Summary

React StrictMode duplicate calls are easily solved with simple `useRef` flags. Choose the right pattern based on your use case:

- **Mount-only**: `hasExecutedOnMount` ref
- **Simple requests**: `isRequestInProgress` ref  
- **Complex requests**: `currentRequestKey` ref

Keep it simple, keep it effective! 🎯
