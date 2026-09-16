# Copyright 2026 Aaron John Schlosser, PhD.
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
