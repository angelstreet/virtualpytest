# 🍓 Raspberry Pi Ubuntu Quickstart

**Get VirtualPyTest running on Raspberry Pi in minutes.**

## 📥 **Download & Flash**

1. **Download pre-configured image**: [https://mega.nz/file/k6xmmYxL#WtKSR0DE4U8Jb8SW_LcJmfzQnWdjpgp2fZ8ql90TXzM]
2. **Flash to SD card**:
   ```bash
   # Insert SD card, find device (usually /dev/sdb or /dev/mmcblk0)
   lsblk
   
   # Flash image (replace /dev/sdX with your SD card)
   sudo dd if=virtualpytest-rpi-ubuntu.img of=/dev/sdX bs=4M status=progress
   sync
   ```

3. **Insert SD card** into Raspberry Pi and boot

## ⚙️ **Configure Environment**

SSH into your Pi and edit these 3 files:

### 1. Main Configuration
```bash
sudo nano /home/pi/virtualpytest/.env
```
**Required changes:**
```bash
# Supabase (get from your Supabase project)
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key

# Cloudflare R2 (get from Cloudflare dashboard)
CLOUDFLARE_R2_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
CLOUDFLARE_R2_ACCESS_KEY_ID=your_r2_access_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_r2_secret_key
CLOUDFLARE_R2_PUBLIC_URL=https://pub-your-bucket-id.r2.dev

# OpenRouter AI (get from openrouter.ai)
OPENROUTER_API_KEY=your_openrouter_api_key

# Update server URL to Pi's IP
SERVER_URL=http://192.168.1.XXX:5109  # Replace XXX with Pi's IP
```

### 2. Host Configuration
```bash
sudo nano /home/pi/virtualpytest/backend_host/src/.env
```
**Required changes:**
```bash
# Update host settings
HOST_NAME=rpi-host-1
HOST_URL=http://192.168.1.XXX:6109  # Replace XXX with Pi's IP

# Copy same Supabase/R2 credentials from main .env
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
CLOUDFLARE_R2_ACCESS_KEY_ID=your_r2_access_key
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_r2_secret_key
```

### 3. Frontend Configuration
```bash
sudo nano /home/pi/virtualpytest/frontend/.env
```
**Required changes:**
```bash
# Update server URL to Pi's IP
VITE_SERVER_URL=http://192.168.1.XXX:5109  # Replace XXX with Pi's IP
VITE_SUPABASE_URL=https://your-project-id.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

## 🌐 **Update Nginx (if needed)**

If accessing from other devices on network:
```bash
sudo nano /etc/nginx/sites-available/default
```
Replace `localhost` with Pi's IP address in proxy_pass directives.

## 🚀 **Start Services**

```bash
sudo systemctl restart vpt_server_host && journalctl -u vpt_server_host.service -f
```

## 🌐 **Access**

- **Web Interface**: http://192.168.1.XXX:3000
- **Backend API**: http://192.168.1.XXX:5109
- **Host API**: http://192.168.1.XXX:6109
- **VNC Desktop**: http://192.168.1.XXX:6080

**Done!** Your Raspberry Pi is running VirtualPyTest.

## 🔧 **Quick Commands**

```bash
# Check service status
sudo systemctl status vpt_server_host

# View logs
journalctl -u vpt_server_host.service -f

# Restart if needed
sudo systemctl restart vpt_server_host
```
