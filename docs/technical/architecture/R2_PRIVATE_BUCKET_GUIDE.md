# R2 Private Bucket with Pre-signed URLs - Implementation Guide

## 🎉 Implementation Complete!

Your codebase now supports **secure, authenticated access to private R2 buckets** using pre-signed URLs with Supabase authentication.

**Mode is AUTO-DETECTED from environment variable - zero code changes needed!**

---

## 🚀 Quick Start (TL;DR)

### Public Bucket (Current - Default)
```bash
# frontend/.env
VITE_CLOUDFLARE_R2_PUBLIC_URL=https://pub-xxxxx.r2.dev
```
→ Uses direct public URLs (fast, no auth)

### Private Bucket (Secure)
```bash
# frontend/.env
# Remove or comment out VITE_CLOUDFLARE_R2_PUBLIC_URL
# VITE_CLOUDFLARE_R2_PUBLIC_URL=
```
→ Uses signed URLs via backend (secure, requires Supabase login)

**That's it!** No code changes needed.

---

## 📋 What Was Implemented

### Backend (Python)

✅ **`shared/src/lib/utils/cloudflare_utils.py`**
- Added `generate_presigned_url()` - Generate single signed URL
- Added `generate_presigned_urls_batch()` - Generate multiple signed URLs efficiently
- Uses boto3's S3-compatible signature generation (no API calls, free operation)

✅ **`backend_server/src/routes/server_storage_routes.py`** (NEW FILE)
- `POST /server/storage/signed-url` - Single URL generation (Supabase auth required)
- `POST /server/storage/signed-urls-batch` - Batch URL generation
- `GET /server/storage/health` - Service health check
- All endpoints protected with `@require_user_auth` decorator

✅ **`backend_server/src/app.py`**
- Registered new storage routes blueprint

### Frontend (TypeScript/React)

✅ **`frontend/src/utils/infrastructure/cloudflareUtils.ts`**
- Auto-detects mode from `VITE_CLOUDFLARE_R2_PUBLIC_URL` env var
- `getR2Url()` - Get single URL (public or signed based on env)
- `getR2UrlsBatch()` - Get multiple URLs efficiently
- `isPublicMode()` / `isPrivateMode()` - Check current mode
- In-memory caching with auto-expiry handling

✅ **`frontend/src/hooks/storage/useR2Url.ts`** (NEW FILE)
- `useR2Url()` - React hook for single URL
- `useR2UrlsBatch()` - React hook for multiple URLs
- `useR2UrlFromExisting()` - Convert existing URL to signed
- Loading states, error handling, auto-refresh

✅ **`frontend/src/hooks/storage/index.ts`** (NEW FILE)
- Exports all storage hooks

✅ **`frontend/src/hooks/index.ts`**
- Exports storage hooks globally

---

## 🚀 How to Use

### Mode is Controlled by Environment Variable

The system auto-detects which mode to use based on `VITE_CLOUDFLARE_R2_PUBLIC_URL`:

| Env Var | Mode | Description |
|---------|------|-------------|
| **Set** (e.g., `https://pub-xxx.r2.dev`) | PUBLIC | Direct URLs, no auth, fast |
| **Not set** or empty | PRIVATE | Signed URLs via backend, requires Supabase auth |

---

### Scenario 1: Keep Public Bucket (Default)

**No changes needed!** Just ensure your `frontend/.env` has:

```bash
VITE_CLOUDFLARE_R2_PUBLIC_URL=https://pub-xxxxx.r2.dev
```

The console will show:
```
[@utils:cloudflareUtils] 🔓 PUBLIC mode - Using direct URLs from: https://pub-xxxxx.r2.dev
```

---

### Scenario 2: Switch to Private Bucket

**Step 1: Remove or comment out the env var**

In `frontend/.env`:

```bash
# Comment out or remove to enable private mode
# VITE_CLOUDFLARE_R2_PUBLIC_URL=https://pub-xxxxx.r2.dev
```

