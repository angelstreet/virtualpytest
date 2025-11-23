# 🌩️ Migrate to Supabase Cloud Database

**Migrate your VirtualPyTest main database from local PostgreSQL to Supabase cloud for better reliability and features.**

## 📋 **What This Guide Covers**

This guide helps you migrate **only the main VirtualPyTest application database** from local PostgreSQL to Supabase cloud. 

**⚠️ Important**: This migration is for the **main project database only** - Grafana metrics will continue using the local PostgreSQL database for optimal performance.

---

## 🎯 **Why Migrate to Supabase Cloud?**

### Benefits
- ✅ **Automatic Backups** - Never lose your test data
- ✅ **High Availability** - 99.9% uptime guarantee  
- ✅ **Global Edge Network** - Faster access worldwide
- ✅ **Real-time Features** - Live updates in your dashboard
- ✅ **Managed Security** - Built-in authentication and RLS
- ✅ **Scalability** - Grows with your testing needs
- ✅ **Free Tier** - Perfect for small teams (500MB storage)

### What Stays Local
- 📊 **Grafana Metrics Database** - Remains local for performance
- 🖥️ **VNC Services** - Local device control
- 📹 **Video Capture** - Local storage (can use R2 for cloud storage)

---

## 🚀 **Quick Migration (TL;DR)**

```bash
# 1. Create Supabase project at https://supabase.com
# 2. Get your connection details
# 3. Update your .env file
# 4. Run migration script
./setup/local/migrate_to_supabase.sh

# 5. Restart services
./scripts/launch_virtualpytest.sh
```

**That's it!** Your main database is now on Supabase cloud.

---

## 📋 **Prerequisites**

