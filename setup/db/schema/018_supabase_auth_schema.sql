-- =====================================================
-- Supabase Authentication Schema
-- Run this in Supabase SQL Editor
-- =====================================================

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

-- Drop existing policies to make this script idempotent
DROP POLICY IF EXISTS "Users can view own profile" ON public.profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
DROP POLICY IF EXISTS "Admins can view all profiles" ON public.profiles;
DROP POLICY IF EXISTS "Admins can update all profiles" ON public.profiles;

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

-- Allow admins to view all profiles
CREATE POLICY "Admins can view all profiles"
  ON public.profiles
  FOR SELECT
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
    )
  );

-- Allow admins to update all profiles
CREATE POLICY "Admins can update all profiles"
  ON public.profiles
  FOR UPDATE
  USING (
    EXISTS (
      SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin'
    )
  );

-- Function to auto-create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
  default_team_id UUID;
BEGIN
  -- Get the default team ID
  SELECT id INTO default_team_id 
  FROM public.teams 
  WHERE is_default = true 
  LIMIT 1;
  
  -- Create profile with default team assignment
  INSERT INTO public.profiles (id, email, full_name, avatar_url, role, team_id)
  VALUES (
    NEW.id,
    NEW.email,
    COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name'),
    NEW.raw_user_meta_data->>'avatar_url',
    'viewer', -- Default role for new users
    default_team_id
  );
  
  -- Add user to default team in team_members table
  IF default_team_id IS NOT NULL THEN
    INSERT INTO public.team_members (team_id, user_id, role)
    VALUES (default_team_id, NEW.id, 'member')
    ON CONFLICT (team_id, user_id) DO NOTHING;
  END IF;
  
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

-- =====================================================
-- Backfill: Create profiles for existing users
-- =====================================================
-- Run this if you had users BEFORE creating the trigger
DO $$
DECLARE
  default_team_id UUID;
BEGIN
  -- Get the default team ID
  SELECT id INTO default_team_id 
  FROM public.teams 
  WHERE is_default = true 
  LIMIT 1;
  
  -- Create profiles for existing users
  INSERT INTO public.profiles (id, email, full_name, avatar_url, role, permissions, team_id)
  SELECT 
    u.id,
    u.email,
    COALESCE(u.raw_user_meta_data->>'full_name', u.raw_user_meta_data->>'name'),
    u.raw_user_meta_data->>'avatar_url',
    'viewer',
    '[]'::jsonb,
    default_team_id
  FROM auth.users u
  LEFT JOIN public.profiles p ON u.id = p.id
  WHERE p.id IS NULL
  ON CONFLICT (id) DO NOTHING;
  
  -- Add existing users to default team in team_members table
  IF default_team_id IS NOT NULL THEN
    INSERT INTO public.team_members (team_id, user_id, role)
    SELECT default_team_id, id, 'member'
    FROM public.profiles
    WHERE team_id = default_team_id
    ON CONFLICT (team_id, user_id) DO NOTHING;
  END IF;
END $$;

-- =====================================================
-- Initial Admin User (OPTIONAL)
-- =====================================================
-- After you create your first user (sign up), run this to make yourself admin:
-- UPDATE public.profiles SET role = 'admin' WHERE email = 'your-email@example.com';

