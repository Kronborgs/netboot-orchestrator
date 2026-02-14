#!/bin/bash
# version-bump.ps1 - Bump version and create release (PowerShell)

param(
    [switch]$SkipGit = $false
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$versionFile = Join-Path $scriptDir "VERSION"

# Get current date
$currentDate = (Get-Date).ToString("yyyy-MM-dd")

# Read current version
$currentVersion = (Get-Content $versionFile).Trim()
$currentDateFromVersion = $currentVersion -replace '-V\d+$'
$currentV = [int]($currentVersion -replace '^.*-V')

Write-Host "Current version: $currentVersion" -ForegroundColor Cyan
Write-Host "Current date: $currentDate" -ForegroundColor Cyan
Write-Host "Current V number: $currentV" -ForegroundColor Cyan

# Check if we're on the same day
if ($currentDate -eq $currentDateFromVersion) {
    # Increment V number
    $newV = $currentV + 1
} else {
    # New day, reset V to 1
    $newV = 1
}

$newVersion = "$currentDate-V$newV"

Write-Host "New version: $newVersion" -ForegroundColor Green

# Update VERSION file
Set-Content -Path $versionFile -Value $newVersion

# Update README.md badge
$readmeContent = Get-Content (Join-Path $scriptDir "README.md") -Raw
$readmeContent = $readmeContent -replace "Release-\d{4}-\d{2}-\d{2}-V\d+", "Release-$newVersion"
$readmeContent = $readmeContent -replace "Version\*\*: \d{4}-\d{2}-\d{2}-V\d+", "Version**: $newVersion"
$readmeContent = $readmeContent -replace "Last Updated\*\*: .+", "Last Updated**: $currentDate"
Set-Content -Path (Join-Path $scriptDir "README.md") -Value $readmeContent

Write-Host "`n✓ Version bumped to $newVersion" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "1. Review changes: git log --oneline -5" -ForegroundColor Yellow
Write-Host "2. Push: git push origin main && git push origin --tags" -ForegroundColor Yellow
Write-Host "3. Create GitHub release from tag: https://github.com/Kronborgs/netboot-orchestrator/releases/new?tag=$newVersion" -ForegroundColor Yellow

if (-not $SkipGit) {
    Write-Host "`nGit operations:" -ForegroundColor Cyan
    & git add VERSION, README.md, CHANGELOG.md
    & git commit -m "chore(release): bump version to $newVersion"
    & git tag -a "$newVersion" -m "Release version $newVersion"
    Write-Host "✓ Git commit and tag created" -ForegroundColor Green
}
