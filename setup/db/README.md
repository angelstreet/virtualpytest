# VirtualPyTest Database Setup

Complete database schema and setup scripts for VirtualPyTest Supabase database.

## 📁 Structure

```
setup/db/
├── schema/                    # SQL schema files
│   ├── 001_core_tables.sql           # Core tables (devices, controllers, campaigns)
│   ├── 002_ui_navigation_tables.sql  # UI and navigation trees
│   ├── 003_test_execution_tables.sql # Test cases and results
│   ├── 004_actions_verifications.sql # Actions and verifications
│   └── 005_monitoring_analytics.sql  # Alerts and metrics
├── scripts/                   # Setup scripts
│   └── install_supabase_schema.sh    # Complete schema installation
└── README.md                  # This file
```

## 🚀 Quick Setup

### 1. Prerequisites

- Supabase project created
- PostgreSQL client (`psql`) installed

### 2. Get Supabase Credentials

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project → Settings → API
3. Copy your Project URL and service_role key

### 3. Install Database Schema

```bash
# Set environment variables
export SUPABASE_URL='https://your-project.supabase.co'
export SUPABASE_SERVICE_ROLE_KEY='your-service-role-key'

# Run installation script
./setup/db/scripts/install_supabase_schema.sh
```

## 📊 Database Tables

The schema creates **20+ tables** organized in 5 categories:

### Core Tables
- `device_models` - Device model definitions
- `device` - Physical device instances  
- `controllers` - Device controller configs
- `environment_profiles` - Test environments
- `campaigns` - Test campaigns

### UI & Navigation
- `userinterfaces` - UI definitions
- `navigation_trees` - Navigation structures
- `navigation_trees_history` - Version history

### Test Execution
- `test_cases` - Test definitions
- `test_executions` - Execution tracking
- `test_results` - Test outcomes
- `execution_results` - Detailed results
- `script_results` - Script execution logs

### Actions & Verifications
- `actions` - Test actions/commands
- `verifications` - Verification rules
- `verifications_references` - Reference data

### Monitoring & Analytics
- `alerts` - System alerts
- `heatmaps` - Performance data
- `node_metrics` - Navigation metrics
- `edge_metrics` - Transition metrics

## 🔧 Manual Installation

If you prefer to run schema files individually:

```bash
# Connect to your Supabase database
psql "postgresql://postgres:YOUR_SERVICE_ROLE_KEY@db.YOUR_PROJECT.supabase.co:5432/postgres"

# Run schema files in order
\i setup/db/schema/001_core_tables.sql
\i setup/db/schema/002_ui_navigation_tables.sql
\i setup/db/schema/003_test_execution_tables.sql
\i setup/db/schema/004_actions_verifications.sql
\i setup/db/schema/005_monitoring_analytics.sql
```

## 🛠️ Environment Configuration

After database setup, update your `.env` files:

```bash
# In shared/.env, backend-server/.env, backend-host/.env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## ✅ Verification

Check your Supabase dashboard to verify all tables were created successfully. 