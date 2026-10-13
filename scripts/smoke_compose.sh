#!/usr/bin/env bash
set -euo pipefail
curl -sf http://127.0.0.1:8000/health | grep -q ok
curl -sf -H 'X-Tenant-Id: demo-plant' -H 'X-Role: ehs_engineer' \
  http://127.0.0.1:8000/api/hazards | grep -q HZ-2026
echo "smoke ok"
