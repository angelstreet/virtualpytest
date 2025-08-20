# Backend Discard Service

AI-powered false positive detection for alerts and test execution results.

## 🎯 **How It Works**

### **Overview**
The backend_discard service automatically analyzes test results and alerts using AI to identify false positives, reducing manual review workload.

### **Process Flow**
1. **Queue Population**: When alerts or script results are created, they're automatically added to Redis queues
2. **Priority Processing**: Service processes P1 (alerts) → P2 (scripts) → P3 (reserved) 
3. **AI Analysis**: Uses vision AI to analyze report screenshots and text AI for metadata
4. **Database Update**: Marks items as checked and sets discard status with AI reasoning

### **What Gets Analyzed**
- **Alerts**: System alerts for potential issues
- **Script Results**: Test execution results with reports/screenshots  
- **P3 Queue**: Reserved for future use cases

### **AI Models Used**
- **Vision**: `qwen/qwen-2.5-vl-7b-instruct` for analyzing report images/screenshots
- **Text**: `moonshotai/kimi-k2:free` for analyzing metadata and descriptions

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

Uses environment variables from **project root** `.env`:

```bash
# Required (shared across host and discard services)
UPSTASH_REDIS_REST_URL=your_upstash_redis_url
UPSTASH_REDIS_REST_TOKEN=your_upstash_redis_token
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
OPENROUTER_API_KEY=your_openrouter_api_key
```

## 🤖 **AI Models**

- **Text Analysis**: `moonshotai/kimi-k2:free`
- **Image Analysis**: `qwen/qwen-2.5-vl-7b-instruct`

## 📊 **Database Integration**

Adds 5 columns to existing `alerts` and `script_results` tables:

| Column | Type | Purpose |
|--------|------|---------|
| `checked` | boolean | Has this item been analyzed? |
| `check_type` | string | Who checked it: 'ai' or 'user' |
| `discard` | boolean | Should this be discarded as false positive? |
| `discard_type` | string | Category: 'false_positive', 'valid', etc. |
| `discard_comment` | text | AI reasoning for the decision |

## 🏗️ **Service Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Alert/Test    │    │  Redis Queues   │    │ Backend Discard │
│   Generation    │───▶│  P1: alerts     │◄───│   AI Service    │
│                 │    │  P2: scripts    │    │                 │ 
│ alerts_db.py    │    │  P3: reserved   │    │ • Vision AI     │
│ script_results  │    │                 │    │ • Text AI       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **File Structure**
```
backend_discard/
├── src/
│   ├── app.py              # Main service loop
│   ├── queue_processor.py   # Upstash Redis queues  
│   ├── ai_analyzer.py      # OpenRouter AI analysis
│   └── .env               # Service configuration
├── Dockerfile              # Docker deployment
└── requirements.txt        # Python dependencies
```

## 🔍 **Monitoring**

### **Service Logs**
- Queue processing status and task counts
- AI analysis results and confidence scores  
- Database update confirmations
- Health check status every 5 minutes

### **Health Endpoint**
```bash
curl http://localhost:6209/health
```
