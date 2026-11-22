#!/usr/bin/env python3
"""
Syntheris Continuum V5.1.0 - Main Entry Point  
Perfect Duration Preservation + Audio Sync
"""

import sys
import os
import warnings
from pathlib import Path

# Add project root to path BEFORE any local imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)

# Suppress Gradio version warnings
warnings.filterwarnings('ignore', message='.*gradio version.*')
warnings.filterwarnings('ignore', message='.*IMPORTANT.*gradio.*')

def main():
    """Main entry point for Syntheris Continuum."""
    
    # Import and launch the modular UI
    try:
        from syntheris_video_processor.ui.gradio_interface_modular import launch_interface
        print("[V5.1.0] Perfect duration preservation + audio sync")
        print("[V5.1.0] Features: Nuclear duration enforcement, scene detection fix, RIFE v4.26")
        launch_interface(port=7860, share=False)
    except ImportError as e:
        print(f"[ERROR] Failed to import modular UI: {e}")
        print("Make sure all dependencies are installed: pip install -r requirements.txt")
        print("If issues persist, see docs/Troubleshooting.md for solutions")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Failed to launch application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()