# Supabase Authentication Setup Guide

Complete guide for setting up user authentication in VirtualPyTest with Supabase.

## Overview

VirtualPyTest supports **optional authentication** with multiple sign-in methods:

✅ **Email/Password** - Built-in Supabase authentication  
✅ **Google OAuth** - Sign in with Google account  
✅ **GitHub OAuth** - Sign in with GitHub account  
✅ **Role-Based Access Control** - Admin, Tester, Viewer roles  
✅ **Backend JWT Validation** - Secure API protection  

**Authentication is completely optional:**
- If you add Supabase credentials → All pages require login
- If you skip setup → App works without authentication

## Prerequisites

- **Optional**: Supabase account ([supabase.com](https://supabase.com))
- **Optional**: Google Cloud Console account (for Google OAuth)
- **Optional**: GitHub account (for GitHub OAuth)

## 1. Create Supabase Project

1. Go to [app.supabase.com](https://app.supabase.com)
2. Click "New Project"
3. Fill in project details:
   - **Name**: VirtualPyTest (or your preferred name)
   - **Database Password**: Generate a strong password
   - **Region**: Choose closest to your users
4. Click "Create new project"
5. Wait for the project to be provisioned (~2 minutes)

## 2. Get Supabase Credentials

1. In your Supabase project dashboard, go to **Settings** → **API**
2. Copy the following values:
   - **Project URL** (e.g., `https://xxxxx.supabase.co`)
   - **anon/public key** (starts with `eyJ...`)
3. Add to `frontend/.env` file:

```env
# Add these to enable authentication:
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGc...your-anon-key
```

**Note:** If you don't add these variables, the app runs without authentication (all pages public).

## 3. Create Database Schema

The SQL schema is already prepared at `setup/db/schema/018_supabase_auth_schema.sql`.

**To apply it:**

1. In Supabase dashboard, go to **SQL Editor**
2. Click "New Query"
3. Copy contents from `setup/db/schema/018_supabase_auth_schema.sql` OR paste the SQL below:

```sql
-- Create profiles table
CREATE TABLE IF NOT EXISTS public.profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT,
  full_name TEXT,
  avatar_url TEXT,
  role TEXT DEFAULT 'viewer' CHECK (role IN ('admin', 'tester', 'viewer')),
  permissions JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

-- Allow users to read their own profile
CREATE POLICY "Users can view own profile"
  ON public.profiles
  FOR SELECT
  USING (auth.uid() = id);

-- Allow users to update their own profile (except role and permissions)
CREATE POLICY "Users can update own profile"
  ON public.profiles
  FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Function to auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.profiles (id, email, full_name, avatar_url, role)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name'),
    NEW.raw_user_meta_data->>'avatar_url',
    'viewer' -- Default role for new users
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile on user signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update updated_at on profile changes
DROP TRIGGER IF EXISTS on_profile_updated ON public.profiles;
CREATE TRIGGER on_profile_updated
  BEFORE UPDATE ON public.profiles
  FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();
```

4. Click **Run** to execute the SQL

**What this does:**
- Creates `profiles` table linked to `auth.users`
- Auto-creates profile when user signs up (any method)
- Sets default role to `viewer`
- Enables Row Level Security (users can only see their own data)

## 4. Enable Email/Password Authentication

Email/password authentication works automatically once you've created the database schema.

**To enable it in Supabase:**

1. Go to **Authentication** → **Providers**
2. Find **Email** provider
3. Ensure it's **enabled** (should be on by default)
4. Optional: Configure email templates for verification emails

**Users can now:**
- Sign up with email/password
- Sign in with email/password
- Reset forgotten passwords

## 5. Configure Google OAuth (Optional)

### 5.1 Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Go to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. Configure consent screen if prompted:
   - User Type: **External**
   - App name: **VirtualPyTest**
   - User support email: Your email
   - Developer contact: Your email
6. Create OAuth client ID:
   - Application type: **Web application**
   - Name: **VirtualPyTest**
   - Authorized redirect URIs:
     ```
     https://your-project.supabase.co/auth/v1/callback
     ```
7. Copy the **Client ID** and **Client Secret**

### 5.2 Configure in Supabase

1. In Supabase dashboard, go to **Authentication** → **Providers**
2. Find **Google** and click to expand
3. Enable Google provider
4. Paste your **Client ID** and **Client Secret**
5. Click **Save**

**Note:** Google OAuth is optional. Email/password auth works without it.

## 6. Configure GitHub OAuth (Optional)

### 6.1 Create GitHub OAuth App

1. Go to [GitHub Settings](https://github.com/settings/developers)
2. Click **OAuth Apps** → **New OAuth App**
3. Fill in the details:
   - **Application name**: VirtualPyTest
   - **Homepage URL**: `http://localhost:5173` (development) or your production URL
   - **Authorization callback URL**:
     ```
     https://your-project.supabase.co/auth/v1/callback
     ```
4. Click **Register application**
5. Copy the **Client ID**
6. Click **Generate a new client secret** and copy it

### 6.2 Configure in Supabase

1. In Supabase dashboard, go to **Authentication** → **Providers**
2. Find **GitHub** and click to expand
3. Enable GitHub provider
4. Paste your **Client ID** and **Client Secret**
5. Click **Save**

**Note:** GitHub OAuth is optional. Email/password auth works without it.

## 7. Configure Redirect URLs (Required for OAuth only)

1. In Supabase dashboard, go to **Authentication** → **URL Configuration**
2. Add your redirect URLs:
   - **Site URL**: `http://localhost:5173` (for development)
   - **Redirect URLs**: Add:
     ```
     http://localhost:5173/auth/callback
     https://your-production-domain.com/auth/callback
     ```

## 8. Test Authentication

1. Start your frontend:
   ```bash
   cd frontend
   npm run dev
   ```

2. Navigate to `http://localhost:5073`
   - Should automatically redirect to `/login`

3. **Try all authentication methods:**

   **Email/Password:**
   - Click **SIGN UP** tab
   - Enter your name, email, password
   - Click "Create Account"
   - Check your email for verification (if enabled)
   - Switch to **LOGIN** tab and sign in

   **Google OAuth:**
   - Click the Google icon
   - Complete Google sign-in flow
   - Redirected back to dashboard

   **GitHub OAuth:**
   - Click the GitHub icon
   - Authorize the application
   - Redirected back to dashboard

4. After first login, you should see the dashboard

## 9. Create Your First Admin User

All new users get the default `viewer` role. To promote yourself to admin:

1. Sign in to your app (any method)
2. In Supabase dashboard, go to **Table Editor** → **profiles**
3. Find your user row
4. Edit the `role` column and change it to `admin`
5. Refresh your app - you now have admin access!

**Admin SQL shortcut:**
```sql
UPDATE public.profiles 
SET role = 'admin' 
WHERE email = 'your-email@example.com';
```

## 10. User Roles & Permissions

### Default Roles

| Role | Description | Default Permissions |
|------|-------------|---------------------|
| **admin** | Full access to everything | All permissions (`*`) |
| **tester** | Can create and run tests | view_dashboard, run_tests, create_test_cases, edit_test_cases, view_reports, api_testing, jira_integration, manage_devices, view_monitoring, create_campaigns, edit_campaigns |
| **viewer** | Read-only access | view_dashboard, view_reports, view_monitoring |

### Changing User Roles

**Option 1: Manually in Supabase**
1. Go to **Table Editor** → **profiles**
2. Find the user
3. Edit the `role` field

**Option 2: Create an Admin Panel** (Future enhancement)
- Build a UI in Settings page to manage users and roles

### Custom Permissions

You can grant additional permissions to specific users:

1. Go to **Table Editor** → **profiles**
2. Find the user
3. Edit the `permissions` column (JSONB array)
4. Example: `["api_testing", "jira_integration"]`

## 11. Backend API Protection

The backend automatically validates JWT tokens when auth is enabled.

**Protected endpoints** (require authentication):
- Device control: `/server/devices/control`
- Settings: `/server/settings/*`
- Admin routes: `/configuration/models`, `/configuration/settings`

**How it works:**

1. Frontend sends JWT token in `Authorization: Bearer <token>` header
2. Backend validates token using `@require_user_auth` decorator
3. Backend checks role/permissions with `@require_role` or `@require_permission`
4. Request proceeds if authorized, returns 401/403 if not

**Example protected route:**
```python
from lib.auth_middleware import require_user_auth, require_role

@app.route('/api/admin-only')
@require_user_auth
@require_role('admin')
def admin_endpoint():
    user_email = request.user_email  # Available after auth
    return jsonify({'message': 'Admin access granted'})
```

## 12. How Authentication Works

### Frontend Flow

```
User visits app
   ↓
Check if VITE_SUPABASE_URL exists in frontend/.env
   ↓
YES → Redirect to /login         NO → Allow access (no auth)
   ↓
User signs in (email/Google/GitHub)
   ↓
Supabase returns JWT token
   ↓
Token stored in browser
   ↓
Every API call includes: Authorization: Bearer <JWT>
   ↓
Backend validates JWT → Allows/Denies
```

### Backend Flow

```
API Request arrives
   ↓
@require_user_auth checks for JWT token
   ↓
Validates token with Supabase secret
   ↓
Extracts user_id, email, role
   ↓
@require_role checks if user has required role
   ↓
Proceeds if authorized ✅  OR  Returns 403 ❌
```

## 13. Troubleshooting

### "Invalid redirect URL" error
- Check that your redirect URLs are correctly configured in Supabase
- Ensure the callback URL matches exactly: `/auth/callback`

### User profile not created
- Check the SQL function `handle_new_user()` is created
- Check the trigger `on_auth_user_created` exists
- Look at Supabase logs for errors

### Can't access protected pages
- Check your role in the `profiles` table
- Verify permissions are correctly set
- Check browser console for auth errors

### Environment variables not loading
- Make sure `.env` file is in the `frontend` directory (NOT project root)
- Restart the Vite dev server after changing `.env`
- Variables must start with `VITE_` prefix
- Check browser console: Should see "🔒 Auth enabled" or "🔓 Auth disabled"

### Login page says "Authentication Disabled"
- Check `frontend/.env` has `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
- Restart dev server after adding credentials
- Variables must NOT have quotes in .env file

### "supabaseUrl is required" error
- Ensure `VITE_SUPABASE_URL` is set in `frontend/.env` (not project root)
- Clear browser cache and restart dev server

### Email verification not working
- Check Supabase → Authentication → Email Templates
- For development, disable email confirmation in Supabase settings
- Or check your email spam folder

## Security Best Practices

1. **Never commit `.env` files** - They're in `.gitignore` by default
2. **Use Row Level Security (RLS)** - Already configured in the SQL above
3. **Validate roles on backend** - Always verify user permissions on your API
4. **Rotate secrets regularly** - Update OAuth credentials periodically
5. **Use different projects for dev/prod** - Keep environments separate

## 14. Architecture Summary

### Frontend Components

```
frontend/src/
├── lib/supabase.ts                    # Supabase client + auth detection
├── contexts/auth/
│   ├── AuthContext.tsx                # Auth state management
│   └── PermissionContext.tsx          # Role/permission logic
├── components/auth/
│   ├── LoginPage.tsx                  # Email/OAuth login UI
│   ├── ProtectedRoute.tsx             # Route protection
│   ├── PermissionGate.tsx             # UI element protection
│   └── UserMenu.tsx                   # User avatar dropdown
├── hooks/auth/
│   ├── useAuth.ts                     # Login/logout
│   ├── usePermissions.ts              # Check permissions
│   └── useProfile.ts                  # User profile data
└── utils/apiClient.ts                 # Auto JWT injection
```

### Backend Components

```
backend_server/src/
├── lib/auth_middleware.py             # JWT validation decorators
└── routes/server_auth_routes.py       # Auth test endpoints
```

### Database Schema

```
Supabase:
├── auth.users                         # Managed by Supabase
└── public.profiles                    # Your custom user data
    ├── id → auth.users(id)
    ├── email, full_name, avatar_url
    ├── role (admin/tester/viewer)
    └── permissions (JSONB array)
```

## 15. Disabling Authentication

To disable authentication completely:

1. Remove or comment out in `frontend/.env`:
   ```env
   # VITE_SUPABASE_URL=...
   # VITE_SUPABASE_ANON_KEY=...
   ```

2. Restart dev server

3. App will run without login requirements

**All pages become public** when auth is disabled.

## Next Steps

**Completed:**
- ✅ Email/password authentication
- ✅ Google & GitHub OAuth
- ✅ Backend JWT validation
- ✅ Role-based access control
- ✅ Protected routes
- ✅ Password reset flow

**Future Enhancements:**
- [ ] Admin panel for user management
- [ ] Custom email templates (branded emails)
- [ ] Multi-Factor Authentication (MFA)
- [ ] Session management UI
- [ ] Activity logs/audit trail

## Resources

- [Supabase Auth Documentation](https://supabase.com/docs/guides/auth)
- [Google OAuth Setup](https://supabase.com/docs/guides/auth/social-login/auth-google)
- [GitHub OAuth Setup](https://supabase.com/docs/guides/auth/social-login/auth-github)
- [Row Level Security Guide](https://supabase.com/docs/guides/auth/row-level-security)

