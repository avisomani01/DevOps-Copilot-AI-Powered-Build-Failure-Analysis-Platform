[CmdletBinding()]
param(
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$aiService = Join-Path $projectRoot "ai-service"
$backend = Join-Path $projectRoot "backend"
$frontend = Join-Path $projectRoot "frontend"

function Require-Command([string]$name, [string]$installHint) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "$name is not installed or is not on PATH. $installHint"
    }
}

function Start-ServiceWindow([string]$title, [string]$workingDirectory, [string]$command) {
    $arguments = "-NoExit -ExecutionPolicy Bypass -Command `"`$Host.UI.RawUI.WindowTitle = '$title'; Set-Location -LiteralPath '$workingDirectory'; $command`""
    Start-Process -FilePath "powershell.exe" -ArgumentList $arguments -WorkingDirectory $workingDirectory
}

Require-Command "java" "Install a Java 21 JDK."
Require-Command "mvn" "Install Apache Maven, then open a new PowerShell window."
Require-Command "node" "Install Node.js LTS, then open a new PowerShell window."
Require-Command "npm" "Install Node.js LTS, then open a new PowerShell window."

if (-not (Test-Path (Join-Path $aiService "setup.ps1"))) {
    throw "AI service setup script was not found: $aiService"
}

$postgresOpen = Test-NetConnection -ComputerName "localhost" -Port 5432 -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $postgresOpen) {
    throw "PostgreSQL is not accepting connections on localhost:5432. Start its Windows service, then run this script again."
}

$frontendInstall = if ($SkipDependencyInstall) { "" } else { "npm install; " }
Start-ServiceWindow "DevOps Copilot - AI" $aiService ".\setup.ps1 -Serve -SkipTests"
Start-ServiceWindow "DevOps Copilot - Backend" $backend "mvn spring-boot:run"
Start-ServiceWindow "DevOps Copilot - Frontend" $frontend "$frontendInstall npm run dev"

Write-Host "Starting DevOps Copilot services in separate windows..." -ForegroundColor Green
Write-Host "Wait until the Frontend window reports a local URL, then open http://localhost:5173"