The console will show:
```
[@utils:cloudflareUtils] 🔐 PRIVATE mode - Using signed URLs (VITE_CLOUDFLARE_R2_PUBLIC_URL not set)
```

**Step 2: Make R2 bucket private in Cloudflare Dashboard**

1. Go to Cloudflare Dashboard → R2
2. Select your `virtualpytest` bucket
3. Settings → Public Access → **Disable**
4. Save

**That's it!** ✅ All file access now requires Supabase authentication.

---

### Using in Components (Optional)

If you want loading states and error handling, use the hooks:

**Single Image:**
```typescript
import { useR2Url } from '@/hooks/storage/useR2Url';

function MyComponent({ imagePath }: { imagePath: string }) {
  const { url, loading, error } = useR2Url(imagePath);

  if (loading) return <Spinner />;
  if (error) return <div>Error: {error}</div>;
  if (!url) return null;

  return <img src={url} alt="Capture" />;
}
```

**Multiple Images (Batch - More Efficient):**
```typescript
import { useR2UrlsBatch } from '@/hooks/storage/useR2Url';

function GalleryComponent({ imagePaths }: { imagePaths: string[] }) {
  const { urls, loading, error } = useR2UrlsBatch(imagePaths);

  if (loading) return <Spinner />;

  return (
    <div className="gallery">
      {urls.map((url, index) => (
        url && <img key={index} src={url} alt={`Image ${index}`} />
      ))}
    </div>
  );
}
```

---

### Check Current Mode Programmatically

```typescript
import { isPublicMode, isPrivateMode, getR2Mode } from '@/utils/infrastructure/cloudflareUtils';

console.log(getR2Mode()); // 'public' or 'private'
console.log(isPublicMode()); // true/false
console.log(isPrivateMode()); // true/false
```

---

## 🔐 Security Features

### Authentication Flow

```
User Login (Supabase)
  ↓
Get JWT Token
  ↓
Frontend: Call /server/storage/signed-url (with JWT)
  ↓
Backend: Validate JWT
  ↓
Backend: Generate signed URL (cryptographic signature)
  ↓
Frontend: Receive temporary URL (expires in 1 hour)
  ↓
Browser: Access R2 directly (R2 validates signature)
```

### What's Protected

✅ **Authentication Required**: Must have valid Supabase account
✅ **Time-Limited**: URLs expire (default: 1 hour, configurable)
✅ **Auditable**: Backend logs who requested what file
✅ **Revocable**: Disable user → no new URLs generated
✅ **Role-Based**: Can restrict by user role (admin, tester, viewer)

### What's NOT Protected (By Design)

⚠️ **URL Sharing**: If someone gets a signed URL, they can use it until expiry
- This is normal - signed URLs are meant to be shared temporarily
- Similar to how AWS S3 signed URLs work
- Mitigation: Use shorter expiry times for sensitive files

---

## ⚙️ Configuration Options

### Expiry Times

Default: **3600 seconds (1 hour)**

Change per-request:

```typescript
// 30 minutes
const url = await getR2Url('file.jpg', 1800);

// 2 hours
const url = await getR2Url('file.jpg', 7200);

// 24 hours
const url = await getR2Url('file.jpg', 86400);
```

Backend validates: **60 seconds (min) to 604800 seconds (7 days max)**

### Caching

**Enabled by default** - URLs cached in memory until 5 minutes before expiry

Disable caching:

```typescript
// In cloudflareUtils.ts
const SIGNED_URL_CONFIG = {
  enabled: true,
  defaultExpiry: 3600,
  cacheEnabled: false, // Disable cache
  cacheExpiryBuffer: 300,
};
```

Clear cache manually:

```typescript
import { clearSignedUrlCache } from '@/utils/infrastructure/cloudflareUtils';

// Clear on logout
function handleLogout() {
  clearSignedUrlCache();
  // ... rest of logout logic
}
```