Before starting:
- ✅ **Working VirtualPyTest installation** (local PostgreSQL)
- ✅ **Internet connection** for Supabase access
- ✅ **Supabase account** (free at [supabase.com](https://supabase.com))
- ✅ **Backup of existing data** (automatic during migration)

---

## 🔧 **Step 1: Create Supabase Project**

### 1.1 Sign Up for Supabase

1. Go to [supabase.com](https://supabase.com)
2. Click **"Start your project"**
3. Sign up with GitHub, Google, or email
4. Verify your email if required

### 1.2 Create New Project

1. Click **"New project"** in your dashboard
2. Choose your organization (or create one)
3. Fill in project details:
   - **Name**: `virtualpytest-main` (or your preferred name)
   - **Database Password**: Generate a strong password (**save this!**)
   - **Region**: Choose closest to your location
   - **Pricing Plan**: Start with **Free** (500MB storage)

4. Click **"Create new project"**

⏳ **Wait 2-3 minutes** for your database to be provisioned.

---

## 🔑 **Step 2: Get Connection Details**

Once your project is ready:

### 2.1 Find Your Project Settings

1. Go to **Settings** → **API** in your Supabase dashboard
2. Copy these values:

```bash
# Project URL
https://your-project-id.supabase.co

# Anonymous Key (for frontend)
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Service Role Key (for backend - keep secret!)
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2.2 Get Database Connection String

Go to **Settings** → **Database** and copy:

```bash
# Connection string
postgresql://postgres:[YOUR-PASSWORD]@db.your-project-id.supabase.co:5432/postgres
```

---

## 📊 **Step 3: Set Up Database Schema**

### 3.1 Open Supabase SQL Editor

1. In your Supabase dashboard, go to **SQL Editor**
2. You'll see a query editor with syntax highlighting

### 3.2 Execute Schema Files

Execute these files **in order** by copying and pasting each file's content:

#### File 1: Core Tables
1. Open `setup/db/schema/001_core_tables.sql` in your local project
2. Copy the entire contents
3. Paste into Supabase SQL Editor  
4. Click **"Run"** (or press Ctrl/Cmd + Enter)
5. Verify success: ✅ should appear

#### File 2: UI Navigation Tables
1. Open `setup/db/schema/002_ui_navigation_tables.sql`
2. Copy contents and paste into SQL Editor
3. Click **"Run"**

#### File 3: Test Execution Tables  
1. Open `setup/db/schema/003_test_execution_tables.sql`
2. Copy contents and paste into SQL Editor
3. Click **"Run"**

#### File 4: Actions & Verifications
1. Open `setup/db/schema/004_actions_verifications.sql`
2. Copy contents and paste into SQL Editor
3. Click **"Run"**

#### File 5: Monitoring & Analytics
1. Open `setup/db/schema/005_monitoring_analytics.sql`
2. Copy contents and paste into SQL Editor
3. Click **"Run"**

### 3.3 Verify Tables Created

1. Go to **Table Editor** in Supabase dashboard
2. You should see these main tables:
   - `teams`
   - `device_models`
   - `device`
   - `campaign_executions`
   - `test_executions`
   - `navigation_configs`
   - `navigation_nodes`
   - And more...

---

## ⚙️ **Step 4: Update Configuration**

### 4.1 Backup Current Configuration

```bash
# Backup your current .env file
cp .env .env.backup.local
```

### 4.2 Update Main .env File

Edit your `.env` file and update these settings:

```bash
# =============================================================================
# DATABASE CONFIGURATION - SUPABASE CLOUD
# =============================================================================

# Supabase Configuration (ENABLED for cloud database)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.your-project-id.supabase.co:5432/postgres
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key

# Local PostgreSQL (DISABLED - commented out)
# POSTGRES_HOST=localhost
# POSTGRES_PORT=5432
# POSTGRES_DB=virtualpytest
# POSTGRES_USER=vpt_user
# POSTGRES_PASSWORD=vpt_local_pass

# Database connection details (for Supabase)
DB_HOST=db.your-project-id.supabase.co
DB_PORT=5432
DB_NAME=postgres
DB_USER=postgres
DB_PASSWORD=your_supabase_db_password
```

### 4.3 Keep Grafana Local (Important!)

**Do NOT change** these Grafana settings in your `.env` - they should remain local:

```bash
# =============================================================================
# GRAFANA CONFIGURATION - KEEP LOCAL
# =============================================================================

# Grafana Database (KEEP using local PostgreSQL for performance)
GF_DATABASE_TYPE=postgres
GF_DATABASE_HOST=localhost:5432
GF_DATABASE_NAME=grafana_metrics
GF_DATABASE_USER=grafana_user
GF_DATABASE_PASSWORD=grafana_pass
```

---

## 📦 **Step 5: Migrate Existing Data (Optional)**

If you have existing test data you want to keep:

### 5.1 Export Local Data

```bash
# Export your current data
pg_dump -h localhost -U vpt_user -d virtualpytest --data-only --inserts > local_data_backup.sql
```

### 5.2 Import to Supabase

1. Open the `local_data_backup.sql` file
2. Copy the contents
3. Paste into Supabase SQL Editor
4. Click **"Run"**

**Note**: This step is optional - you can start fresh with an empty database.

---

## 🚀 **Step 6: Test the Migration**

### 6.1 Restart Services

```bash
# Stop any running services
pkill -f "python.*5109"
pkill -f "python.*6109"

# Launch with new configuration
./scripts/launch_virtualpytest.sh
```

### 6.2 Verify Connection

1. Open http://localhost:3000
2. Go to **Devices** section
3. Try creating a test device
4. Check if it appears in your Supabase **Table Editor**

### 6.3 Test Basic Operations

```bash
# Test device creation
curl -X POST http://localhost:5109/api/devices \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Device", "description": "Migration test"}'

# Test device listing
curl http://localhost:5109/api/devices
```

---

## 📊 **Step 7: Monitor Performance**

### 7.1 Supabase Dashboard

Monitor your database in **Settings** → **Usage**:
- **Database size**: Free tier includes 500MB
- **API requests**: 50,000 per month on free tier
- **Bandwidth**: 2GB per month on free tier

### 7.2 Application Performance

Check response times in your application:
- Database queries should be fast (< 100ms for simple queries)
- Real-time updates should work immediately
- No connection errors in logs

---

## 🔧 **Troubleshooting**

### Connection Issues

**Problem**: Can't connect to Supabase
```bash
# Test connection
curl -H "apikey: YOUR_ANON_KEY" \
     -H "Authorization: Bearer YOUR_ANON_KEY" \
     https://your-project-id.supabase.co/rest/v1/teams
```

**Solutions**:
- ✅ Check your API keys are correct
- ✅ Verify project URL format
- ✅ Ensure internet connection is stable

### Schema Errors

**Problem**: Tables not created properly
- ✅ Execute schema files in the correct order (001, 002, 003, 004, 005)
- ✅ Check for syntax errors in SQL Editor
- ✅ Verify UUID extension is enabled

### Performance Issues

**Problem**: Slow database queries
- ✅ Check your internet connection speed
- ✅ Consider upgrading Supabase plan for better performance
- ✅ Optimize queries with proper indexes

### Data Migration Issues

**Problem**: Data not importing correctly
- ✅ Check for foreign key constraints
- ✅ Ensure UUIDs are properly formatted
- ✅ Import schema before data

---

## 🔄 **Rollback to Local Database**

If you need to go back to local PostgreSQL:

### Quick Rollback

```bash
# 1. Restore backup configuration
cp .env.backup.local .env

# 2. Restart local PostgreSQL
sudo systemctl start postgresql

# 3. Restart services
./scripts/launch_virtualpytest.sh
```

### Complete Rollback

```bash
# 1. Restore configuration
cp .env.backup.local .env

# 2. Reinstall local database
./setup/local/install_db.sh --force-clean

# 3. Restart all services
./scripts/launch_virtualpytest.sh
```

---

## 📈 **Next Steps After Migration**

### 1. Set Up Real-time Features

Enable real-time updates in your Supabase dashboard:
1. Go to **Database** → **Replication**
2. Enable replication for tables you want real-time updates
3. Update your frontend to use Supabase real-time subscriptions

### 2. Configure Backups

Set up automated backups:
1. Go to **Settings** → **Database**
2. Configure backup schedule
3. Set up backup notifications

### 3. Monitor Usage

Keep an eye on your usage:
- Database size (500MB free tier limit)
- API requests (50,000/month free tier)
- Consider upgrading if you exceed limits

### 4. Security (Production)

For production deployments:
```sql
-- Enable Row Level Security
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_models ENABLE ROW LEVEL SECURITY;

-- Create security policies
CREATE POLICY "team_access" ON teams
FOR ALL USING (auth.uid() IS NOT NULL);
```

---

## 🎉 **Migration Complete!**

**Congratulations!** Your VirtualPyTest main database is now running on Supabase cloud.

### What You Now Have

- ✅ **Cloud Database** - Main application data on Supabase
- ✅ **Local Metrics** - Grafana still uses local PostgreSQL for performance
- ✅ **Automatic Backups** - Your data is safe
- ✅ **Global Access** - Access your data from anywhere
- ✅ **Real-time Ready** - Can enable live updates anytime

### Architecture Overview

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │  Backend Server  │    │  Backend Host   │
│  (localhost)    │◄──►│  (localhost)     │◄──►│  (localhost)    │
└─────────────────┘    └─────────┬────────┘    └─────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Supabase Cloud DB     │
                    │  (Main Application)     │
                    └─────────────────────────┘
                                 
                    ┌─────────────────────────┐
                    │  Local PostgreSQL DB    │
                    │   (Grafana Metrics)     │
                    └─────────────────────────┘
```

---

## 🆘 **Need Help?**

- **🐛 Issues**: Check [Troubleshooting Guide](troubleshooting.md)
- **❓ Questions**: See [Features Documentation](features.md)  
- **💬 Community**: GitHub Discussions and Issues
- **📧 Supabase Support**: [Supabase Support](https://supabase.com/support)

---

**🌩️ Your VirtualPyTest system is now cloud-powered!**

*Enjoy the benefits of managed database hosting while keeping the performance of local metrics storage.*
