# Use Case AI Agent Implementation Plan

## 🎯 **Overview**
Implement AI-powered test case generation that creates, stores, and executes test cases through natural language prompts. Each test case is stored individually with clear AI/manual creator attribution.

## 📋 **Core Requirements**
- AI generates executable test cases from natural language prompts
- Single `test_cases` table with `creator` column (ai/manual)
- Integration with existing test cases page at `/test-plan/test-cases`
- AI capability caching to avoid repeated device/interface queries
- Clean implementation without fallbacks or legacy code
- Each use case stored separately for individual execution
- **Device/Userinterface Compatibility**: Test cases work across multiple device models and userinterfaces like validation.py and goto_live.py

## 🏗️ **Architecture: Server Generates, Host Executes**

### **Generation Phase: Server-Only**
- **Server** directly accesses `backend_host` for AI test case generation
- **Server** has access to AI agents, navigation trees, device capabilities
- **No proxy needed** - server handles generation locally for efficiency

### **Execution Phase: Server → Host Proxy**  
- **Server** receives execution requests and proxies to **Host**
- **Host** handles actual test execution using existing script framework
- **Host** has direct device access for real execution

### **Benefits of This Approach**
- **Fast Generation**: No network overhead for AI processing
- **Distributed Execution**: Leverage host infrastructure for device control
- **Clean Separation**: Generation logic vs execution logic clearly separated
- **Existing Patterns**: Matches your current AI agent and execution patterns

## 🗃️ **Database Schema Redesign**

### **New test_cases Table Structure**
```sql
-- Clean redesign of test_cases table
DROP TABLE IF EXISTS test_cases CASCADE;

CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    creator VARCHAR(20) NOT NULL CHECK (creator IN ('ai', 'manual')),
    
    -- AI-specific fields
    original_prompt TEXT, -- Only for AI-created test cases
    ai_analysis JSONB,    -- AI's reasoning and feasibility analysis
    
    -- Device/Interface context
    device_model VARCHAR(100) NOT NULL,
    interface_name VARCHAR(100) NOT NULL,
    
    -- Compatibility metadata for cross-device execution
    compatible_devices JSONB DEFAULT '["all"]',  -- Array of compatible device models/types or ["all"]
    compatible_userinterfaces JSONB DEFAULT '["all"]',  -- Array of compatible userinterface names or ["all"]
    device_adaptations JSONB DEFAULT '{}',  -- Device-specific adaptations (e.g., mobile->live_fullscreen)
    
    -- Test case definition
    test_steps JSONB NOT NULL, -- Array of step objects
    expected_outcomes JSONB,   -- Expected results for each step
    
    -- Execution context
    estimated_duration_ms INTEGER,
    required_capabilities TEXT[], -- ['remote', 'verification_image', 'av']
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by_user_id UUID, -- Optional: link to user who created/prompted
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'validated', 'ready', 'deprecated')),
    validation_results JSONB, -- Results from test case validation
    
    -- Execution history summary
    total_executions INTEGER DEFAULT 0,
    successful_executions INTEGER DEFAULT 0,
    last_execution_at TIMESTAMP,
    last_execution_result VARCHAR(20) -- 'success', 'failure', 'partial'
);

-- Indexes for performance
CREATE INDEX idx_test_cases_creator ON test_cases(creator);
CREATE INDEX idx_test_cases_device_interface ON test_cases(device_model, interface_name);
CREATE INDEX idx_test_cases_status ON test_cases(status);
CREATE INDEX idx_test_cases_created_at ON test_cases(created_at DESC);
```

### **AI Capability Cache Table**
```sql
-- Cache AI-learned device capabilities and patterns
CREATE TABLE ai_capability_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    device_model VARCHAR(100) NOT NULL,
    interface_name VARCHAR(100) NOT NULL,
    
    -- Cached capabilities
    available_actions JSONB NOT NULL,
    available_verifications JSONB NOT NULL,
    navigation_nodes TEXT[],
    
    -- AI learned patterns
    success_patterns JSONB, -- Common successful action sequences
    failure_patterns JSONB, -- Known failure points and solutions
    optimization_hints JSONB, -- AI-discovered optimizations
    
    -- Cache metadata
    last_updated TIMESTAMP DEFAULT NOW(),
    cache_version INTEGER DEFAULT 1,
    
    UNIQUE(device_model, interface_name)
);
```