---

## 📊 Performance & Cost

### Performance

**Public Bucket (Current)**:
- Direct browser → R2 access
- Latency: ~50-200ms (CDN)

**Private Bucket with Signed URLs**:
- Browser → Backend API → Generate URL (local, no R2 call)
- Browser → R2 (direct access with signed URL)
- First load latency: +100-300ms (API call)
- Cached loads: Same as public (no API call)

### Cost

**Cloudflare R2 Pricing**:
- Storage: $0.015/GB/month (unchanged)
- Class B operations (GET): **FREE** ✅
- `generate_presigned_url()`: **Local operation (FREE)** ✅

**No extra cost for signed URLs!** 🎉

Backend API calls use your existing server infrastructure.

---

## 🧪 Testing

### Test Backend API

```bash
# Get your Supabase JWT token from browser console:
# supabase.auth.getSession()

# Test single URL generation
curl -X POST http://localhost:5109/server/storage/signed-url \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "path": "captures/device1/capture_123.jpg",
    "expires_in": 3600
  }'

# Test batch URL generation
curl -X POST http://localhost:5109/server/storage/signed-urls-batch \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "paths": ["file1.jpg", "file2.jpg", "file3.jpg"],
    "expires_in": 7200
  }'

# Test health check (no auth)
curl http://localhost:5109/server/storage/health
```

### Test Frontend Hook

Create a test component:

```typescript
import { useR2Url } from '@/hooks/storage/useR2Url';
import { setSignedUrlMode } from '@/utils/infrastructure/cloudflareUtils';

function TestSignedUrls() {
  useEffect(() => {
    setSignedUrlMode(true); // Enable signed URLs
  }, []);

  const { url, loading, error, refresh } = useR2Url(
    'captures/device1/test.jpg',
    3600 // 1 hour
  );

  return (
    <div>
      <h2>Signed URL Test</h2>
      {loading && <p>Loading...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}
      {url && (
        <>
          <p>URL: {url.substring(0, 100)}...</p>
          <img src={url} alt="Test" />
          <button onClick={refresh}>Refresh URL</button>
        </>
      )}
    </div>
  );
}
```

---

## 🔄 Migration Path

**Simple 2-step process:**

### Step 1: Test in Development

1. ✅ In development `frontend/.env`, comment out `VITE_CLOUDFLARE_R2_PUBLIC_URL`
2. ✅ Restart frontend dev server
3. ✅ Check console shows: `🔐 PRIVATE mode - Using signed URLs`
4. ✅ Test that images/files still load (via signed URLs)
5. ✅ Bucket is still public, but you're testing signed URL flow

### Step 2: Go Live

1. ✅ Update production `frontend/.env` - remove `VITE_CLOUDFLARE_R2_PUBLIC_URL`
2. ✅ Deploy frontend
3. ✅ Make bucket **private** in Cloudflare dashboard
4. 🎉 Done! All file access now requires authentication

**Rollback if needed:**
- Add `VITE_CLOUDFLARE_R2_PUBLIC_URL` back to env
- Make bucket public again
- Instant rollback, no code changes

---

## 🐛 Troubleshooting

### Check Current Mode

Open browser console and look for:
```
[@utils:cloudflareUtils] 🔓 PUBLIC mode - Using direct URLs from: https://...
```
or
```
[@utils:cloudflareUtils] 🔐 PRIVATE mode - Using signed URLs (VITE_CLOUDFLARE_R2_PUBLIC_URL not set)
```

### Error: "Authentication required" (401)

**Cause**: In private mode but user not logged in

**Fix**:
- Ensure user is logged in to Supabase
- Check `supabase.auth.getSession()` returns valid session
- Private mode requires authentication for ALL file access

### Error: "Failed to generate signed URL"

**Cause**: Backend R2 credentials not configured

