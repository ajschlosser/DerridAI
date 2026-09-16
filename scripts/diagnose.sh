#!/usr/bin/env sh
# Copyright 2026 Aaron John Schlosser, PhD.
set +e

echo "== docker compose ps =="
docker compose ps

echo
echo "== web logs =="
docker compose logs --tail=100 web

echo
echo "== api logs =="
docker compose logs --tail=150 api

echo
echo "== host HTTP checks =="
WEB_PORT="${WEB_PORT:-8181}"
API_PORT="${API_PORT:-8000}"

if command -v curl >/dev/null 2>&1; then
  for url in \
    "http://127.0.0.1:${WEB_PORT}/healthz" \
    "http://127.0.0.1:${WEB_PORT}/" \
    "http://127.0.0.1:${API_PORT}/api/live" \
    "http://127.0.0.1:${API_PORT}/api/health" \
    "http://127.0.0.1:${API_PORT}/api/llm/status"
  do
    echo "-- $url"
    curl -sS -i --max-time 8 "$url"
    echo
  done
fi

echo "== Ollama from API container =="
docker compose exec -T api python -c "import os,httpx; u=os.environ.get('OLLAMA_BASE_URL'); print('OLLAMA_BASE_URL=',u); r=httpx.get(u+'/api/tags',timeout=5); print(r.status_code); print(r.text[:1500])"
