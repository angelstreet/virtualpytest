# VirtualPyTest Database Setup

Complete database schema for VirtualPyTest Supabase database.

## 📁 Structure

```
setup/db/
├── schema/                    # SQL schema files
│   ├── 001_core_tables.sql           # Core tables (devices, controllers, campaigns)
│   ├── 002_ui_navigation_tables.sql  # UI and navigation trees  
│   ├── 003_test_execution_tables.sql # Test cases and results
│   ├── 004_actions_verifications.sql # Actions and verifications
│   └── 005_monitoring_analytics.sql  # Alerts and metrics
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

## ✅ Verification

After running all 5 schema files, verify your setup:

1. Go to **Database** → **Tables** in your Supabase dashboard
2. You should see **20+ tables** created
3. All tables should have the correct relationships and indexes

### Expected Tables:

**Core Tables:**
- `device_models`, `device`, `controllers`, `environment_profiles`, `campaigns`

**UI & Navigation:**
- `userinterfaces`, `navigation_trees`, `navigation_nodes`, `navigation_edges`, `navigation_trees_history`

**Test Execution:**
- `test_cases`, `test_executions`, `test_results`, `execution_results`, `script_results`

**Actions & Verifications:**
- `actions`, `verifications`, `verifications_references`

**Monitoring & Analytics:**
- `alerts`, `heatmaps`, `node_metrics`, `edge_metrics`

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
- **Monitoring**: Performance metrics, alerts, and analytics
- **Verification**: Reference data for automated testing

All tables include proper indexes, foreign key relationships, and are designed for high performance and scalability. 