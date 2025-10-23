# AI Validation and Learning System - CONSOLIDATED Implementation Plan

## 📋 Overview

**Full functionality, minimal files**

**Problem:** AI generates navigation nodes that don't exist → execution fails

**Complete Solution:**
1. **Pre-process:** Check learned mappings before AI generation
2. **Post-process:** Validate AI plan, find suggestions
3. **User choice:** Show modal if ambiguous
4. **Learning:** Save to DB, auto-apply next time

**Files:** 3 backend + 3 frontend = 6 total files (~600 lines)

---

## 🗄️ Database Schema

Following pattern from `ai_analysis_cache_db.py`:

### Table: `ai_prompt_disambiguation`

```sql
CREATE TABLE ai_prompt_disambiguation (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  team_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
  
  -- Context
  userinterface_name VARCHAR(255) NOT NULL,
  
  -- Mapping
  user_phrase TEXT NOT NULL,           -- "live fullscreen"
  resolved_node VARCHAR(255) NOT NULL, -- "live_fullscreen"
  
  -- Learning
  usage_count INTEGER DEFAULT 1,
  last_used_at TIMESTAMP DEFAULT NOW(),
  created_at TIMESTAMP DEFAULT NOW(),
  
  -- Constraints
  UNIQUE(team_id, userinterface_name, user_phrase)
);

CREATE INDEX idx_ai_disambiguation_lookup 
  ON ai_prompt_disambiguation(team_id, userinterface_name, user_phrase);
```

**Why this name:** Follows `ai_analysis_cache` pattern, describes purpose clearly

---

## 📁 Backend Files (3 Total)

### **File 1: Database Operations**
📁 `shared/src/lib/supabase/ai_prompt_disambiguation_db.py` - **~150 lines**

Following exact pattern from `ai_analysis_cache_db.py`:

