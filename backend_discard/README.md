# Backend Discard Service

AI-powered false positive detection for alerts and test execution results.

## 🎯 **Purpose**

Monitors Redis queues and uses AI to analyze:
- **P1 Queue**: Alerts (highest priority)
- **P2 Queue**: Script execution results
- **P3 Queue**: Reserved for future use

## 🚀 **Quick Start**

### **Standalone**
```bash
cd backend_discard
pip install -r requirements.txt
python src/app.py
```

### **Docker**
```bash
docker build -t backend_discard .
docker run -d --env-file ../.env backend_discard
```

## ⚙️ **Configuration**

Uses environment variables from project root `.env`:

```bash
# Required
UPSTASH_REDIS_REST_URL=your_upstash_redis_url
UPSTASH_REDIS_REST_TOKEN=your_upstash_redis_token
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## 🤖 **AI Models**

- **Text Analysis**: `moonshotai/kimi-k2:free`
- **Image Analysis**: `qwen/qwen-2-vl-7b-instruct`

## 📊 **Database Updates**

Updates `alerts` and `script_results` tables with:
- `checked`: Boolean flag
- `check_type`: 'ai' or 'user'  
- `discard`: Boolean discard flag
- `discard_type`: 'false_positive' or 'valid'
- `discard_comment`: AI explanation

## 🔍 **Monitoring**

Service logs show:
- Queue processing status
- AI analysis results
- Database update confirmations
- Error handling

## 🏗️ **Architecture**

```
backend_discard/
├── src/
│   ├── app.py              # Main service
│   ├── queue_processor.py  # Upstash Redis queues
│   └── ai_analyzer.py      # OpenRouter AI analysis
├── Dockerfile
└── requirements.txt
```
