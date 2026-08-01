[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ollamaCommand = Get-Command ollama.exe -ErrorAction SilentlyContinue
if ($null -eq $ollamaCommand) {
    throw "ollama.exe was not found in PATH."
}

$serverSettings = [ordered]@{
    OLLAMA_LLM_LIBRARY      = "cpu_avx2"
    OLLAMA_MAX_LOADED_MODELS = "1"
    OLLAMA_NUM_PARALLEL      = "1"
}

foreach ($entry in $serverSettings.GetEnumerator()) {
    [Environment]::SetEnvironmentVariable(
        $entry.Key,
        $entry.Value,
        "User"
    )
    Set-Item -Path "Env:$($entry.Key)" -Value $entry.Value
}

Get-Process -Name "ollama", "ollama app" -ErrorAction SilentlyContinue |
    Stop-Process -Force
Start-Sleep -Seconds 2

$server = Start-Process `
    -FilePath $ollamaCommand.Source `
    -ArgumentList "serve" `
    -WindowStyle Hidden `
    -PassThru

$versionUri = "http://127.0.0.1:11434/api/version"
$ready = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $null = Invoke-RestMethod -Uri $versionUri -TimeoutSec 2
        $ready = $true
        break
    }
    catch {
        if ($server.HasExited) {
            throw "Ollama exited before its API became ready."
        }
        Start-Sleep -Seconds 1
    }
}

if (-not $ready) {
    throw "Ollama did not become ready within 30 seconds."
}

$probe = [ordered]@{
    model      = "qwen3-embedding:0.6b"
    input      = @("MAAP CPU embedding startup probe.")
    dimensions = 1024
    truncate   = $true
    keep_alive = "10m"
    options    = [ordered]@{
        num_ctx   = 1024
        num_batch = 64
    }
}

$probeJson = $probe | ConvertTo-Json -Depth 6 -Compress
$response = Invoke-RestMethod `
    -Method POST `
    -Uri "http://127.0.0.1:11434/api/embed" `
    -ContentType "application/json; charset=utf-8" `
    -Body ([Text.Encoding]::UTF8.GetBytes($probeJson)) `
    -TimeoutSec 120

$embeddingCount = @($response.embeddings).Count
$dimension = 0
if ($embeddingCount -eq 1) {
    $dimension = @($response.embeddings[0]).Count
}

if ($embeddingCount -ne 1 -or $dimension -ne 1024) {
    throw (
        "Ollama returned an invalid embedding response. " +
        "count=$embeddingCount dimension=$dimension"
    )
}

Write-Host ""
Write-Host "Ollama configuration and embedding probe succeeded." `
    -ForegroundColor Green
Write-Host "Ollama runner: cpu_avx2"
Write-Host "Expected runner options: num_ctx=1024 num_batch=64"
Write-Host "Expected dimension: 1024"
Write-Host ""
& $ollamaCommand.Source ps
