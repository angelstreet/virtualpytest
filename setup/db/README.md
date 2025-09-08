# VirtualPyTest Database Setup

Complete database schema for VirtualPyTest Supabase database.

## 📁 Structure

```
setup/db/
├── schema/                    # SQL schema files
│   ├── 001_core_tables.sql           # Core tables (devices, campaigns, AI cache, zap results)
│   ├── 002_ui_navigation_tables.sql  # UI and navigation trees with nested support
│   ├── 003_test_execution_tables.sql # Test cases and results with AI features
│   ├── 004_actions_verifications.sql # Verification references
│   ├── 005_monitoring_analytics.sql  # Alerts and metrics (simplified)
│   ├── (system_metrics table created via MCP) # System monitoring metrics (CREATED)
│   ├── 007_parent_node_sync_triggers.sql # Parent node sync triggers
│   ├── auto_sync_nested_node.md      # Documentation for nested node sync
│   └── CURRENT_DATABASE_BACKUP.sql   # Complete backup of current schema
└── README.md                  # This file
```

## 🚀 Quick Setup

### 1. Go to Supabase SQL Editor

1. Open your [Supabase Dashboard](https://app.supabase.com)
2. Select your project → **SQL Editor**
3. Click **New Query**

### 2. Execute Schema Files in Order

Copy and paste the contents of each SQL file **in order** and execute them:

#### Step 1: Core Tables
Copy and paste the entire contents of `001_core_tables.sql` and run it.

#### Step 2: UI & Navigation Tables  
Copy and paste the entire contents of `002_ui_navigation_tables.sql` and run it.

#### Step 3: Test Execution Tables
Copy and paste the entire contents of `003_test_execution_tables.sql` and run it.

#### Step 4: Actions & Verifications
Copy and paste the entire contents of `004_actions_verifications.sql` and run it.

#### Step 5: Monitoring & Analytics
Copy and paste the entire contents of `005_monitoring_analytics.sql` and run it.

#### Step 6: System Metrics (ALREADY CREATED)
✅ The `system_metrics` table has been automatically created via MCP Supabase server.

#### Step 7: Parent Node Sync Triggers
Copy and paste the entire contents of `007_parent_node_sync_triggers.sql` and run it.

## ✅ Verification

After running all 7 schema files, verify your setup:

1. Go to **Database** → **Tables** in your Supabase dashboard
2. You should see **23+ tables** created
3. All tables should have the correct relationships and indexes

### Expected Tables:

**Core Tables:**
- `teams`, `device_models`, `device`, `environment_profiles`, `campaign_executions`, `ai_analysis_cache`, `zap_results`

**UI & Navigation:**
- `userinterfaces`, `navigation_trees`, `navigation_nodes`, `navigation_edges`, `navigation_trees_history`

**Test Execution:**
- `test_cases`, `test_executions`, `test_results`, `execution_results`, `script_results`

**Verifications:**
- `verifications_references`

**Monitoring & Analytics:**
- `alerts`, `heatmaps`, `node_metrics`, `edge_metrics`, `system_metrics`

### Key Features:
- ✅ **Nested Navigation Trees**: Support for multi-level navigation with automatic parent-child sync
- ✅ **Bidirectional Edges**: Action sets for forward/reverse navigation paths
- ✅ **AI Test Generation**: AI analysis cache and test case generation support
- ✅ **Zap Results**: Detailed media analysis and monitoring data
- ✅ **System Monitoring**: Real-time host and server performance metrics
- ✅ **Automatic Triggers**: Parent node sync and edge label management

## 🛠️ Application Configuration

After database setup, update your application `.env` files with your Supabase credentials:

```bash
# Frontend: frontend/.env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key

# Backend: backend_server/.env, backend_host/.env  
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

## 📊 Schema Overview

The VirtualPyTest database schema supports:

- **Device Management**: Physical devices and their models
- **Test Automation**: Controllers and execution engines  
- **UI Testing**: Navigation trees and interface definitions
- **Test Execution**: Test cases, results, and campaign management
- **Monitoring**: Performance metrics, alerts, analytics, and system monitoring
- **Verification**: Reference data for automated testing

All tables include proper indexes, foreign key relationships, and are designed for high performance and scalability. 