#!/usr/bin/env python3
"""
Quick launcher for V5.1.0 - ATFI error handling & fallback system
"""

import sys
import os
from pathlib import Path

# Set up path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

def main():
    try:
        print("=== QUICK LAUNCHER V5.1.0 ===")
        print("Clearing module cache...")
        
        # Force module reload on every launch
        import importlib
        
        # Clear any cached syntheris modules
        modules_to_clear = []
        for module_name in list(sys.modules.keys()):
            if any(x in module_name for x in ['syntheris', 'atfi', 'processor', 'media_utils']):
                modules_to_clear.append(module_name)
        
        for module_name in modules_to_clear:
            del sys.modules[module_name]
            print(f"✓ Purged: {module_name}")
        
        # Force import cache invalidation
        importlib.invalidate_caches()
        print("✓ Module cache cleared - loading fresh code")
        
        print("Loading modules...")
        
        # Test basic imports first
        from syntheris_video_processor.core.processor import VideoProcessor
        print("✓ Core processor loaded")
        
        from syntheris_video_processor.ui.gradio_interface_modular import launch_interface
        print("✓ UI module loaded")
        
        print("✓ All modules loaded successfully")
        print("Starting interface on port 7860...")
        print("Open browser to: http://localhost:7860")
        
        launch_interface(port=7860, share=False)
        
    except ImportError as e:
        print(f"IMPORT ERROR: {e}")
        print("Check if all dependencies are installed in virtual environment")
        sys.exit(1)
    except Exception as e:
        print(f"LAUNCHER ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()