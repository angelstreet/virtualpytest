# AI Navigation Model Generation

## 🎯 **Overview**

Automated navigation model creation using AI-driven device exploration. The system can generate 80-90% of navigation models automatically, requiring only manual setup of the Entry→Home node.

## 🏗️ **Current Model Architecture Understanding**

### **Navigation Model Components**

Based on codebase analysis:

#### **1. Navigation Trees** (`nested_navigation.md`)
- **Hierarchical structure** - up to 5 levels deep with parent-child relationships
- **Unified graph** - all trees merged for seamless cross-tree pathfinding  
- **Embedded actions** - actions stored directly in edges with bidirectional support

#### **2. Device Models** (`device_models_db.py`)
- **Controller definitions** - maps device types to available commands
- **Capability mapping** - defines what each device can do
- **Cross-device compatibility** - same interface works on multiple device types

#### **3. Navigation Components** (`useNode.ts`, `useEdge.ts`)
- **useNode** - node CRUD, screenshot capture, position tracking
- **useEdge** - action execution, bidirectional actions, validation
- **Pathfinding** - NetworkX-based optimal path finding

## 🤖 **AI Model Generation Workflow**

### **Phase 1: Manual Setup (Required)**

**User creates foundation:**
```
Entry Node → Home Node
- User takes screenshot of home screen
- Sets as entry point in navigation tree
- Defines device model and basic metadata
- AI inherits: device capabilities, screenshot system, action execution
```

### **Phase 2: AI Exploration (Automated)**

**Intelligent device exploration:**

```python
class AINavigationExplorer(AIAgentController):
    """AI-driven navigation model generation using existing infrastructure"""
    
    def explore_and_generate_model(self, home_id: str, max_nodes: int = 50) -> Dict:
        """
        Main AI exploration workflow
        
        Args:
            home_id: User-created home node to start from
            max_nodes: Maximum nodes to discover (safety limit)
            
        Returns:
            Generated navigation model with nodes, edges, and metadata
        """
        
        # Initialize exploration state
        current_position = home_id
        discovered_nodes = {home_id: {'source': 'user_created', 'verified': True}}
        exploration_queue = [home_id]
        generated_edges = []
        
        print(f"AI Explorer: Starting from home node {home_id}")
        
        # Exploration loop
        while exploration_queue and len(discovered_nodes) < max_nodes:
            current_node = exploration_queue.pop(0)
            
            print(f"AI Explorer: Exploring node {current_node}")
            
            # 1. VISUAL ANALYSIS
            screenshot_result = self.take_node_screenshot(current_node)
            screen_analysis = self.analyze_screen_with_vision_ai(screenshot_result)
            
            # 2. ACTION EXPLORATION
            for suggested_action in screen_analysis['interactive_elements']:
                try:
                    # Execute exploratory action
                    exploration_result = self.execute_exploratory_action(
                        current_node=current_node,
                        action=suggested_action
                    )
                    
                    # Analyze if significant change occurred
                    if exploration_result['screen_changed']:
                        # Create new node from analysis
                        new_node = self.create_node_from_exploration(exploration_result)
                        
                        # Create bidirectional edge
                        edge = self.create_edge_from_exploration(
                            source=current_node,
                            target=new_node['id'],
                            forward_action=suggested_action,
                            exploration_result=exploration_result
                        )
                        
                        # Add to discovery queue if new
                        if new_node['id'] not in discovered_nodes:
                            discovered_nodes[new_node['id']] = {
                                'source': 'ai_generated',
                                'parent': current_node,
                                'verified': False
                            }
                            exploration_queue.append(new_node['id'])
                        
                        generated_edges.append(edge)
                    
                    # Return to starting position for next exploration
                    self.return_to_exploration_position(current_node)
                    
                except Exception as e:
                    print(f"AI Explorer: Action exploration failed: {e}")
                    # Attempt recovery to known position
                    self.recover_to_known_position(home_id)
        
        # 3. MODEL OPTIMIZATION
        optimized_model = self.optimize_generated_model(discovered_nodes, generated_edges)
        
        return {
            'success': True,
            'discovered_nodes': len(discovered_nodes),
            'generated_edges': len(generated_edges),
            'exploration_coverage': self.calculate_coverage_metrics(discovered_nodes),
            'generated_model': optimized_model
        }
```

### **Phase 3: AI Intelligence Implementation**

#### **1. Visual Analysis with AI**

```python
def analyze_screen_with_vision_ai(self, screenshot: bytes) -> Dict:
    """
    Use vision AI to understand screen structure and interactive elements
    
    Returns:
        {
            'interactive_elements': [
                {'type': 'button', 'text': 'OK', 'action': 'press_key', 'params': {'key': 'OK'}},
                {'type': 'menu_item', 'text': 'Settings', 'action': 'click_element', 'params': {'element': 'Settings'}}
            ],
            'screen_type': 'main_menu',
            'content_areas': ['channel_list', 'info_panel'],
            'suggested_label': 'Main Menu Screen',
            'complexity_score': 0.7
        }
    """
    
    # Use existing vision AI system
    vision_prompt = f"""
    Analyze this TV interface screenshot. Identify:
    1. Interactive elements (buttons, menu items, clickable areas)
    2. Screen type (menu, content, overlay, etc.)
    3. Suggested screen label
    4. Available actions based on visible elements
    
    Available device commands: {self._get_available_actions(self.device_id)}
    
    Return JSON with interactive elements and their corresponding device commands.
    """
    
    from shared.lib.utils.ai_utils import call_vision_ai
    result = call_vision_ai(vision_prompt, screenshot)
    return json.loads(result['response'])
```

