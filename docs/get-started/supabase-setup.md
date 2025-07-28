# 🗄️ Supabase Database Setup

This guide walks you through setting up your PostgreSQL database on Supabase for VirtualPyTest. This is required for both local development and cloud deployment.

## 🌟 Why Supabase?

Supabase provides:
- ✅ **Managed PostgreSQL** with automatic backups
- ✅ **Real-time subscriptions** for live updates
- ✅ **Built-in authentication** and row-level security
- ✅ **Global edge network** for low latency
- ✅ **Free tier** perfect for development
- ✅ **SQL editor** with syntax highlighting

## 🚀 Step 1: Create Supabase Project

### 1.1 Sign Up for Supabase

1. Go to [supabase.com](https://supabase.com)
2. Click **"Start your project"**
3. Sign up with GitHub, Google, or email
4. Verify your email if required

### 1.2 Create New Project

1. Click **"New project"** in your dashboard
2. Choose your organization (or create one)
3. Fill in project details:
   - **Name**: `virtualpytest-db` (or your preferred name)
   - **Database Password**: Generate a strong password (save this!)
   - **Region**: Choose closest to your users/servers
   - **Pricing Plan**: Start with **Free** (upgrade later if needed)

4. Click **"Create new project"**

⏳ **Wait 2-3 minutes** for your database to be provisioned.

## 🔧 Step 2: Get Connection Details

Once your project is ready:

### 2.1 Find Your Project Settings

1. Go to **Settings** → **API** in your Supabase dashboard
2. Note down these important values:

```bash
# Project URL
SUPABASE_URL=https://your-project-id.supabase.co

# Anonymous Key (safe for frontend)
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Service Role Key (backend only - keep secret!)
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2.2 Database Connection String

For direct database access (if needed):

```bash
# PostgreSQL connection string
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.your-project-id.supabase.co:5432/postgres
```

## 📊 Step 3: Execute Database Schema

VirtualPyTest requires several database tables. Execute these SQL files in order:

### 3.1 Open SQL Editor

1. In your Supabase dashboard, go to **SQL Editor**
2. You'll see a query editor with syntax highlighting

### 3.2 Execute Schema Files

Execute these files **in order** by copying and pasting each file's content:

#### File 1: Core Tables
```sql
-- Copy and paste content from: setup/db/schema/001_core_tables.sql
```

1. Go to your local `setup/db/schema/001_core_tables.sql` file
2. Copy the entire contents
3. Paste into Supabase SQL Editor  
4. Click **"Run"** (or press Ctrl/Cmd + Enter)
5. Verify success: ✅ should appear

#### File 2: UI Navigation Tables
```sql
-- Copy and paste content from: setup/db/schema/002_ui_navigation_tables.sql
```

#### File 3: Test Execution Tables  
```sql
-- Copy and paste content from: setup/db/schema/003_test_execution_tables.sql
```

#### File 4: Actions & Verifications
```sql
-- Copy and paste content from: setup/db/schema/004_actions_verifications.sql
```

#### File 5: Monitoring & Analytics
```sql
-- Copy and paste content from: setup/db/schema/005_monitoring_analytics.sql
```

### 3.3 Verify Tables Created

After executing all schemas:

1. Go to **Table Editor** in Supabase dashboard
2. You should see these tables:
   - `teams`
   - `device_models`
   - `device`
   - `controllers`
   - `navigation_configs`
   - `navigation_nodes`
   - `navigation_edges`
   - `test_campaigns`
   - `test_executions`
   - `actions`
   - `verifications`
   - `monitoring_sessions`
   - And more...

## 🔐 Step 4: Configure Security (Optional)

### 4.1 Row Level Security (RLS)

For production deployments, consider enabling RLS:

```sql
-- Enable RLS on sensitive tables
ALTER TABLE teams ENABLE ROW LEVEL SECURITY;
ALTER TABLE device_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE device ENABLE ROW LEVEL SECURITY;

-- Create policies (example for teams table)
CREATE POLICY "Users can view own team data" ON teams
    FOR SELECT USING (auth.uid() = created_by);

CREATE POLICY "Users can insert own team data" ON teams  
    FOR INSERT WITH CHECK (auth.uid() = created_by);
```

### 4.2 API Settings

In **Settings** → **API**:

- **JWT expiry**: Default (1 hour) is fine for development
- **Additional headers**: Leave default unless specific needs

## 🌍 Step 5: Configure for Your Environment

### 5.1 For Local Development

Add to your `shared/.env`:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here

# Environment
ENVIRONMENT=development
DEBUG=true
```

### 5.2 For Cloud Deployment

#### Vercel (Frontend)
Add environment variables in Vercel dashboard:
```bash
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key_here
```

#### Render (Backend Server)
Add environment variables in Render dashboard:
```bash
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

## 📈 Step 6: Monitoring and Maintenance

### 6.1 Database Usage

Monitor your database in **Settings** → **Usage**:
- **Database size**: Free tier includes 500MB
- **Bandwidth**: 2GB per month on free tier
- **API requests**: 50,000 per month on free tier

### 6.2 Backups

Supabase automatically backs up your database:
- **Point-in-time recovery**: Available on paid plans
- **Daily backups**: Included in free tier (7 days retention)

### 6.3 Performance Monitoring

Use **Reports** section to monitor:
- Query performance
- API usage patterns
- Error rates

## 🔍 Troubleshooting

### Common Issues

#### Connection Errors
```bash
# Test connection from your application
curl -H "apikey: YOUR_ANON_KEY" \
     -H "Authorization: Bearer YOUR_ANON_KEY" \
     https://your-project-id.supabase.co/rest/v1/teams
```

#### Schema Errors
- Ensure you execute schema files in the correct order
- Check for syntax errors in SQL Editor
- Verify all extensions are enabled (UUID, etc.)

#### Permission Issues
- Use **Service Role Key** for backend operations
- Use **Anon Key** for frontend operations
- Check RLS policies if enabled

### SQL Editor Tips

- **Syntax highlighting**: Automatic for SQL
- **Auto-complete**: Use Ctrl+Space
- **Multiple queries**: Separate with semicolons
- **Save queries**: Use the save button for reusable queries
- **Query history**: Access previous queries from history panel

## 🎯 Production Checklist

Before going live:

- [ ] All schema files executed successfully
- [ ] Tables visible in Table Editor
- [ ] Connection strings tested from application
- [ ] Environment variables configured
- [ ] Backup strategy understood
- [ ] Usage limits appropriate for expected load
- [ ] Security policies configured (if needed)

## 🔄 Schema Updates

When you need to update the database schema:

### Adding New Tables/Columns
1. Create new migration SQL file
2. Test in development environment first
3. Execute in Supabase SQL Editor
4. Update application code accordingly

### Example Migration
```sql
-- Add new column to existing table
ALTER TABLE device_models 
ADD COLUMN firmware_version VARCHAR(50);

-- Create new table
CREATE TABLE device_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_id UUID REFERENCES device(id) ON DELETE CASCADE,
    log_level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 🔗 Next Steps

1. **Test Connection**: Verify your application can connect to the database
2. **Set up Authentication**: Configure Supabase Auth if needed
3. **Choose Deployment**: Continue with [Local Setup](./local-setup.md) or [Cloud Setup](./cloud-setup.md)
4. **Explore Features**: Try real-time subscriptions and advanced queries

## 🔗 Related Guides

- [Local Development Setup](./local-setup.md)
- [Cloud Deployment Setup](./cloud-setup.md)
- [Architecture Overview](../ARCHITECTURE_REDESIGN.md)

## 📚 Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [SQL Tutorial](https://www.w3schools.com/sql/) 