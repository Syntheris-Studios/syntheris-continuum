#!/usr/bin/env python3
"""
Direct RIFE testing without Gradio overhead
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from syntheris_video_processor.backends.rife_backend_final_fixed import RIFEBackend
from syntheris_video_processor.core.atfi import ATFIProcessor

def test_large_file_direct():
    """Test large file processing directly"""
    
    # Find a recent large input file
    test_files = []
    for f in Path("temp").rglob("segment_001.mp4"):
        size_mb = f.stat().st_size / (1024 * 1024)
        if size_mb > 30:  # Large file
            test_files.append((f, size_mb))
    
    if not test_files:
        print("No large test files found")
        return
    
    test_file, size_mb = test_files[0]
    print(f"Testing with: {test_file} ({size_mb:.1f}MB)")
    
    # Test 1: Direct RIFE processing
    print("\n=== TEST 1: Direct RIFE Processing ===")
    try:
        backend = RIFEBackend()
        output_path = test_file.parent / "direct_rife_test.mp4"
        
        for progress in backend.process(
            test_file,
            output_path,
            mode="custom_fps",
            target_fps=30.0,
            scale=1.0,
            uhd_mode="auto"
        ):
            print(f"RIFE: {progress}")
        
        if output_path.exists():
            print(f"SUCCESS: RIFE direct test - {output_path.stat().st_size} bytes")
        else:
            print("FAIL: RIFE direct test - no output")
            
    except Exception as e:
        print(f"FAIL: RIFE direct test - {type(e).__name__}: {e}")
    
    # Test 2: Direct ATFI processing  
    print("\n=== TEST 2: Direct ATFI Processing ===")
    try:
        atfi = ATFIProcessor()
        backend = RIFEBackend()
        
        atfi_output = atfi.process_segment(
            test_file,
            test_file.parent,
            1,
            high_fps=60,
            threshold=0.30,
            min_duration=0.25,
            method="scene",
            backend=backend,
            scale=1.0,
            uhd_mode="auto",
            user_target_fps=30.0
        )
        
        if atfi_output.exists():
            print(f"SUCCESS: ATFI direct test - {atfi_output.stat().st_size} bytes")
        else:
            print("FAIL: ATFI direct test - no output")
            
    except Exception as e:
        print(f"FAIL: ATFI direct test - {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_large_file_direct()