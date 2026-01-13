#!/usr/bin/env python3
"""
Test kworkid parsing logic
"""

def extract_kwork_id(kwork_id_str: str) -> int:
    """Extract numeric ID from Kwork ID string like 'kwork_12345' or 'kwork_12345.678'"""
    try:
        # Remove 'kwork_' prefix
        if kwork_id_str.startswith('kwork_'):
            kwork_id_str = kwork_id_str[6:]
        
        # Extract numeric part before dot if present
        if '.' in kwork_id_str:
            kwork_id_str = kwork_id_str.split('.')[0]
        
        # Convert to integer
        return int(kwork_id_str)
    except (ValueError, AttributeError):
        # Fallback: use hash of string as numeric ID
        return abs(hash(kwork_id_str)) % 1000000000

# Test cases
test_cases = [
    "kwork_12345",
    "kwork_12345.678",
    "12345",
    "kwork_abc123",
    "test-123",
    "",
    None
]

print("Testing kworkid parsing:")
for test in test_cases:
    try:
        result = extract_kwork_id(test)
        print(f"  '{test}' -> {result}")
    except Exception as e:
        print(f"  '{test}' -> ERROR: {e}")

# Test with actual values that might come from Kwork
print("\nSimulating webhook processing:")
sample_kworkids = ["kwork_987654321", "kwork_123456789.001", "invalid_id"]
for kworkid in sample_kworkids:
    numeric_id = extract_kwork_id(kworkid)
    print(f"  Kwork ID: '{kworkid}' -> Numeric ID: {numeric_id}")
    
    # Check if it would work with RPC function
    if numeric_id > 2147483647:  # PostgreSQL INTEGER max value
        print(f"    WARNING: ID {numeric_id} exceeds PostgreSQL INTEGER max (2147483647)")
        print(f"    Should use BIGINT in RPC function")
    else:
        print(f"    OK: ID {numeric_id} within INTEGER range")
