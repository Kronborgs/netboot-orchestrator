param(
    [string]$Repo = "Kronborgs/netboot-orchestrator",
    [string]$Workflow = "docker-build.yml",
    [int]$PerPage = 5,
    [string]$TargetSha = "",
    [switch]$Watch,
    [int]$PollSeconds = 10
)

$ErrorActionPreference = "Stop"

function Get-GitHubHeaders {
    param([string]$Token)

    $headers = @{
        "Accept" = "application/vnd.github+json"
        "User-Agent" = "netboot-orchestrator-status-check"
    }

    if ($Token -and $Token.Trim()) {
        $headers["Authorization"] = "Bearer $Token"
    }

    return $headers
}

function Get-TokenFromEnv {
    if ($env:GITHUB_TOKEN -and $env:GITHUB_TOKEN.Trim()) {
        return $env:GITHUB_TOKEN.Trim()
    }
    if ($env:GH_TOKEN -and $env:GH_TOKEN.Trim()) {
        return $env:GH_TOKEN.Trim()
    }
    return ""
}

function Show-RateLimit {
    param([hashtable]$Headers)

    $rate = Invoke-RestMethod -Headers $Headers -Uri "https://api.github.com/rate_limit" -Method Get
    $core = $rate.resources.core
    $resetLocal = [DateTimeOffset]::FromUnixTimeSeconds([int64]$core.reset).ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss zzz")

    Write-Host "Rate limit: $($core.remaining)/$($core.limit) (resets: $resetLocal)"
}

function Get-WorkflowRuns {
    param(
        [hashtable]$Headers,
        [string]$Repo,
        [string]$Workflow,
        [int]$PerPage
    )

    $url = "https://api.github.com/repos/$Repo/actions/workflows/$Workflow/runs?per_page=$PerPage"
    $res = Invoke-RestMethod -Headers $Headers -Uri $url -Method Get
    return @($res.workflow_runs)
}

function Select-Run {
    param(
        [array]$Runs,
        [string]$TargetSha
    )

    if (-not $Runs -or $Runs.Count -eq 0) {
        return $null
    }

    if ($TargetSha -and $TargetSha.Trim()) {
        $short = $TargetSha.Trim().ToLower()
        $match = $Runs | Where-Object { $_.head_sha.ToLower().StartsWith($short) } | Select-Object -First 1
        if ($match) { return $match }
    }

    return $Runs[0]
}

function Show-Run {
    param([object]$Run)

    if (-not $Run) {
        Write-Host "No workflow run found."
        return
    }

    Write-Host "run_number=$($Run.run_number)"
    Write-Host "head_sha=$($Run.head_sha)"
    Write-Host "status=$($Run.status)"
    Write-Host "conclusion=$($Run.conclusion)"
    Write-Host "html_url=$($Run.html_url)"
}

try {
    $token = Get-TokenFromEnv
    $headers = Get-GitHubHeaders -Token $token

    if (-not $token) {
        Write-Host "No token found in GITHUB_TOKEN/GH_TOKEN. Using unauthenticated API (60 requests/hour per IP)."
    }

    Show-RateLimit -Headers $headers

    if ($Watch) {
        while ($true) {
            $runs = Get-WorkflowRuns -Headers $headers -Repo $Repo -Workflow $Workflow -PerPage $PerPage
            $run = Select-Run -Runs $runs -TargetSha $TargetSha
            Show-Run -Run $run

            if ($run -and $run.status -eq "completed") {
                break
            }

            Start-Sleep -Seconds ([Math]::Max(2, $PollSeconds))
        }
    }
    else {
        $runs = Get-WorkflowRuns -Headers $headers -Repo $Repo -Workflow $Workflow -PerPage $PerPage
        $run = Select-Run -Runs $runs -TargetSha $TargetSha
        Show-Run -Run $run
    }
}
catch {
    Write-Error "GitHub status check failed: $($_.Exception.Message)"
    exit 1
}
