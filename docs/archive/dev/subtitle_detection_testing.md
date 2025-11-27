# Subtitle Detection Testing Guide

This document provides easy-to-use commands for testing subtitle detection using different methods.

## 🚨 **TESTING WORKFLOW - ALWAYS FOLLOW THIS ORDER**

1. **FIRST**: Test OpenRouter API directly to verify API key/quota
2. **SECOND**: Test VirtualPyTest Host API debug endpoint
3. **THIRD**: Investigate specific issues if either fails

## Test Images
- **Primary**: https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/stb/fullzap_20250902_20250902184621/capture_20250902184533.jpg
  - **Expected Result**: Contains subtitle text "lets you browse like Chrome, but it blocks cookies and ads"
- **Alternative**: Any public image URL with visible subtitles

## 1. 🔥 **STEP 1: Direct OpenRouter API Test (ALWAYS DO FIRST)**

**⚠️ CRITICAL**: Always test this first to verify API key, account status, and quota before debugging VirtualPyTest issues.

### Quick Test Command
```bash
# Download test image
curl -o /tmp/test_subtitle_image.jpg "https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/stb/fullzap_20250902_20250902184621/capture_20250902184533.jpg"

# Convert to base64
base64 -i /tmp/test_subtitle_image.jpg > /tmp/test_image_b64.txt

# Test OpenRouter API directly (load API key from .env)
source .env && curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -H "HTTP-Referer: https://virtualpytest.com" \
  -H "X-Title: VirtualPyTest" \
  -d '{
    "model": "qwen/qwen-2.5-vl-7b-instruct",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Analyze this image for subtitles. Respond with JSON: {\"subtitles_detected\": true/false, \"extracted_text\": \"text or empty\", \"detected_language\": \"language or unknown\", \"confidence\": 0.0-1.0}"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,'$(cat /tmp/test_image_b64.txt)'"
            }
          }
        ]
      }
    ],
    "max_tokens": 300,
    "temperature": 0.0
  }'
```

**Expected Response:**
```json
{
  "id": "gen-...",
  "choices": [{
    "message": {
      "content": "```json\n{\n  \"subtitles_detected\": true,\n  \"extracted_text\": \"lets you browse like Chrome, but it blocks cookies and ads\",\n  \"detected_language\": \"English\",\n  \"confidence\": 0.95\n}\n```"
    }
  }]
}
```

## 2. 🎯 **STEP 2: VirtualPyTest Host API Debug Test**

**✅ ONLY DO THIS AFTER STEP 1 PASSES**

### New Debug Endpoint (Recommended)
This endpoint can handle public URLs directly:

```bash
curl -X POST "https://virtualpytest.com/host/verification/video/debugSubtitlesAI" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device1",
    "image_url": "https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/stb/fullzap_20250902_20250902184621/capture_20250902184533.jpg"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "subtitles_detected": true,
  "combined_extracted_text": "lets you browse like Chrome, but it blocks cookies and ads",
  "detected_language": "English",
  "execution_time_ms": 3618,
  "debug_info": {
    "original_url": "https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/stb/fullzap_20250902_20250902184621/capture_20250902184533.jpg",
    "downloaded_size": 71549
  },
  "results": [
    {
      "confidence": 0.95,
      "extracted_text": "lets you browse like Chrome, but it blocks cookies and ads",
      "has_subtitles": true,
      "detected_language": "English"
    }
  ]
}
```

## 3. VirtualPyTest Server API Test (Proxy)

Test subtitle detection through the server endpoint (proxies to host):

```bash
curl -X POST "https://virtualpytest.com/server/verification/video/analyzeSubtitles" \
  -H "Content-Type: application/json" \
  -d '{
    "host": {
      "host_name": "sunri-pi1",
      "host_port": 6109,
      "host_url": "https://virtualpytest.com",
      "status": "online"
    },
    "device_id": "device2",
    "image_source_url": "https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/stb/fullzap_20250902_20250902184621/capture_20250902184533.jpg"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "subtitles_detected": true,
  "extracted_text": "lets you browse like Chrome, but it blocks cookies and ads",
  "detected_language": "English",
  "confidence": 0.95,
  "execution_time_ms": 1250
}
```

## 4. Test with Different Images

### Using a local image file:
```bash
# Convert your image to base64
base64 -i /path/to/your/image.jpg > /tmp/your_image_b64.txt

