#!/usr/bin/env python3
"""
Script to fix OpenAPI schema references in the merged TrainTicket API spec.

Problem: Schema references use generic 'api_' prefix instead of service-specific prefixes.
Solution: Replace 'api_' with the correct service name from 'x-service-name' field.

Example:
  - Reference: '#/components/schemas/api_HttpEntity'
  - x-service-name: ts-admin-basic-info-service
  - Fixed: '#/components/schemas/ts-admin-basic-info-service_HttpEntity'
"""

import yaml
import re
import sys
from copy import deepcopy


def fix_refs_in_obj(obj, service_name, fixed_count):
    """Recursively fix $ref values in an object, replacing 'api_' with service_name."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == '$ref' and isinstance(value, str):
                # Check for api_ prefix patterns
                patterns = [
                    (r"#/components/schemas/api_", f"#/components/schemas/{service_name}_"),
                    (r"#/components/requestBodies/api_", f"#/components/requestBodies/{service_name}_"),
                ]
                for pattern, replacement in patterns:
                    if re.search(pattern, value):
                        new_value = re.sub(pattern, replacement, value)
                        obj[key] = new_value
                        fixed_count[0] += 1
            else:
                fix_refs_in_obj(value, service_name, fixed_count)
    elif isinstance(obj, list):
        for item in obj:
            fix_refs_in_obj(item, service_name, fixed_count)


def fix_openapi_spec(input_file, output_file):
    """Fix the OpenAPI spec by replacing api_ prefixes with service-specific prefixes."""
    print(f"Loading {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        spec = yaml.safe_load(f)
    
    fixed_count = [0]
    
    # Process each path
    paths = spec.get('paths', {})
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        
        # Process each HTTP method (get, post, put, delete, etc.)
        for method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
            if method not in path_item:
                continue
            
            operation = path_item[method]
            if not isinstance(operation, dict):
                continue
            
            # Get the service name
            service_name = operation.get('x-service-name')
            if not service_name:
                continue
            
            # Fix all $ref values in this operation
            fix_refs_in_obj(operation, service_name, fixed_count)
    
    # Also fix any requestBodies that reference api_ schemas
    request_bodies = spec.get('components', {}).get('requestBodies', {})
    for rb_name, rb_value in list(request_bodies.items()):
        # If the requestBody name starts with api_, we need to handle it differently
        if rb_name.startswith('api_'):
            # Find which service uses this requestBody and fix it
            # For now, we'll look for the schema type and match it
            pass
    
    print(f"Fixed {fixed_count[0]} schema references")
    
    # Now we need to also fix the requestBodies section
    # Find all unique api_ requestBodies that are referenced
    api_request_bodies = set()
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
            if method not in path_item:
                continue
            operation = path_item[method]
            if not isinstance(operation, dict):
                continue
            
            request_body = operation.get('requestBody', {})
            if isinstance(request_body, dict):
                ref = request_body.get('$ref', '')
                if 'api_' in ref:
                    api_request_bodies.add(ref)
    
    # Now we need to create the service-specific requestBodies
    # by duplicating the api_ ones with the correct service name
    components = spec.get('components', {})
    request_bodies = components.get('requestBodies', {})
    
    # Build a mapping of which services need which requestBodies
    service_rb_mapping = {}
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method in ['get', 'post', 'put', 'delete', 'patch', 'options', 'head']:
            if method not in path_item:
                continue
            operation = path_item[method]
            if not isinstance(operation, dict):
                continue
            
            service_name = operation.get('x-service-name')
            if not service_name:
                continue
            
            request_body = operation.get('requestBody', {})
            if isinstance(request_body, dict):
                ref = request_body.get('$ref', '')
                # Check if it's already a service-specific ref (we just fixed it)
                match = re.search(r'#/components/requestBodies/(.+)', ref)
                if match:
                    rb_name = match.group(1)
                    if rb_name.startswith(service_name + '_'):
                        # Extract the base name (after service prefix)
                        base_name = rb_name[len(service_name) + 1:]
                        if service_name not in service_rb_mapping:
                            service_rb_mapping[service_name] = set()
                        service_rb_mapping[service_name].add(base_name)
    
    # Create service-specific requestBodies based on api_ ones
    for service_name, base_names in service_rb_mapping.items():
        for base_name in base_names:
            api_rb_name = f"api_{base_name}"
            service_rb_name = f"{service_name}_{base_name}"
            
            if api_rb_name in request_bodies and service_rb_name not in request_bodies:
                # Copy the api_ requestBody to service-specific one
                request_bodies[service_rb_name] = deepcopy(request_bodies[api_rb_name])
                print(f"Created requestBody: {service_rb_name} from {api_rb_name}")
    
    # Write the fixed spec
    print(f"Writing fixed spec to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(spec, f, default_flow_style=False, allow_unicode=True, sort_keys=False, width=1000)
    
    print("Done!")


if __name__ == '__main__':
    input_file = 'merged_openapi_spec 1.yaml'
    output_file = 'merged_openapi_spec_fixed.yaml'
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    fix_openapi_spec(input_file, output_file)
