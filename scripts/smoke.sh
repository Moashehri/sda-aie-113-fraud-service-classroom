#!/usr/bin/env bash
set -euo pipefail

base_url="${BASE_URL:-http://localhost:8000}"
timeout_seconds="${SMOKE_TIMEOUT_SECONDS:-60}"
payload_path="${PAYLOAD_PATH:-payloads/sample.json}"
deadline=$(( $(date +%s) + timeout_seconds ))

until curl --fail --silent --show-error "${base_url}/v1/ready" >/dev/null; do
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "Timed out after ${timeout_seconds}s waiting for ${base_url}/v1/ready" >&2
    exit 1
  fi
  sleep 1
done

response="$(
  curl --fail --silent --show-error \
    --header "content-type: application/json" \
    --data-binary "@${payload_path}" \
    "${base_url}/v1/predict"
)"

python3 -c '
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
response = json.load(sys.stdin)
required = {"transaction_id", "fraud_probability", "decision", "model_version", "trace_id"}
assert required <= response.keys(), f"missing fields: {required - response.keys()}"
assert response["transaction_id"] == payload["transaction_id"]
assert 0.0 <= response["fraud_probability"] <= 1.0
assert response["decision"] in {"allow", "review", "block"}
assert response["model_version"]
assert response["trace_id"]
' "$payload_path" <<<"$response"

echo "Smoke test passed: ${base_url}/v1/predict returned a valid prediction."