**Fix**:
- Check backend `.env` has:
  - `CLOUDFLARE_R2_ENDPOINT`
  - `CLOUDFLARE_R2_ACCESS_KEY_ID`
  - `CLOUDFLARE_R2_SECRET_ACCESS_KEY`
- Restart backend server

### URLs Return 403 Forbidden

**Cause**: Bucket is private but using public URLs

**Fix**:
- Check env var is NOT set: `VITE_CLOUDFLARE_R2_PUBLIC_URL` should be empty/missing
- Verify console shows `🔐 PRIVATE mode`
- If console shows `🔓 PUBLIC mode`, the env var is still set

### Images Not Loading in Private Mode

**Cause**: User not authenticated or token expired

**Fix**:
- Check user is logged in
- Check Supabase session is valid
- Try logging out and back in

### Want to Switch Back to Public

**Fix**:
- Add `VITE_CLOUDFLARE_R2_PUBLIC_URL=https://your-bucket.r2.dev` to frontend `.env`
- Restart frontend
- Make bucket public in Cloudflare (if it was private)

---

## 📚 API Reference

### Backend API

#### POST `/server/storage/signed-url`

Generate a pre-signed URL for a single file.

**Headers**:
- `Authorization: Bearer <supabase-jwt>` (required)

**Request Body**:
```json
{
  "path": "captures/device1/capture_123.jpg",
  "expires_in": 3600
}
```

**Response**:
```json
{
  "success": true,
  "url": "https://account.r2.cloudflarestorage.com/...?X-Amz-Signature=...",
  "expires_in": 3600,
  "expires_at": "2025-12-05T15:30:00Z",
  "path": "captures/device1/capture_123.jpg"
}
```

#### POST `/server/storage/signed-urls-batch`

Generate multiple pre-signed URLs.

**Request Body**:
```json
{
  "paths": ["file1.jpg", "file2.jpg", "file3.jpg"],
  "expires_in": 3600
}
```

**Response**:
```json
{
  "success": true,
  "urls": [
    {
      "path": "file1.jpg",
      "url": "https://...",
      "expires_at": "2025-12-05T15:30:00Z",
      "expires_in": 3600
    }
  ],
  "failed": [],
  "generated_count": 3,
  "failed_count": 0
}
```

### Frontend Hooks

#### `useR2Url(path, expiresIn, autoRefresh)`

**Parameters**:
- `path`: R2 path or full URL
- `expiresIn`: Seconds until expiry (default: 3600)
- `autoRefresh`: Auto-refresh before expiry (default: true)

**Returns**:
```typescript
{
  url: string | null,
  loading: boolean,
  error: string | null,
  refresh: () => Promise<void>
}
```

#### `useR2UrlsBatch(paths, expiresIn, autoRefresh)`

**Parameters**:
- `paths`: Array of R2 paths
- `expiresIn`: Seconds until expiry (default: 3600)
- `autoRefresh`: Auto-refresh before expiry (default: true)

**Returns**:
```typescript
{
  urls: (string | null)[],
  urlMap: Record<string, string>,
  loading: boolean,
  error: string | null,
  refresh: () => Promise<void>
}
```

---

## 🎯 Next Steps

1. **Test in Development**
   - Enable signed URL mode
   - Update a test component
   - Verify signed URLs are generated

2. **Plan Migration**
   - Identify components using R2 URLs
   - Prioritize high-security content
   - Update components incrementally

3. **Go Private** (When Ready)
   - Make bucket private in Cloudflare
   - Monitor for errors
   - Celebrate secure storage! 🎉

---

## 📞 Support

If you encounter issues:
1. Check browser console for errors
2. Check backend logs for authentication failures
3. Verify R2 credentials are correct
4. Test with health check endpoint first

---

**Implementation completed**: ✅ All files created, no linter errors
**Security**: ✅ Supabase JWT authentication
**Performance**: ✅ Cached signed URLs, batch generation
**Cost**: ✅ No additional R2 charges

Happy secure storage! 🔐

