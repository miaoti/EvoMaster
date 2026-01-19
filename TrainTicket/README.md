# TrainTicket API Black-Box Testing with EvoMaster

This guide explains how to run EvoMaster for black-box testing of the TrainTicket API, including authentication setup and injected fault detection analysis.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running Tests](#running-tests)
- [Viewing Results](#viewing-results)
- [Fault Detection Analysis](#fault-detection-analysis)
- [Configuration Files](#configuration-files)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

1. **EvoMaster built** - The JAR file should be available at `../core/target/evomaster.jar`
   ```powershell
   cd "c:\Users\Tingshuo_Miao2\Documents\GitHub\EvoMaster"
   mvn clean install -DskipTests
   ```

2. **TrainTicket API running** - Your API must be accessible (default: `http://129.62.148.112:32677`)

3. **Python 3** - Required for fault detection analysis script

4. **Fixed OpenAPI spec** - Use `merged_openapi_spec_fixed.yaml` (schema references have been fixed)

---

## Setup

### 1. Fix OpenAPI Schema References (Already Done)

The original OpenAPI file had generic `api_` prefixes that needed to be replaced with service-specific prefixes. This has been fixed using `fix_openapi_schema.py`.

**Fixed file:** `merged_openapi_spec_fixed.yaml`

### 2. Configure Authentication

Authentication is configured in `em.yaml`:

```yaml
auth:
  - name: admin
    loginEndpointAuth:
      endpoint: /api/v1/users/login
      verb: POST
      contentType: application/json
      payloadUserPwd:
        username: admin
        password: "222222"
        usernameField: username
        passwordField: password
      token:
        headerPrefix: "Bearer "
        extractFromField: "/data/token"
        httpHeaderName: "Authorization"
```

**Note:** If your login endpoint or response format differs, update `em.yaml` accordingly.

---

## Running Tests

### Option 1: Using PowerShell Script (Recommended)

```powershell
cd "c:\Users\Tingshuo_Miao2\Documents\GitHub\EvoMaster\TrainTicket"

# Default settings (localhost:8080, 30 minutes)
.\run_evomaster_test.ps1

# Custom settings
.\run_evomaster_test.ps1 -TargetUrl "http://your-api-host:port" -MaxTime "1h"
```

### Option 2: Using Batch Script

```cmd
cd "c:\Users\Tingshuo_Miao2\Documents\GitHub\EvoMaster\TrainTicket"
run_evomaster_test.bat
```

**Edit `run_evomaster_test.bat`** to change `TARGET_URL` if needed.

### Option 3: Manual Command

```powershell
cd "c:\Users\Tingshuo_Miao2\Documents\GitHub\EvoMaster\TrainTicket"

java -jar ..\core\target\evomaster.jar `
    --blackBox true `
    --bbSwaggerUrl "merged_openapi_spec_fixed.yaml" `
    --bbTargetUrl "http://localhost:8080" `
    --outputFolder "generated_tests" `
    --outputFormat PYTHON_UNITTEST `
    --maxTime 30m `
    --configPath em.yaml
```

**Parameters:**
- `--blackBox true` - Enable black-box testing mode
- `--bbSwaggerUrl` - Path to OpenAPI/Swagger file
- `--bbTargetUrl` - URL where your API is running
- `--outputFolder` - Where to save generated tests
- `--outputFormat` - Test format (PYTHON_UNITTEST, JAVA_JUNIT_5, etc.)
- `--maxTime` - How long to run (e.g., `30m`, `1h`, `24h`)
- `--configPath` - Path to authentication config file

---

## Viewing Results

### 1. Interactive Web Report

Open the generated HTML report in your browser:

```powershell
start generated_tests\index.html
```

Or navigate to: `TrainTicket\generated_tests\index.html`

The report shows:
- Overall coverage statistics
- Endpoint coverage breakdown
- Detected faults/errors
- Test case details
- Visual charts and graphs

### 2. Generated Test Files

Test files are located in `generated_tests\`:

- `EvoMaster_faults_Test.py` - Tests that detected potential faults
- `EvoMaster_successes_Test.py` - Tests that passed successfully
- `EvoMaster_others_Test.py` - Other test cases
- `em_test_utils.py` - Utility functions for tests

### 3. JSON Report

`generated_tests\report.json` contains all test data in JSON format.

---

## Fault Detection Analysis

After running EvoMaster, analyze which injected faults were detected:

```powershell
python analyze_fault_detection.py generated_tests
```

This generates a log file: `fault_detection_report_YYYYMMDD_HHMMSS.log`

### Injected Faults (10 Total)

The analysis checks for these 10 injected faults:

1. **INVALID_CONTACTS_NAME_FAULT** (ts-admin-order-service)
   - APIs: `POST /api/v1/adminorderservice/adminorder`, `PUT /api/v1/adminorderservice/adminorder`
   - Trigger: `contactsName` is null, empty, or purely numeric

2. **INVALID_SEAT_NUMBER_FAULT** (ts-admin-order-service)
   - APIs: `POST /api/v1/adminorderservice/adminorder`, `PUT /api/v1/adminorderservice/adminorder`
   - Trigger: `seatNumber` doesn't follow format (digits + uppercase letter)

3. **INVALID_PRICE_RATE_FAULT** (ts-admin-basic-info-service)
   - API: `POST /api/v1/adminbasicservice/adminbasic/prices`
   - Trigger: Price rates are non-positive

4. **INVALID_ROUTE_ID_FAULT** (ts-admin-basic-info-service)
   - API: `POST /api/v1/adminbasicservice/adminbasic/prices`
   - Trigger: `routeId` is null or empty

5. **INVALID_STATION_NAME_FAULT** (ts-travel-plan-service)
   - API: `POST /api/v1/travelplanservice/travelPlan/minStation`
   - Trigger: Station names are null or empty

6. **INVALID_STATION_LENGTH_FAULT** (ts-travel-plan-service)
   - API: `POST /api/v1/travelplanservice/travelPlan/minStation`
   - Trigger: Station name length outside valid range (2-50 chars)

7. **INVALID_TRIP_ID_FORMAT_FAULT** (ts-admin-travel-service)
   - API: `DELETE /api/v1/admintravelservice/admintravel/{tripId}`
   - Trigger: `tripId` is null or empty

8. **INVALID_TRIP_ID_LENGTH_FAULT** (ts-admin-travel-service)
   - API: `DELETE /api/v1/admintravelservice/admintravel/{tripId}`
   - Trigger: `tripId` length invalid (4-20 chars)

9. **INSUFFICIENT_STATIONS_FAULT** (ts-admin-route-service)
   - API: `POST /api/v1/adminrouteservice/adminroute`
   - Trigger: Station list has fewer than 2 stations

10. **INVALID_STATION_NAME_LENGTH_FAULT** (ts-admin-route-service)
    - API: `POST /api/v1/adminrouteservice/adminroute`
    - Trigger: Station name length outside valid range

### Fault Detection Indicators

Injected faults can be identified by:
- **HTTP Status Code:** `400 Bad Request`
- **Response status:** `0` (failure) in response body
- **Response contains:** `"isInjected": true`
- **Response contains:** Specific `faultName` field

---

## Configuration Files

### `em.yaml` - EvoMaster Configuration

Contains authentication settings and common options.

**Key settings:**
- `auth` - Login credentials and token extraction
- `blackBox: true` - Black-box testing mode
- `outputFormat: PYTHON_UNITTEST` - Test output format
- `maxTime: 30m` - Default search time

### `merged_openapi_spec_fixed.yaml` - OpenAPI Specification

Fixed version of the OpenAPI spec with correct schema references (service-specific prefixes instead of generic `api_`).

### `analyze_fault_detection.py` - Fault Analysis Script

Python script that analyzes test results to identify detected injected faults.

**Usage:**
```powershell
python analyze_fault_detection.py [test_folder] [output_log_file]
```

---

## Troubleshooting

### Issue: "EvoMaster JAR not found"

**Solution:** Build EvoMaster first:
```powershell
cd "c:\Users\Tingshuo_Miao2\Documents\GitHub\EvoMaster"
mvn clean install -DskipTests
```

### Issue: "401 Unauthorized" errors

**Possible causes:**
1. Authentication not configured correctly
2. Login endpoint URL is wrong
3. Token extraction path is incorrect

**Solution:** 
- Check `em.yaml` configuration
- Verify login endpoint: `POST /api/v1/users/login`
- Check token response format and update `extractFromField` if needed

### Issue: No faults detected

**Possible causes:**
1. API not running or unreachable
2. Authentication failed (can't access admin endpoints)
3. Test time too short
4. API endpoints not covered

**Solutions:**
- Verify API is running: `curl http://localhost:8080/api/v1/users/login`
- Increase test time: `--maxTime 1h` or `--maxTime 24h`
- Check web report for endpoint coverage
- Verify authentication is working

### Issue: Schema reference errors

**Solution:** Use `merged_openapi_spec_fixed.yaml` instead of the original file. The fixed file has correct service-specific schema references.

### Issue: Python script errors

**Solution:** Ensure Python 3 is installed and accessible:
```powershell
python --version
```

---

## Quick Reference

### Run EvoMaster
```powershell
.\run_evomaster_test.ps1 -TargetUrl "http://localhost:8080" -MaxTime "1h"
```

### Analyze Faults
```powershell
python analyze_fault_detection.py generated_tests
```

### View Web Report
```powershell
start generated_tests\index.html
```

### View Log File
```powershell
Get-Content fault_detection_report_*.log | more
```

---

## File Structure

```
TrainTicket/
├── README.md                          # This file
├── em.yaml                            # EvoMaster auth configuration
├── merged_openapi_spec_fixed.yaml     # Fixed OpenAPI spec
├── merged_openapi_spec 1.yaml         # Original OpenAPI spec
├── fix_openapi_schema.py              # Script to fix schema references
├── analyze_fault_detection.py         # Fault detection analysis script
├── run_evomaster_test.ps1             # PowerShell test runner
├── run_evomaster_test.bat             # Batch test runner
├── generated_tests/                   # Generated test files
│   ├── index.html                     # Web report
│   ├── report.json                    # JSON report
│   ├── EvoMaster_faults_Test.py      # Fault detection tests
│   ├── EvoMaster_successes_Test.py    # Success tests
│   └── EvoMaster_others_Test.py       # Other tests
└── fault_detection_report_*.log       # Fault analysis logs
```

---

## Additional Resources

- [EvoMaster Documentation](https://github.com/WebFuzzing/EvoMaster)
- [EvoMaster Black-Box Testing Guide](../docs/blackbox.md)
- [EvoMaster Authentication Guide](../docs/auth.md)
- [EvoMaster CLI Options](../docs/options.md)

---

## Notes

- **Test Duration:** Longer test runs (1-24 hours) typically yield better coverage and fault detection
- **Authentication:** Admin endpoints require authentication - ensure `em.yaml` is correctly configured
- **Rate Limiting:** For remote APIs, consider adding `--ratePerMinute 60` to avoid DoS
- **Local Testing:** Rate limiting is not needed for localhost testing

---

**Last Updated:** January 2026