## 🎨 **Frontend Implementation**

### **1. Enhanced Existing Test Cases Page**

**Location**: `frontend/src/pages/TestCases.tsx` (enhance existing)

**Extends existing TestCase interface** in `frontend/src/types/pages/TestCase_Types.ts`:

```typescript
// Add to existing TestCase_Types.ts
export interface TestCase {
  // ... existing fields ...
  
  // NEW: AI-specific fields
  creator?: 'ai' | 'manual';  // Add to existing interface
  original_prompt?: string;   // Only for AI-created test cases
  ai_analysis?: {
    feasibility: 'possible' | 'impossible' | 'partial';
    reasoning: string;
    required_capabilities: string[];
    estimated_steps: number;
    compatible_devices: string[];
    compatible_userinterfaces: string[];
    device_adaptations: Record<string, any>;
  };
  
  // NEW: Compatibility metadata for cross-device execution
  compatible_devices?: string[];
  compatible_userinterfaces?: string[];
  device_adaptations?: Record<string, any>;
}

// NEW: AI-specific types
export interface AITestCaseRequest {
  prompt: string;
  device_model: string;
  interface_name: string;
}

export interface CompatibilityResult {
  interface_name: string;
  compatible: boolean;
  reasoning: string;
  missing_capabilities?: string[];
  required_nodes?: string[];
  available_nodes?: string[];
}

export interface AITestCaseResponse {
  success: boolean;
  test_case?: TestCase;
  compatibility_results?: CompatibilityResult[];
  error?: string;
}
```

**Key UI Components**:
- **AI Test Generator Section**: Natural language input with real-time feasibility
- **Test Case Grid**: Displays all test cases with creator badges (AI/Manual)
- **Test Case Detail Modal**: Shows generated steps, AI analysis, execution history
- **Execution Panel**: Run individual test cases with live progress
- **AI Insights Panel**: Shows learned patterns and suggestions

### **2. AI Test Case Generation Component**

**Location**: `frontend/src/components/testcase/AITestCaseGenerator.tsx` (new)

```typescript
const AITestGenerator: React.FC = () => {
  const [prompt, setPrompt] = useState('');
  const [selectedDevice, setSelectedDevice] = useState<Device | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedTestCase, setGeneratedTestCase] = useState<TestCase | null>(null);
  const [feasibilityCheck, setFeasibilityCheck] = useState<FeasibilityResult | null>(null);

  // Real-time feasibility checking as user types
  const debouncedFeasibilityCheck = useDebounce(async (prompt: string) => {
    if (prompt.length > 10 && selectedDevice) {
      const result = await fetch('/api/ai/check-feasibility', {
        method: 'POST',
        body: JSON.stringify({
          prompt,
          deviceModel: selectedDevice.model,
          interfaceName: getUserinterfaceName(selectedDevice.model)
        })
      });
      setFeasibilityCheck(await result.json());
    }
  }, 500);

  const generateTestCase = async () => {
    setIsGenerating(true);
    try {
      const result = await fetch('/server/aitestcase/generateTestCase', {
        method: 'POST',
        body: JSON.stringify({
          prompt,
          deviceModel: selectedDevice.model,
          interfaceName: getUserinterfaceName(selectedDevice.model)
        })
      });
      
      const testCase = await result.json();
      setGeneratedTestCase(testCase);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <Card>
      <CardContent>
        <Typography variant="h6">🤖 AI Test Case Generator</Typography>
        
        {/* Device Selection */}
        <DeviceSelector 
          selectedDevice={selectedDevice}
          onDeviceChange={setSelectedDevice}
        />
        
        {/* Natural Language Input */}
        <TextField
          fullWidth
          multiline
          rows={3}
          placeholder="Describe what you want to test... (e.g., 'Go to live TV and zap 3 times, verify audio video works')"
          value={prompt}
          onChange={(e) => {
            setPrompt(e.target.value);
            debouncedFeasibilityCheck(e.target.value);
          }}
        />
        
        {/* Real-time Feasibility Indicator */}
        {feasibilityCheck && (
          <Alert severity={feasibilityCheck.feasible ? 'success' : 'warning'}>
            {feasibilityCheck.feasible ? '✅ Test case is feasible' : '⚠️ ' + feasibilityCheck.reason}
            {feasibilityCheck.suggestions && (
              <ul>
                {feasibilityCheck.suggestions.map((suggestion, i) => (
                  <li key={i}>{suggestion}</li>
                ))}
              </ul>
            )}
          </Alert>
        )}
        
        {/* Generate Button */}
        <Button 
          variant="contained" 
          onClick={generateTestCase}
          disabled={!selectedDevice || !prompt || isGenerating}
          startIcon={isGenerating ? <CircularProgress size={20} /> : <AutoAwesomeIcon />}
        >
          {isGenerating ? 'Generating...' : 'Generate Test Case'}
        </Button>
        
        {/* Generated Test Case Preview */}
        {generatedTestCase && (
          <GeneratedTestCasePreview 
            testCase={generatedTestCase}
            onSave={() => saveTestCase(generatedTestCase)}
            onExecute={() => executeTestCase(generatedTestCase)}
          />
        )}
      </CardContent>
    </Card>
  );
};
```