#### **2. Action Intelligence**

```python
def execute_exploratory_action(self, current_node: str, action: Dict) -> Dict:
    """
    Execute action and analyze the result for model generation
    
    Returns:
        {
            'screen_changed': True/False,
            'new_screen_analysis': {...},
            'action_executed': {...},
            'return_action': {...},
            'transition_type': 'navigation'/'action'/'overlay'
        }
    """
    
    # Take before screenshot
    before_screenshot = self.take_screenshot()
    
    # Execute the action using existing action system
    action_result = self._execute_action(action['action'], action['params'])
    
    # Wait for UI to settle
    time.sleep(2)
    
    # Take after screenshot
    after_screenshot = self.take_screenshot()
    
    # AI compares before/after to detect changes
    change_analysis = self.analyze_screen_change(before_screenshot, after_screenshot)
    
    return {
        'screen_changed': change_analysis['significant_change'],
        'change_score': change_analysis['change_score'],
        'new_screen_analysis': change_analysis['after_analysis'],
        'action_executed': action,
        'return_action': self.determine_return_action(action),
        'transition_type': change_analysis['transition_type']
    }
```

#### **3. Model Generation Intelligence**

```python
def create_node_from_exploration(self, exploration_result: Dict) -> Dict:
    """
    Create navigation node from AI exploration results
    
    Returns:
        Complete node definition ready for storage
    """
    
    screen_analysis = exploration_result['new_screen_analysis']
    
    # AI generates meaningful node data
    node_data = {
        'id': f"ai_node_{int(time.time())}_{random.randint(1000, 9999)}",
        'label': screen_analysis['suggested_label'],
        'type': self.determine_node_type(screen_analysis),
        'description': f"AI-generated: {screen_analysis['description']}",
        'screenshot': exploration_result.get('screenshot_url'),
        'data': {
            'ai_generated': True,
            'exploration_metadata': {
                'discovered_via': exploration_result['action_executed'],
                'complexity_score': screen_analysis['complexity_score'],
                'interactive_elements': screen_analysis['interactive_elements']
            }
        },
        'verifications': self.generate_appropriate_verifications(screen_analysis)
    }
    
    return node_data

def create_edge_from_exploration(self, source: str, target: str, forward_action: Dict, exploration_result: Dict) -> Dict:
    """
    Create bidirectional edge from exploration results
    
    Returns:
        Complete edge definition with forward and reverse action sets
    """
    
    return_action = exploration_result['return_action']
    
    edge_data = {
        'id': f"ai_edge_{source}_{target}",
        'source': source,
        'target': target,
        'action_sets': [
            {
                'id': 'forward',
                'actions': [forward_action],
                'retry_actions': [],
                'failure_actions': []
            },
            {
                'id': 'reverse', 
                'actions': [return_action] if return_action else [],
                'retry_actions': [],
                'failure_actions': []
            }
        ],
        'default_action_set_id': 'forward',
        'final_wait_time': 2000,
        'data': {
            'ai_generated': True,
            'exploration_confidence': exploration_result.get('confidence', 0.8)
        }
    }
    
    return edge_data
```

## 🔄 **Integration with Existing System**

### **Reuses All Proven Infrastructure:**

1. **Screenshot System** (`useNode.takeAndSaveScreenshot`)
2. **Action Execution** (`useEdge.executeEdgeActions`) 
3. **Device Capabilities** (`controller_config_factory`)
4. **Pathfinding Validation** (`navigation_pathfinding.py`)
5. **Vision AI** (`ai_utils.call_vision_ai`)

### **Benefits of Reuse:**

- ✅ **No new infrastructure** - leverages battle-tested systems
- ✅ **Consistent behavior** - same action execution as manual creation
- ✅ **Automatic validation** - pathfinding ensures connectivity
- ✅ **Quality assurance** - existing screenshot and verification systems

## 🎯 **Implementation Strategy**

### **Minimal New Code Required:**

1. **AINavigationExplorer class** - extends existing AIAgentController
2. **Vision analysis methods** - uses existing vision AI infrastructure  
3. **Exploration coordination** - orchestrates existing screenshot/action/analysis systems
4. **Model optimization** - applies AI intelligence to cleanup and organize

### **Development Phases:**

#### **Phase 1: Basic Explorer (Week 1)**
- Create AINavigationExplorer class
- Implement basic screenshot→action→analysis loop
- Test on simple menu structures

#### **Phase 2: Intelligence Layer (Week 2)**  
- Add vision AI analysis for element detection
- Implement smart return action determination
- Add screen change detection algorithms

#### **Phase 3: Model Generation (Week 3)**
- Add node and edge creation from exploration results
- Implement model optimization and cleanup
- Add subtree detection for complex menus

#### **Phase 4: Validation & Polish (Week 4)**
- Add pathfinding validation of generated models
- Implement exploration recovery mechanisms
- Add quality metrics and confidence scoring

## 🚀 **Expected Results**

### **Automation Level:**
- ✅ **90% automation** - only Entry→Home requires manual setup
- ✅ **Intelligent exploration** - AI understands UI patterns and navigation logic
- ✅ **Quality models** - generated models work with existing pathfinding system
- ✅ **Cross-device support** - models can be adapted across device types

### **Time Savings:**
- **Manual model creation**: 2-4 hours per device interface
- **AI model generation**: 10-20 minutes per device interface
- **Quality validation**: Automatic pathfinding and connectivity validation

This approach would **revolutionize navigation model creation** while building on the solid foundation of existing proven systems!
