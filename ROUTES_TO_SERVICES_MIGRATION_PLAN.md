# Routes to Services Migration Plan

## 🎯 Goal
Move business logic from routes to services **without breaking any code or logic** - just reorganizing for better architecture.

## 📊 Route Categories

### ✅ **ALREADY HANDLED**
- **Pure Proxy Routes** → Moved to `auto_proxy.py` (73 routes)
- **server_verification_routes.py** → Already migrated to `verification_service.py`

### 🔄 **ROUTES WITH DATABASE LOGIC** (High Priority - Move to Services)

#### 1. **Navigation & Trees** (Complex DB Operations)
- **`server_navigation_trees_routes.py`** (27 routes)
  - **Logic**: Complex Supabase operations (trees, nodes, edges)
  - **Service**: `navigation_service.py`
  - **Functions to Move**: All CRUD operations for trees/nodes/edges

- **`server_navigation_routes.py`** (3 routes) 
  - **Logic**: Navigation path operations
  - **Service**: `navigation_service.py`

#### 2. **Campaign Management** (Business Logic)
- **`server_campaign_routes.py`** (5 routes)
  - **Logic**: Campaign CRUD, execution logic
  - **Service**: `campaign_service.py`

- **`server_campaign_execution_routes.py`** (6 routes)
  - **Logic**: Async campaign execution, task management
  - **Service**: `campaign_execution_service.py`

- **`server_campaign_results_routes.py`** (1 route)
  - **Logic**: Results aggregation
  - **Service**: `campaign_service.py`

#### 3. **AI & Test Cases** (Complex Logic)
- **`server_ai_testcase_routes.py`** (5 routes)
  - **Logic**: AI test generation, compatibility analysis
  - **Service**: `ai_testcase_service.py`

- **`server_ai_generation_routes.py`** (6 routes)
  - **Logic**: AI interface generation, tree exploration
  - **Service**: `ai_generation_service.py`

#### 4. **Device & System Management** (DB Operations)
- **`server_device_routes.py`** (5 routes)
  - **Logic**: Device CRUD operations
  - **Service**: `device_service.py`

- **`server_devicemodel_routes.py`** (5 routes)
  - **Logic**: Device model management
  - **Service**: `device_service.py`

- **`server_system_routes.py`** (5 routes)
  - **Logic**: System configuration, health checks
  - **Service**: `system_service.py`

#### 5. **Scripts & Execution** (File Operations)
- **`server_script_routes.py`** (5 routes)
  - **Logic**: Script file management, execution
  - **Service**: `script_service.py`

- **`server_script_results_routes.py`** (3 routes)
  - **Logic**: Script results processing
  - **Service**: `script_service.py`

#### 6. **User Interface Management** (DB Operations)
- **`server_userinterface_routes.py`** (6 routes)
  - **Logic**: UI configuration management
  - **Service**: `userinterface_service.py`

#### 7. **Test Cases & Validation** (Complex Logic)
- **`server_testcase_routes.py`** (6 routes)
  - **Logic**: Test case CRUD, validation
  - **Service**: `testcase_service.py`

- **`server_validation_routes.py`** (1 route)
  - **Logic**: Complex validation with cache management
  - **Service**: `validation_service.py`

#### 8. **Monitoring & Metrics** (Data Processing)
- **`server_metrics_routes.py`** (6 routes)
  - **Logic**: Metrics aggregation, calculations
  - **Service**: `metrics_service.py`

- **`server_heatmap_routes.py`** (5 routes)
  - **Logic**: Complex async data processing, image analysis
  - **Service**: `heatmap_service.py`

#### 9. **Alerts & Results** (DB Operations)
- **`server_alerts_routes.py`** (5 routes)
  - **Logic**: Alert management, notifications
  - **Service**: `alerts_service.py`

- **`server_execution_results_routes.py`** (1 route)
  - **Logic**: Results aggregation
  - **Service**: `execution_service.py`

### 🔄 **ROUTES WITH TASK/ASYNC LOGIC** (Medium Priority)

#### 10. **Web Automation** (Task Management)
- **`server_web_routes.py`** (7 routes)
  - **Logic**: Async task management, threading
  - **Service**: `web_automation_service.py`

#### 11. **AI Queue Management** (Queue Logic)
- **`server_ai_queue_routes.py`** (2 routes)
  - **Logic**: Queue monitoring, task management
  - **Service**: `ai_queue_service.py`

### 🔄 **ROUTES WITH BUSINESS LOGIC** (Lower Priority)

#### 12. **Stream Proxy** (Custom Logic)
- **`server_stream_proxy_routes.py`** (3 routes)
  - **Logic**: Host selection, URL building
  - **Service**: `stream_service.py`

#### 13. **API Testing** (Test Logic)
- **`server_api_testing_routes.py`** (5 routes)
  - **Logic**: API test execution, validation
  - **Service**: `api_testing_service.py`

#### 14. **Control Operations** (System Logic)
- **`server_control_routes.py`** (7 routes)
  - **Logic**: System control operations
  - **Service**: `control_service.py`

### ✅ **KEEP AS ROUTES** (Minimal Logic)
- **`server_core_routes.py`** - Basic health checks
- **`server_frontend_routes.py`** - Simple frontend serving
- **`auto_proxy.py`** - Pure HTTP handling

## 📋 **Migration Priority**

### **Phase 1: High Impact Database Routes**
1. `server_navigation_trees_routes.py` → `navigation_service.py`
2. `server_campaign_routes.py` → `campaign_service.py`
3. `server_ai_testcase_routes.py` → `ai_testcase_service.py`
4. `server_device_routes.py` → `device_service.py`

### **Phase 2: Complex Logic Routes**
5. `server_heatmap_routes.py` → `heatmap_service.py`
6. `server_validation_routes.py` → `validation_service.py`
7. `server_web_routes.py` → `web_automation_service.py`

### **Phase 3: Remaining Routes**
8. All other routes with business logic

## 🔧 **Migration Process**

For each route file:

1. **Create Service File**
   ```python
   # services/navigation_service.py
   class NavigationService:
       def get_all_trees(self, team_id):
           # Move exact logic from route
   ```

2. **Update Route to Use Service**
   ```python
   # routes/server_navigation_trees_routes.py
   @bp.route('/trees', methods=['GET'])
   def get_trees():
       from services.navigation_service import navigation_service
       result = navigation_service.get_all_trees(team_id)
       return jsonify(result)
   ```

3. **Test - Same API, Same Behavior**

## 📊 **Expected Results**

- **Before**: Business logic scattered across 20+ route files
- **After**: Clean separation - routes handle HTTP, services handle logic
- **Benefits**: Better testability, reusability, maintainability
- **Risk**: Zero (just moving functions, no logic changes)

**Total Routes to Migrate: ~100 routes across 20 files**