### **3. Test Case Management Components**

**Test Case Grid with Creator Badges**:
```typescript
const TestCaseGrid: React.FC = () => {
  return (
    <Grid container spacing={2}>
      {testCases.map(testCase => (
        <Grid item xs={12} md={6} lg={4} key={testCase.id}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <Typography variant="h6">{testCase.name}</Typography>
                <Chip 
                  label={testCase.creator === 'ai' ? '🤖 AI' : '👤 Manual'}
                  color={testCase.creator === 'ai' ? 'primary' : 'default'}
                  variant="outlined"
                />
              </Box>
              
              <Typography variant="body2" color="textSecondary">
                {testCase.description}
              </Typography>
              
              {testCase.creator === 'ai' && testCase.originalPrompt && (
                <Alert severity="info" sx={{ mt: 1 }}>
                  <strong>Original Prompt:</strong> {testCase.originalPrompt}
                </Alert>
              )}
              
              <Box mt={2} display="flex" justifyContent="space-between">
                <Chip label={`${testCase.deviceModel}`} size="small" />
                <Typography variant="caption">
                  {testCase.successfulExecutions}/{testCase.totalExecutions} successful
                </Typography>
              </Box>
              
              <Box mt={2}>
                <Button size="small" onClick={() => executeTestCase(testCase)}>
                  Execute
                </Button>
                <Button size="small" onClick={() => viewTestCase(testCase)}>
                  View Details
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};
```

## 🔧 **Backend Implementation**

### **1. Enhanced AI Agent Controller**

**Location**: `backend_host/src/controllers/ai/usecase_ai_agent.py`

