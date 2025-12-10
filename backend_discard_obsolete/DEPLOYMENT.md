# Backend Discard Service - Deployment Guide

## 🚀 **Quick Deploy**

### **1. Standalone (Local)**
```bash
cd backend_discard
pip install -r requirements.txt
python src/app.py
```

### **2. Docker (Single Service)**
```bash
docker build -t backend_discard .
docker run -d --env-file ../.env backend_discard
```

### **3. Docker Compose (Full Stack)**
```bash
# From project root
docker-compose up backend_discard
```

## ⚙️ **Environment Setup**

Ensure these variables are set in your **project root** `.env`:

```bash
# Required (shared across host and discard services)
UPSTASH_REDIS_REST_URL=your_upstash_redis_url
UPSTASH_REDIS_REST_TOKEN=your_upstash_redis_token
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## 🧪 **Testing**

### **Test Queue Operations**
```bash
cd backend_discard
python scripts/test_queue.py
```

### **Manual Queue Check**
```bash
# Check if service is processing
docker logs backend_discard

# Or for standalone
tail -f service.log
```

## 📊 **Monitoring**

### **Service Logs**
The service outputs structured logs showing:
- Queue processing status
- AI analysis results  
- Database updates
- Error handling

### **Key Log Patterns**
```
🔄 Processing alert task: alert-123
🤖 AI Analysis: discard=true, confidence=0.85, reason='Brief blackscreen during channel change'
📝 Updated alert alert-123 in database
✅ SUCCESS - Task alert-123 processed
```

### **Health Check**
```bash
# Check if service is running
ps aux | grep "python src/app.py"

# Check Redis connectivity
# (Logs will show connection status)
```

## 🎯 **Production Deployment**

### **Render/Vercel (Cloud)**
1. Deploy as separate service
2. Use same environment variables
3. Connect to existing Upstash Redis
4. Monitor via service logs

### **Local Infrastructure**
1. Run alongside other services
2. Uses existing Redis/DB setup
3. Automatic startup with Docker Compose

## 🔧 **Troubleshooting**

### **Common Issues**

1. **Redis Connection Failed**
   - Check `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN`
   - Verify Upstash Redis is active

2. **AI Analysis Failed** 
   - Check `OPENROUTER_API_KEY`
   - Verify OpenRouter account has credits

3. **Database Updates Failed**
   - Check Supabase connection
   - Verify database schema has new columns

4. **Import Errors**
   - Ensure `shared/` directory is accessible
   - Check PYTHONPATH in Docker

### **Debug Mode**
Set `DEBUG=true` in environment for verbose logging.

## 📈 **Scaling**

- **Single Instance**: Handles ~100 tasks/minute
- **Multiple Instances**: Can run multiple containers
- **Queue Backlog**: Redis handles large queues efficiently
- **AI Rate Limits**: OpenRouter manages API limits automatically

## 🔄 **Updates**

To update the service:
1. Pull latest code
2. Rebuild Docker image: `docker build -t backend_discard .`
3. Restart: `docker-compose restart backend_discard`

Service handles graceful shutdowns and queue persistence.
