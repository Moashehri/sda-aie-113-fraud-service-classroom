#!/usr/bin/env bash
set -euo pipefail

cache_image="${CACHE_IMAGE:-fraud-service:cache-check}"
temp_dir="$(mktemp -d)"
context_dir="${temp_dir}/context"
log_file="${temp_dir}/warm-build.log"
trap 'rm -rf "$temp_dir"' EXIT

mkdir -p "$context_dir"
rsync -a \
  --exclude .git \
  --exclude .venv \
  --exclude .ruff_cache \
  --exclude .pytest_cache \
  --exclude scored.csv \
  ./ "$context_dir/"

docker build --no-cache --progress=plain --tag "$cache_image" "$context_dir" >/dev/null
printf '\n# Temporary source-only cache measurement change\n' >> "$context_dir/src/fraud_service/api/routes.py"

start_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"
docker build --progress=plain --tag "$cache_image" "$context_dir" 2>&1 | tee "$log_file"
end_ns="$(python3 -c 'import time; print(time.monotonic_ns())')"

elapsed="$(python3 -c 'import sys; print(f"{(int(sys.argv[2]) - int(sys.argv[1])) / 1_000_000_000:.3f}")' "$start_ns" "$end_ns")"
echo "source_changed_warm_rebuild_seconds=${elapsed}"

if awk '
  /pip install --no-cache-dir --prefix=\/install/ { dependency_step = 1; next }
  dependency_step && /CACHED/ { cache_hit = 1 }
  END { exit !cache_hit }
' "$log_file"; then
  echo "dependency_layer_cache_hit=true"
else
  echo "dependency_layer_cache_hit=not_detected"
  exit 1
fi