```python
"""
AI Prompt Disambiguation Database Operations

Stores learned user preferences for disambiguating ambiguous navigation prompts.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from shared.src.lib.utils.supabase_utils import get_supabase_client

def get_supabase():
    """Get the Supabase client instance."""
    return get_supabase_client()


def get_learned_mapping(team_id: str, userinterface_name: str, user_phrase: str) -> Optional[str]:
    """Get learned node mapping for a phrase."""
    supabase = get_supabase()
    
    try:
        result = supabase.table('ai_prompt_disambiguation').select('resolved_node').eq(
            'team_id', team_id
        ).eq('userinterface_name', userinterface_name).eq('user_phrase', user_phrase).execute()
        
        if result.data:
            return result.data[0]['resolved_node']
    except Exception as e:
        print(f"[@ai_prompt_disambiguation_db] Error getting mapping: {e}")
    
    return None


def get_learned_mappings_batch(team_id: str, userinterface_name: str, 
                               user_phrases: List[str]) -> Dict[str, str]:
    """Get multiple learned mappings in one query."""
    supabase = get_supabase()
    
    try:
        result = supabase.table('ai_prompt_disambiguation').select(
            'user_phrase', 'resolved_node'
        ).eq('team_id', team_id).eq('userinterface_name', userinterface_name).in_(
            'user_phrase', user_phrases
        ).execute()
        
        # Return as dict: {"live fullscreen": "live_fullscreen"}
        return {row['user_phrase']: row['resolved_node'] for row in result.data}
    except Exception as e:
        print(f"[@ai_prompt_disambiguation_db] Error getting batch mappings: {e}")
        return {}


def save_disambiguation(team_id: str, userinterface_name: str, 
                       user_phrase: str, resolved_node: str) -> Dict:
    """Save or update disambiguation mapping."""
    supabase = get_supabase()
    
    # Try to update existing
    try:
        existing = supabase.table('ai_prompt_disambiguation').select('id', 'usage_count').eq(
            'team_id', team_id
        ).eq('userinterface_name', userinterface_name).eq('user_phrase', user_phrase).execute()
        
        if existing.data:
            # Update usage count
            mapping_id = existing.data[0]['id']
            new_count = existing.data[0]['usage_count'] + 1
            
            result = supabase.table('ai_prompt_disambiguation').update({
                'resolved_node': resolved_node,
                'usage_count': new_count,
                'last_used_at': datetime.now(timezone.utc).isoformat()
            }).eq('id', mapping_id).execute()
            
            print(f"[@ai_prompt_disambiguation_db] Updated: '{user_phrase}' → '{resolved_node}' (count: {new_count})")
            return {'success': True, 'updated': True, 'usage_count': new_count}
        
        # Insert new
        result = supabase.table('ai_prompt_disambiguation').insert({
            'team_id': team_id,
            'userinterface_name': userinterface_name,
            'user_phrase': user_phrase,
            'resolved_node': resolved_node,
            'usage_count': 1,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'last_used_at': datetime.now(timezone.utc).isoformat()
        }).execute()
        
        print(f"[@ai_prompt_disambiguation_db] Created: '{user_phrase}' → '{resolved_node}'")
        return {'success': True, 'updated': False, 'usage_count': 1}
        
    except Exception as e:
        print(f"[@ai_prompt_disambiguation_db] Error saving: {e}")
        return {'success': False, 'error': str(e)}


def delete_disambiguation(team_id: str, mapping_id: str) -> bool:
    """Delete a disambiguation mapping."""
    supabase = get_supabase()
    
    try:
        result = supabase.table('ai_prompt_disambiguation').delete().eq(
            'id', mapping_id
        ).eq('team_id', team_id).execute()
        return len(result.data) > 0
    except Exception as e:
        print(f"[@ai_prompt_disambiguation_db] Error deleting: {e}")
        return False


def get_all_disambiguations(team_id: str, userinterface_name: str = None, 
                            limit: int = 100) -> List[Dict]:
    """Get all learned disambiguations for management UI."""
    supabase = get_supabase()
    
    try:
        query = supabase.table('ai_prompt_disambiguation').select('*').eq('team_id', team_id)
        
        if userinterface_name:
            query = query.eq('userinterface_name', userinterface_name)
        
        result = query.order('usage_count', desc=True).order(
            'last_used_at', desc=True
        ).limit(limit).execute()
        
        return [dict(row) for row in result.data]
    except Exception as e:
        print(f"[@ai_prompt_disambiguation_db] Error getting all: {e}")
        return []
```

**Pattern:** Same structure as `ai_analysis_cache_db.py` - clean, simple functions

---

### **File 2: Validation Logic (All-in-One)**
📁 `shared/src/lib/executors/ai_prompt_validation.py` - **~250 lines**

**Contains:** Pre-processing, post-processing, fuzzy matching - ALL validation logic

