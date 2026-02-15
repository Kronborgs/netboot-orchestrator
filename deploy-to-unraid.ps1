# Netboot Orchestrator - Safe Unraid Deployment Script (PowerShell)
# This script is for running on Windows to deploy to remote Unraid server
# Usage: .\deploy-to-unraid.ps1 -UnraidHost 192.168.1.50 [-Clean]

param(
    [Parameter(Mandatory=$true)]
    [string]$UnraidHost,
    
    [Parameter(Mandatory=$false)]
    [switch]$Clean = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$SSHUser = "root"
)

# Configuration
$projectDir = "/mnt/user/appdata/netboot-orchestrator"
$projectName = "netboot-orchestrator"

# Colors for output
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] " -ForegroundColor Cyan -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

# Check SSH connectivity
function Test-UnraidConnection {
    Write-Info "Testing connection to Unraid server at $UnraidHost..."
    
    try {
        $result = Test-NetConnection -ComputerName $UnraidHost -Port 22 -WarningAction SilentlyContinue
        if ($result.TcpTestSucceeded) {
            Write-Success "Connected to $UnraidHost"
            return $true
        }
        else {
            Write-Error "Cannot connect to $UnraidHost on port 22"
            return $false
        }
    }
    catch {
        Write-Error "Connection test failed: $_"
        return $false
    }
}

# Execute remote command via SSH
function Invoke-RemoteCommand {
    param(
        [string]$Command,
        [string]$Description = ""
    )
    
    if ($Description) {
        Write-Info $Description
    }
    
    $sshCmd = @"
ssh -o StrictHostKeyChecking=no ${SSHUser}@${UnraidHost} "
    set -e
    $Command
"
@
    
    Invoke-Expression $sshCmd
}

# Main deployment function
function Deploy-Unraid {
    Write-Host ""
    Write-Host "=== Netboot Orchestrator Deployment (Remote Unraid) ===" -ForegroundColor Cyan
    Write-Info "Target: $UnraidHost"
    Write-Info "Project directory: $projectDir"
    Write-Info "SAFETY: Only operating within project directory"
    Write-Host ""
    
    # Test connection
    if (-not (Test-UnraidConnection)) {
        Write-Error "Cannot connect to Unraid server. Ensure SSH is enabled and address is correct."
        exit 1
    }
    
    # Ask for confirmation
    $confirm = Read-Host "Continue with deployment? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Warning "Deployment cancelled"
        exit 0
    }
    
    # Create deployment commands
    $deployCmd = @"
#!/bin/bash
set -e

PROJECT_DIR="$projectDir"
COMPOSE_FILE="\${PROJECT_DIR}/docker-compose.yml"
DATA_DIR="\${PROJECT_DIR}/data"
BACKUP_DIR="\${PROJECT_DIR}/backup"

echo "[INFO] Creating project directory..."
mkdir -p "\$PROJECT_DIR"
cd "\$PROJECT_DIR"

echo "[INFO] Cloning/updating repository..."
if [ -d .git ]; then
    git pull origin main 2>/dev/null || echo "[WARNING] Could not pull from origin"
else
    cd /tmp
    rm -rf netboot-orchestrator-temp 2>/dev/null || true
    git clone https://github.com/Kronborgs/netboot-orchestrator.git netboot-orchestrator-temp
    cp -r netboot-orchestrator-temp/* "\$PROJECT_DIR/"
    rm -rf netboot-orchestrator-temp
    cd "\$PROJECT_DIR"
fi

echo "[INFO] Creating backup of data..."
mkdir -p "\$BACKUP_DIR"
if [ -d "\$DATA_DIR" ]; then
    TIMESTAMP=\$(date +%Y%m%d_%H%M%S)
    cp -r "\$DATA_DIR" "\$BACKUP_DIR/backup_\${TIMESTAMP}" || echo "[WARNING] Backup failed"
fi

echo "[INFO] Stopping old containers..."
docker-compose -f "\$COMPOSE_FILE" down 2>/dev/null || true

echo "[INFO] Building Docker images (this may take 10-15 minutes)..."
docker-compose -f "\$COMPOSE_FILE" build --no-cache

echo "[INFO] Creating data directory..."
mkdir -p "\$DATA_DIR"

echo "[INFO] Starting services..."
docker-compose -f "\$COMPOSE_FILE" up -d

echo "[SUCCESS] Deployment complete!"
echo "[INFO] Services:"
echo "  - Web UI: http://$UnraidHost:30000"
echo "  - API: http://$UnraidHost:8000"
echo "  - TFTP: port 69 (UDP)"
echo "  - HTTP: port 8080"
echo "  - iSCSI: port 3260"
"@
    
    # Write script to temp file
    $tempScript = New-TemporaryFile
    $deployCmd | Set-Content $tempScript
    
    try {
        # Copy script to Unraid
        Write-Info "Uploading deployment script..."
        & scp -o StrictHostKeyChecking=no $tempScript "${SSHUser}@${UnraidHost}:/tmp/deploy-netboot.sh" | Out-Null
        
        # Execute script
        Write-Info "Executing deployment script on Unraid..."
        Write-Host ""
        & ssh -o StrictHostKeyChecking=no "${SSHUser}@${UnraidHost}" "bash /tmp/deploy-netboot.sh"
        Write-Host ""
        
        if ($?) {
            Write-Success "Deployment completed successfully!"
        }
        else {
            Write-Error "Deployment script returned an error"
            exit 1
        }
    }
    finally {
        Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
    }
}

# Clean function
function Clean-Unraid {
    Write-Host ""
    Write-Host "=== Cleaning Netboot Orchestrator (Unraid) ===" -ForegroundColor Cyan
    Write-Warning "This will stop and remove containers only (data preserved)"
    Write-Host ""
    
    if (-not (Test-UnraidConnection)) {
        Write-Error "Cannot connect to Unraid server"
        exit 1
    }
    
    $confirm = Read-Host "Continue? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Warning "Cancelled"
        exit 0
    }
    
    Write-Info "Stopping containers..."
    & ssh -o StrictHostKeyChecking=no "${SSHUser}@${UnraidHost}" "cd /mnt/user/appdata/netboot-orchestrator && docker-compose down"
    
    Write-Success "Containers stopped. Data preserved."
    Write-Info "To redeploy: .\deploy-to-unraid.ps1 -UnraidHost $UnraidHost"
}

# Main execution
if ($Clean) {
    Clean-Unraid
}
else {
    Deploy-Unraid
}
