# Nginx Hot Storage Configuration Fix

## Problem
Frontend requests files from paths like:
```
/host/stream/capture1/captures/capture_001.jpg
/host/stream/capture1/segments/output.m3u8
```

But nginx serves from:
```nginx
location /host/stream/ {
    alias /var/www/html/stream/;
}
```

This resolves to `/var/www/html/stream/capture1/captures/...` which is COLD storage!

With RAM hot storage enabled, files are actually in:
```
/var/www/html/stream/capture1/hot/captures/...  ← Nginx not checking here!
```

---

## Solution

Add `try_files` directive to check hot storage first, then fallback to cold storage:

```nginx
location /host/stream/ {
    alias /var/www/html/stream/;
    
    # HOT/COLD ARCHITECTURE: Try hot storage (RAM) first, fallback to cold (SD)
    # This makes hot storage transparent to frontend - no URL changes needed!
    try_files $uri @try_hot_storage;
    
    # CORS headers for HLS streaming
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Range" always;
    add_header Access-Control-Expose-Headers "Content-Length,Content-Range" always;
}

# Hot storage fallback handler
location @try_hot_storage {
    # Extract device and path from URI
    # /host/stream/capture1/captures/file.jpg → /stream/capture1/hot/captures/file.jpg
    rewrite ^/host/stream/([^/]+)/([^/]+)/(.+)$ /stream/$1/hot/$2/$3 break;
    
    root /var/www/html;
    try_files $uri =404;
    
    # CORS headers (duplicated for fallback)
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Range" always;
    add_header Access-Control-Expose-Headers "Content-Length,Content-Range" always;
}
```

---

## Alternative (Simpler) Solution

Use internal rewrite to check both locations:

```nginx
location /host/stream/ {
    alias /var/www/html/stream/;
    
    # HOT/COLD ARCHITECTURE: Transparent hot storage support
    # Checks: /stream/X/hot/Y/file → /stream/X/Y/file
    location ~ ^/host/stream/([^/]+)/(captures|thumbnails|segments|metadata)/(.+)$ {
        set $device $1;
        set $folder $2;
        set $file $3;
        
        # Try hot storage first (RAM), then cold storage (SD)
        try_files /stream/$device/hot/$folder/$file /stream/$device/$folder/$file =404;
        
        root /var/www/html;
        
        # CORS headers
        add_header Access-Control-Allow-Origin "*" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Range" always;
        add_header Access-Control-Expose-Headers "Content-Length,Content-Range" always;
    }
    
    # CORS headers for general stream location
    add_header Access-Control-Allow-Origin "*" always;
    add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
}
```

---

## Which Files Need Update?

### Production Hosts (Update these):
1. `backend_server/config/nginx/sunri-pi1.conf` - Line 116
2. `backend_server/config/nginx/sunri-pi4.conf` - Check if exists
3. Local nginx configs on each Pi

### Development (Optional):
1. `backend_server/config/nginx/local.conf` - Line 151
2. `backend_server/config/nginx/virtualpytest.conf` - Line 143

---

## Testing

After nginx config update:

```bash
# 1. Test nginx configuration
sudo nginx -t

# 2. Reload nginx
sudo systemctl reload nginx

# 3. Create test file in hot storage
echo "test" > /var/www/html/stream/capture1/hot/captures/test.txt

# 4. Request via nginx
curl http://localhost/host/stream/capture1/captures/test.txt
# Should return: "test"

# 5. Check nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

---

## Impact

### Before Fix:
- ❌ Frontend requests → `/captures/` (cold storage, empty)
- ❌ Health checks show "0 files"
- ❌ Streams don't work
- ❌ Images don't load

### After Fix:
- ✅ Frontend requests → `/hot/captures/` (RAM, active files)
- ✅ Automatic fallback to cold storage for archived files
- ✅ Zero URL changes needed in frontend
- ✅ Transparent hot/cold architecture

---

## Rollback Plan

If issues occur after nginx update:

```bash
# 1. Restore backup
sudo cp /etc/nginx/sites-available/virtualpytest.conf.backup /etc/nginx/sites-available/virtualpytest.conf

# 2. Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

---

## Recommended Approach

**OPTION 1: Simple symlink (Quick fix, no nginx changes)**
```bash
# Create symlinks in cold storage pointing to hot storage
cd /var/www/html/stream/capture1
ln -s hot/captures captures_hot
ln -s hot/thumbnails thumbnails_hot
ln -s hot/segments segments_hot
```

**OPTION 2: Nginx try_files (Proper solution, requires testing)**
- Update nginx config as shown above
- Test thoroughly before production deploy

**OPTION 3: Frontend URL update (Not recommended - breaks centralization)**
- Change frontend to request from `/hot/captures/` explicitly
- ❌ This breaks when not in RAM mode!

---

## Recommendation

Use **OPTION 2 (nginx try_files)** because:
1. ✅ Transparent to frontend
2. ✅ Works in both RAM and SD modes
3. ✅ Proper fallback mechanism
4. ✅ No code changes needed
5. ✅ Easy to test and rollback

**Next Steps:**
1. Test nginx config in development
2. Apply to one production Pi
3. Verify health checks show files
4. Roll out to all Pis