```python
"""
AI Prompt Validation and Disambiguation

Pre-processes prompts, validates AI plans, finds suggestions for invalid nodes.
Integrates with learned disambiguation database.
"""

import re
from difflib import get_close_matches
from typing import Dict, List, Optional, Tuple

from shared.src.lib.database.ai_prompt_disambiguation_db import (
    get_learned_mappings_batch,
    save_disambiguation
)


# =============================================================================
# FUZZY MATCHING UTILITIES
# =============================================================================

def find_fuzzy_matches(target: str, available_nodes: List[str], 
                      max_results: int = 3, cutoff: float = 0.4) -> List[str]:
    """Find fuzzy string matches using difflib."""
    # Try exact match first (case-insensitive)
    for node in available_nodes:
        if node.lower() == target.lower():
            return [node]
    
    # Fuzzy match
    target_lower = target.lower()
    nodes_lower = [n.lower() for n in available_nodes]
    
    matches = get_close_matches(target_lower, nodes_lower, n=max_results, cutoff=cutoff)
    
    # Return original-cased nodes
    return [n for n in available_nodes if n.lower() in matches]


def extract_potential_node_phrases(prompt: str) -> List[str]:
    """Extract phrases from prompt that could be node references."""
    # Pattern 1: Quoted strings
    quoted = re.findall(r'["\']([^"\']+)["\']', prompt)
    
    # Pattern 2: Words after "to", "navigate", "go"
    navigation_pattern = r'(?:to|navigate to|go to)\s+([a-zA-Z0-9_\s]+?)(?:\s+and|\s+then|$|,|\.|;)'
    nav_matches = re.findall(navigation_pattern, prompt.lower())
    
    # Combine and clean
    all_phrases = quoted + nav_matches
    cleaned = [p.strip() for p in all_phrases if p.strip()]
    
    # Also add single words
    words = prompt.lower().split()
    cleaned.extend(words)
    
    # Deduplicate
    return list(set(cleaned))


# =============================================================================
# PRE-PROCESSING (Before AI Generation)
# =============================================================================

def preprocess_prompt(prompt: str, available_nodes: List[str], 
                     team_id: str, userinterface_name: str) -> Dict:
    """
    Pre-process prompt: apply learned mappings and check for ambiguities.
    
    Returns:
        {
            'status': 'clear' | 'auto_corrected' | 'needs_disambiguation',
            'corrected_prompt': str (if auto_corrected),
            'corrections': [...] (if auto_corrected),
            'ambiguities': [...] (if needs_disambiguation)
        }
    """
    # Extract potential node phrases
    phrases = extract_potential_node_phrases(prompt)
    
    # Get learned mappings from DB
    learned = get_learned_mappings_batch(team_id, userinterface_name, phrases)
    
    # Track what we corrected vs what needs user input
    auto_corrections = []
    needs_disambiguation = []
    
    for phrase in phrases:
        # Skip if exact match exists
        if phrase in available_nodes:
            continue
        
        # Check learned mapping (HIGHEST PRIORITY)
        if phrase in learned:
            learned_node = learned[phrase]
            if learned_node in available_nodes:  # Validate learned mapping is still valid
                auto_corrections.append({
                    'from': phrase,
                    'to': learned_node,
                    'source': 'learned'
                })
                continue
        
        # Find fuzzy matches
        matches = find_fuzzy_matches(phrase, available_nodes, max_results=3)
        
        if len(matches) == 1:
            # Single high-confidence match → auto-correct
            auto_corrections.append({
                'from': phrase,
                'to': matches[0],
                'source': 'fuzzy'
            })
        elif len(matches) > 1:
            # Multiple matches → needs user disambiguation
            needs_disambiguation.append({
                'original': phrase,
                'suggestions': matches
            })
    
    # Determine status
    if not auto_corrections and not needs_disambiguation:
        return {'status': 'clear', 'prompt': prompt}
    
    if needs_disambiguation:
        return {
            'status': 'needs_disambiguation',
            'original_prompt': prompt,
            'ambiguities': needs_disambiguation,
            'auto_corrections': auto_corrections
        }
    
    # Auto-corrected only
    corrected_prompt = prompt
    for correction in auto_corrections:
        corrected_prompt = corrected_prompt.replace(correction['from'], correction['to'])
    
    return {
        'status': 'auto_corrected',
        'original_prompt': prompt,
        'corrected_prompt': corrected_prompt,
        'corrections': auto_corrections
    }


# =============================================================================
# POST-PROCESSING (After AI Generation)
# =============================================================================

def validate_plan(plan: Dict, available_nodes: List[str], 
                 team_id: str, userinterface_name: str) -> Dict:
    """
    Validate AI-generated plan: check nodes exist, apply learned mappings, find suggestions.
    
    Returns:
        {
            'valid': bool,
            'plan': modified_plan,
            'invalid_nodes': [{'original': str, 'suggestions': [str]}]
        }
    """
    if not plan.get('steps'):
        return {'valid': True, 'plan': plan, 'invalid_nodes': []}
    
    invalid_nodes = []
    modified = False
    
    for step in plan['steps']:
        if step.get('command') != 'execute_navigation':
            continue
        
        target = step.get('params', {}).get('target_node')
        if not target:
            continue
        
        # Check if valid
        if target in available_nodes:
            continue
        
        # Try learned mapping
        learned_node = get_learned_mapping(team_id, userinterface_name, target)
        if learned_node and learned_node in available_nodes:
            step['params']['target_node'] = learned_node
            if 'description' in step:
                step['description'] = learned_node
            modified = True
            print(f"[@ai_prompt_validation] Auto-fixed: '{target}' → '{learned_node}' (learned)")
            continue
        
        # Find suggestions
        suggestions = find_fuzzy_matches(target, available_nodes, max_results=3)
        
        if len(suggestions) == 1:
            # Single match → auto-fix
            step['params']['target_node'] = suggestions[0]
            if 'description' in step:
                step['description'] = suggestions[0]
            modified = True
            print(f"[@ai_prompt_validation] Auto-fixed: '{target}' → '{suggestions[0]}' (fuzzy)")
        else:
            # Multiple or no matches → needs user input
            invalid_nodes.append({
                'original': target,
                'suggestions': suggestions,
                'step_index': plan['steps'].index(step)
            })
    
    return {
        'valid': len(invalid_nodes) == 0,
        'plan': plan,
        'invalid_nodes': invalid_nodes,
        'modified': modified
    }


# =============================================================================
# HELPER: Apply User Selections
# =============================================================================

def apply_user_selections(plan: Dict, selections: Dict[str, str], 
                         team_id: str, userinterface_name: str, 
                         save_to_db: bool = True) -> Dict:
    """
    Apply user disambiguation selections to plan and optionally save to DB.
    
    Args:
        plan: AI plan with invalid nodes
        selections: {"original_phrase": "selected_node"}
        save_to_db: Whether to save selections for learning
    
    Returns:
        Modified plan with selections applied
    """
    for step in plan.get('steps', []):
        if step.get('command') != 'execute_navigation':
            continue
        
        target = step.get('params', {}).get('target_node')
        if target in selections:
            new_node = selections[target]
            step['params']['target_node'] = new_node
            if 'description' in step:
                step['description'] = new_node
            
            # Save to DB for learning
            if save_to_db:
                save_disambiguation(team_id, userinterface_name, target, new_node)
                print(f"[@ai_prompt_validation] Saved learning: '{target}' → '{new_node}'")
    
    return plan
```