```python
class UseCaseAIAgent(AIAgentController):
    """Enhanced AI Agent specialized for test case generation and management."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.capability_cache = {}
        self.success_patterns = {}
        
    async def generate_test_case(self, prompt: str, device_model: str, interface_name: str) -> Dict[str, Any]:
        """
        Generate a complete test case from natural language prompt.
        
        Args:
            prompt: Natural language description of test scenario
            device_model: Target device model
            interface_name: Target interface name
            
        Returns:
            Complete test case ready for storage and execution
        """
        try:
            print(f"AIAgent[UseCase]: Generating test case for: {prompt}")
            
            # Get cached capabilities or fetch fresh
            capabilities = await self._get_cached_capabilities(device_model, interface_name)
            
            # AI analysis and generation
            ai_result = await self._analyze_and_generate(prompt, capabilities, device_model, interface_name)
            
            if not ai_result.get('feasible'):
                return {
                    'success': False,
                    'feasible': False,
                    'reason': ai_result.get('reason'),
                    'suggestions': ai_result.get('suggestions', [])
                }
            
            # Create test case object
            test_case = {
                'name': ai_result['generated_name'],
                'description': ai_result['description'],
                'creator': 'ai',
                'original_prompt': prompt,
                'ai_analysis': ai_result['analysis'],
                'device_model': device_model,
                'interface_name': interface_name,
                'test_steps': ai_result['steps'],
                'expected_outcomes': ai_result['expected_outcomes'],
                'estimated_duration_ms': ai_result['estimated_duration'],
                'required_capabilities': ai_result['required_capabilities'],
                'status': 'ready'
            }
            
            return {
                'success': True,
                'test_case': test_case,
                'ai_confidence': ai_result.get('confidence', 0.8)
            }
            
        except Exception as e:
            print(f"AIAgent[UseCase]: Error generating test case: {e}")
            return {
                'success': False,
                'error': f'Test case generation failed: {str(e)}'
            }
    
    async def _get_cached_capabilities(self, device_model: str, interface_name: str) -> Dict[str, Any]:
        """Get device capabilities from cache or fetch fresh."""
        cache_key = f"{device_model}:{interface_name}"
        
        if cache_key in self.capability_cache:
            cached = self.capability_cache[cache_key]
            if self._is_cache_valid(cached):
                print(f"AIAgent[UseCase]: Using cached capabilities for {cache_key}")
                return cached['data']
        
        # Fetch fresh capabilities
        print(f"AIAgent[UseCase]: Fetching fresh capabilities for {cache_key}")
        capabilities = await self._fetch_device_capabilities(device_model, interface_name)
        
        # Cache the result
        self.capability_cache[cache_key] = {
            'data': capabilities,
            'timestamp': time.time(),
            'version': 1
        }
        
        # Persist to database for cross-session caching
        await self._persist_capability_cache(device_model, interface_name, capabilities)
        
        return capabilities
    
    async def _analyze_and_generate(self, prompt: str, capabilities: Dict, device_model: str, interface_name: str) -> Dict[str, Any]:
        """Core AI analysis and test case generation."""
        
        # Enhanced prompt for test case generation
        system_prompt = f"""You are an expert test case architect for device automation. 
        Generate a complete, executable test case from the user's natural language description.

        DEVICE CONTEXT:
        - Model: {device_model}
        - Interface: {interface_name}
        - Available Actions: {json.dumps(capabilities['actions'], indent=2)}
        - Available Verifications: {capabilities['verifications']}
        - Navigation Nodes: {capabilities.get('navigation_nodes', [])}

        SUCCESS PATTERNS (learned from previous executions):
        {json.dumps(self.success_patterns.get(device_model, {}), indent=2)}

        USER REQUEST: "{prompt}"

        GENERATE A COMPLETE TEST CASE with:
        1. Clear, descriptive name
        2. Detailed description
        3. Feasibility analysis
        4. Step-by-step execution plan
        5. Expected outcomes for each step
        6. Estimated execution time
        7. Required device capabilities

        CRITICAL RULES:
        - Each step must use only available actions/verifications
        - Navigation steps must use existing navigation nodes
        - Include proper wait times between actions
        - Add verification steps after critical actions
        - Generate realistic expected outcomes

        OUTPUT FORMAT: Return only valid JSON with this structure:
        {{
            "feasible": true/false,
            "reason": "explanation if not feasible",
            "generated_name": "descriptive test case name",
            "description": "what this test case validates",
            "analysis": "AI reasoning about approach chosen",
            "steps": [
                {{
                    "step": 1,
                    "type": "navigation|action|verification",
                    "command": "specific_command",
                    "params": {{}},
                    "description": "human readable description",
                    "estimated_duration_ms": 2000
                }}
            ],
            "expected_outcomes": ["outcome1", "outcome2"],
            "estimated_duration": 30000,
            "required_capabilities": ["remote", "verification_image"],
            "confidence": 0.9,
            "suggestions": ["optional improvement suggestions"]
        }}"""
        
        # Call AI API with enhanced context
        response = await self._call_ai_api(system_prompt)
        return json.loads(response)
    
    async def check_feasibility(self, prompt: str, device_model: str, interface_name: str) -> Dict[str, Any]:
        """Quick feasibility check for real-time feedback."""
        try:
            capabilities = await self._get_cached_capabilities(device_model, interface_name)
            
            # Quick AI analysis for feasibility only
            quick_prompt = f"""
            Quick feasibility check only. Can this be automated?
            Request: "{prompt}"
            Available: {list(capabilities['actions'].keys())} actions, {capabilities['verifications']} verifications
            
            Return JSON: {{"feasible": true/false, "reason": "brief explanation", "suggestions": ["alternatives"]}}
            """
            
            response = await self._call_ai_api(quick_prompt)
            result = json.loads(response)
            
            return {
                'success': True,
                'feasible': result.get('feasible', False),
                'reason': result.get('reason', ''),
                'suggestions': result.get('suggestions', [])
            }
            
        except Exception as e:
            return {
                'success': False,
                'feasible': False,
                'reason': f'Feasibility check failed: {str(e)}'
            }
```

### **2. API Routes**

