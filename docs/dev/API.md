# VirtualPyTest API Examples

This document shows how to test subtitle detection using different API endpoints.

## 1. Direct OpenRouter API

Test subtitle detection directly with OpenRouter's vision model:

```bash
# Convert image to base64 first
base64 -i your_image.jpg > image_b64.txt

# Call OpenRouter API directly
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
              "url": "data:image/jpeg;base64,$(cat image_b64.txt)"
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
  "id": "gen-123...",
  "choices": [{
    "message": {
      "content": "```json\n{\n  \"subtitles_detected\": true,\n  \"extracted_text\": \"But to do that, I feel like I have to reset everything, you know?\",\n  \"detected_language\": \"English\",\n  \"confidence\": 0.95\n}\n```"
    }
  }]
}
```

## 2. VirtualPyTest Host API

Test subtitle detection through the host endpoint (requires host to be running):

```bash
curl -X POST "https://virtualpytest.com/host/verification/video/detectSubtitlesAI" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "device2",
    "image_source_url": "https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/android_mobile/fullzap_20250821_20250821004238/capture_20250821004133.jpg"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "subtitles_detected": true,
  "extracted_text": "But to do that, I feel like I have to reset everything, you know?",
  "detected_language": "English",
  "confidence": 0.95,
  "execution_time_ms": 1250
}
```

## 3. VirtualPyTest Server API (Proxy)

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
    "image_source_url": "https://pub-604f1a4ce32747778c6d5ac5e3100217.r2.dev/script-reports/android_mobile/fullzap_20250821_20250821004238/capture_20250821004133.jpg"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "subtitles_detected": true,
  "extracted_text": "But to do that, I feel like I have to reset everything, you know?",
  "detected_language": "English",
  "confidence": 0.95,
  "execution_time_ms": 1250
}
```

## Notes

- **OpenRouter API**: Direct access, fastest, requires API key in environment
- **Host API**: Requires local host running, handles image processing
- **Server API**: Requires host object with connection details, proxies to host
- **Image URLs**: Host/Server APIs can handle both local paths and HTTP URLs
- **Performance**: Direct OpenRouter ~1-2s, Host/Server ~2-3s (includes processing overhead)

## Error Handling

Common error responses:

```json
// Missing API key
{"success": false, "error": "No API key"}

// Invalid host URL format  
{"success": false, "error": "Failed to convert host URL to local path"}

// Host not reachable
{"success": false, "error": "Proxy error: Connection failed"}

// Invalid image
{"success": false, "error": "Image file not found"}
```