# Use the same curl command but replace the base64 data
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer sk-or-v1-YOUR-API-KEY" \
  -H "Content-Type: application/json" \
  -H "HTTP-Referer: https://virtualpytest.com" \
  -H "X-Title: VirtualPyTest" \
  -d '{
    "model": "qwen/qwen-2.5-vl-7b-instruct",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Analyze this image for subtitles. Respond with JSON: {\"subtitles_detected\": true/false, \"extracted_text\": \"text or empty\", \"detected_language\": \"language or unknown\", \"confidence\": 0.0-1.0}"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,'$(cat /tmp/your_image_b64.txt)'"
            }
          }
        ]
      }
    ],
    "max_tokens": 300,
    "temperature": 0.0
  }'
```

## 5. Quick Test Script

Create a reusable test script:

```bash
#!/bin/bash
# save as test_subtitle_detection.sh

IMAGE_URL="$1"
API_KEY="sk-or-v1-YOUR-API-KEY"

if [ -z "$IMAGE_URL" ]; then
    echo "Usage: $0 <image_url_or_path>"
    exit 1
fi

# Download or use local file
if [[ $IMAGE_URL == http* ]]; then
    echo "Downloading image..."
    curl -o /tmp/test_image.jpg "$IMAGE_URL"
    IMAGE_PATH="/tmp/test_image.jpg"
else
    IMAGE_PATH="$IMAGE_URL"
fi

# Convert to base64
echo "Converting to base64..."
base64 -i "$IMAGE_PATH" > /tmp/test_b64.txt

# Test OpenRouter API
echo "Testing OpenRouter API..."
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "HTTP-Referer: https://virtualpytest.com" \
  -H "X-Title: VirtualPyTest" \
  -d '{
    "model": "qwen/qwen-2.5-vl-7b-instruct",
    "messages": [
      {
        "role": "user",
        "content": [
          {
            "type": "text",
            "text": "Analyze this image for subtitles. Respond with JSON: {\"subtitles_detected\": true/false, \"extracted_text\": \"text or empty\", \"detected_language\": \"language or unknown\", \"confidence\": 0.0-1.0}"
          },
          {
            "type": "image_url",
            "image_url": {
              "url": "data:image/jpeg;base64,'$(cat /tmp/test_b64.txt)'"
            }
          }
        ]
      }
    ],
    "max_tokens": 300,
    "temperature": 0.0
  }'

# Clean up
rm -f /tmp/test_image.jpg /tmp/test_b64.txt
```

Usage:
```bash
chmod +x test_subtitle_detection.sh
./test_subtitle_detection.sh "https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/stb/fullzap_20250902_20250902184621/capture_20250902184533.jpg"
```

## 🚨 **Troubleshooting Guide**

### ⚠️ **CRITICAL: 401 "User not found" Error**

**If you get `{"error":{"message":"User not found.","code":401}}` from OpenRouter:**

1. **API Key Issues**: 
   - Invalid or expired API key
   - Check `.env` file has correct `OPENROUTER_API_KEY`
   - Verify key format: `sk-or-v1-YOUR-API-KEY`

2. **Account Issues**:
   - OpenRouter account suspended or deactivated
   - Payment method expired
   - Account verification required

3. **Quota/Credit Issues**:
   - No remaining credits on account
   - Monthly/daily limits exceeded
   - Free tier exhausted

**✅ SOLUTION**: Always test Step 1 (Direct OpenRouter) first to isolate the issue!

### Common Issues:

1. **API Key Issues**: Make sure the API key is valid and has sufficient credits
2. **Image Format**: Ensure image is in JPEG/PNG format  
3. **Base64 Encoding**: Verify base64 encoding is correct (no newlines in JSON)
4. **Network Issues**: Check internet connectivity and firewall settings
5. **Device ID**: Use `device1` for host API (not `device2`)

### Error Responses:

```json
// 401 - API key/account/quota issues
{"error": {"message": "User not found", "code": 401}}

