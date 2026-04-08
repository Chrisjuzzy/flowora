param(
    [string]$Flyctl = "flyctl",
    [string]$ApiConfig = "infra/fly/flowora-api.toml",
    [string]$WebConfig = "infra/fly/flowora-web.toml",
    [string]$WorkerConfig = "infra/fly/flowora-worker.toml",
    [string]$BeatConfig = "infra/fly/flowora-beat.toml",
    [string]$ApiHealthUrl = "https://flowora-api.fly.dev/api/health",
    [string]$WebUrl = "https://flowora-web.fly.dev",
    [int]$HealthTimeoutSeconds = 20,
    [int]$HealthAttempts = 12,
    [switch]$SkipWeb,
    [switch]$SkipWorkers
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Test-FlyAuth {
    Write-Step "Checking Fly authentication"
    & $Flyctl auth whoami | Out-Host
}

function Invoke-FlyDeploy {
    param(
        [string]$Name,
        [string]$ConfigPath
    )

    Write-Step "Deploying $Name"
    & $Flyctl deploy --config $ConfigPath
}

function Wait-ForHttpOk {
    param(
        [string]$Name,
        [string]$Url
    )

    Write-Step "Waiting for $Name at $Url"
    for ($attempt = 1; $attempt -le $HealthAttempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec $HealthTimeoutSeconds
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                Write-Host "$Name is healthy (HTTP $($response.StatusCode))" -ForegroundColor Green
                return
            }
        } catch {
            Write-Host ("Attempt {0}/{1}: waiting for {2}..." -f $attempt, $HealthAttempts, $Name)
        }
        Start-Sleep -Seconds 5
    }

    throw "$Name did not become healthy at $Url"
}

Test-FlyAuth
Invoke-FlyDeploy -Name "flowora-api" -ConfigPath $ApiConfig
Wait-ForHttpOk -Name "flowora-api" -Url $ApiHealthUrl

if (-not $SkipWeb) {
    Invoke-FlyDeploy -Name "flowora-web" -ConfigPath $WebConfig
    Wait-ForHttpOk -Name "flowora-web" -Url $WebUrl
}

if (-not $SkipWorkers) {
    Invoke-FlyDeploy -Name "flowora-worker" -ConfigPath $WorkerConfig
    Invoke-FlyDeploy -Name "flowora-beat" -ConfigPath $BeatConfig
}

Write-Step "Controlled rollout completed"
