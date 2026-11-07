#!/usr/bin/env bash
curl -X POST "https://engine.sqrengine.com/v1/chat/completions" \
  -H "Authorization: Bearer $SQR_API_KEY" \
  -H "X-SQR-Project-ID: sqr-jira-bundle" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sqr",
    "flow": "jira_flow",
    "messages": [
      { "role": "user", "content": "Execute task" }
    ]
  }'