**Location**: `backend_server/src/routes/server_ai_testcase_routes.py` (following your naming pattern)

```python
from flask import Blueprint, request, jsonify
from backend_host.src.controllers.ai.usecase_ai_agent import UseCaseAIAgent

ai_testcase_bp = Blueprint('ai_testcase', __name__)

@ai_testcase_bp.route('/api/ai/check-feasibility', methods=['POST'])
async def check_feasibility():
    """Real-time feasibility checking for UI feedback."""
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        device_model = data.get('deviceModel')
        interface_name = data.get('interfaceName')
        
        ai_agent = UseCaseAIAgent()
        result = await ai_agent.check_feasibility(prompt, device_model, interface_name)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'feasible': False,
            'reason': f'Feasibility check error: {str(e)}'
        }), 500

@server_aitestcase_bp.route('/generateTestCase', methods=['POST'])
def generate_test_case():
    """Generate test case directly on server - NO PROXY NEEDED for generation"""
    error = check_supabase()
    if error:
        return error
        
    try:
        print("[@route:server_aitestcase:generate_test_case] Generating test case directly on server")
        
        team_id = get_team_id()
        user_id = get_user_id()
        
        request_data = request.get_json() or {}
        prompt = request_data.get('prompt')
        device_model = request_data.get('device_model')
        interface_name = request_data.get('interface_name')
        
        # Validate required fields
        if not all([prompt, device_model, interface_name]):
            return jsonify({
                'success': False,
                'error': 'prompt, device_model, and interface_name are required'
            }), 400
        
        # SERVER CAN ACCESS BACKEND_CORE DIRECTLY - No proxy needed for generation
        from backend_host.src.controllers.ai.ai_agent import AIAgent
        from backend_host.src.controllers.controller_config_factory import get_device_capabilities
        from shared.lib.utils.navigation_cache import get_cached_unified_graph
        
        # Get device capabilities directly on server
        capabilities = get_device_capabilities(device_model)
        if not capabilities:
            return jsonify({
                'success': False,
                'error': f'No capabilities found for device model: {device_model}'
            }), 404
        
        # Get navigation context directly on server
        unified_graph = get_cached_unified_graph(interface_name, team_id)
        if not unified_graph:
            return jsonify({
                'success': False,
                'error': f'No navigation tree found for interface: {interface_name}'
            }), 404
        
        # Generate test case directly on server using AI agent
        ai_agent = AIAgent()
        generation_result = ai_agent.generate_test_case({
            'prompt': prompt,
            'device_model': device_model,
            'interface_name': interface_name,
            'capabilities': capabilities,
            'navigation_context': unified_graph,
            'team_id': team_id
        })
        
        if not generation_result.get('success'):
            return jsonify({
                'success': False,
                'error': generation_result.get('error', 'Test case generation failed')
            }), 400
        
        # Store test case in database
        test_case = generation_result['test_case']
        test_case['creator'] = 'ai'
        test_case['original_prompt'] = prompt
        save_test_case(test_case, team_id, user_id)
        
        return jsonify({
            'success': True,
            'test_case': test_case,
            'compatibility_results': generation_result.get('compatibility_results', [])
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Test case generation failed: {str(e)}'
        }), 500

@ai_testcase_bp.route('/api/test-cases', methods=['GET'])
def get_test_cases():
    """Get all test cases with creator information."""
    try:
        # Query with creator information and execution stats
        query = """
        SELECT 
            id, name, description, creator, original_prompt,
            device_model, interface_name, test_steps, status,
            created_at, total_executions, successful_executions,
            last_execution_result
        FROM test_cases 
        ORDER BY created_at DESC
        """
        
        test_cases = execute_query(query)
        
        return jsonify({
            'success': True,
            'test_cases': test_cases
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch test cases: {str(e)}'
        }), 500

@server_aitestcase_bp.route('/executeTestCase', methods=['POST'])
def execute_test_case():
    """Execute test case - PROXY TO HOST for execution"""
    error = check_supabase()
    if error:
        return error
        
    try:
        print("[@route:server_aitestcase:execute_test_case] Proxying test case execution to host")
        
        team_id = get_team_id()
        
        request_data = request.get_json() or {}
        test_case_id = request_data.get('test_case_id')
        device_id = request_data.get('device_id')
        interface_name = request_data.get('interface_name')
        
        if not all([test_case_id, device_id, interface_name]):
            return jsonify({
                'success': False,
                'error': 'test_case_id, device_id, and interface_name are required'
            }), 400
        
        # Get test case from database
        test_case = get_test_case(test_case_id, team_id)
        
        if not test_case:
            return jsonify({
                'success': False,
                'error': 'Test case not found'
            }), 404
        
        # EXECUTION REQUIRES HOST - Proxy to host for actual execution
        host_request = {
            'test_case': test_case,
            'device_id': device_id,
            'interface_name': interface_name,
            'team_id': team_id
        }
        
        response_data, status_code = proxy_to_host(
            '/host/aitestcase/executeTestCase',
            'POST',
            host_request
        )
        
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Test case execution error: {str(e)}'
        }), 500
        
        # Execute using existing script framework
        executor = TestCaseExecutor()
        result = await executor.execute_test_case(test_case)
        
        # Update execution statistics
        await update_test_case_execution_stats(test_case_id, result)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Test case execution failed: {str(e)}'
        }), 500
```

