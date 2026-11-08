curl -X POST "${SQR_BASE_URL:?Set SQR_BASE_URL}/v1/chat/completions" \
  -H "Authorization: Bearer $SQR_API_KEY" \
  -H "X-SQR-Project-ID: ${SQR_PROJECT_ID:?Set SQR_PROJECT_ID}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "sqr",
    "flow": "jira-real-read",
    "messages": [
      { "role": "user", "content": "Execute task" }
    ]
  }'
