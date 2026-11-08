# Run the installed project flow; SQR_API_KEY is an engine project key.
export SQR_PROJECT_ID="${SQR_PROJECT_ID:?Set SQR_PROJECT_ID}"
export SQR_BASE_URL="${SQR_BASE_URL:?Set SQR_BASE_URL}"
payload="$(python3 -c 'import json,os; print(json.dumps({"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ask","arguments":{"question":os.environ["SQR_TASK"]}}}))')"
project_path="$(python3 -c 'import os,urllib.parse; print(urllib.parse.quote(os.environ["SQR_PROJECT_ID"],safe=""))')"
curl --fail-with-body --max-time 30 -X POST "${SQR_BASE_URL}/mcp/p/$project_path" \
  -H "Authorization: Bearer $SQR_API_KEY" \
  -H "X-SQR-Project-ID: ${SQR_PROJECT_ID}" \
  -H "Content-Type: application/json" \
  --data-binary "$payload"
