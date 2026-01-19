#!/usr/bin/env python3
"""
Fault Detection Analysis Script for TrainTicket API Testing

This script analyzes EvoMaster test results to identify which injected faults were detected.
It outputs a detailed log file with detection results in a formatted report.

Usage:
    python analyze_fault_detection.py [generated_tests_folder] [output_log_file]
    
Default:
    - generated_tests_folder: ./generated_tests
    - output_log_file: ./fault_detection_report_<timestamp>.log
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict


# Define all injected faults
INJECTED_FAULTS = [
    {
        "faultName": "INVALID_CONTACTS_NAME_FAULT",
        "service": "ts-admin-order-service",
        "api": ["POST /api/v1/adminorderservice/adminorder", "PUT /api/v1/adminorderservice/adminorder"],
        "description": "Rejects order when contactsName is null, empty, or purely numeric"
    },
    {
        "faultName": "INVALID_SEAT_NUMBER_FAULT",
        "service": "ts-admin-order-service",
        "api": ["POST /api/v1/adminorderservice/adminorder", "PUT /api/v1/adminorderservice/adminorder"],
        "description": "Rejects order when seatNumber doesn't follow format (digits + uppercase letter)"
    },
    {
        "faultName": "INVALID_PRICE_RATE_FAULT",
        "service": "ts-admin-basic-info-service",
        "api": ["POST /api/v1/adminbasicservice/adminbasic/prices"],
        "description": "Rejects price creation when price rates are non-positive"
    },
    {
        "faultName": "INVALID_ROUTE_ID_FAULT",
        "service": "ts-admin-basic-info-service",
        "api": ["POST /api/v1/adminbasicservice/adminbasic/prices"],
        "description": "Rejects price creation when routeId is null or empty"
    },
    {
        "faultName": "INVALID_STATION_NAME_FAULT",
        "service": "ts-travel-plan-service",
        "api": ["POST /api/v1/travelplanservice/travelPlan/minStation"],
        "description": "Rejects travel plan when station names are null or empty"
    },
    {
        "faultName": "INVALID_STATION_LENGTH_FAULT",
        "service": "ts-travel-plan-service",
        "api": ["POST /api/v1/travelplanservice/travelPlan/minStation"],
        "description": "Rejects travel plan when station name length is outside valid range"
    },
    {
        "faultName": "INVALID_TRIP_ID_FORMAT_FAULT",
        "service": "ts-admin-travel-service",
        "api": ["DELETE /api/v1/admintravelservice/admintravel/{tripId}"],
        "description": "Rejects trip deletion when tripId is null or empty"
    },
    {
        "faultName": "INVALID_TRIP_ID_LENGTH_FAULT",
        "service": "ts-admin-travel-service",
        "api": ["DELETE /api/v1/admintravelservice/admintravel/{tripId}"],
        "description": "Rejects trip deletion when tripId length is invalid"
    },
    {
        "faultName": "INSUFFICIENT_STATIONS_FAULT",
        "service": "ts-admin-route-service",
        "api": ["POST /api/v1/adminrouteservice/adminroute"],
        "description": "Rejects route creation when station list has fewer than 2 stations"
    },
    {
        "faultName": "INVALID_STATION_NAME_LENGTH_FAULT",
        "service": "ts-admin-route-service",
        "api": ["POST /api/v1/adminrouteservice/adminroute"],
        "description": "Rejects route creation when station name length is outside valid range"
    }
]


class FaultDetectionAnalyzer:
    def __init__(self, test_folder):
        self.test_folder = Path(test_folder)
        self.detected_faults = defaultdict(list)  # fault_name -> list of detection details
        self.total_test_cases = 0
        self.experiment_name = f"trainticket_evomaster_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.tracking_started = None
        self.report_json_data = None
        
    def analyze(self):
        """Run all analysis methods."""
        self._analyze_report_json()
        self._analyze_test_files()
        self._count_test_cases()
        
    def _analyze_report_json(self):
        """Analyze the report.json file for fault detection."""
        report_path = self.test_folder / "report.json"
        
        if not report_path.exists():
            return
        
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                self.report_json_data = json.load(f)
            
            # Try to extract experiment metadata
            if isinstance(self.report_json_data, dict):
                # Look for timestamp or other metadata
                self._search_json_for_faults(self.report_json_data, "report.json")
                    
        except Exception as e:
            print(f"Warning: Error reading report.json: {e}")
    
    def _search_json_for_faults(self, obj, source, path=""):
        """Recursively search JSON for fault indicators."""
        if isinstance(obj, dict):
            # Check for isInjected flag
            if obj.get('isInjected') == True:
                fault_name = obj.get('faultName', 'UNKNOWN')
                self._record_detection(fault_name, {
                    'source': source,
                    'path': path,
                    'message': obj.get('message', ''),
                    'details': obj.get('details', ''),
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            # Check for fault name in string values
            for key, value in obj.items():
                if isinstance(value, str):
                    for fault in INJECTED_FAULTS:
                        if fault['faultName'] in value:
                            self._record_detection(fault['faultName'], {
                                'source': source,
                                'path': f"{path}.{key}" if path else key,
                                'context': value[:200],
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                else:
                    self._search_json_for_faults(value, source, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._search_json_for_faults(item, source, f"{path}[{i}]")
    
    def _analyze_test_files(self):
        """Analyze generated test files for fault-related patterns."""
        test_files = list(self.test_folder.glob("*.py"))
        
        for test_file in test_files:
            if test_file.name.startswith('__') or test_file.name == 'em_test_utils.py':
                continue
            
            try:
                content = test_file.read_text(encoding='utf-8')
                self._analyze_test_content(content, test_file.name)
            except Exception as e:
                print(f"Warning: Error reading {test_file.name}: {e}")
    
    def _analyze_test_content(self, content, filename):
        """Analyze test file content for fault detections."""
        # Find all test methods
        test_methods = re.findall(r'def (test_\w+)\(self\):', content)
        
        # Search for fault patterns
        for fault in INJECTED_FAULTS:
            fault_name = fault['faultName']
            
            # Direct fault name match
            if fault_name in content:
                # Find context around each match
                for match in re.finditer(re.escape(fault_name), content):
                    # Try to find the test method this belongs to
                    test_method = self._find_containing_test_method(content, match.start())
                    
                    self._record_detection(fault_name, {
                        'source': filename,
                        'test_class': filename.replace('.py', ''),
                        'test_method': test_method or 'unknown',
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            # Check for isInjected pattern
            if '"isInjected": true' in content or "'isInjected': true" in content.lower():
                # Find associated fault names
                pattern = r'["\']isInjected["\']\s*:\s*[Tt]rue.*?["\']faultName["\']\s*:\s*["\'](\w+)["\']'
                for match in re.finditer(pattern, content, re.DOTALL):
                    found_fault = match.group(1)
                    if found_fault == fault_name:
                        test_method = self._find_containing_test_method(content, match.start())
                        self._record_detection(fault_name, {
                            'source': filename,
                            'test_class': filename.replace('.py', ''),
                            'test_method': test_method or 'unknown',
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
            
            # Check for API endpoint + 400 status code pattern
            for api in fault['api']:
                method, path = api.split(' ', 1)
                # Normalize path for regex
                path_pattern = path.replace('{tripId}', r'[^"\']+').replace('/', r'/')
                
                # Look for the API path in the content
                if re.search(path_pattern, content):
                    # Check if there's a 400 status nearby or fault indication
                    api_matches = list(re.finditer(path_pattern, content))
                    for api_match in api_matches:
                        # Get surrounding context (500 chars before and after)
                        start = max(0, api_match.start() - 500)
                        end = min(len(content), api_match.end() + 500)
                        context = content[start:end]
                        
                        # Check for 400 status or fault indicators in context
                        if ('400' in context or 'status": 0' in context or 
                            'isInjected' in context or fault_name in context):
                            test_method = self._find_containing_test_method(content, api_match.start())
                            # Only record if not already recorded for this test method
                            existing = [d for d in self.detected_faults.get(fault_name, []) 
                                        if d.get('test_method') == test_method]
                            if not existing:
                                self._record_detection(fault_name, {
                                    'source': filename,
                                    'test_class': filename.replace('.py', ''),
                                    'test_method': test_method or 'unknown',
                                    'api_path': path,
                                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
    
    def _find_containing_test_method(self, content, position):
        """Find the test method that contains the given position."""
        # Find all test method definitions before this position
        test_defs = list(re.finditer(r'def (test_\w+)\(self\):', content[:position]))
        if test_defs:
            return test_defs[-1].group(1)
        return None
    
    def _record_detection(self, fault_name, details):
        """Record a fault detection, avoiding duplicates."""
        # Check for duplicates
        for existing in self.detected_faults[fault_name]:
            if (existing.get('test_method') == details.get('test_method') and 
                existing.get('source') == details.get('source')):
                return  # Skip duplicate
        
        self.detected_faults[fault_name].append(details)
    
    def _count_test_cases(self):
        """Count total test cases in the generated files."""
        test_files = list(self.test_folder.glob("EvoMaster_*.py"))
        
        for test_file in test_files:
            try:
                content = test_file.read_text(encoding='utf-8')
                # Count test methods
                test_methods = re.findall(r'def test_\w+\(self\):', content)
                self.total_test_cases += len(test_methods)
            except:
                pass
    
    def generate_progress_bar(self, percentage, width=50):
        """Generate a text-based progress bar."""
        filled = int(width * percentage / 100)
        bar = '#' * filled + '-' * (width - filled)
        return f"[{bar}] {percentage:.1f}%"
    
    def generate_report(self, output_file):
        """Generate the formatted fault detection report."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate statistics
        total_faults = len(INJECTED_FAULTS)
        detected_count = len([f for f in INJECTED_FAULTS if self.detected_faults.get(f['faultName'])])
        undetected_count = total_faults - detected_count
        detection_percentage = (detected_count / total_faults * 100) if total_faults > 0 else 0
        
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("                    FAULT DETECTION SUMMARY REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Experiment:         {self.experiment_name}")
        lines.append(f"Generated:          {timestamp}")
        lines.append(f"Test Folder:        {self.test_folder}")
        lines.append(f"Total Test Cases:   {self.total_test_cases}")
        lines.append("")
        
        # Fault Coverage Summary
        lines.append("=" * 80)
        lines.append("FAULT COVERAGE SUMMARY")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Total Injected Faults:    {total_faults}")
        lines.append(f"Detected Faults:          {detected_count} ({detection_percentage:.1f}%)")
        lines.append(f"Undetected Faults:        {undetected_count} ({100 - detection_percentage:.1f}%)")
        lines.append("")
        lines.append("Detection Progress:")
        lines.append(self.generate_progress_bar(detection_percentage))
        lines.append("")
        
        # Detected Faults Section
        lines.append("=" * 80)
        lines.append(f"DETECTED FAULTS ({detected_count})")
        lines.append("=" * 80)
        lines.append("")
        
        detected_fault_num = 0
        for fault in INJECTED_FAULTS:
            fault_name = fault['faultName']
            detections = self.detected_faults.get(fault_name, [])
            
            if detections:
                detected_fault_num += 1
                lines.append(f"{detected_fault_num}. {fault_name}")
                lines.append(f"   Service:       {fault['service']}")
                lines.append(f"   API:           {', '.join(fault['api'])}")
                lines.append(f"   Description:   {fault['description']}")
                lines.append(f"   Detections:    {len(detections)} time(s)")
                lines.append("")
                
                # Show up to 5 detection details
                for i, detection in enumerate(detections[:5], 1):
                    lines.append(f"   Detection #{i}:")
                    if detection.get('test_class'):
                        lines.append(f"     Test Class:  {detection['test_class']}")
                    if detection.get('test_method'):
                        lines.append(f"     Test Method: {detection['test_method']}")
                    if detection.get('source') and not detection.get('test_class'):
                        lines.append(f"     Source:      {detection['source']}")
                    if detection.get('api_path'):
                        lines.append(f"     API Path:    {detection['api_path']}")
                    if detection.get('timestamp'):
                        lines.append(f"     Timestamp:   {detection['timestamp']}")
                    lines.append("")
                
                if len(detections) > 5:
                    lines.append(f"   ... and {len(detections) - 5} more detection(s)")
                    lines.append("")
                
                lines.append("-" * 80)
                lines.append("")
        
        if detected_count == 0:
            lines.append("No faults were detected in this test run.")
            lines.append("")
        
        # Undetected Faults Section
        lines.append("=" * 80)
        lines.append(f"UNDETECTED FAULTS ({undetected_count})")
        lines.append("=" * 80)
        lines.append("")
        
        undetected_fault_num = 0
        for fault in INJECTED_FAULTS:
            fault_name = fault['faultName']
            detections = self.detected_faults.get(fault_name, [])
            
            if not detections:
                undetected_fault_num += 1
                lines.append(f"{undetected_fault_num}. {fault_name}")
                lines.append(f"   Service:       {fault['service']}")
                lines.append(f"   API:           {', '.join(fault['api'])}")
                lines.append(f"   Description:   {fault['description']}")
                lines.append(f"   Status:        NOT DETECTED")
                lines.append("")
                lines.append(f"   Trigger Conditions:")
                lines.append(f"     - Check if the API endpoint was tested")
                lines.append(f"     - Verify authentication is working for admin endpoints")
                lines.append(f"     - Consider increasing test duration")
                lines.append("")
                lines.append("-" * 80)
                lines.append("")
        
        if undetected_count == 0:
            lines.append("All injected faults were detected! Excellent coverage.")
            lines.append("")
        
        # Summary Statistics
        lines.append("=" * 80)
        lines.append("DETECTION STATISTICS")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"{'Fault Name':<45} {'Status':<15} {'Count':<10}")
        lines.append("-" * 70)
        
        for fault in INJECTED_FAULTS:
            fault_name = fault['faultName']
            detections = self.detected_faults.get(fault_name, [])
            status = "DETECTED" if detections else "NOT DETECTED"
            count = len(detections)
            lines.append(f"{fault_name:<45} {status:<15} {count:<10}")
        
        lines.append("-" * 70)
        lines.append(f"{'TOTAL':<45} {detected_count}/{total_faults:<14} {sum(len(d) for d in self.detected_faults.values()):<10}")
        lines.append("")
        
        # Footer
        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)
        
        # Write report
        report_content = "\n".join(lines)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        # Also print to console (handle encoding for Windows)
        try:
            print(report_content)
        except UnicodeEncodeError:
            # Fallback for Windows console encoding issues
            print(report_content.encode('ascii', 'replace').decode('ascii'))
        print(f"\nReport saved to: {output_file}")
        
        return detected_count, total_faults


def main():
    # Default paths
    test_folder = "./generated_tests"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"./fault_detection_report_{timestamp}.log"
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        test_folder = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    # Ensure paths exist
    if not os.path.exists(test_folder):
        print(f"Error: Test folder not found: {test_folder}")
        sys.exit(1)
    
    # Run analysis
    analyzer = FaultDetectionAnalyzer(test_folder)
    analyzer.analyze()
    detected, total = analyzer.generate_report(output_file)
    
    # Print final summary
    detection_rate = detected / total * 100 if total > 0 else 0
    print(f"\n{'='*50}")
    print(f"Final Detection Rate: {detected}/{total} ({detection_rate:.1f}%)")
    print(f"{'='*50}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
