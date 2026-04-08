param(
    [string]$EnvFile = ".env.prod"
)

if (-not (Test-Path $EnvFile)) {
    throw "Env file not found: $EnvFile"
}

function Parse-EnvFile {
    param([string]$Path)
    $map = [ordered]@{}
    foreach ($line in Get-Content -Path $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }
        $parts = $trimmed -split "=", 2
        if ($parts.Count -ne 2) {
            continue
        }
        $key = $parts[0].Trim()
        $value = $parts[1].Trim()
        $map[$key] = $value
    }
    return $map
}

function Quote-Value {
    param([string]$Value)
    return '"' + ($Value -replace '"', '\"') + '"'
}

$envMap = Parse-EnvFile -Path $EnvFile

$backendKeys = @(
    "SECRET_KEY",
    "DATABASE_URL",
    "REDIS_URL",
    "CELERY_BROKER_URL",
    "CELERY_RESULT_BACKEND",
    "FRONTEND_URL",
    "ALLOWED_ORIGINS",
    "DEFAULT_AI_PROVIDER",
    "DEFAULT_AI_MODEL",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "REQUEST_TIMEOUT_SECONDS",
    "TIMEOUT_BUFFER_SECONDS",
    "OLLAMA_TIMEOUT_SECONDS",
    "EMAIL_VERIFICATION_REQUIRED",
    "AUTO_VERIFY_EMAIL",
    "EMAIL_VERIFICATION_TOKEN_TTL_MINUTES",
    "ALLOW_LLM_MOCK_FALLBACK",
    "RATE_LIMIT_USER_PER_MINUTE",
    "PROMPT_FILTER_ENABLED",
    "PROMPT_MAX_CHARS",
    "MINIO_ENDPOINT",
    "MINIO_ACCESS_KEY",
    "MINIO_SECRET_KEY",
    "MINIO_BUCKET",
    "MINIO_SECURE",
    "SMTP_HOST",
    "SMTP_PORT",
    "SMTP_USER",
    "SMTP_PASSWORD",
    "FROM_EMAIL",
    "ENVIRONMENT",
    "LOG_LEVEL"
)

$frontendKeys = @(
    "NEXT_PUBLIC_API_URL",
    "NEXT_PUBLIC_SITE_URL",
    "NEXT_PUBLIC_DEMO_AGENT_ID",
    "TRAEFIK_DOMAIN"
)

function Build-FlySecretsCommand {
    param(
        [string]$AppName,
        [string[]]$Keys
    )

    $pairs = @()
    foreach ($key in $Keys) {
        if ($envMap.Contains($key) -and $envMap[$key] -ne "") {
            $pairs += "$key=$(Quote-Value $envMap[$key])"
        }
    }

    if (-not $pairs.Count) {
        return "# No values found for $AppName"
    }

    return "fly secrets set " + ($pairs -join " ") + " --app $AppName"
}

Write-Output "# Flowora Fly secrets commands generated from $EnvFile"
Write-Output ""
Write-Output "## API"
Write-Output (Build-FlySecretsCommand -AppName "flowora-api" -Keys $backendKeys)
Write-Output ""
Write-Output "## Worker"
Write-Output (Build-FlySecretsCommand -AppName "flowora-worker" -Keys $backendKeys)
Write-Output ""
Write-Output "## Beat"
Write-Output (Build-FlySecretsCommand -AppName "flowora-beat" -Keys $backendKeys)
Write-Output ""
Write-Output "## Web"
Write-Output (Build-FlySecretsCommand -AppName "flowora-web" -Keys $frontendKeys)
