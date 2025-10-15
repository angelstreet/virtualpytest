# Deployment System Documentation

## 🎯 Overview

The Deployment System allows scheduling automated test script executions on devices using **cron expressions** with optional time-based and count-based constraints.

---

## ✨ Key Features

### **1. Cron-Based Scheduling**
- Use industry-standard cron expressions for flexible scheduling
- Supports all standard cron patterns
- 14+ preset patterns for common use cases
- Custom expression support for advanced users

### **2. Optional Constraints**
- **Start Date**: Schedule when to begin executions
- **End Date**: Automatic expiration after specific date
- **Max Executions**: Limit number of runs (e.g., "run 10 times then stop")

### **3. Multi-Device Support**
- Create deployments across multiple devices in one go
- Each device gets its own deployment instance
- Independent scheduling per device

### **4. Execution Tracking**
- Track execution count per deployment
- View execution history with status
- Link to test reports and logs
- Automatic status management (active → completed/expired)

---

## 📅 Cron Expression Guide

### **Format**
```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of Week (0-6, Sunday=0)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of Month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### **Common Patterns**

| Pattern | Cron Expression | Description |
|---------|----------------|-------------|
| **Every 5 minutes** | `*/5 * * * *` | High-frequency monitoring |
| **Every 10 minutes** | `*/10 * * * *` | Standard monitoring |
| **Every 30 minutes** | `*/30 * * * *` | Smoke tests |
| **Every hour** | `0 * * * *` | Hourly checks |
| **Every 2 hours** | `0 */2 * * *` | Periodic validation |
| **Daily at 2am** | `0 2 * * *` | Nightly regression |
| **Daily at 10am** | `0 10 * * *` | Morning test runs |
| **Weekdays at 9am** | `0 9 * * 1-5` | Business hours start |
| **Business hours** | `0 9-17 * * 1-5` | Every hour, 9am-5pm, Mon-Fri |
| **Weekly Monday** | `0 0 * * 1` | Weekly test suite |

### **Special Syntax**

- **`*`**: Any value (every minute/hour/day)
- **`*/N`**: Every N units (e.g., `*/10` = every 10 minutes)
- **`N-M`**: Range (e.g., `9-17` = 9am to 5pm)
- **`N,M,O`**: List (e.g., `1,3,5` = Monday, Wednesday, Friday)

### **Examples**

```bash
# Every 15 minutes
*/15 * * * *

# Three times daily (8am, 2pm, 8pm)
0 8,14,20 * * *

# Business hours only (Mon-Fri, 9am-5pm, every 30 min)
*/30 9-17 * * 1-5

