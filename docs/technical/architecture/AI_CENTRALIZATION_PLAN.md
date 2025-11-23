# AI Centralization Architecture Plan - MINIMALIST

## 🎯 **Objective**
Centralize AI inference with minimal code changes. Focus on centralizing models, providers, and core inference logic while keeping prompts where they make sense.

## 📊 **Current State Analysis**

### **Current Scattered Architecture (BEFORE)**

```
virtualpytest/
├── backend_host/src/controllers/
│   ├── ai/ai_agent.py                     # ❌ Direct OpenRouter, hardcoded model
│   └── verification/video_ai_helpers.py   # ❌ Direct OpenRouter, hardcoded model
├── shared/lib/utils/
│   ├── ai_utils.py                        # ❌ Basic utils, only OpenRouter
│   ├── translation_utils.py               # ❌ Direct AI calls
│   └── browseruse_utils.py                # ❌ Different provider
└── backend_discard/src/ai_analyzer.py     # ❌ Separate implementation
```

### **Current Problems**
- ❌ **Scattered API Calls**: 5+ files making direct AI API calls
- ❌ **Hardcoded Models**: Models scattered across files
- ❌ **No Provider Choice**: Only OpenRouter, no Hugging Face
- ❌ **Duplicate Code**: Same API patterns repeated
- ❌ **No Fallback**: Limited error handling between providers

## 🏗️ **New Minimalist Architecture (AFTER)**

### **Simple File Structure - Only 3 New Files**

```
virtualpytest/
├── shared/lib/ai/                         # 🆕 ONLY 3 FILES
│   ├── __init__.py                        # 🆕 Simple exports
│   ├── ai_service.py                      # 🆕 Main service (replaces scattered calls)
│   └── prompts.py                         # 🆕 Shared prompts only
├── shared/lib/utils/
│   └── ai_utils.py                        # ✅ ENHANCED: Uses ai_service
├── backend_host/src/controllers/
│   ├── ai/ai_agent.py                     # ✅ MINIMAL CHANGE: Uses ai_service
│   └── verification/video_ai_helpers.py   # ✅ MINIMAL CHANGE: Uses ai_service
└── config/ai_config.py                    # 🆕 Simple Python config (not YAML)
```

## 🔧 **Minimalist Components**

### **1. Simple AI Service (One File)**
```python
# shared/lib/ai/ai_service.py
class AIService:
    """Simple centralized AI service - no over-engineering"""
    
    def __init__(self):
        self.providers = {
            'openrouter': self._openrouter_call,
            'huggingface': self._huggingface_call
        }
        self.default_provider = 'openrouter'
        self.fallback_provider = 'huggingface'
    
    # Main methods - same interface for all AI calls
    def call_ai(self, prompt, task_type='text', image=None, provider=None, **kwargs):
        """Single method for all AI calls"""
        
    def _openrouter_call(self, prompt, model, image=None, **kwargs):
        """OpenRouter implementation"""
        
    def _huggingface_call(self, prompt, model, image=None, **kwargs):
        """Hugging Face implementation"""
```

### **2. Simple Configuration**
```python
# config/ai_config.py
AI_CONFIG = {
    'providers': {
        'openrouter': {
            'api_key_env': 'OPENROUTER_API_KEY',
            'base_url': 'https://openrouter.ai/api/v1/chat/completions',
            'models': {
                'text': 'microsoft/phi-3-mini-128k-instruct',
                'vision': 'qwen/qwen-2.5-vl-7b-instruct',
                'translation': 'microsoft/phi-3-mini-128k-instruct'
            }
        },
        'huggingface': {
            'api_key_env': 'HUGGINGFACE_API_KEY',
            'base_url': 'https://api-inference.huggingface.co/models',
            'models': {
                'text': 'microsoft/DialoGPT-medium',
                'vision': 'Salesforce/blip-image-captioning-base',
                'translation': 'Helsinki-NLP/opus-mt-en-de'
            }
        }
    },
    'defaults': {
        'primary_provider': 'openrouter',
        'fallback_provider': 'huggingface',
        'timeout': 60,
        'max_tokens': 1000
    }
}
```

### **3. Shared Prompts (Optional)**
```python
# shared/lib/ai/prompts.py
SHARED_PROMPTS = {
    'json_response': "CRITICAL: Respond with ONLY valid JSON. No other text.",
    'language_menu': "Analyze this image for language/subtitle menu options...",
    'channel_banner': "Analyze this TV screen for channel information banner..."
}
```

## 🔄 **Simple Migration - 3 Steps Only**

### **Step 1: Create AI Service (15 minutes)**
1. Create `shared/lib/ai/ai_service.py` - one file with both providers
2. Create `config/ai_config.py` - simple Python dict
3. Create `shared/lib/ai/__init__.py` - export AIService

### **Step 2: Update Existing Files (10 minutes each)**
1. Update `ai_utils.py` - replace direct calls with AIService
2. Update `ai_agent.py` - change import, same interface
3. Update `video_ai_helpers.py` - change import, same interface
4. Update `translation_utils.py` - change import, same interface

### **Step 3: Test & Deploy (5 minutes)**
1. Test OpenRouter still works
2. Test Hugging Face fallback
3. Done!

## 🚀 **Benefits - Keep It Simple**

- ✅ **Minimal Changes**: Only change imports in existing files
- ✅ **Two Providers**: OpenRouter + Hugging Face with auto-fallback
- ✅ **Same Interface**: Existing code mostly unchanged
- ✅ **Easy Config**: Change models in one Python file
- ✅ **No Over-Engineering**: 3 files total, not 20+

## 📋 **Implementation Checklist**

- [ ] Create `shared/lib/ai/ai_service.py` (main service)
- [ ] Create `config/ai_config.py` (simple config)
- [ ] Create `shared/lib/ai/__init__.py` (exports)
- [ ] Update `ai_utils.py` to use AIService
- [ ] Update `ai_agent.py` to use AIService  
- [ ] Update `video_ai_helpers.py` to use AIService
- [ ] Test both providers work

## 🔧 **Usage Examples**

### **Before (Current)**
```python
# In ai_agent.py - Direct OpenRouter call
response = requests.post(
    'https://openrouter.ai/api/v1/chat/completions',
    headers={'Authorization': f'Bearer {api_key}'},
    json={'model': 'microsoft/phi-3-mini-128k-instruct', ...}
)
```

### **After (Minimalist)**
```python
# Same files, just change the import and one line
from shared.lib.ai import get_ai_service

ai = get_ai_service()

# Simple interface - always defaults to OpenRouter, auto-fallback to Hugging Face
result = ai.call_ai(prompt, task_type='text')           # Text generation
result = ai.call_ai(prompt, task_type='vision', image=img)  # Vision analysis
result = ai.call_ai(prompt, task_type='translation')    # Translation

# No need to specify provider - OpenRouter first, then Hugging Face fallback
```

## 🎯 **Success Metrics**

- ✅ **Minimal Code Changes**: <10 lines changed per file
- ✅ **Two Providers**: OpenRouter + Hugging Face with auto-fallback  
- ✅ **Same Interface**: Existing code works with minimal changes
- ✅ **Simple Config**: One Python file to change all models
- ✅ **No Over-Engineering**: 3 new files total

---

**TLDR: Replace scattered AI calls with one simple service. Same interface, two providers, minimal changes.**
