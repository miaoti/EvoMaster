@echo off
REM ============================================================
REM EvoMaster Black-Box Testing Script for TrainTicket
REM ============================================================
REM This script:
REM 1. Runs EvoMaster with authentication
REM 2. Generates tests in the TrainTicket/generated_tests folder
REM 3. Analyzes results for injected fault detection
REM 4. Creates a detailed log report
REM ============================================================

setlocal enabledelayedexpansion

REM Configuration
set "EVOMASTER_JAR=..\core\target\evomaster.jar"
set "OPENAPI_FILE=merged_openapi_spec_fixed.yaml"
set "OUTPUT_FOLDER=generated_tests"
set "TARGET_URL=http://localhost:8080"
set "MAX_TIME=30m"
set "OUTPUT_FORMAT=PYTHON_UNITTEST"

REM Get timestamp for log file
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list') do set datetime=%%I
set "TIMESTAMP=%datetime:~0,8%_%datetime:~8,6%"
set "LOG_FILE=fault_detection_report_%TIMESTAMP%.log"

echo ============================================================
echo EvoMaster Black-Box Testing for TrainTicket
echo ============================================================
echo.
echo Configuration:
echo   - Target URL: %TARGET_URL%
echo   - OpenAPI File: %OPENAPI_FILE%
echo   - Output Folder: %OUTPUT_FOLDER%
echo   - Max Time: %MAX_TIME%
echo   - Output Format: %OUTPUT_FORMAT%
echo.

REM Check if EvoMaster JAR exists
if not exist "%EVOMASTER_JAR%" (
    echo ERROR: EvoMaster JAR not found at %EVOMASTER_JAR%
    echo Please build EvoMaster first: mvn clean install -DskipTests
    exit /b 1
)

REM Check if OpenAPI file exists
if not exist "%OPENAPI_FILE%" (
    echo ERROR: OpenAPI file not found: %OPENAPI_FILE%
    exit /b 1
)

echo Step 1: Running EvoMaster...
echo ============================================================

java -jar "%EVOMASTER_JAR%" ^
    --blackBox true ^
    --bbSwaggerUrl "%OPENAPI_FILE%" ^
    --bbTargetUrl "%TARGET_URL%" ^
    --outputFolder "%OUTPUT_FOLDER%" ^
    --outputFormat %OUTPUT_FORMAT% ^
    --maxTime %MAX_TIME% ^
    --configPath em.yaml

if errorlevel 1 (
    echo.
    echo WARNING: EvoMaster finished with errors or warnings
)

echo.
echo Step 2: Analyzing fault detection...
echo ============================================================

python analyze_fault_detection.py "%OUTPUT_FOLDER%" "%LOG_FILE%"

if errorlevel 1 (
    echo ERROR: Fault detection analysis failed
    exit /b 1
)

echo.
echo ============================================================
echo COMPLETE!
echo ============================================================
echo.
echo Results saved to:
echo   - Tests: %OUTPUT_FOLDER%\
echo   - Web Report: %OUTPUT_FOLDER%\index.html
echo   - Fault Analysis: %LOG_FILE%
echo.

pause