### **3. Test Case Executor**

**Location**: `backend_host/src/services/testcase_executor.py`

```python
class TestCaseExecutor:
    """Execute AI-generated test cases using existing script framework."""
    
    def __init__(self):
        self.script_executor = ScriptExecutor("testcase_executor", "AI Test Case Execution")
    
    async def execute_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a test case and return detailed results."""
        try:
            print(f"TestCaseExecutor: Executing test case: {test_case['name']}")
            
            # Setup execution context
            context = self.script_executor.setup_execution_context(
                SimpleNamespace(
                    userinterface_name=test_case['interface_name'],
                    device=self._extract_device_from_model(test_case['device_model']),
                    host=None
                ),
                enable_db_tracking=True
            )
            
            if context.error_message:
                return {
                    'success': False,
                    'error': f'Setup failed: {context.error_message}'
                }
            
            # Load navigation tree
            if not self.script_executor.load_navigation_tree(context, test_case['interface_name']):
                return {
                    'success': False,
                    'error': f'Navigation tree loading failed: {context.error_message}'
                }
            
            # Execute test steps
            step_results = []
            overall_success = True
            
            for step in test_case['test_steps']:
                step_result = await self._execute_step(context, step)
                step_results.append(step_result)
                
                if not step_result.get('success'):
                    overall_success = False
                    break  # Stop on first failure
            
            # Generate execution report
            report_result = self.script_executor.generate_final_report(context, test_case['interface_name'])
            
            return {
                'success': overall_success,
                'step_results': step_results,
                'total_steps': len(test_case['test_steps']),
                'successful_steps': len([s for s in step_results if s.get('success')]),
                'execution_time_ms': context.get_execution_time_ms(),
                'report_url': report_result.get('report_url') if report_result.get('success') else None,
                'test_case_name': test_case['name'],
                'creator': test_case['creator']
            }
            
        except Exception as e:
            print(f"TestCaseExecutor: Execution error: {e}")
            return {
                'success': False,
                'error': f'Test case execution failed: {str(e)}'
            }
        finally:
            # Always cleanup
            self.script_executor.cleanup_and_exit(context, test_case['interface_name'])
    
    async def _execute_step(self, context, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single test step."""
        try:
            step_type = step.get('type')
            command = step.get('command')
            params = step.get('params', {})
            
            print(f"TestCaseExecutor: Executing step {step['step']}: {step['description']}")
            
            if step_type == 'navigation':
                return await self._execute_navigation_step(context, command, params)
            elif step_type == 'action':
                return await self._execute_action_step(context, command, params)
            elif step_type == 'verification':
                return await self._execute_verification_step(context, command, params)
            else:
                return {
                    'success': False,
                    'error': f'Unknown step type: {step_type}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Step execution failed: {str(e)}'
            }
    
    async def _execute_navigation_step(self, context, command: str, params: Dict) -> Dict[str, Any]:
        """Execute navigation step using existing navigation system."""
        if command == 'execute_navigation':
            target_node = params.get('target_node')
            result = execute_navigation_with_verifications(
                context.host, context.selected_device, 
                {'to_node_id': target_node}, 
                context.team_id, context.tree_id
            )
            return result
        else:
            return {'success': False, 'error': f'Unknown navigation command: {command}'}
    
    async def _execute_action_step(self, context, command: str, params: Dict) -> Dict[str, Any]:
        """Execute action step using device controllers."""
        try:
            from shared.lib.utils.host_utils import get_controller
            
            controller = get_controller(context.selected_device.device_id, 'remote')
            if not controller:
                return {'success': False, 'error': 'No remote controller available'}
            
            success = controller.execute_command(command, params)
            return {
                'success': success,
                'message': f'Action {command} executed'
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Action execution failed: {str(e)}'}
    
    async def _execute_verification_step(self, context, command: str, params: Dict) -> Dict[str, Any]:
        """Execute verification step using verification controllers."""
        try:
            from shared.lib.utils.host_utils import get_controller
            
            verification_type = params.get('verification_type', 'image')
            controller = get_controller(context.selected_device.device_id, f'verification_{verification_type}')
            
            if not controller:
                return {'success': False, 'error': f'No {verification_type} verification controller available'}
            
            verification_config = {
                'command': command,
                'params': params
            }
            
            result = controller.execute_verification(verification_config)
            return result
            
        except Exception as e:
            return {'success': False, 'error': f'Verification execution failed: {str(e)}'}
```

