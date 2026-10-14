#!/usr/bin/env sh
# This file is part of DerridAI, a cELF-compliant research workspace
# Copyright © 2026  Aaron John Schlosser, PhD
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
