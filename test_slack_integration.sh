#!/bin/bash
# Test Slack Integration

SERVER_URL="http://localhost:5109"

echo "================================"
echo "Testing Slack Integration"
echo "================================"

echo ""
echo "1. Get Slack Status:"
curl -s "${SERVER_URL}/server/integrations/slack/status" | jq '.'

echo ""
echo ""
echo "2. Get Slack Config (token hidden):"
curl -s "${SERVER_URL}/server/integrations/slack/config" | jq '.'

echo ""
echo ""
echo "3. Test Connection:"
curl -s -X POST "${SERVER_URL}/server/integrations/slack/test" \
  -H "Content-Type: application/json" | jq '.'

echo ""
echo ""
echo "4. Send Test Message to Slack:"
curl -s -X POST "${SERVER_URL}/server/integrations/slack/send-test" \
  -H "Content-Type: application/json" | jq '.'

echo ""
echo ""
echo "================================"
echo "If step 4 succeeds, check your Slack channel!"
echo "================================"

