#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-docker-compose.yml}"
base_url="${BASE_URL:-http://localhost:8000}"
timeout_seconds="${STARTUP_TIMEOUT_SECONDS:-90}"

start_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"
docker compose --file "$compose_file" up --build --detach fraud-api feature-cache

deadline=$(( $(date +%s) + timeout_seconds ))
until curl --fail --silent --show-error "${base_url}/v1/ready" >/dev/null; do
  if [ "$(date +%s)" -ge "$deadline" ]; then
    echo "Timed out after ${timeout_seconds}s waiting for ${base_url}/v1/ready" >&2
    exit 1
  fi
  sleep 1
done

end_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"
python3 -c 'import sys; print(f"time_to_ready_seconds={(int(sys.argv[2]) - int(sys.argv[1])) / 1_000_000_000:.3f}")' "$start_ns" "$end_ns"
