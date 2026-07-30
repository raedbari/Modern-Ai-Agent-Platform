[CmdletBinding()]
param(
    [switch]$Build
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$composeEnv = Join-Path $projectRoot ".env.compose"
$backendEnv = Join-Path $projectRoot "backend\.env"

if (-not (Test-Path (Join-Path $projectRoot "compose.local.yaml"))) {
    throw "compose.local.yaml was not found. Run this script from the repository."
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker CLI was not found."
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop is not running."
}

try {
    $null = Invoke-RestMethod `
        -Uri "http://127.0.0.1:11434/api/version" `
        -TimeoutSec 5
    $ollamaTags = Invoke-RestMethod `
        -Uri "http://127.0.0.1:11434/api/tags" `
        -TimeoutSec 10
} catch {
    throw "Ollama is not reachable on http://127.0.0.1:11434."
}

$embeddingModel = "qwen3-embedding:0.6b"
$availableModels = @($ollamaTags.models | ForEach-Object { $_.name })
if ($embeddingModel -notin $availableModels) {
    throw "Ollama model '$embeddingModel' is not installed."
}

if (-not (Test-Path $composeEnv)) {
    $passwordBytes = [Security.Cryptography.RandomNumberGenerator]::GetBytes(32)
    $password = [Convert]::ToHexString($passwordBytes).ToLowerInvariant()
    @(
        "MAAP_POSTGRES_USER=maap"
        "MAAP_POSTGRES_PASSWORD=$password"
        "MAAP_POSTGRES_DB=maap"
        "MAAP_POSTGRES_PORT=5433"
        "MAAP_API_PORT=8000"
        "MAAP_RUNTIME_ENVIRONMENT=development"
    ) | Set-Content -LiteralPath $composeEnv -Encoding utf8
    Write-Host "Created .env.compose with a random local database password."
}

if (-not (Test-Path $backendEnv)) {
    Copy-Item `
        -LiteralPath (Join-Path $projectRoot "backend\.env.example") `
        -Destination $backendEnv
    Write-Host "Created backend\.env. Add MAAP_DEEPSEEK_API_KEY before live chat."
}

$arguments = @(
    "compose",
    "--env-file", $composeEnv,
    "-f", (Join-Path $projectRoot "compose.local.yaml"),
    "up", "-d"
)
if ($Build) {
    $arguments += "--build"
}

& docker @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose failed."
}

& docker compose `
    --env-file $composeEnv `
    -f (Join-Path $projectRoot "compose.local.yaml") `
    ps

$apiPort = (
    Get-Content -LiteralPath $composeEnv |
    Where-Object { $_ -match "^MAAP_API_PORT=" } |
    Select-Object -First 1
) -replace "^MAAP_API_PORT=", ""
if (-not $apiPort) {
    $apiPort = "8000"
}

$readyUri = "http://127.0.0.1:$apiPort/ready"
$isReady = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $ready = Invoke-RestMethod -Uri $readyUri -TimeoutSec 3
        if ($ready.status -eq "ready") {
            $isReady = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $isReady) {
    & docker compose `
        --env-file $composeEnv `
        -f (Join-Path $projectRoot "compose.local.yaml") `
        logs --tail 100 api ingestion-worker migrate postgres storage-init
    throw "The local API did not become ready."
}

$runningServices = @(
    & docker compose `
        --env-file $composeEnv `
        -f (Join-Path $projectRoot "compose.local.yaml") `
        ps --status running --services
)
if ("ingestion-worker" -notin $runningServices) {
    & docker compose `
        --env-file $composeEnv `
        -f (Join-Path $projectRoot "compose.local.yaml") `
        logs --tail 100 ingestion-worker
    throw "The ingestion worker is not running."
}

Write-Host ""
Write-Host "Local API: http://127.0.0.1:$apiPort"
Write-Host "API docs:  http://127.0.0.1:$apiPort/docs"