## 📊 **Implementation Steps**

### **Phase 1: Database Foundation (Week 1)**
1. ✅ Create new `test_cases` table schema
2. ✅ Create `ai_capability_cache` table  
3. ✅ Migrate existing test case data (if any)
4. ✅ Create database indexes for performance

### **Phase 2: Backend AI Core (Week 2)**
1. ✅ Implement `UseCaseAIAgent` class
2. ✅ Add capability caching system
3. ✅ Create AI prompt templates for test generation
4. ✅ Implement feasibility checking
5. ✅ Add test case storage/retrieval

### **Phase 3: API Layer (Week 2)**
1. ✅ Create `/api/ai/check-feasibility` endpoint
2. ✅ Create `/api/ai/generate-test-case` endpoint  
3. ✅ Create `/api/test-cases` CRUD endpoints
4. ✅ Add test case execution endpoint

### **Phase 4: Frontend Implementation (Week 3)**
1. ✅ Create `AITestGenerator` component
2. ✅ Enhance existing test cases page
3. ✅ Add real-time feasibility checking
4. ✅ Implement test case preview/editing
5. ✅ Add execution progress tracking

### **Phase 5: Test Case Execution (Week 4)**  
1. ✅ Implement `TestCaseExecutor` class
2. ✅ Integration with existing script framework
3. ✅ Add execution statistics tracking
4. ✅ Generate execution reports

### **Phase 6: AI Learning & Optimization (Week 5)**
1. ✅ Implement success pattern learning
2. ✅ Add failure pattern analysis  
3. ✅ Create AI improvement suggestions
4. ✅ Optimize capability caching

## 🎯 **Success Metrics**

### **Functional Goals**
- ✅ AI generates executable test cases from natural language (>90% success rate)
- ✅ Test cases execute successfully using existing framework
- ✅ Real-time feasibility checking (<500ms response time)
- ✅ Capability caching reduces API calls (>80% cache hit rate)

### **User Experience Goals**  
- ✅ Intuitive natural language input
- ✅ Clear AI vs manual creator distinction
- ✅ Fast test case generation (<10 seconds)
- ✅ Comprehensive execution reporting

### **Technical Goals**
- ✅ Clean architecture without legacy code
- ✅ Proper database normalization
- ✅ Efficient caching strategy
- ✅ Integration with existing systems

## 🔮 **Future Enhancements**

### **AI Learning Evolution**
- Pattern recognition from execution history
- Automatic test case optimization suggestions
- Cross-device capability learning
- Smart parameter tuning

### **Advanced Features**
- Test case templates and variations  
- Bulk test case generation
- A/B testing of AI approaches
- Visual test case flow editor

### **Integration Expansion**
- CI/CD pipeline integration
- Slack/Teams notifications
- Advanced analytics dashboard
- Multi-language prompt support

---

## 📝 **Notes**
- No fallback or legacy code - clean modern implementation
- Each test case stored individually for precise tracking
- AI capability caching prevents redundant API calls
- Seamless integration with existing architecture
- Creator attribution for all test cases (AI vs manual)

This implementation plan provides a complete, production-ready system for AI-powered test case generation that integrates seamlessly with your existing VirtualPyTest architecture.
