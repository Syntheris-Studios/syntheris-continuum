#!/usr/bin/env python3
"""
Test processing without Gradio's generator handling
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from syntheris_video_processor.core.processor import VideoProcessor

# Find a test file
test_files = list(Path("temp").rglob("segment_001.mp4"))
if not test_files:
    print("No test files")
    sys.exit(1)

test_file = test_files[0]
print(f"Testing: {test_file}")

processor = VideoProcessor()

# Collect all outputs instead of yielding
outputs = []
try:
    for status, output in processor.process_video(
        test_file,
        mode="custom_fps",
        target_fps=30.0,
        atfi_enabled=True
    ):
        if status:
            outputs.append(status)
            print(f"STATUS: {status}")
        if output:
            print(f"OUTPUT: {output}")
except Exception as e:
    print(f"CRASHED: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print(f"\nTotal status messages: {len(outputs)}")
print("Last 5 messages:")
for msg in outputs[-5:]:
    print(f"  - {msg[:100]}...")