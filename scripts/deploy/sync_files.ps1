# PowerShell script to sync files to server
param(
    [string]$SourcePath = "d:\work6.05",
    [string]$ServerIP = "8.163.37.124",
    [string]$ServerUser = "novelapp",
    [string]$KeyFile = "d:\work6.05\xsdm.pem",
    [string]$RemotePath = "/home/novelapp/novel-system"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Sync Files to Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Define directories to exclude
$excludeDirs = @('Chrome', '.git', '.venv', 'venv', 'generated_images', 'logs', 'temp_fanqie_upload', 'chapter_failures', '__pycache__', '.vscode', '.idea', '.claude', 'node_modules', 'ai_enhanced_settings', 'fusion_settings', 'optimized_prompts', 'knowledge_base', 'static', 'data', 'tests', 'tools')

Write-Host "Scanning files..." -ForegroundColor Yellow

# Get files to sync
$files = Get-ChildItem -Path $SourcePath -Recurse -Force | Where-Object {
    $relativePath = $_.FullName.Replace($SourcePath, '')
    $firstDir = if ($relativePath -match '^\\+?([^\\]+)') { $matches[1] } else { '' }
    $excludeDirs -notcontains $firstDir -and
    $_.Name -notmatch '\.(pyc|pyo|db|log)$' -and
    $_.Name -notmatch 'test_|check_|diagnose_|debug_' -and
    $_.Name -ne '.env' -and
    $_.Name -ne 'Chrome.rar'
}

Write-Host "Found $($files.Count) files to sync" -ForegroundColor Green

# Create temp directory
$tempDir = Join-Path $env:TEMP "novel_deploy_$(Get-Date -Format 'yyyyMMddHHmmss')"
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
Write-Host "Created temp dir: $tempDir" -ForegroundColor Gray

# Copy files to temp
$copied = 0
foreach ($file in $files) {
    $destPath = Join-Path $tempDir $file.FullName.Replace($SourcePath, '').TrimStart('\')
    $destDir = Split-Path $destPath -Parent
    if (-not (Test-Path $destDir)) {
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
    }
    Copy-Item $file.FullName -Destination $destPath -Force
    $copied++
    if ($copied % 100 -eq 0) {
        Write-Host "Copied $copied / $($files.Count) files" -ForegroundColor Gray
    }
}

Write-Host "Files ready: $copied files" -ForegroundColor Green

# Calculate size
$totalSize = (Get-ChildItem -Path $tempDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "Temp size: $([math]::Round($totalSize, 2)) MB" -ForegroundColor Yellow

# Upload via SCP
Write-Host "Uploading to server..." -ForegroundColor Yellow

$scpArgs = @(
    "-i", $KeyFile,
    "-o", "StrictHostKeyChecking=no",
    "-r",
    "$tempDir\*",
    "$ServerUser@${ServerIP}:${RemotePath}/"
)

$process = Start-Process -FilePath "scp" -ArgumentList $scpArgs -Wait -PassThru -NoNewWindow

if ($process.ExitCode -ne 0) {
    Write-Host "ERROR: SCP upload failed, exit code: $($process.ExitCode)" -ForegroundColor Red
    Remove-Item -Path $tempDir -Recurse -Force
    exit 1
}

Write-Host "Upload success!" -ForegroundColor Green

# Cleanup
Remove-Item -Path $tempDir -Recurse -Force
Write-Host "Temp files cleaned" -ForegroundColor Gray

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Sync Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan