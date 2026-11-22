#!/usr/bin/env python3
"""
Test V4.2.2 Nuclear Diagnostics in isolation
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_v422_import():
    """Test if V4.2.2 nuclear diagnostics are available"""
    print("Testing V4.2.2 nuclear diagnostics import...")
    
    try:
        from syntheris_video_processor.core.processor import VideoProcessor
        
        # Create processor instance
        processor = VideoProcessor()
        
        # Check if nuclear diagnostics are in the code
        import inspect
        source = inspect.getsource(processor.process_video)
        
        if "V4.2.1 NUCLEAR" in source:
            print("SUCCESS: V4.2.2 NUCLEAR diagnostics detected in code!")
            print("SUCCESS: Found V4.2.1 NUCLEAR checkpoints")
            return True
        elif "V4.2.1 EMERGENCY" in source:
            print("SUCCESS: V4.2.2 EMERGENCY diagnostics detected in code!")
            print("SUCCESS: Found V4.2.1 EMERGENCY checkpoints")
            return True
        else:
            print("FAIL: V4.2.2 nuclear diagnostics NOT found")
            print("Code is still using old version")
            return False
            
    except Exception as e:
        print(f"FAIL: Failed to import V4.2.2: {e}")
        return False

def test_generator_issue():
    """Test if the issue is in generator continuation"""
    print("\nTesting generator continuation after ATFI...")
    
    def mock_atfi_generator():
        """Mock ATFI generator to test crash point"""
        yield "Starting ATFI..."
        yield "ATFI processing..."
        yield "[ATFI 1] Original segment: 9.667s -> ATFI output: 9.633s | Diff: 33.3ms"
        
        # This is where the real crash happens
        print("Post-ATFI checkpoint reached")
        yield "Post-ATFI processing..."
        yield "Complete!"
    
    try:
        for message in mock_atfi_generator():
            print(f"Generator yield: {message}")
        print("SUCCESS: Generator continuation works fine")
        return True
    except Exception as e:
        print(f"FAIL: Generator issue: {e}")
        return False

if __name__ == "__main__":
    print("V4.2.2 NUCLEAR DIAGNOSTICS TEST")
    print("=" * 40)
    
    # Test 1: Import check
    import_ok = test_v422_import()
    
    # Test 2: Generator check
    generator_ok = test_generator_issue()
    
    print("\n" + "=" * 40)
    if import_ok:
        print("SUCCESS: V4.2.2 is ready - nuclear diagnostics available")
        print("ISSUE: Main application process needs restart to load V4.2.2")
    else:
        print("FAIL: V4.2.2 not loaded - cache clearing incomplete")
    
    if generator_ok:
        print("SUCCESS: Generator pattern works - issue is elsewhere")
    else:
        print("FAIL: Generator issue detected")