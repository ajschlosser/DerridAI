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

$ErrorActionPreference = "Continue"

Write-Host "== docker compose ps ==" -ForegroundColor Cyan
docker compose ps

Write-Host "`n== web logs ==" -ForegroundColor Cyan
docker compose logs --tail=100 web

Write-Host "`n== api logs ==" -ForegroundColor Cyan
docker compose logs --tail=150 api

$webPort = if ($env:WEB_PORT) { $env:WEB_PORT } else { "8181" }
$apiPort = if ($env:API_PORT) { $env:API_PORT } else { "8000" }

Write-Host "`n== HTTP checks ==" -ForegroundColor Cyan
$checks = @(
  "http://127.0.0.1:$webPort/healthz",
  "http://127.0.0.1:$webPort/",
  "http://127.0.0.1:$apiPort/api/live",
  "http://127.0.0.1:$apiPort/api/health",
  "http://127.0.0.1:$apiPort/api/llm/status"
)
foreach ($url in $checks) {
  Write-Host "-- $url"
  try {
    curl.exe -sS -i --max-time 8 $url
  } catch {
    Write-Host $_ -ForegroundColor Red
  }
  Write-Host ""
}

Write-Host "== Ollama from API container ==" -ForegroundColor Cyan
docker compose exec -T api python -c "import os,httpx; u=os.environ.get('OLLAMA_BASE_URL'); print('OLLAMA_BASE_URL=',u); r=httpx.get(u+'/api/tags',timeout=5); print(r.status_code); print(r.text[:1500])"
