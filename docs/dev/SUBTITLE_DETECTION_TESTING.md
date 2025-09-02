# Subtitle Detection Testing Guide

This document provides easy-to-use commands for testing subtitle detection using different methods.

## Test Image
- **URL**: https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/stb/fullzap_20250902_20250902184621/capture_20250902184533.jpg
- **Expected Result**: Contains subtitle text "lets you browse like Chrome, but it blocks cookies and ads"

## 1. Direct OpenRouter API Test

### Step 1: Download and encode test image
```bash
# Download test image
curl -o /tmp/test_subtitle_image.jpg "https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/stb/fullzap_20250902_20250902184621/capture_20250902184533.jpg"

# Convert to base64
base64 -i /tmp/test_subtitle_image.jpg > /tmp/test_image_b64.txt
```

### Step 2: Direct OpenRouter API call
```bash
curl -X POST "https://openrouter.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer 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" \
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

## 2. VirtualPyTest Host API Test

Test subtitle detection through the host endpoint (requires host to be running and local image path):

```bash
curl -X POST "https://virtualpytest.com/host/verification/video/detectSubtitlesAI" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device2",
    "image_source_url": "/var/www/html/stream/capture1/captures/capture_20250902184533.jpg"
  }'
```

**Note**: Host endpoint requires local file paths or URLs that can be converted to local paths with `/host/` in the path.

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
  -H "Authorization: Bearer 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" \
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
API_KEY="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"

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

## Troubleshooting

### Common Issues:

1. **API Key Issues**: Make sure the API key is valid and has sufficient credits
2. **Image Format**: Ensure image is in JPEG/PNG format
3. **Base64 Encoding**: Verify base64 encoding is correct (no newlines in JSON)
4. **Network Issues**: Check internet connectivity and firewall settings

### Error Responses:

```json
// Missing API key
{"error": {"message": "Invalid API key", "type": "invalid_request_error"}}

// Rate limit exceeded
{"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}}

// Invalid image format
{"error": {"message": "Invalid image format", "type": "invalid_request_error"}}
```

## Performance Comparison

- **Direct OpenRouter**: ~1-2 seconds
- **Host API**: ~2-3 seconds (includes processing overhead)
- **Server API**: ~3-4 seconds (includes proxy overhead)

## Root Cause Analysis & Fix

### The Problem
The VirtualPyTest implementation was failing because it switched from a **JSON structured prompt** to a **natural language prompt**:

- **Direct OpenRouter** (✅ WORKS): `"Analyze this image for subtitles. Respond with JSON: {...}"`
- **VirtualPyTest Before Fix** (❌ FAILED): `"Look at this image and tell me if you can see any subtitles..."`

### The Solution
Implemented a **fallback approach** in `backend_core/src/controllers/verification/video_ai_helpers.py`:

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

## Notes

- The direct OpenRouter API test confirmed subtitle detection works correctly
- The test image contains the subtitle: "lets you browse like Chrome, but it blocks cookies and ads"
- The fix restores the original JSON approach while keeping natural language as fallback
- Always test with the direct API first to isolate issues