**Why consolidated:** All validation logic in one place, easy to understand and maintain

---

### **File 3: API Routes**
📁 `backend_host/src/routes/host_ai_disambiguation_routes.py` - **~100 lines**

Following pattern from `server_ai_generation_routes.py`:

```python
"""
Host AI Disambiguation Routes

Routes for AI prompt pre-processing and disambiguation management.
"""

from flask import Blueprint, request, jsonify, current_app
from shared.src.lib.executors.ai_prompt_validation import preprocess_prompt
from shared.src.lib.database.ai_prompt_disambiguation_db import (
    save_disambiguation,
    get_all_disambiguations,
    delete_disambiguation
)

# Create blueprint
host_ai_disambiguation_bp = Blueprint('host_ai_disambiguation', __name__, 
                                     url_prefix='/host/ai-disambiguation')


@host_ai_disambiguation_bp.route('/analyzePrompt', methods=['POST'])
def analyze_prompt():
    """
    Pre-analyze prompt for ambiguities before AI generation.
    
    Request: {prompt, userinterface_name, device_id, team_id}
    Response: {status: 'clear'|'auto_corrected'|'needs_disambiguation', ...}
    """
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        userinterface_name = data.get('userinterface_name')
        device_id = data.get('device_id', 'device1')
        team_id = data.get('team_id')
        
        if not all([prompt, userinterface_name, team_id]):
            return jsonify({
                'success': False, 
                'error': 'Missing required fields'
            }), 400
        
        # Get device and navigation context
        host_devices = getattr(current_app, 'host_devices', {})
        device = host_devices.get(device_id)
        
        if not device:
            return jsonify({'success': False, 'error': f'Device {device_id} not found'}), 404
        
        # Get available nodes
        nav_context = device.navigation_executor.get_available_context(userinterface_name, team_id)
        available_nodes = nav_context.get('available_nodes', [])
        
        # Analyze prompt
        analysis = preprocess_prompt(prompt, available_nodes, team_id, userinterface_name)
        
        return jsonify({
            'success': True,
            'analysis': analysis,
            'available_nodes': available_nodes  # For manual edit mode
        })
        
    except Exception as e:
        print(f"[@host_ai_disambiguation] Error analyzing prompt: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_disambiguation_bp.route('/saveDisambiguation', methods=['POST'])
def save_disambiguation_route():
    """
    Save user disambiguation choices for learning.
    
    Request: {team_id, userinterface_name, selections: [{phrase, resolved}]}
    """
    try:
        data = request.get_json()
        team_id = data.get('team_id')
        userinterface_name = data.get('userinterface_name')
        selections = data.get('selections', [])
        
        if not all([team_id, userinterface_name]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400
        
        saved_count = 0
        for selection in selections:
            result = save_disambiguation(
                team_id,
                userinterface_name,
                selection['phrase'],
                selection['resolved']
            )
            if result.get('success'):
                saved_count += 1
        
        return jsonify({
            'success': True,
            'saved_count': saved_count
        })
        
    except Exception as e:
        print(f"[@host_ai_disambiguation] Error saving: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_disambiguation_bp.route('/getMappings', methods=['GET'])
def get_mappings():
    """Get all learned disambiguations for management UI."""
    try:
        team_id = request.args.get('team_id')
        userinterface_name = request.args.get('userinterface_name')
        
        mappings = get_all_disambiguations(team_id, userinterface_name)
        
        return jsonify({'success': True, 'mappings': mappings})
        
    except Exception as e:
        print(f"[@host_ai_disambiguation] Error getting mappings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@host_ai_disambiguation_bp.route('/deleteMapping/<mapping_id>', methods=['DELETE'])
def delete_mapping_route(mapping_id):
    """Delete a learned disambiguation."""
    try:
        team_id = request.args.get('team_id')
        success = delete_disambiguation(team_id, mapping_id)
        
        return jsonify({'success': success})
        
    except Exception as e:
        print(f"[@host_ai_disambiguation] Error deleting: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
```

