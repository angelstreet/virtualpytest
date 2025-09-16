# Requirements Setup Guide

**External services setup for VirtualPyTest - Complete this before installation.**

VirtualPyTest requires 4 external services to function properly. This guide walks you through setting up each one and obtaining the necessary credentials.

**⏱️ Estimated time: 15 minutes**

---

## 🗄️ **1. Supabase - Database & Authentication**

Supabase provides the PostgreSQL database and authentication system for VirtualPyTest.

### Step 1: Create Supabase Project

1. **Sign up** at [supabase.com](https://supabase.com)
2. **Create new project**:
   - Project name: `virtualpytest` (or your preferred name)
   - Database password: Generate a strong password and **save it**
   - Region: Choose closest to your location
3. **Wait for project creation** (~2 minutes)

### Step 2: Get Supabase Credentials

Once your project is ready:

1. Go to **Settings** → **API**
2. Copy these values:
   ```
   Project URL: https://your-project-id.supabase.co
   Anon (public) key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   Service role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

### Step 3: Database Setup

VirtualPyTest will automatically create the required tables on first run, but you can also run the setup manually:

1. Go to **SQL Editor** in Supabase dashboard
2. Run the initialization scripts from `setup/db/` in your VirtualPyTest project

### ✅ Supabase Complete
Save these credentials - you'll add them to your `.env` files later.

---

## ☁️ **2. Cloudflare R2 - Cloud Storage**

R2 stores video recordings, screenshots, and test artifacts with S3-compatible API.

### Step 1: Create Cloudflare Account

1. **Sign up** at [cloudflare.com](https://cloudflare.com)
2. **Verify your email** and complete account setup

### Step 2: Create R2 Bucket

1. Go to **R2 Object Storage** in Cloudflare dashboard
2. **Create bucket**:
   - Bucket name: `virtualpytest-storage` (must be globally unique)
   - Location: Choose closest region
3. **Create bucket**

### Step 3: Generate R2 API Token

1. Go to **Manage R2 API tokens**
2. **Create API token**:
   - Token name: `VirtualPyTest Access`
   - Permissions: `Object Read and Write`
   - Specify bucket: Select your bucket
   - TTL: No expiry (or set as needed)
3. **Create API token**

### Step 4: Get R2 Credentials

After creating the token, copy:
```
Access Key ID: abc123...
Secret Access Key: xyz789...
Bucket Name: virtualpytest-storage
Account ID: your-account-id (from R2 dashboard)
```

### ✅ R2 Complete
Your bucket is ready for storing test artifacts.

---

## 🚀 **3. Upstash Redis - Queue Management**

Upstash provides serverless Redis for managing test queues and caching.

### Step 1: Create Upstash Account

1. **Sign up** at [upstash.com](https://upstash.com)
2. **Verify email** and complete registration

### Step 2: Create Redis Database

1. **Create database**:
   - Name: `virtualpytest-queue`
   - Region: Choose closest to your location
   - Type: Regional (recommended for better performance)
2. **Create database**

### Step 3: Get Redis Credentials

From your database dashboard, copy:
```
Endpoint: redis-12345.upstash.io
Port: 12345
Password: your-redis-password
REST URL: https://redis-12345.upstash.io
REST Token: your-rest-token
```

### ✅ Upstash Complete
Your Redis queue is ready for job management.

---

## 🤖 **4. OpenRouter - AI Analysis**

OpenRouter provides access to multiple AI models for test analysis and reporting.

### Step 1: Create OpenRouter Account

1. **Sign up** at [openrouter.ai](https://openrouter.ai)
2. **Verify email** and complete account setup

### Step 2: Add Credits

1. Go to **Credits** in dashboard
2. **Add credits** (minimum $5 recommended for testing)
3. Choose payment method and add funds

### Step 3: Generate API Key

1. Go to **Keys** in dashboard
2. **Create key**:
   - Name: `VirtualPyTest`
   - Permissions: Full access (or customize as needed)
3. **Create key** and copy the API key

### Step 4: Choose AI Models

VirtualPyTest works with these recommended models:
- **GPT-4o**: Best quality, higher cost
- **Claude 3.5 Sonnet**: Excellent balance of quality/cost
- **GPT-4o Mini**: Fast and cost-effective

### ✅ OpenRouter Complete
Your AI analysis service is ready.

---

## 📝 **5. Configure Environment Files**

After setting up all services, you'll configure these credentials in your VirtualPyTest environment files:

### Main Configuration (`.env`)
```bash
# Supabase
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Cloudflare R2
R2_ACCESS_KEY_ID=abc123...
R2_SECRET_ACCESS_KEY=xyz789...
R2_BUCKET_NAME=virtualpytest-storage
R2_ACCOUNT_ID=your-account-id

# Upstash Redis
REDIS_URL=redis://default:your-password@redis-12345.upstash.io:12345
UPSTASH_REDIS_REST_URL=https://redis-12345.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-rest-token

# OpenRouter AI
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
```

### Host Configuration (`backend_host/src/.env`)
```bash
# Copy relevant credentials here for host services
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
R2_ACCESS_KEY_ID=abc123...
R2_SECRET_ACCESS_KEY=xyz789...
# ... other host-specific settings
```

### Frontend Configuration (`frontend/.env`)
```bash
# Public keys only (never put secret keys in frontend)
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 💰 **Cost Estimation**

Here's what you can expect to spend:

| Service | Free Tier | Typical Monthly Cost |
|---------|-----------|---------------------|
| **Supabase** | 500MB DB, 1GB bandwidth | $0-25 (depending on usage) |
| **Cloudflare R2** | 10GB storage, 1M requests | $0-10 (pay per use) |
| **Upstash Redis** | 10K requests/day | $0-20 (depending on usage) |
| **OpenRouter** | No free tier | $5-50 (depending on AI usage) |

**Total estimated cost: $5-105/month** (most users spend $10-30/month)

---

## 🔐 **Security Best Practices**

- **Never commit** API keys or secrets to version control
- **Use environment files** (`.env`) for all credentials
- **Rotate keys regularly** (every 3-6 months)
- **Use least-privilege access** - only grant necessary permissions
- **Monitor usage** - set up billing alerts for unexpected costs

---

## ✅ **Verification Checklist**

Before proceeding to VirtualPyTest installation, ensure you have:

- [ ] **Supabase project** created with URL and API keys
- [ ] **R2 bucket** created with access credentials
- [ ] **Upstash Redis** database with connection details
- [ ] **OpenRouter account** with API key and credits
- [ ] **All credentials** saved securely for environment configuration

---

## 🆘 **Troubleshooting**

### Common Issues

**Supabase connection fails:**
- Verify project URL format: `https://your-project-id.supabase.co`
- Check if project is fully initialized (wait 2-3 minutes after creation)
- Ensure API keys are copied correctly (they're very long)

**R2 upload errors:**
- Verify bucket name is globally unique
- Check API token has correct permissions (Object Read and Write)
- Ensure Account ID is correct (found in R2 dashboard)

**Redis connection timeout:**
- Verify endpoint format: `redis-12345.upstash.io`
- Check if database is in same region as your server
- Ensure password is copied correctly

**OpenRouter API errors:**
- Verify API key format starts with `sk-or-v1-`
- Check account has sufficient credits
- Ensure model name is correct (case-sensitive)

### Getting Help

- **Supabase**: [docs.supabase.com](https://docs.supabase.com)
- **Cloudflare R2**: [developers.cloudflare.com/r2](https://developers.cloudflare.com/r2)
- **Upstash**: [docs.upstash.com](https://docs.upstash.com)
- **OpenRouter**: [openrouter.ai/docs](https://openrouter.ai/docs)

---

## 🎯 **Next Steps**

Once you've completed all requirements setup:

1. **Return to** [Getting Started Guide](getting-started.md)
2. **Continue with** the Quick Start installation
3. **Configure** your `.env` files with the credentials you just obtained

**🎉 Ready to install VirtualPyTest!**
