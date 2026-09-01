#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://localhost:8081"
VERSION="v0.1.0"
PROMPT="${1:?Usage: $0 <prompt>}"

# Submit the query and capture the job_id
job_id=$(curl -s -X POST "${BASE_URL}/${VERSION}/query" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"${PROMPT}\"}" | python3 -c 'import sys, json; print(json.load(sys.stdin)["job_id"])')

echo "Submitted job: ${job_id}"

# Poll until status is "done"
while true; do
  response=$(curl -s "${BASE_URL}/${VERSION}/query/${job_id}")
  status=$(echo "${response}" | python3 -c 'import sys, json; print(json.load(sys.stdin)["status"])')

  if [[ "${status}" == "done" ]]; then
    echo "Job complete:"
    echo "${response}" | python3 -m json.tool
    break
  fi

  echo "Status: ${status}... retrying"
  sleep 1
done