# Weekends only at midnight
0 0 * * 0,6
```

**Need Help?** Visit [crontab.guru](https://crontab.guru) for an interactive cron expression builder.

---

## 🚀 Usage

### **Creating a Deployment**

1. **Navigate to Deployments page**
2. **Click "New Deployment"**
3. **Select Configuration**:
   - Script to run
   - Host and device
   - User interface
   - Script parameters (if any)

4. **Set Schedule** (Required):
   - Choose from preset patterns, OR
   - Enter custom cron expression

5. **Set Optional Constraints**:
   - ☑️ **Start Date**: When to begin scheduling
   - ☑️ **End Date**: When to automatically stop
   - ☑️ **Max Executions**: Run N times then complete

6. **Optional: Add More Devices**:
   - Click "Add Device" to deploy same script to multiple devices
   - Each device gets independent deployment with same schedule

7. **Click "Create Deployment(s)"**

### **Example Scenarios**

#### **Scenario 1: Continuous Monitoring**
```
Purpose: Monitor login flow every 10 minutes indefinitely
Cron: */10 * * * *
Start Date: (none - start now)
End Date: (none - run forever)
Max Executions: (none - unlimited)
```

#### **Scenario 2: Limited Test Campaign**
```
Purpose: Run checkout flow 20 times to validate stability
Cron: */30 * * * * (every 30 minutes)
Start Date: (none - start now)
End Date: (none)
Max Executions: 20
Result: Runs every 30 min, stops after 20 successful runs
```

#### **Scenario 3: Scheduled Regression**
```
Purpose: Daily regression tests for 1 week
Cron: 0 2 * * * (daily at 2am)
Start Date: 2025-10-16 00:00
End Date: 2025-10-23 00:00
Max Executions: (none)
Result: Runs nightly at 2am for 7 days, then expires
```

#### **Scenario 4: Business Hours Only**
```
Purpose: Test during office hours for 30 days
Cron: 0 9-17 * * 1-5 (hourly, 9am-5pm, weekdays)
Start Date: (none - start now)
End Date: 2025-11-15 00:00
Max Executions: (none)
Result: Runs every hour during business hours until Nov 15
```

---

## 📊 Deployment Status

### **Status Types**

| Status | Description | Icon |
|--------|-------------|------|
| **active** | Currently scheduled and running | 🟢 |
| **paused** | Temporarily stopped | ⏸️ |
| **stopped** | Manually stopped | ⏹️ |
| **completed** | Finished (max executions reached) | ✅ |
| **expired** | Finished (end date reached) | ⏰ |

### **Status Transitions**

```
active ──pause──> paused
paused ──resume──> active
active ──stop──> stopped
active ──[max reached]──> completed
active ──[end date]──> expired
```

---

## 🔄 Execution Flow

### **How Deployments Execute**

1. **APScheduler** (on host) checks cron schedule
2. **Constraint Check**:
   - ❌ Before start_date? → Skip execution
   - ❌ After end_date? → Mark as expired, stop
   - ❌ Max executions reached? → Mark as completed, stop
   - ✅ All checks pass → Proceed

3. **Script Execution**:
   - Create execution record in database
   - Run script using ScriptExecutor
   - Record results (success/failure)
   - Link to script_result and report

4. **Post-Execution**:
   - Increment execution_count
   - Update last_executed_at
   - Check if limits reached
   - Auto-complete if max reached

---

## 🗄️ Database Schema

### **deployments Table**

```sql
CREATE TABLE deployments (
  id UUID PRIMARY KEY,
  team_id UUID NOT NULL,
  name TEXT NOT NULL,
  host_name TEXT NOT NULL,
  device_id TEXT NOT NULL,
  script_name TEXT NOT NULL,
  userinterface_name TEXT NOT NULL,
  parameters TEXT,
  
  -- Cron-based scheduling
  cron_expression TEXT NOT NULL,
  start_date TIMESTAMP WITH TIME ZONE,
  end_date TIMESTAMP WITH TIME ZONE,
  max_executions INTEGER,
  
  -- Execution tracking
  execution_count INTEGER DEFAULT 0 NOT NULL,
  last_executed_at TIMESTAMP WITH TIME ZONE,
  
  -- Status
  status TEXT DEFAULT 'active',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### **deployment_executions Table**

```sql
CREATE TABLE deployment_executions (
  id UUID PRIMARY KEY,
  deployment_id UUID REFERENCES deployments(id),
  script_result_id UUID REFERENCES script_results(id),
  
  scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
  started_at TIMESTAMP WITH TIME ZONE,
  completed_at TIMESTAMP WITH TIME ZONE,
  
  status TEXT DEFAULT 'running',
  success BOOLEAN,
  skip_reason TEXT,
  error_message TEXT
);
```

---

## 🏗️ Architecture

### **Components**

```
┌─────────────────┐
│   Frontend      │  Deployments.tsx
│  (React + MUI)  │  └─ CronHelper component
└────────┬────────┘     └─ Cron validation
         │
         ↓
┌─────────────────┐
│  Backend Server │  /server/deployment/* routes
│   (Flask API)   │  └─ CRUD operations
└────────┬────────┘     └─ Supabase storage
         │
         ↓
┌─────────────────┐
│  Backend Host   │  DeploymentScheduler
│  (APScheduler)  │  └─ Cron trigger
└─────────────────┘     └─ Script execution
                        └─ Constraint checking
```

### **Flow Diagram**

```
User creates deployment
    ↓
Frontend validates cron
    ↓
POST /server/deployment/create
    ↓
Save to Supabase
    ↓
Notify host via API
    ↓
Host adds to APScheduler
    ↓
[Scheduled execution]
    ↓
Check constraints (start/end/max)
    ↓
Execute script if valid
    ↓
Record results
    ↓
Update execution_count
    ↓
Check if should complete
```

---

## 🔧 Technical Details

### **Backend: DeploymentScheduler**

**Location**: `backend_host/src/services/deployment_scheduler.py`

**Key Methods**:
- `_add_job(deployment)`: Add deployment to APScheduler
- `_should_execute(deployment)`: Check constraints before execution
- `_execute_deployment(deployment_id)`: Execute and record results
- `_mark_as_completed(deployment_id)`: Auto-complete when max reached
- `_mark_as_expired(deployment_id)`: Auto-expire when end date passed

**Features**:
- UTC timezone for consistent scheduling
- Automatic constraint validation
- Execution tracking
- Error handling and retry
- Device lock checking (skips if device busy)

### **Frontend: CronHelper Component**

**Location**: `frontend/src/components/common/CronHelper.tsx`

**Features**:
- 14 preset patterns
- Custom expression input
- Real-time validation
- Human-readable description
- Toggle between preset/custom

### **Utilities**

**Location**: `frontend/src/utils/cronUtils.ts`

**Functions**:
- `validateCronExpression(cron)`: Validate syntax
- `cronToHuman(cron)`: Convert to readable text
- `legacyToCron(...)`: Migrate old format

---

## 📝 Migration from Legacy System

### **Old Format**
```typescript
schedule_type: 'daily'
schedule_config: { hour: 10, minute: 0 }
```

### **New Format**
```typescript
cron_expression: '0 10 * * *'
start_date: null
end_date: null
max_executions: null
```

### **Migration SQL**

The migration script (`011_add_cron_scheduling.sql`) automatically converts:
- `hourly` → `M * * * *`
- `daily` → `M H * * *`
- `weekly` → `M H * * D`

**Backward Compatibility**: Legacy fields (`schedule_type`, `schedule_config`) are kept for transition period.

---

## 🎓 Best Practices

### **1. Start with Presets**
Use preset patterns for common scenarios before writing custom expressions.

### **2. Use Start Dates for Future Scheduling**
Schedule deployments to start tomorrow or next week instead of manually starting later.

### **3. Set End Dates for Temporary Monitoring**
Automatically clean up temporary monitoring deployments.

### **4. Use Max Executions for Test Campaigns**
Run tests N times to validate stability without manual intervention.

### **5. Name Deployments Clearly**
Auto-generated names include script, host, device, and timestamp for easy identification.

### **6. Monitor Execution Counts**
Track progress in the deployments table to see how many times each has run.

---

## 🐛 Troubleshooting

### **Issue: Deployment not executing**

**Check**:
1. Status is 'active' (not paused/stopped)
2. Start date is in the past (or not set)
3. End date hasn't passed
4. Max executions not reached
5. Cron expression is valid
6. Host is online and registered
7. Device is available (not locked)

**Solution**: View deployment details, check constraints, verify host status.

### **Issue: Invalid cron expression**

**Check**:
1. Must have exactly 5 parts (minute hour day month day_of_week)
2. Each part must be valid for its range
3. Use `*` for "any value"
4. Use `*/N` for "every N"

**Solution**: Use preset patterns or visit [crontab.guru](https://crontab.guru) for help.

### **Issue: Deployment completed early**

**Check**:
1. max_executions reached before expected
2. End date passed
3. Manually stopped by user

**Solution**: Check execution_count and status. Create new deployment if needed.

---

## 🔐 Security & Permissions

- **RLS Enabled**: Row Level Security on deployments table
- **Team Isolation**: Users only see deployments for their team
- **Host Authentication**: Hosts must be registered to receive deployment instructions
- **Execution Logs**: Full audit trail in deployment_executions table

---

## 📚 Related Documentation

- **Cron Guide**: [crontab.guru](https://crontab.guru)
- **APScheduler**: [APScheduler Documentation](https://apscheduler.readthedocs.io/)
- **Script Execution**: See `docs/script_execution.md`
- **Test Reports**: See `docs/test_reports.md`

---

## 💡 Tips & Tricks

### **Quick Test Schedule**
```bash
# Test every minute for 10 iterations
Cron: * * * * *
Max Executions: 10
```

### **Overnight Soak Test**
```bash
# Run every hour overnight
Cron: 0 22-6 * * *
```

### **Weekly Regression**
```bash
# Every Monday at 1am
Cron: 0 1 * * 1
```

### **Business Hours Monitoring**
```bash
# Every 15 min, 9am-5pm, weekdays
Cron: */15 9-17 * * 1-5
```

---

## 📞 Support

For issues or questions:
1. Check cron expression validity
2. Verify constraints are correct
3. Check host and device status
4. Review deployment execution history
5. Contact team lead if issues persist

---

**Last Updated**: October 2025  
**Version**: 2.0 (Cron-based system)

