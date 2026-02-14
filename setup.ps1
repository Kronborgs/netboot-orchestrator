@echo off
REM setup.ps1 - Setup script for netboot-orchestrator (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  RPi Netboot Orchestrator - Initial Setup              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Check for Docker
try {
    $dockerVersion = docker --version
    Write-Host "✓ Docker found: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not installed. Please install Docker first." -ForegroundColor Red
    exit 1
}

# Check for Docker Compose
try {
    $composeVersion = docker-compose --version
    Write-Host "✓ Docker Compose found: $composeVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker Compose is not installed. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}

# Create .env from .env.example if it doesn't exist
if (!(Test-Path .env)) {
    Write-Host ""
    Write-Host "📝 Creating .env file from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "✓ .env file created. Edit it if needed." -ForegroundColor Green
} else {
    Write-Host "✓ .env file already exists" -ForegroundColor Green
}

# Create data directory
Write-Host ""
Write-Host "📁 Creating data directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Path "data/http/raspi/kernels/default" -Force | Out-Null
New-Item -ItemType Directory -Path "data/http/raspi/kernels/test" -Force | Out-Null
New-Item -ItemType Directory -Path "data/http/os" -Force | Out-Null
New-Item -ItemType Directory -Path "data/http/ipxe" -Force | Out-Null
New-Item -ItemType Directory -Path "data/tftp/raspi" -Force | Out-Null
New-Item -ItemType Directory -Path "data/tftp/pxe" -Force | Out-Null
New-Item -ItemType Directory -Path "data/iscsi/images" -Force | Out-Null
Write-Host "✓ Data directories created" -ForegroundColor Green

# Show next steps
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Setup Complete! Next Steps:                           ║" -ForegroundColor Cyan
Write-Host "╠════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  1. Edit .env file with your configuration             ║" -ForegroundColor Cyan
Write-Host "║  2. Run: docker-compose up -d                          ║" -ForegroundColor Cyan
Write-Host "║  3. Access UI: http://localhost:3000                   ║" -ForegroundColor Cyan
Write-Host "║  4. API Docs: http://localhost:8000/docs               ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