**Why minimal:** Simple proxy routes, all logic in validation module

---

### **Integration: AI Executor**
📁 `shared/src/lib/executors/ai_executor.py` - **Modify existing, +30 lines**

```python
from .ai_prompt_validation import preprocess_prompt, validate_plan, apply_user_selections

def generate_plan(self, prompt: str, context: Dict, current_node_id: str = None) -> Dict:
    """Generate plan with validation pipeline"""
    available_nodes = context['available_nodes']
    team_id = context['team_id']
    userinterface_name = context['userinterface_name']
    
    # 1. PRE-PROCESS: Apply learned mappings (auto-correct if possible)
    preprocessed = preprocess_prompt(prompt, available_nodes, team_id, userinterface_name)
    
    if preprocessed['status'] == 'needs_disambiguation':
        # Return early - frontend will show modal
        return {
            'needs_disambiguation': True,
            'disambiguation_data': preprocessed,
            'feasible': False
        }
    
    # Use corrected prompt if available
    final_prompt = preprocessed.get('corrected_prompt', prompt)
    
    # 2. GENERATE: Call AI (existing code)
    cached_context = self._get_cached_context(context)
    ai_response = self._call_ai(final_prompt, cached_context)
    
    # 3. POST-PROCESS: Validate plan
    validation = validate_plan(ai_response, available_nodes, team_id, userinterface_name)
    
    if not validation['valid']:
        # Return plan with invalid nodes flagged
        ai_response['needs_disambiguation'] = True
        ai_response['invalid_nodes'] = validation['invalid_nodes']
    
    ai_response['plan'] = validation['plan']
    
    # ... rest of existing code (transform, prefetch transitions)
    return ai_response
```

---

## 📱 Frontend Files (3 Total)

### **File 1: Main Disambiguation Component**
📁 `frontend/src/components/ai/PromptDisambiguation.tsx` - **~200 lines**

**Contains:** Modal, selection UI, edit mode - ALL UI in one component

```tsx
import React, { useState } from 'react';

interface Ambiguity {
  original: string;
  suggestions: string[];
}

interface Props {
  ambiguities: Ambiguity[];
  autoCorrections?: Array<{from: string; to: string; source: string}>;
  availableNodes?: string[];
  onResolve: (selections: Record<string, string>, saveToDb: boolean) => void;
  onCancel: () => void;
}

export const PromptDisambiguation: React.FC<Props> = ({
  ambiguities,
  autoCorrections = [],
  availableNodes = [],
  onResolve,
  onCancel
}) => {
  const [mode, setMode] = useState<'select' | 'edit'>('select');
  const [selections, setSelections] = useState<Record<string, string>>({});
  const [saveToDb, setSaveToDb] = useState(true);
  const [editedSelections, setEditedSelections] = useState<string>('');

  const allSelected = ambiguities.every(a => selections[a.original]);

  const handleProceed = () => {
    if (mode === 'edit') {
      // Parse edited selections
      const parsed = parseEditedSelections(editedSelections);
      onResolve(parsed, saveToDb);
    } else {
      onResolve(selections, saveToDb);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-2xl w-full shadow-xl">
        <h3 className="text-xl font-bold mb-4">🤔 Clarify Navigation Nodes</h3>
        
        {/* Auto-corrections banner */}
        {autoCorrections.length > 0 && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded">
            <p className="text-sm font-medium text-green-900 mb-1">
              ✅ Auto-applied:
            </p>
            {autoCorrections.map((c, i) => (
              <div key={i} className="text-sm text-green-700">
                "{c.from}" → "{c.to}" 
                {c.source === 'learned' && <span className="ml-2">🎓</span>}
              </div>
            ))}
          </div>
        )}

        {mode === 'select' ? (
          <>
            {/* Selection mode */}
            <div className="space-y-4 mb-6">
              {ambiguities.map((amb, idx) => (
                <div key={idx} className="border rounded p-3">
                  <p className="text-sm font-medium mb-2">
                    What did you mean by "<span className="text-blue-600">{amb.original}</span>"?
                  </p>
                  <div className="space-y-2">
                    {amb.suggestions.map(sugg => (
                      <button
                        key={sugg}
                        onClick={() => setSelections({...selections, [amb.original]: sugg})}
                        className={`w-full text-left px-3 py-2 rounded border-2 transition ${
                          selections[amb.original] === sugg
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-blue-300'
                        }`}
                      >
                        <span className="font-mono">{sugg}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            {/* Options */}
            <div className="flex items-center gap-4 mb-4">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={saveToDb}
                  onChange={(e) => setSaveToDb(e.target.checked)}
                />
                Remember my choices
              </label>
              
              <button
                onClick={() => setMode('edit')}
                className="ml-auto text-sm text-blue-600 hover:underline"
              >
                ✏️ Edit manually
              </button>
            </div>
          </>
        ) : (
          <>
            {/* Edit mode */}
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">
                Type or select nodes:
              </label>
              <textarea
                value={editedSelections}
                onChange={(e) => setEditedSelections(e.target.value)}
                placeholder={ambiguities.map(a => `${a.original} → ?`).join('\n')}
                className="w-full border rounded p-2 font-mono min-h-[100px]"
              />
            </div>

            {/* Node chips */}
            <div className="mb-4">
              <p className="text-sm font-medium mb-2">Available nodes:</p>
              <div className="border rounded p-2 max-h-[150px] overflow-y-auto">
                <div className="flex flex-wrap gap-2">
                  {availableNodes.slice(0, 20).map(node => (
                    <button
                      key={node}
                      onClick={() => setEditedSelections(prev => prev + '\n' + node)}
                      className="px-2 py-1 bg-gray-100 hover:bg-blue-100 rounded text-sm font-mono"
                    >
                      {node}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <button
              onClick={() => setMode('select')}
              className="text-sm text-blue-600 hover:underline mb-4"
            >
              ← Back to selection
            </button>
          </>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="px-4 py-2 border rounded hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleProceed}
            disabled={mode === 'select' && !allSelected}
            className={`px-4 py-2 rounded ${
              (mode === 'edit' || allSelected)
                ? 'bg-blue-500 text-white hover:bg-blue-600'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            Proceed
          </button>
        </div>
      </div>
    </div>
  );
};

