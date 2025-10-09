# AI Workflow Unification

## Single Unified Endpoint

**`POST /server/ai/analyzeTask`**

```python
# backend_server/src/routes/server_ai_unified_routes.py
@server_ai_unified_bp.route('/analyzeTask', methods=['POST'])
def analyze_task():
    data = request.get_json()
    results = []
    
    for iface in data['interfaces']:
        host = iface.get('host_name') or _find_host()
        
        # 1. Preprocessing
        prep = proxy_to_host('/host/ai-disambiguation/analyzePrompt', {
            'prompt': data['prompt'], 'userinterface_name': iface['name'],
            'device_id': iface.get('device_id', 'device1'), 'host_name': host
        })
        if prep['status'] == 'needs_disambiguation':
            results.append({'interface': iface['name'], 'preprocessing': prep, 'plan': None})
            continue
        
        # 2. Generate plan
        plan = proxy_to_host('/host/ai/generatePlan', {
            'prompt': data['prompt'], 'userinterface_name': iface['name'], 
            'device_id': iface.get('device_id', 'device1'), 'host_name': host
        })
        
        # 3. Execute if requested
        exec_result = None
        if data['options'].get('execute_immediately'):
            exec_result = proxy_to_host('/host/ai/executePrompt', {
                'prompt': data['prompt'], 'userinterface_name': iface['name'],
                'device_id': iface.get('device_id', 'device1'), 'host_name': host
            })
        
        # 4. Get commands
        commands = get_model_commands(iface['name'], team_id)
        
        results.append({
            'interface': iface['name'], 'preprocessing': prep, 
            'plan': plan, 'execution': exec_result, 'model_commands': commands
        })
    
    return jsonify({'success': True, 'results': results})

def _find_host():
    return list(get_host_manager().get_all_hosts().keys())[0]
```

## Frontend Updates

**REC Modal** (`useAI.ts`)
```typescript
const { results } = await fetch('/server/ai/analyzeTask', {
  body: { 
    prompt, 
    interfaces: [{ name, host_name, device_id }],
    options: { execute_immediately: true }
  }
}).then(r => r.json());

const result = results[0];
if (result.preprocessing?.status === 'needs_disambiguation') {
  setDisambiguationData(result.preprocessing);
  return;
}
pollStatus(result.execution.execution_id);
```

**Test Case** (`AITestCaseGenerator.tsx`)
```typescript
const { results } = await fetch('/server/ai/analyzeTask', {
  body: {
    prompt,
    interfaces: allInterfaces.map(i => ({ name: i.name })),
    options: { execute_immediately: false }
  }
}).then(r => r.json());

setAnalysis({ results, compatible: results.filter(r => r.plan?.feasible) });
```

## Delete Files

```bash
rm backend_server/src/routes/server_ai_testcase_routes.py
rm backend_server/src/routes/server_ai_generation_routes.py
```

## Register Blueprint

```python
# backend_server/src/app.py
from routes import server_ai_unified_routes

blueprints = [
    # ... other blueprints
    (server_ai_unified_routes.server_ai_unified_bp, 'AI unified'),
]
```
