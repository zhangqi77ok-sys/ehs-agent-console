#!/usr/bin/env bash
# Ind-05 smoke: validate compose file, bring stack up, hit /health.
# Does not run in default pytest. Requires Docker daemon.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found; skip compose smoke (files still valid for machines with Docker)"
  exit 0
fi

echo "== docker compose config =="
docker compose config >/dev/null
echo "compose config OK"

echo "== docker compose up -d --build =="
docker compose up -d --build

echo "== wait for /health =="
ok=0
for _ in $(seq 1 60); do
  if curl -sf "http://127.0.0.1:${API_PORT:-8000}/health" | grep -q '"status"[[:space:]]*:[[:space:]]*"ok"'; then
    ok=1
    break
  fi
  sleep 2
done

if [[ "$ok" -ne 1 ]]; then
  echo "ERROR: /health did not become ok in time"
  docker compose ps || true
  docker compose logs --tail=80 api || true
  exit 1
fi

curl -s "http://127.0.0.1:${API_PORT:-8000}/health"
echo
echo "compose smoke OK"