function parseEditedSelections(text: string): Record<string, string> {
  // Simple parser: "phrase → node" format
  const lines = text.split('\n').filter(l => l.trim());
  const result: Record<string, string> = {};
  
  lines.forEach(line => {
    const match = line.match(/(.+?)\s*→\s*(.+)/);
    if (match) {
      result[match[1].trim()] = match[2].trim();
    }
  });
  
  return result;
}
```

**Why one component:** Simple modal with two modes, no need for multiple components

---

### **File 2: TypeScript Types**
📁 `frontend/src/types/aiagent/AIDisambiguation_Types.ts` - **~50 lines**

```typescript
export interface Ambiguity {
  original: string;
  suggestions: string[];
  step_index?: number;
}

export interface AutoCorrection {
  from: string;
  to: string;
  source: 'learned' | 'fuzzy';
}

export interface DisambiguationData {
  status: 'needs_disambiguation';
  original_prompt: string;
  ambiguities: Ambiguity[];
  auto_corrections?: AutoCorrection[];
  available_nodes?: string[];
}

export interface LearnedMapping {
  id: string;
  user_phrase: string;
  resolved_node: string;
  usage_count: number;
  last_used_at: string;
}
```

---

### **File 3: Hook Integration**
📁 `frontend/src/hooks/useAI.ts` - **Modify existing, +80 lines**

```typescript
// Add state
const [disambiguationData, setDisambiguationData] = useState<DisambiguationData | null>(null);

// Modify executeTask
const executeTask = async (prompt, userinterface_name, useCache, skipAnalysis = false) => {
  if (isExecuting) return;

  // STEP 1: Pre-analyze (unless skipped)
  if (!skipAnalysis) {
    try {
      const analysisResponse = await fetch(buildServerUrl('/host/ai-disambiguation/analyzePrompt'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({prompt, userinterface_name, device_id: device.device_id, team_id})
      });

      const {success, analysis} = await analysisResponse.json();
      
      if (success && analysis.status === 'needs_disambiguation') {
        // PAUSE - show modal
        setDisambiguationData(analysis);
        return;
      }
      
      if (success && analysis.status === 'auto_corrected') {
        // Show toast, use corrected prompt
        toast.showInfo(`Auto-corrected: ${analysis.corrections.length} changes`, {duration: 3000});
        prompt = analysis.corrected_prompt;
      }
    } catch (err) {
      console.warn('Pre-analysis failed, proceeding anyway:', err);
    }
  }

  // STEP 2: Execute (existing code)
  const response = await fetch(buildServerUrl('/host/ai/executePrompt'), {
    method: 'POST',
    body: JSON.stringify({prompt, userinterface_name, device_id, team_id, use_cache: useCache})
  });

  const result = await response.json();
  
  // Check if AI plan has invalid nodes
  if (result.plan?.needs_disambiguation) {
    setDisambiguationData({
      status: 'needs_disambiguation',
      ambiguities: result.plan.invalid_nodes,
      available_nodes: result.available_nodes || []
    });
    return;
  }

  // Continue with execution...
};

