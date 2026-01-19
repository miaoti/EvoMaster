# ============================================================
# EvoMaster Black-Box Testing Script for TrainTicket
# ============================================================
# This script:
# 1. Runs EvoMaster with authentication
# 2. Generates tests in the TrainTicket/generated_tests folder
# 3. Analyzes results for injected fault detection
# 4. Creates a detailed log report
# ============================================================

param(
    [string]$TargetUrl = "http://129.62.148.112:32677",
    [string]$MaxTime = "600m",
    [string]$OutputFormat = "PYTHON_UNITTEST"
)

# Configuration
$EvoMasterJar = "..\core\target\evomaster.jar"
$OpenApiFile = "merged_openapi_spec_fixed.yaml"
$OutputFolder = "generated_tests"
$ConfigFile = "em.yaml"

# Generate timestamp for log file
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = "fault_detection_report_$Timestamp.log"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "EvoMaster Black-Box Testing for TrainTicket" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  - Target URL: $TargetUrl"
Write-Host "  - OpenAPI File: $OpenApiFile"
Write-Host "  - Output Folder: $OutputFolder"
Write-Host "  - Max Time: $MaxTime"
Write-Host "  - Output Format: $OutputFormat"
Write-Host "  - Config File: $ConfigFile"
Write-Host ""

# Check if EvoMaster JAR exists
if (-not (Test-Path $EvoMasterJar)) {
    Write-Host "ERROR: EvoMaster JAR not found at $EvoMasterJar" -ForegroundColor Red
    Write-Host "Please build EvoMaster first: mvn clean install -DskipTests" -ForegroundColor Red
    exit 1
}

# Check if OpenAPI file exists
if (-not (Test-Path $OpenApiFile)) {
    Write-Host "ERROR: OpenAPI file not found: $OpenApiFile" -ForegroundColor Red
    exit 1
}

# Check if config file exists
if (-not (Test-Path $ConfigFile)) {
    Write-Host "WARNING: Config file not found: $ConfigFile" -ForegroundColor Yellow
    Write-Host "Running without authentication configuration..." -ForegroundColor Yellow
}

Write-Host "Step 1: Running EvoMaster..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

$evoArgs = @(
    "-jar", $EvoMasterJar,
    "--blackBox", "true",
    "--bbSwaggerUrl", $OpenApiFile,
    "--bbTargetUrl", $TargetUrl,
    "--outputFolder", $OutputFolder,
    "--outputFormat", $OutputFormat,
    "--maxTime", $MaxTime
)

# Add config path if file exists
if (Test-Path $ConfigFile) {
    $evoArgs += @("--configPath", $ConfigFile)
}

Write-Host "Running: java $($evoArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

$process = Start-Process -FilePath "java" -ArgumentList $evoArgs -Wait -PassThru -NoNewWindow

if ($process.ExitCode -ne 0) {
    Write-Host ""
    Write-Host "WARNING: EvoMaster finished with exit code $($process.ExitCode)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Step 2: Analyzing fault detection..." -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green

python analyze_fault_detection.py $OutputFolder $LogFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Fault detection analysis failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "COMPLETE!" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Results saved to:" -ForegroundColor Green
Write-Host "  - Tests: $OutputFolder\" -ForegroundColor White
Write-Host "  - Web Report: $OutputFolder\index.html" -ForegroundColor White
Write-Host "  - Fault Analysis: $LogFile" -ForegroundColor White
Write-Host ""

# Open the web report
$reportPath = Join-Path $OutputFolder "index.html"
if (Test-Path $reportPath) {
    $openReport = Read-Host "Open web report in browser? (Y/n)"
    if ($openReport -ne "n") {
        Start-Process $reportPath
    }
}