// Missing API key
{"error": {"message": "Invalid API key", "type": "invalid_request_error"}}

// Rate limit exceeded
{"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}

// Invalid image format
{"error": {"message": "Invalid image format", "type": "invalid_request_error"}}

// Host API - No controller
{"error": "No verification_video controller found for device device2", "success": false}

// Host API - Image download failed
{"error": "Failed to download image: 404 Client Error", "success": false}
```

## Performance Comparison

- **Direct OpenRouter**: ~1-2 seconds
- **Host API**: ~2-3 seconds (includes processing overhead)
- **Server API**: ~3-4 seconds (includes proxy overhead)

## Subtitle Detection Optimization

**New Behavior (Max 3 Attempts):**
- Tests maximum 3 images with +1s intervals
- Breaks early if subtitles are found in any image
- Only shows the last tested image in logs
- Reduces API calls and improves performance

## Root Cause Analysis & Fix

### The Problem
The VirtualPyTest implementation was failing because it switched from a **JSON structured prompt** to a **natural language prompt**:

- **Direct OpenRouter** (✅ WORKS): `"Analyze this image for subtitles. Respond with JSON: {...}"`
- **VirtualPyTest Before Fix** (❌ FAILED): `"Look at this image and tell me if you can see any subtitles..."`

### The Solution
Implemented a **fallback approach** in `backend_host/src/controllers/verification/video_ai_helpers.py`:

1. **Primary**: Try JSON structured prompt (same as successful direct test)
2. **Fallback**: If JSON parsing fails, use natural language parsing

```python
# Primary: JSON structured prompt
prompt = "Analyze this image for subtitles. Respond with JSON: {\"subtitles_detected\": true/false, \"extracted_text\": \"text or empty\", \"detected_language\": \"language or unknown\", \"confidence\": 0.0-1.0}"

# Try JSON parsing first
try:
    ai_result = json.loads(json_content)
    # Extract structured data...
except json.JSONDecodeError:
    # Fallback to natural language parsing
    extracted_text, detected_language, confidence = self.parse_natural_language_response(content)
```

### Git History
- **Original**: Used JSON structured prompt (worked)
- **NLD Change** (dddbfc6c): Switched to natural language prompt (broke)
- **Current Fix**: JSON-first with natural language fallback (robust)

## 📋 **Quick Reference Summary**

### ✅ **Working Test Commands**

**Step 1 - Direct OpenRouter Test:**
```bash
source .env && curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -H "HTTP-Referer: https://virtualpytest.com" \
  -H "X-Title: VirtualPyTest" \
  -d '{"model": "qwen/qwen-2.5-vl-7b-instruct", "messages": [{"role": "user", "content": [{"type": "text", "text": "Analyze this image for subtitles. Respond with JSON: {\"subtitles_detected\": true/false, \"extracted_text\": \"text or empty\", \"detected_language\": \"language or unknown\", \"confidence\": 0.0-1.0}"}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,'"$(base64 -i /tmp/test_subtitle_image.jpg)"'"}}]}], "max_tokens": 300, "temperature": 0.0}'
```

**Step 2 - Host Debug Endpoint:**
```bash
curl -X POST "https://virtualpytest.com/host/verification/video/debugSubtitlesAI" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "device1", "image_url": "https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/stb/fullzap_20250902_20250902184621/capture_20250902184533.jpg"}'
```

### 🎯 **Key Points**
- **Always test OpenRouter directly first** - isolates API key/quota issues
- **Use device1** for host API (not device2)
- **401 errors** = API key, account, or quota problems
- **New debug endpoint** handles public URLs automatically
- **Expected subtitle**: "lets you browse like Chrome, but it blocks cookies and ads"

## Notes

- The direct OpenRouter API test confirmed subtitle detection works correctly
- The test image contains the subtitle: "lets you browse like Chrome, but it blocks cookies and ads"  
- The fix restores the original JSON approach while keeping natural language as fallback
- Always test with the direct API first to isolate issues
- New debug endpoint `/debugSubtitlesAI` simplifies testing with public URLs