// Handle disambiguation resolve
const handleDisambiguationResolve = async (selections: Record<string, string>, saveToDb: boolean) => {
  if (saveToDb) {
    // Save to DB
    const selectionsArray = Object.entries(selections).map(([phrase, resolved]) => ({phrase, resolved}));
    
    await fetch(buildServerUrl('/host/ai-disambiguation/saveDisambiguation'), {
      method: 'POST',
      body: JSON.stringify({team_id, userinterface_name: 'horizon_android_mobile', selections: selectionsArray})
    });
    
    toast.showSuccess(`🎓 Saved ${selectionsArray.length} preferences`);
  }
  
  // Clear modal
  setDisambiguationData(null);
  
  // Re-execute with resolved selections applied
  // (implementation depends on whether it's pre or post disambiguation)
};

return {
  // ... existing returns
  disambiguationData,
  handleDisambiguationResolve,
  handleDisambiguationCancel: () => setDisambiguationData(null)
};
```

---

### **Integration: AI Execution Panel**
📁 `frontend/src/components/ai/AIExecutionPanel.tsx` - **Modify existing, +10 lines**

```tsx
import { PromptDisambiguation } from './PromptDisambiguation';

// In render
{disambiguationData && (
  <PromptDisambiguation
    ambiguities={disambiguationData.ambiguities}
    autoCorrections={disambiguationData.auto_corrections}
    availableNodes={disambiguationData.available_nodes}
    onResolve={handleDisambiguationResolve}
    onCancel={handleDisambiguationCancel}
  />
)}
```

---

## 📊 Final Summary

### **Backend (3 files)**
1. `ai_prompt_disambiguation_db.py` - 150 lines (DB operations)
2. `ai_prompt_validation.py` - 250 lines (ALL validation logic)
3. `host_ai_disambiguation_routes.py` - 100 lines (API routes)

**Total Backend: ~500 lines**

### **Frontend (3 files)**
1. `PromptDisambiguation.tsx` - 200 lines (UI component)
2. `AIDisambiguation_Types.ts` - 50 lines (TypeScript types)
3. `useAI.ts` modifications - +80 lines (hook integration)

**Total Frontend: ~330 lines**

### **Grand Total: 6 files, ~830 lines**

### **Comparison**

| Metric | Over-Engineered | Minimal | **Consolidated** |
|--------|-----------------|---------|------------------|
| **New Files** | 15 | 3 | **6** |
| **Total Lines** | 1,600 | 410 | **830** |
| **Time** | 10 days | 2 days | **3 days** |
| **Functionality** | Full | Basic | **Full** |
| **Maintainability** | Complex | Simple | **Balanced** |

---

## ✅ Implementation Checklist

**Day 1: Backend**
- [ ] Create `ai_prompt_disambiguation` table migration
- [ ] Create `ai_prompt_disambiguation_db.py` (150 lines)
- [ ] Create `ai_prompt_validation.py` (250 lines)
- [ ] Create `host_ai_disambiguation_routes.py` (100 lines)
- [ ] Modify `ai_executor.py` (+30 lines)

**Day 2: Frontend**
- [ ] Create `AIDisambiguation_Types.ts` (50 lines)
- [ ] Create `PromptDisambiguation.tsx` (200 lines)
- [ ] Modify `useAI.ts` (+80 lines)
- [ ] Modify `AIExecutionPanel.tsx` (+10 lines)

**Day 3: Testing & Polish**
- [ ] Test pre-processing flow
- [ ] Test post-processing flow
- [ ] Test learning/saving
- [ ] Test auto-application
- [ ] Polish UI/UX

---

**This is the sweet spot: Full functionality, minimal files, following your codebase patterns! 🎯**
